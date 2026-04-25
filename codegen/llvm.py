# codegen/llvm.py
from typing import Any

from parser import *


class LLVMCodegen:
    def __init__(self, tree: Program):
        self.tree = tree
        self.output = []
        self.strings = []  # globale String-Konstanten
        self.tmp = 0  # temporäre Register
        self.scope = {}  # name → llvm register
        self.structs = {}  # name → [(field, llvm_type), ...]

    def fresh(self) -> str:
        self.tmp += 1
        return f"%t{self.tmp}"

    def emit(self, line: str):
        self.output.append(line)

    def generate(self) -> str:
        # Erst Structs registrieren
        for node in self.tree.body:
            if isinstance(node, StructDef):
                self.gen_structdef(node)

        # Dann Funktionen
        for node in self.tree.body:
            if isinstance(node, FuncDef):
                self.gen_funcdef(node)

        self.emit("""define void @_start() {
entry:
  %ret = call i32 @main()
  %ret64 = sext i32 %ret to i64
  call i64 asm sideeffect "syscall", "={ax},{ax},{di},~{dirflag},~{fpsr},~{flags}"(i64 60, i64 %ret64)
  ret void
}""")

        header = [
            """define void @__cobra_print_int(i32 %n) {
            entry:
              %is_neg = icmp slt i32 %n, 0
              br i1 %is_neg, label %neg, label %pos
            neg:
              %minus = alloca [1 x i8]
              %mp = getelementptr [1 x i8], [1 x i8]* %minus, i32 0, i32 0
              store i8 45, i8* %mp
              call i64 asm sideeffect "syscall", "={ax},{ax},{di},{si},{dx},~{dirflag},~{fpsr},~{flags}"(i64 1, i64 1, i8* %mp, i64 1)
              %pos_n = sub i32 0, %n
              call void @__cobra_print_int(i32 %pos_n)
              br label %end
            pos:
              %gt9 = icmp sgt i32 %n, 9
              br i1 %gt9, label %recurse, label %digit
            recurse:
              %div = sdiv i32 %n, 10
              call void @__cobra_print_int(i32 %div)
              br label %digit
            digit:
              %mod = srem i32 %n, 10
              %ch = add i32 %mod, 48
              %buf = alloca [1 x i8]
              %bp = getelementptr [1 x i8], [1 x i8]* %buf, i32 0, i32 0
              %ch8 = trunc i32 %ch to i8
              store i8 %ch8, i8* %bp
              call i64 asm sideeffect "syscall", "={ax},{ax},{di},{si},{dx},~{dirflag},~{fpsr},~{flags}"(i64 1, i64 1, i8* %bp, i64 1)
              br label %end
            end:
              ret void
            }""",
            """define i64 @strlen(i8* %s) {
            entry:
              br label %loop
            loop:
              %i = phi i64 [ 0, %entry ], [ %i1, %loop ]
              %p = getelementptr i8, i8* %s, i64 %i
              %c = load i8, i8* %p
              %done = icmp eq i8 %c, 0
              %i1 = add i64 %i, 1
              br i1 %done, label %end, label %loop
            end:
              ret i64 %i
            }"""
        ]

        # Struct Typ-Definitionen in header
        for name, fields in self.structs.items():
            field_types = ", ".join(t for _, t in fields)
            header.append(f"%{name} = type {{ {field_types} }}")

        for i, s in enumerate(self.strings):
            fmt_s = s.replace("\\n", "\\0A").replace("\n", "\\0A")
            length = len(s.replace("\\n", "n")) + 1
            header.append(f'@str{i} = private constant [{length} x i8] c"{fmt_s}\\00"')

        return "\n".join(header + [""] + self.output)

    @staticmethod
    def cobra_type_to_llvm(t: str) -> str:
        mapping = {
            "i8": "i8", "i32": "i32", "i64": "i64",
            "u8": "i8", "u32": "i32", "u64": "i64",
            "void": "void", "ptr<u8>": "i8*",
        }
        if t in mapping:
            return mapping[t]
        # Struct-Typ
        return f"%{t}*"

    def gen_funcdef(self, node: FuncDef):
        self.tmp = 0
        self.scope = {}
        ret = self.cobra_type_to_llvm(node.return_type)
        params_ir = ", ".join(f"{self.cobra_type_to_llvm(t)} %{n}" for n, t in node.params)

        self.emit(f"define {ret} @{node.name}({params_ir}) {{")
        self.emit("entry:")

        for pname, ptype in node.params:
            llty = self.cobra_type_to_llvm(ptype)
            ptr = self.fresh()
            self.emit(f"  {ptr} = alloca {llty}")
            self.emit(f"  store {llty} %{pname}, {llty}* {ptr}")
            self.scope[pname] = (ptr, llty, True)

        for stmt in node.body:
            self.gen_stmt(stmt)

        if node.return_type == "void":
            self.emit("  ret void")
        self.emit("}")

    def gen_stmt(self, node):
        if isinstance(node, LetStmt):
            self.gen_let(node)
        elif isinstance(node, ReturnStmt):
            self.gen_return(node)
        elif isinstance(node, WhileStmt):
            self.gen_while(node)
        elif isinstance(node, IfStmt):
            self.gen_if(node)
        else:
            self.gen_expr(node)

    def gen_let(self, node: LetStmt):
        reg, ty = self.gen_expr(node.value)
        if ty.endswith("*"):  # Pointer direkt speichern
            self.scope[node.name] = (reg, ty, False)
            return
        ptr = self.fresh()
        self.emit(f"  {ptr} = alloca {ty}")
        self.emit(f"  store {ty} {reg}, {ty}* {ptr}")
        self.scope[node.name] = (ptr, ty, True)

    def gen_return(self, node: ReturnStmt):
        reg, type = self.gen_expr(node.value)
        self.emit(f"  ret {type} {reg}")

    def gen_expr(self, node) -> tuple[str, str] | None | Any:
        if isinstance(node, Number):
            return str(node.value), "i32"
        if isinstance(node, StringLit):
            i = len(self.strings)
            self.strings.append(node.value)
            length = len(node.value.replace("\\n", "n")) + 1
            reg = self.fresh()
            self.emit(f"  {reg} = getelementptr [{length} x i8], [{length} x i8]* @str{i}, i32 0, i32 0")
            return reg, "i8*"
        if isinstance(node, StructLit):
            return self.gen_structlit(node)

        if isinstance(node, MemberAccess):
            return self.gen_member_access(node)
        if isinstance(node, Ident):
            ptr, ty, is_ptr = self.scope[node.name]
            if is_ptr:
                reg = self.fresh()
                self.emit(f"  {reg} = load {ty}, {ty}* {ptr}")
                return reg, ty
            return ptr, ty
        if isinstance(node, FuncCall):
            return self.gen_call(node)
        if isinstance(node, IndexAccess):
            return self.gen_index_access(node)
        if isinstance(node, IfStmt):
            self.gen_if(node)
        if isinstance(node, BinOp):
            if node.op == "=":
                reg, ty = self.gen_expr(node.right)
                if isinstance(node.left, Ident):
                    ptr, _, _ = self.scope[node.left.name]
                    self.emit(f"  store {ty} {reg}, {ty}* {ptr}")
                if isinstance(node.left, IndexAccess):
                    ptr_reg, _ = self.gen_expr(node.left.obj)
                    idx_reg, _ = self.gen_expr(node.left.index)
                    gep_reg = self.fresh()
                    self.emit(f"  {gep_reg} = getelementptr i32, i32* {ptr_reg}, i32 {idx_reg}")
                    self.emit(f"  store i32 {reg}, i32* {gep_reg}")
                    return reg, ty
                return reg, ty

            l_reg, l_ty = self.gen_expr(node.left)
            r_reg, _ = self.gen_expr(node.right)
            reg = self.fresh()

            ops = {
                "+": "add", "-": "sub", "*": "mul", "/": "sdiv", "%": "srem",
                "==": "icmp eq", "!=": "icmp ne",
                "<": "icmp slt", ">": "icmp sgt",
                "<=": "icmp sle", ">=": "icmp sge",
            }
            instr = ops.get(node.op, "add")
            self.emit(f"  {reg} = {instr} {l_ty} {l_reg}, {r_reg}")
            result_type = "i1" if "icmp" in instr else l_ty
            return reg, result_type
        return None

    def gen_call(self, node: FuncCall) -> tuple[str, str]:
        if node.name == "syscall":
            return self.gen_syscall(node)
        if node.name == "print":
            return self.gen_print(node)
        if node.name == "alloc":
            return self.gen_alloc(node)

        args = [self.gen_expr(a) for a in node.args]
        args_ir = ", ".join(f"{t} {r}" for r, t in args)
        reg = self.fresh()
        self.emit(f"  {reg} = call i32 @{node.name}({args_ir})")
        return reg, "i32"

    def gen_print(self, node: FuncCall):
        reg, ty = self.gen_expr(node.args[0])

        if ty == "i8*":
            len_reg = self.fresh()
            self.emit(f"  {len_reg} = call i64 @strlen(i8* {reg})")
            syscall_reg = self.fresh()
            constraints = "={ax},{ax},{di},{si},{dx},~{dirflag},~{fpsr},~{flags}"
            self.emit(
                f'  {syscall_reg} = call i64 asm sideeffect "syscall", "{constraints}"(i64 1, i64 1, i8* {reg}, i64 {len_reg})')
            return syscall_reg, "void"

        if ty == "i32":
            self.emit(f"  call void @__cobra_print_int(i32 {reg})")
            return "%0", "void"

        raise NotImplementedError(f"print() für Typ {ty} noch nicht implementiert")

    def gen_syscall(self, node: FuncCall) -> tuple[str, str]:
        processed = []
        for a in node.args:
            r, t = self.gen_expr(a)
            if t == "i32":  # Syscalls brauchen i64
                nr = self.fresh()
                self.emit(f"  {nr} = sext i32 {r} to i64")
                processed.append((nr, "i64"))
            else:
                processed.append((r, t))

        vals = ", ".join(f"{t} {r}" for r, t in processed)
        constraints = "={ax},{ax},{di},{si},{dx},~{dirflag},~{fpsr},~{flags}"
        reg = self.fresh()
        self.emit(f'  {reg} = call i64 asm sideeffect "syscall", "{constraints}"({vals})')
        return reg, "i64"

    def gen_structdef(self, node: StructDef):
        fields = [(fname, self.cobra_type_to_llvm(ftype)) for fname, ftype in node.fields]
        self.structs[node.name] = fields

    def gen_structlit(self, node: StructLit) -> tuple[str, str]:
        # Alloziere auf Stack
        reg = self.fresh()
        self.emit(f"  {reg} = alloca %{node.name}")
        for i, (fname, fval) in enumerate(node.fields):
            val_reg, val_type = self.gen_expr(fval)
            ptr_reg = self.fresh()
            self.emit(f"  {ptr_reg} = getelementptr %{node.name}, %{node.name}* {reg}, i32 0, i32 {i}")
            self.emit(f"  store {val_type} {val_reg}, {val_type}* {ptr_reg}")
        return reg, f"%{node.name}*"

    def gen_member_access(self, node: MemberAccess) -> tuple[str, str]:
        obj_reg, obj_type = self.gen_expr(node.obj)
        struct_name = obj_type.lstrip("%").rstrip("*")
        fields = self.structs[struct_name]
        idx = next(i for i, (f, _) in enumerate(fields) if f == node.member)
        field_type = fields[idx][1]
        ptr_reg = self.fresh()
        val_reg = self.fresh()
        self.emit(f"  {ptr_reg} = getelementptr %{struct_name}, %{struct_name}* {obj_reg}, i32 0, i32 {idx}")
        self.emit(f"  {val_reg} = load {field_type}, {field_type}* {ptr_reg}")
        return val_reg, field_type

    def gen_while(self, node: WhileStmt):
        loop_label = f"while_cond{self.tmp}"
        body_label = f"while_body{self.tmp}"
        end_label = f"while_end{self.tmp}"
        self.tmp += 1

        # Sprung in die Bedingung
        self.emit(f"  br label %{loop_label}")

        # Bedingung prüfen
        self.emit(f"{loop_label}:")
        cond_reg, cond_type = self.gen_expr(node.condition)

        # Falls Bedingung i32 ist → zu i1 konvertieren
        if cond_type == "i32":
            cmp_reg = self.fresh()
            self.emit(f"  {cmp_reg} = icmp ne i32 {cond_reg}, 0")
            cond_reg = cmp_reg

        self.emit(f"  br i1 {cond_reg}, label %{body_label}, label %{end_label}")

        # Body
        self.emit(f"{body_label}:")
        for stmt in node.body:
            self.gen_stmt(stmt)
        self.emit(f"  br label %{loop_label}")

        # Ende
        self.emit(f"{end_label}:")

    def gen_if(self, node: IfStmt):
        then_label = f"if_then{self.tmp}"
        else_label = f"if_else{self.tmp}"
        end_label = f"if_end{self.tmp}"
        self.tmp += 1

        cond_reg, cond_type = self.gen_expr(node.condition)

        # i32 → i1 konvertieren
        if cond_type == "i32":
            cmp_reg = self.fresh()
            self.emit(f"  {cmp_reg} = icmp ne i32 {cond_reg}, 0")
            cond_reg = cmp_reg

        if node.else_body:
            self.emit(f"  br i1 {cond_reg}, label %{then_label}, label %{else_label}")
        else:
            self.emit(f"  br i1 {cond_reg}, label %{then_label}, label %{end_label}")

        # Then
        self.emit(f"{then_label}:")
        for stmt in node.then_body:
            self.gen_stmt(stmt)
        self.emit(f"  br label %{end_label}")

        # Else
        if node.else_body:
            self.emit(f"{else_label}:")
            for stmt in node.else_body:
                self.gen_stmt(stmt)
            self.emit(f"  br label %{end_label}")

        self.emit(f"{end_label}:")

    def gen_alloc(self, node: FuncCall) -> tuple[str, str]:
        count_reg, _ = self.gen_expr(node.args[0])
        size_reg = self.fresh()
        self.emit(f"  {size_reg} = mul i32 {count_reg}, 4")
        size64 = self.fresh()
        self.emit(f"  {size64} = sext i32 {size_reg} to i64")
        ptr_reg = self.fresh()
        constraints = "={ax},{ax},{di},{si},{dx},{r10},{r8},{r9},~{dirflag},~{fpsr},~{flags}"
        self.emit(
            f'  {ptr_reg} = call i64 asm sideeffect "syscall", "{constraints}"(i64 9, i64 0, i64 {size64}, i64 3, i64 34, i64 -1, i64 0)')
        cast_reg = self.fresh()
        self.emit(f"  {cast_reg} = inttoptr i64 {ptr_reg} to i32*")  # ← i32* statt i8*
        return cast_reg, "i32*"

    def gen_index_access(self, node: IndexAccess) -> tuple[str, str]:
        ptr_reg, ptr_type = self.gen_expr(node.obj)
        idx_reg, _ = self.gen_expr(node.index)
        elem_type = "i32"
        gep_reg = self.fresh()
        self.emit(f"  {gep_reg} = getelementptr {elem_type}, {elem_type}* {ptr_reg}, i32 {idx_reg}")
        val_reg = self.fresh()
        self.emit(f"  {val_reg} = load {elem_type}, {elem_type}* {gep_reg}")
        return (val_reg, elem_type)