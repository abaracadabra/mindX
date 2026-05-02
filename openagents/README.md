# mindX × Open Agents — eight agnostic, composable modules

[![tests](https://github.com/AgenticPlace/openagents/actions/workflows/test.yml/badge.svg?branch=main)](https://github.com/AgenticPlace/openagents/actions/workflows/test.yml)
&nbsp;**165/165 tests · 82% coverage · Slither audited (1 contract bug + 1 vault bug fixed)** &middot; 9 live consoles &middot; ETHGlobal Open Agents 2026

> Submission for **ETHGlobal Open Agents** · Apr 24 → May 3 2026 · BANKON × mindX
> Live console: [https://mindx.pythai.net/openagents](https://mindx.pythai.net/openagents) — composition page with links to **9 live module consoles**
> Repo: [github.com/AgenticPlace/openagents](https://github.com/AgenticPlace/openagents)

> **Documentation:**
> - **Judging?** Start at [`docs/JUDGE_TOUR.md`](docs/JUDGE_TOUR.md) — 5-minute verification path with click-by-click instructions.
> - **Filing forms?** Use [`docs/SUBMISSIONS.md`](docs/SUBMISSIONS.md) — paste-ready blocks for all 8 ETHGlobal submission forms.
> - **Curl-verifying claims?** [`docs/LIVE_EVIDENCE.md`](docs/LIVE_EVIDENCE.md) — every claim linked to a runnable check.
> - **Full nav?** [`docs/INDEX.md`](docs/INDEX.md).

## Live module consoles (all 200 OK on prod, real wiring)

| Track | URL | Highlights |
|---|---|---|
| 0G iNFT-7857 | https://mindx.pythai.net/inft7857 | 9-tab ethers v6 console, 14 events |
| 0G Adapter | https://mindx.pythai.net/zerog | Sidecar /health + live Galileo RPC |
| Gensyn AXL | https://mindx.pythai.net/conclave | 8-node mesh viz |
| ENS BANKON | https://mindx.pythai.net/bankon-ens | Real ENS lookup |
| KeeperHub | https://mindx.pythai.net/keeperhub | Auto-polls dual-rail challenge |
| Uniswap V4 | https://mindx.pythai.net/uniswap | Live V4 Quoter eth_call |
| ERC-8004 | https://mindx.pythai.net/agentregistry | Schema + 20 tests + MetaMask |
| Cabinet (bonus) | https://mindx.pythai.net/cabinet | Vault signing oracle |

## Architectural principle

Every module here is an **agnostic, composable peer** with **horizontal + vertical scaling first-class**. mindX is one canonical *consumer* of these modules — never the only home. Each module:

- Lives at `openagents/<name>/` (or `daio/contracts/<name>/`) with its own README, tests, and Solidity contracts
- Exposes one clean interface (Solidity ABI or Python/TS API) — other frameworks call it without importing internals
- Documents an explicit "agnostic-module statement" naming only the assumed primitives (e.g. *"ed25519 + an EVM chain"*)
- Submits to its own prize track independently
- mindX's `/openagents.html` is the *composition demo* — proof the modules form a coherent stack — but it's one example, not the only one

If your framework wants any subset of the eight, lift them — they don't depend on mindX.

---

## Module roster (8 modules · 4 sponsors · 8 prize slots)

| # | Module | Track / Sponsor | Tests | Status | Where |
|---|--------|------------------|------:|--------|-------|
| 1 | **iNFT-7857** — encrypted-intelligence ERC-7857 contract | 0G · Best Autonomous Agents / iNFT (5 × $1.5k) | **56** ✓ | shipped + UI | `daio/contracts/inft/iNFT_7857.sol` · [`/inft7857`](https://mindx.pythai.net/inft7857) |
| 2 | **0G Adapter** — OpenAI-compat client + Node sidecar | 0G · Best Framework, Tooling & Core Extensions ($7.5k) | — | shipped | `llm/zerog_handler.py` + `openagents/sidecar/` |
| 3 | **Conclave** — P2P signed-envelope mesh deliberation | Gensyn · AXL ($5k) | **9 + 10** ✓ | shipped + 8-node demo | `openagents/conclave/` |
| 4 | **BANKON v1** — ENS NameWrapper subname registrar | ENS · Best Integration + Most Creative ($5k) | **29** ✓ | shipped (29 fuzz incl.) | `daio/contracts/ens/v1/` |
| 5 | **KeeperHub Bridge** — bidirectional x402/MPP facilitator | KeeperHub · Best Use + Builder Bounty ($5k) | — | shipped + verified | `openagents/keeperhub/` |
| 6 | **Uniswap V4 Trader** — BDI-reasoning swap agent | Uniswap · Best API Integration ($5k) | — | shipped + persona | `tools/uniswap_v4_tool.py` + `openagents/uniswap/` |
| 7 | **THOT.commit()** — pillar-gated memory-anchor primitive | composable; boosts M1 + M2 | **14** ✓ | shipped | `daio/contracts/THOT/v1/THOT.sol` |
| 8 | **ERC-8004 AgentRegistry** — identity + capability layer | composable; boosts M1 + M4 | **20** ✓ | shipped | `daio/contracts/agentregistry/AgentRegistry.sol` |

**Aggregate test totals: 164 tests, all green · 82% Python (Cabinet) line coverage · 89-96% Solidity coverage (4 daio contracts) · Slither audited (1 finding fixed + permanent CI guard).**

---

## Architecture diagram

```
                  ┌───────────────────────────────────────────────────────┐
                  │   ANY FRAMEWORK (mindX, OpenClaw, NanoClaw, …)        │
                  │   composes any subset of the modules below.           │
                  └─────────────────────────┬─────────────────────────────┘
                                            │
   ┌──────────────────┬───────────────┬─────┼──────┬──────────────┬────────────────┐
   ▼                  ▼               ▼     ▼      ▼              ▼                ▼
┌───────────┐  ┌───────────────┐  ┌─────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐
│ iNFT_7857 │  │ 0G Adapter    │  │ Conclave│ │ BANKON   │ │ KeeperHub    │ │ Uniswap V4  │
│ ERC-7857  │  │ zerog_handler │  │ AXL     │ │ ENS v1   │ │ x402 bridge  │ │ trader      │
│ contract  │  │ + sidecar     │  │ mesh    │ │ Sub-Reg  │ │              │ │ persona     │
│ + UI      │  │ (Py + Node)   │  │ + bond  │ │ + Oracle │ │              │ │             │
│           │  │               │  │ + slash │ │ + Router │ │              │ │             │
│           │  │               │  │         │ │ + Gate   │ │              │ │             │
└─────▲─────┘  └───────▲───────┘  └────▲────┘ └─────▲────┘ └──────▲───────┘ └─────▲───────┘
      │                │               │            │             │                │
      │       ┌────────┴────────┐      │            │             │                │
      │       │ THOT.commit()   │      │            │             │                │
      │       │ Memory anchor   │      │            │             │                │
      │       └────────▲────────┘      │            │             │                │
      │                │               │            │             │                │
      │       ┌────────┴────────┐      │            │             │                │
      └───────│ ERC-8004        │──────┴────────────┘             │                │
              │ AgentRegistry   │                                 │                │
              │ (capability     │                                 │                │
              │  + attestation) │                                 │                │
              └─────────────────┘                                 │                │
                                                                  ▼                ▼
                                              /openagents.html (mindX composition demo)
```

Boxes are wired by interfaces only; no module imports another's internals.

---

## Compose your own — minimum viable agent (Python)

Any framework, three coroutines:

```python
# pip install web3 eth-account aiohttp
from openagents.ens.subdomain_issuer  import SubdomainIssuer, AgentMetadata
from agents.storage.zerog_provider    import ZeroGProvider
from llm.zerog_handler                import ZeroGHandler

# ─ 1. Identity ─────────────────────────────────────────────
issuer = SubdomainIssuer()                                  # BANKON v1
res    = await issuer.register_free(
    "ceo-mastermind-2k", agent_wallet,
    AgentMetadata(agentURI="ipfs://Qm/agent.json",
                  mindxEndpoint="https://you.example/agent/x",
                  baseAddress=base_l2_addr),
)
# → soulbound <ceo-mastermind-2k>.bankon.eth + bundled ERC-8004 mint

# ─ 2. Inference ────────────────────────────────────────────
llm  = ZeroGHandler(api_key=ZEROG_API_KEY)
text = await llm.generate_text(prompt="hello", model="zerog/gpt-oss-120b")
chat_id = llm.last_attestation                              # ZG-Res-Key

# ─ 3. Memory ───────────────────────────────────────────────
provider = ZeroGProvider()                                  # 0G Storage
root, tx = await provider.upload(b"persona-bytes")
# → THOT.commit(author, root.value, chat_id, provider_addr, parent=0)
#   — anchors the reasoning step on chain
```

mindX's full composition lives in [`demo_agent.py`](demo_agent.py).

---

## Per-module quick links

- [iNFT-7857 docs](docs/0g/INFT_7857.md) · [tests](../daio/contracts/test/inft/iNFT_7857.t.sol) · [/inft7857 console](https://mindx.pythai.net/inft7857)
- [0G Adapter — sidecar](sidecar/) · [Python handler](../llm/zerog_handler.py) · [storage provider](../agents/storage/zerog_provider.py) · [track positioning](docs/0g/README.md)
- [Conclave](conclave/) · [SUBMISSION](conclave/SUBMISSION.md) · [AXL track positioning](docs/axl/README.md) · [boardroom adapter](conclave/integrations/mindx_boardroom_adapter.py)
- [BANKON v1 contracts](../daio/contracts/ens/v1/) · [test suite (29 pass)](../daio/contracts/ens/v1/test/BankonSubnameRegistrar.t.sol) · [Python client](ens/subdomain_issuer.py) · [ENS track positioning](docs/ens/README.md)
- [KeeperHub Bridge](keeperhub/bridge_routes.py) · [FEEDBACK.md](docs/keeperhub/FEEDBACK.md) · [/p2p/keeperhub/info](https://mindx.pythai.net/p2p/keeperhub/info) · [KeeperHub track positioning](docs/keeperhub/README.md)
- [Uniswap V4 Trader](uniswap/) · [tool](../tools/uniswap_v4_tool.py) · [persona](../personas/trader.prompt) · [demo](uniswap/demo_trader.py) · [Uniswap track positioning + FEEDBACK.md](docs/uniswap/README.md)
- [THOT v1](../daio/contracts/THOT/v1/THOT.sol) · [tests (14 pass)](../daio/contracts/THOT/v1/test/THOT.t.sol)
- [AgentRegistry (ERC-8004)](../daio/contracts/agentregistry/AgentRegistry.sol) · [tests (20 pass)](../daio/contracts/agentregistry/test/AgentRegistry.t.sol)

---

## Quickstart

```bash
git clone https://github.com/Professor-Codephreak/mindX
cd mindX
python -m venv .mindx_env && .mindx_env/bin/pip install -r requirements.txt
cd openagents/sidecar && npm install && cd ../..

# Run all four module test suites
cd daio/contracts
FOUNDRY_PROFILE=inft           forge test  # iNFT-7857: 56/56
FOUNDRY_PROFILE=bankon         forge test  # BANKON v1: 29/29
FOUNDRY_PROFILE=thot           forge test  # THOT v1:   14/14
FOUNDRY_PROFILE=agentregistry  forge test  # AgentRegistry: 20/20
cd ../..

# Run the Conclave Python protocol tests
cd openagents/conclave && pytest tests/  # 9 protocol tests
forge test                                # 10 contract tests; from contracts/
cd ../..

# Run the dashboard
./mindX.sh --frontend
# → http://localhost:8000/openagents.html
```

See [docs/QUICKSTART.md](docs/QUICKSTART.md) for the full deployment + demo sequence.
For per-track navigation, see [`docs/INDEX.md`](docs/INDEX.md).

---

## Submission packets (8 forms)

| # | Track | Project name |
|---|-------|--------------|
| 1 | 0G — Best Autonomous Agents / iNFT | mindX iNFT-7857 |
| 2 | 0G — Best Framework, Tooling & Core Extensions | mindX 0G Adapter |
| 3 | Gensyn — AXL | Conclave |
| 4 | ENS — Best Integration for AI Agents | BankonSubnameRegistrar v1 |
| 5 | ENS — Most Creative Use of ENS | BankonSubnameRegistrar v1 (creative pitch) |
| 6 | KeeperHub — Best Use of KeeperHub | mindX × KeeperHub Bridge |
| 7 | KeeperHub — Builder Feedback Bounty | [docs/keeperhub/FEEDBACK.md](docs/keeperhub/FEEDBACK.md) |
| 8 | Uniswap — Best API Integration | mindX Uniswap V4 Trader |

**Team:** [codephreak](https://github.com/Professor-Codephreak) (registered for the hackathon by **BANKON**).
**Live demo:** https://mindx.pythai.net/openagents
**Marketplace:** https://agenticplace.pythai.net

---

*Prior art: see `daio/contracts/inft/iNFT.sol`, `daio/contracts/inft/IntelligentNFT.sol`, `daio/contracts/THOT/core/THOT.sol`, `mindx_backend_service/inft.html`, committed Apr 11 2026 (`fff941a7`, `468de468`, `f07b025a`). Hardened standards-aligned variants (iNFT_7857, THOT v1, BANKON v1) live in their own paths; the Apr 11 contracts remain in the tree as committed.*
