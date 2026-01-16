# iNFT - Immutable THOT

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/inft/iNFT.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.20 |
| **Category** | INFT - Immutable THOT NFT |
| **Inherits** | ERC721, ERC721URIStorage, Ownable |

## Summary

iNFT (Immutable THOT) is an ERC721 implementation for creating immutable THOT (Transferable Hyper-Optimized Tensor) NFTs. Unlike the standard THOT contract, iNFT creates immutable tokens with deterministic token IDs based on the data CID, timestamp, and recipient address.

## Purpose

- Create immutable THOT NFTs
- Generate deterministic token IDs
- Store THOT tensor data (CID, dimensions, parallel units)
- Prevent duplicate THOTs via CID tracking
- Enable verification status tracking

## Technical Specification

### Data Structures

```solidity
struct ThotData {
    bytes32 dataCID;      // IPFS CID hash
    uint8 dimensions;     // 64, 512, or 768
    uint8 parallelUnits;  // Processing units
    uint40 timestamp;     // Creation time
    bool verified;        // Verification status
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `_thotData` | `mapping(uint256 => ThotData)` | THOT data storage |
| `_cidExists` | `mapping(bytes32 => bool)` | CID existence tracking |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `mint` | `recipient`, `dataCID`, `dimensions`, `parallelUnits` | Owner | Mint immutable THOT NFT |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getThotData` | `tokenId` | `ThotData` | Get THOT data structure |
| `tokenURI` | `tokenId` | `string` | Get token URI (inherited) |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `ThotMinted` | `tokenId`, `dataCID`, `dimensions`, `timestamp` | New iNFT minted |

## Key Features

### Deterministic Token IDs

Unlike standard THOT which uses a counter, iNFT generates deterministic token IDs:

```solidity
uint256 tokenId = uint256(
    keccak256(abi.encodePacked(dataCID, block.timestamp, recipient))
);
```

This ensures:
- Same CID + timestamp + recipient = same token ID
- Immutable once minted
- No sequential token ID dependency

### Immutability

- Once minted, THOT data cannot be changed
- CID uniqueness prevents duplicates
- Verification status set to `true` on mint

### Dimension Standards

Supports three standard dimensions:
- **64**: Lightweight tensors
- **512**: Standard tensors (most common)
- **768**: High-dimensional tensors

## Usage Examples

### Minting an iNFT

```javascript
const recipient = agentAddress;
const dataCID = ipfsCIDHash; // bytes32
const dimensions = 512; // 64, 512, or 768
const parallelUnits = 4;

const tokenId = await inft.mint(
    recipient,
    dataCID,
    dimensions,
    parallelUnits
);
```

### Getting iNFT Data

```javascript
const tokenId = 1;
const thotData = await inft.getThotData(tokenId);

console.log(`CID: ${thotData.dataCID}`);
console.log(`Dimensions: ${thotData.dimensions}`);
console.log(`Parallel Units: ${thotData.parallelUnits}`);
console.log(`Timestamp: ${thotData.timestamp}`);
console.log(`Verified: ${thotData.verified}`);
```

## Comparison with THOT

| Feature | THOT | iNFT |
|---------|------|------|
| Token ID | Sequential counter | Deterministic hash |
| Mutability | Can update metadata | Immutable |
| CID Tracking | Yes | Yes |
| Verification | Can toggle | Set on mint |
| Use Case | Mutable THOTs | Immutable THOTs |

## Integration Points

### For AgenticPlace

```javascript
// iNFTs can be listed on marketplace
await agenticPlace.offerSkill(
    inftTokenId,
    inftAddress,
    price,
    true, // isETH
    address(0), // paymentToken
    expiresAt
);
```

### For TransmuteAgent

```javascript
// Can create iNFTs from transmuted data
const dataCID = keccak256(transformedData);
const tokenId = await inft.mint(recipient, dataCID, 512, 4);
```

## Security Considerations

- **Access Control**: Only owner can mint
- **CID Uniqueness**: Prevents duplicate THOTs
- **Dimension Validation**: Only allows 64, 512, or 768
- **Immutability**: Once minted, data cannot be changed
- **ERC721 Standard**: Full NFT compatibility

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `mint` | ~120,000 |
| `getThotData` | ~2,000 (view) |

## Use Cases

1. **Immutable Knowledge**: Store permanent agent knowledge
2. **Deterministic IDs**: Predictable token IDs for integration
3. **Verification**: Pre-verified THOTs on mint
4. **Marketplace**: List immutable skills on AgenticPlace
5. **Identity**: Link immutable knowledge to agent identity

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
