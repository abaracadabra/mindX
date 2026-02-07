# Intelligent NFT (iNFT) — Technical Summary and Usage

Complete technical reference and usage guide for the DAIO iNFT contracts in `daio/contracts/inft/`.

---

## 1. Technical Summary

### 1.1 What Is an iNFT?

An **Intelligent NFT (iNFT)** is an ERC721 token that extends **DynamicNFT (dNFT)** with per-token **intelligence configuration**. Each token carries:

- **Dynamic metadata** (name, description, image, URIs, THOT CID) — updatable until frozen, as in dNFT.
- **Intelligence configuration** — an authorized agent address, autonomous flag, optional behavior/THOT CIDs, and an intelligence level. The configured agent (or owner, or contract owner) can call `agentInteract(tokenId, data)` to log or drive on-chain behavior tied to that token.

iNFTs are used for: skill/assets that can be traded on AgenticPlace, agent-bound intelligence (e.g. mindX agents interacting with tokens), THOT-linked intelligence, and vault key minting (see keyminter).

### 1.2 Contract Layout in This Folder

| File | Purpose |
|------|--------|
| **IntelligentNFT.sol** | Main iNFT implementation. Extends DynamicNFT; adds `IntelligenceConfig` per token and iNFT-specific functions. |
| **IIntelligentNFT.sol** | Interface (extends IDynamicNFT) defining iNFT API and `IntelligenceConfig`. |
| **IntelligentNFTFactory.sol** | Factory that deploys new IntelligentNFT collections; tracks deployer and all deployments. |
| **iNFT.sol** | Separate contract: immutable THOT-style ERC721 with `ThotData` (dataCID, dimensions, etc.). Not the same as IntelligentNFT; use for THOT-only minting when you do not need dNFT metadata or agent interaction. |

This document focuses on **IntelligentNFT** and the **factory**. Use **iNFT.sol** when you need a minimal THOT NFT without dynamic metadata or agent semantics.

### 1.3 Inheritance and Dependencies

```
IntelligentNFT
  → DynamicNFT (ERC721, ERC721URIStorage, Ownable, IDynamicNFT)
       → ERC721, ERC721URIStorage, Ownable
       → IAgenticPlace (optional: skill marketplace)
  → IIntelligentNFT (IDynamicNFT + IntelligenceConfig + agent APIs)
```

- **DynamicNFT** provides: `mint(to, NFTMetadata)`, `updateMetadata`, `freezeMetadata`, `metadata(tokenId)`, `frozen(tokenId)`, `setTokenURI`, `offerSkillOnMarketplace`.
- **IntelligentNFT** adds: per-token `IntelligenceConfig`, `mintIntelligent`, `agentInteract`, `updateIntelligence`, `intelligence(tokenId)`, `mintWithAgent`, `linkTHOT`, `triggerIntelligence`, `updateAgent`, and overrides for `setAgenticPlace` and `offerSkillOnMarketplace`.

### 1.4 Data Structures

**NFTMetadata** (from IDynamicNFT, used in mint/update):

- `name` — Token name.
- `description` — Token description.
- `imageURI` — IPFS CID or image URL.
- `externalURI` — Optional external link.
- `thotCID` — Optional THOT artifact CID.
- `isDynamic` — Whether metadata can be updated (typically `true` until frozen).
- `lastUpdated` — Timestamp of last metadata update.

**IntelligenceConfig** (per-token, from IIntelligentNFT):

- `agentAddress` — Address allowed to call `agentInteract` for this token (e.g. backend, mindX agent). Use `address(0)` to disable agent interaction.
- `autonomous` — If true, the contract allows future autonomous behavior when `agentAddress` calls (on-chain logic can branch on this).
- `behaviorCID` — IPFS CID for behavior definition (informational or used by off-chain systems).
- `thotCID` — Optional THOT artifact CID (can be synced to metadata via `linkTHOT`).
- `intelligenceLevel` — Integer 0–100; semantic meaning is application-defined (e.g. capability tier).

### 1.5 Events

