# Intelligent NFT (iNFT) Contracts

**Purpose:** ERC721 NFTs with intelligence capabilities extending DynamicNFT  
**Status:** Ready for deployment  
**Version:** 1.0.0

**Full technical summary and usage:** **[USAGE.md](USAGE.md)** — complete API, data structures, authorization, deployment, minting, agent interaction, THOT linking, and integration (mindX, keyminter, AgenticPlace).

---

## Overview

Intelligent NFTs (iNFT) extend Dynamic NFTs with on-chain intelligence capabilities. They can interact with agents and exhibit autonomous behavior.

### Key Features

- **All dNFT Features** - Everything from DynamicNFT
- **Agent Interaction** - Agents can interact with NFTs
- **Autonomous Behavior** - NFTs can act autonomously
- **Intelligence Configuration** - Configurable intelligence levels
- **THOT Integration** - Optional THOT for enhanced intelligence

---

## Contracts

### IntelligentNFT.sol

Extends DynamicNFT with intelligence.

**Functions:**
- `mintIntelligent(address to, NFTMetadata memory nftMetadata, IntelligenceConfig memory intelConfig)` - Mint intelligent NFT
- `agentInteract(uint256 tokenId, bytes calldata interactionData)` - Agent interaction
- `updateIntelligence(uint256 tokenId, IntelligenceConfig memory newConfig)` - Update intelligence
- `intelligence(uint256 tokenId)` - Get intelligence config

### IntelligentNFTFactory.sol

Factory contract for easy deployment.

**Functions:**
- `deployIntelligentNFT(string memory name, string memory symbol, address agenticPlace)` - Deploy new iNFT contract
- `getDeployedContracts(address deployer)` - Get contracts by deployer
- `getTotalContracts()` - Get total deployed contracts

---

## Usage

### Deploy via Factory

```solidity
// Deploy factory first
factory.deployIntelligentNFT("My iNFT Collection", "MINFT");

// Then mint intelligent NFTs
nft.mintIntelligent(to, metadata, intelConfig);
```

### Direct Deployment

```bash
./scripts/deploy/deploy_inft.sh polygon "My iNFT Collection" "MINFT"
```

---

## Intelligence Configuration

```solidity
struct IntelligenceConfig {
    address agentAddress;      // Agent that can interact
    bool autonomous;           // Can act autonomously
    string behaviorCID;       // IPFS CID for behavior definition
    string thotCID;           // Optional THOT for intelligence
    uint256 intelligenceLevel; // Level of intelligence (0-100)
}
```

---

## Integration

- **FinancialMind** - Intelligent trading strategies as iNFTs
- **DAIO** - Intelligent governance participants
- **mindX** - Orchestration of intelligent assets
- **Agents** - Direct interaction with iNFTs

---

**Last Updated:** 2026-02-05
