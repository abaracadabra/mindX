# Ollama Cloud & vLLM Research — 2026-04-10

## Summary

Ollama now has a **free cloud tier**. vLLM is **not viable on this VPS**. The optimal strategy for mindx.pythai.net (4GB RAM, no GPU) is Ollama local for lightweight tasks + Ollama cloud free tier for heavy reasoning.

---

## 1. Ollama Cloud API

Ollama is no longer strictly local-only. A cloud inference service launched with free and paid tiers.

### Free Tier
- Light usage with session limits (reset every 5 hours) and weekly limits (reset every 7 days)
- 1 cloud model at a time
- Cloud models run on NVIDIA GPU hardware with native weights (not quantized)

### Paid Tiers
- **Pro** ($20/mo): 50x more cloud usage, 3 concurrent cloud models
- **Max** ($100/mo): 5x more than Pro, 10 concurrent models

### API Endpoints
- Native: `https://ollama.com/api/chat`
- OpenAI-compatible: `https://ollama.com/v1/chat/completions`
- Authentication: `OLLAMA_API_KEY` via bearer token

### Cloud-Enabled Models
Available at `https://ollama.com/search?c=cloud`:
- qwen3.5, qwen3-coder-next, qwen3-vl
- deepseek-v3.2, gemma4, glm-5
- nemotron-3-super, devstral-small-2
- ministral-3, kimi-k2.5
- Many more — full list at the search URL

### Third-Party Free Option
[OllamaFreeAPI](https://github.com/mfoud444/ollamafreeapi) — community-run public gateway to managed Ollama servers with 50+ models, no API key required.

---

## 2. Local Models for Constrained Hardware (4GB RAM, No GPU)

Models that fit in 4GB RAM with CPU-only inference:

| Model | Params | Disk (Q4) | RAM | Strength |
|-------|--------|-----------|-----|----------|
| `qwen2.5-coder:0.5b` | 0.5B | ~400MB | ~1GB | Coding, completion |
| `qwen2.5-coder:1.5b` | 1.5B | ~1.0GB | ~2GB | Best small coder |
| `deepseek-r1:1.5b` | 1.5B | ~1.0GB | ~2GB | Reasoning, chain-of-thought |
| `qwen3.5:0.8b` | 0.8B | ~600MB | ~1GB | General + reasoning (newest) |
| `qwen3:0.6b` | 0.6B | ~500MB | ~1GB | General (already installed) |
| `qwen3:1.7b` | 1.7B | ~1.4GB | ~2GB | General (already installed, current autonomous model) |
| `smollm2:1.7b` | 1.7B | ~1.0GB | ~2GB | General purpose |
| `smollm2:360m` | 360M | ~250MB | ~500MB | Ultra-light, basic tasks |
| `lfm2.5-thinking:1.2b` | 1.2B | ~800MB | ~1.5GB | Reasoning (hybrid arch) |

### Best Picks for mindX
- **Coding tasks**: `qwen2.5-coder:1.5b`
- **Reasoning/improvement**: `deepseek-r1:1.5b` (already installed)
- **General/current**: `qwen3:1.7b` (already installed, current autonomous model)
- **Ultra-light embedding**: `qwen3:0.6b` (already installed)
- **Heavy tasks**: Ollama cloud free tier → large models remotely

### Currently Installed on VPS
1. `qwen3.5:2b` (2.7GB) — newest, may be tight on RAM
2. `qwen3:1.7b` (1.4GB) — current autonomous model
3. `mxbai-embed-large:latest` (0.7GB) — embeddings
4. `nomic-embed-text:latest` (0.3GB) — embeddings
5. `qwen3:0.6b` (0.5GB) — lightweight

---

## 3. vLLM on CPU

### Verdict: Not Viable for This VPS

vLLM is designed for high-throughput GPU serving with PagedAttention. On CPU:

| Aspect | Ollama (llama.cpp) | vLLM |
|--------|-------------------|------|
| CPU performance | ~80 tok/s | ~55 tok/s |
| RAM efficiency | Excellent (GGUF Q4) | Poor (FP16 default) |
| 4GB RAM viable | Yes (0.5-1.5B models) | No |
| Setup complexity | Simple | Complex |
| GPU performance | Good | Excellent (3-20x faster) |

vLLM requires significantly more RAM than llama.cpp — it uses FP16/BF16 weights by default with no native GGUF quantization on CPU. For a 4GB VPS, vLLM cannot even load its runtime plus a model.

### When vLLM Makes Sense
- GPU servers with 24GB+ VRAM
- Multi-user concurrent serving
- Production throughput optimization
- When the 10.0.0.155 GPU server comes back online

### Free vLLM Cloud
- **AMD Developer Cloud**: Free GPU credits to run vLLM with open-source models
- No general free hosted vLLM API exists

---

## 4. Recommended Strategy for mindX

### Tier 1: Local (always available)
- `qwen3:1.7b` via Ollama localhost:11434 for autonomous improvement cycles
- `qwen3:0.6b` for lightweight tasks (heartbeat, quick classification)
- Embedding models (`mxbai-embed-large`, `nomic-embed-text`) for RAGE/pgvector

### Tier 2: Ollama Cloud (free, rate-limited)
- Register for Ollama cloud free tier
- Use `https://ollama.com` as a secondary inference source
- Route heavy reasoning tasks to cloud models (deepseek-v3.2, qwen3-coder-next)
- Configure in `InferenceDiscovery` as an additional provider

### Tier 3: GPU Server (when available)
- `10.0.0.155:18080` for larger models when the GPU server is online
- Automatic failover already implemented in `ollama_url.py`

### Tier 4: vLLM (future)
- Deploy on the GPU server when it returns
- Not for the VPS — Ollama is strictly better on CPU

### Multi-Model Agent Assignment
Different agents should use different models suited to their tasks:
- **mindXagent** (autonomous loop): `qwen3:1.7b` (general reasoning)
- **BlueprintAgent** (evolution planning): Ollama cloud → `qwen3-coder-next` (coding focus)
- **AuthorAgent** (chapter writing): `qwen3:1.7b` or cloud → `qwen3.5` (prose quality)
- **Heartbeat/health**: `qwen3:0.6b` (ultra-fast, minimal resource)
- **Self-improvement evaluation**: `deepseek-r1:1.5b` (chain-of-thought reasoning)

---

## 5. Implementation Notes

### Current State (2026-04-10)
- Ollama localhost:11434 is the primary inference source (env var `MINDX_LLM__OLLAMA__BASE_URL`)
- `OllamaHandler` and `OllamaAPI` both respect the env var override
- 5 models available locally
- Autonomous loop running with `qwen3:1.7b`, executing real improvements

### To Add Ollama Cloud
1. Sign up at ollama.com, get API key
2. Store in BANKON vault: `python manage_credentials.py store ollama_cloud_api_key "KEY"`
3. Add as inference source in `InferenceDiscovery`
4. Configure `ResourceGovernor` to route heavy tasks to cloud, light tasks to local

### Resource Management
- Run only 1 local model at a time (RAM constraint)
- `ResourceGovernor` should be in `balanced` or `minimal` mode
- Monitor memory via `HealthAuditorTool` — if >80%, downshift to `qwen3:0.6b`

---

*Research conducted 2026-04-10. Sources: ollama.com/pricing, ollama.com/blog/cloud-models, developers.redhat.com (benchmarks), github.com/mfoud444/ollamafreeapi.*
