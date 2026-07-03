# DELTAVERSE Debt Inheritance Protocol

**A production DeFi system for expressing inverse positions against the global debt complex.**

This repository contains the complete source code, off-chain infrastructure, observability layer, and audit preparation materials for the DELTAVERSE Debt Inheritance Protocol. The protocol implements the academic thesis developed across three companion papers in the `docs/` directory: that the global debt system has become structurally unsustainable, that tokenization combined with on-chain derivatives creates a mechanism for the system to fund its own inversion, and that a single capstone contract composed of four primitives plus an oracle is sufficient to turn that mechanism into an executable market.

## What this repository contains

The repository is organized into layers, and each layer exists because production DeFi requires more than just audited Solidity. The contracts in `src/` are the core protocol. The governance contracts in `src/governance/` decide who can change the core protocol and on what timeline. The keepers in `keepers/` perform the off-chain work that makes passive contracts into an active protocol. The subgraph in `subgraph/` turns raw on-chain events into queryable analytics. The audit materials in `audit/` prepare the codebase for third-party security review. The infrastructure files at the root coordinate all of it through Docker Compose and Prometheus. Reading the layers in that order gives you the mental model of how a production DeFi protocol is actually structured, and why each piece is necessary.

## The Inverse Debt Layer

Four additional contracts extend the base protocol with explicit Bitcoin-anchored profit-from-loss mechanics: `BitcoinAnchorOracle` (multi-source BTC/USD oracle), `DebasementIndex` (composite measure of fiat debasement combining GDSI and BTC), `InverseDebtToken` (the iDEBT synthetic that mints at the current debasement index and redeems at the new one), and `BitcoinProfitRecognizer` (atomic router that converts existing sGDSI positions into iDEBT in a single transaction). Together they solve the numeraire problem in the base protocol — that USDC-denominated gains during debasement understate real purchasing-power profit — by using Bitcoin as the hard-money anchor. See `INVERSE_DEBT.md` for the full architecture, the math, and the end-to-end user flow.

## The core contracts

The `src/` directory contains five operational contracts plus three governance contracts. The operational contracts are the economic machinery: `RWAToken.sol` tokenizes an off-chain debt instrument with KYC-gated transfers and yield distribution, `CrossCollateralVault.sol` accepts multiple collateral types and issues stablecoin loans against them, `PerpetualEngine.sol` runs leveraged long and short positions with automated funding rates and an insurance fund, `DeltaVerseDebtOracle.sol` aggregates five sub-indices into a composite Global Debt Stress Index using Synthetix V3 oracle manager patterns, and `DebtInheritanceProtocol.sol` is the capstone orchestrator that composes the other four into the recursive debt inheritance flow while also serving as the ERC-20 contract for the sGDSI synthetic stress index token.

The governance contracts in `src/governance/` are the trust boundary of the protocol. `DeltaVerseTimelock.sol` enforces a minimum delay between when a parameter change is proposed and when it takes effect, giving users time to exit if they disagree. `DeltaVerseGovernor.sol` runs token-weighted proposals and voting using the OpenZeppelin Governor framework and queues passing proposals in the Timelock. `EmergencyPauser.sol` provides a separate fast path for pausing the protocol during an active incident without waiting for the governance delay, controlled by a multisig of guardians whose only power is pausing.

## Quick start

The protocol uses Foundry as its development toolchain, and the off-chain infrastructure uses Node.js 20 or higher. To build and test the contracts from a fresh checkout:

```bash
forge install foundry-rs/forge-std
forge install OpenZeppelin/openzeppelin-contracts
forge install pyth-network/pyth-sdk-solidity
forge build
forge test -vvv
```

To deploy the stack to a testnet or mainnet, populate the environment variables expected by `script/Deploy.s.sol` and broadcast. The script deploys all five operational contracts in the correct dependency order and prints a post-deployment checklist of the wiring steps that must be performed through governance proposals. Do not skip the checklist items; several of them are security-critical, particularly the step that transfers `DEFAULT_ADMIN_ROLE` from the deployer to the Timelock.

```bash
export PRIVATE_KEY=0x...
export ADMIN_ADDRESS=0x...
export STABLECOIN_ADDRESS=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
export PYTH_ADDRESS=0x4305FB66699C3B2702D4d05CF36551390A4c69C6
forge script script/Deploy.s.sol:Deploy --rpc-url mainnet --broadcast --verify
```

