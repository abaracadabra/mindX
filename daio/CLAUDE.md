# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DAIO (Decentralized Autonomous Intelligence Organization) is a **standalone governance system** - a Solidity smart contract ecosystem for blockchain-native governance and economic operations in a distributed intelligence knowledge economy.

**Key Principle**: DAIO operates independently. External systems like mindX interact with DAIO through the `xmind/` subfolder, which serves as the execution/integration layer.

## Development Commands

### Setup
```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Install OpenZeppelin contracts
forge install OpenZeppelin/openzeppelin-contracts
```

### Build & Test
```bash
forge build                           # Compile all contracts
forge test                            # Run all tests
forge test --match-path test/daio/*   # Run DAIO-specific tests
forge test --gas-report               # With gas reporting
forge test -vvvv                      # Verbose output for debugging
```

### Deployment
```bash
# Deploy dNFT Factory
./scripts/deploy/deploy_factory.sh polygon dnft

# Deploy iNFT Factory
./scripts/deploy/deploy_factory.sh polygon inft

# Deploy direct dNFT
./scripts/deploy/deploy_dnft.sh polygon "Collection Name" "SYMBOL"
```

### ARC Testnet Deployment (contracts/arc/)

The ARC chain contracts handle dataset storage and retrieval. Deploy to ARC testnet first.

```bash
# ARC Testnet connection
ARC_TESTNET_RPC=https://testnet-rpc.arcchain.io
ARC_TESTNET_CHAIN_ID=1998
ARC_TESTNET_EXPLORER=https://testnet-explorer.arcchain.io

# Deploy ARC contracts in order
cd contracts/arc

# 1. DatasetRegistry - Dataset registration with IPFS CIDs
forge create --rpc-url $ARC_TESTNET_RPC \
  --private-key $TESTNET_PRIVATE_KEY \
  src/arc/DatasetRegistry.sol:DatasetRegistry

# 2. ProviderRegistry - Provider registration and reputation
forge create --rpc-url $ARC_TESTNET_RPC \
  --private-key $TESTNET_PRIVATE_KEY \
  src/arc/ProviderRegistry.sol:ProviderRegistry

# 3. PinDealEscrow - Storage deal management
forge create --rpc-url $ARC_TESTNET_RPC \
  --private-key $TESTNET_PRIVATE_KEY \
  src/arc/PinDealEscrow.sol:PinDealEscrow

# 4. ChallengeManager - Requires PinDealEscrow and ProviderRegistry addresses
forge create --rpc-url $ARC_TESTNET_RPC \
  --private-key $TESTNET_PRIVATE_KEY \
  --constructor-args <PIN_DEAL_ESCROW_ADDR> <PROVIDER_REGISTRY_ADDR> \
  src/arc/ChallengeManager.sol:ChallengeManager

# 5. RetrievalReceiptSettler - Batch settlement
forge create --rpc-url $ARC_TESTNET_RPC \
  --private-key $TESTNET_PRIVATE_KEY \
  src/arc/RetrievalReceiptSettler.sol:RetrievalReceiptSettler
```

**ARC Testnet Faucet**: Get testnet tokens at https://faucet.arcchain.io

**Verify contracts**:
```bash
forge verify-contract --chain-id 1998 \
  --etherscan-api-key $ARC_API_KEY \
  <CONTRACT_ADDRESS> src/arc/DatasetRegistry.sol:DatasetRegistry
```

## Architecture

### Contract Hierarchy

```
DAIO Governance Layer
├── DAIOGovernance.sol       # Core governance hub (proposals, voting, execution)
├── DAIO_Constitution.sol    # Immutable constitutional rules (15% tithe, diversification)
├── Treasury.sol             # Multi-project treasury with 15% tithe collection
├── GovernanceSettings.sol   # Configurable voting parameters
├── KnowledgeHierarchyDAIO.sol  # 2/3 consensus (Marketing, Community, Development)
├── BoardroomExtension.sol   # Flexible voting within groups, treasury allocation
└── DAIOTimelock.sol         # Time-delayed execution

xmind/ (mindX Execution Layer)
└── [Integration contracts for mindX ↔ DAIO interaction]

Identity Layer
├── IDNFT.sol               # Agent identity NFT (prompt, persona, credentials, THOT links)
└── SoulBadger.sol          # Soulbound non-transferable tokens

THOT (Transferable Hyper-Optimized Tensor) Layer
├── core/
│   ├── THOT.sol            # Core THOT creation (ERC721, 64/512/768 dimensions)
│   ├── THINK.sol           # Batch THOT creation (ERC1155)
│   └── tNFT.sol            # Decision-making THOT NFT
├── nft/
│   ├── NFRLT.sol           # NFT Royalty Token (soulbound support, multi-recipient)
│   ├── gNFT.sol            # Graphics NFT for visualization
│   └── NFPrompT.sol        # Agent Prompt NFT
├── agents/
│   └── TransmuteAgent.sol  # Automated THOT creation from raw data
└── marketplace/
    └── AgenticPlace.sol    # Decentralized skill marketplace

ARC Chain Layer (Data Storage)
├── DatasetRegistry.sol     # Dataset registration with IPFS CIDs
├── ProviderRegistry.sol    # Provider registration and reputation
├── PinDealEscrow.sol       # Storage deal management
├── ChallengeManager.sol    # Proof-of-Availability challenges
└── RetrievalReceiptSettler.sol  # Batch retrieval payment settlement

NFT Extensions
├── dnft/
│   ├── DynamicNFT.sol      # ERC721 with updateable metadata (ERC4906)
│   └── DynamicNFTFactory.sol
├── inft/
│   ├── IntelligentNFT.sol  # DynamicNFT + agent interaction hooks
│   └── IntelligentNFTFactory.sol
└── erc20/
    └── CustomToken.sol     # Standard ERC20 for agent tokens
```

