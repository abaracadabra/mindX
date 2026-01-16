# THINK - THOT Intelligence Network Knowledge

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/core/THINK.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT Core - Batch Knowledge |
| **Inherits** | ERC1155, Ownable |

## Summary

THINK (THOT Intelligence Network Knowledge) is an ERC1155 implementation for batch THOT creation and management. It enables efficient batch operations for knowledge tensors with prompts and agent prompts.

## Purpose

- Create batch knowledge NFTs (ERC1155)
- Store prompts and agent prompts
- Enable batch minting and transfers
- Support dynamic metadata updates
- Track knowledge dimensions and batch sizes

## Technical Specification

### Data Structures

```solidity
struct ThinkData {
    string prompt;          // User prompt
    string agentPrompt;     // Agent execution prompt
    uint40 lastUpdate;      // Last update timestamp
    bool active;            // Active status
    uint8 dimensions;       // Knowledge dimensions
    uint16 batchSize;       // Processing batch size
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `_thinkData` | `mapping(uint256 => ThinkData)` | Think data storage |
| `_thinkIdCounter` | `uint256` | Think ID counter |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `createThinkBatch` | `recipient`, `prompt`, `agentPrompt`, `dimensions`, `batchSize`, `amount` | Owner | Create batch of THINK NFTs |
| `updateThink` | `thinkId`, `newPrompt`, `newAgentPrompt` | Token Owner | Update think prompts |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getThinkData` | `thinkId` | `ThinkData` | Get think data |
| `uri` | `thinkId` | `string` | Get metadata URI |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `ThinkCreated` | `thinkId`, `prompt`, `dimensions`, `batchSize` | New THINK batch created |
| `ThinkUpdated` | `thinkId`, `newPrompt`, `timestamp` | THINK updated |

## Usage Examples

### Creating a THINK Batch

```javascript
const recipient = agentAddress;
const prompt = "Analyze market trends";
const agentPrompt = "Use ML model to analyze";
const dimensions = 512;
const batchSize = 100;
const amount = 10; // Mint 10 tokens

const thinkId = await think.createThinkBatch(
    recipient,
    prompt,
    agentPrompt,
    dimensions,
    batchSize,
    amount
);
```

### Updating THINK

```javascript
const thinkId = 1;
const newPrompt = "Updated analysis prompt";
const newAgentPrompt = "Updated agent prompt";

await think.updateThink(thinkId, newPrompt, newAgentPrompt);
```

## Integration Points

### For tNFT

```javascript
// tNFT extends THINK with decision-making
// Similar structure but with additional state management
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
