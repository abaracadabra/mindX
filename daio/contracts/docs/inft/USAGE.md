# Intelligent NFT (iNFT) — Usage Guide

Step-by-step usage for deploying, minting, and integrating DAIO IntelligentNFTs (agent interaction, THOT linking, marketplace).

**Source contracts:** [../../inft/](../../inft/)

---

## 1. Deployment

### Via factory

1. Deploy or use existing [IntelligentNFTFactory.sol](../../inft/IntelligentNFTFactory.sol).
2. Call `deployIntelligentNFT("My iNFT Collection", "MINFT", agenticPlace)`.
   - Use `agenticPlace = address(0)` to set marketplace later via `setAgenticPlace`.
3. Use returned address as the iNFT collection.

### Direct deployment

```solidity
IntelligentNFT nft = new IntelligentNFT(
    "My iNFT Collection",
    "MINFT",
    msg.sender,
    address(0)
);
```

### Script

```bash
./scripts/deploy/deploy_inft.sh polygon "My iNFT Collection" "MINFT"
```

---

## 2. Minting

**Full mint (metadata + intelligence config):**

```solidity
IDynamicNFT.NFTMetadata memory meta = IDynamicNFT.NFTMetadata({
    name: "Agent Skill #1",
    description: "Trading strategy v1",
    imageURI: "Qm...",
    externalURI: "https://...",
    thotCID: "",
    isDynamic: true,
    lastUpdated: block.timestamp
});

IIntelligentNFT.IntelligenceConfig memory config = IIntelligentNFT.IntelligenceConfig({
    agentAddress: backendAgent,
    autonomous: false,
    behaviorCID: "Qm...",
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
    "ipfs://Qm..."
);
```

Only the contract owner can mint.

---

## 3. Agent Interaction

The address in `IntelligenceConfig.agentAddress` (or contract owner or token owner) can call:

```solidity
bytes memory data = abi.encode(block.timestamp, "vault_access", scope);
iNFTContract.agentInteract(tokenId, data);
```

Emits `AgentInteraction(tokenId, msg.sender, data)`. Index off-chain for logging or analytics. Optionally extend the contract to perform state changes when `config.autonomous && msg.sender == config.agentAddress`.

---

## 4. Updating Intelligence

**Change authorized agent:**

```solidity
iNFTContract.updateAgent(tokenId, newAgentAddress);
```

**Update full config (token owner or contract owner):**

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

**Link THOT CID (updates both intelligence config and dNFT metadata):**

```solidity
iNFTContract.linkTHOT(tokenId, "QmTHOT...");
```

---

## 5. Reading State

```solidity
IDynamicNFT.NFTMetadata memory meta = iNFTContract.metadata(tokenId);
bool isFrozen = iNFTContract.frozen(tokenId);
IIntelligentNFT.IntelligenceConfig memory config = iNFTContract.intelligence(tokenId);
```

---

## 6. Marketplace (AgenticPlace)

1. Owner: `iNFTContract.setAgenticPlace(agenticPlaceAddress)`.
2. Whitelist this iNFT contract in AgenticPlace.
3. Token owner: `iNFTContract.offerSkillOnMarketplace(tokenId, price, isETH, paymentToken, expiresAt)`.

---

## 7. Integration

- **mindX:** Set `agentAddress` to backend or agent wallet; call `agentInteract` for logging or access events.
- **Keyminter:** [VaultKeyIntelligent](../../keyminter/VaultKeyIntelligent.sol) extends iNFT for vault keys; see [../keyminter/README.md](../keyminter/README.md).
- **THOT:** Use `thotCID` and `linkTHOT`; THOTiNFTBridge can reference these.
- **AgenticPlace:** List iNFT skills for hire via `offerSkillOnMarketplace`.

---

## 8. IntelligentNFT vs iNFT.sol

- **IntelligentNFT** — Dynamic metadata + intelligence config + agent interaction. Use for skills, agent-bound assets, vault keys.
- **iNFT.sol** — Immutable THOT-only ERC721; see [iNFT.md](iNFT.md).

---

**See also:** [README.md](README.md), [TECHNICAL.md](TECHNICAL.md), [../../inft/README.md](../../inft/README.md), [iNFT.md](iNFT.md)
