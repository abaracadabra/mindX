# DAIOGovernance

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/DAIOGovernance.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | Governance Layer - Core |
| **Inherits** | None (Standalone) |

## Summary

DAIOGovernance is the core governance orchestrator for the Decentralized Autonomous Intelligence Organization. It provides modular orchestration for multiple projects (FinancialMind, mindX, cryptoAGI, etc.), enabling proposal creation, voting, and execution with integration to GovernanceSettings, DAIO_Constitution, and Treasury.

## Purpose

- Orchestrate multi-project governance within single contract
- Create and manage governance proposals
- Handle treasury allocation proposals
- Integrate with constitutional validation
- Support project-specific governance settings
- Enable cross-project coordination

## Technical Specification

### Data Structures

```solidity
enum ProposalType {
    Generic,           // Generic proposal
    Treasury,          // Treasury allocation
    AgentRegistry,     // Agent registration/removal
    ProjectExtension,  // Project-specific extension
    CrossProject       // Cross-project coordination
}

enum ProposalStatus {
    Pending,      // Proposal created, voting not started
    Active,       // Voting active
    Succeeded,    // Voting succeeded, ready for execution
    Defeated,     // Voting failed
    Executed,     // Proposal executed
    Cancelled     // Proposal cancelled
}

struct Proposal {
    uint256 proposalId;
    address proposer;
    string title;
    string description;
    ProposalType proposalType;
    string projectId;          // Project identifier
    uint256 startBlock;
    uint256 endBlock;
    uint256 forVotes;
    uint256 againstVotes;
    uint256 abstainVotes;
    ProposalStatus status;
    bytes executionCalldata;   // Execution calldata
    address target;           // Target contract for execution
    mapping(address => bool) hasVoted;
    mapping(address => uint256) votes;  // Votes cast by each address
}

struct TreasuryAllocationParams {
    string projectId;
    address recipient;
    uint256 amount;
    address token;
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `proposals` | `mapping(uint256 => Proposal)` | Proposal registry |
| `registeredProjects` | `mapping(string => bool)` | Registered project IDs |
| `votingPower` | `mapping(address => uint256)` | Voting power per address |
| `treasuryAllocations` | `mapping(uint256 => TreasuryAllocationParams)` | Treasury allocation params |
| `proposalCount` | `uint256` | Total proposal count |
| `settings` | `GovernanceSettings` | Settings contract |
| `constitution` | `DAIO_Constitution` | Constitution contract |
| `treasury` | `address` | Treasury contract address |
| `owner` | `address` | Contract owner |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `registerProject` | `projectId` | Owner | Register new project |
| `setVotingPower` | `voter`, `power` | Owner | Set voting power for address |
| `createProposal` | `title`, `description`, `proposalType`, `projectId`, `target`, `executionData` | Public | Create governance proposal |
| `createTreasuryAllocationProposal` | `title`, `description`, `projectId`, `recipient`, `amount`, `token` | Public | Create treasury allocation proposal |
| `vote` | `proposalId`, `support` | Public | Vote on proposal |
| `executeProposal` | `proposalId` | Public | Execute successful proposal |
| `checkProposalStatus` | `proposalId` | Public | Check and update proposal status |
| `updateGovernanceSettings` | `projectId`, all settings params | Owner | Update governance settings |
| `cancelProposal` | `proposalId` | Proposer/Owner | Cancel proposal |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `proposals` | `proposalId` | `Proposal` | Get proposal details |
| `registeredProjects` | `projectId` | `bool` | Check if project registered |
| `votingPower` | `voter` | `uint256` | Get voting power |
| `treasuryAllocations` | `proposalId` | `TreasuryAllocationParams` | Get treasury allocation params |
| `getProposal` | `proposalId` | `(address, string, ProposalStatus, uint256, uint256)` | Get proposal summary |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `ProposalCreated` | `proposalId`, `proposer`, `title`, `proposalType`, `projectId` | New proposal created |
| `VoteCast` | `proposalId`, `voter`, `votes`, `support` | Vote cast on proposal |
| `ProposalExecuted` | `proposalId` | Proposal executed |
| `ProposalCancelled` | `proposalId` | Proposal cancelled |
| `ProjectRegistered` | `projectId`, `registrar` | New project registered |
| `SettingsUpdated` | `projectId` | Settings updated |
| `TreasuryAllocationCreated` | `proposalId`, `projectId`, `recipient`, `amount` | Treasury allocation proposal created |

## Proposal Types

### 1. Generic
Standard governance proposals for any action.

### 2. Treasury
Treasury allocation proposals that require constitutional validation.

### 3. AgentRegistry
Proposals for agent registration or removal.

### 4. ProjectExtension
Project-specific extension proposals.

### 5. CrossProject
Cross-project coordination proposals.

## Usage Examples

### Registering a Project

```javascript
const projectId = "mindX";
await daioGovernance.registerProject(projectId);
```

### Creating a Generic Proposal

```javascript
const title = "Upgrade System Contract";
const description = "Proposal to upgrade the system contract to v2.0";
const proposalType = 0; // Generic
const projectId = "mindX";
const target = systemContractAddress;
const executionData = encodeUpgradeData();

