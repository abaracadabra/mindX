# Vector Search, Embeddings, and a Deep-Dive Evaluation of pgvectorscale

## TL;DR
- **Embeddings** turn text/images/audio into high-dimensional numeric vectors where semantic similarity equals geometric proximity; **vector search** finds nearest neighbors using metrics like cosine/dot-product/L2, accelerated by approximate indexes (IVFFlat = cluster buckets, HNSW = in-memory graph, DiskANN = disk-resident graph). **pgvectorscale** is Timescale/Tiger Data's open-source PostgreSQL extension that adds a DiskANN-style index (StreamingDiskANN) plus Statistical Binary Quantization on top of pgvector, letting Postgres scale to tens–hundreds of millions of vectors cheaply.
- On the vendor's 50M-vector benchmark, Postgres+pgvector+pgvectorscale beat Pinecone's storage-optimized (s1) index by 28× on p95 latency and 16× on throughput at 99% recall, at ~75% lower cost, and beat Qdrant by 11.4× on throughput (471.57 vs 41.47 QPS) — though Qdrant had lower tail latency. A competing Postgres extension, VectorChord, matches or beats pgvectorscale on QPS-at-recall and ingest speed. These headline numbers are vendor-produced and not independently replicated at scale.
- **Recommendation: use PostgreSQL + pgvector (adding pgvectorscale as you cross ~5–10M vectors or when the HNSW index no longer fits in RAM) for the large majority of RAG/semantic-search apps**, because keeping vectors beside relational data in one ACID database eliminates a second system. Reach for a dedicated vector DB (Pinecone, Qdrant, Milvus, Weaviate) at hundreds of millions–billions of vectors, when you need built-in horizontal sharding or GPU indexing, or when vector search *is* the product.

## Key Findings
1. **Embeddings encode meaning as geometry.** An embedding model (BERT, Sentence-BERT, OpenAI text-embedding-3, Cohere, etc.) maps data into a dense vector of hundreds–thousands of dimensions such that semantically similar items sit close together. "teachers design a science experiment" lands near "students test the hypothesis" and far from "kittens are cute."
2. **Similarity search = nearest-neighbor search.** Exact search is O(n·d) and unusable past tens of thousands of rows at high dimensions, so production uses Approximate Nearest Neighbor (ANN) indexes that trade a little recall for orders-of-magnitude speed. Recall = (retrieved∩true)/k, with a typical target ≥0.95, is the key quality metric.
3. **Three dominant index families.** IVFFlat partitions vectors into k-means cells (fast build, low memory, needs periodic rebuilds, degrades as data drifts); HNSW builds a multi-layer navigable graph (95%+ recall out of the box, handles inserts, but 2–5× more RAM and slower builds, and must fit in memory); DiskANN/Vamana builds a single-layer long-edge graph designed to live on SSD, indexing 1B+ vectors on a 64GB machine at 95%+ recall.
4. **pgvectorscale = pgvector + StreamingDiskANN + SBQ + label filtering.** It's an open-source (PostgreSQL License) extension written in Rust/pgrx, complementing (not replacing) pgvector. It reuses pgvector's `vector` type and distance operators and adds a `diskann` index.
5. **StreamingDiskANN** stores the graph on disk (SSD ≪ RAM cost), uses "streaming" post-filtering with no `ef_search` cutoff so filtered queries suffer zero recall loss, and adds label-based filtered search (Filtered-DiskANN).
6. **Statistical Binary Quantization (SBQ)**, developed by Timescale researchers, improves on plain binary quantization by centering the per-dimension cut at the learned mean (not 0.0) and using 2-bit encoding for <~900 dims.
7. **Performance vs Pinecone/Qdrant** favors Postgres in the vendor benchmarks, but a competing Postgres extension (VectorChord/RaBitQ) beats pgvectorscale on QPS-at-recall and index build/insert speed, and Qdrant wins tail latency.
8. **Operational reality:** pgvectorscale is *not* on AWS RDS/Aurora (a major blocker for many teams); it's available self-hosted, on Tiger Cloud, DigitalOcean managed Postgres, and via Docker.

## Details

### Part 1 — First principles

