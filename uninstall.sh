#!/usr/bin/env bash
set -euo pipefail

DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
BIN_PATH="$HOME/.local/bin/velum"
APP_INSTALL_DIR="$DATA_HOME/velum"
FONT_INSTALL_DIR="$DATA_HOME/fonts/atkinson-hyperlegible-next"
ICON_PATH="$DATA_HOME/icons/hicolor/scalable/apps/velum.svg"
DESKTOP_PATH="$DATA_HOME/applications/velum.desktop"
CONFIG_DIR="$CONFIG_HOME/velum"

PURGE=0

for arg in "$@"; do
  case "$arg" in
    --purge)
      PURGE=1
      ;;
    -h|--help)
      cat <<'EOF'
Uninstall Velum for the current user.

Usage:
  ./uninstall.sh [OPTIONS]

Options:
  --purge    Also remove user settings (~/.config/velum)
  -h, --help Show this help message
EOF
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

rm -f "$BIN_PATH" "$ICON_PATH" "$DESKTOP_PATH"
rm -rf "$APP_INSTALL_DIR" "$FONT_INSTALL_DIR"

if [ "$PURGE" -eq 1 ]; then
  rm -rf "$CONFIG_DIR"
fi

if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f "$DATA_HOME/fonts" >/dev/null 2>&1 || true
fi

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DATA_HOME/applications" >/dev/null 2>&1 || true
fi

if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t "$DATA_HOME/icons/hicolor" >/dev/null 2>&1 || true
fi

if command -v kbuildsycoca6 >/dev/null 2>&1; then
  kbuildsycoca6 >/dev/null 2>&1 || true
elif command -v kbuildsycoca5 >/dev/null 2>&1; then
  kbuildsycoca5 >/dev/null 2>&1 || true
fi

echo "==> Velum uninstalled."
if [ "$PURGE" -eq 0 ] && [ -d "$CONFIG_DIR" ]; then
  echo "    Settings preserved at: $CONFIG_DIR (use --purge to remove)"
fi
