# DAIO Contract Interaction Diagram

## Visual Interaction Map

```
┌─────────────────────────────────────────────────────────────────┐
│                    DAIO System Architecture                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      CORE GOVERNANCE LAYER                      │
└─────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────┐
                    │  DAIOGovernance.sol  │ ◄── Main Orchestrator
                    │  (Core Governance)    │
                    └──────────┬────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                        │
        ▼                      ▼                        ▼
┌───────────────┐    ┌──────────────────┐    ┌──────────────────┐
│Governance     │    │DAIO_Constitution │    │   Treasury.sol   │
│Settings.sol   │    │.sol              │    │                  │
│               │    │                  │    │                  │
│• Voting params│    │• 15% Diversify   │    │• Multi-project  │
│• Quorum       │    │• 15% Tithe       │    │• Auto-tithe     │
│• Thresholds   │    │• Chairman Veto   │    │• Allocations    │
└───────────────┘    └────────┬─────────┘    └────────┬─────────┘
                               │                        │
                               │ validates              │ uses
                               │                        │
                               └────────────┬───────────┘
                                            │
                                            ▼
                                    ┌───────────────┐
                                    │  Validates    │
                                    │  All Actions  │
                                    └───────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      IDENTITY LAYER                             │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐         ┌──────────────────────┐
│    IDNFT.sol         │─────────▶│  SoulBadger.sol      │
│                      │          │                      │
│• Agent Identity      │          │• Soulbound Badges    │
│• Prompt & Persona    │          │• Permanent Creds     │
│• THOT Tensors        │          │• User Attributes     │
│• Credentials         │          │• ERC-5484 Compliant  │
│• Trust Scores        │          │                      │
└──────────┬───────────┘          └──────────────────────┘
           │
           │ links to
           ▼
┌──────────────────────┐
│  AgentFactory.sol    │
│                      │
│• Creates Agents      │
│• Custom ERC20 Tokens │
│• Governance NFTs     │
│• Links to IDNFT      │
└──────────┬───────────┘
           │
           │ registers
           ▼
┌──────────────────────────────┐
│ KnowledgeHierarchyDAIO.sol    │
│                               │
│• 66.67% Human Voting          │
│• 33.33% AI Voting             │
│• Knowledge-Weighted           │
│• Domain-Specific Agents       │
└──────────┬────────────────────┘
           │
           │ uses
           ▼
┌──────────────────────┐
│  DAIOTimelock.sol    │
│                      │
│• Delayed Execution   │
│• Security Layer      │
└──────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    AGENT MANAGEMENT LAYER                       │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐
│ AgentManagement.sol  │
│                      │
│• Lifecycle Mgmt      │
│• Metadata Updates    │
│• Inactivity Tracking │
│• Auto-Deactivation   │
└──────────┬───────────┘
           │
           │ manages
           ▼
┌──────────────────────┐
│  AgentFactory.sol    │
└──────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                      EXTENSION LAYER                            │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────┐         ┌──────────────────────┐
│BoardroomExtension.sol │         │ FractionalNFT.sol    │
│                      │         │                      │
│• Treasury Extension   │         │• NFT Fractionalize   │
│• Allocation Mgmt      │         │• Shared Ownership    │
│• Project Treasuries   │         │• Redemption          │
└──────────────────────┘         └──────────────────────┘
```

## Interaction Flows

### Flow 1: Agent Creation
```
User/Governance
    │
    ▼
IDNFT.mintAgentIdentity()
    │
    ├─► Creates Identity NFT
    │   • Prompt, Persona, Metadata
    │   • Optional: SoulBadger badge
    │
    ▼
AgentFactory.createAgent()
    │
    ├─► Creates Custom ERC20 Token
    ├─► Mints Governance NFT
    ├─► Links to IDNFT Token ID
    │
    ▼
KnowledgeHierarchyDAIO.addOrUpdateAgent()
    │
    ├─► Sets Knowledge Level
    ├─► Sets Domain
    └─► Enables AI Voting
```

