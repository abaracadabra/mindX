# S.M.A.I.R.T Bonding Presale: Technical & Professional Overview

## Introduction

**S.M.A.I.R.T** (Solidity Machine Augmented Intelligent Response Technology) is a presale and token system that lets project creators launch ERC20 tokens with fee-on-transfer tokenomics, run a fair and transparent presale, and automatically provide and lock initial liquidity on a Uniswap V2–compatible DEX.

In the **DAIO bonding** implementation, S.M.A.I.R.T is realized as the **Bonding Curve Presale**: it does not replace the bonding curve but **uses** it. The curve defines token price and supply; the presale raises native currency (ETH), then uses that curve to buy tokens for distribution and for liquidity, and finally adds and time-locks LP tokens. This document describes the mechanics of the S.M.A.I.R.T bonding presale from a technical and professional perspective, based on the code in `daio/contracts/bonding`.

---

## Design Goals

- **Simplify token launches**: “Presale as a Service” — creators define token and presale parameters; the system deploys and orchestrates with on-chain automation.
- **Fair launches**: Significant initial liquidity and time-locked LP tokens to support trust and transparency.
- **Configurability**: Fees (reflections, liquidity, marketing, development) and presale mechanics (caps, limits, allocation) are set at deployment and enforced on-chain.
- **Transparency**: All operations and key actions are on-chain and event-logged (“Code is Law”).
- **Security**: OpenZeppelin patterns (ownership, reentrancy protection), input validation, and slippage guards.

---

## Architecture: Three Pillars

The S.M.A.I.R.T bonding system is built from three core layers.

### 1. Bonding Curve (Service Token & Pool)

- **CurveToken** (`CurveToken.sol`): ERC20 whose mint/burn are restricted to the bonding curve pool. Name and symbol are configurable at deployment (defaults: “REFLECT REWARD” / “REWARD”).
- **BondingCurvePoolNative** (`BondingCurvePoolNative.sol`): Native-reserve (ETH) pool supporting multiple curve types (POWER, LINEAR, EXPONENTIAL, DECELERATING, TIERED). When using **POWER** (e.g. via the factory), pricing is `P(S) = k * S^p` (UD60x18). **POWER settings** allow flexible custom behavior: `p = 1e18` for linear, `p < 1e18` for decelerating (e.g. sqrt with `p = 0.5e18`), `p > 1e18` for accelerating; `k` scales the price level. See `CURVE_TYPES.md` for recommended POWER patterns (linear, sub-linear, super-linear, aggressive early, etc.). The pool exposes:
  - `buy(minTokensOut, to)`: pay ETH, receive newly minted tokens.
  - `sell(tokensIn, minEthOut, to)`: burn tokens, receive ETH.
  - Optional protocol fee (bps) on buy/sell.

The presale **does not replace** this curve; it **calls** it. All presale-purchased tokens are obtained by sending ETH to the pool’s `buy()` via the presale’s finalization and contribution logic.

### 2. Liquidity Locker (LP Guardian)

- **LiquidityLocker** (`LiquidityLocker.sol`): Holds and time-locks LP tokens. Deployed and initially owned by the presale contract; ownership is transferred to the presale creator after finalization.
- **lockLP(lpToken, amount, beneficiary, lockDurationDays)**: Called by the presale during finalization. Records an immutable lock (amount, release time, beneficiary).
- **withdrawLP(lpToken)**: Only the beneficiary can call; only after `releaseTime` has passed. Transfers locked LP to the beneficiary.
- **Recovery**: Owner can recover native currency (or other ERC20) accidentally sent to the locker, without affecting existing LP locks.

This gives “Code is Law” guarantees: LP cannot be withdrawn before the on-chain release time.

### 3. Presale (Orchestrator)

