# codegen/llvm.py
from parser import *


class LLVMCodegen:
    def __init__(self, tree: Program):
        self.tree = tree
        self.output = []
        self.strings = []  # globale String-Konstanten
        self.tmp = 0  # temporäre Register
        self.scope = {}  # name → llvm register

    def fresh(self) -> str:
        self.tmp += 1
        return f"%t{self.tmp}"

    def emit(self, line: str):
        self.output.append(line)

    def generate(self) -> str:
        for node in self.tree.body:
            if isinstance(node, FuncDef):
                self.gen_funcdef(node)

        header = []
        for i, s in enumerate(self.strings):
            # Zeilenumbrüche für LLVM korrekt formatieren (\n -> \0A)
            fmt_s = s.replace("\\n", "\\0A").replace("\n", "\\0A")
            length = len(s.replace("\\n", "n")) + 1
            header.append(f'@str{i} = private constant [{length} x i8] c"{fmt_s}\\00"')

        return "\n".join(header + [""] + self.output)

    def cobra_type_to_llvm(self, t: str) -> str:
        mapping = {
            "i8": "i8", "i32": "i32", "i64": "i64",
            "u8": "i8", "u32": "i32", "u64": "i64",
            "void": "void", "ptr<u8>": "i8*",
        }
        return mapping.get(t, "i32")

    def gen_funcdef(self, node: FuncDef):
        self.tmp = 0
        self.scope = {}
        ret = self.cobra_type_to_llvm(node.return_type)
        params_ir = ", ".join(f"{self.cobra_type_to_llvm(t)} %{n}" for n, t in node.params)

        self.emit(f"define {ret} @{node.name}({params_ir}) {{")
        self.emit("entry:")

        for pname, ptype in node.params:
            self.scope[pname] = (f"%{pname}", self.cobra_type_to_llvm(ptype))

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
        else:
            self.gen_expr(node)

    def gen_let(self, node: LetStmt):
        reg, _ = self.gen_expr(node.value)
        self.scope[node.name] = (reg, self.cobra_type_to_llvm(node.type))

    def gen_return(self, node: ReturnStmt):
        reg, type = self.gen_expr(node.value)
        self.emit(f"  ret {type} {reg}")

    def gen_expr(self, node) -> tuple[str, str]:
        if isinstance(node, Number):
            return (str(node.value), "i32")
        if isinstance(node, StringLit):
            i = len(self.strings)
            self.strings.append(node.value)
            length = len(node.value.replace("\\n", "n")) + 1
            reg = self.fresh()
            self.emit(f"  {reg} = getelementptr [{length} x i8], [{length} x i8]* @str{i}, i32 0, i32 0")
            return (reg, "i8*")
        if isinstance(node, Ident):
            return self.scope[node.name]
        if isinstance(node, FuncCall):
            return self.gen_call(node)
        if isinstance(node, BinOp):
            l_reg, l_ty = self.gen_expr(node.left)
            r_reg, _ = self.gen_expr(node.right)
            reg = self.fresh()
            op = {"+": "add", "-": "sub", "*": "mul"}.get(node.op, "add")
            self.emit(f"  {reg} = {op} {l_ty} {l_reg}, {r_reg}")
            return (reg, l_ty)
        return "0", "i32"

    def gen_call(self, node: FuncCall) -> tuple[str, str]:
        if node.name == "syscall":
            return self.gen_syscall(node)

        args = [self.gen_expr(a) for a in node.args]
        args_ir = ", ".join(f"{t} {r}" for r, t in args)
        reg = self.fresh()
        self.emit(f"  {reg} = call i32 @{node.name}({args_ir})")
        return (reg, "i32")

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
        return (reg, "i64")

    