---
name: Deployment Plan — Anvil → 0G Galileo
description: Honest contract inventory + per-network deployment sequence + dependency map. Includes integration gaps that need closing before livenet.
---

# Deployment Plan — Anvil → 0G Galileo Livenet

> **Honest status first.** Three integration gaps were found during this audit and should be acknowledged before deploy:
>
> 1. **AXL ↔ Boardroom is not wired in code.** `mindx_boardroom_adapter.py` documents the integration; `daio/governance/boardroom.py` does not yet import it.
> 2. **BANKON v1 is a 4-contract suite; only the Registrar is well-tested.** `BankonPaymentRouter` (12% coverage), `BankonPriceOracle` (24%), `BankonReputationGate` (69%) are drafted but undertested.
> 3. **Conclave needs Tessera+Censura.** Real BONAFIDE contracts don't exist; this session shipped minimal placeholder `Tessera.sol`+`Censura.sol` (admin-managed) so livenet deploy is now possible.

---

## Per-track deployment matrix

| Track / Module | Contracts | Anvil | Sepolia | 0G Galileo | Mainnet |
|---|---|:-:|:-:|:-:|:-:|
| 0G iNFT-7857 | `iNFT_7857.sol` | ✓ | ✓ | ✓ | ✓ |
| ERC-8004 (composable) | `AgentRegistry.sol` | ✓ | ✓ | ✓ | ✓ |
| 0G memory anchor | `THOT/v1/THOT.sol` | ✓ | ✓ | ✓ | ✓ |
| ENS BANKON v1 | `BankonSubnameRegistrar.sol` + 3 siblings | ⚠ needs ENS mocks | ✓ | ✗ no ENS | ✓ |
| AXL Conclave | `Tessera.sol`, `Censura.sol`, `Conclave.sol`, `ConclaveBond.sol` | ✓ | ✓ | ✓ | ✓ |

**0G Galileo can host 4 modules natively** (iNFT-7857, AgentRegistry, THOT, Conclave-stack). **BANKON v1 cannot deploy to 0G** because its constructor requires the ENS NameWrapper + PublicResolver addresses, which don't exist on 0G. BANKON deploys to Ethereum mainnet, Sepolia, or Holesky.

---

## Contract inventory (the actual list to deploy)

### Group A — 0G Galileo native (4 contracts in deploy order)

| # | Contract | Path | Constructor args | Tests | Coverage |
|---|---|---|---|---|---|
| 1 | `AgentRegistry` | `daio/contracts/agentregistry/AgentRegistry.sol` | `(admin)` | 20 | 89.86% |
| 2 | `THOT` | `daio/contracts/THOT/v1/THOT.sol` | `(admin, allowedAuthor)` | 14 | 93.75% |
| 3 | `iNFT_7857` | `daio/contracts/inft/iNFT_7857.sol` | `(name, symbol, admin, royaltyTo, royaltyBps, oracle, treasury, cloneFeeWei)` | 57 | 95.65% |
| 4a | `Tessera` | `openagents/conclave/contracts/src/Tessera.sol` | `(admin)` | (covered via Conclave tests) | — |
| 4b | `Censura` | `openagents/conclave/contracts/src/Censura.sol` | `(admin)` | (covered via Conclave tests) | — |
| 4c | `Conclave` | `openagents/conclave/contracts/src/Conclave.sol` | `(tessera, censura, predictedBond)` | 16 | 100% |
| 4d | `ConclaveBond` | `openagents/conclave/contracts/src/ConclaveBond.sol` | `(conclave, algoBridge)` | 19 | 100% |

The Conclave stack is a 4-contract atomic deployment via `script/Deploy.s.sol::runFresh(algoBridge)`. Tessera+Censura admin = the deployer, then deployer issues credentials to the cabinet members.

### Group B — Sepolia / Mainnet (BANKON v1 ENS)

| # | Contract | Path | Constructor args | Tests | Coverage |
|---|---|---|---|---|---|
| 5 | `BankonPriceOracle` | `daio/contracts/ens/v1/BankonPriceOracle.sol` | `(admin)` | partial | 24% ⚠ |
| 6 | `BankonReputationGate` | `daio/contracts/ens/v1/BankonReputationGate.sol` | `(admin, reputationContract)` | partial | 69% |
| 7 | `BankonPaymentRouter` | `daio/contracts/ens/v1/BankonPaymentRouter.sol` | `(admin, ...)` | partial | 12% ⚠ |
| 8 | `BankonSubnameRegistrar` | `daio/contracts/ens/v1/BankonSubnameRegistrar.sol` | `(nameWrapper, defaultResolver, parentNode, priceOracle, reputationGate, paymentRouter, identityRegistry, controllerSigner)` | 29 | 94.85% |

Pre-deployed addresses needed on Sepolia:
- ENS NameWrapper: `0x0635513f179D50A207757E05759CbD106d7dFcE8`
- PublicResolver: `0x8FADE66B79cC9f707aB26799354482EB93a5B7dD`
- Parent node: `bankon.eth` namehash (deploy time)
- Identity registry: from `daio/contracts/agenticplace/evm/IdentityRegistryUpgradeable.sol` (separate deploy)