- **BondingCurvePresaleSMAIRT** (`BondingCurvePresaleSMAIRT.sol`): Central orchestrator. It is wired to an existing bonding curve pool and token, and to a liquidity provisioner (e.g. Uniswap V2).
- **Lifecycle states**: `1 = Initialized`, `2 = Active`, `3 = Canceled`, `4 = Finalized`, `5 = Failed`.
- **Contribution phase**: Accepts ETH via `receive()` / `buy()` during the active window, respecting start/end time, per-user min/max contribution, and hard cap.
- **Successful finalization**: If soft cap is met and finalization conditions hold:
  - Allocates raised ETH by BPS to: marketing, dev, DAO, and liquidity.
  - Uses the liquidity share: half stays as ETH, half is used to buy tokens from the bonding curve; then adds liquidity on a Uniswap V2–compatible DEX.
  - Sends resulting LP tokens to the LiquidityLocker and time-locks them for the configured beneficiary and duration.
  - Remaining ETH buys curve tokens for presale distribution; contributors claim proportionally.
  - Optionally performs team allocation (from raised funds and/or from token supply).
  - Transfers ownership of the curve token and LiquidityLocker to the presale creator.
- **Failure / cancellation**: If soft cap is not met or the presale is canceled, contributors can call `refund()` to recover their ETH. Curve token ownership is transferred to the presale creator.

---

## Presale Mechanics in Detail

### Parameters (PresaleOptions)

| Parameter | Description |
|-----------|-------------|
| `hardCapNative` | Maximum ETH the presale will accept. |
| `softCapNative` | Minimum ETH for successful finalization; below this, state can move to Failed. |
| `maxContributionPerUserNative` / `minContributionPerUserNative` | Per-address contribution bounds. |
| `startTime` / `endTime` | Presale window (Unix timestamps). |
| `nativeForLiquidityBps` | Share of raised ETH (basis points) used for DEX liquidity. |
| `presaleNativeForMarketingBps` / `presaleNativeForDevBps` / `presaleNativeForDaoBps` | BPS to marketing, dev, and DAO wallets. |
| `presaleMarketingWallet` / `presaleDevWallet` / `presaleDaoWallet` | Recipients for the above. |
| `liquidityLockDurationDays` | LP lock duration; 0 = no lock. |
| `liquidityBeneficiaryAddress` | Beneficiary of the locked LP (often the presale creator). |
| `minTokensForLiquidity` / `minTokensForSale` | Slippage guards for curve buys used for LP and for sale distribution. |
| `useLiquidityFreePresale` | If true, no DEX liquidity is added; only curve buys for distribution and optional team/marketing/dev/DAO. |
| `useTeamAllocationFromFunds` / `teamAllocationFromFundsBps` | Use a BPS of raised ETH to buy curve tokens for the team wallet. |
| `useTeamAllocationFromSupply` / `teamAllocationFromSupplyBps` | Allocate a BPS of total token supply to the team wallet (implementation may buy from curve as proxy where mint is not exposed). |
| `teamWallet` | Team recipient. |

Validation at deployment ensures caps, times, BPS sums, and non-zero addresses where required.

### State Machine

1. **Initialized (1)**  
   Presale is deployed. Optionally, if `block.timestamp >= startTime`, the constructor can set state to Active.

2. **Active (2)**  
   Owner may call `activate()` if still Initialized and `block.timestamp >= startTime`. Users send ETH to the contract (`receive()` / `buy()`). Checks: within start/end time, per-user min/max, hard cap.

3. **Finalized (4)**  
   Owner calls `finalize()` when:
   - `nativeRaised >= softCapNative`, and  
   - Either `nativeRaised >= hardCapNative` or `block.timestamp >= endTime`.  
   The contract then:
   - Splits ETH (marketing, dev, DAO, liquidity).
   - Uses liquidity ETH: half for curve buy, half paired with those tokens on the DEX; LP tokens are sent to the locker and locked.
   - Uses remaining ETH to buy curve tokens for presale distribution (`tokensBoughtForSale`).
   - Optionally allocates team tokens from funds and/or supply.
   - Sends marketing/dev/DAO ETH to their wallets.
   - Transfers ownership of token and locker to presale creator.
   - Contributors later call `claim()` to receive their share of `tokensBoughtForSale` proportionally to their contribution.

4. **Canceled (3)**  
   Owner calls `cancel()` from Initialized or Active. Contributors can `refund()`.

5. **Failed (5)**  
   Set when finalization is attempted but `nativeRaised < softCapNative` (e.g. after end time). Contributors can `refund()`.

### Allocation Math (Finalization)