After the contracts are deployed, the off-chain keepers need to be started so that the protocol can actually function. The keepers live in the `keepers/` directory and run as a set of four independent bots. Copy the environment template, populate it with your deployment's contract addresses and keeper private key, and start the stack through Docker Compose:

```bash
cp .env.example .env
# Edit .env with real values
docker compose up -d
docker compose logs -f
```

The four keepers will immediately begin their work. The Pyth updater will start pulling signed price data from the Hermes API every sixty seconds. The sub-index finalizer will wait four hours and then aggregate whatever reporter data has accumulated. The fee router will check hourly for accumulated fees above the routing threshold. The liquidator will scan its watchlist every thirty seconds for underwater positions.

## The thesis in executable form

The signature function of the protocol is `expressThesis()` on the capstone contract. It accepts five parameters: the RWA token to use as collateral, the RWA amount, the stablecoin amount to borrow against it, the leverage multiplier, and whether the thesis is long (betting stress will rise) or short (betting stress will fall). In a single atomic transaction, it pulls the RWA collateral from the user, deposits it into the vault, borrows the requested stablecoin amount against the deposit, and opens a leveraged position on the Global Debt Stress Index via the perpetual engine. If the thesis is correct, the leveraged position profits by more than the collateral erodes, and the function `closeThesis()` unwinds the entire structure when the user wants to realize their gains. This is the recursive debt inheritance in executable form: the debt system itself becomes the fuel for shorting the debt system.

For users who want unlevered exposure without the complexity of the full thesis flow, the protocol also exposes `mintSGdsi()` and `burnSGdsi()`. These functions accept stablecoin deposits and issue sGDSI tokens at the current oracle price. When the index rises, burning sGDSI returns more stablecoin than was deposited (less fees), and the reverse when the index falls. This is the passive version of the thesis, suitable for users who want stress-index exposure without managing leverage.

## Fees and the economic loop

Every protocol action charges a small fee, which accumulates in the `pendingFees` counter on the capstone contract. The fee router keeper periodically calls `routeFees()` when the accumulated amount crosses a gas-profitable threshold, which moves the fees into the LP staking pool built into the oracle contract. Stakers in that pool earn pro-rata rewards from routed fees, which gives them an economic incentive to stake alongside the oracle and, implicitly, to verify that the oracle's data quality is good. This is the economic closure of the protocol: traders pay fees, fees fund oracle LP stakers, LP stakers back oracle credibility with their collateral, and accurate measurement enables more trading.

## Governance and the trust model

After deployment, no externally owned account should hold admin roles on any protocol contract. All five operational contracts should have their `DEFAULT_ADMIN_ROLE` transferred to the `DeltaVerseTimelock`, which can only execute changes that have been proposed through the `DeltaVerseGovernor`, passed a token-weighted vote, and waited out the Timelock delay. The total end-to-end governance cycle from proposal to execution is approximately ten days under the default settings, which is long enough to allow informed community participation and short enough to respond to changing conditions.

The one exception to this delay is the `EmergencyPauser`, which holds its own pause roles on the protocol contracts and can pause everything in a single guardian-signed transaction. The pauser cannot change parameters, cannot move funds, and cannot unpause without the Timelock's approval. It exists solely as a fast-path brake for active incidents, and the cooldown enforced on unpausing ensures that a panicked or compromised guardian cannot cause structural damage.

The governance token is expected to be THRUST once it implements the `IVotes` interface, but the Governor contract is agnostic to which token is used and accepts any ERC20Votes-compatible token. During the initial deployment phase, a multisig may hold governance authority as a placeholder until the token transition is complete. This path is documented in the known issues file in the `audit/` directory.

## Observability through the subgraph

The `subgraph/` directory contains a complete The Graph Protocol subgraph that indexes all protocol events and maintains derived analytics. It tracks individual mint and burn events, aggregate protocol state, per-user activity, LP staking positions, thesis position lifecycles, hourly OHLC aggregates of the GDSI composite, and historical oracle snapshots. The subgraph is what powers the dashboard at `agenticplace.pythai.net` and what lets analysts study the protocol's history without running their own indexer. Deploy the subgraph with:

