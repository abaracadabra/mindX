# tNFT - THINK NFT with Decision-Making

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/core/tNFT.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT Core - Decision NFT |
| **Inherits** | ERC1155, Ownable |

## Summary

tNFT extends THINK with decision-making capabilities. It enables THINK NFTs to process external data and make decisions, adding state management and execution capabilities.

## Purpose

- Extend THINK with decision-making
- Process external data
- Track decision states (IDLE, PROCESSING, COMPLETED, FAILED)
- Store decision outcomes
- Enable agent execution workflows

## Technical Specification

### Data Structures

```solidity
enum DecisionState { IDLE, PROCESSING, COMPLETED, FAILED }

struct ThinkData {
    string prompt;          // Main user prompt
    string agentPrompt;     // AI/Agent Execution prompt
    uint40 lastUpdate;      // Timestamp of last state update
    bool active;            // Is the NFT active?
    uint8 dimensions;       // Think dimensions
    uint16 batchSize;       // Size of processing batch
    DecisionState state;    // Current decision-making state
    string lastDecision;    // Last computed decision outcome
}
```

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `createThinkBatch` | `recipient`, `prompt`, `agentPrompt`, `dimensions`, `batchSize`, `amount` | Owner | Create batch with decision capability |
| `updateThink` | `thinkId`, `newPrompt`, `newAgentPrompt` | Token Owner | Update think prompts |
| `executeDecision` | `thinkId`, `externalData` | Token Owner | Execute decision-making process |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getThinkData` | `thinkId` | `ThinkData` | Get think data with state |
| `uri` | `thinkId` | `string` | Get dynamic metadata URI with state |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `ThinkCreated` | `thinkId`, `prompt`, `dimensions`, `batchSize` | New tNFT created |
| `ThinkUpdated` | `thinkId`, `newPrompt`, `timestamp` | tNFT updated |
| `DecisionMade` | `thinkId`, `decision`, `timestamp` | Decision executed |

## Usage Examples

### Creating a tNFT

```javascript
const recipient = agentAddress;
const prompt = "Make trading decision";
const agentPrompt = "Analyze market and decide";
const dimensions = 512;
const batchSize = 1;
const amount = 1;

const thinkId = await tnft.createThinkBatch(
    recipient,
    prompt,
    agentPrompt,
    dimensions,
    batchSize,
    amount
);
```

### Executing a Decision

```javascript
const thinkId = 1;
const externalData = "Market data: price=100, volume=1000";

await tnft.executeDecision(thinkId, externalData);

// Check result
const data = await tnft.getThinkData(thinkId);
console.log(`State: ${data.state}`);
console.log(`Decision: ${data.lastDecision}`);
```

## Decision States

- **IDLE**: Ready to process
- **PROCESSING**: Currently executing
- **COMPLETED**: Decision made successfully
- **FAILED**: Decision failed

## Integration Points

### For AI Agents

```javascript
// Agents can trigger decisions
await tnft.executeDecision(thinkId, marketData);
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
