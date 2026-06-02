#!/usr/bin/env bash
# lint.sh — validate every config in this repo using the same image versions deployed in prod.
# Requires Docker (or docker-compatible) on the local machine.
# Run from anywhere; resolves paths relative to this script.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

PROM_IMG="quay.io/prometheus/prometheus:v3.11.1"
AM_IMG="quay.io/prometheus/alertmanager:v0.32.0"
BB_IMG="quay.io/prometheus/blackbox-exporter:v0.27.0"

DOCKER="${DOCKER:-docker}"
command -v "$DOCKER" >/dev/null 2>&1 || { echo "docker (or podman) required"; exit 1; }

pass=0; fail=0
check() {
    local label="$1"; shift
    if "$@" >/tmp/lint.$$ 2>&1; then
        echo "  PASS  $label"
        pass=$((pass+1))
    else
        echo "  FAIL  $label"
        sed 's/^/        /' /tmp/lint.$$
        fail=$((fail+1))
    fi
    rm -f /tmp/lint.$$
}

echo "==> Prometheus config + rules"
check "prometheus.yml + rules" \
    $DOCKER run --rm \
        -v "$ROOT/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro" \
        -v "$ROOT/prometheus/rules:/etc/prometheus/rules:ro" \
        --entrypoint promtool "$PROM_IMG" check config /etc/prometheus/prometheus.yml

check "rules syntax (standalone)" \
    $DOCKER run --rm -v "$ROOT:/cfg:ro" \
        --entrypoint promtool "$PROM_IMG" \
        check rules /cfg/prometheus/rules/alert_rules.yml /cfg/prometheus/rules/recording_rules.yml

echo
echo "==> Alertmanager config"
check "alertmanager.yml" \
    $DOCKER run --rm -v "$ROOT:/cfg:ro" \
        --entrypoint amtool "$AM_IMG" \
        check-config /cfg/alertmanager/alertmanager.yml

echo
echo "==> Blackbox config"
check "blackbox.yml" \
    $DOCKER run --rm \
        -v "$ROOT/blackbox/blackbox.yml:/etc/blackbox_exporter/config.yml:ro" \
        "$BB_IMG" --config.file=/etc/blackbox_exporter/config.yml --config.check

echo
echo "==> YAML syntax (all .yml in repo)"
if command -v python3 >/dev/null 2>&1; then
    YAML_ERR=0
    while IFS= read -r f; do
        if ! python3 -c "import yaml; yaml.safe_load(open('$f'))" 2>/dev/null; then
            echo "  FAIL  $f"
            YAML_ERR=1; fail=$((fail+1))
        fi
    done < <(find "$ROOT" -name '*.yml' -not -path '*/grafana_data/*' -not -path '*/prometheus_data/*')
    [ "$YAML_ERR" = "0" ] && echo "  PASS  all *.yml parse" && pass=$((pass+1))
fi

echo
echo "==> Dashboard JSON parse"
JSON_ERR=0
for f in "$ROOT"/grafana/provisioning/dashboards/json/*.json; do
    if ! python3 -c "import json; json.load(open('$f'))" 2>/dev/null; then
        echo "  FAIL  $f"
        JSON_ERR=1; fail=$((fail+1))
    fi
done
[ "$JSON_ERR" = "0" ] && echo "  PASS  all dashboard json parse" && pass=$((pass+1))

echo
echo "==> Shell script syntax"
SH_ERR=0
for s in "$ROOT"/scripts/*.sh; do
    if ! bash -n "$s" 2>/dev/null; then
        echo "  FAIL  $s"
        SH_ERR=1; fail=$((fail+1))
    fi
done
[ "$SH_ERR" = "0" ] && echo "  PASS  all *.sh parse" && pass=$((pass+1))

echo
echo "------------------------------"
echo "RESULT: $pass pass, $fail fail"
[ "$fail" = "0" ] && exit 0 || exit 1
