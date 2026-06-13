# BankonPriceOracle

> ENS-aligned length-tiered USD pricing oracle with PYTHAI native-asset discount and Chainlink ETH/USD + Uniswap v3 TWAP conversions.

**SPDX:** MIT | **Pragma:** ^0.8.24 | **Source:** [`BankonPriceOracle.sol`](./BankonPriceOracle.sol)

## Role in bankoneth

`BankonPriceOracle` produces the canonical USD price (always returned in **USDC base units, 6 decimals**) for any subname registration across the bankoneth flows. The pricing tier matches the ENS reference price ladder — 3-char and 4-char labels are premium, 5+/6/7+ slide into commodity tiers. The oracle additionally converts USD prices into ETH (via Chainlink) and PYTHAI (via Uniswap v3 TWAP, with a stub fallback) so registrars can quote in whichever rail the customer chose.

It is agnostic of registrar identity: anything implementing length-based pricing + multi-token conversion can call into it. In bankoneth it is consumed by `BankonSubnameRegistrar` (Flow A — `priceUSD` for quote, also indirectly by `BankonEthRegistrar`) and by `BankonEthRegistrar.quote` (Flow B). `BankonDomainHosting` (Flow C) uses parent-set USD pricing directly rather than the oracle's tiered defaults.

The contract holds no funds and is purely views + admin setters. The Uniswap v3 TWAP path is intentionally a stub for the hackathon ship — the tick is consulted and then the operator-set `pythaiPerUsdcStub` is returned. Live wiring to `OracleLibrary.getQuoteAtTick` is deferred to the mainnet release per inline comment.

## Inheritance

- `IBankonPriceOracle` — public interface defined in [`interfaces/IBankon.sol`](./interfaces/IBankon.sol).
- `AccessControl` — `DEFAULT_ADMIN_ROLE` + `GOV_ROLE`.

## Constructor

| arg    | type      | purpose                                                                  |
|--------|-----------|--------------------------------------------------------------------------|
| `admin`| `address` | Granted both `DEFAULT_ADMIN_ROLE` and `GOV_ROLE`.                        |

Roles granted at construction: `DEFAULT_ADMIN_ROLE` → `admin`, `GOV_ROLE` → `admin`.

## Storage layout

| name                  | type                          | purpose                                                            | mutable? |
|-----------------------|-------------------------------|--------------------------------------------------------------------|----------|
| `GOV_ROLE`            | `bytes32 constant`            | `keccak256("GOV_ROLE")`.                                           | no       |
| `price3`              | `uint256` public              | 3-char per-year USD6 (default `320_000000` = $320).                | yes (gov)|
| `price4`              | `uint256` public              | 4-char per-year USD6 (default `80_000000` = $80).                  | yes (gov)|
| `price5`              | `uint256` public              | 5-char per-year USD6 (default `5_000000` = $5).                    | yes (gov)|
| `price6`              | `uint256` public              | 6-char per-year USD6 (default `3_000000` = $3).                    | yes (gov)|
| `price7plus`          | `uint256` public              | 7+-char per-year USD6 (default `1_000000` = $1).                   | yes (gov)|
| `pythaiDiscountBps`   | `uint16` public               | Basis-point discount for PYTHAI-paid (default `2000` = 20%).       | yes (gov)|
| `ethUsdFeed`          | `IAggregatorV3` public        | Chainlink ETH/USD feed (8 decimals).                               | yes (gov)|
| `twap`                | `IUniV3TwapLike` public       | Uniswap v3 TWAP helper.                                            | yes (gov)|
| `pythaiUsdcPool`      | `address` public              | UniV3 pool for PYTHAI/USDC TWAP.                                   | yes (gov)|
| `pythaiToken`         | `address` public              | PYTHAI ERC-20 (L1 mirror of the ASA).                              | yes (gov)|
| `usdc`                | `address` public              | USDC ERC-20.                                                       | yes (gov)|
| `weth`                | `address` public              | WETH ERC-20.                                                       | yes (gov)|
| `pythaiPerUsdcStub`   | `uint256` public              | Stub fallback PYTHAI-per-USDC (default `50`).                      | yes (gov)|

