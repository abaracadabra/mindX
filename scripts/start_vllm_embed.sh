#!/bin/bash
# Start vLLM serving mxbai-embed-large for fast embedding
# Falls back to Ollama if vLLM is not available
#
# Usage: ./scripts/start_vllm_embed.sh
# Or as systemd service: see below
#
# vLLM serves OpenAI-compatible /v1/embeddings on port 8001
# mindX's memory_pgvector.py tries vLLM first, falls back to Ollama

set -e

MODEL="mixedbread-ai/mxbai-embed-large-v1"
PORT=8001
HOST="0.0.0.0"

echo "Starting vLLM embedding server..."
echo "  Model: $MODEL"
echo "  Port:  $PORT"
echo "  API:   http://$HOST:$PORT/v1/embeddings"

# Check if vLLM is installed
if ! command -v vllm &>/dev/null; then
    VLLM_PATH="/home/mindx/mindX/.mindx_env/bin/vllm"
    if [ ! -f "$VLLM_PATH" ]; then
        echo "ERROR: vLLM not installed. Run: pip install vllm"
        exit 1
    fi
    exec "$VLLM_PATH" serve "$MODEL" --host "$HOST" --port "$PORT" --dtype float32 --max-model-len 512
else
    exec vllm serve "$MODEL" --host "$HOST" --port "$PORT" --dtype float32 --max-model-len 512
fi
