# API Reference: Model Management

> List, show, create, copy, delete, pull, push models.

## List Models — GET /api/tags

```bash
curl http://localhost:11434/api/tags
curl https://ollama.com/api/tags  # Cloud models (requires OLLAMA_API_KEY)
```

### Response: ListResponse

```json
{
  "models": [
    {
      "name": "qwen3:1.7b",
      "model": "qwen3:1.7b",
      "remote_model": "",
      "remote_host": "",
      "modified_at": "2025-10-03T23:34:03Z",
      "size": 1400000000,
      "digest": "sha256:a2af6cc3eb7f...",
      "details": {
        "format": "gguf",
        "family": "qwen3",
        "families": ["qwen3"],
        "parameter_size": "1.7B",
        "quantization_level": "Q4_K_M"
      }
    }
  ]
}
```

### ModelSummary Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Model identifier |
| `model` | string | Model identifier (same as name) |
| `remote_model` | string | Upstream model name (if remote/cloud) |
| `remote_host` | string | Upstream Ollama host URL (if remote) |
| `modified_at` | string | ISO 8601 last modified |
| `size` | integer | Disk size in bytes |
| `digest` | string | SHA256 digest |
| `details.format` | string | File format (`"gguf"`) |
| `details.family` | string | Primary model family |
| `details.families` | string[] | All applicable families |
| `details.parameter_size` | string | e.g., `"1.7B"`, `"7B"` |
| `details.quantization_level` | string | e.g., `"Q4_K_M"`, `"Q8_0"` |

---

## Show Model Details — POST /api/show

```bash
curl http://localhost:11434/api/show -d '{"model": "qwen3:1.7b"}'

# Verbose (includes full model_info)
curl http://localhost:11434/api/show -d '{"model": "qwen3:1.7b", "verbose": true}'
```

### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | **yes** | Model name |
| `verbose` | boolean | no | Include full metadata |

### Response: ShowResponse

| Field | Type | Description |
|-------|------|-------------|
| `parameters` | string | Model parameter settings as text |
| `license` | string | License text |
| `modified_at` | string | ISO 8601 timestamp |
| `details` | object | format, family, families, parameter_size, quantization_level |
| `template` | string | Prompt template (Go template syntax) |
| `capabilities` | string[] | `["completion", "vision", "tools", "thinking"]` |
| `model_info` | object | Detailed architecture metadata |

### Example Response

```json
{
  "parameters": "temperature 0.7\nnum_ctx 2048",
  "capabilities": ["completion", "vision"],
  "details": {
    "format": "gguf",
    "family": "gemma3",
    "parameter_size": "4.3B",
    "quantization_level": "Q4_K_M"
  },
  "model_info": {
    "general.architecture": "gemma3",
    "general.parameter_count": 4299915632,
    "gemma3.context_length": 131072,
    "gemma3.embedding_length": 2560,
    "gemma3.block_count": 34
  }
}
```

**Key for mindX:** The `capabilities` array tells you exactly what a model supports — use this for dynamic capability detection instead of hardcoded lists.

---

## Create Model — POST /api/create

Create a custom model from an existing one with modified system prompt, parameters, etc.

```bash
curl http://localhost:11434/api/create -d '{
  "model": "mindx-agent",
  "from": "qwen3:1.7b",
  "system": "You are mindX, an autonomous multi-agent orchestration system.",
  "parameters": {"temperature": 0.7, "num_ctx": 4096}
}'
```

### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `model` | string | **yes** | Name for the new model |
| `from` | string | no | Base model to derive from |
| `system` | string | no | System prompt |
| `template` | string | no | Prompt template |
| `license` | string\|string[] | no | License text |
| `parameters` | object | no | Default parameter overrides |
| `messages` | ChatMessage[] | no | Conversation examples |
| `quantize` | string | no | Quantization level: `q4_K_M`, `q8_0`, etc. |
| `stream` | boolean | no | Stream status updates |

### Quantize an Existing Model

```bash
curl http://localhost:11434/api/create -d '{
  "model": "qwen3:1.7b-q8",
  "from": "qwen3:1.7b-instruct-fp16",
  "quantize": "q8_0"
}'
```

---

## Copy Model — POST /api/copy

```bash
curl http://localhost:11434/api/copy -d '{
  "source": "qwen3:1.7b",
  "destination": "qwen3-backup"
}'
```

Useful for creating OpenAI-compatible aliases:
```bash
curl http://localhost:11434/api/copy -d '{
  "source": "qwen3:1.7b",
  "destination": "gpt-3.5-turbo"
}'
```

---

## Delete Model — DELETE /api/delete

```bash
curl -X DELETE http://localhost:11434/api/delete -d '{"model": "old-model"}'
```

---

## Pull Model — POST /api/pull

Download from Ollama registry.

```bash
# Streaming (default) — shows progress
curl http://localhost:11434/api/pull -d '{"model": "qwen3:1.7b"}'

# Non-streaming
curl http://localhost:11434/api/pull -d '{"model": "qwen3:1.7b", "stream": false}'
```

### Status Events (streaming)

```json
{"status": "pulling manifest"}
{"status": "downloading sha256:abc...", "digest": "sha256:abc...", "total": 1400000000, "completed": 700000000}
{"status": "verifying sha256 digest"}
{"status": "writing manifest"}
{"status": "success"}
```

---

## Push Model — POST /api/push

Publish to Ollama registry (requires authentication).

```bash
curl http://localhost:11434/api/push -d '{"model": "username/my-model"}'
```

---

## Blobs

### Check Blob Exists — HEAD /api/blobs/:digest

```bash
curl -I http://localhost:11434/api/blobs/sha256:29fdb92e57cf...
# 200 = exists, 404 = not found
```

### Upload Blob — POST /api/blobs/:digest

```bash
curl -T model.gguf -X POST http://localhost:11434/api/blobs/sha256:29fdb92e57cf...
# 201 = created, 400 = digest mismatch
```

---

## mindX Integration

```python
# Via OllamaHandler (llm/ollama_handler.py)
handler = OllamaHandler(model_name_for_api="qwen3:1.7b")

# List models
models = await handler.list_local_models_api()

# Get model info
info = await handler.get_model_info_api("qwen3:1.7b")

# Pull a model (with progress)
await handler.pull_model_api("deepseek-r1:1.5b")

# Via OllamaChatManager — automatic discovery
await chat_manager.discover_models(force=True)
available = chat_manager.available_models
```