### Flow 2: Governance Proposal
```
Proposer
    │
    ▼
DAIOGovernance.createProposal()
    │
    ├─► Checks GovernanceSettings (threshold)
    ├─► Creates Proposal
    │
    ▼
Voting Phase
    │
    ├─► Human Voting
    │   └─► KnowledgeHierarchyDAIO.voteOnProposal()
    │       • Development, Marketing, Community
    │
    └─► AI Voting
        └─► KnowledgeHierarchyDAIO.aggregateAIVotes()
            • Knowledge-weighted votes
    │
    ▼
DAIOGovernance.executeProposal()
    │
    ├─► DAIO_Constitution.validateAction()
    │   • Checks diversification
    │   • Validates action
    │
    └─► Executes via Target Contract
        • Treasury.createAllocation()
        • Other contract calls
```

### Flow 3: Treasury Allocation
```
Deposit
    │
    ▼
Treasury.deposit()
    │
    ├─► Calculates 15% Tithe (from Constitution)
    ├─► Stores in Project Treasury
    │
    ▼
Proposal
    │
    ▼
DAIOGovernance.createTreasuryAllocationProposal()
    │
    ▼
Voting & Execution
    │
    ▼
Treasury.createAllocation()
    │
    ├─► DAIO_Constitution.checkDiversificationLimit()
    │   • Enforces 15% max per recipient
    │
    └─► Records Allocation
    │
    ▼
Treasury.executeAllocation()
    │
    └─► Transfers Funds
```

## Dependency Graph

```
DAIOGovernance (Root)
├── GovernanceSettings (provides parameters)
├── DAIO_Constitution (validates actions)
└── Treasury (executes allocations)
    └── DAIO_Constitution (tithe calculation)

AgentFactory
├── IDNFT (identity linking)
├── KnowledgeHierarchyDAIO (governance registration)
└── DAIOGovernance (authorization)

IDNFT
└── SoulBadger (optional soulbound)

KnowledgeHierarchyDAIO
├── TimelockController (execution)
└── DAIO_Constitution (validation)

AgentManagement
└── AgentFactory (lifecycle operations)

BoardroomExtension
└── DAIOGovernance (authorization)
```

## Data Flow Patterns

### Identity → Agent → Governance
```
IDNFT Token
    ↓ (tokenId)
AgentFactory.createAgent()
    ↓ (agentAddress, nftId)
KnowledgeHierarchyDAIO.addOrUpdateAgent()
    ↓ (knowledgeLevel, domain)
Voting Participation
```

### Proposal → Validation → Execution
```
Proposal Creation
    ↓
Settings Check (threshold)
    ↓
Voting (human + AI)
    ↓
Constitution Validation
    ↓
Timelock Delay
    ↓
Execution
```

### Treasury → Tithe → Allocation
```
Deposit
    ↓
15% Tithe (Constitution)
    ↓
Project Treasury
    ↓
Allocation Proposal
    ↓
Diversification Check (Constitution)
    ↓
Allocation Record
    ↓
Execution & Transfer
```

## Access Control Matrix

| Contract | Owner | Governance | Chairman | Signers | Public |
|----------|-------|------------|----------|---------|--------|
| DAIOGovernance | ✓ | - | - | - | vote, view |
| DAIO_Constitution | ✓ | ✓ | ✓ (veto) | - | view |
| Treasury | ✓ | ✓ | - | ✓ (3-of-5) | deposit, view |
| GovernanceSettings | ✓ | - | - | - | view |
| IDNFT | - | - | - | - | MINTER_ROLE |
| SoulBadger | - | - | - | - | BADGE_ISSUER_ROLE |
| AgentFactory | ✓ | ✓ | - | - | view |
| AgentManagement | - | ✓ | - | - | view |
| KnowledgeHierarchyDAIO | ✓ | ✓ (timelock) | - | - | vote, view |

## Key Integration Points

1. **Identity System**
   - IDNFT provides core identity
   - SoulBadger provides permanent credentials
   - Both used by AgentFactory

2. **Governance System**
   - DAIOGovernance orchestrates proposals
   - KnowledgeHierarchyDAIO handles voting
   - Constitution validates all actions

3. **Treasury System**
   - Treasury manages funds
   - Constitution enforces tithe and diversification
   - BoardroomExtension extends functionality

4. **Agent System**
   - AgentFactory creates agents
   - AgentManagement manages lifecycle
   - KnowledgeHierarchyDAIO enables voting

---

**Last Updated**: 2026-01-14  
**Version**: 1.0.0
