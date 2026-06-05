# openBDK Bridge Deployment Runbook

This document describes the step-by-step process for deploying the openBDK bridge contracts to a production environment connected to the AggLayer.

## Prerequisites

- Foundry installed (`curl -L https://foundry.paradigm.xyz | bash && foundryup`)
- Node.js 20+ (for AggLayer SDK tooling)
- A funded deployer account on both L1 and the openBDK chain
- A Gnosis Safe multisig deployed on both chains (recommended for ADMIN_ROLE)
- An openBDK chain registered with the AggLayer (rollup ID assigned)
- The Unified Bridge contract deployed and operational on the openBDK chain

## Phase 1: Pre-deployment validation

### 1.1 Verify the Unified Bridge address

The Unified Bridge MUST be deployed at the same address on both Ethereum L1 and the openBDK chain. The canonical address is:

```
0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe
```

Verify on L1:
```bash
cast code 0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe --rpc-url $ETHEREUM_RPC_URL | head -c 100
```

Verify on the openBDK chain:
```bash
cast code 0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe --rpc-url $OPENBDK_RPC_URL | head -c 100
```

Both should return non-zero bytecode. If either is empty, the bridge is not deployed and you cannot proceed.

### 1.2 Confirm your AggLayer network ID

Each AggLayer-connected chain has a unique network ID. Ethereum is `0`, Polygon zkEVM is `1`, and your openBDK chain has been assigned a unique ID by the AggLayer registration process.

```bash
cast call $UNIFIED_BRIDGE "networkID()(uint32)" --rpc-url $OPENBDK_RPC_URL
```

This is `OPENBDK_NETWORK_ID` in your deployment script. **Verify this matches the value in `script/DeployOpenBDK.s.sol`** before proceeding.

### 1.3 Compute the BridgeWrappedToken address

When L1 USDC is first bridged through the Unified Bridge to the openBDK chain (without using L1Escrow), it creates a `TokenWrapped` contract at a deterministic address. This address must be passed to the `NativeConverter` initializer.

To compute it:
```bash
# Method 1: Make a small bridge deposit and observe the BridgeWrappedToken creation event
cast send $UNIFIED_BRIDGE "bridgeAsset(uint32,address,uint256,address,bool,bytes)" \
  $OPENBDK_NETWORK_ID $YOUR_ADDRESS 1000000 $L1_USDC true 0x \
  --rpc-url $ETHEREUM_RPC_URL --private-key $DEPLOYER_PRIVATE_KEY

# After AggLayer settlement (~30 min), claim on the openBDK chain
# The TokenWrapped will be deployed and the address logged
```

Set this as `BRIDGE_WRAPPED_TOKEN_ADDRESS` in your `.env`.

## Phase 2: Deployment

### 2.1 Configure environment

```bash
cp .env.example .env
# Edit .env with all required values
```

Critical values to verify:
- `DEPLOYER_PRIVATE_KEY` — funded on both chains
- `ADMIN_ADDRESS` — Gnosis Safe multisig address
- `INITIAL_RELAYER_ADDRESS` — first Relayer for the validator registry
- `STAKING_TOKEN_ADDRESS` — your governance/staking token contract
- `MINIMUM_VALIDATOR_STAKE` — economic threshold for Validator registration
- `BRIDGE_WRAPPED_TOKEN_ADDRESS` — from Phase 1.3

### 2.2 Run deployment

```bash
forge script script/DeployOpenBDK.s.sol \
  --multi \
  --broadcast \
  --slow \
  --verify \
  -vvvv 2>&1 | tee deployment-$(date +%Y%m%d-%H%M%S).log
```

The `--slow` flag waits for each transaction to be mined before sending the next, preventing nonce issues during multi-chain deployment.

### 2.3 Verify deployment success

The script logs all deployed contract addresses. Save these to a deployment manifest:

```bash
# Example expected output
L1Escrow:         0x1234...abcd
L2Token:          0x2345...bcde
L2MinterBurner:   0x3456...cdef
NativeConverter:  0x4567...defg
ValidatorRegistry: 0x5678...efgh
```

## Phase 3: Post-deployment configuration

### 3.1 Grant CONSENSUS_ROLE to the consensus manager

