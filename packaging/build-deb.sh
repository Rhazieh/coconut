#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="$(python3 -c "import re; print(re.search(r'__version__\s*=\s*\"([^\"]+)\"', open('$REPO_ROOT/src/coconut/__init__.py').read()).group(1))")"

OUT_DIR="$REPO_ROOT/dist"
DEB_NAME="coconut_${VERSION}_all.deb"
DEB_PATH="$OUT_DIR/$DEB_NAME"

STAGING="$(mktemp -d)"
trap 'rm -rf "$STAGING"' EXIT

mkdir -p "$OUT_DIR" \
         "$STAGING/DEBIAN" \
         "$STAGING/usr/bin" \
         "$STAGING/usr/share/coconut" \
         "$STAGING/usr/share/applications" \
         "$STAGING/usr/share/icons/hicolor/scalable/apps" \
         "$STAGING/usr/share/fonts/truetype/atkinson-hyperlegible-next" \
         "$STAGING/usr/share/doc/coconut"

cp -r "$REPO_ROOT/src/coconut" "$STAGING/usr/share/coconut/coconut"
find "$STAGING/usr/share/coconut/coconut" -type d -name "__pycache__" -exec rm -rf {} +

cp -f "$REPO_ROOT"/src/coconut/fonts/*.ttf "$STAGING/usr/share/fonts/truetype/atkinson-hyperlegible-next/"
cp -f "$REPO_ROOT/assets/icons/coconut.svg" "$STAGING/usr/share/icons/hicolor/scalable/apps/coconut.svg"
sed "s|@BIN_PATH@|/usr/bin/coco|g" "$REPO_ROOT/assets/coconut.desktop.in" >"$STAGING/usr/share/applications/coconut.desktop"

cat >"$STAGING/usr/bin/coco" <<'EOF'
#!/usr/bin/env bash
exec /usr/bin/python3 /usr/share/coconut/coconut/app.py "$@"
EOF
chmod 0755 "$STAGING/usr/bin/coco"
ln -sf coco "$STAGING/usr/bin/coconut"

cat >"$STAGING/usr/share/doc/coconut/copyright" <<'EOF'
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: Coconut
Source: https://github.com/Rhazieh/coconut

Files: *
Copyright: 2026 Maximiliano Cano (Rhazieh)
License: MIT

Files: usr/share/coconut/coconut/fonts/* usr/share/fonts/truetype/atkinson-hyperlegible-next/*
Copyright: 2020-2024 The Atkinson Hyperlegible Next Project Authors
License: SIL-OFL-1.1
EOF

chmod -R a+rX,go-w "$STAGING/usr"
chmod 0755 "$STAGING/usr/bin/coco"

INSTALLED_KB="$(du -sk "$STAGING/usr" | awk '{print $1}')"

cat >"$STAGING/DEBIAN/control" <<EOF
Package: coconut
Version: ${VERSION}
Section: editors
Priority: optional
Architecture: all
Installed-Size: ${INSTALLED_KB}
Maintainer: Maximiliano Cano <maxi24cano@gmail.com>
Homepage: https://github.com/Rhazieh/coconut
Depends: python3 (>= 3.10), python3-pyqt6, python3-pyqt6.qtwebengine, python3-pyqt6.qtwebchannel, cmark-gfm | python3-markdown
Recommends: fonts-noto-color-emoji, xdg-utils
Description: Minimalist, local-first, eye-comfort Markdown viewer for Linux
 Coconut (coco) is a viewer-only Markdown reader built for long reading
 sessions without raw syntax clutter, split editors, or cloud tracking.
 It uses Atkinson Hyperlegible Next as its sole typeface and calibrated
 anti-halation palettes on Wayland and X11.
EOF

cat >"$STAGING/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f /usr/share/fonts/truetype/atkinson-hyperlegible-next >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 0755 "$STAGING/DEBIAN/postinst"

cat >"$STAGING/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
if command -v fc-cache >/dev/null 2>&1; then
  fc-cache -f /usr/share/fonts/truetype >/dev/null 2>&1 || true
fi
if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database -q /usr/share/applications || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
  gtk-update-icon-cache -f -t /usr/share/icons/hicolor >/dev/null 2>&1 || true
fi
exit 0
EOF
chmod 0755 "$STAGING/DEBIAN/postrm"

fakeroot dpkg-deb --build "$STAGING" "$DEB_PATH"
echo "==> Built Debian package: $DEB_PATH"
dpkg-deb --info "$DEB_PATH"
