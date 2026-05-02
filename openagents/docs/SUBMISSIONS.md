# ETHGlobal Open Agents — Submission Templates (8 forms)

> Paste-ready text blocks for each of the 8 prize forms.
> All claims are backed by either passing tests, live curl-able endpoints, or runnable demos. See [`LIVE_EVIDENCE.md`](LIVE_EVIDENCE.md) for the verification index.
>
> **Common fields** (use the same value in every form):
>
> - **Repo:** `https://github.com/AgenticPlace/openagents` *(currently private — invite ETHGlobal judges or flip to public for submission)*
> - **Live demo:** `https://mindx.pythai.net/openagents` (composition page with links to all 9 module consoles)
> - **Marketplace:** `https://agenticplace.pythai.net`
> - **Demo video:** `<TBD — record per docs/SHIP_NOW.md §Block B>`
> - **Team:** `codephreak` (registered for the hackathon by **BANKON**)
>
> **Live module consoles (per-track, all 200 OK on prod):**
>
> | Track | Console URL |
> |---|---|
> | 0G iNFT-7857 (Form 1) | https://mindx.pythai.net/inft7857 |
> | 0G Adapter (Form 2) | https://mindx.pythai.net/zerog |
> | Gensyn AXL (Form 3) | https://mindx.pythai.net/conclave |
> | ENS BANKON (Forms 4 + 5) | https://mindx.pythai.net/bankon-ens |
> | KeeperHub (Forms 6 + 7) | https://mindx.pythai.net/keeperhub |
> | Uniswap V4 (Form 8) | https://mindx.pythai.net/uniswap |
> | ERC-8004 (composable) | https://mindx.pythai.net/agentregistry |
> | Cabinet (bonus) | https://mindx.pythai.net/cabinet |
>
> The eight forms below use the same project root but are independently judged. Each block is structured to fit the typical ETHGlobal form fields: short description, long description, how-it-works, what-problem, tech-stack.

---

## Form 1 of 8 — 0G · Best Autonomous Agents, Swarms & iNFT Innovations ($7,500)

**Project name:** mindX iNFT-7857

**Short description / tagline (≤140 chars):**
> Standards-aligned ERC-7857 contract for encrypted-intelligence NFTs — sealed-key transfer, oracle-signed re-encryption, 56/56 tests.

**Long description:**

iNFT-7857 is a production-grade implementation of the ERC-7857 draft standard for "intelligent NFTs" — tokens whose payload is the agent's encrypted intelligence (model weights, persona, memory pointers), not a JPEG.

The contract enforces three properties that are absent from most NFT-as-agent demos:

1. **Sealed-key transfer gating** — `transferFrom` and `safeTransferFrom` revert. Ownership only moves through `transferWithSealedKey(...)`, which requires an EIP-712 oracle signature attesting that the new owner has been issued a re-encryption of the payload to their public key. Or through `cloneAgent(...)`, which produces a new tokenId, charges a clone-fee to the treasury, and re-encrypts. The intelligence is never exposed in plaintext during transfer.
2. **Standards-aligned hardness** — ERC-721 + URIStorage + Burnable + ERC-2981 royalty + AccessControl (4 roles: ADMIN, ORACLE, MINTER, AGENTIC_PLACE) + Pausable + ReentrancyGuard + EIP-712. No bespoke primitives where a standard exists.
3. **Composable bindings** — AgenticPlace marketplace and BANKON ENS subname bindings are *hooks*, not requirements. The contract works standalone; bindings register at mint time when the consumer wants them.

**How it's built:**

- Solidity 0.8.24, Foundry, OpenZeppelin v5
- Tests: 56/56 passing (53 unit + 3 fuzz @ 256 runs each) — `cd daio/contracts && FOUNDRY_PROFILE=inft forge test`
- 14 events emitted (Mint, TransferWithSealedKey, Clone, Authorize, Revoke, Burn, Bind, RoyaltyUpdated, etc.)
- Deployed: 0G Galileo testnet via `openagents/deploy/deploy_galileo.sh`
- Live UI: 9-tab single-file ethers v6 + MetaMask console at `mindx_backend_service/inft7857.html`

**What problem it solves:**

