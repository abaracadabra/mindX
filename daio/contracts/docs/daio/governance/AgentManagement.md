# AgentManagement

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/governance/AgentManagement.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - Agent Lifecycle |
| **Inherits** | None (Standalone) |

## Summary

AgentManagement provides agent lifecycle management with inactivity tracking and automatic deactivation capabilities. It manages agent metadata updates and monitors agent activity to ensure only active agents remain in the system.

## Purpose

- Manage agent lifecycle operations
- Track agent inactivity
- Update agent metadata
- Automatically deactivate inactive agents
- Provide agent status information

## Technical Specification

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `agentFactory` | `AgentFactory` | Agent factory contract (immutable) |
| `inactivityTimeout` | `uint256` | Inactivity timeout (default: 365 days) |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `updateAgentMetadataByNFT` | `nftId`, `newMetadata` | Public | Update metadata via NFT ID |
| `updateAgentMetadata` | `agentAddress`, `nftId`, `newMetadata` | Public | Update metadata via agent address |
| `deactivateInactiveAgent` | `agentAddress` | Public | Deactivate inactive agent |
| `setInactivityTimeout` | `newTimeout` | Governance | Set inactivity timeout |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `shouldDeactivateAgent` | `agentAddress` | `bool` | Check if agent should be deactivated |
| `getAgentStatus` | `agentAddress` | `(bool, uint256, uint256, bool)` | Get agent status info |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `AgentUpdated` | `agentAddress`, `active`, `timestamp` | Agent metadata updated |
| `AgentDeactivatedDueToInactivity` | `agentAddress`, `timestamp` | Agent deactivated |
| `InactivityTimeoutUpdated` | `oldTimeout`, `newTimeout` | Timeout updated |

## Usage Examples

### Updating Agent Metadata

```javascript
const nftId = 1;
const newMetadata = "ipfs://updated-metadata";
await agentManagement.updateAgentMetadataByNFT(nftId, newMetadata);
```

### Checking Agent Status

```javascript
const agentAddress = agentWalletAddress;
const [active, createdAt, timeSinceCreation, shouldDeactivate] = 
    await agentManagement.getAgentStatus(agentAddress);
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
