# OpenAgents Documentation Index

> Eight agnostic, composable peer modules for AI agents on Ethereum.
> mindX is one reference consumer of these modules — never the only home.
>
> Submission for **ETHGlobal Open Agents** (Apr 24 → May 6 2026 · BANKON × mindX).

This is the master navigation hub. Each prize track has its own subfolder with a positioning `README.md` and one or more deep-dive references. Code lives at `openagents/<module>/` and `daio/contracts/<module>/`; this folder holds documentation only.

## Cross-cutting

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system map, module diagram, data flows.
- [`QUICKSTART.md`](QUICKSTART.md) — ten-minute reproduction (deps → forge test → demo).
- [`EXPLANATION.md`](EXPLANATION.md) — design rationale and per-module narrative.
- **[`JUDGE_TOUR.md`](JUDGE_TOUR.md)** — 5-minute verification path. If you only read one file, read this.
- **[`LIVE_EVIDENCE.md`](LIVE_EVIDENCE.md)** — per-track verification page: curl commands, live endpoint status, and source-file pointers a judge can scan in one pass.
- **[`SUBMISSIONS.md`](SUBMISSIONS.md)** — paste-ready text for all 8 ETHGlobal submission forms (tagline · long description · how-it-works · tech stack · test status). Use this when filing.
- **[`SHIP_NOW.md`](SHIP_NOW.md)** — 24-hour deadline-aware execution roadmap (deadline moved up to May 3).
- **[`SUBMIT_NOW.md`](SUBMIT_NOW.md)** — submission-day playbook: 9 user-action items walked step-by-step in optimal order. ~60 min if you follow it.
- **[`DEPLOYMENT.md`](DEPLOYMENT.md)** — Anvil + 0G Galileo + Sepolia deployment plan with full contract inventory, dependency map, gas estimates, integration-gap audit, and reproduce-from-scratch judge sequence.
- **[`boardroom/BOARDROOM.md`](boardroom/BOARDROOM.md)** — the deliberation engine that consumes every track. Live at `/insight/boardroom/recent` and `/boardroom/sessions`. See the dedicated section below.

### Live module consoles (all 200 OK on prod, real wiring no mocks)

