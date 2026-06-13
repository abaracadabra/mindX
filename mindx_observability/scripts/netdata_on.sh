#!/usr/bin/env bash
# netdata_on.sh — bring netdata (the daily monitoring UI) up
# Phase 1.2: netdata is the always-on monitoring layer. This script is the
# explicit kill-switch reverse; useful when netdata has been stopped via
# netdata_off.sh or obs_off.sh and needs to come back.
set -euo pipefail

MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

echo "==> starting netdata.service"
$RUN_AS_MINDX systemctl --user start netdata.service

# Wait up to 30s for active state
for i in 1 2 3 4 5 6; do
    sleep 5
    state="$($RUN_AS_MINDX systemctl --user is-active netdata.service 2>/dev/null || true)"
    [ "$state" = "active" ] && break
done

echo "    netdata state: $state"
if [ "$state" = "active" ]; then
    echo
    echo "==> netdata is available at https://netdata.pythai.net"
    echo "    Local probe: curl http://127.0.0.1:19999/api/v1/info | jq .version"
else
    echo
    echo "==> netdata did not become active in 30s."
    echo "    Diagnostics: $RUN_AS_MINDX journalctl --user -u netdata.service -n 30 --no-pager"
    exit 1
fi
