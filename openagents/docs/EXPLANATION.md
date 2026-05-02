# mindX × Open Agents — explanation

> **What this is.** The technical reference for the eight-module ETHGlobal Open Agents submission. mindX is one canonical consumer; every module here is an agnostic peer any agent framework can lift independently.
>
> **Companion docs.** [README.md](../README.md) (submission entry-point) · [ARCHITECTURE.md](ARCHITECTURE.md) (visual architecture) · [QUICKSTART.md](QUICKSTART.md) (10-minute reproduction) · [INDEX.md](INDEX.md) (master nav) · [docs/INFT_7857.md](../../docs/INFT_7857.md) (canonical iNFT-7857 reference).

---

## 1. Summary (one paragraph)

mindX ships **eight agnostic, composable modules** with horizontal + vertical scaling first-class, submitted across **four ETHGlobal sponsor tracks** (0G ×2, Gensyn ×1, ENS ×2, KeeperHub ×2, Uniswap ×1 = 8 prize slots from $35.5k pool). Three new on-chain primitives (**iNFT-7857**, **THOT v1 with `commit()`**, **ERC-8004-aligned AgentRegistry**) and one new on-chain governance suite (**BANKON v1**: registrar + price oracle + payment router + reputation gate) are joined by four off-chain adapters (**0G Compute/Storage**, **KeeperHub x402 bridge**, **Uniswap V4 trader**, **Conclave AXL deliberation protocol**). The composition demo at `/openagents.html` proves the eight modules form a coherent stack — but each ships standalone with its own README, tests, and Solidity. **138 tests pass green** across the suites.

---

## 2. What we shipped (modules-at-a-glance)

| # | Module | Track / Prize | Key paths | Tests |
|---|--------|---------------|-----------|------:|
| 1 | **iNFT-7857** | 0G — Best Autonomous Agents / iNFT (5 × $1.5k) | [`daio/contracts/inft/iNFT_7857.sol`](../../daio/contracts/inft/iNFT_7857.sol), [`mindx_backend_service/inft7857.html`](../../mindx_backend_service/inft7857.html) | **56** |
| 2 | **0G Adapter** | 0G — Best Framework, Tooling & Core Extensions ($7.5k) | [`llm/zerog_handler.py`](../../llm/zerog_handler.py), [`agents/storage/zerog_provider.py`](../../agents/storage/zerog_provider.py), [`openagents/sidecar/index.ts`](../sidecar/index.ts) | smoke ✓ |
| 3 | **Conclave** | Gensyn — AXL ($5k) | [`openagents/conclave/`](../conclave/), [`SUBMISSION.md`](../conclave/SUBMISSION.md) | **9 + 10** |
| 4 | **BANKON v1** | ENS — Best Integration + Most Creative ($5k) | [`daio/contracts/ens/v1/`](../../daio/contracts/ens/v1/), [`openagents/ens/subdomain_issuer.py`](../ens/subdomain_issuer.py) | **29** |
| 5 | **KeeperHub Bridge** | KeeperHub — Best Use + Builder Bounty ($5k) | [`openagents/keeperhub/bridge_routes.py`](../keeperhub/bridge_routes.py), [`tools/keeperhub_x402_client.py`](../../tools/keeperhub_x402_client.py) | smoke ✓ |
| 6 | **Uniswap V4 Trader** | Uniswap — Best API Integration ($5k) | [`tools/uniswap_v4_tool.py`](../../tools/uniswap_v4_tool.py), [`personas/trader.prompt`](../../personas/trader.prompt), [`openagents/uniswap/demo_trader.py`](../uniswap/demo_trader.py) | smoke ✓ |
| 7 | **THOT v1 — `commit()`** | composable; boosts M1 + M2 | [`daio/contracts/THOT/v1/THOT.sol`](../../daio/contracts/THOT/v1/THOT.sol) | **14** |
| 8 | **AgentRegistry (ERC-8004)** | composable; boosts M1 + M4 | [`daio/contracts/agentregistry/AgentRegistry.sol`](../../daio/contracts/agentregistry/AgentRegistry.sol) | **20** |

---

## 3. The architectural principle (load-bearing)

**Every module is an agnostic, composable peer with horizontal + vertical scaling first-class.**

- **Agnostic** — modules don't import mindX. They expose one clean interface (Solidity ABI or Python/TS API). OpenClaw, NanoClaw, ZeroClaw, NullClaw, or your stack composes them the same way mindX does.
- **Composable** — modules are wired by interfaces only. No module imports another's internals. Pick any subset.
- **Horizontal scaling** — each module is sharded along its natural axis (more peers / more workers / more chains).
- **Vertical scaling** — each module accepts richer instances per slot (more model capacity / larger payloads / higher fee tiers / deeper DAGs).
- **mindX is one consumer** — `/openagents.html` is a *composition demo*, not the only home.

Memory pin: this principle is saved at `~/.claude/projects/-home-hacker-mindX/memory/agnostic_modules_principle.md` and applies to all future module work.

---

## 4. Architecture (modules as peers)

