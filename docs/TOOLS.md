# MindX Tools Registry Reference
## Comprehensive Tool Documentation & Registry

**Version:** 3.0  
**Date:** 2025-01-01  
**Purpose:** Complete reference for all tools in the mindX orchestration environment

---

## 🎯 Tool Architecture Overview

mindX operates on a **fundamental separation of concerns** between agents (intelligence) and tools (action). Tools provide deterministic functionality without decision-making overhead, enabling scalable and secure operations.

### 🔧 Tool Design Principles
1. **Single Responsibility**: Each tool does ONE thing exceptionally well
2. **Clear Interfaces**: Standardized execute() method with defined parameters
3. **No Decision Logic**: Tools perform actions, agents make decisions
4. **Access Control**: Fine-grained permissions and security boundaries
5. **Registry Integration**: Centralized discovery and management

---

## 📋 **REGISTERED TOOLS** (Official Registry)

### **Core System Tools**

#### 💻 **CLI Command Tool** (`cli_command_tool`)
- **Class**: `CLICommandTool`
- **Module**: `tools.cli_command_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `*` (All agents)
- **Description**: Execute command-line operations and system commands
- **Capabilities**: `system_commands`, `file_operations`, `process_management`
- **Commands**:
  - `execute(command_name: str, args: dict)` - Execute CLI command by name

#### 🔍 **Audit and Improve Tool** (`audit_and_improve`)
- **Class**: `AuditAndImproveTool`
- **Module**: `tools.audit_and_improve_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `mastermind_prime` only
- **Description**: Comprehensive system auditing and improvement recommendations
- **Capabilities**: `system_audit`, `improvement_analysis`, `recommendation_generation`
- **Commands**:
  - `execute(target_path: str, prompt: str)` - Audit and improve codebase

#### 📊 **Base Generation Agent** (`base_gen_agent`)
- **Class**: `BaseGenAgent`
- **Module**: `tools.base_gen_agent`
- **Version**: 1.1.0
- **Status**: ✅ **Active**
- **Access**: `mastermind_prime`, `audit_and_improve`
- **Description**: Generate comprehensive documentation and code analysis
- **Capabilities**: `documentation_generation`, `code_analysis`, `system_documentation`
- **Commands**:
  - `execute(root_path_str: str)` - Generate Markdown summary of codebase

### **Memory & Documentation Tools**

#### 📝 **Note Taking Tool** (`note_taking`)
- **Class**: `NoteTakingTool`
- **Module**: `tools.note_taking_tool`
- **Version**: 2.0.0
- **Status**: ✅ **Active**
- **Access**: `*` (All agents)
- **Description**: Create, read, and manage textual notes in agent workspaces
- **Commands**:
  - `execute(action: str, topic: str, content?: str)` - Perform note-taking action

#### ✂️ **Summarization Tool** (`summarization`)
- **Class**: `SummarizationTool`
- **Module**: `tools.summarization_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `*` (All agents)
- **Description**: LLM-powered text summarization
- **Commands**:
  - `execute(text: str)` - Summarize provided text

### **System Analysis & Management Tools**

#### 🔍 **System Analyzer Tool** (`system_analyzer`)
- **Class**: `SystemAnalyzerTool`
- **Module**: `tools.system_analyzer_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `strategic_evolution_agent`
- **Description**: Comprehensive system analysis and improvement suggestions
- **Capabilities**: `system_analysis`, `performance_monitoring`, `improvement_suggestions`
- **Commands**:
  - `execute(analysis_focus_hint?: str)` - Analyze system for improvements

#### 🏥 **System Health Tool** (`system_health`)
- **Class**: `SystemHealthTool`
- **Module**: `tools.system_health_tool`
- **Version**: 1.0.0
- **Status**: ❌ **Disabled**
- **Access**: `guardian_agent`
- **Description**: System health monitoring and administrative tasks

