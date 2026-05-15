#!/usr/bin/env bash
# deploy_quadlets.sh — rsync configs to /home/mindx/obs/, install Quadlets, start units
# Run as root on 168.231.126.58 after bootstrap_vps.sh.
# Expects mindx_observability/ to already be on the VPS (rsync from laptop).
set -euo pipefail

SRC="${1:-/root/mindx_observability}"
[ -d "$SRC" ] || { echo "source dir not found: $SRC (pass as \$1)"; exit 1; }

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
MINDX_HOME="/home/$MINDX_USER"

echo "==> sync configs to $MINDX_HOME/obs/"
rsync -av --delete \
    --exclude='*_data' \
    --exclude='podman_quadlets' \
    --exclude='apache' \
    --exclude='scripts' \
    --exclude='docs' \
    --exclude='vendor' \
    --exclude='cli' \
    --exclude='*.md' \
    --exclude='LICENSE' \
    "$SRC/" "$MINDX_HOME/obs/"
chown -R "$MINDX_USER:$MINDX_USER" "$MINDX_HOME/obs/"
chown -R 472:472 "$MINDX_HOME/obs/grafana_data" 2>/dev/null || true

echo "==> install Quadlets to $MINDX_HOME/.config/containers/systemd/"
install -o "$MINDX_USER" -g "$MINDX_USER" -m 644 \
    "$SRC/podman_quadlets/"*.{network,container} \
    "$MINDX_HOME/.config/containers/systemd/"

echo "==> daemon-reload (user manager for $MINDX_USER)"
sudo -u "$MINDX_USER" XDG_RUNTIME_DIR="/run/user/$MINDX_UID" \
    systemctl --user daemon-reload

echo "==> verify SMTP password file"
SMTP_FILE="$MINDX_HOME/obs/alertmanager/smtp_app_password"
if [ ! -f "$SMTP_FILE" ]; then
    echo "WARNING: $SMTP_FILE not present. Alertmanager will fail to send email."
    echo "  Place a Gmail app-password (single-line, no newline) and chmod 600."
fi

echo "==> start units (Phase 1.2: netdata only by default — Prom stack OFF)"
# Phase 1.2: netdata is the always-on monitoring UI. Prom + AM + node + blackbox
# + Grafana are all off-by-default; bring them up via scripts/prom_on.sh.
# Set WITH_PROM=1 (and optionally WITH_GRAFANA=1) to start the full stack.
[ "${WITH_GRAFANA:-0}" = "1" ] && WITH_PROM=1

UNITS="obs-network netdata"
if [ "${WITH_PROM:-0}" = "1" ]; then
    UNITS="$UNITS prometheus node-exporter blackbox-exporter alertmanager"
fi
[ "${WITH_GRAFANA:-0}" = "1" ] && UNITS="$UNITS grafana"

for u in $UNITS; do
    sudo -u "$MINDX_USER" XDG_RUNTIME_DIR="/run/user/$MINDX_UID" \
        systemctl --user start "${u}.service" 2>&1 | sed "s/^/    [$u] /"
done

echo
echo "==> default state: netdata https://netdata.pythai.net (Basic Auth)"
if [ "${WITH_PROM:-0}" = "1" ]; then
    echo "    Prom stack ALSO started — https://prom.pythai.net + alerts.pythai.net"
else
    echo "    Prom stack OFF — run scripts/prom_on.sh when needed for PromQL"
fi

echo "==> status"
sudo -u "$MINDX_USER" XDG_RUNTIME_DIR="/run/user/$MINDX_UID" \
    systemctl --user status netdata --no-pager -l | head -10
if [ "${WITH_PROM:-0}" = "1" ]; then
    sudo -u "$MINDX_USER" XDG_RUNTIME_DIR="/run/user/$MINDX_UID" \
        systemctl --user status prometheus alertmanager node-exporter blackbox-exporter --no-pager -l \
        | head -32
fi
if [ "${WITH_GRAFANA:-0}" = "1" ]; then
    sudo -u "$MINDX_USER" XDG_RUNTIME_DIR="/run/user/$MINDX_UID" \
        systemctl --user status grafana --no-pager -l | head -8
fi

echo "==> deploy complete. Next: install Apache vhosts + certbot (see runbook)."
