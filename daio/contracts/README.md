# Smart Contracts for THOT-DAIO Architecture

This directory contains all Solidity smart contracts for the THOT-DAIO ecosystem.

## Directory Structure

```
contracts/
├── arc/                    # ARC Chain contracts
│   ├── DatasetRegistry.sol
│   ├── ProviderRegistry.sol
│   ├── PinDealEscrow.sol
│   ├── ChallengeManager.sol
│   └── RetrievalReceiptSettler.sol
├── daio/                   # DAIO Governance contracts
│   ├── DAIOGovernance.sol
│   ├── BoardroomExtension.sol
│   ├── constitution/
│   ├── treasury/
│   ├── governance/
│   ├── identity/
│   └── settings/
├── dnft/                   # Dynamic NFT contracts
│   ├── DynamicNFT.sol
│   ├── DynamicNFTFactory.sol
│   └── interfaces/
│       └── IDynamicNFT.sol
├── inft/                   # Intelligent NFT contracts
│   ├── IntelligentNFT.sol
│   ├── IntelligentNFTFactory.sol
│   └── interfaces/
│       └── IIntelligentNFT.sol
├── THOT/                   # THOT (Transferable Hyper-Optimized Tensor) contracts
│   ├── core/
│   │   ├── THOT.sol
│   │   ├── THINK.sol
│   │   └── tNFT.sol
│   ├── nft/
│   │   ├── gNFT.sol
│   │   ├── NFPrompT.sol
│   │   └── NFRLT.sol
│   ├── agents/
│   │   └── TransmuteAgent.sol
│   └── marketplace/
│       └── AgenticPlace.sol
└── README.md
```

## THOT Contracts (`contracts/THOT/`)

### Core THOT Contracts
- **THOT.sol** - Core THOT creation and management (ERC721)
  - [Documentation](../docs/solidity/thot.md) - Technical guide, usage, and UI creation
- **THINK.sol** - Batch THOT creation (ERC1155)
- **tNFT.sol** - THINK NFT with decision-making capabilities

### THOT NFT Contracts
- **gNFT.sol** - Graphics NFT for THOT visualization
- **NFPrompT.sol** - Agent Prompt NFT for agentic marketplace
- **NFRLT.sol** - NFT Royalty Token with comprehensive royalty system
  - [Documentation](../docs/solidity/nfrlt.md) - Technical guide, usage, and UI creation

### THOT Agent Contracts
- **TransmuteAgent.sol** - Automated THOT creation from raw data
  - [Documentation](../docs/solidity/transmute-agent.md) - Technical guide, usage, and UI creation

### THOT Marketplace Contracts
- **AgenticPlace.sol** - Decentralized marketplace for THOT skills
  - [Documentation](../docs/solidity/agentic-place.md) - Technical guide, usage, and UI creation

See `contracts/THOT/README.md` for complete THOT contract documentation.

---

## ARC Chain Contracts

### DatasetRegistry.sol
- **Purpose:** Register datasets and map to IPFS CIDs
- **Functions:**
  - `registerDataset()` - Register a new dataset
  - `versionDataset()` - Create new version of dataset
  - `getDataset()` - Get dataset information
  - `getLatestVersion()` - Get latest version CID

### ProviderRegistry.sol
- **Purpose:** Register dataset providers (alive agents)
- **Functions:**
  - `registerProvider()` - Register as provider
  - `addDataset()` - Add dataset to provider's list
  - `updateReputation()` - Update provider reputation
  - `getDatasetProviders()` - Get providers for a dataset

### PinDealEscrow.sol
- **Purpose:** Manage storage deals (Filecoin-style, ARC-native)
- **Functions:**
  - `createDeal()` - Create storage deal
  - `activateDeal()` - Activate deal
  - `releasePayment()` - Release payment to provider
  - `slashCollateral()` - Slash provider collateral

### ChallengeManager.sol
- **Purpose:** Proof-of-Availability challenges
- **Functions:**
  - `issueChallenge()` - Issue challenge for deal
  - `respondToChallenge()` - Provider responds to challenge
  - `verifyChallenge()` - Verify challenge response

### RetrievalReceiptSettler.sol
- **Purpose:** Batch settlement of retrieval payments
- **Functions:**
  - `createReceipt()` - Create retrieval receipt
  - `settleReceipt()` - Settle single receipt
  - `batchSettleReceipts()` - Batch settle multiple receipts

## DAIO Governance Contracts

### DAIOGovernance.sol
- **Purpose:** Core governance contract for DAIO
- **Features:**
  - Multi-project support (FinancialMind, mindX, cryptoAGI, etc.)
  - Proposal creation and voting
  - Project registration
  - Voting power management
