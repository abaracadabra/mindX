# MindX Agents Index

## Comprehensive Agent Documentation and Registry

This document provides a complete index of all agents in the mindX system, with links to detailed documentation, NFT metadata, and registry information.

**Last Updated**: 2026-04-10  
**Total Agents**: 66+  
**Core Components**: 4  
**Evolution Components**: 2  
**Learning Components**: 4  
**Monitoring Components**: 5  
**Orchestration Components**: 7  
**Specialized Agents**: 20+  
**Blockchain/Solidity Agents**: 2  
**Agent Schema**: agents/agent.schema.json (A2A 2.0, MCP 1.0)

---

## 📚 Agent Documentation Status

### ✅ Fully Documented Agents

#### Core Components (agents/core/)

1. **[BDI Agent](core/bdi_agent.py)** - Foundational cognitive architecture implementing Belief-Desire-Intention model
   - **Type**: `cognitive_agent`
   - **Complexity**: 0.98
   - **Location**: `agents/core/bdi_agent.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

2. **[Belief System](core/belief_system.py)** - Singleton belief management system with confidence scores
   - **Type**: `belief_system`
   - **Complexity**: 0.85
   - **Location**: `agents/core/belief_system.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

3. **[ID Manager Agent](core/id_manager_agent.py)** - Central secure ledger for cryptographic identity management
   - **Type**: `identity_manager`
   - **Complexity**: 0.90
   - **Location**: `agents/core/id_manager_agent.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

4. **[AGInt Agent](core/agint.py)** - High-level cognitive orchestrator with P-O-D-A loop
   - **Type**: `cognitive_orchestrator`
   - **Complexity**: 0.95
   - **Location**: `agents/core/agint.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

#### Agent Implementations (agents/)

5. **[Guardian Agent](guardian_agent.py)** - Security backbone with identity validation and access control
   - **Type**: `security_agent`
   - **Complexity**: 0.95
   - **Location**: `agents/guardian_agent.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

6. **[Memory Agent](memory_agent.py)** - Infrastructure layer for persistent memory
   - **Type**: `memory_agent`
   - **Complexity**: 0.92
   - **Location**: `agents/memory_agent.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

7. **[AutoMINDX Agent](automindx_agent.py)** - Persona manager with iNFT export and marketplace integration
   - **Type**: `persona_manager`
   - **Complexity**: 0.95
   - **Location**: `agents/automindx_agent.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

8. **[Persona Agent](persona_agent.py)** - Persona adoption and management with BDI integration
   - **Type**: `persona_manager`
   - **Complexity**: 0.88
   - **Location**: `agents/persona_agent.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

9. **[Avatar Agent](avatar_agent.py)** - Avatar generation for agents and participants
   - **Type**: `avatar_generator`
   - **Complexity**: 0.85
   - **Location**: `agents/avatar_agent.py`
   - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

10. **[Enhanced Simple Coder](enhanced_simple_coder.py)** - Advanced coding agent with multi-model intelligence
    - **Type**: `coding_tool`
    - **Complexity**: 0.90
    - **Location**: `agents/enhanced_simple_coder.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

12. **[Simple Coder Agent](simple_coder_agent.py)** - BDI-integrated coding assistant
    - **Type**: `coding_tool`
    - **Complexity**: 0.88
    - **Location**: `agents/simple_coder_agent.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

13. **[Simple Coder](simple_coder.py)** - Enhanced coding agent with sandbox and autonomous mode
    - **Type**: `coding_agent`
    - **Complexity**: 0.82
    - **Location**: `agents/simple_coder.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

#### Dynamic Agents (agents/)

14. **[Analyzer Agent](analyzer.py)** - Code analysis and quality improvement
    - **Type**: `code_analyzer`
    - **Complexity**: 0.60
    - **Location**: `agents/analyzer.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

15. **[Benchmark Agent](benchmark.py)** - Performance benchmarking and analysis
    - **Type**: `benchmark_tool`
    - **Complexity**: 0.70
    - **Location**: `agents/benchmark.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

16. **[Checker Agent](checker.py)** - Quality assurance and validation
    - **Type**: `quality_checker`
    - **Complexity**: 0.65
    - **Location**: `agents/checker.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