**What embeddings are.** A vector embedding is a numeric representation (an array of floats) produced by a machine-learning model that captures the semantic content of a piece of data. Words, sentences, whole documents, images, and audio can all be embedded. The defining property is that distance in the vector space corresponds to semantic (dis)similarity: similar inputs produce vectors that are close, dissimilar inputs produce vectors that are far apart. Modern text embeddings are contextual (transformer-based), typically 384–3,072 dimensions (e.g., OpenAI text-embedding-3-small = 1,536, text-embedding-3-large = 3,072, many open models = 768). Higher dimensionality can capture more nuance but costs more to store and search.

**How similarity is measured.** The three common metrics:
- **Cosine similarity** — angle between vectors, ignores magnitude; the default for most sentence-embedding models and semantic search.
- **Dot/inner product** — considers both angle and magnitude; equals cosine for normalized vectors; used when the model was trained with dot-product loss (many LLM retrieval models).
- **Euclidean (L2) distance** — straight-line distance, sensitive to magnitude; common in vision embeddings.

The rule of thumb is to match the metric to the one your embedding model was trained with. pgvector/pgvectorscale expose all three (`<=>` cosine, `<#>` inner product, `<->` L2).

**Why you need an index.** Exact nearest-neighbor (brute-force / flat) search computes distance to every stored vector — O(n·d). At 1M+ vectors × 1,536 dims this blows past any real-time latency budget. ANN indexes accept a controllable recall loss for large speedups.

**IVFFlat (Inverted File Flat).** k-means clusters vectors into `lists` cells each with a centroid; a query probes only the nearest `probes` cells. Pros: fast to build, compact, low memory (O(n·d)). Cons: recall depends on cluster quality; new inserts go to the nearest existing cell without rebalancing, so recall drifts and periodic REINDEX is required; must be built on populated data (building on an empty table is the classic pgvector mistake — the k-means centroids get computed against zero meaningful data).

**HNSW (Hierarchical Navigable Small World).** A multi-layer graph — sparse "highway" top layers for long jumps, dense bottom layers for precision. Search descends layer by layer. Pros: 95%+ recall with default params, handles incremental inserts without rebuilds, quality independent of insert order. Cons: 2–5× more memory than IVFFlat (stores neighbor lists at every layer), slower builds; performance collapses if the index doesn't fit in RAM. Key params: `m` (connections/node, 16–64), `ef_construction` (build search width), `ef_search` (query search width).

**DiskANN / Vamana.** From Microsoft Research (Subramanya, Devvrit, Kadekodi, Krishnaswamy & Simhadri, *"DiskANN: Fast Accurate Billion-point Nearest Neighbor Search on a Single Node,"* NeurIPS 2019). A single-layer graph whose construction deliberately creates useful long-range edges (the Vamana algorithm), minimizing hops so the index can live on SSD with few random reads. Classic design: compressed vectors cached in RAM guide beam search; full-precision vectors on SSD are read only to rerank candidates. Per the paper, on the billion-point SIFT1B dataset DiskANN "serves > 5000 queries a second with < 3ms mean latency and 95%+ 1-recall@1 on a 16 core machine" with just 64GB RAM, and "can index and serve 5 − 10x more points per node compared to state-of-the-art graph-based methods such as HNSW and NSG." This is the algorithm pgvectorscale and Pinecone's graph engine are based on.

### Part 2 — What pgvectorscale is and how it relates to pgvector

pgvector (written in C, by Andrew Kane) is the base extension that adds the `vector` data type, distance operators, and the IVFFlat and HNSW indexes to PostgreSQL. pgvectorscale (by Timescale, now "Tiger Data," written in Rust using the pgrx framework) is a complementary extension that depends on pgvector — it reuses pgvector's data type and distance functions and adds a third index method, `diskann`. You enable both: `CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS vectorscale CASCADE;` (the registered name is `vectorscale`; CASCADE auto-installs pgvector). Index creation: `CREATE INDEX ... USING diskann (embedding vector_cosine_ops)`. It supports cosine (`<=>`), L2 (`<->`), and inner product (`<#>`) — a subset of pgvector's full metric set.

pgvectorscale is licensed under the permissive open-source **PostgreSQL License** (100% open source, unlike Pinecone, which is closed/proprietary). It supports PostgreSQL 14–18. Rebrand note: Timescale rebranded to Tiger Data in June 2025 and repositioned from "time-series database" to "fastest PostgreSQL," with TimescaleDB, pgvectorscale, pgai (LLM utilities), and pg_textsearch (BM25) as sibling extensions.