The Validator Registry's `distributeRewards()` and `slash()` functions require `CONSENSUS_ROLE`. This should be granted to the consensus manager contract (CometBFT integration):

```bash
cast send $VALIDATOR_REGISTRY \
  "grantRole(bytes32,address)" \
  $(cast keccak "CONSENSUS_ROLE") \
  $CONSENSUS_MANAGER_ADDRESS \
  --rpc-url $OPENBDK_RPC_URL \
  --private-key $ADMIN_PRIVATE_KEY
```

### 3.2 Onboard initial Validators

Each of the 3 initial Validators must:

```bash
# Validator approves the Registry to spend their stake
cast send $STAKING_TOKEN \
  "approve(address,uint256)" \
  $VALIDATOR_REGISTRY \
  $MINIMUM_VALIDATOR_STAKE \
  --rpc-url $OPENBDK_RPC_URL \
  --private-key $VALIDATOR_PRIVATE_KEY

# Validator registers
cast send $VALIDATOR_REGISTRY \
  "registerValidator()" \
  --rpc-url $OPENBDK_RPC_URL \
  --private-key $VALIDATOR_PRIVATE_KEY
```

Then the Relayer activates each Validator:

```bash
cast send $VALIDATOR_REGISTRY \
  "activateValidator(address)" \
  $VALIDATOR_ADDRESS \
  --rpc-url $OPENBDK_RPC_URL \
  --private-key $RELAYER_PRIVATE_KEY
```

After all 3 are activated, verify the v1 topology:

```bash
cast call $VALIDATOR_REGISTRY "activeValidatorCount()(uint256)" --rpc-url $OPENBDK_RPC_URL
# Expected: 3

cast call $VALIDATOR_REGISTRY "getActiveValidatorSet()(address[])" --rpc-url $OPENBDK_RPC_URL
# Expected: [validator1, validator2, validator3]

cast call $VALIDATOR_REGISTRY "currentRelayer()(address)" --rpc-url $OPENBDK_RPC_URL
# Expected: relayer address
```

### 3.3 Smoke test the bridge

Test a small deposit/withdrawal cycle:

```bash
export TEST_AMOUNT=1000000  # 1 USDC (6 decimals)
export TESTER_ADDR=$(cast wallet address $DEPLOYER_PRIVATE_KEY)

# === L1 → L2 ===
# 1. Approve L1Escrow to spend USDC
cast send $L1_USDC "approve(address,uint256)" $L1_ESCROW $TEST_AMOUNT \
  --rpc-url $ETHEREUM_RPC_URL --private-key $DEPLOYER_PRIVATE_KEY

# 2. Bridge USDC to the openBDK chain
cast send $L1_ESCROW "bridgeToken(address,uint256,bool)" \
  $TESTER_ADDR $TEST_AMOUNT true \
  --rpc-url $ETHEREUM_RPC_URL --private-key $DEPLOYER_PRIVATE_KEY

# 3. Wait for AggLayer settlement (~30-60 minutes for ZK-verified, faster for trusted)
# Then claim on the openBDK chain (the AggLayer SDK can automate this)

# 4. Verify USDC.b balance on the openBDK chain
cast call $L2_TOKEN "balanceOf(address)(uint256)" $TESTER_ADDR --rpc-url $OPENBDK_RPC_URL

# === L2 → L1 ===
# 1. Bridge USDC.b back to L1
cast send $L2_MINTER_BURNER "bridgeToken(address,uint256,bool)" \
  $TESTER_ADDR $TEST_AMOUNT true \
  --rpc-url $OPENBDK_RPC_URL --private-key $DEPLOYER_PRIVATE_KEY

# 2. Wait for AggLayer settlement
# 3. Claim on L1 — USDC released from L1Escrow to TESTER_ADDR
```

## Phase 4: Operational monitoring

Set up monitoring for these critical conditions:

### Bridge health
- L1Escrow `escrowBalance()` should equal L2Token `totalSupply()` (modulo in-flight bridges)
- `BridgeEvent` and `ClaimEvent` emission counts should align between L1 and L2
- L1Escrow `paused()` and L2MinterBurner `paused()` should be `false`

### Validator health
- `activeValidatorCount()` should remain at 3 (v1 target)
- `currentRelayer()` should not change frequently (rotation indicates issues)
- Validator `fidesScore` should be increasing over time
- No `ValidatorSlashed` events under normal operation

