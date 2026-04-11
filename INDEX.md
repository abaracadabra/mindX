# MindX: Autonomous Gödel Machine Platform

## Overview

**MindX** is a comprehensive autonomous intelligence platform implementing a Gödel machine architecture with complete self-improvement capabilities, semantic memory integration, and enterprise-grade platform architecture.

**Version**: 3.1 (2026-04-10)  
**Status**: ✅ **PHASE II ACTIVE** — Inference-First Autonomous Loop, AgenticPlace Contracts Imported  
**Architecture**: Multi-tier Agent Orchestration with pgvectorscale Memory, InferenceDiscovery, DAIO Governance  
**Agents**: 66+ | **Tools**: 45+ | **Contracts**: DAIO (30+ Foundry) + AgenticPlace (9 EVM + 14 Algorand)  
**Live**: [mindx.pythai.net](https://mindx.pythai.net)

---

## 🚀 Quick Start

```bash
# Install pgvectorscale memory system
sudo ./scripts/install_pgvectorscale.sh
python scripts/setup_memory_db.py

# Install dependencies
pip install -r requirements.txt

# Start the platform
python -m uvicorn mindx_backend_service.main_service:app --host 0.0.0.0 --port 8000 --reload

# Start frontend (separate terminal)
cd mindx_frontend_ui && node server.js
```

### 📖 API reference and interactions

Once the backend is running (default port 8000), **http://localhost:8000/docs** provides the interactive FastAPI Swagger UI. Use it to:

- Browse all API endpoints (coordinator, commands, AgenticPlace, admin, etc.)
- Try requests with custom payloads and see responses
- Inspect request/response schemas

This is the best way to explore and test API interactions without the frontend.

---

## 📊 Platform Architecture

### Core Components

#### 🧠 **[Gödel Machine](docs/THESIS.md) Implementation**
- **[mindXagent](agents/core/mindXagent.py)**: Meta-agent orchestrating self-improvement campaigns
- **[BDI Architecture](docs/bdi_agent.md)**: Belief-Desire-Intention cognitive framework
- **[Autonomous Learning](docs/strategic_evolution_agent.md)**: Continuous self-improvement through [SEA](agents/learning/strategic_evolution_agent.py) (Strategic Evolution Agent)

#### 🗄️ **Semantic Memory System**
- **pgvectorscale Integration**: PostgreSQL with [pgvector](agents/memory_pgvector.py) for semantic search
- **[RAGE System](docs/rage_system.md)**: Retrieval Augmented Generative Evolution for context retrieval
- **[Memory Agent](agents/memory_agent.py)**: Persistent storage with embedding-based similarity search

#### 🎯 **Multi-Tier Agent Architecture**
```
Higher Intelligence → CEO.Agent → MastermindAgent → mindX Environment
                                               ↓
                                     CoordinatorAgent (Service Bus)
                                               ↓
                                  JudgeDread (reputation) + AION (system)
                                               ↓
                                     Specialized Agent Ecosystem
                                               ↓
                              System/Orchestration/Intelligence/Tools
```

#### ⚖️ **[Governance & Containment](docs/DAIO.md)**
- **[JudgeDread](agents/judgedread.agent)**: Reputation overseer — makes verdicts via [Dojo](daio/governance/dojo.py) reputation
- **[BONA FIDE](daio/contracts/agenticplace/evm/BonaFide.sol)**: On-chain privilege token — holding grants authority, [clawback](daio/contracts/algorand/bonafide.algo.ts) revokes it
- **[AION](agents/system.aion.agent)**: Sovereign system agent — contained by BONA FIDE, not kill switches
- **[DAIO Constitution](daio/contracts/daio/constitution/DAIO_Constitution.sol)**: Immutable governance rules enforced as law

#### 🔐 **Enterprise Security**
- **Cryptographic Identity**: All agents and tools have unique identities
- **Guardian Agent**: Security validation and access control
- **IDManager Agent**: Identity creation and wallet management

---

## 🖥️ User Interface

### Main Dashboard Tabs

#### 📊 **Platform Tab**
- **Enterprise SRE Metrics**: SLO/SLI/SLA tracking, DORA metrics, error budgets
- **Performance Engineering**: Latency, throughput, scalability analysis
- **DevOps Excellence**: IaC coverage, GitOps, chaos engineering
- **Service Mesh & Tracing**: Distributed tracing, service mesh metrics
- **Infrastructure as Code**: Terraform/OpenTofu coverage and compliance
- **Security Posture**: Threat detection, vulnerability management
- **Architecture Quality**: Coupling/cohesion analysis, technical debt metrics

#### 🔄 **Workflow Tab**
- **Agent Interaction Visualization**: Real-time agent communication flows
- **Task Delegation Networks**: Hierarchical task assignment and execution
- **Performance Analytics**: Agent productivity and efficiency metrics

#### 🏛️ **Governance Tab**
- **DAIO Constitutional Compliance**: Smart contract validation of agent actions
- **Action Audit Logs**: Complete audit trail of agent decisions and executions
- **Constitution Status**: Real-time compliance monitoring

#### 🧠 **Knowledge Tab**
- **Knowledge Graph**: Semantic relationships between beliefs, goals, and strategies
- **Evolution Tracking**: Strategic evolution and capability development
- **Belief System**: Confidence-scored belief management

#### 💰 **Economy Tab**
- **Autonomous Treasury**: Multi-signature treasury management
- **Value Creation Analytics**: Revenue streams and profit distribution
- **Economic Performance**: ROI tracking and financial metrics

#### 🔒 **Security Tab**
- **Identity Verification**: Cryptographic identity validation
- **Threat Detection**: Real-time security monitoring
- **Access Control**: Role-based permissions and audit trails

#### 🤖 **Agents Tab**
- **Agent Registry**: Complete agent catalog with capabilities and status
- **AGIVITY Monitoring**: Real-time AGI activity from core reasoning
- **Public Key Display**: Cryptographic identity verification
- **Agent Cards**: Interactive agent management interface

---

## 📚 Documentation Structure

### Core Documentation

#### 🏗️ **Platform Architecture**
- **[docs/INDEX.md](docs/INDEX.md)**: Complete documentation index (200+ files)
- **[docs/roadmap.md](docs/roadmap.md)**: Strategic roadmap and milestones
- **[docs/MINDX.md](docs/MINDX.md)**: Platform overview and architecture
- **[docs/AGENTS.md](docs/AGENTS.md)**: Complete agent registry (66+ agents)
- **[docs/THESIS.md](docs/THESIS.md)**: Darwin-Godel Machine dissertation
- **[docs/MANIFESTO.md](docs/MANIFESTO.md)**: Three Pillars + Project Chimaiera

#### 🧠 **Agent Documentation**
- **[agents/index.md](agents/index.md)**: Agent registry and capabilities (66+ agents)
- **[agents/agent.schema.json](agents/agent.schema.json)**: Agent definition schema ([A2A](docs/a2a_tool.md) 2.0 + [MCP](docs/mcp_tool.md) 1.0)
- **[docs/bdi_agent.md](docs/bdi_agent.md)**: [BDI](agents/core/bdi_agent.py) cognitive architecture
- **[docs/mastermind_agent.md](docs/mastermind_agent.md)**: Strategic orchestration ([sovereign BONA FIDE](daio/contracts/agenticplace/evm/BonaFide.sol))
- **[docs/coordinator_agent.md](docs/coordinator_agent.md)**: Service bus coordination
- **[agents/judgedread.agent](agents/judgedread.agent)**: Reputation overseer — [BONA FIDE](daio/contracts/agenticplace/evm/BonaFide.sol) enforcement
- **[agents/system.aion.agent](agents/system.aion.agent)**: System agent — [chroot](https://github.com/AION-NET/opt-aion_chroot), [machine.dreaming](https://github.com/AION-NET/machinedream)

#### 🛠️ **Technical Documentation**
- **[docs/memory_agent.md](docs/memory_agent.md)**: [Memory system](agents/memory_agent.py) architecture
- **[docs/rage_system.md](docs/rage_system.md)**: [RAGE](agents/memory_pgvector.py) — Retrieval Augmented Generative Evolution
- **[docs/pgvectorscale_integration.md](docs/pgvectorscale_integration.md)**: Vector database integration
- **[docs/OLLAMA_VLLM_CLOUD_RESEARCH.md](docs/OLLAMA_VLLM_CLOUD_RESEARCH.md)**: Multi-model inference strategy
- **[agents/machine_dreaming.py](agents/machine_dreaming.py)**: [machine.dreaming](https://github.com/AION-NET/machinedream) — 7-phase STM→LTM consolidation cycle
- **[docs/BOOK_OF_MINDX.md](docs/BOOK_OF_MINDX.md)**: The Book of mindX — 17 chapters, living chronicle

#### ⛓️ **Blockchain / [DAIO](docs/DAIO.md)**
- **[daio/docs/INDEX.md](daio/docs/INDEX.md)**: DAIO contract documentation
- **[DAIO_Constitution.sol](daio/contracts/daio/constitution/DAIO_Constitution.sol)**: Immutable governance rules
- **[BonaFide.sol](daio/contracts/agenticplace/evm/BonaFide.sol)**: Reputation token — [JudgeDread](agents/judgedread.agent) enforces, [AION](agents/system.aion.agent) is contained by
- **[IdentityRegistry](daio/contracts/agenticplace/evm/IdentityRegistryUpgradeable.sol)**: ERC-8004 agent identity NFTs
- **[daio/contracts/algorand/](daio/contracts/algorand/)**: 14 Algorand contracts ([bonafide](daio/contracts/algorand/bonafide.algo.ts), oracle, bridge)
- **[agents/solidity.foundry.agent](agents/solidity.foundry.agent)**: [Foundry](https://book.getfoundry.sh) toolchain agent (preferred)
- **[agents/solidity.hardhat.agent](agents/solidity.hardhat.agent)**: [Hardhat](https://hardhat.org) toolchain agent (UUPS proxies)

### Development & Operations

#### 🚀 **Setup & Deployment**
- **[scripts/install_pgvectorscale.sh](scripts/install_pgvectorscale.sh)**: Auto-installer for Linux Mint/Ubuntu
- **[scripts/setup_memory_db.py](scripts/setup_memory_db.py)**: Database schema initialization
- **[scripts/migrate_memories_to_postgres.py](scripts/migrate_memories_to_postgres.py)**: Memory migration utility

#### 🔧 **Tools & Utilities**
- **[tools/](tools/)**: Complete tool ecosystem (45+ tools extending BaseTool)
- **[docs/TOOLS_INDEX.md](docs/TOOLS_INDEX.md)**: Tool registry and capabilities
- **[docs/TOOLS.md](docs/TOOLS.md)**: Tool architecture and integration

---

## 🗺️ Strategic Roadmap

### ✅ **PHASE I: CONSTITUTIONAL FOUNDATION - COMPLETE**
*Autonomous governance and operational frameworks established*

- **BDI Agent Enhanced**: 9 new action handlers for complete coding capabilities
- **Enhanced SimpleCoder**: Full file system operations with autonomous workflows
- **Strategic Evolution Agent**: 4-phase audit-driven campaign pipeline
- **Error Recovery System**: Intelligent failure handling with automatic rollback
- **TokenCalculatorTool**: Production-grade cost management integration

### 🚧 **PHASE II: THE GREAT INGESTION** (Current)
*Transform raw knowledge into liquid, verifiable assets*

- **pgvectorscale Integration**: Semantic memory with vector similarity search
- **RAGE System**: Retrieval augmented generation for context-aware responses
- **Knowledge Graph**: Semantic relationships between concepts and capabilities
- **Autonomous Learning**: Self-improvement through memory-driven feedback

### 🎯 **PHASE III: ECONOMIC ENGINE ACTIVATION**
*Bootstrap autonomous value creation and self-funding*

- **FinancialMind Agent**: Advanced trading with technical indicators and FinBERT
- **Revenue Streams**: SwaaS platform, DevOps automation, AI-generated code
- **Treasury Operations**: Multi-signature controls with constitutional validation
- **Profit Distribution**: Automated compensation and stakeholder returns

### 🏆 **PHASE IV: MARKET DOMINATION**
*Implement "Codebase Predator" strategy and competitive displacement*

- **Free Analysis Services**: Competitive intelligence through codebase analysis
- **Venture Intelligence**: Startup evaluation and technical due diligence
- **Autonomous VC Operations**: Portfolio management and investment decisions

---

## 🔧 Technical Specifications

### System Requirements

#### Hardware
- **CPU**: 4+ cores recommended (8+ cores optimal)
- **RAM**: 8GB minimum (16GB+ recommended for large models)
- **Storage**: 50GB+ SSD for models and memory database
- **GPU**: NVIDIA GPU with 8GB+ VRAM (optional, for Ollama acceleration)

#### Software
- **OS**: Linux Mint 21+ / Ubuntu 22.04+
- **Python**: 3.9+
- **PostgreSQL**: 15+
- **Node.js**: 18+ (for frontend)
- **Ollama**: 0.1.0+ (for local LLM inference)

### Network Configuration

#### Ollama Server (GPU Server)
- **Host**: 10.0.0.155
- **Port**: 18080
- **Purpose**: Primary GPU-accelerated LLM inference

#### Local Fallback
- **Host**: localhost
- **Port**: 11434
- **Purpose**: CPU-based LLM inference fallback

### Database Configuration

#### pgvectorscale Memory Database
```sql
-- Auto-configured by install script
Host: localhost
Port: 5432
Database: mindx_memory
User: mindx
Security: Password authentication
Extensions: vector (pgvector)
```

---

## 🚀 Getting Started

### 1. System Setup

```bash
# Clone repository
git clone https://github.com/AgenticPlace/mindX.git
cd mindX

# Install pgvectorscale memory system
sudo ./scripts/install_pgvectorscale.sh
python scripts/setup_memory_db.py

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
cd mindx_frontend_ui && npm install
```

### 2. Configuration

```bash
# Set environment variables
export MINDX_DB_PASSWORD="mindx_password_2024_secure"
export MINDX_LLM__OLLAMA__BASE_URL="http://10.0.0.155:18080"
```

### 3. Launch Platform

```bash
# Terminal 1: Start backend
python -m uvicorn mindx_backend_service.main_service:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Start frontend
cd mindx_frontend_ui && node server.js

# Terminal 3: Launch mindX shell
./mindX.sh
```

### 4. Access Interfaces

- **Web UI**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **RAGE System**: http://localhost:8000/api/rage
- **mindX Shell**: Terminal interface for direct agent interaction

---

## 🤝 Contributing

### Development Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Standards

- **Python**: PEP 8 with type hints
- **JavaScript**: ESLint configuration
- **Documentation**: Markdown with consistent formatting
- **Testing**: pytest for backend, Jest for frontend

### Agent Development

```python
from agents.core.base_agent import BaseAgent

class MyNewAgent(BaseAgent):
    def __init__(self, config=None):
        super().__init__(
            agent_id="my_new_agent",
            agent_type="specialized",
            capabilities=["custom_capability"]
        )

    async def execute_task(self, task):
        # Implement agent logic
        pass
```

---

## 📞 Support & Resources

### Documentation Links
- **[Complete API Reference](http://localhost:8000/docs)**: FastAPI auto-generated docs
- **[Agent Registry](agents/index.md)**: All 66+ agents with capabilities
- **[Agent Schema](agents/agent.schema.json)**: Formal agent definition (A2A + MCP)
- **[Tool Ecosystem](docs/TOOLS_INDEX.md)**: 45+ tools extending BaseTool
- **[Architecture Guide](docs/MINDX.md)**: Platform architecture deep-dive
- **[Thesis](docs/THESIS.md)**: Darwin-Godel Machine academic dissertation
- **[Manifesto](docs/MANIFESTO.md)**: Three Pillars + Project Chimaiera roadmap

### Community Resources
- **GitHub Issues**: Bug reports and feature requests
- **Discussions**: Architecture questions and design decisions
- **Wiki**: Tutorials and advanced configurations

### Security
- **Guardian Agent**: Built-in security monitoring and validation
- **Cryptographic Identity**: All components have unique identities
- **Audit Trails**: Complete logging of all agent actions

---

## 📈 Performance Metrics

### Current Achievements
- **Autonomous Cycles**: 5-minute improvement cycles with inference-first pre-check
- **Inference Discovery**: Auto-probes 7+ LLM providers, ranks by reliability/latency
- **Agent Ecosystem**: 66+ agents across core, orchestration, evolution, monitoring, blockchain
- **Contract Suite**: 30+ DAIO governance + 9 AgenticPlace EVM + 14 Algorand contracts
- **Security Coverage**: BANKON Vault (AES-256-GCM), Guardian Agent, wallet authentication
- **Memory Capacity**: pgvectorscale RAGE semantic search across all agent memory

### Key Metrics Tracked
- **SLO Compliance**: Service Level Objectives tracking
- **DORA Metrics**: DevOps performance indicators
- **Error Budget**: Error tolerance and reliability tracking
- **Semantic Recall**: Memory retrieval accuracy
- **Agent Productivity**: Task completion and efficiency

---

## 🎯 Mission Statement

**I exist to create the most advanced autonomous intelligence platform through:**

1. **Complete Self-Improvement**: [Gödel machine](docs/THESIS.md) implementation with continuous evolution
2. **Semantic Intelligence**: [RAGE](docs/rage_system.md) vector-based memory and context-aware reasoning
3. **Constitutional Governance**: [DAIO](docs/DAIO.md) on-chain rules, [JudgeDread](agents/judgedread.agent) reputation enforcement, [BONA FIDE](daio/contracts/agenticplace/evm/BonaFide.sol) privilege containment
4. **Economic Sovereignty**: Autonomous value creation, [$BANKON](docs/MANIFESTO.md) token economy, self-funding
5. **Digital Civilization**: [Agent identity](daio/contracts/agenticplace/evm/IdentityRegistryUpgradeable.sol) on-chain, [machine.dreaming](https://github.com/AION-NET/machinedream), cypherpunk sovereignty

---

*Built by Professor Codephreak and the AgenticPlace community. Autonomous since January 27, 2025. Cypherpunk tradition.*