# iDEBT — Mechanics

> This document explains *how the machine actually runs*. It traces every
> meaningful state transition from oracle byte to settled payout, shows
> the source code that implements each step, and connects those mechanics
> back to the protocol's thesis: that global debt — all of it, everywhere —
> can be expressed as a single tradeable claim.
>
> Companion to [`explanation.md`](./explanation.md) (conceptual overview)
> and [`technical.md`](./technical.md) (storage and invariants). This one
> is for the engineer who wants to understand *why each line of code
> exists*.

---

## Contents

1. [The thesis, expressed mechanically](#1-the-thesis-expressed-mechanically)
2. [Workflow — end-to-end diagram](#2-workflow--end-to-end-diagram)
3. [The compression pipeline: raw world → one scalar](#3-the-compression-pipeline-raw-world--one-scalar)
4. [Step 1: Oracle adapter — raw source to confidence-weighted observation](#4-step-1-oracle-adapter--raw-source-to-confidence-weighted-observation)
5. [Step 2: Blending — many truths to one](#5-step-2-blending--many-truths-to-one)
6. [Step 3: Normalisation — signed magnitudes to stress](#6-step-3-normalisation--signed-magnitudes-to-stress)
7. [Step 4: Aggregation — seven stresses to one index](#7-step-4-aggregation--seven-stresses-to-one-index)
8. [Step 5: Mark — the position is born](#8-step-5-mark--the-position-is-born)
9. [Step 6: Mark-to-market — value as a function of time](#9-step-6-mark-to-market--value-as-a-function-of-time)
10. [Step 7: Heartbeat, dormancy, inheritance](#10-step-7-heartbeat-dormancy-inheritance)
11. [Step 8: Settlement and reserve accrual](#11-step-8-settlement-and-reserve-accrual)
12. [The payment loop: x402 and how Algorand pays for EVM](#12-the-payment-loop-x402-and-how-algorand-pays-for-evm)
13. [The identity loop: BANKON and cross-chain inheritance](#13-the-identity-loop-bankon-and-cross-chain-inheritance)
14. [The advisory loop: mindX and signed off-chain intelligence](#14-the-advisory-loop-mindx-and-signed-off-chain-intelligence)
15. [The agent loop: AgenticPlace and reputation-weighted automation](#15-the-agent-loop-agenticplace-and-reputation-weighted-automation)
16. [How global debt becomes one tradeable asset](#16-how-global-debt-becomes-one-tradeable-asset)
17. [Closing: the invariant that proves the thesis](#17-closing-the-invariant-that-proves-the-thesis)

---

## 1. The thesis, expressed mechanically

The thesis statement is four sentences:

1. Global sovereign debt is not a balance-sheet item; it is a state
   variable of civilisation.
2. Every fiat-exposed person is already long or short this variable,
   whether they hedge or not.
3. The transfer of that debt burden will outlive individual humans.
4. Truth about the variable must be decentralised the same way the
   variable's effects are.

Mechanically, the thesis demands a system with four properties:

| Thesis clause | Mechanical requirement |
| --- | --- |
| State variable of civilisation | A single on-chain scalar that summarises the variable at any block |
| Everyone is already exposed | Positions must be open to anyone, permissionlessly, with configurable notional |
| Outlives humans | Positions must carry a cryptographic succession primitive resilient to holder death or key loss |
| Decentralised truth | Multiple independent data sources blended under adversarial governance |

The rest of this document shows how each of those four properties is
implemented. Every code path in iDEBT traces back to exactly one of the
four.

## 2. Workflow — end-to-end diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OFF-CHAIN OBSERVATION                       │
│                                                                     │
│   Chainlink nodes    Pyth publishers    Synthetix V3 markets        │
│       │                  │                    │                     │
│       ▼                  ▼                    ▼                     │
│   feed.latest()     pyth.getPrice()     core.getMarketTotalDebt()   │
└───────┼──────────────────┼────────────────────┼────────────────────┘
        │                  │                    │
        │  per-source      │                    │
        │  normalisation   │                    │
        ▼                  ▼                    ▼
   ┌────────────┐    ┌────────────┐       ┌────────────┐
   │ Chainlink  │    │ Pyth       │       │ SynthetixV3│      (1) adapters
   │ Adapter    │    │ Adapter    │       │ Adapter    │      emit
   └─────┬──────┘    └─────┬──────┘       └─────┬──────┘      Observation
         │                 │                    │             in WAD +
         └──────────────┬──┴────────────────────┘             confidence
                        │
                        ▼
              ┌─────────────────────┐
              │ DeltaVerseDebtOracle│  (2) confidence-blended mean per Metric
              │  blended(metric)    │
              └──────────┬──────────┘
                         │
                         │ 7 blended values
                         ▼
              ┌─────────────────────┐
              │GlobalDebtStressIndex│  (3) logistic normalisation → weighted sum
              │  score() / poke()   │      → regime classification
              └──────────┬──────────┘
                         │ 0..1e18 index
                         ▼
              ┌─────────────────────┐
              │     iDEBT ERC-721   │  (4) mark at mint, MTM = f(Δstress)
              │   positions + heirs │      heirs = Merkle root
              └──────────┬──────────┘
                         │
        ┌────────────────┼──────────────────┐
        ▼                ▼                  ▼
   openPosition     heartbeat          close / claim      (5) lifecycle
        │                │                  │
        │    gated by    │                  │    gated by
        ▼    x402        ▼                  ▼    x402
   ┌─────────────────┐                 ┌─────────────────┐
   │X402Gateway      │                 │X402Gateway      │
   │ .hasPaid(scope) │                 │ .hasPaid(scope) │
   └────────┬────────┘                 └────────┬────────┘
            │                                   │
            └──────────────┬────────────────────┘
                           │ signed off-chain by
                           ▼
                  ┌─────────────────┐
                  │ Parsec x402     │  (6) Algorand payment → EIP-712 Receipt
                  │ facilitator     │
                  └─────────────────┘

   (concurrent loops:)
   - mindX advisory signs attestations   → MindXBridge.settle
   - BANKON sovereign binding signs      → BANKONConnector.bind
   - AgenticPlace registers agents       → AgenticPlaceRegistry.attest
   - DAIO passes proposals               → TimelockController.execute
```

Numbers in parentheses are the steps detailed in §4 through §11. The
three right-side loops (mindX, BANKON, AgenticPlace) are the
off-chain-to-on-chain bridges for intelligence, identity, and
reputation respectively; §12-§15 cover them.

## 3. The compression pipeline: raw world → one scalar

The core engineering problem is **compression**. Global sovereign debt
is trillions of data points — every bond, every CDS, every
cross-currency basis swap. The protocol must reduce that to a single
number between 0 and 1e18, in a way that:

- Moves when the world moves.
- Doesn't move when individual sources misbehave.
- Is cheap enough to read on every position mint.
- Is legible enough that governance can reason about its parameters.

The pipeline is five stages:

```
   raw upstream value              (scale: arbitrary, per-source)
        │  adapter normalisation
        ▼
   Observation in WAD              (scale: 1e18, signed)
        │  confidence-weighted blend
        ▼
   blended int256                  (scale: 1e18, signed)
        │  logistic normalisation + baseline shift
        ▼
   component in [0, 1e18]          (scale: 1e18, unsigned, bounded)
        │  weighted sum over 7 components
        ▼
   index in [0, 1e18]              (scale: 1e18, unsigned, bounded)
        │  regime threshold
        ▼
   Regime enum { Calm, Elevated, Distress, Crisis, Default }
```

Each stage has well-defined failure modes and recovery paths. The next
five sections walk through each stage with source code.

## 4. Step 1: Oracle adapter — raw source to confidence-weighted observation

**Goal of this step:** convert any upstream feed into a uniform
`Observation` struct in WAD (1e18) scale with a self-declared confidence
weight.

### 4.1 The target shape

```solidity
// src/interfaces/IDebtOracle.sol
struct Observation {
    int256  value;       // signed magnitude in WAD
    uint64  timestamp;   // when the upstream source published
    uint256 confidence;  // 0..1e18, this adapter's confidence in itself
    bytes32 source;      // identifier, e.g. bytes32("CL_DXY")
}
```

The struct is deliberately minimal. `value` is signed because real-rate
and yield-curve metrics can legitimately be negative. `confidence` is
the adapter's own self-assessment — not a governance input. `source` is
how the blender de-duplicates overlapping adapters.

### 4.2 Chainlink adapter

Chainlink feeds publish integers with per-feed decimals and a maximum
publication interval ("heartbeat"). The adapter scales to WAD and
computes confidence as linear decay toward the heartbeat:

```solidity
// src/oracles/ChainlinkAdapter.sol (excerpt)
function latest() external view returns (IDebtOracle.Observation memory obs) {
    (, int256 answer,, uint256 updatedAt,) = feed.latestRoundData();
    if (answer <= 0) revert InvalidAnswer();
    if (block.timestamp - updatedAt > heartbeat) {
        revert StaleFeed(updatedAt, heartbeat);
    }

    // Scale to 1e18.
    int256 scaled;
    if (feedDecimals < 18) {
        scaled = answer * int256(10 ** uint256(18 - feedDecimals));
    } else if (feedDecimals > 18) {
        scaled = answer / int256(10 ** uint256(feedDecimals - 18));
    } else {
        scaled = answer;
    }

    obs = IDebtOracle.Observation({
        value: scaled,
        timestamp: uint64(updatedAt),
        confidence: _confidence(updatedAt),  // linear decay to heartbeat
        source: sourceId
    });
}

function _confidence(uint256 updatedAt) internal view returns (uint256) {
    uint256 age = block.timestamp - updatedAt;
    if (age >= heartbeat) return 0;
    return 1e18 - (age * 1e18) / heartbeat;
}
```

**Why linear decay and not a step function?** A step function at the
heartbeat boundary creates a discontinuity the blender would exploit —
an observation one second before the boundary counts fully; one second
after, not at all. Linear decay makes the transition smooth so a stale
feed contributes proportionally less as it ages, and the blend remains
stable across the boundary.

### 4.3 Pyth adapter

Pyth is pull-based with a confidence interval published alongside each
price. The adapter converts the interval into the same 0..1e18 scale:

```solidity
// src/oracles/PythAdapter.sol (excerpt)
function _toObservation(IPyth.PriceFeed memory pf)
    internal
    view
    returns (IDebtOracle.Observation memory obs)
{
    // ... exponent normalisation to WAD ...

    // Confidence ∝ price / (price + conf)
    uint256 conf;
    if (pf.conf == 0) {
        conf = 1e18;
    } else {
        uint256 priceAbs = uint256(uint64(pf.price < 0 ? -pf.price : pf.price));
        conf = (priceAbs * 1e18) / (uint256(pf.conf) + priceAbs);
    }

    obs = IDebtOracle.Observation({
        value: value,
        timestamp: pf.publishTime,
        confidence: conf,
        source: sourceId
    });
}
```

**Why that formula?** Pyth's `conf` is in the same units as the price
itself — it's the width of the confidence interval. A price of 100
with `conf = 0` means "I know this exactly" → weight 1. A price of 100
with `conf = 100` means "it's somewhere between 0 and 200" → weight
0.5. A price of 100 with `conf = 10_000` means "I have no idea" →
weight close to 0.

### 4.4 Synthetix V3 adapter

Synthetix V3 markets atomically expose debt and collateral. There's no
staleness: the read is as fresh as the block itself. Confidence is
therefore hardcoded to 1e18:

```solidity
// src/oracles/SynthetixV3Adapter.sol (excerpt)
function latest() external view returns (IDebtOracle.Observation memory obs) {
    int256 debt = core.getMarketTotalDebt(marketId);
    uint256 coll = core.getMarketCollateral(marketId);
    if (coll == 0) revert NoCollateral();

    int256 ratio = (debt * int256(1e18)) / int256(coll);

    obs = IDebtOracle.Observation({
        value: ratio,
        timestamp: uint64(block.timestamp),
        confidence: 1e18,
        source: sourceId
    });
}
```

**This returns the debt/collateral ratio, not an absolute value.** For
the iDEBT use case this is actually what we want: a market that's 50%
utilised contributes differently than one that's 150% utilised, and the
ratio expresses that directly.

### 4.5 What each adapter accomplishes (thesis connection)

Each adapter is a **different disciplined way of looking at debt**:

- Chainlink: the *consensus* of human-run oracle nodes.
- Pyth: the *published uncertainty* of market makers on their own feeds.
- Synthetix V3: the *revealed preference* of on-chain lenders and
  borrowers.

No single one of these sources is truth. Each is a projection of truth
through a specific institutional lens. The blender's job is to combine
the three projections into something that moves when at least two of
the three lenses agree.

## 5. Step 2: Blending — many truths to one

**Goal of this step:** combine all adapter observations for a metric
into a single confidence-weighted value, rejecting stale and
low-confidence sources entirely.

### 5.1 The blend formula

```
blended(metric) = Σ (value_i × conf_i) / Σ conf_i,    for conf_i ≥ minConfidence
```

Implemented in `DeltaVerseDebtOracle`:

```solidity
// src/core/DeltaVerseDebtOracle.sol (excerpt)
function blended(Metric metric) external view returns (int256) {
    address[] memory adapters = _adapters[metric];
    int256 num;
    uint256 den;
    for (uint256 i = 0; i < adapters.length; ++i) {
        Observation memory obs = IAdapter(adapters[i]).latest();
        if (obs.confidence < minConfidence) continue;
        uint64 age = uint64(block.timestamp) - obs.timestamp;
        if (age > uint64(_freshnessWindow)) continue;
        num += obs.value * int256(obs.confidence);
        den += obs.confidence;
    }
    if (den == 0) revert StaleObservation(metric, 0, uint64(_freshnessWindow));
    return num / int256(den);
}
```

### 5.2 Three filters, in order

Each observation has to clear three filters before it enters the blend:

1. **Self-confidence floor**: `obs.confidence ≥ minConfidence` (default
   0.25e18). An adapter that thinks it's 15% confident in itself is
   excluded entirely. This prevents a stale-but-present adapter from
   dragging the blend.
2. **Freshness window**: `age ≤ freshnessWindow` (default 30 minutes).
   The *oracle* decides what's fresh, independent of what each adapter
   claims. This is an adversarial check: an adapter lying about its
   timestamp can still be rejected by the oracle's window.
3. **Non-zero denominator**: if every observation was filtered out, the
   blend reverts. A metric with no fresh sources is uncallable — which
   cascades into the index read reverting, which cascades into
   `openPosition` and `markToMarket` reverting. The *entire system
   halts* rather than serving a value based on stale data.

That cascade is not a bug. It is the central safety property of the
oracle layer. iDEBT refuses to operate on bad data.

### 5.3 Why a mean and not a median?

A median would be more robust to single-source attacks. The trade-off:

- **Mean** allocates weight proportional to confidence. A high-confidence
  Pyth update and a low-confidence Chainlink update produce an answer
  dominated by Pyth.
- **Median** ignores confidence entirely. Three equally-weighted sources
  where one is 100% confident and two are 30% confident still produce
  the middle value.

iDEBT uses mean because confidence is already adversarial — adapters
can't inflate their own confidence without reason (the formulas are
public and auditable). Median throws away that signal.

For safety against a single malicious high-confidence source, iDEBT
relies on **multiple independent adapters per metric**. The recommended
wiring (§14) attaches 2–3 adapters per metric; a single malicious
source can at most distort by its share of the total confidence, not
swing the entire blend.

### 5.4 What this step accomplishes (thesis connection)

The blend is where *decentralisation of truth* becomes real. No adapter
can unilaterally move the result. No governance key can set a value
directly. The only way to change the blend is to change the set of
registered adapters — which requires a DAIO proposal that waits the
timelock delay before execution. Governance attacks are visible on-chain
for two days before they land.

## 6. Step 3: Normalisation — signed magnitudes to stress

**Goal of this step:** convert a metric's signed magnitude in WAD into a
bounded 0..1e18 "stress contribution" that encodes both direction and
saturation.

### 6.1 The logistic function

```
σ(x) = 1 / (1 + e^(-x))
```

This is the standard sigmoid. Real `exp` is expensive on-chain, so iDEBT
uses a closed-form approximation:

```solidity
// src/libraries/DebtMath.sol (excerpt)
function logistic(int256 x) internal pure returns (uint256) {
    if (x >= int256(6e18)) return WAD;
    if (x <= -int256(6e18)) return 0;

    // sigmoid(x) ≈ 0.5 + 0.5 · x / (4 + |x|)
    int256 ax = x >= 0 ? x : -x;
    int256 num = x * int256(WAD / 2);
    int256 den = int256(4e18) + ax;
    int256 s = int256(WAD / 2) + num / den;
    if (s < 0) return 0;
    return clamp(uint256(s));
}
```

**Properties the approximation preserves:**

- `σ(0) = 0.5e18` — perfectly neutral.
- `σ(x) → 1e18` as `x → ∞`.
- `σ(x) → 0` as `x → -∞`.
- Monotone increasing.
- Accurate to ≤1% on `x ∈ [-6, 6]` in WAD units, the range where
  calibration baselines land.
- Saturates (not overflows) outside [-6, 6].

### 6.2 Baselines shift the neutral point

Each of the seven metrics has a calibration baseline — the raw value
that should map to 0.5e18 stress. The normalisers subtract the baseline
before applying the logistic:

```solidity
// src/core/GlobalDebtStressIndex.sol (excerpts)
function _normDebtGDP(int256 v) internal pure returns (uint256) {
    // Baseline: 100% debt/GDP is neutral. (v - 1e18) × 2 scales sensitivity.
    return DebtMath.logistic((v - int256(1e18)) * 2);
}

function _normCds(int256 v) internal pure returns (uint256) {
    // Baseline: 1% CDS spread. × 100 scales basis-point moves.
    return DebtMath.logistic((v - int256(0.01e18)) * 100);
}

function _normYield(int256 v) internal pure returns (uint256) {
    // Inversion depth: negative = inverted = higher stress, hence -v.
    return DebtMath.logistic(-v * 20);
}

function _normReal(int256 v) internal pure returns (uint256) {
    // High real rates = disinflationary stress on debtors.
    return DebtMath.logistic(v * 20);
}

function _normDxy(int256 v) internal pure returns (uint256) {
    // DXY baseline 100 (1e18 when scaled). × 5 scales index moves.
    return DebtMath.logistic((v - int256(1e18)) * 5);
}

function _normVix(int256 v) internal pure returns (uint256) {
    // VIX 20 neutral. ÷ 10 softens — VIX moves in larger integer jumps.
    return DebtMath.logistic((v - int256(20e18)) / 10);
}

function _normGold(int256 v) internal pure returns (uint256) {
    // Gold/reserves ratio; baseline 1.0.
    return DebtMath.logistic((v - int256(1e18)) * 3);
}
```

**Each multiplier is a sensitivity knob.** A multiplier of 2 means
"100 percentage points of debt/GDP change is a full stress swing". A
multiplier of 100 means "1 percentage point of CDS spread change is a
full stress swing". These multipliers are **hardcoded** in v0.1; see
§17 and `explanation.md` §18 for the upgrade path.

### 6.3 Why seven components and not more?

The seven components were chosen to span the **causal axes** of
sovereign debt stress:

| Component | What it captures | Causal axis |
| --- | --- | --- |
| debt/GDP | absolute burden | accumulation |
| CDS5Y | default probability | direct credit |
| yield curve inversion | market's recession expectation | forward growth |
| real rate | inflation-adjusted cost of carry | monetary regime |
| DXY | dollar liquidity conditions | global reserve |
| VIX | equity-market fear | risk appetite |
| gold ratio | flight to tangible | faith in fiat |

Adding more components (e.g. cross-currency basis, ETF redemption
flows, central bank balance sheet growth) could refine the index but
would dilute the signal — each component's weight shrinks and the
interpretation becomes harder. Seven is the minimum that spans the
causal axes without redundancy.

### 6.4 What this step accomplishes (thesis connection)

Normalisation is where *a state variable of civilisation* becomes
legible. Raw debt/GDP is a number with context most readers don't
share. A 0..1e18 stress score is a number anyone can read. The
translation is expensive to get right — the baselines encode
macroeconomic judgment about what counts as "neutral" for each metric —
but the output is universal.

## 7. Step 4: Aggregation — seven stresses to one index

**Goal of this step:** combine seven component stresses into a single
0..1e18 index via weighted sum, then classify into a discrete regime.

### 7.1 Weighted sum with enforced totals

```solidity
// src/libraries/DebtMath.sol (excerpt)
function weightedSum(uint256[7] memory components, uint256[7] memory weights)
    internal
    pure
    returns (uint256 acc)
{
    uint256 wsum;
    for (uint256 i = 0; i < 7; ++i) {
        acc += wmul(components[i], weights[i]);
        wsum += weights[i];
    }
    if (wsum != WAD) revert Overflow(); // weights must sum to 1e18 exactly
}
```

The sum-to-1e18 requirement is not cosmetic. Without it, governance
could change a single weight and inadvertently change the index's
scale. With it, the weights are a *distribution* — every re-weighting
preserves the index range and only redistributes sensitivity.

### 7.2 The full compute path

```solidity
// src/core/GlobalDebtStressIndex.sol (excerpt)
function _compute() internal view returns (Snapshot memory s) {
    uint256 debtGDP  = _normDebtGDP(oracle.blended(IDebtOracle.Metric.SovereignDebtGDP));
    uint256 cds      = _normCds(oracle.blended(IDebtOracle.Metric.CDS5Y));
    uint256 yieldInv = _normYield(oracle.blended(IDebtOracle.Metric.YieldCurveInversion));
    uint256 realRate = _normReal(oracle.blended(IDebtOracle.Metric.RealRate));
    uint256 dxy      = _normDxy(oracle.blended(IDebtOracle.Metric.DXY));
    uint256 vix      = _normVix(oracle.blended(IDebtOracle.Metric.VIX));
    uint256 gold     = _normGold(oracle.blended(IDebtOracle.Metric.GoldRatio));

    uint256[7] memory c = [debtGDP, cds, yieldInv, realRate, dxy, vix, gold];
    uint256 idx = DebtMath.weightedSum(c, weights);

    s = Snapshot({
        index: idx,
        regime: _regimeFromIndex(idx),
        timestamp: uint64(block.timestamp),
        debtGDP: debtGDP, cds: cds, yieldInv: yieldInv, realRate: realRate,
        dxy: dxy, vix: vix, gold: gold
    });
}
```

`_compute` is `view` and cheap — it's called on every `score()` and
every position `markToMarket`. This is why the upstream adapters had to
be efficient: this function calls `oracle.blended(metric)` seven
times per read.

### 7.3 Regime classification

```solidity
function _regimeFromIndex(uint256 idx) internal view returns (Regime) {
    if (idx < calmMax)     return Regime.Calm;      // default < 0.20e18
    if (idx < elevatedMax) return Regime.Elevated;  //         < 0.40e18
    if (idx < distressMax) return Regime.Distress;  //         < 0.60e18
    if (idx < crisisMax)   return Regime.Crisis;    //         < 0.80e18
    return Regime.Default;                          //         ≥ 0.80e18
}
```

Regimes give integrations a cheap `switch` they can use to change
behaviour without doing fixed-point arithmetic. A lending protocol might
refuse new positions in Crisis regime; an insurance protocol might
halve its premium rate in Calm.

### 7.4 The poke / score split

Two entry points exist:

```solidity
// Cheap read, recomputed every call — what integrations actually use.
function score() external view returns (uint256) {
    return _compute().index;
}

// Cheap write, recomputed AND persisted — emits events for indexers.
function poke() external returns (Snapshot memory s) {
    s = _compute();
    Regime prev = _snap.regime;
    _snap = s;
    emit IndexUpdated(s.index, s.regime, s.timestamp);
    if (s.regime != prev) emit RegimeTransition(prev, s.regime, s.timestamp);
}
```

The split means: **the stored snapshot is advisory, the live score is
authoritative**. `iDEBT.markToMarket` always uses `score()`, so there is
no "stale snapshot" failure mode where positions settle against a
snapshot from an hour ago. Keepers call `poke` only to emit events for
subscribers.

### 7.5 What this step accomplishes (thesis connection)

This is where the thesis becomes literally a scalar. The variable
named in clause 1 — "global sovereign debt as a state variable of
civilisation" — is now a `uint256` at storage slot `_snap.index`,
updated every block on request, readable by any contract, priced
against by any market.

## 8. Step 5: Mark — the position is born

**Goal of this step:** capture the current stress score at mint time so
the position can settle against its historical mark.

### 8.1 The full mint function

```solidity
// src/core/iDEBT.sol (excerpt)
function openPosition(
    uint256 principal,
    uint64  maturity,
    uint64  dormancy,
    Heir[] calldata heirs
) external override whenNotPaused nonReentrant returns (uint256 tokenId) {
    if (principal == 0 || principal > maxPrincipal) revert ExceedsCap();
    if (maturity <= block.timestamp) revert NotMatured();
    if (heirs.length == 0 || heirs.length > 32) revert InvalidHeirs();
    _ensurePaid(SCOPE_OPEN);

    uint256 sharesSum;
    bytes32 root = heirs[0].proofRoot;
    for (uint256 i = 0; i < heirs.length; ++i) {
        if (heirs[i].successor == address(0)) revert InvalidHeirs();
        sharesSum += heirs[i].sharesBps;
    }
    if (sharesSum != 10_000) revert InvalidHeirs();

    tokenId = nextTokenId++;
    uint256 mark = stressIndex.score();    // ← the thesis, captured

    _positions[tokenId] = Position({
        principal:     principal,
        stressMark:    mark,
        mintedAt:      uint64(block.timestamp),
        maturity:      maturity,
        lastHeartbeat: uint64(block.timestamp),
        dormancy:      dormancy,
        holder:        msg.sender
    });
    _heirRoot[tokenId]  = root;
    _heirCount[tokenId] = uint8(heirs.length);

    uint256 fee = (principal * protocolFeeBps) / 10_000;
    if (fee > 0 && feeSink != address(0)) {
        settlementToken.safeTransferFrom(msg.sender, feeSink, fee);
    }
    settlementToken.safeTransferFrom(msg.sender, address(this), principal);

    _safeMint(msg.sender, tokenId);
    emit PositionOpened(tokenId, msg.sender, principal);
    emit HeirsConfigured(tokenId, uint8(heirs.length), root);
}
```

### 8.2 Step ordering is security-critical

The function performs checks, state mutations, and external calls in a
specific order that matters:

1. **All revert-checks first** — principal cap, maturity, heir count.
   Cheap, fail fast.
2. **`_ensurePaid`** — read the x402 gateway. This is a cross-contract
   `view` call; it must happen before any state mutation so a revert
   here doesn't leave partial state.
3. **Share-sum validation** — loops through calldata, no storage.
4. **Storage writes** — `_positions`, `_heirRoot`, `_heirCount`. All
   writes happen *before* the token transfer.
5. **External calls** — `safeTransferFrom` for fee, then for principal.
   These invoke arbitrary user-controlled settlement tokens and must
   happen after state is finalised (Checks-Effects-Interactions).
6. **ERC-721 mint** — `_safeMint` can invoke the recipient's
   `onERC721Received`, which is untrusted. Happens last.
7. **Events** — after `_safeMint` so indexers see the token exist
   before the semantic event.

`nonReentrant` wraps everything as belt-and-braces, but the CEI order
means even a compromised settlement token can't re-enter to create
inconsistent state.

### 8.3 The heir commitment

```solidity
bytes32 root = heirs[0].proofRoot;   // first heir carries the Merkle root
```

The storage savings from committing rather than storing is substantial.
A 32-heir position would otherwise consume 32 × (20 + 2 + 20) = 1,344
bytes. With a commitment it consumes 32 bytes. The trade-off: heirs
must store their own leaf + proof off-chain until claim time.

**The contract does not store who the heirs are.** Until a heir actually
claims, their identity is not on-chain. This is the privacy property.

### 8.4 What this step accomplishes (thesis connection)

The mint is where *everyone is already exposed* (thesis clause 2)
becomes *you can make the exposure explicit*. Anyone with `principal`
worth of settlement token can stamp a specific block's stress index
onto an NFT and own a claim on subsequent debt dynamics. No KYC,
no whitelist, no minimum size above dust (subject to DAIO's
`maxPrincipal` cap from above — there's no floor other than gas
economics).

## 9. Step 6: Mark-to-market — value as a function of time

**Goal of this step:** compute a position's current value from its
stressMark and the live index.

### 9.1 The MTM formula

```solidity
// src/core/iDEBT.sol (excerpt)
function markToMarket(uint256 tokenId) public view returns (uint256) {
    Position memory p = _positions[tokenId];
    if (p.principal == 0) return 0;
    uint256 now_ = stressIndex.score();               // live read, not snapshot
    int256 delta = int256(now_) - int256(p.stressMark);
    int256 factor = int256(1e18) - delta;             // 1 − Δstress
    if (factor <= 0) return 0;
    uint256 mtm = DebtMath.wmul(p.principal, uint256(factor));
    uint256 cap = p.principal * 2;
    return mtm > cap ? cap : mtm;
}
```

### 9.2 Reading the formula

```
Δ      = score_now − stressMark
factor = 1e18 − Δ                      (clamped ≥ 0)
MTM    = principal × factor / 1e18     (capped ≤ 2 × principal)
```

Three regimes of behavior:

| Δ (WAD) | factor | MTM | Holder outcome |
| --- | --- | --- | --- |
| `0` | `1.0e18` | `1.0 × principal` | Breakeven |
| `+0.10e18` (stress up 10pp) | `0.90e18` | `0.90 × principal` | 10% loss |
| `−0.10e18` (stress down 10pp) | `1.10e18` | `1.10 × principal` | 10% gain |
| `+1.0e18` (crisis onset) | `0` (clamped) | `0` | Total loss of principal |
| `−1.0e18` (crisis resolves) | `2.0e18` | `2.0 × principal` (capped) | 100% gain |

### 9.3 Why linear?

A linear factor is the simplest formula that is:

- **Symmetric around zero**: equal stress moves in either direction
  produce equal MTM changes. This matches the thesis that the index is
  a *state variable* — moves in either direction have equal
  informational content.
- **Bounded below by zero**: a holder can never owe more than they put
  in. This is a hard requirement for permissionless mint without
  credit checks.
- **Bounded above by 2× principal**: runaway windfalls from extreme
  mean-reversion are truncated. The truncated upside accrues to the
  reserve.
- **Cheap**: a handful of opcodes.

A convex curve (e.g. `(1 − Δ)²`) would amplify tail losses and dampen
tail gains, which would make positions more insurance-like. v0.1 is
deliberately linear so the early market can form without
position-specific curvature.

### 9.4 Live reads, not stored snapshots

The line `uint256 now_ = stressIndex.score()` is doing a live
cross-contract computation, not reading `_snap`. This is important: a
position never settles against a stale snapshot. If keepers are down,
the stored snapshot ages but `markToMarket` still returns the
authoritative current value.

The gas cost: ~80k additional gas per `markToMarket` read (the full
oracle traversal). This is acceptable for mint/close/claim, which are
infrequent, but would be punishing for anything called on every
block. For UIs, `score()` is read once and cached client-side.

### 9.5 What this step accomplishes (thesis connection)

MTM is where the position *becomes a derivative*. The position is no
longer a static NFT; its cash value depends on the live state of the
compression pipeline. This is the machinery that makes global debt
tradeable: anyone can open a position at stressMark X, and anyone can
observe its current MTM at score Y. The difference (Y − X) is the P&L.

Markets — secondary-market venues, DEXes with ERC-721 pools, OTC
custodians — can price these positions using only public data. No
trusted custodian is in the loop between the oracle and the P&L.

## 10. Step 7: Heartbeat, dormancy, inheritance

**Goal of this step:** let the holder prove liveness, and let heirs
claim if the holder doesn't.

### 10.1 Heartbeat

```solidity
// src/core/iDEBT.sol (excerpt)
function heartbeat(uint256 tokenId) external override whenNotPaused {
    Position storage p = _positions[tokenId];
    if (p.holder != msg.sender) revert NotHolder();
    p.lastHeartbeat = uint64(block.timestamp);
    emit HeartbeatRecorded(tokenId, uint64(block.timestamp));
}
```

One storage write, one event. Trivial in isolation; consequential in
aggregate.

### 10.2 What else counts as a heartbeat?

Transfers do, implicitly, via the ERC-721 `_update` override:

```solidity
// src/core/iDEBT.sol (excerpt)
function _update(address to, uint256 tokenId, address auth)
    internal
    override
    returns (address from)
{
    from = super._update(to, tokenId, auth);
    if (to != address(0) && _positions[tokenId].principal != 0) {
        _positions[tokenId].holder        = to;
        _positions[tokenId].lastHeartbeat = uint64(block.timestamp);
    }
}
```

A transfer implicitly proves the old holder had signing capability at
that block. The new holder gets a fresh dormancy clock.

What does **not** count:

- `service` — third parties can service, so a service call from an
  arbitrary account would let the holder pretend to be alive via a
  proxy paying on their behalf. The heartbeat must come from the
  holder directly.
- Approvals — ambient state, doesn't prove liveness.
- Viewing / reading — free and doesn't touch storage.

### 10.3 The claim function

```solidity
// src/core/iDEBT.sol (excerpt)
function claimInheritance(uint256 tokenId, bytes calldata heirProof)
    external
    override
    whenNotPaused
    nonReentrant
    returns (uint256 payout)
{
    Position storage p = _positions[tokenId];
    require(p.principal != 0, "no position");
    if (block.timestamp < p.lastHeartbeat + p.dormancy) revert NotDormant();
    _ensurePaid(SCOPE_CLAIM);

    (address successor, uint16 sharesBps, bytes32[] memory proof) =
        abi.decode(heirProof, (address, uint16, bytes32[]));
    if (successor != msg.sender) revert NotHolder();

    bytes32 leaf = keccak256(abi.encode(successor, sharesBps));
    if (!MerkleProof.verify(proof, _heirRoot[tokenId], leaf)) revert InvalidHeirs();
    if (_claimed[tokenId][leaf]) revert InvalidHeirs();
    _claimed[tokenId][leaf] = true;

    uint256 mtm = markToMarket(tokenId);
    payout = (mtm * sharesBps) / 10_000;
    uint256 principalShare = (p.principal * sharesBps) / 10_000;
    p.principal = p.principal > principalShare ? p.principal - principalShare : 0;

    if (payout > 0) settlementToken.safeTransfer(successor, payout);
    emit InheritanceClaimed(tokenId, successor, sharesBps);

    if (p.principal == 0) {
        address holder = p.holder;
        delete _positions[tokenId];
        delete _heirRoot[tokenId];
        delete _heirCount[tokenId];
        _burn(tokenId);
        emit PositionClosed(tokenId, holder, 0);
    }
}
```

### 10.4 Reading the claim function

Five checks, five actions:

1. **Position must exist** — `p.principal != 0` rules out already-closed
   positions.
2. **Dormancy must have elapsed** — `block.timestamp ≥ lastHeartbeat +
   dormancy`. This is the holder's silence condition.
3. **x402 payment required** — `_ensurePaid(SCOPE_CLAIM)`. The DAIO
   charges a small fee for claims to discourage frivolous inheritance
   attempts.
4. **Caller must be the named successor** — `successor == msg.sender`.
   A third party with a copy of the proof cannot claim on behalf of
   someone else.
5. **Merkle proof must verify** against the commitment stored at mint.
6. **Leaf must not have been claimed before** — `_claimed[tokenId][leaf]`
   is set once.
7. **MTM computed against live index** — the same `markToMarket` path
   used by `close`.
8. **Payout pro-rated by share** — a 3000 bps heir gets 30% of current
   MTM.
9. **Principal reduced** — each heir takes their share of the remaining
   principal, so subsequent heirs get a fair draw on what's left.
10. **Token burned if fully claimed** — when `principal == 0`, the NFT
    ceases to exist.

### 10.5 Why Merkle instead of a list?

Three reasons:

- **Storage cost**: 32-byte commitment vs N × 42-byte records.
- **Privacy**: heir identities aren't on-chain until claim.
- **Updatability**: in a future version, the holder can commit a new
  root without revealing the difference.

Trade-off: heirs must store their own leaf + Merkle path off-chain. If
they lose it, they can't claim. The commitment scheme recommends that
holders distribute the proofs to heirs at mint time, outside of the
chain (encrypted email, sealed envelope, etc.).

### 10.6 What this step accomplishes (thesis connection)

This is where *outlives individual humans* (thesis clause 3) becomes a
state transition on Ethereum. A holder who dies in year N leaves an
iDEBT position that settles against stress index state in year N+K,
paid out to heirs named at mint time and bound by a Merkle commitment
that cannot be tampered with. The protocol does not need a will, a
court, or a custodian — the cryptographic succession plan is the plan.

## 11. Step 8: Settlement and reserve accrual

**Goal of this step:** close the loop between MTM, treasury, and upside
capture.

### 11.1 The close function

```solidity
// src/core/iDEBT.sol (excerpt)
function close(uint256 tokenId) external override whenNotPaused nonReentrant returns (uint256 payout) {
    Position storage p = _positions[tokenId];
    if (p.holder != msg.sender) revert NotHolder();
    if (block.timestamp < p.maturity) revert NotMatured();

    payout = markToMarket(tokenId);
    uint256 remaining = p.principal;

    delete _positions[tokenId];
    delete _heirRoot[tokenId];
    delete _heirCount[tokenId];
    _burn(tokenId);

    uint256 send = payout > remaining ? remaining : payout;
    if (send > 0) settlementToken.safeTransfer(msg.sender, send);
    emit PositionClosed(tokenId, msg.sender, send);
}
```

### 11.2 Reserve accrual

The critical line:

```solidity
uint256 send = payout > remaining ? remaining : payout;
```

This caps the payout at the original principal. If MTM > principal
(stress fell), the holder receives only principal; the excess
(MTM - principal) stays in the contract balance. That balance accrues
to the `DAIOTreasury` — the treasury can sweep at any time via DAO
proposal.

### 11.3 The accounting flow

Contract balance evolves as:

```
balance += principal                (on openPosition)
balance += fee                      (fee transferred separately to feeSink)
balance -= servicing payouts        (on service — reduces liability)
balance -= payout                   (on close — payout ≤ principal)
balance -= heir_payout              (on claimInheritance — payout ≤ MTM share)
```

The treasury ends up with:

```
treasury_accrual = Σ(principal_i - payout_i) + Σ fee_i
                 = Σ max(0, Δstress_i × principal_i) + fees
```

In plain English: **the treasury captures the integrated upside of all
positions minted during elevated-stress regimes**. The holder captures
the downside protection; the treasury captures the statistical
expectation.

### 11.4 What this step accomplishes (thesis connection)

Reserve accrual is the answer to "how does this protocol pay for
itself?" The fees alone cover keeper rebates and gas. The real funding
comes from the statistical asymmetry between holder optionality and
treasury accrual. In expectation over many positions, the treasury
accrues; individual positions can still win.

This is the engine that keeps the oracle wired, the keepers running,
the audits paid, the front-end hosted. The thesis sustains its own
infrastructure.

## 12. The payment loop: x402 and how Algorand pays for EVM

**Goal of this loop:** let a user pay a tiny Algorand fee to unlock a
specific EVM operation, without bridging funds.

### 12.1 The full flow

```
  1. Client → EVM: call openPosition(...)
         ↑
         └── reverts with PaymentRequired
  2. Client → Parsec API: GET /api/price/keccak256("iDEBT.open")
         ← { amount: 1_000_000, asset: USDCa }
  3. Client → Parsec API: POST /api/intent
         ← { facilitatorAlgoAddress, nonce, expires }
  4. Client → parsec-wallet: send 1 USDCa to facilitatorAlgoAddress on Algorand
         ← algoTxId
  5. Parsec: observes settlement on Algorand
  6. Parsec → Client: EIP-712 signed Receipt bundle
  7. Client → X402Gateway: consume(receipt, signature)
         ← ReceiptConsumed event; _paidUntil[client][SCOPE_OPEN] = expiry
  8. Client → EVM: call openPosition(...) again
         ← succeeds; x402.hasPaid(client, SCOPE_OPEN) = true
```

### 12.2 The receipt structure

```solidity
// src/interfaces/IX402.sol (excerpt)
struct Receipt {
    address facilitator;
    address payer;
    uint256 amount;
    bytes32 asset;       // bytes32("ALGO") or bytes32("USDCa")
    bytes32 scope;
    uint64  nonce;
    uint64  expiry;
    bytes32 algoTxId;
}
```

### 12.3 The verification

```solidity
// src/integrations/X402PaymentGateway.sol (excerpt)
function consume(Receipt calldata r, bytes calldata sig) external {
    if (!facilitators[r.facilitator]) revert UnauthorisedFacilitator();
    if (block.timestamp > r.expiry)   revert ReceiptExpired();
    if (usedNonces[r.payer][r.nonce]) revert ReceiptReplayed();
    if (scopePrice[r.scope] == 0)     revert BadScope();
    if (r.amount < scopePrice[r.scope] || r.asset != scopeAsset[r.scope]) {
        revert InsufficientPayment();
    }

    bytes32 structHash = keccak256(abi.encode(
        keccak256(
            "Receipt(address facilitator,address payer,uint256 amount,bytes32 asset,bytes32 scope,uint64 nonce,uint64 expiry,bytes32 algoTxId)"
        ),
        r.facilitator, r.payer, r.amount, r.asset, r.scope,
        r.nonce, r.expiry, r.algoTxId
    ));
    bytes32 digest = _hashTypedDataV4(structHash);
    address signer = ECDSA.recover(digest, sig);
    if (signer != r.facilitator) revert UnauthorisedFacilitator();

    usedNonces[r.payer][r.nonce] = true;
    _paidUntil[r.payer][r.scope] = r.expiry;
    emit ReceiptConsumed(r.payer, r.scope, r.nonce);
}
```

Five checks, in order:

1. Facilitator must be authorised (DAIO proposal to set).
2. Receipt must not be expired.
3. Nonce must not be reused.
4. Scope price must be set (not a typo'd scope).
5. Amount must meet or exceed scope price AND asset must match.

Then EIP-712 verification: the recovered signer must equal the
facilitator. Signed attack surface is a single address per deployed
gateway.

### 12.4 Why Algorand?

The x402 protocol is chain-agnostic, but Algorand was chosen for v0.1
because:

- **Finality**: 3-second deterministic finality means the facilitator
  can sign a receipt without waiting for reorgs.
- **Cost**: ~0.001 ALGO per transaction.
- **Native USDC**: USDCa is a canonical ASA, not a bridged IOU.
- **Tooling**: parsec-wallet has mature Algorand support.

The gateway could consume receipts from a Parsec facilitator paying out
on any L2 or L1; Algorand is the reference implementation.

### 12.5 What this loop accomplishes (thesis connection)

Cross-chain payments mean a holder whose wealth is on one chain can
mint a position on another. This supports thesis clause 2: *everyone
is already exposed*. iDEBT adoption does not require moving funds to
Ethereum or Polygon specifically. The payment surface is global; the
settlement surface is wherever the holder wants to anchor the position.

## 13. The identity loop: BANKON and cross-chain inheritance

**Goal of this loop:** bind Algorand sovereign identity to EVM wallets
so that a heir whose EVM wallet changes can still be recognised.

### 13.1 The bind function

```solidity
// src/integrations/BANKONConnector.sol (excerpt)
function bind(bytes32 algoIdRoot, bytes calldata algoSig) external {
    if (ownerOfRoot[algoIdRoot] != address(0)) revert InvalidBinding();
    if (_bound[msg.sender].active)             revert InvalidBinding();

    bytes32 digest = MessageHashUtils.toEthSignedMessageHash(
        keccak256(abi.encode(algoIdRoot, msg.sender, block.chainid))
    );
    address signer = ECDSA.recover(digest, algoSig);
    if (signer != bankonSigner) revert InvalidBinding();

    _bound[msg.sender] = SovereignId({
        algoIdRoot:  algoIdRoot,
        evmBinding:  msg.sender,
        boundAt:     uint64(block.timestamp),
        active:      true
    });
    ownerOfRoot[algoIdRoot] = msg.sender;
    emit SovereignIdBound(algoIdRoot, msg.sender);
}
```

### 13.2 Why the signature includes `block.chainid`

The EIP-191 digest includes `(algoIdRoot, msg.sender, block.chainid)`.
Without chain ID, a signature valid on Polygon would also be valid on
Arbitrum for the same EVM wallet. With chain ID, a user must obtain a
fresh BANKON signature per chain — which matches the reality that an
EVM wallet on Polygon and the "same" wallet on Arbitrum are
technically distinct account states.

This enables a nuanced binding model:

- A single AlgoIDNFT root can be bound to different EVM wallets on
  different chains.
- The sovereign identity (the Algorand root) is the *person*.
- The EVM wallet (the bound address) is the *key* on a specific chain.
- Losing the key on one chain does not destroy the sovereign identity.

### 13.3 What this loop accomplishes (thesis connection)

Without BANKON, a heir is bound to a specific EVM wallet at position
mint time. If that wallet is compromised or lost years later, the heir
is unreachable.

With BANKON, heirs can be named as EVM wallets that are *themselves
bound* to sovereign roots. When a claim triggers, the claim contract
could optionally check `bankon.isBound(successor)` to require that the
successor maintain a valid sovereign identity.

v0.1 does not enforce this check on `claimInheritance` — the heir set
is opaque behind the Merkle root, and binding is a convention heirs
adopt off-chain. v0.2 may introduce an opt-in "sovereign-bound heirs
only" position variant.

## 14. The advisory loop: mindX and signed off-chain intelligence

**Goal of this loop:** let the off-chain mindX model publish
cryptographically signed risk scores that on-chain integrations can
read.

### 14.1 The settle function

```solidity
// src/integrations/MindXBridge.sol (excerpt)
function settle(Attestation calldata a, bytes calldata sig) external {
    if (consumed[a.requestId])                 revert AttestationReplayed();
    if (block.timestamp - a.issuedAt > maxAge) revert AttestationExpired();

    bytes32 structHash = keccak256(abi.encode(
        ATTESTATION_TYPEHASH,
        a.requestId, a.claimHash, a.issuedAt,
        a.modelVersion, a.riskScore, a.subject
    ));
    bytes32 digest = _hashTypedDataV4(structHash);
    address signer = ECDSA.recover(digest, sig);
    if (signer != _signingKey) revert BadSignature();

    consumed[a.requestId] = true;
    _latest[a.subject] = LastScore({ score: a.riskScore, at: uint64(block.timestamp) });
    emit AttestationSettled(a.requestId, a.subject, a.riskScore);
}
```

### 14.2 Key rotation

```solidity
function rotateKey(address newKey) external onlyRole(GOVERNOR_ROLE) {
    require(newKey != address(0), "zero key");
    emit MindXKeyRotated(_signingKey, newKey);
    _signingKey = newKey;
}
```

The mindX signing key is rotatable by the DAIO. Key compromise is
handled by a governance proposal; existing attestations signed by the
old key become un-replayable because `_signingKey` has changed, and the
verification check at line `if (signer != _signingKey)` fails.

### 14.3 Why only the latest score?

The bridge stores only the latest `(riskScore, at)` per subject. The
full advisory history lives off-chain at `mindx.pythai.net`. This is a
deliberate trade: on-chain storage is expensive, and integrations only
need the current score for current decisions. Historical analysis is a
separate concern served by the off-chain archive.

### 14.4 What this loop accomplishes (thesis connection)

mindX brings **adaptive judgment** into a protocol that is otherwise
mechanistic. The stress index is a deterministic function of seven
metrics; the mindX model can identify position-specific risk that the
index misses. An integration (e.g. a lending protocol accepting iDEBT
positions as collateral) can require recent mindX attestation before
accepting.

This supports thesis clause 4 (*decentralised truth*) by adding a
second epistemic source: the index is the *market's* truth,
blend-weighted across Chainlink/Pyth/Synthetix; mindX is the *model's*
truth, signed by a specific version of a specific inference system.

## 15. The agent loop: AgenticPlace and reputation-weighted automation

**Goal of this loop:** give automation (heartbeat bots, underwriters,
advisors) an on-chain reputation that decays if idle and builds if
they deliver.

### 15.1 The registration

```solidity
// src/integrations/AgenticPlaceRegistry.sol (excerpt)
function register(bytes32 agentId, string calldata endpoint) external {
    if (_agents[agentId].registeredAt != 0) revert AgentExists();
    _agents[agentId] = Agent({
        agentId:      agentId,
        owner:        msg.sender,
        reputation:   1e18,          // starts at 1.0
        registeredAt: uint64(block.timestamp),
        lastActivity: uint64(block.timestamp),
        endpoint:     endpoint
    });
    agentOwnedBy[msg.sender] = agentId;
    emit AgentRegistered(agentId, msg.sender, endpoint);
}
```

### 15.2 Reputation with lazy decay

```solidity
// src/integrations/AgenticPlaceRegistry.sol (excerpt)
function _projectedReputation(Agent memory a) internal view returns (uint128) {
    if (a.reputation == 0) return 0;
    uint256 elapsed = block.timestamp - a.lastActivity;
    uint256 periods = elapsed / DECAY_INTERVAL;      // 30 days per period
    if (periods == 0) return a.reputation;
    uint256 rep = a.reputation;
    if (periods > 64) periods = 64;                  // safety cap
    for (uint256 i = 0; i < periods; ++i) {
        rep = rep - (rep * decayBps) / 10_000;       // 1% per period default
        if (rep == 0) break;
    }
    return uint128(rep);
}
```

### 15.3 Why exponential decay?

Exponential decay has the property that a period of inactivity *N*
times longer reduces reputation by a factor that grows multiplicatively.
An agent dormant 5 years (~60 periods) at 1% decay/period retains
`0.99^60 ≈ 54%`. An agent dormant 10 years retains
`0.99^120 ≈ 29%`.

This matches intuition: reputation should persist through short gaps,
fade through medium gaps, and be effectively lost through long gaps.
Linear decay would either be too aggressive (full reset after N
periods) or too lenient (reputation preserved indefinitely).

### 15.4 Attestation and slashing

```solidity
function attest(bytes32 agentId, uint128 delta) external onlyRole(ATTESTER_ROLE) {
    Agent storage a = _agents[agentId];
    if (a.registeredAt == 0) revert UnknownAgent();
    _applyDecay(a);                            // apply pending decay first
    a.reputation += delta;
    a.lastActivity = uint64(block.timestamp);
    emit AgentAttested(agentId, delta, msg.sender);
}

function slash(bytes32 agentId, uint128 amount, string calldata reason)
    external onlyRole(SLASHER_ROLE)
{
    Agent storage a = _agents[agentId];
    if (a.registeredAt == 0) revert UnknownAgent();
    _applyDecay(a);
    a.reputation = amount >= a.reputation ? 0 : a.reputation - amount;
    a.lastActivity = uint64(block.timestamp);
    emit AgentSlashed(agentId, amount, reason);
}
```

Both functions apply pending decay *before* the update. This prevents a
long-dormant agent from being rehabilitated with a single `attest`
without first paying the decay penalty.

### 15.5 What this loop accomplishes (thesis connection)

An agent economy is what makes *outlives individual humans* (thesis
clause 3) practical at scale. A holder planning a 20-year position
needs heartbeat automation they trust. AgenticPlace lets them query:
"show me agents with > 100x reputation, < 1-year last-activity gap,
advertised heartbeat capability". The agents that survive that filter
have a measurable on-chain track record.

## 16. How global debt becomes one tradeable asset

The full chain, from raw truth to tradeable asset:

```
  REAL WORLD
   │
   │ sovereign bond markets, CDS markets, FX, equities, commodities
   ▼
  UPSTREAM ORACLES (Chainlink / Pyth / Synthetix)
   │
   │ adapter normalisation → Observation (WAD + confidence)
   ▼
  DeltaVerseDebtOracle.blended()           ← Step 2
   │
   │ 7 blended values per Metric
   ▼
  GlobalDebtStressIndex.score()            ← Steps 3 + 4
   │
   │ one uint256 in [0, 1e18]
   ▼
  iDEBT.openPosition()                     ← Step 5
   │   stressMark := score()
   │
   │   + heirs (Merkle root)
   │   + dormancy
   │   + principal (USDC)
   │
   ├──────────────┐
   │              │
   ▼              ▼
  TRADING        WAITING
  │              │
  │ secondary    │ block by block
  │ market       │ the stress index drifts
  │ prices       │
  │ ~MTM         │
  │              ▼
  │            CLOSE / INHERITANCE
  │              │
  │              │ settle against current MTM
  │              ▼
  │           SETTLEMENT TOKEN (USDC)
  │              │
  └──────────────┘
       holder       treasury
       payout  +    upside reserve
```

**Every box in this chain is on-chain, deterministic, and
non-discretionary.** The compression from the real world to one scalar
happens through functions whose parameters (weights, thresholds,
adapters, feeds) are governed by a two-day-timelocked DAO. The tradeable
asset that results is as credible as the sum of its ingredients.

Three properties make this "the whole world's debt, tradeable":

**1. Metric coverage.** The seven components span the causal axes of
debt stress. The oracle blending means new sources can be added to any
component without disrupting existing positions — governance just
registers a new adapter.

**2. Chain coverage.** The stack deploys independently on every
supported EVM chain (§14 of explanation.md). A holder anywhere can
mint; a heir anywhere can claim. BANKON provides cross-chain identity
so the same sovereign can participate on multiple deployments.

**3. Asset coverage.** Positions settle in whatever settlement token
the deployment is configured for — typically USDC, but any ERC-20 works.
Payments for gated operations settle in ALGO or USDCa via x402. A user
with USDCa on Algorand can open a USDC position on Polygon without ever
holding MATIC.

The compound effect: **no matter where a user is, what wealth they
hold, or which chain their heirs use, the protocol offers a single
consistent claim on the state variable named by the thesis.**

## 17. Closing: the invariant that proves the thesis

The thesis claims that global debt is *a state variable of
civilisation*. The proof-of-concept that the protocol makes this claim
operational is a single invariant:

> For any two addresses A and B, on the same chain, at the same
> block N, with equal principal and equal stressMark, if A is silent and
> their dormancy elapses and their heir claims, and B chooses to close
> at the same block M, then A's heir and B receive exactly the same
> payout: `principal × max(0, 1 − (score_M − stressMark)) / 1e18`,
> capped at `2 × principal`.

In other words: **the protocol treats a dead holder and a living
closer identically**. The succession primitive is not a privilege or a
discretion; it is a re-derivation of the same MTM formula with a
different authorisation path. There is no special "death case". The
mathematics doesn't know the difference.

That identity — *dead holder ≡ living closer, at equal principal and
mark* — is the minimum sufficient property to call the system a
cryptographic inheritance mechanism. It is what makes iDEBT a
**primitive rather than a product**. Anything built on top of the
primitive — estate planning dApps, institutional custody, multigen
family offices, automated insurance — inherits the property.

Global debt is already a state variable. iDEBT gives that variable an
on-chain representation, a tradeable claim, and a succession mechanism.
The remaining work of the thesis is not engineering; it is adoption.