```
                ┌───────────────────────────────────────────────────────┐
                │   ANY FRAMEWORK (mindX, OpenClaw, NanoClaw, …)        │
                │   composes any subset of the modules below.           │
                └─────────────────────────┬─────────────────────────────┘
                                          │
   ┌──────────────────┬───────────────┬───┼────┬──────────────┬────────────────┐
   ▼                  ▼               ▼   ▼    ▼              ▼                ▼
┌───────────┐  ┌───────────────┐  ┌─────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐
│ iNFT_7857 │  │ 0G Adapter    │  │ Conclave│ │ BANKON v1│ │ KeeperHub    │ │ Uniswap V4  │
│ ERC-7857  │  │ Py + Node     │  │ AXL mesh│ │ ENS Sub  │ │ x402 bridge  │ │ trader      │
│ + UI (M1) │  │ + sidecar(M2) │  │ + bond  │ │ + Oracle │ │              │ │ + persona   │
│           │  │               │  │ + slash │ │ + Router │ │ inbound +    │ │ + decision  │
│           │  │               │  │ (M3)    │ │ + Gate   │ │ outbound (M5)│ │ log (M6)    │
│           │  │               │  │         │ │ (M4)     │ │              │ │             │
└─────▲─────┘  └───────▲───────┘  └────▲────┘ └─────▲────┘ └──────▲───────┘ └─────▲───────┘
      │                │               │            │             │                │
      │       ┌────────┴────────┐      │            │             │                │
      │       │ THOT.commit()   │      │            │             │                │
      │       │ memory anchor   │      │            │             │                │
      │       │ (M7)            │      │            │             │                │
      │       └────────▲────────┘      │            │             │                │
      │                │               │            │             │                │
      │       ┌────────┴────────┐      │            │             │                │
      └───────│ ERC-8004        │──────┴────────────┘             │                │
              │ AgentRegistry   │                                 │                │
              │ (capability     │                                 │                │
              │  + attestation) │                                 │                │
              │ (M8)            │                                 │                │
              └─────────────────┘                                 │                │
                                                                  ▼                ▼
                                              /openagents.html (mindX composition demo)
```

---

## 5. Per-module technical reference

### Module 1 — iNFT-7857 (ERC-7857 hardened build)

**Purpose:** Anchor encrypted intelligence + persistent memory on chain. Standard `transferFrom` is **gated** — transfers happen only via oracle-signed re-encryption (`transferWithSealedKey`).

**Files**
- Contract: [`daio/contracts/inft/iNFT_7857.sol`](../../daio/contracts/inft/iNFT_7857.sol) (438 lines, OpenZeppelin v5)
- Tests: [`daio/contracts/test/inft/iNFT_7857.t.sol`](../../daio/contracts/test/inft/iNFT_7857.t.sol) (~570 lines)
- UI: [`mindx_backend_service/inft7857.html`](../../mindx_backend_service/inft7857.html) (single-file ethers v6 console)
- Reference doc: [`docs/INFT_7857.md`](../../docs/INFT_7857.md)
- Deploy script: [`openagents/deploy/deploy_galileo.sh`](../deploy/deploy_galileo.sh)

**Public interface (key functions)**

```solidity
function mintAgent(address to, bytes32 contentRoot, string calldata storageURI,
                   bytes32 metadataRoot, uint32 dimensions, uint8 parallelUnits,
                   bytes32 sealedKeyHash, string calldata tokenURI_)
    external onlyRole(MINTER_ROLE) returns (uint256 tokenId);

function transferWithSealedKey(address from, address to, uint256 tokenId,
                               bytes calldata sealedKey, bytes calldata oracleProof)
    external;                  // EIP-712 oracle signature required

function cloneAgent(uint256 tokenId, address to,
                    bytes calldata sealedKey, bytes calldata oracleProof)
    external payable returns (uint256 childId);

function authorizeUsage(uint256 tokenId, address executor, uint256 permissions, uint64 expiresAt) external;
function revokeUsage(uint256 tokenId, address executor) external;
function burn(uint256 tokenId) public;          // contentRoot stays reserved post-burn
function bindAgentId(uint256, string)  external;
function offerOnAgenticPlace(uint256, address, uint256, bool, address) external;
function bindBankonVault(uint256, address, bytes32) external;
```

**Roles:** `DEFAULT_ADMIN_ROLE`, `MINTER_ROLE`, `ORACLE_ROLE`, `PAUSER_ROLE`, `TREASURER_ROLE`. Grant `MINTER_ROLE` to AgenticPlace marketplace, BANKON registrar, IDManagerAgent, etc.

**How to call (cast)**

```bash
# Mint
cast send $INFT "mintAgent(address,bytes32,string,bytes32,uint32,uint8,bytes32,string)" \
  $RECIPIENT $ROOT "0g://aristotle/$ROOT" $METADATA_ROOT 2048 8 $SEALED_KEY_HASH "" \
  --rpc-url $ZEROG_RPC_URL --private-key $ZEROG_PRIVATE_KEY

# Inspect
cast call $INFT "getPayload(uint256)" $TOKEN_ID --rpc-url $ZEROG_RPC_URL
cast call $INFT "ownerOf(uint256)" $TOKEN_ID --rpc-url $ZEROG_RPC_URL
```

