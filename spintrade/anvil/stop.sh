#!/usr/bin/env bash
# Stop the anvil node started by start.sh
set -euo pipefail
PID_FILE="$(dirname "$0")/.log/anvil.pid"
if [[ -f "$PID_FILE" ]]; then
  PID=$(cat "$PID_FILE")
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "stopped anvil (pid $PID)"
  fi
  rm -f "$PID_FILE"
fi
