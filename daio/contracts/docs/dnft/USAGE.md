# Dynamic NFT (dNFT) — Usage Guide

Step-by-step usage for deploying, minting, updating, and integrating DAIO dNFTs.

**Source contracts:** [../../dnft/](../../dnft/)

---

## 1. Deployment

### Via factory

1. Deploy or use existing [DynamicNFTFactory.sol](../../dnft/DynamicNFTFactory.sol).
2. Call `deployDynamicNFT("Collection Name", "SYMBOL", agenticPlace)`.
   - Use `agenticPlace = address(0)` to skip marketplace; set later with `setAgenticPlace` on the new contract.
3. Use returned address as the dNFT collection.

### Direct deployment

```solidity
DynamicNFT nft = new DynamicNFT(
    "My Collection",
    "MC",
    msg.sender,
    address(0)
);
```

### Script

```bash
./scripts/deploy/deploy_dnft.sh polygon "My Collection" "MC"
```

---

## 2. Minting

```solidity
IDynamicNFT.NFTMetadata memory meta = IDynamicNFT.NFTMetadata({
    name: "Skill #1",
    description: "Trading strategy v1",
    imageURI: "Qm...",        // IPFS CID or full URI
    externalURI: "https://...",
    thotCID: "Qm...",         // optional
    isDynamic: true,
    lastUpdated: block.timestamp
});
uint256 tokenId = dNFTContract.mint(recipient, meta);
```

Only the contract owner can mint. After minting, `metadata(tokenId)` and `tokenURI(tokenId)` reflect the stored metadata and built URI.

---

## 3. Updating Metadata

Allowed only if the token is **not** frozen. Token owner or contract owner.

```solidity
IDynamicNFT.NFTMetadata memory newMeta = IDynamicNFT.NFTMetadata({
    name: "Skill #1 Updated",
    description: "Trading strategy v2",
    imageURI: "QmNew...",
    externalURI: "https://...",
    thotCID: "QmNew...",
    isDynamic: true,
    lastUpdated: block.timestamp
});
dNFTContract.updateMetadata(tokenId, newMeta);
```

To set only the URI (e.g. custom IPFS JSON), use `setTokenURI(tokenId, "ipfs://QmJson...")`. This does **not** update the internal `_metadata` mapping.

---

## 4. Freezing

When the token should be immutable:

```solidity
dNFTContract.freezeMetadata(tokenId);
```

After this, `updateMetadata`, `setTokenURI`, and `updateTokenMetadata` revert for that token. Irreversible.

---

## 5. Reading State

```solidity
IDynamicNFT.NFTMetadata memory meta = dNFTContract.metadata(tokenId);
bool isFrozen = dNFTContract.frozen(tokenId);
string memory uri = dNFTContract.tokenURI(tokenId);
address tokenOwner = dNFTContract.ownerOf(tokenId);
```

---

## 6. AgenticPlace Marketplace

1. Deploy AgenticPlace and whitelist this dNFT contract.
2. Owner: `dNFTContract.setAgenticPlace(agenticPlaceAddress)`.
3. Token owner: `dNFTContract.offerSkillOnMarketplace(tokenId, price, isETH, paymentToken, expiresAt)`.

---

## 7. Integration

- **iNFT:** [IntelligentNFT](../../inft/IntelligentNFT.sol) extends DynamicNFT; use iNFT when you need per-token agent interaction. See [../inft/USAGE.md](../inft/USAGE.md).
- **Keyminter:** [VaultKeyDynamic](../../keyminter/VaultKeyDynamic.sol) extends DynamicNFT for vault access keys. See [../keyminter/README.md](../keyminter/README.md).
- **THOT:** Use `thotCID` in metadata to reference THOT artifacts.
- **mindX:** Update metadata from backend/agent as token owner or contract owner.

---

**See also:** [README.md](README.md), [TECHNICAL.md](TECHNICAL.md), [../../dnft/README.md](../../dnft/README.md)
