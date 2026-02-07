# Dynamic NFT (dNFT) — Technical Specification

Technical architecture, interfaces, state, and security for the DAIO dNFT contracts.

**Contracts:** [../../dnft/DynamicNFT.sol](../../dnft/DynamicNFT.sol), [../../dnft/interfaces/IDynamicNFT.sol](../../dnft/interfaces/IDynamicNFT.sol), [../../dnft/DynamicNFTFactory.sol](../../dnft/DynamicNFTFactory.sol)

---

## 1. Architecture

### 1.1 Inheritance

```
DynamicNFT
  ├── ERC721 (OpenZeppelin)
  ├── ERC721URIStorage (OpenZeppelin)  — per-token URI
  ├── Ownable (OpenZeppelin)           — owner for mint + setAgenticPlace
  ├── IDynamicNFT                      — NFTMetadata + mint/update/freeze/view
  └── IAgenticPlace (internal ref)     — optional marketplace
```

- No additional access control beyond Ownable; token owner and contract owner share update/freeze rights.
- `offerSkillOnMarketplace` delegates to AgenticPlace; this contract does not hold funds.

### 1.2 Interface IDynamicNFT

- **Struct:** `NFTMetadata(name, description, imageURI, externalURI, thotCID, isDynamic, lastUpdated)`
- **Events:** `MetadataUpdated(uint256 indexed tokenId, NFTMetadata metadata)`, `MetadataFrozen(uint256 indexed tokenId)`
- **Functions:** `mint(to, nftMetadata)`, `updateMetadata(tokenId, newMetadata)`, `freezeMetadata(tokenId)`, `metadata(tokenId)`, `frozen(tokenId)`

DynamicNFT adds: `setTokenURI`, `updateTokenMetadata(bytes)`, `setAgenticPlace`, `offerSkillOnMarketplace`, and internal `_buildTokenURI`.

### 1.3 Dependency: IAgenticPlace

Used only when marketplace is enabled. Required calls:

- `agenticPlace.isNFTContractWhitelisted(address(this))` — must be true to list.
- `agenticPlace.offerSkill(tokenId, address(this), price, isETH, paymentToken, expiresAt)` — called by token owner.

Constructor and `setAgenticPlace` accept `address(0)` to leave marketplace unset.

---

## 2. State Layout (DynamicNFT)

| Variable | Type | Description |
|----------|------|-------------|
| `_metadata` | `mapping(uint256 => NFTMetadata)` | Stored metadata per token (used for views and for rebuilding URI on update). |
| `_frozen` | `mapping(uint256 => bool)` | If true, no further metadata/URI updates. |
| `_tokenIdCounter` | `uint256` | Incremented on each mint; next token id. |
| `_baseTokenURI` | `string` | Declared but not used in current logic; token URI is per-token via ERC721URIStorage. |
| `agenticPlace` | `IAgenticPlace` (internal) | Marketplace contract; can be zero. |

Token URI is stored in ERC721URIStorage’s internal mapping (per OpenZeppelin).

---

## 3. Token URI Semantics (_buildTokenURI)

Internal, used on `mint` and `updateMetadata`:

1. **imageURI non-empty and starts with "ipfs"**  
   Return `meta.imageURI` as-is (assumed full `ipfs://...`).

2. **imageURI non-empty, does not start with "ipfs"**  
   Return `"ipfs://" + meta.imageURI` (treat imageURI as CID).

3. **Otherwise**  
   Build JSON with: `name`, `description`, `image` (ipfs:// + imageURI if any), optional `external_url`, optional `thot_cid`, and `attributes`: `Dynamic` (bool), `Last Updated` (timestamp). Encode as `data:application/json;base64,<base64(json)>`.

So `tokenURI(tokenId)` can be either an off-chain IPFS URI or an on-chain data URI. `setTokenURI` and `updateTokenMetadata` set the URI directly without changing `_metadata` or running `_buildTokenURI`.

---

## 4. Authorization Matrix

| Function | Caller | Other conditions |
|----------|--------|-------------------|
| `mint` | owner | — |
| `updateMetadata`, `setTokenURI`, `updateTokenMetadata` | token owner or owner | token exists, not frozen |
| `freezeMetadata` | token owner or owner | token exists |
| `setAgenticPlace` | owner | — |
| `offerSkillOnMarketplace` | token owner | agenticPlace set, contract whitelisted |
| `metadata`, `frozen`, `tokenURI` | any | token exists (metadata/tokenURI) |

---

## 5. Events

- **MetadataUpdated(tokenId, metadata)** — On successful `updateMetadata`.
- **MetadataFrozen(tokenId)** — On successful `freezeMetadata`.
- **AgenticPlaceUpdated(oldPlace, newPlace)** — On `setAgenticPlace`.

ERC721 transfer events (Transfer, Approval) are unchanged.

---

## 6. Factory (DynamicNFTFactory)

- **State:** `deployedContracts[deployer][]`, `allContracts[]`.
- **deployDynamicNFT(name, symbol, agenticPlace):** Deploys `new DynamicNFT(name, symbol, msg.sender, agenticPlace)`; appends to arrays; emits `DNFTDeployed`; returns new contract address. Caller is the new contract’s owner.
- **getDeployedContracts(deployer):** Returns all dNFT addresses deployed by `deployer`.
- **getTotalContracts():** Returns length of `allContracts`.

No reentrancy guard; deployment is a simple constructor call and storage update.

---

## 7. Security Considerations

- **Owner:** Single owner can mint and set AgenticPlace. Use multisig or DAO in production.
- **Freezing:** Irreversible. Ensures metadata and URI immutability after freeze.
- **Sensitive data:** Do not put secrets in metadata; use IPFS or external URIs and control access off-chain.
- **updateTokenMetadata(bytes):** Implemented as `uri = string(metadataBytes)`; does not decode to NFTMetadata. Use for raw URI only or extend with proper decoding.
- **AgenticPlace:** Trust and whitelist model; this contract does not hold funds. Audit AgenticPlace for marketplace security.

---

## 8. ERC4906 Compatibility

The pattern “metadata can change and is reflected in tokenURI” aligns with the idea of mutable metadata (e.g. ERC4906). This implementation does not necessarily emit a specific ERC4906 event; it uses `MetadataUpdated` and updates the stored URI. Consumers can treat `MetadataUpdated` as the signal that metadata/URI may have changed.

---

**Last updated:** 2026-02-05
