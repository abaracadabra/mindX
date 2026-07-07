# RAGE Embed — Semantic Search over Documentation and Memory

## Overview

**RAGE** (Retrieval Augmented Generative Engine) **embed** is the embedding layer of mindX. It bridges LLM inference with pgvector database storage, enabling semantic search over all documentation and agent memories.

mindX embeds all documentation and agent memories into pgvector. The **active embed model is
switchable** via a registry (see below); the **default is `bge-m3`** (1024-dim, 8192-token context).
RAGE provides the semantic retrieval layer for RAG (Retrieval Augmented Generation) queries.

## Architecture

```
Question → Embed (active model, default bge-m3) → pgvector cosine similarity → Top-K chunks → qwen3:0.6b answer
```

### Switchable embed models (registry)

The embed backend is **not hardcoded** — `agents/memory_pgvector.py` defines an `EMBED_MODELS` registry so
the store can be optimized/adapted to different data and types. Select the active model with the env var
**`MINDX_EMBED_MODEL`** (default `bge-m3`); truncation (`_EMBED_MAX_CHARS`) and default chunk size
(`DEFAULT_CHUNK_WORDS`) **derive automatically** from the active model's context window.

| Model | Dims | Context | Default chunk | In-schema? |
|-------|------|---------|---------------|------------|
| **bge-m3** (default) | 1024 | 8192 tok | 512 words | ✅ drop-in for `VECTOR(1024)` |
| mxbai-embed-large | 1024 | 512 tok | 200 words | ✅ interchangeable (re-embed to switch) |
| nomic-embed-text | 768 | 8192 tok | 512 words | ⚠️ needs `VECTOR(768)` migration + re-embed |
| all-minilm | 384 | 256 tok | 200 words | ⚠️ needs `VECTOR(384)` migration + re-embed |

**Dimension guard:** the pgvector columns are hard-typed `VECTOR(1024)` (`SCHEMA_EMBED_DIMS`). Selecting a
model whose `dims` ≠ 1024 logs a loud warning and embeddings fail until you migrate the column type **and**
re-embed every doc + memory (mixed-dimension / mixed-model vectors break cosine search). The two 1024-dim
models (bge-m3, mxbai) are dimensionally interchangeable but still occupy **different vector spaces** — a
model switch always requires a full re-embed, never a live mix.

### Embedding Pipeline

