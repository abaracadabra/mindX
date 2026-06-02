#!/usr/bin/env bash
# bootstrap_vps.sh — idempotent VPS prep for mindX observability
# Run as root on 168.231.126.58.
# Side effects: apt install obs deps (via install_deps.sh), 4 GB swap, enable lingering for mindx, mkdir /home/mindx/obs/*
# Phase 1.1: package installs delegated to install_deps.sh wrapper (adds htop/jq/dnsutils/python3-psutil for text tools)
set -euo pipefail

REQUIRE_ROOT() { [ "$(id -u)" = "0" ] || { echo "must run as root"; exit 1; }; }
REQUIRE_ROOT

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER" 2>/dev/null || echo)"
[ -n "$MINDX_UID" ] || { echo "user $MINDX_USER not found"; exit 1; }

echo "==> apt install obs deps"
# Phase 1.1: defer to install_deps.sh if present, else minimal fallback
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -x "$HERE/install_deps.sh" ]; then
    "$HERE/install_deps.sh" --skip-bootstrap   # avoid recursion
else
    apt-get update -qq
    apt-get install -y -qq podman apache2-utils jq dnsutils htop python3-psutil
fi

echo "==> verify Podman >= 4.4"
PODMAN_VER="$(podman --version | awk '{print $3}')"
echo "    podman $PODMAN_VER"

echo "==> swap file (4 GB)"
if ! swapon --show=NAME --noheadings | grep -q '^/swapfile$'; then
    fallocate -l 4G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "    swap enabled"
else
    echo "    swap already enabled"
fi

echo "==> enable lingering for $MINDX_USER"
loginctl enable-linger "$MINDX_USER"

echo "==> create /home/$MINDX_USER/obs/ tree"
sudo -u "$MINDX_USER" mkdir -p \
    "/home/$MINDX_USER/obs/prometheus_data" \
    "/home/$MINDX_USER/obs/alertmanager_data" \
    "/home/$MINDX_USER/obs/grafana_data" \
    "/home/$MINDX_USER/obs/prometheus/rules" \
    "/home/$MINDX_USER/obs/alertmanager" \
    "/home/$MINDX_USER/obs/blackbox" \
    "/home/$MINDX_USER/obs/grafana/provisioning/datasources" \
    "/home/$MINDX_USER/obs/grafana/provisioning/dashboards/json"
sudo -u "$MINDX_USER" mkdir -p "/home/$MINDX_USER/.config/containers/systemd"

# grafana container runs as uid 472 inside; chown data dir so SQLite is writable
chown -R 472:472 "/home/$MINDX_USER/obs/grafana_data" 2>/dev/null || true

echo "==> create htpasswd dir"
mkdir -p /etc/apache2/htpasswd
chmod 750 /etc/apache2/htpasswd

echo "==> bootstrap complete. Next: rsync mindx_observability/ + run deploy_quadlets.sh"
