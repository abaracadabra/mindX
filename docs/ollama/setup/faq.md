# FAQ & Troubleshooting

## Configuration

### Context Window Size

Default is 4096 tokens. Override per request or globally:

```bash
# Global (env var)
OLLAMA_CONTEXT_LENGTH=8192 ollama serve

# Per request (API)
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "...",
  "options": {"num_ctx": 8192}
}'

# Interactive session
/set parameter num_ctx 4096
```

### Keep Models Loaded

Default: 5 minutes after last request. Control via:

```bash
# Keep forever
curl http://localhost:11434/api/generate -d '{"model": "qwen3:1.7b", "keep_alive": -1}'

# Unload immediately
curl http://localhost:11434/api/generate -d '{"model": "qwen3:1.7b", "keep_alive": 0}'
ollama stop qwen3:1.7b

# Global default
OLLAMA_KEEP_ALIVE=10m ollama serve
```

### Preload Models

Send empty request to load model into memory:

```bash
curl http://localhost:11434/api/generate -d '{"model": "qwen3:1.7b"}'
curl http://localhost:11434/api/chat -d '{"model": "qwen3:1.7b"}'
ollama run qwen3:1.7b ""
```

### GPU vs CPU Status

```bash
ollama ps
# NAME          SIZE    PROCESSOR   UNTIL
# qwen3:1.7b   1.4 GB  100% CPU    4 minutes from now
```

### Expose on Network

```bash
OLLAMA_HOST=0.0.0.0:11434 ollama serve
```

### Allow CORS Origins

```bash
OLLAMA_ORIGINS=chrome-extension://*,http://localhost:3000 ollama serve
```

### Model Storage Location

| OS | Default Path |
|----|-------------|
| macOS | `~/.ollama/models` |
| Linux | `/usr/share/ollama/.ollama/models` |
| Windows | `C:\Users\%username%\.ollama\models` |

Override: `OLLAMA_MODELS=/custom/path`

### Disable Cloud

```json
// ~/.ollama/server.json
{"disable_ollama_cloud": true}
```

Or: `OLLAMA_NO_CLOUD=1`

## Server Environment Variables

Set via `systemctl edit ollama.service` on Linux:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="OLLAMA_MODELS=/data/models"
Environment="OLLAMA_KEEP_ALIVE=10m"
Environment="OLLAMA_CONTEXT_LENGTH=8192"
Environment="OLLAMA_FLASH_ATTENTION=1"
Environment="OLLAMA_KV_CACHE_TYPE=q8_0"
Environment="OLLAMA_MAX_LOADED_MODELS=3"
Environment="OLLAMA_NUM_PARALLEL=1"
Environment="OLLAMA_MAX_QUEUE=512"
```

Then: `systemctl daemon-reload && systemctl restart ollama`

## Concurrency

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_MAX_LOADED_MODELS` | 3 * GPUs (or 3) | Max concurrent models |
| `OLLAMA_NUM_PARALLEL` | 1 | Parallel requests per model |
| `OLLAMA_MAX_QUEUE` | 512 | Queue size before 503 |

RAM scales by: `OLLAMA_NUM_PARALLEL * OLLAMA_CONTEXT_LENGTH`

## Performance Tuning

### Flash Attention

Reduces memory with large contexts:

```bash
OLLAMA_FLASH_ATTENTION=1 ollama serve
```

### KV Cache Quantization

Requires Flash Attention enabled:

| Type | Memory | Quality |
|------|--------|---------|
| `f16` (default) | 100% | Highest |
| `q8_0` | ~50% | Minimal loss (recommended) |
| `q4_0` | ~25% | Noticeable at large context |

```bash
OLLAMA_KV_CACHE_TYPE=q8_0 ollama serve
```

### GPU Selection

```bash
# NVIDIA — select specific GPUs
CUDA_VISIBLE_DEVICES=0,1 ollama serve

# AMD
ROCR_VISIBLE_DEVICES=0 ollama serve

# Force CPU only
CUDA_VISIBLE_DEVICES=-1 ollama serve
```

## Troubleshooting

### Finding Logs

```bash
# Linux (systemd)
journalctl -u ollama --no-pager --follow

# macOS
cat ~/.ollama/logs/server.log

# Docker
docker logs <container-name>
```

### Linux GPU Not Detected After Suspend

```bash
sudo rmmod nvidia_uvm && sudo modprobe nvidia_uvm
```

### AMD Driver Version Mismatch

If GPU discovery times out (30s), upgrade to ROCm v7:

```bash
# Install amdgpu-install from AMD docs, then:
sudo amdgpu-install
sudo reboot
```

### Override LLM Library

```bash
OLLAMA_LLM_LIBRARY="cpu_avx2" ollama serve
# Options: cpu, cpu_avx, cpu_avx2, cuda_v11, rocm_v5, rocm_v6
```

### 503 Server Overloaded

Increase queue: `OLLAMA_MAX_QUEUE=1024`

### Upgrade Ollama

```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Specific version
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION=0.5.7 sh
```

## mindX Production Notes (from deployment at mindx.pythai.net)

### VPS Constraints (4GB RAM, No GPU)

- Run only **1 model at a time** — `OLLAMA_MAX_LOADED_MODELS=1`
- Use `qwen3:1.7b` as default — fits in ~2GB RAM
- Set `OLLAMA_KV_CACHE_TYPE=q8_0` to halve context memory
- Monitor with `ResourceGovernor` — downshift to `qwen3:0.6b` at >80% RAM
- Set `OLLAMA_KEEP_ALIVE=5m` — free memory between cycles
- The `keep_alive: 0` trick unloads immediately after each request for RAM-critical periods

### Dual-URL Failover (from ollama_url.py)

```
Primary:  MINDX_LLM__OLLAMA__BASE_URL (10.0.0.155:18080 when GPU available)
Fallback: localhost:11434 (always available on VPS)

Timeout:  120s total, 10s connect, 60s sock_read
```

### Health Check Endpoint

```bash
# Simple ping
curl http://localhost:11434/api/tags

# mindX admin route
curl http://localhost:8000/api/admin/ollama/status
```
