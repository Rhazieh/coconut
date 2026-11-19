"""Lightweight English / Spanish UI localization for Velum."""

from __future__ import annotations

import os
from typing import Mapping

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "toc_label": "Outline",
        "welcome_sub": "Drop a <code>.md</code> file here or open one from disk.",
        "welcome_open": "Open file…",
        "recent_title": "Recent",
        "hint_open": "Ctrl+O Open",
        "hint_zoom": "Ctrl+/− Text",
        "hint_theme": "Ctrl+T Palette",
        "hint_toc": "Ctrl+B Outline",
        "btn_toc_title": "Outline (Ctrl+B)",
        "btn_open_title": "Open file (Ctrl+O)",
        "btn_dec_title": "Decrease text size (Ctrl+-)",
        "btn_reset_title": "Reset text size (Ctrl+0)",
        "btn_inc_title": "Increase text size (Ctrl++)",
        "btn_theme_prefix": "Palette",
        "find_placeholder": "Find…",
        "find_prev_title": "Previous (Shift+Enter)",
        "find_next_title": "Next (Enter)",
        "find_close_title": "Close (Esc)",
        "drop_prompt": "Drop file to read",
        "copy_btn": "Copy",
        "copied_btn": "Copied",
        "toast_copied": "Copied",
        "toast_text": "Text: {size} px",
        "toast_palette": "Palette: {label}",
        "toast_reloaded": "Reloaded",
        "toast_not_found": "File not found: {name}",
        "toast_open_error": "Unable to open: {err}",
        "theme_warm-dark": "Warm Night",
        "theme_sepia": "Paper Sepia",
        "theme_soft-light": "Soft Stone",
        "dialog_open_title": "Open Markdown File",
        "dialog_filter": "Markdown files (*.md *.markdown *.mdown *.mkd *.mdx);;Text (*.txt);;All files (*)",
        "ctx_copy": "Copy",
        "ctx_open": "Open file…\tCtrl+O",
        "ctx_inc": "Increase text\tCtrl++",
        "ctx_dec": "Decrease text\tCtrl+-",
        "ctx_reset": "Default size\tCtrl+0",
        "ctx_theme": "Switch palette\tCtrl+T",
        "ctx_toc": "Toggle outline\tCtrl+B",
    },
    "es": {
        "toc_label": "Índice",
        "welcome_sub": "Arrastrá un archivo <code>.md</code> aquí o abrí uno desde tu carpeta.",
        "welcome_open": "Abrir archivo…",
        "recent_title": "Recientes",
        "hint_open": "Ctrl+O Abrir",
        "hint_zoom": "Ctrl+/− Texto",
        "hint_theme": "Ctrl+T Paleta",
        "hint_toc": "Ctrl+B Índice",
        "btn_toc_title": "Índice (Ctrl+B)",
        "btn_open_title": "Abrir archivo (Ctrl+O)",
        "btn_dec_title": "Reducir texto (Ctrl+-)",
        "btn_reset_title": "Restablecer tamaño normal (Ctrl+0)",
        "btn_inc_title": "Aumentar texto (Ctrl++)",
        "btn_theme_prefix": "Paleta",
        "find_placeholder": "Buscar…",
        "find_prev_title": "Anterior (Shift+Enter)",
        "find_next_title": "Siguiente (Enter)",
        "find_close_title": "Cerrar (Esc)",
        "drop_prompt": "Soltá el archivo para leerlo",
        "copy_btn": "Copiar",
        "copied_btn": "Copiado",
        "toast_copied": "Copiado",
        "toast_text": "Texto: {size} px",
        "toast_palette": "Paleta: {label}",
        "toast_reloaded": "Actualizado",
        "toast_not_found": "No se encontró: {name}",
        "toast_open_error": "Error al abrir: {err}",
        "theme_warm-dark": "Noche cálida",
        "theme_sepia": "Sepia papel",
        "theme_soft-light": "Piedra suave",
        "dialog_open_title": "Abrir archivo Markdown",
        "dialog_filter": "Archivos Markdown (*.md *.markdown *.mdown *.mkd *.mdx);;Texto (*.txt);;Todos los archivos (*)",
        "ctx_copy": "Copiar",
        "ctx_open": "Abrir archivo…\tCtrl+O",
        "ctx_inc": "Aumentar texto\tCtrl++",
        "ctx_dec": "Reducir texto\tCtrl+-",
        "ctx_reset": "Tamaño normal\tCtrl+0",
        "ctx_theme": "Cambiar paleta\tCtrl+T",
        "ctx_toc": "Mostrar/ocultar índice\tCtrl+B",
    },
}


def resolve_language(pref: str = "auto", env: Mapping[str, str] | None = None) -> str:
    """Resolve UI language ('en' or 'es') from explicit preference or system locale."""
    if pref in ("en", "es"):
        return pref

    lookup = env if env is not None else os.environ
    for key in ("LC_ALL", "LANGUAGE", "LANG"):
        val = lookup.get(key, "").strip().lower()
        if not val:
            continue
        first = val.split(":", 1)[0]
        if first.startswith("es"):
            return "es"
        if first.startswith(("en", "c.", "c", "posix")):
            return "en"

    try:
        from PyQt6.QtCore import QLocale

        if QLocale.system().name().lower().startswith("es"):
            return "es"
    except Exception:
        pass

    return "en"


def get_strings(lang: str) -> dict[str, str]:
    """Return UI string table for the resolved language."""
    return dict(STRINGS["es"] if lang == "es" else STRINGS["en"])
