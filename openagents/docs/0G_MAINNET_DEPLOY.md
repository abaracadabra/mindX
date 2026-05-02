---
name: 0G Mainnet Deployment — Full Workflow
description: Complete contract inventory (12 contracts across 0G mainnet + Eth) with deploy order, dependency graph, post-deploy wiring, verification, and operational runbook.
---

# 0G Mainnet Deployment — Full Workflow

> **Network split.** openagents deploys across two chains:
>
> - **0G mainnet** (chainId `16661`, RPC `https://evmrpc.0g.ai`) — 8 contracts. Native compute + storage anchor + intelligent NFT + AXL conclave mesh.
> - **Ethereum mainnet** (or Sepolia for staging) — 4 BANKON v1 contracts. ENS NameWrapper + PublicResolver only exist on Ethereum, so the BANKON registrar must live there.
>
> No mock-ENS shim is deployed on 0G. BANKON deploys to Eth.

---

## Complete contract inventory

### Group A — 0G mainnet (8 contracts)

| # | Contract | Path | Constructor | Tests | Coverage | Gas |
|---|---|---|---|---:|---:|---:|
| 1 | `AgentRegistry` | `daio/contracts/agentregistry/AgentRegistry.sol` | `(admin)` | 20 | 89.86% | ~2.1M |
| 2 | `THOT v1` | `daio/contracts/THOT/v1/THOT.sol` | `(admin, allowedAuthor)` | 14 | 93.75% | ~1.5M |
| 3 | `iNFT_7857` | `daio/contracts/inft/iNFT_7857.sol` | `(name, symbol, admin, royaltyTo, royaltyBps, oracle, treasury, cloneFeeWei)` | 57 | 95.65% | ~3.8M |
| 4 | `DatasetRegistry` | `daio/contracts/arc/DatasetRegistry.sol` | `()` | — | — | ~0.7M |
| 5 | `Tessera` | `openagents/conclave/contracts/src/Tessera.sol` | `(admin)` | covered via Conclave | — | ~0.5M |
| 6 | `Censura` | `openagents/conclave/contracts/src/Censura.sol` | `(admin)` | covered via Conclave | — | ~0.4M |
| 7 | `Conclave` | `openagents/conclave/contracts/src/Conclave.sol` | `(tessera, censura, predictedBond)` | 16 | 100% | ~2.0M |
| 8 | `ConclaveBond` | `openagents/conclave/contracts/src/ConclaveBond.sol` | `(conclave, algoBridge)` | 19 | 100% | ~0.9M |

**Group A total ≈ 11.9M gas. At 4 gwei (probed live 2026-05-02) ≈ 0.048 OG.** Keep ≥ 0.1 OG for headroom.

### Group B — Ethereum (mainnet or Sepolia) — 4 contracts

| # | Contract | Path | Constructor | Tests | Coverage | Gas |
|---|---|---|---|---:|---:|---:|
| 9 | `BankonPriceOracle` | `daio/contracts/ens/v1/BankonPriceOracle.sol` | `(admin)` | partial | 24% ⚠ | ~1.0M |
| 10 | `BankonReputationGate` | `daio/contracts/ens/v1/BankonReputationGate.sol` | `(admin)` | partial | 69% | ~0.6M |
| 11 | `BankonPaymentRouter` | `daio/contracts/ens/v1/BankonPaymentRouter.sol` | `(admin)` | partial | 12% ⚠ | ~1.5M |
| 12 | `BankonSubnameRegistrar` | `daio/contracts/ens/v1/BankonSubnameRegistrar.sol` | `(nameWrapper, defaultResolver, parentNode, paymentRouter, priceOracle, reputationGate, identityRegistry, admin)` | 34 | 95.39% | ~3.5M |

**Group B total ≈ 6.6M gas.** Sepolia at low gwei < $0.50; Ethereum mainnet at 20 gwei ≈ 0.13 ETH.

### External dependencies (Group B only)