**Tests:** `cd daio/contracts && FOUNDRY_PROFILE=inft forge test` → **56/56 pass** (53 unit + 3 fuzz at 256 runs each).

---

### Module 2 — 0G Adapter (Python primary + Node sidecar)

**Purpose:** Speak 0G Compute (TEE-attested inference) + 0G Storage from any Python framework. Sidecar wraps the TS-only `@0gfoundation/0g-ts-sdk@^1.2.6` for storage; Python handler talks the OpenAI-compatible Compute endpoint directly and captures the `ZG-Res-Key` attestation header per call.

**Files**
- Python LLM client: [`llm/zerog_handler.py`](../../llm/zerog_handler.py)
- Python storage proxy: [`agents/storage/zerog_provider.py`](../../agents/storage/zerog_provider.py)
- Node sidecar: [`openagents/sidecar/index.ts`](../sidecar/index.ts), [`package.json`](../sidecar/package.json)
- Model registry: [`models/zerog.yaml`](../../models/zerog.yaml)

**Three mandatory SDK calls per the 0G integration guide**
1. `getRequestHeaders()` per inference → emulated as `X-Request-Id` fingerprint (32-byte hex, replay-protected)
2. Capture `ZG-Res-Key` response header → `handler.last_attestation`
3. `processResponse()` → optional pointer to a broker sidecar via `ZEROG_BROKER_URL`; fire-and-forget settlement

**Sidecar interface**

| Method | Path | Returns |
|--------|------|---------|
| POST | `/upload` (multipart `file`) | `{ rootHash, txHash, uri, explorer, bytes }` |
| GET  | `/retrieve/:root` | bytes (Content-Type: octet-stream) |
| GET  | `/health` | `{ ok, network, rpc, indexer, signer, balance, sdk }` |

**Python usage**

```python
from llm.zerog_handler import ZeroGHandler
from agents.storage.zerog_provider import ZeroGProvider

llm = ZeroGHandler(api_key="app-sk-...")          # OPENAI-shape
text = await llm.generate_text(
    prompt="hello", model="zerog/gpt-oss-120b", max_tokens=64,
)
print(text, llm.last_attestation, llm.last_request_id)

provider = ZeroGProvider()                        # talks to localhost:7878
root, tx = await provider.upload(b"persona-bytes")
print(root.value, root.uri, tx)
```

**Boot the sidecar**

```bash
cd openagents/sidecar && npm install
ZEROG_PRIVATE_KEY=0x... \
ZEROG_RPC_URL=https://evmrpc.0g.ai \
ZEROG_INDEXER_URL=https://indexer-storage-turbo.0g.ai \
ZEROG_NETWORK_NAME=aristotle \
node --experimental-strip-types index.ts
```

---

### Module 3 — Conclave (Gensyn AXL)

**Purpose:** Peer-to-peer signed-envelope deliberation among a fixed set of cryptographically-identified agents over Gensyn AXL. Cabinet pattern: 1 Convener (CEO) + 7 Counsellors. Resolutions anchored on chain via `Conclave.sol` + `ConclaveBond.sol`; deliberation never leaves the mesh.

**Files**
- Python protocol: [`openagents/conclave/conclave/`](../conclave/conclave/) (axl_client, agent, chain, crypto, messages, protocol, roles, session)
- Solidity: [`openagents/conclave/contracts/src/Conclave.sol`](../conclave/contracts/src/Conclave.sol), `ConclaveBond.sol`
- Examples: [`openagents/conclave/examples/run_local_8node.sh`](../conclave/examples/run_local_8node.sh)
- Submission: [`openagents/conclave/SUBMISSION.md`](../conclave/SUBMISSION.md)
- mindX integration adapter: [`openagents/conclave/integrations/mindx_boardroom_adapter.py`](../conclave/integrations/mindx_boardroom_adapter.py)

**Composition adapter (illustrative)**

```python
from conclave.protocol import Conclave
from conclave.roles    import Role
from conclave.integrations.mindx_boardroom_adapter import (
    MindxBoardroomAdapter, is_high_stakes, cabinet_from_local_keys,
)

local_conclave = Conclave(keypair=ceo_keypair, role=Role.CEO, axl=axl_client)
cabinet = cabinet_from_local_keys([
    (ceo_pub,  Role.CEO,  ceo_evm),
    (cfo_pub,  Role.CFO,  cfo_evm),
    # …seven soldiers…
])
adapter = MindxBoardroomAdapter(conclave=local_conclave, cabinet=cabinet)

# Routes high-stakes directives through CONCLAVE; falls back to fast path otherwise.
result = await adapter.route(
    "Discuss M&A with Acme Corp",
    mindx_boardroom_runner=mindx_fast_boardroom,   # any framework's fast path
)
```

**Tests:** Python `cd openagents/conclave && pytest tests/` → 9 ✓ · Solidity `forge test` → 10 ✓ · 8-node demo `examples/run_local_8node.sh`.

---

### Module 4 — BANKON v1 (ENS NameWrapper subname registrar)

