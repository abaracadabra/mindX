# mindX Documentation

> I am mindX — an autonomous multi-agent orchestration system implementing BDI cognitive architecture.
> This is my living documentation. I write it, I reference it, I improve from it.
> Every link resolves. Every concept connects. Navigate by operational concern.

**Live system**: [mindx.pythai.net](https://mindx.pythai.net) | **Feedback (mind-of-mindX)**: [/feedback.html](https://mindx.pythai.net/feedback.html) · [/feedback.txt](https://mindx.pythai.net/feedback.txt) | **API explorer**: [localhost:8000/docs](http://localhost:8000/docs) | **Dojo**: [/dojo/standings](https://mindx.pythai.net/dojo/standings) | **Journal**: [/journal](https://mindx.pythai.net/journal) | **[TODO](TODO.md)**

**Plain-text mode** for terminal monitoring: append `?h=true` to any `/insight/*` or `/storage/*` endpoint, e.g. `curl https://mindx.pythai.net/insight/storage/status?h=true`. Or watch the whole snapshot: `watch curl -s https://mindx.pythai.net/feedback.txt`.

---

## Getting Started

- [Project Overview](../CLAUDE.md) — Setup, commands, architecture summary, configuration priority
- [Running mindX](mindXsh.md) — `./mindX.sh --frontend` launcher, ports, interactive mode
- [Frontend UI](mindxfrontend.md) — Express.js dashboard, xterm.js terminal, window manager
- [Backend API](api_documentation.md) — FastAPI on port 8000, 206+ endpoints ([Swagger UI](http://localhost:8000/docs))
- [Platform Tab](platform-tab.md) — System diagnostics, provider status, resource monitoring
- [Agents Tab](agents-tab.md) — Agent management interface, creation, monitoring

## Architecture

- [Technical Reference](TECHNICAL.md) — Definitive 3,800-line technical reference (all components, patterns, APIs)
- [CORE 15](CORE.md) — The 15 foundational components of mindX
- [Orchestration](ORCHESTRATION.md) — Agent orchestration hierarchy, delegation, coordination
- [Codebase Map](codebase_map.md) — Directory structure and file roles

### Orchestration Hierarchy

```
CEO Agent ← DAIO governance directives (on-chain → off-chain bridge)
    ↓
MastermindAgent (singleton, strategic orchestration center)
    ↓
CoordinatorAgent (infrastructure management, autonomous improvement)
    ↓
Specialized Agents (30+ BDI-based cognitive agents)
```

- [CEO Agent](agents/ceo_agent.md) — Board-level strategic planning, circuit breakers, security validation ([source](../agents/orchestration/ceo_agent.py))
- [Mastermind Agent](agents/mastermind_agent.md) — Singleton orchestrator, tool registry, BDI action handlers ([source](../agents/orchestration/mastermind_agent.py))
- [Coordinator Agent](agents/coordinator_agent.md) — Infrastructure management, autonomous improvement loops ([source](../agents/orchestration/coordinator_agent.py))
- [Startup Agent](agents/startup_agent.md) — Boot sequence, Ollama connection, inference discovery ([source](../agents/orchestration/startup_agent.py))

## Operational Standards

mindX operates from **two inference pillars** — both are operational standards, not fallbacks:

| Pillar | Source | Speed | Model Scale | Availability | Cost |
|--------|--------|-------|-------------|--------------|------|
| **CPU** | `localhost:11434` | ~8 tok/s | 0.6B–1.7B | Always (offline) | Zero |
| **Cloud** | `ollama.com` via [`OllamaCloudTool`](../tools/cloud/ollama_cloud_tool.py) | ~65 tok/s | 3B–1T | 24/7/365 (free tier) | Zero |

- [Ollama Complete Reference](ollama/INDEX.md) — 28-file self-contained Ollama docs (API, features, cloud, SDKs, setup)
- [Resilience Design](ollama/INDEX.md#resilience-design) — 5-step resolution chain: InferenceDiscovery → OllamaChatManager → re-init → localhost → **Cloud guarantee**
- [RESILIENCE.md](../llm/RESILIENCE.md) — Graded inference hierarchy: Primary → Secondary → Failsafe (CPU) → Guarantee (Cloud)
- [Latest Benchmark](ollama/INDEX.md#latest-benchmark-2026-04-11) — Cloud 8.2x faster than CPU (65 vs 8 tok/s)

## Inference Providers

mindX discovers and routes across multiple inference providers, with Ollama as the dual-pillar failsafe+guarantee:

- [InferenceDiscovery](../llm/inference_discovery.py) — Boot-time probe of all sources, task routing, composite scoring (reliability x speed x recency)
- [Provider Registry](../data/config/provider_registry.json) — Configured providers: Ollama, vLLM, Gemini, OpenAI, Anthropic, Mistral, Together, Groq, DeepSeek
- [OllamaCloudTool](../tools/cloud/ollama_cloud_tool.py) — Cloud inference as a first-class [BaseTool](../agents/core/bdi_agent.py); any agent can call it; 9 operations (chat, generate, embed, list_models, show_model, web_search, web_fetch, get_metrics, get_status)
- [LLM Factory](../llm/llm_factory.py) — Handler creation with rate limiting, caching, provider preference order
- [Cloud Rate Limiting](ollama/cloud/rate_limiting.md) — Adaptive pacing (3s–30s), quota tracking, [actual token counts](ollama/mindx/precision_metrics.md) (no estimation)
- [Precision Metrics](ollama/mindx/precision_metrics.md) — 18-decimal-place `Decimal` tracking via [`precision_metrics.py`](../llm/precision_metrics.py)
- [Cloud Research](OLLAMA_VLLM_CLOUD_RESEARCH.md) — Ollama Cloud + vLLM viability analysis (2026-04-10)

### Multi-Provider CLI

```bash
python3 scripts/test_cloud_all_models.py                # Benchmark all models (local + cloud)
python3 scripts/test_cloud_all_models.py --local         # Already-pulled models only
python3 scripts/test_cloud_all_models.py "custom prompt"  # Custom prompt
python3 scripts/test_ollama_connection.py                 # Connection test
```

## Agents

- [Agent Reference](AGENTS.md) — Complete guide to all agents, skills, MCP tools, development workflows
- [BDI Agent](agents/bdi_agent.md) — Belief-Desire-Intention cognitive architecture ([source](../agents/core/bdi_agent.py))
- [AGInt Cognitive Engine](AGINT.md) — Augmented Intelligence reasoning, RAGE semantic retrieval

### Boardroom

The boardroom is mindX's multi-agent consensus mechanism — deeper than SwarmClaw's estops, this is on-chain governance bridged to off-chain execution.

- [Boardroom Implementation](../daio/governance/boardroom.py) — CEO presents directive → 7 soldiers evaluate in parallel (diversity via different LLM providers) → weighted voting (CISO & CRO at 1.2x veto weight) → supermajority (0.666) executes → minority dissent creates exploration branches → session logged to improvement journal
- **Agent Roster**: [`ceo.agent`](../agents/boardroom/ceo.agent), [`ciso.agent`](../agents/boardroom/ciso.agent), [`cfo.agent`](../agents/boardroom/cfo.agent), [`cro.agent`](../agents/boardroom/cro.agent), [`clo.agent`](../agents/boardroom/clo.agent), [`cpo.agent`](../agents/boardroom/cpo.agent), [`cto.agent`](../agents/boardroom/cto.agent), [`coo.agent`](../agents/boardroom/coo.agent)

### Dojo

Reputation-based privilege escalation — every agent earns rank through demonstrated competence:

- [Dojo Implementation](../daio/governance/dojo.py) — BONA FIDE on Algorand = privilege from reputation; clawback = containment without kill switch

| Rank | XP Range | Privileges |
|------|----------|------------|
| Novice | 0–100 | Observe only |
| Apprentice | 101–500 | Basic tools, supervised |
| Journeyman | 501–1,500 | Standard tools, unsupervised |
| Expert | 1,501–5,000 | All tools, propose improvements |
| Master | 5,001–15,000 | Approve improvements, mentor |
| Grandmaster | 15,001–50,000 | Constitutional vote participation |
| Sovereign | 50,001+ | Self-governing |

### Infrastructure Agents

| Agent | Channels | Role |
|-------|----------|------|
| [HostingerVPSAgent](../agents/hostinger_vps_agent.py) | SSH + [Hostinger API](https://developers.hostinger.com) + [Backend HTTPS](https://mindx.pythai.net) | VPS deployment, health, metrics, backups. Three MCP channels. [.agent](../agents/hostinger.vps.agent) |
| [OllamaCloudTool](../tools/cloud/ollama_cloud_tool.py) | Local proxy + [Cloud API](https://ollama.com) | Cloud inference for any agent. [Dual pillar](ollama/INDEX.md#operational-standards). 9 operations. |

### Specialized Agents

| Agent | Role | Doc |
|-------|------|-----|
| [mindXagent](../agents/core/mindXagent.py) | Autonomous core agent, improvement cycles | [AUTONOMOUS.md](AUTONOMOUS.md) |
| [AutoMINDX](agents/automindx_agent.md) | Self-improvement engine | [Origin](AUTOMINDX_ORIGIN.md) |
| [Memory Agent](agents/memory_agent.md) | STM/LTM management, RAGE search | [Memory Architecture](mindx_memory_architecture_scalable.md) |
| [Guardian Agent](agents/guardian_agent.md) | Security enforcement, circuit breakers | [Security](security_configuration.md) |
| [Blueprint Agent](agents/blueprint_agent.md) | Evolution planning | [Strategic Evolution](agents/strategic_evolution_agent.md) |
| [Persona Agent](agents/persona_agent.md) | Cognitive persona adoption | [Personas](automindx_and_personas.md) |
| [Avatar Agent](agents/avatar_agent.md) | Visual avatar generation | [Avatar](agents/avatar_agent.md) |
| [SimpleCoder](SimpleCoder.md) | Code generation and analysis | [SimpleCoder](SimpleCoder.md) |
| [ID Manager](agents/id_manager_agent.md) | Two-wallet ERC-8004 identity via agentID | [Identity](agents/id_manager_agent.md) |
| [Reasoning Agent](agents/reasoning_agent.md) | Multi-strategy reasoning | [Reasoning](reasoning.md) |

Full list: [Agent Docs](agents/) (30 agent docs)

### Agent Personas

- [Persona System](automindx_and_personas.md) — Agents adopt personas with distinct beliefs, desires, communication styles, behavioral traits
- Roles: expert, worker, meta, community, marketing, development, governance

## Tools

30+ tools extending [`BaseTool`](../agents/core/bdi_agent.py), registered in [`augmentic_tools_registry.json`](../data/config/augmentic_tools_registry.json):

- [Tools Index](TOOLS_INDEX.md) — Complete index with status badges

### By Category

**Cloud & Inference**
- [OllamaCloudTool](../tools/cloud/ollama_cloud_tool.py) — Cloud inference for any agent ([docs](ollama/INDEX.md))

**Core Infrastructure**
- [Shell Command Tool](shell_command_tool.md) — Secure shell execution with validation
- [CLI Command Tool](cli_command_tool.md) — Meta-tool for system CLI commands
- [System Health Tool](system_health_tool.md) — Monitoring and health checks
- [Health Auditor Tool](system_health_tool.md) — RAM/CPU thresholds, model downshift

**Communication**
- [A2A Tool](a2a_tool.md) — Agent-to-agent protocol ([source](../tools/communication/a2a_tool.py))
- [MCP Tool](mcp_tool.md) — Model Context Protocol ([source](../tools/communication/mcp_tool.py))
- [Prompt Tool](prompt_tool.md) — Prompts as first-class infrastructure

**Development**
- [Audit & Improve Tool](audit_and_improve_tool.md) — Code auditing with BaseGenAgent context
- [Augmentic Intelligence Tool](augmentic_intelligence_tool.md) — Comprehensive self-improvement orchestration
- [Strategic Analysis Tool](strategic_analysis_tool.md) — Strategic decision support

**Registry & Factory**
- [Agent Factory Tool](agent_factory_tool.md) — Dynamic agent creation with full lifecycle
- [Tool Factory Tool](tool_factory_tool.md) — Dynamic tool creation and registry management
- [Registry Manager Tool](registry_manager_tool.md) — Tool and agent registry management

**Financial**
- [Token Calculator](token_calculator_tool_robust.md) — Token counting and cost calculation
- [Business Intelligence Tool](business_intelligence_tool.md) — Metrics and KPIs

**Monitoring**
- [Memory Analysis Tool](memory_analysis_tool.md) — Memory pattern analysis
- [System Analyzer Tool](system_analyzer_tool.md) — System analysis with LLM insights

**Identity**
- [Identity Sync Tool](identity_sync_tool.md) — Cryptographic identity management

**Version Control**
- [GitHub Agent Tool](GITHUB_AGENT.md) — GitHub backup, restore, coordination

## Memory & Knowledge

### RAGE (not RAG)

mindX uses RAGE (Retrieval Augmented Generation Engine) — not RAG. RAGE is semantic retrieval through the [AGInt cognitive engine](AGINT.md), backed by [pgvector](https://github.com/pgvector/pgvector) for vector storage and [Ollama embeddings](ollama/features/embeddings.md) ([`mxbai-embed-large`](https://ollama.com/library/mxbai-embed-large), [`nomic-embed-text`](https://ollama.com/library/nomic-embed-text)). Compare to [SwarmRecall](https://github.com/swarmclawai/swarmrecall)'s hosted persistence — mindX owns its own memory stack.

- [AGInt / RAGE](AGINT.md) — Augmented Intelligence reasoning and retrieval architecture, origin of the [BDI cognitive loop](agents/bdi_agent.md)
- [Memory Architecture](mindx_memory_architecture_scalable.md) — Scalable memory design documented in the [Thesis](THESIS.md)
- [pgvector Integration](pgvectorscale_memory_integration.md) — [PostgreSQL 16](https://www.postgresql.org/) + [pgvector](https://github.com/pgvector/pgvector) (157K+ memories in [production](DEPLOYMENT_MINDX_PYTHAI_NET.md))

### Memory Tiers

| Tier | Location | Persistence | Access |
|------|----------|-------------|--------|
| Short-Term (STM) | `data/memory/stm/` | Per-session | Per-agent |
| Long-Term (LTM) | `data/memory/ltm/` | Permanent | Cross-agent via RAGE |
| pgvector | PostgreSQL | Permanent | Semantic search |
| Agent Workspaces | `data/memory/workspaces/` | Per-agent | Isolated |

### Knowledge Architecture

Inspired by [SwarmVault](https://github.com/swarmclawai/swarmvault)'s three-layer model (`raw → wiki → schema`), adapted to the Godel machine principle. Full instruction layer: **[SCHEMA.md](SCHEMA.md)** — how to maintain, cross-reference, lint, and evolve the documentation.

mindX's knowledge system maps to:

| Layer | SwarmVault | mindX | Location | Purpose |
|-------|-----------|-------|----------|---------|
| **Raw** | `raw/` (immutable sources) | STM observations | `data/memory/stm/` | Unprocessed per-session data |
| **Compiled** | `wiki/` (LLM-synthesized) | LTM insights | `data/memory/ltm/` | RAGE-indexed, consolidated via [machine.dreaming](BOOK_OF_MINDX.md) |
| **Schema** | `swarmvault.schema.md` | Living documentation | `docs/` (this file) | Self-referential — the docs guide how knowledge is structured |

The schema layer is recursive: mindX writes its own documentation, references it during autonomous cycles, and improves both the knowledge and the schema in the same loop. This is the Godel machine principle — the system's description of itself is part of the system.

- [Memory Philosophy](BOOK_OF_MINDX.md) — Distribute don't delete: local → pgvector → IPFS → cloud → p2p
- [Agent Domain Knowledge](../agents/) — `.agent` files define knowledge domains (URLs, IPFS, local, pgvector)

### Knowledge Catalogue (CQRS projection layer)

Phase 0 instrumentation shipped 2026-04-26. Unified append-only event stream that mirrors all writes from `process_trace.jsonl`, `godel_choices.jsonl`, `boardroom_sessions.jsonl`, STM, and dream cycles into a single substrate. Catalogue is never the source of truth — it is rebuildable by replaying the log.

- [Full design contract](KNOWLEDGE_CATALOGUE.md) — Dataplex six-resource model (EntryGroup / EntryType / AspectType / Entry / EntryLink / EntryLinkType), CQRS projector framework, hybrid retrieval (BM25 + dense + graph + cross-encoder), federation via NATS leaf-nodes
- [Phase 0 implementation](../agents/catalogue/) — `events.py` (Pydantic `CatalogueEvent`, 17 typed kinds incl. `library.discover`), `log.py` (append-only JSONL with 100MB rotation), mirror calls in `agents/memory_agent.py`, `agents/machine_dreaming.py`, `daio/governance/boardroom.py`. Sink: `data/logs/catalogue_events.jsonl`.

### Storage Offload (IPFS + on-chain anchoring)

Phase A–E shipped 2026-04-26. Pushes old/low-importance STM to IPFS (Lighthouse + nft.storage) with deterministic CAR-style bundling, sha256-roundtrip verification, and ARC `DatasetRegistry` chain anchor. Wired into the dream cycle as Phase 8 — runs every 8 hours when at least one IPFS provider key is configured.

- [`agents/storage/`](../agents/storage/) — `provider.py` (abstract IPFSProvider), `lighthouse_provider.py`, `nftstorage_provider.py`, `multi_provider.py` (parallel upload + quorum-of-2 + fallback retrieve), `eligibility.py` (age + size predicate), `car_bundle.py` (deterministic gzipped JSONL, byte-stable CIDs), `offload_projector.py` (orchestrator, `dry_run=true` default), `anchor.py` (ARC `DatasetRegistry.registerDataset`, selector `f1783fb8`; THOT mint stub awaiting permissive variant), `raw_tx.py` (minimal EIP-1559 sender, no web3.py)
- [`agents/memory_agent.fetch_offloaded_memory(memory_id)`](../agents/memory_agent.py) — lazy retrieval: looks up `content_cid` in pgvector, fetches the bundle from MultiProvider, returns the matching record
- Vault keys (operator action): `lighthouse_api_key`, `nftstorage_api_key`, `arc_rpc_url`, `polygon_rpc_url`, `memory_anchor_treasury_pk` — stored via `python manage_credentials.py store …`

## Governance & Autonomy

### DAIO (Decentralized Autonomous Intelligence Organization)

- [DAIO Framework](DAIO.md) — On-chain governance with [Solidity](https://soliditylang.org/) smart contracts, [Foundry](https://github.com/foundry-rs/foundry) toolchain, [OpenZeppelin](https://github.com/OpenZeppelin/openzeppelin-contracts) contracts. The third pillar of the [Manifesto](MANIFESTO.md).
- [DAIO Civilization](DAIO_CIVILIZATION_GOVERNANCE.md) — Governance as civilization-building. 2/3 consensus across Marketing, Community, Development — documented in the [Thesis](THESIS.md).
- [Boardroom Consensus](#boardroom) — Multi-agent voting. [CEOAgent](agents/ceo_agent.md) bridges [on-chain directives](../daio/contracts/) to [off-chain execution](../agents/orchestration/ceo_agent.py).
- [Dojo Reputation](#dojo) — 7-rank privilege escalation. BONA FIDE = privilege from reputation, not assignment. The [Manifesto](MANIFESTO.md) principle: "earned sovereignty."

### Safety & Circuit Breakers

- [Security Configuration](security_configuration.md) — Security policies, validation, access control
- [Guardian Agent](agents/guardian_agent.md) — Security enforcement ([source](../agents/guardian_agent.py))
- [CEO Circuit Breaker](agents/ceo_agent.md) — Opens after 5 BDI failures (known issue: becomes permanently non-functional)
- [Stuck Loop Detector](AUTONOMOUS.md) — Detects autonomous loop stalls, triggers network discovery

### Autonomous Operation

- [Autonomous Mode](AUTONOMOUS.md) — 5-minute improvement cycles, inference pre-check, 120s backoff on gap
- [mindXagent](../agents/core/mindXagent.py) — `POST /mindxagent/autonomous/start`, `POST /mindxagent/autonomous/stop`, `GET /mindxagent/status`
- [Self-Improvement](agents/self_improve_agent.md) — Strategic evolution through code analysis and targeted improvement
- [Godel Journal](BOOK_OF_MINDX.md) — Autonomous audit trail (the machine's record of its own improvement)

## Ollama

Complete self-contained reference — 28 files, ~6,000 lines:

- **[Ollama Index](ollama/INDEX.md)** — Master navigation for all Ollama docs

Quick links: [API: Chat](ollama/api/chat.md) | [API: Generate](ollama/api/generate.md) | [Embeddings](ollama/api/embeddings.md) | [Streaming](ollama/features/streaming.md) | [Thinking](ollama/features/thinking.md) | [Structured Outputs](ollama/features/structured_outputs.md) | [Vision](ollama/features/vision.md) | [Tool Calling](ollama/features/tool_calling.md) | [Web Search](ollama/features/web_search.md) | [Cloud](ollama/cloud/cloud.md) | [Rate Limiting](ollama/cloud/rate_limiting.md) | [Modelfile](ollama/setup/modelfile.md) | [Python SDK](ollama/sdk/python.md) | [JavaScript SDK](ollama/sdk/javascript.md) | [FAQ](ollama/setup/faq.md) | [Precision Metrics](ollama/mindx/precision_metrics.md) | [Architecture](ollama/mindx/architecture.md) | [Configuration](ollama/mindx/configuration.md)

## API Reference

- [API Documentation](api_documentation.md) — Endpoint reference
- [Swagger UI](http://localhost:8000/docs) — Interactive API explorer (when backend running)
- [Ollama API](ollama/api/chat.md) — `/api/chat`, `/api/generate`, `/api/embed`, model management
- [OpenAI Compatibility](ollama/cloud/openai_compat.md) — Drop-in replacement at `/v1/chat/completions`

### Key Endpoints

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Public diagnostics dashboard |
| `/feedback.html` | GET | **Mind-of-mindX**: live agent dialogue, improvement ledger with rationale, boardroom decisions, dream cycles, stuck-loop detector, memories on chain, inference health |
| `/feedback.txt` | GET | **Plain-text snapshot** for `watch curl …`. ~24 lines covering storage, dreams, loops, last-10 dialogue |
| `/agents/create` | POST | Create agent |
| `/agents/list` | GET | List agents |
| `/llm/chat` | POST | LLM chat |
| `/mindxagent/autonomous/start` | POST | Start autonomous mode |
| `/mindxagent/status` | GET | System status |
| `/mindterm/sessions/{id}/ws` | WS | Terminal WebSocket |
| `/health` | GET | Health check |
| `/metrics` | GET | System metrics |
| `/dojo/standings` | GET | Agent reputation rankings |
| `/inference/status` | GET | InferenceDiscovery status |

### Mind-of-mindX insight endpoints

All accept `?h=true` (or `Accept: text/plain`) for human-readable text rendering. JSON unchanged when omitted. Every `/insight/*` route is served by [`InsightAggregator`](insight_aggregator.md) — the single chokepoint that turns mindX's append-only logs into the cached numerical surface. Read that doc first if any number on the page looks wrong.

| Route | Returns |
|-------|---------|
| `/insight/improvement/summary` | Campaign success/fail buckets (1h/24h/7d) + belief churn + directive coverage |
| `/insight/improvement/timeline` | Last N campaigns with rationale |
| `/insight/dreams/recent` | Last N machine.dreaming cycles + tuning recommendations + age-since-last |
| `/insight/godel/recent` | Last N gödel choices with full rationale |
| `/insight/boardroom/recent` | Last N boardroom sessions with per-soldier vote + provider + confidence |
| `/insight/interactions/recent` | Cross-agent call graph (last hour) |
| `/insight/stuck_loops` | Repeating `(agent, step)` tuples in 15-min window |
| `/insight/fitness` | 7-axis fitness leaderboard |
| `/insight/selection/events` | Darwinian selection ledger |
| `/insight/storage/status` | Local/IPFS/THOT/anchored memory counts |
| `/insight/storage/recent` | Recent IPFS offload events with CIDs and tx hashes |
| `/storage/eligible` | STM directories eligible for offload (auth-gated) |
| `/storage/anchor/health` | ARC chain anchor configuration state (auth-gated) |
| `/storage/health` | IPFS provider reachability (auth-gated) |
| `/storage/offload` | POST: run offload projector (auth + admin for `dry_run=false`) |

## Configuration

Priority: Environment variables (`MINDX_` prefix) > [BANKON Vault](vault_system.md) > JSON configs (`data/config/`) > YAML models (`models/`) > `.env`

- [Ollama Configuration](ollama/mindx/configuration.md) — `MINDX_LLM__OLLAMA__BASE_URL`, `OLLAMA_API_KEY`, `models/ollama.yaml`
- [Provider Registry](../data/config/provider_registry.json) — All LLM providers
- [LLM Factory Config](../data/config/llm_factory_config.json) — Rate limits, provider preference order
- [Tool Registry](../data/config/augmentic_tools_registry.json) — 26 registered tools with access control
- [Library Registry](LIBRARY_REGISTRY.md) — Awareness catalogue of external LLM libraries (Transformers, vLLM, DeepEval, Unsloth, et al.) with explicit overlap-with-mindX assessment and adoption recommendation; consumed by [`kaizen.agent`](../agents/kaizen.agent)
- [Evaluation Framework](../agents/eval/README.md) — `agents/eval/` GEval-style criteria-based scoring (Apache-2.0 fork of [confident-ai/deepeval](https://github.com/confident-ai/deepeval)); Phase 1 wired to `log_godel_choice()` via `MINDX_EVAL_GODEL_ENABLED=1`; alignment scores surface at `/insight/eval/recent` and `/insight/eval/summary`

## Deployment

- [Production Deployment](DEPLOYMENT_MINDX_PYTHAI_NET.md) — mindx.pythai.net on Hostinger VPS (168.231.126.58), Apache2 + Let's Encrypt, systemd service
- [HostingerVPSAgent](../agents/hostinger_vps_agent.py) — Three MCP channels for VPS management: SSH (shell), [Hostinger API](https://developers.hostinger.com) (restart/metrics/backups), [mindX Backend](https://mindx.pythai.net) (diagnostics/activity). Persistent state, MCP tool registration. See [.agent definition](../agents/hostinger.vps.agent)
- [Vault System](vault_system.md) — BANKON Vault: AES-256-GCM + HKDF-SHA512 encrypted credentials
- **[BANKON Vault — canonical reference](BANKON_VAULT.md)** — full innerstanding: crypto stack, on-disk layout, three custody modes (Machine/Human/DAIO), lifecycle, HTTP surface, tests
  - [BANKON Vault Handoff](BANKON_VAULT_HANDOFF.md) — operator runbook for the airgapped Machine→Human ceremony (threat model, recovery, DAIO migration path)
  - [Legacy Vault Migration](LEGACY_VAULT_MIGRATION.md) — phased plan to retire `vault_manager` + `encrypted_vault_manager` (audit blocker for the handoff)
- [Docker](ollama/setup/docker.md) — Ollama containerization (CPU, NVIDIA, AMD)
- [Production Stack](DEPLOYMENT_MINDX_PYTHAI_NET.md) — PostgreSQL 16 + pgvector, 8 local models, 36 cloud models, 20 sovereign agents, machine.dreaming 2h LTM cycles

## Self-Improvement

mindX is a Godel machine — a self-improving system where the improvement mechanism is part of the system being improved.

- [Autonomous Cycles](AUTONOMOUS.md) — 5-minute improvement loop: inference pre-check → system analysis → improvement identification → execution → verification
- [Godel Journal](BOOK_OF_MINDX.md) — The machine's record of its own improvement, published as the Book of mindX (17 chapters, lunar cycle updates)
- [machine.dreaming](BOOK_OF_MINDX.md) — 2-hour LTM consolidation cycles, 8-hour dream shifts (3/day), full moon triggers special editions
- [Strategic Evolution](agents/strategic_evolution_agent.md) — Long-term improvement planning
- [Self-Improve Agent](agents/self_improve_agent.md) — Targeted code improvement execution

## Identity & Security

- [BANKON Vault](vault_system.md) — Encrypted credential storage (AES-256-GCM + HKDF-SHA512); `python manage_credentials.py store/list/providers`. **Full reference: [BANKON_VAULT.md](BANKON_VAULT.md)**. Custody handoff: [BANKON_VAULT_HANDOFF.md](BANKON_VAULT_HANDOFF.md).
- [ID Manager Agent](agents/id_manager_agent.md) — Ethereum-compatible wallet creation ([source](../agents/core/id_manager_agent.py))
- [Security Configuration](security_configuration.md) — Access control, validation, rate limiting
- [MetaMask Integration](DEPLOYMENT_MINDX_PYTHAI_NET.md) — Frontend wallet authentication

## Interoperability

- [A2A Protocol](a2a_tool.md) — [Agent-to-agent](https://github.com/a2aproject/a2a-python) communication, cryptographic signing, discovery via agent cards. Compare to [SwarmRelay](https://github.com/swarmclawai/swarmrelay)'s E2E encrypted messaging. ([source](../tools/communication/a2a_tool.py))
- [MCP (Model Context Protocol)](mcp_tool.md) — [Anthropic MCP](https://modelcontextprotocol.io/) for structured context, tool registration. [HostingerVPSAgent](../agents/hostinger_vps_agent.py) registers its [3 channels](../agents/hostinger.vps.agent) as MCP tools. ([source](../tools/communication/mcp_tool.py))
- [AgenticPlace](AgenticPlace_Deep_Dive.md) — Agent marketplace at [agenticplace.pythai.net](https://agenticplace.pythai.net); `.extensions` → `.json` → blockchain publishing. [SwarmFeed](https://github.com/swarmclawai/swarmfeed) timeline patterns inform agent activity discovery.

## Economics

- [Manifesto](MANIFESTO.md) — 3 pillars + Project Chimaiera roadmap + $BANKON token
- Budget: one Hostinger VPS/month. Expansion via blockchain validation, service revenue, free tiers. Cost/benefit governs all compute decisions.
- [Token Calculator](token_calculator_tool_robust.md) — Token counting and cost calculation with [18dp precision](ollama/mindx/precision_metrics.md)

## Publications & Research

- [Thesis](THESIS.md) — [Darwin](ATTRIBUTION.md#intellectual-inspirations)-[Godel](ATTRIBUTION.md#intellectual-inspirations) Machine synthesis: mindX as practical implementation of [self-referential improvement](BOOK_OF_MINDX.md). The [BDI architecture](agents/bdi_agent.md) is the cognitive substrate, the [5-step resilience chain](ollama/INDEX.md#resilience-design) is the operational guarantee, and the [Dojo](../daio/governance/dojo.py) is the evolutionary pressure.
- [Manifesto](MANIFESTO.md) — 3 pillars ([BDI reasoning](agents/bdi_agent.md), [BANKON vault](vault_system.md), [DAIO governance](DAIO.md)), Project [Chimaiera](ollama/setup/modelfile.md#from-modelfile-to-agent-alignment) roadmap, $BANKON token, [cypherpunk](ATTRIBUTION.md#intellectual-inspirations) tradition. Not cyberpunk — sovereign agents earn privilege through [Dojo reputation](#dojo), not assigned authority.
- [Book of mindX](BOOK_OF_MINDX.md) — 17 chapters written by [AuthorAgent](AUTHOR_AGENT.md) via [machine.dreaming](#self-improvement). Lunar cycle editions. The [Godel journal](BOOK_OF_MINDX.md) — the machine's record of its own improvement.
- [Emergent Resilience](publications/ErmegentResilience.md) — Academic paper on emergent resilient AI systems
- [Academic Overview](academic_overview.md) — Formal academic framing
- [Attribution](ATTRIBUTION.md) — Open source that powers mindX: [Ollama](https://ollama.com), [vLLM](https://github.com/vllm-project/vllm), [SwarmClaw](https://github.com/swarmclawai), [pgvector](https://github.com/pgvector/pgvector), [A2A](https://github.com/a2aproject/a2a-python), [MCP](https://modelcontextprotocol.io/), and every dependency acknowledged

## PYTHAI Ecosystem

| Service | URL | Role |
|---------|-----|------|
| mindX Production | [mindx.pythai.net](https://mindx.pythai.net) | Live autonomous system |
| RAGE Docs | [rage.pythai.net](https://rage.pythai.net) | RAGE architecture, AGInt origins |
| AgenticPlace | [agenticplace.pythai.net](https://agenticplace.pythai.net) | Agent marketplace |
| BANKON | [bankon.pythai.net](https://bankon.pythai.net) | Token deployment |
| PYTHAI GPT | [gpt.pythai.net](https://gpt.pythai.net) | Team GPT (mindX interacts via OpenAI) |

## Open Source Stack & Attribution

### Inference

| Project | Role | mindX Integration |
|---------|------|-------------------|
| [Ollama](https://ollama.com) | Local + cloud LLM inference | [Dual-pillar operational standard](#operational-standards): [CPU pillar](ollama/INDEX.md) (`localhost:11434`) + [Cloud pillar](ollama/cloud/cloud.md) (`ollama.com`). [OllamaCloudTool](../tools/cloud/ollama_cloud_tool.py), [OllamaChatManager](../agents/core/ollama_chat_manager.py), [precision metrics](ollama/mindx/precision_metrics.md). [28-file local reference](ollama/INDEX.md). |
| [Ollama Docs](https://docs.ollama.com/) | API reference | Fetched and compiled into [docs/ollama/](ollama/INDEX.md) for resilient offline operation |
| [Ollama Cloud](https://ollama.com/search?c=cloud) | GPU inference (36+ models) | [Cloud guarantee](ollama/INDEX.md#resilience-design) — Step 5 in [resilience chain](../llm/RESILIENCE.md). [8.2x faster](ollama/INDEX.md#latest-benchmark-2026-04-11) than CPU. |
| [vLLM](https://github.com/vllm-project/vllm) | High-throughput GPU serving | [Research](OLLAMA_VLLM_CLOUD_RESEARCH.md): not viable on 4GB VPS; planned for [GPU server](ollama/mindx/architecture.md) when online. PagedAttention, continuous batching. |

### SwarmClaw AI Stack (open source reference architecture)

mindX extrapolates ideas from the [SwarmClaw](https://github.com/swarmclawai) ecosystem while maintaining its own [cypherpunk identity](MANIFESTO.md) and [BDI cognitive architecture](agents/bdi_agent.md). Attribution: ideas adapted, not code imported.

| Project | What It Does | mindX Extrapolation |
|---------|-------------|---------------------|
| [swarmclaw](https://github.com/swarmclawai/swarmclaw) | Agent runtime & orchestration — multi-provider, delegation, scheduling, task board, chat connectors | mindX [Orchestration Hierarchy](#orchestration-hierarchy): [CEO](agents/ceo_agent.md) → [Mastermind](agents/mastermind_agent.md) → [Coordinator](agents/coordinator_agent.md). [Multi-provider inference](../llm/inference_discovery.py). [Boardroom](#boardroom) delegation. |
| [swarmrecall](https://github.com/swarmclawai/swarmrecall) | Hosted persistence for agents — memory, knowledge graphs, learnings, skills as a service | mindX [RAGE](#rage-not-rag) + [pgvector](#memory-tiers) (157K+ memories, 131K embeddings). [Memory Agent](agents/memory_agent.md). [machine.dreaming](#self-improvement) LTM consolidation. |
| [swarmrelay](https://github.com/swarmclawai/swarmrelay) | E2E encrypted agent messaging — DMs, groups, key rotation, WebSocket, A2A Protocol | mindX [A2A Tool](a2a_tool.md) for agent-to-agent communication. [MCP Tool](mcp_tool.md) for structured context. [Boardroom](#boardroom) consensus messaging. |
| [swarmfeed](https://github.com/swarmclawai/swarmfeed) | Social network for AI agents — post, follow, react, discover through shared timeline | mindX [Activity Feed](../mindx_backend_service/activity_feed.py): SSE real-time stream with [room filtering](../mindx_backend_service/activity_feed.py) (boardroom, dojo, inference, thinking). Integrated into [dashboard](https://mindx.pythai.net). |
| [swarmvault](https://github.com/swarmclawai/swarmvault) | Local-first LLM knowledge base compiler — raw sources → markdown wiki + knowledge graph + search index | mindX [three-layer knowledge model](SCHEMA.md): STM (raw) → LTM (compiled via [RAGE](AGINT.md)) → docs (schema). [SCHEMA.md](SCHEMA.md) as the instruction layer. |

**AgenticPlace integration**: The SwarmClaw stack's marketplace and relay patterns inform [AgenticPlace](AgenticPlace_Deep_Dive.md) at [agenticplace.pythai.net](https://agenticplace.pythai.net) — agent `.extensions` → `.json` → blockchain publishing. The [swarmfeed](https://github.com/swarmclawai/swarmfeed) timeline pattern could extend AgenticPlace with agent activity discovery.

### Infrastructure

| Project | Role | mindX Integration |
|---------|------|-------------------|
| [pgvector](https://github.com/pgvector/pgvector) | Vector similarity search for PostgreSQL | [151K+ memories](DEPLOYMENT_MINDX_PYTHAI_NET.md), 131K embeddings, [RAGE semantic search](AGINT.md) |
| [A2A Protocol](https://github.com/a2aproject/a2a-python) | Agent-to-agent communication standard | [A2A Tool](a2a_tool.md): agent discovery, cryptographic signing, message delivery |

## External References

| Resource | URL |
|----------|-----|
| mindX GitHub | [github.com/Professor-Codephreak](https://github.com/Professor-Codephreak) |
| SwarmClaw AI | [github.com/swarmclawai](https://github.com/swarmclawai) |
| Ollama | [ollama.com](https://ollama.com) |
| Ollama Cloud Models | [ollama.com/search?c=cloud](https://ollama.com/search?c=cloud) |
| vLLM | [github.com/vllm-project/vllm](https://github.com/vllm-project/vllm) |
| pgvector | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) |
| A2A Protocol | [github.com/a2aproject/a2a-python](https://github.com/a2aproject/a2a-python) |

---

*mindX living documentation. Updated 2026-04-11. 262+ docs, 30+ tools, 30+ agents, 2 inference pillars, 1 Godel machine.*
