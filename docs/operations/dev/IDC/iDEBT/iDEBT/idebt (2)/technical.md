# iDEBT — Technical Reference

## 1. Conceptual model

iDEBT models **sovereign debt stress** as a single scalar in `[0, 1e18]`, the
**Global Debt Stress Index (GDSI)**. Every iDEBT position is minted at some
`stressMark` and settles against the live index. A holder's position is
therefore long or short debt stress depending on how `stressIndex - stressMark`
evolves over the position's life.

Three distinct timescales run concurrently:

| Timescale   | Mechanism                | Controlled by                |
| ----------- | ------------------------ | ---------------------------- |
| Seconds     | Oracle confidence blend  | `DeltaVerseDebtOracle`       |
| Minutes     | Index poke / freshness   | Keepers + `GlobalDebtStressIndex` |
| Days–years  | Position life, dormancy  | `iDEBT` holder + heirs       |
| Governance  | Parameter changes        | `DAIO` → `DAIOTreasury`      |

## 2. Oracle layer

### 2.1 Adapter contract

Each upstream source (Chainlink feed, Pyth price id, Synthetix V3 market) is
wrapped in an **adapter** that exposes a single method:

```solidity
function latest() external view returns (IDebtOracle.Observation memory);
```

`Observation` carries `(value, timestamp, confidence, source)` where:

- `value` is always normalised to **WAD (1e18)** — the adapter is responsible
  for handling its upstream's decimals/exponent.
- `confidence` is `[0, 1e18]`. Adapters may compute it from upstream
  signals — e.g. Chainlink linearly decays confidence from `WAD` at publish
  to `0` at the heartbeat deadline, Pyth uses `price / (price + conf)`.
- `source` is a `bytes32` identifier used to key storage inside
  `DeltaVerseDebtOracle`.

### 2.2 DeltaVerseDebtOracle

Governance-aware registry of adapters per metric. Two read paths:

- **`latest(metric)`** — returns the freshest observation above the minimum
  confidence floor. Reverts on `StaleObservation`.
- **`blended(metric)`** — returns the **confidence-weighted mean** of all
  fresh, above-floor observations:

  ```
  blended = Σ (value_i · conf_i) / Σ conf_i,   conf_i ≥ minConfidence
  ```

  Reverts if no qualifying observation exists.

Storage invariants:

- `_sources[sourceId]` is 1-to-1 with adapter address; re-registering a source
  overwrites.
- `_adapters[metric]` is a simple array; the same adapter may appear on
  multiple metrics (legitimate — e.g. one Pyth adapter may serve both real
  rate and DXY if configured with separate instances).

Admin (`ORACLE_ADMIN_ROLE`) is granted to the `DAIOTreasury` post-deploy;
only the treasury (via a DAIO proposal) may attach/revoke/freshness-tune.

### 2.3 Metric ↔ source mapping (reference wiring)

| Metric                | Chainlink                     | Pyth                                | Synthetix V3        |
| --------------------- | ----------------------------- | ----------------------------------- | ------------------- |
| `SovereignDebtGDP`    | custom feed (off-chain req.)  | —                                   | —                   |
| `CDS5Y`               | —                             | —                                   | CDS-market adapter  |
| `YieldCurveInversion` | 2s10s spread feed             | 10Y-2Y UST                          | —                   |
| `RealRate`            | 5Y TIPS feed                  | 5Y real yield                       | —                   |
| `DXY`                 | DXY index feed                | DXY price id                        | —                   |
| `VIX`                 | VIX index feed                | VIX price id                        | —                   |
| `GoldRatio`           | XAU/USD feed                  | XAU/USD                             | —                   |

This is a recommended wiring, not a hard requirement. Any combination of
adapters registered against a metric will be blended.

## 3. Global Debt Stress Index

### 3.1 Normalisation

Each metric's signed raw value is passed through a **logistic normaliser** to
produce a stress contribution in `[0, 1e18]`. The approximation used (`DebtMath.logistic`):

```
sigmoid(x) ≈ 0.5 + 0.5 · x / (4 + |x|)
```

chosen for gas (O(1), no exp) and ≤ 1% accuracy on `x ∈ [-6, 6]` WAD. Outside
that band the output saturates at 0 or 1e18. Each metric has its own
calibration baseline baked into a `_norm*` function:

