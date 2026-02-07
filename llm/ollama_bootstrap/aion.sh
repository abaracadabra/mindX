#!/usr/bin/env bash
# aion.sh - Install and configure Ollama on Linux when no inference connection is found.
# mindX uses this to bootstrap local inference so self-improvement can continue from core.
# Official install: https://ollama.com/download/linux
# Usage: ./aion.sh [--pull-model MODEL] [--serve]

set -e

OLLAMA_INSTALL_URL="${OLLAMA_INSTALL_URL:-https://ollama.com/install.sh}"
DEFAULT_MODEL="${DEFAULT_MODEL:-llama3.2}"
SERVE_IN_BACKGROUND=false
PULL_MODEL=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull-model) PULL_MODEL="${2:-$DEFAULT_MODEL}"; shift 2 ;;
    --serve) SERVE_IN_BACKGROUND=true; shift ;;
    *) shift ;;
  esac
done

if [[ -z "$PULL_MODEL" ]]; then
  PULL_MODEL="$DEFAULT_MODEL"
fi

echo "[aion.sh] Checking for Ollama..."

# Already installed and in PATH?
if command -v ollama &>/dev/null; then
  echo "[aion.sh] Ollama already installed: $(ollama --version 2>/dev/null || true)"
else
  echo "[aion.sh] Ollama not found. Installing via official script..."
  if ! curl -fsSL "$OLLAMA_INSTALL_URL" | sh; then
    echo "[aion.sh] ERROR: Install failed. Manual install: curl -fsSL https://ollama.com/install.sh | sh" >&2
    exit 1
  fi
  echo "[aion.sh] Install completed."
fi

# Start serve in background if requested (e.g. headless server)
if [[ "$SERVE_IN_BACKGROUND" == true ]]; then
  if ! pgrep -x ollama &>/dev/null; then
    echo "[aion.sh] Starting ollama serve in background..."
    nohup ollama serve &>/dev/null &
    sleep 3
  fi
fi

# Wait for API to be reachable
OLLAMA_HOST="${OLLAMA_HOST:-http://127.0.0.1:11434}"
for i in {1..30}; do
  if curl -sSf "${OLLAMA_HOST}/api/tags" &>/dev/null; then
    echo "[aion.sh] Ollama API is reachable at $OLLAMA_HOST"
    break
  fi
  if [[ $i -eq 30 ]]; then
    echo "[aion.sh] WARN: Ollama API not reachable after 30 tries. Start with: ollama serve" >&2
    exit 1
  fi
  sleep 1
done

# Pull default model so mindX has a working model
echo "[aion.sh] Ensuring model '$PULL_MODEL' is available..."
if ollama list 2>/dev/null | grep -qE "^${PULL_MODEL}([[:space:]]|$)"; then
  echo "[aion.sh] Model $PULL_MODEL already present."
else
  ollama pull "$PULL_MODEL" || {
    echo "[aion.sh] WARN: Pull failed. Try: ollama pull $PULL_MODEL" >&2
  }
fi

echo "[aion.sh] Done. mindX can use Ollama at $OLLAMA_HOST (set OLLAMA_HOST or use fallback_url in models/ollama.yaml)."