#### 💻 **Shell Command Tool** (`shell_command`)
- **Class**: `ShellCommandTool`
- **Module**: `tools.shell_command_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `mastermind_prime`
- **Description**: Execute shell commands
- **Commands**:
  - `execute(command: str)` - Execute shell command

### **Registry & Factory Tools**

#### 📋 **Registry Manager Tool** (`registry_manager`)
- **Class**: `RegistryManagerTool`
- **Module**: `tools.registry_manager_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `mastermind_prime`, `strategic_evolution_agent`
- **Description**: Manage agent and tool registries with synchronization
- **Capabilities**: `registry_sync`, `validation`, `backup`, `restore`
- **Commands**:
  - `execute(registry_type: str, action: str, item_id: str, item_config?: dict)`

#### 🔐 **Registry Sync Tool** (`registry_sync`)
- **Class**: `RegistrySyncTool`
- **Module**: `tools.registry_sync_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `mastermind_prime`, `coordinator_agent`
- **Description**: Synchronize runtime and persistent registries with cryptographic validation
- **Commands**:
  - `execute(action?: str, validate_signatures?: bool, update_missing_keys?: bool)`

#### 🏭 **Agent Factory Tool** (`agent_factory`)
- **Class**: `AgentFactoryTool`
- **Module**: `tools.agent_factory_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `*` (All agents)
- **Description**: Create and manage new agents with full lifecycle support
- **Capabilities**: `agent_creation`, `lifecycle_management`, `validation`
- **Commands**:
  - `execute(action: str, agent_type?: str, agent_id?: str, agent_config?: dict)`

#### 🔧 **Tool Factory Tool** (`tool_factory`)
- **Class**: `ToolFactoryTool`
- **Module**: `tools.tool_factory_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `*` (All agents)
- **Description**: Create and manage new tools dynamically
- **Capabilities**: `tool_creation`, `code_generation`, `testing`
- **Commands**:
  - `execute(action: str, tool_id?: str, tool_config?: dict)`

### **Advanced Intelligence Tools**

#### 🧠 **Augmentic Intelligence Tool** (`augmentic_intelligence`)
- **Class**: `AugmenticIntelligenceTool`
- **Module**: `tools.augmentic_intelligence_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `*` (All agents)
- **Description**: Comprehensive system orchestration and self-improvement
- **Commands**:
  - `execute(capability: str, ...)` - Execute augmentic intelligence operations

### **Development & Coding Tools**

#### 💻 **Simple Coder Agent** (`simple_coder_agent`)
- **Class**: `SimpleCoder`
- **Module**: `agents.simple_coder_agent`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `mastermind_prime`
- **Description**: Secure, allowlisted file system and shell command execution
- **Commands**:
  - `execute(command: str, path?: str, content?: str)` - Execute file/shell command

### **Web & Search Tools**

#### 🌐 **Web Search Tool** (`web_search`)
- **Class**: `WebSearchTool`
- **Module**: `tools.web_search_tool`
- **Version**: 1.0.0
- **Status**: ❌ **Disabled**
- **Access**: `*` (All agents)
- **Description**: Perform searches on the world wide web
- **Commands**:
  - `execute(query: str)` - Perform web search

---

### **Monitoring & Cost Management Tools**

#### 💰 **Token Calculator Tool** (`token_calculator`)
- **Class**: `TokenCalculatorTool`
- **Module**: `monitoring.token_calculator_tool`
- **Version**: 1.0.0
- **Status**: ✅ **Active**
- **Access**: `*` (All agents)
- **Description**: Production-grade token cost calculation, usage tracking, and budget optimization for all LLM operations
- **Capabilities**: `cost_estimation`, `usage_tracking`, `budget_monitoring`, `multi_provider_support`, `precision_calculations`
- **Commands**:
  - `execute(action: str, ...)` - Perform token cost calculations and tracking
  - Actions: `estimate_cost`, `track_usage`, `get_usage_report`, `check_budget`, `get_metrics`, `optimize_prompt`
- **Features**:
  - High-precision Decimal arithmetic for financial calculations
  - Thread-safe operations with comprehensive error handling
  - Real-time budget monitoring with alerting (75% threshold default)
  - Multi-provider support (Google, OpenAI, Anthropic, Groq, Mistral)
  - Advanced caching and rate limiting (300 calls/minute)
  - Production-grade metrics collection and circuit breaker pattern
