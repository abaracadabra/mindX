---
name: openagents — Production Handoff
description: Complete project summary, shadow-overlord wallet handoff procedure, deployment sequence across 0G mainnet + Ethereum, and ABI-driven contract-interaction wiring. Read this before deploying.
---

# openagents — Production Handoff

This document is the single source of truth for taking openagents from
"hackathon-ready local demo" to "live on chain with the shadow-overlord
wallet driving everything." It covers:

1. What openagents *is* (module inventory + sibling modules)
2. Live infrastructure (what's already running on `mindx.pythai.net`)
3. Shadow-overlord wallet generation + handoff procedure
4. Funding requirements per network
5. Full deployment sequence (12 contracts across 2 chains)
6. ABI wiring — how openagents calls deployed contracts
7. Verification checklist + Day-1 operational runbook

---

## 1. Project summary

openagents is a roster of 8 agnostic, composable peer modules + 1 bonus
composability demo, plus a sibling **SPINTRADE** module for local trade
testing. mindX is one canonical consumer; the modules are framework-agnostic
and can be lifted by any agent stack.

### Core 8 modules

| ID | Module | Repo path | What it does |
|---|---|---|---|
| M1 | **iNFT-7857** | `daio/contracts/inft/iNFT_7857.sol` | ERC-7857 hardened NFT — sealed-key transfer gating, EIP-712 oracle proofs, AgentRegistry/BANKON/0G hooks |
| M2 | **0G Adapter** | `llm/zerog_handler.py` + `agents/storage/zerog_provider.py` + sidecar | LLM compute + storage — captures `ZG-Res-Key` attestations per call |
| M3 | **Conclave** | `openagents/conclave/contracts/src/{Conclave,ConclaveBond}.sol` + Tessera/Censura | AXL/Gensyn P2P signed-envelope mesh deliberation. Cabinet pattern (CEO + 7 soldiers), bonded |
| M4 | **BANKON v1** | `daio/contracts/ens/v1/{BankonSubnameRegistrar,BankonPaymentRouter,BankonPriceOracle,BankonReputationGate}.sol` | ENS NameWrapper subname registrar — soulbound `<agent>.bankon.eth`, length-tiered pricing, EIP-712 voucher, ERC-8004 bundle, free agent path |
| M5 | **KeeperHub Bridge** | `mindx_backend_service/keeperhub/` + `tools/keeperhub_*.py` | Bidirectional x402 + MPP bridge between AgenticPlace and KeeperHub |
| M6 | **Uniswap V4 Trader** | `openagents/uniswap/demo_trader.py` + `tools/uniswap_api_tool.py` | BDI loop (perceive → LLM deliberate → execute). Three execution venues: trade-api (default — real Uniswap gateway), spintrade (local CPMM), v4-stub (legacy) |
| M7 | **THOT.commit()** | `daio/contracts/THOT/v1/THOT.sol` | Memory-anchoring primitive — pillar-gated commit() with (rootHash, chatID, parentRootHash) → episodic-memory DAG |
| M8 | **AgentRegistry** | `daio/contracts/agentregistry/AgentRegistry.sol` | ERC-8004 identity + capability registry — linked iNFT_7857, capability bitmap, attestor signatures, soulbound option |

### Bonus / composability demo

| Module | Repo path | What it does |
|---|---|---|
| **Cabinet** | `mindx_backend_service/bankon_vault/cabinet.py` + `cabinet.html` | Composes M2 + M4 + M8 + BANKON Vault. Provisions 1 CEO + 7 Counsellors per company; vault signs on agents' behalf without leaking keys. Shadow-overlord ECDSA gate |

### Sibling modules

| Module | Repo path | What it does |
|---|---|---|
| **SPINTRADE** | `spintrade/` (separate repo: `agenticplace/spintrade`) | Standalone Uniswap V2-style local CPMM with BANKON/PYTHAI test tokens. Used as a local execution venue for the Uniswap BDI trader. **No code-level dependency on openagents** in either direction |
| **Bankonminter UI** | `mindx_backend_service/bankonminter.html` + `tools/uniswap_api_tool.py` | Direct BankonSubnameRegistrar interaction — load deployed registrar from JSON, mint via two free paths (role-gated agent / 7+ char rep-gated) or quoted paid path |

---

## 2. Live infrastructure (already running)

Production VPS: **`mindx.pythai.net`** (Hostinger 168.231.126.58)

| Endpoint | Status | Note |
|---|---|---|
| `/` | live | mindX dashboard |
| `/openagents` | live | console index — 12 component links + module summary |
| `/uniswap` | live | possibility (live quote) + actions (BDI history) + 8-skill panel |
| `/bankonminter` | live | direct registrar mint UI |
| `/bankon-ens` | live | ENS resolver (4-RPC fallback chain) |
| `/cabinet` | live | shadow-overlord admin tier |
| `/conclave` | live | AXL mesh viewer |
| `/agentregistry` | live | ERC-8004 explorer |
| `/keeperhub` | live | x402/MPP bridge demo |
| `/zerog` | live | 0G adapter sidecar status |
| `/inft7857` | live | iNFT-7857 module status |
| `/THOT` | live | memory-anchor module |
| `/api/uniswap/{quote,check_approval,decisions,skills}` | live | vault-keyed proxy to Uniswap Trading API |
| `/api/uniswap/skills/{name}` | live | 8 Uniswap AI skills, both human + agent callable |
| `/openagents/deployments/{network}.json` | route ready | will return addresses once contracts deploy |

Backend systemd unit: `mindx.service` (User=mindx, /home/mindx/mindX/).
Reverse proxy: Apache2 with Let's Encrypt SSL.
Vault: BANKON Vault (AES-256-GCM + HKDF-SHA512). Already holds the
Uniswap Trade API key under id `uniswap_trade_api_key`.

---

## 3. Shadow-overlord wallet — generation + handoff

### Why this wallet matters

The shadow-overlord wallet plays **two roles** simultaneously:

1. **Admin gate** for BANKON Vault privileged operations — provisioning
   Cabinet wallets, signing on behalf of agents, releasing private keys.
   Every admin action requires a fresh ECDSA signature from this key.

2. **Deployer** for all 12 production contracts. The deployer becomes the
   default admin role-holder on each deployed contract. Since admin
   actions on those contracts (granting roles, pausing, treasury moves)
   should also be shadow-gated, using the same key is the canonical
   choice.

The private key **never lives on the server**. The server stores only the
public address as `SHADOW_OVERLORD_ADDRESS`. You hold the key offline.

### Generation — choose one path

#### Option A: Hardware wallet (recommended for prod)

1. Use a Ledger / Trezor / GridPlus
2. Create a fresh account on a **dedicated** derivation path (do not
   reuse a path that holds personal funds)
3. Note the public address — that's what we hand to the server

#### Option B: Airgap-generated EOA

```bash
# Generate on an airgapped machine
cast wallet new
# Output:
#   Address:     0x<your-public-address>
#   Private key: 0x<keep-this-OFFLINE>
```

Save the private key to an offline medium (paper, encrypted USB, hardware
keystore). **Never** type or paste it on a connected machine.

#### Option C: MetaMask (acceptable for staging)

1. Create a fresh MetaMask account
2. Export private key only if you need it for a CLI deploy; otherwise
   keep it in MetaMask and sign deploy txs through the wallet

### What you give us

Just one thing: **the public address**. Format:

```
SHADOW_OVERLORD_ADDRESS=0xYourFortyCharHexAddressHere
```

That's it. The server knows nothing else about the key.

### Optional: backup shadow address

For continuity if the primary key is lost, you can configure a second
address with OR-semantics:

```
SHADOW_OVERLORD_ADDRESS_PRIMARY=0xPrimary…
SHADOW_OVERLORD_ADDRESS_BACKUP=0xBackup…
```

A signature from either address satisfies the admin gate.

### Server-side install (we run this once)

```bash
# On the prod VPS (we do this together)
sudo systemctl edit mindx.service
# Add to the [Service] block:
#   Environment="SHADOW_OVERLORD_ADDRESS=0x<your-address>"
#   Environment="SHADOW_JWT_SECRET=<32-byte random hex>"
sudo systemctl daemon-reload
sudo systemctl restart mindx.service

# Verify the challenge endpoint works
curl https://mindx.pythai.net/admin/shadow/challenge
# → {"nonce":"...","message":"MINDX-SHADOW-OVERLORD\nnonce: ...","expires_at":...}
```

The JWT secret is a separate value — a 32-byte random hex string we
generate with `openssl rand -hex 32`. It signs short-lived (5min) session
JWTs after a successful ECDSA challenge. You don't need to know or hold
this; rotate quarterly.

---

## 4. Funding requirements

Per network, this is what the shadow-overlord wallet needs **before** the
deploy.

### 0G mainnet (chainId 16661, Group A — 8 contracts)

| Item | Estimate | Notes |
|---|---|---|
| Total deploy gas | ~11.9M gas | AgentRegistry + THOT + iNFT_7857 + DatasetRegistry + Tessera + Censura + Conclave + ConclaveBond |
| Live gas price (probed) | ~4 gwei | `cast gas-price --rpc-url https://evmrpc.0g.ai` |
| Total OG required | ~0.048 OG | rounding-safe minimum |
| **Recommended balance** | **0.20 OG** | leaves ~0.15 OG for cabinet onboarding + role grants + headroom |

### Ethereum mainnet (Group B — 4 BANKON contracts)

| Item | Estimate | Notes |
|---|---|---|
| Total deploy gas | ~6.6M gas | BankonPriceOracle + BankonReputationGate + BankonPaymentRouter + BankonSubnameRegistrar |
| Mainnet gas price | varies, plan ~20 gwei | check before sending |
| Total ETH required | ~0.13 ETH at 20 gwei | |
| **Recommended balance** | **0.30 ETH** | covers deploy + first 100 free agent mints + role grants |

### Sepolia (staging — same Group B)

| Item | Estimate | Notes |
|---|---|---|
| Total deploy gas | ~6.6M gas | identical contracts |
| Sepolia gas price | ~1 gwei | low |
| Total ETH required | ~0.0066 ETH | get from faucet |
| **Recommended balance** | **0.05 ETH** | faucet a fresh batch; no real money |

### Algorand (optional — Conclave bond bridge target)

The `ALGO_BRIDGE_ADDR` arg defaults to `0x0`. If you have a deployed
Algorand bridge contract, set the address before running the Conclave
deploy. Otherwise leave at `0x0` and patch later via the
`ConclaveBond.setAlgoBridge()` admin call.

---

## 5. Deployment sequence

> **Do these in the order shown.** Each phase depends on the prior phase's
> addresses. All scripts read `SHADOW_OVERLORD_PK` (or `ZEROG_PRIVATE_KEY`
> for Group A) from env and never write it to disk.

### Phase 0 — pre-flight (any network)

```bash
export SHADOW_OVERLORD_PK=0x<your-key>           # only for the deploy session
export SHADOW_OVERLORD_ADDR=$(cast wallet address --private-key $SHADOW_OVERLORD_PK)
echo "Deployer: $SHADOW_OVERLORD_ADDR"
echo "Should match SHADOW_OVERLORD_ADDRESS env on the server."

# Toolchain check
forge --version    # foundry stable, 0.2.0+
cast --version
jq --version
```

### Phase 1 — 0G mainnet (Group A: 8 contracts)

```bash
cd /home/hacker/mindX

export ZEROG_PRIVATE_KEY=$SHADOW_OVERLORD_PK
export ROYALTY_RECEIVER=$SHADOW_OVERLORD_ADDR     # or your treasury
export TREASURY_ADDR=$SHADOW_OVERLORD_ADDR
export ORACLE_ADDR=$SHADOW_OVERLORD_ADDR          # iNFT EIP-712 oracle pubkey
export ALGO_BRIDGE_ADDR=0x0000000000000000000000000000000000000000
export CLONE_FEE_WEI=10000000000000000            # 0.01 OG
export ROYALTY_BPS=250                            # 2.5%

bash openagents/deploy/deploy_0g_mainnet.sh
# → deploys 8 contracts in order
# → writes openagents/deployments/0g_mainnet.json
# → prints explorer URLs
```

The script verifies chain ID 16661, deployer balance ≥ 0.05 OG, and asks
for `DEPLOY` confirmation before sending.

### Phase 2 — verify Group A on chain

```bash
ADDRS=openagents/deployments/0g_mainnet.json
RPC=https://evmrpc.0g.ai

# AgentRegistry — should expose ERC-721 interface
cast call $(jq -r .contracts.AgentRegistry $ADDRS) \
  "supportsInterface(bytes4)(bool)" 0x80ac58cd --rpc-url $RPC
# → true

# THOT — owner is the deployer
cast call $(jq -r .contracts.THOT $ADDRS) "owner()(address)" --rpc-url $RPC

# iNFT — name + cloneFeeWei
cast call $(jq -r .contracts.iNFT_7857 $ADDRS) "name()(string)" --rpc-url $RPC
cast call $(jq -r .contracts.iNFT_7857 $ADDRS) "cloneFeeWei()(uint256)" --rpc-url $RPC

# DatasetRegistry — owner
cast call $(jq -r .contracts.DatasetRegistry $ADDRS) "owner()(address)" --rpc-url $RPC

# Tessera + Censura — admins
cast call $(jq -r .contracts.Tessera $ADDRS) "admin()(address)" --rpc-url $RPC
cast call $(jq -r .contracts.Censura $ADDRS) "admin()(address)" --rpc-url $RPC

# Conclave round-trip — bond contract is wired
cast call $(jq -r .contracts.Conclave $ADDRS) "bondContract()(address)" --rpc-url $RPC
# → should equal jq -r .contracts.ConclaveBond $ADDRS
```

### Phase 3 — wire Cabinet on 0G

The shadow-overlord must be authenticated to the live `/cabinet` endpoint
to provision PYTHAI's 8 wallets:

```bash
# 1. From your machine, hit the challenge endpoint
curl -X POST https://mindx.pythai.net/admin/shadow/challenge -d '{}' \
     -H 'content-type: application/json' > challenge.json

# 2. Sign the challenge offline (or via MetaMask/hardware wallet)
MSG=$(jq -r .message challenge.json)
SIG=$(cast wallet sign --private-key $SHADOW_OVERLORD_PK "$MSG")
NONCE=$(jq -r .nonce challenge.json)

# 3. Verify, get JWT
JWT=$(curl -s -X POST https://mindx.pythai.net/admin/shadow/verify \
  -H 'content-type: application/json' \
  -d "{\"nonce\":\"$NONCE\",\"signature\":\"$SIG\"}" | jq -r .jwt)

# 4. Provision (requires a SECOND fresh challenge + signature for the op)
# … full flow in docs/operations/SHADOW_OVERLORD_RUNBOOK.md

# 5. After cabinet is provisioned, issue Tessera + Censura on chain
TESSERA=$(jq -r .contracts.Tessera $ADDRS)
CENSURA=$(jq -r .contracts.Censura $ADDRS)
for ROLE in ceo coo_operations cfo_finance cto_technology ciso_security clo_legal cpo_product cro_risk; do
  ADDR=$(curl -s https://mindx.pythai.net/cabinet/PYTHAI | jq -r ".${ROLE}.address // .soldiers.${ROLE}.address")
  cast send $TESSERA "issue(address,string,bytes32)" $ADDR "did:bankon:pythai:$ROLE" $(cast keccak "$ROLE") \
    --private-key $SHADOW_OVERLORD_PK --rpc-url $RPC
  cast send $CENSURA "setScore(address,uint8)" $ADDR 200 \
    --private-key $SHADOW_OVERLORD_PK --rpc-url $RPC
done
```

### Phase 4 — Ethereum (Group B: 4 BANKON contracts)

You need these prerequisites first:

- An ERC-8004 IdentityRegistry already deployed on Eth (one-time)
- Ownership of `bankon.eth` (or whichever parent name)

```bash
export BANKON_DEPLOYER_PK=$SHADOW_OVERLORD_PK
export PARENT_NODE=$(cast namehash bankon.eth)
export IDENTITY_REGISTRY=0x<your-deployed-IdentityRegistry-address>

bash openagents/deploy/deploy_eth_bankon.sh sepolia    # or mainnet
# → 4 contracts in order, pre-flight verifies real ENS NameWrapper exists
# → writes openagents/deployments/{sepolia,ethereum_mainnet}.json
```

### Phase 5 — grant `MINDX_AGENT_MINTER_ROLE`

This unlocks the free `<agent_addr>.bankon.eth` mint path:

```bash
ETH_RPC=https://eth.drpc.org   # or sepolia
REGISTRAR=$(jq -r .contracts.BankonSubnameRegistrar openagents/deployments/sepolia.json)
MINTER=0x<wallet-of-agent-mint-service>

ROLE=$(cast call $REGISTRAR "MINDX_AGENT_MINTER_ROLE()(bytes32)" --rpc-url $ETH_RPC)
cast send $REGISTRAR "grantRole(bytes32,address)" $ROLE $MINTER \
  --private-key $SHADOW_OVERLORD_PK --rpc-url $ETH_RPC
```

### Phase 6 — approve registrar on NameWrapper (one-time, from `bankon.eth` owner)

```bash
cast send $NAME_WRAPPER "setApprovalForAll(address,bool)" $REGISTRAR true \
  --private-key $BANKON_OWNER_PK --rpc-url $ETH_RPC
```

The bankon.eth owner can be the same wallet as shadow-overlord, or a
separate one — depends on your governance setup.

---

## 6. ABI wiring — openagents calling deployed contracts

Once contracts are live, the BDI trader (and any agent) needs to *call*
them. We use a generic registry that maps contract names → addresses (from
`deployments/<network>.json`) → ABIs (from foundry `out/` or vendored
copies).

The implementation lives at `openagents/contracts/registry.py` and exposes:

```python
from openagents.contracts.registry import OpenAgentsContracts

oac = OpenAgentsContracts(network="0g_mainnet")  # reads deployments/0g_mainnet.json

# Read calls
total = oac.AgentRegistry.functions.totalSupply().call()
inft_name = oac.iNFT_7857.functions.name().call()

# Write calls (signer required)
oac = OpenAgentsContracts(network="0g_mainnet", signer_pk="0x...")
tx = oac.DatasetRegistry.functions.registerDataset(
    dataset_id=b"\x00" * 32,
    rootCID="ipfs://Qm...",
).transact()
```

The registry handles:
- Loading addresses from the deployment JSON
- Loading ABIs from `out/<Contract>.sol/<Contract>.json` or vendored under
  `openagents/contracts/abi/<Contract>.json`
- Building web3 Contract instances on demand
- Picking the right RPC for the network

See `openagents/contracts/registry.py` (shipped with this handoff) for
the full implementation.

### What an agent gets

Any BDI agent in the loop can introspect the contract surface:

```python
oac.list()
# → ["AgentRegistry", "THOT", "iNFT_7857", "DatasetRegistry",
#    "Tessera", "Censura", "Conclave", "ConclaveBond",
#    "BankonSubnameRegistrar", "BankonPaymentRouter",
#    "BankonPriceOracle", "BankonReputationGate"]

oac.AgentRegistry.functions    # all callable functions on the contract
```

### Backend route for browsers

```
GET  /api/contracts                       → list all 12 contracts (name, address, network)
GET  /api/contracts/{name}                → full ABI + address + network
POST /api/contracts/{name}/call           → eth_call any view function (key never crosses)
POST /api/contracts/{name}/send           → admin-gated, requires shadow JWT
```

These four routes together let the existing UIs (e.g. `/uniswap`,
`/agentregistry`, `/inft7857`) bind directly to live deployed contracts
without each page needing its own ABI copy.

---

## 7. Production readiness checklist

Print this and check off:

### Pre-deploy

- [ ] Shadow-overlord public address generated; private key stored offline
- [ ] `SHADOW_OVERLORD_ADDRESS` set in `mindx.service` env
- [ ] `SHADOW_JWT_SECRET` set (32-byte random hex)
- [ ] `mindx.service` restarted; `/admin/shadow/challenge` returns 200
- [ ] 0G mainnet wallet funded ≥ 0.20 OG
- [ ] Eth wallet funded ≥ 0.30 ETH (mainnet) or ≥ 0.05 ETH (Sepolia)
- [ ] `bankon.eth` owner identified (same as shadow-overlord, or separate)
- [ ] ERC-8004 IdentityRegistry deployed on the chosen Eth network

### Deploy

- [ ] Phase 1: `bash openagents/deploy/deploy_0g_mainnet.sh` — 8/8 contracts deployed
- [ ] Phase 2: all 8 verify calls return expected values
- [ ] Phase 3: Cabinet provisioned; Tessera + Censura issued for all 8 members
- [ ] Phase 4: `bash openagents/deploy/deploy_eth_bankon.sh sepolia` (or mainnet) — 4/4 deployed
- [ ] Phase 5: `MINDX_AGENT_MINTER_ROLE` granted to mint-service wallet
- [ ] Phase 6: `setApprovalForAll(registrar, true)` from `bankon.eth` owner

### Post-deploy verification

- [ ] `openagents/deployments/0g_mainnet.json` exists, all 8 addresses populated
- [ ] `openagents/deployments/sepolia.json` (or `ethereum_mainnet.json`) exists, all 4 populated
- [ ] `https://mindx.pythai.net/openagents/deployments/0g_mainnet.json` returns 200
- [ ] `/agentregistry`, `/inft7857`, `/conclave`, `/zerog` UIs show live addresses
- [ ] `/bankonminter` Auto-load button populates registrar address
- [ ] BDI trader cycle 1: `python3 openagents/uniswap/demo_trader.py --backend trade-api --duration 1 --dry-run` produces a real quote
- [ ] Sample mint: `python3 -m openagents.ens.agent_mint_service --agent 0xTest…` succeeds
- [ ] Boardroom session: `/cabinet/PYTHAI` returns the 8 addresses; `Conclave.registerConclave` succeeds

### Operational

- [ ] Backup the `mindx.service` env file (encrypted)
- [ ] Document the deploy tx hashes in a private log
- [ ] Set up monitoring on `/health` + `/insight/storage/status`
- [ ] Schedule a quarterly rotation of `SHADOW_JWT_SECRET`
- [ ] First Cabinet boardroom session run + recorded

---

## 8. Day-1 operational runbook

| Task | How |
|---|---|
| Authenticate as shadow-overlord | `POST /admin/shadow/challenge` → sign offline → `POST /admin/shadow/verify` |
| Provision a new Cabinet (e.g. AGENTICPLACE) | `POST /admin/cabinet/AGENTICPLACE/provision` with shadow JWT + fresh sig |
| Mint a free agent ENS subname | `python3 -m openagents.ens.agent_mint_service --agent 0x…` (uses MINDX_AGENT_MINTER_ROLE wallet) |
| Run a BDI trade cycle | `python3 openagents/uniswap/demo_trader.py --backend trade-api --duration 30 --provider zerog` |
| Run a boardroom session | `POST /boardroom/convene` (existing endpoint) |
| Pause a contract on incident | `cast send $ADDR "pause()" --private-key $SHADOW_OVERLORD_PK --rpc-url $RPC` |
| Rotate JWT secret | `openssl rand -hex 32` → update env → restart `mindx.service` |
| Recover from lost shadow key | Use `SHADOW_OVERLORD_ADDRESS_BACKUP` if configured; otherwise vault contents become orphaned (encrypted ciphertext remains, but admin operations are locked) |

---

## 9. What's *not* in this handoff

- **Demo video** — operator records a 1-min walkthrough for ETHGlobal submission
- **8 ETHGlobal form submissions** — operator fills these (URLs already in TODO list)
- **Algorand bridge deployment** — separate track; ConclaveBond accepts post-deploy patch via `setAlgoBridge`
- **OG token acquisition** — operator buys/bridges OG to fund deployer
- **`bankon.eth` ownership transfer** — if the owner is changing hands, do this on a separate cadence

---

## 10. Quick reference

### Contract count

| Network | Contracts | Source path |
|---|---|---|
| 0G mainnet (16661) | 8 | `daio/contracts/{agentregistry,THOT/v1,inft,arc}/` + `openagents/conclave/contracts/src/` |
| Sepolia or Eth mainnet | 4 | `daio/contracts/ens/v1/` |
| **Total** | **12** | + 1 IdentityRegistry pre-req on Eth |

### Key files

| Path | Purpose |
|---|---|
| `openagents/HANDOFF.md` | This document |
| `openagents/deploy/deploy_0g_mainnet.sh` | Group A deploy |
| `openagents/deploy/deploy_eth_bankon.sh` | Group B deploy |
| `openagents/deployments/0g_mainnet.json` | Generated address surface (0G) |
| `openagents/deployments/{sepolia,ethereum_mainnet}.json` | Generated address surface (Eth) |
| `openagents/contracts/registry.py` | Generic ABI loader for all 12 contracts |
| `openagents/docs/0G_MAINNET_DEPLOY.md` | Full deployment workflow |
| `openagents/docs/DEPLOYMENT.md` | Per-track deployment matrix |
| `openagents/docs/uniswap/UNISWAP_API.md` | Trading API reference |
| `docs/operations/SHADOW_OVERLORD_RUNBOOK.md` | Admin auth runbook |
| `mindx_backend_service/bankon_vault/cabinet.py` | Cabinet provisioner |

### Contact surface

- Live UI: https://mindx.pythai.net/openagents
- API docs: https://mindx.pythai.net/docs
- Health: https://mindx.pythai.net/health
- Repo (private until launch): `github.com/AgenticPlace/openagents`

---

When you're ready, send me the public address of the shadow-overlord
wallet plus confirmation that it's funded on each network you want to
deploy to. We then run Phase 1-6 together over a single session.
