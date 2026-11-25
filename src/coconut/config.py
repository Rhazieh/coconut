"""Persistent XDG-compliant settings management for Coconut."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

MIN_FONT_SIZE = 12
MAX_FONT_SIZE = 36
DEFAULT_FONT_SIZE = 18

MIN_SIDEBAR_WIDTH = 180
MAX_SIDEBAR_WIDTH = 520
DEFAULT_SIDEBAR_WIDTH = 260

IGNORED_DIR_NAMES: frozenset[str] = frozenset({
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".idea",
    ".vscode",
    "dist",
    "build",
    "target",
    ".next",
    ".nuxt",
})

VALID_THEMES = ("warm-dark", "sepia", "soft-light")
VALID_LANGUAGES = ("auto", "en", "es")
VALID_READING_WIDTHS = ("narrow", "medium", "wide")
VALID_LINE_HEIGHTS = ("compact", "comfortable", "spacious")
VALID_ACCENT_COLORS = ("default", "amber", "sage", "ocean", "berry", "lavender")
VALID_CODE_STYLES = ("card", "minimal", "contrast")

THEME_BG = {
    "warm-dark": "#191817",
    "sepia": "#F3ECDC",
    "soft-light": "#F4F3EE",
}

MAX_RECENT_FILES = 8

CORE_MD_EXTENSIONS: tuple[str, ...] = (
    ".md",
    ".markdown",
    ".mdown",
    ".mkd",
    ".mkdn",
    ".mdx",
)

EXTENSION_CATALOG: tuple[dict[str, Any], ...] = (
    {
        "id": "txt",
        "category": "document",
        "badge": ".txt",
        "extensions": (".txt", ".text", ".log"),
        "lang": "plaintext",
        "name_en": "Plain Text",
        "name_es": "Texto plano",
        "desc_en": "Distraction-free reader and editor for .txt, .text, and .log notes.",
        "desc_es": "Lectura y edición limpia para notas y registros .txt, .text y .log.",
    },
    {
        "id": "epub",
        "category": "document",
        "badge": ".epub",
        "extensions": (".epub",),
        "lang": "epub",
        "name_en": "EPUB E-Books",
        "name_es": "Libros EPUB",
        "desc_en": "Lightweight native e-book reader with chapter outline navigation.",
        "desc_es": "Lector nativo y liviano de libros digitales con índice de capítulos lateral.",
    },
    {
        "id": "js",
        "category": "code",
        "badge": ".js .jsx",
        "extensions": (".js", ".jsx", ".mjs", ".cjs"),
        "lang": "javascript",
        "name_en": "JavaScript & JSX",
        "name_es": "JavaScript y JSX",
        "desc_en": "Syntax highlighting and symbol outline for ES modules, Node, and React JSX.",
        "desc_es": "Resaltado de sintaxis e índice para módulos ES, Node y React JSX.",
    },
    {
        "id": "ts",
        "category": "code",
        "badge": ".ts .tsx",
        "extensions": (".ts", ".tsx"),
        "lang": "typescript",
        "name_en": "TypeScript & TSX",
        "name_es": "TypeScript y TSX",
        "desc_en": "Type-aware syntax highlighting for TypeScript and TSX components.",
        "desc_es": "Resaltado de sintaxis con soporte de tipos e interfaces para TypeScript y TSX.",
    },
    {
        "id": "py",
        "category": "code",
        "badge": ".py",
        "extensions": (".py", ".pyw", ".pyi"),
        "lang": "python",
        "name_en": "Python",
        "name_es": "Python",
        "desc_en": "Syntax highlighting and class/function outline for Python scripts.",
        "desc_es": "Resaltado de sintaxis e índice de clases y funciones para scripts Python.",
    },
    {
        "id": "java",
        "category": "code",
        "badge": ".java",
        "extensions": (".java",),
        "lang": "java",
        "name_en": "Java",
        "name_es": "Java",
        "desc_en": "Syntax highlighting for Java classes, annotations, interfaces, and types.",
        "desc_es": "Resaltado de sintaxis para clases, anotaciones, interfaces y tipos de Java.",
    },
    {
        "id": "html",
        "category": "code",
        "badge": ".html",
        "extensions": (".html", ".htm"),
        "lang": "html",
        "name_en": "HTML",
        "name_es": "HTML",
        "desc_en": "Source inspection and editing with tag and attribute highlighting.",
        "desc_es": "Inspección y edición de código fuente HTML con resaltado de etiquetas y atributos.",
    },
    {
        "id": "css",
        "category": "code",
        "badge": ".css",
        "extensions": (".css", ".scss", ".less"),
        "lang": "css",
        "name_en": "CSS & Stylesheets",
        "name_es": "CSS y Hojas de estilo",
        "desc_en": "Syntax highlighting for CSS selectors, custom properties, and rules.",
        "desc_es": "Resaltado de sintaxis para selectores, variables y reglas de estilo CSS.",
    },
    {
        "id": "json",
        "category": "code",
        "badge": ".json",
        "extensions": (".json", ".jsonc", ".jsonl"),
        "lang": "json",
        "name_en": "JSON",
        "name_es": "JSON",
        "desc_en": "Clean key, value, number, and boolean highlighting for JSON data.",
        "desc_es": "Resaltado claro de claves, valores, números y booleanos para archivos JSON.",
    },
    {
        "id": "yaml",
        "category": "code",
        "badge": ".yaml .yml",
        "extensions": (".yaml", ".yml"),
        "lang": "yaml",
        "name_en": "YAML",
        "name_es": "YAML",
        "desc_en": "Syntax highlighting for configuration files, manifests, and CI workflows.",
        "desc_es": "Resaltado de sintaxis para archivos de configuración, manifiestos y pipelines.",
    },
    {
        "id": "sh",
        "category": "code",
        "badge": ".sh",
        "extensions": (".sh", ".bash", ".zsh"),
        "lang": "bash",
        "name_en": "Shell & Bash",
        "name_es": "Shell y Bash",
        "desc_en": "Highlighting for Linux shell scripts, flags, variables, and functions.",
        "desc_es": "Resaltado para scripts de terminal Linux, variables, banderas y funciones.",
    },
    {
        "id": "sql",
        "category": "code",
        "badge": ".sql",
        "extensions": (".sql",),
        "lang": "sql",
        "name_en": "SQL",
        "name_es": "SQL",
        "desc_en": "Syntax highlighting for database queries, schemas, and migrations.",
        "desc_es": "Resaltado de sintaxis para consultas, esquemas y migraciones de bases de datos.",
    },
    {
        "id": "c_cpp",
        "category": "code",
        "badge": ".c .cpp",
        "extensions": (".c", ".cpp", ".cc", ".cxx", ".h", ".hpp"),
        "lang": "cpp",
        "name_en": "C & C++",
        "name_es": "C y C++",
        "desc_en": "Highlighting for C/C++ source and header files, macros, and types.",
        "desc_es": "Resaltado para código fuente y cabeceras C/C++, directivas y tipos.",
    },
    {
        "id": "rs",
        "category": "code",
        "badge": ".rs",
        "extensions": (".rs",),
        "lang": "rust",
        "name_en": "Rust",
        "name_es": "Rust",
        "desc_en": "Syntax highlighting for Rust traits, lifetimes, macros, and structs.",
        "desc_es": "Resaltado de sintaxis para traits, lifetimes, macros y estructuras de Rust.",
    },
    {
        "id": "go",
        "category": "code",
        "badge": ".go",
        "extensions": (".go",),
        "lang": "go",
        "name_en": "Go",
        "name_es": "Go",
        "desc_en": "Syntax highlighting for Go packages, goroutines, structs, and interfaces.",
        "desc_es": "Resaltado de sintaxis para paquetes, goroutines, estructuras e interfaces de Go.",
    },
    {
        "id": "xml",
        "category": "code",
        "badge": ".xml",
        "extensions": (".xml",),
        "lang": "xml",
        "name_en": "XML",
        "name_es": "XML",
        "desc_en": "Clean tag, namespace, and attribute highlighting for XML documents.",
        "desc_es": "Resaltado limpio de etiquetas, espacios de nombres y atributos XML.",
    },
)

VALID_EXTENSION_IDS: tuple[str, ...] = tuple(item["id"] for item in EXTENSION_CATALOG)
EXTENSION_BY_ID: dict[str, dict[str, Any]] = {item["id"]: item for item in EXTENSION_CATALOG}

EXTENSION_ALIASES: dict[str, str] = {
    "text": "txt",
    "plaintext": "txt",
    "log": "txt",
    "javascript": "js",
    "jsx": "js",
    "mjs": "js",
    "cjs": "js",
    "typescript": "ts",
    "tsx": "ts",
    "python": "py",
    "htm": "html",
    "scss": "css",
    "less": "css",
    "jsonc": "json",
    "jsonl": "json",
    "yml": "yaml",
    "bash": "sh",
    "shell": "sh",
    "zsh": "sh",
    "c": "c_cpp",
    "cpp": "c_cpp",
    "c++": "c_cpp",
    "cc": "c_cpp",
    "cxx": "c_cpp",
    "h": "c_cpp",
    "hpp": "c_cpp",
    "rust": "rs",
    "golang": "go",
}
for _item in EXTENSION_CATALOG:
    EXTENSION_ALIASES[_item["id"]] = _item["id"]
    for _ext in _item["extensions"]:
        EXTENSION_ALIASES[_ext] = _item["id"]
        EXTENSION_ALIASES[_ext.lstrip(".")] = _item["id"]

SUFFIX_TO_EXTENSION_ID: dict[str, str] = {
    ext: item["id"]
    for item in EXTENSION_CATALOG
    for ext in item["extensions"]
}

SUFFIX_TO_LANGUAGE: dict[str, str] = {}
for _item in EXTENSION_CATALOG:
    for _ext in _item["extensions"]:
        if _ext == ".jsx":
            SUFFIX_TO_LANGUAGE[_ext] = "jsx"
        elif _ext == ".tsx":
            SUFFIX_TO_LANGUAGE[_ext] = "tsx"
        else:
            SUFFIX_TO_LANGUAGE[_ext] = _item["lang"]

DEFAULT_ENABLED_EXTENSIONS: tuple[str, ...] = ("txt",)

DEFAULT_SHORTCUTS: dict[str, str] = {
    "open_file": "Ctrl+O",
    "open_folder": "Ctrl+Shift+O",
    "new_file": "Ctrl+N",
    "toggle_edit": "Ctrl+E",
    "save_file": "Ctrl+S",
    "font_increase": "Ctrl++",
    "font_decrease": "Ctrl+-",
    "font_reset": "Ctrl+0",
    "cycle_theme": "Ctrl+T",
    "toggle_sidebar": "Ctrl+B",
    "find": "Ctrl+F",
    "fullscreen": "F11",
    "reload": "Ctrl+R",
    "go_back": "Alt+Left",
    "go_forward": "Alt+Right",
    "next_file": "Ctrl+Tab",
    "prev_file": "Ctrl+Shift+Tab",
    "close_file": "Ctrl+W",
    "open_settings": "Ctrl+,",
    "quit": "Ctrl+Q",
}

# (code, label_en, label_es)
TRANSLATE_LANGUAGES: tuple[tuple[str, str, str], ...] = (
    ("auto", "Auto-detect", "Detectar automáticamente"),
    ("es", "Spanish", "Español"),
    ("en", "English", "Inglés"),
    ("pt", "Portuguese", "Portugués"),
    ("fr", "French", "Francés"),
    ("de", "German", "Alemán"),
    ("it", "Italian", "Italiano"),
    ("ja", "Japanese", "Japonés"),
    ("zh-CN", "Chinese (Simplified)", "Chino (Simplificado)"),
    ("zh-TW", "Chinese (Traditional)", "Chino (Tradicional)"),
    ("ko", "Korean", "Coreano"),
    ("ru", "Russian", "Ruso"),
    ("ar", "Arabic", "Árabe"),
    ("nl", "Dutch", "Neerlandés"),
    ("pl", "Polish", "Polaco"),
    ("tr", "Turkish", "Turco"),
    ("sv", "Swedish", "Sueco"),
    ("uk", "Ukrainian", "Ucraniano"),
    ("hi", "Hindi", "Hindi"),
    ("ca", "Catalan", "Catalán"),
    ("gl", "Galician", "Gallego"),
    ("eu", "Basque", "Euskera"),
    ("cs", "Czech", "Checo"),
    ("el", "Greek", "Griego"),
    ("iw", "Hebrew", "Hebreo"),
    ("vi", "Vietnamese", "Vietnamita"),
    ("th", "Thai", "Tailandés"),
    ("id", "Indonesian", "Indonesio"),
)

TRANSLATE_SOURCE_CODES = frozenset(code for code, _, _ in TRANSLATE_LANGUAGES)
TRANSLATE_TARGET_CODES = frozenset(code for code, _, _ in TRANSLATE_LANGUAGES if code != "auto")

DEFAULT_CONFIG: dict[str, Any] = {
    "font_size": DEFAULT_FONT_SIZE,
    "theme": "warm-dark",
    "language": "auto",
    "reading_width": "medium",
    "line_height": "comfortable",
    "show_line_numbers": True,
    "accent_color": "default",
    "code_style": "card",
    "enabled_extensions": list(DEFAULT_ENABLED_EXTENSIONS),
    "sidebar_visible": True,
    "sidebar_width": DEFAULT_SIDEBAR_WIDTH,
    "show_progress_bar": True,
    "auto_reload": True,
    "restore_session": True,
    "open_files": [],
    "open_folders": [],
    "custom_file_order": {},
    "active_file": "",
    "collapsed_folders": [],
    "translate_enabled": True,
    "translate_source": "auto",
    "translate_target": "es",
    "shortcuts": dict(DEFAULT_SHORTCUTS),
    "window_width": 1120,
    "window_height": 820,
    "recent_files": [],
}


def get_config_dir() -> Path:
    """Return XDG-compliant configuration directory for Coconut."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "coconut"


