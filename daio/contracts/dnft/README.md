# Dynamic NFT (dNFT) Contracts

**Purpose:** ERC721 NFTs with dynamic metadata support (ERC4906 compatible)  
**Status:** Ready for deployment  
**Version:** 1.0.0

**Full technical summary and usage:** **[USAGE.md](USAGE.md)** — complete API, NFTMetadata, token URI building, authorization, deployment, minting, updates, freezing, and integration (iNFT, keyminter, THOT, AgenticPlace).

---

## Overview

Dynamic NFTs (dNFT) are ERC721 tokens with updateable metadata. They can be created with or without THOT artifacts and work standalone or within mindX orchestration.

### Key Features

- **ERC721 Compliance** - Standard NFT functionality
- **Dynamic Metadata** - Update metadata after minting (ERC4906 compatible)
- **IPFS Integration** - Store images and metadata on IPFS
- **THOT-Optional** - Link THOT artifacts when relevant
- **Metadata Freezing** - Lock metadata to prevent further updates
- **Easy Deployment** - Factory contract for simplified deployment

---

## Contracts

### DynamicNFT.sol

Base contract for dynamic NFTs.

**Functions:**
- `mint(address to, NFTMetadata memory nftMetadata)` - Mint new NFT (onlyOwner)
- `updateMetadata(uint256 tokenId, NFTMetadata memory newMetadata)` - Update metadata (owner or token owner; not frozen)
- `setTokenURI(uint256 tokenId, string memory newURI)` - Set token URI directly
- `freezeMetadata(uint256 tokenId)` - Freeze metadata (owner or token owner)
- `metadata(uint256 tokenId)` - Get metadata
- `frozen(uint256 tokenId)` - Check if frozen
- `setAgenticPlace(address)` - Set marketplace (onlyOwner)
- `offerSkillOnMarketplace(...)` - List skill (token owner; requires AgenticPlace)

### DynamicNFTFactory.sol

Factory contract for easy deployment.

**Functions:**
- `deployDynamicNFT(string memory name, string memory symbol, address agenticPlace)` - Deploy new dNFT contract
- `getDeployedContracts(address deployer)` - Get contracts by deployer
- `getTotalContracts()` - Get total deployed contracts

---

## Usage

### Deploy via Factory

```solidity
// Deploy factory first (agenticPlace can be address(0))
factory.deployDynamicNFT("My Collection", "MC", agenticPlace);

// Then mint NFTs
nft.mint(to, metadata);
```

### Direct Deployment

```bash
./scripts/deploy/deploy_dnft.sh polygon "My Collection" "MC"
```

---

## Metadata Structure

```solidity
struct NFTMetadata {
    string name;
    string description;
    string imageURI;        // IPFS CID or URL
    string externalURI;     // Optional external link
    string thotCID;         // Optional THOT artifact CID
    bool isDynamic;         // Can metadata be updated
    uint256 lastUpdated;    // Timestamp of last update
}
```

---

## Integration

- **FinancialMind** - Agents can create dNFTs from trading data
- **DAIO** - NFTs can be used in governance
- **mindX** - Orchestration of NFT workflows
- **THOT** - Optional linking to THOT artifacts

---

**Last Updated:** 2026-02-05