### Key Design Patterns

**Constitutional Constraints**: All treasury allocations validated against `DAIO_Constitution.sol`:
- 15% treasury tithe on all deposits
- 15% diversification mandate (max single allocation)
- Chairman's veto power for emergencies

**2/3 Consensus Governance** in `KnowledgeHierarchyDAIO.sol`:

```
Decision Consensus (2/3 of group results required)
├── Marketing (3 votes: 2 human + 1 AI) → 2/3 majority
├── Community (3 votes: 2 human + 1 AI) → 2/3 majority
└── Development (3 votes: 2 human + 1 AI) → 2/3 majority
```

- Each group has 3 votes: 2 human members + 1 AI vote
- AI can make proposals to any group
- Within each group: 2/3 majority required (2 of 3 votes)
- Overall decision: 2/3 of group results required (2 of 3 groups)

**Boardroom Extension**: Within each group (Marketing, Community, Development), a Boardroom can be created via `BoardroomExtension.sol` to provide flexible voting parameters for achieving consensus on specific decisions

**THOT Standardization**:
- Fixed dimensions: 64, 512, or 768 f32 vectors
- IPFS CID tracking prevents duplicate THOTs
- Verification system for trusted THOTs

**Multi-Project Support**: Single DAIO instance governs multiple projects (mindX, FinancialMind, cryptoAGI) with project-specific settings.

### NFT Type Distinctions

| Type | Purpose | Transferability | Intelligence Features |
|------|---------|-----------------|----------------------|
| **IDNFT** | Agent identity & persona | Transferable or soulbound (via SoulBadger) | Prompt, persona metadata |
| **iNFT** | Full intelligent NFT | Transferable/dynamic | Prompt, persona, model dataset, THOT tensors |
| **dNFT** | Dynamic metadata NFT | Transferable with updates | No intelligence - just dynamic metadata |

### THOT Tensor Types

THOTs (Transferable Hyper-Optimized Tensors) come in three dimension variants stored on IPFS:
- **THOT64**: 64-dimension vectors (lightweight)
- **THOT512**: 512-dimension 8x8x8 3D knowledge clusters (standard)
- **THOT768**: 768-dimension optimized tensors (high-fidelity)

### Proposal Types

| Type | Description | Group Approval | Overall Consensus | Timelock |
|------|-------------|----------------|-------------------|----------|
| **Strategic Evolution** | Architecture changes, new agents | 2/3 within group | 2/3 of groups | 7 days |
| **Economic** | Treasury allocation, investments | 2/3 within group | 2/3 of groups | 3 days |
| **Constitutional** | Core principle changes | 3/3 within group | 3/3 of groups | 14 days |
| **Operational** | Routine operations, agent activation | 2/3 within group | 1/3 of groups | 1 day |

**Note**: AI can submit proposals to any group (Marketing, Community, Development). Each group votes independently, then overall consensus is calculated.

## Deployment Order

