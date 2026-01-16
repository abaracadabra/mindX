# NFPrompT - Agent Prompt NFT

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/nft/NFPrompT.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT NFT - Agent Prompts |
| **Inherits** | ERC721, ReentrancyGuard |

## Summary

NFPrompT (Agent Prompt NFT) enables creation and management of agent prompts as NFTs. It stores agent capabilities, actions, and permissions for agentic marketplace integration.

## Purpose

- Create agent prompts as NFTs
- Store agent capabilities and modifiers
- Register agent actions
- Manage agent permissions
- Enable agent builder credits

## Technical Specification

### Data Structures

```solidity
struct AgentData {
    bytes32 agentId;          // Unique agent identifier
    address agentWallet;      // Agent's wallet address
    string basePrompt;        // Core prompt template
    string[] modifiers;       // Prompt modifiers/parameters
    uint40 creationTime;      // Creation timestamp
    uint40 lastUpdate;        // Last update timestamp
    bool isActive;            // Agent active status
    mapping(string => string) capabilities; // Agent capabilities
}

struct ActionData {
    string actionType;        // Type of action
    bytes parameters;         // Encoded parameters
    uint40 timestamp;        // Action timestamp
    bool requiresApproval;    // Whether action needs approval
    bool isExecuted;          // Execution status
}
```

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `createAgentPrompt` | `agentId`, `basePrompt`, `initialModifiers`, `initialCapabilities`, `capabilityValues` | Public | Create agent prompt NFT |
| `registerAgentAction` | `tokenId`, `actionType`, `parameters`, `requiresApproval` | Agent Wallet | Register agent action |
| `mintAgentBuilder` | `builderType`, `parentTokenId` | Public | Mint agent builder NFT |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getAgentData` | `tokenId` | `AgentData` | Get agent data |
| `getAgentActions` | `tokenId` | `ActionData[]` | Get agent actions |
| `getAgentCapability` | `tokenId`, `capability` | `string` | Get capability value |
| `hasPermission` | `tokenId`, `permission` | `bool` | Check permission |

## Usage Examples

### Creating Agent Prompt

```javascript
const agentId = keccak256("agent-1");
const basePrompt = "You are a trading agent";
const modifiers = ["aggressive", "risk-tolerant"];
const capabilities = ["trading", "analysis"];
const values = ["enabled", "enabled"];

const tokenId = await nfprompt.createAgentPrompt(
    agentId,
    basePrompt,
    modifiers,
    capabilities,
    values
);
```

### Registering Agent Action

```javascript
const tokenId = 1;
const actionType = "execute_trade";
const parameters = encodeTradeParams(...);
const requiresApproval = false;

await nfprompt.registerAgentAction(
    tokenId,
    actionType,
    parameters,
    requiresApproval
);
```

## Integration Points

### For AgenticPlace

```javascript
// Agent prompts can be hired as skills
await agenticPlace.offerSkill(
    promptTokenId,
    nfpromptAddress,
    price,
    true,
    address(0),
    0
);
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
