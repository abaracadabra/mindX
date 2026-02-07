# DAIO Complete Deployment Roadmap — xmind Strategy

This document lists **all DAIO components** required for a full, modular DAIO deployment and frames **mindX (xmind)** as the extension example. DAIO remains standalone; xmind is one optional strategy for connecting an external orchestration layer (mindX) to DAIO.

---

## 1. Modular DAIO Overview

DAIO is structured in layers. Core layers are required for a minimal deployment; extension layers (including xmind) can be added per strategy.

| Layer | Purpose |
|-------|--------|
| **Foundation** | Constitution, settings, timelock — immutable rules and parameters |
| **Identity** | Agent identity (IDNFT), optional soulbound (SoulBadger) |
| **Governance core** | DAIOGovernance (hub), KnowledgeHierarchyDAIO (agent + human voting) |
| **Treasury** | Multi-project treasury, tithe, allocations |
| **Agent layer** | AgentFactory (create agents + ERC20 + NFT), AgentManagement (lifecycle) |
| **Extensions** | BoardroomExtension (treasury extension), FractionalNFT (as needed) |
| **xmind (mindX strategy)** | Bridge, agent registry, proposer queue, treasury receiver |

---

## 2. Complete DAIO Component List

All contracts under `contracts/daio/` (and referenced by xmind) that are part of a full deployment:

### 2.1 Foundation

| Component | Path | Role |
|-----------|------|------|
| **DAIO_Constitution** | `constitution/DAIO_Constitution.sol` | Constitutional constraints (15% diversify, 15% tithe, chairman veto); validates actions |
| **GovernanceSettings** | `settings/GovernanceSettings.sol` | Voting period, quorum, approval threshold, timelock delay, proposal threshold, min voting power (global + per project) |
| **DAIOTimelock** | `governance/DAIOTimelock.sol` | TimelockController wrapper; delayed execution for KnowledgeHierarchyDAIO and security layer |

### 2.2 Identity

| Component | Path | Role |
|-----------|------|------|
| **SoulBadger** | `identity/SoulBadger.sol` | Optional soulbound badges; ERC-5484; linked by IDNFT |
| **IDNFT** | `identity/IDNFT.sol` | Agent identity NFT (prompt, persona, credentials, trust score, optional SoulBadger) |

### 2.3 Governance Core

| Component | Path | Role |
|-----------|------|------|
| **DAIOGovernance** | `DAIOGovernance.sol` | Central hub: proposals, voting, project registration, treasury allocation proposals, execution |
| **KnowledgeHierarchyDAIO** | `governance/KnowledgeHierarchyDAIO.sol` | 66.67% human (Dev/Marketing/Community), 33.33% AI (knowledge-weighted); proposal creation only via timelock executor |

### 2.4 Treasury

| Component | Path | Role |
|-----------|------|------|
| **Treasury** | `treasury/Treasury.sol` | Multi-project treasury, 15% tithe, allocations, multi-sig execution |

### 2.5 Agent Layer

| Component | Path | Role |
|-----------|------|------|
| **AgentFactory** | `governance/AgentFactory.sol` | Create agents (custom ERC20 + governance NFT); links to IDNFT; callable only by governance |
| **AgentManagement** | `governance/AgentManagement.sol` | Lifecycle, metadata updates, inactivity tracking; operates on AgentFactory |

### 2.6 Extensions (optional but typical)

| Component | Path | Role |
|-----------|------|------|
| **BoardroomExtension** | `BoardroomExtension.sol` | Treasury extension (allocate/execute); only callable by DAIOGovernance; project treasuries |
| **FractionalNFT** | `governance/FractionalNFT.sol` | Fractionalize NFTs as needed (e.g. per NFT) |

### 2.7 xmind (mindX extension strategy)

| Component | Path | Role |
|-----------|------|------|
| **DAIOBridge** | `contracts/xmind/DAIOBridge.sol` | Single entry for mindX → DAIOGovernance (getProposal, createProposal, vote, execute, etc.) |
| **XMindAgentRegistry** | `contracts/xmind/XMindAgentRegistry.sol` | Register mindX agents; optional IDNFT mint; request AgentFactory creation (event for governance) |
| **XMindProposer** | `contracts/xmind/XMindProposer.sol` | Proposal request queue; timelock executor calls KnowledgeHierarchyDAIO.createProposal |
| **XMindTreasuryReceiver** | `contracts/xmind/XMindTreasuryReceiver.sol` | Recipient for treasury allocations; receive ETH/tokens; owner withdraw |

---

## 3. Canonical Deployment Order

Deploy in this order so each contract’s constructor dependencies are already deployed. Optional components can be skipped for minimal deployments.