- `ethForLiquidityTotal = nativeRaised * nativeForLiquidityBps / 10_000`
- `ethForMkt` / `ethForDev` / `ethForDao` similarly from their BPS.
- `ethForSaleBuy = nativeRaised - (ethForLiquidityTotal + ethForMkt + ethForDev + ethForDao)`
- Liquidity split: `ethForRouter = ethForLiquidityTotal / 2`, `ethForCurveBuyLP = ethForLiquidityTotal - ethForRouter`.
- Curve buy for LP: `curvePool.buy{value: ethForCurveBuyLP}(minTokensForLiquidity, presaleContract)`.
- Curve buy for sale: `curvePool.buy{value: ethForSaleBuy}(minTokensForSale, presaleContract)` → `tokensBoughtForSale`.
- If liquidity is enabled and not liquidity-free: add liquidity with `ethForRouter` and the tokens from the LP buy; send LP to locker and call `locker.lockLP(...)`.

Claim amount for a user: `(contributions[user] * tokensBoughtForSale) / nativeRaised`.

### Security Properties

- **ReentrancyGuard** on all value-moving functions (buy, refund, claim, finalize).
- **State checks** so buy/claim/refund/finalize run only in the correct state.
- **Slippage**: `minTokensForLiquidity` and `minTokensForSale` protect curve buys.
- **LP locking**: Locker holds LP until `releaseTime`; only beneficiary can withdraw after that.
- **No generic LP recovery** in the locker to avoid rug vectors; only designated recovery for accidentally sent assets.

---

## Integration with Uniswap V2

- **ILiquidityProvisioner**: Abstract interface for adding liquidity (V2/V3/V4 modes; bonding uses V2 in production).
- **UniV2Provisioner**: Implements `addLiquidity(LiquidityRequest)`: pulls token from sender, approves router, calls `addLiquidityETH`, returns pair address and liquidity amount. Presale passes a template request (router, WETH, mode, enabled) at deployment; at finalization it fills in token, amounts, recipient (presale contract), and deadline.
- Presale approves the provisioner, then calls `provisioner.addLiquidity{value: ethForRouter}(r)`. LP tokens are received by the presale contract, then transferred to the LiquidityLocker and locked.

---

## Factory Flow (BondingCurveFactory)

- **BondingCurveFactory** deploys CurveToken and BondingCurvePoolNative, configures the pool (e.g. protocol fee), and optionally deploys **BondingCurvePresaleSMAIRT** with the chosen PresaleOptions and liquidity template.
- One call to `launchPowerCurveNative(...)` yields token, pool, and (if enabled) presale address. The presale is already wired to that pool and token and to the provisioner.

---

## Events and Transparency

Events emitted include:  
`Purchased`, `Finalized`, `Canceled`, `Refunded`, `TokensClaimed`, `LiquidityAdded`, `LiquidityLocked`, `TeamAllocatedFromFunds`, `TeamAllocatedFromSupply`, `LiquidityFreePresaleMode`.  
These allow indexing and UIs to reflect presale state, contributions, and LP lock details in real time.

---

## Frontend and User Flows

A typical S.M.A.I.R.T bonding frontend (e.g. DAIO-style dapp) will:

1. **Connect wallet** and detect network.
2. **Read presale state**: `state()`, `options()`, `nativeRaised()`, `contributions(user)`, `tokensBoughtForSale()`, `claimed(user)`.
3. **Contribute**: Send ETH to the presale contract (calls `receive()`/`buy()`).
4. **Claim**: After finalization, call `claim()` to receive proportional tokens.
5. **Refund**: If Canceled or Failed, call `refund()` to get ETH back.
6. **LP lock info**: Query LiquidityLocker’s `getLockDetails(lpToken, beneficiary)` for amount, release time, and lock status.

Creator flows (owner only): `activatePresale()`, `finalizePresale()`, `cancelPresale()`.

---

## Summary

The S.M.A.I.R.T bonding presale is a **presale layer on top of a bonding curve**: it raises ETH, enforces caps and time windows, and on success uses that ETH to buy curve tokens for distribution and for DEX liquidity, then time-locks LP tokens. The curve remains the single source of token minting and pricing; the presale is the automated, rule-driven orchestrator that implements fair launches, configurable allocation, and transparent, on-chain execution suitable for deployment and integration with the DAIO ecosystem and Uniswap V2–compatible DEXs.
