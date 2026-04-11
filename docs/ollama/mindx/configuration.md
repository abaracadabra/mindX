# mindX Ollama Configuration Guide

> Complete configuration reference for Ollama in mindX.

## Environment Variables

### Primary (in `.env` or systemd)

```bash
# Ollama server URL (overrides all other config)
MINDX_LLM__OLLAMA__BASE_URL=http://10.0.0.155:18080

# Cloud API key (store in BANKON vault for production)
OLLAMA_API_KEY=your_key_here

# Logging
MINDX_LOGGING_LEVEL=INFO
```

### Ollama Server Configuration

```bash
# Set in systemd: /etc/systemd/system/ollama.service.d/override.conf
OLLAMA_HOST=0.0.0.0:11434       # Listen on all interfaces
OLLAMA_KEEP_ALIVE=5m             # Default model retention
OLLAMA_CONTEXT_LENGTH=4096       # Default context
OLLAMA_MAX_LOADED_MODELS=1       # 4GB VPS = 1 model at a time
OLLAMA_NUM_PARALLEL=1            # Single request at a time
OLLAMA_MAX_QUEUE=64              # Queue limit
OLLAMA_FLASH_ATTENTION=1         # Reduce memory
OLLAMA_KV_CACHE_TYPE=q8_0        # Halve context memory
```

## Model Registry: models/ollama.yaml

```yaml
provider: ollama
display_name: Ollama (Local GPU)
enabled: true
base_url: http://10.0.0.155:18080
fallback_url: http://localhost:11434

timeout: 120.0
connect_timeout: 10.0
sock_read_timeout: 60.0

rate_limits:
  requests_per_minute: 1000      # Local = high limits
  tokens_per_minute: 10000000

default_model: qwen3:1.7b
keep_alive: 10m

models:
  - name: qwen3:1.7b
    task_scores:
      reasoning: 0.75
      code_generation: 0.78
      simple_chat: 0.88

features:
  streaming: true
  embeddings: true
  function_calling: false  # Update when tool models are available locally
  vision: false            # Update when vision models are available locally
  tool_use: false
```

## LLM Factory Config: data/config/llm_factory_config.json

```json
{
  "default_provider_preference_order": ["gemini", "openai", "anthropic", "ollama"],
  "ollama_settings_for_factory": {
    "base_url_override": null,
    "api_key_override": null
  },
  "rate_limit_profiles": {
    "ollama_local": {"rpm": 1000, "rph": 60000},
    "ollama_cloud": {"rpm": 10, "rph": 150}
  }
}
```

## BANKON Vault (Production)

```bash
# Store cloud API key in vault (not .env)
python manage_credentials.py store ollama_cloud_api_key "KEY"
python manage_credentials.py list
```

## Connection Testing

```bash
# Script test
python scripts/test_ollama_connection.py

# Admin API
curl http://localhost:8000/api/admin/ollama/status
curl http://localhost:8000/api/admin/ollama/test
curl http://localhost:8000/api/admin/ollama/models

# Direct Ollama
curl http://localhost:11434/api/tags
curl http://localhost:11434/api/ps
curl http://localhost:11434/api/version
```

## Models Currently Installed (VPS as of 2026-04-11)

| Model | Size | Purpose |
|-------|------|---------|
| qwen3:1.7b | 1.4GB | Autonomous default |
| qwen3.5:2b | 2.7GB | Newer, may be tight on RAM |
| qwen3:0.6b | 0.5GB | Lightweight tasks |
| mxbai-embed-large | 0.7GB | Embeddings for RAGE |
| nomic-embed-text | 0.3GB | Embeddings (alternative) |
| deepseek-r1:1.5b | ~1.0GB | Reasoning (GPU server) |

## Adding Cloud as Inference Source

To add Ollama cloud alongside local inference:

1. **Store API key**: `python manage_credentials.py store ollama_cloud_api_key "KEY"`
2. **Add to InferenceDiscovery**: Register `https://ollama.com` as a provider
3. **Configure rate limiting**: 10 RPM for cloud (see cloud/rate_limiting.md)
4. **Set routing rules**: Heavy tasks → cloud, light tasks → local