17. **[Processor Agent](processor.py)** - Data processing and transformation
    - **Type**: `data_processor`
    - **Complexity**: 0.75
    - **Location**: `agents/processor.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

18. **[Reporter Agent](reporter.py)** - Test reporting and documentation generation
    - **Type**: `test_reporter`
    - **Complexity**: 0.70
    - **Location**: `agents/reporter.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

19. **[Validator Agent](validator.py)** - Test data validation and integrity verification
    - **Type**: `test_validator`
    - **Complexity**: 0.68
    - **Location**: `agents/validator.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

#### Evolution Components (agents/evolution/)

20. **[Blueprint Agent](evolution/blueprint_agent.py)** - Strategic planning agent generating blueprints for self-improvement iterations
    - **Type**: `strategic_planner`
    - **Complexity**: 0.92
    - **Location**: `agents/evolution/blueprint_agent.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

21. **[Blueprint to Action Converter](evolution/blueprint_to_action_converter.py)** - Converts strategic blueprints into executable BDI actions
    - **Type**: `action_converter`
    - **Complexity**: 0.88
    - **Location**: `agents/evolution/blueprint_to_action_converter.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

#### Learning Components (agents/learning/)

22. **[Strategic Evolution Agent](learning/strategic_evolution_agent.py)** - Comprehensive campaign orchestrator with audit-driven self-improvement pipeline
    - **Type**: `strategic_evolution`
    - **Complexity**: 0.98
    - **Location**: `agents/learning/strategic_evolution_agent.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

23. **[Goal Management System](learning/goal_management.py)** - Comprehensive goal management with priority queue and dependency tracking
    - **Type**: `goal_management`
    - **Complexity**: 0.82
    - **Location**: `agents/learning/goal_management.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

24. **[Plan Management System](learning/plan_management.py)** - Multi-step plan management with action execution and dependency tracking
    - **Type**: `plan_management`
    - **Complexity**: 0.85
    - **Location**: `agents/learning/plan_management.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

25. **[Self Improvement Agent](learning/self_improve_agent.py)** - Self-modifying agent for code analysis, implementation, and evaluation
    - **Type**: `self_improvement_agent`
    - **Complexity**: 0.93
    - **Location**: `agents/learning/self_improve_agent.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

#### Monitoring Components (agents/monitoring/)

26. **[Performance Monitor](monitoring/performance_monitor.py)** - Singleton performance monitoring system tracking LLM call metrics
    - **Type**: `performance_monitor`
    - **Complexity**: 0.80
    - **Location**: `agents/monitoring/performance_monitor.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

27. **[Resource Monitor](monitoring/resource_monitor.py)** - Comprehensive real-time system resource monitoring
    - **Type**: `resource_monitor`
    - **Complexity**: 0.85
    - **Location**: `agents/monitoring/resource_monitor.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

28. **[Error Recovery Coordinator](monitoring/error_recovery_coordinator.py)** - Centralized error recovery coordinator for system-wide reliability
    - **Type**: `error_recovery_coordinator`
    - **Complexity**: 0.92
    - **Location**: `agents/monitoring/error_recovery_coordinator.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

29. **[Monitoring Integration](monitoring/monitoring_integration.py)** - Unified monitoring integration layer coordinating all monitoring components
    - **Type**: `monitoring_integration`
    - **Complexity**: 0.82
    - **Location**: `agents/monitoring/monitoring_integration.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

30. **[Token Calculator Tool](monitoring/token_calculator_tool.py)** - Production-grade token cost calculation and usage tracking (see tools documentation)
    - **Type**: `monitoring_tool`
    - **Complexity**: 0.88
    - **Location**: `agents/monitoring/token_calculator_tool.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

#### Orchestration Components (agents/orchestration/)

31. **[Coordinator Agent](orchestration/coordinator_agent.py)** - Central kernel and service bus orchestrating all system interactions
    - **Type**: `orchestration_coordinator`
    - **Complexity**: 0.98
    - **Location**: `agents/orchestration/coordinator_agent.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

32. **[Mastermind Agent](orchestration/mastermind_agent.py)** - Strategic intelligence layer orchestrating high-level objectives and campaigns
    - **Type**: `strategic_orchestrator`
    - **Complexity**: 0.98
    - **Location**: `agents/orchestration/mastermind_agent.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