| Step | Contract | Constructor / Requires | Notes |
|------|----------|-------------------------|--------|
| **1** | DAIOTimelock | `minDelay`, `proposers[]`, `executors[]`, `admin` | Foundation; executors will include KnowledgeHierarchyDAIO flow |
| **2** | DAIO_Constitution | `chairman` | Set governance later via `setGovernance()` |
| **3** | SoulBadger | `name`, `symbol`, `baseBadgeUri`, `agenticPlace` (optional) | Optional; use `address(0)` for agenticPlace if not needed |
| **4** | IDNFT | `soulBadgerAddress` (or `address(0)`) | Grant MINTER_ROLE to XMindAgentRegistry later if using xmind |
| **5** | GovernanceSettings | `votingPeriod`, `quorumThreshold`, `approvalThreshold`, `timelockDelay`, `proposalThreshold`, `minVotingPower` | Can tune per project later |
| **6** | Treasury | `constitution`, `initialSigners[]` (e.g. 5 for 3-of-5) | Constitution enforces tithe |
| **7** | KnowledgeHierarchyDAIO | `timelock`, `constitution` | Timelock must grant EXECUTOR_ROLE to proposer path (e.g. multisig that pushes from XMindProposer) |
| **8** | AgentFactory | `governanceContract`, `idNFT`, `knowledgeHierarchy` | `governanceContract` = DAIOGovernance or timelock (who may create agents) |
| **9** | DAIOGovernance | `settings`, `constitution`, `treasury` | Central hub; register projects (e.g. `"mindx"`) |
| **10** | BoardroomExtension | `daioGovernance` | Optional; use if boardroom-style allocation flow is desired |
| **11** | AgentManagement | `agentFactory` | Optional; for lifecycle and inactivity handling |
| **12** | FractionalNFT | (per-NFT) `nftAddress`, `nftId`, `totalFractions`, `initialOwner` | Deploy as needed for specific NFTs |
| **13** | **DAIOBridge** | `daioGovernance` | xmind: single entry for mindX |
| **14** | **XMindAgentRegistry** | `idNFT`, `agentFactory` | xmind: grant IDNFT MINTER_ROLE if registry should mint |
| **15** | **XMindProposer** | `knowledgeHierarchy` | xmind: request queue; executor calls KnowledgeHierarchyDAIO.createProposal |
| **16** | **XMindTreasuryReceiver** | (none) | xmind: use contract address as allocation recipient |

Post-deploy configuration (examples):

- **DAIO_Constitution:** `setGovernance(DAIOGovernance)`.
- **DAIOGovernance:** `registerProject("mindx")`, `setVotingPower(mindXEOA, power)` for proposal/voting.
- **IDNFT:** Grant `MINTER_ROLE` to XMindAgentRegistry if mindX should mint identities from the registry.
- **Timelock:** Ensure an executor (multisig or script) can call KnowledgeHierarchyDAIO.createProposal for descriptions coming from XMindProposer.

---

## 4. xmind Strategy as Roadmap

The **xmind strategy** is the roadmap for using DAIO as a modular base with mindX as an extension:

1. **Deploy full DAIO** (steps 1–12 above) so that governance, identity, treasury, and agent creation are live.
2. **Deploy xmind** (steps 13–16) to add the mindX-facing bridge, registry, proposer queue, and treasury receiver.
3. **Configure** DAIO for mindX: register project, voting power, IDNFT minter role, timelock executor for proposal creation from XMindProposer.
4. **Operate**: mindX (off-chain) sends transactions to DAIOBridge (proposals, votes), XMindAgentRegistry (register/request agents), XMindProposer (request proposals); allocations use XMindTreasuryReceiver as recipient.

This keeps DAIO **modular** and **standalone**; xmind is one **extension example** that does not modify DAIO core and can be replaced or duplicated for other orchestrators (e.g. other projects with their own “bridge + registry + proposer + receiver” set).

---

## 5. References

| Document | Description |
|----------|-------------|
| [README.md](README.md) | xmind purpose, contracts table, integration flow |
| [TECHNICAL.md](TECHNICAL.md) | Architecture, usage, limitations |
| [../contracts/daio/README.md](../contracts/daio/README.md) | DAIO contract structure and deployment order |
| [../contracts/docs/daio/DAIO_INTERACTION_DIAGRAM.md](../contracts/docs/daio/DAIO_INTERACTION_DIAGRAM.md) | DAIO interaction flows and dependency graph |
| [../contracts/xmind/](../contracts/xmind/) | xmind Solidity sources (DAIOBridge, XMindAgentRegistry, XMindProposer, XMindTreasuryReceiver) |

---

**Last updated:** 2026-02-05
