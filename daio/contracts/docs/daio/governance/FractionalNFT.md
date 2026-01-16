# FractionalNFT

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/daio/governance/FractionalNFT.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | Governance Layer - NFT Fractionalization |
| **Inherits** | ERC20, Ownable |

## Summary

FractionalNFT fractionalizes ERC721 NFTs into ERC20 tokens, enabling shared ownership and governance. This allows multiple holders to own fractions of an NFT for voting and governance purposes.

## Purpose

- Fractionalize NFTs into ERC20 tokens
- Enable shared ownership of governance NFTs
- Support fractional voting and governance
- Allow redemption of full NFT with all fractions

## Technical Specification

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `nftAddress` | `address` | Original NFT contract (immutable) |
| `nftId` | `uint256` | NFT token ID (immutable) |
| `totalFractions` | `uint256` | Total fractions created (immutable) |
| `redeemed` | `bool` | Whether NFT has been redeemed |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `redeemNFT` | - | Public | Redeem all fractions to claim NFT |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getOwnershipPercentage` | `holder` | `uint256` | Get ownership percentage (basis points) |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `NFTFractionalized` | `nftAddress`, `nftId`, `totalFractions` | NFT fractionalized |
| `NFTRedeemed` | `redeemer`, `nftId` | NFT redeemed |

## Usage Examples

### Creating Fractional NFT

```javascript
const nftAddress = agentFactoryAddress;
const nftId = 1;
const totalFractions = 1000;
const initialOwner = creatorAddress;

const fractionalNFT = await FractionalNFT.deploy(
    nftAddress,
    nftId,
    totalFractions,
    initialOwner
);
```

### Redeeming NFT

```javascript
// Must hold all fractions to redeem
const totalSupply = await fractionalNFT.totalSupply();
const balance = await fractionalNFT.balanceOf(msg.sender);

if (balance == totalSupply) {
    await fractionalNFT.redeemNFT();
}
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
