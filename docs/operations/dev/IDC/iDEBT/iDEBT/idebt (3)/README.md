# iDEBT — Cryptographic Inheritance of Global DEBT

> A tokenised debt instrument whose mark-to-market value is driven by a
> confidence-blended Global Debt Stress Index, governed by a DAIO, and whose
> holders can encode cryptographic succession through Merkle-committed heirs.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Solidity 0.8.24](https://img.shields.io/badge/solidity-0.8.24-blue)](./foundry.toml)
[![Foundry](https://img.shields.io/badge/built_with-Foundry-orange)](https://getfoundry.sh)

---

## What iDEBT is

iDEBT is a DELTAVERSE protocol that turns exposure to global debt stress into
a transferable, inheritable ERC-721 position. Each position is minted against
a principal of settlement stablecoin, marked at the time's stress index, and
pays the holder (or their cryptographically-named heirs) according to how
debt stress evolves over the position's life.

Three pillars:

1. **DeltaVerseDebtOracle** — a governance-registered set of adapters
   (Chainlink, Pyth, Synthetix V3, and any other `IAdapter`) blended by
   confidence into a single value per metric.
2. **GlobalDebtStressIndex** — a seven-component, weight-sum 0..1e18 index
   deriving a discrete regime (`Calm → Elevated → Distress → Crisis → Default`).
3. **iDEBT ERC-721** — positions with heartbeat-based dormancy and Merkle-
   committed heirs; closing, servicing, and inheritance all mark-to-market
   against the stress index.

Surrounding the core:

- **DAIO governance** — OZ Governor + TimelockController controlling oracle
  wiring, weights, thresholds, and fees.
- **AgenticPlaceRegistry** — ERC-8004-style agent reputation (advisors /
  underwriters / automated heirs) backed off-chain by
  [agenticplace.pythai.net](https://agenticplace.pythai.net).
- **MindXBridge** — settles EIP-712 attestations from the mindX API
  ([mindx.pythai.net](https://mindx.pythai.net)).
- **BANKONConnector** — binds Algorand AlgoIDNFT sovereign identities to
  EVM wallets via co-signed commitments.
- **X402PaymentGateway** — consumes Parsec-facilitator-signed EIP-712
  receipts for x402 payments executed on Algorand (via
  [parsec-wallet](https://parsec.finance)), gating the stack's mutating ops.

## Repo layout

```
idebt/
├── src/
│   ├── core/            DeltaVerseDebtOracle, GlobalDebtStressIndex, iDEBT
│   ├── oracles/         Chainlink / Pyth / Synthetix V3 adapters
│   ├── integrations/    X402PaymentGateway, MindXBridge, AgenticPlaceRegistry, BANKONConnector
│   ├── governance/      DAIO, DAIOTreasury
│   ├── tokens/          iDEBTVoteToken (ERC20Votes)
│   ├── interfaces/      Seven I* interfaces defining the external surface
│   └── libraries/       DebtMath, ChainMapping
├── test/                Foundry tests (unit, fuzz, integration)
├── script/deploy/       Deploy.s.sol, Configure.s.sol, DeployTestnet.s.sol
├── api/                 TypeScript clients for mindX, AgenticPlace, BANKON
├── frontend/            React UI (stress index, inheritance form, chain map, x402 flow)
├── technical.md         Architecture & invariants
├── usage.md             End-user / integrator guide
├── deploy.md            Deployment runbook
└── foundry.toml
```

## Quick start

```bash
# 1. Install toolchain
curl -L https://foundry.paradigm.xyz | bash && foundryup
npm install

# 2. Install Solidity deps
forge install openzeppelin/openzeppelin-contracts@v5.0.2 --no-commit
forge install foundry-rs/forge-std --no-commit
forge install smartcontractkit/chainlink@v2.14.0 --no-commit
forge install pyth-network/pyth-sdk-solidity --no-commit

# 3. Build & test
forge build
forge test -vv

# 4. Deploy to Sepolia
cp .env.example .env && $EDITOR .env   # fill in keys
npm run deploy:sepolia
npm run configure
```

## Documentation

- [**explanation.md**](./explanation.md) — comprehensive conceptual
  walkthrough and complete deployment guide. Start here if you're new
  to the project.
- [**technical.md**](./technical.md) — architecture, storage layout, invariants,
  oracle-blending math, and regime thresholds.
- [**usage.md**](./usage.md) — opening positions, heartbeat/dormancy,
  inheritance flow, x402 payment flow, API reference.
- [**deploy.md**](./deploy.md) — per-chain deployment runbook (mainnet,
  Polygon, Arbitrum, Optimism, Base, Arc, Sepolia) including post-deploy
  oracle wiring and role transfer to the DAIO.

## Supported chains

EVM mainnet deployment is supported on: Ethereum, Polygon PoS, Polygon zkEVM,
Arbitrum One, Optimism, Base, BSC, Avalanche C-Chain, zkSync Era, Fantom,
Arc Network. Non-EVM sovereign-identity binding via BANKON is supported
through Algorand (mainnet + testnet). See
[`src/libraries/ChainMapping.sol`](./src/libraries/ChainMapping.sol) for the
canonical table.

## Security disclosure

Security disclosures should be sent to security@pythai.net encrypted to the
PGP key published at [pythai.net/.well-known/security](https://pythai.net/.well-known/security).

## License

MIT © DELTAVERSE / PYTHAI. See [LICENSE](./LICENSE).
