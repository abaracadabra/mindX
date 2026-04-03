> **[ARCHIVED]** This document is outdated. See [AGENTS.md](AGENTS.md) for the current agent architecture reference.

---

# MindX Agent Architecture Reference
## Comprehensive Agent Registry & Documentation

**Version:** 3.0  
**Date:** 2025-09-14 
**Purpose:** Complete reference for all agents in the mindX orchestration environment

---

## 🎯 Agent Architecture Overview

mindX operates as an **agnostic orchestration environment** with a multi-tier agent architecture supporting symphonic coordination across intelligence levels. Each agent maintains cryptographic identity, specialized capabilities, and standardized A2A (Agent-to-Agent) communication.

### 🎼 Orchestration Hierarchy
```
Higher Intelligence → CEO.Agent → Conductor.Agent → mindX Environment
                                                        ↓
                                              MastermindAgent (Coordinator)
                                                        ↓
                                              Specialized Agent Ecosystem
```

---

## 📋 **REGISTERED AGENTS** (Official Registry)

### **Tier 1: Core Orchestration**

#### 🧠 **MastermindAgent** (`mastermind_prime`)
- **File**: `orchestration/mastermind_agent.py`
- **Type**: `orchestrator`
- **Status**: ✅ **Registered & Active**
- **Identity**: `0xb9B46126551652eb58598F1285aC5E86E5CcfB43`
- **Access**: Full system access (`*` permissions)
- **Role**: Primary orchestration coordinator within mindX environment
- **Capabilities**: Strategic planning, agent lifecycle management, BDI-driven decisions

#### 🎛️ **CoordinatorAgent** (`coordinator_agent`)
- **File**: `orchestration/coordinator_agent.py`
- **Type**: `kernel`
- **Status**: ✅ **Registered & Active**
- **Identity**: `0x7371e20033f65aB598E4fADEb5B4e400Ef22040A`
- **Access**: `system_analyzer` tool
- **Role**: Central kernel and service bus for agent lifecycle
- **Capabilities**: Agent creation, identity provisioning, registry synchronization

### **Tier 2: Security & Identity**

#### 🛡️ **GuardianAgent** (`guardian_agent_main`)
- **File**: `agents/guardian_agent.py`
- **Type**: `core_service`
- **Status**: ✅ **Registered & Active**
- **Identity**: `0xC2cca3d6F29dF17D1999CFE0458BC3DEc024F02D`
- **Access**: `system_health` tool
- **Role**: Security validation and challenge-response authentication
- **Capabilities**: Resource protection, security scanning, audit logging

#### 🆔 **IDManagerAgent** (Unregistered - see below)
- **Status**: ⚠️ **Core component but not in registry**
- **Critical**: Identity management for all agents

### **Tier 3: Specialized Services**

#### 🤖 **AutoMINDXAgent** (`automindx_agent_main`)
- **File**: `agents/automindx_agent.py`
- **Type**: `core_service`
- **Status**: ✅ **Registered & Active**
- **Identity**: `0xCeFF40C3442656D06d0722DfB1e2b2A62D1C1d76`
- **Access**: No tools assigned
- **Role**: Persona management and adaptive behavior
- **Capabilities**: Adaptive persona switching, behavioral optimization

#### 🧬 **StrategicEvolutionAgent** (`sea_for_mastermind`)
- **File**: `learning/strategic_evolution_agent.py`
- **Type**: `core_service`
- **Status**: ✅ **Registered & Active**
- **Identity**: `0x5208088F9C7c45a38f2a19B6114E3C5D17375C65`
- **Access**: `system_analyzer`, `registry_manager` tools
- **Role**: Self-modification and software engineering specialist
- **Capabilities**: Code evolution, system improvement, lesson learning

#### 🏗️ **BlueprintAgent** (`blueprint_agent_mindx_v2`)
- **File**: `evolution/blueprint_agent.py`
- **Type**: `core_service`
- **Status**: ✅ **Registered & Active**
- **Identity**: `0xa61c00aCA8966A7c070D6DbeE86c7DD22Da94C18`
- **Access**: `base_gen_agent` tool
- **Role**: System architecture and blueprint management
- **Capabilities**: Architecture documentation, system blueprinting

---

## ⚠️ **UNREGISTERED AGENTS** (Found in Codebase)

### **Critical Core Agents**

#### 🆔 **IDManagerAgent**
- **File**: `core/id_manager_agent.py`
- **Status**: ❌ **UNREGISTERED** - Critical system component
- **Role**: Cryptographic identity and agent instantiation
- **Capabilities**: Identity creation, wallet management, permissions
- **Priority**: **HIGH** - Should be registered immediately

#### 🧭 **AGInt** (Augmentic General Intelligence)
- **File**: `core/agint.py`
- **Status**: ❌ **UNREGISTERED** - Core cognitive engine
- **Role**: P-O-D-A cognitive processing cycle
- **Capabilities**: Perception, orientation, decision-making, action
- **Priority**: **HIGH** - Central intelligence component

#### 🎯 **BDIAgent** (Belief-Desire-Intention)
- **File**: `core/bdi_agent.py`
- **Status**: ❌ **UNREGISTERED** - Tactical execution engine
- **Role**: Goal-oriented autonomous behavior with BDI architecture
- **Capabilities**: Belief management, intention planning, tool execution
- **Priority**: **HIGH** - Primary execution agent