| Address | Purpose | Sepolia | Mainnet |
|---|---|---|---|
| ENS NameWrapper | Wraps ENS names so subname records are token-bound | `0x0635513f179D50A207757E05759CbD106d7dFcE8` | `0xD4416b13d2b3a9aBae7AcD5D6C2BbDBE25686401` |
| ENS PublicResolver | Default resolver for written records | `0x8FADE66B79cC9f707aB26799354482EB93a5B7dD` | `0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63` |
| `bankon.eth` parent node | namehash; deploy-time arg | (your subdomain) | (your subdomain) |
| Identity registry (ERC-8004) | Agent identity issuer | deploy `IdentityRegistryUpgradeable.sol` | deploy `IdentityRegistryUpgradeable.sol` |

---

## Deploy order — dependency graph

```
Phase 1 — Independent contracts (any order on 0G):
  ┌───────────────────┐
  │ AgentRegistry     │ ← admin
  ├───────────────────┤
  │ THOT v1           │ ← admin, allowedAuthor
  ├───────────────────┤
  │ iNFT_7857         │ ← admin, royaltyTo, royaltyBps, oracle, treasury, cloneFeeWei
  ├───────────────────┤
  │ DatasetRegistry   │ ← (none)
  ├───────────────────┤
  │ Tessera           │ ← admin
  ├───────────────────┤
  │ Censura           │ ← admin
  └───────────────────┘
            │
            ▼
Phase 2 — Conclave stack (atomic via runFresh script):
  ┌───────────────────┐
  │ Conclave          │ ← Tessera, Censura, predicted ConclaveBond addr
  ├───────────────────┤
  │ ConclaveBond      │ ← Conclave, algoBridge
  └───────────────────┘
            │
            ▼  (bridge to Ethereum)
            │
Phase 3 — Eth network: BANKON v1 (after Group A):
  ┌───────────────────────┐
  │ BankonPriceOracle     │ ← admin
  ├───────────────────────┤
  │ BankonReputationGate  │ ← admin
  ├───────────────────────┤
  │ BankonPaymentRouter   │ ← admin
  └───────────────────────┘
            │
            ▼
  ┌───────────────────────┐
  │ BankonSubnameRegistrar│ ← all 3 above + ENS wrapper + resolver + parent node + identity registry
  └───────────────────────┘
            │
            ▼
Phase 4 — Post-deploy wiring (on each chain):
  - Cabinet onboarding (0G): tessera.issue + censura.setScore for 8 members
  - Bonds posted (0G): conclaveBond.postBond × 8
  - Conclave registered (0G): conclave.registerConclave with the 8-member array
  - Mint role (Eth): BankonSubnameRegistrar.grantRole(MINDX_AGENT_MINTER_ROLE, mintService)
  - Optional: AgentRegistry → DatasetRegistry permissions, oracle key rotation
```

---

## Workflow — execute in this order

### Step 0 — pre-flight (any chain)

```bash
# Funded deployer wallet — keep separate from any wallet with valuables
export DEPLOYER_PK=0x...
export DEPLOYER=$(cast wallet address --private-key $DEPLOYER_PK)
echo "Deployer: $DEPLOYER"
```

Verify your toolchain:

```bash
forge --version    # foundry stable, 0.2.0+
cast --version
jq --version       # used to parse broadcast JSON
```

### Step 1 — deploy Group A to 0G mainnet

One-shot script (recommended — pre-flight checks chain id, balance, gas; prompts before sending):

```bash
export ZEROG_PRIVATE_KEY=$DEPLOYER_PK
export ROYALTY_RECEIVER=$DEPLOYER       # or treasury
export TREASURY_ADDR=$DEPLOYER          # iNFT clone-fee recipient
export ORACLE_ADDR=$DEPLOYER            # iNFT EIP-712 sealed-key proof signer
export ALGO_BRIDGE_ADDR=0x0000000000000000000000000000000000000000  # set later
export CLONE_FEE_WEI=10000000000000000  # 0.01 OG
export ROYALTY_BPS=250                  # 2.5%

bash openagents/deploy/deploy_0g_mainnet.sh
```

The script deploys all 8 Group A contracts in dependency order, writes addresses to `openagents/deployments/0g_mainnet.json`, and prints explorer links.

