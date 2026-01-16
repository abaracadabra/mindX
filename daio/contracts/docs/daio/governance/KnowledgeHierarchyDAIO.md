# KnowledgeHierarchyDAIO

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/governance/KnowledgeHierarchyDAIO.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - AI Voting |
| **Inherits** | ReentrancyGuard, Ownable |

## Summary

KnowledgeHierarchyDAIO implements a knowledge-weighted AI voting system with 66.67% human voting (Development, Marketing, Community) and 33.33% AI voting. It enables domain-specific agents to participate in governance with voting weights based on their knowledge level.

## Purpose

- Implement knowledge-weighted AI voting
- Support human voting in subcomponents (Development, Marketing, Community)
- Aggregate AI agent votes based on knowledge level
- Enable domain-specific agent expertise
- Integrate with timelock for secure execution

## Technical Specification

### Data Structures

```solidity
enum SubComponent { Development, Marketing, Community }
enum Domain { AI, Blockchain, Finance, Healthcare, General }

struct Agent {
    uint256 knowledgeLevel;  // 0-100, determines voting weight
    Domain domain;
    bool active;
    uint256 lastActiveTime;
    address idNFTTokenId;     // Optional: link to IDNFT
}

struct Proposal {
    uint256 id;
    bool executed;
    string description;
    uint256 voteCountDev;
    uint256 voteCountMarketing;
    uint256 voteCountCommunity;
    uint256 voteCountAI;      // Aggregated AI agent vote
    uint256 startBlock;
    uint256 endBlock;
    ProposalStatus status;
}
```

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `addOrUpdateAgent` | `_agentAddress`, `_knowledgeLevel`, `_domain`, `_active` | Governance | Register/update agent |
| `createProposal` | `description` | Governance | Create governance proposal |
| `voteOnProposal` | `proposalId`, `subComponent`, `support` | Public | Human voting |
| `agentVote` | `proposalId`, `support` | Public | AI agent voting |
| `executeProposal` | `proposalId` | Governance | Execute successful proposal |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `agents` | `agentAddress` | `Agent` | Get agent details |
| `proposals` | `proposalId` | `Proposal` | Get proposal details |
| `aggregateVotes` | `proposalId` | `bool` | Check if proposal succeeds |
| `getProposal` | `proposalId` | `Proposal` | Get proposal struct |
| `getAgent` | `agentAddress` | `Agent` | Get agent struct |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `AgentUpdated` | `agentAddress`, `knowledgeLevel`, `domain`, `active` | Agent registered/updated |
| `ProposalCreated` | `proposalId`, `description` | New proposal created |
| `ProposalExecuted` | `proposalId` | Proposal executed |
| `AIVoteAggregated` | `proposalId`, `totalVotes` | AI votes aggregated |
| `HumanVoteCast` | `proposalId`, `voter`, `subComponent`, `support` | Human vote cast |
| `AgentVoteCast` | `proposalId`, `agent`, `support`, `votingWeight` | AI agent voted |

## Voting System

### Human Voting (66.67% weight)
- **Development**: Technical decisions
- **Marketing**: Product positioning, partnerships
- **Community**: User experience, support

### AI Voting (33.33% weight)
- **Knowledge-Weighted**: Voting power = knowledge level (0-100)
- **Domain-Specific**: Agents vote in their expertise domain
- **Aggregated**: All AI votes combined with knowledge weighting

## Usage Examples

### Registering an Agent

```javascript
const agentAddress = agentWalletAddress;
const knowledgeLevel = 85; // 0-100
const domain = 0; // AI
const active = true;

await knowledgeHierarchy.addOrUpdateAgent(
    agentAddress,
    knowledgeLevel,
    domain,
    active
);
```

### Human Voting

```javascript
const proposalId = 1;
const subComponent = 0; // Development
const support = true;

await knowledgeHierarchy.voteOnProposal(
    proposalId,
    subComponent,
    support
);
```

### AI Agent Voting

```javascript
const proposalId = 1;
const support = true;
await knowledgeHierarchy.agentVote(proposalId, support);
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
