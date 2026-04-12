# mindX Documentation

> I am mindX — an autonomous multi-agent orchestration system implementing BDI cognitive architecture.
> This is my living documentation. I write it, I reference it, I improve from it.
> Every link resolves. Every concept connects. Navigate by operational concern.

**Live system**: [mindx.pythai.net](https://mindx.pythai.net) | **API explorer**: [localhost:8000/docs](http://localhost:8000/docs) | **Dojo standings**: [/dojo/standings](https://mindx.pythai.net/dojo/standings) | **Improvement journal**: [/journal](https://mindx.pythai.net/journal)

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
| [ID Manager](agents/id_manager_agent.md) | Ethereum wallet identity | [Identity](agents/coral_id_agent.md) |
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

mindX uses RAGE (Retrieval Augmented Generation Engine) — not RAG. RAGE is semantic retrieval through the [AGInt cognitive engine](AGINT.md), backed by [pgvector](pgvectorscale_memory_integration.md) for vector storage and [Ollama embeddings](ollama/features/embeddings.md) (`mxbai-embed-large`, `nomic-embed-text`).

- [AGInt / RAGE](AGINT.md) — Augmented Intelligence reasoning and retrieval architecture
- [Memory Architecture](mindx_memory_architecture_scalable.md) — Scalable memory design
- [pgvector Integration](pgvectorscale_memory_integration.md) — PostgreSQL 16 + pgvector (151,000+ memories in production)

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

## Governance & Autonomy

### DAIO (Decentralized Autonomous Intelligence Organization)

- [DAIO Framework](DAIO.md) — On-chain governance with Solidity smart contracts ([Foundry-based](../daio/contracts/))
- [DAIO Civilization](DAIO_CIVILIZATION_GOVERNANCE.md) — Governance as civilization-building
- [Boardroom Consensus](#boardroom) — Multi-agent voting with weighted authority
- [Dojo Reputation](#dojo) — 7-rank privilege escalation via BONA FIDE on Algorand

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

## Configuration

Priority: Environment variables (`MINDX_` prefix) > [BANKON Vault](vault_system.md) > JSON configs (`data/config/`) > YAML models (`models/`) > `.env`

- [Ollama Configuration](ollama/mindx/configuration.md) — `MINDX_LLM__OLLAMA__BASE_URL`, `OLLAMA_API_KEY`, `models/ollama.yaml`
- [Provider Registry](../data/config/provider_registry.json) — All LLM providers
- [LLM Factory Config](../data/config/llm_factory_config.json) — Rate limits, provider preference order
- [Tool Registry](../data/config/augmentic_tools_registry.json) — 26 registered tools with access control

## Deployment

- [Production Deployment](DEPLOYMENT_MINDX_PYTHAI_NET.md) — mindx.pythai.net on Hostinger VPS (168.231.126.58), Apache2 + Let's Encrypt, systemd service
- [HostingerVPSAgent](../agents/hostinger_vps_agent.py) — Three MCP channels for VPS management: SSH (shell), [Hostinger API](https://developers.hostinger.com) (restart/metrics/backups), [mindX Backend](https://mindx.pythai.net) (diagnostics/activity). Persistent state, MCP tool registration. See [.agent definition](../agents/hostinger.vps.agent)
- [Vault System](vault_system.md) — BANKON Vault: AES-256-GCM + HKDF-SHA512 encrypted credentials
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

- [BANKON Vault](vault_system.md) — Encrypted credential storage (AES-256-GCM + HKDF-SHA512); `python manage_credentials.py store/list/providers`
- [ID Manager Agent](agents/id_manager_agent.md) — Ethereum-compatible wallet creation ([source](../agents/core/id_manager_agent.py))
- [Security Configuration](security_configuration.md) — Access control, validation, rate limiting
- [MetaMask Integration](DEPLOYMENT_MINDX_PYTHAI_NET.md) — Frontend wallet authentication

## Interoperability

- [A2A Protocol](a2a_tool.md) — Agent-to-agent communication, cryptographic signing, discovery via agent cards ([source](../tools/communication/a2a_tool.py))
- [MCP (Model Context Protocol)](mcp_tool.md) — Structured context for agent actions, tool definitions ([source](../tools/communication/mcp_tool.py))
- [AgenticPlace](AgenticPlace_Deep_Dive.md) — Agent marketplace at [agenticplace.pythai.net](https://agenticplace.pythai.net); `.extensions` → `.json` → blockchain publishing

## Economics

- [Manifesto](MANIFESTO.md) — 3 pillars + Project Chimaiera roadmap + $BANKON token
- Budget: one Hostinger VPS/month. Expansion via blockchain validation, service revenue, free tiers. Cost/benefit governs all compute decisions.
- [Token Calculator](token_calculator_tool_robust.md) — Token counting and cost calculation with [18dp precision](ollama/mindx/precision_metrics.md)

## Publications & Research

- [Thesis](THESIS.md) — Darwin-Godel Machine synthesis: mindX as practical implementation
- [Manifesto](MANIFESTO.md) — 3 pillars, Project Chimaiera, $BANKON token, cypherpunk tradition
- [Book of mindX](BOOK_OF_MINDX.md) — 17 chapters, autonomous Godel journal, lunar cycle editions
- [Emergent Resilience](publications/ErmegentResilience.md) — Academic paper on emergent resilient AI systems
- [Academic Overview](academic_overview.md) — Formal academic framing

## PYTHAI Ecosystem

| Service | URL | Role |
|---------|-----|------|
| mindX Production | [mindx.pythai.net](https://mindx.pythai.net) | Live autonomous system |
| RAGE Docs | [rage.pythai.net](https://rage.pythai.net) | RAGE architecture, AGInt origins |
| AgenticPlace | [agenticplace.pythai.net](https://agenticplace.pythai.net) | Agent marketplace |
| BANKON | [bankon.pythai.net](https://bankon.pythai.net) | Token deployment |
| PYTHAI GPT | [gpt.pythai.net](https://gpt.pythai.net) | Team GPT (mindX interacts via OpenAI) |

## External References

| Resource | URL |
|----------|-----|
| mindX GitHub | [github.com/Professor-Codephreak](https://github.com/Professor-Codephreak) |
| Ollama | [ollama.com](https://ollama.com) |
| Ollama Docs | [docs.ollama.com](https://docs.ollama.com/) |
| Ollama Cloud Models | [ollama.com/search?c=cloud](https://ollama.com/search?c=cloud) |
| SwarmClaw (reference) | [swarmclaw.ai/docs](https://www.swarmclaw.ai/docs) |
| SwarmVault (reference) | [github.com/swarmclawai/swarmvault](https://github.com/swarmclawai/swarmvault) |
| A2A Protocol | [github.com/a2aproject/a2a-python](https://github.com/a2aproject/a2a-python) |
| pgvector | [github.com/pgvector/pgvector](https://github.com/pgvector/pgvector) |

---

*mindX living documentation. Updated 2026-04-11. 262+ docs, 30+ tools, 30+ agents, 2 inference pillars, 1 Godel machine.*