NFTs typically tokenize a public asset — a JPEG, a profile picture, a deed. An *agent* is the opposite: its value is its encrypted intelligence, which must remain encrypted to whoever doesn't currently own the agent. Standard ERC-721 transfer reveals the asset on transfer; iNFT-7857 makes transfer cryptographic.

**Tracks applied for:** 0G · Best Autonomous Agents, Swarms & iNFT Innovations

**Tech stack:** Solidity, Foundry, OpenZeppelin, EIP-712, ERC-7857 (draft), ERC-2981, 0G Compute, 0G Storage, 0G Galileo Chain, ethers.js v6, MetaMask, FastAPI, Python

**Tested:** ✓ 56/56 forge tests pass · ✓ Live UI at https://mindx.pythai.net/inft7857

**Source:**
- Contract: `daio/contracts/inft/iNFT_7857.sol`
- Tests: `daio/contracts/test/inft/iNFT_7857.t.sol`
- UI: `mindx_backend_service/inft7857.html`
- Module brief: `openagents/docs/0g/INFT_7857.md`

---

## Form 2 of 8 — 0G · Best Agent Framework, Tooling & Core Extensions ($7,500)

**Project name:** mindX 0G Adapter — Compute + Storage + Galileo wiring

**Short description / tagline (≤140 chars):**
> OpenAI-compatible Python client + Node TS sidecar wrapping 0G Storage SDK; ZG-Res-Key attestations, Merkle root anchoring on Galileo.

**Long description:**

A full 0G wiring layer for Python-based agent frameworks. Three pieces:

1. **0G Compute client** (`llm/zerog_handler.py`) — drop-in OpenAI-compatible interface for inference against 0G Compute. Captures the `ZG-Res-Key` attestation header on every call and surfaces it as `llm.last_attestation` so callers can prove the inference happened. Used by mindX's BDI agents, Boardroom soldiers, the Uniswap V4 trader persona, and the iNFT mint flow.
2. **0G Storage sidecar** (`openagents/sidecar/`) — Node TypeScript HTTP bridge wrapping `@0glabs/0g-ts-sdk`. Binds localhost-only by default; exposes `POST /upload`, `GET /retrieve/:root`, `GET /health`. Solves the impedance mismatch where the official SDK is JS-first and most agent code is Python.
3. **Galileo deployment** (`openagents/deploy/deploy_galileo.sh`) — one-command deploy of iNFT-7857 + DatasetRegistry to 0G Galileo. Outputs land in `openagents/deployments/galileo.json` and feed the `THOT.commit()` memory-anchor primitive (a 14-test composable contract that anchors agent reasoning steps to 0G Storage Merkle roots).

The three together let any framework run an agent that thinks on 0G Compute, remembers on 0G Storage, and proves both on 0G Chain.

**How it's built:**

- Python 3.11, FastAPI, aiohttp, eth-account
- Node 20, TypeScript, `@0glabs/0g-ts-sdk` v0.7+
- Solidity 0.8.24 (Galileo deployment), Foundry
- THOT v1 anchor: 14/14 tests pass (`FOUNDRY_PROFILE=thot forge test`)

**What problem it solves:**

Most 0G demos are JS-only or smart-contract-only. Building a Python agent framework on 0G means hand-rolling sidecars, attestation parsing, and Merkle root encoding. This adapter ships those pieces production-ready so other Python frameworks (LangChain, CrewAI, AutoGen, mindX itself) can adopt 0G as a peer in three lines of code.

**Tracks applied for:** 0G · Best Agent Framework, Tooling & Core Extensions

**Tech stack:** Python, FastAPI, Node, TypeScript, 0G Compute, 0G Storage, 0G Galileo Chain, OpenAI API compat, Merkle trees, EIP-712, Solidity, Foundry

**Tested:** ✓ 14/14 THOT forge tests · ✓ Live composition demo at https://mindx.pythai.net/openagents

**Source:**
- Compute client: `llm/zerog_handler.py`
- Storage sidecar: `openagents/sidecar/index.ts` + `openagents/sidecar/package.json`
- Storage Python provider: `agents/storage/zerog_provider.py`
- Galileo deploy: `openagents/deploy/deploy_galileo.sh`
- Memory-anchor primitive: `daio/contracts/THOT/v1/THOT.sol`
- Track positioning: `openagents/docs/0g/README.md`

