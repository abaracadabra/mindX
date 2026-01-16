# NFRLT - NFT Royalty Token

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/nft/NFRLT.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT NFT - Royalty Distribution |
| **Inherits** | ERC721, AccessControl, ReentrancyGuard |

## Summary

NFRLT (NFT Royalty Token) is an NFT with royalty distribution and soulbound support. It enables automatic royalty payments on transfers, supports multiple royalty recipients, and can create soulbound NFTs that cannot be transferred.

## Purpose

- Create NFTs with royalty distribution
- Support multiple royalty recipients (up to 5)
- Enable soulbound NFTs (non-transferable)
- Store user identity data
- Support ETH and ERC20 payments

## Technical Specification

### Data Structures

```solidity
struct TokenSaleInfo {
    uint256 salePriceETH;
    SalePriceERC20 salePriceERC20;
    bool isListed;
    uint256 lastUpdateTime;
}

struct RoyaltyInfo {
    address payable recipient;
    uint256 percentage;        // 0-25%
    uint256 fixedAmount;       // Fixed amount in wei
    bool isActive;
}

struct UserIdentity {
    string username;
    string class;
    uint32 level;
    uint32 health;
    uint32 stamina;
    uint32 strength;
    uint32 intelligence;
    uint32 dexterity;
    bool isSoulbound;
}
```

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `createNFT` | `tokenURI` | Minter | Create standard NFT |
| `createSoulboundNFT` | `to`, `tokenURI`, identity params | Minter | Create soulbound NFT |
| `addRoyalty` | `tokenId`, `recipient`, `percentage`, `fixedAmount` | Owner | Add royalty recipient |
| `brokerTransferETH` | `from`, `to`, `tokenId` | Public (payable) | Transfer with royalty distribution |
| `setSalePrice` | `tokenId`, `price`, `currency` | Owner | Set sale price |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getUserIdentity` | `tokenId` | `UserIdentity` | Get user identity |
| `isTokenSoulbound` | `tokenId` | `bool` | Check if soulbound |
| `tokenURI` | `tokenId` | `string` | Get token URI |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `RoyaltyPaid` | `recipient`, `tokenId`, `amount`, `currency` | Royalty distributed |
| `NFTTransferred` | `from`, `to`, `tokenId`, `salePrice`, `currency` | NFT transferred |
| `SalePriceUpdated` | `tokenId`, `newPrice`, `currency` | Sale price updated |

## Usage Examples

### Creating a Standard NFT

```javascript
const tokenURI = "ipfs://metadata";
const tokenId = await nfrlt.createNFT(tokenURI);
```

### Creating a Soulbound NFT

```javascript
const to = userAddress;
const tokenURI = "ipfs://soulbound-metadata";
const username = "Agent1";
const class_ = "Trader";
const level = 1;
const health = 100;
const stamina = 50;
const strength = 10;
const intelligence = 20;
const dexterity = 15;

const tokenId = await nfrlt.createSoulboundNFT(
    to,
    tokenURI,
    username,
    class_,
    level,
    health,
    stamina,
    strength,
    intelligence,
    dexterity
);
```

### Adding Royalty

```javascript
const tokenId = 1;
const recipient = royaltyAddress;
const percentage = 5; // 5%
const fixedAmount = 0;

await nfrlt.addRoyalty(tokenId, recipient, percentage, fixedAmount);
```

### Broker Transfer with Royalties

```javascript
const from = sellerAddress;
const to = buyerAddress;
const tokenId = 1;

await nfrlt.brokerTransferETH(from, to, tokenId, {
    value: ethers.utils.parseEther("1.0")
});
```

## Integration Points

### For AgenticPlace

```javascript
// NFRLT automatically distributes royalties on hire
await agenticPlace.hireSkillETH(skillTokenId, nfrltAddress, { value: price });
```

### For SoulBadger

```javascript
// Soulbound NFRLTs can represent credentials
const badgeId = await nfrlt.createSoulboundNFT(...);
```

## Security Considerations

- **Royalty Limits**: Maximum 25% total royalty
- **Soulbound Protection**: Soulbound NFTs cannot be transferred
- **Access Control**: Role-based minting and admin functions
- **Reentrancy Protection**: Transfer functions protected

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
