# OPEN BDK : whitepaper

---

## Abstract

OPEN BDK (Blockchain Development Kit) is an innovative, developer-centric blockchain ecosystem that simplifies blockchain deployment, incentivizes developers, and promotes interoperability. With its zkEVM-based infrastructure, dual-token model (BDK and SATPAY), and DAIO governance, OPEN BDK aims to become the foundational layer for blockchain innovation. This document provides a comprehensive outline of the project's vision, technical architecture, tokenomics, governance, and roadmap.

---

## Introduction

### Problem Statement

- Blockchain development faces significant barriers:
  - Complex deployment processes.
  - High costs and inefficiencies in gas fees.
  - Limited developer incentives and rewards.
  - Centralized control of governance in many ecosystems.
  - Interoperability challenges across blockchain networks.

### OPEN BDK Solution

- Simplified Deployment:
  - zkEVM-based architecture for high scalability and EVM compatibility.
- Incentive Systems:
  - Developer-centric tokenomics powered by BDK tokens.
- Decentralized Governance:
  - DAIO ensures equitable and AI enhanced community-driven decision-making
- Interoperability:
  - BANKON SATPAY as a universal Bitcoin-pegged gas token ensures seamless transactions across chains
- Innovative Tools:
  - A suite of developer tools for dApp creation, node management, and ecosystem expansion

---

## Architecture

### Blockchain Infrastructure

- zkEVM-Based Layer 1 Chain:
  - Combines zero-knowledge proof scalability with EVM compatibility.
  - Ensures low transaction fees and high throughput.

- Multi-Token Gas Mechanism:
  - Supports multiple gas tokens validated by consensus, enabling flexibility for developers and projects.

- Validator and Light Node Framework:
  - Decentralized validators ensure security and network integrity.
  - Light nodes delegate staking to validators, earning proportional rewards.

### DAIO (Decentralized Autonomous Intelligent Organization)

- Purpose:
  - Govern validator selection, tokenomics, ecosystem grants, and treasury allocation.

- Governance Mechanism:
  - Weighted voting by developers, validators, and token holders ensures balanced decision-making.

### Developer Tools

- OPEN BDK SDK:
  - A modular toolkit for deploying smart contracts and dApps.

- Integration Support:
  - Pre-built APIs for seamless cross-chain interactions.

- Templates:
  - Ready-to-use templates for zkEVM-based applications.

---

## Tokenomics

### Dual-Token System

- BDK Token:
  - **Utility**:
    - Gas token within the OPEN BDK chain
    - Developer rewards
    - Governance token for DAIO voting
  - **Supply**: 10 billion BDK
  - **Distribution**:
    - 30% developer grants and incentives
    - 20% validator incentives (timelocked)
    - 15% marketing incentives
    - 10% ecosystem treasury
    - 10% liquidity
    - 10% for community marketing and development partnerships
    - 5% initial funding

- SATPAY Token:
  - **Utility**:
    - Bitcoin-pegged gas token for stable transaction fees
  - **Supply**:
    - Fully backed 1:1 with Bitcoin reserves

### Fee Recycling Mechanism

- Redistribution of transaction fees:
  - 89% to validators
  - 8% to the DAIO treasury
  - 3% to developer incentives

---

## Governance

### DAIO Governance Model

- Voting System:
  - Developers: 1/3
  - Validators: 1/3
  - Community: 1/3

- Proposal Lifecycle:
  - Proposal submission by any staked token holder.
  - Weighted voting by DAIO participants.
  - Automated implementation of approved proposals.

### Immutable Code is Law

- Core contracts cannot be altered once deployed, ensuring transparency and security.
- Forked projects must adhere to this principle under the custom OPEN BDK license.

---

## Licensing

### Custom GPL-3 License

- Immutable Code Clause:
  - Deployed contracts are immutable.

- Pay-to-Fork Mechanism:
  - Forked projects must allocate 1% of token supply to the DAIO treasury, locked for 90 days.

- Open Source Mandate:
  - All modifications must remain open source under the same licensing terms.

---

## Roadmap

- Foundational Development:
  - Deploy zkEVM-based Layer 1 blockchain.
  - Launch BDK and SATPAY tokens.
  - Establish DAIO governance.

- Testnet Deployment:
  - Launch public testnet.
  - Onboard validators and developers.
  - Conduct performance testing and audits.

- Mainnet Launch:
  - Transition to the mainnet.
  - Bootstrap liquidity pools (e.g., BDK/SATPAY, SATPAY/tBTC).
  - Activate DAIO governance.

- Ecosystem Expansion:
  - Build cross-chain bridges.
  - Launch a marketplace for dApp templates and tools.
  - Scale validator and light node participation globally.

- Mass Adoption:
  - Partner with enterprises and institutions.
  - Integrate SATPAY as a universal gas token across other chains.
  - Drive mass adoption through marketing and education.

---

# Part II — Technical Implementation (v1, shipped)

The litepaper above states the vision. This half documents what is built and tested
today, reconciled to a single Foundry toolchain (solc 0.8.24, EVM Cancun, via_ir,
OpenZeppelin v5) as a modular sub-module of the bankoneth project. `forge test` is
green across the bridge, validator-registry, allocations, whitelist, and deployer
suites.

## The Bridge — L1Escrow / L2MinterBurner / NativeConverter

openBDK composes with, rather than replaces, the canonical AggLayer **Unified Bridge**
on Ethereum mainnet (`0x2a3DD3EB832aF982ec71669E178424b10Dca2EDe`). Three roles,
inherited from Polygon's well-documented Stake-the-Bridge / usdc-lxly pattern:

