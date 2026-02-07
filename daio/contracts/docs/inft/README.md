# Intelligent NFT (iNFT) — Documentation

Documentation for the DAIO **Intelligent NFT** contracts: ERC721 tokens extending DynamicNFT with per-token intelligence configuration and agent interaction.

**Source:** [../../inft/](../../inft/) — `IntelligentNFT.sol`, `IIntelligentNFT.sol`, `IntelligentNFTFactory.sol`, `iNFT.sol`

---

## Contents

| Document | Description |
|----------|-------------|
| **[TECHNICAL.md](TECHNICAL.md)** | Architecture, interfaces, state layout, authorization, events, and security for IntelligentNFT. |
| **[USAGE.md](USAGE.md)** | Full usage guide: deployment, minting, agent interaction, THOT linking, marketplace, and integration. |
| **[iNFT.md](iNFT.md)** | **Immutable THOT** contract (`iNFT.sol`): deterministic THOT NFTs with `ThotData` — separate from IntelligentNFT. |

---

## Two contracts in this folder

| Contract | Purpose |
|----------|---------|
| **IntelligentNFT.sol** | Full iNFT: dynamic metadata (dNFT) + per-token `IntelligenceConfig` + `agentInteract`. Use for skills, agent-bound assets, vault keys. |
| **iNFT.sol** | Immutable THOT ERC721: `ThotData` (dataCID, dimensions, parallelUnits). No metadata updates, no agent config. Use for THOT-only minting. |

See [TECHNICAL.md](TECHNICAL.md) and [USAGE.md](USAGE.md) for **IntelligentNFT**; see [iNFT.md](iNFT.md) for **iNFT.sol**.
