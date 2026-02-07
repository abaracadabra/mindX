# xmind/ — mindX Execution Layer

Integration contracts for mindX to interact with the DAIO standalone governance system. DAIO remains **standalone**; mindX talks to DAIO only through this on-chain bridge.

## Purpose

- **Bridge** mindX (Python orchestration, agents) to DAIO governance without modifying DAIO core.
- **Register** mindX agents with DAIO identity (IDNFT) and agent creation (AgentFactory).
- **Submit** AI proposals to Marketing / Community / Development groups.
- **Receive** treasury allocations approved by DAIO (BoardroomExtension → XMindTreasuryReceiver).

## Documentation

| Document | Description |
|----------|-------------|
| **[roadmap.md](roadmap.md)** | **Complete DAIO deployment roadmap:** all DAIO components, canonical deployment order, xmind as extension example. |
| **[TECHNICAL.md](TECHNICAL.md)** | Architecture, contract roles, deployment order, usage summary, and **limitations** (Phase 2 out of scope). |

## Contracts

Source: **[../contracts/xmind/](../contracts/xmind/)** (Solidity).

| Contract | Description |
|----------|-------------|
| `DAIOBridge.sol` | Bridge connecting mindX to DAIO governance (single entry; requires DAIOGovernance) |
| `XMindAgentRegistry.sol` | Registry for mindX agents with IDNFT and AgentFactory integration |
| `XMindProposer.sol` | AI proposal submission to Marketing/Community/Development groups |
| `XMindTreasuryReceiver.sol` | Receive treasury allocations from BoardroomExtension |

## Deployment Order

Deploy **after** DAIO core contracts are live. Order and constructor dependencies:

| Order | Contract | Requires |
|-------|----------|----------|
| 1 | `DAIOBridge.sol` | DAIOGovernance address |
| 2 | `XMindAgentRegistry.sol` | IDNFT, AgentFactory addresses |
| 3 | `XMindProposer.sol` | KnowledgeHierarchyDAIO address |
| 4 | `XMindTreasuryReceiver.sol` | Treasury, BoardroomExtension addresses |

No circular dependency between these four; deploy in the order above.

## Integration Flow

```
mindX (Python orchestration)
    ↓
xmind/ contracts (on-chain bridge)
    ↓
DAIO Governance (KnowledgeHierarchyDAIO)
    ↓
Marketing / Community / Development (2/3 consensus per group)
    ↓
BoardroomExtension (flexible voting → treasury execution)
```

## AI Proposal Capability

AI agents can create proposals to any of the three governance groups:

- **Marketing**: Product positioning, partnerships, outreach
- **Community**: User experience, support, engagement
- **Development**: Technical changes, architecture, agents

Each group has 3 votes (2 human + 1 AI). Proposals require 2/3 within each group, and overall decisions require 2/3 of groups to approve.