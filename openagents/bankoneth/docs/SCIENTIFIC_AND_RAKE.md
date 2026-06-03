# SCIENTIFIC + RAKE — the cypherpunk2048 financial primitives (`contracts/cp2048/`)

The economic core of the ETHGlobal NY build: a **golden-ratio fee** charged on universal payments,
collected home to **bankon.eth** only when it beats the chain's cost, with a **precision rail** that
breaks past EVM's 18-decimal ceiling. Built to the cypherpunk2048 standard (flat snake_case, Apache-2.0).
**9/9 tests pass** (mocks, no RPC).

## The golden-ratio fee (φ)

`cp2048_constants.sol` pins φ to the precision each rail allows:
- `PHI_WAD = 1_618033988749894848` — φ to **18 dp** (EVM-native max).
- `PHI_E36 = 1_618033988749894848204586834365638118` — φ to **36 dp** (the SCIENTIFIC rail).
- `PHI_MINUS_ONE_WAD = 618033988749894848` — the canonical golden fraction 1/φ = φ−1.

The BANKON fee is a φ-derived micro-fee: `goldenFeeWad(amount, feeDiv) = amount × (φ−1) / feeDiv`,
computed in the 36-dp rail then truncated to 18 dp. Default `feeDiv` ≈ 10 000 → a ~0.00618% golden
micro-fee; `feeDiv` is configurable (set 0 to disable). *Adjustable:* the exact economic form (φ-bps vs
golden fraction) is a parameter — this is the sane default.

## SCIENTIFIC — the precision rail (`scientific_token.sol` + `scientific_math.sol`)

`scientific_math` carries values in **1e36 scale** — *"18 places on both sides"* — so fee math keeps
accuracy beyond 18 dp. Verified by the **φ² = φ + 1** identity holding to 36 dp in-test.

`scientific_token` (**SCIENTIFIC / SCIEN**), 18-decimal ERC-20:
- **Total supply minted once** to a single issuance address (constructor) — no further mint exists.
- **`BENEFICIARY` is `immutable`** (derived from the owner's public key, `bankon.eth`).
- **Owner-renounce** after issuance + Uniswap pairing (`renounceOwnership()`); the beneficiary stays.
- **Tradeable + Uniswap-pairable** (plain ERC-20, no transfer tax/hooks).
- **`self_purge(asset)`** — permissionless sweep of ANY token/ETH the contract holds; funds can **only**
  ever reach the immutable beneficiary. The contract cannot leak value anywhere else (test-proven).

## RAKE — collect home, only when it's worth it (`rake.sol` + `bankon_oracle.sol`)

`bankon_oracle` prices an asset **straight from its Uniswap pair** (`valueUsd6` reads `getReserves`),
USDC pass-through for the quote.

`rake` accrues the golden fee in any asset and `collect(asset)` sweeps it to the **immutable beneficiary
(`bankon.eth`)** **only when** `oracle.valueUsd6(asset, balance) > chainCostThresholdUsd6` — so collection
never costs more than it returns, and the threshold differs per chain (immutable + governance setter).
`collect` is permissionless (any keeper); funds only ever go home. `collect_native` handles ETH.

## Universal collection rails (`bankon_autoconvert.sol` + `bridge_collect.sol`)

- **`bankon_autoconvert`** — pull any token, take the golden fee → RAKE, swap the rest to the settlement
  token via the **Uniswap V3 SwapRouter** (reuse of Uniswap's open-source stack = the Uniswap Stack
  Contribution), deliver to the recipient. Works on every chain hosting a V3 router.
- **`bridge_collect`** — the on-chain anchor of the **"GLMR bridging machine"** (LI.FI extrapolation):
  pay any currency on any chain, take the golden fee → RAKE, emit a `BridgeCollected` intent the
  LI.FI/GLMR relayer fulfils to the settlement chain. Sovereign on-chain collection + open bridge infra.

## How it plugs into the payment layer
`packages/web/payments.js` `swap`/`bridge` rails call `bankon_autoconvert` / `bridge_collect`; the φ fee
+ SCIENTIFIC precision toggle surface in the UI. Settlement feeds the iNFT/subname registrar or the ARC
marketspace. Every fee, on every chain, rakes home to `bankon.eth`.

## Deploy notes
SCIENTIFIC: deploy → add Uniswap liquidity → `renounceOwnership()`. RAKE/oracle/autoconvert per chain;
set the pair, USDC, threshold, and the V3 router for that chain. `script/export-abis.mjs` emits all ABIs
(`category: "cp2048"`); deployment keys: `scientific`/`rakeCollector`/`bankonOracle`/`autoconvert`/`bridgeCollect`.
