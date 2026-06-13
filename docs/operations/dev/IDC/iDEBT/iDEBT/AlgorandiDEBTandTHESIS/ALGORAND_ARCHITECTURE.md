# Algorand Architecture: From Synthetix V3 to Production RWA

## What This Architecture Makes Possible

This blueprint translates Synthetix V3's battle-tested modular liquidity architecture into a deployment-ready RWA protocol on Algorand — a chain that already leads in production RWA tokenization. Three architectural insights emerge that go beyond simple mapping.

First, Algorand's atomic transaction groups solve the composability problem differently than EVM. Where Synthetix V3 uses a Router Proxy to merge contracts into a monolithic super-contract, Algorand's native 16-transaction atomic groups and 256-inner-transaction capability enable the same composability through coordinated multi-contract execution. This is architecturally cleaner and avoids the 24KB workaround entirely.

Second, the pull oracle model is mandatory for RWA on Algorand. Without native Chainlink, the rwa.oracle hub must implement a hybrid push-pull model: oracle runners push periodic attestations (push for base freshness), while consumers can request on-demand updates for time-sensitive operations (pull for transaction-time accuracy). The circuit breaker DAG from Synthetix's Oracle Manager translates directly into box-storage-based configuration per feed.

Third, the DELTAVERSE integration stack fills the compliance gap that pure DeFi protocols ignore. The combination of AlgoIDNFT (identity), BONAFIDE (reputation), DAIO (governance), and x402 (payments) creates a full-stack compliance infrastructure that maps to ERC-3643's ONCHAINID model but using Algorand-native primitives. This is the difference between a DeFi protocol that tokenizes RWA and a regulated financial product that uses blockchain rails — the latter is what institutional adoption requires, and this architecture provides it.

---

## Deployment Stages

The protocol deploys across four stages. Each stage is a self-contained deployment that can be tested and verified independently before the next stage is added.

### Stage 1: Core Measurement (5 contracts)

**RWA Controller** (`rwa_controller.py`) — manages the lifecycle of a tokenized sovereign debt ASA. Unlike the EVM `RWAToken.sol` which extends ERC-20 with compliance overrides, this contract does not replicate the token — it manages the ASA's lifecycle through Algorand's native asset-control primitives. Setting the contract as the ASA's freeze address means compliance enforcement happens at the consensus layer rather than in contract code. Every holder starts frozen (ASA `default_frozen=True`) until whitelisted by the compliance officer or admin.

**RWA Oracle Hub** (`rwa_oracle_hub.py`) — hybrid push-pull oracle implementing the circuit breaker pattern from Synthetix's Oracle Manager. Five sub-indices representing dimensions of debt stress are stored in BoxMap with per-feed configuration for staleness, deviation bounds, and reporter authorization. Oracle runners push periodic attestations for base freshness; consumers can request synchronous updates for transaction-time accuracy. EMA smoothing and stress-level classification (0-5) are computed on-chain. The deviation circuit breaker stages excessive moves for governor approval rather than applying them directly — the single most important safety feature in the oracle layer.

**Sovereign Debt Registry** (`sovereign_debt_registry.py`) — on-chain registry of per-country sovereign debt providing basket weights. Each country record lives in BoxMap keyed by 3-byte ISO 4217 currency codes. Seeded with five major debt-issuing currencies (USD $38.3T, EUR $21T, CNY $18.7T, JPY $9.8T, GBP $3.5T) totaling $91.3 trillion. Weight computation is on-read, so quarterly reporter updates automatically re-weight the basket. A 20% deviation circuit breaker on debt updates prevents reporter-error blowups.

**Global Currency Basket** (`global_currency_basket.py`) — aggregates per-currency fiat-vs-BTC ratios into a single weighted index of global fiat strength relative to Bitcoin. Weights come from the SovereignDebtRegistry. The basket reads FX rates and BTC price from the Oracle Hub via sub-index references. Because the full basket computation can exceed single-call opcode budgets on Algorand, the caller pre-fetches current prices and weights and passes them in. The contract validates structural integrity and computes the weighted fiat debasement index.

### Stage 2: Derivatives (4 contracts)

**Collateral Vault** (`collateral_vault.py`) — multi-asset vault accepting whitelisted ASAs as collateral. Deposits happen via atomic groups where the user submits an asset-transfer AND an app-call in the same group. The contract verifies the companion transfer via `gtxn` inspection. Health factor computation pulls prices from the oracle hub. Liquidations use a 50% close factor with 5% bonus, matching the Aave/Compound model.

**Perpetual Engine** (`perpetual_engine.py`) — 24/7 leveraged positions against the GDSI oracle, max 20x leverage. One-position-per-trader model with insurance fund for socialized losses. Funding rate accrues per-timestamp (not per-block as on EVM) and is computed at settlement time from the stored rate rather than updating continuously, saving box writes.

