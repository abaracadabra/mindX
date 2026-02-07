# Dynamic NFT (dNFT) — Documentation

Documentation for the DAIO **Dynamic NFT** contracts: ERC721 tokens with updatable metadata (ERC4906-style), optional AgenticPlace integration, and freezing.

**Source:** [../../dnft/](../../dnft/) — `DynamicNFT.sol`, `IDynamicNFT.sol`, `DynamicNFTFactory.sol`

---

## Contents

| Document | Description |
|----------|-------------|
| **[TECHNICAL.md](TECHNICAL.md)** | Architecture, interfaces, state layout, token URI building, security, and implementation notes. |
| **[USAGE.md](USAGE.md)** | Full usage guide: deployment, minting, updating metadata, freezing, marketplace, and integration. |

---

## Quick reference

- **What:** ERC721 with stored `NFTMetadata` (name, description, imageURI, externalURI, thotCID, isDynamic, lastUpdated) and derived or direct token URI. Metadata can be updated until frozen.
- **Who:** Contract owner mints and sets AgenticPlace; token owner or contract owner can update metadata (if not frozen) and freeze.
- **Where:** [../../dnft/DynamicNFT.sol](../../dnft/DynamicNFT.sol), [../../dnft/interfaces/IDynamicNFT.sol](../../dnft/interfaces/IDynamicNFT.sol), [../../dnft/DynamicNFTFactory.sol](../../dnft/DynamicNFTFactory.sol).

See [TECHNICAL.md](TECHNICAL.md) for specification and [USAGE.md](USAGE.md) for step-by-step usage.
