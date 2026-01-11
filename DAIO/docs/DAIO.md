# DAIO: Decentralized Autonomous Intelligent Organization
## Technical Documentation for Production Implementation

**Version:** 2.0.0
**Network:** ARC Testnet (Initial Deployment)
**Testing Framework:** Foundry
**Status:** Production Ready - Migrated from DAIO4
**Contract Location:** `/DAIO/CONTRACTS/src/`

---

## Overview

The **Decentralized Autonomous Intelligent Organization (DAIO)** is the blockchain-native governance and economic layer for mindX, enabling seamless orchestration of autonomous agents with cryptographic identity, on-chain governance, and sovereign economic operations.

This document provides comprehensive technical documentation for the production DAIO implementation, migrated from the DAIO4 research phase.

---

## Architecture

### Core Smart Contracts

#### 1. DAIO_Constitution.sol
**Purpose:** Primary governance contract enforcing constitutional constraints

**Key Functions:**
- `validateAction()`: Validates all actions against constitutional rules
- `checkDiversificationLimit()`: Enforces 15% diversification mandate
- `pauseSystem()` / `unpauseSystem()`: Emergency pause (Chairman's Veto)

**Constitutional Principles:**
- Code is Law
- 15% Diversification Mandate
- Chairman's Veto
- Immutable Tithe (15% to treasury)

#### 2. KnowledgeHierarchyDAIO.sol
**Purpose:** Agent registry and governance proposal system

**Key Functions:**
- `addOrUpdateAgent()`: Register agents with knowledge levels
- `createProposal()`: Create governance proposals
- `voteOnProposal()`: Human subcomponent voting
- `agentVote()`: AI agent voting (knowledge-weighted)
- `executeProposal()`: Execute approved proposals

**Governance Model:**
- Human Vote: 66.67% (Development, Marketing, Community subcomponents)
- AI Vote: 33.33% (Knowledge-weighted agent aggregation)
- Execution: 2/3 majority required, timelock delays

#### 3. IDNFT.sol (Identity NFT - Optional Soulbound)
**Purpose:** Cryptographic identity and persona management for agents with optional soulbound functionality via SoulBadger

**Key Distinctions:**
- **IDNFT**: Identity and persona handling (can optionally be soulbound)
- **iNFT**: Intelligent NFT (can be dynamic, includes intelligence metadata: prompt, persona, model dataset, THOT)
- **dNFT**: Dynamic NFT (not intelligent, just dynamic metadata updates)

**Key Functions:**
- `mintAgentIdentity()`: Create agent identity with prompt, persona, model dataset, and THOT integration
- `mintSoulboundIdentity()`: Create soulbound agent identity using SoulBadger integration
- `updateTrustScore()`: Update agent trust metrics
- `issueCredential()`: Issue verifiable credentials
- `attachTHOT()`: Attach transferable hyper optimized tensors to agent identity
- `updatePersona()`: Update agent persona and prompt metadata
- `enableSoulbound()`: Convert existing IDNFT to soulbound (one-way operation)
- `isSoulbound()`: Check if identity is soulbound

**SoulBadger Integration:**
- Optional soulbound functionality via SoulBadger contract
- Soulbound identities are non-transferable (permanently bound to agent wallet)
- Choice between transferable IDNFT and soulbound IDNFT at minting
- Soulbound enforcement prevents identity transfer after minting
- Useful for permanent agent credentials and immutable identity records

**IDNFT Identity Components:**
- Ethereum-compatible wallet address
- **Prompt**: System prompt defining agent behavior and capabilities (from AutoMINDXAgent)
- **Persona**: Cognitive traits, behavioral patterns, and personality metadata (JSON-encoded)
- **Model Dataset**: IPFS CID reference to agent model weights and architecture (optional)
- **THOT Integration**: Transferable hyper optimized tensors (THOT8d, THOT512, THOT768) stored on IPFS (optional)
- NFT representing identity with persona metadata
- Trust score tracking
- Metadata stored on IPFS with content addressing
- **Soulbound Flag**: Optional flag indicating if identity is soulbound (non-transferable)

**THOT Tensor Support:**
- THOT8d: 8-dimensional transferable tensors (spatial-temporal-quantum)
- THOT512: 512 data point knowledge clusters (8x8x8 3D)
- THOT768: 768-dimensional optimized tensors
- IPFS CID storage for tensor data
- Transferable between agents and systems (unless soulbound)
- Verifiable tensor integrity via cryptographic hashing

**Soulbound vs Transferable:**
- **Transferable IDNFT**: Can be transferred between wallets (default)
- **Soulbound IDNFT**: Permanently bound to agent wallet via SoulBadger (optional)
- Soulbound conversion is one-way and irreversible
- Soulbound identities provide immutable identity records

#### 4. AgentFactory.sol
**Purpose:** On-chain agent creation and lifecycle management

**Key Functions:**
- `createAgent()`: Create new agent with ERC20 token and NFT
- `destroyAgent()`: Deactivate agent
- `reactivateAgent()`: Reactivate inactive agent
- `updateNFTMetadata()`: Update agent metadata

**Agent Creation Process:**
1. Governance approval required
2. Custom ERC20 token created for agent
3. Fractionalized NFT minted for governance rights
4. Agent registered in KnowledgeHierarchyDAIO

#### 5. Treasury.sol
**Purpose:** Economic operations and profit distribution

**Key Functions:**
- `deposit()`: Receive profits from operations
- `distributeReward()`: Distribute rewards to agents
- `requestAllocation()`: Request treasury funds (requires governance)
- `checkConstitutionalConstraints()`: Validate all operations

**Economic Model:**
- 15% tithe to treasury (constitutional)
- 85% distributed to contributing agents
- Multi-signature wallet (3-of-5)
- Cross-chain asset support

---

## Integration with mindX

### mindX → DAIO Bridge

**Web3 Integration Layer:**
```python
class DAIOBridge:
    """Bridge between mindX orchestration and DAIO smart contracts."""
    
    def __init__(self, web3_provider: str, contract_addresses: dict):
        self.w3 = Web3(Web3.HTTPProvider(web3_provider))
        self.contracts = self._load_contracts(contract_addresses)
```

### Integration Points

#### 1. Agent Identity Registration (IDNFT)
- IDManagerAgent generates cryptographic identity (ECDSA keypair)
- AutoMINDXAgent provides prompt and persona metadata
- Agent model dataset prepared and uploaded to IPFS (if applicable)
- THOT tensors (if applicable) prepared and uploaded to IPFS
- Decision made: Transferable IDNFT or Soulbound IDNFT (via SoulBadger)
- Agent registered in IDNFT contract:
  - **Transferable**: `mintAgentIdentity()` with `useSoulbound = false`
  - **Soulbound**: `mintSoulboundIdentity()` or `mintAgentIdentity()` with `useSoulbound = true`
  - Prompt and persona metadata stored
  - Model dataset CID linked (optional)
  - THOT tensor CIDs attached (optional)
  - IDNFT minted with identity and persona metadata
  - If soulbound: SoulBadger contract enforces non-transferability
- Agent added to KnowledgeHierarchyDAIO with knowledge level
- CoordinatorAgent updates runtime registry
- Agent becomes active participant in DAIO governance

**NFT Type Selection:**
- **IDNFT**: Use for identity and persona (can be soulbound or transferable)
- **iNFT**: Use when full intelligence metadata needed (prompt, persona, model, THOT) - can be dynamic
- **dNFT**: Use for dynamic metadata updates without intelligence features

#### 2. Governance Proposal Generation
- MastermindAgent creates strategic proposals
- Proposals submitted to KnowledgeHierarchyDAIO
- AI agents vote via aggregated system
- Human subcomponents vote
- Approved proposals executed via timelock

#### 3. Economic Operations
- FinancialMind profits routed to treasury
- Treasury distributes rewards to agents
- All transactions recorded on-chain
- Constitutional constraints enforced

---

## Deployment

### Network: ARC Testnet

**Initial Deployment:**
- EVM-compatible testnet
- Low-cost testing environment
- Mainnet migration path

**Mainnet Migration:**
- Comprehensive audit required
- Gradual migration with dual-operation
- Multi-signature governance during transition

### Deployment Order

```
1. TimelockController.sol
2. DAIO_Constitution.sol
3. KnowledgeHierarchyDAIO.sol
4. SoulBadger.sol (optional, if soulbound identities are needed)
5. IDNFT.sol (references SoulBadger if soulbound functionality enabled)
6. AgentFactory.sol
7. Treasury.sol
8. Integration Contracts
```

**Note:** SoulBadger deployment is optional. If soulbound identity functionality is not required, IDNFT can operate without SoulBadger integration.

### Foundry Deployment Script

**Location:** `/DAIO/CONTRACTS/script/Deploy.s.sol`

```solidity
// script/Deploy.s.sol
contract DeployDAIO is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        vm.startBroadcast(deployerPrivateKey);

        // 1. Deploy TimelockController
        TimelockController timelock = new TimelockController(
            2 days,      // minDelay
            proposers,   // proposers array
            executors,   // executors array
            deployer     // admin
        );

        // 2. Deploy DAIO_Constitution
        DAIO_Constitution constitution = new DAIO_Constitution(
            deployer,           // chairman
            address(timelock)   // governance
        );

        // 3. Deploy SoulBadger
        SoulBadger soulBadger = new SoulBadger(
            "DAIO Soul Badger",
            "DSOUL",
            "https://daio.mindx.io/soulbadger/"
        );

        // 4. Deploy IDNFT
        IDNFT idnft = new IDNFT();
        idnft.setSoulBadger(address(soulBadger));

        // 5. Deploy KnowledgeHierarchyDAIO
        KnowledgeHierarchyDAIO knowledgeHierarchy = new KnowledgeHierarchyDAIO(timelock);

        // 6. Deploy AgentFactory
        AgentFactory agentFactory = new AgentFactory(address(knowledgeHierarchy));

        // 7. Deploy Treasury
        Treasury treasury = new Treasury(address(constitution));

        vm.stopBroadcast();
    }
}
```

**Deployment Commands:**
```bash
# Deploy to testnet
forge script script/Deploy.s.sol:DeployDAIOTestnet --rpc-url $RPC_URL --broadcast

# Deploy to mainnet (requires additional verification)
forge script script/Deploy.s.sol:DeployDAIO --rpc-url $RPC_URL --broadcast --verify
```

---

## Testing

### Foundry Test Suite

**Test Location:** `/DAIO/CONTRACTS/test/`

**Test Files:**
| File | Description |
|------|-------------|
| `DAIO_Constitution.t.sol` | Constitutional validation tests |
| `SoulBadger.t.sol` | Soulbound token tests |
| `IDNFT.t.sol` | Agent identity and THOT integration tests |
| `Integration.t.sol` | Full system integration tests |

**Test Categories:**
1. Constitutional validation tests (tithe, diversification, veto)
2. Soulbound token minting and transfer restrictions
3. Agent identity creation and credential management
4. THOT tensor attachment and verification
5. Governance proposal and voting tests
6. Agent creation and lifecycle tests
7. Treasury operations and multi-sig tests
8. Full integration tests with all contracts

**Running Tests:**
```bash
# Run all tests
forge test

# Run specific test file
forge test --match-path test/DAIO_Constitution.t.sol

# Run with gas report
forge test --gas-report

# Run with verbosity
forge test -vvvv

# Run specific test function
forge test --match-test test_ChairmanCanPause
```

---

## Security

### Audit Requirements
- Comprehensive smart contract audit
- Formal verification for critical functions
- Bug bounty program
- Emergency response procedures

### Key Management
- Hardware Security Modules (HSM)
- Multi-signature wallets
- Deterministic key generation
- Secure key storage

### Access Control
- GuardianAgent validation
- Challenge-response authentication
- Rate limiting
- Gas optimization

---

## API Reference

### Agent Identity Minting (IDNFT)
```solidity
function mintAgentIdentity(
    address primaryWallet,
    string memory agentType,
    string memory prompt,              // System prompt defining agent behavior
    string memory persona,              // JSON-encoded persona metadata
    string memory modelDatasetCID,      // IPFS CID for model weights/dataset (optional)
    bytes32[] memory thotCIDs,          // Array of THOT tensor IPFS CIDs (optional)
    uint8[] memory thotDimensions,      // Dimensions for each THOT (64, 512, 768)
    string memory metadataURI,           // Additional metadata URI
    bool useSoulbound                    // Optional: Use SoulBadger for soulbound identity
) external returns (uint256 tokenId);
```

**Parameters:**
- `primaryWallet`: Ethereum wallet address for agent
- `agentType`: Type/category of agent (e.g., "BDIAgent", "MastermindAgent")
- `prompt`: System prompt from AutoMINDXAgent persona system
- `persona`: JSON-encoded persona data including:
  - Cognitive traits
  - Behavioral patterns
  - Complexity score
  - Capabilities array
  - Avatar metadata
- `modelDatasetCID`: IPFS content identifier for agent model dataset (optional, empty string if not applicable)
- `thotCIDs`: Array of IPFS CIDs for THOT tensors (THOT8d, THOT512, THOT768) (optional, empty array if not applicable)
- `thotDimensions`: Corresponding dimensions for each THOT tensor
- `metadataURI`: Additional metadata stored on IPFS
- `useSoulbound`: If true, uses SoulBadger integration for non-transferable soulbound identity

**Soulbound Identity Minting:**
```solidity
function mintSoulboundIdentity(
    address primaryWallet,
    string memory agentType,
    string memory prompt,
    string memory persona,
    string memory modelDatasetCID,
    bytes32[] memory thotCIDs,
    uint8[] memory thotDimensions,
    string memory metadataURI
) external returns (uint256 tokenId);
```

**Soulbound Behavior:**
- Identity permanently bound to agent wallet address
- Non-transferable after minting
- Enforced via SoulBadger contract integration
- Useful for permanent credentials and immutable identity records
- One-way operation (cannot be converted back to transferable)

**THOT Tensor Integration:**
- THOT tensors stored on IPFS with content addressing
- Transferable between agents and systems (unless identity is soulbound)
- Verifiable integrity via cryptographic hashing
- Supports THOT8d (8-dim), THOT512 (512 data points), THOT768 (768-dim)
- Enables knowledge transfer and agent evolution

**NFT Type Distinctions:**
- **IDNFT**: Identity and persona handling (can be soulbound or transferable)
- **iNFT**: Intelligent NFT with full intelligence metadata (can be dynamic, includes prompt/persona/model/THOT)
- **dNFT**: Dynamic NFT with updatable metadata (not intelligent, just dynamic updates)

### Agent Registration
```solidity
function addOrUpdateAgent(
    address _agentAddress,
    uint _knowledgeLevel,
    Domain _domain,
    bool _active
) external onlyGovernance;
```

### Proposal Creation
```solidity
function createProposal(
    string memory description
) public onlyGovernance returns (uint256);
```

### Agent Voting
```solidity
function agentVote(
    uint256 proposalId,
    bool support
) public;
```

### Treasury Distribution
```solidity
function distributeReward(
    address to,
    uint256 amount,
    string memory reason
) external onlyGovernance;
```

### THOT Tensor Attachment
```solidity
function attachTHOT(
    uint256 tokenId,
    bytes32 thotCID,
    uint8 dimensions,
    uint8 parallelUnits
) external returns (bool);
```

**Purpose:** Attach additional THOT tensors to existing agent identity

**Parameters:**
- `tokenId`: Agent identity NFT token ID
- `thotCID`: IPFS CID for THOT tensor data
- `dimensions`: THOT dimensions (64, 512, or 768)
- `parallelUnits`: Number of parallel processing units

**Returns:** Success status of THOT attachment

### Soulbound Operations
```solidity
function enableSoulbound(uint256 tokenId) external returns (bool);
function isSoulbound(uint256 tokenId) external view returns (bool);
function getSoulBadgerAddress() external view returns (address);
```

**Purpose:** Manage soulbound identity functionality via SoulBadger integration

**Functions:**
- `enableSoulbound()`: Convert transferable IDNFT to soulbound (one-way, irreversible)
- `isSoulbound()`: Check if identity is soulbound
- `getSoulBadgerAddress()`: Get address of integrated SoulBadger contract

---

## Status

**Current Phase:** Production Implementation  
**Network:** ARC Testnet  
**Testing:** Foundry Framework  
**Integration:** mindX Orchestration Layer

---

**Last Updated:** 2026-01-11
**Maintainer:** mindX Architecture Team

---

## Contract Summary

### Production Contract Files

| Contract | Location | Description |
|----------|----------|-------------|
| `DAIO_Constitution.sol` | `src/DAIO_Constitution.sol` | Constitutional governance and constraints |
| `SoulBadger.sol` | `src/SoulBadger.sol` | Soulbound token implementation (ERC-5484 inspired) |
| `IDNFT.sol` | `src/IDNFT.sol` | Agent identity with THOT and credential support |
| `KnowledgeHierarchyDAIO.sol` | `src/KnowledgeHierarchyDAIO.sol` | Governance and voting system |
| `AgentFactory.sol` | `src/AgentFactory.sol` | Agent creation with ERC20/NFT |
| `Treasury.sol` | `src/Treasury.sol` | Multi-sig treasury with tithe enforcement |

### Supporting Files

| File | Location | Description |
|------|----------|-------------|
| `Deploy.s.sol` | `script/Deploy.s.sol` | Foundry deployment script |
| `foundry.toml` | `foundry.toml` | Foundry configuration |

### Dependencies

- OpenZeppelin Contracts v5.x (`lib/openzeppelin-contracts/`)
- Foundry (forge, cast, anvil)

### Key Features Implemented

1. **Constitutional Governance**
   - 15% diversification mandate
   - 15% treasury tithe
   - Chairman's veto (emergency pause)
   - Action validation system

2. **Agent Identity (IDNFT)**
   - System prompt storage
   - JSON persona metadata
   - THOT tensor attachments (8D, 512, 768)
   - Model dataset CID references
   - Optional soulbound functionality
   - Credential issuance and verification

3. **Governance (KnowledgeHierarchyDAIO)**
   - 66.67% human voting (Dev, Marketing, Community)
   - 33.33% AI agent voting (knowledge-weighted)
   - Timelock-controlled execution
   - Proposal lifecycle management

4. **Treasury**
   - Multi-signature (3-of-5) transactions
   - Automatic tithe collection
   - Reward distribution to agents
   - Diversification tracking
   - Constitutional compliance checks

5. **SoulBadger**
   - Non-transferable badges
   - Agent credential management
   - ERC-5484 inspired burn authorization
   - Badge expiration support
