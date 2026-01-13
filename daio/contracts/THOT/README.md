# THOT (Transferable Hyper-Optimized Tensor) Contracts

**Version:** 1.0.0  
**Status:** Production Ready  
**Network:** Multi-chain (ARC, Polygon, Testnet)

---

## Overview

The THOT contracts provide a complete system for creating, managing, and trading Transferable Hyper-Optimized Tensors - standardized 512-dimension f32 vectors with metadata for distributed knowledge in the intelligence economy.

### Key Principles

- **Standardized Format**: 64, 512, or 768 dimension THOTs
- **IPFS Integration**: All THOT data stored on IPFS with CID tracking
- **Verification System**: On-chain verification for trusted THOTs
- **Agentic Intelligence**: Support for agentic THOT emergence and orchestration
- **Marketplace Ready**: Full NFT support with royalties and trading

---

## Contract Structure

```
contracts/THOT/
├── core/
│   ├── THOT.sol          # Core THOT creation and management (ERC721)
│   ├── THINK.sol         # Batch THOT creation (ERC1155)
│   └── tNFT.sol          # THINK NFT with decision-making
├── nft/
│   ├── gNFT.sol          # Graphics NFT for visualization
│   ├── NFPrompT.sol      # Agent Prompt NFT
│   └── NFRLT.sol         # NFT Royalty Token with soulbound support
├── agents/
│   └── TransmuteAgent.sol # Automated THOT creation from raw data
├── marketplace/
│   └── AgenticPlace.sol   # Decentralized marketplace for THOT skills
└── interfaces/
```

---

## Core Contracts

### 1. THOT.sol
**Purpose:** Core contract for THOT creation and management

**Key Features:**
- Mint THOTs with IPFS CID references
- Support for 64, 512, and 768 dimensions
- Verification system
- CID tracking to prevent duplicates
- Metadata URI support

**Documentation:** `docs/solidity/thot.md`

### 2. THINK.sol
**Purpose:** Batch THOT creation using ERC1155

**Key Features:**
- Batch minting of THOTs
- Prompt and agent prompt storage
- Updateable THINK data
- URI generation

### 3. tNFT.sol
**Purpose:** THINK NFT with decision-making capabilities

**Key Features:**
- Decision state management (IDLE, PROCESSING, COMPLETED, FAILED)
- External data processing
- Decision execution triggers
- Dynamic metadata based on state

---

## NFT Contracts

### 4. gNFT.sol
**Purpose:** Graphics NFT for THOT visualization

**Key Features:**
- Base image and animation URL support
- Dynamic visual updates
- Custom attributes
- Base64 encoded metadata

### 5. NFPrompT.sol
**Purpose:** Agent Prompt NFT for agentic marketplace

**Key Features:**
- Agent identity management
- Prompt templates and modifiers
- Capability system
- Action registration
- Builder NFT minting

### 6. NFRLT.sol
**Purpose:** NFT Royalty Token with comprehensive royalty system

**Key Features:**
- Multiple royalty recipients (up to 5)
- ETH and ERC20 payment support
- Soulbound token support
- User identity attributes
- Broker transfer with automatic royalty distribution

**Documentation:** `docs/solidity/nfrlt.md`

---

## Agent Contracts

### 7. TransmuteAgent.sol
**Purpose:** Automated THOT creation from raw data

**Key Features:**
- Data transmutation to THOT format
- Batch processing
- Full parameter control
- IPFS integration

**Documentation:** `docs/solidity/transmute-agent.md`

---

## Marketplace Contracts

### 8. AgenticPlace.sol
**Purpose:** Decentralized marketplace for THOT skills

**Key Features:**
- Skill offering system
- ETH and ERC20 payment support
- Automatic royalty distribution
- Skill hiring mechanism

**Documentation:** `docs/solidity/agentic-place.md`

---

## Integration with DAIO

THOT contracts integrate seamlessly with the DAIO system:

- **IDNFT**: THOTs can be attached to agent identities
- **iNFT**: THOTs enable intelligent NFT behavior
- **DAIO Governance**: Verified THOTs contribute to knowledge-weighted voting
- **Treasury**: THOT royalties can flow to DAIO treasury

---

## Deployment Order

1. **THOT.sol** - Core THOT contract
2. **THINK.sol** - Batch creation (optional)
3. **tNFT.sol** - Decision-making NFTs (optional)
4. **TransmuteAgent.sol** - Requires THOT.sol
5. **NFRLT.sol** - Marketplace NFT
6. **AgenticPlace.sol** - Requires NFRLT.sol
7. **gNFT.sol** - Visualization (optional)
8. **NFPrompT.sol** - Agent prompts (optional)

---

## Usage Examples

### Creating a THOT

```solidity
// Via THOT contract
thot.mintTHOT(
    recipient,
    dataCID,      // IPFS CID
    512,          // dimensions
    1,            // parallelUnits
    metadataURI   // Additional metadata
);

// Via TransmuteAgent
transmuteAgent.transmuteDataFull(
    recipient,
    inputData,
    512,
    1,
    metadataURI
);
```

### Creating a Soulbound NFT

```solidity
nfrlt.createSoulboundNFT(
    to,
    tokenURI,
    username,
    class,
    level,
    health,
    stamina,
    strength,
    intelligence,
    dexterity
);
```

### Offering a Skill

```solidity
agenticPlace.offerSkill(
    skillTokenId,
    price,
    true,  // isETH
    address(0)  // paymentToken (if ETH)
);
```

---

## Events

### THOT Events
- `THOTMinted(uint256 indexed tokenId, bytes32 indexed dataCID, uint8 dimensions, uint40 timestamp)`
- `THOTVerified(uint256 indexed tokenId, bool verified)`

### NFRLT Events
- `RoyaltyPaid(address indexed recipient, uint256 indexed tokenId, uint256 amount, address indexed currency)`
- `NFTTransferred(address indexed from, address indexed to, uint256 indexed tokenId, uint256 salePrice, address currency)`

### AgenticPlace Events
- `SkillOffered(uint256 indexed skillTokenId, uint256 price, bool isETH, address paymentToken, address indexed owner)`
- `SkillHired(uint256 indexed skillTokenId, address indexed hirer, uint256 price, bool isETH)`

---

## Security Considerations

- **Reentrancy Protection**: All marketplace contracts use `ReentrancyGuard`
- **Access Control**: Role-based permissions via OpenZeppelin `AccessControl`
- **Soulbound Protection**: Transfer prevention enforced in `_update` hook
- **Royalty Caps**: Maximum 25% total royalty percentage
- **CID Validation**: Duplicate CID prevention

---

## Related Documentation

- [THOT Technical Spec](../docs/technical/THOT.md)
- [THOT Whitepaper](../docs/technical/THOTpaper.md)
- [THOT-DAIO Architecture](../docs/architecture/THOT-DAIO-ARCHITECTURE.md)
- [THOT Distributed Knowledge](../docs/architecture/THOT_DISTRIBUTED_KNOWLEDGE.md)

---

## Version History

- **v1.0.0** (2025-01-27): Initial production release
  - Core THOT contracts
  - NFT contracts (gNFT, NFPrompT, NFRLT)
  - TransmuteAgent
  - AgenticPlace marketplace
  - Full OpenZeppelin v5 compatibility