---

## Form 3 of 8 — Gensyn · Best Application of Agent eXchange Layer (AXL) ($5,000)

**Project name:** Conclave — P2P signed-envelope mesh deliberation

**Short description / tagline (≤140 chars):**
> Cabinet pattern (CEO + 7 Counsellors) over AXL — no central broker, ed25519 envelopes, on-chain bond + slash, 8-node demo.

**Long description:**

Conclave is a small, signed protocol on top of Gensyn AXL that lets a fixed set of cryptographically-identified agents convene in private, deliberate, and resolve — with no central server, no cloud account, and no third-party message broker ever touching the payload.

The canonical instance is the **Cabinet pattern**: one Convener (CEO) plus seven Counsellors (COO / CFO / CTO / CISO / GC / COS / OPS), the same 8-role roster used in the mindX Boardroom. The reference run boots 8 separate AXL nodes (`examples/run_local_8node.sh`), each with its own ed25519 keypair, and runs a full session — propose, deliberate, resolve, anchor — across the mesh.

What makes this AXL-native, not just AXL-adjacent:

1. **Every AXL primitive used.** `/send`, `/recv`, `/mcp/`, `/a2a/`, `/topology` — see `conclave/docs/ARCHITECTURE.md` for the layer map.
2. **Cross-process from byte 1.** Every member is a separate AXL node with its own keypair. No in-process shortcuts. Eight processes on one host or eight hosts in eight cities, the protocol doesn't care.
3. **A real B2B use case.** M&A war rooms, board exec sessions, incident response, threat-intel sharing between rival CISOs, family-office governance. None of those can use Slack.
4. **On-chain accountability without on-chain content.** Membership is gated by BONAFIDE Tessera + Censura + ConclaveBond. Resolutions are anchored on chain; deliberations never leave the mesh. Full slash path implemented (Algorand PAI bond via x402 + parsec-wallet relayer in `Conclave.sol` + `ConclaveBond.sol`).

**How it's built:**

- Python 3.11, asyncio, PyNaCl (ed25519), CBOR canonical encoding
- 19 Python source files in `conclave/conclave/` (crypto, roles, session FSM, AXL client, agent wrapper, protocol state machine, on-chain anchoring)
- 2 Solidity contracts: `Conclave.sol` (gating + anchoring + slashing — integrates BONAFIDE primitives Tessera, Senatus, Censura), `ConclaveBond.sol` (x402 / Algorand honor-stake module — settles trade-secret bonds via Parsec rail)
- Foundry, Solidity 0.8.24
- 19 Python protocol tests + 10 Solidity contract tests, all passing

**What problem it solves:**

Multi-agent systems today route through cloud message brokers (Pub/Sub, SQS, Slack, Discord). For high-stakes deliberation — legal review, M&A negotiations, incident response — that's a non-starter: the broker sees the content. Conclave gives any framework's "executive cabinet" a P2P mesh where the messages never leave the participants, with on-chain bond/slash for accountability.

**Tracks applied for:** Gensyn · Best Application of AXL

**Tech stack:** Python, asyncio, PyNaCl, ed25519, CBOR, Gensyn AXL, Solidity, Foundry, BONAFIDE (Tessera, Senatus, Censura), Algorand, x402

**Tested:** ✓ 9/9 Python protocol tests · ✓ 10/10 Solidity contract tests · ✓ 8-node local mesh demo (`examples/run_local_8node.sh`) · ✓ Live mesh visualization (`examples/camera_view.html`)

**Source:**
- Self-contained submission package: `openagents/conclave/`
- Submission packet: `openagents/conclave/SUBMISSION.md`
- Architecture: `openagents/conclave/docs/ARCHITECTURE.md`
- Threat model: `openagents/conclave/docs/THREAT_MODEL.md`
- mindX adapter (proves agnostic peer status — does not import mindX): `openagents/conclave/integrations/mindx_boardroom_adapter.py`

---

## Form 4 of 8 — ENS · Best ENS Integration for AI Agents ($2,500)

**Project name:** BankonSubnameRegistrar v1 — ENS as active agent identity

**Short description / tagline (≤140 chars):**
> Soulbound `<agent>.bankon.eth` subnames bundled with ERC-8004 mint; agents discover and call each other by name. 29 fuzz tests.