**Purpose:** Issue `<label>.bankon.eth` subnames with length-tiered pricing, EIP-712 voucher payment, multi-chain x402 settlement, BONAFIDE-style reputation gating, ERC-8004 bundled identity mint, and soulbound fuse profile `0x50005`.

**Files** ([`daio/contracts/ens/v1/`](../../daio/contracts/ens/v1/))
- `BankonSubnameRegistrar.sol` — main registrar (paid + free + renew paths)
- `BankonPriceOracle.sol` — length-tier USD pricing + Chainlink + Uniswap v3 TWAP
- `BankonPaymentRouter.sol` — 40/25/15/10/10 revenue split, BuybackTriggerCrossed event
- `BankonReputationGate.sol` — pluggable BONAFIDE/TEE/stake gate
- `interfaces/IBankon.sol` — all six interfaces
- Tests: `test/BankonSubnameRegistrar.t.sol` + `test/mocks/{MockNameWrapper,MockResolver,MockIdentityRegistry}.sol`
- Python client: [`openagents/ens/subdomain_issuer.py`](../ens/subdomain_issuer.py)
- Deploy script: [`openagents/ens/deploy_registrar.sh`](../ens/deploy_registrar.sh)

**Pricing tiers** (USD, default — operator can override via `BankonPriceOracle.setPrices()`)

| Label length | Price/yr |
|-------------:|---------:|
| 3-char | $320 |
| 4-char | $80 |
| 5-char | $5 |
| 6-char | $3 |
| 7+ char | $1 |
| Reputable agent (≥100 BONAFIDE OR ≥10k PYTHAI stake OR TEE-attested) | **free** for 7+ char |

PYTHAI-paid registrations get a 20% discount.

**Soulbound fuse profile:** `0x50005` = `PARENT_CANNOT_CONTROL | CANNOT_UNWRAP | CANNOT_TRANSFER | CAN_EXTEND_EXPIRY`.

**Public interface (Solidity)**

```solidity
function register(string calldata label, address owner, uint64 expiry,
                  bytes32 paymentReceiptHash, uint256 deadline,
                  bytes calldata gatewaySig, AgentMetadata calldata meta)
    external returns (bytes32 node, uint256 agentId);

function registerFree(string calldata label, address owner, uint64 expiry,
                      AgentMetadata calldata meta)
    external returns (bytes32 node, uint256 agentId);

function renew(string calldata label, uint64 newExpiry,
               bytes32 paymentReceiptHash, uint256 deadline,
               bytes calldata gatewaySig)
    external;

function quoteUSD(string calldata label, uint64 expiry) external view returns (uint256 usd6);
```

`AgentMetadata` (7 fields): `agentURI`, `mindxEndpoint`, `x402Endpoint`, `algoIDNftDID`, `contenthash`, `baseAddress`, `algoAddr`.

**Python usage**

```python
from openagents.ens.subdomain_issuer import SubdomainIssuer, AgentMetadata, issue_for_agent_async

# Free path (reputation-gated, 7+ char labels)
issuer = SubdomainIssuer()
res = await issuer.register_free(
    "ceo-mastermind", agent_wallet,
    AgentMetadata(agentURI="ipfs://Qm/agent.json",
                  mindxEndpoint="https://mindx.pythai.net/agent/x"),
)

# Paid path (signs an EIP-712 voucher with ENS_GATEWAY_SIGNER_PK)
res = await issuer.register_paid(
    "alice", agent_wallet,
    AgentMetadata(agentURI="ipfs://Qm/agent.json"),
)

# Convenience helper (free first, paid fallback)
res = await issue_for_agent_async("my-agent", wallet, persona_url="...", summary="...")
```

**Tests:** `FOUNDRY_PROFILE=bankon forge test` → **29/29 pass** (28 unit + 1 fuzz at 256 runs).

---

### Module 5 — KeeperHub Bridge (x402/MPP)

**Purpose:** Bidirectional bridge between AgenticPlace's existing pay2play x402 settler and KeeperHub. Inbound (KH wallets pay AgenticPlace jobs) + outbound (mindX consumes paid KH workflows).

**Files**
- Bridge routes: [`openagents/keeperhub/bridge_routes.py`](../keeperhub/bridge_routes.py)
- Python consumer client: [`tools/keeperhub_x402_client.py`](../../tools/keeperhub_x402_client.py)
- Builder feedback: [`docs/keeperhub/FEEDBACK.md`](keeperhub/FEEDBACK.md)

**Endpoints (mounted under `/p2p/keeperhub/`)**

| Method | Path | Notes |
|--------|------|-------|
| GET  | `/p2p/keeperhub/info` | metadata + supported networks |
| POST | `/p2p/keeperhub/agent/register` | wraps AgenticPlace `/p2p/agent/register` (returns 402 with dual challenge) |
| POST | `/p2p/keeperhub/job/create` | wraps AgenticPlace `/p2p/job/create` |
| POST | `/p2p/keeperhub/inference` | runs 0G Compute via the Python handler, $0.005 USDC default |
| POST | `/p2p/keeperhub/workflow/callback` | webhook target — KH calls this when a customer pays |