1. **Model**: active from the registry — default **bge-m3** (1024-dim, 8192-token window)
2. **Three sources (use every source to advantage)** — `generate_embedding()` tries in order:
   1. **vLLM** `/v1/embeddings` on :8001 — fast/batched, only when a GPU node serves it (`POST /vllm/serve`)
   2. **Ollama** `/api/embeddings` on :11434 — CPU-native, always running; the effective embedder on CPU-only nodes
   3. **HuggingFace Inference** `feature-extraction` (remote) — gated on `HF_TOKEN`; works with **no local
      model pulled and no GPU**. Endpoint `…/hf-inference/models/{repo}/pipeline/feature-extraction`
      (repo = the registry's `vllm_id`, e.g. `BAAI/bge-m3`). Returns None only if **all** available legs fail.
3. **Storage**: PostgreSQL pgvector — `doc_embeddings` and `memories.embedding` columns
4. **Indexing**: IVFFlat cosine similarity index for fast nearest-neighbor search

### Tables

```sql
-- Document chunks with embeddings
doc_embeddings (
    doc_name VARCHAR(256),
    chunk_idx INTEGER,
    text_content TEXT,
    embedding vector(1024),
    UNIQUE(doc_name, chunk_idx)
)

-- Memory embeddings (column on existing memories table)
memories.embedding vector(1024)
```

### Chunking Strategy

Chunk size is **derived from the active model** (`DEFAULT_CHUNK_WORDS` in `agents/memory_pgvector.py`):
long-context models take big chunks, short-context ones stay small. With the default **bge-m3** it's
**512-word chunks** (8192-token window has ample room); on **mxbai** it auto-drops to **200 words** (512-token
window). Each chunk is embedded independently so search returns specific passages, not whole documents.

### Input truncation (the single choke point)

Every embedding input — doc chunk **and** memory — is truncated to **`_EMBED_MAX_CHARS`** inside
`generate_embedding()` before any source is called. The cap is **derived from the active model** (override
with `MINDX_EMBED_MAX_CHARS`): **bge-m3 → 4000 chars** (~1000 tokens, holds a 512-word chunk inside the 8192
window); **mxbai → 1400 chars** (~350 tokens, under its 512 window). This is the single guarantee that an
input can't overflow the model window — overflow used to return `None`, leaving the row perpetually
unembedded and retried every cycle → sustained CPU churn. **Consequence:** text beyond the cap in a single
chunk/memory is not embedded — chunk long
content upstream rather than relying on a single large embed call.

## API Endpoints

### RAGE Embed Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/rage/embed?query=...` | GET | Semantic search over docs + memories |
| `/api/rage/embed/stats` | GET | Embedding counts + action efficiency |
| `/actions/export` | GET | Export all actions as JSON |
| `/actions/export/csv` | GET | Export actions as CSV download |
| `/actions/efficiency` | GET | Action pipeline efficiency metrics |
| `/diagnostics/export` | GET | Full diagnostics snapshot download |

### Chat Endpoints

### POST /chat/docs — RAG Q&A

Ask a question about mindX documentation. Returns an answer generated from relevant doc chunks.

```bash
curl -X POST "https://mindx.pythai.net/chat/docs?question=What+is+the+BDI+agent"
```

Response:
```json
{
  "question": "What is the BDI agent",
  "answer": "The BDI (Belief-Desire-Intention) agent is the core reasoning engine...",
  "sources": [
    {"doc": "AGINT", "similarity": 0.6226},
    {"doc": "AGENTS", "similarity": 0.6207}
  ]
}
```

### GET /chat/docs/stats — Embedding Statistics

```bash
curl https://mindx.pythai.net/chat/docs/stats
```

Response:
```json
{"docs": 95, "memories": 558}
```

## Embedding Models

See **[Switchable embed models (registry)](#switchable-embed-models-registry)** above — the `EMBED_MODELS`
registry in `agents/memory_pgvector.py` is the single source of truth (models, dims, context windows,
default chunk sizes, in-schema status). Select with `MINDX_EMBED_MODEL`. Default: **bge-m3**.

**Switching models always requires a full re-embed** (different models = different vector spaces, even at
the same dimension), and switching to a non-1024-dim model additionally requires a `VECTOR(n)` schema
migration. The dimension guard warns on mismatch.

## Batch Embedding

```bash
# Embed all docs and memories
python scripts/embed_docs.py
```

This walks `docs/*.md`, chunks each, embeds via mxbai-embed-large, and stores in pgvector. Also embeds all memories without embeddings. Takes ~5 minutes on CPU.

## Auto-Embedding

New memories are auto-embedded on save via `MemoryAgent.save_timestamped_memory()`. New docs are picked up every 6 hours by the periodic re-embedding task.

## File Paths

- Embedding engine: `agents/memory_pgvector.py` (generate_embedding, embed_and_store_doc, semantic_search_docs)
- Batch script: `scripts/embed_docs.py`
- vLLM handler: `llm/vllm_handler.py` (generate_embeddings method)
- vLLM startup: `scripts/start_vllm_embed.sh`
- RAG endpoint: `mindx_backend_service/main_service.py` (/chat/docs)

## vLLMAgent

`agents/vllm_agent.py` manages the vLLM lifecycle for mindX:

| Endpoint | Purpose |
|----------|---------|
| `GET /vllm/status` | Installation status, hardware, recommendations |
| `POST /vllm/build-cpu` | Build vLLM from source for CPU (AVX2) |
| `POST /vllm/serve` | Start serving a model on port 8001 |
| `POST /vllm/stop` | Stop serving |
| `GET /vllm/health` | Server health check |

### Current VPS Status

- **vLLM 0.19.0** installed, backend=ready
- **AMD EPYC 7543P** (2 vCPUs, AVX2 supported)
- **7.8GB RAM** — sufficient for bge-m3 (~1.2GB) on CPU
- **Ollama** handles chat (qwen3:0.6b) and embeddings (bge-m3, the active model) on CPU
- **vLLM** can serve embeddings when started (`POST /vllm/serve`)

### Efficiency Strategy

1. **Embeddings**: vLLM :8001 (GPU, when serving) → Ollama :11434 (CPU) → HuggingFace Inference (remote, `HF_TOKEN`)
2. **Chat/Generation**: Ollama qwen3:0.6b (always available, CPU-native)
3. **Cloud LLM**: Gemini, Groq, etc. for complex reasoning
4. **Multi-stream**: Parallel queries across providers for critical decisions

## Configuration

```bash
# --- Embedding model selection (registry in agents/memory_pgvector.py) ---
MINDX_EMBED_MODEL=bge-m3               # active model; default bge-m3 (also: mxbai-embed-large, …)
MINDX_EMBED_MAX_CHARS=4000             # optional override; else derived from the active model

# --- Sources (tried in order; each optional) ---
VLLM_EMBED_URL=http://localhost:8001   # 1) vLLM embedding server (GPU)
HF_TOKEN=hf_xxx                        # 3) enables the HuggingFace Inference fallback (feature-extraction)
                                       #    also read from HUGGINGFACE_TOKEN / HUGGINGFACEHUB_API_TOKEN
HF_EMBED_URL=https://router.huggingface.co/hf-inference/models  # optional override

# --- Ollama models (2, CPU fallback — pull the active model if not present) ---
ollama pull bge-m3                     # default embedder (1024-dim, 8192-token)
ollama pull qwen3:0.6b                 # chat/generation
# ollama pull mxbai-embed-large        # only if MINDX_EMBED_MODEL=mxbai-embed-large
```

> **HF_TOKEN is not in `.env` by default** — the HuggingFace leg stays dormant until you add a token
> (`.env` or export). With it set, embeddings work with **no local model pulled and no GPU** — useful for a
> fresh node or while `ollama pull` is still downloading.