- **Functions:**
  - `registerProject()` - Register a project with DAIO
  - `createProposal()` - Create governance proposal
  - `vote()` - Vote on proposal
  - `executeProposal()` - Execute successful proposal

### BoardroomExtension.sol
- **Purpose:** Treasury management and proposal execution
- **Features:**
  - Multi-project treasury management
  - Treasury allocation
  - Proposal execution
- **Functions:**
  - `allocateTreasury()` - Allocate treasury funds
  - `executeAllocation()` - Execute treasury allocation
  - `depositTreasury()` - Deposit funds to treasury

## Dynamic & Intelligent NFTs (dNFT/iNFT)

### DynamicNFT.sol
- **Purpose:** ERC721 NFT with dynamic metadata support (ERC4906 compatible)
- **Features:**
  - Metadata can be updated after minting
  - IPFS integration for images and metadata
  - Optional THOT artifact linking
  - Metadata freezing capability
- **Use Cases:** Trading strategies, datasets, models, any dynamic content

### IntelligentNFT.sol
- **Purpose:** Extends DynamicNFT with intelligence capabilities
- **Features:**
  - All dNFT features
  - Agent interaction hooks
  - Autonomous behavior support
  - Optional THOT integration for intelligence
- **Use Cases:** AI agents, autonomous systems, intelligent assets

### Factory Contracts
- **DynamicNFTFactory.sol** - Easy deployment of dNFT contracts
- **IntelligentNFTFactory.sol** - Easy deployment of iNFT contracts
- **Usage:** Participants and agents can deploy NFTs with minimal setup

### Key Principles
- **THOT-Optional:** dNFT/iNFT can be created with or without THOT artifacts
- **ERC Compliant:** Follows ERC721 and ERC4906 standards
- **Modular:** Works standalone or within mindX orchestration
- **Easy Deployment:** One-command deployment via Foundry scripts

## Deployment

### Prerequisites
- Solidity compiler ^0.8.20
- Foundry (forge, cast)
- ARC chain or Polygon network access
- Private key for deployment (set in environment variables)

### Foundry Setup
```bash
# Install Foundry (if not already installed)
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Install OpenZeppelin contracts
forge install OpenZeppelin/openzeppelin-contracts
```

### Environment Variables
Create `.env` file in project root:
```bash
# Network RPC URLs
ARC_RPC_URL=https://rpc.arc-chain.com
POLYGON_RPC_URL=https://polygon-rpc.com
POLYGON_TESTNET_RPC_URL=https://rpc-mumbai.maticvigil.com

# Private keys (NEVER commit these)
ARC_PRIVATE_KEY=your_arc_private_key
POLYGON_PRIVATE_KEY=your_polygon_private_key
TESTNET_PRIVATE_KEY=your_testnet_private_key
```

### Deployment Scripts

**Deploy dNFT Factory:**
```bash
./scripts/deploy/deploy_factory.sh polygon dnft
```

**Deploy iNFT Factory:**
```bash
./scripts/deploy/deploy_factory.sh polygon inft
```

**Deploy Direct dNFT:**
```bash
./scripts/deploy/deploy_dnft.sh polygon "My NFT Collection" "MNFT"
```

### Deployment Order (THOT-DAIO Contracts)
1. Deploy `DatasetRegistry.sol`
2. Deploy `ProviderRegistry.sol`
3. Deploy `PinDealEscrow.sol`
4. Deploy `ChallengeManager.sol` (requires PinDealEscrow and ProviderRegistry addresses)
5. Deploy `RetrievalReceiptSettler.sol`
6. Deploy `DAIOGovernance.sol`
7. Deploy `BoardroomExtension.sol` (requires DAIOGovernance address)
8. Deploy `DynamicNFTFactory.sol` (optional, for easy dNFT deployment)
9. Deploy `IntelligentNFTFactory.sol` (optional, for easy iNFT deployment)

## Integration

These contracts integrate with:
- **IPFS** - For dataset storage (CIDs)
- **ARC Chain** - For low-cost settlement
- **DAIO** - For governance and coordination
- **Multiple Projects** - FinancialMind, mindX, cryptoAGI, etc.

## Security Considerations

- All contracts use Solidity ^0.8.20 (safe math by default)
- Access control via `onlyOwner` and `onlyChallengeManager` modifiers
- Reentrancy protection should be added for production
- Input validation on all public functions
- Consider using OpenZeppelin contracts for additional security

## Testing

Contracts should be tested with:
- Unit tests for each function
- Integration tests for contract interactions
- Gas optimization tests
- Security audits before mainnet deployment

## License

MIT License - See individual contract headers for details.
