#!/usr/bin/env bash
# Install the Linux *system* packages needed to build The Dojo with `npm run tauri build`.
# (This is the build toolchain — WebKitGTK, the tray's appindicator, librsvg for the
#  AppImage bundler, etc. The Python training stack is a separate step: scripts/setup.sh.)
#
#   ./scripts/setup-linux.sh
#
# Supports Debian/Ubuntu (apt) and Fedora (dnf). Re-run safe (idempotent installs).
set -euo pipefail

SUDO=""
if [ "$(id -u)" -ne 0 ]; then SUDO="sudo"; fi

if command -v apt-get >/dev/null 2>&1; then
  echo "==> Debian/Ubuntu detected — installing build dependencies via apt"
  $SUDO apt-get update
  $SUDO apt-get install -y \
    libwebkit2gtk-4.1-dev \
    build-essential curl wget file \
    libxdo-dev \
    libssl-dev \
    libayatana-appindicator3-dev \
    librsvg2-dev \
    libgtk-3-dev \
    patchelf \
    pkg-config
elif command -v dnf >/dev/null 2>&1; then
  echo "==> Fedora detected — installing build dependencies via dnf"
  $SUDO dnf install -y \
    webkit2gtk4.1-devel \
    openssl-devel curl wget file \
    libxdo-devel \
    libappindicator-gtk3-devel \
    librsvg2-devel \
    gtk3-devel \
    patchelf \
    pkgconf-pkg-config
  $SUDO dnf group install -y "C Development Tools and Libraries" "Development Tools"
else
  echo "Unsupported distro: need apt-get or dnf." >&2
  echo "Install the equivalents of: webkit2gtk-4.1, gtk3, libayatana-appindicator3, librsvg2, libxdo, openssl, patchelf, pkg-config, plus a C toolchain." >&2
  exit 1
fi

echo "==> Done. You can now run: npm install && npm run tauri build"
