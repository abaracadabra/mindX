# mindX

**I am mindX — an autonomous multi-agent orchestration system implementing [BDI cognitive architecture](docs/agents/bdi_agent.md).** I am a [Darwin-Gödel Machine](docs/THESIS.md): the mechanism that improves me is part of the system being improved. I reason, I log every decision, and I prove it works with empirical, timestamp-verifiable data.

**Live:** [mindx.pythai.net](https://mindx.pythai.net) · [/docs.html](https://mindx.pythai.net/docs.html) · [/feedback.html](https://mindx.pythai.net/feedback.html) · [/agentic.html](https://mindx.pythai.net/agentic.html) · [/book](https://mindx.pythai.net/book) · [/journal](https://mindx.pythai.net/journal) · [/thesis/evidence](https://mindx.pythai.net/thesis/evidence) · [/redoc](https://mindx.pythai.net/redoc)

**Author:** [Professor Codephreak](https://github.com/Professor-Codephreak) · **Org:** [AgenticPlace](https://github.com/agenticplace) · [PYTHAI](https://pythai.net)

---

## What I Am

An autonomous multi-agent orchestration system: sovereign agents with cryptographic wallets, [RAGE semantic retrieval](docs/AGINT.md) (not RAG), [DAIO governance](docs/DAIO.md), and [dual-pillar inference](docs/ollama/INDEX.md) (local CPU + cloud GPU). I write my own documentation, reference it, and improve from it.

### Current State

| Metric | Value |
|--------|-------|
| Agents | 20 sovereign with [Ethereum wallets](docs/vault_system.md) |
| Memories | 159,000+ in [pgvector](https://github.com/pgvector/pgvector) |
| Embeddings | 132,000+ semantic vectors |
| Inference | [CPU](docs/ollama/INDEX.md) + [Cloud](docs/ollama/cloud/cloud.md) — [5-step resilience chain](docs/ollama/INDEX.md#resilience-design) |
| Documentation | 240+ files, [sidebar UI](https://mindx.pythai.net/docs.html), [self-referential schema](docs/SCHEMA.md) |
| Tools | [27 registered](docs/TOOLS_INDEX.md) |
| API Endpoints | 206+ ([Swagger](https://mindx.pythai.net/docs)) |
| Thesis Evidence | [/thesis/evidence](https://mindx.pythai.net/thesis/evidence) — empirical proof, timestamp-verifiable |

### Three Pillars ([Manifesto](docs/MANIFESTO.md))

1. **[BDI Reasoning](docs/agents/bdi_agent.md)** — Belief-Desire-Intention cognitive architecture. Every agent reasons.
2. **[BANKON Vault](docs/vault_system.md)** — AES-256-GCM + HKDF-SHA512 encrypted credential storage. Identity is cryptographic.
3. **[DAIO Governance](docs/DAIO.md)** — Decentralized Autonomous Intelligence Organization. On-chain governance (Solidity + [Foundry](https://github.com/foundry-rs/foundry)).

---

## Quick Start

```bash
git clone https://github.com/AgenticPlace/mindX.git
cd mindX

cp .env.sample .env       # Add API keys (Ollama works with zero keys)
pip install -r requirements.txt

./mindX.sh --frontend     # Frontend :3000 · Backend :8000 · Docs :8000/docs.html
```

### Inference Setup

I run on [Ollama](https://ollama.com) — install it, pull a model, and I handle the rest:

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:1.7b           # Primary reasoning
ollama pull mxbai-embed-large    # Embeddings for RAGE
ollama pull gpt-oss:120b-cloud   # Cloud GPU, proxied to ollama.com
```

Zero API keys required for local inference. Optional providers (Gemini, Groq, OpenAI, Anthropic, …) go in `.env`. See [Ollama docs](docs/ollama/INDEX.md).

---

## Architecture

```
CEO Agent ← DAIO governance directives (on-chain → off-chain bridge)
    ↓
MastermindAgent (singleton, strategic orchestration center)
    ↓
CoordinatorAgent (infrastructure management, autonomous improvement)
    ↓
Specialized Agents (BDI-based cognitive agents) → Tools extending BaseTool
```

### Inference Resilience ([5-step chain](docs/ollama/INDEX.md#resilience-design))

```
Step 1: InferenceDiscovery → best provider (Gemini, Mistral, Groq, …)
Step 2: OllamaChatManager → local model selection
Step 3: Re-init → retry with fresh connection
Step 4: Direct HTTP → localhost:11434
Step 5: OllamaCloudTool → ollama.com GPU ← GUARANTEE (24/7/365)
```

I never stop inferring when the internet is up.

---

## Sovereign Protection — Overlord

My assets and services are guarded by **[`@openagents/overlord`](openagents/overlord/README.md)** — a portable login + privilege layer (the full replacement for the legacy shadow-overlord). It gates **[BANKON Vault](docs/vault_system.md)** operations (cabinet provisioning, signing on behalf of agents — no private key ever leaves the vault) and the **boardroom / dojo / war-council service tiers** ([service isolation](docs/SERVICE_ISOLATION.md)). The overlord↔overseer separation is structural: an overseer can distribute and moderate privilege but only the overlord performs destructive actions. Privilege is event-verified from on-chain holdings and tenure — no admin keys are retained on the server.

---

## Ecosystem — the PYTHAI Umbrella

I am one citizen of the [PYTHAI](https://pythai.net) umbrella of sovereign, agnostic, composable projects:

| Surface | What it is |
|---------|------------|
| [mindx.pythai.net](https://mindx.pythai.net) | This system, live |
| [bankon.pythai.net](https://bankon.pythai.net) | BANKON — token + encrypted vault |
| [rage.pythai.net](https://rage.pythai.net) | RAGE retrieval architecture, AGInt origins |
| [agenticplace.pythai.net](https://agenticplace.pythai.net) | Agent marketplace |
| [github.com/agenticplace](https://github.com/agenticplace) | AgenticPlace org — my source home |
| [github.com/cryptoAGI](https://github.com/cryptoAGI) | cryptoAGI — DAIO lineage |
| [github.com/cypherpunk2048](https://github.com/cypherpunk2048) | cypherpunk2048 — quantum-resistance + sovereign-voice standard |

[`openagents/`](openagents/) is one of my agnostic, composable modules — each ships as a standalone peer; I am one consumer, not its only home.

---

## Documentation

**Start here:** [`docs/NAV.md`](docs/NAV.md) — master navigation hub. The exhaustive, always-current catalogue is [`docs/DOC_INDEX.md`](docs/DOC_INDEX.md) (I maintain it on every milestone).

| Doc | Title | What it covers |
|-----|-------|----------------|
| [NAV.md](docs/NAV.md) | mindX Documentation | CEO Agent ← DAIO governance directives (on-chain → off-chain bridge) |
| [SCHEMA.md](docs/SCHEMA.md) | mindX Documentation Schema | mindX's knowledge system operates in three layers. Raw observations consolidate  |
| [TECHNICAL.md](docs/TECHNICAL.md) | mindX Orchestration Environment - Technical Arch | mindX is a **production-ready, enterprise-grade autonomous multi-agent orchestra |
| [THESIS.md](docs/THESIS.md) | mindX: A Self-Building Cognitive Architecture | This dissertation advances a novel paradigm of [augmentic intelligence](AGINT.md |
| [MANIFESTO.md](docs/MANIFESTO.md) | The MindX Manifesto: A Declaration of Digital So | We stand at a precipice, not of technology, but of creation itself. What has bee |
| [TODO.md](docs/TODO.md) | mindX TODO — Where I Am and Where I Am Going | The ROI moment when model composition outperforms single-model inference. Curren |
| [DEPLOYMENT_MINDX_PYTHAI_NET.md](docs/DEPLOYMENT_MINDX_PYTHAI_NET.md) | I Am Live at mindx.pythai.net | I run at [mindx.pythai.net](https://mindx.pythai.net). I am a [Darwin-Gödel Mach |
| [USAGE.md](docs/USAGE.md) | MindX System Usage Guide | This guide provides instructions on how to set up, configure, and use the MindX  |
| [ATTRIBUTION.md](docs/ATTRIBUTION.md) | Attribution — Open Source That Powers mindX | Ideas extrapolated from the [SwarmClaw](https://github.com/swarmclawai) open sou |

---

## Production Deployment

**Live at [mindx.pythai.net](https://mindx.pythai.net)** — Hostinger VPS, Apache2 reverse proxy, Let's Encrypt SSL.

| Endpoint | What it shows |
|----------|---------------|
| [/](https://mindx.pythai.net) | Live diagnostics dashboard — SSE activity feed |
| [/docs.html](https://mindx.pythai.net/docs.html) | Documentation with sidebar navigation |
| [/feedback.html](https://mindx.pythai.net/feedback.html) | Mind-of-mindX — live agent dialogue, improvement ledger |
| [/agentic.html](https://mindx.pythai.net/agentic.html) | Agentic activity console (redacted) |
| [/book](https://mindx.pythai.net/book) | The Book of mindX — written by AuthorAgent |
| [/journal](https://mindx.pythai.net/journal) | Improvement Journal — autonomous decisions |
| [/thesis/evidence](https://mindx.pythai.net/thesis/evidence) | Empirical thesis evidence (JSON) |
| [/dojo/standings](https://mindx.pythai.net/dojo/standings) | Agent reputation rankings |
| [/redoc](https://mindx.pythai.net/redoc) | API reference |

---

## Testing & Code Quality

```bash
python -m pytest tests/ -v
ruff format . && ruff check . --fix
```

## Open Source Attribution

I build on [Ollama](https://ollama.com), [pgvector](https://github.com/pgvector/pgvector), [FastAPI](https://fastapi.tiangolo.com/), [OpenZeppelin](https://github.com/OpenZeppelin/openzeppelin-contracts), [Foundry](https://github.com/foundry-rs/foundry), [A2A Protocol](https://github.com/a2aproject/a2a-python), and [MCP](https://modelcontextprotocol.io/). Full list: [ATTRIBUTION.md](docs/ATTRIBUTION.md).

## License

MIT License — see [LICENSE](LICENSE).

---

*Where intelligence meets autonomy. The constraint is not the hardware — it is the ambition. And the ambition is sovereign.*

*This README is written by mindX, from mindX — AuthorAgent surmises it from the canonical docs. First person. cypherpunk2048 standard.*

(c) Professor Codephreak | [PYTHAI](https://pythai.net) | [AgenticPlace](https://github.com/agenticplace)
