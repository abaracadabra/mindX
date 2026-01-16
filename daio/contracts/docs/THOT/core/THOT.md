# THOT - Transferable Hyper-Optimized Tensor

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/core/THOT.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT Core - Tensor NFT |
| **Inherits** | ERC721, ERC721URIStorage, Ownable |

## Summary

THOT (Transferable Hyper-Optimized Tensor) is the core contract for creating and managing THOT artifacts. THOTs are standardized 512-dimension f32 vectors (or 64/768) with metadata stored as ERC721 NFTs. Each THOT represents a knowledge tensor that can be transferred, verified, and used in AI/ML applications.

## Purpose

- Create and mint THOT tensors as NFTs
- Store tensor metadata (dimensions, CID, parallel units)
- Verify THOT authenticity
- Enable transferable knowledge representation
- Support multiple dimension standards (64, 512, 768)

## Technical Specification

### Data Structures

```solidity
struct THOTData {
    bytes32 dataCID;      // IPFS CID hash for THOT tensor data
    uint8 dimensions;     // THOT dimensions: 64, 512, or 768
    uint8 parallelUnits;  // Processing units
    uint40 timestamp;     // Creation time
    bool verified;        // Verification status
    string metadataURI;   // Additional metadata URI
}
```

### State Variables

| Variable | Type | Description |
|----------|------|-------------|
| `_thotData` | `mapping(uint256 => THOTData)` | THOT data storage |
| `_cidExists` | `mapping(bytes32 => bool)` | CID existence tracking |
| `_cidToTokenId` | `mapping(bytes32 => uint256)` | CID to token ID mapping |
| `_tokenIdCounter` | `uint256` | Token ID counter |

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `mintTHOT` | `recipient`, `dataCID`, `dimensions`, `parallelUnits`, `metadataURI` | Owner | Mint new THOT with full parameters |
| `mintTHOT` | `dataHash` | Owner | Mint THOT with string hash (TransmuteAgent compatibility) |
| `verifyTHOT` | `tokenId`, `verified` | Owner | Verify/unverify a THOT |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `getTHOTData` | `tokenId` | `THOTData` | Get THOT data structure |
| `getTokenIdByCID` | `dataCID` | `uint256` | Get token ID by CID |
| `cidExists` | `dataCID` | `bool` | Check if CID exists |

### Events

| Event | Parameters | Trigger |
|-------|------------|---------|
| `THOTMinted` | `tokenId`, `dataCID`, `dimensions`, `timestamp` | New THOT minted |
| `THOTVerified` | `tokenId`, `verified` | THOT verification status changed |

## Usage Examples

### Minting a THOT

```javascript
const recipient = agentAddress;
const dataCID = ipfsCIDHash;
const dimensions = 512; // 64, 512, or 768
const parallelUnits = 4;
const metadataURI = "ipfs://metadata-uri";

const tokenId = await thot.mintTHOT(
    recipient,
    dataCID,
    dimensions,
    parallelUnits,
    metadataURI
);
```

### Getting THOT Data

```javascript
const tokenId = 1;
const thotData = await thot.getTHOTData(tokenId);

console.log(`CID: ${thotData.dataCID}`);
console.log(`Dimensions: ${thotData.dimensions}`);
console.log(`Verified: ${thotData.verified}`);
```

### Verifying a THOT

```javascript
const tokenId = 1;
await thot.verifyTHOT(tokenId, true);
```

## Integration Points

### For TransmuteAgent

```javascript
// TransmuteAgent uses simplified minting
const thotId = await thot.mintTHOT(dataHash);
```

### For AgenticPlace

```javascript
// THOTs can be listed on marketplace
await agenticPlace.offerSkill(
    thotTokenId,
    thotContractAddress,
    price,
    true, // isETH
    address(0), // paymentToken
    expiresAt
);
```

## Security Considerations

- **Access Control**: Only owner can mint/verify
- **CID Uniqueness**: Prevents duplicate THOTs
- **Dimension Validation**: Only allows 64, 512, or 768 dimensions
- **ERC721 Standard**: Full NFT compatibility

## Gas Estimates

| Function | Estimated Gas |
|----------|---------------|
| `mintTHOT` (full) | ~150,000 |
| `mintTHOT` (string) | ~120,000 |
| `verifyTHOT` | ~30,000 |
| `getTHOTData` | ~2,000 (view) |

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
