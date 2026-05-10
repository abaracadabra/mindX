# `daio/contracts/marketing/` — Marketing Counsellor on-chain layer

Two contracts. Both new in this drop. Both consume existing Conclave + Tier-1 infrastructure.

| File | Purpose | Deploy target | Lines |
|---|---|---|---|
| `MarketingAttributionReceipt.sol` | Per-campaign envelope, EIP-712 v2 with indexed `boardroomSessionId` joining the receipt to the 8-soldier weighted vote that approved it | Base mainnet (sub-cent per receipt) | ~220 |
| `MarketingTreasury.sol` | Marketing-attributed revenue → 99% buyback → BANKON SATOSHI burn | Ethereum L1 (constitutional finality) | ~210 |

## The three-receipt model

A marketing campaign emits three orthogonal receipt types. Each answers a different question; conflating them would lose information. Reading [`docs/MARKETING_RECEIPTS.md`](../../../docs/MARKETING_RECEIPTS.md) first is strongly recommended.

| Question answered | Contract | Module |
|---|---|---|
| **WHO acted, with what authority, when?** | `Tessera.sol` | `openagents/conclave/contracts/src/Tessera.sol` |
| **WAS A PAYMENT settled?** | `X402Receipt.sol` | `daio/contracts/x402/X402Receipt.sol` |
| **WHAT was the campaign, why, total cost, what outcome?** | `MarketingAttributionReceipt.sol` | THIS PACKAGE |

A typical campaign emits 1 of these envelopes + N Tessera credentials (one per executing soldier) + M X402Receipts. All three cross-reference each other by `traceId` (32-byte hash off-chain derived from `campaignId | soldier_id | step`). The `MarketingAttributionReceipt` envelope additionally carries the `boardroomSessionId` that approved it, so analysts can join the on-chain receipt to the off-chain weighted-vote record from `daio.governance.boardroom.Boardroom.convene()`.

## Why a separate `MarketingTreasury`

`MarketingTreasury.sol` is not a receipt; it is a buyback/burn router. It is intentionally separate from the main `Treasury.sol` for three reasons:

1. **Different burn rule.** Hard-coded 99% revenue → buyback → BANKON SATOSHI burn. Encoded in code, not config — non-circumventable and auditable.
2. **Accounting separation.** Marketing-attributed revenue must be tagged distinctly so quarterly RetroPGF + BANKON SATOSHI burn dashboards can read a single source.
3. **Narrative transparency.** Every burn is a public narrative beat; decoupled events keep marketing burns from polluting (or being polluted by) other treasury flows.

## Build + test

A scoped Foundry profile lives at `daio/contracts/foundry.toml::[profile.marketing]`:

```bash
cd daio/contracts
FOUNDRY_PROFILE=marketing forge build
FOUNDRY_PROFILE=marketing forge test --fuzz-runs 50000 -vvv
```

The `--fuzz-runs 50000` is the load-bearing CI gate: replay protection on `MarketingAttributionReceipt` is the single most consequential property, and the fuzz fuzzes `(agent, campaignId, nonce)` exhaustively to confirm no two valid signatures exist for the same tuple.

## Deploy

Two legs, run by the operator (NOT this plan):

```bash
# Leg A — receipts to Base mainnet
forge script daio/contracts/marketing/script/DeployMarketing.s.sol:DeployMarketing \
  --rpc-url $BASE_RPC_URL --broadcast --verify

# Leg B — treasury to Ethereum L1
forge script daio/contracts/marketing/script/DeployMarketing.s.sol:DeployMarketingTreasury \
  --rpc-url $MAINNET_RPC_URL --broadcast --verify
```

Required env vars (set in `.env.deploy`):

```
DEPLOYER_PRIVATE_KEY
OWNER_MULTISIG

# Leg A
MARKETING_TESSERA_ADDR
MARKETING_CENSURA_ADDR
MARKETING_CENSURA_FLOOR     # default 50

# Leg B
MARKETING_REVENUE_ASSET     # USDC L1 contract
MARKETING_BANKON_SATOSHI    # BKS L1 contract
MARKETING_UNI_V3_ROUTER     # Uniswap SwapRouter02
MARKETING_POOL_FEE          # default 3000 (0.3%)
MARKETING_FOUNDATION_ADDR
```

After deploy, populate the corresponding `marketinga.toml` env vars
(`MARKETING_ATTRIBUTION_RECEIPT_ADDR`, `MARKETING_TREASURY_ADDR`) and run:

```bash
python -m agents.marketing.onchain.bind_identity --execute
```

## Pause / kill switch

`MarketingTreasury` is `Pausable`. The `PAUSE_ROLE` is granted to the admin
multisig; production wires it to the `BoardroomExtension` admin (today) or
BONAFIDE Censura (when wired). Any pause halts new buybacks immediately;
unpaid revenue stays in the contract until unpause.

`MarketingAttributionReceipt` is not pausable — receipts are pure record
attestations. Censura can fade an agent's reputation, which the contract
checks per-call, so pausing one agent costs no contract changes.

## Subgraph / Dune indexing

All envelope fields are indexed event topics. A subgraph that reads
`AttributionReceiptRecorded(bytes32 indexed campaignId, address indexed agent, bytes32 indexed traceId, ...)` plus `MarketingRevenueReceived` and `MarketingBuybackExecuted` from the treasury can reconstruct full per-campaign provenance: brief CID, audience hash, channel mask, total spend in USD micro, outcome metric CID, revenue inflow, buyback output, burn announcement.
