# Intelligent NFT (iNFT) — Technical Specification

Technical architecture, interfaces, state, and security for the DAIO IntelligentNFT contracts.

**Contracts:** [../../inft/IntelligentNFT.sol](../../inft/IntelligentNFT.sol), [../../inft/interfaces/IIntelligentNFT.sol](../../inft/interfaces/IIntelligentNFT.sol), [../../inft/IntelligentNFTFactory.sol](../../inft/IntelligentNFTFactory.sol)

---

## 1. Architecture

### 1.1 Inheritance

```
IntelligentNFT
  ├── DynamicNFT (ERC721, ERC721URIStorage, Ownable, IDynamicNFT)
  │     ├── ERC721, ERC721URIStorage, Ownable
  │     └── IAgenticPlace (internal ref)
  └── IIntelligentNFT (IDynamicNFT + IntelligenceConfig + agent APIs)
```

- IntelligentNFT adds one storage mapping (`_intelligence`) and overrides `setAgenticPlace` and `offerSkillOnMarketplace` for interface compliance.
- All dNFT behavior (mint, updateMetadata, freezeMetadata, metadata, frozen, setTokenURI, offerSkillOnMarketplace) is inherited; iNFT-specific entrypoints are `mintIntelligent`, `mintWithAgent`, `agentInteract`, `triggerIntelligence`, `updateIntelligence`, `updateAgent`, `linkTHOT`, `intelligence`.

### 1.2 Interface IIntelligentNFT

Extends **IDynamicNFT** (NFTMetadata, mint, updateMetadata, freezeMetadata, metadata, frozen).

**Struct:** `IntelligenceConfig(agentAddress, autonomous, behaviorCID, thotCID, intelligenceLevel)`

**Events:**
- `AgentInteraction(uint256 indexed tokenId, address indexed agent, bytes interactionData)`
- `IntelligenceUpdated(uint256 indexed tokenId, IntelligenceConfig config)`

**Functions:** `mintIntelligent(to, nftMetadata, intelConfig)`, `agentInteract(tokenId, interactionData)`, `updateIntelligence(tokenId, newConfig)`, `intelligence(tokenId)`.

IntelligentNFT also exposes: `mintWithAgent`, `linkTHOT`, `triggerIntelligence`, `updateAgent`.

### 1.3 Dependency: DynamicNFT and IAgenticPlace

- DynamicNFT provides metadata and URI handling and optional AgenticPlace listing.
- IAgenticPlace is unchanged from dNFT: whitelist and `offerSkill` delegation.

---

## 2. State Layout (IntelligentNFT)

| Variable | Type | Description |
|----------|------|-------------|
| `_intelligence` | `mapping(uint256 => IntelligenceConfig)` | Per-token intelligence config. |

All other state (metadata, frozen, tokenIdCounter, agenticPlace, ERC721 state) is inherited from DynamicNFT and ERC721.

---

## 3. Data Structures

**NFTMetadata** (from IDynamicNFT): name, description, imageURI, externalURI, thotCID, isDynamic, lastUpdated.

**IntelligenceConfig:**
- `agentAddress` — Address allowed to call `agentInteract` (and, when `autonomous`, future on-chain behavior). Can be zero to disable.
- `autonomous` — Reserved for future autonomous behavior when `agentAddress` calls.
- `behaviorCID` — IPFS CID for behavior definition (informational or off-chain).
- `thotCID` — THOT artifact CID; can be synced with metadata via `linkTHOT`.
- `intelligenceLevel` — uint256, typically 0–100; application-defined.

---

## 4. Authorization Matrix

| Function | Caller | Other conditions |
|----------|--------|-------------------|
| `mint`, `mintIntelligent`, `mintWithAgent` | owner | — |
| `updateMetadata`, `freezeMetadata`, `setTokenURI` | token owner or owner | not frozen (for updates) |
| `agentInteract`, `triggerIntelligence` | config.agentAddress, or owner, or token owner | token exists |
| `updateIntelligence`, `updateAgent`, `linkTHOT` | token owner or owner | token exists |
| `setAgenticPlace` | owner | — |
| `offerSkillOnMarketplace` | token owner | AgenticPlace set, contract whitelisted |
| `metadata`, `frozen`, `intelligence`, `tokenURI` | any | token exists |

---

## 5. Events

- **AgentInteraction(tokenId, agent, interactionData)** — On `agentInteract`.
- **IntelligenceUpdated(tokenId, config)** — On `mintIntelligent`, `updateIntelligence`, `linkTHOT`, `updateAgent`.
- From DynamicNFT: **MetadataUpdated**, **MetadataFrozen**, **AgenticPlaceUpdated**.

---

## 6. Factory (IntelligentNFTFactory)

- **deployIntelligentNFT(name, symbol, agenticPlace):** Deploys `new IntelligentNFT(name, symbol, msg.sender, agenticPlace)`; records deployer and emits `INFTDeployed`; returns new contract address.
- **getDeployedContracts(deployer)**, **getTotalContracts()** — Same pattern as DynamicNFTFactory.

---

## 7. Security Considerations

- **Owner:** Single owner can mint and set AgenticPlace. Use multisig or DAO in production.
- **agentAddress:** Trusted for `agentInteract`; use a dedicated backend or agent wallet. Zero address disables agent interaction.
- **autonomous:** Currently a placeholder; future logic could perform state changes when `autonomous` and caller is `agentAddress`. Audit any such extensions.
- **Metadata and URIs:** Same as dNFT; no sensitive data on-chain; freezing is irreversible.
- **linkTHOT:** Updates both `_intelligence[tokenId].thotCID` and dNFT metadata; requires token owner or contract owner.

---

## 8. Relation to iNFT.sol

**IntelligentNFT.sol** (this spec) — Dynamic metadata + intelligence config + agent interaction.  
**iNFT.sol** — Separate contract: immutable THOT ERC721 with `ThotData`; no IntelligenceConfig, no AgenticPlace. See [iNFT.md](iNFT.md).

---

**Last updated:** 2026-02-05
