"""Coconut — Minimalist, local-first, eye-comfort Markdown & code reader for Linux (Wayland & X11)."""

from __future__ import annotations

import json
import os
import re
import sys
from collections.abc import Mapping, MutableMapping
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from __init__ import APP_NAME, __version__  # noqa: E402
from config import (  # noqa: E402
    CORE_MD_EXTENSIONS,
    DEFAULT_FONT_SIZE,
    DEFAULT_SHORTCUTS,
    DEFAULT_SIDEBAR_WIDTH,
    EXTENSION_BY_ID,
    SUFFIX_TO_LANGUAGE,
    THEME_BG,
    TRANSLATE_SOURCE_CODES,
    TRANSLATE_TARGET_CODES,
    VALID_ACCENT_COLORS,
    VALID_CODE_STYLES,
    VALID_EXTENSION_IDS,
    VALID_LANGUAGES,
    VALID_LINE_HEIGHTS,
    VALID_READING_WIDTHS,
    VALID_THEMES,
    add_recent_file,
    build_file_dialog_filter,
    build_translate_url,
    clamp_font_size,
    clamp_sidebar_width,
    ensure_extensions_enabled_for_paths,
    get_active_file_extensions,
    get_extension_catalog,
    is_file_supported,
    is_known_supported_file,
    load_config,
    normalize_extension_id,
    save_config,
    scan_folder_tree,
)
from i18n import get_strings, get_translate_languages, resolve_language  # noqa: E402
from renderer import (  # noqa: E402
    render_code_text,
    render_document_file,
    render_markdown_text,
    render_plain_text,
)

ASSETS_DIR = APP_DIR / "assets"
FONTS_DIR = APP_DIR / "fonts"
INDEX_HTML = (ASSETS_DIR / "index.html").resolve()
MD_EXTENSIONS = set(CORE_MD_EXTENSIONS) | {".txt"}