### **Memory & Learning Agents**

#### 🧠 **EnhancedMemoryAgent**
- **File**: `agents/enhanced_memory_agent.py`
- **Status**: ❌ **UNREGISTERED**
- **Role**: Advanced memory management and learning
- **Capabilities**: Memory analysis, pattern recognition, self-improvement

#### 🧠 **MemoryAgent**
- **File**: `agents/memory_agent.py`
- **Status**: ❌ **UNREGISTERED**
- **Role**: Basic memory operations and storage
- **Capabilities**: Memory persistence, retrieval, organization

#### 📈 **SelfImprovementAgent**
- **File**: `learning/self_improve_agent.py`
- **Status**: ❌ **UNREGISTERED**
- **Role**: Autonomous self-improvement and optimization
- **Capabilities**: Performance analysis, capability enhancement

### **Utility & Development Agents**

#### 💻 **SimpleCoderAgent**
- **File**: `agents/simple_coder_agent.py`
- **Status**: ❌ **UNREGISTERED** - Listed in tools registry as tool
- **Role**: Secure file system and shell command execution
- **Capabilities**: Code generation, file operations, sandboxed execution

#### 🌐 **MultiModelAgent**
- **File**: `llm/multimodel_agent.py`
- **Status**: ❌ **UNREGISTERED**
- **Role**: Multi-model LLM coordination
- **Capabilities**: Model selection, load balancing, optimization

#### 📚 **DocumentationAgent**
- **File**: `docs/documentation_agent.py`
- **Status**: ❌ **UNREGISTERED**
- **Role**: Automated documentation generation
- **Capabilities**: Code documentation, API docs, system documentation

### **Testing & Validation Agents**

#### 🧪 **UltimateCognitionTestAgent**
- **File**: `tests/test_agent.py`
- **Status**: ❌ **UNREGISTERED** - Test infrastructure
- **Role**: Comprehensive system testing
- **Capabilities**: Cognitive testing, validation, benchmarking

#### 🧪 **EnhancedUltimateCognitionTestAgent**
- **File**: `tests/enhanced_test_agent.py`
- **Status**: ❌ **UNREGISTERED** - Enhanced test infrastructure
- **Role**: Advanced testing capabilities
- **Capabilities**: Enhanced testing, performance analysis

#### 📊 **ReportAgent**
- **File**: `tests/report_agent.py`
- **Status**: ❌ **UNREGISTERED** - Reporting infrastructure
- **Role**: Test reporting and analysis
- **Capabilities**: Report generation, data analysis

---

## 🚨 **CRITICAL REGISTRATION GAPS**

### **Immediate Action Required**
1. **IDManagerAgent** - Core identity management (CRITICAL)
2. **AGInt** - Central cognitive engine (CRITICAL)
3. **BDIAgent** - Primary execution engine (CRITICAL)
4. **EnhancedMemoryAgent** - Advanced memory capabilities (HIGH)
5. **SelfImprovementAgent** - Autonomous improvement (HIGH)

### **Agent Registration Priority Matrix**

| Agent | Priority | Reason | Impact |
|-------|----------|--------|---------|
| IDManagerAgent | CRITICAL | Identity management for all agents | System failure |
| AGInt | CRITICAL | Core cognitive processing | No intelligence |
| BDIAgent | CRITICAL | Primary execution engine | No task execution |
| EnhancedMemoryAgent | HIGH | Advanced learning capabilities | Limited learning |
| SelfImprovementAgent | HIGH | Autonomous evolution | No self-improvement |
| MultiModelAgent | MEDIUM | LLM optimization | Performance impact |
| SimpleCoderAgent | MEDIUM | Development capabilities | Limited coding |

---

## 📊 **Agent Statistics**

- **Total Agents Found**: 20+
- **Registered Agents**: 6 (30%)
- **Unregistered Agents**: 14+ (70%)
- **Critical Unregistered**: 3 (IDManager, AGInt, BDI)
- **Active Registered**: 6 (100% of registered)

---

## 🔧 **Agent Architecture Principles**

### **Core Design Patterns**
1. **Cryptographic Identity**: Every agent has unique identity and signature
2. **A2A Communication**: Standardized agent-to-agent protocols
3. **Tool Integration**: Agents use tools, not internal implementations
4. **Memory-Driven Learning**: Comprehensive logging enables evolution
5. **BDI Cognitive Model**: Belief-Desire-Intention for goal-oriented behavior

### **Registration Requirements**
- Unique cryptographic identity
- A2A model card specification
- Tool access control definitions
- Capability documentation
- Version and lifecycle management

---

## 🎯 **Next Steps**

1. **Register Critical Agents**: IDManager, AGInt, BDI immediately
2. **Audit Agent Capabilities**: Ensure all agents have proper tool access
3. **Standardize A2A Communication**: Implement model cards for all agents
4. **Memory Integration**: Connect all agents to enhanced memory system
5. **Performance Monitoring**: Track agent effectiveness and resource usage

---

*This documentation reflects the current state of agent registration and highlights critical gaps that need immediate attention for optimal mindX orchestration environment performance.* 