- **AgentInteraction(tokenId, agent, interactionData)** — Emitted when `agentInteract` is called.
- **IntelligenceUpdated(tokenId, config)** — Emitted when intelligence config is set or updated (mintIntelligent, updateIntelligence, linkTHOT, updateAgent).
- From dNFT: **MetadataUpdated**, **MetadataFrozen**; from DynamicNFT: **AgenticPlaceUpdated**.

### 1.6 Authorization Summary

| Action | Who can call |
|--------|----------------------|
| `mint`, `mintIntelligent`, `mintWithAgent` | Contract `owner` only |
| `updateMetadata`, `freezeMetadata`, `setTokenURI` | Token owner or contract owner (dNFT rules) |
| `agentInteract`, `triggerIntelligence` | `config.agentAddress`, or contract owner, or token owner |
| `updateIntelligence`, `updateAgent`, `linkTHOT` | Token owner or contract owner |
| `setAgenticPlace` | Contract owner only |
| `offerSkillOnMarketplace` | Token owner only (and AgenticPlace must be set and contract whitelisted) |

---

## 2. Contract API (IntelligentNFT)

### 2.1 Minting

**mintIntelligent(to, nftMetadata, intelConfig)**  
- **Visibility:** external, onlyOwner  
- **Returns:** tokenId (uint256)  
- Mints a new ERC721 token to `to` with the given dNFT metadata and intelligence config. Stores `intelConfig` in `_intelligence[tokenId]` and emits `IntelligenceUpdated`.

**mintWithAgent(to, agentAddress, initialURI)**  
- **Visibility:** external, onlyOwner  
- **Returns:** tokenId  
- Convenience: mints with minimal metadata (imageURI = initialURI, empty name/description) and `IntelligenceConfig(agentAddress, autonomous=false, empty CIDs, intelligenceLevel=0)`. Calls `mintIntelligent` internally.

### 2.2 Agent Interaction

**agentInteract(tokenId, interactionData)**  
- **Visibility:** external  
- **Auth:** `msg.sender` must be `config.agentAddress`, or contract owner, or token owner.  
- **Effect:** Emits `AgentInteraction(tokenId, msg.sender, interactionData)`. If `config.autonomous` and `msg.sender == config.agentAddress`, the contract can extend this with further on-chain logic (currently a placeholder).  
- **Use:** Logging, access events, or triggering downstream logic; off-chain systems can index the event and `interactionData`.

**triggerIntelligence(tokenId, input)**  
- **Visibility:** external  
- **Auth:** Same as `agentInteract`.  
- **Effect:** Calls `agentInteract(tokenId, input)` and returns empty bytes (return value can be extended later for on-chain “intelligence” output).

### 2.3 Intelligence Configuration

**updateIntelligence(tokenId, newConfig)**  
- **Visibility:** external  
- **Auth:** Token owner or contract owner.  
- **Effect:** Replaces `_intelligence[tokenId]` with `newConfig`; emits `IntelligenceUpdated`.

**updateAgent(tokenId, newAgent)**  
- **Visibility:** external  
- **Auth:** Token owner or contract owner.  
- **Effect:** Sets `config.agentAddress = newAgent` for that token; emits `IntelligenceUpdated`.

**linkTHOT(tokenId, thotCID)**  
- **Visibility:** external  
- **Auth:** Token owner or contract owner.  
- **Effect:** Updates the token’s intelligence config `thotCID` and the dNFT metadata `thotCID` so metadata and intelligence stay in sync; emits `IntelligenceUpdated`.

**intelligence(tokenId)**  
- **Visibility:** external view  
- **Returns:** IntelligenceConfig for the token.  
- **Reverts:** If token does not exist.

### 2.4 Inherited (DynamicNFT) Functions Used With iNFT