def _resolve_icon_path() -> Path | None:
    xdg_data = os.environ.get("XDG_DATA_HOME", "").strip()
    data_dir = Path(xdg_data).expanduser() if xdg_data else Path.home() / ".local" / "share"
    candidates = [
        data_dir / "icons" / "hicolor" / "scalable" / "apps" / "coconut.svg",
        Path("/usr/share/icons/hicolor/scalable/apps/coconut.svg"),
        APP_DIR.parent.parent / "assets" / "icons" / "coconut.svg",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


VIRTUAL_GPU_VENDORS = frozenset({"0x15ad", "0x80ee", "0x1234", "0x1b36"})
SOFTWARE_GPU_CHROMIUM_FLAGS = ("--disable-gpu", "--disable-gpu-compositing")


def _read_drm_vendors(drm_sys: Path) -> set[str]:
    """Read normalized PCI vendor IDs for DRM card devices."""
    if not drm_sys.is_dir():
        return set()
    vendors: set[str] = set()
    try:
        entries = list(drm_sys.iterdir())
    except OSError:
        return vendors
    for entry in entries:
        if not re.fullmatch(r"card\d+", entry.name):
            continue
        try:
            vendor = (entry / "device" / "vendor").read_text(encoding="utf-8").strip().lower()
        except OSError:
            continue
        if vendor:
            vendors.add(vendor)
    return vendors


def _has_dri_render_node(dri_dir: Path) -> bool:
    """Return True if at least one /dev/dri/renderD* node exists."""
    if not dri_dir.is_dir():
        return False
    try:
        return any(True for _ in dri_dir.glob("renderD*"))
    except OSError:
        return False


def should_use_software_gpu(
    argv: list[str],
    env: Mapping[str, str] | None = None,
    dri_dir: Path = Path("/dev/dri"),
    drm_sys: Path = Path("/sys/class/drm"),
) -> bool:
    """Determine whether WebEngine should disable GPU compositing (e.g. VMs / no DRM)."""
    if "--software-gpu" in argv:
        return True
    if "--hardware-gpu" in argv:
        return False

    target_env = os.environ if env is None else env
    override = target_env.get("COCONUT_SOFTWARE_GPU", "").strip().lower()
    if override in {"1", "true", "yes", "on"}:
        return True
    if override in {"0", "false", "no", "off"}:
        return False

    vendors = _read_drm_vendors(drm_sys)
    if vendors and all(v in VIRTUAL_GPU_VENDORS for v in vendors):
        return True
    if not _has_dri_render_node(dri_dir) and "0x10de" not in vendors:
        return True
    return False


def configure_gpu_env(
    argv: list[str],
    env: MutableMapping[str, str] | None = None,
    dri_dir: Path = Path("/dev/dri"),
    drm_sys: Path = Path("/sys/class/drm"),
) -> bool:
    """Apply software-GPU Chromium flags before QApplication initializes if needed."""
    target_env = os.environ if env is None else env
    if not should_use_software_gpu(argv, env=target_env, dri_dir=dri_dir, drm_sys=drm_sys):
        return False

    existing = target_env.get("QTWEBENGINE_CHROMIUM_FLAGS", "").split()
    for flag in SOFTWARE_GPU_CHROMIUM_FLAGS:
        if flag not in existing:
            existing.append(flag)
    target_env["QTWEBENGINE_CHROMIUM_FLAGS"] = " ".join(existing)
    return True


def _print_help() -> None:
    print(
        f"{APP_NAME} {__version__} — Minimalist, eye-comfort Markdown & code reader for Linux\n\n"
        "Usage:\n"
        "  coco [OPTIONS] [FILE...]\n\n"
        "Options:\n"
        "  -h, --help          Show this help message and exit\n"
        "  -v, --version       Show version and exit\n"
        "      --standalone    Run a separate process instead of forwarding to existing instance\n"
        "      --software-gpu  Force software WebEngine rendering (auto-enabled in VMs / no DRM)\n"
        "      --hardware-gpu  Force hardware GPU rendering (disable VM auto-fallback)\n"
        "      --self-test F   Verify rendering and font loading on FILE and exit\n"
    )


def create_qt_runtime() -> dict[str, Any]:
    """Lazily import PyQt6 and construct Coconut's GUI classes."""
    # Import QtWebChannel BEFORE QWebEngineView so qrc:///qtwebchannel/qwebchannel.js is registered.
    from PyQt6.QtCore import (
        QEvent,
        QFileSystemWatcher,
        QObject,
        QStandardPaths,
        QTimer,
        QUrl,
        Qt,
        pyqtSlot,
    )
    from PyQt6.QtGui import (
        QAction,
        QColor,
        QDesktopServices,
        QFont,
        QFontDatabase,
        QIcon,
        QKeySequence,
        QShortcut,
    )
    from PyQt6.QtNetwork import QLocalServer, QLocalSocket
    from PyQt6.QtWebChannel import QWebChannel
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMenu

    def normalize_cli_paths(args: list[str]) -> list[str]:
        result: list[str] = []
        skip_next = False
        for arg in args:
            if skip_next:
                skip_next = False
                if not arg.startswith("-"):
                    continue
            if arg == "--self-test":
                skip_next = True
                continue
            if not arg or arg.startswith("-"):
                continue
            if arg.startswith("file://"):
                local = QUrl(arg).toLocalFile()
                if local:
                    result.append(str(Path(local).expanduser().resolve()))
            else:
                result.append(str(Path(arg).expanduser().resolve()))
        return result

    class ExternalLinkPage(QWebEnginePage):
        """Ephemeral page for target=_blank links so external URLs open in the browser."""

        def __init__(self, win: "ReaderWindow") -> None:
            super().__init__(win.page)
            self.win = win

        def acceptNavigationRequest(
            self,
            url: QUrl,
            nav_type: QWebEnginePage.NavigationType,
            is_main_frame: bool,
        ) -> bool:
            if url.isLocalFile():
                target = Path(url.toLocalFile())
                if is_file_supported(target, self.win.controller.config) and target.is_file():
                    QTimer.singleShot(0, lambda p=target: self.win.open_file(p, push_history=True))
                else:
                    QDesktopServices.openUrl(url)
            elif url.scheme().lower() in ("http", "https", "mailto"):
                QDesktopServices.openUrl(url)
            self.deleteLater()
            return False

    class ReaderPage(QWebEnginePage):
        """Sandboxed page intercepting external links and local document navigation."""

        def __init__(self, win: "ReaderWindow") -> None:
            super().__init__(win)
            self.win = win
            self.js_errors: list[str] = []

            settings = self.settings()
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ErrorPageEnabled, False)
            settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        def javaScriptConsoleMessage(
            self,
            level: QWebEnginePage.JavaScriptConsoleMessageLevel,
            message: str,
            line_number: int,
            source_id: str,
        ) -> None:
            if level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
                self.js_errors.append(f"{source_id}:{line_number}: {message}")

        def acceptNavigationRequest(
            self,
            url: QUrl,
            nav_type: QWebEnginePage.NavigationType,
            is_main_frame: bool,
        ) -> bool:
            if url.isLocalFile():
                local_path = Path(url.toLocalFile())
                try:
                    if local_path.resolve() == INDEX_HTML:
                        return True
                except OSError:
                    pass
                if not is_main_frame:
                    return False
                if is_file_supported(local_path, self.win.controller.config):
                    QTimer.singleShot(0, lambda p=local_path: self.win.open_file(p, push_history=True))
                else:
                    QDesktopServices.openUrl(url)
                return False

            if url.scheme().lower() in ("http", "https", "mailto"):
                QDesktopServices.openUrl(url)
                return False

            return False

        def createWindow(self, win_type: QWebEnginePage.WebWindowType) -> QWebEnginePage:
            return ExternalLinkPage(self.win)

    class Bridge(QObject):
        """QWebChannel bridge exposed as window.bridge in reader.js."""

        def __init__(self, win: "ReaderWindow") -> None:
            super().__init__(win)
            self.win = win

        @pyqtSlot()
        def onReady(self) -> None:
            self.win.on_web_ready()

        @pyqtSlot(int)
        def setFontSize(self, size: int) -> None:
            self.win.controller.set_font_size(size)

        @pyqtSlot(int)
        def adjustFontSize(self, delta: int) -> None:
            self.win.controller.adjust_font_size(delta)

        @pyqtSlot()
        def resetFontSize(self) -> None:
            self.win.controller.set_font_size(DEFAULT_FONT_SIZE)

        @pyqtSlot()
        def cycleTheme(self) -> None:
            self.win.controller.cycle_theme()

        @pyqtSlot(str)
        def setTheme(self, theme: str) -> None:
            self.win.controller.set_theme(theme)

        @pyqtSlot(str)
        def setLanguage(self, lang: str) -> None:
            self.win.controller.set_language(lang)

        @pyqtSlot(str, bool)
        def setSettingBool(self, key: str, value: bool) -> None:
            self.win.controller.set_setting_bool(key, value)

        @pyqtSlot(str, str)
        def setSettingChoice(self, key: str, value: str) -> None:
            self.win.controller.set_setting_choice(key, value)

        @pyqtSlot(str, bool)
        def toggleExtension(self, ext_id: str, enabled: bool) -> None:
            self.win.controller.set_extension_enabled(ext_id, enabled)

        @pyqtSlot(bool)
        def setAllExtensions(self, enabled: bool) -> None:
            self.win.controller.set_all_extensions(enabled)

        @pyqtSlot(str, str)
        def setTranslatePair(self, source: str, target: str) -> None:
            self.win.controller.set_translate_pair(source, target)

        @pyqtSlot(str, str)
        def setShortcut(self, action: str, seq: str) -> None:
            self.win.controller.set_shortcut(action, seq)

        @pyqtSlot()
        def resetShortcuts(self) -> None:
            self.win.controller.reset_shortcuts()

        @pyqtSlot(bool)
        def setShortcutsEnabled(self, enabled: bool) -> None:
            self.win.set_shortcuts_enabled(enabled)

        @pyqtSlot()
        def toggleSidebar(self) -> None:
            self.win.controller.toggle_sidebar()

        @pyqtSlot()
        def toggleFullscreen(self) -> None:
            self.win.toggle_fullscreen()

        @pyqtSlot()
        def reloadCurrent(self) -> None:
            self.win.reload_current()

        @pyqtSlot()
        def openFileDialog(self) -> None:
            self.win.open_file_dialog()

        @pyqtSlot()
        def openFolderDialog(self) -> None:
            self.win.open_folder_dialog()

        @pyqtSlot(str)
        def closeFolder(self, path: str) -> None:
            if path:
                self.win.controller.close_folder(Path(path))

        @pyqtSlot(str)
        def reorderOpenFiles(self, paths_json: str) -> None:
            try:
                items = json.loads(paths_json)
                if isinstance(items, list):
                    self.win.controller.reorder_open_files([str(p) for p in items if isinstance(p, str)])
            except Exception:
                pass

        @pyqtSlot(str)
        def reorderOpenFolders(self, folders_json: str) -> None:
            try:
                items = json.loads(folders_json)
                if isinstance(items, list):
                    self.win.controller.reorder_open_folders([str(p) for p in items if isinstance(p, str)])
            except Exception:
                pass

        @pyqtSlot(str, str)
        def reorderFolderChildren(self, folder_path: str, children_json: str) -> None:
            try:
                items = json.loads(children_json)
                if folder_path and isinstance(items, list):
                    self.win.controller.reorder_folder_children(
                        folder_path, [str(p) for p in items if isinstance(p, str)]
                    )
            except Exception:
                pass

        @pyqtSlot(int)
        def setSidebarWidth(self, width: int) -> None:
            self.win.controller.set_sidebar_width(width)

        @pyqtSlot(str)
        def openRecentFile(self, path: str) -> None:
            if path:
                self.win.open_file(Path(path), push_history=True)

        @pyqtSlot(str)
        def activateFile(self, path: str) -> None:
            if path:
                self.win.controller.activate_file(Path(path), push_history=True)

        @pyqtSlot(str)
        def closeFile(self, path: str) -> None:
            if path:
                self.win.controller.close_file(Path(path))

        @pyqtSlot(str)
        def toggleFolderCollapsed(self, folder: str) -> None:
            if folder:
                self.win.controller.toggle_folder_collapsed(folder)

        @pyqtSlot(bool, bool)
        def setEditState(self, editing: bool, dirty: bool) -> None:
            self.win.set_edit_state(editing, dirty)

        @pyqtSlot(str, str)
        def previewRawText(self, text: str, path_or_name: str) -> None:
            self.win.preview_raw_text(text, path_or_name)

        @pyqtSlot(str, str)
        def saveFile(self, path: str, content: str) -> None:
            self.win.save_file_content(path, content)

        @pyqtSlot(str)
        def copyText(self, text: str) -> None:
            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(text)

        @pyqtSlot(str, bool)
        def findText(self, query: str, backward: bool) -> None:
            flags = QWebEnginePage.FindFlag(0)
            if backward:
                flags = QWebEnginePage.FindFlag.FindBackward
            self.win.page.findText(query, flags)

        @pyqtSlot()
        def clearFind(self) -> None:
            self.win.page.findText("")

        @pyqtSlot(str)
        def openExternalUrl(self, url: str) -> None:
            parsed = QUrl(url)
            if parsed.scheme().lower() in ("https", "http"):
                QDesktopServices.openUrl(parsed)

    class ReaderWindow(QMainWindow):
        """Minimalist distraction-free Markdown & code reading/editing window."""

        def __init__(self, controller: "AppController", initial_file: Path | None = None) -> None:
            super().__init__()
            self.controller = controller
            self.current_file: Path | None = None
            self.pending_file: Path | None = initial_file
            self.web_ready = False
            self.has_toc = False
            self.is_editing = False
            self.is_dirty = False
            self._ignore_next_watch = False

            self._history: list[Path] = []
            self._history_idx = -1
            self._shortcuts: list[QShortcut] = []

            self.setWindowTitle(APP_NAME)
            self.resize(
                controller.config.get("window_width", 1120),
                controller.config.get("window_height", 820),
            )
            self.setAcceptDrops(True)

            self.view = QWebEngineView(self)
            self.page = ReaderPage(self)
            self.view.setPage(self.page)
            self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.view.customContextMenuRequested.connect(self._show_context_menu)
            self.setCentralWidget(self.view)

            self.view.installEventFilter(self)
            if self.view.focusProxy() is not None:
                self.view.focusProxy().installEventFilter(self)

            # Set background color BEFORE loading URL to prevent any white startup flash.
            self.apply_theme_background(controller.config["theme"])

            self.channel = QWebChannel(self.page)
            self.bridge = Bridge(self)
            self.channel.registerObject("bridge", self.bridge)
            self.page.setWebChannel(self.channel)

            self.watcher = QFileSystemWatcher(self)
            self.watcher.fileChanged.connect(self._on_file_changed)
            self._reload_timer = QTimer(self)
            self._reload_timer.setSingleShot(True)
            self._reload_timer.setInterval(150)
            self._reload_timer.timeout.connect(self._reload_watched_file)

            self.rebuild_shortcuts()
            self.view.load(QUrl.fromLocalFile(str(INDEX_HTML)))

        def _shortcut_handlers(self) -> dict[str, Any]:
            return {
                "open_file": self.open_file_dialog,
                "open_folder": self.open_folder_dialog,
                "new_file": self.start_new_document,
                "toggle_edit": self.toggle_edit_mode,
                "save_file": self.request_save,
                "font_increase": lambda: self.controller.adjust_font_size(1),
                "font_decrease": lambda: self.controller.adjust_font_size(-1),
                "font_reset": lambda: self.controller.set_font_size(DEFAULT_FONT_SIZE),
                "cycle_theme": self.controller.cycle_theme,
                "toggle_sidebar": self.controller.toggle_sidebar,
                "find": self.open_find_bar,
                "fullscreen": self.toggle_fullscreen,
                "reload": self.reload_current,
                "go_back": self.go_back,
                "go_forward": self.go_forward,
                "next_file": lambda: self.controller.cycle_open_file(1),
                "prev_file": lambda: self.controller.cycle_open_file(-1),
                "close_file": self.close_current_file,
                "open_settings": self.open_settings_modal,
                "quit": QApplication.quit,
            }

        def rebuild_shortcuts(self) -> None:
            for sc in self._shortcuts:
                sc.setEnabled(False)
                sc.deleteLater()
            self._shortcuts.clear()

            handlers = self._shortcut_handlers()
            shortcuts_cfg = self.controller.config.get("shortcuts", DEFAULT_SHORTCUTS)
            used_seqs = {v for v in shortcuts_cfg.values() if isinstance(v, str) and v}

            for action, handler in handlers.items():
                seq = shortcuts_cfg.get(action, "")
                if not seq:
                    continue
                sc = QShortcut(QKeySequence(seq), self)
                sc.setContext(Qt.ShortcutContext.WindowShortcut)
                sc.activated.connect(handler)
                self._shortcuts.append(sc)

            # Helpful non-conflicting secondary aliases for keyboard layouts
            if shortcuts_cfg.get("font_increase") == "Ctrl++" and "Ctrl+=" not in used_seqs:
                sc_eq = QShortcut(QKeySequence("Ctrl+="), self)
                sc_eq.setContext(Qt.ShortcutContext.WindowShortcut)
                sc_eq.activated.connect(handlers["font_increase"])
                self._shortcuts.append(sc_eq)
            if shortcuts_cfg.get("reload") == "Ctrl+R" and "F5" not in used_seqs:
                sc_f5 = QShortcut(QKeySequence("F5"), self)
                sc_f5.setContext(Qt.ShortcutContext.WindowShortcut)
                sc_f5.activated.connect(handlers["reload"])
                self._shortcuts.append(sc_f5)

        def set_shortcuts_enabled(self, enabled: bool) -> None:
            for sc in self._shortcuts:
                sc.setEnabled(enabled)

        def _run_js(self, script: str) -> None:
            if self.web_ready:
                self.page.runJavaScript(script)

        def apply_theme_background(self, theme: str) -> None:
            bg = THEME_BG.get(theme, "#191817")
            self.setStyleSheet(f"QMainWindow {{ background-color: {bg}; }}")
            self.page.setBackgroundColor(QColor(bg))

        def _update_window_title(self) -> None:
            prefix = "● " if self.is_dirty else ""
            if self.current_file is not None:
                self.setWindowTitle(f"{prefix}{self.current_file.name} — {APP_NAME}")
            elif self.is_editing or self.is_dirty:
                untitled = self.controller.strings.get("untitled_filename", "Untitled.md")
                self.setWindowTitle(f"{prefix}{untitled} — {APP_NAME}")
            else:
                self.setWindowTitle(APP_NAME)

        def set_edit_state(self, editing: bool, dirty: bool) -> None:
            self.is_editing = bool(editing)
            self.is_dirty = bool(dirty)
            self._update_window_title()

        def toggle_edit_mode(self) -> None:
            self._run_js("window.Coconut && window.Coconut.toggleEditMode();")

        def start_new_document(self) -> None:
            self.current_file = None
            self.is_editing = True
            self.is_dirty = False
            self._update_window_title()
            self._run_js("window.Coconut && window.Coconut.startNewDocument();")

        def request_save(self) -> None:
            self._run_js("window.Coconut && window.Coconut.requestSave();")

        def preview_raw_text(self, text: str, path_or_name: str) -> None:
            p = Path(path_or_name) if path_or_name else Path("Untitled.md")
            suffix = p.suffix.lower()
            base_dir = p.parent if p.is_absolute() and p.parent.is_dir() else None
            if suffix in CORE_MD_EXTENSIONS or not suffix:
                doc = render_markdown_text(text, base_dir=base_dir, filename=p.name)
            elif suffix in (".txt", ".text", ".log"):
                doc = render_plain_text(text, filename=p.name)
            elif suffix in SUFFIX_TO_LANGUAGE:
                doc = render_code_text(text, filename=p.name)
            else:
                doc = render_markdown_text(text, base_dir=base_dir, filename=p.name)
            doc["path"] = str(self.current_file) if self.current_file else ""
            self.has_toc = len(doc.get("toc", [])) >= 2
            doc_json = json.dumps(doc, ensure_ascii=False)
            self._run_js(f"window.Coconut && window.Coconut.renderDocument({doc_json}, true, true);")

        def save_file_content(self, path_str: str, content: str) -> None:
            target: Path | None = None
            if path_str:
                target = Path(path_str).expanduser().resolve()
            elif self.current_file is not None:
                target = self.current_file
            else:
                docs_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
                start_dir = Path(docs_dir) if docs_dir else Path.home()
                default_name = self.controller.strings.get("untitled_filename", "Untitled.md")
                s = self.controller.strings
                chosen, _ = QFileDialog.getSaveFileName(
                    self,
                    s["dialog_save_title"],
                    str(start_dir / default_name),
                    build_file_dialog_filter(self.controller.config, self.controller.lang),
                )
                if not chosen:
                    return
                target = Path(chosen).expanduser().resolve()

            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                self._ignore_next_watch = True
                target.write_text(content, encoding="utf-8")
            except Exception as exc:
                self._ignore_next_watch = False
                msg = self.controller.strings["toast_save_error"].format(err=str(exc))
                self._run_js(f"window.Coconut && window.Coconut.showToast({json.dumps(msg)});")
                return

            self.current_file = target
            self.is_dirty = False
            self.controller.register_open_file(target)
            self._watch_file(target)
            self.controller.record_recent_file(str(target))
            self.push_session_to_web()

            try:
                doc = render_document_file(target)
            except Exception as exc:
                msg = self.controller.strings["toast_open_error"].format(err=str(exc))
                self._run_js(f"window.Coconut && window.Coconut.showToast({json.dumps(msg)});")
                return

            self.has_toc = len(doc.get("toc", [])) >= 2
            self._update_window_title()
            doc_json = json.dumps(doc, ensure_ascii=False)
            self._run_js(f"window.Coconut && window.Coconut.onFileSaved({doc_json});")
            saved_msg = self.controller.strings["toast_saved"].format(name=target.name)
            self._run_js(f"window.Coconut && window.Coconut.showToast({json.dumps(saved_msg)});")

        def push_strings_to_web(self) -> None:
            if not self.web_ready:
                return
            strings_json = json.dumps(self.controller.strings, ensure_ascii=False)
            langs_json = json.dumps(get_translate_languages(self.controller.lang), ensure_ascii=False)
            self._run_js(f"window.Coconut && window.Coconut.applyStrings({strings_json}, {langs_json});")

        def push_settings_to_web(self, toast_msg: str | None = None) -> None:
            cfg = self.controller.config
            self.apply_theme_background(cfg["theme"])
            if not self.web_ready:
                return
            payload = json.dumps({
                "font_size": cfg["font_size"],
                "theme": cfg["theme"],
                "language": cfg["language"],
                "reading_width": cfg.get("reading_width", "medium"),
                "line_height": cfg.get("line_height", "comfortable"),
                "show_line_numbers": cfg.get("show_line_numbers", True),
                "accent_color": cfg.get("accent_color", "default"),
                "code_style": cfg.get("code_style", "card"),
                "enabled_extensions": cfg.get("enabled_extensions", []),
                "extensions_catalog": get_extension_catalog(
                    self.controller.lang, cfg.get("enabled_extensions", [])
                ),
                "sidebar_visible": cfg["sidebar_visible"],
                "sidebar_width": cfg.get("sidebar_width", DEFAULT_SIDEBAR_WIDTH),
                "show_progress_bar": cfg["show_progress_bar"],
                "auto_reload": cfg["auto_reload"],
                "restore_session": cfg["restore_session"],
                "translate_enabled": cfg["translate_enabled"],
                "translate_source": cfg["translate_source"],
                "translate_target": cfg["translate_target"],
                "shortcuts": cfg["shortcuts"],
            }, ensure_ascii=False)
            self._run_js(f"window.Coconut && window.Coconut.applySettings({payload});")
            if toast_msg:
                self._run_js(f"window.Coconut && window.Coconut.showToast({json.dumps(toast_msg)});")

        def push_session_to_web(self) -> None:
            if not self.web_ready:
                return
            payload = json.dumps(self.controller.session_payload(), ensure_ascii=False)
            self._run_js(f"window.Coconut && window.Coconut.updateSession({payload});")

        def on_web_ready(self) -> None:
            self.web_ready = True
            self.push_strings_to_web()
            self.push_settings_to_web()
            self.push_session_to_web()
            self._run_js(
                f"window.Coconut && window.Coconut.setFullscreenState({'true' if self.isFullScreen() else 'false'});"
            )
            if self.pending_file is not None:
                target = self.pending_file
                self.pending_file = None
                self.open_file(target, push_history=True)
            else:
                self.show_welcome()

        def show_welcome(self) -> None:
            self.current_file = None
            self.has_toc = False
            self.is_editing = False
            self.is_dirty = False
            self.setWindowTitle(APP_NAME)
            recent_json = json.dumps(self.controller.config.get("recent_files", []))
            self._run_js(f"window.Coconut && window.Coconut.showWelcome({recent_json});")

        def open_file(self, path: Path, push_history: bool = True) -> None:
            resolved = path.expanduser().resolve()
            if not resolved.is_file():
                msg = self.controller.strings["toast_not_found"].format(name=resolved.name)
                self._run_js(f"window.Coconut && window.Coconut.showToast({json.dumps(msg)});")
                if self.current_file is None and self.web_ready:
                    self.show_welcome()
                return

            if not self.web_ready:
                self.pending_file = resolved
                return

            if push_history:
                if self._history_idx < 0 or self._history[self._history_idx] != resolved:
                    self._history = self._history[: self._history_idx + 1]
                    self._history.append(resolved)
                    self._history_idx = len(self._history) - 1

            self.controller.auto_enable_extensions_for_paths([resolved], notify=True)
            self.controller.register_open_file(resolved)
            self._watch_file(resolved)
            self.current_file = resolved
            self.is_editing = False
            self.is_dirty = False
            self._load_and_render(resolved, preserve_scroll=False)
            self.controller.record_recent_file(str(resolved))
            self.push_session_to_web()

        def close_current_file(self) -> None:
            if self.current_file is not None:
                self.controller.close_file(self.current_file)
            elif self.is_editing:
                self.show_welcome()
            else:
                self.close()

        def _watch_file(self, path: Path) -> None:
            existing = self.watcher.files()
            if existing:
                self.watcher.removePaths(existing)
            self.watcher.addPath(str(path))

        def _on_file_changed(self, _changed_path: str) -> None:
            if self._ignore_next_watch:
                self._ignore_next_watch = False
                if self.current_file and self.current_file.is_file():
                    p_str = str(self.current_file)
                    if p_str not in self.watcher.files():
                        self.watcher.addPath(p_str)
                return
            if not self.controller.config.get("auto_reload", True):
                return
            # Coordinate with Edit mode: pause auto-reload while editing or holding unsaved changes
            if self.is_editing or self.is_dirty:
                return
            self._reload_timer.start()

        def _reload_watched_file(self) -> None:
            if not self.controller.config.get("auto_reload", True):
                return
            if self.is_editing or self.is_dirty:
                return
            if self.current_file is None or not self.current_file.is_file():
                return
            path_str = str(self.current_file)
            if path_str not in self.watcher.files():
                self.watcher.addPath(path_str)
            self._load_and_render(self.current_file, preserve_scroll=True)

        def _load_and_render(self, path: Path, preserve_scroll: bool) -> None:
            try:
                doc = render_document_file(path)
            except Exception as exc:
                msg = self.controller.strings["toast_open_error"].format(err=str(exc))
                self._run_js(f"window.Coconut && window.Coconut.showToast({json.dumps(msg)});")
                return

            self.has_toc = len(doc.get("toc", [])) >= 2
            self._update_window_title()
            doc_json = json.dumps(doc, ensure_ascii=False)
            preserve_js = "true" if preserve_scroll else "false"
            self._run_js(f"window.Coconut && window.Coconut.renderDocument({doc_json}, {preserve_js});")

        def reload_current(self) -> None:
            if self.current_file is not None and self.current_file.is_file():
                if self.is_editing:
                    return
                self._load_and_render(self.current_file, preserve_scroll=True)
                msg = self.controller.strings["toast_reloaded"]
                self._run_js(f"window.Coconut && window.Coconut.showToast({json.dumps(msg)});")

        def go_back(self) -> None:
            if self._history_idx > 0:
                self._history_idx -= 1
                self.open_file(self._history[self._history_idx], push_history=False)

        def go_forward(self) -> None:
            if self._history_idx + 1 < len(self._history):
                self._history_idx += 1
                self.open_file(self._history[self._history_idx], push_history=False)

        def open_file_dialog(self) -> None:
            if self.current_file is not None:
                start_dir = str(self.current_file.parent)
            else:
                docs_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
                start_dir = docs_dir or str(Path.home())

            s = self.controller.strings
            file_filter = build_file_dialog_filter(self.controller.config, self.controller.lang)
            chosen_list, _ = QFileDialog.getOpenFileNames(
                self,
                s["dialog_open_title"],
                start_dir,
                file_filter,
            )
            if chosen_list:
                self.controller.add_files_to_session([Path(p) for p in chosen_list], activate_first=True)

        def open_folder_dialog(self) -> None:
            if self.current_file is not None:
                start_dir = str(self.current_file.parent)
            else:
                docs_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
                start_dir = docs_dir or str(Path.home())

            s = self.controller.strings
            chosen_dir = QFileDialog.getExistingDirectory(
                self,
                s["dialog_open_folder_title"],
                start_dir,
            )
            if chosen_dir:
                self.controller.add_folder_to_session(Path(chosen_dir), activate_first=True)

        def open_find_bar(self) -> None:
            self._run_js("window.Coconut && window.Coconut.openFindBar();")

        def open_settings_modal(self) -> None:
            self._run_js("window.Coconut && window.Coconut.openSettings('reading');")

        def toggle_fullscreen(self) -> None:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

        def changeEvent(self, event: QEvent) -> None:
            if event.type() == QEvent.Type.WindowStateChange:
                self._run_js(
                    f"window.Coconut && window.Coconut.setFullscreenState({'true' if self.isFullScreen() else 'false'});"
                )
            super().changeEvent(event)

        def _show_context_menu(self, pos: Any) -> None:
            s = self.controller.strings
            sc = self.controller.config.get("shortcuts", DEFAULT_SHORTCUTS)
            menu = QMenu(self)

            if self.page.hasSelection():
                selected = self.page.selectedText().strip()
                act_copy = QAction(s["ctx_copy"], menu)
                act_copy.triggered.connect(lambda: self.page.triggerAction(QWebEnginePage.WebAction.Copy))
                menu.addAction(act_copy)

                if selected and self.controller.config.get("translate_enabled", True):
                    sl = self.controller.config.get("translate_source", "auto")
                    tl = self.controller.config.get("translate_target", "es")
                    pair_label = f"{'Auto' if sl == 'auto' else sl.upper()} → {tl.upper()}"
                    act_tr = QAction(s["ctx_translate"].format(pair=pair_label), menu)
                    tr_url = build_translate_url(selected, sl, tl)
                    act_tr.triggered.connect(lambda _c=False, u=tr_url: QDesktopServices.openUrl(QUrl(u)))
                    menu.addAction(act_tr)
                menu.addSeparator()

            def _label(key: str, sc_key: str) -> str:
                seq = sc.get(sc_key, "")
                return f"{s[key]}\t{seq}" if seq else s[key]

            act_open = QAction(_label("ctx_open", "open_file"), menu)
            act_open.triggered.connect(self.open_file_dialog)
            menu.addAction(act_open)

            act_open_folder = QAction(_label("ctx_open_folder", "open_folder"), menu)
            act_open_folder.triggered.connect(self.open_folder_dialog)
            menu.addAction(act_open_folder)

            act_new = QAction(_label("ctx_new_file", "new_file"), menu)
            act_new.triggered.connect(self.start_new_document)
            menu.addAction(act_new)

            if self.current_file is None or self.current_file.suffix.lower() != ".epub":
                act_edit = QAction(_label("ctx_edit", "toggle_edit"), menu)
                act_edit.triggered.connect(self.toggle_edit_mode)
                menu.addAction(act_edit)

            if self.is_editing or self.is_dirty:
                act_save = QAction(_label("ctx_save", "save_file"), menu)
                act_save.triggered.connect(self.request_save)
                menu.addAction(act_save)

            menu.addSeparator()

            act_inc = QAction(_label("ctx_inc", "font_increase"), menu)
            act_inc.triggered.connect(lambda: self.controller.adjust_font_size(1))
            menu.addAction(act_inc)

            act_dec = QAction(_label("ctx_dec", "font_decrease"), menu)
            act_dec.triggered.connect(lambda: self.controller.adjust_font_size(-1))
            menu.addAction(act_dec)

            act_reset = QAction(_label("ctx_reset", "font_reset"), menu)
            act_reset.triggered.connect(lambda: self.controller.set_font_size(DEFAULT_FONT_SIZE))
            menu.addAction(act_reset)

            menu.addSeparator()

            act_theme = QAction(_label("ctx_theme", "cycle_theme"), menu)
            act_theme.triggered.connect(self.controller.cycle_theme)
            menu.addAction(act_theme)

            act_toc = QAction(_label("ctx_toc", "toggle_sidebar"), menu)
            act_toc.triggered.connect(self.controller.toggle_sidebar)
            menu.addAction(act_toc)

            act_fs = QAction(_label("ctx_fullscreen", "fullscreen"), menu)
            act_fs.triggered.connect(self.toggle_fullscreen)
            menu.addAction(act_fs)

            if self.current_file is not None:
                act_close = QAction(_label("ctx_close_file", "close_file"), menu)
                act_close.triggered.connect(self.close_current_file)
                menu.addAction(act_close)

            menu.addSeparator()

            act_settings = QAction(_label("ctx_settings", "open_settings"), menu)
            act_settings.triggered.connect(self.open_settings_modal)
            menu.addAction(act_settings)

            menu.exec(self.view.mapToGlobal(pos))

        def _extract_dropped_paths(self, mime: Any) -> list[Path]:
            paths: list[Path] = []
            if mime is None or not mime.hasUrls():
                return paths
            for url in mime.urls():
                if url.isLocalFile():
                    p = Path(url.toLocalFile())
                    if p.is_dir():
                        paths.append(p)
                    elif p.is_file() and is_known_supported_file(p):
                        paths.append(p)
            return paths

        def _handle_dropped_paths(self, paths: list[Path]) -> None:
            if not paths:
                return
            dirs = [p for p in paths if p.is_dir()]
            files = [p for p in paths if p.is_file()]
            for d in dirs:
                self.controller.add_folder_to_session(d, activate_first=not files)
            if files:
                self.controller.add_files_to_session(files, activate_first=True)

        def dragEnterEvent(self, event: Any) -> None:
            if self._extract_dropped_paths(event.mimeData()):
                event.acceptProposedAction()

        def dropEvent(self, event: Any) -> None:
            paths = self._extract_dropped_paths(event.mimeData())
            if paths:
                event.acceptProposedAction()
                self._handle_dropped_paths(paths)

        def eventFilter(self, obj: QObject, event: QEvent) -> bool:
            etype = event.type()
            if etype == QEvent.Type.ChildAdded and obj is self.view:
                child = event.child()
                if child is not None:
                    child.installEventFilter(self)
                return False

            if etype in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                if self._extract_dropped_paths(event.mimeData()):
                    event.acceptProposedAction()
                    return False

            if etype == QEvent.Type.Drop:
                paths = self._extract_dropped_paths(event.mimeData())
                if paths:
                    event.acceptProposedAction()
                    self._run_js("document.getElementById('drop-overlay')?.classList.add('hidden');")
                    QTimer.singleShot(0, lambda ps=paths: self._handle_dropped_paths(ps))
                    return True

            if etype == QEvent.Type.MouseButtonPress:
                btn = event.button()
                if btn == Qt.MouseButton.BackButton:
                    self.go_back()
                    return True
                if btn == Qt.MouseButton.ForwardButton:
                    self.go_forward()
                    return True

            return super().eventFilter(obj, event)

        def closeEvent(self, event: Any) -> None:
            if not self.controller.ephemeral:
                if not self.isFullScreen():
                    self.controller.config["window_width"] = self.width()
                    self.controller.config["window_height"] = self.height()
                self.controller.sync_session_to_config()
                self.controller.persist_config()
            self.controller.unregister_window(self)
            super().closeEvent(event)

    class AppController(QObject):
        """Coordinates settings, multi-file session, extensions, localization, IPC, and windows."""

        def __init__(self, ephemeral: bool = False) -> None:
            super().__init__()
            self.ephemeral = ephemeral
            self.config = load_config()
            self.lang = resolve_language(self.config.get("language", "auto"))
            self.strings = get_strings(self.lang)
            self.windows: list[ReaderWindow] = []
            self.server: QLocalServer | None = None
            self._ipc_buffers: dict[int, bytes] = {}

            self.open_files: list[Path] = []
            self.open_folders: list[Path] = []
            self.custom_file_order: dict[str, list[str]] = dict(self.config.get("custom_file_order", {}))
            self.active_file: Path | None = None
            self.collapsed_folders: set[str] = set(self.config.get("collapsed_folders", []))

            if not ephemeral and self.config.get("restore_session", True):
                for raw_path in self.config.get("open_files", []):
                    p = Path(raw_path).expanduser().resolve()
                    if p.is_file() and p not in self.open_files:
                        self.open_files.append(p)
                for raw_dir in self.config.get("open_folders", []):
                    d = Path(raw_dir).expanduser().resolve()
                    if d.is_dir() and d not in self.open_folders:
                        self.open_folders.append(d)
                raw_active = self.config.get("active_file", "")
                if raw_active:
                    cand = Path(raw_active).expanduser().resolve()
                    if cand in self.open_files or (self.open_folders and cand.is_file()):
                        self.active_file = cand
                if self.active_file is None and self.open_files:
                    self.active_file = self.open_files[0]

        def persist_config(self) -> None:
            if self.ephemeral:
                return
            try:
                save_config(self.config)
            except Exception:
                pass

        def sync_session_to_config(self) -> None:
            if self.ephemeral:
                return
            if self.config.get("restore_session", True):
                self.config["open_files"] = [str(p) for p in self.open_files]
                self.config["open_folders"] = [str(d) for d in self.open_folders]
                self.config["active_file"] = str(self.active_file) if self.active_file else ""
            else:
                self.config["open_files"] = []
                self.config["open_folders"] = []
                self.config["active_file"] = ""
            self.config["custom_file_order"] = self.custom_file_order
            self.config["collapsed_folders"] = sorted(self.collapsed_folders)

        def session_payload(self) -> dict[str, Any]:
            folder_trees: list[dict[str, Any]] = []
            for d in self.open_folders:
                if d.is_dir():
                    tree, _ = scan_folder_tree(d, self.custom_file_order)
                    folder_trees.append(tree)
            return {
                "open_files": [str(p) for p in self.open_files],
                "open_folders": [str(d) for d in self.open_folders if d.is_dir()],
                "folder_trees": folder_trees,
                "active_file": str(self.active_file) if self.active_file else "",
                "collapsed_folders": sorted(self.collapsed_folders),
            }

        def auto_enable_extensions_for_paths(self, paths: list[Path], notify: bool = True) -> list[str]:
            newly = ensure_extensions_enabled_for_paths(self.config, list(paths))
            if not newly:
                return []
            toast_msg: str | None = None
            if notify:
                names = [
                    EXTENSION_BY_ID.get(eid, {}).get("name_es" if self.lang == "es" else "name_en", eid)
                    for eid in newly
                ]
                toast_msg = self.strings.get("toast_ext_auto_enabled", "Auto-enabled: {names}").format(
                    names=", ".join(names[:4]) + ("…" if len(names) > 4 else "")
                )
            self.broadcast_settings(toast_msg)
            return newly

        def add_folder_to_session(self, folder: Path, activate_first: bool = True) -> None:
            resolved_dir = folder.expanduser().resolve()
            if not resolved_dir.is_dir():
                return
            if resolved_dir not in self.open_folders:
                self.open_folders.append(resolved_dir)
            _tree, discovered_files = scan_folder_tree(resolved_dir, self.custom_file_order)
            if discovered_files:
                self.auto_enable_extensions_for_paths(discovered_files, notify=False)
                if activate_first:
                    target = discovered_files[0]
                    self.active_file = target
                    win = self._ensure_window(initial_file=target)
                    if win.web_ready:
                        win.open_file(target, push_history=True)
                    else:
                        win.pending_file = target
                else:
                    self._ensure_window(initial_file=self.active_file)
                msg = self.strings.get("toast_folder_opened", "Opened folder: {name} ({count} files)").format(
                    name=resolved_dir.name, count=len(discovered_files)
                )
            else:
                self._ensure_window(initial_file=self.active_file)
                msg = self.strings.get("toast_folder_empty", "No supported files in {name}").format(
                    name=resolved_dir.name
                )
            self.broadcast_session()
            for win in self.windows:
                win.push_settings_to_web(msg)

        def close_folder(self, folder: Path) -> None:
            resolved_dir = folder.expanduser().resolve()
            if resolved_dir in self.open_folders:
                self.open_folders.remove(resolved_dir)
                self.broadcast_session()

        def reorder_open_files(self, ordered_paths: list[str]) -> None:
            existing = {str(p): p for p in self.open_files}
            new_list: list[Path] = []
            seen: set[str] = set()
            for raw in ordered_paths:
                if raw in existing and raw not in seen:
                    seen.add(raw)
                    new_list.append(existing[raw])
            for p in self.open_files:
                if str(p) not in seen:
                    new_list.append(p)
            self.open_files = new_list
            self.sync_session_to_config()
            self.persist_config()

        def reorder_open_folders(self, ordered_dirs: list[str]) -> None:
            existing = {str(d): d for d in self.open_folders}
            new_list: list[Path] = []
            seen: set[str] = set()
            for raw in ordered_dirs:
                if raw in existing and raw not in seen:
                    seen.add(raw)
                    new_list.append(existing[raw])
            for d in self.open_folders:
                if str(d) not in seen:
                    new_list.append(d)
            self.open_folders = new_list
            self.broadcast_session()

        def reorder_folder_children(self, folder_path: str, ordered_children: list[str]) -> None:
            if not folder_path:
                return
            self.custom_file_order[folder_path] = list(ordered_children)
            self.broadcast_session()

        def set_sidebar_width(self, width: int) -> None:
            self.config["sidebar_width"] = clamp_sidebar_width(width)
            self.persist_config()

        def broadcast_session(self) -> None:
            self.sync_session_to_config()
            self.persist_config()
            for win in self.windows:
                win.push_session_to_web()

        def broadcast_settings(self, toast_msg: str | None = None) -> None:
            self.sync_session_to_config()
            self.persist_config()
            for win in self.windows:
                win.push_settings_to_web(toast_msg)

        def register_open_file(self, resolved: Path) -> None:
            if resolved not in self.open_files:
                self.open_files.append(resolved)
            self.active_file = resolved
            self.sync_session_to_config()
            self.persist_config()

        def add_files_to_session(self, paths: list[Path], activate_first: bool = True) -> None:
            added: list[Path] = []
            for p in paths:
                resolved = p.expanduser().resolve()
                if resolved.is_file():
                    if resolved not in self.open_files:
                        self.open_files.append(resolved)
                    added.append(resolved)
            if not added:
                return
            self.auto_enable_extensions_for_paths(added, notify=True)
            target = added[0] if activate_first else (self.active_file or added[0])
            self.active_file = target
            win = self._ensure_window(initial_file=target)
            if win.web_ready:
                win.open_file(target, push_history=True)
            else:
                win.pending_file = target
            self.broadcast_session()

        def activate_file(self, path: Path, push_history: bool = True) -> None:
            resolved = path.expanduser().resolve()
            if not resolved.is_file():
                self.close_file(resolved)
                return
            win = self._ensure_window(initial_file=resolved)
            win.open_file(resolved, push_history=push_history)

        def close_file(self, path: Path) -> None:
            resolved = path.expanduser().resolve()
            if resolved not in self.open_files:
                return
            idx = self.open_files.index(resolved)
            self.open_files.pop(idx)

            if self.active_file == resolved:
                if self.open_files:
                    nxt = self.open_files[min(idx, len(self.open_files) - 1)]
                    self.active_file = nxt
                    for win in self.windows:
                        win.open_file(nxt, push_history=False)
                else:
                    self.active_file = None
                    for win in self.windows:
                        win.show_welcome()
            self.broadcast_session()

        def cycle_open_file(self, delta: int) -> None:
            if len(self.open_files) < 2:
                return
            try:
                idx = self.open_files.index(self.active_file) if self.active_file else 0
            except ValueError:
                idx = 0
            nxt = self.open_files[(idx + delta) % len(self.open_files)]
            self.activate_file(nxt, push_history=False)

        def toggle_folder_collapsed(self, folder: str) -> None:
            if folder in self.collapsed_folders:
                self.collapsed_folders.remove(folder)
            else:
                self.collapsed_folders.add(folder)
            self.sync_session_to_config()
            self.persist_config()

        def set_font_size(self, size: int) -> None:
            clamped = clamp_font_size(size)
            self.config["font_size"] = clamped
            self.broadcast_settings(self.strings["toast_text"].format(size=clamped))

        def adjust_font_size(self, delta: int) -> None:
            current = int(self.config.get("font_size", DEFAULT_FONT_SIZE))
            self.set_font_size(current + int(delta))

        def set_theme(self, theme: str) -> None:
            if theme not in VALID_THEMES:
                return
            self.config["theme"] = theme
            label = self.strings.get(f"theme_{theme}", theme)
            self.broadcast_settings(self.strings["toast_palette"].format(label=label))

        def cycle_theme(self) -> None:
            current = self.config.get("theme", "warm-dark")
            try:
                idx = VALID_THEMES.index(current)
            except ValueError:
                idx = 0
            self.set_theme(VALID_THEMES[(idx + 1) % len(VALID_THEMES)])

        def set_language(self, lang_pref: str) -> None:
            if lang_pref not in VALID_LANGUAGES:
                return
            self.config["language"] = lang_pref
            self.lang = resolve_language(lang_pref)
            self.strings = get_strings(self.lang)
            self.persist_config()
            for win in self.windows:
                win.push_strings_to_web()
                win.push_settings_to_web()

        def set_setting_bool(self, key: str, value: bool) -> None:
            allowed = {
                "sidebar_visible",
                "show_progress_bar",
                "show_line_numbers",
                "auto_reload",
                "restore_session",
                "translate_enabled",
            }
            if key not in allowed:
                return
            self.config[key] = bool(value)
            self.broadcast_settings()

        def set_setting_choice(self, key: str, value: str) -> None:
            validators: dict[str, tuple[str, ...]] = {
                "reading_width": VALID_READING_WIDTHS,
                "line_height": VALID_LINE_HEIGHTS,
                "accent_color": VALID_ACCENT_COLORS,
                "code_style": VALID_CODE_STYLES,
            }
            valid_values = validators.get(key)
            if not valid_values or value not in valid_values:
                return
            self.config[key] = value
            self.broadcast_settings()

        def set_extension_enabled(self, ext_id: str, enabled: bool) -> None:
            norm = normalize_extension_id(ext_id)
            if norm is None:
                return
            current = set(self.config.get("enabled_extensions", []))
            if enabled:
                current.add(norm)
            else:
                current.discard(norm)
            self.config["enabled_extensions"] = [
                eid for eid in VALID_EXTENSION_IDS if eid in current
            ]
            mod = EXTENSION_BY_ID.get(norm, {})
            mod_name = mod.get("name_es" if self.lang == "es" else "name_en", norm)
            toast_key = "toast_ext_added" if enabled else "toast_ext_removed"
            toast_msg = self.strings.get(toast_key, "{name}").format(name=mod_name)
            self.broadcast_settings(toast_msg)

        def set_all_extensions(self, enabled: bool) -> None:
            self.config["enabled_extensions"] = list(VALID_EXTENSION_IDS) if enabled else []
            self.broadcast_settings()

        def set_translate_pair(self, source: str, target: str) -> None:
            if source in TRANSLATE_SOURCE_CODES:
                self.config["translate_source"] = source
            if target in TRANSLATE_TARGET_CODES:
                self.config["translate_target"] = target
            self.broadcast_settings()

        def set_shortcut(self, action: str, seq: str) -> None:
            if action not in DEFAULT_SHORTCUTS:
                return
            cleaned = seq.strip()[:40]
            shortcuts = dict(self.config.get("shortcuts", DEFAULT_SHORTCUTS))
            if cleaned:
                for other_action, other_seq in list(shortcuts.items()):
                    if other_action != action and other_seq == cleaned:
                        shortcuts[other_action] = ""
            shortcuts[action] = cleaned
            self.config["shortcuts"] = shortcuts
            self.persist_config()
            for win in self.windows:
                win.rebuild_shortcuts()
                win.push_settings_to_web(self.strings["toast_shortcut_saved"])

        def reset_shortcuts(self) -> None:
            self.config["shortcuts"] = dict(DEFAULT_SHORTCUTS)
            self.persist_config()
            for win in self.windows:
                win.rebuild_shortcuts()
                win.push_settings_to_web(self.strings["toast_shortcuts_reset"])

        def toggle_sidebar(self) -> None:
            self.config["sidebar_visible"] = not bool(self.config.get("sidebar_visible", True))
            self.broadcast_settings()

        def record_recent_file(self, path: str) -> None:
            if self.ephemeral:
                return
            add_recent_file(self.config, path)
            self.persist_config()

        def _ensure_window(self, initial_file: Path | None = None) -> ReaderWindow:
            if self.windows:
                win = self.windows[0]
                win.show()
                win.raise_()
                win.activateWindow()
                return win
            return self.open_new_window(initial_file=initial_file)

        def open_new_window(self, initial_file: Path | None = None) -> ReaderWindow:
            win = ReaderWindow(self, initial_file=initial_file)
            self.windows.append(win)
            win.show()
            win.raise_()
            win.activateWindow()
            return win

        def unregister_window(self, win: ReaderWindow) -> None:
            if win in self.windows:
                self.windows.remove(win)

        def open_paths(self, raw_paths: list[str]) -> None:
            if not raw_paths:
                if self.windows:
                    win = self.windows[0]
                    win.show()
                    win.raise_()
                    win.activateWindow()
                else:
                    self.open_new_window(self.active_file)
                return

            resolved_list = [Path(p).expanduser().resolve() for p in raw_paths]
            dirs = [p for p in resolved_list if p.is_dir()]
            files = [p for p in resolved_list if p.is_file()]
            for d in dirs:
                self.add_folder_to_session(d, activate_first=not files)
            if files:
                self.add_files_to_session(files, activate_first=True)

        def start_ipc_server(self, socket_name: str) -> None:
            QLocalServer.removeServer(socket_name)
            self.server = QLocalServer(self)
            if self.server.listen(socket_name):
                self.server.newConnection.connect(self._on_ipc_connection)

        def _on_ipc_connection(self) -> None:
            if self.server is None:
                return
            while self.server.hasPendingConnections():
                conn = self.server.nextPendingConnection()
                if conn is None:
                    continue
                self._ipc_buffers[id(conn)] = b""
                conn.readyRead.connect(lambda c=conn: self._read_ipc_message(c))
                conn.disconnected.connect(lambda c=conn: self._cleanup_ipc(c))
                if conn.bytesAvailable() > 0:
                    self._read_ipc_message(conn)

        def _cleanup_ipc(self, conn: QLocalSocket) -> None:
            self._ipc_buffers.pop(id(conn), None)
            conn.deleteLater()

        def _read_ipc_message(self, conn: QLocalSocket) -> None:
            key = id(conn)
            buf = self._ipc_buffers.get(key, b"") + bytes(conn.readAll())
            self._ipc_buffers[key] = buf
            if b"\n" not in buf:
                return
            line, _rest = buf.split(b"\n", 1)
            self._ipc_buffers.pop(key, None)
            try:
                payload = json.loads(line.decode("utf-8", errors="replace"))
                paths = payload.get("paths", []) if isinstance(payload, dict) else []
                if isinstance(paths, list):
                    self.open_paths([p for p in paths if isinstance(p, str)])
            except Exception:
                pass
            finally:
                conn.disconnectFromServer()

    def try_send_to_running_instance(socket_name: str, paths: list[str]) -> bool:
        sock = QLocalSocket()
        sock.connectToServer(socket_name)
        if not sock.waitForConnected(150):
            return False
        payload = json.dumps({"paths": paths}).encode("utf-8") + b"\n"
        sock.write(payload)
        sock.waitForBytesWritten(300)
        sock.disconnectFromServer()
        return True

    def load_bundled_fonts(app: QApplication) -> None:
        for fname in (
            "AtkinsonHyperlegibleNext[wght].ttf",
            "AtkinsonHyperlegibleNext-Italic[wght].ttf",
        ):
            fpath = FONTS_DIR / fname
            if fpath.is_file():
                QFontDatabase.addApplicationFont(str(fpath))
        app.setFont(QFont("Atkinson Hyperlegible Next", 10))

    def run_self_test(app: QApplication, target_file: Path) -> int:
        controller = AppController(ephemeral=True)
        win = ReaderWindow(controller, initial_file=target_file)
        controller.windows.append(win)

        exit_code = {"value": 1}

        def finish(code: int) -> None:
            exit_code["value"] = code
            win.close()
            app.quit()

        safety = QTimer()
        safety.setSingleShot(True)
        safety.timeout.connect(lambda: (print("SELF_TEST_TIMEOUT=True"), finish(1)))
        safety.start(10000)

        js_probe = """
        (() => {
          const contentEl = document.getElementById('content');
          if (!document.body || !contentEl) {
            return { contentLen: 0, fontLoaded: false };
          }
          const fonts = Array.from(document.fonts).map(f => ({family: f.family, status: f.status}));
          const fontLoaded = fonts.some(f => f.family.includes('Atkinson Hyperlegible Next') && f.status === 'loaded');
          const bodyFont = getComputedStyle(document.body).fontFamily;
          const codeEl = document.querySelector('#content code');
          const preEl = document.querySelector('#content pre');
          const codeFont = codeEl ? getComputedStyle(codeEl).fontFamily : bodyFont;
          const preFont = preEl ? getComputedStyle(preEl).fontFamily : bodyFont;
          const tocCount = document.querySelectorAll('#toc-list .toc-item').length;
          const theme = document.documentElement.getAttribute('data-theme');
          const bg = getComputedStyle(document.body).backgroundColor;
          const fontSize = getComputedStyle(contentEl).fontSize;
          const contentLen = (contentEl.textContent || '').trim().length;
          const hasSettingsBtn = Boolean(document.getElementById('btn-settings'));
          const hasFullscreenBtn = Boolean(document.getElementById('btn-fullscreen'));
          const hasFilesSection = Boolean(document.getElementById('files-section'));
          const hasSettingsModal = Boolean(document.getElementById('settings-modal'));
          const hasExtensionsBtn = Boolean(document.getElementById('extensions-pill'));
          const hasExtensionsModal = Boolean(document.getElementById('extensions-modal'));
          const extCardsCount = document.querySelectorAll('#extensions-list .ext-card').length;
          const hasEditBtn = Boolean(document.getElementById('btn-edit-mode'));
          const hasEditorView = Boolean(document.getElementById('editor-view'));
          const hasHighlightEngine = Boolean(window.CocoHighlight);
          return {
            fontLoaded,
            bodyFont,
            codeFont,
            preFont,
            tocCount,
            theme,
            bg,
            fontSize,
            contentLen,
            hasSettingsBtn,
            hasFullscreenBtn,
            hasFilesSection,
            hasSettingsModal,
            hasExtensionsBtn,
            hasExtensionsModal,
            extCardsCount,
            hasEditBtn,
            hasEditorView,
            hasHighlightEngine
          };
        })();
        """

        def check_state() -> None:
            def on_probe(res: Any) -> None:
                if not isinstance(res, dict) or res.get("contentLen", 0) == 0 or not res.get("fontLoaded"):
                    QTimer.singleShot(120, check_state)
                    return
                js_errs = len(win.page.js_errors)
                print(f"FONT_LOADED={res.get('fontLoaded')}")
                print(f"BODY_FONT={res.get('bodyFont')}")
                print(f"CODE_FONT={res.get('codeFont')}")
                print(f"PRE_FONT={res.get('preFont')}")
                print(f"TOC_COUNT={res.get('tocCount')}")
                print(f"THEME={res.get('theme')}")
                print(f"BG={res.get('bg')}")
                print(f"FONT_SIZE={res.get('fontSize')}")
                print(f"HAS_SETTINGS_BTN={res.get('hasSettingsBtn')}")
                print(f"HAS_FULLSCREEN_BTN={res.get('hasFullscreenBtn')}")
                print(f"HAS_FILES_SECTION={res.get('hasFilesSection')}")
                print(f"HAS_SETTINGS_MODAL={res.get('hasSettingsModal')}")
                print(f"HAS_EXTENSIONS_BTN={res.get('hasExtensionsBtn')}")
                print(f"HAS_EXTENSIONS_MODAL={res.get('hasExtensionsModal')}")
                print(f"EXT_CARDS_COUNT={res.get('extCardsCount')}")
                print(f"HAS_EDIT_BTN={res.get('hasEditBtn')}")
                print(f"HAS_EDITOR_VIEW={res.get('hasEditorView')}")
                print(f"HAS_HIGHLIGHT_ENGINE={res.get('hasHighlightEngine')}")
                print(f"JS_ERRORS={js_errs}")
                for err in win.page.js_errors:
                    print(f"JS_ERROR_DETAIL={err}")

                ok = (
                    bool(res.get("fontLoaded"))
                    and "Atkinson Hyperlegible Next" in str(res.get("bodyFont", ""))
                    and "Atkinson Hyperlegible Next" in str(res.get("codeFont", ""))
                    and "Atkinson Hyperlegible Next" in str(res.get("preFont", ""))
                    and int(res.get("tocCount", 0)) > 0
                    and res.get("theme") == controller.config["theme"]
                    and bool(res.get("hasSettingsBtn"))
                    and bool(res.get("hasFullscreenBtn"))
                    and bool(res.get("hasFilesSection"))
                    and bool(res.get("hasSettingsModal"))
                    and bool(res.get("hasExtensionsBtn"))
                    and bool(res.get("hasExtensionsModal"))
                    and int(res.get("extCardsCount", 0)) >= 16
                    and bool(res.get("hasEditBtn"))
                    and bool(res.get("hasEditorView"))
                    and bool(res.get("hasHighlightEngine"))
                    and js_errs == 0
                )
                finish(0 if ok else 1)

            win.page.runJavaScript(js_probe, on_probe)

        win.show()
        QTimer.singleShot(350, check_state)
        app.exec()
        return exit_code["value"]

    return {
        "QApplication": QApplication,
        "QIcon": QIcon,
        "AppController": AppController,
        "ReaderWindow": ReaderWindow,
        "load_bundled_fonts": load_bundled_fonts,
        "run_self_test": run_self_test,
        "try_send_to_running_instance": try_send_to_running_instance,
        "normalize_cli_paths": normalize_cli_paths,
    }


