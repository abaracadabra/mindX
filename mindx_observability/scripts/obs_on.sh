#!/usr/bin/env bash
# obs_on.sh — start the obs stack (Grafana excluded by default)
# Run as root on VPS. Set WITH_GRAFANA=1 to include Grafana.
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

UNITS="prometheus node-exporter blackbox-exporter alertmanager"
[ "${WITH_GRAFANA:-0}" = "1" ] && UNITS="$UNITS grafana"

echo "==> starting obs stack: $UNITS"
for u in $UNITS; do
    $RUN_AS_MINDX systemctl --user start "${u}.service" \
        && echo "    [+] ${u}.service" \
        || echo "    [!] ${u}.service FAILED to start"
done

echo
echo "==> status"
$RUN_AS_MINDX systemctl --user is-active prometheus alertmanager node-exporter blackbox-exporter \
    | paste -d' ' <(echo -e "prometheus\nalertmanager\nnode-exporter\nblackbox-exporter") -

if [ "${WITH_GRAFANA:-0}" = "1" ]; then
    echo "grafana       $($RUN_AS_MINDX systemctl --user is-active grafana.service || true)"
    echo "    UI: https://grafana.pythai.net"
else
    echo "grafana       (skipped — run scripts/grafana_on.sh when needed)"
fi

echo
echo "==> mindx-stat all   # for live text dashboard"