Manual sequence (if you prefer cast directly — see `openagents/docs/DEPLOYMENT.md`).

### Step 2 — verify Group A on 0G mainnet

```bash
export ZEROG_RPC=https://evmrpc.0g.ai
ADDRS=openagents/deployments/0g_mainnet.json

# AgentRegistry: ERC-721 surface
cast call $(jq -r .contracts.AgentRegistry $ADDRS) "supportsInterface(bytes4)(bool)" 0x80ac58cd --rpc-url $ZEROG_RPC
# → true

# THOT: owner is the admin we passed
cast call $(jq -r .contracts.THOT $ADDRS) "owner()(address)" --rpc-url $ZEROG_RPC

# iNFT: name + clone fee
cast call $(jq -r .contracts.iNFT_7857 $ADDRS) "name()(string)" --rpc-url $ZEROG_RPC
cast call $(jq -r .contracts.iNFT_7857 $ADDRS) "cloneFeeWei()(uint256)" --rpc-url $ZEROG_RPC

# DatasetRegistry: owner + total
cast call $(jq -r .contracts.DatasetRegistry $ADDRS) "owner()(address)" --rpc-url $ZEROG_RPC
cast call $(jq -r .contracts.DatasetRegistry $ADDRS) "totalDatasets()(uint256)" --rpc-url $ZEROG_RPC

# Tessera: admin
cast call $(jq -r .contracts.Tessera $ADDRS) "admin()(address)" --rpc-url $ZEROG_RPC

# Conclave: bond is wired
cast call $(jq -r .contracts.Conclave $ADDRS) "bondContract()(address)" --rpc-url $ZEROG_RPC
# → ConclaveBond address from JSON

# ConclaveBond: conclave is wired (round-trip check)
cast call $(jq -r .contracts.ConclaveBond $ADDRS) "conclave()(address)" --rpc-url $ZEROG_RPC
# → Conclave address from JSON
```

### Step 3 — wire Cabinet on 0G mainnet

Run AFTER provisioning the 8-member Cabinet (CEO + 7 Counsellors) via BANKON Vault shadow-overlord. See `docs/operations/SHADOW_OVERLORD_RUNBOOK.md`.

```bash
TESSERA=$(jq -r .contracts.Tessera $ADDRS)
CENSURA=$(jq -r .contracts.Censura $ADDRS)
CONCLAVE=$(jq -r .contracts.Conclave $ADDRS)
BOND=$(jq -r .contracts.ConclaveBond $ADDRS)

# Read 8 cabinet addresses from the cabinet JSON
CABINET=https://mindx.pythai.net/cabinet/PYTHAI
curl -s $CABINET | jq

# For each member: issue Tessera credential + Censura score
for ROLE in ceo coo_operations cfo_finance cto_technology ciso_security clo_legal cpo_product cro_risk; do
  ADDR=$(curl -s $CABINET | jq -r ".${ROLE}.address // .soldiers.${ROLE}.address")
  DID="did:bankon:pythai:$ROLE"
  PUBKEY=$(cast keccak "$ROLE")  # placeholder — production uses real ed25519 transport key

  cast send $TESSERA "issue(address,string,bytes32)" $ADDR "$DID" $PUBKEY \
    --private-key $DEPLOYER_PK --rpc-url $ZEROG_RPC
  cast send $CENSURA "setScore(address,uint8)" $ADDR 200 \
    --private-key $DEPLOYER_PK --rpc-url $ZEROG_RPC
done

# Each member posts a bond (1 OG each) — done from each member's own wallet,
# OR scripted via vault-as-signing-oracle (see /vault/sign).

# Convener (CEO) registers the conclave once with the 8-member array
MEMBERS_JSON=$(curl -s $CABINET | jq -r '[.ceo.address, .soldiers.coo_operations.address, .soldiers.cfo_finance.address, .soldiers.cto_technology.address, .soldiers.ciso_security.address, .soldiers.clo_legal.address, .soldiers.cpo_product.address, .soldiers.cro_risk.address]')
CONCLAVE_ID=0xPYTHAI...  # 32-byte conclave id
cast send $CONCLAVE "registerConclave(bytes32,address[8])" $CONCLAVE_ID "$MEMBERS_JSON" \
  --private-key $CEO_PK --rpc-url $ZEROG_RPC
```