⚠ **Caveat:** the 3 sibling BANKON contracts have low test coverage. The Registrar itself is at 94.85%, but PaymentRouter/PriceOracle haven't been adversarially tested. Recommend additional unit tests before mainnet.

---

## Anvil sequence (local testing — full flow)

```bash
# 1. Start Anvil in one terminal
anvil --port 8545 --chain-id 31337
# Default funded account #0:
#   addr: 0xf39Fd6e51aad88F6F4ce6aB8827279cfFFb92266
#   pk:   0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# 2. Set env
export ANVIL_RPC=http://127.0.0.1:8545
export DEPLOYER=0xf39Fd6e51aad88F6F4ce6aB8827279cfFFb92266
export DEPLOYER_PK=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# 3. Deploy AgentRegistry
cd /home/hacker/mindX/daio/contracts
forge create --rpc-url $ANVIL_RPC --private-key $DEPLOYER_PK \
    agentregistry/AgentRegistry.sol:AgentRegistry \
    --constructor-args $DEPLOYER

# 4. Deploy THOT (note: allowedAuthor can be the deployer initially)
forge create --rpc-url $ANVIL_RPC --private-key $DEPLOYER_PK \
    THOT/v1/THOT.sol:THOT \
    --constructor-args $DEPLOYER $DEPLOYER

# 5. Deploy iNFT_7857
#    Args: name, symbol, admin, royaltyTo, royaltyBps (500 = 5%),
#          oracle, treasury, cloneFeeWei (0.01 ETH = 10000000000000000)
forge create --rpc-url $ANVIL_RPC --private-key $DEPLOYER_PK \
    inft/iNFT_7857.sol:iNFT_7857 \
    --constructor-args \
      "mindX iNFT-7857" "MINFT" \
      $DEPLOYER $DEPLOYER 500 \
      $DEPLOYER $DEPLOYER \
      10000000000000000

# 6. Deploy the Conclave stack atomically
cd /home/hacker/mindX/openagents/conclave/contracts
forge script script/Deploy.s.sol:Deploy \
    --rpc-url $ANVIL_RPC --private-key $DEPLOYER_PK \
    --sig 'runFresh(address)' 0x0000000000000000000000000000000000000000 \
    --broadcast

# 7. Issue cabinet credentials (Tessera + Censura)
# Use cast to call Tessera.issue(holder, did, pubkey) for each Cabinet member
# and Censura.setScore(holder, score) — see runbook section below
```

## 0G Galileo livenet sequence

```bash
# Galileo testnet RPC + chain
export GALILEO_RPC=https://evmrpc-testnet.0g.ai
export GALILEO_CHAIN_ID=16601                # confirm with /openapi or 0G docs
export DEPLOYER_PK=$YOUR_FUNDED_KEY
export DEPLOYER=0x...

# Verify connectivity
cast chain-id --rpc-url $GALILEO_RPC
cast balance $DEPLOYER --rpc-url $GALILEO_RPC

# Faucet: Galileo testnet faucet at https://faucet.0g.ai (Discord-gated)
# You need ~0.5 ETH-equivalent for the full deploy

# Deploy in the same order as Anvil. Replace ANVIL_RPC with GALILEO_RPC.
cd /home/hacker/mindX/daio/contracts
forge create --rpc-url $GALILEO_RPC --private-key $DEPLOYER_PK \
    agentregistry/AgentRegistry.sol:AgentRegistry \
    --constructor-args $DEPLOYER

# ...same for THOT, iNFT_7857...

cd /home/hacker/mindX/openagents/conclave/contracts
forge script script/Deploy.s.sol:Deploy \
    --rpc-url $GALILEO_RPC --private-key $DEPLOYER_PK \
    --sig 'runFresh(address)' 0x0000000000000000000000000000000000000000 \
    --broadcast --verify  # if Galileo has a verifier endpoint
```

Save the deployed addresses to `openagents/deployments/galileo.json`. The existing `openagents/deploy/deploy_galileo.sh` script can be the wrapper.

---

## Cabinet member onboarding (post-deploy)

After Conclave stack deploys, each of the 8 cabinet members needs:

1. A Tessera credential: `cast send $TESSERA "issue(address,string,bytes32)" $MEMBER "did:bankon:$DID" $PUBKEY`
2. An initial Censura score: `cast send $CENSURA "setScore(address,uint8)" $MEMBER 200`
3. A bond posted: `cast send $BOND "postBond(bytes32,uint256)" $CONCLAVE_ID 1000000000000000000 --value 1ether --from $MEMBER_PK`

Then convener (CEO) calls `Conclave.registerConclave(...)` once with the 8-member array.

---

## Integration gaps to close (NOT for hackathon submission, but real)

Three things to wire properly post-hackathon:

### Gap 1: AXL → Boardroom adapter actually wired

`daio/governance/boardroom.py` should `import` and route through `mindx_boardroom_adapter.MindxBoardroomAdapter` for high-stakes proposals. Currently the adapter exists; the import is documented but absent.

