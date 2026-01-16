# BoardroomExtension

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/BoardroomExtension.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - Extension |
| **Inherits** | None (Standalone) |

## Summary

BoardroomExtension extends DAIO governance with boardroom.sol integration, providing treasury management and proposal execution capabilities. It acts as a bridge between DAIOGovernance and treasury operations, enabling flexible treasury allocation and execution.

## Purpose

- Extend DAIO governance with treasury management
- Provide treasury allocation management
- Enable proposal-based treasury allocations
- Support project-specific treasuries
- Execute treasury allocations after proposal success

## Technical Specification

### Data Structures

```solidity
struct TreasuryInfo {
    address token;      // Token address (address(0) for native)
    uint256 balance;    // Current balance
    uint256 allocated;  // Allocated but not spent
}

struct TreasuryAllocation {
    string projectId;
    address recipient;
    uint256 amount;
    address token;
    bool executed;
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `daioGovernance` | `DAIOGovernance` | DAIO governance contract |
| `projectTreasuries` | `mapping(string => TreasuryInfo)` | Project treasury info |
| `allocations` | `mapping(uint256 => TreasuryAllocation)` | Proposal allocations |
| `owner` | `address` | Contract owner |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `allocateTreasury` | `proposalId`, `projectId`, `recipient`, `amount`, `token` | DAIO only | Allocate treasury funds |
| `executeAllocation` | `proposalId` | Public | Execute treasury allocation |
| `depositTreasury` | `projectId`, `token` | Public (payable) | Deposit funds to treasury |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `projectTreasuries` | `projectId` | `TreasuryInfo` | Get treasury info |
| `allocations` | `proposalId` | `TreasuryAllocation` | Get allocation details |
| `getTreasury` | `projectId` | `(uint256, uint256)` | Get balance and allocated |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `TreasuryAllocated` | `proposalId`, `projectId`, `recipient`, `amount` | Treasury allocated |
| `TreasuryExecuted` | `proposalId`, `recipient`, `amount` | Allocation executed |

## Usage Examples

### Allocating Treasury Funds

```javascript
// Called by DAIOGovernance after proposal succeeds
const proposalId = 42;
const projectId = "mindX";
const recipient = agentAddress;
const amount = ethers.utils.parseEther("10");
const token = ethers.constants.AddressZero; // ETH

await boardroomExtension.allocateTreasury(
    proposalId,
    projectId,
    recipient,
    amount,
    token
);
```

### Executing Allocation

```javascript
// Execute allocation after proposal executed
const proposalId = 42;
await boardroomExtension.executeAllocation(proposalId);
```

### Depositing to Treasury

```javascript
const projectId = "mindX";
const token = ethers.constants.AddressZero; // ETH

await boardroomExtension.depositTreasury(projectId, token, {
    value: ethers.utils.parseEther("100")
});
```

## Integration Points

### For DAIOGovernance

```javascript
// DAIOGovernance calls after proposal execution
await boardroomExtension.allocateTreasury(
    proposalId,
    projectId,
    recipient,
    amount,
    token
);
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
