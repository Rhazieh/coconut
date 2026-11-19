# Changelog

All notable changes to **Velum** are documented in this file.

## [1.1.0] - 2026-11-19

### Added
- **Multi-file session & collapsible folder groups:** Open multiple `.md` files simultaneously, grouped cleanly by parent folder (`FOLDERNAME`) beneath the reading outline in the left sidebar. Open files persist across restarts like a notepad until explicitly closed (`×`, middle-click, or `Ctrl+W`), remembering scroll position per document while switching.
- **Minimalist Settings modal (`Ctrl+,`) via bottom-left gear button:**
  - **Reading:** Palette cards, text size controls, live EN/ES/Auto language switcher, toggle switches (sidebar, progress hairline, auto-reload, session restore), and quick action buttons.
  - **Translate:** Configurable right-click Google Translate option for selected text (`Auto` + 27 common languages, quick presets like `EN → ES` / `ES → EN`, language swap button).
  - **Shortcuts:** Live shortcut editor for all 16 actions with automatic conflict clearing and one-click reset to defaults.
  - **About:** Credits, open-source licenses (MIT + SIL OFL 1.1), and direct links to contribute on GitHub.
- **Top-right Fullscreen button:** Dedicated button next to the palette switcher synchronized with `F11`.

## [1.0.0] - 2026-11-18

### Added
- Minimalist, viewer-only Markdown reader for Linux (**Wayland & X11**; KDE Plasma, GNOME, Hyprland, Sway, XFCE, and other Freedesktop environments).
- Bundled **Atkinson Hyperlegible Next** variable typeface (upright & italic) used uniformly across headings, body prose, UI chrome, tables, and code blocks.
- Three eye-comfort palettes designed to prevent halation and glare: **Warm Night** (`#191817` / `#DCD7CE`, default), **Paper Sepia** (`#F3ECDC` / `#352F28`), and **Soft Stone** (`#F4F3EE` / `#2A2926`).
- Customizable text size (`12–36 px`), `68ch` line measure, generous `1.72` line height, and reading progress hairline.
- Collapsible outline sidebar (`Ctrl+B`) with smooth scrollspy (auto-hidden when `< 2` headings).
- Fast GitHub-Flavored Markdown engine via `libcmark-gfm` (`ctypes`) with automatic `python-markdown` fallback, HTML/XSS sanitization, strict CSP, and local link/image resolution.
- Single-instance IPC (`QLocalServer`), live auto-reload (`QFileSystemWatcher`), drag-and-drop, in-document search (`Ctrl+F`), and bilingual EN/ES interface.
- User-level XDG installer (`install.sh`) and uninstaller (`uninstall.sh`), MIT + SIL OFL 1.1 licensing, and CI unit tests.