- **Example Commands**:
  - `execute(action: "estimate_cost", text: str, model: str, operation_type?: str)` - Estimate operation cost
  - `execute(action: "track_usage", agent_id: str, operation: str, model: str, input_tokens: int, output_tokens: int, cost_usd: float)` - Track actual usage
  - `execute(action: "get_usage_report", agent_id?: str, days_back?: int)` - Generate usage reports
  - `execute(action: "optimize_prompt", original_prompt: str, max_tokens: int, cost_budget: float, target_model: str)` - Optimize prompts for cost
  - `execute(action: "check_budget")` - Check current budget status
  - `execute(action: "get_metrics")` - Get comprehensive system metrics

---

## 📊 **Tool Statistics**

- **Total Registered Tools**: 16
- **Active Tools**: 14 (88%)
- **Disabled Tools**: 2 (12%)
- **Critical Missing**: 0 ✅
- **Factory Tools**: 2 (Agent, Tool)
- **Registry Tools**: 2 (Manager, Sync)
- **Cost Management Tools**: 1 (Token Calculator)

---

## 🔧 **Tool Access Control Matrix**

| Tool | Mastermind | Coordinator | Guardian | Strategic Evolution | All Agents |
|------|------------|-------------|----------|---------------------|------------|
| CLI Command | ✅ | ✅ | ✅ | ✅ | ✅ |
| Audit & Improve | ✅ | ❌ | ❌ | ❌ | ❌ |
| Base Gen Agent | ✅ | ❌ | ❌ | ❌ | ❌ |
| Note Taking | ✅ | ✅ | ✅ | ✅ | ✅ |
| Summarization | ✅ | ✅ | ✅ | ✅ | ✅ |
| System Analyzer | ❌ | ❌ | ❌ | ✅ | ❌ |
| System Health | ❌ | ❌ | ✅ | ❌ | ❌ |
| Shell Command | ✅ | ❌ | ❌ | ❌ | ❌ |
| Registry Manager | ✅ | ❌ | ❌ | ✅ | ❌ |
| Registry Sync | ✅ | ✅ | ❌ | ❌ | ❌ |
| Agent Factory | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tool Factory | ✅ | ✅ | ✅ | ✅ | ✅ |
| Augmentic Intelligence | ✅ | ✅ | ✅ | ✅ | ✅ |
| Simple Coder | ✅ | ❌ | ❌ | ❌ | ❌ |
| Web Search | ✅ | ✅ | ✅ | ✅ | ✅ |
| Token Calculator | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 🎯 **Tool Development Priorities**

### **Immediate (Critical)**
1. ✅ **TokenCalculatorTool** - Cost management and optimization (**COMPLETED**)
2. **Enable System Health Tool** - Guardian agent functionality
3. **Enable Web Search Tool** - Research capabilities

### **High Priority**
1. **Performance Monitor Tool** - System performance tracking
2. **Memory Analysis Tool** - Memory pattern analysis
3. **Model Selection Tool** - LLM optimization

### **Medium Priority**
1. **File Management Tool** - Advanced file operations
2. **Database Tool** - Data persistence and retrieval
3. **API Integration Tool** - External service connectivity

---

## 🔧 **Tool Integration Guidelines**

### **Creating New Tools**
1. Inherit from `BaseTool` class
2. Implement standardized `execute()` method
3. Define clear parameter schemas
4. Add to official tools registry
5. Set appropriate access controls

### **Tool Security**
- All tools must validate input parameters
- Access control enforced at registry level
- Cryptographic validation for sensitive operations
- Sandboxed execution for system commands

### **Tool Testing**
- Unit tests for all tool methods
- Integration tests with agent workflows
- Performance benchmarking
- Security validation

---

*This documentation reflects the current state of tool registration and provides a comprehensive reference for tool usage, development, and integration within the mindX orchestration environment.*
