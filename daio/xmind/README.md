# xmind/ - mindX Execution Layer

This folder contains the integration contracts for mindX to interact with the DAIO standalone governance system.

## Purpose

DAIO is a **standalone governance system**. External systems like mindX interact with DAIO through this execution layer rather than directly modifying DAIO contracts.

## Planned Contracts

| Contract | Description |
|----------|-------------|
| `DAIOBridge.sol` | Bridge contract connecting mindX agents to DAIO governance |
| `XMindAgentRegistry.sol` | Registry for mindX agents with IDNFT integration |
| `XMindProposer.sol` | AI proposal submission to Marketing/Community/Development groups |
| `XMindTreasuryReceiver.sol` | Receive treasury allocations from BoardroomExtension |

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

## Deployment Order

Deploy after DAIO core contracts are live:

1. `DAIOBridge.sol` (requires DAIOGovernance address)
2. `XMindAgentRegistry.sol` (requires IDNFT, AgentFactory addresses)
3. `XMindProposer.sol` (requires KnowledgeHierarchyDAIO address)
4. `XMindTreasuryReceiver.sol` (requires Treasury, BoardroomExtension addresses)
