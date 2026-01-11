# DAIO Governance Contracts

## Overview

This directory contains governance-related smart contracts for the DAIO (Decentralized Autonomous Intelligent Organization) system.

## Contracts

### AgenticOrchestrator.sol

**Purpose:** On-chain orchestration system for agent lifecycle and consensus management

**Key Features:**
- Consensus-based agent creation, destruction, and updates
- Agent hierarchy management (parent-child relationships)
- Integration with IDNFT for agent identity
- Role-based access control
- Configurable consensus thresholds
- Timelock for proposal execution

**Roles:**
- `ORCHESTRATOR_ROLE`: Manages agent hierarchies
- `CONSENSUS_ROLE`: Votes on proposals
- `AGENT_CREATOR_ROLE`: Proposes agent creation
- `AGENT_DESTROYER_ROLE`: Proposes agent destruction

**Integration:**
- Requires IDNFT contract address in constructor
- Must be granted MINTER_ROLE in IDNFT to create agent identities
- Works with KnowledgeHierarchyDAIO for governance proposals

**Usage:**
1. Deploy IDNFT contract first
2. Deploy AgenticOrchestrator with IDNFT address
3. Grant MINTER_ROLE to AgenticOrchestrator in IDNFT
4. Grant appropriate roles to agents/users
5. Agents can propose creation/destruction/updates
6. Consensus role holders vote on proposals
7. Proposals execute after consensus and timelock

---

### SoulBadger.sol

**Purpose:** Soulbound token implementation for permanent agent credentials

**Key Features:**
- Non-transferable NFTs (soulbound)
- User identity with 8 attributes
- Link to IDNFT token IDs
- ERC-5484 inspired

**Usage:**
- Mint soulbound badges for agents
- Link badges to IDNFT identities
- Permanent credential representation

---

### UniversalIdentity.sol

**Purpose:** ERC-7777 implementation for human-robot governance

**Key Features:**
- Universal Identity for robots and humans
- Universal Charter for rule sets
- Challenge-response verification
- Compliance checking

**Usage:**
- Register robots and humans
- Define rule sets
- Check compliance
- Manage human-robot interactions

---

## Deployment Order

1. Deploy IDNFT contract
2. Deploy SoulBadger contract (optional)
3. Deploy AgenticOrchestrator with IDNFT address
4. Grant MINTER_ROLE to AgenticOrchestrator in IDNFT
5. Deploy UniversalIdentity/UniversalCharter (if needed)
6. Configure roles and thresholds

---

## Integration with mindX

The AgenticOrchestrator integrates with mindX orchestration:

- **CoordinatorAgent** → Monitors on-chain agent registry
- **MastermindAgent** → Creates proposals for agent operations
- **IDManagerAgent** → Generates identities that get registered on-chain
- **AgentFactoryTool** → Creates agents that are registered in AgenticOrchestrator

---

**Last Updated:** 2025-01-27