### Phase 1: ARC Testnet (contracts/arc/) - Data Layer
1. `DatasetRegistry` - Dataset registration with IPFS CIDs
2. `ProviderRegistry` - Provider registration and reputation
3. `PinDealEscrow` - Storage deal management
4. `ChallengeManager` - Proof-of-Availability (requires #3, #2)
5. `RetrievalReceiptSettler` - Batch retrieval payments

### Phase 2: Governance Layer (contracts/daio/)
6. `DAIOTimelock` - Timelock controller
7. `DAIO_Constitution` - Constitution with chairman address
8. `SoulBadger` - Soulbound token contract (optional)
9. `IDNFT` - Identity NFT with SoulBadger integration
10. `GovernanceSettings` - Governance parameters
11. `Treasury` - Treasury with constitution and multi-sig signers
12. `KnowledgeHierarchyDAIO` - 2/3 consensus governance (Marketing, Community, Development)
13. `AgentFactory` - Agent creation factory
14. `DAIOGovernance` - Main governance hub
15. `BoardroomExtension` - Flexible voting within groups, treasury allocation

### Phase 2b: xmind/ Execution Layer
16. `DAIOBridge` - Bridge for external system integration
17. `XMindAgentRegistry` - mindX agent registration
18. `XMindProposer` - AI proposal submission to groups
19. `XMindTreasuryReceiver` - Treasury allocation receiver

### Phase 3: THOT & Marketplace (contracts/THOT/)
15. `THOT` - Core THOT contract
16. `NFRLT` - Royalty NFT (requires THOT for AgenticPlace)
17. `AgenticPlace` - Marketplace (requires NFRLT, THOT, AgentFactory)
18. `DynamicNFTFactory` / `IntelligentNFTFactory` - As needed

## Environment Variables

Create `.env` in project root:
```bash
# ARC Chain
ARC_RPC_URL=https://rpc.arcchain.io
ARC_TESTNET_RPC=https://testnet-rpc.arcchain.io
ARC_TESTNET_CHAIN_ID=1998
ARC_API_KEY=your_arc_explorer_api_key

# Polygon
POLYGON_RPC_URL=https://polygon-rpc.com
POLYGON_TESTNET_RPC_URL=https://rpc-mumbai.maticvigil.com

# Private keys (NEVER commit)
ARC_PRIVATE_KEY=your_arc_private_key
POLYGON_PRIVATE_KEY=your_polygon_private_key
TESTNET_PRIVATE_KEY=your_testnet_private_key
```

## Contract Patterns

**OpenZeppelin v5 Compatibility**: All contracts use OpenZeppelin v5 patterns:
```solidity
// Constructor with Ownable
constructor() Ownable(msg.sender) { }

// ERC721 _update override instead of _beforeTokenTransfer
function _update(address to, uint256 tokenId, address auth)
    internal override returns (address) { }
```

**Access Control Roles** (used in IDNFT, AgentFactory):
```solidity
bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
bytes32 public constant CREDENTIAL_ISSUER_ROLE = keccak256("CREDENTIAL_ISSUER_ROLE");
```

**Reentrancy Protection**: All marketplace and treasury functions use `ReentrancyGuard`.

## Integration Points

- **IPFS**: All THOT data, dataset manifests, and metadata stored via CIDs
- **Treasury**: 15% tithe automatically collected on deposits, multi-sig for large allocations
- **AgenticPlace**: Supports NFRLT, THOT, AgentFactory NFTs, and any whitelisted ERC721
- **BoardroomExtension**: Project-specific treasury management and allocation execution

### xmind/ - mindX Execution Layer

DAIO is a standalone governance system. External systems interact via the `xmind/` subfolder:

```
xmind/ (mindX Execution Layer)
├── DAIOBridge.sol           # Bridge contract for mindX ↔ DAIO
├── XMindAgentRegistry.sol   # Agent registration for mindX agents
├── XMindProposer.sol        # AI proposal submission to groups
└── XMindTreasuryReceiver.sol # Receive allocations from DAIO Treasury
```

**Integration Architecture**:
```
mindX (off-chain)
    ↓
xmind/ contracts (on-chain bridge)
    ↓
DAIO Governance (standalone)
    ↓
Marketing / Community / Development (2/3 consensus)
    ↓
BoardroomExtension (flexible voting → treasury execution)
```

**AI Proposal Flow**:
1. mindX AI agent creates proposal via `xmind/XMindProposer.sol`
2. Proposal submitted to target group (Marketing, Community, or Development)
3. Group votes (2 human + 1 AI = 3 votes, 2/3 required)
4. If 2/3 of groups approve, proposal succeeds
5. `BoardroomExtension` executes treasury allocation if applicable

### FinancialMind Integration

FinancialMind serves as the self-funding economic engine:

```
FinancialMind Trading Operation
    ↓
Profit Generated
    ↓
Constitutional Tithe (15% → Treasury)
    ↓
Agent Rewards (85% distributed)
    ↓
Agent Wallets (via smart contract)
    ↓
Increased Agent Voting Power
```

**Economic Sovereignty**: Agents earn shares through verified contributions, with compensation determined by smart contract logic

## Security Notes

- Solidity ^0.8.20/^0.8.24 (safe math by default)
- All external calls protected with reentrancy guards
- Soulbound tokens use `_update` hook to prevent transfers
- Maximum 25% total royalty cap in NFRLT
- CID validation prevents duplicate THOT minting
- Multi-signature wallets require 3-of-5 for treasury operations
- Challenge-response authentication for private key access via IDManagerAgent

## Strategic Roadmap

| Phase | Timeline | Objectives |
|-------|----------|------------|
| **Foundation** | Months 0-3 | ARC testnet deployment, mindX bridge, basic governance |
| **Integration** | Months 3-6 | THOT integration, FinancialMind treasury, AgenticPlace marketplace |
| **Expansion** | Months 6-12 | Mainnet deployment, multi-chain support, $100K+ treasury |
| **Sovereignty** | Months 12+ | Full economic autonomy, self-evolving governance |

## Related Documentation

See `../docs/` for comprehensive documentation:
- `DAIO.md` - Complete blockchain integration strategy
- `DAIO_CIVILIZATION_GOVERNANCE.md` - Constitutional framework and governance model
- `IDENTITY.md` - IDManagerAgent and cryptographic identity system
- `TECHNICAL.md` - mindX orchestration architecture