def main() -> int:
    raw_argv = sys.argv[1:]
    if "-h" in raw_argv or "--help" in raw_argv:
        _print_help()
        return 0
    if "-v" in raw_argv or "--version" in raw_argv:
        print(f"{APP_NAME} {__version__}")
        return 0

    configure_gpu_env(raw_argv)

    rt = create_qt_runtime()
    QApplication = rt["QApplication"]
    QIcon = rt["QIcon"]
    AppController = rt["AppController"]
    load_bundled_fonts = rt["load_bundled_fonts"]
    run_self_test = rt["run_self_test"]
    try_send_to_running_instance = rt["try_send_to_running_instance"]
    normalize_cli_paths = rt["normalize_cli_paths"]

    standalone = "--standalone" in raw_argv
    self_test_path: Path | None = None
    temp_self_test_file: Path | None = None
    if "--self-test" in raw_argv:
        idx = raw_argv.index("--self-test")
        if idx + 1 < len(raw_argv) and not raw_argv[idx + 1].startswith("-"):
            self_test_path = Path(raw_argv[idx + 1]).expanduser().resolve()
        else:
            import tempfile
            fd, tmp_name = tempfile.mkstemp(prefix="coconut-selftest-", suffix=".md")
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(
                    "# Coconut Self-Test\n\n"
                    "## Section One\n\n"
                    "Reading and inline `code` check.\n\n"
                    "```python\n"
                    "def hello(name: str) -> str:\n"
                    "    return f'Hello {name}'\n"
                    "```\n\n"
                    "## Section Two\n\n"
                    "- [x] Extensions\n"
                    "- [x] Editor\n"
                )
            temp_self_test_file = Path(tmp_name)
            self_test_path = temp_self_test_file
        standalone = True

    paths = normalize_cli_paths(raw_argv)
    socket_name = f"coconut-ipc-{os.getuid()}"

    app = QApplication(sys.argv)
    if not standalone and try_send_to_running_instance(socket_name, paths):
        return 0

    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("coconut")

    icon_path = _resolve_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon.fromTheme("coconut", QIcon(str(icon_path))))
    else:
        app.setWindowIcon(QIcon.fromTheme("coconut"))

    load_bundled_fonts(app)

    if self_test_path is not None:
        try:
            return run_self_test(app, self_test_path)
        finally:
            if temp_self_test_file is not None:
                try:
                    temp_self_test_file.unlink(missing_ok=True)
                except OSError:
                    pass

    controller = AppController(ephemeral=False)
    if not standalone:
        controller.start_ipc_server(socket_name)

    controller.open_paths(paths)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
