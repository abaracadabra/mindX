# gNFT - Graphics NFT

## Contract Overview

| Property | Value |
|----------|-------|
| **File** | `contracts/THOT/nft/gNFT.sol` |
| **License** | MIT |
| **Solidity** | ^0.8.24 |
| **Category** | THOT NFT - Graphics Visualization |
| **Inherits** | ERC721, Ownable |

## Summary

gNFT (Graphics NFT) is a graphics component for visualization of THOT data. It enables creation of visual representations of THOT tensors with SVG, animations, and external viewer URLs.

## Purpose

- Create visual representations of THOT data
- Store graphics metadata (SVG, animations)
- Enable dynamic visual updates
- Support multiple visualization types
- Link to external viewers

## Technical Specification

### Data Structures

```solidity
struct VisualData {
    string baseImage;     // Base SVG or IPFS image
    string animationUrl;  // Optional 3D/animation URL
    string externalUrl;   // External viewer URL
    uint8 visualType;     // Type of visualization
    bool dynamic;         // Whether visual can be updated
}
```

### Functions

#### Write Functions

| Function | Parameters | Access | Description |
|----------|------------|--------|-------------|
| `createVisual` | `recipient`, `baseImage`, `animationUrl`, `externalUrl`, `visualType`, `dynamic` | Owner | Create new gNFT |
| `updateVisual` | `tokenId`, `newBaseImage`, `newAnimationUrl` | Token Owner | Update visual (if dynamic) |
| `setAttribute` | `tokenId`, `key`, `value` | Token Owner | Set custom attribute |

#### Read Functions

| Function | Parameters | Returns | Description |
|----------|------------|---------|-------------|
| `tokenURI` | `tokenId` | `string` | Get base64 encoded metadata |

## Usage Examples

### Creating a gNFT

```javascript
const recipient = ownerAddress;
const baseImage = "ipfs://svg-image";
const animationUrl = "ipfs://3d-model";
const externalUrl = "https://viewer.example.com";
const visualType = 1; // 2D visualization
const dynamic = true;

const tokenId = await gnft.createVisual(
    recipient,
    baseImage,
    animationUrl,
    externalUrl,
    visualType,
    dynamic
);
```

### Updating Visual

```javascript
const tokenId = 1;
const newBaseImage = "ipfs://updated-svg";
const newAnimationUrl = "ipfs://updated-3d";

await gnft.updateVisual(tokenId, newBaseImage, newAnimationUrl);
```

## Integration Points

### For THOT

```javascript
// gNFT can visualize THOT tensors
const thotData = await thot.getTHOTData(thotId);
const visual = createVisualization(thotData);
await gnft.createVisual(recipient, visual, ...);
```

---

**Last Updated**: 2026-01-15  
**Version**: 1.0.0
