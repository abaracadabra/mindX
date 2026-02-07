# Dynamic NFT (dNFT) — Technical Summary and Usage

Complete technical reference and usage guide for the DAIO dNFT contracts in `daio/contracts/dnft/`.

---

## 1. Technical Summary

### 1.1 What Is a dNFT?

A **Dynamic NFT (dNFT)** is an ERC721 token whose **metadata can be updated after minting**, in line with the idea of mutable metadata (e.g. ERC4906). Each token has:

- **Stored metadata** — name, description, image URI (IPFS or URL), optional external URI, optional THOT CID, dynamic flag, and last-updated timestamp.
- **Token URI** — Derived from that metadata: either a direct `ipfs://` URI (when imageURI is IPFS) or a base64-encoded data URI containing JSON (name, description, image, external_url, thot_cid, attributes).
- **Freezable** — Once frozen, metadata and token URI can no longer be changed.

dNFTs are used for: skills or assets that evolve over time, THOT-linked artifacts, AgenticPlace skill listings, and as the base for Intelligent NFTs (iNFT) and vault key collections (e.g. VaultKeyDynamic).

### 1.2 Contract Layout

| File | Purpose |
|------|--------|
| **DynamicNFT.sol** | Main dNFT implementation: ERC721 + updatable metadata, optional AgenticPlace integration. |
| **IDynamicNFT.sol** | Interface defining NFTMetadata and the dNFT API (mint, updateMetadata, freezeMetadata, metadata, frozen). |
| **DynamicNFTFactory.sol** | Factory that deploys new DynamicNFT collections; tracks deployer and all deployments. |

### 1.3 Inheritance and Dependencies

```
DynamicNFT
  → ERC721, ERC721URIStorage (OpenZeppelin)
  → Ownable (OpenZeppelin)
  → IDynamicNFT
  → IAgenticPlace (optional: skill marketplace)
```

- **ERC721 / ERC721URIStorage** — Standard NFT and per-token URI.
- **Ownable** — Single owner for minting and `setAgenticPlace`.
- **IAgenticPlace** — Optional; when set and contract is whitelisted, token owners can list skills via `offerSkillOnMarketplace`.

### 1.4 Data Structure: NFTMetadata

- **name** — Token name (e.g. "Trading Strategy v1").
- **description** — Token description.
- **imageURI** — IPFS CID (e.g. "Qm...") or full URI. If it starts with "ipfs", the built token URI may be `ipfs://` directly; otherwise the contract builds JSON and encodes it as a data URI.
- **externalURI** — Optional external link (in JSON as `external_url`).
- **thotCID** — Optional THOT artifact CID (in JSON as `thot_cid`).
- **isDynamic** — Set to `true` on mint/update; indicates metadata is mutable until frozen.
- **lastUpdated** — Set to `block.timestamp` on mint and on each update.

### 1.5 Events

- **MetadataUpdated(tokenId, metadata)** — Emitted when `updateMetadata` is called.
- **MetadataFrozen(tokenId)** — Emitted when `freezeMetadata` is called.
- **AgenticPlaceUpdated(oldPlace, newPlace)** — Emitted when owner calls `setAgenticPlace`.

### 1.6 Authorization Summary

| Action | Who can call |
|--------|----------------------|
| `mint` | Contract owner only |
| `updateMetadata`, `setTokenURI`, `updateTokenMetadata` | Token owner or contract owner; token must not be frozen |
| `freezeMetadata` | Token owner or contract owner |
| `setAgenticPlace` | Contract owner only |
| `offerSkillOnMarketplace` | Token owner only (and AgenticPlace set and contract whitelisted) |
| `metadata`, `frozen`, `tokenURI` | Anyone (view) |

---

## 2. Contract API (DynamicNFT)

### 2.1 Constructor

**DynamicNFT(name, symbol, initialOwner, _agenticPlace)**

- **name** — ERC721 collection name.
- **symbol** — ERC721 symbol.
- **initialOwner** — Owner address (can mint and set AgenticPlace).
- **_agenticPlace** — AgenticPlace contract address, or `address(0)` to skip marketplace until set later.

### 2.2 Minting

**mint(to, nftMetadata)**

- **Visibility:** public, onlyOwner  
- **Returns:** tokenId (uint256)  
- **Effect:** Increments internal token id counter, `_safeMint(to, tokenId)`, stores metadata (with `isDynamic = true`, `lastUpdated = block.timestamp`), builds token URI via `_buildTokenURI` and sets it.  
- **Reverts:** Standard ERC721 `_safeMint` (e.g. if `to` is zero or rejects).