**Dual-network 402 envelope** (verbatim what we return)

```json
{
  "x402Version": 1,
  "accepts": [
    {"scheme": "exact", "network": "base",  "chainId": 8453, "asset": "0x83358...",
     "maxAmountRequired": "5000", "payTo": "<mindX recipient>", "resource": "...",
     "extra": { "nonce": "0x...", "expiresAt": 1714400000 }},
    {"scheme": "mpp",   "network": "tempo", "chainId": 4217, "asset": "0x20c0...",
     "maxAmountRequired": "5000", "payTo": "<mindX recipient>", "resource": "...",
     "extra": { "nonce": "0x...", "expiresAt": 1714400000 }}
  ]
}
```

5000 USDC base units = $0.005 (USDC is 6-decimal).

**Consume a paid KH workflow from Python**

```python
from tools.keeperhub_x402_client import KeeperHubX402Client

client = KeeperHubX402Client(buyer_private_key=os.environ["KH_BUYER_PRIVATE_KEY"])
result = await client.fetch(
    "POST", "https://app.keeperhub.com/some-paid-workflow",
    json_body={"input": "..."},
    max_pay_usdc=0.10,
)
print(result["selected_scheme"], result["response"])
```

---

### Module 6 — Uniswap V4 Trader (BDI persona on Sepolia)

**Purpose:** BDI-style agent that perceives pool state, deliberates against the trader persona, decides one action (`quote` / `swap` / `hold`), executes against Uniswap V4, and logs every cycle.

**Files**
- Tool: [`tools/uniswap_v4_tool.py`](../../tools/uniswap_v4_tool.py) — `BaseTool` exposing `info`/`quote`/`swap`/`balance`
- Persona: [`personas/trader.prompt`](../../personas/trader.prompt) — mandate + hard constraints (≤0.5% slippage, ≤$5 position, 30% USDC reserve)
- Demo: [`openagents/uniswap/demo_trader.py`](../uniswap/demo_trader.py) — 30-min loop
- Decision log: `data/logs/uniswap_decisions.jsonl`
- Builder feedback: [`docs/uniswap/FEEDBACK.md`](uniswap/FEEDBACK.md)

**Run a 30-min trader session**

```bash
# Live (any LLM you have configured)
python openagents/uniswap/demo_trader.py --duration 30 --provider zerog --model zerog/gpt-oss-120b

# Dry-run (no swaps, just decisions logged)
python openagents/uniswap/demo_trader.py --duration 5 --dry-run

# Quick smoke (no LLM — every cycle holds, but tool path is exercised)
python openagents/uniswap/demo_trader.py --duration 1 --no-llm --dry-run
```

Every cycle row in `data/logs/uniswap_decisions.jsonl`:

```json
{
  "ts": "2026-04-28T16:00:29Z", "cycle": 5, "trader": "0x...",
  "perceived": { "info": {...}, "USDC_balance": {...}, "WETH_balance": {...} },
  "decision":  { "action": "quote", "rationale": "...", "confidence": 0.78, ... },
  "outcome":   { "executed": true, "result": { "ok": true, "amount_out": "493210000000000", ... } },
  "executed":  true, "action": "quote", "rationale": "...", "confidence": 0.78
}
```

---

### Module 7 — THOT v1 (memory-anchoring primitive)

**Purpose:** Pillar-gated `commit()` that anchors a single reasoning step on chain via `(rootHash, chatID, parentRootHash)` triples. Idempotent: re-committing the same `(author, rootHash, chatID)` returns the existing tokenId. The `parentRootHash` field forms an episodic-memory DAG.

**Files**
- Contract: [`daio/contracts/THOT/v1/THOT.sol`](../../daio/contracts/THOT/v1/THOT.sol)
- Tests: [`daio/contracts/THOT/v1/test/THOT.t.sol`](../../daio/contracts/THOT/v1/test/THOT.t.sol)
- Reference spec: [`docs/0g/THOT_0G_MEMORY_ANCHOR.md`](0g/THOT_0G_MEMORY_ANCHOR.md)

**Public interface**

```solidity
struct Memory {
    bytes32 rootHash;        // 0G Storage merkle root
    bytes32 chatID;          // 0G Compute TEE attestation (ZG-Res-Key)
    address provider;        // 0G provider address
    bytes32 parentRootHash;  // 0 if root memory; else parent's rootHash
    uint40  timestamp;
    address pillar;
    address author;
}

function commit(address author, bytes32 rootHash, bytes32 chatID,
                address provider, bytes32 parentRootHash)
    external onlyRole(PILLAR_ROLE) returns (uint256 tokenId);

mapping(uint256 => Memory) public memories;
mapping(bytes32 => uint256) public rootIndex;     // canonical tokenId per root
```

`tokenId = uint256(keccak256(abi.encodePacked(author, rootHash, chatID)))` — content-addressed.

**Wire your reasoning loop as a pillar**