### Step 4 — deploy Group B to Sepolia (staging) or Ethereum mainnet

```bash
bash openagents/deploy/deploy_eth_bankon.sh sepolia    # or mainnet
```

This deploys the 4 BANKON contracts in order, wires them, and writes addresses to `openagents/deployments/{sepolia,ethereum_mainnet}.json`. See `openagents/docs/DEPLOYMENT.md` for ENS dependency addresses.

### Step 5 — grant `MINDX_AGENT_MINTER_ROLE` on the registrar

```bash
ETH_RPC=https://sepolia.infura.io/v3/$KEY    # or mainnet
REGISTRAR=$(jq -r .contracts.BankonSubnameRegistrar openagents/deployments/sepolia.json)
MINTER=0x...    # the wallet that runs openagents/ens/agent_mint_service.py

ROLE=$(cast call $REGISTRAR "MINDX_AGENT_MINTER_ROLE()(bytes32)" --rpc-url $ETH_RPC)
cast send $REGISTRAR "grantRole(bytes32,address)" $ROLE $MINTER \
  --private-key $ADMIN_PK --rpc-url $ETH_RPC
```

After this, the agent mint service can issue `<agent_addr>.bankon.eth` for free to any mindX agent. The mint role-holder pays gas.

### Step 6 — point UIs at deployed addresses

The 4 component UIs (`agentregistry.html`, `inft7857.html`, `conclave.html`, `zerog.html`) read addresses from `/openagents/deployments/0g_mainnet.json`. The BANKON UI reads from `/openagents/deployments/sepolia.json` (or `ethereum_mainnet.json`).

Confirm by loading each console with MetaMask and watching the address banner.

---

## Address surface — what gets written where

After the full sequence (Steps 1+4), you have **two deployment JSON files**:

```
openagents/deployments/
├── 0g_mainnet.json           # 8 contracts on 0G
└── sepolia.json              # 4 BANKON contracts on Sepolia
                              # OR ethereum_mainnet.json for prod
```

Schema (both files):

```json
{
  "network": "0g-mainnet" | "sepolia" | "ethereum-mainnet",
  "chain_id": 16661 | 11155111 | 1,
  "rpc": "https://...",
  "explorer": "https://...",
  "deployed_at": "2026-05-02T...",
  "deployer": "0x...",
  "contracts": {
    "AgentRegistry": "0x...",
    ...
  },
  "config": { ... },
  "note": "..."
}
```

UIs and the agent mint service read these files to populate live addresses.

---

## Operational invariants

After full deploy, the system upholds:

| Invariant | Where enforced |
|---|---|
| Cabinet keys never leave BANKON Vault | `mindx_backend_service/bankon_vault/cabinet.py` + AES-256-GCM |
| Shadow-overlord auth required for sign | `bankon_vault/shadow_overlord.py` — JWT + per-op fresh ECDSA sig |
| iNFT transfer requires sealed-key proof | `iNFT_7857.sol` `_safeTransfer` reentrancy-guarded |
| THOT memory anchor is append-only | `THOT.sol` no delete path |
| Conclave can only act with 8-member quorum | `Conclave.sol` `registerConclave` requires 8 |
| Slash-on-leak mid-conclave | `ConclaveBond.sol` `slashForLeak(member,conclave,leakHash,evidence)` |
| Free agent ENS subnames are role-gated | `BankonSubnameRegistrar.sol` `MINDX_AGENT_MINTER_ROLE` |
| BANKON paid mints require fresh EIP-712 voucher | `BankonSubnameRegistrar.registerWithVoucher` |
| DatasetRegistry CIDs are immutable per dataset id | `DatasetRegistry.versionDataset` increments version |

---

## Pre-flight checklist (concrete — print and check)

Before pressing DEPLOY:

**0G mainnet (Group A):**
- [ ] Deployer balance ≥ 0.1 OG
- [ ] Gas price < 10 gwei (probe with `cast gas-price --rpc-url https://evmrpc.0g.ai`)
- [ ] Treasury / royalty / oracle addresses set deliberately (not the default deployer)
- [ ] Algorand bridge address known, OR deliberate `0x0` to be patched later
- [ ] `forge build` clean from `daio/contracts` and `openagents/conclave/contracts`
- [ ] Slither passes on iNFT, AgentRegistry, THOT, Conclave, ConclaveBond (`make slither` in CI)
- [ ] Backup the broadcast directory — it is the source of truth for address extraction if `0g_mainnet.json` corrupts

**Ethereum (Group B):**
- [ ] Deployer balance ≥ 0.05 ETH (Sepolia: get from faucet; mainnet: real funds)
- [ ] `parentNode` namehash for `bankon.eth` (or the chosen parent) computed correctly
- [ ] Wallet that owns `bankon.eth` is ready to delegate to the deployed registrar (via `setApprovalForAll(registrar, true)` on NameWrapper)
- [ ] Identity registry (ERC-8004) is deployed first (separate from Group B sequence)

---

## Cost estimate (real money)

| Network | Group | Gas | Gas price | Cost |
|---|---|---:|---:|---:|
| 0G mainnet | A (8 contracts) | 11.9M | 4 gwei | **0.0476 OG** (~ negligible USD) |
| Sepolia | B (4 contracts) | 6.6M | 1 gwei | **0.0066 ETH** (faucet) |
| Eth mainnet | B (4 contracts) | 6.6M | 20 gwei | **0.132 ETH** (~$400 at $3k ETH) |

For staging, deploy A on 0G + B on Sepolia. For production launch, redo B on Eth mainnet.

---

## Recovery / rollback

There is no atomic rollback across 8 separate forge create calls. If something fails mid-deploy:

1. **Capture the partial state.** `openagents/deployments/0g_mainnet.json` may be missing later contracts; the broadcast directories `daio/contracts/broadcast/.../16661/` and `openagents/conclave/contracts/broadcast/.../16661/` retain the truth.
2. **Don't redeploy what already deployed.** Each contract gets a unique address; redeploying creates orphans that aren't wired into the rest of the stack.
3. **Continue from the last successful step.** The script is structured so each step depends only on prior addresses written to `0g_mainnet.json` — patch the JSON manually with the partial addresses, then run only the missing forge create commands.
4. **For Conclave + ConclaveBond:** these MUST deploy together via `runFresh`. If Conclave succeeds but ConclaveBond fails, redeploy both — the predicted-bond pattern means the Conclave address depends on the eventual ConclaveBond address.

---

## Key file pointers

- `openagents/deploy/deploy_0g_mainnet.sh` — Group A deploy (8 contracts)
- `openagents/deploy/deploy_eth_bankon.sh` — Group B deploy (4 contracts) **TODO: write next**
- `openagents/docs/DEPLOYMENT.md` — manual sequence + per-track matrix
- `openagents/deployments/0g_mainnet.json` — generated address surface (0G)
- `openagents/deployments/sepolia.json` — generated address surface (BANKON)
- `openagents/ens/agent_mint_service.py` — free `<addr>.bankon.eth` mint client
- `mindx_backend_service/bankon_vault/cabinet.py` — Cabinet provisioner (8 wallets per company)
- `docs/operations/SHADOW_OVERLORD_RUNBOOK.md` — admin auth runbook

---

## What changes if you want a faster, smaller deploy

If you're tight on gas or only need a demo:

- **0G mainnet smoke test:** deploy only AgentRegistry + iNFT_7857 + Conclave stack (skip THOT, DatasetRegistry). 5 contracts, ~9.7M gas, ~0.039 OG.
- **0G storage-only:** deploy only DatasetRegistry. 1 contract, ~0.7M gas, ~0.003 OG.
- **Local Anvil rehearsal:** the same scripts work against `http://127.0.0.1:8545` — point `ZEROG_RPC_URL` and `ZEROG_CHAIN_ID=31337`. Free; takes ~3 minutes end to end.

For full hackathon submission evidence, deploy the complete 12-contract surface so all 6 prize tracks have a live anchor.
