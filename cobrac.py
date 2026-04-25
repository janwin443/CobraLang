#!/usr/bin/python3
import argparse
import subprocess
import os
import sys
from lexer import tokenize
from parser import Parser
from checker import TypeChecker
from codegen.llvm import LLVMCodegen

def main():
    arg_parser = argparse.ArgumentParser(description="CobraLang Compiler")
    arg_parser.add_argument("input", help="Eingabedatei (.co)")
    arg_parser.add_argument("-o", "--output", help="Output Binary Name", default="a.out")
    arg_parser.add_argument("-s", "--asm", help="Generiere Assembly (.s)", action="store_true")
    arg_parser.add_argument("-x", "--hex", help="Generiere Hexdump", action="store_true")
    arg_parser.add_argument("-v", "--verbose", help="Verbose Output", action="store_true")
    args = arg_parser.parse_args()

    def log(msg):
        if args.verbose:
            print(msg)

    if not os.path.exists(args.input):
        print(f"Fehler: Datei '{args.input}' nicht gefunden.")
        sys.exit(1)

    with open(args.input, "r") as f:
        source = f.read()

    print(f"[*] Kompiliere {args.input}...")

    try:
        tokens = tokenize(source)
        log("\n=== TOKENS ===")
        for tok in tokens:
            log(f"  {tok}")

        tree = Parser(tokens).parse()
        log("\n=== AST ===")
        for node in tree.body:
            log(f"  {node}")

        TypeChecker(tree).check()
        log("\n=== TYPCHECK OK ===")

        ir = LLVMCodegen(tree).generate()
        log("\n=== LLVM IR ===")
        log(ir)

    except Exception as e:
        print(f"[!] Compiler Fehler: {e}")
        sys.exit(1)

    base_name = args.input.rsplit(".", 1)[0]
    ll_file = f"{base_name}.ll"
    obj_file = f"{base_name}.o"
    asm_file = f"{base_name}.s"

    with open(ll_file, "w") as f:
        f.write(ir)

    try:
        log("\n=== TOOLCHAIN ===")
        subprocess.run(["llc", "-filetype=obj", "-relocation-model=static", ll_file, "-o", obj_file], check=True)
        log(f"[+] Object File: {obj_file}")

        if args.asm:
            subprocess.run(["llc", "-filetype=asm", "-relocation-model=static", ll_file, "-o", asm_file], check=True)
            print(f"[+] Assembly gespeichert in {asm_file}")

        subprocess.run(["ld", "-static", obj_file, "-o", args.output], check=True)
        print(f"[+] Binary erzeugt: {args.output}")

        if args.hex:
            print(f"[*] Hexdump von {args.output}:")
            subprocess.run(["hexdump", "-C", args.output])

    except subprocess.CalledProcessError as e:
        print(f"[!] Toolchain Fehler: {e}")
    finally:
        if os.path.exists(ll_file): os.remove(ll_file)
        if os.path.exists(obj_file): os.remove(obj_file)

if __name__ == "__main__":
    main()