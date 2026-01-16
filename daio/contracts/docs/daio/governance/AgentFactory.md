# AgentFactory

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/governance/AgentFactory.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - Agent Management |
| **Inherits** | Ownable, ERC721URIStorage |

## Summary

AgentFactory is a production agent creation factory that creates agents with custom ERC20 tokens and fractionalized NFTs for governance. It integrates with IDNFT for identity linking and KnowledgeHierarchyDAIO for governance participation.

## Purpose

- Create agents with custom ERC20 tokens
- Mint governance NFTs for agent representation
- Link agents to IDNFT identities
- Register agents with KnowledgeHierarchyDAIO
- Manage agent lifecycle (create, destroy, reactivate)

## Technical Specification

### Data Structures

```solidity
struct Agent {
    address agentAddress;
    bool active;
    uint256 createdAt;
    address tokenAddress;      // Custom ERC20 token address
    uint256 nftId;            // NFT ID for governance rights
    bytes32 metadataHash;      // Metadata hash for gas optimization
    uint256 idNFTTokenId;      // Linked IDNFT token ID (optional)
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `agents` | `mapping(address => Agent)` | Agent registry |
| `nftToAgent` | `mapping(uint256 => address)` | NFT ID to agent mapping |
| `governanceContract` | `address` | Governance contract (immutable) |
| `idNFT` | `IDNFT` | IDNFT contract |
| `knowledgeHierarchy` | `KnowledgeHierarchyDAIO` | Knowledge hierarchy contract |
| `agentCount` | `uint256` | Total agent count |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `createAgent` | `_agentAddress`, `_metadataHash`, `_tokenName`, `_tokenSymbol`, `_nftMetadata`, `_idNFTTokenId` | Governance | Create agent with token and NFT |
| `updateNFTMetadata` | `nftId`, `newMetadata` | NFT Owner | Update agent NFT metadata |
| `reactivateAgent` | `_agentAddress` | Governance | Reactivate inactive agent |
| `destroyAgent` | `_agentAddress` | Governance | Deactivate agent |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `agents` | `agentAddress` | `Agent` | Get agent details |
| `nftToAgent` | `nftId` | `address` | Get agent by NFT ID |
| `isAgentActive` | `agentAddress` | `bool` | Check if agent active |
| `getAgentByNFT` | `nftId` | `Agent` | Get agent by NFT ID |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `AgentCreated` | `agentAddress`, `timestamp`, `metadataHash`, `tokenAddress`, `nftId`, `idNFTTokenId` | New agent created |
| `AgentDestroyed` | `agentAddress`, `timestamp` | Agent deactivated |
| `AgentReactivated` | `agentAddress`, `timestamp` | Agent reactivated |
| `NFTMetadataUpdated` | `nftId`, `newMetadata` | NFT metadata updated |

## Usage Examples

### Creating an Agent

```javascript
const agentAddress = agentWalletAddress;
const metadataHash = keccak256(agentMetadata);
const tokenName = "AgentToken";
const tokenSymbol = "AGT";
const nftMetadata = "ipfs://agent-nft-metadata";
const idNFTTokenId = 1; // Optional

await agentFactory.createAgent(
    agentAddress,
    metadataHash,
    tokenName,
    tokenSymbol,
    nftMetadata,
    idNFTTokenId
);
```

## Integration Points

### For IDNFT

```javascript
// Link agent to IDNFT identity
const idNFTTokenId = await idnft.mintAgentIdentity(...);
await agentFactory.createAgent(..., idNFTTokenId);
```

### For KnowledgeHierarchyDAIO

```javascript
// Register agent for governance after creation
await knowledgeHierarchy.addOrUpdateAgent(
    agentAddress,
    knowledgeLevel,
    domain,
    true
);
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