| Metric              | Baseline (neutral)    | Direction that increases stress |
| ------------------- | --------------------- | ------------------------------- |
| SovereignDebtGDP    | 100% (`1e18`)         | higher                          |
| CDS5Y               | 1% (`0.01e18`)        | higher                          |
| YieldCurveInversion | 0 (flat)              | deeper inversion (negative)     |
| RealRate            | 0%                    | higher (disinflationary stress) |
| DXY                 | 100 (`1e18` @ 1:1)    | higher                          |
| VIX                 | 20                    | higher                          |
| GoldRatio           | 1.0                   | higher (risk-off flight)        |

### 3.2 Aggregation

Weighted sum with weights that must sum to exactly `1e18`:

```
index = Σ component_i · weight_i
```

Default weights (governance can change):

```
debtGDP 25% | cds 20% | yield 15% | real 10% | dxy 10% | vix 10% | gold 10%
```

### 3.3 Regime map

| Regime    | Index band      |
| --------- | --------------- |
| Calm      | `[0,    0.20)`  |
| Elevated  | `[0.20, 0.40)`  |
| Distress  | `[0.40, 0.60)`  |
| Crisis    | `[0.60, 0.80)`  |
| Default   | `[0.80, 1.00]`  |

Thresholds are strictly monotone; `setThresholds` enforces this.

### 3.4 Update path

- `poke()` recomputes and writes `_snap`; emits `IndexUpdated` and conditionally
  `RegimeTransition`. Callable by anyone.
- `score()` / `regime()` return recomputed values without writing — useful for
  read-only calls in MTM math.

## 4. iDEBT position contract

### 4.1 Position lifecycle

```
open → (heartbeat | service)* → (close | inheritance)
```

At `openPosition`:

1. `principal` + `fee` is pulled from the holder in the settlement token
   (typically USDC).
2. An ERC-721 is minted to the holder; `tokenId` is monotonic from 1.
3. The position records the current `stressIndex.score()` as `stressMark`.
4. `heirs[]` must total exactly 10_000 bps. The first heir's `proofRoot` is
   the authoritative Merkle root committing to the full heir set; subsequent
   heir structs reuse it (stored once per position).
5. If an `X402PaymentGateway` is wired (`setX402`), the holder must have a
   live receipt for `SCOPE_OPEN` or the call reverts with `PaymentRequired`.

### 4.2 Mark-to-market

Linear in Δstress:

```
Δ     = score_now − stressMark                 // signed WAD
factor = 1e18 − Δ                              // clamped ≥ 0
MTM    = principal · factor / 1e18             // clamped ≤ 2 · principal
```

Rationale: a 10 pp rise in stress (`Δ = 0.10e18`) pulls MTM to 90% of
principal; a 10 pp fall lifts it to 110%. The 2× cap prevents unbounded
windfalls from extreme regime collapses that are typically reversals rather
than durable gains.

### 4.3 Heartbeat & dormancy

Each position has a `dormancy` window (seconds). Any time the holder calls
`heartbeat`, `lastHeartbeat` is refreshed to `block.timestamp`. ERC-721
transfer also refreshes `lastHeartbeat` (via `_update`) so a deliberate
transfer resets the dormancy clock — transfers are an implicit proof-of-life.

An heir may call `claimInheritance` only if
`block.timestamp ≥ lastHeartbeat + dormancy`. Servicing a position
(`service`) explicitly does **not** refresh the heartbeat, because third
parties may service; the intent is that only the holder's own control
actions count as proof-of-life.

### 4.4 Inheritance proof

- `heirProof = abi.encode(address successor, uint16 sharesBps, bytes32[] merkleProof)`
- `leaf = keccak256(abi.encode(successor, sharesBps))`
- `MerkleProof.verify(proof, heirRoot, leaf)` must hold.
- Each heir can claim **once**; `_claimed[tokenId][leaf]` is set on successful
  verification.
- Each heir receives `MTM × sharesBps / 10_000`. Principal is reduced by
  `principal × sharesBps / 10_000`. When the last heir claims, principal
  reaches zero and the NFT is burned.

## 5. Integration surface

### 5.1 X402PaymentGateway (Parsec)

Off-chain payment flow (all non-EVM legs happen on Algorand):

```
client → gated endpoint (HTTP 402 + x-payment-required header)
client → parsec-wallet: pay amount in ALGO or USDCa
parsec-wallet → Parsec facilitator: submit tx
Parsec facilitator → client: EIP-712 signed Receipt
client → X402PaymentGateway.consume(r, sig)
client → gated on-chain call (e.g. iDEBT.openPosition)
```

Validation in `consume`:

- `facilitators[r.facilitator]` must be true.
- `block.timestamp ≤ r.expiry`.
- `usedNonces[r.payer][r.nonce]` must be false.
- `scopePrice[r.scope] > 0` and `r.amount ≥ scopePrice`, `r.asset == scopeAsset`.
- ECDSA recover of the EIP-712 digest must equal `r.facilitator`.