```bash
cd subgraph
npm install
npm run codegen
npm run build
npm run deploy
```

The subgraph entities are documented in `subgraph/schema.graphql`, and the mapping handlers that populate them from on-chain events are in `subgraph/src/mappings/`. A pattern worth understanding in the mappings is the hourly aggregate entity, which lets dashboards query daily or weekly time series without scanning individual events.

## Security and audit preparation

The `audit/` directory contains everything a third-party security firm needs to begin a review of the protocol. The scope document explains the contract inventory, trust model, invariants, and attack surface. The known issues document discloses the design compromises the team is already aware of so that the auditor can focus their time on genuinely unknown risks. The Slither configuration is tuned to the codebase with appropriate detector exclusions, and the Mythril configuration is prepared for symbolic execution of the critical contracts. Running the static analysis toolchain against the source is the first pass of any serious audit workflow:

```bash
slither . --config-file audit/slither.config.json
myth analyze src/DebtInheritanceProtocol.sol --solc-json audit/mythril-solc.json
```

The known issues file lists ten design compromises that the team has accepted as reasonable tradeoffs for the current phase. Each entry explains what the compromise is, why it was accepted, and what conditions would cause the team to revisit the decision. Auditors reviewing the codebase should start by reading the scope document, then the known issues, then the contracts themselves, and finally the tests. In that order the codebase should feel like a well-organized system rather than a pile of files.

## Project structure

```
debt-inheritance/
├── src/
│   ├── RWAToken.sol
│   ├── CrossCollateralVault.sol
│   ├── PerpetualEngine.sol
│   ├── DeltaVerseDebtOracle.sol
│   ├── DebtInheritanceProtocol.sol
│   └── governance/
│       ├── DeltaVerseTimelock.sol
│       ├── DeltaVerseGovernor.sol
│       └── EmergencyPauser.sol
├── test/
│   └── DebtInheritanceProtocol.t.sol
├── script/
│   └── Deploy.s.sol
├── keepers/
│   ├── src/
│   │   ├── config.ts
│   │   ├── pythUpdater.ts
│   │   ├── subIndexFinalizer.ts
│   │   ├── feeRouter.ts
│   │   ├── liquidator.ts
│   │   └── index.ts
│   ├── package.json
│   ├── tsconfig.json
│   └── Dockerfile
├── subgraph/
│   ├── schema.graphql
│   ├── subgraph.yaml
│   ├── src/mappings/
│   │   ├── protocol.ts
│   │   └── oracle.ts
│   └── package.json
├── audit/
│   ├── SCOPE.md
│   ├── KNOWN_ISSUES.md
│   ├── slither.config.json
│   └── .mythril.yml
├── monitoring/
│   └── prometheus.yml
├── docs/
│   ├── global_debt_thesis.docx
│   ├── cryptographic_inheritance.docx
│   └── recursive_proof_part3.docx
├── docker-compose.yml
├── .env.example
├── foundry.toml
├── FRONTEND_INTEGRATION.md
└── README.md
```

## References

The intellectual antecedents of this protocol are worth acknowledging directly because they shaped the design at every level. The Synthetix V3 architecture inspired the oracle manager pattern used to compose multiple data sources into a single synthetic feed. The Compound V2 protocol pioneered the close factor cap and health factor mechanics used in the cross-collateral vault. The dYdX v3 and GMX funding rate models informed the perpetual engine's funding calculation, though our implementation is deliberately simpler to match the protocol's scale. The OpenZeppelin Governor framework provides the voting and timelock infrastructure, and the OpenZeppelin Contracts library provides the ERC-20, AccessControl, and ReentrancyGuard primitives throughout. The Pyth Network pull oracle model is what makes cross-chain deployment feasible, and the Hermes API is how keepers fetch the signed price data that the on-chain Pyth contract verifies.

## License

MIT

---

**Built by Professor Codephreak**
**DELTAVERSE Ecosystem • PYTHAI Platform • BANKON Infrastructure**

*The thesis is diagnosed. The contracts are written. The governance is delegated.*
*The keepers run. The subgraph indexes. The audit is scoped.*
*What remains is deployment.*