def get_config_file() -> Path:
    """Return path to Coconut's settings.json."""
    return get_config_dir() / "settings.json"


def clamp_font_size(value: Any) -> int:
    """Clamp font size to the supported ergonomic range."""
    try:
        size = int(value)
    except (TypeError, ValueError):
        return DEFAULT_FONT_SIZE
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))


def clamp_sidebar_width(value: Any) -> int:
    """Clamp sidebar width in pixels to a comfortable VS Code-like range."""
    try:
        width = int(value)
    except (TypeError, ValueError):
        return DEFAULT_SIDEBAR_WIDTH
    return max(MIN_SIDEBAR_WIDTH, min(MAX_SIDEBAR_WIDTH, width))


def normalize_extension_id(raw_id: Any) -> str | None:
    """Resolve an extension module ID, suffix, or alias to its canonical ID."""
    if not isinstance(raw_id, str):
        return None
    cleaned = raw_id.strip().lower()
    if not cleaned:
        return None
    return EXTENSION_ALIASES.get(cleaned)


def sanitize_enabled_extensions(raw_list: Any) -> list[str]:
    """Validate and deduplicate enabled extension module IDs."""
    if not isinstance(raw_list, (list, tuple, set)):
        return list(DEFAULT_ENABLED_EXTENSIONS)
    enabled_set: set[str] = set()
    for item in raw_list:
        norm = normalize_extension_id(item)
        if norm is not None:
            enabled_set.add(norm)
    return [ext_id for ext_id in VALID_EXTENSION_IDS if ext_id in enabled_set]


