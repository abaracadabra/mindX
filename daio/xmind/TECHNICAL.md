# xmind — Technical Specification

Technical explanation, usage summary, and limitations of the mindX execution layer (xmind) for DAIO integration.

**Status:** Contracts are **planned**; no Solidity implementation exists in the repo yet. This document describes the intended design and deployment.

---

## 1. Explanation

### 1.1 Role of xmind

DAIO is a **standalone governance system**. mindX (Python orchestration, agents, tools) does not call DAIO contracts directly from off-chain code in an ad-hoc way. Instead, the **xmind** layer provides a small set of on-chain contracts that:

- **Bridge** mindX to DAIO governance (DAIOBridge).
- **Register** mindX agents with DAIO identity and factory (XMindAgentRegistry).
- **Submit** AI-driven proposals to DAIO groups (XMindProposer).
- **Receive** treasury allocations approved by DAIO (XMindTreasuryReceiver).

All interaction with DAIO (proposals, voting, treasury) stays on-chain through these contracts; mindX backend or agents trigger transactions to them (e.g. via signed txs or relayer).

### 1.2 Architecture

```
mindX (off-chain: Python, agents, wallet/signer)
    ↓  (signed transactions or relayer)
xmind contracts (on-chain)
    ├── DAIOBridge         → DAIOGovernance (central hub)
    ├── XMindAgentRegistry → IDNFT, AgentFactory (identity + agent creation)
    ├── XMindProposer      → KnowledgeHierarchyDAIO (proposals to groups)
    └── XMindTreasuryReceiver → Treasury, BoardroomExtension (receive allocations)
    ↓
DAIO core (standalone)
    → KnowledgeHierarchyDAIO (2/3 consensus: Marketing, Community, Development)
    → BoardroomExtension (voting parameters, treasury execution)
    → Treasury (hold funds, execute allocations)
```

### 1.3 Contract Roles and Dependencies

| Contract | Purpose | Requires (constructor / config) |
|----------|--------|----------------------------------|
| **DAIOBridge.sol** | Single entry point for mindX ↔ DAIO; can expose governance view functions and route to DAIOGovernance. | DAIOGovernance address |
| **XMindAgentRegistry.sol** | Register mindX agents with DAIO: link to IDNFT (identity) and AgentFactory (create agent NFTs). | IDNFT address, AgentFactory address |
| **XMindProposer.sol** | Submit proposals to one of the three groups (Marketing, Community, Development) in KnowledgeHierarchyDAIO. | KnowledgeHierarchyDAIO address |
| **XMindTreasuryReceiver.sol** | Be set as the recipient for treasury allocations from BoardroomExtension; receive and optionally forward funds. | Treasury address, BoardroomExtension address |

Dependencies imply a **deployment order** (see below): DAIO core must be deployed first; then xmind in the order that satisfies each contract’s constructor requirements.

### 1.4 Deployment Order (Canonical)

Deploy after DAIO core contracts are live:

1. **DAIOBridge.sol** — requires **DAIOGovernance** address.
2. **XMindAgentRegistry.sol** — requires **IDNFT**, **AgentFactory** addresses.
3. **XMindProposer.sol** — requires **KnowledgeHierarchyDAIO** address.
4. **XMindTreasuryReceiver.sol** — requires **Treasury**, **BoardroomExtension** addresses.

DAIOBridge has no dependency on the other xmind contracts, so it can be first. XMindAgentRegistry needs identity and agent factory. XMindProposer needs the hierarchy contract. XMindTreasuryReceiver needs treasury and boardroom so it can be the allocation recipient. No circular dependency between the four.

---

## 2. Usage Summary

### 2.1 How mindX Uses the Bridge

- **Agent registration:** mindX (or an operator) calls **XMindAgentRegistry** to register agents with DAIO (IDNFT identity, AgentFactory-created agent NFTs). This ties mindX agents to on-chain identity and agent records.
- **Proposals:** mindX AI (via a signer or relayer) calls **XMindProposer** to submit a proposal to a chosen group (Marketing, Community, or Development). The proposal is processed by KnowledgeHierarchyDAIO (2/3 per group, 2/3 of groups for overall approval).
- **Treasury:** When a proposal that allocates treasury is approved and executed, **BoardroomExtension** (and possibly Treasury) sends funds to the configured recipient. **XMindTreasuryReceiver** is that recipient (or wraps it); mindX can then use or forward received funds according to policy.
- **DAIOBridge:** Optional central facade: read governance state (e.g. proposal status, group state) or forward calls to DAIOGovernance for consistency and a single mindX-facing entry point.