### 2.3 Metadata Updates (require not frozen)

**updateMetadata(tokenId, newMetadata)**

- **Visibility:** external  
- **Auth:** Token owner or contract owner; token must exist and not be frozen.  
- **Effect:** Overwrites `_metadata[tokenId]`, sets `lastUpdated = block.timestamp`, rebuilds URI with `_buildTokenURI`, sets new token URI, emits `MetadataUpdated`.

**setTokenURI(tokenId, newURI)**

- **Visibility:** external  
- **Auth:** Token owner or contract owner; token must exist and not be frozen.  
- **Effect:** Sets the token’s URI directly to `newURI` (does not change stored `_metadata`). Use when you want to point to an external or custom URI without going through the struct.

**updateTokenMetadata(tokenId, metadataBytes)**

- **Visibility:** external  
- **Auth:** Token owner or contract owner; token must not be frozen.  
- **Effect:** Treats `metadataBytes` as a string and sets that as the token URI. Documented as a placeholder for a fuller bytes→NFTMetadata decode; in current form it only updates the URI, not the internal `_metadata` struct.

### 2.4 Freezing

**freezeMetadata(tokenId)**

- **Visibility:** external  
- **Auth:** Token owner or contract owner; token must exist.  
- **Effect:** Sets `_frozen[tokenId] = true`; no further `updateMetadata`, `setTokenURI`, or `updateTokenMetadata` for that token. Emits `MetadataFrozen`.

### 2.5 Views

**metadata(tokenId)**  
- **Visibility:** external view  
- **Returns:** NFTMetadata for the token.  
- **Reverts:** If token does not exist.

**frozen(tokenId)**  
- **Visibility:** external view  
- **Returns:** Whether the token’s metadata is frozen.

**tokenURI(tokenId)**  
- **Visibility:** public view (ERC721)  
- **Returns:** The current token URI (from ERC721URIStorage).

### 2.6 Marketplace (AgenticPlace)

**setAgenticPlace(_agenticPlace)**  
- **Visibility:** external, onlyOwner  
- **Effect:** Sets the internal AgenticPlace reference; emits `AgenticPlaceUpdated`. Use `address(0)` to clear.

**offerSkillOnMarketplace(tokenId, price, isETH, paymentToken, expiresAt)**  
- **Visibility:** external (virtual; overridden in iNFT)  
- **Auth:** Caller must be token owner.  
- **Requirements:** `agenticPlace != address(0)` and this dNFT contract must be whitelisted in AgenticPlace.  
- **Effect:** Calls `agenticPlace.offerSkill(tokenId, address(this), price, isETH, paymentToken, expiresAt)` to list the skill.

### 2.7 Token URI Building (_buildTokenURI)

Internal logic (used on mint and updateMetadata):