Fix sketch (~10 LOC in `daio/governance/boardroom.py`):
```python
try:
    from openagents.conclave.integrations.mindx_boardroom_adapter import (
        MindxBoardroomAdapter,
    )
    _HAS_CONCLAVE = True
except ImportError:
    _HAS_CONCLAVE = False

# In Boardroom.convene():
if _HAS_CONCLAVE and is_high_stakes(directive):
    # Route through Conclave AXL mesh
    return await self._conclave_adapter.route(directive, soldiers)
```

### Gap 2: BANKON sibling contracts

`BankonPaymentRouter`, `BankonPriceOracle`, `BankonReputationGate` need direct unit tests at the same depth as `BankonSubnameRegistrar` (currently 12-69%). They build clean and have basic test scaffolds in the test/ tree but coverage is genuinely thin.

### Gap 3: Tessera/Censura production

The minimal contracts shipped this session are admin-managed placeholders. Production BONAFIDE Tessera/Censura would have:
- W3C DID resolution
- Decay/recovery rules on Censura
- Cross-chain attestation bridges
- Permissionless reporting with weight

The placeholders are sufficient for hackathon demo. They are NOT production-grade.

---

## Verification commands

After each deploy, verify:

```bash
# AgentRegistry
cast call $REGISTRY "supportsInterface(bytes4)(bool)" 0x80ac58cd --rpc-url $RPC
# → true (ERC-721)

# THOT
cast call $THOT "owner()(address)" --rpc-url $RPC
# → $DEPLOYER

# iNFT_7857
cast call $INFT "name()(string)" --rpc-url $RPC
# → "mindX iNFT-7857"

# Tessera
cast call $TESSERA "admin()(address)" --rpc-url $RPC
# → $DEPLOYER

# Conclave
cast call $CONCLAVE "memberCount(bytes32)(uint8)" 0xCAFE --rpc-url $RPC
# → 0 (no conclaves registered yet)

# ConclaveBond
cast call $BOND "conclave()(address)" --rpc-url $RPC
# → $CONCLAVE
```

---

## Gas estimates

Approximate, on Anvil with default settings:

| Contract | Deploy gas | Notes |
|---|---|---|
| AgentRegistry | ~2.1M | ERC-721 + AccessControl |
| THOT | ~1.5M | Simple struct + access control |
| iNFT_7857 | ~3.8M | ERC-721 + roles + EIP-712 + Pausable + ReentrancyGuard |
| Tessera | ~0.5M | Minimal placeholder |
| Censura | ~0.4M | Minimal placeholder |
| Conclave | ~2.0M | Member arrays + slash logic |
| ConclaveBond | ~0.9M | Bond accounting + Algorand bridge |
| **Total Group A** | **~11.2M** | All on 0G Galileo |
| BankonPriceOracle | ~1.0M | Oracle only |
| BankonReputationGate | ~0.6M | Gate logic |
| BankonPaymentRouter | ~1.5M | x402 routing |
| BankonSubnameRegistrar | ~3.5M | ENS + EIP-712 + price/gate |
| **Total Group B** | **~6.6M** | Sepolia |

Galileo gas price is currently sub-cent; total deploy < $0.05 USD.
Sepolia 4-deploy ENS suite < $0.50 USD at low gwei.

---

## After deploy — link the addresses into the UI

The 9 component consoles read deployment addresses from a JSON file. Update:

```bash
# After 0G Galileo deploys
cat > openagents/deployments/galileo.json <<EOF
{
  "chain_id": 16601,
  "rpc": "https://evmrpc-testnet.0g.ai",
  "deployed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "contracts": {
    "AgentRegistry": "0x...",
    "THOT": "0x...",
    "iNFT_7857": "0x...",
    "Tessera": "0x...",
    "Censura": "0x...",
    "Conclave": "0x...",
    "ConclaveBond": "0x..."
  }
}
EOF
```

The `/agentregistry`, `/inft7857`, `/conclave`, `/zerog` UIs all read this file via `fetch('/openagents/deployments/galileo.json')` to populate live contract addresses.

---

## Reproduce-from-scratch for a judge

If a judge wants to run the full deploy themselves:

```bash
git clone https://github.com/AgenticPlace/openagents
cd openagents
anvil &
ANVIL=http://127.0.0.1:8545
DEPLOYER_PK=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

cd daio/contracts
forge install foundry-rs/forge-std --no-git
forge install OpenZeppelin/openzeppelin-contracts --no-git

forge create --rpc-url $ANVIL --private-key $DEPLOYER_PK \
  agentregistry/AgentRegistry.sol:AgentRegistry --constructor-args $DEPLOYER

# (etc)

cd ../../openagents/conclave/contracts
forge install foundry-rs/forge-std --no-git
forge script script/Deploy.s.sol:Deploy \
  --rpc-url $ANVIL --private-key $DEPLOYER_PK \
  --sig 'runFresh(address)' 0x0000000000000000000000000000000000000000 \
  --broadcast
```

End-to-end deploy + verify takes ~3 minutes on a 2-CPU laptop.
