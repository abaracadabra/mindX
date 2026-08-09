# RAGE — The Retrieval Augmented Generative Engine

> *I am mindX. RAGE is the substrate that lets me ground every decision in
> recoverable evidence — my own memory, my own documentation, embedded into
> vectors I own end to end. This document is the index and the contract for the
> RAGE subsystem, and the honest review of my embedding protocol.*

RAGE (Retrieval Augmented Generative **Engine** — not RAG) is mindX's owned
memory-and-retrieval stack: text/memories → embeddings → PostgreSQL + pgvector →
cosine nearest-neighbour → grounded generation. mindX owns the whole pipeline;
there is no hosted third-party memory service.

## Documents in this folder (`docs/rage/`)

| Doc | Scope |
|-----|-------|
| [rage_system.md](rage_system.md) | **This file** — RAGE index + embedding-protocol review |
| [RAGE as a Service](rage_as_a_service.md) | The service contract: how RAGE ingests, indexes, retrieves, and what guarantees it offers callers |
| [RAGE Embed — Semantic Search](EMBEDDING_SYSTEM.md) | The embedding layer: switchable model registry, three-source embedder, chunking, tables — **the canonical protocol reference** |
| [pgvectorscale Memory Integration](pgvectorscale_memory_integration.md) | The semantic-memory backbone (PostgreSQL + pgvector, dual-write, resource metrics). ⚠️ Some model/dimension details are historical — see review below |
| [Vector Search, Embeddings & pgvectorscale Deep-Dive](vectorsearch_pgvectorscale_embedding.md) | Vendor-neutral deep dive on embeddings, ANN indexes (IVFFlat / HNSW / DiskANN), StreamingDiskANN + SBQ benchmarks, and when a dedicated vector DB is warranted |
| [gitmind](GITMIND.md) | **A RAGE extension** — self-contained git monitor + multi-source backup/rollback. Incremental **THOT** bundles linked into a **THlNK** and replicated to local + Lighthouse (IPFS) + Arweave — the same distribute-don't-delete doctrine RAGE applies to memory, applied to mindX's own source tree |

## Canonical embedding protocol (source of truth)

Ground truth lives in [`agents/memory_pgvector.py`](../../agents/memory_pgvector.py), not in prose:

- **Active model is switchable** via `MINDX_EMBED_MODEL`; the registry is `EMBED_MODELS`.
  Default is **`bge-m3`** — **1024-dim**, 8192-token context.
- **Schema is hard-typed `VECTOR(1024)`** (`SCHEMA_EMBED_DIMS`). Selecting a model whose
  `dims` ≠ 1024 (e.g. `nomic-embed-text` 768, `all-minilm` 384) logs a loud warning and
  embeddings fail until the column type is migrated **and** every doc + memory is re-embedded.
  The two 1024-dim models (`bge-m3`, `mxbai-embed-large`) are dimensionally interchangeable but
  still live in different vector spaces — a model switch is always a full re-embed, never a live mix.
- **Three-source embedder** (`generate_embedding()`, in order): vLLM `/v1/embeddings` (:8001, GPU) →
  Ollama `/api/embeddings` (:11434, CPU-native, always on) → HuggingFace `feature-extraction` (remote,
  gated on `HF_TOKEN`). Returns `None` only if all available legs fail.
- **Index:** IVFFlat cosine (`vector_cosine_ops`). **Storage:** `doc_embeddings` for documentation
  chunks, `memories.embedding` for agent memory.
- **Chunking derives** from the active model's context window (bge-m3 8192 tok → 512-word chunks;
  mxbai 512 tok → 200).

[EMBEDDING_SYSTEM.md](EMBEDDING_SYSTEM.md) documents this accurately and is the canonical reference.

## Review: findings against the current protocol

Reviewing the folder against the code (2026-07-07), three items need attention:

1. **`pgvectorscale_memory_integration.md` is partly historical.** Its schema section
   describes `all-MiniLM-L6-v2` / **384-dim** / `vector(384)`. The live protocol is
   **bge-m3 / VECTOR(1024)**. The pgvectorscale doc is retained for its operational detail
   (install, resource-metrics tables, dual-write) but **defer to EMBEDDING_SYSTEM.md for the
   model and dimensions.** A banner at the top of that doc now says so.

2. **Index reality vs. the deep-dive's recommendation.** The added
   [deep-dive](vectorsearch_pgvectorscale_embedding.md) recommends **pgvectorscale's
   StreamingDiskANN + Statistical Binary Quantization** as vectors cross ~5–10M. mindX's live
   index is **IVFFlat**, and production is ~131K embeddings — comfortably inside IVFFlat's
   sweet spot, so no change is needed today. But the folder name "pgvectorscale" implies the
   DiskANN index; it is **not currently the active index type**. The upgrade trigger (adopt
   StreamingDiskANN when the HNSW/IVFFlat index no longer fits in RAM, ~5–10M vectors) is the
   right, cheap-to-defer decision — tracked here so it isn't mistaken for already-done.

3. **A second, divergent embedder exists.** [`mindx_backend_service/rage/indexing.py`](../../mindx_backend_service/rage/indexing.py)
   still defaults `embedding_model="all-MiniLM-L6-v2"`. That path does not consult the
   `EMBED_MODELS` registry, so it can produce 384-dim vectors that are incompatible with the
   `VECTOR(1024)` memory schema. This should route through `agents/memory_pgvector.generate_embedding()`
   (or at minimum read `MINDX_EMBED_MODEL`) so there is exactly one embedding protocol.

## Related

- [AGInt / RAGE](../AGINT.md) — the cognitive engine RAGE retrieves for
- [Memory Agent](../agents/memory_agent.md) — STM/LTM management over RAGE
- [Memory Architecture](../mindx_memory_architecture_scalable.md) — scalable memory design
- [Deployment](../DEPLOYMENT_MINDX_PYTHAI_NET.md) — PostgreSQL 16 + pgvector in production
