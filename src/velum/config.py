"""Persistent XDG-compliant settings management for Velum."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

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

DEFAULT_CONFIG: dict[str, Any] = {
    "font_size": DEFAULT_FONT_SIZE,
    "theme": "warm-dark",
    "language": "auto",
    "sidebar_visible": True,
    "window_width": 1120,
    "window_height": 820,
    "recent_files": [],
}


def get_config_dir() -> Path:
    """Return XDG-compliant configuration directory for Velum."""
    xdg = os.environ.get("XDG_CONFIG_HOME", "").strip()
    base = Path(xdg).expanduser() if xdg else Path.home() / ".config"
    return base / "velum"


def get_config_file() -> Path:
    """Return path to Velum's settings.json."""
    return get_config_dir() / "settings.json"


def clamp_font_size(value: Any) -> int:
    """Clamp font size to the supported ergonomic range."""
    try:
        size = int(value)
    except (TypeError, ValueError):
        return DEFAULT_FONT_SIZE
    return max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, size))


def _sanitize_config(raw: dict[str, Any]) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    cfg["font_size"] = clamp_font_size(raw.get("font_size", DEFAULT_FONT_SIZE))

    theme = raw.get("theme", "warm-dark")
    cfg["theme"] = theme if theme in VALID_THEMES else "warm-dark"

    lang = raw.get("language", "auto")
    cfg["language"] = lang if lang in VALID_LANGUAGES else "auto"

    cfg["sidebar_visible"] = bool(raw.get("sidebar_visible", True))

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

    recent = raw.get("recent_files", [])
    cleaned_recent: list[str] = []
    if isinstance(recent, list):
        seen: set[str] = set()
        for item in recent:
            if isinstance(item, str) and item and item not in seen:
                if Path(item).is_file():
                    seen.add(item)
                    cleaned_recent.append(item)
            if len(cleaned_recent) >= MAX_RECENT_FILES:
                break
    cfg["recent_files"] = cleaned_recent
    return cfg


def load_config() -> dict[str, Any]:
    """Load settings from disk, falling back to safe defaults on errors."""
    config_file = get_config_file()
    if not config_file.exists():
        return dict(DEFAULT_CONFIG)
    try:
        data = json.loads(config_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return _sanitize_config(data)
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)


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