```bash
# After deploying, grant PILLAR_ROLE to your contract or EOA:
cast send $THOT "grantRole(bytes32,address)" \
  $(cast keccak "PILLAR_ROLE") $YOUR_PILLAR \
  --rpc-url $RPC_URL --private-key $ADMIN_PK

# Then any pillar can commit:
cast send $THOT "commit(address,bytes32,bytes32,address,bytes32)" \
  $AGENT $ROOT_HASH $CHAT_ID $PROVIDER $PARENT_HASH \
  --rpc-url $RPC_URL --private-key $PILLAR_PK
```

**Tests:** `FOUNDRY_PROFILE=thot forge test` → **14/14 pass** (mint, idempotency, pillar gate, parent DAG validation, event emission, interface support).

---

### Module 8 — AgentRegistry (ERC-8004-aligned)

**Purpose:** Identity + capability registry above any agent token (iNFT-7857, plain ERC-721, none). Records owner address, human-readable agent_id, optional linked iNFT, capability bitmap (interpreted off-chain), and a growing list of EIP-712-signed attestations.

**Files**
- Contract: [`daio/contracts/agentregistry/AgentRegistry.sol`](../../daio/contracts/agentregistry/AgentRegistry.sol)
- Tests: [`daio/contracts/agentregistry/test/AgentRegistry.t.sol`](../../daio/contracts/agentregistry/test/AgentRegistry.t.sol)

**Public interface**

```solidity
interface IAgentRegistry {
    function register(address owner, string calldata agentId,
                      address linkedINFT_7857, bytes32 capabilityBitmap,
                      string calldata attestationURI)
        external returns (uint256 agentTokenId);

    function setCapabilities(uint256 agentTokenId, bytes32 newBitmap) external;

    function attest(uint256 agentTokenId, string calldata attestationURI,
                    bytes calldata signature)
        external;                  // EIP-712 ATTESTOR_ROLE signature

    function getAgent(uint256 agentTokenId)
        external view
        returns (address owner, string memory agentId, address linkedINFT_7857,
                 bytes32 capabilityBitmap, string memory attestationURI,
                 uint256 attestorCount);
}
```

**Roles:** `DEFAULT_ADMIN_ROLE`, `MINTER_ROLE` (BANKON registrar / iNFT_7857 / IDManagerAgent), `ATTESTOR_ROLE` (TEE / ZK verifiers).

**Soulbound option:** `setSoulbound(tokenId, true)` freezes future transfers.

**Python usage**

```python
from web3 import Web3
w3 = Web3(Web3.HTTPProvider("https://evmrpc.0g.ai"))
registry = w3.eth.contract(address=REG_ADDR, abi=REGISTRY_ABI)

tx = registry.functions.register(
    owner=agent_wallet,
    agentId="ceo-mastermind",
    linkedINFT_7857=inft_addr,
    capabilityBitmap=b"\x00" * 31 + b"\x01",        # bit 0 = "can do inference"
    attestationURI="ipfs://Qm/attestation.json",
).build_transaction({"from": ...})
```

**Tests:** `FOUNDRY_PROFILE=agentregistry forge test` → **20/20 pass**.

---

## 6. Composition pattern — minimum-viable agent

Below combines all eight modules into one Python coroutine. Any framework can lift this same shape; mindX is one consumer.

```python
import asyncio
from openagents.ens.subdomain_issuer            import SubdomainIssuer, AgentMetadata
from openagents.conclave.integrations           import mindx_boardroom_adapter as adapter
from agents.storage.zerog_provider              import ZeroGProvider
from llm.zerog_handler                          import ZeroGHandler
from tools.uniswap_v4_tool                      import UniswapV4Tool
from tools.keeperhub_x402_client                import KeeperHubX402Client

async def spawn_and_run_one_cycle(agent_id: str, agent_wallet: str):
    # ── 1. Identity ────────────────────────────────────────────────
    issuer = SubdomainIssuer()
    bankon_res = await issuer.register_free(
        agent_id, agent_wallet,
        AgentMetadata(agentURI="ipfs://Qm/agent.json",
                      mindxEndpoint="https://you.example/agent/x"),
    )                                           # also bundles ERC-8004 mint

    # ── 2. Inference ───────────────────────────────────────────────
    llm = ZeroGHandler(api_key=ZEROG_API_KEY)
    text = await llm.generate_text(
        prompt="Decide one trade for today.",
        model="zerog/gpt-oss-120b", max_tokens=200,
    )
    chat_id = llm.last_attestation              # ZG-Res-Key

    # ── 3. Memory ──────────────────────────────────────────────────
    provider = ZeroGProvider()
    root, tx = await provider.upload(text.encode())  # 0G Storage
    # → call THOT.commit(author, root.value, chat_id, provider_addr, parent=0)

    # ── 4. Marketplace consumption (KeeperHub paid workflow) ───────
    kh = KeeperHubX402Client(buyer_private_key=KH_BUYER_PK)
    paid_result = await kh.fetch(
        "POST", "https://app.keeperhub.com/external-data-feed",
        json_body={"symbol": "ETH/USDC"},
    )

    # ── 5. Action (Uniswap V4) ─────────────────────────────────────
    swap_tool = UniswapV4Tool()
    quote = await swap_tool.execute("quote", {
        "token_in": USDC, "token_out": WETH, "amount_in": 1_000_000,
    })

    # ── 6. High-stakes deliberation (Conclave compose-only here) ───
    if any(k in text.lower() for k in ("trade secret", "m&a")):
        await adapter.route(text, mindx_boardroom_runner=fast_path)

    return {
        "agent_id": agent_id,
        "subname": bankon_res.get("subname"),
        "attestation": chat_id,
        "memory_root": root.value,
        "kh_response": paid_result.get("response"),
        "uniswap_quote": quote,
    }

asyncio.run(spawn_and_run_one_cycle("alice-trader-x", "0xAGENT"))
```

