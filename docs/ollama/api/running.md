# API Reference: Running Models & Version

## List Running Models — GET /api/ps

Shows models currently loaded in memory with their resource usage.

```bash
curl http://localhost:11434/api/ps
```

### Response

```json
{
  "models": [
    {
      "name": "qwen3:1.7b",
      "model": "qwen3:1.7b",
      "size": 2800000000,
      "digest": "sha256:a2af6cc3eb7f...",
      "details": {
        "format": "gguf",
        "family": "qwen3",
        "families": ["qwen3"],
        "parameter_size": "1.7B",
        "quantization_level": "Q4_K_M"
      },
      "expires_at": "2025-10-17T16:47:07Z",
      "size_vram": 2500000000,
      "context_length": 4096
    }
  ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Model name |
| `size` | integer | Total memory used (bytes) |
| `digest` | string | SHA256 digest |
| `details` | object | Format, family, parameter_size, quantization |
| `expires_at` | string | When the model will be unloaded (ISO 8601) |
| `size_vram` | integer | VRAM usage in bytes |
| `context_length` | integer | Active context length |

### mindX Usage

Monitor which models are loaded to prevent OOM on 4GB VPS:

```python
import aiohttp

async def get_running_models(base_url="http://localhost:11434"):
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{base_url}/api/ps") as resp:
            data = await resp.json()
            return data.get("models", [])

# Check if we need to unload before loading a new model
running = await get_running_models()
total_mem = sum(m["size"] for m in running)
if total_mem > 3_000_000_000:  # 3GB threshold on 4GB VPS
    # Unload least recently used
    for model in running:
        await unload_model(model["name"])
```

---

## Version — GET /api/version

```bash
curl http://localhost:11434/api/version
```

Response:
```json
{"version": "0.12.6"}
```

---

## CLI Equivalents

```bash
# List running models
ollama ps

# Stop/unload a model
ollama stop qwen3:1.7b
```

### Output of `ollama ps`:

```
NAME          ID            SIZE    PROCESSOR   UNTIL
qwen3:1.7b   abc123def456  1.4 GB  100% CPU    4 minutes from now
```

The `PROCESSOR` column shows:
- `100% GPU` — entirely on GPU
- `100% CPU` — entirely in system memory
- `48%/52% CPU/GPU` — split across both
