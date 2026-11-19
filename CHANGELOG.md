# Changelog

All notable changes to **Coconut** (`coco`) are documented in this file.

## [1.3.0] - 2026-11-19

### Added
- **Floating Extensions pill & modal:** Symmetrical rounded top-left button (`Extensions` / `Extensiones`) opening a clean modal with a **Languages support** section (*"For future languages support"*), laying the groundwork for optional text-only modules (`.txt`, `.epub`, `.js`, `.ts`, `.java`, `.html`, etc.) installable on demand without compiler/IDE bloat.
- **Debian `.deb` & Arch `PKGBUILD` packaging:** Added `packaging/build-deb.sh` (`coconut_1.3.0_all.deb` published in GitHub Releases) and `packaging/aur/PKGBUILD`.
- **GitHub Social Preview banner:** Added `docs/social-preview.png` (`1280x640`).

### Changed
- **Full-bleed Coconut SVG icon:** Scaled the tilted half-coconut emblem in `assets/icons/coconut.svg` to match standard taskbar icon proportions on KDE Plasma and GNOME.

## [1.2.0] - 2026-11-19

### Changed
- **Rebranded to Coconut (`coco`):** Renamed project, repository (`Rhazieh/coconut`), application ID (`coconut.desktop`), and CLI (`coco`, with `coconut` alias) to establish a distinctive, memorable identity aligned with its dark charcoal shell and warm cream/amber palettes (previously *Velum*).
- **New Coconut Logo:** Custom minimalist 3D tilted half-coconut SVG icon (`assets/icons/coconut.svg`).

## [1.1.0] - 2026-11-19

### Added
- **Multi-file session & collapsible folder groups:** Open multiple `.md` files simultaneously, grouped cleanly by parent folder (`FOLDERNAME`) beneath the reading outline in the left sidebar. Open files persist across restarts like a notepad until explicitly closed (`×`, middle-click, or `Ctrl+W`), remembering scroll position per document while switching.
- **Minimalist Settings modal (`Ctrl+,`) via bottom-left gear button:**
  - **Reading:** Palette cards, text size controls, live EN/ES/Auto language switcher, toggle switches (sidebar, progress hairline, auto-reload, session restore), and quick action buttons.
  - **Translate:** Configurable right-click Google Translate option for selected text (`Auto` + 27 common languages, quick presets like `EN → ES` / `ES → EN`).
  - **Shortcuts:** Live shortcut editor for all 16 actions with automatic conflict clearing and one-click reset to defaults.
  - **About:** Credits, open-source licenses (MIT + SIL OFL 1.1), and direct links to contribute on GitHub.
- **Top-right Fullscreen button:** Dedicated button next to the palette switcher synchronized with `F11`.

## [1.0.0] - 2026-11-18

### Added
- Initial release of the minimalist, viewer-only Markdown reader for Linux (**Wayland & X11**; KDE Plasma, GNOME, Hyprland, Sway, XFCE, and other Freedesktop environments).
- Bundled **Atkinson Hyperlegible Next** variable typeface (upright & italic) used uniformly across headings, body prose, UI chrome, tables, and code blocks.
- Three eye-comfort palettes designed to prevent halation and glare: **Warm Night** (`#191817` / `#DCD7CE`, default), **Paper Sepia** (`#F3ECDC` / `#352F28`), and **Soft Stone** (`#F4F3EE` / `#2A2926`).
- Fast GitHub-Flavored Markdown engine via `libcmark-gfm` (`ctypes`) with automatic `python-markdown` fallback, HTML/XSS sanitization, strict CSP, and local link/image resolution.
- Single-instance IPC (`QLocalServer`), live auto-reload (`QFileSystemWatcher`), drag-and-drop, in-document search (`Ctrl+F`), bilingual EN/ES interface, and user-level XDG installer (`install.sh`).