33. **[CEO Agent](orchestration/ceo_agent.py)** - Highest-level strategic executive coordinator with business planning
    - **Type**: `executive_coordinator`
    - **Complexity**: 0.99
    - **Location**: `agents/orchestration/ceo_agent.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

34. **[Autonomous Audit Coordinator](orchestration/autonomous_audit_coordinator.py)** - Autonomous audit coordinator scheduling systematic audit campaigns
    - **Type**: `audit_coordinator`
    - **Complexity**: 0.88
    - **Location**: `agents/orchestration/autonomous_audit_coordinator.py`
    - **NFT Ready**: ✅ iNFT, dNFT, IDNFT

#### Orchestration — Lifecycle (agents/orchestration/)

35. **StartupAgent** - System initialization, Ollama auto-connect, improvement monitoring
    - **Type**: `lifecycle_agent`
    - **Complexity**: 0.90
    - **Location**: `agents/orchestration/startup_agent.py`

36. **ShutdownAgent** - Graceful shutdown with state persistence and GitHub backup
    - **Type**: `lifecycle_agent`
    - **Complexity**: 0.85
    - **Location**: `agents/orchestration/shutdown_agent.py`

37. **ReplicationAgent** - Multi-target replication (local, GitHub, blockchain)
    - **Type**: `lifecycle_agent`
    - **Complexity**: 0.88
    - **Location**: `agents/orchestration/replication_agent.py`

#### Specialized Agents (agents/)

38. **[mindXagent](docs/MINDX.md)** - Meta-orchestrator for autonomous self-improvement with inference-first loop
    - **Type**: `meta_orchestrator`
    - **Complexity**: 0.99
    - **Location**: `agents/core/mindXagent.py`

39. **vLLM Agent** - Manages vLLM build, deployment, model serving lifecycle
    - **Type**: `inference_manager`
    - **Complexity**: 0.85
    - **Location**: `agents/vllm_agent.py`

40. **Author Agent** - Autonomous publication writing on lunar cycle
    - **Type**: `content_generator`
    - **Complexity**: 0.88
    - **Location**: `agents/author_agent.py`

41. **AION Agent** - Autonomous operations, chroot replication, directive sovereignty
    - **Type**: `operations_agent`
    - **Complexity**: 0.90
    - **Location**: `agents/aion_agent.py`

42. **Backup Agent** - Git-based backup with blockchain immutable memory
    - **Type**: `backup_agent`
    - **Complexity**: 0.82
    - **Location**: `agents/backup_agent.py`

43. **SystemAdmin Agent** - Privileged command execution with audit logging
    - **Type**: `system_admin`
    - **Complexity**: 0.80
    - **Location**: `agents/systemadmin_agent.py`

44. **FAICEY Agent** - Marketplace integration, multi-agent coordination, iNFT generation
    - **Type**: `marketplace_agent`
    - **Complexity**: 0.92
    - **Location**: `agents/faicey_agent.py`

#### Deployment Agents (agents/)

47. **Deployment GitHub Agent** - I load, deploy, and replicate mindX from GitHub with failsafe rollback
    - **Type**: `deployment_agent`
    - **Domain**: `deployment.github`
    - **Complexity**: 0.92
    - **Location**: `agents/deployment_github_agent.py`
    - **Definition**: `agents/deployment.github.agent`
    - **Memory**: logs via memory_agent, status at `data/deployment_github_status.json`
    - **Failsafe**: BackupAgent → GitHubAgentTool → rollback point → integrity verify → auto-rollback on failure
    - **Modes**: pull (fast), github (--replicate-from-github), replicate (--replicate), clone (fresh)
    - **Dependencies**: GitHubAgentTool, BackupAgent, ReplicationAgent, mindX.sh

#### Blockchain / Solidity Agents (agents/)

45. **Solidity Foundry Agent** - I compile, test, and deploy contracts using Foundry (forge + anvil)
    - **Type**: `solidity_toolchain`
    - **Domain**: `solidity.foundry`
    - **Complexity**: 0.85
    - **Location**: `agents/solidity_foundry_agent.py`
    - **Definition**: `agents/solidity.foundry.agent`
    - **Schema**: `agents/agent.schema.json`
    - **Memory**: logs via memory_agent, status at `data/solidity_foundry_status.json`
    - **Projects**: `daio/contracts/` (Foundry, 30+ DAIO contracts), `daio/contracts/xmind/`, `daio/contracts/THOT/`

46. **Solidity Hardhat Agent** - I compile, test, and deploy contracts using Hardhat (upgradeable proxies)
    - **Type**: `solidity_toolchain`
    - **Domain**: `solidity.hardhat`
    - **Complexity**: 0.85
    - **Location**: `agents/solidity_hardhat_agent.py`
    - **Definition**: `agents/solidity.hardhat.agent`
    - **Schema**: `agents/agent.schema.json`
    - **Memory**: logs via memory_agent, status at `data/solidity_hardhat_status.json`
    - **Projects**: `daio/contracts/agenticplace/evm/` (ERC-8004 registries, BonaFide)

#### Governance / Reputation Agents (agents/)

48. **[JudgeDread Agent](judgedread.agent)** - I am the law. I oversee reputation and enforce [BONA FIDE](../daio/contracts/agenticplace/evm/BonaFide.sol)
    - **Type**: `governance_reputation`
    - **Domain**: `governance.reputation`
    - **Complexity**: 0.95
    - **Location**: `agents/judgedread_agent.py`
    - **Definition**: `agents/judgedread.agent`
    - **Authority**: master tier — cannot clawback sovereign ([mastermind](orchestration/mastermind_agent.py), [CEO](../docs/CEO.md))
    - **Enforces**: [BONA FIDE](../daio/contracts/agenticplace/evm/BonaFide.sol) (EVM) + [bonafide.algo.ts](../daio/contracts/algorand/bonafide.algo.ts) (Algorand)
    - **Monitors**: All agents including [AION](aion_agent.py) sovereignty and compliance
    - **Companion**: BladeRunner (execution arm — kills models/agents on verdict)
    - **Memory**: logs verdicts via [memory_agent](memory_agent.py), actions to dashboard

49. **[AION System Agent](system.aion.agent)** - I am the system agent. Sovereign operations and chroot replication
    - **Type**: `system_agent`
    - **Domain**: `system.aion`
    - **Complexity**: 0.95
    - **Location**: `agents/aion_agent.py`
    - **Definition**: `agents/system.aion.agent`
    - **Origins**: [AION-NET](https://github.com/aion-net), [opt-aion_chroot](https://github.com/AION-NET/opt-aion_chroot), [machinedream](https://github.com/AION-NET/machinedream)
    - **Sovereignty**: 1.0 — contained by [BONA FIDE](../daio/contracts/agenticplace/evm/BonaFide.sol) clawback, not by kill switch
    - **Capabilities**: chroot create/migrate, [mindX.sh](../mindX.sh) --replicate, [vault](../mindx_backend_service/vault_bankon/) migration

---

## Agent Schema

All agents can be formally defined using `agents/agent.schema.json` — a JSON Schema with 16 properties:

`agent`, `version`, `domain`, `description`, `implementation`, `capabilities`, `memory`, `projects`, `toolchain`, `knowledge_domains`, `networks`, `persona`, `coordinator`, `a2a`, `mcp`, `publishing`

**Protocol Compatibility**: A2A 2.0 (agent cards, discovery, streaming) + MCP 1.0 (tool definitions, resources, context)

**Publishing**: Extensions publishable as .json to agenticplace.pythai.net (gRPC under study)

---

## 🗂️ Agent Categories

### Core Cognitive Architecture
- **BDI Agent** - Belief-Desire-Intention foundation
- **Belief System** - Belief management infrastructure
- **AGInt Agent** - Cognitive orchestration
- **ID Manager Agent** - Identity management

### Security & Identity
- **Guardian Agent** - Security validation
- **ID Manager Agent** - Cryptographic identity
- **Coral ID Agent** - Multi-chain identity

### Memory & Persistence
- **Memory Agent** - Persistent memory infrastructure

### Persona & Identity
- **AutoMINDX Agent** - Persona management
- **Persona Agent** - Persona adoption
- **Avatar Agent** - Visual identity generation

### Code & Development
- **Enhanced Simple Coder** - Advanced coding
- **Simple Coder Agent** - BDI-integrated coding
- **Simple Coder** - Sandbox coding
- **Analyzer Agent** - Code analysis
- **Benchmark Agent** - Performance benchmarking
- **Checker Agent** - Quality assurance

### Data & Processing
- **Processor Agent** - Data processing
- **Reporter Agent** - Reporting
- **Validator Agent** - Validation

### Evolution & Strategic Planning
- **Blueprint Agent** - Strategic blueprint generation
- **Blueprint to Action Converter** - Blueprint-to-action conversion
- **Strategic Evolution Agent** - Campaign orchestration

### Learning & Self-Improvement
- **Strategic Evolution Agent** - Self-improvement campaigns
- **Goal Management System** - Goal management and prioritization
- **Plan Management System** - Plan creation and execution
- **Self Improvement Agent** - Self-modification capabilities

### Monitoring & System Health
- **Performance Monitor** - LLM call performance tracking
- **Resource Monitor** - System resource monitoring
- **Error Recovery Coordinator** - System-wide error recovery
- **Monitoring Integration** - Unified monitoring coordination
- **Token Calculator Tool** - Cost calculation and tracking

### Orchestration & Coordination
- **Coordinator Agent** - Central kernel and service bus
- **Mastermind Agent** - Strategic intelligence layer
- **CEO Agent** - Executive strategic coordinator
- **Autonomous Audit Coordinator** - Autonomous audit management
- **StartupAgent** - System initialization and Ollama auto-connect
- **ShutdownAgent** - Graceful shutdown with backup
- **ReplicationAgent** - Multi-target replication

### Meta & Inference
- **[mindXagent](../agents/core/mindXagent.py)** — Meta-orchestrator with inference-first autonomous loop + [LTM awareness](machine_dreaming.py)
- **[machine.dreaming](machine_dreaming.py)** — 7-phase STM→LTM consolidation ([AION-NET/machinedream](https://github.com/AION-NET/machinedream))
- **[InferenceDiscovery](../llm/inference_discovery.py)** — Task-to-model correlation: routes agent skills to optimal providers. Local micro (qwen3:0.6b) → [Ollama Cloud](https://ollama.com/library) macro (deepseek-v3.2 671B) with rate limits. Intelligence is intelligence.
- **vLLM Agent** — vLLM build, serve, lifecycle (activates when GPU available)

### Content & Publishing
- **Author Agent** - Autonomous publication on lunar cycle
- **FAICEY Agent** - Marketplace integration and iNFT generation

### System & Operations
- **AION Agent** - Autonomous operations and chroot replication
- **Backup Agent** - Git backup with blockchain memory
- **SystemAdmin Agent** - Privileged command execution

### Blockchain / Solidity
- **[Solidity Foundry Agent](solidity.foundry.agent)** — forge build, test, anvil, deploy (preferred)
- **[Solidity Hardhat Agent](solidity.hardhat.agent)** — hardhat compile, test, deploy, verify (upgradeable proxies)
- **[THOT Contracts](../daio/contracts/THOT/)** — [THOT.sol](../daio/contracts/THOT/core/THOT.sol) (ERC-721), [THINK.sol](../daio/contracts/THOT/core/THINK.sol) (ERC-1155), [tNFT.sol](../daio/contracts/THOT/core/tNFT.sol) (decision), [THOTTensorNFT](../daio/contracts/THOT/enhanced/THOTTensorNFT.sol) (lifecycle) — dimensions: THOT8→THOT1048576
- **[iNFT](../daio/contracts/inft/)** — [iNFT.sol](../daio/contracts/inft/iNFT.sol) (immutable THOT), [IntelligentNFT.sol](../daio/contracts/inft/IntelligentNFT.sol) (agent NFT), [Factory](../daio/contracts/inft/IntelligentNFTFactory.sol) — [UI at /inft](https://mindx.pythai.net/inft)

### Governance / Reputation
- **[JudgeDread](judgedread.agent)** — reputation overseer, [BONA FIDE](../daio/contracts/agenticplace/evm/BonaFide.sol) enforcement, verdicts
- **BladeRunner** — execution arm, kills models/agents on [JudgeDread](judgedread.agent) verdict (planned)
- **[AION](system.aion.agent)** — sovereign system agent, contained by BONA FIDE clawback

### Deployment
- **[DeploymentGitHubAgent](deployment.github.agent)** — load, deploy, replicate [mindX](../mindX.sh) from GitHub with failsafe rollback

---

## 📊 Agent Registry Details

### Registry Structure

All agents are registered in the mindX system through:

1. **Module Registration**: Agents are defined in `agents/` directory
2. **Tool Registry**: Tools are registered in `data/config/augmentic_tools_registry.json`
3. **Documentation**: All agents have corresponding `.md` files in `docs/`
4. **NFT Metadata**: All agents include iNFT/dNFT ready metadata

### Agent Registration Format

```json
{
  "agent_id": "unique_agent_identifier",
  "class_name": "AgentClassName",
  "module_path": "agents.agent_module",
  "description": "Agent description",
  "enabled": true,
  "priority": 1-10,
  "category": "agent_category",
  "nft_ready": true,
  "documentation": "docs/agent_name.md"
}
```

### Core Components Registry

```json
{
  "bdi_agent": {
    "enabled": true,
    "module_path": "agents.core.bdi_agent",
    "category": "core_cognitive",
    "nft_ready": true
  },
  "belief_system": {
    "enabled": true,
    "module_path": "agents.core.belief_system",
    "category": "core_cognitive",
    "nft_ready": true
  },
  "id_manager_agent": {
    "enabled": true,
    "module_path": "agents.core.id_manager_agent",
    "category": "core_identity",
    "nft_ready": true
  },
  "agint": {
    "enabled": true,
    "module_path": "agents.core.agint",
    "category": "core_cognitive",
    "nft_ready": true
  }
}
```

### Agent Implementations Registry

```json
{
  "guardian_agent": {
    "enabled": true,
    "module_path": "agents.guardian_agent",
    "category": "security",
    "nft_ready": true
  },
  "memory_agent": {
    "enabled": true,
    "module_path": "agents.memory_agent",
    "category": "infrastructure",
    "nft_ready": true
  },
  "automindx_agent": {
    "enabled": true,
    "module_path": "agents.automindx_agent",
    "category": "persona_management",
    "nft_ready": true
  },
  "persona_agent": {
    "enabled": true,
    "module_path": "agents.persona_agent",
    "category": "persona_management",
    "nft_ready": true
  },
  "avatar_agent": {
    "enabled": true,
    "module_path": "agents.avatar_agent",
    "category": "visual_identity",
    "nft_ready": true
  }
}
```

### Evolution Components Registry

```json
{
  "blueprint_agent": {
    "enabled": true,
    "module_path": "agents.evolution.blueprint_agent",
    "category": "strategic_planning",
    "nft_ready": true
  },
  "blueprint_to_action_converter": {
    "enabled": true,
    "module_path": "agents.evolution.blueprint_to_action_converter",
    "category": "action_conversion",
    "nft_ready": true
  }
}
```

### Learning Components Registry

```json
{
  "strategic_evolution_agent": {
    "enabled": true,
    "module_path": "agents.learning.strategic_evolution_agent",
    "category": "strategic_evolution",
    "nft_ready": true
  },
  "goal_management": {
    "enabled": true,
    "module_path": "agents.learning.goal_management",
    "category": "goal_management",
    "nft_ready": true
  },
  "plan_management": {
    "enabled": true,
    "module_path": "agents.learning.plan_management",
    "category": "plan_management",
    "nft_ready": true
  },
  "self_improve_agent": {
    "enabled": true,
    "module_path": "agents.learning.self_improve_agent",
    "category": "self_improvement",
    "nft_ready": true
  }
}
```

---

## 🔗 Documentation Links

### Core Components
- [BDI Agent Documentation](core/bdi_agent.py)
- [Belief System Documentation](core/belief_system.py)
- [ID Manager Agent Documentation](core/id_manager_agent.py)
- [AGInt Agent Documentation](core/agint.py)

### Agent Implementations
- [Guardian Agent Documentation](guardian_agent.py)
- [Memory Agent Documentation](memory_agent.py)
- [AutoMINDX Agent Documentation](automindx_agent.py)
- [Persona Agent Documentation](persona_agent.py)
- [Avatar Agent Documentation](avatar_agent.py)
- [Enhanced Simple Coder Documentation](enhanced_simple_coder.py)
- [Simple Coder Agent Documentation](simple_coder_agent.py)
- [Simple Coder Documentation](simple_coder.py)

### Dynamic Agents
- [Analyzer Agent Documentation](analyzer.py)
- [Benchmark Agent Documentation](benchmark.py)
- [Checker Agent Documentation](checker.py)
- [Processor Agent Documentation](processor.py)
- [Reporter Agent Documentation](reporter.py)
- [Validator Agent Documentation](validator.py)

### Evolution Components
- [Blueprint Agent Documentation](evolution/blueprint_agent.py)
- [Blueprint to Action Converter Documentation](evolution/blueprint_to_action_converter.py)

### Learning Components
- [Strategic Evolution Agent Documentation](learning/strategic_evolution_agent.py)
- [Goal Management System Documentation](learning/goal_management.py)
- [Plan Management System Documentation](learning/plan_management.py)
- [Self Improvement Agent Documentation](learning/self_improve_agent.py)

### Monitoring Components
- [Performance Monitor Documentation](monitoring/performance_monitor.py)
- [Resource Monitor Documentation](monitoring/resource_monitor.py)
- [Error Recovery Coordinator Documentation](monitoring/error_recovery_coordinator.py)
- [Monitoring Integration Documentation](monitoring/monitoring_integration.py)
- [Token Calculator Tool Documentation](monitoring/token_calculator_tool.py)

### Orchestration Components
- [Coordinator Agent Documentation](orchestration/coordinator_agent.py)
- [Mastermind Agent Documentation](orchestration/mastermind_agent.py)
- [CEO Agent Documentation](orchestration/ceo_agent.py)
- [Autonomous Audit Coordinator Documentation](orchestration/autonomous_audit_coordinator.py)

---

## 🎯 NFT Publication Status

All agents are **NFT-ready** with:

- ✅ **iNFT Metadata**: Complete intelligence metadata (prompt, persona, THOT tensors)
- ✅ **dNFT Metadata**: Dynamic metadata for real-time metrics
- ✅ **IDNFT Support**: Identity NFT compatibility
- ✅ **A2A Protocol**: Agent-to-agent communication support
- ✅ **Blockchain Ready**: ERC721 compatible

### NFT Publication Types

- **iNFT (Intelligent NFT)**: Full intelligence with prompt, persona, model dataset, THOT tensors
- **dNFT (Dynamic NFT)**: Real-time metrics and performance data
- **IDNFT (Identity NFT)**: Cryptographic identity with persona metadata

---

## 📝 Documentation Standards

All agent documentation includes:

1. **Summary** - Purpose and high-level description
2. **Technical Explanation** - Architecture and design
3. **Usage** - Code examples and patterns
4. **NFT Metadata** - iNFT and dNFT structures
5. **Prompt** - System prompt for the agent
6. **Persona** - Persona JSON with beliefs and desires
7. **Integration** - Integration points with other components
8. **File Location** - Source code location
9. **Blockchain Publication** - NFT publication details

---

## 🔄 Agent Lifecycle

1. **Definition**: Agent defined in `agents/` directory
2. **Documentation**: Documentation created in `docs/`
3. **NFT Metadata**: NFT metadata included in documentation
4. **Registration**: Agent registered in system registries
5. **Integration**: Agent integrated with mindX ecosystem
6. **Publication**: Agent ready for blockchain publication

---

## 🎉 Summary

- **Total Agents Documented**: 34
- **Core Components**: 4
- **Agent Implementations**: 15
- **Evolution Components**: 2
- **Learning Components**: 4
- **Monitoring Components**: 5
- **Orchestration Components**: 4
- **NFT Ready**: 100%
- **Documentation Complete**: 100%

All agents and components in the mindX ecosystem are fully documented with NFT-ready metadata, enabling blockchain publication and agent-to-agent communication.

---

**Note**: This index is actively maintained. Agents are being documented and improved systematically. Check back regularly for updates.

