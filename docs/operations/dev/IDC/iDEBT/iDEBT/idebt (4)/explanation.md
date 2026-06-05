# iDEBT — Complete Explanation & Deployment Guide

> A single document covering what iDEBT is, why it's built the way it is,
> what every contract does, how the off-chain services fit in, and exactly
> how to put it in production on any supported chain.
>
> For shorter, task-focused docs, see [`technical.md`](./technical.md),
> [`usage.md`](./usage.md), and [`deploy.md`](./deploy.md). This document
> is the long-form companion that makes the rest legible.

---

## Table of Contents

1. [What iDEBT Is](#1-what-idebt-is)
2. [Why It Exists (The Thesis)](#2-why-it-exists-the-thesis)
3. [Architectural Overview](#3-architectural-overview)
4. [The Four Token Economy](#4-the-four-token-economy)
5. [The Oracle Layer](#5-the-oracle-layer)
6. [The Global Debt Stress Index](#6-the-global-debt-stress-index)
7. [The iDEBT Position Contract](#7-the-idebt-position-contract)
8. [Cryptographic Inheritance Mechanics](#8-cryptographic-inheritance-mechanics)
9. [DAIO Governance](#9-daio-governance)
10. [AgenticPlace: Agent Identity & Reputation](#10-agenticplace-agent-identity--reputation)
11. [mindX: Advisory Settlement](#11-mindx-advisory-settlement)
12. [BANKON: Sovereign Identity Binding](#12-bankon-sovereign-identity-binding)
13. [x402 Payments via Parsec on Algorand](#13-x402-payments-via-parsec-on-algorand)
14. [Multi-Chain Strategy & ChainMapping](#14-multi-chain-strategy--chainmapping)
15. [Security Model & Invariants](#15-security-model--invariants)
16. [Complete Deployment Guide](#16-complete-deployment-guide)
17. [Post-Deployment Operations](#17-post-deployment-operations)
18. [Upgrade & Migration Strategy](#18-upgrade--migration-strategy)
19. [Emergency Procedures](#19-emergency-procedures)
20. [Glossary](#20-glossary)

---

## 1. What iDEBT Is

iDEBT is a Solidity protocol that turns **exposure to global sovereign-debt
stress** into a transferable, inheritable, mark-to-market ERC-721 position.

A holder opens a position by depositing settlement stablecoin (typically
USDC). The protocol records two things: the **principal** (the notional
amount) and the **stress mark** (the value of the Global Debt Stress Index
at mint time). The position's mark-to-market value tracks the inverse of
subsequent index movement: if stress rises after the holder mints, the
position is worth less; if stress falls, it's worth more. At maturity the
holder can close and receive `min(MTM, principal)` — the protocol's reserve
captures MTM > principal as the DAIO's upside pool.

What makes iDEBT distinct from a generic parametric derivative is the
**inheritance layer**. Every position carries:

- a Merkle root committing to a private set of `(heir_address, shares_bps)`
  tuples totaling exactly 10,000 bps,
- a `dormancy` window measured in seconds, and
- a `lastHeartbeat` timestamp maintained by the holder.

If the holder is silent longer than `dormancy`, any heir can present their
Merkle proof and claim their share of the mark-to-market value. The heir
set is private until claim time — the Merkle root reveals nothing about
*who* the heirs are, only that *some* committed set exists. This is the
"cryptographic inheritance" in the protocol's name.

The other pieces of the stack exist to make this primitive actually
usable in production:

- The oracle layer blends Chainlink, Pyth, and Synthetix V3 data into
  confidence-weighted truth.
- DAIO governance lets the ecosystem change weights, thresholds, fees, and
  oracle wiring without touching the core contracts.
- The integrations (AgenticPlace, mindX, BANKON, x402) connect the
  on-chain primitives to the off-chain services that actually originate
  positions, advise on them, prove sovereign identity, and collect
  micro-payments for gated operations.

## 2. Why It Exists (The Thesis)

The protocol operationalises a specific thesis — the **Cryptographic
Inheritance of Global Debt** — first articulated in the DELTAVERSE
whitepaper. The thesis has four parts:

**Part 1: Debt is not a balance sheet line, it's a state variable of
civilisation.** Global sovereign debt / GDP crossed 100% in the early 2020s
and has not retreated. At some point the burden stops being *payable*
through growth and becomes *transferable* — either through inflation,
default, restructuring, or some synthesis of all three. The transfer
mechanics are opaque; asset prices reflect *expectations* of the transfer,
not the underlying metric.

**Part 2: Anyone exposed to fiat systems is already exposed to this
transfer, whether they hedge or not.** The unasked question is not "should
I take exposure?" but "is my exposure intentional and priced correctly?"
An iDEBT position is the instrument that makes the exposure *explicit*,
*priced*, and *settle-able against a transparent index*.

**Part 3: The transfer will outlive any single human.** Sovereign debt
cycles are multi-decade. A position meaningful in 2026 may still be
meaningful in 2056. The protocol therefore needs a **succession primitive**
— not a legal will, not a multisig inheritance hack, but a cryptographic
commitment that survives the death or disappearance of the holder.

**Part 4: Truth about global debt must be decentralised the same way the
debt's effects are.** No single oracle source can be authoritative. The
protocol blends multiple upstreams with confidence weighting, regimes, and
governance-set thresholds, so that the *process* of defining stress is
itself adversarial and auditable.

iDEBT is the engineering expression of that thesis. Every design decision
in the codebase traces back to one of those four parts.

## 3. Architectural Overview

```
                            ┌───────────────────────────┐
                            │        DAIO (Governor)    │
                            │   │  Timelock Treasury    │
                            └─────────────┬─────────────┘
                                          │ admin role
               ┌──────────────────────────┼──────────────────────────┐
               ▼                          ▼                          ▼
   ┌─────────────────────┐  ┌────────────────────────┐  ┌─────────────────────┐
   │ DeltaVerseDebtOracle│──│ GlobalDebtStressIndex  │──│ iDEBT (ERC-721)     │
   │  adapter registry   │  │  7-component 0..1e18   │  │  positions + heirs  │
   └──────────┬──────────┘  └────────────────────────┘  └──────────┬──────────┘
              │                                                    │
   ┌──────────┼──────────┐                                         │ USDC / settlement
   ▼          ▼          ▼                                         ▼
 ┌────────┐┌──────┐┌──────────┐                            ┌────────────────┐
 │Chainlnk││Pyth  ││SynthetixV3│                           │ DAIOTreasury   │
 │Adapter ││Adptr ││ Adapter  │                            │ reserve sink   │
 └────────┘└──────┘└──────────┘                            └────────────────┘

   Off-chain services (gated on-chain by the contracts on the right):
     agenticplace.pythai.net   ◀────▶   AgenticPlaceRegistry  (agent reputation)
     mindx.pythai.net          ◀────▶   MindXBridge            (EIP-712 advisory)
     bankon.pythai.net         ◀────▶   BANKONConnector        (AlgoIDNFT binding)
     parsec.finance / x402     ◀────▶   X402PaymentGateway     (Algorand payments)
```

The stack is deployed **independently per chain**. There is no bridge token
in v0.1. Cross-chain coherence comes from three shared sources of truth:

1. A canonical `ChainMapping` library replicated on every chain.
2. A DAIO treasury that approves oracle wiring changes chain-by-chain.
3. A BANKON sovereign identity that lets a holder prove identity across
   deployments without a bridge.

## 4. The Four Token Economy

iDEBT's token surface is narrow. It has **one ERC-20** (`iDEBTVoteToken`)
and **one ERC-721** (`iDEBT` position token). The wider DELTAVERSE
four-token economy (THRUST / PAIMINT / PAI / DELTAVERSE NFT) plugs in
through the adapter pattern — positions can be gated against any
`IERC20`-compatible settlement token, and the vote token can be replaced
with a wrapped version of PAI for DELTAVERSE-native deployments.

**iDEBTVoteToken (`iVOTE`)** is a standard OpenZeppelin ERC20Votes with
`ERC20Permit` for gasless approvals and a `MINTER_ROLE` that is intended to
be renounced after initial distribution. Supply mints to the deployer at
deploy time; the deployer is expected to transfer to the DAIO treasury and
then renounce minting. From that point on, supply is fixed.

**iDEBT (the ERC-721)** is one token per position. The NFT is the
*claim*, not the collateral — collateral (the settlement token principal)
sits in the iDEBT contract's balance. Transferring the NFT transfers the
claim; this is intentional because it lets a holder hand a position to a
custodian or market maker without involving the treasury.

The economic parameters the DAIO controls:

- `protocolFeeBps` — up to 1,000 (10%); charged on `openPosition`.
- `maxPrincipal` — cap per position.
- `scopePrice[scope]` — the x402 price for each gated operation.
- `weights[7]` — the index weights (must sum to exactly 1e18).
- `calmMax, elevatedMax, distressMax, crisisMax` — the regime thresholds.

No economic parameter can be changed outside of a DAIO proposal that
executes through the treasury's timelock.

## 5. The Oracle Layer

### 5.1 Why blending matters

Every oracle has a failure mode. Chainlink feeds can go stale; Pyth can
return high-confidence prices that are nonetheless wrong during market
halts; Synthetix markets can diverge from spot when liquidity is thin. A
stress index that trusted any single source would inherit all of that
single source's failure modes. Blending doesn't eliminate failure — it
forces multiple oracles to fail *in the same direction* before the index
moves incorrectly.

### 5.2 The adapter contract

Each upstream source is wrapped in a thin adapter whose only job is to
present an `IDebtOracle.Observation`:

```solidity
struct Observation {
    int256  value;       // normalised to 1e18
    uint64  timestamp;   // source publish time
    uint256 confidence;  // 0..1e18
    bytes32 source;      // identifier
}
```

`value` is signed because some metrics (yield curve slope, real rates) can
legitimately be negative. `confidence` is computed by the adapter from
upstream signals:

- **Chainlink**: confidence decays linearly from 1e18 at publish time to 0
  at the feed's heartbeat. A feed that hasn't updated in half its
  heartbeat window therefore contributes with 50% weight.
- **Pyth**: uses the published `conf` interval — `confidence = price /
  (price + conf)`. A Pyth price with zero confidence interval contributes
  with weight 1; a price whose confidence interval equals the price
  contributes with weight 0.5.
- **Synthetix V3**: currently hardcoded to 1e18 because the Synthetix
  V3 Core proxy is atomic with the chain — there's no "staleness" once
  the call returns. Future versions may incorporate utilization-based
  confidence.

### 5.3 DeltaVerseDebtOracle

The oracle contract is a registry, not a compute engine. It:

- **attaches** adapters to metrics (`attachAdapter(metric, sourceId, addr)`),
- **revokes** sources (`revokeSource(sourceId)`),
- **blends** live adapter reads (`blended(metric)`),
- **picks** the freshest above-floor observation (`latest(metric)`), and
- **caches** observations on demand (`refresh(metric)`).

The blend formula is explicit:

```
blended = Σ (value_i × conf_i) / Σ conf_i,     conf_i ≥ minConfidence
```

Confidence values under `minConfidence` (default 0.25e18) are excluded
entirely — they don't reduce the blend, they're discarded. This is a
deliberate choice: a 10%-confidence Chainlink update during a staleness
event should not pollute the blended value at all.

### 5.4 Metric → adapter recommended wiring

| Metric                | Chainlink                 | Pyth                        | Synthetix V3        |
| --------------------- | ------------------------- | --------------------------- | ------------------- |
| `SovereignDebtGDP`    | custom aggregator         | —                           | —                   |
| `CDS5Y`               | —                         | —                           | CDS-market adapter  |
| `YieldCurveInversion` | 10Y-2Y spread feed        | 10Y-2Y UST                  | —                   |
| `RealRate`            | 5Y TIPS                   | 5Y real yield               | —                   |
| `DXY`                 | DXY feed                  | DXY                         | —                   |
| `VIX`                 | VIX feed                  | VIX                         | —                   |
| `GoldRatio`           | XAU/USD                   | XAU/USD                     | —                   |

None of this is hardcoded. `Configure.s.sol` reads adapter addresses from
environment variables and can wire any subset.

## 6. The Global Debt Stress Index

### 6.1 From raw values to component stress

Each of the seven metrics has its own raw scale — CDS in basis points,
VIX in percent, debt/GDP as a ratio, and so on. The index converts each to
a `[0, 1e18]` **stress contribution** using a logistic function.

The logistic function squashes any real input to a bounded output:

```
sigmoid(x) = 1 / (1 + exp(-x))
```

But a real `exp` is expensive on-chain. The contract uses a closed-form
rational approximation (`DebtMath.logistic`):

```
sigmoid(x) ≈ 0.5 + 0.5 × x / (4 + |x|)
```

This is accurate to ≤1% across `x ∈ [-6, 6]` in WAD units and saturates
correctly outside that range. It compiles to a handful of opcodes with no
loops.

Each metric's raw value is shifted by a calibration baseline before being
passed to the logistic. The baselines are:

| Metric              | Baseline (neutral)    | Stress direction            |
| ------------------- | --------------------- | --------------------------- |
| SovereignDebtGDP    | 100% (1e18)           | higher                      |
| CDS5Y               | 1% (0.01e18)          | higher                      |
| YieldCurveInversion | 0 (flat curve)        | deeper inversion (negative) |
| RealRate            | 0%                    | higher                      |
| DXY                 | 100 (1e18)            | higher                      |
| VIX                 | 20                    | higher                      |
| GoldRatio           | 1.0                   | higher                      |

The baselines are currently hardcoded in `GlobalDebtStressIndex._norm*`
functions. Governance can change *weights* and *regime thresholds* but not
the baselines; that's a v0.2 item.

### 6.2 Aggregation

A weighted sum:

```
index = Σ component_i × weight_i,     Σ weight_i = 1e18 (enforced)
```

Default weights:

| Component | Weight |
| --------- | ------ |
| debt/GDP  | 25%    |
| CDS       | 20%    |
| yield inv | 15%    |
| real rate | 10%    |
| DXY       | 10%    |
| VIX       | 10%    |
| gold      | 10%    |

### 6.3 Regime thresholds

The numeric index maps to a discrete regime that external integrations can
switch on cheaply:

| Regime    | Index band     |
| --------- | -------------- |
| Calm      | `[0.00, 0.20)` |
| Elevated  | `[0.20, 0.40)` |
| Distress  | `[0.40, 0.60)` |
| Crisis    | `[0.60, 0.80)` |
| Default   | `[0.80, 1.00]` |

Thresholds are strictly monotone; `setThresholds` enforces this at write
time.

### 6.4 Update path

Two modes:

- **Read-only** (`score()`, `regime()`): recompute on every call. Cheap
  because all dependencies are `view`.
- **Snapshot write** (`poke()`): recompute and persist. Emits
  `IndexUpdated` and, if the regime changed, `RegimeTransition`. Callable
  by anyone — keeper networks can call this on a schedule.

The `iDEBT` contract always reads via `score()`, not from the stored
snapshot, so positions are always marked against live oracle state even if
no one has poked recently.

## 7. The iDEBT Position Contract

### 7.1 Storage layout

```solidity
struct Position {
    uint256 principal;      // notional in settlement token
    uint256 stressMark;     // index value at mint
    uint64  mintedAt;
    uint64  maturity;
    uint64  lastHeartbeat;
    uint64  dormancy;
    address holder;         // denormalised for fast access
}

mapping(uint256 => Position)                         _positions;
mapping(uint256 => bytes32)                          _heirRoot;
mapping(uint256 => uint8)                            _heirCount;
mapping(uint256 => mapping(bytes32 => bool))         _claimed;
```

The `holder` field is denormalised from ERC-721 `ownerOf` for two reasons:

- Some heir-claim paths read the position after the NFT is burned.
- The `_update` hook refreshes `holder` and `lastHeartbeat` atomically on
  transfer; keeping both in the `Position` struct lets this be a single
  SSTORE sequence.

### 7.2 Lifecycle

```
   openPosition
        │
        ▼
   ┌─────────┐     heartbeat ───▶ (no effect on principal)
   │  live   │◀──┐  service   ───▶ (reduces principal)
   └────┬────┘   │  transfer  ───▶ (refreshes holder + heartbeat)
        │        │
        ├────────┘
        │
        ▼
   block.timestamp ≥ maturity
        │
        ├── holder calls close ────▶ burn + transfer min(MTM, principal)
        │
        OR
        │
        ▼
   block.timestamp ≥ lastHeartbeat + dormancy
        │
        └── any heir calls claimInheritance ──▶ partial or full burn
```

### 7.3 Mark-to-market

The mark-to-market formula is deliberately simple:

```
Δ      = score_now − stressMark           // signed WAD
factor = max(0, 1e18 − Δ)                 // floor at zero
MTM    = min(principal × factor / 1e18, 2 × principal)
```

This gives:

- `Δ = 0`: MTM = principal
- `Δ = +0.10e18` (stress rose 10pp): MTM = 0.9 × principal
- `Δ = −0.10e18` (stress fell 10pp): MTM = 1.1 × principal
- `Δ = +1.0e18` (absolute crisis): MTM = 0
- `Δ ≤ −1.0e18`: MTM capped at 2 × principal

The 2× upside cap is a design choice, not an accounting necessity. A
sudden collapse in the stress index often represents measurement noise or
a policy-driven reversal rather than durable improvement, and we don't
want positions to capture windfalls from those events. The 2× cap
captures reasonable mean-reversion profits while leaving the tail for the
reserve. Governance could replace this with a different curve in a future
upgrade.

### 7.4 Fees and reserves

At `openPosition` the holder pays:

- `principal` (locked in the contract as collateral), and
- `principal × protocolFeeBps / 10_000` (sent to `feeSink`, typically the
  treasury).

At `close`, the holder receives `min(MTM, principal)`. Any excess
(MTM > principal) stays in the contract and accrues to the treasury's
upside pool, building the protocol reserve. At `claimInheritance`, each
heir receives `MTM × sharesBps / 10_000` and principal is reduced
pro-rata, so the reserve also captures MTM > principal on the inheritance
path.

This is the protocol's economic engine: **stress-regime volatility
generates carry for the reserve**, which funds DAIO operations, oracle
keeper rebates, and emergency reserves.

## 8. Cryptographic Inheritance Mechanics

### 8.1 The Merkle commitment

At mint time, the holder provides a `Heir[]` array where each entry is:

```solidity
struct Heir {
    address successor;
    uint16  sharesBps;
    bytes32 proofRoot;
}
```

All entries must share the same `proofRoot`. That root is a Merkle tree
over leaves computed as:

```
leaf = keccak256(abi.encode(successor, sharesBps))
```

The contract stores only the root (`_heirRoot[tokenId]`) and the count
(`_heirCount[tokenId]`). The individual heirs and their shares are
**private** — observers see only that the position commits to *some* set
of ≤32 heirs summing to 10,000 bps.

This is cheaper than storing each heir on-chain (O(1) vs O(n) storage),
but more importantly it's **privacy-preserving**. A holder can name heirs
without publishing the succession plan to the world.

### 8.2 The claim flow

When `block.timestamp ≥ lastHeartbeat + dormancy`, any heir can claim by
presenting:

```solidity
bytes heirProof = abi.encode(
    address successor,        // == msg.sender
    uint16  sharesBps,
    bytes32[] merkleProof
);
```

The contract:

1. Checks `successor == msg.sender` (only the named heir can claim).
2. Computes the leaf and verifies the Merkle proof against
   `_heirRoot[tokenId]`.
3. Checks `_claimed[tokenId][leaf] == false` and sets it true
   (single-claim per heir).
4. Computes `payout = MTM × sharesBps / 10_000`.
5. Reduces position's `principal` by `principal × sharesBps / 10_000`.
6. Transfers the payout in settlement token.
7. If the principal reaches zero (last heir claimed), burns the NFT.

### 8.3 Heartbeat semantics

Four actions count as proof-of-life:

- `heartbeat(tokenId)` by the holder
- `service(tokenId, amount)` **by the holder** — *wait, actually, the
  implementation does not treat `service` as a heartbeat.* This is
  intentional: third parties may service a position, and accepting a
  third-party payment should not reset the dormancy clock. Only the
  holder's *own* `heartbeat` or position *transfer* count.
- ERC-721 `transferFrom` / `safeTransferFrom` — the `_update` override
  refreshes `lastHeartbeat` to `block.timestamp`.
- Granting approvals — does **not** count; approvals are ambient state.

The holder is expected to run a heartbeat bot for long-dated positions. A
simple multisig with an auto-heartbeat Gelato task is the common
production pattern.

### 8.4 What happens if the holder loses keys

Depends on `dormancy`:

- **Short dormancy** (30 days): heirs can claim within a month, which is
  the desired outcome for most holders. A holder who merely goes on
  vacation should still heartbeat before leaving, or transfer the NFT to
  a trusted heartbeat relay contract.
- **Long dormancy** (1 year): the holder has a year to recover from
  temporary key loss before heirs can claim.
- **Zero dormancy**: disallowed by the constructor's validation; the
  minimum enforced dormancy is 0 seconds *technically*, but a zero value
  means the first block after mint allows inheritance, which is rarely
  useful. Practical minimum is `1 days`.

## 9. DAIO Governance

### 9.1 Stack

The DAIO (Decentralised Autonomous Intelligence Organisation) uses
OpenZeppelin's standard Governor composition:

- **`iDEBTVoteToken`** — ERC20Votes with checkpointing.
- **`DAIO`** — `Governor` + `GovernorSettings` + `GovernorCountingSimple`
  + `GovernorVotes` + `GovernorVotesQuorumFraction` +
  `GovernorTimelockControl`.
- **`DAIOTreasury`** — `TimelockController`.

Any proposal that passes has to wait `minDelay` (default 2 days) in the
timelock before execution. The timelock is the *only* holder of admin
roles on every other contract in the system — `DeltaVerseDebtOracle`,
`GlobalDebtStressIndex`, `iDEBT`, `X402PaymentGateway`, `MindXBridge`,
`AgenticPlaceRegistry`, `BANKONConnector`.

### 9.2 Parameters

| Parameter           | Default       | What it controls                              |
| ------------------- | ------------- | --------------------------------------------- |
| `votingDelay`       | 7_200 blocks  | delay between `propose` and vote start (~1d)  |
| `votingPeriod`      | 50_400 blocks | vote window duration (~7d)                    |
| `proposalThreshold` | 100k iVOTE    | minimum voting power to propose               |
| `quorumPct`         | 20            | quorum as percent of supply (denominator 100) |
| `minDelay`          | 2 days        | timelock delay before execution               |

These are constructor arguments, so they can differ per chain. For
low-activity chains a shorter voting period may be preferred; for
high-value mainnet a longer one.

### 9.3 What proposals can do

- **Oracle management**: attach or revoke adapters, change freshness
  windows, change minimum confidence.
- **Index tuning**: change the 7-weight vector, change the 4 regime
  thresholds.
- **iDEBT parameters**: change `protocolFeeBps`, change `maxPrincipal`,
  change `feeSink`.
- **x402 prices**: set the per-scope price and asset, authorise or revoke
  Parsec facilitators.
- **mindX / BANKON key rotation**: replace the signing keys if
  compromised.
- **Treasury operations**: withdraw accrued reserves, stake them
  elsewhere, distribute to voters, etc.
- **Upgrade migrations**: deploy new oracle / index / position
  implementations and transition state (see §18).

## 10. AgenticPlace: Agent Identity & Reputation

The `AgenticPlaceRegistry` contract mirrors the off-chain
`agenticplace.pythai.net` service. It implements an ERC-8004-style
identity and reputation registry with **BONAFIDE** decay semantics.

### 10.1 Why it exists in the iDEBT stack

iDEBT has natural agent roles:

- **Underwriters** recommend maturity/dormancy/heir configurations.
- **Heartbeat relays** keep positions alive for passive holders.
- **Risk advisors** produce mindX attestations.
- **Automated heirs** claim on behalf of beneficiaries who can't
  transact themselves.

Any of these can be an on-chain agent with a reputation score that the
ecosystem can slash if the agent misbehaves and raise if they deliver
reliably over time.

### 10.2 Reputation mechanics

Reputation starts at 1e18 (1.0) on registration. `attest` adds to it;
`slash` removes from it. Both are gated on `ATTESTER_ROLE` and
`SLASHER_ROLE`, which in production are held by the DAIO treasury and can
be delegated to specific verifier contracts.

Reputation **decays** at `decayBps` (default 1%) per `DECAY_INTERVAL`
(30 days). Decay is applied lazily: `attest` and `slash` apply pending
decay before their update; `reputationOf` computes a projected decay
without writing. The decay cap is 64 periods (~5.3 years) — beyond that
the loop stops to prevent gas blow-ups on long-dormant agents.

### 10.3 Off-chain mirror

The off-chain service at `agenticplace.pythai.net` maintains the agent
directory, handles capability discovery (via `/.well-known/agent.json`),
and routes reputation signals to on-chain `attest` / `slash` calls. The
on-chain reputation is the canonical score; the off-chain service is an
index for discovery.

## 11. mindX: Advisory Settlement

`MindXBridge` is the on-chain settlement surface for advisories issued by
the mindX API at `mindx.pythai.net`. The flow:

1. A holder (or anyone) calls mindX's off-chain API with a subject
   address and optional position context.
2. mindX runs its model, produces an advisory blob, hashes it, and signs
   an EIP-712 `Attestation` struct:

   ```solidity
   struct Attestation {
       bytes32 requestId;
       bytes32 claimHash;    // keccak256 of the advisory text
       uint64  issuedAt;
       uint32  modelVersion;
       uint16  riskScore;    // 0..10000 bps
       address subject;
   }
   ```

3. The caller submits `(attestation, signature)` to
   `MindXBridge.settle`. The bridge:
   - Rejects if `requestId` is already consumed (replay protection).
   - Rejects if `issuedAt` is older than `maxAge` (default 1 day).
   - Recovers the EIP-712 signer and rejects if it's not the registered
     mindX key.
   - Stores the latest `(riskScore, timestamp)` per subject.

The bridge stores only the *latest* score — the full history lives in
the off-chain archive. This is a deliberate cost/benefit trade: iDEBT
only needs the current risk score for gating decisions, and the archive
is cheap and immutable off-chain.

Integrations that want to use mindX scores to gate actions (e.g. refuse
to accept positions from high-risk subjects) can read
`latestRiskScore(subject)` and act on the bps value.

## 12. BANKON: Sovereign Identity Binding

`BANKONConnector` binds Algorand **AlgoIDNFT** sovereign-identity
commitments to EVM wallets. The off-chain BANKON service at
`bankon.pythai.net` is the issuer.

### 12.1 Why the binding matters

Inheritance is fundamentally about identity continuity — the *person*
matters, not just the wallet. A heir whose EVM wallet is compromised but
whose sovereign Algorand identity remains intact can re-bind a new EVM
wallet to the same `algoIdRoot` and continue to be recognised by the
protocol.

iDEBT does *not* require BANKON binding to operate. A position can be
opened and claimed without any sovereign identity. But integrators
building on iDEBT (estate-planning front-ends, institutional custody,
family offices) typically require BANKON-bound parties and will refuse
to accept positions where the holder or any heir is unbound.

### 12.2 Binding flow

1. User mints or retrieves an AlgoIDNFT on Algorand. The NFT's commitment
   root is `algoIdRoot`.
2. User POSTs `{algoIdRoot, evm, chainId}` to BANKON.
3. BANKON verifies Algorand ownership off-chain, then returns an ECDSA
   signature over
   `toEthSignedMessageHash(keccak256(algoIdRoot, evm, chainId))` under
   the registered BANKON signer key.
4. User calls `BANKONConnector.bind(algoIdRoot, sig)` from the EVM
   wallet. The contract verifies the signer and records the binding.

Bindings are one-to-one (one root ↔ one EVM wallet per chain). The user
can `revoke()` to clear the binding and rebind to a new wallet.

## 13. x402 Payments via Parsec on Algorand

`X402PaymentGateway` implements an on-chain verifier for the
**x402 payment-required protocol**, facilitated by Parsec
(`parsec.finance`) on Algorand. The gateway gates mutating operations on
the iDEBT core contract — currently `openPosition` and `claimInheritance`.

### 13.1 Why gate payments off-chain?

Two reasons:

- **Cost discipline**: small per-operation fees discourage spam without
  forcing holders to hold the gas token.
- **Cross-chain UX**: a user whose wealth is in Algorand ALGO or USDCa
  can pay for operations on an EVM chain without bridging.

### 13.2 The full flow

```
1. Client requests gated EVM operation.
2. Gated endpoint returns HTTP 402 with:
   x-payment-required: { scope, amount, asset, expiry, facilitatorAddr }
3. Client uses parsec-wallet to pay `amount` of `asset` (ALGO or USDCa)
   to Parsec's Algorand facilitator address.
4. Client reports the Algorand tx id to Parsec.
5. Parsec verifies settlement on Algorand, produces an EIP-712 Receipt:
      struct Receipt {
        address facilitator;
        address payer;
        uint256 amount;
        bytes32 asset;
        bytes32 scope;
        uint64  nonce;
        uint64  expiry;
        bytes32 algoTxId;
      }
   and signs it under a key registered with X402PaymentGateway.
6. Client calls X402PaymentGateway.consume(receipt, signature).
   The gateway:
     - verifies the facilitator is authorised,
     - verifies nonce has not been used,
     - verifies expiry has not passed,
     - verifies amount ≥ scopePrice and asset matches scopeAsset,
     - recovers the EIP-712 signer and verifies it equals facilitator,
     - marks usedNonces[payer][nonce] = true,
     - sets _paidUntil[payer][scope] = expiry.
7. Client calls the gated EVM operation (e.g. iDEBT.openPosition).
   iDEBT checks x402.hasPaid(msg.sender, scope) and proceeds.
```

### 13.3 Trust assumptions

The on-chain contract **cannot verify Algorand settlement directly**. It
trusts that the Parsec facilitator will not sign receipts for unsettled
transactions. This is enforced by:

- **Facilitator authorisation**: the DAIO treasury is the only role that
  can `setFacilitator`; a misbehaving facilitator is revoked by
  governance proposal.
- **Receipt expiry**: receipts have short expiry windows (typically
  < 1 hour); a compromised key gives the attacker limited time to do
  damage before the DAIO can react.
- **Nonce uniqueness**: even with a valid key, a given receipt is single-
  use per payer per scope.

If absolute Algorand finality verification becomes required in a future
version, a light-client bridge (e.g. via Algorand State Proofs) can be
added without breaking the receipt format.

### 13.4 Scopes currently defined

- `keccak256("iDEBT.open")` — gate on `openPosition`.
- `keccak256("iDEBT.claim")` — gate on `claimInheritance`.

Additional scopes can be registered by governance proposals to gate any
other mutating function (e.g. high-value `service` payments, mindX
advisory requests, BANKON binding submissions).

## 14. Multi-Chain Strategy & ChainMapping

### 14.1 The canonical table

`src/libraries/ChainMapping.sol` is a pure Solidity library that returns
a structured record for every supported chain. The same table is
replicated in TypeScript at `api/src/chainmap.ts` and as a JSON
publication at `agenticplace.pythai.net/allchain.html`.

```
EVM mainnet: Ethereum, Optimism, Polygon, Polygon zkEVM, BSC, Fantom,
             zkSync Era, Base, Arbitrum One, Avalanche C, Arc Network
EVM testnet: Sepolia
Non-EVM:     Algorand (mainnet + testnet), Solana, Cosmos Hub, Sui
```

Non-EVM chains use sentinel chain IDs chosen to never collide with
EIP-155:

- `4_160_001` / `4_160_002` — Algorand mainnet / testnet
- `5_001_001` — Solana mainnet
- `6_001_001` — Cosmos Hub
- `7_001_001` — Sui mainnet

### 14.2 Why no bridge?

v0.1 deploys the full stack independently per chain. This means:

- A position opened on Polygon cannot be directly transferred to
  Arbitrum.
- The stress index on each chain is computed independently; there is no
  guarantee that Polygon's index equals Arbitrum's index at any given
  block.

This is a deliberate simplification. Cross-chain messaging (Chainlink
CCIP, LayerZero, Axelar) adds significant audit surface and trust
assumptions. v0.2 may introduce a bridge token (`iDEBTXChain`) if market
demand justifies the cost, but the core thesis — cryptographic
inheritance of debt exposure — is expressible per-chain without a bridge.

### 14.3 Coordination layer

What keeps cross-chain deployments coherent:

- **Identical `ChainMapping`**: same table on every chain.
- **DAIO alignment**: when the DAIO changes weights on one chain, the
  intent is to propagate identical changes to other chains via parallel
  proposals.
- **Shared sovereign identity via BANKON**: a single AlgoIDNFT root can
  be bound to different EVM wallets on different chains — the holder
  remains the same person.
- **Shared agent identity via AgenticPlace**: an agent registered with
  a given `agentId` on one chain has the same commitment on every
  chain.

## 15. Security Model & Invariants

### 15.1 Trust boundaries

| Boundary | Trust assumption | Mitigation |
| --- | --- | --- |
| Upstream oracles | Chainlink/Pyth/SNX report correctly | Confidence blending across sources |
| Freshness window | Keepers call `refresh` regularly | `blended` reverts on stale-only sources |
| Parsec facilitator | Signs only settled Algorand txs | Authorisation + expiry + nonce |
| mindX signer | Signs only real model outputs | Key rotation via governance |
| BANKON signer | Signs only verified Algorand holders | Key rotation via governance |
| DAIO voters | Quorum-weighted honest vote | 20% quorum + 2-day timelock |
| Holder heartbeat | Holder proves life or transfers | Inheritance fallback |

### 15.2 Invariants enforced at compile + test time

1. `Σ weights_i == 1e18` — checked in `setWeights`.
2. `calmMax < elevatedMax < distressMax < crisisMax ≤ 1e18` — checked in
   `setThresholds`.
3. `Σ heirs[i].sharesBps == 10_000` — checked in `openPosition`.
4. `heirs.length ≤ 32` — checked in `openPosition`.
5. `maturity > block.timestamp` at mint — checked in `openPosition`.
6. `MTM ≤ 2 × principal` — clamped in `markToMarket`.
7. `MTM ≥ 0` — clamped (the factor can't go below zero).
8. `usedNonces[payer][nonce]` monotonically set — enforced in `consume`.
9. `_claimed[tokenId][leaf]` single-set — enforced in `claimInheritance`.
10. All blended observations have `confidence ≥ minConfidence` — enforced
    in `blended` and `latest`.

### 15.3 Invariants verified by the test suite

- `test_Blended_WeightsByConfidence`: blend formula matches the
  confidence-weighted mean.
- `test_BaselineIsCalm`: at neutral oracle values the index is in the
  Calm regime.
- `test_ScoreMonotonicallyIncreasesWithStress`: raising any component
  raises the index.
- `test_Inheritance_MaturedHeirCanClaim`: dormancy + proof → payout.
- `test_Heartbeat_PreventsInheritance`: active heartbeat prevents claim.
- `test_MarkToMarket_DecreasesWithStress`: elevated stress reduces MTM.
- `test_RejectBadShareSum`: heir shares must sum to 10_000 bps.
- `test_X402 consume`: receipts are verified, replayed, expired correctly.
- `testFuzz_LogisticMonotone`: sigmoid approximation is monotone.
- `testFuzz_WdivWmulRoundTrip`: WAD division/multiplication is an
  identity modulo 1-wei rounding.

### 15.4 Known open risks

- **Hardcoded metric baselines**: the `_norm*` functions in
  `GlobalDebtStressIndex` carry hardcoded calibration constants that
  governance cannot change without a contract upgrade. Scheduled for v0.2.
- **Linear MTM curve**: the 1 − Δ factor is simple and therefore cheap,
  but it does not reflect genuine convexity in distressed regimes. v0.2
  may introduce regime-conditional curves.
- **No Algorand finality verification**: see §13.3. Mitigated by Parsec
  trust assumptions, not eliminated.
- **Keeper incentives**: v0.1 relies on altruistic or DAIO-paid keepers
  to call `refresh` and `poke`. v0.2 will introduce keeper rewards from
  the reserve.

## 16. Complete Deployment Guide

This section is the authoritative, step-by-step procedure. Everything in
`deploy.md` is a shorter reference; this is the long-form version that
assumes nothing.

### 16.1 Prerequisites

**Tooling:**

- Foundry ≥ 0.2.0 (install via `curl -L https://foundry.paradigm.xyz |
  bash && foundryup`)
- Node.js ≥ 20 for off-chain tooling
- `jq` for manipulating deployment artefacts

**Credentials:**

- A deployer private key holding ≥ 0.3 of the chain's native gas token
- Block-explorer API keys for Etherscan/Polygonscan/Arbiscan/etc.

**Addresses needed (chain-specific):**

- Settlement stablecoin (typically USDC)
- Parsec x402 facilitator
- mindX signing key
- BANKON signing key
- Chainlink feed addresses (per metric)
- Pyth contract + price IDs (per metric)
- Synthetix V3 Core proxy + market ID (if using)

### 16.2 Clone and build

```bash
git clone https://github.com/PYTHAI/idebt.git
cd idebt

foundryup

forge install openzeppelin/openzeppelin-contracts@v5.0.2 --no-commit
forge install foundry-rs/forge-std --no-commit
forge install smartcontractkit/chainlink@v2.14.0 --no-commit
forge install pyth-network/pyth-sdk-solidity --no-commit

forge build
forge test -vv
```

If any test fails on a clean checkout, stop. Do not deploy a failing tree.

### 16.3 Configure environment

```bash
cp .env.example .env
$EDITOR .env
```

Minimum required variables:

```
PRIVATE_KEY=0x...
DEPLOYER_ADDRESS=0x...
SETTLEMENT_TOKEN=0x...                    # chain-specific USDC

PARSEC_FACILITATOR=0x...
MINDX_SIGNING_KEY=0x...
BANKON_SIGNER=0x...

<CHAIN>_RPC_URL=...
ETHERSCAN_API_KEY=...                     # (or chain-specific)
```

Optional governance tuning:

```
DAIO_TIMELOCK_DELAY=172800                # 2 days
DAIO_VOTING_DELAY=7200                    # ~1 day on 12s blocks
DAIO_VOTING_PERIOD=50400                  # ~1 week
DAIO_PROPOSAL_THRESHOLD=100000000000000000000000  # 100k iVOTE
DAIO_QUORUM_PCT=20
```

### 16.4 Dry-run the deploy

```bash
forge script script/deploy/Deploy.s.sol \
  --rpc-url polygon \
  -vvvv
```

Note: no `--broadcast`. Foundry simulates the full transaction sequence
and prints gas estimates. Inspect the output and verify every constructor
argument.

### 16.5 Broadcast

```bash
forge script script/deploy/Deploy.s.sol \
  --rpc-url polygon \
  --broadcast \
  --verify \
  --slow \
  -vvvv
```

Flags explained:

- `--broadcast`: actually send transactions (absence = simulation only).
- `--verify`: automatically verify contracts on the block explorer.
- `--slow`: wait for transaction confirmation before sending the next.
  Required for chains where role grants need their targets to exist
  first (mainnet, Polygon PoS). Can be dropped on fast-finality L2s.

Expected console output:

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

### 16.6 Save the deployment record

```bash
# The broadcast JSON is in broadcast/Deploy.s.sol/<chainId>/run-latest.json
jq '.transactions[] | {contractName, contractAddress}' \
   broadcast/Deploy.s.sol/137/run-latest.json \
   > deployments/polygon.json
```

Commit `deployments/polygon.json` to the repo. This is the canonical
record of the deployment — it's what the frontend `useAddresses` hook
reads.

### 16.7 Wire the oracles

```bash
ORACLE=0x...          \
INDEX=0x...           \
DEBT=0x...            \
X402=0x...            \
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

This does three things:

1. **Deploys and attaches oracle adapters** for every Chainlink/Pyth/SNX
   feed whose address is provided.
2. **Authorises the Parsec facilitator** on `X402PaymentGateway` and
   sets default prices (1 USDCa for `iDEBT.open`, 0.5 USDCa for
   `iDEBT.claim`).
3. **Links the x402 gateway** into the core `iDEBT` contract
   (`iDEBT.setX402(gateway)`).

After this step, the oracle has live data and the x402 gating is
operational.

### 16.8 Transfer admin roles to the DAIO (if not already)

The `Deploy.s.sol` script sets the treasury as the admin on every
contract at construction time, so this step is usually already complete.
However, the deployer holds the `DEFAULT_ADMIN_ROLE` on the `DAIOTreasury`
itself during the deploy transaction (needed to grant the governor its
proposer role) and must renounce it:

```bash
cast send $TREASURY "renounceRole(bytes32,address)" \
  0x0000000000000000000000000000000000000000000000000000000000000000 \
  $DEPLOYER \
  --private-key $PRIVATE_KEY \
  --rpc-url polygon
```

Verify:

```bash
cast call $TREASURY "hasRole(bytes32,address)" \
  0x0000000000000000000000000000000000000000000000000000000000000000 \
  $DEPLOYER \
  --rpc-url polygon
# → 0x0000...0000 (false)
```

The deployer also holds `MINTER_ROLE` on `iDEBTVoteToken` until initial
distribution is complete. The procedure:

1. Mint the intended initial supply (done automatically in `Deploy.run`
   — the `100_000_000e18` constructor argument).
2. Transfer voting tokens to the treasury and intended founding voters.
3. Renounce minting:

```bash
cast send $VOTE_TOKEN "renounceRole(bytes32,address)" \
  $(cast keccak "MINTER_ROLE") \
  $DEPLOYER \
  --private-key $PRIVATE_KEY \
  --rpc-url polygon
```

From this point forward, the iDEBT stack is fully under DAIO control.

### 16.9 Publish deployment addresses

Update two places:

- **`deployments/<chain>.json` in the repo** (commit + PR).
- **`frontend/src/config/deployments.json`** — add your chain's block
  with all 11 addresses:

```json
{
  "137": {
    "voteToken":  "0x...",
    "treasury":   "0x...",
    "governor":   "0x...",
    "oracle":     "0x...",
    "index":      "0x...",
    "debtToken":  "0x...",
    "x402":       "0x...",
    "mindx":      "0x...",
    "agents":     "0x...",
    "bankon":     "0x...",
    "settlement": "0x...    # same as SETTLEMENT_TOKEN"
  }
}
```

After the merge, rebuild and deploy the frontend; users on Polygon will
now see the stack in the UI.

### 16.10 Run a smoke test

```bash
# 1. Mint a small position as the deployer
cast send $SETTLEMENT "approve(address,uint256)" $DEBT 100000000000000000000 \
  --private-key $PRIVATE_KEY --rpc-url polygon

# 2. Open a simple single-heir position
LEAF=$(cast keccak $(cast abi-encode "f(address,uint16)" $DEPLOYER 10000))
cast send $DEBT "openPosition(uint256,uint64,uint64,(address,uint16,bytes32)[])" \
  100000000000000000000 \
  $(( $(date +%s) + 31536000 )) \
  86400 \
  "[($DEPLOYER,10000,$LEAF)]" \
  --private-key $PRIVATE_KEY --rpc-url polygon

# 3. Read the current index
cast call $INDEX "score()(uint256)" --rpc-url polygon

# 4. Read the position
cast call $DEBT "positionOf(uint256)" 1 --rpc-url polygon
```

If all four succeed, the deployment is operational.

### 16.11 Testnet quickstart

For Sepolia and similar testnets, use the wrapper:

```bash
npm run deploy:sepolia
```

This runs `DeployTestnet.s.sol`, which first creates a mock USDC
(`tUSDC`), mints 10M to the deployer, then runs the full `Deploy`.
Configure and smoke-test the same way.

### 16.12 Multi-chain rollout order

Recommended sequence for rolling out to multiple mainnets:

1. **Sepolia** (or any testnet) — full dry-run, smoke-test, UI integration.
2. **Polygon PoS** — cheap gas, large user base, battle-test in
   production for ≥ 4 weeks.
3. **Arbitrum One** — L2 with mature oracle support.
4. **Base** — broadens L2 reach.
5. **Optimism** — further L2 coverage.
6. **Ethereum mainnet** — deploy only after multi-chain operation has
   been validated; mainnet gas costs make any mistake expensive.

The DAIO should propose identical weights and thresholds on every chain
to keep the index comparable across deployments.

## 17. Post-Deployment Operations

### 17.1 Keeper responsibilities

A keeper bot is needed to:

- Call `oracle.refresh(metric)` for each metric every ~5 minutes (or
  whenever a new Chainlink aggregator round is finalised). This caches
  fresh observations in the oracle contract.
- Call `stressIndex.poke()` every ~15 minutes to keep the stored
  snapshot current. `poke` emits `IndexUpdated` and `RegimeTransition`,
  which integrators subscribe to.

Reference keeper implementations (Gelato, Chainlink Automation, a simple
cron job with a hot wallet) are out of scope for this document but are
trivially written against the public read methods.

### 17.2 Monitoring

Subscribe to these events for operational health:

| Event | Emitter | What it signals |
| ----- | ------- | --------------- |
| `ObservationPublished` | `DeltaVerseDebtOracle` | adapter refresh |
| `IndexUpdated`         | `GlobalDebtStressIndex` | snapshot poke   |
| `RegimeTransition`     | `GlobalDebtStressIndex` | regime change   |
| `PositionOpened`       | `iDEBT`                 | new user        |
| `InheritanceClaimed`   | `iDEBT`                 | dormancy fired  |
| `ReceiptConsumed`      | `X402PaymentGateway`    | x402 payment    |
| `AttestationSettled`   | `MindXBridge`           | mindX advisory  |

Alerting rules to consider:

- No `IndexUpdated` in 30 minutes → keepers are down.
- `RegimeTransition` to Crisis or Default → notify DAIO + risk team.
- `confidence < minConfidence` on any adapter for > 1 hour → upstream
  oracle issue.
- Unusually high `InheritanceClaimed` rate → potential key-loss event
  on a popular custodian.

### 17.3 Routine maintenance

**Weekly:**
- Verify keeper bot is posting `IndexUpdated`.
- Check facilitator nonce accumulation in `X402PaymentGateway`; rotate
  if a single payer is exhausting their nonce space.

**Monthly:**
- Review mindX model version drift — if `modelVersion` field has
  increased, review the release notes.
- Review DAIO proposal backlog.

**Quarterly:**
- Re-verify oracle adapter heartbeats against upstream source docs.
- Rotate mindX and BANKON signing keys if the integrator policy
  mandates it.

### 17.4 Reporting

The DAIO should publish a quarterly report covering:

- Index trajectory (min/max/regime distribution).
- Position count, TVL, inheritance claims.
- Reserve accrual (MTM-to-principal spread captured by treasury).
- Proposals executed.
- Oracle uptime.
- Keeper operational cost vs reserve.

## 18. Upgrade & Migration Strategy

iDEBT v0.1 contracts are **immutable** — no proxies, no upgrade slots.
This is a deliberate security posture. Upgrades happen by deploying
new versions and migrating state via DAIO proposals.

### 18.1 Oracle upgrades

Adding a new adapter is not an upgrade — `attachAdapter` supports it
natively. Upgrading an adapter's internal logic requires a new adapter
contract and:

1. Deploy new `ChainlinkAdapter`/`PythAdapter`/`SynthetixV3Adapter`.
2. Governance proposal: `oracle.attachAdapter(metric, newSourceId, new)`.
3. Governance proposal: `oracle.revokeSource(oldSourceId)` (optional —
   adapters can coexist during transition).

### 18.2 Index upgrades

Changing the weights is a parameter update, not a logical upgrade —
covered by `setWeights`. Changing the normalisation baselines, adding a
new component metric, or changing the regime count requires a new
`GlobalDebtStressIndex` contract. Migration:

1. Deploy `GlobalDebtStressIndexV2`.
2. Governance proposal: the `iDEBT` contract's `stressIndex` is
   `immutable`, so migration requires also deploying a new `iDEBT`
   contract pointing at the new index.
3. Existing positions stay on the old contract until natural maturity or
   claim. New positions go to the new contract. Both contracts coexist.

This **position-stability guarantee** is the key property: a holder who
minted a position at stressMark X cannot have their MTM formula changed
retroactively. Any new curve applies only to new positions.

### 18.3 iDEBT upgrades

Same as index: deploy `iDEBTV2`, announce via governance, position
cohorts coexist. The DAIOTreasury remains shared; reserve accrual
continues unaffected.

### 18.4 Integration contract upgrades

`X402PaymentGateway`, `MindXBridge`, `AgenticPlaceRegistry`, and
`BANKONConnector` are simpler — they are pointed at by the core `iDEBT`
contract only in the case of x402 (via `setX402`). Upgrading any of
them is:

1. Deploy new version.
2. If it's `X402PaymentGateway`, governance proposal:
   `iDEBT.setX402(newGateway)`.
3. Otherwise, simply announce the new address; integrators update their
   clients.

### 18.5 Governance upgrades

Replacing the governor or timelock is the most invasive operation and
requires migration of every contract's `DEFAULT_ADMIN_ROLE`. This is
feasible but should not be done casually. The recommended path is:

1. Deploy new `DAIO` + `DAIOTreasuryV2`.
2. Governance proposal on the old DAIO: grant `DEFAULT_ADMIN_ROLE` on
   every contract to the new treasury.
3. Governance proposal on the old DAIO: revoke `DEFAULT_ADMIN_ROLE`
   from the old treasury on every contract.
4. Users switch to voting via the new governor.

## 19. Emergency Procedures

### 19.1 Pause

Both `DeltaVerseDebtOracle` and `iDEBT` implement OpenZeppelin's
`Pausable`. `EMERGENCY_ROLE` is held by the `DAIOTreasury`; pausing
therefore requires a governance proposal that passes the full voting
period + timelock.

**This is slower than most emergency flows**. The rationale: a protocol
that can be paused quickly can be paused maliciously. For faster response
to active exploits, consider:

- Deploying an emergency multisig with `EMERGENCY_ROLE`, separate from
  `DEFAULT_ADMIN_ROLE`. The multisig can pause immediately but can only
  pause — not change any parameter.
- Configuring a reduced timelock delay for specific proposal types
  (e.g. 1 hour for pause-only proposals) via OZ's `TimelockController`
  batch mechanics.

This is a deployer policy choice, not a contract change.

### 19.2 Adapter compromise

If a Chainlink or Pyth source starts returning adversarial values:

1. Governance proposal: `oracle.revokeSource(compromisedSourceId)`.
2. The blended value now excludes the revoked source; remaining
   adapters dominate the blend.
3. Separately, reduce `minConfidence` temporarily if other sources drop
   below floor due to the shock.

The blending design means a single compromised source cannot push the
index outside its normal range alone — it would need to overcome the
combined confidence of the other sources.

### 19.3 Facilitator compromise (x402)

If the Parsec facilitator key is compromised:

1. Governance proposal: `gate.setFacilitator(oldSigner, false)`.
2. Existing in-flight receipts signed by the old key will fail on
   `consume` (the facilitator check runs first).
3. Parsec deploys a new signer; governance proposal:
   `gate.setFacilitator(newSigner, true)`.

Any receipts-in-flight at the time of compromise are lost; users
whose Algorand payments went through but whose receipts never got
consumed can be reimbursed via DAIO proposal.

### 19.4 Mass inheritance event

If a popular custodian experiences a key-loss event, many positions
may become simultaneously claimable by heirs. The protocol handles this
correctly (each position is independent), but:

- Monitor for spike in `InheritanceClaimed` events.
- If the spike is localised to one holder pattern (e.g. same custody
  contract), announce via DAIO channels to prevent panic.
- Check reserve sufficiency — a mass event can exercise the MTM curve
  near its lower bound, requiring the treasury to pay out principal
  while reserve upside accrues.

### 19.5 Stress-index manipulation attempt

If an attacker tries to manipulate oracles to trigger a specific regime
transition (e.g. to claim extreme MTM on a short position):

1. The confidence blending means they must move multiple sources
   simultaneously.
2. The freshness window bounds how long a stale bad value can influence
   the blend.
3. Keepers are incentivised to call `refresh` to squeeze out stale
   adversarial data.

If manipulation is detected, the DAIO can pause, widen the freshness
window (requiring more sources to agree), or temporarily raise
`minConfidence` to exclude low-confidence adversarial data.

## 20. Glossary

- **AgenticPlace** — the agent marketplace at
  `agenticplace.pythai.net` and its on-chain registry
  (`AgenticPlaceRegistry`).
- **AlgoIDNFT** — Algorand-native sovereign-identity NFT issued by
  BANKON.
- **BANKON** — the sovereign-identity service at `bankon.pythai.net`
  and its on-chain connector.
- **BONAFIDE** — the reputation model used in `AgenticPlaceRegistry`,
  with additive attestation and time decay.
- **Blended value** — confidence-weighted mean across all fresh
  adapters for a metric.
- **bps** — basis points, 1/100th of a percent. 10_000 bps = 100%.
- **Confidence** — 0..1e18 weight assigned by an adapter to its
  observation.
- **DAIO** — Decentralised Autonomous Intelligence Organisation, the
  governance entity controlling iDEBT parameters.
- **DELTAVERSE** — the umbrella ecosystem that contains iDEBT, mindX,
  AgenticPlace, BANKON, PYTHAI, and related projects.
- **Dormancy** — seconds of holder inactivity after which heirs can
  claim.
- **Freshness window** — maximum age allowed for an oracle observation
  before it's rejected.
- **GDSI** — Global Debt Stress Index, the 0..1e18 scalar.
- **Heartbeat** — holder action that refreshes `lastHeartbeat`.
- **Heir** — a named successor with a Merkle-committed address and
  share.
- **Logistic** — the sigmoid function used to squash metrics to
  `[0, 1e18]`.
- **Mark-to-market (MTM)** — the current value of a position based on
  the live stress index.
- **mindX** — the advisory API at `mindx.pythai.net` and its on-chain
  bridge (`MindXBridge`).
- **Parsec** — the facilitator at `parsec.finance` that settles x402
  Algorand payments and signs EIP-712 receipts.
- **Poke** — calling `GlobalDebtStressIndex.poke()` to recompute and
  store the latest snapshot.
- **Position** — an iDEBT ERC-721 token representing a single debt
  exposure.
- **Principal** — the settlement-token collateral locked at mint.
- **Refresh** — calling `DeltaVerseDebtOracle.refresh(metric)` to
  cache live adapter observations.
- **Regime** — discrete classification of the stress index: Calm,
  Elevated, Distress, Crisis, Default.
- **Settlement token** — the ERC-20 used for position collateral and
  payouts; typically USDC.
- **Stress mark** — the value of the stress index recorded at mint
  time; MTM formula's reference point.
- **WAD** — 18-decimal fixed-point unit, 1 WAD = 1e18.
- **x402** — the HTTP 402 payment-required protocol; iDEBT's gating
  mechanism using Parsec on Algorand.
