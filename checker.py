from lexer import tokenize
from parser import Parser

BUILTINS = {
    "syscall",
    "cast",
    "print",
    "alloc",
}

# typechecker.py
from parser import *

class TypeError(Exception):
    def __init__(self, message, line=0):
        self.message = message
        self.line    = line

    def __str__(self):
        return f"\nCobraTypeError: {self.message} (Zeile {self.line})\n"

class TypeChecker:
    def __init__(self, tree: Program):
        self.tree = tree
        self.scope = {}
        self.funcs = {}
        self.structs = {}  # name → {field: type}

    def check(self):
        # Erst Structs registrieren
        for node in self.tree.body:
            if isinstance(node, StructDef):
                self.structs[node.name] = dict(node.fields)

        # Dann Funktionssignaturen
        for node in self.tree.body:
            if isinstance(node, FuncDef):
                self.funcs[node.name] = (node.params, node.return_type)

        # Dann alles prüfen
        for node in self.tree.body:
            self.check_node(node)

    def check_node(self, node):
        if isinstance(node, FuncDef):
            self.check_funcdef(node)
        elif isinstance(node, LetStmt):
            self.check_let(node)
        elif isinstance(node, ReturnStmt):
            self.check_return(node)
        elif isinstance(node, IfStmt):
            self.check_if(node)
        elif isinstance(node, WhileStmt):
            self.check_while(node)
        elif isinstance(node, StructDef):
            pass  # bereits registriert
        else:
            self.infer_type(node)

    def check_funcdef(self, node: FuncDef):
        # Parameter in Scope laden
        for pname, ptype in node.params:
            self.scope[pname] = ptype
        for stmt in node.body:
            self.check_node(stmt)

    def check_while(self, node: WhileStmt):
        self.infer_type(node.condition)
        for stmt in node.body:
            self.check_node(stmt)

    def check_let(self, node: LetStmt):
        value_type = self.infer_type(node.value)
        # alloc gibt immer einen ptr zurück — Typ vom let übernehmen
        if isinstance(node.value, FuncCall) and node.value.name == "alloc":
            self.scope[node.name] = node.type
            return
        if value_type != node.type and node.type not in self.structs:
            raise TypeError(
                f"Typ-Mismatch: '{node.name}' ist {node.type}, aber Wert ist {value_type}",
                line=0
            )
        self.scope[node.name] = node.type

    def check_return(self, node: ReturnStmt):
        self.infer_type(node.value)  # prüft, ob Wert gültig ist

    def check_if(self, node: IfStmt):
        self.infer_type(node.condition)
        for stmt in node.then_body:
            self.check_node(stmt)
        if node.else_body:
            for stmt in node.else_body:
                self.check_node(stmt)

    def infer_type(self, node) -> str:
        if isinstance(node, Number):
            return "i32"

        if isinstance(node, StructLit):
            if node.name not in self.structs:
                raise TypeError(f"Unbekannter Struct '{node.name}'")
            return node.name

        if isinstance(node, IndexAccess):
            obj_type = self.infer_type(node.obj)
            # ptr<i32>[i] → i32
            if obj_type.startswith("ptr<"):
                return obj_type[4:-1]  # ptr<i32> → i32
            raise TypeError(f"'{obj_type}' ist nicht indexierbar")

        if isinstance(node, MemberAccess):
            obj_type = self.infer_type(node.obj)
            if obj_type not in self.structs:
                raise TypeError(f"'{obj_type}' ist kein Struct")
            fields = self.structs[obj_type]
            if node.member not in fields:
                raise TypeError(f"Struct '{obj_type}' hat kein Feld '{node.member}'")
            return fields[node.member]

        if isinstance(node, FuncCall):
            if node.name in BUILTINS:
                if node.name == "syscall": return "i64"
                if node.name == "cast":    return "ptr<u8>"  # Platzhalter
                if node.name == "print": return "void"
                if node.name == "alloc": return "ptr<i32>"

            if node.name not in self.funcs:
                raise TypeError(f"Unbekannte Funktion '{node.name}'")

        if isinstance(node, StringLit):
            return "ptr<u8>"

        if isinstance(node, Ident):
            if node.name not in self.scope:
                raise TypeError(f"Unbekannte Variable '{node.name}'")
            return self.scope[node.name]

        if isinstance(node, BinOp):
            left  = self.infer_type(node.left)
            right = self.infer_type(node.right)
            if left != right:
                raise TypeError(f"Typ-Mismatch in BinOp: {left} {node.op} {right}")
            return left

        if isinstance(node, FuncCall):
            if node.name not in self.funcs:
                raise TypeError(f"Unbekannte Funktion '{node.name}'")
            params, return_type = self.funcs[node.name]
            if len(node.args) != len(params):
                raise TypeError(f"Falsche Anzahl Argumente für '{node.name}'")
            return return_type

        raise TypeError(f"Unbekannter Node-Typ: {type(node)}")
