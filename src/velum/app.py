"""Velum — Minimalist, local-first, eye-comfort Markdown viewer for Linux (Wayland & X11)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from __init__ import APP_NAME, __version__  # noqa: E402
from config import (  # noqa: E402
    DEFAULT_FONT_SIZE,
    THEME_BG,
    VALID_THEMES,
    add_recent_file,
    clamp_font_size,
    load_config,
    save_config,
)
from i18n import get_strings, resolve_language  # noqa: E402
from renderer import render_markdown_file  # noqa: E402

ASSETS_DIR = APP_DIR / "assets"
FONTS_DIR = APP_DIR / "fonts"
INDEX_HTML = (ASSETS_DIR / "index.html").resolve()
MD_EXTENSIONS = {".md", ".markdown", ".mdown", ".mkd", ".mkdn", ".mdx", ".txt"}


def _resolve_icon_path() -> Path | None:
    xdg_data = os.environ.get("XDG_DATA_HOME", "").strip()
    data_dir = Path(xdg_data).expanduser() if xdg_data else Path.home() / ".local" / "share"
    candidates = [
        data_dir / "icons" / "hicolor" / "scalable" / "apps" / "velum.svg",
        APP_DIR.parent.parent / "assets" / "icons" / "velum.svg",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _print_help() -> None:
    print(
        f"{APP_NAME} {__version__} — Minimalist, eye-comfort Markdown viewer for Linux\n\n"
        "Usage:\n"
        "  velum [OPTIONS] [FILE...]\n\n"
        "Options:\n"
        "  -h, --help         Show this help message and exit\n"
        "  -v, --version      Show version and exit\n"
        "      --standalone   Run a separate process instead of forwarding to existing instance\n"
        "      --self-test F  Verify rendering and font loading on FILE and exit\n"
    )


def create_qt_runtime() -> dict[str, Any]:
    """Lazily import PyQt6 and construct Velum's GUI classes."""
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

    def is_markdown_or_text(path: Path) -> bool:
        return path.suffix.lower() in MD_EXTENSIONS

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
                if is_markdown_or_text(target) and target.is_file():
                    QTimer.singleShot(0, lambda p=target: self.win.open_file(p, push_history=True))
                else:
                    QDesktopServices.openUrl(url)
            elif url.scheme().lower() in ("http", "https", "mailto"):
                QDesktopServices.openUrl(url)
            self.deleteLater()
            return False

    class ReaderPage(QWebEnginePage):
        """Sandboxed page intercepting external links and local markdown navigation."""

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
                if is_markdown_or_text(local_path):
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

        @pyqtSlot()
        def toggleSidebar(self) -> None:
            self.win.controller.toggle_sidebar()

        @pyqtSlot()
        def openFileDialog(self) -> None:
            self.win.open_file_dialog()

        @pyqtSlot(str)
        def openRecentFile(self, path: str) -> None:
            if path:
                self.win.open_file(Path(path), push_history=True)

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

    class ReaderWindow(QMainWindow):
        """Minimalist distraction-free Markdown reading window."""

        def __init__(self, controller: "AppController", initial_file: Path | None = None) -> None:
            super().__init__()
            self.controller = controller
            self.current_file: Path | None = None
            self.pending_file: Path | None = initial_file
            self.web_ready = False
            self.has_toc = False

            self._history: list[Path] = []
            self._history_idx = -1

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

            self._setup_shortcuts()
            self.view.load(QUrl.fromLocalFile(str(INDEX_HTML)))

        def _setup_shortcuts(self) -> None:
            bindings: list[tuple[str, Any]] = [
                ("Ctrl+O", self.open_file_dialog),
                ("Ctrl++", lambda: self.controller.adjust_font_size(1)),
                ("Ctrl+=", lambda: self.controller.adjust_font_size(1)),
                ("Ctrl+-", lambda: self.controller.adjust_font_size(-1)),
                ("Ctrl+0", lambda: self.controller.set_font_size(DEFAULT_FONT_SIZE)),
                ("Ctrl+B", self.controller.toggle_sidebar),
                ("Ctrl+T", self.controller.cycle_theme),
                ("Ctrl+F", self.open_find_bar),
                ("F11", self.toggle_fullscreen),
                ("Ctrl+R", self.reload_current),
                ("F5", self.reload_current),
                ("Alt+Left", self.go_back),
                ("Alt+Right", self.go_forward),
                ("Ctrl+W", self.close),
                ("Ctrl+Q", QApplication.quit),
            ]
            for key, handler in bindings:
                sc = QShortcut(QKeySequence(key), self)
                sc.setContext(Qt.ShortcutContext.WindowShortcut)
                sc.activated.connect(handler)

        def _run_js(self, script: str) -> None:
            if self.web_ready:
                self.page.runJavaScript(script)

        def apply_theme_background(self, theme: str) -> None:
            bg = THEME_BG.get(theme, "#191817")
            self.setStyleSheet(f"QMainWindow {{ background-color: {bg}; }}")
            self.page.setBackgroundColor(QColor(bg))

        def push_settings_to_web(self, toast_msg: str | None = None) -> None:
            cfg = self.controller.config
            self.apply_theme_background(cfg["theme"])
            if not self.web_ready:
                return
            payload = json.dumps({
                "font_size": cfg["font_size"],
                "theme": cfg["theme"],
                "sidebar_visible": cfg["sidebar_visible"],
            })
            self._run_js(f"window.Velum && window.Velum.applySettings({payload});")
            if toast_msg:
                self._run_js(f"window.Velum && window.Velum.showToast({json.dumps(toast_msg)});")

        def on_web_ready(self) -> None:
            self.web_ready = True
            self._run_js(
                f"window.Velum && window.Velum.applyStrings({json.dumps(self.controller.strings)});"
            )
            self.push_settings_to_web()
            if self.pending_file is not None:
                target = self.pending_file
                self.pending_file = None
                self.open_file(target, push_history=True)
            else:
                self._show_welcome()

        def _show_welcome(self) -> None:
            self.current_file = None
            self.has_toc = False
            self.setWindowTitle(APP_NAME)
            recent_json = json.dumps(self.controller.config.get("recent_files", []))
            self._run_js(f"window.Velum && window.Velum.showWelcome({recent_json});")

        def open_file(self, path: Path, push_history: bool = True) -> None:
            resolved = path.expanduser().resolve()
            if not resolved.is_file():
                msg = self.controller.strings["toast_not_found"].format(name=resolved.name)
                self._run_js(f"window.Velum && window.Velum.showToast({json.dumps(msg)});")
                if self.current_file is None and self.web_ready:
                    self._show_welcome()
                return

            if not self.web_ready:
                self.pending_file = resolved
                return

            if push_history:
                if self._history_idx < 0 or self._history[self._history_idx] != resolved:
                    self._history = self._history[: self._history_idx + 1]
                    self._history.append(resolved)
                    self._history_idx = len(self._history) - 1

            self._watch_file(resolved)
            self.current_file = resolved
            self._load_and_render(resolved, preserve_scroll=False)
            self.controller.record_recent_file(str(resolved))

        def _watch_file(self, path: Path) -> None:
            existing = self.watcher.files()
            if existing:
                self.watcher.removePaths(existing)
            self.watcher.addPath(str(path))

        def _on_file_changed(self, _changed_path: str) -> None:
            self._reload_timer.start()

        def _reload_watched_file(self) -> None:
            if self.current_file is None or not self.current_file.is_file():
                return
            path_str = str(self.current_file)
            if path_str not in self.watcher.files():
                self.watcher.addPath(path_str)
            self._load_and_render(self.current_file, preserve_scroll=True)

        def _load_and_render(self, path: Path, preserve_scroll: bool) -> None:
            try:
                doc = render_markdown_file(path)
            except Exception as exc:
                msg = self.controller.strings["toast_open_error"].format(err=str(exc))
                self._run_js(f"window.Velum && window.Velum.showToast({json.dumps(msg)});")
                return

            self.has_toc = len(doc.get("toc", [])) >= 2
            self.setWindowTitle(f"{doc['filename']} — {APP_NAME}")
            doc_json = json.dumps(doc, ensure_ascii=False)
            preserve_js = "true" if preserve_scroll else "false"
            self._run_js(f"window.Velum && window.Velum.renderDocument({doc_json}, {preserve_js});")

        def reload_current(self) -> None:
            if self.current_file is not None and self.current_file.is_file():
                self._load_and_render(self.current_file, preserve_scroll=True)
                msg = self.controller.strings["toast_reloaded"]
                self._run_js(f"window.Velum && window.Velum.showToast({json.dumps(msg)});")

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
            chosen, _ = QFileDialog.getOpenFileName(
                self,
                s["dialog_open_title"],
                start_dir,
                s["dialog_filter"],
            )
            if chosen:
                self.open_file(Path(chosen), push_history=True)

        def open_find_bar(self) -> None:
            self._run_js("window.Velum && window.Velum.openFindBar();")

        def toggle_fullscreen(self) -> None:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()

        def _show_context_menu(self, pos: Any) -> None:
            s = self.controller.strings
            menu = QMenu(self)
            if self.page.hasSelection():
                act_copy = QAction(s["ctx_copy"], menu)
                act_copy.triggered.connect(lambda: self.page.triggerAction(QWebEnginePage.WebAction.Copy))
                menu.addAction(act_copy)
                menu.addSeparator()

            act_open = QAction(s["ctx_open"], menu)
            act_open.triggered.connect(self.open_file_dialog)
            menu.addAction(act_open)

            menu.addSeparator()

            act_inc = QAction(s["ctx_inc"], menu)
            act_inc.triggered.connect(lambda: self.controller.adjust_font_size(1))
            menu.addAction(act_inc)

            act_dec = QAction(s["ctx_dec"], menu)
            act_dec.triggered.connect(lambda: self.controller.adjust_font_size(-1))
            menu.addAction(act_dec)

            act_reset = QAction(s["ctx_reset"], menu)
            act_reset.triggered.connect(lambda: self.controller.set_font_size(DEFAULT_FONT_SIZE))
            menu.addAction(act_reset)

            menu.addSeparator()

            act_theme = QAction(s["ctx_theme"], menu)
            act_theme.triggered.connect(self.controller.cycle_theme)
            menu.addAction(act_theme)

            if self.has_toc:
                act_toc = QAction(s["ctx_toc"], menu)
                act_toc.triggered.connect(self.controller.toggle_sidebar)
                menu.addAction(act_toc)

            menu.exec(self.view.mapToGlobal(pos))

        def _extract_dropped_paths(self, mime: Any) -> list[Path]:
            paths: list[Path] = []
            if mime is None or not mime.hasUrls():
                return paths
            for url in mime.urls():
                if url.isLocalFile():
                    p = Path(url.toLocalFile())
                    if p.is_file():
                        paths.append(p)
            return paths

        def _handle_dropped_paths(self, paths: list[Path]) -> None:
            if not paths:
                return
            self.open_file(paths[0], push_history=True)
            for extra in paths[1:]:
                self.controller.open_new_window(extra)

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
            if not self.controller.ephemeral and not self.isFullScreen():
                self.controller.config["window_width"] = self.width()
                self.controller.config["window_height"] = self.height()
                self.controller.persist_config()
            self.controller.unregister_window(self)
            super().closeEvent(event)

    class AppController(QObject):
        """Coordinates settings, localization, single-instance IPC, and open windows."""

        def __init__(self, ephemeral: bool = False) -> None:
            super().__init__()
            self.ephemeral = ephemeral
            self.config = load_config()
            self.lang = resolve_language(self.config.get("language", "auto"))
            self.strings = get_strings(self.lang)
            self.windows: list[ReaderWindow] = []
            self.server: QLocalServer | None = None
            self._ipc_buffers: dict[int, bytes] = {}

        def persist_config(self) -> None:
            if self.ephemeral:
                return
            try:
                save_config(self.config)
            except Exception:
                pass

        def broadcast_settings(self, toast_msg: str | None = None) -> None:
            self.persist_config()
            for win in self.windows:
                win.push_settings_to_web(toast_msg)

        def set_font_size(self, size: int) -> None:
            clamped = clamp_font_size(size)
            self.config["font_size"] = clamped
            self.broadcast_settings(self.strings["toast_text"].format(size=clamped))

        def adjust_font_size(self, delta: int) -> None:
            current = int(self.config.get("font_size", DEFAULT_FONT_SIZE))
            self.set_font_size(current + int(delta))

        def cycle_theme(self) -> None:
            current = self.config.get("theme", "warm-dark")
            try:
                idx = VALID_THEMES.index(current)
            except ValueError:
                idx = 0
            nxt = VALID_THEMES[(idx + 1) % len(VALID_THEMES)]
            self.config["theme"] = nxt
            label = self.strings.get(f"theme_{nxt}", nxt)
            self.broadcast_settings(self.strings["toast_palette"].format(label=label))

        def toggle_sidebar(self) -> None:
            self.config["sidebar_visible"] = not bool(self.config.get("sidebar_visible", True))
            self.broadcast_settings()

        def record_recent_file(self, path: str) -> None:
            if self.ephemeral:
                return
            add_recent_file(self.config, path)
            self.persist_config()

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
                self.open_new_window(None)
                return

            for path_str in raw_paths:
                target = Path(path_str).expanduser().resolve()
                existing = next(
                    (w for w in self.windows if w.current_file is not None and w.current_file == target),
                    None,
                )
                if existing is not None:
                    existing.show()
                    existing.raise_()
                    existing.activateWindow()
                    continue

                welcome_win = next(
                    (w for w in self.windows if w.current_file is None and w.pending_file is None),
                    None,
                )
                if welcome_win is not None and len(raw_paths) == 1:
                    welcome_win.open_file(target, push_history=True)
                    welcome_win.show()
                    welcome_win.raise_()
                    welcome_win.activateWindow()
                else:
                    self.open_new_window(target)

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
          const fontSize = getComputedStyle(document.getElementById('content')).fontSize;
          const contentLen = (document.getElementById('content').textContent || '').trim().length;
          return {
            fontLoaded,
            bodyFont,
            codeFont,
            preFont,
            tocCount,
            theme,
            bg,
            fontSize,
            contentLen
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
    if "--self-test" in raw_argv:
        idx = raw_argv.index("--self-test")
        if idx + 1 >= len(raw_argv):
            print("Usage: velum --self-test <file.md>", file=sys.stderr)
            return 2
        self_test_path = Path(raw_argv[idx + 1]).expanduser().resolve()
        standalone = True

    paths = normalize_cli_paths(raw_argv)
    socket_name = f"velum-ipc-{os.getuid()}"

    app = QApplication(sys.argv)
    if not standalone and try_send_to_running_instance(socket_name, paths):
        return 0

    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setDesktopFileName("velum")

    icon_path = _resolve_icon_path()
    if icon_path is not None:
        app.setWindowIcon(QIcon.fromTheme("velum", QIcon(str(icon_path))))
    else:
        app.setWindowIcon(QIcon.fromTheme("velum"))

    load_bundled_fonts(app)

    if self_test_path is not None:
        return run_self_test(app, self_test_path)

    controller = AppController(ephemeral=False)
    if not standalone:
        controller.start_ipc_server(socket_name)

    controller.open_paths(paths)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
