#!/usr/bin/env bash
# netdata_off.sh — stop netdata
# Frees ~256 MB. Pair with netdata_on.sh.
# Note: stopping netdata leaves mindX with NO always-on monitoring UI;
# the Prom stack is also off-by-default. Operator should know what they're doing.
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

echo "==> stopping netdata.service"
$RUN_AS_MINDX systemctl --user stop netdata.service || true

state="$($RUN_AS_MINDX systemctl --user is-active netdata.service 2>/dev/null || echo inactive)"
echo "    netdata state: $state"

if [ "$state" = "inactive" ] || [ "$state" = "failed" ]; then
    echo "==> netdata stopped. ~256 MB freed."
    echo "    Reminder: mindX now has NO always-on monitoring UI."
    echo "    Bring it back with: bash scripts/netdata_on.sh"
else
    echo "==> WARNING: netdata still reports state=$state"
    exit 1
fi