def get_extension_catalog(
    lang: str = "en",
    enabled_extensions: list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[dict[str, Any]]:
    """Return localized extension modules with current active status."""
    use_es = lang == "es"
    active_ids = set(
        sanitize_enabled_extensions(
            list(DEFAULT_ENABLED_EXTENSIONS) if enabled_extensions is None else list(enabled_extensions)
        )
    )
    items: list[dict[str, Any]] = []
    for item in EXTENSION_CATALOG:
        ext_id = item["id"]
        items.append({
            "id": ext_id,
            "category": item["category"],
            "badge": item["badge"],
            "extensions": list(item["extensions"]),
            "lang": item["lang"],
            "name": item["name_es"] if use_es else item["name_en"],
            "description": item["desc_es"] if use_es else item["desc_en"],
            "enabled": ext_id in active_ids,
        })
    return items


def get_active_file_extensions(cfg: Mapping[str, Any] | None = None) -> set[str]:
    """Return set of file suffixes currently enabled (Markdown core + active modules)."""
    exts: set[str] = set(CORE_MD_EXTENSIONS)
    raw_enabled = cfg.get("enabled_extensions") if isinstance(cfg, Mapping) else None
    enabled_ids = sanitize_enabled_extensions(raw_enabled)
    for ext_id in enabled_ids:
        mod = EXTENSION_BY_ID.get(ext_id)
        if mod:
            exts.update(mod["extensions"])
    return exts


def get_all_known_file_extensions() -> set[str]:
    """Return set of all file suffixes supported by Coconut and its extensions."""
    exts: set[str] = set(CORE_MD_EXTENSIONS)
    for item in EXTENSION_CATALOG:
        exts.update(item["extensions"])
    return exts


def is_file_supported(path: Path | str, cfg: Mapping[str, Any] | None = None) -> bool:
    """Return True if path has an extension active in the current configuration."""
    suffix = Path(path).suffix.lower()
    return suffix in get_active_file_extensions(cfg)


def is_known_supported_file(path: Path | str) -> bool:
    """Return True if path matches Markdown core or any known extension module."""
    suffix = Path(path).suffix.lower()
    return suffix in get_all_known_file_extensions()


def ensure_extension_enabled_for_path(cfg: dict[str, Any], path: Path | str) -> str | None:
    """Auto-detect and activate the extension module for *path* if not already enabled."""
    suffix = Path(path).suffix.lower()
    ext_id = SUFFIX_TO_EXTENSION_ID.get(suffix)
    if ext_id is None:
        return None
    current = list(cfg.get("enabled_extensions", []))
    if ext_id in current:
        return None
    current.append(ext_id)
    cfg["enabled_extensions"] = sanitize_enabled_extensions(current)
    return ext_id


def ensure_extensions_enabled_for_paths(cfg: dict[str, Any], paths: list[Path | str]) -> list[str]:
    """Auto-detect and activate extension modules for multiple paths; return newly enabled IDs."""
    newly_enabled: list[str] = []
    for p in paths:
        added = ensure_extension_enabled_for_path(cfg, p)
        if added is not None and added not in newly_enabled:
            newly_enabled.append(added)
    return newly_enabled


def _apply_custom_order(
    children: list[dict[str, Any]],
    order_list: list[str] | None,
) -> list[dict[str, Any]]:
    """Sort children according to a saved custom order, defaulting to dirs-first alphabetical."""
    if not order_list:
        return children
    rank = {path_str: idx for idx, path_str in enumerate(order_list)}
    return sorted(
        children,
        key=lambda item: (
            0 if item["path"] in rank else 1,
            rank.get(item["path"], 0),
            0 if item["type"] == "dir" else 1,
            item["name"].lower(),
        ),
    )


def scan_folder_tree(
    folder: Path,
    custom_order: Mapping[str, list[str]] | None = None,
    max_files: int = 500,
) -> tuple[dict[str, Any], list[Path]]:
    """Recursively scan *folder* for known supported files and build a nested VS Code-style tree."""
    root_path = folder.expanduser().resolve()
    known_exts = get_all_known_file_extensions()
    discovered_files: list[Path] = []
    order_map = custom_order if isinstance(custom_order, Mapping) else {}

    def _walk(current: Path, depth: int) -> dict[str, Any]:
        children: list[dict[str, Any]] = []
        if depth > 12 or len(discovered_files) >= max_files:
            return {
                "type": "dir",
                "name": current.name or str(current),
                "path": str(current),
                "children": children,
            }
        try:
            entries = sorted(
                current.iterdir(),
                key=lambda p: (0 if p.is_dir() else 1, p.name.lower()),
            )
        except OSError:
            entries = []

        for entry in entries:
            if len(discovered_files) >= max_files:
                break
            name = entry.name
            if not name:
                continue
            try:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    if name in IGNORED_DIR_NAMES or name.startswith("."):
                        continue
                    sub_node = _walk(entry, depth + 1)
                    if sub_node["children"]:
                        children.append(sub_node)
                elif entry.is_file():
                    if entry.suffix.lower() in known_exts:
                        resolved_file = entry.resolve()
                        discovered_files.append(resolved_file)
                        children.append({
                            "type": "file",
                            "name": name,
                            "path": str(resolved_file),
                            "ext": entry.suffix.lower(),
                        })
            except OSError:
                continue

        ordered_children = _apply_custom_order(children, order_map.get(str(current)))
        return {
            "type": "dir",
            "name": current.name or str(current),
            "path": str(current),
            "children": ordered_children,
        }

    tree = _walk(root_path, 0)
    return tree, discovered_files


def build_file_dialog_filter(cfg: Mapping[str, Any] | None = None, lang: str = "en") -> str:
    """Build dynamic QFileDialog filter string reflecting active extensions."""
    use_es = lang == "es"
    raw_enabled = cfg.get("enabled_extensions") if isinstance(cfg, Mapping) else None
    enabled_ids = sanitize_enabled_extensions(raw_enabled)

    md_globs = " ".join(f"*{ext}" for ext in CORE_MD_EXTENSIONS)
    active_globs: list[str] = [f"*{ext}" for ext in CORE_MD_EXTENSIONS]
    module_filters: list[str] = []

    for ext_id in enabled_ids:
        mod = EXTENSION_BY_ID.get(ext_id)
        if not mod:
            continue
        globs = " ".join(f"*{ext}" for ext in mod["extensions"])
        for ext in mod["extensions"]:
            g = f"*{ext}"
            if g not in active_globs:
                active_globs.append(g)
        label = mod["name_es"] if use_es else mod["name_en"]
        module_filters.append(f"{label} ({globs})")

    all_supported_globs = " ".join(active_globs)
    if use_es:
        parts = [
            f"Archivos compatibles ({all_supported_globs})",
            f"Archivos Markdown ({md_globs})",
            *module_filters,
            "Todos los archivos (*)",
        ]
    else:
        parts = [
            f"Supported files ({all_supported_globs})",
            f"Markdown files ({md_globs})",
            *module_filters,
            "All files (*)",
        ]
    return ";;".join(parts)


def build_translate_url(
    text: str,
    source: str = "auto",
    target: str = "es",
    max_chars: int = 4500,
) -> str:
    """Build a safely encoded Google Translate URL for selected text."""
    sl = source if source in TRANSLATE_SOURCE_CODES else "auto"
    tl = target if target in TRANSLATE_TARGET_CODES else "es"
    cleaned = " ".join(text.split()) if "\n" not in text else text.strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip()
    return f"https://translate.google.com/?sl={sl}&tl={tl}&text={quote(cleaned, safe='')}&op=translate"


def _sanitize_existing_paths(raw_list: Any, limit: int | None = None) -> list[str]:
    cleaned: list[str] = []
    if not isinstance(raw_list, list):
        return cleaned
    seen: set[str] = set()
    for item in raw_list:
        if not isinstance(item, str) or not item:
            continue
        try:
            resolved = str(Path(item).expanduser().resolve())
        except OSError:
            continue
        if resolved not in seen and Path(resolved).is_file():
            seen.add(resolved)
            cleaned.append(resolved)
        if limit is not None and len(cleaned) >= limit:
            break
    return cleaned


def _sanitize_existing_dirs(raw_list: Any) -> list[str]:
    cleaned: list[str] = []
    if not isinstance(raw_list, list):
        return cleaned
    seen: set[str] = set()
    for item in raw_list:
        if not isinstance(item, str) or not item:
            continue
        try:
            resolved = str(Path(item).expanduser().resolve())
        except OSError:
            continue
        if resolved not in seen and Path(resolved).is_dir():
            seen.add(resolved)
            cleaned.append(resolved)
    return cleaned


def _sanitize_config(raw: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    cfg["font_size"] = clamp_font_size(raw.get("font_size", DEFAULT_FONT_SIZE))

    theme = raw.get("theme", "warm-dark")
    cfg["theme"] = theme if theme in VALID_THEMES else "warm-dark"

    lang = raw.get("language", "auto")
    cfg["language"] = lang if lang in VALID_LANGUAGES else "auto"

    width = raw.get("reading_width", "medium")
    cfg["reading_width"] = width if width in VALID_READING_WIDTHS else "medium"

    lh = raw.get("line_height", "comfortable")
    cfg["line_height"] = lh if lh in VALID_LINE_HEIGHTS else "comfortable"

    cfg["show_line_numbers"] = bool(raw.get("show_line_numbers", True))

    accent = raw.get("accent_color", "default")
    cfg["accent_color"] = accent if accent in VALID_ACCENT_COLORS else "default"

    cstyle = raw.get("code_style", "card")
    cfg["code_style"] = cstyle if cstyle in VALID_CODE_STYLES else "card"

    if "enabled_extensions" in raw and isinstance(raw.get("enabled_extensions"), list):
        cfg["enabled_extensions"] = sanitize_enabled_extensions(raw.get("enabled_extensions"))
    else:
        cfg["enabled_extensions"] = list(DEFAULT_ENABLED_EXTENSIONS)

    cfg["sidebar_visible"] = bool(raw.get("sidebar_visible", True))
    cfg["sidebar_width"] = clamp_sidebar_width(raw.get("sidebar_width", DEFAULT_SIDEBAR_WIDTH))
    cfg["show_progress_bar"] = bool(raw.get("show_progress_bar", True))
    cfg["auto_reload"] = bool(raw.get("auto_reload", True))
    cfg["restore_session"] = bool(raw.get("restore_session", True))
    cfg["translate_enabled"] = bool(raw.get("translate_enabled", True))

    src = raw.get("translate_source", "auto")
    cfg["translate_source"] = src if src in TRANSLATE_SOURCE_CODES else "auto"

    tgt = raw.get("translate_target", "es")
    cfg["translate_target"] = tgt if tgt in TRANSLATE_TARGET_CODES else "es"

    open_files = _sanitize_existing_paths(raw.get("open_files", []))
    cfg["open_files"] = open_files

    open_folders = _sanitize_existing_dirs(raw.get("open_folders", []))
    cfg["open_folders"] = open_folders

    custom_order: dict[str, list[str]] = {}
    raw_order = raw.get("custom_file_order", {})
    if isinstance(raw_order, dict):
        for folder_key, items in raw_order.items():
            if not isinstance(folder_key, str) or not folder_key or not isinstance(items, list):
                continue
            deduped: list[str] = []
            seen_items: set[str] = set()
            for item in items:
                if isinstance(item, str) and item and item not in seen_items:
                    seen_items.add(item)
                    deduped.append(item)
            if deduped:
                custom_order[folder_key] = deduped
    cfg["custom_file_order"] = custom_order

    active_raw = raw.get("active_file", "")
    active_resolved = ""
    if isinstance(active_raw, str) and active_raw:
        try:
            cand = str(Path(active_raw).expanduser().resolve())
            if cand in open_files or (open_folders and Path(cand).is_file()):
                active_resolved = cand
        except OSError:
            pass
    if not active_resolved and open_files:
        active_resolved = open_files[0]
    cfg["active_file"] = active_resolved

    collapsed: list[str] = []
    raw_collapsed = raw.get("collapsed_folders", [])
    if isinstance(raw_collapsed, list):
        seen_folders: set[str] = set()
        for folder in raw_collapsed:
            if isinstance(folder, str) and folder and folder not in seen_folders:
                seen_folders.add(folder)
                collapsed.append(folder)
    cfg["collapsed_folders"] = collapsed

    shortcuts = dict(DEFAULT_SHORTCUTS)
    raw_shortcuts = raw.get("shortcuts", {})
    if isinstance(raw_shortcuts, dict):
        for action in DEFAULT_SHORTCUTS:
            val = raw_shortcuts.get(action)
            if isinstance(val, str):
                shortcuts[action] = val.strip()[:40]
    cfg["shortcuts"] = shortcuts

    try:
        w = int(raw.get("window_width", DEFAULT_CONFIG["window_width"]))
        cfg["window_width"] = max(480, min(7680, w))
    except (TypeError, ValueError):
        pass

    try:
        h = int(raw.get("window_height", DEFAULT_CONFIG["window_height"]))
        cfg["window_height"] = max(360, min(4320, h))
    except (TypeError, ValueError):
        pass

    cfg["recent_files"] = _sanitize_existing_paths(raw.get("recent_files", []), limit=MAX_RECENT_FILES)
    return cfg


def load_config() -> dict[str, Any]:
    """Load settings from disk, falling back to safe defaults on errors."""
    config_file = get_config_file()
    if not config_file.exists():
        return _sanitize_config({})
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return _sanitize_config(data)
    except Exception:
        pass
    return _sanitize_config({})


def save_config(cfg: dict[str, Any]) -> None:
    """Atomically write settings to settings.json."""
    config_dir = get_config_dir()
    config_file = get_config_file()
    config_dir.mkdir(parents=True, exist_ok=True)
    sanitized = _sanitize_config(cfg)
    payload = json.dumps(sanitized, indent=2, ensure_ascii=False) + "\n"

    fd, tmp_path = tempfile.mkstemp(prefix=".settings-", suffix=".tmp", dir=str(config_dir))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, config_file)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def add_recent_file(cfg: dict[str, Any], path: str) -> None:
    """Prepend an existing file path to recent_files, deduplicating and capping length."""
    try:
        resolved = str(Path(path).expanduser().resolve())
    except OSError:
        resolved = str(path)
    if not Path(resolved).is_file():
        return
    existing = [
        p for p in cfg.get("recent_files", [])
        if isinstance(p, str) and p != resolved and Path(p).is_file()
    ]
    cfg["recent_files"] = [resolved, *existing][:MAX_RECENT_FILES]
