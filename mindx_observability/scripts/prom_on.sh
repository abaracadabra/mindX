#!/usr/bin/env bash
# prom_on.sh — bring the full Prometheus stack up on demand
# Phase 1.2: Prom + Alertmanager + node_exporter + blackbox_exporter all start
# as a unit. Operator invokes this for PromQL sessions, incident investigation,
# or to arm email alerts. Pair with prom_off.sh.
#
# Set WITH_GRAFANA=1 to also start Grafana for dashboards.
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

UNITS="prometheus node-exporter blackbox-exporter alertmanager"
[ "${WITH_GRAFANA:-0}" = "1" ] && UNITS="$UNITS grafana"

echo "==> starting full Prom stack: $UNITS"
for u in $UNITS; do
    $RUN_AS_MINDX systemctl --user start "${u}.service" \
        && echo "    [+] ${u}.service" \
        || echo "    [!] ${u}.service FAILED to start"
done

# Verify each unit
echo
echo "==> verification"
sleep 5
for u in $UNITS; do
    state="$($RUN_AS_MINDX systemctl --user is-active "${u}.service" 2>/dev/null || echo inactive)"
    printf "    %-20s %s\n" "$u" "$state"
done

echo
echo "==> Prom stack URLs"
echo "    Prometheus  https://prom.pythai.net          (Basic Auth)"
echo "    Alertmanager https://alerts.pythai.net       (Basic Auth)"
if [ "${WITH_GRAFANA:-0}" = "1" ]; then
    echo "    Grafana     https://grafana.pythai.net       (Grafana auth)"
fi
echo
echo "    Reminder: bash scripts/prom_off.sh when done — frees ~416 MB."
