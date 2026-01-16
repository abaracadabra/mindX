# AgenticPlace

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/marketplace/AgenticPlace.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT Marketplace - Skills Market |
| **Inherits** | Ownable, ReentrancyGuard |

## Summary

AgenticPlace is a foundational standalone marketplace contract for NFT skills and services. It supports multiple NFT types (NFRLT, THOT, AgentFactory NFTs, ERC721) and enables hiring of NFT-based skills with royalty distribution.

## Purpose

- Marketplace for NFT skills and services
- Support multiple NFT types (NFRLT, THOT, AgentNFT, ERC721)
- Enable skill hiring with ETH or ERC20
- Distribute royalties automatically
- Whitelist NFT contracts and payment tokens

## Technical Specification

### Data Structures

```solidity
enum NFTType {
    NFRLT,      // NFT Royalty Token
    THOT,       // Transferable Hyper-Optimized Tensor
    AgentNFT,   // AgentFactory NFT
    ERC721      // Generic ERC721
}

struct SkillOffer {
    uint256 skillTokenId;
    NFTType nftType;
    address nftContract;
    uint256 price;
    bool isETH;
    address paymentToken;
    address owner;
    bool isActive;
    uint40 createdAt;
    uint40 expiresAt;
}
```

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `offerSkill` | `skillTokenId`, `nftContract`, `price`, `isETH`, `paymentToken`, `expiresAt` | Public | Offer NFT skill for hire |
| `hireSkillETH` | `skillTokenId`, `nftContract` | Public (payable) | Hire skill with ETH |
| `hireSkillERC20` | `skillTokenId`, `nftContract`, `amount` | Public | Hire skill with ERC20 |
| `removeSkillOffer` | `skillTokenId`, `nftContract` | Owner | Remove skill offer |
| `whitelistNFTContract` | `nftContract`, `nftType` | Owner | Whitelist NFT contract |
| `whitelistPaymentToken` | `token`, `status` | Owner | Whitelist payment token |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getSkillOffer` | `skillTokenId`, `nftContract` | `SkillOffer` | Get offer details |
| `isNFTContractWhitelisted` | `nftContract` | `bool` | Check if whitelisted |
| `getNFTType` | `nftContract` | `NFTType` | Get NFT type |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `SkillOffered` | `skillTokenId`, `nftContract`, `nftType`, `price`, `isETH`, `paymentToken`, `owner`, `expiresAt` | Skill offered |
| `SkillHired` | `skillTokenId`, `nftContract`, `hirer`, `owner`, `price`, `isETH`, `royaltyAmount` | Skill hired |
| `SkillRemoved` | `skillTokenId`, `nftContract`, `owner` | Skill removed |

## Usage Examples

### Offering a Skill

```javascript
const skillTokenId = 1;
const nftContract = thotAddress;
const price = ethers.utils.parseEther("1.0");
const isETH = true;
const paymentToken = address(0);
const expiresAt = 0; // No expiration

await agenticPlace.offerSkill(
    skillTokenId,
    nftContract,
    price,
    isETH,
    paymentToken,
    expiresAt
);
```

### Hiring a Skill with ETH

```javascript
const skillTokenId = 1;
const nftContract = thotAddress;

await agenticPlace.hireSkillETH(skillTokenId, nftContract, {
    value: ethers.utils.parseEther("1.0")
});
```

### Hiring a Skill with ERC20

```javascript
const skillTokenId = 1;
const nftContract = thotAddress;
const amount = ethers.utils.parseEther("100");

await tokenContract.approve(agenticPlace.address, amount);
await agenticPlace.hireSkillERC20(skillTokenId, nftContract, amount);
```

## Integration Points

### For NFRLT

```javascript
// NFRLT royalties distributed automatically
await agenticPlace.hireSkillETH(skillTokenId, nfRLTAddress, { value: price });
```

### For THOT

```javascript
// THOTs can be hired as skills
await agenticPlace.offerSkill(thotTokenId, thotAddress, price, true, address(0), 0);
```

### For AgentFactory

```javascript
// Agent NFTs can be hired
// Active status checked automatically
await agenticPlace.hireSkillETH(agentNFTId, agentFactoryAddress, { value: price });
```

## Security Considerations

- **Reentrancy Protection**: All hire functions protected
- **Whitelist Validation**: Only whitelisted contracts/tokens
- **Active Agent Check**: AgentFactory NFTs checked for active status
- **Expiration Validation**: Expired offers rejected

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
