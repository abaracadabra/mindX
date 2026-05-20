#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
#
# Smoke-test a running WordPress.agent instance.
# Exits 0 if healthy, non-zero otherwise.

set -euo pipefail

HOST="${WP_SERVER_HOST:-127.0.0.1}"
PORT="${WP_SERVER_PORT:-8765}"
URL="http://${HOST}:${PORT}/healthz"

echo "Probing ${URL}"
response="$(curl -sS -w '\n%{http_code}' --max-time 5 "${URL}")"
body="$(echo "${response}" | head -n -1)"
code="$(echo "${response}" | tail -n 1)"

echo "${body}"
if [[ "${code}" != "200" ]]; then
    echo "FAIL: HTTP ${code}" >&2
    exit 1
fi

if ! echo "${body}" | grep -q '"ok": true'; then
    echo "FAIL: health check returned ok=false" >&2
    exit 1
fi

echo "OK"