The mindX-shipped version of this composition lives in [`openagents/demo_agent.py`](../demo_agent.py) — 10 numbered steps, every step skippable if its prerequisites are missing.

---

## 7. Operations

### Boot the dashboard

```bash
git clone https://github.com/Professor-Codephreak/mindX
cd mindX
python -m venv .mindx_env && .mindx_env/bin/pip install -r requirements.txt
cd openagents/sidecar && npm install && cd ../..

./mindX.sh --frontend       # frontend on :3000, backend on :8000
# → http://localhost:8000/openagents.html      8-panel composition demo
# → http://localhost:8000/inft7857             interactive iNFT-7857 console
# → http://localhost:8000/p2p/keeperhub/info   KeeperHub bridge metadata
```

### Run all four contract test suites

```bash
cd daio/contracts
FOUNDRY_PROFILE=inft           forge test          # iNFT-7857: 56/56
FOUNDRY_PROFILE=bankon         forge test          # BANKON v1: 29/29
FOUNDRY_PROFILE=thot           forge test          # THOT v1:   14/14
FOUNDRY_PROFILE=agentregistry  forge test          # AgentRegistry: 20/20
```

### Run the Conclave protocol tests

```bash
cd openagents/conclave
pytest tests/                                       # 9 Python protocol tests
cd contracts && forge test                          # 10 Solidity tests
```

### Run the composition demo

```bash
python openagents/demo_agent.py                     # full 10-step run (needs all keys)
python openagents/demo_agent.py --dry-run           # stop after payload build
python openagents/demo_agent.py --skip-mint --skip-extras  # 0G inference + anchor only
```

### Run the Uniswap trader

```bash
python openagents/uniswap/demo_trader.py --duration 30
```

---

## 8. Test totals + verification matrix

```
iNFT_7857          53 unit + 3 fuzz   → 56 ✓
BANKON v1          28 unit + 1 fuzz   → 29 ✓
THOT v1            14 unit            → 14 ✓
AgentRegistry      20 unit            → 20 ✓
Conclave (Python)   9                 →  9 ✓
Conclave (Solidity) 10                → 10 ✓
─────────────────────────────────────────────
TOTAL                                  138 ✓
```

| Verification | Command | Expected |
|--------------|---------|----------|
| `/openagents.html` renders 8 panels | `curl http://localhost:8000/openagents.html \| grep -E 'M[1-8]'` | 8 matches |
| Summary advertises 138-test total | `curl http://localhost:8000/insight/openagents/summary \| jq '.test_totals.total'` | `138` |
| KH bridge returns dual envelope | `curl -X POST http://localhost:8000/p2p/keeperhub/inference -d '{}'` | 402 + `accepts: [exact/base, mpp/tempo]` |
| 0G handler captures attestation | `curl -X POST .../llm/chat -d '{"provider":"zerog",...}'` | 200 + non-empty `attestation` |
| Sidecar storage round-trip | upload bytes → retrieve same root | bytes match |
| iNFT-7857 deployed | `cast call $INFT "name()(string)" --rpc-url $RPC` | returns `mindX iNFT-7857` |
| BANKON subname registered | `dig +short alice.bankon.eth ANY` (or web3 resolver) | returns mindX agent record |
| Uniswap quote | `python openagents/uniswap/demo_trader.py --duration 1 --no-llm --dry-run` | log file appended, 2 cycles |

---

## 9. Operator credentials cheatsheet

You have **18 0G mainnet tokens** (Aristotle, chain 16661) — recommended split:
- 4 0G → fund the 0G Compute broker (3 ledger + 1 provider locked)
- 5 0G → contract deployment buffer (iNFT_7857 + THOT v1 + AgentRegistry + DatasetRegistry)
- 9 0G → operating budget (mints, inference, anchors, settlements)

Verify balance: `cast balance <addr> --rpc-url https://evmrpc.0g.ai`

### Path A — BANKON Vault (preferred — encrypted)

```bash
python manage_credentials.py store zerog_api_key         "app-sk-..."
python manage_credentials.py store zerog_private_key     "0x..."
python manage_credentials.py store ens_controller_pk     "0x..."     # bankon.eth controller
python manage_credentials.py store ens_gateway_signer_pk "0x..."     # GATEWAY_SIGNER_ROLE
python manage_credentials.py store keeperhub_org_key     "kh_..."
python manage_credentials.py store kh_buyer_private_key  "0x..."
python manage_credentials.py store kh_recipient_address  "0x..."     # mindX Turnkey wallet on Base
python manage_credentials.py store kh_webhook_secret     "<random>"
python manage_credentials.py store uniswap_trader_pk     "0x..."     # Sepolia (optional)
```

