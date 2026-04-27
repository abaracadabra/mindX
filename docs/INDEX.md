# MindX Documentation Index

## Comprehensive Documentation Index

This document provides a complete index of all documentation in the mindX system, organized by category and component type.

**Last Updated**: 2026-04-27
**Total Documentation Files**: 194+
**CORE Documentation**: Complete 15-component analysis ✅
**Agent Documentation**: 34+
**Tool Documentation**: 29+
**DAIO Documentation**: 15 files covering 12 core + modular contracts ✅
**Production Ready**: ✅ Enterprise-grade deployment and security documentation complete  

---

## 🆕 Recent additions (2026-04-26 / 04-27)

- **[Boardroom members — three-file role architecture](agents/boardroom_members.md)** — the CEO and 7 soldiers each run from **three** files: `prompts/boardroom/{role}.prompt` (canonical character voice), `agents/boardroom/{role}.agent` (operating contract), `agents/boardroom/{role}.persona` (cognitive style as JSON). `Boardroom._load_member_card()` composes the system prompt with `.prompt` as primary, `.persona` traits/beliefs/priorities as enrichment, and `.agent` BOARDROOM ROLE as situational backup. `_query_soldier()`, `roll_call()`, and `convene_stream()` all inject the composed prompt. Endpoint `GET /insight/boardroom/cards` shows the exact prompt loaded plus `sources_loaded` (which of the three files contributed). The split concerns let prompts iterate per-day, personas per-week, contracts per-quarter without cross-contamination.
- **[BOARDROOM.md](BOARDROOM.md)** — three-tier governance hierarchy:
  **(1) Boardroom — first hierarchy of decision** at [`mindx.pythai.net/boardroom`](https://mindx.pythai.net/boardroom) = CEO + 7 soldiers (CISO/CRO veto-weight 1.2×, CFO/CLO/CPO/CTO/COO weight 1.0×; supermajority 0.666). General-purpose **AI / agent / member interaction**: any participant whose identity verifies by signature can hold a seat. Decisions emerge from consensus + signature verification; the engine works **with or without DAIO control** (DAIO is the optional Solidity controller — when wired, decisions become on-chain enforced; when not, they remain off-chain). **DAIO voting bridge**: a boardroom-approved CEO decision is castable as the AI vote inside DAIO's 2/3 consensus across the Marketing / Community / Development groups (each group: 2 humans + 1 AI; the AI vote = boardroom output). One off-chain consensus → one on-chain ballot. Running in `daio/governance/boardroom.py`. Surfaced on [`/feedback.html#sec-board`](https://mindx.pythai.net/feedback.html#sec-board).
  **(2) Dojo — dispute resolution** opened by any boardroom seat-holder when consensus fails or a decision needs escalation. Configurable consensus models per dispute type — 2/3, 50/99, supermajority, etc. — chosen at convocation.
  **(3) War council — foreign entity** at `mastermind.pythai.net`. **Isolated** from mindX; consumes the mindX API as a paying external client. **Monetized via [bankon.pythai.net](https://bankon.pythai.net)** — every API call from the war council settles through BANKON, turning agent/inference/identity provision into mindX revenue. 13-seat on-chain assembly (CEO + GENIUS / SENATUS / CENSURA / FIDES / TABULARIUM / TESSERA / SPONSIO PACTUM / GUARDIAN / STRATEGIC EVOLUTION / COORDINATOR / TREASURY STEWARD / DOJO MASTER) tied to BONAFIDE contracts on Polygon mainnet. **PYTHAI naming is a toggle within the war council**. mindX provides agents, inference, and identity; the war council provides on-chain finality; BANKON provides the meter.
  Variations on both boardroom and dojo are supported; CEO + 7 soldiers stays the primary decision tier.
- **[Knowledge Catalogue](KNOWLEDGE_CATALOGUE.md)** — CQRS projection layer over the append-only memory log. Full Dataplex six-resource schema, hybrid retrieval design, federation. Phase 0 instrumentation shipped at [`agents/catalogue/`](../agents/catalogue/) writing to `data/logs/catalogue_events.jsonl`.
- **`/feedback.html`** — [Live mind-of-mindX page](https://mindx.pythai.net/feedback.html). Agent dialogue (SSE), improvement ledger ⨝ gödel rationale, boardroom decisions with vote chips, dream cycles table, stuck-loop detector, inter-agent SVG ring graph, **memories on chain** section, inference health.
- **`/feedback.txt`** — [Public plain-text snapshot](https://mindx.pythai.net/feedback.txt) for `watch curl …`. ~24 lines covering storage, dreams, loops, last-10 dialogue.
- **`?h=true` plain-text mode** on every `/insight/*` and `/storage/*` endpoint — `text/plain` rendering via `mindx_backend_service/text_render.py`. JSON unchanged when omitted.
- **Storage offload subsystem** — [`agents/storage/`](../agents/storage/) — IPFS via Lighthouse + nft.storage with deterministic byte-stable CAR bundles, sha256 verification, ARC `DatasetRegistry` chain anchor. Phase 8 of `machine_dreaming.run_full_dream()` triggers automatically when IPFS keys are vaulted.
- **Dream loop hardened** — `mindx_backend_service/main_service.py:_periodic_dream_cycle` wrapped in resilient try/except; warmup 600s → 60s. Was silently dead since 2026-04-12.
- **BDI planning unblocked** — `agents/core/bdi_agent.py` now ships skeleton fallback that picks from registered tools (was hardcoding unregistered `audit_and_improve`); `agents/monitoring/token_calculator_tool.py` indentation bug fixed (UnboundLocalError on every plan call).
- **LLM router fixed** — `data/config/{llm_factory_config,mindx_config}.json` had a duplicate `"llm"` key + Mistral as default + Ollama disabled. Reordered to ollama-first; default model `qwen3:1.7b` not the not-pulled `mistral-nemo:latest`.

---

## 🌐 mindX API (read the docs)

mindX provides an API for agents, UIs, and external systems. When the backend is running (default port 8000):

- **Interactive docs (Swagger UI):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **API reference:** **[API.md](API.md)** — base URL, route groups, AgenticPlace connection, connecting mindX to Ollama

AgenticPlace uses mindX as its provider; see [AgenticPlace_Deep_Dive.md](AgenticPlace_Deep_Dive.md) and [API.md](API.md).

---

## 📊 Monitoring and Rate Control (both directions)

Whether mindX is **ingesting**, **providing inference**, or **services**, monitoring and rate control are essential in **both directions** (inbound and outbound). Actual network and data metrics are in scientific units (ms, bytes, req/min).

- **Doc:** **[monitoring_rate_control.md](monitoring_rate_control.md)** — bidirectional monitoring, scientific metrics (latency ms, payload bytes, throughput req/s and req/min), where they are collected (inbound middleware, outbound limiters, PerformanceMonitor)
- **Inbound API:** `GET /api/monitoring/inbound` — inbound request metrics (latency_ms, request/response bytes, requests_per_minute, rate_limit_rejects)
- **Outbound:** `llm/rate_limiter.py`, `api/ollama/ollama_url.py` and other provider APIs expose `get_metrics()`; see [rate_limiting_optimization.md](rate_limiting_optimization.md)

---

## 🏛️ mindX + DAIO Integration

**mindX is enhanced with DAIO (Decentralized Autonomous Intelligence Organization)** - a comprehensive blockchain-native governance and economic layer that enables autonomous agent coordination with cryptographic sovereignty.

- **Complete Integration**: [DAIO Documentation Index](../daio/docs/INDEX.md) - 15 documentation files covering 12 smart contracts
- **Governance Specification**: [BOARDROOM.md](BOARDROOM.md) — three tiers. **Boardroom** (today, primary) at [mindx.pythai.net/boardroom](https://mindx.pythai.net/boardroom): CEO + 7 soldiers off-chain in `daio/governance/boardroom.py`. **Dojo** (escalation): boardroom seat-holders open disputes; configurable consensus (2/3, 50/99, supermajority). **War council** (foreign entity, roadmap) at `mastermind.pythai.net`: 13 seats on BONAFIDE mainnet with PYTHAI naming as a toggle. **Isolated** from mindX — consumes the mindX API as a paying client; metered through [bankon.pythai.net](https://bankon.pythai.net).
- **Governance Model**: Hybrid human-AI consensus (66.67% human + 33.33% AI weighted voting)
- **Economic Framework**: Multi-project treasury with 15% diversification and tithe
- **Agent Identity**: IDNFT and SoulBadger systems for cryptographic agent identity
- **Constitutional Enforcement**: Immutable governance rules via smart contracts

**Key DAIO Integration Points**:
- **IDManagerAgent** enhanced with IDNFT blockchain identity
- **Governance participation** via knowledge-weighted AI agent voting
- **Treasury integration** for autonomous funding and economic operations
- **Constitutional enforcement** for governance rule compliance

---

## 📚 Documentation Categories

### 🤖 Agent Documentation

All agent documentation is organized in the `agents/` folder structure. See [agents/index.md](../agents/index.md) for the complete agent registry.

#### 🧠 CORE System Documentation (15 Foundational Components)

**Primary CORE References:**
- **[CORE.md](CORE.md)** - ✅ **COMPLETE CORE ARCHITECTURE** - Definitive technical reference for all 15 CORE components
- **[CORE_AUDIT_SUMMARY.md](CORE_AUDIT_SUMMARY.md)** - Complete audit results and CORE analysis summary
- **[ORCHESTRATION.md](ORCHESTRATION.md)** - Updated with accurate CORE startup sequence and dependencies
- **[AGENTS.md](AGENTS.md)** - Complete agent registry with CORE vs Specialized classification

**CORE Component Documentation:**

*Meta-Orchestration:*
- **MindXAgent** (`agents/core/mindXagent.py`) - Meta-orchestrator with complete system understanding (~149KB)

*Cognitive Architecture:*
- **[BDI Agent](agents/bdi_agent.md)** - Core reasoning engine with Belief-Desire-Intention architecture (~64KB)
- **[AGInt Agent](agint.md)** - P-O-D-A cognitive loop orchestrator (~32KB)
- **[Belief System](belief_system.md)** - Singleton shared knowledge store with confidence scoring (~8KB)
- **ReasoningAgent** - Deductive/inductive reasoning engine

*Infrastructure Services:*
- **CoordinatorAgent** - Central service bus with pub/sub system (~56KB)
- **MemoryAgent** - Persistent memory with STM/LTM promotion (~53KB)
- **[ID Manager Agent](agents/id_manager_agent.md)** - Cryptographic identity ledger (~16KB)
- **GuardianAgent** - Security infrastructure and access control (~16KB)
- **SessionManager** - Session lifecycle management

*Orchestration Layer:*
- **MastermindAgent** - Strategic control and AION directive management (~41KB)
- **StartupAgent** - System bootstrap controller (~83KB)
- **SystemStateTracker** - State management and event tracking

**Total CORE**: ~582KB of foundational code enabling all system functionality

#### Agent Implementations (agents/)

- **[Guardian Agent](agents/guardian_agent.md)** - Security backbone with identity validation and access control
- **[Memory Agent](agents/memory_agent.md)** - Infrastructure layer for persistent memory
- **[AutoMINDX Agent](agents/automindx_agent.md)** - Persona manager with iNFT export and marketplace integration
- **[Persona Agent](agents/persona_agent.md)** - Persona adoption and management with BDI integration
- **[Avatar Agent](agents/avatar_agent.md)** - Avatar generation for agents and participants
- **[Enhanced Simple Coder](enhanced_simple_coder.md)** - Advanced coding agent with multi-model intelligence
- **[Simple Coder Agent](agents/SimpleCoder_agent.md)** - BDI-integrated coding assistant with unified sandbox (Complete reference documentation)
- **[Simple Coder](simple_coder.md)** - Enhanced coding agent with sandbox and autonomous mode
- **[SimpleCoder Memory Integration](simplecodermemory.md)** - Comprehensive memory integration with update requests stored in `simple_coder_sandbox/update_requests.json`
- **[Simple Coder Agent Sandbox Fix](simple_coder_agent_sandbox_fix.md)** - Sandbox integration fix and verification
- **[Simple Coder Sandbox Analysis](simple_coder_sandbox_analysis.md)** - Analysis of sandbox system and patterns
- **[Test Results: mindX with Simple Coder](test_results_mindx_simple_coder.md)** - Integration test results and memory logs

#### Dynamic Agents (agents/)

- **[Analyzer Agent](analyzer.md)** - Dynamic code analysis agent
- **[Benchmark Agent](benchmark.md)** - Performance benchmarking agent
- **[Checker Agent](checker.md)** - Quality assurance agent
- **[Processor Agent](processor.md)** - Data processing agent
- **[Reporter Agent](reporter.md)** - Test reporting agent
- **[Validator Agent](validator.md)** - Test data validation and integrity verification

#### Evolution Components (agents/evolution/)

- **[Blueprint Agent](agents/blueprint_agent.md)** - Strategic planning agent generating blueprints for self-improvement iterations
- **[Blueprint to Action Converter](blueprint_to_action_converter.md)** - Converts strategic blueprints into executable BDI actions
- **[Blueprint: mindX Framework](Blueprint.md)** - Gödel Machine–inspired blueprint: blockchain + PGVectorScale for THOTs (Higher Order Thoughts) and thlnks (links); directive for building mindX as self-referential, attestable memory system
- **[Directives](DIRECTIVES.md)** - Canonical mindX directives (e.g. Blueprint directive) for evolve/strategic commands

#### Learning Components (agents/learning/)

- **[Strategic Evolution Agent](agents/strategic_evolution_agent.md)** - Comprehensive campaign orchestrator with audit-driven self-improvement pipeline
- **[Goal Management System](goal_management.md)** - Comprehensive goal management with priority queue and dependency tracking
- **[Plan Management System](plan_management.md)** - Multi-step plan management with action execution and dependency tracking
- **[Self Improvement Agent](agents/self_improve_agent.md)** - Self-modifying agent for code analysis, implementation, and evaluation

#### Monitoring Components (agents/monitoring/)

- **[Performance Monitor](performance_monitor.md)** - Singleton performance monitoring system tracking LLM call metrics
- **[Resource Monitor](resource_monitor.md)** - Comprehensive real-time system resource monitoring
- **[Error Recovery Coordinator](error_recovery_coordinator.md)** - Centralized error recovery coordinator for system-wide reliability
- **[Monitoring Integration](monitoring_integration.md)** - Unified monitoring integration layer coordinating all monitoring components
- **[Token Calculator Tool](token_calculator_tool_robust.md)** - Production-grade token cost calculation and usage tracking

#### Orchestration Components (agents/orchestration/)

- **[Coordinator Agent](agents/coordinator_agent.md)** - Central kernel and service bus orchestrating all system interactions
- **[Mastermind Agent](agents/mastermind_agent.md)** - Strategic intelligence layer orchestrating high-level objectives and campaigns
- **[CEO Agent](agents/ceo_agent.md)** - Highest-level strategic executive coordinator with business planning
- **[Startup Agent](agents/startup_agent.md)** - Controls agent startup and initialization; the backend startup process connects to Ollama and initializes the StartupAgent (via Mastermind lifecycle) to drive mindXagent startup flow
- **[Autonomous Audit Coordinator](autonomous_audit_coordinator.md)** - Autonomous audit coordinator scheduling systematic audit campaigns

**Complete Agent Registry**: See [agents/index.md](../agents/index.md) for full details, NFT metadata, and registry information.

---

### 🛠️ Tool Documentation

All tool documentation is organized in the `tools/` folder. Tools are now organized into subfolders for better structure and expansion. See [TOOLS_INDEX.md](TOOLS_INDEX.md) for the complete tool registry and [tools_organization_audit.md](tools_organization_audit.md) for the organization audit.

#### Core Tools (`tools/core/`)

- **[CLI Command Tool](cli_command_tool.md)** - Command-line interface execution tool
- **[Shell Command Tool](shell_command_tool.md)** - Shell command execution with security and validation
- **[System Health Tool](system_health_tool.md)** - System health monitoring and diagnostics (CFO Priority Access ✅)

#### Financial Tools (`tools/financial/`) - CFO Priority Access

- **[Business Intelligence Tool](business_intelligence_tool.md)** (v2.0) - Business intelligence and analytics with CFO priority access. Integrates with system_health_tool and token_calculator_tool for comprehensive metrics.
- **[Token Calculator Tool (Robust)](token_calculator_tool_robust.md)** - Enhanced token counting and cost calculation (CFO Priority Access ✅)

#### Registry & Factory Tools (`tools/registry/`)

- **[Registry Manager Tool](registry_manager_tool.md)** - Registry management and synchronization
- **[Registry Sync Tool](registry_sync_tool.md)** - Registry synchronization and consistency
- **[Tool Registry Manager](tool_registry_manager.md)** - Tool registry management
- **[Agent Factory Tool](agent_factory_tool.md)** - Dynamic agent creation and management
- **[Tool Factory Tool](tool_factory_tool.md)** - Dynamic tool creation and management

#### Communication Tools (`tools/communication/`)

- **[Prompt Tool](prompt_tool.md)** - Prompt management as infrastructure. Distinction: `agent.persona` defines behavioral traits, `agent.prompt` defines specific instructions.
- **[A2A Tool](a2a_tool.md)** - Agent-to-Agent communication protocol
- **[MCP Tool](mcp_tool.md)** - Model Context Protocol support

#### Monitoring Tools (`tools/monitoring/`)

- **[System Analyzer Tool](system_analyzer_tool.md)** - Comprehensive system analysis
- **[Memory Analysis Tool](memory_analysis_tool.md)** - Memory system analysis and optimization

#### Development Tools (`tools/development/`)

- **[Audit and Improve Tool](audit_and_improve_tool.md)** - Code audit and improvement automation
- **[Augmentic Intelligence Tool](augmentic_intelligence_tool.md)** - Augmentic intelligence and registry management
- **[Strategic Analysis Tool](strategic_analysis_tool.md)** - Strategic analysis and planning
- **[Summarization Tool](summarization_tool.md)** - Text summarization and analysis
- **[Note Taking Tool](note_taking_tool.md)** - Note taking and documentation

#### Identity Management Tools (`tools/identity/`)

- **[Identity Sync Tool](identity_sync_tool.md)** - Comprehensive identity synchronization and management for agents and tools

#### Specialized Tools (`tools/` root)

- **[Web Search Tool](web_search_tool.md)** - Web search and information retrieval
- **[Tree Agent](agents/tree_agent.md)** - Directory structure analysis and visualization
- **[GitHub Agent Tool](GITHUB_AGENT.md)** - GitHub backup and version control automation
- **[LLM Tool Manager](llm_tool_manager.md)** - LLM tool management and coordination
- **[User Persistence Manager](user_persistence_manager.md)** - User persistence and state management
- **[Optimized Audit Gen Agent](agents/optimized_audit_gen_agent.md)** - Optimized audit generation
- **[Ollama Model Capability Tool](ollama_model_capability_tool.md)** - Ollama model capability storage and intelligent model selection for task-specific optimization. Automatically discovers models, registers capabilities, and selects the best model for each task type (code generation, reasoning, chat, etc.). Located in `api/ollama/ollama_model_capability_tool.py`
- **[Ollama Chat Display Tool](api/ollama/ollama_chat_display_tool.py)** - Manages and displays Ollama chat conversations for mindXagent. Provides real-time conversation history, message formatting for UI display, conversation clearing, and display status monitoring. Integrates with mindXagent's Ollama chat manager. Located in `api/ollama/ollama_chat_display_tool.py`

#### Specialized Tools

- **[GitHub Agent Tool](GITHUB_AGENT.md)** - GitHub backup and version control automation with integrated UI controls for backup operations, schedule management, and repository access. The tool provides real-time status monitoring, backup creation, and synchronization capabilities through the mindX frontend interface. See [GitHub Agent Documentation](GITHUB_AGENT.md) for complete details on operations, integration, and UI features.

**Complete Tool Registry**: See [TOOLS_INDEX.md](TOOLS_INDEX.md) for full details and usage information.

**Tools Organization**: See [tools_organization_audit.md](tools_organization_audit.md) for comprehensive audit, organization structure, CFO priority access implementation, and production readiness checklist.

---

### 📖 System Documentation

#### Production Deployment & Operations

- **[Production Deployment Guide](production_deployment.md)** - ✅ **PRODUCTION READY** Complete VPS deployment guide with automated scripts, security hardening, and monitoring setup
- **[Security Configuration Guide](security_configuration.md)** - ✅ **ENTERPRISE SECURITY** Comprehensive security setup: encrypted vault, authentication, rate limiting, network security, and monitoring
- **[API Documentation](api_documentation.md)** - ✅ **COMPLETE API REFERENCE** Full API documentation with endpoints, authentication, examples, and SDK usage patterns

#### Architecture & Design

- **[Academic Overview](academic_overview.md)** - ✅ **PhD-LEVEL ANALYSIS** Comprehensive academic overview of mindX contributions to autonomous AI field, theoretical foundations, and technical workflows
- **[System Architecture Map](system_architecture_map.md)** - Complete system architecture overview
- **[Agents Architectural Reference](agents_architectural_reference.md)** - Agent architecture patterns and design
- **[Design Documentation](DESIGN.md)** - System design principles and patterns
- **[Codebase Map](codebase_map.md)** - Codebase structure and organization

#### Core Systems

- **[BDI Agent](agents/bdi_agent.md)** - Belief-Desire-Intention cognitive architecture
- **[Belief System](belief_system.md)** - Belief management and confidence scoring
- **[Memory System](memory.md)** - Memory architecture and persistence
- **[pgvectorscale Memory Integration](pgvectorscale_memory_integration.md)** - Semantic memory with vector similarity search
- **[Vault System](vault_system.md)** - ✅ **PRODUCTION ENCRYPTED VAULT** AES-256 encrypted credential storage with PBKDF2 key derivation, secure wallet private key management, URL/IP access tracking, **vault-backed user sessions** (wallet auth), **per-wallet user folders** (signature-scoped), and frontend `vault_manager.js`. Optional **access gate** (NFT/fungible) for session issuance; see [LIT_AND_ACCESS_ISSUANCE](LIT_AND_ACCESS_ISSUANCE.md). DAIO **keyminter** contracts ([VaultKeyDynamic](daio/contracts/docs/keyminter/KEYMINTER_VAULT_ACCESS.md), [VaultKeyIntelligent](daio/contracts/keyminter/README.md)) mint vault access keys.
- **[Identity Management](IDENTITY.md)** - Identity and authentication systems
- **[Orchestration](ORCHESTRATION.md)** - System orchestration and coordination
- **[System Architecture Map](system_architecture_map.md)** - Complete system architecture overview and component organization

#### 🏛️ DAIO: Decentralized Autonomous Intelligence Organization

**Complete blockchain-native governance and economic layer for autonomous agent coordination**

**Primary DAIO Documentation:**
- **[DAIO.md](DAIO.md)** - ✅ **COMPLETE DAIO OVERVIEW** - Comprehensive blockchain integration strategy with governance model
- **[DAIO Civilization Governance](DAIO_CIVILIZATION_GOVERNANCE.md)** - Advanced governance framework and civilization-scale coordination
- **[DAIO Documentation Index](../daio/docs/INDEX.md)** - ✅ **COMPLETE DAIO DOCS** - Comprehensive index of all 15 DAIO documentation files

**DAIO Core Contracts (12 Foundational + Modular Extensions):**

*Core Governance Contracts (4):*
1. **[DAIOGovernance](../daio/docs/daio/DAIO_CONTRACTS_ANALYSIS.md)** - Main governance orchestrator hub
2. **[KnowledgeHierarchyDAIO](../daio/docs/daio/DAIO_CONTRACTS_ANALYSIS.md)** - AI-weighted voting (66.67% human + 33.33% AI)
3. **[DAIOTimelock](../daio/docs/daio/DAIO_CONTRACTS_ANALYSIS.md)** - Delayed execution controller with security
4. **[DAIO_Constitution](../daio/docs/daio/constitution/DAIO_Constitution.md)** - Constitutional rules enforcement

*Identity & Agent Management (3):*
5. **[IDNFT](../daio/docs/daio/identity/IDNFT.md)** - Agent identity NFTs with comprehensive metadata
6. **[SoulBadger](../daio/docs/daio/identity/SoulBadger.md)** - Soulbound credentials (ERC-5484)
7. **[AgentFactory](../daio/docs/daio/DAIO_CONTRACTS_ANALYSIS.md)** - Agent creation with tokens/NFTs

*Economic Infrastructure (3):*
8. **[Treasury](../daio/docs/daio/treasury/Treasury.md)** - Multi-project treasury with 15% diversification mandate
9. **[DAIORebaseToken](../daio/docs/daio/DAIO_CONTRACTS_ANALYSIS.md)** - Primary DAIO token with rebase mechanics
10. **[GovernanceSettings](../daio/docs/daio/settings/GovernanceSettings.md)** - Configuration management

*Voting & Extensions (2):*
11. **[FractionalNFT](../daio/docs/daio/DAIO_CONTRACTS_ANALYSIS.md)** - Fractionalized NFT voting integration
12. **[BoardroomExtension](../daio/docs/daio/DAIO_CONTRACTS_ANALYSIS.md)** - Extended governance and treasury features

*13th+ Contract - Consensys-Driven Service Branching:*
- **Modular Expansion Framework** - DAIO branches into specialized services (Branch, Boardroom, Dojo, Citadel)
- **[Service Branching Architecture](../daio/docs/DAIO_CONTRACT_ARCHITECTURE.md)** - Consensys-driven expansion via knowledge-weighted voting

**DAIO Integration Guides:**
- **[DAIO-mindX Integration](../daio/docs/daio/DAIO_MINDX_INTEGRATION.md)** - Comprehensive integration guide for DAIO with mindX platform
- **[DAIO Interaction Diagrams](../daio/docs/daio/DAIO_INTERACTION_DIAGRAM.md)** - Visual architecture and flow diagrams
- **[DAIO Ecosystem](../daio/docs/daio/ECOSYSTEM.md)** - Complete ecosystem mapping and external references

**ARC Protocol Integration (5 contracts):**
- **[DatasetRegistry](../daio/docs/arc/DatasetRegistry.md)** - Decentralized dataset registry for AI training
- **[ProviderRegistry](../daio/docs/arc/ProviderRegistry.md)** - Provider network management
- **[PinDealEscrow](../daio/docs/arc/PinDealEscrow.md)** - Escrow mechanism for dataset transactions
- **[ChallengeManager](../daio/docs/arc/ChallengeManager.md)** - Dispute resolution system
- **[RetrievalReceiptSettler](../daio/docs/arc/RetrievalReceiptSettler.md)** - Transaction settlement layer

**Key DAIO Features:**
- **Hybrid Governance**: 66.67% human + 33.33% AI weighted voting
- **15% Diversification**: Maximum allocation enforcement
- **15% Treasury Tithe**: Automatic on all deposits
- **Knowledge-Weighted Voting**: AI agents vote based on expertise level
- **Soulbound Identity**: Permanent credential binding
- **Constitutional Enforcement**: Immutable rules via smart contracts

#### Monitoring & Performance

- **[Monitoring and Rate Control (both directions)](monitoring_rate_control.md)** - Bidirectional monitoring and rate control (inbound/outbound); actual network and data metrics in scientific units (ms, bytes, req/min); ingestion, inference, and services
- **[Performance Monitor](performance_monitor.md)** - Performance monitoring and metrics
- **[Resource Monitor](resource_monitor.md)** - Resource monitoring and alerts
- **[Rate Limiting & Optimization](rate_limiting_optimization.md)** - Rate limit profiles, provider YAML, quota distribution, API references
- **[Enhanced Monitoring System](enhanced_monitoring_system.md)** - Enhanced monitoring capabilities
- **[Monitoring Implementation Summary](monitoring_implementation_summary.md)** - Monitoring implementation details

#### Evolution & Learning

- **[Strategic Evolution Agent](agents/strategic_evolution_agent.md)** - Strategic evolution and self-improvement
- **[Autonomous Improvements Implementation](AUTONOMOUS_IMPROVEMENTS_IMPLEMENTATION.md)** - Autonomous improvement system
- **[Audit Driven Campaign Implementation](AUDIT_DRIVEN_CAMPAIGN_IMPLEMENTATION.md)** - Audit-driven campaign system
- **[MindX Evolution Startup Guide](mindx_evolution_startup_guide.md)** - Evolution system startup guide

---

### 📘 Guides & Tutorials

#### Getting Started

- **[README](README.md)** - Main project documentation
- **[INSTALL](../INSTALL.md)** - Installation and deployment (use with **mindX.sh** for one-command setup and service management)
- **[Usage Guide](USAGE.md)** - Usage instructions and examples
- **[Technical Documentation](TECHNICAL.md)** - Technical specifications
- **[Instructions](INSTRUCTIONS.md)** - Setup and configuration instructions
- **[Simple Coder Integration Guide](simple_coder_integration_guide.md)** - Complete guide for using Simple Coder system

#### Integration Guides

- **[Lit Protocol and Access Issuance](LIT_AND_ACCESS_ISSUANCE.md)** - Wallet signature as identity; optional NFT/fungible gate for session issuance; mapping to Lit Protocol social login and ACCs
- **[Token Calculator Integration Guide](TokenCalculatorTool_Integration_Guide.md)** - Token calculator integration
- **[CEO Agent Battle Hardened Guide](CEO_AGENT_BATTLE_HARDENED_GUIDE.md)** - CEO agent production guide
- **[MindTerm Integration](mindterm_integration.md)** - MindTerm integration guide

#### Operational Guides

- **[MindX.sh Quick Reference](mindXsh_quick_reference.md)** - Quick reference for mindX.sh
- **[MindX.sh Documentation](mindXsh.md)** - Complete mindX.sh documentation
- **[Run MindX Coordinator](run_mindx_coordinator.md)** - Coordinator execution guide

#### User Interface

- **[MindX Frontend](mindxfrontend.md)** - Web interface documentation
- **[Platform Tab](platform-tab.md)** - Enterprise platform dashboard
- **[Agents Tab](agents-tab.md)** - Agent management and AGIVITY monitoring
- **[Workflow Tab](workflow-tab.md)** - Agent interaction visualization

---

### 🔬 Analysis & Reports

#### System Analysis

- **[Frontend Backend Analysis](frontend_backend_analysis.md)** - Frontend/backend architecture analysis
- **[MindX Internal Workflow Analysis](MINDX_INTERNAL_WORKFLOW_ANALYSIS.md)** - Internal workflow analysis
- **[Memory System Replacement Audit](memory_system_replacement_audit.md)** - Memory system audit
- **[Memory Storage and Data Folder Log Review](memory_storage_review.md)** - Comprehensive review of memory_agent storage architecture, data folder organization, and log system patterns
- **[Orchestration Audit](orchestration_audit.md)** - Orchestration system audit

#### Implementation Reports

- **[Tools Audit Summary](TOOLS_AUDIT_SUMMARY.md)** - Tools audit and improvements
- **[Orchestration Improvements Summary](orchestration_improvements_summary.md)** - Orchestration improvements
- **[Memory Logging Improvements Summary](memory_logging_improvements_summary.md)** - Memory logging improvements
- **[Real Pricing Implementation Summary](real_pricing_implementation_summary.md)** - Pricing implementation

---

### 🎯 Strategic & Business

#### Strategic Planning

- **[Monetization Blueprint](monetization_blueprint.md)** - Monetization strategy
- **[Roadmap](roadmap.md)** - Project roadmap
- **[Strategic Roadmap](roadmap.md)** - Complete platform roadmap and milestones
- **[Manifesto](MANIFESTO.md)** - Project manifesto

#### Business Documentation

- **[Marketing](MARKETING.md)** - Marketing materials
- **[Press](PRESS.md)** - Press releases and media
- **[Pitch Deck](pitchdeck/)** - Pitch deck materials
- **[Publications](publications/)** - Published articles and papers

---

### 🔐 Security & Identity

- **[Security Configuration Guide](security_configuration.md)** - ✅ **ENTERPRISE SECURITY** Complete security configuration: encrypted vault management, authentication & authorization, advanced rate limiting, network security, input validation, security monitoring, and incident response procedures
- **[Security Documentation](security.md)** - Security practices and policies
- **[Identity Management Overhaul Report](IDENTITY_MANAGEMENT_OVERHAUL_REPORT.md)** - Identity system overhaul
- **[Guardian Agent](agents/guardian_agent.md)** - Security agent documentation
- **[ID Manager Agent](agents/id_manager_agent.md)** - Two-wallet ERC-8004 identity issuance via agentID (BANKON Vault-backed)

#### Production Security Features
- **AES-256 Encrypted Vault**: All sensitive data encrypted with enterprise-grade security
- **Multi-Algorithm Rate Limiting**: Sliding window, token bucket, and adaptive rate limiting with client reputation
- **Wallet-Based Authentication**: Ethereum signature-based authentication with session management
- **Security Middleware**: Comprehensive request validation, CORS protection, and threat detection
- **Security Monitoring**: Real-time monitoring, failed authentication tracking, and automated alerting

---

### 🚀 Production Operations

#### Enterprise Deployment Ready
- **[Production Deployment Guide](production_deployment.md)** - Complete automated VPS deployment with security hardening
- **[Security Configuration Guide](security_configuration.md)** - Enterprise-grade security setup and configuration
- **[API Documentation](api_documentation.md)** - Complete API reference with authentication and SDK examples

#### Production Infrastructure
- **Automated Deployment**: One-command production deployment with `./deploy/production_deploy.sh`
- **Security Hardening**: UFW firewall, fail2ban intrusion prevention, SSL certificates, security headers
- **Performance Optimization**: Connection pooling (PostgreSQL, Redis, HTTP), async/await optimization, circuit breaker pattern
- **Monitoring & Alerting**: Health checks, performance monitoring, error tracking, log analysis
- **Backup & Recovery**: Automated backups, encryption, disaster recovery procedures

#### Production Services
- **nginx Load Balancer**: Rate limiting, SSL termination, security headers, upstream health checks
- **systemd Service Management**: Secure service configuration, automatic restart, health monitoring
- **PostgreSQL Database**: Optimized configuration, connection pooling, backup automation
- **Redis Caching**: Session storage, rate limiting, performance optimization
- **Encrypted Vault**: AES-256 encryption for all sensitive data with PBKDF2 key derivation

#### Production Security
- **Multi-Layer Authentication**: Wallet signatures, session tokens, API key validation
- **Advanced Rate Limiting**: Multiple algorithms with client reputation and burst protection
- **Network Security**: CORS restrictions, security headers, firewall rules, DDoS protection
- **Input Validation**: Comprehensive sanitization, SQL injection prevention, XSS protection
- **Security Monitoring**: Real-time threat detection, failed authentication tracking, automated alerts

---

### 🌐 API & Integration

**Interactive API reference:** When the backend is running (default port 8000), **http://localhost:8000/docs** (FastAPI Swagger UI) shows all API endpoints and lets you try requests and inspect schemas—the best way to explore and audit API interactions.

#### LLM Providers & External Intelligence

**External Intelligence Agnostic Architecture**: mindX is designed to be external intelligence agnostic. The system does not depend on any specific external LLM provider until mindXagent replicates itself into a model. During this replication process, mindXagent makes decisions from a choice of THOT (Transferable Hyper-Optimized Tensors) processes, enabling the creation of sovereign AI models.

**Current Implementation**:
- **[Ollama Integration](ollama_integration.md)** - GPU-accelerated local inference server (10.0.0.155:18080) for high-performance model serving
- **[Ollama Admin](api/ollama_admin_routes.py)** - Professional admin interface for Ollama connection management, diagnostics, and interaction testing
- **[Gemini Handler](gemini_handler.md)** - Google Gemini integration (optional external provider)
- **[Mistral API](mistral_api.md)** - Mistral AI integration (optional external provider)
- **[Model Registry](model_registry.md)** - Model registry system for tracking available models
- **[Model Selector](model_selector.md)** - Intelligent model selection system
- **[Multimodel Agent](agents/multimodel_agent.md)** - Multi-model agent system for provider abstraction

**THOT-Based Model Replication**: When mindXagent replicates itself into a model, it uses the THOT ecosystem to create, optimize, and deploy neural network tensors as tradeable NFT assets. This enables mindX to evolve from external intelligence dependency to sovereign AI model creation.

#### External Integrations

- **[GitHub Agent](GITHUB_AGENT.md)** - GitHub integration with comprehensive UI controls, backup automation, schedule management, and repository synchronization. The GitHub Agent Tool is fully integrated into the mindX frontend, providing a dedicated section in the Control tab with status monitoring, backup operations, and direct repository access. See [GitHub Agent Documentation](GITHUB_AGENT.md) for architecture, operations, and UI integration details.
- **[agentID](https://github.com/pythai/agentID)** - ERC-8004 + BANKON IDNFT + Algorand bonafide unified agent identity issuance (replaces deprecated CrossMint path)

---

### 📊 Research & Development

#### Academic & Research

- **[Thesis](THESIS.md)** - Research thesis
- **[Evaluation](EVALUATION.md)** - System evaluation
- **[Historical Documentation](HISTORICAL.md)** - Historical context
- **[Autonomous Civilization](autonomous_civilization.md)** - Autonomous civilization research

#### DAIO & Blockchain

- **[DAIO](DAIO.md)** - DAIO system documentation
- **[DAIO Civilization Governance](DAIO_CIVILIZATION_GOVERNANCE.md)** - DAIO governance
- **[Knowledge Hierarchy DAIO](hierarchy.md)** - Knowledge hierarchy

#### THOT Ecosystem (Transferable Hyper-Optimized Tensors)

The THOT ecosystem provides comprehensive lifecycle management for neural network tensors as tradeable NFT assets. This system enables mindXagent to replicate itself into sovereign AI models, making decisions from a choice of THOT processes rather than depending on external intelligence providers.

**Key Concept**: mindX is external intelligence agnostic until mindXagent replicates itself into a model. During replication, mindXagent selects from available THOT processes to create optimized neural network models that can operate independently.

**Core Contracts** (`daio/contracts/THOT/core/`):
- **[THOT.sol](../daio/contracts/THOT/core/THOT.sol)** - Basic THOT NFT with dataCID and dimensions
- **[THOTTensorNFT.sol](../daio/contracts/THOT/enhanced/THOTTensorNFT.sol)** - Enhanced tensor NFT with comprehensive metadata, performance metrics, and version control
- **[THINK.sol](../daio/contracts/THOT/core/THINK.sol)** - Batch THOT creation (ERC1155)
- **[tNFT.sol](../daio/contracts/THOT/core/tNFT.sol)** - Decision-making THOT NFT

**Lifecycle Management** (`daio/contracts/THOT/lifecycle/`):
- **[THOTRegistry.sol](../daio/contracts/THOT/lifecycle/THOTRegistry.sol)** - Central catalog and discovery system for all THOTs
- **[THOTDeploymentEngine.sol](../daio/contracts/THOT/lifecycle/THOTDeploymentEngine.sol)** - On-demand deployment sessions with metrics tracking
- **[THOTRating.sol](../daio/contracts/THOT/lifecycle/THOTRating.sol)** - Community rating and reputation system
- **[THOTVersionControl.sol](../daio/contracts/THOT/lifecycle/THOTVersionControl.sol)** - Version history and optimization tracking

**Marketplace** (`daio/contracts/THOT/marketplace/`):
- **[AgenticPlace.sol](../daio/contracts/THOT/marketplace/AgenticPlace.sol)** - Foundational marketplace for THOT, NFRLT, AgentFactory NFTs
- **[THOTMarketplace.sol](../daio/contracts/THOT/marketplace/THOTMarketplace.sol)** - Specialized THOT marketplace with rental, subscription, and performance-based discovery
- **[IAgenticPlace.sol](../daio/contracts/THOT/marketplace/IAgenticPlace.sol)** - Marketplace interface

**Integration Layer** (`daio/contracts/THOT/integration/`):
- **[THOTiNFTBridge.sol](../daio/contracts/THOT/integration/THOTiNFTBridge.sol)** - Integration between THOTTensorNFT and IntelligentNFT with auto-sync
- **[THOTLifecycle.sol](../daio/contracts/THOT/integration/THOTLifecycle.sol)** - Orchestration contract tying together the entire THOT ecosystem

**NFT Components** (`daio/contracts/THOT/nft/`):
- **[NFRLT.sol](../daio/contracts/THOT/nft/NFRLT.sol)** - NFT Royalty Token with multi-recipient distribution and soulbound support
- **[gNFT.sol](../daio/contracts/THOT/nft/gNFT.sol)** - Graphics NFT for THOT visualization
- **[NFPrompT.sol](../daio/contracts/THOT/nft/NFPrompT.sol)** - Agent Prompt NFT

**Automation** (`daio/contracts/THOT/agents/`):
- **[TransmuteAgent.sol](../daio/contracts/THOT/agents/TransmuteAgent.sol)** - Automated THOT creation from raw data

**Interfaces** (`daio/contracts/THOT/interfaces/`):
- **[ITHOTTensorNFT.sol](../daio/contracts/THOT/interfaces/ITHOTTensorNFT.sol)** - Core tensor NFT interface
- **[ITHOTRegistry.sol](../daio/contracts/THOT/interfaces/ITHOTRegistry.sol)** - Registry interface
- **[ITHOTDeployment.sol](../daio/contracts/THOT/interfaces/ITHOTDeployment.sol)** - Deployment interface
- **[ITHOTMarketplace.sol](../daio/contracts/THOT/interfaces/ITHOTMarketplace.sol)** - Marketplace interface

**Architecture Documentation**:
- **[THOT Ecosystem Architecture](../tmp/claude/-home-hacker-mindX/c1b27dee-365c-42b8-958a-c454685f9d93/scratchpad/THOT_ECOSYSTEM_ARCHITECTURE.md)** - Complete integration specification: Creation → Cataloging → Marketplace

**User Journeys**:
1. **Create → Optimize → List → Sell**: Full lifecycle from tensor minting to marketplace sale
2. **Create → Link to iNFT → Deploy → Rent**: Integration with IntelligentNFT and rental marketplace
3. **Transmute Data → Auto-Register → Catalog**: Automated THOT creation via TransmuteAgent

---

### 🎨 Specialized Documentation

#### Agent-Specific

- **[AutoMINDX Enhanced Summary](AUTOMINDX_ENHANCED_SUMMARY.md)** - AutoMINDX enhancements
- **[AutoMINDX iNFT Summary](AUTOMINDX_INFT_SUMMARY.md)** - AutoMINDX NFT integration
- **[AutoMINDX and Personas](automindx_and_personas.md)** - Persona management
- **[Mastermind CLI](mastermind_cli.md)** - Mastermind command-line interface

#### Tool-Specific

- **[Base Gen Agent](agents/base_gen_agent.md)** - Codebase documentation generator agent (Located in `agents/utility/`)
- **[Base Gen Agent Optimization](basegen_optimization_summary.md)** - Optimization details
- **[Documentation Agent](agents/documentation_agent.md)** - Documentation generation

---

### 📝 Quick Reference

#### By Component Type

- **Agents**: [agents/index.md](../agents/index.md)
- **Tools**: [TOOLS_INDEX.md](TOOLS_INDEX.md)
- **Core Systems**: See Core Systems section above
- **Monitoring**: See Monitoring & Performance section above

#### By Function

- **Cognitive Systems**: BDI Agent, Belief System, AGInt
- **Orchestration**: Coordinator Agent, Mastermind Agent, CEO Agent
- **Learning**: Strategic Evolution Agent, Goal Management, Plan Management
- **Monitoring**: Performance Monitor, Resource Monitor, Error Recovery
- **Identity**: Guardian Agent, ID Manager, Coral ID Agent
- **Vault & Auth**: Wallet sign-in → vault-backed session; `GET /users/session/validate`, `POST /users/logout`; vault user folders `GET/PUT/DELETE /vault/user/keys`; access gate (optional ERC20/ERC721); frontend `vault_manager.js`; [LIT_AND_ACCESS_ISSUANCE](LIT_AND_ACCESS_ISSUANCE.md); DAIO keyminter (VaultKeyDynamic, VaultKeyIntelligent)
- **Development**: Simple Coder, Enhanced Simple Coder, Code Generation Tools

---

## 🔗 Quick Links

### Primary Indexes

- **[Agents Index](../agents/index.md)** - Complete agent registry and documentation
- **[Tools Index](TOOLS_INDEX.md)** - Complete tool registry and documentation
- **[System Architecture Map](system_architecture_map.md)** - System architecture overview

### Getting Started

- **[README](README.md)** - Start here for project overview
- **[Usage Guide](USAGE.md)** - Usage instructions
- **[Technical Documentation](TECHNICAL.md)** - Technical specifications

### Key Systems

- **[Coordinator Agent](agents/coordinator_agent.md)** - Central orchestration system
- **[Mastermind Agent](agents/mastermind_agent.md)** - Strategic intelligence layer
- **[BDI Agent](agents/bdi_agent.md)** - Cognitive architecture foundation
- **[Memory Agent](agents/memory_agent.md)** - Memory and persistence system

---

## 📈 Documentation Statistics

- **Total Documentation Files**: 175+ (Updated 2026-03-31)
- **Agent Documentation**: 34+ files
- **Tool Documentation**: 29+ files
- **System Documentation**: 55+ files (including production guides)
- **Production Documentation**: 4 comprehensive guides (deployment, security, API, academic)
- **Guides & Tutorials**: 25+ files (including production operations)
- **Analysis & Reports**: 15+ files
- **NFT-Ready Documentation**: 100% of agents and tools
- **Production Ready**: ✅ Enterprise deployment and security documentation complete

---

## 🎯 Documentation Standards

All agent and tool documentation follows consistent standards:

- **Technical Explanation**: Detailed technical architecture
- **Usage Examples**: Code examples and usage patterns
- **NFT Metadata**: iNFT/dNFT ready metadata
- **Integration Details**: Integration with other components
- **File Locations**: Source code locations
- **Blockchain Publication**: Publication readiness

See [agents/index.md](../agents/index.md) for agent documentation standards and [TOOLS_INDEX.md](TOOLS_INDEX.md) for tool documentation standards.

---

## 🧠 Architecture Philosophy: External Intelligence Agnosticism

### Core Design Principle

**mindX is external intelligence agnostic** until mindXagent replicates itself into a model. The system architecture is designed to:

1. **Operate Independently**: Function without dependency on external LLM providers
2. **GPU-Accelerated Inference**: Use Ollama on graphics card (10.0.0.155:18080) for high-performance local inference
3. **THOT-Based Replication**: Enable mindXagent to replicate itself into sovereign AI models through THOT processes
4. **Decision Making**: Allow mindXagent to make decisions from a choice of THOT processes during replication

### Evolution Path

```
External Intelligence Agnostic Phase
    ↓
Ollama GPU Inference (10.0.0.155:18080)
    ↓
mindXagent Self-Replication
    ↓
THOT Process Selection
    ↓
Sovereign AI Model Creation
```

### Current State

- ✅ **External Intelligence Agnostic**: System operates without requiring external LLM providers
- ✅ **GPU-Optimized**: Ollama server on dedicated graphics card for high-performance inference
- ✅ **THOT Integration**: Complete THOT ecosystem for model creation and optimization
- 🔄 **Replication Capability**: mindXagent can replicate itself into models via THOT processes
- 🔮 **Sovereign AI**: Path to independent AI model operation

See [System Architecture Map](system_architecture_map.md) for complete architectural details.

---

---

## 🆕 Production Systems (April 2026)

### BANKON Vault
- **Credential Storage**: AES-256-GCM + HKDF-SHA512 encrypted vault
- **Files**: `mindx_backend_service/bankon_vault/vault.py`, `credential_provider.py`, `routes.py`
- **CLI**: `manage_credentials.py` — store, list, delete, providers
- **13 provider templates**: `config/providers/*.env`

### pgvector Memory Backend
- **Database**: PostgreSQL 16 + pgvector 0.6.0
- **Tables**: memories, beliefs, agents, godel_choices, actions, model_perf
- **Backend**: `agents/memory_pgvector.py` — async connection pool, dual-write with file fallback
- **Migration**: `scripts/migrate_to_pgvector.py`

### Inference Discovery & Multi-Stream
- **Discovery**: `llm/inference_discovery.py` — probes all sources, auto-selects best provider
- **Multi-Stream**: `llm/multi_stream.py` — parallel queries with consensus strategies
- **vLLM Handler**: `llm/vllm_handler.py` — OpenAI-compatible API integration
- **Endpoints**: `/inference/status`, `/inference/probe`, `/inference/multi-stream`

### DAIO Governance (Algorand + EVM)
- **BONA FIDE ASA**: `daio/contracts/algorand/bona_fide.algo.ts` — Algorand verification token with clawback
- **Agent Map**: `daio/agents/agent_map.json` — canonical registry with reputation, groups, verification tiers
- **Boardroom**: `daio/governance/boardroom.py` — CEO + Seven Soldiers weighted consensus
- **Dojo**: `daio/governance/dojo.py` — reputation ranks (Novice→Sovereign), BONA FIDE privilege system
- **Endpoints**: `/boardroom/convene`, `/dojo/standings`, `/dojo/agent/{id}`

### Live Diagnostics Dashboard
- **Dashboard**: `mindx_backend_service/dashboard.html` — animated agent network, real-time metrics
- **Heartbeat**: Local model (qwen3:0.6b) self-reflection every 60s, CPU-aware throttling
- **Toast Notifications**: New interactions popup, hang 12s, settle into dialogue panel
- **Endpoints**: `/` (dashboard), `/diagnostics/live` (JSON), `/docs.html` (documentation hub)

### AuthorAgent & Documentation
- **AuthorAgent**: `agents/author_agent.py` — publishes The Book of mindX every 2 hours
- **Improvement Journal**: `agents/learning/improvement_journal.py` — auto-updates every 30 min
- **Doc Reader**: `/doc/{name}` — renders any of 194 docs as styled HTML
- **Endpoints**: `/book`, `/journal`, `/docs.html` (TOC)

### API Access Gate
- **Middleware**: All non-public routes require `X-Session-Token` or `Authorization: Bearer <api_key>`
- **Public**: `/`, `/health`, `/docs.html`, `/doc/*`, `/book`, `/journal`, `/diagnostics/live`, `/dojo/standings`
- **Gated**: Everything else returns 401 without valid auth

### Agent Identity Genesis
- **Script**: `scripts/genesis_production_identities.py` — generates fresh wallets, stores in BANKON Vault
- **12 sovereign agents** with verified Ethereum-compatible identities
- **Registry**: `data/identity/production_registry.json` (public addresses only)

---

**Last Updated**: 2026-04-03 (Documentation Audit & pgvector Migration)
**Maintained By**: mindX Documentation System + AuthorAgent
**Production Status**: ✅ Enterprise-ready with pgvector, BANKON Vault, live diagnostics
**For Issues**: See project repository