- **L1Escrow** — locks the underlying ERC-20 on L1 and emits a unified-bridge message.
- **L2MinterBurner** — receives that message and natively mints the L2 representation.
- **NativeConverter** — 1:1 conversion between the natively-minted token and the
  bridge-wrapped LxLy variant.

All three are UUPS-upgradeable, ERC-7201 namespaced (collision-resistant storage),
pausable, and role-gated. The Unified Bridge dependency is mainnet/AggLayer-specific;
non-AggLayer targets must supply a bridge mock.

## The Relayer–Validator BFT Topology

The "Validator and Light Node Framework" is realised by **OpenBDKValidatorRegistry**:
the minimum-viable honest-majority quorum — **1 Relayer + 3 Validators**, where `n =
3f + 1` for `f = 1` Byzantine fault, so **2-of-3** validator consensus is required and
any one node may fail. Validators stake the governance token (the "20% validator
incentives, timelocked" allocation), earn the fee split, and are slashable; falling
below the minimum stake deactivates a validator. Relayer rotation is governance-gated.

## Sane Deployment — the dual deployer (blockchain CI/CD)

openBDK closes the litepaper's "blockchain CI/CD" thread with two deployers sharing
one contract set:

- **Client-side** (`deployer/index.xml` + `index.html`, ships as a **Tauri** app for
  multi-device): a two-event flow — **DEPLOY** arms a transaction (resolves
  constructor args, encodes, no cost); **LAUNCH** fires it *from value* — a token
  payment or an identity **signature** — and the connected wallet's public key is the
  identity that receives the conferred privilege. Keys never leave the device.
- **Server-side, governed** (`agents/deployer`): a declarative `.deploy` manifest
  drives a Foundry runner with a **two-step intent → confirm** gate, per-chain isolated
  stages, vault-scoped deploy keys, machine-readable receipts, and an append-only
  audit event per deploy. Mainnet requires explicit confirmation and approver tiers.

## OVERLORD Handoff & the Non-Custodial Invariant

The cardinal rule: **the OWNER holds the private key; the software does not.**

- **On-chain**, `OpenBDKDeployer` stands up the control plane in one transaction and
  hands *everything* to the OWNER: it deploys an **OVERLORD timelock** (an OZ
  `TimelockController` whose sole proposer/executor is the OWNER wallet), makes that
  timelock the `DEFAULT_ADMIN` of the ValidatorRegistry, and owns the allocations
  vault by the timelock. The factory grants itself **no role** and keeps **no key**;
  the deploy key that broadcasts retains nothing once the constructor returns. (Proven
  by test: the timelock holds admin; the factory, the software address, and even the
  raw owner-EOA hold none — the owner acts *through* the transparency delay.)
- **Off-chain**, owner **recognition is by proof-of-signature only** — an EIP-191
  signature is recovered to an address; the software stores nothing for the owner.
  Agents/participants without a wallet receive a **vault-custodied** key via
  **walletgen**, but only under an owner signature bound to (purpose, room, chainId,
  nonce) — replay-resistant, fails closed on mismatch. The BANKON vault itself can be
  bound to the participant's own signature (AES-256-GCM + HKDF-SHA512), so custody
  follows the key holder.

## Timelocks & Allocations

`OpenBDKAllocations` issues team/treasury/validator allocations as **cliff + linear
vesting** schedules over a single ERC-20: nothing before the cliff, linear to
`start + duration`, revocable allocations return only the *unvested* remainder (vested
tokens are always safe to the beneficiary). This makes the litepaper's "timelocked"
distributions a property of the contract, not of trust. The **OVERLORD timelock**
additionally queues every privileged action behind a public delay.

## Whitelist-as-a-Service

`whitelist.sol` is a multi-room registry of public keys. Membership is the
gas-cheapest store for arbitrary addresses (`mapping(room => mapping(addr => bool))`);
room metadata is packed into one 256-bit slot. A room's capacity expands by adding
**databanks** — fixed-size capacity grants that only an authorised **gate**,
**registry**, or **holding** role may add — so a whitelist can grow on demand under
explicit authority.

## DeltaVerse Integration

The DeltaVerse NeuralNode suite (rooms / bubblerooms) plugs in as a **modular deploy
option** surfaced through the same DEPLOY/LAUNCH toggle. Crossing the DeltaVerse
turnstile mints a room and spawns a bubbleroom; bubbleroom participants receive their
blockchain keys through the same owner-signed walletgen handoff described above.

## Licensing (implementation reconciliation)

The doctrine above (immutable-code, pay-to-fork to the DAIO treasury) governs the
*kit*. At the file level: the openBDK **contracts and SDK are MIT** (Professor
Codephreak); **Alpine-Linux-based BDK infrastructure** (the Kurtosis-CDK devnet
orchestration) remains **GPL** per its upstream; **macOS/BSD** platform targets are
**BSD**. We pay **GPLv3 homage to Tomb (the Crypto Undertaker) and the GNU project** —
the encrypted-vault lineage openBDK's custody model stands on. See `NOTICE`.

## Security Posture

Relayers, validators, and key custody should run on **OpenBSD** — secure by default,
made in Canada. 🐡

---

## Conclusion

OPEN BDK is a next-generation blockchain platform designed to empower developers and communities. By integrating scalable technology, decentralized governance, and sustainable tokenomics, OPEN BDK ensures long-term growth and innovation in the blockchain ecosystem.

Its developer-first approach, combined with tools and grants, bridges the gap between blockchain infrastructure and real-world applications, creating a foundation for blockchain CI/CD
