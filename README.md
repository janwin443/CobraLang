# 🐍 Cobra Programming Language

**Cobra** ist eine Systemprogrammiersprache mit Python-Syntax die direkt zu Maschinencode kompiliert.
Kein Garbage Collector, kein Runtime, kein libc — perfekt für Kernel, Embedded und Homebrew-CPUs.

> *"If you know Python, you know Cobra."*

---

## Was Cobra kann

```python
def fib(n: i32) -> i32:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

def main() -> i32:
    let i: i32 = 0
    while i <= 15:
        print("fib(")
        print(i)
        print(") = ")
        print(fib(i))
        print("\n")
        i = i + 1
    return 0
```

Das kompiliert zu einem **freestanding ELF Binary** — kein libc, keine Dependencies, direkte Linux Syscalls.

---

## Features

- **Python-Syntax** — Einrückung, `def`, `if`, `while`, `return`, alles identisch
- **C-Typen** — `i8`, `i16`, `i32`, `i64`, `u8`–`u64`, `f32`, `f64`, `bool`, `void`, `ptr<T>`
- **Structs** — mit Member-Zugriff (`tok.type`)
- **Arrays** — `ptr<i32>` + `arr[i]` Syntax
- **Manuelle Speicherverwaltung** — `alloc(n)` via mmap Syscall, kein GC
- **Freestanding** — kein libc, direkter Zugriff auf Syscalls
- **LLVM Backend** — optimierter Code für x86-64, ARM, und mehr
- **Kein Semikolon** — nie

---

## Syntax

### Variablen
```python
let x: i32 = 42
let msg: ptr<u8> = "Hello Cobra!\n"
let arr: ptr<i32> = alloc(10)
```

### Funktionen
```python
def add(a: i32, b: i32) -> i32:
    return a + b
```

### Structs
```python
struct Token:
    type: ptr<u8>
    value: ptr<u8>
    line: i32

def main() -> i32:
    let tok: Token = Token { type: "KEYWORD", value: "def", line: 1 }
    let l: i32 = tok.line
    return l
```

### Arrays
```python
let arr: ptr<i32> = alloc(5)
arr[0] = 10
arr[1] = 20
let x: i32 = arr[1]   # x = 20
```

### Syscalls
```python
syscall(1, 1, msg, 13)   # write(stdout, msg, 13)
syscall(60, 0, 0, 0)     # exit(0)
```

### Beide Block-Stile
```python
# Python-Stil
def foo() -> i32:
    return 1

# C-Stil
def foo() -> i32 {
    return 1
}
```

---

## Compiler Pipeline

```
source.co
    ↓ lexer.py        — Tokenizer (re-based, INDENT/DEDENT)
    ↓ parser.py       — Recursive Descent, AST
    ↓ checker.py      — Typchecker
    ↓ codegen/llvm.py — LLVM IR Generator
    ↓ llc             — LLVM → Object File
    ↓ ld              — Linker → ELF Binary
```

---

## Installation & Usage

```bash
# Abhängigkeiten
pacman -S llvm python      # Arch Linux
apt install llvm python3   # Debian/Ubuntu

# Kompilieren
git clone https://github.com/CobraLabs/cobra
cd cobra

# Hello World
./cobrac.py hello.co -o hello
./hello

# Flags
./cobrac.py hello.co -o hello -v    # Verbose (Tokens, AST, IR)
./cobrac.py hello.co -o hello -s    # Assembly Output
./cobrac.py hello.co -o hello -x    # Hexdump
```

---

## Datentypen

| Typ | Größe | Beschreibung |
|-----|-------|--------------|
| `i8` | 1B | Signed 8-bit |
| `i16` | 2B | Signed 16-bit |
| `i32` | 4B | Signed 32-bit |
| `i64` | 8B | Signed 64-bit |
| `u8`–`u64` | 1–8B | Unsigned |
| `f32` | 4B | Float |
| `f64` | 8B | Double |
| `bool` | 1B | Boolean |
| `void` | — | Kein Rückgabewert |
| `ptr<T>` | 8B | Pointer auf T |

---

## Projektstruktur

```
cobra/
├── cobrac.py          — Compiler Entry Point
├── lexer.py           — Tokenizer
├── parser.py          — Parser + AST Nodes
├── checker.py         — Typchecker
├── codegen/
│   ├── __init__.py
│   └── llvm.py        — LLVM IR Codegen
├── builtins/
│   └── builtins.py    — Builtin Funktionen
├── examples/
│   ├── hello.co
│   └── fibonacci.co
└── README.md
```

---

## Roadmap

### Phase 1 — Python Compiler ✅
- [x] Lexer (INDENT/DEDENT, alle Token)
- [x] Parser (AST, alle Konstrukte)
- [x] Typchecker
- [x] LLVM IR Codegen
- [x] Structs + Member Access
- [x] Arrays (`ptr<T>` + `arr[i]`)
- [x] while loops
- [x] if/else
- [x] Arithmetik + Vergleiche
- [x] print (String + Integer)
- [x] alloc (mmap-basiert, kein libc)
- [x] freestanding Binary (kein libc)

### Phase 2 — Spracherweiterungen
- [ ] `for` + `range`
- [ ] String Vergleiche (`streq`)
- [ ] Import System
- [ ] `isinstance` (tagged structs)
- [ ] Pointer Dereferenzierung (`*ptr`)

### Phase 3 — Targets
- [ ] Sectum-V Backend (custom 64-bit RISC CPU)
- [ ] LLVM Backend für Sectum-V

### Phase 4 — Self-Hosting
- [ ] Cobra in Cobra schreiben (`cobrac.co`)
- [ ] Bootstrap: `cobrac.py` kompiliert `cobrac.co`
- [ ] Cobra kompiliert sich selbst

### Phase 5 — Kernel
- [ ] ZenKernel in Cobra portieren
- [ ] Echter malloc/free
- [ ] Prozesse + Scheduling

---

## Kontakt

- 📧 **Email:** support-cobralabs@proton.me
- 🐙 **GitHub:** github.com/CobraLabs

---

*Cobra — Code like Python. Run like C. Strike like a machine.* ⚡🐍