| Track / Module | Console URL | What it shows |
|---|---|---|
| Composition demo | [`/openagents.html`](https://mindx.pythai.net/openagents.html) | All 8 panels with deep-links |
| 0G iNFT-7857 | [`/inft7857`](https://mindx.pythai.net/inft7857) | 9-tab MetaMask console for ERC-7857 |
| 0G Adapter | [`/zerog`](https://mindx.pythai.net/zerog) | Sidecar /health + live Galileo RPC probe |
| Gensyn AXL | [`/conclave`](https://mindx.pythai.net/conclave) | 8-node mesh viz + FSM + tests |
| ENS BANKON | [`/bankon-ens`](https://mindx.pythai.net/bankon-ens) | Real ENS lookup any-name |
| KeeperHub | [`/keeperhub`](https://mindx.pythai.net/keeperhub) | Auto-polls dual-rail challenge envelope |
| Uniswap V4 | [`/uniswap`](https://mindx.pythai.net/uniswap) | Live V4 Quoter `eth_call` on Sepolia |
| ERC-8004 | [`/agentregistry`](https://mindx.pythai.net/agentregistry) | Schema + 20 tests + MetaMask lookup |
| Cabinet (bonus) | [`/cabinet`](https://mindx.pythai.net/cabinet) | Vault signing oracle (operator-activated) |

## By hackathon track

### 0G — $15,000 (Best Framework $7.5k · Best iNFT/Swarm $7.5k)
- [`0g/README.md`](0g/README.md) — track positioning + which files matter for judging.
- [`0g/INFT_7857.md`](0g/INFT_7857.md) — ERC-7857 module brief; deployed addresses; 56/56 tests; 9-tab UI.
- [`0g/OG_INTEGRATION_GUIDE.md`](0g/OG_INTEGRATION_GUIDE.md) — 0G Compute API client setup, ZG-Res-Key attestation header, model registry.
- [`0g/THOT_0G_MEMORY_ANCHOR.md`](0g/THOT_0G_MEMORY_ANCHOR.md) — THOT.commit() + 0G Storage + sidecar wiring.

### Uniswap — $5,000 (Best API Integration)
- [`uniswap/README.md`](uniswap/README.md) — track positioning + how to reproduce a swap.
- [`uniswap/UNISWAP_TRADER.md`](uniswap/UNISWAP_TRADER.md) — V4 tool + BDI persona + decision-trace demo.
- [`uniswap/FEEDBACK.md`](uniswap/FEEDBACK.md) — **required by track**: DX friction + API gaps.

### Gensyn — $5,000 (Best AXL Application)
- [`axl/README.md`](axl/README.md) — track positioning; pointers into `conclave/` (separate package).
- [`axl/AXL_CEO_SEVENSOLDIERS.md`](axl/AXL_CEO_SEVENSOLDIERS.md) — Cabinet pattern (CEO + 7 Counsellors) over AXL mesh.
- The Conclave module ships its own pyproject and full docs; see [`../conclave/README.md`](../conclave/README.md), [`../conclave/CONCLAVE.md`](../conclave/CONCLAVE.md), [`../conclave/SUBMISSION.md`](../conclave/SUBMISSION.md), and [`../conclave/docs/`](../conclave/docs/).

### ENS — $5,000 (Best Integration $2.5k · Most Creative $2.5k)
- [`ens/README.md`](ens/README.md) — track positioning + soulbound subname pitch.
- [`ens/BANKON_ENS.md`](ens/BANKON_ENS.md) — BANKON ENS overview.
- [`ens/BANKON_ARCHITECTURE.md`](ens/BANKON_ARCHITECTURE.md) — NameWrapper deep dive (1303 lines: free/paid paths, EIP-712 vouchers, gateway relayer). Includes the KeeperHub touch points; `keeperhub/KEEPERHUB_BRIDGE.md` extracts the agnostic write-up.
- [`ens/SUBNAME_REGISTRY.md`](ens/SUBNAME_REGISTRY.md) — `BankonSubnameRegistrar.sol` registrar contract + ABIs + role-based access control.

### KeeperHub — $5,000 (Best Use $4.5k · Builder Feedback Bounty $500)
- [`keeperhub/README.md`](keeperhub/README.md) — track positioning + Builder-Bounty submission notes.
- [`keeperhub/KEEPERHUB_BRIDGE.md`](keeperhub/KEEPERHUB_BRIDGE.md) — bidirectional x402/MPP bridge; dual-network challenge envelopes (Base USDC + Tempo MPP).
- [`keeperhub/FEEDBACK.md`](keeperhub/FEEDBACK.md) — Builder-Bounty submission: DX feedback from real integration.

## Boardroom — the deliberation engine that connects every track

The Boardroom isn't a prize track on its own — it's the cross-cutting consensus mechanism that makes the eight modules into one system. Every track lands here:

- **0G Compute attestations** — every soldier's vote carries the `ZG-Res-Key` from `llm/zerog_handler.py`. The ledger is provider-attested.
- **iNFT-7857 mint decisions** — flow through Boardroom voting before the contract call.
- **ENS / BANKON subname issuance** — agent-name decisions are Boardroom outputs.
- **Uniswap V4 Trader** — opportunity beliefs are *produced* by Boardroom and consumed by `uniswap/demo_trader.py`.
- **AXL / Conclave** — Conclave is the **distributed** Boardroom: same deliberation contract, but P2P over AXL with on-chain bond + slash. `conclave/integrations/mindx_boardroom_adapter.py` shows the symmetry.

**Live endpoints** (all public read-only, all returning 200 as of 2026-04-30):

- [`/insight/boardroom/recent`](https://mindx.pythai.net/insight/boardroom/recent) — sessions with per-soldier votes, providers, confidence
- [`/boardroom/sessions`](https://mindx.pythai.net/boardroom/sessions) — session list
- `/boardroom/convene`, `/boardroom/convene/stream` — auth-gated; start a deliberation or stream one in progress

**Source + spec**: [`boardroom/BOARDROOM.md`](boardroom/BOARDROOM.md) (1911 lines · DAIO Boardroom v1.0.0). Implementation: `daio/governance/boardroom.py`. Catalogue mirroring: every session lands in `agents/catalogue/events.py`.

## Composable primitives (boost multiple tracks)

These don't have their own prize track; they multiply the value of the modules above.

- **THOT.commit()** — pillar-gated memory-anchor primitive. Contract: [`../../daio/contracts/THOT/v1/THOT.sol`](../../daio/contracts/THOT/v1/THOT.sol) · 14 tests pass. Touches 0G memory anchoring + iNFT lineage. See [`0g/THOT_0G_MEMORY_ANCHOR.md`](0g/THOT_0G_MEMORY_ANCHOR.md).
- **ERC-8004 AgentRegistry** — identity + capability layer. Contract: [`../../daio/contracts/agentregistry/AgentRegistry.sol`](../../daio/contracts/agentregistry/AgentRegistry.sol) · 20 tests pass. Boosts the 0G iNFT track and the ENS track (subname-binding hook).
- **Shadow-Overlord Cabinet** — admin tier that composes BANKON Vault + IDManagerAgent + Boardroom roster + AgentRegistry into a custodial 8-wallet cabinet (1 CEO + 7 soldiers per company namespace). Vault-as-signing-oracle; private keys never leave the vault. **20 tests pass** (10 unit + 10 integration). Live UI at [`/cabinet`](https://mindx.pythai.net/cabinet). Full guide: [`../../docs/operations/SHADOW_OVERLORD_GUIDE.md`](../../docs/operations/SHADOW_OVERLORD_GUIDE.md). See also `LIVE_EVIDENCE.md` § Cabinet.

## Governance & supporting docs

- Boardroom — see the dedicated section above; spec lives at [`boardroom/BOARDROOM.md`](boardroom/BOARDROOM.md).
- [`governance/WARCOUNCIL.md`](governance/WARCOUNCIL.md) — WarCouncil governance structure.
- [`lighthouse/LIGHTHOUSE_AND_MINDX.md`](lighthouse/LIGHTHOUSE_AND_MINDX.md) — Lit Protocol + inference-chain integration (full version, 1051 lines).
- [`lighthouse/LIGHTHOUSE_MINDX.md`](lighthouse/LIGHTHOUSE_MINDX.md) — Lighthouse + mindX integration (alternate cut, 753 lines; kept because content differs).
- [`vercel/VERCEL_AISDK_MINDX.md`](vercel/VERCEL_AISDK_MINDX.md) — Vercel AI SDK + mindX integration notes.
- [`_archive/`](_archive/) — strategic roadmap PDF and other archival material.

## Coupling notes (the "agnostic" claim, audited)

Most modules import nothing from mindX. Two light couplings remain — both are demo/wiring conveniences, not architectural locks:

- `openagents/demo_agent.py` imports `agents.storage.zerog_provider` and `llm.zerog_handler` — these are *factory wirings*, not mindX logic. Any framework can substitute its own provider.
- `openagents/keeperhub/bridge_routes.py` imports `agents.catalogue.events` — wrapped in `try/except ImportError` so KeeperHub runs cleanly outside mindX.

Conclave (`openagents/conclave/`), the sidecar (`openagents/sidecar/`), and `openagents/ens/subdomain_issuer.py` import nothing from mindX. They're production-ready peer modules today.

## Submission roster (eight forms across five tracks)

| # | Track | Project name | Entry doc |
|---|-------|--------------|-----------|
| 1 | 0G — Best Autonomous Agents / iNFT | mindX iNFT-7857 | [`0g/INFT_7857.md`](0g/INFT_7857.md) |
| 2 | 0G — Best Framework, Tooling & Core Extensions | mindX 0G Adapter | [`0g/OG_INTEGRATION_GUIDE.md`](0g/OG_INTEGRATION_GUIDE.md) |
| 3 | Gensyn — AXL | Conclave | [`../conclave/SUBMISSION.md`](../conclave/SUBMISSION.md) |
| 4 | ENS — Best Integration for AI Agents | BankonSubnameRegistrar v1 | [`ens/README.md`](ens/README.md) |
| 5 | ENS — Most Creative Use of ENS | BankonSubnameRegistrar v1 (creative pitch) | [`ens/README.md`](ens/README.md) |
| 6 | KeeperHub — Best Use of KeeperHub | mindX × KeeperHub Bridge | [`keeperhub/README.md`](keeperhub/README.md) |
| 7 | KeeperHub — Builder Feedback Bounty | KeeperHub DX Feedback | [`keeperhub/FEEDBACK.md`](keeperhub/FEEDBACK.md) |
| 8 | Uniswap — Best API Integration | mindX Uniswap V4 Trader | [`uniswap/README.md`](uniswap/README.md) |