- If **imageURI** is non-empty and starts with `"ipfs"`, the function returns that string as the token URI (assumed full `ipfs://...`).
- Else if **imageURI** is non-empty, the token URI is `ipfs://` + imageURI (treating imageURI as a CID).
- Otherwise, the contract builds a JSON object with: `name`, `description`, `image` (ipfs:// + imageURI if set), optional `external_url`, optional `thot_cid`, and `attributes` (Dynamic true/false, Last Updated timestamp). That JSON is base64-encoded and returned as `data:application/json;base64,<encoded>`.

So tokens can have either an IPFS URI or an on-chain data URI as their `tokenURI`.

---

## 3. Factory API (DynamicNFTFactory)

**deployDynamicNFT(name, symbol, agenticPlace)**

- **Visibility:** external  
- **Effect:** Deploys `new DynamicNFT(name, symbol, msg.sender, agenticPlace)`. Caller becomes the owner of the new contract. Pushes the address to `deployedContracts[msg.sender]` and `allContracts`; emits `DNFTDeployed(deployer, contractAddress, name, symbol, timestamp)`.  
- **Returns:** address of the new dNFT contract.

**getDeployedContracts(deployer)**  
- **Visibility:** external view  
- **Returns:** array of dNFT contract addresses deployed by `deployer`.

**getTotalContracts()**  
- **Visibility:** external view  
- **Returns:** total number of dNFT contracts deployed through this factory.

---

## 4. Usage (Complete)

### 4.1 Deployment

**Option A: Via factory**

1. Deploy or use an existing `DynamicNFTFactory`.
2. Call `deployDynamicNFT("My Collection", "MC", agenticPlace)`.
   - Use `agenticPlace = address(0)` to deploy without a marketplace; set later with `setAgenticPlace` on the new contract.
3. Use the returned address as the dNFT collection.

**Option B: Direct deployment**

```solidity
DynamicNFT nft = new DynamicNFT(
    "My Collection",
    "MC",
    msg.sender,
    address(0)
);
```

**Option C: Script**

```bash
./scripts/deploy/deploy_dnft.sh polygon "My Collection" "MC"
```

(Adjust network and parameters to your deploy scripts.)

### 4.2 Minting

```solidity
IDynamicNFT.NFTMetadata memory meta = IDynamicNFT.NFTMetadata({
    name: "Skill #1",
    description: "Trading strategy v1",
    imageURI: "Qm...",        // IPFS CID or full URI
    externalURI: "https://...",
    thotCID: "Qm...",         // optional
    isDynamic: true,          // set to true; contract overwrites on mint
    lastUpdated: block.timestamp
});
uint256 tokenId = dNFTContract.mint(recipient, meta);
```

After minting, `metadata(tokenId)` and `tokenURI(tokenId)` reflect the stored metadata and built URI.

### 4.3 Updating Metadata

Only if the token is **not** frozen:

```solidity
IDynamicNFT.NFTMetadata memory newMeta = IDynamicNFT.NFTMetadata({
    name: "Skill #1 Updated",
    description: "Trading strategy v2",
    imageURI: "QmNew...",
    externalURI: "https://...",
    thotCID: "QmNew...",
    isDynamic: true,
    lastUpdated: block.timestamp  // contract will set to block.timestamp
});
dNFTContract.updateMetadata(tokenId, newMeta);
```

To set only the URI (e.g. custom IPFS JSON):

```solidity
dNFTContract.setTokenURI(tokenId, "ipfs://QmJson...");
```

Note: `setTokenURI` does not update the internal `_metadata` mapping; `metadata(tokenId)` will still return the previous struct. Use when you care only about the URI.

### 4.4 Freezing

When the token should no longer change:

```solidity
dNFTContract.freezeMetadata(tokenId);
```

After this, `updateMetadata`, `setTokenURI`, and `updateTokenMetadata` will revert for that token.

### 4.5 Reading State

```solidity
IDynamicNFT.NFTMetadata memory meta = dNFTContract.metadata(tokenId);
bool isFrozen = dNFTContract.frozen(tokenId);
string memory uri = dNFTContract.tokenURI(tokenId);
address tokenOwner = dNFTContract.ownerOf(tokenId);
```

### 4.6 Using AgenticPlace

1. Deploy or obtain AgenticPlace and whitelist this dNFT contract.
2. As owner: `dNFTContract.setAgenticPlace(agenticPlaceAddress)`.
3. As token owner:  
   `dNFTContract.offerSkillOnMarketplace(tokenId, price, isETH, paymentToken, expiresAt)`.

---

## 5. Integration Context

- **Intelligent NFT (iNFT):** IntelligentNFT extends DynamicNFT and adds per-token IntelligenceConfig and `agentInteract`. Use dNFT when you do not need agent semantics; use iNFT when you do (see `../inft/USAGE.md`).
- **Keyminter:** VaultKeyDynamic (in `../keyminter/`) extends DynamicNFT for vault access keys: fixed name/symbol and `mintKey(to, scope, expiryHint)`. Backend access_gate can require holding a key from that contract.
- **THOT:** Use `thotCID` in metadata to reference THOT artifacts; explorers or off-chain systems can resolve and display the link.
- **AgenticPlace:** dNFTs can represent skills listable on the marketplace; token ownership and marketplace logic determine hiring/rental flows.
- **mindX:** dNFTs can represent orchestrated assets or skills whose metadata is updated by agents or backends (as token owner or contract owner).

---

## 6. Security and Conventions

- **Owner:** Only the owner can mint and set AgenticPlace. Use a multisig or DAO for production.
- **Freezing:** Irreversible; use for compliance or permanent representation.
- **Metadata:** Avoid storing highly sensitive data on-chain; use IPFS or external URIs and control access off-chain if needed.
- **updateTokenMetadata(bytes):** Current implementation treats bytes as a raw URI string; do not rely on it for structured decoding unless the contract is updated to decode NFTMetadata properly.

---

**Last updated:** 2026-02-05  
**Contracts:** DynamicNFT.sol, IDynamicNFT.sol, DynamicNFTFactory.sol  
**See also:** [README.md](README.md), [../inft/USAGE.md](../inft/USAGE.md), [../keyminter/README.md](../keyminter/README.md)
