#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_DIR="$HOME/.local/bin"
APP_INSTALL_DIR="$DATA_HOME/velum"
FONT_INSTALL_DIR="$DATA_HOME/fonts/atkinson-hyperlegible-next"
ICON_INSTALL_DIR="$DATA_HOME/icons/hicolor/scalable/apps"
DESKTOP_DIR="$DATA_HOME/applications"
BIN_PATH="$BIN_DIR/velum"
DESKTOP_PATH="$DESKTOP_DIR/velum.desktop"

SET_DEFAULT=1

for arg in "$@"; do
  case "$arg" in
    --no-default)
      SET_DEFAULT=0
      ;;
    -h|--help)
      cat <<'EOF'
Install Velum for the current user (XDG-compliant, no root required).

Usage:
  ./install.sh [OPTIONS]

Options:
  --no-default   Install launcher and .desktop entry without setting Velum as default for .md files
  -h, --help     Show this help message
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

echo "==> Checking dependencies..."
if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 is required." >&2
  exit 1
fi

if ! python3 -c "import PyQt6, PyQt6.QtWebEngineWidgets, PyQt6.QtWebChannel" >/dev/null 2>&1; then
  cat >&2 <<'EOF'
Error: Missing PyQt6 WebEngine dependencies.

Install them for your distribution:
  Debian / Ubuntu:
    sudo apt install python3-pyqt6 python3-pyqt6.qtwebengine python3-pyqt6.qtwebchannel cmark-gfm
  Fedora:
    sudo dnf install python3-pyqt6 python3-pyqt6-webengine cmark-gfm-libs
  Arch Linux:
    sudo pacman -S python-pyqt6 python-pyqt6-webengine cmark-gfm
EOF
  exit 1
fi

if ! python3 -c "
import ctypes, ctypes.util
has_cmark = bool(ctypes.util.find_library('cmark-gfm'))
if not has_cmark:
    import markdown
" >/dev/null 2>&1; then
  echo "Warning: Neither libcmark-gfm nor python3-markdown was detected." >&2
  echo "Install libcmark-gfm (recommended) or python3-markdown so Velum can render files." >&2
fi

echo "==> Installing Velum to $APP_INSTALL_DIR..."
mkdir -p "$BIN_DIR" "$APP_INSTALL_DIR" "$FONT_INSTALL_DIR" "$ICON_INSTALL_DIR" "$DESKTOP_DIR"

rm -rf "$APP_INSTALL_DIR/velum"
cp -r "$SCRIPT_DIR/src/velum" "$APP_INSTALL_DIR/velum"
find "$APP_INSTALL_DIR/velum" -type d -name "__pycache__" -exec rm -rf {} +

cp -f "$SCRIPT_DIR"/src/velum/fonts/*.ttf "$FONT_INSTALL_DIR/"
cp -f "$SCRIPT_DIR/assets/icons/velum.svg" "$ICON_INSTALL_DIR/velum.svg"

cat >"$BIN_PATH" <<EOF
#!/usr/bin/env bash
exec /usr/bin/python3 "$APP_INSTALL_DIR/velum/app.py" "\$@"
EOF
chmod +x "$BIN_PATH"

sed "s|@BIN_PATH@|$BIN_PATH|g" "$SCRIPT_DIR/assets/velum.desktop.in" >"$DESKTOP_PATH"

if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f "$DATA_HOME/fonts" >/dev/null 2>&1 || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
  kbuildsycoca5 >/dev/null 2>&1 || true
fi

if [ "$SET_DEFAULT" -eq 1 ] && command -v xdg-mime >/dev/null 2>&1; then
  xdg-mime default velum.desktop text/markdown >/dev/null 2>&1 || true
  xdg-mime default velum.desktop text/x-markdown >/dev/null 2>&1 || true
  echo "==> Set Velum as default viewer for Markdown files."
fi

echo "==> Velum installed successfully!"
echo "    Binary:  $BIN_PATH"
echo "    Desktop: $DESKTOP_PATH"

case ":$PATH:" in
  *":$BIN_DIR:"*)
    ;;
  *)
    echo ""
    echo "Note: $BIN_DIR is not in your PATH. Add this line to ~/.bashrc or ~/.zshrc:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    ;;
esac
