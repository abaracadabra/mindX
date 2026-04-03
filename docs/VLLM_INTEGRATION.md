# vLLM Integration — mindX Inference Engine

vLLM is the primary high-performance inference engine in mindX. It provides PagedAttention-optimized serving for both embeddings and language model inference, with Ollama as the always-on fallback.

## Architecture

```
Request (embedding / chat / completion)
    ↓
InferenceDiscovery (auto-scores available providers)
    ↓ best_provider()
┌─────────────────────────────────────────┐
│  vLLM (primary)          port 8001      │
│  PagedAttention, continuous batching    │
│  OpenAI-compatible API                  │
│  Model: mxbai-embed-large (embeddings)  │
│         qwen3:0.6b / 1.7b (chat)       │
├─────────────────────────────────────────┤
│  Ollama (fallback)       port 11434     │
│  CPU-native, always-on                  │
│  qwen3:0.6b, qwen3:1.7b, mxbai-embed  │
├─────────────────────────────────────────┤
│  Cloud (escalation)      Gemini, Groq   │
│  For complex tasks beyond local models  │
└─────────────────────────────────────────┘
```

## How vLLM Is Used

### 1. Embedding Engine (Primary)

All semantic search in mindX flows through vLLM embeddings first:

- **RAGE semantic search** — doc and memory embeddings via `POST /v1/embeddings`
- **Document indexing** — 500-word chunks embedded into pgvectorscale `doc_embeddings` table
- **Memory embeddings** — agent memories vectorized for semantic retrieval
- **Model**: `mxbai-embed-large` (1024-dimensional vectors)
- **Fallback**: Ollama `/api/embeddings` on port 11434 if vLLM is unavailable

```
memory_pgvector.generate_embedding(text)
    ↓ try vLLM first
    POST http://localhost:8001/v1/embeddings
    ↓ fallback to Ollama
    POST http://localhost:11434/api/embeddings
    ↓ returns
    1024-dim float vector → pgvectorscale
```

### 2. Inference Discovery

`InferenceDiscovery` automatically probes and scores all available inference sources:

- Probes vLLM `/health` endpoint (preferred) with fallback to `/v1/models`
- Scans network for vLLM on common ports (8000, 8001, 8080, 18080)
- Composite scoring: `reliability × speed_factor × recency`
- Returns best available provider via `get_best_provider()`

### 3. VLLMAgent — Lifecycle Management

The `VLLMAgent` (singleton) manages the vLLM server lifecycle:

- **Build**: Can build vLLM from source for CPU-only hardware (AVX2 optimization)
- **Serve**: Start/stop serving models on port 8001
- **Monitor**: Proactive health checks, status persistence to `data/vllm_status.json`
- **Efficiency**: Hardware context reporting (CPU count, RAM, AVX2 support)

### 4. LLM Factory Integration

`LLMFactory` creates vLLM handlers when the provider is available:

```python
# Provider resolution order
handler = LLMFactory.create_llm_handler(
    provider="vllm",     # or auto-detected
    model="qwen3:0.6b",
)
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /vllm/status` | GET | Full efficiency report: version, backend, serving model, hardware, recommendations |
| `POST /vllm/build-cpu` | POST | Build vLLM from source for CPU-only VPS (10-30 min) |
| `POST /vllm/serve?model=MODEL` | POST | Start serving a model on port 8001 |
| `POST /vllm/stop` | POST | Stop serving |
| `GET /vllm/health` | GET | Server health check |

## Configuration

### config/providers/vllm.env
```bash
# vLLM OpenAI-compatible endpoints
VLLM_BASE_URL=http://localhost:8001
VLLM_CHAT_ENDPOINT=/v1/chat/completions
VLLM_EMBED_ENDPOINT=/v1/embeddings
VLLM_MODELS_ENDPOINT=/v1/models
```

### models/vllm.yaml
Recommended models for the 2-core VPS:
- **qwen3:0.6b** — Fast tasks, heartbeat, boardroom votes
- **qwen3:1.7b** — Complex reasoning, autonomous improvement
- **mxbai-embed-large** — 1024-dim embeddings for RAGE semantic search

### scripts/start_vllm_embed.sh
```bash
python -m vllm.entrypoints.openai.api_server \
  --model mxbai-embed-large \
  --port 8001 \
  --dtype float16
```

## vLLM vs Ollama

| Feature | vLLM | Ollama |
|---------|------|--------|
| **Role** | Primary (performance) | Fallback (reliability) |
| **Architecture** | PagedAttention, continuous batching | CPU-native, simple |
| **API** | OpenAI-compatible (`/v1/*`) | Ollama API (`/api/*`) |
| **Embeddings** | `/v1/embeddings` (fast) | `/api/embeddings` (reliable) |
| **Port** | 8001 | 11434 |
| **GPU** | Optimized (tensor parallelism) | CPU-only on VPS |
| **Always-on** | On-demand | 24/7 |

## Current Deployment (mindx.pythai.net)

- **Ollama** runs 24/7 with qwen3:0.6b, qwen3:1.7b, mxbai-embed-large
- **vLLM** available for on-demand performance bursts (build-cpu for VPS)
- **Resource Governor** manages model loading to stay within 7.8GB RAM
- **InferenceDiscovery** auto-selects the best available provider each request

## Key Files

| File | Purpose |
|------|---------|
| `agents/vllm_agent.py` | Lifecycle management (build, serve, stop, monitor) |
| `llm/vllm_handler.py` | OpenAI API client for vLLM |
| `llm/inference_discovery.py` | Auto-discovery, health probing, provider scoring |
| `agents/memory_pgvector.py` | Embedding engine (vLLM primary, Ollama fallback) |
| `llm/llm_factory.py` | Provider creation and caching |
| `config/providers/vllm.env` | Configuration |
| `models/vllm.yaml` | Model recommendations |
| `scripts/start_vllm_embed.sh` | Startup script |
