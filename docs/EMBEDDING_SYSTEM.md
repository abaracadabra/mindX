# RAGE Embed — Semantic Search over Documentation and Memory

## Overview

**RAGE** (Retrieval Augmented Generative Engine) **embed** is the embedding layer of mindX. It bridges LLM inference with pgvector database storage, enabling semantic search over all documentation and agent memories.

mindX embeds all documentation (194 files) and agent memories into pgvector using mxbai-embed-large (1024 dimensions). RAGE facilitates the interaction between LLM and pgvectorscale, providing the semantic retrieval layer for RAG (Retrieval Augmented Generation) queries.

## Architecture

```
Question → Embed (mxbai-embed-large) → pgvector cosine similarity → Top-K chunks → qwen3:0.6b answer
```

### Embedding Pipeline

1. **Model**: mxbai-embed-large via Ollama (1024-dimensional vectors)
2. **Production (VPS)**: Ollama `/api/embeddings` on port 11434 — CPU-native, always running
3. **GPU path**: vLLM `/v1/embeddings` on port 8001 — auto-activates when GPU hardware available
4. **Storage**: PostgreSQL pgvector — `doc_embeddings` and `memories.embedding` columns
5. **Indexing**: IVFFlat cosine similarity index for fast nearest-neighbor search

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

Documents are split into ~500-word chunks. Each chunk is embedded independently. A 10KB doc typically produces 3-5 chunks. This ensures that search results return specific, relevant passages rather than entire documents.

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

| Model | Dimensions | Speed | Use |
|-------|-----------|-------|-----|
| mxbai-embed-large | 1024 | ~100ms/query | Primary — best quality |
| nomic-embed-text | 768 | ~80ms/query | Available as alternative |
| qwen3:0.6b | N/A | ~3-6s/query | Chat/generation (not embedding) |

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
- **7.8GB RAM** — sufficient for mxbai-embed-large
- **Ollama** handles chat (qwen3:0.6b) and embeddings (mxbai-embed-large) on CPU
- **vLLM** can serve embeddings when started (`POST /vllm/serve`)

### Efficiency Strategy

1. **Embeddings**: vLLM on port 8001 (when serving) → Ollama fallback on port 11434
2. **Chat/Generation**: Ollama qwen3:0.6b (always available, CPU-native)
3. **Cloud LLM**: Gemini, Groq, etc. for complex reasoning
4. **Multi-stream**: Parallel queries across providers for critical decisions

## Configuration

```bash
# Environment variables
VLLM_EMBED_URL=http://localhost:8001  # vLLM embedding server
VLLM_PORT=8001                        # vLLM serving port
EMBED_MODEL=mxbai-embed-large         # Default embedding model

# Ollama models (pull if not present)
ollama pull mxbai-embed-large
ollama pull nomic-embed-text
ollama pull qwen3:0.6b
```
