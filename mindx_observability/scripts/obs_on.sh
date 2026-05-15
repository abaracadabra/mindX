#!/usr/bin/env bash
# obs_on.sh — start the observability stack
# Phase 1.2 default: netdata only (the always-on monitoring layer).
# Flags:
#   WITH_PROM=1       — also start Prom + AM + node + blackbox (equivalent to prom_on.sh)
#   WITH_GRAFANA=1    — implies WITH_PROM=1, plus Grafana
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

# Grafana implies Prom (no point running Grafana without a datasource).
[ "${WITH_GRAFANA:-0}" = "1" ] && WITH_PROM=1

UNITS="netdata"
if [ "${WITH_PROM:-0}" = "1" ]; then
    UNITS="$UNITS prometheus node-exporter blackbox-exporter alertmanager"
fi
[ "${WITH_GRAFANA:-0}" = "1" ] && UNITS="$UNITS grafana"

echo "==> starting obs stack: $UNITS"
for u in $UNITS; do
    $RUN_AS_MINDX systemctl --user start "${u}.service" \
        && echo "    [+] ${u}.service" \
        || echo "    [!] ${u}.service FAILED to start"
done

echo
echo "==> status"
for u in $UNITS; do
    state="$($RUN_AS_MINDX systemctl --user is-active "${u}.service" 2>/dev/null || echo inactive)"
    printf "    %-20s %s\n" "$u" "$state"
done

echo
echo "==> URLs"
echo "    netdata     https://netdata.pythai.net      (Basic Auth — daily UI)"
if [ "${WITH_PROM:-0}" = "1" ]; then
    echo "    Prometheus  https://prom.pythai.net         (Basic Auth)"
    echo "    Alertmanager https://alerts.pythai.net      (Basic Auth)"
fi
[ "${WITH_GRAFANA:-0}" = "1" ] && echo "    Grafana     https://grafana.pythai.net      (Grafana auth)"

echo
echo "==> Terminal: mindx-stat all   |   Kill switch: bash scripts/obs_off.sh"