## Roles

| Role                 | keccak256                  | Who holds                | What they can do                                                            |
|----------------------|----------------------------|--------------------------|------------------------------------------------------------------------------|
| `DEFAULT_ADMIN_ROLE` | OpenZeppelin default       | `admin` (constructor)    | Manage roles.                                                                |
| `GOV_ROLE`           | `keccak256("GOV_ROLE")`    | `admin` (constructor)    | `setPrices`, `setPythaiDiscount`, `setFeeds`, `setTokens`, `setPythaiStub`. |

## Events

### `PricesUpdated(uint256 p3, uint256 p4, uint256 p5, uint256 p6, uint256 p7)`

Emitted on `setPrices`. Mirror in any off-chain quoting system.

### `PythaiDiscountUpdated(uint16 oldBps, uint16 newBps)`

Emitted on `setPythaiDiscount`.

### `FeedsUpdated(address ethUsdFeed, address twap, address pythaiUsdcPool)`

Emitted on `setFeeds`. Indexers should re-validate that the new addresses respond to the expected ABIs (the contract does not).

### `TokensUpdated(address pythaiToken, address usdc, address weth)`

Emitted on `setTokens`.

### `PythaiStubUpdated(uint256 oldRate, uint256 newRate)`

Emitted on `setPythaiStub`. While the production TWAP path is deferred, this is the only knob that affects PYTHAI quotes — operators should monitor it carefully.

## Errors

### `UnsupportedToken(address token)`

Reverted by `priceInToken` when the token is none of `usdc`, `weth`, or `pythaiToken`. Caller should pick one of the three.

### `BadEthPrice()`

Reverted by `_usdToEth` when `ethUsdFeed` is unset or when `latestRoundData()` returns `px <= 0`. Indicates a stale or missing Chainlink feed — caller should retry later or fall back to USDC.

### `EmptyLabel()`

Reverted when `bytes(label).length == 0`. Both `priceUSD` and `priceInToken` enforce this.

## External / public API

### `priceUSD(string calldata label, uint256 durationYears) external view returns (uint256 usd6)`

Returns the total USD-base-units price for `label` over `durationYears`. Internally: tier-by-length × years (treats `durationYears == 0` as `1`). Reverts `EmptyLabel` on empty input.

### `priceInToken(string calldata label, uint256 durationYears, address token) external view returns (uint256 amount)`

Returns the price denominated in `token`:
- `token == usdc` → returns `usd6` unchanged.
- `token == weth` → converts via Chainlink `ethUsdFeed` (8-decimal price), returning **wei** (18-decimal).
- `token == pythaiToken` → applies `pythaiDiscountBps` discount first, then `_usdToPythai` (consults TWAP but currently returns `usd6 * pythaiPerUsdcStub`).
- Anything else → reverts `UnsupportedToken(token)`.

### `setPrices(uint256 _p3, uint256 _p4, uint256 _p5, uint256 _p6, uint256 _p7) external`

Atomically updates all five tier prices. Access: `GOV_ROLE`.

### `setPythaiDiscount(uint16 newBps) external`

Updates the PYTHAI discount. Reverts `"discount > 50%"` if `newBps > 5000`. Access: `GOV_ROLE`.

### `setFeeds(address _ethUsd, address _twap, address _pool) external`

Atomically replaces the Chainlink feed + TWAP helper + UniV3 pool address. Access: `GOV_ROLE`.

### `setTokens(address _pythai, address _usdc, address _weth) external`

Atomically replaces the recognized token addresses. Access: `GOV_ROLE`.

### `setPythaiStub(uint256 newRate) external`

Updates the stub PYTHAI/USDC rate (units: PYTHAI per USDC base unit). Access: `GOV_ROLE`.

## Internal helpers

### `_perYearUSD(uint256 len) internal view returns (uint256)`

Pure tier mapping: `len <= 3 → price3`, `len == 4 → price4`, `len == 5 → price5`, `len == 6 → price6`, else `price7plus`. Note "1-char" and "2-char" labels fall into `price3` even though the registrar's `_checkLabel` rejects `len < 3`.

### `_usdToEth(uint256 usd6) internal view returns (uint256)`

