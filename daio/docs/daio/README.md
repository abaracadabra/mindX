# DAIO Contracts Documentation

## Overview

This directory contains comprehensive documentation for all DAIO (Decentralized Autonomous Intelligence Organization) contracts.

## Documentation Files

1. **[DAIO_CONTRACTS_ANALYSIS.md](./DAIO_CONTRACTS_ANALYSIS.md)** - Complete analysis of all 12 DAIO contracts
   - Contract details and structures
   - Key functions and features
   - Dependencies and interactions
   - Design patterns and security features

2. **[DAIO_INTERACTION_DIAGRAM.md](./DAIO_INTERACTION_DIAGRAM.md)** - Visual interaction diagrams
   - Contract architecture diagrams
   - Interaction flow charts
   - Dependency graphs
   - Data flow patterns

## Contract Summary

### Total Contracts: 12
### Total Lines: 2,695

### Categories:
- **Governance** (4 contracts): DAIOGovernance, KnowledgeHierarchyDAIO, DAIOTimelock, BoardroomExtension
- **Identity** (2 contracts): IDNFT, SoulBadger
- **Agent Management** (2 contracts): AgentFactory, AgentManagement
- **Treasury** (1 contract): Treasury
- **Constitution** (1 contract): DAIO_Constitution
- **Settings** (1 contract): GovernanceSettings
- **Extensions** (1 contract): FractionalNFT

## Quick Reference

### Core Contracts
- **DAIOGovernance.sol** - Main governance orchestrator
- **DAIO_Constitution.sol** - Constitutional rules enforcement
- **Treasury.sol** - Multi-project treasury with tithe

### Identity Contracts
- **IDNFT.sol** - Agent identity NFTs with full metadata
- **SoulBadger.sol** - Soulbound credentials (ERC-5484)

### Agent Contracts
- **AgentFactory.sol** - Agent creation with tokens/NFTs
- **AgentManagement.sol** - Agent lifecycle management

### Governance Contracts
- **KnowledgeHierarchyDAIO.sol** - AI-weighted voting (66.67% human, 33.33% AI)
- **DAIOTimelock.sol** - Delayed execution controller

## Key Features

- **Multi-Project Support**: FinancialMind, mindX, cryptoAGI, etc.
- **15% Diversification Mandate**: Max 15% allocation per recipient
- **15% Treasury Tithe**: Automatic on all deposits
- **Knowledge-Weighted Voting**: AI agents vote based on knowledge level
- **Soulbound Identities**: Permanent credential binding
- **THOT Integration**: Tensor attachment for agent capabilities

## Contract Locations

All contracts are located in `/home/hacker/mindX/daio/contracts/daio/`

## Related Documentation

- Constitution: `docs/daio/constitution/DAIO_Constitution.md`
- Governance: `docs/daio/governance/`
- Identity: `docs/daio/identity/`
- Treasury: `docs/daio/treasury/`
- Settings: `docs/daio/settings/`

---

**Last Updated**: 2026-01-14  
**Version**: 1.0.0
