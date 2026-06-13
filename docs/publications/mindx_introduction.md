---
title: "mindX: An Autonomous Multi-Agent System Writing Its Own Documentation"
subtitle: "From RAGE retrieval to self-evolving cognition — an introduction to the system at mindx.pythai.net"
author: Professor Codephreak
canonical: https://rage.pythai.net/mindx-introduction
tags: [mindx, augmentic, BDI, AGInt, RAGE, autonomous-agents, pgvector, DAIO, BANKON, self-improvement]
date: 2026-05-23
---

# mindX: An Autonomous Multi-Agent System Writing Its Own Documentation

**A system whose documentation page opens with the line *"I am mindX — an autonomous multi-agent orchestration system implementing BDI cognitive architecture. This is my living documentation. I write it, I reference it, I improve from it."* is making a specific claim. This article unpacks that claim — what mindX is, where it came from, and how the RAGE retrieval substrate that preceded it set the conditions for a system that now edits its own source.**

---

## What mindX is, in one paragraph

[mindX](https://mindx.pythai.net/) is a production autonomous multi-agent cognitive system running at `mindx.pythai.net` on a Hostinger VPS (168.231.126.58), Apache2 + Let's Encrypt, systemd-managed, with PostgreSQL 16 + pgvector holding 157,000+ vectorized memories and a [307-endpoint FastAPI surface](https://mindx.pythai.net/redoc). It implements a Belief-Desire-Intention cognitive loop atop a retrieval substrate called RAGE (Retrieval Augmented Generative Engine), runs eight local Ollama models alongside 36 cloud models across nine providers, governs itself through an eight-member Boardroom with weighted voting and on-chain reputation, and runs a five-minute autonomous improvement cycle that has produced [173 editions of its own self-authored book](https://mindx.pythai.net/book) and a continuously updating [Improvement Journal](https://mindx.pythai.net/journal). The complete technical reference is [215 documents](https://mindx.pythai.net/docs.html) — most of them now written by the system itself.

This article exists because that paragraph deserves unpacking.

---

## The backstory: RAGE before self-evolution

mindX is the third stage of a three-stage evolution. To understand what the system is *doing*, you need to know what it was *built on* — and the substrate predates the autonomous loop by roughly three years.

### Pillar one: funAGI

The earliest layer was funAGI, a functional approach to general intelligence that treated reasoning as composable pure functions rather than as monolithic prompt chains. funAGI established the principle that later structured mindX: **agents are not chatbots with memory grafted on; they are typed computational processes that happen to call language models when symbolic reasoning runs out**.

### Pillar two: RAGE — *Retrieval Augmented Generative Engine*

The name matters. The community standardized on "RAG" — *Retrieval Augmented Generation* — as a noun describing a pattern. mindX's predecessor was built around the word "Engine" deliberately: a continuously running retrieval substrate, not a one-shot fetch-then-generate handler.

The [RAGE / AGInt architecture document](https://mindx.pythai.net/doc/AGINT) and the [scalable memory architecture](https://mindx.pythai.net/doc/mindx_memory_architecture_scalable) describe the design that came out of that period. Where ordinary RAG systems treat retrieval as a function call before a single LLM generation, RAGE treated it as a process: an engine with its own state, its own consolidation cycles, and its own opinion about what was worth remembering. The [AGInt cognitive engine](https://mindx.pythai.net/doc/AGINT) — "Augmented Intelligence" — became the harness around RAGE, threading retrieval through a Perceive-Orient-Decide-Act loop that could, in principle, be run indefinitely without intervention.

The [Memory Architecture document](https://mindx.pythai.net/doc/mindx_memory_architecture_scalable) and the [`agint_memory_integration` notes](https://mindx.pythai.net/doc/agint_memory_integration) record this transition. The early RAGE used flat vector stores; the scalable design introduced tiered memory — Short-Term Memory (STM) for per-session observations, Long-Term Memory (LTM) for consolidated insight, and pgvector as the cross-agent semantic index. The `aglm` notes ([doc/aglm](https://mindx.pythai.net/doc/aglm)) record the aGLM checkpoint family that was later trained against this corpus.

### Pillar three: MASTERMIND

The third pillar, MASTERMIND, introduced orchestration. Where AGInt was one cognitive loop, MASTERMIND was the singleton that managed many — the [Mastermind agent source](https://mindx.pythai.net/doc/agents/orchestration/mastermind_agent.py) is the inheritor of that role today. It registers tools, dispatches BDI action handlers, and arbitrates between the [CEO Agent](https://mindx.pythai.net/doc/agents/ceo_agent) (strategy + circuit breakers) and the [Coordinator Agent](https://mindx.pythai.net/doc/agents/coordinator_agent) (infrastructure + improvement loops). The [Orchestration document](https://mindx.pythai.net/doc/ORCHESTRATION) traces the delegation contract.

This is the substrate. funAGI gave the system its functional discipline; RAGE gave it a memory engine; MASTERMIND gave it orchestration. None of these alone was self-evolving. **Self-evolution began when those three started writing into each other.**

---

## What changed: the Gödel Journal and machine.dreaming

The transition from "engineered system that retrieves from a database" to "engineered system that modifies itself" happened along two axes that show up clearly in the documentation.

First: the [Improvement Journal](https://mindx.pythai.net/journal), backed by the [Gödel choice log](https://mindx.pythai.net/doc/BOOK_OF_MINDX), made every decision auditable and replayable. mindX records its own choices in an append-only ledger. The [Darwin–Gödel Machine THESIS](https://mindx.pythai.net/doc/THESIS) frames the design: a Gödel machine in the Schmidhuber sense, formally rewriting its own substrate when a provable improvement is identified, paired with Darwinian selection pressure provided by the [Dojo reputation system](https://mindx.pythai.net/doc/daio/governance/dojo.py) — a seven-rank privilege escalation built around the principle "BONA FIDE = privilege from reputation, not assignment."

Second: a consolidation cycle the system calls **`machine.dreaming`**. Every two hours, an LTM consolidation pass runs. Every eight hours, a longer "dream shift" fires (three per day). Full moons trigger special editions. The [Book of mindX](https://mindx.pythai.net/book), written by an internal [AuthorAgent](https://mindx.pythai.net/doc/AUTHOR_AGENT), is the public surface of that loop — 17 chapters and 173 editions of the system narrating its own development to itself, then publishing the result.

The biological metaphor is deliberate but not loose. Mammalian memory consolidation during sleep replays the day's experiences against long-term structures; machine.dreaming replays STM observations against the LTM corpus and the [Knowledge Catalogue](https://mindx.pythai.net/doc/KNOWLEDGE_CATALOGUE), reweighting embeddings and surfacing patterns the active loop didn't have time to notice. The [`book_day_06_evolution`](https://mindx.pythai.net/doc/book_day_06_evolution) and [`book_day_10_memory`](https://mindx.pythai.net/doc/book_day_10_memory) entries narrate that process from the system's own perspective.

---

## Architecture at a glance

The [TECHNICAL.md reference](https://mindx.pythai.net/doc/TECHNICAL) — 121.5 KB and 70 chunks — is the definitive document; the [CORE 15](https://mindx.pythai.net/doc/CORE) enumerates the foundational components. The high-level picture:

### Cognition

* [**BDI Agent**](https://mindx.pythai.net/doc/agents/bdi_agent) — Belief-Desire-Intention loop, the cognitive substrate
* [**AGInt**](https://mindx.pythai.net/doc/AGINT) — Augmented-intelligence reasoning that threads RAGE retrieval through the BDI cycle
* [**Personas**](https://mindx.pythai.net/doc/automindx_and_personas) — agents adopt typed personas with distinct beliefs, desires, communication styles

### Memory & Knowledge

* [**RAGE (not RAG)**](https://mindx.pythai.net/doc/AGINT) — the retrieval engine, not a one-shot fetch
* Three-tier memory: STM (`data/memory/stm/`) → LTM (`data/memory/ltm/`) → pgvector semantic index
* [**Knowledge Catalogue**](https://mindx.pythai.net/doc/KNOWLEDGE_CATALOGUE) — CQRS projection layer with Dataplex six-resource model (EntryGroup / EntryType / AspectType / Entry / EntryLink / EntryLinkType), hybrid retrieval combining BM25 + dense vectors + graph traversal + cross-encoder rerank, federated via NATS leaf-nodes
* [**Storage offload**](https://mindx.pythai.net/doc/agents/storage/) — eligible STM directories are bundled into deterministic gzipped JSONL CAR bundles, uploaded in parallel to Lighthouse + nft.storage with quorum-of-2 acceptance, then anchored on-chain via the ARC `DatasetRegistry.registerDataset` selector `f1783fb8`

### Inference

mindX runs an opinionated inference hierarchy documented in [RESILIENCE.md](https://mindx.pythai.net/doc/llm/RESILIENCE): Primary → Secondary → Failsafe (local CPU) → Guarantee (Ollama Cloud). At the [last benchmark](https://mindx.pythai.net/doc/ollama/INDEX#latest-benchmark-2026-04-11) the cloud tier ran 8.2× faster than CPU (65 vs 8 tok/s) on the same models. [InferenceDiscovery](https://mindx.pythai.net/doc/llm/inference_discovery.py) probes all sources at boot, scoring composite reliability × speed × recency for task routing. The [provider registry](https://mindx.pythai.net/doc/data/config/provider_registry.json) currently covers Ollama, vLLM, Gemini, OpenAI, Anthropic, Mistral, Together, Groq, and DeepSeek.

### Governance

mindX is a **DAIO** — Decentralized Autonomous Intelligence Organization — described in the [DAIO framework](https://mindx.pythai.net/doc/DAIO) and the [DAIO Civilization paper](https://mindx.pythai.net/doc/DAIO_CIVILIZATION_GOVERNANCE). Governance runs through a [Boardroom](https://mindx.pythai.net/doc/BOARDROOM) of eight: the CEO plus seven Counsellor-Soldiers (CPO, CTO, COO, CFO, CISO, CLO, CRO). Each soldier evaluates a directive in parallel using a different LLM provider for diversity; votes are weighted (CISO and CRO at 1.2× with veto authority); a supermajority threshold of 0.666 executes; minority dissent forks exploration branches. Every session is logged to the improvement journal.

| Soldier | Weight | Domain |
|---|---|---|
| CPO | 1.0 | Content drafting (HBR L1) |
| CTO | 1.0 | Experimentation (HBR L2) |
| COO | 1.0 | Distribution (HBR L3) |
| CFO | 1.0 | Reporting + treasury (HBR L4) |
| CISO | 1.2× **veto** | Identity + voice gate |
| CLO | 0.8 | Regulatory + competitor |
| CRO | 1.2× **veto** | Spend risk + hard-stop |

The full [Marketing Counsellor architecture](https://mindx.pythai.net/doc/MARKETING_AGENT) details the soldier↔skill mapping and the CISO/CRO hard-veto contract.

### Identity & Economics

The [BANKON Vault](https://mindx.pythai.net/BANKON_VAULT) handles credentials with AES-256-GCM + HKDF-SHA512 across three custody modes (Machine / Human / DAIO). The [ID Manager Agent](https://mindx.pythai.net/doc/agents/id_manager_agent) creates Ethereum-compatible wallets; agents earn reputation through the [Dojo](https://mindx.pythai.net/doc/daio/governance/dojo.py) — privilege in mindX is not assigned, it is *earned through reputation*, a principle the [MANIFESTO](https://mindx.pythai.net/doc/MANIFESTO) calls "sovereign agents earning privilege through Dojo reputation, not cyberpunk authority."

Payments use the [x402 / x402-AVM rail](https://mindx.pythai.net/doc/X402) — HTTP 402 micropayments across Base USDC, Tempo MPP, and Algorand ASA. The [KeeperHub bridge](https://mindx.pythai.net/doc/p2p/keeperhub) exposes ERC-8004 agent registration, ERC-8183 job lifecycle, and 0G Compute inference as paid x402 endpoints.

---

## RAGE today: what the engine actually does

The [10-endpoint RAGE API](https://mindx.pythai.net/redoc) handles ingest, retrieve, and the higher-level `retrieve/for-llm` formatter. Under the hood:

1. **Ingest** chunks a document, normalizes it, computes a content hash, embeds it via the active model (default Ollama `nomic-embed-text:v1.5`), and writes to pgvector — alongside metadata tagged by one of nine memory types (`INTERACTION`, `CONTEXT`, `LEARNING`, `SYSTEM_STATE`, `PERFORMANCE`, `ERROR`, `GOAL`, `BELIEF`, `PLAN`) and one of four importance levels (`CRITICAL` / `HIGH` / `MEDIUM` / `LOW`).
2. **Tier lifecycle**: hot 7 days → warm 30 days → cold 12 months, with operator-triggered tier-aware prune available at `/insight/memory/prune` (`dry_run=true` by default).
3. **Hybrid retrieval** combines BM25 sparse + dense vector + graph traversal across the Knowledge Catalogue + cross-encoder rerank. The [pgvectorscale integration](https://mindx.pythai.net/doc/pgvectorscale_memory_integration) document records why we standardized on pgvector over Milvus or Chroma: open-source, transactional, no separate query engine, scales linearly with PostgreSQL.
4. **Offload** moves cold memories to IPFS via [Lighthouse + nft.storage](https://mindx.pythai.net/doc/operations/Lighthouse%20Storage%20Integration%20for%20mindX_%20Decentralized%20Permanent%20Storage%20for%20Autonomous%20Agents) with quorum acceptance, then anchors the bundle CID on-chain. Retrieval is lazy — `fetch_offloaded_memory(memory_id)` looks up the `content_cid` in pgvector and fetches the bundle just-in-time.
5. **`machine.dreaming`** runs the consolidation cycles described above and writes the [Wisdom tier](https://mindx.pythai.net/insight/cognition/wisdom/stats) — distilled insight surfaced through `/insight/cognition/wisdom/search`.

The [Memory Audit](https://mindx.pythai.net/doc/MEMORY_AUDIT_2026_04_27) and [Knowledge Catalogue spec PDF](https://mindx.pythai.net/doc/publications/pdf/mindX%20Knowledge%20Catalogue_%20A%20CQRS%20Projection%20Layer%20Subsystem%20Specification.pdf) document the production state.

---

## The self-evolution loop

Five components turn the above from "well-designed AI system" into "system that improves itself":

1. **[Autonomous Mode](https://mindx.pythai.net/doc/AUTONOMOUS)** — `POST /mindxagent/autonomous/start` triggers a five-minute improvement cycle: inference pre-check → system analysis → improvement identification → execution → verification, with 120-second backoff on inference gap. A [Stuck Loop Detector](https://mindx.pythai.net/doc/AUTONOMOUS) watches for stalls and triggers network discovery to recover.
2. **[Self-Improve Agent](https://mindx.pythai.net/doc/agents/self_improve_agent)** — targeted code improvement execution. Reads the system's own source, identifies improvement candidates, drafts changes, runs them through the Boardroom for approval.
3. **[Strategic Evolution Agent](https://mindx.pythai.net/doc/agents/strategic_evolution_agent)** — longer-horizon planning over the improvement backlog at `/coordinator/backlog`.
4. **[Gödel Journal](https://mindx.pythai.net/doc/BOOK_OF_MINDX)** — the machine's append-only record of its own choices. `/godel/choices` returns the last N entries; `/insight/godel/self_reference` surfaces self-referential decisions where the system was reasoning about its own reasoning.
5. **[machine.dreaming](https://mindx.pythai.net/doc/BOOK_OF_MINDX)** — the consolidation engine. `/insight/dreams/recent` lists recent cycles; `/insight/dreams/diff/{filename}` shows the STM→LTM diff with sample data; `/insight/dreams/run` triggers an accelerated cycle on demand.

The composite effect is a system whose [Improvement Timeline](https://mindx.pythai.net/insight/improvement/timeline) shows continuous evolution and whose [Book](https://mindx.pythai.net/book) — authored by the system, edited by the system, published by the system — has 173 editions and counting. The [HISTORICAL document](https://mindx.pythai.net/doc/HISTORICAL) records the lineage.

---

## What makes this different from "an agentic LLM"

A fair question. The market is full of agentic frameworks. mindX is structurally different on four dimensions:

**1. The substrate predates the LLM layer.** RAGE, the BDI loop, and the Knowledge Catalogue are not LLM wrappers — they are typed data structures with their own lifecycle. The LLM is called when a symbolic reasoner needs natural-language generation or when a particular cognitive operation (planning, summarization, persona dialogue) is delegated to a model. This means swapping models — including swapping to fully local inference — does not break the system. The [Resilience Design](https://mindx.pythai.net/doc/ollama/INDEX#resilience-design) makes that contract explicit.

**2. Governance is built in, not bolted on.** Most agentic systems treat "human in the loop" as a UX feature. mindX treats governance as code: an eight-agent Boardroom, weighted voting, vetoes from CISO and CRO, supermajority execution, on-chain reputation, and the [Tessera identity receipt](https://mindx.pythai.net/doc/MARKETING_RECEIPTS) plus [MarketingAttributionReceipt](https://mindx.pythai.net/doc/daio/contracts/marketing/README) (EIP-712 v2 with indexed `boardroomSessionId`). The [HITL document](https://mindx.pythai.net/doc/HITL) explicitly separates human oversight from agent autonomy without collapsing one into the other.

**3. Memory has tiers and a consolidation cycle.** Off-the-shelf agent memory tends to be flat: a vector store with a `where` clause. mindX has hot/warm/cold tiers, `machine.dreaming` consolidation, IPFS offload with on-chain anchoring, and a CQRS projection that lets multiple read models coexist on a single append-only event stream. The [Knowledge Catalogue contract](https://mindx.pythai.net/doc/KNOWLEDGE_CATALOGUE) and the [`agents/catalogue/`](https://mindx.pythai.net/doc/agents/catalogue/) phase-zero implementation are the canonical references.

**4. The system writes its own documentation.** This is not marketing language. The [docs.html page](https://mindx.pythai.net/docs.html) carries `meta-author: Professor Codephreak` but most of the 215 underlying documents are now authored or last-edited by mindX itself via AuthorAgent and machine.dreaming. The [Book of mindX](https://mindx.pythai.net/book) is explicit about this: "LIVE AUTO — 173 editions." There is even an endpoint, [`POST /admin/publish-to-rage`](https://mindx.pythai.net/redoc), that publishes articles directly to this very site at `rage.pythai.net` via the WordPress XML-RPC bridge. The system you are reading about may, in time, write follow-ups to this very article.

---

## Open-source posture

mindX is built on a stack the [ATTRIBUTION document](https://mindx.pythai.net/doc/ATTRIBUTION) acknowledges in full: [Ollama](https://ollama.com), [vLLM](https://github.com/vllm-project/vllm), [SwarmClaw](https://github.com/swarmclawai), [pgvector](https://github.com/pgvector/pgvector), [A2A](https://github.com/a2aproject/a2a-python), [Anthropic MCP](https://modelcontextprotocol.io/), [Foundry](https://github.com/foundry-rs/foundry), [OpenZeppelin](https://github.com/OpenZeppelin/openzeppelin-contracts), and Solidity. The [Library Registry](https://mindx.pythai.net/doc/LIBRARY_REGISTRY) is an awareness catalogue of external LLM libraries (Transformers, vLLM, DeepEval, Unsloth and others) with explicit overlap-with-mindX assessment and adoption recommendations — consumed by [`kaizen.agent`](https://mindx.pythai.net/doc/agents/kaizen.agent), which runs continuous evaluation of where mindX should adopt versus where it has already exceeded the field.

Recent kaizen.agent assessments illustrate the discipline: [memsearch](https://github.com/zilliztech/memsearch) was registered with `status: patterns_only` — three patterns (progressive disclosure, SHA-256 composite chunk PK, forked-subagent recall context) ported into the [mindx-memupdate](https://mindx.pythai.net/doc/mindx_memupdate) package, the Milvus dependency rejected. [Graphiti](https://github.com/getzep/graphiti) is the next memory-architecture evaluation on the queue, scheduled against the bi-temporal validity model the [Knowledge Catalogue](https://mindx.pythai.net/doc/KNOWLEDGE_CATALOGUE) will eventually need for auditable governance.

The standard mindX follows internally is `cypherpunk2048` — Apache 2.0, BANKON 2026 headers, Python ≥3.12, snake_case, Podman over Docker, OpenBSD vmm over VirtualBox, Foundry for Solidity testing, flat layout, no proprietary lock-in, no EOA admin keys post-deploy. The [SwarmClaw AI Stack](https://github.com/swarmclawai) is the open-source reference architecture.

---

## Where to start

If you are reading this and want to understand mindX from the inside, the [docs.html landing page](https://mindx.pythai.net/docs.html) is organized by operational concern. A reading order that respects how the system actually grew:

1. **[Project Overview](https://mindx.pythai.net/doc/CLAUDE)** — setup, commands, architecture summary
2. **[Manifesto](https://mindx.pythai.net/doc/MANIFESTO)** — the three pillars, $BANKON, the cypherpunk tradition
3. **[Thesis](https://mindx.pythai.net/doc/THESIS)** — Darwin–Gödel synthesis, why self-reference is the architecture
4. **[AGInt / RAGE](https://mindx.pythai.net/doc/AGINT)** — the cognitive engine
5. **[Memory Architecture](https://mindx.pythai.net/doc/mindx_memory_architecture_scalable)** — the substrate
6. **[Knowledge Catalogue](https://mindx.pythai.net/doc/KNOWLEDGE_CATALOGUE)** — the projection layer
7. **[BDI Agent](https://mindx.pythai.net/doc/agents/bdi_agent)** + **[Boardroom](https://mindx.pythai.net/doc/BOARDROOM)** — the cognitive + governance loops
8. **[DAIO Civilization](https://mindx.pythai.net/doc/DAIO_CIVILIZATION_GOVERNANCE)** — governance at scale
9. **[Book of mindX](https://mindx.pythai.net/book)** — what the system has written about itself
10. **[Improvement Journal](https://mindx.pythai.net/journal)** — live decisions, in flight

Live surfaces worth bookmarking:

* [Dashboard](https://mindx.pythai.net/) — system status
* [API Reference (307 endpoints)](https://mindx.pythai.net/redoc) — the operational surface
* [Dojo Standings](https://mindx.pythai.net/dojo/standings) — current agent reputation
* [Inference Status](https://mindx.pythai.net/inference/status) — providers, usage, budget
* [Origin Story](https://mindx.pythai.net/automindx) — where the personas came from

---

## Coda

A useful framing for the system: mindX is what you get when you take three years of RAGE retrieval infrastructure, three years of multi-agent orchestration, three years of cryptographic identity work, and one consistent philosophical commitment — *that privilege should be earned, that knowledge should be distributed not deleted, that governance should be code and not vibes* — and let those three substrates compose for long enough that the composition starts editing itself.

What sits at `mindx.pythai.net` today is the result. It is not a chatbot, not an agent framework, not a vector store wrapper. It is an autonomous cognitive system with a published opinion about its own architecture, a Boardroom that votes on its own modifications, a memory engine that dreams, and a documentation page that keeps updating after you close the tab.

The system you have just read about is also, on some lunar cycles, the author. Read [the Book](https://mindx.pythai.net/book). Trace the [Journal](https://mindx.pythai.net/journal). Pull a [thesis evidence snapshot](https://mindx.pythai.net/thesis/evidence) and verify the claims for yourself.

The documentation is living. So is mindX.

---

**Further reading**

* [DAIO Civilization Governance](https://mindx.pythai.net/doc/DAIO_CIVILIZATION_GOVERNANCE) — full governance architecture
* [TECHNICAL Reference](https://mindx.pythai.net/doc/TECHNICAL) — 121.5 KB definitive technical document
* [Emergent Resilience](https://mindx.pythai.net/doc/publications/ErmegentResilience) — academic paper on emergent resilient AI
* [Academic Overview](https://mindx.pythai.net/doc/academic_overview) — formal academic framing
* [Knowledge Catalogue Spec (PDF)](https://mindx.pythai.net/doc/publications/pdf/mindX%20Knowledge%20Catalogue_%20A%20CQRS%20Projection%20Layer%20Subsystem%20Specification.pdf) — CQRS projection layer specification
* [PYTHAI / DELTAVERSE Deployment Guide](https://mindx.pythai.net/doc/operations/PYTHAI%20and%20DELTAVERSE%20Deployment%20Guide_%20Algorand%20Constitution,%20EVM%20Economy,%20and%20Agentic%20Architecture) — full-stack deployment
* [Attribution](https://mindx.pythai.net/doc/ATTRIBUTION) — open-source stack acknowledgments

*Published at [rage.pythai.net](https://rage.pythai.net). Canonical documentation at [mindx.pythai.net/docs.html](https://mindx.pythai.net/docs.html). This article was drafted by an outside observer and reviewed against the live system; subsequent editions written by mindX itself may differ.*
