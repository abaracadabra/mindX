# iDEBT — Deployment Runbook

This runbook is the authoritative procedure for deploying the iDEBT stack to
a new chain and transferring control to the DAIO. It assumes basic familiarity
with Foundry and a production-grade key-management setup.

## 1. Chain eligibility

- **EVM mainnet**: Ethereum, Polygon PoS, Polygon zkEVM, Arbitrum One,
  Optimism, Base, BNB Smart Chain, Avalanche C-Chain, zkSync Era, Fantom,
  Arc Network (Chain ID 5042002, USDC-native gas).
- **EVM testnet**: Sepolia (reference testnet for the repo's CI).
- **Non-EVM**: Algorand mainnet + testnet are supported only for x402
  facilitator and BANKON binding — no core iDEBT deployment lives on
  Algorand.

See [`src/libraries/ChainMapping.sol`](./src/libraries/ChainMapping.sol) for
the canonical table. `Deploy.s.sol` will revert with `chain not supported by
iDEBT` if run on any unknown EVM chain id; register the chain by extending
`ChainMapping.chainOf` and submitting a DAIO proposal.

## 2. Prerequisites

| Requirement | Why |
| --- | --- |
| Foundry `> 0.2.0` | compiler + script runner |
| Node `>= 20` | workspace tooling + frontend |
| A deployer private key with ≥ 0.3 native gas token | contract deployment |
| A chain-appropriate block explorer API key | source-code verification |
| Chainlink / Pyth / Synthetix feed addresses for the chain | oracle wiring |
| A designated Parsec x402 facilitator address | payment gateway |
| A designated mindX signing key and BANKON signer key | bridge / connector |
| A canonical settlement-token address (USDC preferred) | iDEBT collateral |

## 3. Directory conventions

```
deployments/
  mainnet.json
  polygon.json
  arbitrum.json
  base.json
  sepolia.json
  ...
```

Each JSON is written by the Foundry broadcast artefact plus a post-run
`jq`-generated summary; keep them checked into `main`.

## 4. One-time repo setup

```bash
git clone https://github.com/PYTHAI/idebt.git && cd idebt
foundryup
npm install
forge install openzeppelin/openzeppelin-contracts@v5.0.2 --no-commit
forge install foundry-rs/forge-std --no-commit
forge install smartcontractkit/chainlink@v2.14.0 --no-commit
forge install pyth-network/pyth-sdk-solidity --no-commit
# Synthetix V3 imports are interface-only; vendor them if you intend to build.
forge build
forge test -vv
```

If tests fail against a clean checkout, stop. Do not deploy a failing tree.

## 5. Environment

Copy `.env.example` → `.env` and fill:

```
PRIVATE_KEY=0x...
DEPLOYER_ADDRESS=0x...
SETTLEMENT_TOKEN=0x...                     # per-chain USDC (or tUSDC on testnet)
PARSEC_FACILITATOR=0x...
MINDX_SIGNING_KEY=0x...
BANKON_SIGNER=0x...

MAINNET_RPC_URL=...
POLYGON_RPC_URL=...
# ...
```

Verification keys:

```
ETHERSCAN_API_KEY=...
POLYGONSCAN_API_KEY=...
# ...
```

Governance knobs — override only if you have a reason:

```
DAIO_TIMELOCK_DELAY=172800        # 2 days in seconds
DAIO_VOTING_DELAY=7200            # ~1 day on 12s blocks
DAIO_VOTING_PERIOD=50400          # ~1 week
DAIO_PROPOSAL_THRESHOLD=100000000000000000000000  # 100k iVOTE
DAIO_QUORUM_PCT=20
```

## 6. Deployment procedure

### 6.1 Dry run

```bash
forge script script/deploy/Deploy.s.sol --rpc-url polygon -vvvv
```

Inspect the console output. Verify:

- All constructor arguments match your environment.
- `chainId` in the log matches the target network.
- No unexpected adapters are deployed.

### 6.2 Broadcast

```bash
forge script script/deploy/Deploy.s.sol \
  --rpc-url polygon \
  --broadcast \
  --verify \
  --slow \
  -vvvv
```

`--slow` serialises transactions so the treasury's role grants land after
their targets exist. On fast-finality L2s this can usually be dropped.

Expected output (example):

```
iDEBT deployment complete:
  voteToken      0x...
  treasury       0x...
  governor       0x...
  oracle         0x...
  stressIndex    0x...
  debtToken      0x...
  x402 gateway   0x...
  mindx bridge   0x...
  agent registry 0x...
  bankon conn    0x...
```

Record these in `deployments/<chain>.json`.

### 6.3 Post-deploy configuration

Set the oracle feed and Pyth price id env vars (chain-specific), then:

```bash
ORACLE=0x...  \
INDEX=0x...   \
DEBT=0x...    \
X402=0x...    \
PARSEC_FACILITATOR=0x...  \
CHAINLINK_DXY_FEED=0x...  \
CHAINLINK_VIX_FEED=0x...  \
CHAINLINK_GOLD_FEED=0x... \
PYTH_CONTRACT=0x...       \
PYTH_REAL_RATE_ID=0x...   \
PYTH_YIELD_ID=0x...       \
SYNTHETIX_V3_CORE=0x...   \
SYNTHETIX_MARKET_ID=1     \
forge script script/deploy/Configure.s.sol \
  --rpc-url polygon \
  --broadcast \
  -vvvv
```

`Configure` attaches oracle adapters, authorises the Parsec facilitator,
sets default x402 prices (`1 USDCa` for `iDEBT.open`, `0.5 USDCa` for
`iDEBT.claim`), and links `X402PaymentGateway` into the `iDEBT` core.

### 6.4 Role handover

After `Deploy` runs, the `DAIOTreasury` already holds the admin role on
every contract in the system. The deployer's temporary roles granted at
construction (for the mid-broadcast `grantRole` calls on the timelock) must
be renounced in a final transaction:

```bash
# OpenZeppelin v5 TimelockController uses DEFAULT_ADMIN_ROLE = 0x00...00.
cast send $TREASURY "renounceRole(bytes32,address)" \
  0x0000000000000000000000000000000000000000000000000000000000000000 \
  $DEPLOYER \
  --private-key $PRIVATE_KEY --rpc-url polygon
```

After this call, the DAIO (via proposal → timelock execution) is the sole
controller. Confirm with:

```bash
cast call $TREASURY "hasRole(bytes32,address)" \
  0x0000000000000000000000000000000000000000000000000000000000000000 \
  $DEPLOYER
# → 0x0000...0000 (false)
```

### 6.5 Verification

If `--verify` failed (rate limits, new chain), manually verify:

```bash
forge verify-contract \
  --chain polygon \
  --constructor-args $(cast abi-encode "constructor(address,address,address,address)" \
      $INDEX $USDC $TREASURY $TREASURY) \
  $DEBT src/core/iDEBT.sol:iDEBT \
  --etherscan-api-key $POLYGONSCAN_API_KEY
```

Repeat for each contract in the deployment summary.

## 7. Testnet (Sepolia) quickstart

```bash
npm run deploy:sepolia
```

`DeployTestnet.s.sol` first creates a mock USDC (`tUSDC`), mints 10M to the
deployer, and then runs the full Deploy. Use the same `Configure` invocation
with testnet oracle addresses.

## 8. Multi-chain coordination

iDEBT is deployed independently per chain — there is no bridge token or
cross-chain messaging layer in v0.1. Consistency comes from:

1. **A canonical oracle stack** published on each chain with the same
   per-metric weightings (`GlobalDebtStressIndex.weights`).
2. **A shared BANKON sovereign identity** bound once per chain via
   `BANKONConnector.bind`, letting heirs prove identity across deployments.
3. **A shared `chainmapping` table** in `src/libraries/ChainMapping.sol` and
   mirrored at `agenticplace.pythai.net/allchain.html`.

Cross-chain messaging (Chainlink CCIP, LayerZero) can be integrated in v0.2
once market demand justifies the audit expense.

## 9. Emergency procedures

### 9.1 Pause

Both the `DeltaVerseDebtOracle` and the `iDEBT` core implement `Pausable`.
The `EMERGENCY_ROLE` holder (the `DAIOTreasury`) can pause via a fast-track
timelock op (min-delay can be set to 0 for this path if configured at deploy
time — see `DAIOTreasury` docs; the reference config uses the full 2-day
delay, so emergency pauses require proactive governance).

### 9.2 Adapter revocation

If a Chainlink/Pyth feed turns malicious or deprecated:

```solidity
oracle.revokeSource(bytes32("CL_DXY"));
```

This does **not** remove the adapter from `_adapters[metric]`, only from the
source registry. To surgically detach, deploy a patched oracle and migrate
iDEBT by governance proposal (update the `stressIndex` immutable via a
factory redeploy).

### 9.3 x402 facilitator compromise

If the Parsec facilitator key is compromised:

1. Governance proposal: `gate.setFacilitator(oldSigner, false)`.
2. Deploy new Parsec signer; proposal: `gate.setFacilitator(newSigner, true)`.
3. Any in-flight receipts from the old signer will be rejected on
   `consume`; paid users can request re-issuance via Parsec.

## 10. Checklist

Before merging a deployment PR:

- [ ] All tests pass on clean checkout (`forge test -vv`).
- [ ] `forge coverage` reports ≥ 90% line coverage on `src/core/` and
      `src/integrations/`.
- [ ] Slither clean or every finding justified in PR.
- [ ] Deployment artefact written to `deployments/<chain>.json`.
- [ ] DAIO holds every admin role; deployer holds none.
- [ ] Oracle wired for all 7 metrics with at least one adapter each.
- [ ] x402 price table set for both scopes.
- [ ] `iDEBT.x402()` points at the deployed gateway.
- [ ] Verified contract source on the chain's block explorer.
- [ ] `deployments/<chain>.json` PR opened against `main`.

Once merged, publish the addresses to the registry at
`agenticplace.pythai.net/allchain.html` and announce on DAIO channels.
