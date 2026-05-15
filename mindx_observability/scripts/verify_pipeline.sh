#!/usr/bin/env bash
# verify_pipeline.sh — six-step end-to-end check after deploy
# Run from anywhere with curl access to *.pythai.net. Requires PROM_USER / PROM_PASS env.
set -euo pipefail

PROM_USER="${PROM_USER:-ops}"
PROM_PASS="${PROM_PASS:?set PROM_PASS env var}"
PROM_URL="${PROM_URL:-https://prom.pythai.net}"
GRAFANA_URL="${GRAFANA_URL:-https://grafana.pythai.net}"

pass() { echo "  PASS  $*"; }
fail() { echo "  FAIL  $*"; FAILED=1; }
FAILED=0

echo "[1/6] Prometheus targets — every job up"
TARGETS_JSON="$(curl -fsSL -u "$PROM_USER:$PROM_PASS" "$PROM_URL/api/v1/targets" || true)"
if [ -z "$TARGETS_JSON" ]; then
    fail "could not fetch /api/v1/targets — check Apache + Prom + htpasswd"
else
    DOWN=$(echo "$TARGETS_JSON" | jq -r '.data.activeTargets[] | select(.health!="up") | .labels.job' | sort -u)
    if [ -z "$DOWN" ]; then
        pass "all scrape jobs reporting up"
        echo "$TARGETS_JSON" | jq -r '.data.activeTargets[] | "    \(.labels.job)\t\(.health)\t\(.scrapeUrl)"'
    else
        fail "scrape jobs down: $DOWN"
    fi
fi

echo
echo "[2/6] node_exporter samples ingested"
LOAD=$(curl -fsSL -u "$PROM_USER:$PROM_PASS" "$PROM_URL/api/v1/query?query=node_load1" | jq -r '.data.result[0].value[1] // empty')
if [ -n "$LOAD" ]; then
    pass "node_load1 = $LOAD"
else
    fail "no node_load1 samples — node_exporter unreachable from Prom?"
fi

echo
echo "[3/6] blackbox probes resolving real targets"
PROBES=$(curl -fsSL -u "$PROM_USER:$PROM_PASS" "$PROM_URL/api/v1/query?query=probe_success" | jq -r '.data.result[]? | "\(.metric.instance)=\(.value[1])"')
if [ -n "$PROBES" ]; then
    echo "$PROBES" | sed 's/^/    /'
    if echo "$PROBES" | grep -qE '=0$'; then
        fail "one or more probe_success=0 — check the targets in prometheus.yml"
    else
        pass "all probe_success=1"
    fi
else
    fail "no probe_success samples — blackbox not scraping?"
fi

echo
echo "[4/6] Grafana login page reachable"
HTTP=$(curl -fsSL -o /dev/null -w "%{http_code}" "$GRAFANA_URL/login" || true)
if [ "$HTTP" = "200" ]; then
    pass "Grafana /login returned 200"
else
    fail "Grafana /login returned $HTTP"
fi

echo
echo "[5/6] Synthetic alert path"
echo "    (manual step — edit blackbox target to /intentional-404, POST /-/reload, wait 2m30s, check inbox)"
echo "    skip-marker: SYNTHETIC_ALERT_TESTED=1 to suppress"
if [ "${SYNTHETIC_ALERT_TESTED:-0}" = "1" ]; then
    pass "synthetic alert manually verified"
else
    echo "  SKIP  synthetic alert (run manually first time)"
fi

echo
echo "[6/6] Disk + memory budget sanity"
if command -v ssh >/dev/null 2>&1 && [ -n "${VPS_SSH:-}" ]; then
    ssh "$VPS_SSH" 'du -sh /home/mindx/obs/prometheus_data 2>/dev/null; free -h | head -2; swapon --show'
    pass "remote disk/mem reported above"
else
    echo "  SKIP  set VPS_SSH=root@168.231.126.58 to run remote disk/mem check"
fi

echo
[ "$FAILED" = "0" ] && echo "VERIFY: GREEN" || { echo "VERIFY: RED ($FAILED failure(s))"; exit 1; }