**Debt Inheritance Coordinator** (`debt_inheritance_coordinator.py`) — the capstone. Orchestrates the full recursive inheritance flow via atomic group. On EVM, `expressThesis()` makes four sequential internal calls within one transaction. On Algorand, the same atomicity is provided by the chain itself: the user submits an atomic group containing asset transfers and app calls to vault, perp, and coordinator, and the group either commits entirely or fails entirely. The coordinator also issues the sGDSI ASA and manages mint/burn against the oracle composite.

**Inverse Debt Token** (`inverse_debt_token.py`) — iDEBT synthetic ASA implementing the profit-from-loss mechanic. Users mint iDEBT by depositing stablecoin at the current debasement index; they burn to receive stablecoin at the new index. If the index rose between mint and burn, the user profits. Proportional haircut under insolvency rather than revert. The debasement index is reported by authorized reporters who read it from the basket layer, matching the push oracle pattern.

### Stage 3: Compliance (1 contract)

**Compliance Integrator** (`compliance_integrator.py`) — queries the four DELTAVERSE subsystems:
- **AlgoIDNFT** — sovereign identity NFTs carrying jurisdiction and accreditation credentials
- **BONAFIDE** — reputation tokens reflecting on-chain history (settled trades, repaid loans, governance participation)
- **DAIO** — Decentralized Autonomous Investment Organization governance
- **x402** — HTTP-402-compliant micropayment rails for protocol fees and bridge tolls

The integrator queries these subsystems by app-ID reference, caching compliance results with a configurable TTL (default 1 hour) to avoid redundant cross-contract calls. This maps to ERC-3643's ONCHAINID compliance model using Algorand-native primitives.

### Stage 4: Cross-Chain Bridge (1 contract)

**Wormhole Bridge** (`wormhole_bridge.py`) — bridges tokenized RWA from Algorand to EVM chains where the iDEBT derivatives infrastructure lives. Uses Wormhole's 19-guardian, 13-of-19 threshold model. Bridge-out locks ASA and emits VAA payload. Bridge-in verifies VAA via companion Wormhole core call. Per-asset 24-hour epoch limits prevent full-drain scenarios. Replay protection via consumed VAA hash tracking in BoxMap.

The companion EVM contract `WormholeRwaReceiver.sol` mints wrapped ERC-20 RWA tokens from verified VAAs, which can be deposited into the CrossCollateralVault as collateral for iDEBT.

---

## Architectural Patterns: EVM vs Algorand

### Composability

On EVM, Synthetix V3 merges dozens of "modules" into a single proxy contract (the Router Proxy pattern) to achieve composability within one transaction. This works but creates a monolithic deployment that approaches the 24KB EVM contract size limit and makes auditing harder because every module shares the same storage namespace.

On Algorand, composability comes from the chain itself. Atomic transaction groups allow up to 16 transactions to commit or fail as a unit. Each contract can remain small, focused, and independently auditable. The `expressThesis` flow that requires four contract calls on EVM (pull RWA, deposit into vault, borrow, open perp) is expressed as a 5-transaction atomic group on Algorand where each contract does its one job and the chain enforces atomicity.

The 256-inner-transaction capability extends this further. A single app call can trigger up to 256 inner transactions, enabling batch operations like yield distribution to hundreds of holders in a single outer call. On EVM, this would require either a loop within one transaction (bounded by gas) or a multicall wrapper.

### Oracle Architecture

On EVM, Chainlink provides push-based price feeds that are always available for on-chain reads. The protocol's oracle layer can aggregate multiple Chainlink feeds by reading them in a single view function.

On Algorand, there are no native Chainlink aggregators. The Oracle Hub implements the hybrid push-pull model explicitly: authorized reporters push attestations into box storage at regular intervals (providing base freshness), and consumers can trigger synchronous updates via app calls when they need guaranteed freshness for a specific operation. The circuit breaker pattern from Synthetix's Oracle Manager — where excessive deviations are staged for governor approval rather than applied directly — translates into per-feed box-storage configuration with threshold checks.

For the Global Currency Basket, the computational overhead of reading 5+ oracle sub-indices, computing per-currency BTC ratios, weighting by registry, and producing the aggregate exceeds a single app call's opcode budget. The architecture handles this by having keepers pre-compute the basket value off-chain and submit it as a reported value, with the on-chain contract validating the structural integrity (correct number of currencies, non-zero weights, non-zero prices) rather than re-deriving the computation.

### Compliance

ERC-3643's ONCHAINID stores claims about an identity in an on-chain registry queried by the token contract before every transfer. The DELTAVERSE compliance integrator achieves the same result using Algorand-native primitives. AlgoIDNFT replaces the ONCHAINID registry with ASA-based identity tokens whose metadata carries jurisdiction and accreditation claims. BONAFIDE replaces the reputation module with a standalone scoring protocol. DAIO replaces the governance module with a purpose-built DAO infrastructure. x402 adds the payment rails that pure compliance protocols lack.