Post-validation:

- `usedNonces[r.payer][r.nonce] = true`
- `_paidUntil[r.payer][r.scope] = r.expiry`

`hasPaid(payer, scope)` returns `_paidUntil[payer][scope] >= block.timestamp`.

### 5.2 MindXBridge

Records EIP-712 signed advisory attestations from the mindX API. The bridge
stores only the **last** score per subject; historical scores are the
responsibility of the off-chain archive at `mindx.pythai.net`. Replay is
prevented by the `requestId` consumed-set.

### 5.3 AgenticPlaceRegistry

BONAFIDE-style reputation:

- Agents self-register; the caller becomes `owner`.
- `ATTESTER_ROLE` can award reputation (`attest`).
- `SLASHER_ROLE` can burn reputation.
- Reputation decays at `decayBps` (default 1%) per `DECAY_INTERVAL`
  (30 days). Decay is applied lazily — reads compute a projected reputation;
  writes also persist the decay.

### 5.4 BANKONConnector

Binds an Algorand AlgoIDNFT sovereign-identity commitment (`algoIdRoot`) to
an EVM wallet:

1. User requests binding from BANKON; receives an ECDSA signature over
   `keccak256(algoIdRoot, msg.sender, block.chainid)` under the EIP-191
   personal-sign prefix.
2. User calls `bind(algoIdRoot, sig)` on the connector; the contract
   recovers the signer and accepts only `bankonSigner`.
3. The binding is permanent until the user calls `revoke()`; one algoIdRoot
   ↔ one EVM wallet at a time.

iDEBT does not **require** a BANKON binding, but heirs/integrators may
choose to refuse interactions with unbound holders.

## 6. Governance

Standard OpenZeppelin Governor stack:

- **`iDEBTVoteToken`** — ERC20Votes with `MINTER_ROLE` that can be renounced
  after initial distribution.
- **`DAIO`** — Governor with `GovernorSettings` (`votingDelay`,
  `votingPeriod`, `proposalThreshold`), `GovernorVotes`,
  `GovernorVotesQuorumFraction` (default 20%), `GovernorCountingSimple`, and
  `GovernorTimelockControl`.
- **`DAIOTreasury`** — `TimelockController` with `minDelay`
  (`DAIO_TIMELOCK_DELAY`, default 2 days). The treasury is the **only**
  holder of the admin roles on every other contract in the system. The
  deployer's roles are transferred to the treasury during `Deploy.run` and
  renounced after verification.

## 7. Invariants

The test suite (and the forthcoming invariant suite under `test/invariant/`)
enforces:

1. `Σ weights_i == 1e18` (`GlobalDebtStressIndex`).
2. `index ∈ [0, 1e18]` at all times.
3. Oracle reads revert on any stale-above-freshness observation.
4. `iDEBT.markToMarket(id) ≤ 2 × principal_id`.
5. For any position, `Σ_heirs sharesBps == 10_000` at mint and per-heir
   `_claimed[id][leaf]` is set ≤ 1 time.
6. `X402PaymentGateway.usedNonces[payer][nonce]` is monotonically set; once
   true it never becomes false.
7. Only the `DAIOTreasury` holds the admin role across the system after
   deployment wiring is complete.

## 8. Gas & opcode notes

- Via-IR on, `optimizer_runs = 1_000_000`, `evm_version = cancun`.
  The chains that don't yet support Cancun opcodes (`MCOPY`, transient
  storage) are excluded in `ChainMapping` or require a compatibility rebuild
  with `evm_version = shanghai`.
- `GlobalDebtStressIndex._compute` reads 7 blended oracle values per call.
  With three adapters per metric that's up to 21 adapter reads — keepers
  should call `oracle.refresh(metric)` between oracle chain-updates and
  index pokes rather than hot-path every read.

## 9. Audit surface & open questions

- Oracle calibration constants inside `GlobalDebtStressIndex._norm*` are
  hard-coded. Governance can change weights and thresholds but not the
  per-metric scaling; future versions may move these into storage.
- `iDEBT.markToMarket` uses a simple linear transform of `Δstress`.
  Alternative curves (convex, regime-conditional) can be explored once the
  protocol has enough historical index data.
- The x402 `Receipt` carries an `algoTxId` but the contract cannot verify it
  against the Algorand chain directly; the assumption is that Parsec
  facilitators will not sign off receipts for unsettled Algo txs, which is
  a trust assumption documented in `deploy.md`.
