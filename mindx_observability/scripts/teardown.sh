#!/usr/bin/env bash
# teardown.sh — rollback the mindX observability stack
# Tier 1: stop heavy units (prometheus + grafana)   — default, no data loss
# Tier 2: stop entire stack                          — TIER=2
# Tier 3: wipe TSDB (last resort if disk is killing) — TIER=3
set -euo pipefail

TIER="${TIER:-1}"
MINDX_USER="${MINDX_USER:-mindx}"
MINDX_UID="$(id -u "$MINDX_USER")"
RUN_AS_MINDX="sudo -u $MINDX_USER XDG_RUNTIME_DIR=/run/user/$MINDX_UID"

echo "==> teardown tier $TIER"

case "$TIER" in
  1)
    $RUN_AS_MINDX systemctl --user stop prometheus.service grafana.service
    echo "    prometheus + grafana stopped. Alertmanager + exporters still running."
    ;;
  2)
    $RUN_AS_MINDX systemctl --user stop \
        prometheus.service grafana.service alertmanager.service \
        node-exporter.service blackbox-exporter.service
    echo "    all obs units stopped. Data + configs intact."
    ;;
  3)
    $RUN_AS_MINDX systemctl --user stop prometheus.service
    rm -rf "/home/$MINDX_USER/obs/prometheus_data"/*
    echo "    prometheus stopped + TSDB wiped. Restart with: $RUN_AS_MINDX systemctl --user start prometheus.service"
    ;;
  *)
    echo "unknown TIER=$TIER (use 1, 2, or 3)"
    exit 1
    ;;
esac

echo "==> remaining obs containers:"
$RUN_AS_MINDX podman ps --filter 'pod=' --format 'table {{.Names}}\t{{.Status}}'
