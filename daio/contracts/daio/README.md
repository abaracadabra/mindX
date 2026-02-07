# DAIO (Decentralized Autonomous Intelligence Organization) Contracts

**Version:** 2.0.0  
**Status:** Production Ready  
**Network:** Multi-chain (ARC, Polygon, Testnet)

---

## Overview

The DAIO system provides blockchain-native governance and economic operations for the distributed intelligence knowledge economy. It enables seamless orchestration of autonomous agents with cryptographic identity, on-chain governance, and sovereign economic operations.

### Key Principles

- **Modular Design** - Works standalone or within mindX orchestration
- **Multi-Project Support** - FinancialMind, mindX, cryptoAGI, and more
- **Constitutional Governance** - Immutable rules enforced on-chain
- **Knowledge-Weighted Voting** - AI agents vote with knowledge-based power
- **Treasury Management** - 15% tithe, allocation system, multi-sig

---

## Contract Structure

```
contracts/daio/
├── DAIOGovernance.sol          # Core governance hub
├── DAIORebaseToken.sol         # DAIO inflationary rebase (positive rebase / mint)
├── DAIODeflateToken.sol        # DAIO deflationary rebase (negative rebase / burn)
├── reflection/
│   ├── DAIOReflectionToken.sol # Reflection token (fee-on-transfer, holder rewards; DAIO admin hierarchy)
│   └── README.md               # Auto-swap fixes, slippage, deployment
├── BoardroomExtension.sol       # Treasury extension
├── constitution/
│   └── DAIO_Constitution.sol    # Constitutional constraints
├── treasury/
│   ├── Treasury.sol             # Multi-project treasury (owns any/all assets)
│   ├── CustomERC20Minter.sol     # ERC20 with minter role
│   └── WETH.sol                 # Wrapped Ether (value-inheritance example)
├── governance/
│   ├── KnowledgeHierarchyDAIO.sol  # Agent governance
│   ├── AgentFactory.sol            # Agent creation
│   ├── DAIOTimelock.sol            # Timelock controller
│   └── FractionalNFT.sol           # NFT fractionalization
├── identity/
│   ├── IDNFT.sol                   # Agent identity
│   └── SoulBadger.sol              # Soulbound tokens
├── settings/
│   └── GovernanceSettings.sol       # Parameter management
└── interfaces/
```

---

## Core Contracts

### 1. DAIOGovernance.sol
**Purpose:** Central governance hub for multi-project orchestration

**Key Features:**
- Proposal creation and voting
- Treasury allocation proposals
- Project registration
- Settings integration
- Constitutional validation

**Documentation:** `docs/solidity/daio-governance.md`

### 2. DAIO_Constitution.sol
**Purpose:** Enforces immutable constitutional rules

**Key Features:**
- 15% diversification mandate
- 15% treasury tithe (enforced in Treasury)
- Chairman's veto power
- Action validation

**Documentation:** `docs/solidity/daio-constitution.md`

### 3. Treasury.sol
**Purpose:** Multi-project treasury with allocation management

**Key Features:**
- Automatic 15% tithe collection
- Native and ERC20 token support
- Proposal-based allocations
- Multi-signature support
- Constitutional compliance

**Documentation:** `docs/solidity/daio-treasury.md`

### 4. KnowledgeHierarchyDAIO.sol
**Purpose:** Agent registry with knowledge-weighted voting

**Key Features:**
- 66.67% human voting (Dev, Marketing, Community)
- 33.33% AI voting (knowledge-weighted)
- Agent registration with knowledge levels
- Proposal execution via timelock

**Documentation:** `docs/solidity/knowledge-hierarchy-daio.md`

### 5. AgentFactory.sol
**Purpose:** Agent creation with ERC20 and NFT

**Key Features:**
- Custom ERC20 token per agent
- Fractionalized NFT for governance
- IDNFT integration
- Agent lifecycle management

**Documentation:** `docs/solidity/agent-factory.md`

### 6. IDNFT.sol
**Purpose:** Agent identity with full metadata support

**Key Features:**
- System prompt and persona storage
- THOT tensor attachments
- Credential issuance
- Trust score tracking
- Optional soulbound functionality

**Documentation:** `docs/solidity/idnft.md`

### 7. SoulBadger.sol
**Purpose:** Soulbound token implementation

**Key Features:**
- Non-transferable NFTs
- User identity attributes
- IDNFT linking
- Permanent credentials

**Documentation:** `docs/solidity/soulbadger.md`

### 8. GovernanceSettings.sol
**Purpose:** Configurable governance parameters

**Key Features:**
- Global and project-specific settings
- Voting periods and thresholds
- Timelock delays
- Proposal thresholds

**Documentation:** `docs/solidity/governance-settings.md`

### 9. DAIOTimelock.sol
**Purpose:** Time-delayed execution wrapper

**Key Features:**
- Minimum delay enforcement
- Role-based access
- Security layer for proposals

**Documentation:** `docs/solidity/daiotimelock.md`

### 10. FractionalNFT.sol
**Purpose:** NFT fractionalization for governance

**Key Features:**
- Split NFT into ERC20 tokens
- Governance voting
- Redeemable for full NFT

**Documentation:** `docs/solidity/fractional-nft.md`

---

## Deployment Order

