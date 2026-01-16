# IAgenticPlace

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/marketplace/IAgenticPlace.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT Marketplace - Interface |
| **Inherits** | Interface |

## Summary

IAgenticPlace is the interface for AgenticPlace foundational marketplace. It allows iNFT, dNFT, and other contracts to interact with AgenticPlace in a standardized way.

## Purpose

- Define standard interface for marketplace interactions
- Enable contract-to-contract integration
- Support multiple NFT types
- Standardize skill offering and hiring

## Interface Functions

```solidity
function offerSkill(
    uint256 skillTokenId,
    address nftContract,
    uint256 price,
    bool isETH,
    address paymentToken,
    uint40 expiresAt
) external;

function hireSkillETH(
    uint256 skillTokenId,
    address nftContract
) external payable;

function hireSkillERC20(
    uint256 skillTokenId,
    address nftContract,
    uint256 amount
) external;

function getSkillOffer(
    uint256 skillTokenId,
    address nftContract
) external view returns (SkillOffer memory);

function whitelistNFTContract(
    address nftContract,
    NFTType nftType
) external;

function isNFTContractWhitelisted(address nftContract) external view returns (bool);
function getNFTType(address nftContract) external view returns (NFTType);
```

## Usage Examples

### Implementing Interface

```solidity
contract MyNFT is IERC721 {
    IAgenticPlace public agenticPlace;
    
    function listOnMarketplace(
        uint256 tokenId,
        uint256 price
    ) external {
        agenticPlace.offerSkill(
            tokenId,
            address(this),
            price,
            true,
            address(0),
            0
        );
    }
}
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