### AggLayer settlement
- Monitor certificate settlement times in the AggLayer node
- Track `globalExitRoot` updates on Ethereum L1
- Verify pessimistic proofs are settling without errors

## Phase 5: Emergency procedures

### Pause the bridge
If a critical issue is detected:

```bash
cast send $L1_ESCROW "pause()" --rpc-url $ETHEREUM_RPC_URL --private-key $ADMIN_PRIVATE_KEY
cast send $L2_MINTER_BURNER "pause()" --rpc-url $OPENBDK_RPC_URL --private-key $ADMIN_PRIVATE_KEY
```

### Rotate the Relayer
If the Relayer is offline or compromised:

```bash
cast send $VALIDATOR_REGISTRY "rotateRelayer(address)" $NEW_RELAYER_ADDRESS \
  --rpc-url $OPENBDK_RPC_URL --private-key $GOVERNANCE_PRIVATE_KEY
```

### Slash a misbehaving Validator
If a Validator is detected double-signing or producing invalid votes:

```bash
cast send $VALIDATOR_REGISTRY "slash(address,uint256,string)" \
  $VALIDATOR_ADDRESS \
  $SLASH_AMOUNT \
  "Equivocation detected at block 12345" \
  --rpc-url $OPENBDK_RPC_URL --private-key $CONSENSUS_PRIVATE_KEY
```

### Upgrade contracts
All openBDK contracts are UUPS upgradeable. Upgrades require `DEFAULT_ADMIN_ROLE` (3-day timelock):

```bash
# 1. Deploy new implementation
forge create OpenBDKL1Escrow --rpc-url $ETHEREUM_RPC_URL --private-key $ADMIN_PRIVATE_KEY

# 2. Schedule upgrade via timelock (3 days)
# (Use Gnosis Safe transaction builder — DO NOT skip the timelock)

# 3. After timelock expires, execute upgrade
cast send $L1_ESCROW \
  "upgradeToAndCall(address,bytes)" \
  $NEW_IMPLEMENTATION \
  0x \
  --rpc-url $ETHEREUM_RPC_URL --private-key $ADMIN_PRIVATE_KEY
```

## Verification checklist

Before going live with significant value:

- [ ] All contracts verified on Etherscan/openBDK explorer
- [ ] Admin role transferred to Gnosis Safe multisig (3-day timelock active)
- [ ] All 3 Validators registered and activated
- [ ] Relayer configured and producing blocks
- [ ] Smoke test deposit/withdrawal completed end-to-end
- [ ] Monitoring dashboards deployed (Grafana/Prometheus)
- [ ] Emergency pause runbook tested in staging
- [ ] Independent security audit completed
- [ ] Bug bounty program announced
- [ ] L1 forced inclusion enabled as censorship backstop

## Reference deployment (Polygon zkEVM mainnet — DO NOT MODIFY)

These are the canonical contracts that openBDK inherits from. Use them as reference for what a successful deployment looks like:

| Contract | Address | Etherscan |
|----------|---------|-----------|
| Unified Bridge | `0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe` | [View](https://etherscan.io/address/0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe) |
| L1Escrow (USDC) | `0x70E70e58ed7B1Cec0D8ef7464072ED8A52d755eB` | [View](https://etherscan.io/address/0x70E70e58ed7B1Cec0D8ef7464072ED8A52d755eB) |
| ZkMinterBurner | `0xBDa0B27f93B2FD3f076725b89cf02e48609bC189` | [View](https://zkevm.polygonscan.com/address/0xBDa0B27f93B2FD3f076725b89cf02e48609bC189) |
| NativeConverter | `0xd4F3531Fc95572D9e7b9e9328D9FEaa8e8496054` | [View](https://zkevm.polygonscan.com/address/0xd4F3531Fc95572D9e7b9e9328D9FEaa8e8496054) |
| USDC.e | `0x37eAA0eF3549a5Bb7D431be78a3D99BD360d19e5` | [View](https://zkevm.polygonscan.com/address/0x37eAA0eF3549a5Bb7D431be78a3D99BD360d19e5) |

These contracts have been securing real value since 2023 with zero exploits.

---

For questions: `dev@openbdk.org`  
For security issues: `security@openbdk.org`