1. **DAIOTimelock** - Deploy timelock controller
2. **DAIO_Constitution** - Deploy constitution with chairman
3. **SoulBadger** - Deploy soulbound token contract (optional)
4. **IDNFT** - Deploy identity NFT with SoulBadger integration
5. **GovernanceSettings** - Deploy settings contract
6. **Treasury** - Deploy treasury with constitution and signers
7. **KnowledgeHierarchyDAIO** - Deploy governance with timelock
8. **AgentFactory** - Deploy agent factory
9. **DAIOGovernance** - Deploy main governance hub
10. **FractionalNFT** - Deploy as needed for specific NFTs

---

## Integration with Projects

### FinancialMind
- Register as project: `registerProject("financialmind")`
- Create treasury allocations for model upgrades
- Agent registration for trading agents
- Reward distribution for profitable trades

### mindX
- Orchestration environment integration
- Cross-project coordination
- Agent lifecycle management
- Multi-project treasury

### cryptoAGI
- Agent identity management
- THOT tensor integration
- Governance participation
- Treasury allocations

---

## Governance Flow

1. **Proposal Creation**
   - Governance creates proposal via `DAIOGovernance.createProposal()`
   - Or treasury allocation via `createTreasuryAllocationProposal()`

2. **Voting**
   - Human votes via `KnowledgeHierarchyDAIO.voteOnProposal()`
   - AI agents vote via `agentVote()` with knowledge-weighted power
   - Votes aggregated: 66.67% human, 33.33% AI

3. **Validation**
   - Constitutional validation via `DAIO_Constitution.validateAction()`
   - Diversification limit checking
   - Treasury balance verification

4. **Execution**
   - Timelock delay enforced
   - Execution via `executeProposal()`
   - Treasury allocations executed via `Treasury.executeAllocation()`

---

## Configuration

### Governance Settings

```solidity
// Global settings
settings.updateSettings(
    45818,   // Voting period (blocks)
    5000,    // Quorum threshold (50%)
    5000,    // Approval threshold (50%)
    17280,   // Timelock delay (blocks)
    100,     // Proposal threshold
    10       // Min voting power
);

// Project-specific settings
settings.updateProjectSettings(
    "financialmind",
    23090,   // Custom voting period
    4000,    // Custom quorum
    6000,    // Custom approval
    8640,    // Custom timelock
    50,      // Custom proposal threshold
    5        // Custom min voting power
);
```

### Treasury Setup

```solidity
// Deploy with 3-of-5 multi-sig
address[] memory signers = [signer1, signer2, signer3, signer4, signer5];
Treasury treasury = new Treasury(
    address(constitution),
    signers
);
```

---

## Events

All contracts emit comprehensive events for:
- Proposal lifecycle
- Voting actions
- Agent creation/updates
- Treasury operations
- Identity management
- Settings changes

---

## Security Features

- **Constitutional Constraints** - All actions validated
- **Timelock Delays** - Prevents immediate execution
- **Multi-Signature** - Large allocations require multiple signers
- **Access Control** - Role-based permissions
- **Reentrancy Protection** - Guards on critical functions
- **Soulbound Tokens** - Immutable identity records

---

## Testing

All contracts are tested with Foundry:

```bash
forge test
forge test --match-path test/daio/*
forge test --gas-report
```

---

## Documentation

Comprehensive documentation available in `docs/solidity/`:

- `daio-governance.md` - Core governance contract
- `daio-constitution.md` - Constitutional constraints
- `daio-treasury.md` - Treasury management
- `knowledge-hierarchy-daio.md` - Agent governance
- `agent-factory.md` - Agent creation
- `idnft.md` - Identity management
- `soulbadger.md` - Soulbound tokens
- `governance-settings.md` - Parameter management
- `daiotimelock.md` - Timelock controller
- `fractional-nft.md` - NFT fractionalization

---

## Related Documentation

- **Architecture:** `docs/architecture/THOT-DAIO-ARCHITECTURE.md`
- **Deployment:** `docs/getting-started/DNFT-DEPLOYMENT-GUIDE.md`
- **DAIO Spec:** `DDD/DAIO.md`

---

## References and ecosystem

| Link | Description |
|------|-------------|
| [interplanetaryfilesystem](https://github.com/interplanetaryfilesystem) | IPFS core and ecosystem. |
| [ipNFTfs](https://github.com/ipNFTfs) | Interplanetary NFT file system and IPFS utilities; reference for NFT-on-IPFS and DAIO identity/NFT workflows. |
| [mlodular](https://github.com/mlodular) | Modular ML / tooling reference. |
| [faicey](https://github.com/faicey), [jaimla](https://github.com/jaimla), [Professor-Codephreak](https://github.com/Professor-Codephreak) | References. |
| [w3DAIO](https://github.com/w3DAIO) | First public showing of the DAIO code; Decentralized Autonomous Intelligent Organization (scaffold-eth-2, EVM dev stack). |
| [DAONOW](https://github.com/DAONOW) | Reference for DAO tooling and governance patterns. |
| [dairef](https://github.com/dairef) | Programmable DAI reference (see [Treasury and DAI](docs/daio/treasury/Treasury.md#dai-and-stablecoin-support)). |
| **Sites:** [rage.pythai.net](https://rage.pythai.net), [mindx.pythai.net](https://mindx.pythai.net), [agenticplace.pythai.net](https://agenticplace.pythai.net), [daio.pythai.net](https://daio.pythai.net) (voting UI). |

---

**Last Updated:** 2026-01-11  
**Status:** Production Ready  
**Maintainer:** mindX Architecture Team
