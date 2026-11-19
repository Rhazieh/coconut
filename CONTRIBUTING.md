# Contributing to Coconut / Contribuir a Coconut

Thanks for taking an interest in **Coconut** (`coco`)! / ¡Gracias por tu interés en **Coconut** (`coco`)!

Coconut is intentionally focused on one job: **fast, distraction-free, eye-comfort Markdown reading on Linux**.

---

## Core Design Principles / Principios de Diseño

1. **Viewer-only:** No inline editor, no split source/preview panes, no WYSIWYG clutter.
2. **Local-first & offline:** Never add network telemetry, remote CDNs, or cloud sync requirements.
3. **Single typeface:** Everything renders in **Atkinson Hyperlegible Next** (`Noto Color Emoji` strictly as emoji glyph fallback).
4. **Eye comfort first:** Low-halation palettes and comfortable measure (`68ch`), line height, and text scaling (`12–36 px`).
5. **Cross-DE & Wayland/X11 friendly:** Rely on standard XDG directories and PyQt6 rather than desktop-specific hacks.

---

## Development Setup / Entorno de Desarrollo

```bash
git clone https://github.com/Rhazieh/coconut.git
cd coconut
python3 -m unittest discover -s tests -v
python3 src/coconut/app.py --standalone docs/demo.md
```

Before opening a pull request:
- Keep functions small and clean; add docstrings and unit tests in `tests/` for new behavior.
- Run `python3 -m py_compile src/coconut/*.py tests/*.py`, `bash -n install.sh uninstall.sh`, and `python3 -m unittest discover -s tests -v`.
- Verify GUI changes with `python3 src/coconut/app.py --self-test docs/demo.md`.
