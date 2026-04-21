# 🐍 Cobra Programming Language

**Cobra** ist eine moderne Systemprogrammiersprache, die die Eleganz und Lesbarkeit von **Python** mit der kompromisslosen Performance von **C** verbindet. Sie wurde entwickelt, um direkt zu Maschinencode kompiliert zu werden – ohne Garbage Collector, ohne Runtime-Overhead.

### 🚀 Das Ziel
Cobra schließt die Lücke zwischen High-Level-Scripting und Low-Level-Systems-Programming. Schreibe deinen Betriebssystem-Kernel, Treiber oder Embedded-Software in einer Syntax, die du liebst, mit der Kontrolle, die du brauchst.

---

## ✨ Key Features

* **Pythonic Syntax:** 1:1 Support für Pythons Einrückungs-Logik.
* **Dual-Block Support:** Nutze `: / Indents` oder `{ / }` – ganz wie du willst (oder mische sie!).
* **Static Typing:** C-ähnliche Typen (`i32`, `u8`, `ptr`, `struct`) für maximale Performance und Sicherheit.
* **Freestanding & Bare-Metal:** Kein Standard-OS nötig. Perfekt für die Kernel-Entwicklung.
* **Manual Memory Access:** Volle Kontrolle über Pointer-Arithmetik und direkten Speicherzugriff.
* **Self-Hosting Roadmap:** Der erste Compiler ist in Python geschrieben, der finale Compiler wird in Cobra selbst geschrieben.

---

## 🛠 Syntax-Vorschau

Cobra fühlt sich an wie Python, agiert aber wie C:

```python
# Cobra: Low-Level Power mit High-Level Look
struct VGAChar:
    character: u8
    color: u8

def kmain(magic: u32, addr: *u32) -> i32:
    # Manueller Speicherzugriff (VGA Buffer)
    video_mem: *VGAChar = cast(*VGAChar, 0xB8000)
    
    if magic == 0x2BADB002 {
        video_mem[0].character = 0x43 # 'C'
        video_mem[0].color = 0x0F     # Weiß auf Schwarz
    }
    
    return 0