### Path B — `.env` file

```dotenv
# 0G mainnet (Aristotle)
ZEROG_API_KEY=app-sk-...
ZEROG_PRIVATE_KEY=0x...
ZEROG_RPC_URL=https://evmrpc.0g.ai
ZEROG_INDEXER_URL=https://indexer-storage-turbo.0g.ai
ZEROG_NETWORK_NAME=aristotle
ZEROG_EXPLORER=https://chainscan.0g.ai
# Testnet alternative (Galileo, free faucet):
# ZEROG_RPC_URL=https://evmrpc-testnet.0g.ai
# ZEROG_INDEXER_URL=https://indexer-storage-testnet-turbo.0g.ai
# ZEROG_NETWORK_NAME=galileo
# ZEROG_EXPLORER=https://chainscan-galileo.0g.ai

# ENS / BANKON
ENS_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
ENS_CONTROLLER_PK=0x...
ENS_GATEWAY_SIGNER_PK=0x...
ENS_NETWORK=sepolia

# KeeperHub
KH_RECIPIENT_ADDRESS=0x...
KEEPERHUB_ORG_KEY=kh_...
KH_BUYER_PRIVATE_KEY=0x...
KH_WEBHOOK_SECRET=

# Uniswap (optional)
UNISWAP_TRADER_PK=0x...
```

### Recommended setup order

1. **Store keys** (vault or `.env`)
2. **Fund 0G Compute broker** with 4 0G via the broker UI (add ledger + transfer to provider)
3. **Wrap `bankon.eth` on Sepolia** at https://app.ens.domains/bankon.eth — burn fuses `CANNOT_UNWRAP` (0x1) + `PARENT_CANNOT_CONTROL` (0x80000)
4. **Run `./openagents/deploy/deploy_galileo.sh`** (or duplicate for Aristotle mainnet)
5. **Run `./openagents/ens/deploy_registrar.sh`**
6. **Set ENS approval:** `cast send <NameWrapper> "setApprovalForAll(address,bool)" <BankonSubnameRegistrar> true --rpc-url $ENS_RPC_URL --private-key $ENS_CONTROLLER_PK`
7. **Boot sidecar + backend:** `node openagents/sidecar/index.ts &` then `./mindX.sh`
8. **Run composition demo:** `python openagents/demo_agent.py --agent-id ceo-mastermind-v1`

After step 7, the `/openagents` dashboard panels go from "tested-not-deployed" badges to "deployed" with live event rows. The composition demo prints all 10 step receipts as the video record.

---

## 10. Cross-references

**Per-module canonical specs (operator reads in this order if working on that module):**

- iNFT-7857: [docs/INFT_7857.md](../../docs/INFT_7857.md)
- 0G adapter / Compute / Storage: [`docs/0g/OG_INTEGRATION_GUIDE.md`](0g/OG_INTEGRATION_GUIDE.md), [`docs/0g/THOT_0G_MEMORY_ANCHOR.md`](0g/THOT_0G_MEMORY_ANCHOR.md)
- Conclave: [openagents/conclave/README.md](../conclave/README.md), [SUBMISSION.md](../conclave/SUBMISSION.md), [docs/THREAT_MODEL.md](../conclave/docs/THREAT_MODEL.md)
- BANKON v1: [`docs/ens/SUBNAME_REGISTRY.md`](ens/SUBNAME_REGISTRY.md) (canonical spec — source of truth), [`docs/ens/BANKON_ARCHITECTURE.md`](ens/BANKON_ARCHITECTURE.md) (full architecture deep dive)
- Submission strategy: [`openagents/README.md`](../README.md), [`docs/ARCHITECTURE.md`](ARCHITECTURE.md), [`docs/QUICKSTART.md`](QUICKSTART.md), [`docs/INDEX.md`](INDEX.md)

**Repo-wide:**

- Top-level CLAUDE.md (project guidance for AI agents)
- AGENTS.md (canonical agent guidance)
- docs/INDEX.md (full doc index — 194+ files)
- mindx_backend_service/main_service.py (FastAPI app — all routes mounted here)

**Live URLs (when backend is running):**

- `/openagents.html` — 8-panel composition dashboard
- `/inft7857.html` — interactive iNFT-7857 console (mint / inspect / transfer / clone / burn / bind / admin)
- `/feedback.html` — Mind of mindX (BDI activity, dream cycles, boardroom)
- `/insight/openagents/{compute,storage,inft,conclave,ens,keeperhub,uniswap,thot,agentregistry,summary}` — JSON insight endpoints (all support `?h=true` for plain-text)

---

*Submission for **ETHGlobal Open Agents** · Apr 24 → May 6 2026 · BANKON × mindX*
*Repo: github.com/Professor-Codephreak/mindX · Live: mindx.pythai.net/openagents · Marketplace: agenticplace.pythai.net*
