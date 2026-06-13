#!/usr/bin/env bash
# obs_off.sh — single canonical kill switch for the entire obs stack
# Phase 1.2: stops ALL 6 obs units (netdata + Prom + AM + node + blackbox + Grafana).
# Returns within 10s. Configs + data left intact — restart with scripts/obs_on.sh.
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

# All 6 units — kill switch is total. netdata FIRST so the daily UI goes dark fast.
UNITS="netdata prometheus alertmanager node-exporter blackbox-exporter grafana"

echo "==> stopping obs stack (kill switch — all 5 units)"
$RUN_AS_MINDX systemctl --user stop $(printf "%s.service " $UNITS) 2>&1 \
    | sed 's/^/    /' || true

echo
echo "==> verification"
for u in $UNITS; do
    state="$($RUN_AS_MINDX systemctl --user is-active "${u}.service" 2>/dev/null || echo inactive)"
    printf "    %-20s %s\n" "$u" "$state"
done

echo
echo "==> containers"
$RUN_AS_MINDX podman ps --filter 'name=prometheus' --filter 'name=grafana' \
    --filter 'name=alertmanager' --filter 'name=node-exporter' --filter 'name=blackbox-exporter' \
    --format 'table {{.Names}}\t{{.Status}}' || true

echo
echo "==> obs stack stopped. Data + configs preserved. Restart: scripts/obs_on.sh"
