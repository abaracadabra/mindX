# Keyminter for Vault Access – dNFT/iNFT Suitability and Design

## Assessment: DAIO dNFT and iNFT for Vault Key Issuance

### DynamicNFT (dNFT)

| Aspect | Suitability | Notes |
|--------|-------------|--------|
| **Purpose** | ✅ High | ERC721 with updatable metadata (ERC4906-style). Generic; we specialize for "vault access key" semantics. |
| **Minting** | ✅ | `mint(to, NFTMetadata)` onlyOwner. Ideal for issuer (mindX/DAIO) to mint keys to wallets. |
| **Metadata** | ✅ | `NFTMetadata`: name, description, imageURI, externalURI, thotCID, isDynamic, lastUpdated. We use name/description for scope (e.g. "vault_folder") and can store expiry hint in metadata or externalURI. |
| **Updates** | ✅ | `updateMetadata(tokenId, newMetadata)` by owner or token owner. Keys can have scope/expiry updated without burning. |
| **Freeze** | ✅ | `freezeMetadata(tokenId)` locks key metadata (e.g. permanent key). |
| **Marketplace** | Optional | AgenticPlace integration for skill trading; not required for keyminter. |

**Verdict**: dNFT is well-suited as a **dynamic** vault key: mint keys to users, update scope/expiry in metadata, optional freeze. Backend access_gate checks `balanceOf(wallet) >= 1` or `ownerOf(tokenId) == wallet` for the keyminter contract.

### IntelligentNFT (iNFT)

| Aspect | Suitability | Notes |
|--------|-------------|--------|
| **Purpose** | ✅ High | Extends dNFT with per-token `IntelligenceConfig`: agentAddress, autonomous, behaviorCID, thotCID, intelligenceLevel. |
| **Key semantics** | ✅ | Mint key with `mintIntelligent(to, nftMetadata, intelConfig)`. Set `agentAddress` to vault backend or mindX service so it can `agentInteract(tokenId, data)` to log access or signal revoke. |
| **Agent interaction** | ✅ | `agentInteract(tokenId, interactionData)` restricted to config.agentAddress, owner(), or token owner. Backend can call to log vault access or update state. |
| **Updates** | ✅ | `updateIntelligence(tokenId, newConfig)` and `updateAgent(tokenId, newAgent)`. Enables key reassignment or revoke (e.g. set agent to zero or to a revoker contract). |

**Verdict**: iNFT is well-suited as an **intelligent** vault key: same as dNFT plus authorized-agent semantics for logging, revoke, or future on-chain rules (behaviorCID).

---

## Design: Keyminter Contracts

We **modify** dNFT and iNFT into purpose-built keyminters for **issuance of access to the vault** (one key per mint; holding a key grants access as enforced by the backend access_gate).

### 1. VaultKeyDynamic (dynamic key)

- **Base**: Inherits from `DynamicNFT`.
- **Role**: Single collection "MindX Vault Key" (or configurable name/symbol). Only owner mints keys.
- **Metadata**: Keys carry `name` (e.g. "Vault Folder Access"), `description` (scope/expiry hint), optional `externalURI` (e.g. policy URL). `imageURI` can be a key icon CID.
- **Optional**: AgenticPlace can be set to zero (no marketplace) or to a marketplace if keys are tradeable.
- **Backend**: `access_gate` checks `balanceOf(wallet) >= 1` for this contract (or specific `tokenId` if MINDX_ACCESS_GATE_TOKEN_ID set).

### 2. VaultKeyIntelligent (intelligent key)

- **Base**: Inherits from `IntelligentNFT`.
- **Role**: Same as above plus `IntelligenceConfig` per key: `agentAddress` = vault backend or mindX agent that can `agentInteract` to log/revoke; `autonomous` false for issuer-controlled only.
- **Backend**: Same balance/ownerOf check; optionally backend calls `agentInteract(tokenId, abi.encode(accessTime, scope))` to log vault access on-chain.

### 3. Deployment and access_gate

- Deploy **VaultKeyDynamic** and/or **VaultKeyIntelligent** (or use factories). Set `MINDX_ACCESS_GATE_CONTRACT` to the keyminter address and `MINDX_ACCESS_GATE_TYPE=erc721`. Backend already supports ERC721 balance or specific token id; no change required for keyminter beyond deploying the contracts and configuring env.

---

## File Layout

```
daio/contracts/keyminter/
├── VaultKeyDynamic.sol      # Dynamic key minter (extends DynamicNFT)
├── VaultKeyIntelligent.sol  # Intelligent key minter (extends IntelligentNFT)
└── README.md                # Usage and deployment
```

Both contracts are **keyminters**: their sole purpose is to mint and manage NFTs that represent **issuance of access to the vault**. Dynamic = updatable key metadata; intelligent = key + authorized agent for interaction/revoke.
