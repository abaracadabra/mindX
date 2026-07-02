#!/usr/bin/env bash
# One-shot setup for The Dojo's training engine (Linux / macOS).
#   ./scripts/setup.sh [target]   target = auto|cpu|cuda|rocm-linux  (default: auto)
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET="${1:-auto}"
PY="${PYTHON:-python3}"

echo "==> Creating venv (.venv)"
"$PY" -m venv .venv
VENV_PY=".venv/bin/python"

echo "==> Installing training stack (target: $TARGET)"
( cd engine && "../$VENV_PY" -m dojo_engine.installer --install --target "$TARGET" )

echo "==> Fetching llama.cpp sidecar (auto-detect accel)"
"$VENV_PY" scripts/fetch_llama.py || echo "  (sidecar fetch skipped/failed — you can run it later)"

echo "==> Done. Point the app's Python path at: $(pwd)/$VENV_PY"
