"""Persistent XDG-compliant settings management for Coconut."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

MIN_FONT_SIZE = 12
MAX_FONT_SIZE = 36
DEFAULT_FONT_SIZE = 18

VALID_THEMES = ("warm-dark", "sepia", "soft-light")
VALID_LANGUAGES = ("auto", "en", "es")

THEME_BG = {
    "warm-dark": "#191817",
    "sepia": "#F3ECDC",
    "soft-light": "#F4F3EE",
}

MAX_RECENT_FILES = 8

DEFAULT_SHORTCUTS: dict[str, str] = {
    "open_file": "Ctrl+O",
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
    "sidebar_visible": True,
    "show_progress_bar": True,
    "auto_reload": True,
    "restore_session": True,
    "open_files": [],
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


def _sanitize_config(raw: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    cfg["font_size"] = clamp_font_size(raw.get("font_size", DEFAULT_FONT_SIZE))

    theme = raw.get("theme", "warm-dark")
    cfg["theme"] = theme if theme in VALID_THEMES else "warm-dark"

    lang = raw.get("language", "auto")
    cfg["language"] = lang if lang in VALID_LANGUAGES else "auto"

    cfg["sidebar_visible"] = bool(raw.get("sidebar_visible", True))
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

    active_raw = raw.get("active_file", "")
    active_resolved = ""
    if isinstance(active_raw, str) and active_raw:
        try:
            cand = str(Path(active_raw).expanduser().resolve())
            if cand in open_files:
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
