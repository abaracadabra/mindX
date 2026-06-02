#!/usr/bin/env bash
# grafana_on.sh — bring Grafana up on demand
# Phase 1.1: Grafana is off-by-default. Run this for deep-dive sessions.
# Pair with grafana_off.sh when done to free ~200 MB RAM.
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

echo "==> starting grafana.service"
$RUN_AS_MINDX systemctl --user start grafana.service

# Wait up to 30s for active state
for i in 1 2 3 4 5 6; do
    sleep 5
    state="$($RUN_AS_MINDX systemctl --user is-active grafana.service 2>/dev/null || true)"
    [ "$state" = "active" ] && break
done

echo "    grafana state: $state"
if [ "$state" = "active" ]; then
    echo
    echo "==> Grafana UI is now available at https://grafana.pythai.net"
    echo "    Remember: bash scripts/grafana_off.sh when done to free ~200 MB RAM"
else
    echo
    echo "==> Grafana did not become active. Check: $RUN_AS_MINDX journalctl --user -u grafana.service -n 30 --no-pager"
    exit 1
fi