const proposalId = await daioGovernance.createProposal(
    title,
    description,
    proposalType,
    projectId,
    target,
    executionData
);
```

### Creating a Treasury Allocation Proposal

```javascript
const title = "Fund Development Team";
const description = "Allocate 100 ETH to development team";
const projectId = "mindX";
const recipient = devTeamAddress;
const amount = ethers.utils.parseEther("100");
const token = ethers.constants.AddressZero; // ETH

const proposalId = await daioGovernance.createTreasuryAllocationProposal(
    title,
    description,
    projectId,
    recipient,
    amount,
    token
);
```

### Voting on a Proposal

```javascript
const proposalId = 1;
const support = true; // Vote yes

await daioGovernance.vote(proposalId, support);
```

### Executing a Successful Proposal

```javascript
const proposalId = 1;

// Check status first
await daioGovernance.checkProposalStatus(proposalId);

// Execute if succeeded
await daioGovernance.executeProposal(proposalId);
```

## UI Design Considerations

### Proposal Dashboard
- List: All proposals with status badges
- Filter: By project, type, status
- Sort: By date, votes, status
- Search: By title, description

### Proposal Creation Form
- Input: Title, description
- Select: Proposal type, project
- Input: Target address, execution data
- Preview: Proposal summary
- Validation: Check voting power threshold

### Voting Interface
- Display: Proposal details
- Buttons: Vote Yes/No/Abstain
- Show: Current vote counts
- Progress: Voting progress bar
- Timer: Time remaining

## Integration Points

### For GovernanceSettings

```javascript
// Get settings when creating proposal
const settings = await governanceSettings.getSettings(projectId);
const endBlock = currentBlock + settings.votingPeriod;
```

### For DAIO_Constitution

```javascript
// Validate action before execution
const isValid = await constitution.validateAction(
    target,
    executionData,
    amount
);
```

### For Treasury

```javascript
// Create allocation after proposal succeeds
await treasury.createAllocation(
    proposalId,
    projectId,
    recipient,
    amount,
    token
);
```

## Security Considerations

- **Access Control**: Owner-only functions for critical operations
- **Proposal Validation**: Checks proposal threshold before creation
- **Constitutional Validation**: All treasury allocations validated
- **Status Checks**: Prevents double execution
- **Voting Power**: Must meet minimum threshold to vote

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `createProposal` | ~150,000 |
| `createTreasuryAllocationProposal` | ~180,000 |
| `vote` | ~80,000 |
| `executeProposal` | ~100,000 |
| `checkProposalStatus` | ~30,000 |

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
