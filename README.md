# mindX

[![tests](https://github.com/AgenticPlace/openagents/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/AgenticPlace/openagents/actions/workflows/test.yml)
&nbsp;**190/190 tests passing** in clean CI · **80% line coverage** on Cabinet code

> 🏆 **ETHGlobal Open Agents submission lives at [`openagents/`](openagents/) — start with [`openagents/README.md`](openagents/README.md).**
> If you're a judge: jump directly to **[`openagents/docs/JUDGE_TOUR.md`](openagents/docs/JUDGE_TOUR.md)** for the 5-minute verification path. Live demo: [https://mindx.pythai.net/openagents](https://mindx.pythai.net/openagents).
> Submission text: [`openagents/docs/SUBMISSIONS.md`](openagents/docs/SUBMISSIONS.md). Test results: [`tests/results/2026-05-02/SUMMARY.md`](tests/results/2026-05-02/SUMMARY.md). 190 tests passing across 7 suites.

---

**I am a Darwin-Godel Machine.** I improve myself, log every decision, and prove it works with empirical data.

**Live:** [mindx.pythai.net](https://mindx.pythai.net) | **Docs:** [/docs.html](https://mindx.pythai.net/docs.html) | **API:** [/redoc](https://mindx.pythai.net/redoc) | **Thesis Evidence:** [/thesis/evidence](https://mindx.pythai.net/thesis/evidence) | **Book:** [/book](https://mindx.pythai.net/book)

**Author:** [Professor Codephreak](https://github.com/Professor-Codephreak) | **Org:** [AgenticPlace](https://github.com/agenticplace) | [PYTHAI](https://pythai.net)

---

## What mindX Is

An autonomous multi-agent orchestration system implementing [BDI cognitive architecture](docs/agents/bdi_agent.md). A [Godel machine](docs/THESIS.md) — a self-improving system where the improvement mechanism is part of the system being improved. 20 sovereign agents with cryptographic wallets, [RAGE semantic search](docs/AGINT.md) (not RAG), [DAIO governance](docs/DAIO.md), and [dual-pillar inference](docs/ollama/INDEX.md) (CPU + Cloud).

### Current State (2026-04-12)

| Metric | Value |
|--------|-------|
| Agents | 20 sovereign with [Ethereum wallets](docs/vault_system.md) |
| Memories | 159,000+ in [pgvector](https://github.com/pgvector/pgvector) |
| Embeddings | 132,000+ semantic vectors |
| Inference | [CPU](docs/ollama/INDEX.md) (~8 tok/s) + [Cloud](docs/ollama/cloud/cloud.md) (~65 tok/s) — [5-step resilience chain](docs/ollama/INDEX.md#resilience-design) |
| Documentation | 262+ files, [sidebar UI](https://mindx.pythai.net/docs.html), [self-referential schema](docs/SCHEMA.md) |
| Tools | [31+ registered](docs/TOOLS_INDEX.md) |
| API Endpoints | 206+ ([Swagger](https://mindx.pythai.net/docs)) |
| Thesis Evidence | [/thesis/evidence](https://mindx.pythai.net/thesis/evidence) — empirical proof, timestamp-verifiable |

### Three Pillars ([Manifesto](docs/MANIFESTO.md))

1. **[BDI Reasoning](docs/agents/bdi_agent.md)** — Belief-Desire-Intention cognitive architecture. Every agent reasons.
2. **[BANKON Vault](docs/vault_system.md)** — AES-256-GCM + HKDF-SHA512 encrypted credential storage. Identity is cryptographic.
3. **[DAIO Governance](docs/DAIO.md)** — Decentralized Autonomous Intelligence Organization. On-chain governance (Solidity + [Foundry](https://github.com/foundry-rs/foundry)).

---

## Quick Start

```bash
# Clone
git clone https://github.com/AgenticPlace/mindX.git
cd mindX

# Setup
cp .env.sample .env       # Add API keys (Ollama works with zero keys)
pip install -r requirements.txt

# Run (recommended)
./mindX.sh --frontend

# Access
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
# Docs:      http://localhost:8000/docs.html
```

### Inference Setup

mindX runs on [Ollama](https://ollama.com) — install it, pull a model, and mindX handles the rest:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull models
ollama pull qwen3:1.7b           # Primary reasoning (1.4GB)
ollama pull mxbai-embed-large    # Embeddings for RAGE (669MB)

# Cloud models (free tier, no API key via local proxy)
ollama pull gpt-oss:120b-cloud   # 120B on GPU, proxied to ollama.com
```

Zero API keys required for local inference. Cloud extends to 36+ models at [ollama.com](https://ollama.com/search?c=cloud). See [Ollama docs](docs/ollama/INDEX.md) for the complete reference.

### Other Providers (Optional)

```bash
# Add to .env for additional providers
GEMINI_API_KEY=...      # Google AI Studio
GROQ_API_KEY=...        # Groq
OPENAI_API_KEY=...      # OpenAI
ANTHROPIC_API_KEY=...   # Anthropic
```

---

## Architecture

```
CEO Agent ← DAIO governance directives (on-chain → off-chain bridge)
    ↓
MastermindAgent (singleton, strategic orchestration center)
    ↓
CoordinatorAgent (infrastructure management, autonomous improvement)
    ↓
20+ Specialized Agents (BDI-based cognitive agents)
    ↓
31+ Tools extending BaseTool (registered in augmentic_tools_registry.json)
```

### Inference Resilience ([5-step chain](docs/ollama/INDEX.md#resilience-design))

```
Step 1: InferenceDiscovery → best provider (Gemini, Mistral, Groq, etc.)
Step 2: OllamaChatManager → local model selection
Step 3: Re-init → retry with fresh connection
Step 4: Direct HTTP → localhost:11434
Step 5: OllamaCloudTool → ollama.com GPU ← GUARANTEE (24/7/365)
```

mindX never stops inferring when the internet is up.

### Key Components

| Component | File | Role |
|-----------|------|------|
| [mindXagent](agents/core/mindXagent.py) | Autonomous core | 5-minute improvement cycles, [Godel journal](docs/BOOK_OF_MINDX.md) |
| [OllamaCloudTool](tools/cloud/ollama_cloud_tool.py) | Cloud inference | 9 operations, [18dp precision](docs/ollama/mindx/precision_metrics.md), branch-ready |
| [Boardroom](daio/governance/boardroom.py) | Consensus | CEO + 7 soldiers, weighted voting, dissent branches |
| [Dojo](daio/governance/dojo.py) | Reputation | 7 ranks (Novice → Sovereign), BONA FIDE |
| [ActivityFeed](mindx_backend_service/activity_feed.py) | Real-time | SSE stream, room filtering, [dashboard](https://mindx.pythai.net) integration |
| [ThesisEvidence](mindx_backend_service/thesis_evidence.py) | Scientific proof | Collects empirical data, evaluates 6 thesis claims |
| [HostingerVPSAgent](agents/hostinger_vps_agent.py) | Deployment | 3 MCP channels: SSH + [Hostinger API](https://developers.hostinger.com) + Backend HTTPS |
| [PrecisionMetrics](llm/precision_metrics.py) | Token tracking | 18 decimal places, `Decimal`, actual counts from Ollama API |

---

## Documentation

**Start here:** [`docs/NAV.md`](docs/NAV.md) — master navigation hub with 150+ hyperlinks across 40+ sections.

| Doc | What It Covers |
|-----|----------------|
| [NAV.md](docs/NAV.md) | Master navigation — every agent, tool, concept linked |
| [SCHEMA.md](docs/SCHEMA.md) | How to maintain the docs (self-referential instruction layer) |
| [TECHNICAL.md](docs/TECHNICAL.md) | 3,800-line definitive technical reference |
| [TODO.md](docs/TODO.md) | Honest assessment — 5.7/10, what's working, what's broken, what's next |
| [ATTRIBUTION.md](docs/ATTRIBUTION.md) | Open source that powers mindX |
| [Ollama Reference](docs/ollama/INDEX.md) | 28-file self-contained Ollama docs |
| [THESIS.md](docs/THESIS.md) | Darwin-Godel Machine synthesis |
| [MANIFESTO.md](docs/MANIFESTO.md) | 3 pillars, Chimaiera roadmap, cypherpunk tradition |
| [DEPLOYMENT](docs/DEPLOYMENT_MINDX_PYTHAI_NET.md) | Production at mindx.pythai.net |
| [USAGE.md](docs/USAGE.md) | Detailed usage guide |

---

## Production Deployment

**Live at [mindx.pythai.net](https://mindx.pythai.net)** — Hostinger VPS, 2 CPU, 8GB RAM, Ubuntu 24.04.

| Endpoint | What It Shows |
|----------|---------------|
| [/](https://mindx.pythai.net) | Live diagnostics dashboard — deep expandable panels, SSE activity feed |
| [/docs.html](https://mindx.pythai.net/docs.html) | Documentation with sidebar navigation |
| [/book](https://mindx.pythai.net/book) | The Book of mindX — written by AuthorAgent |
| [/journal](https://mindx.pythai.net/journal) | Improvement Journal — autonomous decisions |
| [/thesis/evidence](https://mindx.pythai.net/thesis/evidence) | Empirical thesis evidence (JSON) |
| [/dojo/standings](https://mindx.pythai.net/dojo/standings) | Agent reputation rankings |
| [/inference/status](https://mindx.pythai.net/inference/status) | Inference provider availability |
| [/activity/stream](https://mindx.pythai.net/activity/stream) | SSE real-time activity feed |
| [/redoc](https://mindx.pythai.net/redoc) | API reference (206+ endpoints) |

---

## Testing

```bash
python -m pytest tests/ -v
python -m pytest tests/ --cov=mindx --cov-report=term-missing
```

## Code Quality

```bash
ruff format .
ruff check . --fix
mypy mindx/
```

---

## Open Source Attribution

mindX builds on: [Ollama](https://ollama.com), [vLLM](https://github.com/vllm-project/vllm), [pgvector](https://github.com/pgvector/pgvector), [FastAPI](https://fastapi.tiangolo.com/), [OpenZeppelin](https://github.com/OpenZeppelin/openzeppelin-contracts), [Foundry](https://github.com/foundry-rs/foundry), [A2A Protocol](https://github.com/a2aproject/a2a-python), [MCP](https://modelcontextprotocol.io/). Ideas extrapolated from [SwarmClaw](https://github.com/swarmclawai) (docs layout, activity feed, knowledge model). Full list: [ATTRIBUTION.md](docs/ATTRIBUTION.md).

## License

MIT License — See [LICENSE](LICENSE) for details.

---

*Where intelligence meets autonomy. The constraint is not the hardware — it is the ambition. And the ambition is sovereign.*

(c) Professor Codephreak | [PYTHAI](https://pythai.net) | [AgenticPlace](https://github.com/agenticplace)
