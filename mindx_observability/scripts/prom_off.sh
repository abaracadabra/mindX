#!/usr/bin/env bash
# prom_off.sh — stop the full Prometheus stack
# Phase 1.2: tears down Prom + AM + node + blackbox + Grafana (if running).
# netdata stays running — it's the always-on monitoring layer.
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

# All Prom-stack units (5). Note: netdata is NOT included — it stays up.
UNITS="prometheus alertmanager node-exporter blackbox-exporter grafana"

echo "==> stopping Prom stack (keeps netdata running)"
$RUN_AS_MINDX systemctl --user stop $(printf "%s.service " $UNITS) 2>&1 \
    | sed 's/^/    /' || true

echo
echo "==> verification"
for u in $UNITS; do
    state="$($RUN_AS_MINDX systemctl --user is-active "${u}.service" 2>/dev/null || echo inactive)"
    printf "    %-20s %s\n" "$u" "$state"
done

# Verify netdata is still up
netdata_state="$($RUN_AS_MINDX systemctl --user is-active netdata.service 2>/dev/null || echo inactive)"
printf "    %-20s %s  (always-on; should be active)\n" "netdata" "$netdata_state"

echo
echo "==> Prom stack stopped. ~416 MB freed."
echo "    Daily monitoring at https://netdata.pythai.net is unaffected."
