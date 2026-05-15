#!/usr/bin/env bash
# install_deps.sh — single canonical entry point for VPS dependency setup
# Run as root on 168.231.126.58.
# Idempotent: safe to run multiple times.
#
# Installs:
#   - podman           (Quadlet runtime)
#   - apache2-utils    (htpasswd for Basic Auth)
#   - jq               (JSON parsing for verify + mindx-stat)
#   - dnsutils         (dig — for DNS propagation checks)
#   - htop             (text-mode dashboard, for `mindx-stat top`)
#   - python3-psutil   (for the Python TUI + /insight/host/* endpoints)
#
# Then calls bootstrap_vps.sh unless --skip-bootstrap is passed.
set -euo pipefail

REQUIRE_ROOT() { [ "$(id -u)" = "0" ] || { echo "must run as root"; exit 1; }; }
REQUIRE_ROOT

SKIP_BOOTSTRAP=0
for arg in "$@"; do
    case "$arg" in
        --skip-bootstrap) SKIP_BOOTSTRAP=1 ;;
        -h|--help)
            echo "Usage: $0 [--skip-bootstrap]"
            echo "  --skip-bootstrap   only install apt packages, don't call bootstrap_vps.sh"
            exit 0 ;;
    esac
done

echo "==> apt update + install dependencies"
DEBIAN_FRONTEND=noninteractive apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    podman \
    apache2-utils \
    jq \
    dnsutils \
    htop \
    python3-psutil

echo "==> verify versions"
for cmd in podman htpasswd jq dig htop; do
    if command -v "$cmd" >/dev/null 2>&1; then
        printf "    %-12s %s\n" "$cmd" "$("$cmd" --version 2>&1 | head -1)"
    else
        echo "    MISSING: $cmd"
        exit 1
    fi
done
python3 -c "import psutil; print(f'    python3-psutil {psutil.__version__}')"

if [ "$SKIP_BOOTSTRAP" = "0" ]; then
    HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    if [ -x "$HERE/bootstrap_vps.sh" ]; then
        echo
        echo "==> deps installed; continuing to bootstrap_vps.sh (swap, lingering, mkdir tree)"
        "$HERE/bootstrap_vps.sh"
    fi
else
    echo
    echo "==> deps installed (skipping bootstrap per --skip-bootstrap)"
fi