- **mint(to, nftMetadata)** — onlyOwner; use via `mintIntelligent` for iNFTs so config is set.
- **updateMetadata(tokenId, newMetadata)** — token owner or contract owner; not frozen.
- **freezeMetadata(tokenId)** — token owner or contract owner; prevents further metadata updates.
- **metadata(tokenId)** — view; returns NFTMetadata.
- **frozen(tokenId)** — view; returns whether metadata is frozen.
- **setTokenURI(tokenId, newURI)** — token owner or contract owner; not frozen.
- **setAgenticPlace(_agenticPlace)** — onlyOwner.
- **offerSkillOnMarketplace(tokenId, price, isETH, paymentToken, expiresAt)** — token owner; requires AgenticPlace set and contract whitelisted.

---

## 3. Factory API (IntelligentNFTFactory)

**deployIntelligentNFT(name, symbol, agenticPlace)**  
- **Visibility:** external  
- **Effect:** Deploys a new `IntelligentNFT(name, symbol, msg.sender, agenticPlace)`. Caller is the initial owner. Pushes the new contract to `deployedContracts[msg.sender]` and `allContracts`; emits `INFTDeployed(deployer, contractAddress, name, symbol, timestamp)`.  
- **Returns:** address of the new iNFT contract.

**getDeployedContracts(deployer)**  
- **Visibility:** external view  
- **Returns:** array of contract addresses deployed by `deployer`.

**getTotalContracts()**  
- **Visibility:** external view  
- **Returns:** total number of contracts deployed through this factory.

---

## 4. Usage (Complete)

### 4.1 Deployment

**Option A: Via factory (recommended for multiple collections)**

1. Deploy or obtain `IntelligentNFTFactory`.
2. Call `deployIntelligentNFT("My iNFT Collection", "MINFT", agenticPlace)`.
   - Use `agenticPlace = address(0)` if you do not need the marketplace yet; set later with `setAgenticPlace` on the new contract.
3. Use the returned address as the iNFT collection contract.

**Option B: Direct deployment**

Deploy `IntelligentNFT` with constructor:

- `name` — Collection name.
- `symbol` — Symbol (e.g. `"MINFT"`).
- `initialOwner` — Owner address (can mint and set AgenticPlace).
- `_agenticPlace` — AgenticPlace contract or `address(0)`.

Example (Foundry-style script):

```solidity
IntelligentNFT nft = new IntelligentNFT(
    "My iNFT Collection",
    "MINFT",
    msg.sender,
    address(0)  // set AgenticPlace later
);
```

**Option C: Deploy script**

From DAIO repo:

```bash
./scripts/deploy/deploy_inft.sh polygon "My iNFT Collection" "MINFT"
```

(Adjust network and parameters to your scripts.)

### 4.2 Minting an Intelligent NFT

**Full mint with metadata and intelligence:**

```solidity
IDynamicNFT.NFTMetadata memory meta = IDynamicNFT.NFTMetadata({
    name: "Agent Skill #1",
    description: "Trading strategy v1",
    imageURI: "Qm...",      // IPFS CID or URL
    externalURI: "https://...",
    thotCID: "",            // optional, can set later with linkTHOT
    isDynamic: true,
    lastUpdated: block.timestamp
});

IIntelligentNFT.IntelligenceConfig memory config = IIntelligentNFT.IntelligenceConfig({
    agentAddress: backendAgent,   // address allowed to agentInteract
    autonomous: false,
    behaviorCID: "Qm...",         // optional IPFS behavior spec
    thotCID: "",
    intelligenceLevel: 50
});

uint256 tokenId = iNFTContract.mintIntelligent(recipient, meta, config);
```

**Short mint (agent only, minimal metadata):**

```solidity
uint256 tokenId = iNFTContract.mintWithAgent(
    recipient,
    agentAddress,
    "ipfs://Qm..."   // initial URI
);
```

### 4.3 Agent Interaction (Backend / mindX / Keyminter)

The address in `IntelligenceConfig.agentAddress` (or owner) can log or trigger behavior:

```solidity
bytes memory data = abi.encode(block.timestamp, "vault_access", scope);
iNFTContract.agentInteract(tokenId, data);
```

Off-chain: index `AgentInteraction` and decode `interactionData` for logging or analytics. On-chain: extend `agentInteract` (or `triggerIntelligence`) to perform state changes when `config.autonomous && msg.sender == config.agentAddress`.

