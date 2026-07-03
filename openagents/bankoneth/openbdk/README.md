# openBDK Bridge Contracts

> **The bridge that doesn't fail.** Cross-chain liquidity contracts for openBDK chains, derived from Polygon's canonical AggLayer Unified Bridge architecture.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Solidity 0.8.23](https://img.shields.io/badge/Solidity-0.8.23-blue.svg)](https://docs.soliditylang.org/en/v0.8.23/)
[![Foundry](https://img.shields.io/badge/Built%20with-Foundry-orange.svg)](https://book.getfoundry.sh/)

## Overview

This repository contains the bridge contracts for **openBDK** — the Open Blockchain Development Kit. These contracts implement the **L1Escrow + L2MinterBurner + NativeConverter** pattern that has secured billions of dollars on Polygon zkEVM mainnet since 2023.

**openBDK does not invent new bridge code.** It inherits from Polygon's $100M engineering investment in the AggLayer Unified Bridge architecture and adapts it for the openBDK Relayer-Validator consensus model.

## Why this architecture

Cross-chain bridges have been the largest target for crypto exploits, with **$2.8B+ stolen** from Ronin, Wormhole, Nomad, Harmony, and others. Every successful exploit traces to one of these failure patterns:

- Small multisigs (2-of-5, 5-of-9) compromised by social engineering or supply chain attacks
- Lock-and-mint wrapped tokens creating concentrated honeypots
- Signature verification bypasses (Wormhole — deprecated syscall)
- Initialization bugs (Nomad — zero hash trusted root)
- Single points of failure (Multichain — CEO arrested, MPC keys lost)

**The AggLayer Unified Bridge eliminates this entire class of attack** through:

1. A **single unified escrow on Ethereum** — no per-chain honeypots
2. **Pessimistic proofs** that cryptographically enforce `total_withdrawable ≤ total_deposited` per chain
3. **Hierarchical Sparse Merkle Trees** — Local Exit Tree, Local Balance Tree, Nullifier Tree
4. **No multisig committee** — withdrawals require valid Merkle proofs against committed exit roots
5. **Native fungibility** — tokens remain natively interchangeable across all connected chains

## Architecture

```
ETHEREUM L1                              openBDK CHAIN (L2)
┌────────────────┐                      ┌──────────────────┐
│   L1 USDC      │                      │  USDC.b (L2)     │
│ (Circle native)│                      │  (mintable/      │
└───────┬────────┘                      │   burnable)      │
        │                               └────────┬─────────┘
        │ user.bridgeToken()                     │ user.bridgeToken()
        ▼                                        ▼
┌────────────────┐                      ┌──────────────────┐
│  OpenBDKL1     │  ──UnifiedBridge──▶  │ OpenBDKL2        │
│  Escrow        │  ◀─bridgeMessage()─  │ MinterBurner     │
│                │                      │                  │
│  - Holds L1    │  ──onMessage────▶    │  - Mints USDC.b  │
│    backing     │     Received()       │  - Burns USDC.b  │
│  - Yield mgmt  │                      │                  │
└────────────────┘                      └──────────────────┘
                                                ▲
                                                │
                                        ┌───────┴──────────┐
                                        │ NativeConverter  │
                                        │                  │
                                        │ Converts default │
                                        │ BridgeWrapped    │
                                        │ USDC → USDC.b    │
                                        └──────────────────┘
```

## Contract suite

| Contract | Purpose | Reference |
|----------|---------|-----------|
| `OpenBDKL1Escrow` | L1 USDC custody + L2 mint trigger | `BuildOnPolygon/zkevm-stb/L1Escrow.sol` |
| `OpenBDKL2MinterBurner` | L2 mint/burn + L1 release trigger | `BuildOnPolygon/usdc-lxly/ZkMinterBurner.sol` |
| `OpenBDKNativeConverter` | bwUSDC → native USDC.b conversion | `BuildOnPolygon/usdc-lxly/NativeConverter.sol` |
| `OpenBDKL2Token` | USDC.e-style native L2 token | Circle FiatTokenV2_2 pattern |
| `OpenBDKValidatorRegistry` | Token-gated 1+3 Relayer-Validator | openBDK original |
| `PolygonERC20BridgeBaseUpgradeable` | Bridge integration base | Polygon canonical |

## openBDK v1 Topology

The Validator Registry implements the **minimum viable BFT deployment**:

- **1 Relayer** (the +1 in 3f+1) — proposes blocks, spawns Validators
- **3 Validators** (the consensus committee) — vote to finalize blocks
- **2/3 vote required** = 2 of 3 Validators must approve
- **1 Byzantine fault tolerated** — system continues if 1 Validator is malicious
- **1 redundant** — system continues if 1 Validator is offline for maintenance

This maps exactly to Lamport's `n ≥ 3f + 1` BFT theorem with `f = 1`.

Validator status is **token-gated** — operators must hold minimum protocol tokens locked in the staking contract. Validators earn block rewards (default 70% to validators, 20% to relayer, 10% burn) and can be slashed for misbehavior.

## Critical security pattern

Every bridge integration contract enforces three checks in `onMessageReceived`:

```solidity
if (msg.sender != address(polygonZkEVMBridge)) revert InvalidCrossDomainSender();
if (originAddress != counterpartContract) revert InvalidCrossDomainSender();
if (originNetwork != counterpartNetwork) revert InvalidCrossDomainSender();
```

These three lines prevent:

- **Direct invocation attacks** (msg.sender check)
- **Spoofed origin attacks** (originAddress check) — the Wormhole exploit class
- **Cross-network attacks** (originNetwork check) — the Nomad exploit class

## Quick start

### Install

```bash
git clone https://github.com/openbdk/openbdk-bridge-contracts.git
cd openbdk-bridge-contracts
forge install OpenZeppelin/openzeppelin-contracts
forge install OpenZeppelin/openzeppelin-contracts-upgradeable
forge install foundry-rs/forge-std
```

### Build

```bash
forge build
```

### Test

```bash
# Unit tests (mock bridge)
forge test -vvv

# Fork tests against real Ethereum mainnet
ETHEREUM_RPC_URL=https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY \
  forge test --match-contract BridgeForkTest --fork-url $ETHEREUM_RPC_URL -vvv

# Fuzz testing with high run count
forge test --match-test testFuzz -vv

# Coverage
forge coverage
```

### Deploy

```bash
cp .env.example .env
# Edit .env with your deployment configuration

forge script script/DeployOpenBDK.s.sol \
  --multi \
  --broadcast \
  --verify \
  -vvvv
```

## Production reference deployments

These are the **canonical Polygon zkEVM mainnet contracts** that openBDK inherits from. They have been securing real value with zero exploits since 2023.

| Contract | Address | Network |
|----------|---------|---------|
| Unified Bridge | `0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe` | All AggLayer chains |
| L1Escrow (USDC) | `0x70E70e58ed7B1Cec0D8ef7464072ED8A52d755eB` | Ethereum |
| ZkMinterBurner | `0xBDa0B27f93B2FD3f076725b89cf02e48609bC189` | Polygon zkEVM |
| NativeConverter | `0xd4F3531Fc95572D9e7b9e9328D9FEaa8e8496054` | Polygon zkEVM |
| USDC.e | `0x37eAA0eF3549a5Bb7D431be78a3D99BD360d19e5` | Polygon zkEVM |

## Repository structure

```
openbdk-bridge-contracts/
├── src/
│   ├── interfaces/
│   │   ├── IPolygonZkEVMBridgeV2.sol      # Unified Bridge interface
│   │   ├── IBridgeMessageReceiver.sol     # Message receiver pattern
│   │   └── IOpenBDKValidatorRegistry.sol  # Validator registry interface
│   ├── base/
│   │   └── PolygonERC20BridgeBaseUpgradeable.sol  # Bridge integration base
│   ├── bridge/
│   │   ├── OpenBDKL1Escrow.sol            # L1 USDC custody
│   │   ├── OpenBDKL2MinterBurner.sol      # L2 mint/burn
│   │   └── OpenBDKNativeConverter.sol     # bwUSDC → USDC.b conversion
│   ├── token/
│   │   └── OpenBDKL2Token.sol             # USDC.e-style L2 token
│   └── governance/
│       └── OpenBDKValidatorRegistry.sol   # 1+3 Relayer-Validator
├── script/
│   └── DeployOpenBDK.s.sol                # Multi-chain deployment
├── test/
│   ├── Bridge.t.sol                       # Bridge integration tests
│   └── ValidatorRegistry.t.sol            # Validator registry tests
├── foundry.toml
├── remappings.txt
├── .env.example
└── README.md
```

## Acknowledgments

This codebase is **derived from the canonical Polygon implementations**:

- [`BuildOnPolygon/usdc-lxly`](https://github.com/BuildOnPolygon/usdc-lxly) — the bridge contracts that have secured USDC on Polygon zkEVM
- [`BuildOnPolygon/zkevm-stb`](https://github.com/BuildOnPolygon/zkevm-stb) — the upgradeable base pattern
- [`agglayer/agglayer-contracts`](https://github.com/agglayer/agglayer-contracts) — the Unified Bridge V2 contracts
- [`agglayer/agglayer`](https://github.com/agglayer/agglayer) — the Rust pessimistic proof implementation
- [`0xPolygonHermez/zkevm-contracts`](https://github.com/0xPolygonHermez/zkevm-contracts) — the original Polygon zkEVM contracts

The Polygon Labs engineering team — and the security audits commissioned (including the October 2023 confidential audit included in the `usdc-lxly` repository) — represent the engineering investment that LAIR3 and openBDK extrapolate from. We are standing on the shoulders of giants.

## License

MIT — see [LICENSE](LICENSE)

The original Polygon contracts are licensed under MIT (BuildOnPolygon repos) and AGPL-3.0 (agglayer-contracts). openBDK adaptations preserve original licensing where applicable.

## Security

For security disclosures, contact: `security@openbdk.org`

**Production deployments should be audited.** The reference Polygon contracts have been audited; openBDK adaptations should undergo independent audit before mainnet deployment with significant value.

## Related repositories

- [`LAIR3/BDK6`](https://github.com/LAIR3) — Kurtosis-based deployment kit
- [`openbdk/openbdk-consensus`](https://github.com/openbdk) — Relayer-Validator consensus implementation (CometBFT integration)
- [`openbdk/openbdk-docs`](https://github.com/openbdk) — Architecture documentation

---

**Built by codephreak (Professor Codephreak) for the DELTAVERSE ecosystem.**