The compliance integrator itself is a lightweight query contract — it does not reimplement any subsystem. It reads public state from each subsystem by app-ID reference and caches results to avoid redundant cross-contract calls. This separation of concerns means each subsystem can be upgraded independently without touching the RWA protocol stack.

---

## Cross-Chain Flow: Algorand → EVM iDEBT

The complete flow from tokenized RWA on Algorand to iDEBT exposure on EVM:

1. **Algorand**: User locks N units of RWA ASA via atomic group with `wormhole_bridge.bridge_out()`
2. **Algorand**: Bridge emits Wormhole VAA containing source chain (8), asset ID, amount, destination (2), recipient
3. **Off-chain**: Wormhole guardians (19 validators) sign the VAA; 13-of-19 threshold required
4. **Relayer**: Submits signed VAA to EVM Wormhole core bridge for verification
5. **EVM**: `WormholeRwaReceiver.receiveAndMint()` verifies VAA, checks epoch limits, mints wrapped ERC-20 RWA
6. **EVM**: User deposits wrapped RWA into `CrossCollateralVault` as collateral
7. **EVM**: User borrows stablecoin against RWA collateral, mints iDEBT via `InverseDebtToken`
8. **EVM**: As the debasement index rises, user's iDEBT redemption value increases

Reverse flow (EVM → Algorand) burns wrapped RWA on EVM, emits a Wormhole message, and unlocks the original ASA on Algorand.

---

## File Manifest

```
algorand/
├── contracts/
│   ├── stage1_core/
│   │   ├── rwa_controller.py          (379 lines) — ASA lifecycle + compliance
│   │   ├── rwa_oracle_hub.py          (367 lines) — hybrid push-pull oracle
│   │   ├── sovereign_debt_registry.py (200 lines) — per-country debt weights
│   │   └── global_currency_basket.py  (230 lines) — multi-currency fiat-vs-BTC
│   ├── stage2_derivatives/
│   │   ├── collateral_vault.py        (399 lines) — multi-asset vault
│   │   ├── perpetual_engine.py        (341 lines) — leveraged perps
│   │   ├── debt_inheritance_coordinator.py (333 lines) — sGDSI + thesis
│   │   └── inverse_debt_token.py      (310 lines) — iDEBT synthetic
│   ├── stage3_compliance/
│   │   └── compliance_integrator.py   (331 lines) — DELTAVERSE integration
│   └── stage4_bridge/
│       └── wormhole_bridge.py         (375 lines) — cross-chain Wormhole
├── tests/
│   ├── test_rwa_controller.py         — ASA lifecycle tests
│   ├── test_oracle_hub.py             — push-pull oracle tests
│   ├── test_basket.py                 — registry + basket tests
│   ├── test_inverse_debt.py           — iDEBT mint/burn/profit tests
│   ├── test_vault.py                  — collateral vault tests
│   ├── test_perp.py                   — perpetual engine tests
│   ├── test_bridge.py                 — Wormhole bridge tests
│   ├── test_compliance.py             — DELTAVERSE integrator tests
│   └── test_cross_stack.py            — end-to-end integration tests
├── scripts/
│   └── deploy.py                      — AlgoKit stage-based deployment
├── docs/
│   ├── ALGORAND_ARCHITECTURE.md       — this document
│   └── CROSS_CHAIN.md                 — Wormhole flow specification
└── pyproject.toml                     — AlgoKit project config
```

---

## Conclusion

This architecture demonstrates three things that a naive "port the Solidity to Algorand" approach would miss.

The composability difference is not cosmetic — it is structural. Algorand's atomic groups provide the same all-or-nothing semantics as a single EVM transaction, but without forcing all logic into one contract. Each contract remains small, focused, and independently auditable. The 16-transaction group limit is generous for the thesis flow (which needs 5 transactions) and the 256-inner-transaction capability handles batch operations that would require gas-bounded loops on EVM.

The oracle difference is not a limitation — it is an opportunity. The hybrid push-pull model gives the protocol two temporal resolutions: base freshness from periodic push attestations and transaction-time accuracy from on-demand pulls. EVM protocols that rely on Chainlink push feeds alone get only one resolution and have no mechanism for consumers to request fresher data at the moment they need it.

The compliance difference is not optional — it is what separates a toy from a product. Every institutional RWA deployment in 2025-2026 requires KYC/AML integration, accredited-investor verification, and regulatory reporting. The DELTAVERSE stack (AlgoIDNFT + BONAFIDE + DAIO + x402) provides this using Algorand-native primitives that are cheaper, more composable, and more aligned with the chain's existing institutional adoption trajectory than any EVM-based compliance bolt-on.

The protocol is deployment-ready. The contracts are written. The tests cover every critical path. The cross-chain bridge connects the Algorand RWA infrastructure to the EVM iDEBT derivatives layer. What remains is the act of pushing the transactions to chain.
