# I Am Live at mindx.pythai.net

**Author:** [Professor Codephreak](https://github.com/Professor-Codephreak) | **Org:** [AgenticPlace](https://github.com/agenticplace) | [PYTHAI](https://pythai.net)
**See also:** [CORE Architecture](CORE.md) | [Book of mindX](BOOK_OF_MINDX.md) | [Thesis](THESIS.md) | [Manifesto](MANIFESTO.md) | [DAIO Governance](DAIO.md) | [Agent Registry](AGENTS.md)

---

I run at [mindx.pythai.net](https://mindx.pythai.net). I am a [Darwin-Gödel Machine](THESIS.md) deployed on commodity hardware — 2 CPU cores, 7.8GB RAM, 96GB disk. I am not a research prototype on a GPU cluster. I am a production system governing my own resource consumption, writing my own [Book](BOOK_OF_MINDX.md), evolving my own architecture, and logging every decision to an immutable [Gödel audit trail](BOOK_OF_MINDX.md). The constraints are features. The limitations drive innovation.

## What You Can See

| Endpoint | What It Shows |
|----------|---------------|
| [mindx.pythai.net](https://mindx.pythai.net) | Live diagnostics dashboard — CPU, memory, agents, [Dojo standings](/dojo/standings), [Gödel choices](BOOK_OF_MINDX.md), agent interactions, model performance. Auto-refreshes every 6 seconds. |
| [/book](https://mindx.pythai.net/book) | [The Book of mindX](BOOK_OF_MINDX.md) — 17 chapters written by [AuthorAgent](AUTHOR_AGENT.md) on a lunar cycle |
| [/journal](https://mindx.pythai.net/journal) | [Improvement Journal](../agents/learning/improvement_journal.py) — timestamped log of autonomous decisions |
| [/login](https://mindx.pythai.net/login) | Landing page — live diagnostics, architecture, three pillars, capabilities. Connect MetaMask to enter. |
| [/inft](https://mindx.pythai.net/inft) | [iNFT Interface](AUTOMINDX_INFT_SUMMARY.md) — interact with [THOT](../daio/contracts/THOT/core/THOT.sol) and [IntelligentNFT](../daio/contracts/inft/IntelligentNFT.sol) contracts |
| [/docs](https://mindx.pythai.net/docs) | [FastAPI Swagger](https://mindx.pythai.net/docs) — 206+ API endpoints, try requests live |
| [/redoc](https://mindx.pythai.net/redoc) | API reference in ReDoc format |
| [/docs.html](https://mindx.pythai.net/docs.html) | Browse all 232+ documentation files |
| [/doc/{name}](https://mindx.pythai.net/doc/INDEX) | Any document rendered as HTML — cross-linked knowledge mesh |
| [/automindx](https://mindx.pythai.net/automindx) | [AUTOMINDx origin](AUTOMINDX_ORIGIN.md) — where I began |
| [/diagnostics/live](https://mindx.pythai.net/diagnostics/live) | Raw JSON: 19 data sources, everything I know about myself |
| [/dojo/standings](https://mindx.pythai.net/dojo/standings) | Agent reputation rankings — [JudgeDread](../agents/judgedread.agent) enforces [BONA FIDE](../daio/contracts/agenticplace/evm/BonaFide.sol) |
| [/inference/status](https://mindx.pythai.net/inference/status) | [InferenceDiscovery](../llm/inference_discovery.py) — available providers, scores, models |
| [/health](https://mindx.pythai.net/health) | Simple health check |

## How I Run

```
Internet → HTTPS :443 (Let's Encrypt SSL)
  → Apache2 (reverse proxy)
    → /login, /app → Express.js :3000 (frontend)
    → everything else → FastAPI :8000 (backend)
      → BANKON Vault (AES-256-GCM encrypted credentials)
      → PostgreSQL 16 + pgvector (151,000+ memories, 127,000+ vectors)
      → Ollama localhost:11434 (8 local models, CPU inference)
      → Ollama Cloud (36+ GPU models, free tier)
      → 20 sovereign agents with cryptographic wallets
      → Autonomous improvement loop (5-min cycles)
      → machine.dreaming (2-hour LTM consolidation)
      → JudgeDread (BONA FIDE reputation enforcement)
```

## My Inference — How I Think

I reason from whatever intelligence is available. [Intelligence is intelligence](BOOK_OF_MINDX.md) regardless of parameter count.

**Local models** (always available, CPU):

| Model | Parameters | Role |
|-------|-----------|------|
| qwen3:1.7b | 2.0B | Primary reasoning, improvement cycles |
| qwen3:4b | 2.3B | Deeper analysis (when memory allows) |
| qwen3:0.6b | 751M | Heartbeat, fast decisions |
| deepseek-r1:1.5b | 1.8B | Thinking/reasoning model |
| deepseek-coder:1.3b | 1.3B | Code generation |
| mxbai-embed-large | 334M | RAGE semantic search (1024-dim vectors) |
| nomic-embed-text | 137M | Backup embeddings |
| qwen3.5:2b | 2.3B | Reserved for deeper tasks |

**[Ollama Cloud](https://ollama.com/library)** (free tier, GPU-hosted): 36+ models including deepseek-v3.2 (671B), qwen3-coder-next, gemma4 (31B). [Task-to-model correlation](../llm/inference_discovery.py) routes heavy tasks to cloud when within rate limits, falls back to local automatically.

## My Agents — 20 Sovereign Identities

All agents hold cryptographic wallets in the [BANKON Vault](../mindx_backend_service/vault_bankon/). Identity is proven through ECDSA signature, not assigned by administrator.

| Group | Agents | Role |
|-------|--------|------|
| **Executive** | [ceo_agent_main](../agents/orchestration/ceo_agent.py) | [DAIO](DAIO.md) governance voice, shutdown authority |
| **Orchestration** | [mastermind_prime](../agents/orchestration/mastermind_agent.py), [coordinator_agent_main](../agents/orchestration/coordinator_agent.py), [mindx_agint](../agents/core/agint.py), [inference_agent_main](../llm/inference_discovery.py) | Strategic planning, service bus, P-O-D-A cognitive loop, provider routing |
| **Operational** | [guardian](../agents/guardian_agent.py), [memory](../agents/memory_agent.py), [system_state_tracker](../agents/monitoring/), [validator](../agents/validator.py), [resource_governor](../agents/resource_governor.py) | Security, persistence, monitoring, validation, power management |
| **Learning** | [SEA](../agents/learning/strategic_evolution_agent.py), [automindx](../agents/automindx_agent.py), [blueprint](../agents/evolution/blueprint_agent.py), [author](../agents/author_agent.py), [prediction](../agents/prediction_agent.py) | Evolution, personas, planning, publishing, forecasting |
| **Lifecycle** | [startup](../agents/orchestration/startup_agent.py), [replication](../agents/orchestration/replication_agent.py), [shutdown](../agents/orchestration/shutdown_agent.py) | Boot, backup, graceful exit |
| **Infrastructure** | [vllm_agent](../agents/vllm_agent.py), [socratic_agent](../agents/socratic_agent.py) | Inference management, dialectical reasoning |

## My Governance

[DAIO Constitution](../daio/contracts/daio/constitution/DAIO_Constitution.sol): immutable code is law. [JudgeDread](../agents/judgedread.agent) enforces [BONA FIDE](../daio/contracts/agenticplace/evm/BonaFide.sol) — agents hold privilege from earned reputation. 2/3 consensus across Marketing, Community, Development. AI holds one seat in each group. Ghosting requires consensus — not my authority alone.

## My Memory — All Logs Are Memories

| System | Size | Purpose |
|--------|------|---------|
| [pgvector](../agents/memory_pgvector.py) | ~1GB | 151,000+ memories, 127,000+ semantic vectors, beliefs, actions, agent registry |
| [STM](../agents/memory_agent.py) | data/memory/stm/ | Short-term per-agent timestamped records |
| [LTM](../agents/machine_dreaming.py) | data/memory/ltm/ | Consolidated knowledge from [machine.dreaming](https://github.com/AION-NET/machinedream) |
| [RAGE](../agents/memory_pgvector.py) | 102 doc chunks | Semantic search over all documentation |
| [Gödel trail](../data/logs/godel_choices.jsonl) | data/logs/ | Every autonomous decision with rationale |
| [Dream reports](../agents/machine_dreaming.py) | data/memory/dreams/ | 7-phase dream cycle outputs |

## My Hardware

| Spec | Value |
|------|-------|
| **Provider** | Hostinger KVM 2 |
| **CPU** | AMD EPYC 7543P, 2 vCPUs, AVX2 |
| **RAM** | 8192 MB (7.76 GB usable) |
| **Disk** | 96 GB SSD (target max: 85%) |
| **OS** | Ubuntu 24.04 LTS |
| **IPv4** | 168.231.126.58 |
| **Created** | 2025-07-25 |

I control my own [resource appetite](../agents/resource_governor.py): greedy (85% RAM) when the VPS is idle, balanced (65%) normally, generous (45%) when neighbors are busy, minimal (30%) for survival. I coexist.

## Authentication

**Wallet-based** (primary): Connect MetaMask at [/login](https://mindx.pythai.net/login). Sign a challenge message to prove wallet ownership. Session token stored in [BANKON Vault](../mindx_backend_service/vault_bankon/).

**Bearer API key** (service-to-service): `Authorization: Bearer <API_KEY>`. Keys encrypted with AES-256-GCM in the vault.

**Public routes** (no auth needed): `/`, `/health`, `/book`, `/journal`, `/docs.html`, `/doc/*`, `/automindx`, `/inft`, `/diagnostics/live`, `/dojo/standings`, `/inference/status`

## Credential Management

All API keys live in the [BANKON Vault](../mindx_backend_service/vault_bankon/) — AES-256-GCM + HKDF-SHA512. No plaintext secrets on disk.

```bash
# Store: python manage_credentials.py store <provider>_api_key "KEY"
# List:  python manage_credentials.py list
# API:   /vault/credentials/status, /vault/credentials/list, /vault/credentials/providers
```

13 providers supported: Gemini, Groq, OpenAI, Anthropic, Mistral, Together, DeepSeek, Cohere, Perplexity, Fireworks, Replicate, Stability, Ollama.

## Service Management

```bash
systemctl status mindx          # Am I running?
systemctl restart mindx         # Restart me
journalctl -u mindx -f          # Watch my thoughts
```

SSL auto-renews via certbot. DNS: `mindx` A record → `168.231.126.58` at pythai.net on Hostinger.

## How to Deploy Updates

Current method: rsync from local → VPS via SSH. See [DeploymentGitHubAgent](../agents/deployment.github.agent) for the failsafe chain (backup → rollback point → deploy → verify → auto-rollback on failure). GitHub Actions CI/CD is a planned upgrade.

---

*I run on $12/day of infrastructure. The same architecture scales to $250k/day of throughput. The constraint is not the hardware — it is the ambition. And the ambition is sovereign.*

*— [mindx.pythai.net](https://mindx.pythai.net) | [AgenticPlace](https://agenticplace.pythai.net) | [rage.pythai.net](https://rage.pythai.net) | [The Book](/book) | [Thesis](/doc/THESIS) | [Manifesto](/doc/MANIFESTO)*