Converts USD6 to wei using Chainlink's 8-decimal feed: `wei = usd6 * 1e20 / px`. Reverts `BadEthPrice` if feed unset or stale.

### `_usdToPythai(uint256 usd6) internal view returns (uint256)`

Production-intent: consult the UniV3 TWAP and use `OracleLibrary.getQuoteAtTick`. Hackathon-shipped: queries `twap.consult(pool, 1800)` (30-min window) and **discards** the result, falling back to `usd6 * pythaiPerUsdcStub`. Inline comment flags this as deferred work.

## Invariants

- `priceUSD(label, 0) == priceUSD(label, 1)` (zero years is normalized to one).
- `priceInToken(label, n, usdc) == priceUSD(label, n)` (USDC-quoted price equals USD price by definition).
- `pythaiDiscountBps <= 5000` enforced on every `setPythaiDiscount`.
- Tier ordering is **not enforced** — admin could set `price3 < price7plus`, which is intentional flexibility for promotions.
- No funds held; no `receive()`.

## Security considerations

- **Stale Chainlink data**: `_usdToEth` only checks `px > 0`; it does NOT validate `updatedAt`. A frozen feed can leak stale prices. Production callers should add their own freshness check or wire a freshness-checked oracle wrapper.
- **TWAP stub**: PYTHAI price is currently the stub. Until live TWAP is wired, treat PYTHAI quotes as advisory only; large positions could be mispriced.
- **Length tier rounding**: per-year tiers are flat — there is no proration. A 5-char registration for 0.5 years still costs `price5` (because `durationYears == 0` normalizes to 1).
- **Admin trust**: `GOV_ROLE` can flip every parameter. Use a multisig in production. `setFeeds(0, 0, 0)` makes the oracle silently fall back to ETH-revert + PYTHAI-stub paths.
- **Reentrancy**: pure views; no external calls write state here. Safe for use inside `nonReentrant` flows.
- **Cross-token gaps**: `priceInToken` does NOT support cross-token quotes (e.g. PYTHAI denominated in WETH). Add a swap layer off-chain if needed.

## Integration patterns

- `BankonSubnameRegistrar.register` calls `priceOracle.priceUSD(label, _yearsFromExpiry(expiry))` at [`BankonSubnameRegistrar.sol:211`](./BankonSubnameRegistrar.sol) to compute the receipt amount. The registrar uses the result only for the event log + `recordReceipt` accounting (the actual payment happens off-chain via x402).
- `BankonEthRegistrar.quote` calls `priceOracle.priceUSD(label, durationYears)` for the USD side of the dual return [`BankonEthRegistrar.sol:122`](./BankonEthRegistrar.sol).
- `BankonSubnameRegistrar.setPriceOracle(address)` hot-swaps the oracle without redeploying.
- Deployed via [`script/DeployEthereum.s.sol`](../script/DeployEthereum.s.sol) line 71: `new BankonPriceOracle(treasury)`.

## Known gotchas

- The `_usdToPythai` stub silently consumes the TWAP tick and discards it (`tick; // silence unused`). Once production wiring lands, integrators must NOT depend on the stub rate being stable — it will swing with PYTHAI/USDC market.
- `setPrices` does not validate ordering or sane bounds — admin could brick the oracle by setting all prices to `uint256.max`.
- `priceInToken(label, years, pythaiToken)` requires both `pythaiToken` and `pythaiPerUsdcStub` to be set; otherwise the discount math produces a sensible-looking but meaningless 0.
- Chainlink ETH/USD on mainnet has 8 decimals; ensure the `_ethUsd` passed to `setFeeds` matches. The contract assumes 8-decimal feeds without checking `feed.decimals()`.

## See also

- [`interfaces/IBankon.md`](./interfaces/IBankon.md) — `IBankonPriceOracle` interface.
- [`BankonSubnameRegistrar.md`](./BankonSubnameRegistrar.md) — Flow A consumer.
- [`BankonEthRegistrar.md`](./BankonEthRegistrar.md) — Flow B consumer.
- [`BankonPaymentRouter.md`](./BankonPaymentRouter.md) — downstream router that records the USD amount the oracle computed.