### 4.4 Updating Intelligence and THOT

**Change the authorized agent:**

```solidity
iNFTContract.updateAgent(tokenId, newAgentAddress);
```

**Update full config (owner or token owner):**

```solidity
IIntelligentNFT.IntelligenceConfig memory newConfig = IIntelligentNFT.IntelligenceConfig({
    agentAddress: newAgent,
    autonomous: true,
    behaviorCID: "QmNewBehavior",
    thotCID: "QmNewTHOT",
    intelligenceLevel: 75
});
iNFTContract.updateIntelligence(tokenId, newConfig);
```

**Link a THOT CID (updates both intelligence config and dNFT metadata):**

```solidity
iNFTContract.linkTHOT(tokenId, "QmTHOT...");
```

### 4.5 Marketplace (AgenticPlace)

1. Set the marketplace: `iNFTContract.setAgenticPlace(agenticPlaceAddress)` (owner only).
2. Ensure the iNFT contract is whitelisted in AgenticPlace.
3. As token owner: `iNFTContract.offerSkillOnMarketplace(tokenId, price, isETH, paymentToken, expiresAt)`.

### 4.6 Reading State

```solidity
// Metadata (dNFT)
IDynamicNFT.NFTMetadata memory meta = iNFTContract.metadata(tokenId);
bool isFrozen = iNFTContract.frozen(tokenId);

// Intelligence
IIntelligentNFT.IntelligenceConfig memory config = iNFTContract.intelligence(tokenId);
// config.agentAddress, config.autonomous, config.behaviorCID, config.thotCID, config.intelligenceLevel
```

---

## 5. Integration Context

- **mindX:** Use iNFTs for agent-bound skills or assets; set `agentAddress` to a mindX backend or agent wallet so it can `agentInteract` for logging or access control.
- **Keyminter:** `VaultKeyIntelligent` (in `daio/contracts/keyminter/`) extends the iNFT pattern for vault access keys: mint keys with `mintKeyIntelligent(to, scope, expiryHint, agentAddress)`; backend can `agentInteract` to log vault access.
- **THOT:** Use `thotCID` in metadata and/or `IntelligenceConfig` and `linkTHOT` to attach THOT artifacts to iNFTs; THOTiNFTBridge and other THOT contracts can reference these.
- **AgenticPlace:** List iNFT skills for hire by calling `offerSkillOnMarketplace`; buyers receive the skill token or rental according to marketplace logic.

---

## 6. iNFT.sol vs IntelligentNFT.sol

- **IntelligentNFT.sol** — Full iNFT: dynamic metadata + intelligence config + agent interaction + optional AgenticPlace. Use for skills, agent-bound assets, vault keys, and any case where you need updatable metadata and/or authorized agent calls.
- **iNFT.sol** — Simpler ERC721: immutable THOT-style tokens with `ThotData` (dataCID, dimensions, parallelUnits, timestamp, verified). No dynamic metadata, no IntelligenceConfig, no AgenticPlace. Use when you only need THOT-by-CID minting and no agent interaction.

---

## 7. Security and Conventions

- **Owner:** Only the contract owner can mint and set AgenticPlace. Transfer ownership only to a secure multisig or DAO.
- **Agent address:** `agentAddress` is trusted for `agentInteract`; use a dedicated backend or agent wallet, not an EOA used for other purposes.
- **Metadata:** Sensitive data should not be stored on-chain; use IPFS CIDs or external URIs and ensure access control off-chain if needed.
- **Freezing:** Once `freezeMetadata(tokenId)` is called, metadata cannot be changed; use for permanent or compliance-bound tokens.

---

**Last updated:** 2026-02-05  
**Contracts:** `IntelligentNFT.sol`, `IIntelligentNFT.sol`, `IntelligentNFTFactory.sol`, `iNFT.sol`  
**See also:** [README.md](README.md), [../dnft/README.md](../dnft/README.md), [../keyminter/README.md](../keyminter/README.md), [../docs/inft/iNFT.md](../docs/inft/iNFT.md)