**Three innovations:**
1. **StreamingDiskANN index** — a DiskANN-inspired, disk-resident graph. Because SSDs are far cheaper than RAM, storing the index (and full-precision vectors) on disk dramatically lowers the cost of large corpora. It also adds *streaming filtering*: unlike HNSW, which retrieves a fixed `ef_search` set *before* applying secondary filters (so selective filters can return too few — or zero — results), StreamingDiskANN exposes a `get_next()` that keeps returning the "next closest" item until `LIMIT N` filtered rows are found — post-filtering with zero accuracy loss. (This directly neutralizes the filtering weakness Pinecone had highlighted about pgvector's HNSW.)
2. **Statistical Binary Quantization (SBQ)** — Timescale's improvement on binary quantization. Plain BQ sets each dimension's bit to 1 if value > 0.0 and uses XOR (Hamming) distance. Timescale observed real embeddings' per-dimension means are not ~0, so BQ's cutting planes miss the "action." SBQ (a) sets the cutoff at the learned per-dimension mean, and (b) for <~900 dims uses a 2-bit encoding based on z-score regions (00/01/11) to create more "quadrants." Timescale reports that 2-bit encoding meaningfully improves recall for 768-dim data over 1-bit encoding at high recall levels. SBQ is combined with an exact rerank step over full-precision vectors. (Note: SBQ authorship is confirmed by the pgvectorscale README — "developed by Timescale researchers"; the exact per-dataset recall gains are Timescale's own reported figures.)
3. **Label-based filtered search** — based on Microsoft's Filtered-DiskANN research. You attach a `smallint[]` of labels to each row, include it in the index (`USING diskann (embedding vector_cosine_ops, labels)`), and filter with the `&&` array-overlap operator; filtering happens *during* graph traversal (much faster than post-filter). Limitation: labels must fit in `smallint` (−32768..32767), so it's for categorical filters, not foreign keys.

**Version history / recent state (2025–2026):** Release 0.9.0 (November 2025) added parallel index builds (requires SBQ storage, no labels, ≥65,536 vectors by default) and `CREATE INDEX CONCURRENTLY` support, plus PostgreSQL 18 support — addressing the historical weakness that DiskANN builds were slow. Label-based filtering was added in a 2025 release. Index builds are memory-intensive (raise `maintenance_work_mem`; the neighbor cache uses ~80% of it during parallel builds).

### Part 3 — Performance benchmarks

**vs Pinecone (Timescale, 50M Cohere embeddings, 768-dim):** Per Tiger Data's benchmark, "PostgreSQL with pgvector and pgvectorscale outperformed Pinecone's storage-optimized index (s1) with 28x lower p95 latency and 16x higher query throughput for approximate nearest neighbor queries at 99% recall," at ~75% lower monthly cost self-hosted on AWS EC2 (roughly 28ms p95 at 471 QPS vs Pinecone's ~784ms). It also beat Pinecone's performance-optimized p2 index by 1.4× on p95 latency and 1.5× on throughput at 90% recall. A notable methodological point Timescale raises: Pinecone doesn't let you tune the accuracy/performance trade-off (only s1/p1/p2 pods), whereas Postgres exposes tunable index parameters.

**vs Qdrant (Timescale, same 50M dataset, ANN-Benchmarks fork, April 2025):** At 99% recall both stayed sub-100ms; per Tiger Data, "Postgres with pgvector and pgvectorscale demonstrates significantly higher capacity on a single node, achieving 11.4x more throughput than Qdrant (471.57 queries per second vs. 41.47 QPS)." But Qdrant had better single-query tail latency (p95 36.73ms vs 60.42ms; p99 38.71ms vs 74.60ms) and faster index builds. At 90% recall Postgres hit 1,589 QPS vs Qdrant 360 (4.4×). Interpretation: Postgres wins concurrent throughput on a single node; Qdrant wins per-query latency and build speed.

**vs plain pgvector:** pgvectorscale's advantage shows up when the HNSW index no longer fits in RAM. An independent blogger benchmark measured ~9× lower latency than HNSW when the index didn't fit in memory (a 4GB box with an 8GB HNSW index). Plain pgvector HNSW starts slowing above 5–10M vectors; at 50M×768-dim, HNSW needs ~150GB+ RAM. Below a few million rows, plain HNSW is simpler and performs well — start there.

**vs other Postgres extensions (VectorChord):** VectorChord (RaBitQ/IVF-based, from the pgvecto.rs team) reports consistently higher QPS at >95% recall than both pgvector and pgvectorscale, and much faster ingest — per VectorChord's docs, "VectorChord (1565 Insert/Sec) performs much better than pgvector (246 Insert/Sec) and pgvectorscale (107 Insert/Sec) when inserting data" — plus lower memory and shorter build times. VectorChord's own overview claims it can "query 100M 768-dimensional vectors using just 32GB of memory, achieving 35ms P50 latency with top10 recall@95%." This is the most serious open-source challenger to pgvectorscale inside Postgres. (One nuance from a third-party test: pgvectorscale wins the *first, cold* query, but once data is cached in `shared_buffers`, plain pgvector can outperform it — the disk-resident advantage is largest when the working set exceeds RAM.)

**Caveat on all benchmarks:** The headline Pinecone/Qdrant numbers are vendor-produced by Timescale; no independent third party has replicated them at 50M scale. VectorChord's counter-numbers are likewise produced by its maker. Benchmarks are workload-, hardware-, and config-dependent — treat all as directional.

### Part 4 — Cost

The core cost argument is architectural, not just per-unit: keeping vectors in the Postgres you already run avoids a second system to license, run, secure, and keep in sync. Concrete figures from Timescale's 50M-vector benchmark: ~$835/month self-hosted on AWS EC2 vs Pinecone $3,241/month (s1) or $3,889/month (p2) — a 75–79% saving. Broader 2025–2026 market context: managed vector DBs added price floors (Pinecone a $50/mo minimum from Sept 2025, Weaviate a $25/mo floor), and Pinecone's serverless read-unit/write-unit/storage/egress model can produce surprising bills that scale with usage. Third-party cost modeling puts the self-host-vs-Pinecone break-even around 60–100M queries/month or ~100M vectors. Below a few million vectors on existing Postgres, vector search is nearly free (vectors are just columns); the main added cost is a larger instance if the index must fit in RAM (typically $50–200/mo more). The hidden cost of a dedicated DB is operational, not just financial — two data stores, two credential sets, sync logic, and dual monitoring.

### Part 5 — Scalability limits & operations

- **Single-node ceiling:** PostgreSQL has no built-in horizontal sharding for vector workloads. Vertical scaling (bigger instance, more RAM/SSD) is the main path; horizontal scaling requires app-level sharding or external tooling (Citus, CloudNativePG), which is significant engineering effort. This is the fundamental reason to prefer Milvus/Pinecone at billions of vectors.
- **StreamingDiskANN pushes the single-node ceiling** from pgvector's practical ~5–10M (HNSW-in-RAM) into the tens–hundreds of millions.
- **Ops:** Setup on vanilla Postgres requires building from source with Rust/cargo-pgrx (or using the Timescale Docker image / Tiger Cloud, which ship it preinstalled). Standard Postgres tooling applies (pg_stat_statements, EXPLAIN, consistent/streaming/incremental backups, point-in-time recovery, replication, HA) — a major operational advantage over bespoke systems, which often have weaker backup/recovery stories. macOS x86 builds are unsupported (use ARM Mac, Linux, or Docker).
- **Big availability gap:** pgvectorscale is **not available on Amazon RDS or Aurora** (only plain pgvector is), a frequent blocker; users have publicly filed requests for it. It's available on Tiger Cloud, DigitalOcean managed Postgres, self-hosted, and Docker. On Azure, Microsoft's own `pg_diskann` (PQ-based, same underlying algorithm but different compression) is the managed alternative.

### Part 6 — Real-world production use

Named, metrics-rich, independently verifiable pgvectorscale production case studies are genuinely scarce as of mid-2026 — an important honesty caveat. The verifiable named examples:

- **OpenSauced** ("StarSearch," a "Copilot for git history" RAG system over GitHub events) runs at 100M+ vectors, 1,024-dim, with query latency usually under 300–500ms — but their documented production system uses **pgvector + HNSW**, not StreamingDiskANN. Their Head of Infrastructure, **John McBride**, gave a forward-looking endorsement that SBQ "promises lightning performance for vector search and will be valuable as we scale our vector workload" — an expectation, not a reported production result.
- **Pondhouse Data** (a professional-services firm, CEO **Andreas Nigg**) is the clearest named org actually using pgvectorscale's `diskann` index — for multi-tenant AI apps and an SEO content-recommendation system — chosen for its full metadata filtering ("one of the few vector store solutions out there with full metadata filtering without compromises"). No hard scale/QPS numbers were published.
- **PolyPerception** (CEO **Nicolas Bream**) is a named endorsement but references the older "Timescale Vector," not pgvectorscale specifically.
- The underlying **DiskANN algorithm** (distinct from pgvectorscale) is deployed at billion-scale by Microsoft (Bing, M365), Azure Cosmos DB, Couchbase, and Milvus — evidence the algorithm class is production-proven even if the specific Postgres implementation has thin public references.

Typical use cases across the ecosystem: RAG/knowledge-base Q&A, customer-support chatbots, semantic and product search, recommendation systems, and agentic retrieval — especially where metadata filtering + vector similarity + relational joins are needed in one query.

## Recommendations

**Stage 1 — Default to Postgres + pgvector (HNSW).** If you already run PostgreSQL and have <5–10M vectors, start here. You get single-digit-to-~20ms queries at 95%+ recall, vectors alongside relational data, one backup, one ACID transaction, and no new service. Add pgvectorscale only when you hit a real limit — measure first.

**Stage 2 — Add pgvectorscale (StreamingDiskANN) when any of these are true:**
- Your HNSW index no longer fits comfortably in RAM (roughly 10M+ vectors at 768–1,536 dims), and you'd rather buy SSD than a much larger RAM instance.
- You have selective metadata filters that wreck HNSW recall — use StreamingDiskANN streaming filtering or `smallint[]` label filtering.
- HNSW build time or ingest rate is a bottleneck (use the 0.9.0 parallel builds and `CREATE INDEX CONCURRENTLY`).

Benchmark on *your* data at *your* recall target before committing; also evaluate **VectorChord** as an in-Postgres alternative if ingest speed or QPS-at-high-recall is your priority.

**Stage 3 — Move to a dedicated vector database when:**
- You're at hundreds of millions–billions of vectors and need built-in horizontal sharding → **Milvus** (billion-scale, GPU indexing, mature sharding/partitioning).
- Vector search *is* the product / you want zero-ops managed serverless and have spiky traffic → **Pinecone** (but watch usage-based cost above ~60–100M queries/month).
- You need best-in-class filtered search or the lowest tail latency and want to self-host → **Qdrant** (Rust, no GC pauses).
- You want native hybrid (keyword+vector) search and a managed cloud with good DX → **Weaviate**.

**Thresholds that change the decision:**
- RAM cost of the HNSW index exceeding an SSD-based alternative → adopt pgvectorscale.
- Single-node vertical scaling exhausted (you're sharding by hand) → adopt a horizontally sharded engine.
- RDS/Aurora is a hard requirement → pgvectorscale is off the table (use plain pgvector, VectorChord where offered, or a dedicated DB).
- Azure managed Postgres → consider `pg_diskann`.
- Frequent, high-volume writes with tight ingest SLAs → re-test pgvectorscale build/insert throughput specifically (it's its relative weak point) and compare VectorChord/Qdrant.

## Caveats
- **Vendor benchmarks:** The 28×/16×/11.4× figures are Timescale's own and have not been independently replicated at 50M scale; VectorChord's counter-benchmarks are equally vendor-sourced. Real performance is workload/hardware/config dependent.
- **Case studies:** Public, named, quantified pgvectorscale production deployments are scarce; the strongest named reference (OpenSauced) actually runs pgvector/HNSW in production, with only a forward-looking pgvectorscale endorsement.
- **Managed availability** is the biggest practical adoption blocker (no RDS/Aurora as of mid-2026).
- **Not a distributed system:** Postgres/pgvectorscale scales *up*, not *out*; billions of vectors with automatic sharding remain dedicated-DB territory.
- **Caching effects:** pgvectorscale's disk-resident design wins most when the working set exceeds RAM; when everything fits in cache, plain pgvector HNSW can be faster.
- **The field moves fast:** pgvector, pgvectorscale, VectorChord, and the managed vendors all iterate quickly — re-benchmark at decision time rather than relying on any single published number.
