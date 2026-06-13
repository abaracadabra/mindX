#!/usr/bin/env bash
# grafana_off.sh — bring Grafana down on demand
# Frees ~200 MB RAM. Pair with grafana_on.sh.
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

echo "==> stopping grafana.service"
$RUN_AS_MINDX systemctl --user stop grafana.service || true

state="$($RUN_AS_MINDX systemctl --user is-active grafana.service 2>/dev/null || echo inactive)"
echo "    grafana state: $state"

if [ "$state" = "inactive" ] || [ "$state" = "failed" ]; then
    echo "==> Grafana stopped. ~200 MB RAM freed for mindX."
else
    echo "==> WARNING: grafana still reports state=$state"
    exit 1
fi
