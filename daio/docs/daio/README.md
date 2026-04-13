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

3. **[DAIO_MINDX_INTEGRATION.md](./DAIO_MINDX_INTEGRATION.md)** - Comprehensive integration guide for DAIO with mindX
   - Identity integration (IDNFT, SoulBadger)
   - Governance participation (AI-weighted voting)
   - Treasury management and autonomous funding
   - Agent registration and lifecycle
   - Use cases and implementation patterns
   - Code examples and best practices

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

- **Ecosystem and references:** [ECOSYSTEM.md](ECOSYSTEM.md) — ipNFTfs, w3DAIO, DAONOW, dairef, MakerDAO/dss.
- Constitution: `docs/daio/constitution/DAIO_Constitution.md`
- Governance: `docs/daio/governance/`
  - **[CONSENSUS_MATHEMATICS.md](governance/CONSENSUS_MATHEMATICS.md)** — Prime number consensus: 1/3 diffusion (three dictators) → 2/3 majority → 3/3 unilateral. MarriageDAO, SupremeCourtDAO (5/9), UNDAO (Security Council as Boardroom, General Assembly as Dojo), PhysicsDAO, openBDK genesis, 13-validator decentralization, mirror attack.
  - **[PRIME_CONSENSUS.md](governance/PRIME_CONSENSUS.md)** — 5050 consensus combinators: every ratio a/b for body sizes 1–100. The complete reference of governance positions from fragment through unanimous.
  - **[ROBERTS_RULES.md](governance/ROBERTS_RULES.md)** — Robert's Rules of Order encoded for DAIO. Motion state machine, precedence stack, 4 motion classes, 22 motion types, quorum. Contract: `RobertsRulesDAIO.sol`. Boardroom = full protocol (Security Council). Dojo = yes or no (General Assembly). Prior art: Rob's Rules DAO (Vocdoni/Aragon).
- Identity: `docs/daio/identity/`
- Treasury: `docs/daio/treasury/`
- Settings: `docs/daio/settings/`

## References and ecosystem

See [ECOSYSTEM.md](ECOSYSTEM.md) for the full list. Summary: [interplanetaryfilesystem](https://github.com/interplanetaryfilesystem), [ipNFTfs](https://github.com/ipNFTfs), [mlodular](https://github.com/mlodular), [faicey](https://github.com/faicey), [jaimla](https://github.com/jaimla), [Professor-Codephreak](https://github.com/Professor-Codephreak), [w3DAIO](https://github.com/w3DAIO), [DAONOW](https://github.com/DAONOW), [dairef](https://github.com/dairef). Sites: [rage.pythai.net](https://rage.pythai.net), [mindx.pythai.net](https://mindx.pythai.net), [agenticplace.pythai.net](https://agenticplace.pythai.net), [daio.pythai.net](https://daio.pythai.net) (voting UI).

---

**Last Updated**: 2026-01-14  
**Version**: 1.0.0