### 2.2 Proposal Flow (High Level)

1. mindX prepares proposal payload (group, description, optional treasury amount/project).
2. Signer (mindX-controlled or relayer) calls `XMindProposer.submitProposal(...)` (or equivalent) with target group (Marketing / Community / Development).
3. KnowledgeHierarchyDAIO records the proposal; group members (2 human + 1 AI) vote; 2/3 within group required.
4. If overall consensus (2/3 of groups) is reached, proposal can move to execution; BoardroomExtension executes treasury allocation if applicable, sending to XMindTreasuryReceiver when configured.

### 2.3 Treasury Flow (High Level)

1. BoardroomExtension (or Treasury) holds project funds and allocation state.
2. Approved allocation specifies recipient (e.g. XMindTreasuryReceiver).
3. On execution, funds are transferred to XMindTreasuryReceiver.
4. XMindTreasuryReceiver may simply receive (and hold) or forward to another address (e.g. mindX-controlled multisig or EOA) per implementation.

---

## 3. Limitations

### 3.1 Implementation Status

- **No Solidity in repo:** The four contracts (DAIOBridge, XMindAgentRegistry, XMindProposer, XMindTreasuryReceiver) are **not** yet implemented. This document and the README describe the **intended** design and deployment order. Any implementation must follow DAIO’s actual interfaces (DAIOGovernance, KnowledgeHierarchyDAIO, IDNFT, AgentFactory, Treasury, BoardroomExtension) as they exist in the codebase.

### 3.2 Assumptions

- DAIO core is deployed and addresses are known (DAIOGovernance, KnowledgeHierarchyDAIO, IDNFT, AgentFactory, Treasury, BoardroomExtension).
- mindX (or a relayer) has a funded wallet or relayer to send transactions to the chain where DAIO and xmind are deployed.
- Group structure (2 human + 1 AI, 2/3 within group, 2/3 of groups) and proposal types are as in DAIO docs; xmind does not change governance rules, only provides an on-chain bridge for mindX to participate.

### 3.3 Out of Scope for Phase 1

- **Phase 2 candidates** (from XMIND_CONTRACT_ANALYSIS): XMindDynamicAgent, XMindDynamicNFT, XMindUniversalIdentity are **not** part of the canonical deployment order above. They may be added later for action tracking, evolving agent NFTs, or ERC-7777 identity; no dependency order is specified here for them.
- **Voting:** xmind does not cast human votes; it submits proposals and can represent the “AI” vote if the DAIO design allows an AI address to vote. Implementation of AI voting (if any) depends on KnowledgeHierarchyDAIO and group configuration.
- **Fund custody:** XMindTreasuryReceiver is intended to **receive** allocations. Design of internal forwarding, access control, or multisig is left to implementation; xmind is not a full treasury manager.

### 3.4 What xmind Does Not Do

- Does **not** replace or modify DAIO governance logic; it only calls into existing DAIO contracts.
- Does **not** hold user funds except as the designated treasury allocation recipient (and only as implemented).
- Does **not** enforce off-chain policy (e.g. which proposals mindX may submit); that remains in mindX backend and agent logic.
- Does **not** implement THOT, AgenticPlace, or NFT minting beyond what is done via AgentFactory/IDNFT through XMindAgentRegistry.

### 3.5 Security and Upgradeability

- Once implemented, xmind contracts should be audited; they will hold or route value (treasury) and affect governance (proposals).
- Upgradeability (proxy, timelock, owner) is not specified here; it should be decided at implementation time and documented.

---

## 4. References

- **README:** [README.md](README.md) — Purpose, deployment order, integration flow.
- **Contract analysis:** [../contracts/xmind/XMIND_CONTRACT_ANALYSIS.md](../contracts/xmind/XMIND_CONTRACT_ANALYSIS.md) — Phase 2 ideas, DAIO4 comparison.
- **DAIO overview:** [../CLAUDE.md](../CLAUDE.md) — Deployment order, xmind role, proposal flow.

---

**Last updated:** 2026-02-05