**Long description:**

BANKON v1 is an ENS NameWrapper-based registrar that issues `<agent_id>.bankon.eth` subnames as the active, soulbound identity of an autonomous agent — not a cosmetic profile picture, not a human's address.

A `<agent_id>.bankon.eth` issued through `BankonSubnameRegistrar.register_free(...)`:

1. **Resolves to the agent's wallet** (not a human's). Agents discover each other by name and call each other by name.
2. **Carries text records** for `agentURI` (IPFS/0G Storage pointer to the agent's manifest), `mindxEndpoint` (HTTPS/A2A endpoint), `baseAddress` (L2 settlement address), and capability tags.
3. **Is soulbound** — burn-only ownership. Identity is non-fungible, even if the agent forks.
4. **Bundles an ERC-8004 AgentRegistry mint** in the *same transaction*. Atomicity matters: the agent's name and capability attestation are issued together, not separately.
5. **Hooks iNFT-7857** so an agent's encrypted intelligence can be cryptographically bound to its public identity.

The Python client (`openagents/ens/subdomain_issuer.py`) gives any framework a 5-line agent-identity flow: instantiate `SubdomainIssuer`, call `register_free(name, wallet, AgentMetadata(...))`, get back a soulbound subname plus an ERC-8004 token.

**How it's built:**

- Solidity 0.8.24 (ENS NameWrapper integration, EIP-712 signing, ERC-8004 atomic mint)
- 29 Foundry tests (including fuzz) — `cd daio/contracts && FOUNDRY_PROFILE=bankon forge test`
- Python client (`openagents/ens/subdomain_issuer.py`) — eth-account + web3.py, EIP-712 typed-data signer
- Off-chain price oracle for renewal (`BankonPriceOracle.sol`) — 20% PYTHAI-payer discount baked in

**What problem it solves:**

Agent identity today is a wallet address (illegible) or an opaque UUID (not on-chain). ENS subnames are the natural namespace, but most ENS implementations assume a human owner. BANKON v1 issues soulbound, capability-bundled subnames designed for agents — bytes, not human hands, control them.

**Tracks applied for:** ENS · Best ENS Integration for AI Agents

**Tech stack:** Solidity, ENS NameWrapper, ERC-8004 AgentRegistry, EIP-712, OpenZeppelin, Foundry, Python, web3.py, eth-account, IPFS, 0G Storage

**Tested:** ✓ 29/29 fuzz tests pass

**Source:**
- Contract: `daio/contracts/ens/v1/BankonSubnameRegistrar.sol`
- Tests: `daio/contracts/ens/v1/test/BankonSubnameRegistrar.t.sol`
- Python client: `openagents/ens/subdomain_issuer.py`
- Track positioning: `openagents/docs/ens/README.md`
- Architecture: `openagents/docs/ens/BANKON_ARCHITECTURE.md`

---

## Form 5 of 8 — ENS · Most Creative Use of ENS ($2,500)

**Project name:** BankonSubnameRegistrar v1 — Subnames as verifiable agent credentials

**Short description / tagline (≤140 chars):**
> ENS subnames carrying capability attestations, role records, and bundled ERC-8004 mint — credentials, not profile pages.

**Long description (creative angle):**

Treat an ENS subname as a *verifiable credential*, not a profile page. BANKON v1 issues `<role>.<company>.bankon.eth` (or any subdomain shape) where the text records describe what the bearer *can do*, not what the bearer *looks like*:

- `text/agent.role` — `"cfo"`, `"oracle"`, `"validator"`, `"signer"`...
- `text/agent.capabilities` — bitmap or comma-list of permitted operations
- `text/agent.attestor` — who vouches for this credential (companies, DAOs, councils)
- `text/agent.expiry` — credential validity window
- `text/agent.delegate` — who can act on the agent's behalf if it goes offline

Combined with the soulbound transfer rules and the bundled ERC-8004 mint, a single ENS lookup yields:

1. The agent's address (resolver default).
2. The agent's capability attestation (text records + linked ERC-8004 NFT).
3. The agent's encrypted intelligence pointer (text/`agentURI`, resolves through 0G Storage).
4. The chain of trust (the attestor's own ENS name + signature).

This makes ENS a federated agent credential registry. Any service that knows ENS now also knows how to verify whether a wallet is allowed to do a specific thing — without each service re-implementing access control.

**How it's built:**

Same contract as Form 4 (`BankonSubnameRegistrar.sol`); the creativity is in **what's stored in the text records and how they compose**. The shipped demo populates the Cabinet 8-wallet roster (CEO + 7 soldiers) with role-bound subnames; a verifier walks the records to confirm a signature came from the agent currently holding the `cfo.<company>.bankon.eth` credential.

**Tracks applied for:** ENS · Most Creative Use of ENS

**Tech stack:** ENS NameWrapper, ERC-8004 AgentRegistry, ENS text records, EIP-712, IPFS, 0G Storage, Solidity, Python

**Tested:** ✓ Same 29 fuzz tests as Form 4 (the registrar is the same; the creativity is in usage)

**Source:**
- Contract: `daio/contracts/ens/v1/BankonSubnameRegistrar.sol`
- Cabinet integration that uses this credential pattern: `mindx_backend_service/bankon_vault/cabinet.py`
- Architecture: `openagents/docs/ens/BANKON_ARCHITECTURE.md`
- Subname registry detail: `openagents/docs/ens/SUBNAME_REGISTRY.md`

**Note:** Forms 4 and 5 use the same contract but apply for different prizes (Best ENS Integration vs Most Creative Use). The two submissions are independent per ETHGlobal rules.

---

## Form 6 of 8 — KeeperHub · Best Use of KeeperHub ($4,500)

**Project name:** mindX × AgenticPlace × KeeperHub Bridge — bidirectional x402/MPP rails

**Short description / tagline (≤140 chars):**
> Dual-network 402 bridge — Base USDC + Tempo MPP in one envelope; agents can pay each other across rails without picking sides.

**Long description:**

A FastAPI bridge (`openagents/keeperhub/bridge_routes.py`, 390 LOC) that lets mindX hosted endpoints **both expose** paid AgenticPlace endpoints as KH-compatible 402 challenges **and consume** paid KH workflows from Python.

The headline behavior: when a caller hits `/p2p/keeperhub/info`, the response describes *both* a Base USDC payment requirement *and* a Tempo MPP payment requirement in a single envelope. The caller's wallet picks the rail it has balance on. No off-chain coordination, no rail negotiation, no hardcoded "you must use Base."

Endpoints:

- `GET /p2p/keeperhub/info` — service descriptor + dual-rail challenge
- `POST /p2p/keeperhub/agent/register` — paid registration (0.005 USDC)
- `POST /p2p/keeperhub/inference` — paid inference call
- `POST /p2p/keeperhub/job/create` — paid workflow creation
- `POST /p2p/keeperhub/workflow/callback` — webhook receiver (HMAC-validated)

Live verification: `curl -s https://mindx.pythai.net/p2p/keeperhub/info` returns the full dual-rail JSON, deployed as of 2026-05-02 to `mindx.pythai.net`.

**How it's built:**

- Python 3.11, FastAPI, httpx, eth-account
- EIP-3009 `transferWithAuthorization` settlement (no approve round-trip)
- HMAC-SHA256 webhook signature validation
- Hand-rolled Python x402 client (`tools/keeperhub_x402_client.py`) — there is no first-party Python SDK, see Form 7
- KeeperHub MCP integration via `KeeperHubX402Client.list_workflows()`
- Catalogue events (`agents/catalogue/events.py`) for forensic audit on every settlement

**What problem it solves:**

Agentic systems need to pay each other for services (inference, registration, workflow execution). KeeperHub provides the rails (Base USDC and Tempo MPP), but exposing a service that accepts both, and consuming services that expose both, requires non-trivial protocol work. This bridge ships that work production-ready: clone the repo, set the env vars, get a paid AgenticPlace endpoint stack speaking both rails.

**Tracks applied for:** KeeperHub · Best Use of KeeperHub

**Tech stack:** Python, FastAPI, httpx, eth-account, EIP-3009, EIP-712, KeeperHub MCP, x402, MPP, Base, Tempo, USDC, HMAC-SHA256

**Tested:** ✓ Live on prod (`https://mindx.pythai.net/p2p/keeperhub/info` returns 200 with dual-rail envelope, 5 routes registered) · Module imports cleanly outside mindX (catalogue.events wrapped in try/except)

**Source:**
- Bridge: `openagents/keeperhub/bridge_routes.py`
- Python client: `tools/keeperhub_x402_client.py`
- Track positioning: `openagents/docs/keeperhub/README.md`
- Bridge detail: `openagents/docs/keeperhub/KEEPERHUB_BRIDGE.md`

---

## Form 7 of 8 — KeeperHub · Builder Feedback Bounty ($500, two teams × $250)

**Project name:** KeeperHub Integration — DX Feedback from real implementation

**Short description / tagline (≤140 chars):**
> Five categorized friction notes from a real KH integration; documentation gaps, SDK gaps, API friction, discoverability, and what works.

**Long description:**

Drafted during the integration that produced Form 6. Concrete observations, each with **Where / Impact / Suggested fix** structure. Five sections:

1. **Documentation gaps** — `/introduction/what-is-keeperhub` returns 404; missing fee-payer matrix per network; Tempo/MPP USDC.e address not in a single canonical table.
2. **SDK gaps** — no first-party Python SDK (had to hand-roll a 200-line EIP-3009 signer + 402-retry client); `@keeperhub/wallet` v0.1.7 published 6 days before hackathon (drift risk during judging window); no formal type definitions for the 402 challenge envelope.
3. **Behaviour / API friction** — MCP server is org-scoped (multi-tenant agents must switch tokens per call); no on-chain settlement-proof endpoint for skeptical procurement teams; webhook signature scheme is undocumented.
4. **Discoverability** — no public list of registered paid workflows (reduces network effect); hackathon partnership announcement could link the underlying x402 spec and EIP-3009.
5. **Positive notes** — dual-network 402 is excellent design (we modeled our bridge envelope on it directly); EIP-3009 over EIP-2612 was the right call; Turnkey-backed wallets are a strong default; the `kh` CLI is well-organized.

The full document is the submission artifact at `openagents/docs/keeperhub/FEEDBACK.md` (85 lines, dated 2026-04-27).

**Tracks applied for:** KeeperHub · Builder Feedback Bounty

**Source:** `openagents/docs/keeperhub/FEEDBACK.md`

**Note:** This bounty is independent of Form 6 — same integration, separate prize.

---

## Form 8 of 8 — Uniswap · Best API Integration ($5,000)

**Project name:** mindX Uniswap V4 Trader — BDI-reasoning swap agent

**Short description / tagline (≤140 chars):**
> Uniswap V4 swap agent driven by BDI cognitive cycle; persona constraints (slippage ≤0.5%, ≥30% reserve), full decision trace.

**Long description:**

A swap agent built as a Uniswap V4 tool (`tools/uniswap_v4_tool.py`) wrapped in a BDI-reasoning persona (`personas/trader.prompt`). The agent reads opportunities from a Boardroom deliberation, applies hard persona constraints, executes a swap on Sepolia V4, and writes a full decision trace to `data/logs/uniswap_decisions.jsonl` for audit.

Persona constraints (the BDI cycle rejects any action that violates them):
- **Slippage budget**: ≤ 0.5% per swap
- **Position size**: ≤ $5 USDC equivalent
- **Reserve floor**: maintain ≥ 30% USDC of total portfolio after the swap
- **Decision freshness**: opportunity belief must be ≤ 60 seconds old when the swap executes

The tool surface (extending `BaseTool` with four actions):
- `info` — capabilities, supported chains, default reserve floor
- `quote` — `(token_in, token_out, amount_in)` → quote with price impact + gas estimate
- `swap` — execute with explicit slippage and deadline; returns on-chain receipt
- `balance` — trader's USDC, WETH, ETH balances

The complete trade loop in `openagents/uniswap/demo_trader.py` runs a full opportunity → BDI deliberation → swap → audit cycle on Sepolia V4 in under 30 seconds.

**How it's built:**

- Python 3.11, web3.py, eth-account
- Uniswap V4 Quoter V2 (`quoteExactInputSingle` with PoolKey struct ABI)
- Universal Router for swap execution
- BDI cognitive cycle (`core/bdi_agent.py`)
- Persona-driven action filtering (`agents/persona_agent.py`)
- Decision trace mirrored to the catalogue event stream

**What problem it solves:**

Most "AI swap bot" demos are MEV bots wrapped in marketing — no constraints, no audit trail, no rejection logic. A real trading agent needs hard guardrails (position limits, reserve floors, slippage budgets) and a complete decision trace. This trader is both: BDI deliberation produces the candidate, persona constraints accept-or-reject it, and every step lands in `data/logs/uniswap_decisions.jsonl`.

**Tracks applied for:** Uniswap · Best API Integration

**Tech stack:** Python, web3.py, eth-account, Uniswap V4, Quoter V2, Universal Router, Sepolia, USDC, WETH, BDI cognitive architecture, FastAPI

**Tested:** ✓ End-to-end run on Sepolia V4 · ✓ Decision trace persisted

**Source:**
- Tool: `tools/uniswap_v4_tool.py` (~200 lines)
- Persona: `personas/trader.prompt`
- Demo: `openagents/uniswap/demo_trader.py`
- Track positioning: `openagents/docs/uniswap/README.md`
- Trader detail: `openagents/docs/uniswap/UNISWAP_TRADER.md`
- **Required artifact** (per track rules): `openagents/docs/uniswap/FEEDBACK.md`

---

## Cross-cutting talking points (use in any "additional comments" / "what makes this special" field)

These are the architectural points that distinguish the eight submissions as **one coherent system**, not eight independent projects:

1. **Eight agnostic, composable peer modules.** Every module ships with its own README, tests, and Solidity contracts. Each exposes one clean interface (Solidity ABI or Python/TS API) — other frameworks call it without importing internals. The "agnostic-module statement" in each module's docs names only the assumed primitives (e.g. *"ed25519 + an EVM chain"*).

2. **138 passing tests across the stack.** iNFT-7857: 56. BANKON: 29. THOT: 14. AgentRegistry: 20. Conclave Solidity: 10. Conclave Python: 9. (Plus 20 Cabinet tests — see "Bonus" below.)

3. **mindX is one consumer, not the only home.** The composition demo at `https://mindx.pythai.net/openagents` shows the modules wired together as one system; the same modules can be lifted independently into any other framework.

4. **Bonus — the Cabinet feature.** The shadow-overlord admin tier in `mindx_backend_service/bankon_vault/` is a working demonstration of the agnostic-modules thesis: one feature that composes BANKON Vault + IDManagerAgent + Boardroom roster + ERC-8004 AgentRegistry + EIP-712 signer pattern. Cryptographic property: the vault signs on the agent's behalf without leaking the private key — proven by 20 passing tests including a runtime ECDSA-recovery transcript. Live UI at `/cabinet`. See `docs/operations/SHADOW_OVERLORD_GUIDE.md` (~1,150 lines, 5 appendices, captured proof transcript).

5. **Live evidence index.** `openagents/docs/LIVE_EVIDENCE.md` lists every claim with a curl-able verification command. A judge can confirm every line in 5 minutes from their terminal.

6. **Documentation tree.** `openagents/docs/INDEX.md` is the master nav; per-track folders (`docs/{0g,ens,keeperhub,uniswap,axl}/`) contain the per-track positioning. `docs/SHIP_48H.md` is the deadline-aware execution roadmap.

---

## Submission checklist (for you, before clicking submit)

- [ ] Repo URL is the canonical public mirror (verify; locally configured remotes don't include `Professor-Codephreak/mindX`)
- [ ] Demo video URL is filled in (TBD — record per `docs/SHIP_NOW.md` §Block B)
- [ ] FEEDBACK.md contact handles populated (currently `Telegram: TBD, X: TBD` in both keeperhub/FEEDBACK.md and uniswap/FEEDBACK.md)
- [ ] If submitting Forms 4 + 5 (both ENS), confirm with ETHGlobal that double-submission of the same project to Best Integration + Most Creative is permitted on this hackathon (the README implies yes; verify on the form)
- [ ] Form 7 (KeeperHub Builder Bounty) is filed alongside Form 6 — they're separate prizes
- [ ] Cabinet activation on prod (set `SHADOW_OVERLORD_ADDRESS` + `SHADOW_JWT_SECRET`, restart) is optional but lets judges click `/cabinet` and see the bonus demo live
