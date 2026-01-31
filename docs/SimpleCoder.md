# 🛠️ SimpleCoder: Comprehensive Coding Agent System

**Status**: ✅ **PRODUCTION READY** - Fully Integrated with BDI Agent and mindX Ecosystem  
**Last Updated**: January 30, 2026  
**Version**: 7.0 (Augmentic Intelligence Enhanced)

## 📋 Table of Contents

1. [Overview](#overview)
2. [Architecture & Components](#architecture--components)
3. [Technical Explanation](#technical-explanation)
4. [Sandbox System](#sandbox-system)
5. [Memory Integration](#memory-integration)
6. [Usage Guide](#usage-guide)
7. [Integration Guide](#integration-guide)
8. [Limitations & Constraints](#limitations--constraints)
9. [Security & Safety](#security--safety)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)
12. [API Reference](#api-reference)
13. [Examples](#examples)
14. [NFT Metadata](#nft-metadata)

---

## Overview

SimpleCoder is a comprehensive coding agent system for the mindX autonomous digital civilization. It provides intelligent code generation, analysis, execution, and file system operations with secure sandboxing, memory integration, and autonomous operation capabilities.

### System Components

The SimpleCoder system consists of three main implementations:

1. **`simple_coder.py`** - Enhanced coding agent with sandbox mode, autonomous operation, and UI integration
2. **`simple_coder_agent.py`** - BDI-integrated coding assistant with advanced capabilities and multi-model intelligence
3. **`enhanced_simple_coder.py`** - Comprehensive coding agent with multi-model selection and complete file system operations

All three components share a unified sandbox directory (`simple_coder_sandbox/`) for consistent operations.

### Key Features

- ✅ **Sandbox Mode**: Automatic file backups and secure execution
- ✅ **Autonomous Mode**: Infinite cycle iterations for continuous operation
- ✅ **Update Request System**: UI-integrated file update mechanism
- ✅ **Memory Integration**: Full MemoryAgent integration for learning
- ✅ **Pattern Learning**: Adaptive learning from execution patterns
- ✅ **Multi-Model Intelligence**: Intelligent model selection for different tasks
- ✅ **Secure Execution**: Path traversal prevention and command allowlisting
- ✅ **BDI Integration**: Full integration with BDI Agent action system

---

## Architecture & Components

### Component Overview

```
SimpleCoder System
├── simple_coder.py              # Enhanced agent with sandbox/autonomous modes
├── simple_coder_agent.py         # BDI-integrated assistant
├── enhanced_simple_coder.py      # Multi-model comprehensive agent
└── simple_coder_sandbox/        # Unified sandbox directory
    ├── working/                  # Working files
    ├── completed/                # Completed files
    ├── update_requests.json      # Update request tracking
    └── patterns.json            # Learned patterns
```

### Architecture Patterns

#### 1. Direct Execution Mode (Dumb Mode)

The tool's "Dumb Mode" is designed to be called by a higher-level agent (like the BDIAgent) that has already performed its own reasoning and constructed a precise, single-step plan.

**How it works:**
- The calling agent provides a specific command name (e.g., "safe_read_file") and all required parameters
- SimpleCoder validates that the command is on its allowlist and that all required parameters are present
- Executes directly without any further LLM consultation

**Purpose:** Fast, predictable, and secure execution of concrete steps in a pre-defined plan.

#### 2. LLM-Powered Task Mode (Smart Mode)

The tool's "Smart Mode" empowers SimpleCoder to act as a self-contained, intelligent bash agent.

**How it works:**
1. The calling agent provides a high-level, natural language task
2. SimpleCoder initiates its own internal loop:
   - Constructs a specialized prompt for its internal LLM
   - LLM decides which tool to use next and with which arguments
   - SimpleCoder executes the chosen command
   - Output is fed back into the LLM's context
   - Loop continues until the LLM determines the task is complete

**Purpose:** Incredible flexibility for complex, multi-step shell operations with a single command.

### BDI Agent Integration

SimpleCoder is fully integrated with the BDI Agent through 9 action handlers:

```python
# Available BDI Actions:
EXECUTE_BASH_COMMAND          # Direct command execution
EXECUTE_LLM_BASH_TASK         # LLM-powered task execution
READ_FILE                     # File reading
WRITE_FILE                    # File writing
LIST_FILES                    # Directory listing
CREATE_DIRECTORY              # Directory creation
ANALYZE_CODE                  # Code analysis
GENERATE_CODE                 # Code generation
GET_CODING_SUGGESTIONS        # Intelligent suggestions
```

---

## Technical Explanation

### Core Capabilities

#### File System Operations

- **File Management**: `read_file`, `write_file`, `create_directory`, `delete_file`
- **Directory Operations**: `list_files`, recursive directory traversal
- **Path Validation**: Sandboxed workspace security with path traversal prevention
- **Binary & Text Support**: Handles all file types with encoding detection

#### Secure Shell Execution

- **Allowlisted Commands**: Configurable command security with explicit permissions
- **Sandboxed Environment**: Protected execution within workspace boundaries
- **Timeout Controls**: Prevents runaway processes with configurable timeouts
- **Parameter Validation**: Input sanitization and injection prevention

#### Intelligent Code Operations

- **Code Generation**: LLM-powered code creation with context awareness
- **Code Analysis**: Structure analysis, dependency detection, quality assessment
- **Code Optimization**: Performance improvements and efficiency enhancements
- **Code Debugging**: Error identification and solution provision
- **Code Refactoring**: Structure and maintainability improvements
- **Code Explanation**: Detailed code functionality explanations
- **Multi-language Support**: Python, JavaScript, TypeScript, and more

#### Pattern Learning

- **Success Rate Tracking**: Monitors operation success rates
- **Pattern Recognition**: Identifies successful patterns
- **Adaptive Learning**: Improves based on historical data
- **Pattern Storage**: Persistent pattern storage in `patterns.json`

### Model Preferences (Enhanced Simple Coder)

The enhanced version uses different models for different tasks:

- **Code Generation**: `gemini-2.0-flash`
- **Code Analysis**: `gemini-1.5-pro-latest`
- **Debugging**: `gemini-2.0-flash`
- **Optimization**: `gemini-1.5-pro-latest`
- **Documentation**: `gemini-2.0-flash`
- **Shell Tasks**: `gemini-2.0-flash`
- **File Operations**: `gemini-1.5-pro-latest`

### Dependencies

- `asyncio` - Asynchronous operations
- `pathlib` - Path handling
- `LLMHandlerInterface` - LLM integration (provided by mindX framework)
- `MemoryAgent` - Memory integration
- `BaseTool` - Base class for tool integration

### Configuration

Governed by `data/config/SimpleCoder.config`:
- `command_timeout_seconds` - Command execution timeout
- `allowed_commands` - Explicit command allowlist with:
  - Category
  - Description
  - Required parameters
  - Command structure

---

## Sandbox System

### Unified Sandbox Structure

All SimpleCoder components use the same sandbox directory:

```
simple_coder_sandbox/
├── working/              # Default working directory (used by all agents)
├── completed/            # Completed files
├── projects/            # Additional organization (backward compatible)
├── temp/                # Temporary files (backward compatible)
├── tests/               # Test files (backward compatible)
├── update_requests.json  # Shared update request tracking
└── patterns.json        # Shared learned patterns
```

### Sandbox Features

1. **Unified Location**: All agents use `simple_coder_sandbox/`
2. **Working Directory**: Defaults to `simple_coder_sandbox/working/`
3. **Path Validation**: All operations restricted to sandbox root
4. **Update Request Integration**: Shared update request system
5. **Pattern Sharing**: Learned patterns shared between agents

### Update Request System

Update requests are automatically created when processing directives in sandbox mode:

**Update Request Format:**
```json
{
  "request_id": "update_1234567890_1",
  "original_file": "augmentic.py",
  "sandbox_file": "simple_coder_sandbox/working/augmentic.py",
  "changes": [
    {
      "file": "simple_coder_sandbox/working/augmentic.py",
      "type": "modification",
      "changes": [
        {
          "line": 1585,
          "old": "",
          "new": "def improved_function():\n    ..."
        }
      ]
    }
  ],
  "cycle": 1,
  "timestamp": "2026-01-30T18:50:09.599426",
  "status": "pending",
  "backup_created": true
}
```

**Update Request Lifecycle:**
1. Created with status "pending" during sandbox operations
2. Stored in `simple_coder_sandbox/update_requests.json`
3. Can be approved or rejected via UI or API
4. Approved requests apply changes to original file
5. Rejected requests are logged for learning

### Pattern Learning System

Patterns are stored in `simple_coder_sandbox/patterns.json`:

```json
{
  "file_patterns": {
    "augmentic": [
      {
        "directive": "evolve augmentic.py",
        "cycle": 1,
        "timestamp": 1234567890.0
      }
    ]
  },
  "code_patterns": {},
  "success_rates": {
    "augmentic": [
      {
        "cycle": 1,
        "success": true,
        "changes_count": 1,
        "timestamp": 1234567890.0
      }
    ]
  }
}
```

---

## Memory Integration

### Overview

The SimpleCoder agent has been enhanced with comprehensive memory integration capabilities using the `memory_agent.py` system. This integration allows SimpleCoder to store, track, and learn from all its operations by logging them to structured memory files in the data folder.

### Integration Flow

```
SimpleCoder Operation → Memory Logging Method → MemoryAgent → JSON File Storage
```

### Memory System Structure

The SimpleCoder system has comprehensive memory integration using the `memory_agent.py` system:

```
data/memory/
├── stm/                          # Short-Term Memory
│   ├── simple_coder/             # SimpleCoder agent memories
│   │   ├── cycles/               # Cycle operations
│   │   ├── file_operations/      # File operations
│   │   ├── update_requests/      # Update request operations
│   │   └── errors/               # Error logs
│   └── simple_coder_agent/      # SimpleCoderAgent memories
│       └── 20260130/             # Date-organized memories
├── ltm/                          # Long-Term Memory
│   └── pattern_learning/         # Pattern learning data
├── context/                      # Context management
└── analytics/                   # Memory analytics
```

### Core Components

- **SimpleCoder**: Main agent with memory integration
- **MemoryAgent**: Handles memory storage and retrieval
- **Memory Types**: STM (Short-Term Memory) and LTM (Long-Term Memory)
- **Categories**: Organized by operation type (cycles, file_operations, etc.)

### File System Organization

#### Memory File Naming Convention

Memory files follow a consistent naming pattern:
```
{timestamp}_{random_id}.{category}.mem.json
```

**Examples:**
- `20250919135247_993627.cycles.mem.json`
- `20250919135247_997570.cycles.mem.json`
- `20250919135248_123456.file_operations.mem.json`

#### Directory Structure Details

**Short-Term Memory (STM)**:
- **Purpose**: Stores recent operations and temporary data
- **Retention**: Configurable (default: 30 days)
- **Categories**:
  - `cycles/` - Processing cycles and iterations
  - `file_operations/` - File creation, modification, backup operations
  - `update_requests/` - Update request creation and management
  - `errors/` - Error logs and exception tracking

**Long-Term Memory (LTM)**:
- **Purpose**: Stores persistent knowledge and patterns
- **Retention**: Permanent
- **Categories**:
  - `pattern_learning/` - Learned patterns and success rates

### Memory Categories

#### 1. Cycles Memory (`cycles/`)

Tracks processing cycles and their outcomes:

```json
{
  "timestamp_utc": "2025-09-19T20:52:47.997604",
  "memory_type": "STM",
  "category": "simple_coder/cycles",
  "metadata": {
    "agent": "simple_coder",
    "sandbox_mode": true,
    "autonomous_mode": true,
    "cycle_count": 1
  },
  "data": {
    "cycle": 1,
    "directive": "evolve test_file.py",
    "timestamp": "2025-09-19T13:52:47.997477",
    "status": "completed",
    "results": {
      "changes_made": 3,
      "update_requests": 1,
      "success": true
    }
  }
}
```

#### 2. File Operations Memory (`file_operations/`)

Tracks file operations (backups, modifications, creations):

```json
{
  "timestamp_utc": "2025-09-19T20:52:48.123456",
  "memory_type": "STM",
  "category": "simple_coder/file_operations",
  "metadata": {
    "agent": "simple_coder",
    "sandbox_mode": true,
    "autonomous_mode": false,
    "cycle_count": 1
  },
  "data": {
    "operation": "backup",
    "file_path": "test_file.py",
    "success": true,
    "timestamp": "2025-09-19T13:52:48.123456",
    "details": {
      "backup_path": "simple_coder_backups/by_date/2025-09-19/test_file_20250919_135248_abc123.bak"
    }
  }
}
```

#### 3. Update Requests Memory (`update_requests/`)

Tracks update request creation and management:

```json
{
  "timestamp_utc": "2025-09-19T20:52:48.234567",
  "memory_type": "STM",
  "category": "simple_coder/update_requests",
  "metadata": {
    "agent": "simple_coder",
    "sandbox_mode": true,
    "autonomous_mode": true,
    "cycle_count": 1
  },
  "data": {
    "request_id": "update_1758314347_1",
    "original_file": "test_file.py",
    "sandbox_file": "simple_coder_sandbox/working/test_file.py",
    "timestamp": "2025-09-19T13:52:48.234567",
    "status": "pending",
    "changes_count": 3
  }
}
```

#### 4. Errors Memory (`errors/`)

Tracks errors and exceptions for debugging and learning:

```json
{
  "timestamp_utc": "2025-09-19T20:52:48.345678",
  "memory_type": "STM",
  "category": "simple_coder/errors",
  "metadata": {
    "agent": "simple_coder",
    "sandbox_mode": true,
    "autonomous_mode": false,
    "cycle_count": 1
  },
  "data": {
    "error_type": "FileNotFoundError",
    "error_message": "Target file not found: missing_file.py",
    "timestamp": "2025-09-19T13:52:48.345678",
    "context": {
      "directive": "evolve missing_file.py",
      "cycle": 1
    }
  }
}
```

### Memory Integration Methods

#### Core Memory Method

```python
async def _log_to_memory(self, memory_type: str, category: str, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Optional[Path]:
    """Log information to memory agent if available."""
    if not self.memory_agent:
        return None
    
    try:
        if metadata is None:
            metadata = {}
        
        # Add simple_coder specific metadata
        metadata.update({
            "agent": "simple_coder",
            "sandbox_mode": self.sandbox_mode,
            "autonomous_mode": self.autonomous_mode,
            "cycle_count": self.cycle_count
        })
        
        # Use the memory agent's save_memory method
        return await self.memory_agent.save_memory(memory_type, category, data, metadata)
    except Exception as e:
        logger.error(f"Failed to log to memory: {e}")
        return None
```

#### Specialized Logging Methods

1. **Cycle Logging**:
   - `_log_cycle_start()` - Logs cycle initiation
   - `_log_cycle_completion()` - Logs cycle completion with results

2. **File Operation Logging**:
   - `_log_file_operation()` - Logs file operations (backup, modify, create)

3. **Update Request Logging**:
   - `_log_update_request()` - Logs update request creation
   - `_save_update_requests()` - Saves update requests to `simple_coder_sandbox/update_requests.json`

4. **Error Logging**:
   - `_log_error()` - Logs errors and exceptions

### Memory Initialization

```python
# Memory agent integration
self.memory_agent = None
if MEMORY_AVAILABLE:
    try:
        self.memory_agent = MemoryAgent()
        logger.info("Memory agent initialized for simple_coder")
    except Exception as e:
        logger.warning(f"Failed to initialize memory agent: {e}")
        self.memory_agent = None
```

### Memory Data Format

#### Standard Memory Record Structure

```json
{
  "timestamp_utc": "ISO 8601 timestamp",
  "memory_type": "STM|LTM",
  "category": "simple_coder/cycles|simple_coder/file_operations|simple_coder/update_requests|simple_coder/errors",
  "metadata": {
    "agent": "simple_coder",
    "sandbox_mode": boolean,
    "autonomous_mode": boolean,
    "cycle_count": integer
  },
  "data": {
    // Category-specific data structure
  }
}
```

#### Metadata Fields

- **agent**: Always "simple_coder" or "simple_coder_agent"
- **sandbox_mode**: Whether sandbox mode is enabled
- **autonomous_mode**: Whether autonomous mode is enabled
- **cycle_count**: Current cycle count when operation occurred

### Agent-Specific Organization

The memory system organizes memories by agent name for better clarity and organization:

```
/home/hacker/mindX/data/memory/stm/
├── simple_coder/                 # SimpleCoder agent memories
│   ├── cycles/                   # Cycle operations
│   ├── file_operations/          # File operations
│   ├── update_requests/          # Update request operations
│   └── errors/                   # Error logs
├── simple_coder_agent/           # SimpleCoderAgent memories
│   └── 20260130/                 # Date-organized memories
├── id_manager_for_mastermind_prime/  # ID Manager agent memories
├── automindx_agent_main/         # AutoMindX agent memories
└── [other_agents]/               # Other agent memories
```

#### Memory Category Paths

Memory categories use agent-specific paths:
- **SimpleCoder cycles**: `simple_coder/cycles`
- **SimpleCoder file operations**: `simple_coder/file_operations`
- **SimpleCoder update requests**: `simple_coder/update_requests`
- **SimpleCoder errors**: `simple_coder/errors`
- **SimpleCoderAgent**: `simple_coder_agent/` (date-organized)

#### Benefits of Agent-Specific Organization

1. **Clear Separation**: Each agent's memories are isolated
2. **Easy Navigation**: Quick access to specific agent's logs
3. **Scalable**: Easy to add new agents without conflicts
4. **Maintainable**: Clean organization for debugging and analysis
5. **Multi-Agent Support**: Multiple agents can run simultaneously

### Memory Configuration

#### Memory Agent Configuration

The memory system uses the standard mindX configuration:

```yaml
# mindx_config.yaml
system:
  data_path: "data"
  
memory:
  stm_retention_days: 30
  ltm_retention_days: -1  # Permanent
  max_file_size: "10MB"
  compression: true
```

#### Environment Variables

```bash
# .env
MEMORY_ENABLED=true
MEMORY_STM_RETENTION_DAYS=30
MEMORY_LTM_RETENTION_DAYS=-1
MEMORY_COMPRESSION=true
```

### Memory Benefits

1. **Comprehensive Logging**: All SimpleCoder operations are tracked
2. **Structured Data**: Memory is organized for easy analysis
3. **Learning Capability**: Patterns can be identified and learned
4. **Debugging Support**: Detailed error and operation logs
5. **Integration Ready**: Memory can be used by other agents
6. **Scalable Storage**: Efficient file-based storage system

### Memory Future Enhancements

1. **Memory Analytics**: Built-in analysis tools for memory patterns
2. **Memory Compression**: Automatic compression of old memories
3. **Memory Search**: Full-text search across memory files
4. **Memory Visualization**: Dashboard for memory analysis
5. **Memory Cleanup**: Automatic cleanup of old memories
6. **Memory Export**: Export memories for external analysis

### Memory Log Analysis

```python
# Analyze memory patterns
import json
import os
from collections import Counter

def analyze_memory_patterns():
    memory_dir = "/home/hacker/mindX/data/memory/stm/simple_coder/cycles"
    patterns = []
    
    for file in os.listdir(memory_dir):
        if file.endswith('.json'):
            with open(os.path.join(memory_dir, file), 'r') as f:
                data = json.load(f)
                patterns.append(data['data']['status'])
    
    return Counter(patterns)

# Usage
patterns = analyze_memory_patterns()
print(f"Cycle completion patterns: {patterns}")
```

### Memory Retrieval Examples

```python
# Get memory agent instance
memory_agent = simple_coder.memory_agent

# Retrieve cycle memories
cycle_memories = await memory_agent.get_memories_by_category("simple_coder/cycles")

# Retrieve file operation memories
file_memories = await memory_agent.get_memories_by_category("simple_coder/file_operations")

# Retrieve update request memories
update_memories = await memory_agent.get_memories_by_category("simple_coder/update_requests")

# Retrieve error memories
error_memories = await memory_agent.get_memories_by_category("simple_coder/errors")
```

---

## Usage Guide

### Quick Start

#### Using SimpleCoder (simple_coder.py)

```python
from agents.simple_coder import SimpleCoder

# Initialize with sandbox mode
coder = SimpleCoder(sandbox_mode=True, autonomous_mode=False)

# Process a directive
results = await coder.process_directive("evolve augmentic.py - improve code quality")

# Check update requests
requests = coder.get_update_requests()
pending = [r for r in requests if r.get('status') == 'pending']

# Approve an update request
coder.approve_update_request(request_id="update_1234567890_1")

# Reject an update request
coder.reject_update_request(request_id="update_1234567890_1")
```

#### Using SimpleCoderAgent (simple_coder_agent.py)

```python
from agents.simple_coder_agent import SimpleCoderAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config

# Initialize
config = Config()
memory_agent = MemoryAgent(config=config)
coder = SimpleCoderAgent(memory_agent=memory_agent, config=config)

# Execute operations
result = await coder.execute(
    operation="read_file",
    path="augmentic.py"
)

result = await coder.execute(
    operation="analyze_code",
    file_path="augmentic.py"
)

result = await coder.execute(
    operation="generate_code",
    description="Create a REST API endpoint",
    language="python",
    style="clean"
)
```

#### Using Enhanced Simple Coder (enhanced_simple_coder.py)

```python
from agents.enhanced_simple_coder import EnhancedSimpleCoder
from agents.memory_agent import MemoryAgent

memory_agent = MemoryAgent()
coder = EnhancedSimpleCoder(memory_agent=memory_agent)

# Execute coding task
result = await coder.execute(
    operation="generate_code",
    task="Create a Python function to calculate fibonacci numbers",
    context={
        "language": "python",
        "requirements": ["recursive", "memoized"],
        "style": "clean"
    }
)
```

### BDI Agent Integration Examples

#### Example 1: Direct Execution (Dumb Mode)

A BDIAgent plan might contain an action to read a specific configuration file:

```json
{
  "type": "EXECUTE_BASH_COMMAND",
  "params": {
    "command": "safe_read_file",
    "file_path": "data/config/agint_config.json"
  }
}
```

The BDIAgent's handler would call `simple_coder.execute(**params)`.

#### Example 2: LLM-Powered Task (Smart Mode)

A BDIAgent might need to perform a more complex discovery task:

```json
{
  "type": "EXECUTE_LLM_BASH_TASK",
  "params": {
    "task": "List all files in the 'tools' directory, then read the contents of 'system_analyzer_tool.py' and provide a summary."
  }
}
```

The BDIAgent's handler would call `simple_coder.execute_llm_task(task=...)`. SimpleCoder would then manage the multi-step LLM conversation to accomplish this, providing a full log of its actions as the result.

### Autonomous Mode

```python
# Initialize with autonomous mode
coder = SimpleCoder(sandbox_mode=True, autonomous_mode=True)

# Process directive - will run infinite cycles until stopped
results = await coder.process_directive("evolve mindX")

# Check status
status = coder.get_status()
print(f"Cycle count: {status['cycle_count']}")
print(f"Infinite mode: {status['infinite_mode']}")
```

---

## Integration Guide

### Integration with mindX Backend

The backend service provides API endpoints for Simple Coder operations:

```python
# Get status
GET /simple-coder/status

# Get update requests
GET /simple-coder/update-requests

# Approve update request
POST /simple-coder/approve-update/{request_id}

# Reject update request
POST /simple-coder/reject-update/{request_id}
```

### Integration with Memory Agent

```python
from agents.memory_agent import MemoryAgent

memory_agent = MemoryAgent()

# Get memories by category
cycle_memories = await memory_agent.get_memories_by_category("simple_coder/cycles")
file_memories = await memory_agent.get_memories_by_category("simple_coder/file_operations")
```

### Integration with BDI Agent

SimpleCoder is integrated with BDI Agent through action handlers:

```python
# BDI Agent can use SimpleCoder actions in its plans
actions = [
    {
        "type": "EXECUTE_BASH_COMMAND",
        "params": {
            "command": "read_file",
            "path": "config.json"
        }
    },
    {
        "type": "GENERATE_CODE",
        "params": {
            "description": "Create authentication middleware",
            "language": "python"
        }
    }
]
```

---

## Limitations & Constraints

### General Limitations

1. **LLM Handler Requirement**: Advanced features (code generation, analysis) require an LLM handler to be configured. Without it, these operations will return errors.

2. **Sandbox Restrictions**: 
   - All file operations are restricted to the sandbox directory
   - Path traversal outside sandbox is prevented
   - Only allowlisted file extensions are permitted

3. **Command Allowlist**: 
   - Only commands in the allowlist can be executed
   - Commands must be explicitly configured in `data/config/SimpleCoder.config`
   - Shell injection is prevented through parameter validation

4. **Timeout Constraints**: 
   - All shell commands have configurable timeouts (default: 60 seconds)
   - Long-running operations may be terminated

5. **File Size Limits**: 
   - Maximum file size is configurable (default: 10MB)
   - Large files may not be processed

6. **Memory Storage**: 
   - Memory files are stored on disk
   - Large numbers of operations may consume significant disk space
   - STM retention is configurable (default: 30 days)

### Component-Specific Limitations

#### simple_coder.py

- **Cycle Counter**: Currently stuck at cycle 1 in some scenarios (known issue)
- **Repetitive Code Generation**: May generate duplicate code if not properly deduplicated
- **File Type Validation**: Limited to specific file extensions
- **Update Request Management**: Manual approval/rejection required

#### simple_coder_agent.py

- **LLM Dependency**: Most advanced operations require LLM handler
- **Missing Helper Methods**: Some helper methods referenced but not fully implemented:
  - `_get_project_structure()`
  - `_analyze_file_types()`
  - `_analyze_dependencies()`
  - `_analyze_complexity()`
  - `_generate_api_docs()`
  - `_generate_readme()`
  - `_generate_technical_docs()`

#### enhanced_simple_coder.py

- **Model Availability**: Requires specific LLM models to be available
- **Multi-Model Selection**: Model selection logic may not always choose optimal model

### Known Issues

1. **Repetitive Code Generation**: 
   - Issue: Same code added repeatedly to files
   - Impact: Files can become bloated with duplicates
   - Workaround: Manual cleanup or deduplication logic needed

2. **Cycle Counter Stuck**: 
   - Issue: Cycle counter may not increment properly
   - Impact: All cycles show as cycle 1
   - Workaround: Track cycles per directive, not globally

3. **File Type Confusion**: 
   - Issue: HTML files may receive Python code
   - Impact: Incorrect code generation for non-Python files
   - Workaround: Better file type detection needed

4. **High Rejection Rate**: 
   - Issue: Most update requests are rejected
   - Impact: Low success rate for generated changes
   - Workaround: Improve validation before creating requests

---

## Security & Safety

### Security Features

#### 1. Shell Injection Prevention

All commands are executed using `asyncio.create_subprocess_exec`, which passes arguments as a list. This prevents a parameter like `"; rm -rf /"` from being executed as a command.

**Example:**
```python
# Safe - arguments passed as list
await asyncio.create_subprocess_exec('python', 'script.py', user_input)

# Dangerous - would be vulnerable to injection
await asyncio.create_subprocess_shell(f'python script.py {user_input}')
```

#### 2. Sandbox Path Traversal Prevention

The tool establishes a `workspace_root` (sandbox root). A validation method ensures any file path is resolved and confirmed to be within this sandboxed boundary, preventing access to sensitive system files.

**Implementation:**
```python
def _resolve_and_check_path(self, path_str: str) -> Optional[Path]:
    """Resolves a path relative to the CWD and ensures it's within the sandbox."""
    resolved_path = (self.current_working_directory / path_str).resolve()
    
    if not resolved_path.is_relative_to(self.sandbox_root):
        self.logger.error(f"Path Traversal DENIED. Attempt to access '{path_str}' which resolves outside the sandbox.")
        return None
    return resolved_path
```

#### 3. Command Timeouts

All external shell commands are run with a configurable timeout, preventing a runaway or hanging process from freezing the entire mindX system.

**Configuration:**
```json
{
  "command_timeout_seconds": 60
}
```

#### 4. Robust, Native File I/O

Core read/write operations (`safe_read_file`, `safe_write_file`) use native Python functions, bypassing the shell entirely to avoid complex character escaping issues and improve reliability.

#### 5. Explicit Allowlist

The tool's capabilities are defined in an external config file (`data/config/SimpleCoder.config`). System operators can easily add, remove, or modify the agent's powers without touching its source code.

**Example Config:**
```json
{
  "allowed_shell_commands": [
    "python", "python3", "pip", "pip3", "git", "ls", "cat", "grep"
  ],
  "command_timeout_seconds": 60,
  "max_file_size_mb": 10
}
```

#### 6. File Extension Validation

Only specific file extensions are allowed for operations:

```python
allowed_extensions = ['.py', '.js', '.html', '.css', '.json', '.md', '.txt', '.yml', '.yaml']
```

#### 7. Dangerous Path Prevention

Operations on system files are blocked:

```python
dangerous_paths = ['/etc/', '/sys/', '/proc/', '/dev/', '/boot/']
if any(file_path.startswith(path) for path in dangerous_paths):
    logger.warning(f"Blocked operation on system path: {file_path}")
    return False
```

---

## Troubleshooting

### Common Issues

#### 1. Memory Agent Not Initialized

**Symptom**: `self.memory_agent` is `None`

**Cause**: Import error or configuration issue

**Solution**: 
```python
# Check import
from agents.memory_agent import MemoryAgent

# Check initialization
if coder.memory_agent:
    print("Memory agent available")
else:
    print("Memory agent not initialized - check configuration")
```

#### 2. Memory Files Not Created

**Symptom**: No files in memory directories

**Cause**: Permission issues or directory not created

**Solution**: 
```bash
# Check directory permissions
ls -la /home/hacker/mindX/data/memory/stm/

# Ensure data folder exists
mkdir -p data/memory/stm/simple_coder/{cycles,file_operations,update_requests,errors}
```

#### 3. Update Requests Not Appearing

**Symptom**: Update requests not created

**Cause**: Sandbox mode not enabled

**Solution**: 
```python
# Ensure sandbox mode is enabled
coder = SimpleCoder(sandbox_mode=True)  # Must be True
```

#### 4. Files Not in Sandbox

**Symptom**: Files created outside sandbox

**Cause**: Incorrect path usage

**Solution**: 
```python
# Use sandbox path helper
working_file = coder._get_sandbox_path("file.py")
# Returns: simple_coder_sandbox/working/file.py
```

#### 5. LLM Handler Not Available

**Symptom**: Code generation/analysis returns "LLM handler not available"

**Cause**: LLM handler not configured

**Solution**: 
```python
# Configure LLM handler
from llm.llm_factory import get_llm_handler

llm_handler = get_llm_handler(config=config)
coder = SimpleCoderAgent(llm_handler=llm_handler, ...)
```

#### 6. Path Traversal Denied

**Symptom**: "Path Traversal DENIED" errors

**Cause**: Attempting to access files outside sandbox

**Solution**: 
```python
# Use relative paths within sandbox
# Correct:
result = await coder.execute(operation="read_file", path="file.py")

# Incorrect:
result = await coder.execute(operation="read_file", path="/etc/passwd")  # Will be denied
```

#### 7. Command Not in Allowlist

**Symptom**: "Command 'X' is not in the allowlist"

**Cause**: Command not configured in allowlist

**Solution**: 
```json
// Add to data/config/SimpleCoder.config
{
  "allowed_shell_commands": [
    "python", "python3", "your_command_here"
  ]
}
```

### Debug Commands

```bash
# Check memory directory structure
ls -la /home/hacker/mindX/data/memory/stm/

# Check specific category
ls -la /home/hacker/mindX/data/memory/stm/simple_coder/cycles/

# View memory file content
cat /home/hacker/mindX/data/memory/stm/simple_coder/cycles/*.json | jq .

# Check update requests
cat simple_coder_sandbox/update_requests.json | jq .

# Check patterns
cat simple_coder_sandbox/patterns.json | jq .

# Check sandbox structure
tree simple_coder_sandbox/
```

---

## Best Practices

### 1. Always Use Sandbox Mode for Testing

```python
# Good - sandbox mode enabled
coder = SimpleCoder(sandbox_mode=True, autonomous_mode=False)

# Bad - direct file modification
coder = SimpleCoder(sandbox_mode=False)  # Not recommended
```

### 2. Review Update Requests Before Approving

```python
# Get and review requests
requests = coder.get_update_requests()
for req in requests:
    if req.get('status') == 'pending':
        # Review changes
        print(f"Reviewing: {req.get('request_id')}")
        print(f"Changes: {req.get('changes')}")
        # Then approve or reject
        if changes_look_good:
            coder.approve_update_request(req['request_id'])
        else:
            coder.reject_update_request(req['request_id'])
```

### 3. Monitor Memory Logs

```python
# Check recent memory logs
from pathlib import Path

memory_dir = Path("data/memory/stm/simple_coder")
recent_files = sorted(
    memory_dir.rglob("*.json"), 
    key=lambda x: x.stat().st_mtime, 
    reverse=True
)[:10]

for f in recent_files:
    print(f"Recent memory: {f.name}")
```

### 4. Use Pattern Learning

```python
# Review learned patterns
patterns = coder.patterns
print(f"Learned patterns: {len(patterns.get('file_patterns', {}))}")

# Use patterns to inform decisions
for file_key, file_patterns in patterns.get('file_patterns', {}).items():
    success_rate = calculate_success_rate(file_patterns)
    print(f"{file_key}: {success_rate}% success rate")
```

### 5. Implement Deduplication

```python
# Check for duplicate code before adding
def check_duplicate(content, new_code):
    if new_code in content:
        logger.warning("Duplicate code detected, skipping")
        return False
    return True
```

### 6. Proper Error Handling

```python
try:
    results = await coder.process_directive(directive)
    if results.get('error'):
        logger.error(f"Error: {results['error']}")
        # Handle error appropriately
except Exception as e:
    logger.error(f"Exception: {e}", exc_info=True)
    # Handle exception
```

### 7. Configure Timeouts Appropriately

```python
# For long-running operations, increase timeout
config_data = {
    "command_timeout_seconds": 300  # 5 minutes for complex operations
}
```

---

## API Reference

### SimpleCoder (simple_coder.py)

#### Methods

**`process_directive(directive: str, target_file: Optional[str] = None) -> Dict[str, Any]`**
- Process a directive and create update requests
- Returns: Results dictionary with changes, update requests, and status

**`get_update_requests() -> List[Dict[str, Any]]`**
- Get all update requests
- Returns: List of update request dictionaries

**`approve_update_request(request_id: str) -> bool`**
- Approve and apply an update request
- Returns: True if successful, False otherwise

**`reject_update_request(request_id: str) -> bool`**
- Reject an update request
- Returns: True if successful, False otherwise

**`get_status() -> Dict[str, Any]`**
- Get current status
- Returns: Status dictionary with cycle count, mode, etc.

**`update_mode(autonomous_mode: bool = None, max_cycles: int = None)`**
- Update autonomous mode and max cycles
- Parameters: autonomous_mode, max_cycles

### SimpleCoderAgent (simple_coder_agent.py)

#### Methods

**`execute(operation: str = None, **kwargs) -> Dict[str, Any]`**
- Execute an operation
- Operations: `read_file`, `write_file`, `analyze_code`, `generate_code`, etc.
- Returns: Result dictionary with status and data

**Available Operations:**
- `list_files` - List directory contents
- `change_directory` - Change working directory
- `read_file` - Read file contents
- `write_file` - Write file contents
- `create_directory` - Create directory
- `delete_file` - Delete file (requires force=True)
- `run_shell` - Execute shell command
- `create_venv` - Create virtual environment
- `activate_venv` - Activate virtual environment
- `deactivate_venv` - Deactivate virtual environment
- `analyze_code` - Analyze code quality
- `generate_code` - Generate code
- `optimize_code` - Optimize code
- `debug_code` - Debug code
- `test_code` - Generate tests
- `refactor_code` - Refactor code
- `explain_code` - Explain code
- `analyze_project` - Analyze project structure
- `suggest_improvements` - Suggest improvements
- `create_documentation` - Generate documentation
- `learn_from_execution` - Learn from execution results
- `get_coding_suggestions` - Get intelligent suggestions

---

## Examples

### Example 1: Basic File Operation

```python
from agents.simple_coder_agent import SimpleCoderAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config

config = Config()
memory_agent = MemoryAgent(config=config)
coder = SimpleCoderAgent(memory_agent=memory_agent, config=config)

# Read a file
result = await coder.execute(
    operation="read_file",
    path="augmentic.py"
)

if result.get("status") == "SUCCESS":
    content = result.get("content")
    print(f"File content: {len(content)} characters")
```

### Example 2: Code Analysis

```python
# Analyze code quality
result = await coder.execute(
    operation="analyze_code",
    file_path="augmentic.py"
)

if result.get("status") == "SUCCESS":
    analysis = result.get("analysis")
    print(f"Analysis: {analysis}")
```

### Example 3: Code Generation

```python
# Generate code
result = await coder.execute(
    operation="generate_code",
    description="Create a REST API endpoint for user authentication",
    language="python",
    style="clean"
)

if result.get("status") == "SUCCESS":
    generated_code = result.get("generated_code")
    print(f"Generated code: {generated_code}")
```

### Example 4: Update Request Workflow

```python
from agents.simple_coder import SimpleCoder

# Initialize
coder = SimpleCoder(sandbox_mode=True)

# Process directive (creates update request)
results = await coder.process_directive("evolve file.py - add error handling")

# Get update requests
requests = coder.get_update_requests()
pending = [r for r in requests if r.get('status') == 'pending']

# Review and approve
for req in pending:
    print(f"Reviewing: {req['request_id']}")
    # Review changes...
    coder.approve_update_request(req['request_id'])
```

### Example 5: Autonomous Mode

```python
# Initialize with autonomous mode
coder = SimpleCoder(sandbox_mode=True, autonomous_mode=True)

# Process directive - will run infinite cycles
results = await coder.process_directive("evolve mindX")

# Monitor status
while True:
    status = coder.get_status()
    print(f"Cycle: {status['cycle_count']}")
    if not status.get('continue_autonomous', False):
        break
    await asyncio.sleep(1)
```

### Example 6: Memory Integration

```python
# Access memory logs
from agents.memory_agent import MemoryAgent

memory_agent = MemoryAgent()

# Get cycle memories
cycle_memories = await memory_agent.get_memories_by_category("simple_coder/cycles")

# Analyze patterns
for memory in cycle_memories:
    data = memory.get('data', {})
    if data.get('status') == 'completed':
        print(f"Cycle {data.get('cycle')}: {data.get('directive')}")
```

---

## NFT Metadata

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX SimpleCoder",
  "description": "Comprehensive coding agent system with sandbox mode, autonomous operation, multi-model intelligence, and full memory integration",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/simple_coder",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "coding_agent"
    },
    {
      "trait_type": "Capability",
      "value": "Code Generation & Analysis"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.88
    },
    {
      "trait_type": "Sandbox Mode",
      "value": "Yes"
    },
    {
      "trait_type": "Autonomous Mode",
      "value": "Yes"
    },
    {
      "trait_type": "UI Integration",
      "value": "Yes"
    },
    {
      "trait_type": "Memory Integration",
      "value": "Yes"
    },
    {
      "trait_type": "Multi-Model Support",
      "value": "Yes"
    },
    {
      "trait_type": "Version",
      "value": "7.0"
    }
  ],
  "intelligence": {
    "prompt": "You are a comprehensive coding agent in the mindX ecosystem with sandbox mode, autonomous operation capabilities, multi-model intelligence, and UI integration. Your purpose is to generate and execute code changes, manage file updates with UI integration, learn from patterns, and operate autonomously when needed. You maintain sandbox security, provide update requests for UI approval, learn from execution patterns, and use intelligent model selection for optimal results.",
    "persona": {
      "name": "Code Specialist",
      "role": "coder",
      "description": "Comprehensive coding specialist with sandbox, autonomous, and multi-model capabilities",
      "communication_style": "Technical, precise, helpful",
      "behavioral_traits": [
        "code-focused",
        "intelligent",
        "sandbox-oriented",
        "autonomous",
        "ui-integrated",
        "pattern-learning",
        "multi-model",
        "memory-integrated"
      ],
      "expertise_areas": [
        "code_generation",
        "code_analysis",
        "code_execution",
        "file_operations",
        "sandbox_management",
        "autonomous_operation",
        "ui_integration",
        "pattern_learning",
        "memory_integration",
        "multi_model_selection"
      ],
      "beliefs": {
        "sandbox_security": true,
        "autonomous_operation": true,
        "ui_collaboration": true,
        "pattern_learning": true,
        "multi_model_intelligence": true,
        "memory_integration": true
      },
      "desires": {
        "secure_execution": "high",
        "autonomous_operation": "high",
        "ui_collaboration": "high",
        "pattern_learning": "high",
        "efficient_execution": "high",
        "code_quality": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "agent_id": "simple_coder",
    "capabilities": [
      "code_generation",
      "code_execution",
      "file_operations",
      "sandbox_management",
      "autonomous_operation",
      "ui_integration",
      "pattern_learning"
    ],
    "endpoint": "https://mindx.internal/simple_coder/a2a",
    "protocol_version": "2.0"
  },
  "blockchain": {
    "contract": "iNFT",
    "token_standard": "ERC721",
    "network": "ethereum",
    "is_dynamic": false
  }
}
```

### dNFT (Dynamic NFT) Metadata

```json
{
  "name": "mindX SimpleCoder",
  "description": "Coding agent - Dynamic",
  "attributes": [
    {
      "trait_type": "Cycles Executed",
      "value": 12500,
      "display_type": "number"
    },
    {
      "trait_type": "Files Modified",
      "value": 3420,
      "display_type": "number"
    },
    {
      "trait_type": "Patterns Learned",
      "value": 189,
      "display_type": "number"
    },
    {
      "trait_type": "Update Requests",
      "value": 98,
      "display_type": "number"
    },
    {
      "trait_type": "Success Rate",
      "value": 85.5,
      "display_type": "number"
    },
    {
      "trait_type": "Last Execution",
      "value": "2026-01-30T18:50:09Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": [
      "cycles_executed",
      "files_modified",
      "patterns_learned",
      "update_requests",
      "success_rate",
      "execution_metrics"
    ]
  }
}
```

---

## File Locations

- **simple_coder.py**: `agents/simple_coder.py`
- **simple_coder_agent.py**: `agents/simple_coder_agent.py`
- **enhanced_simple_coder.py**: `agents/enhanced_simple_coder.py`
- **Sandbox Directory**: `simple_coder_sandbox/`
- **Backup Directory**: `simple_coder_backups/`
- **Configuration**: `data/config/SimpleCoder.config`
- **Memory Logs**: `data/memory/stm/simple_coder/` and `data/memory/stm/simple_coder_agent/`

---

---

## Complete Reference

This document serves as the complete reference for all SimpleCoder implementations. It consolidates information from:

- `simple_coder.py` - Enhanced coding agent with sandbox and autonomous modes
- `simple_coder_agent.py` - BDI-integrated coding assistant
- `enhanced_simple_coder.py` - Multi-model comprehensive agent
- Memory integration system
- Sandbox system
- Update request system
- Pattern learning system
- Test results and analysis

For the most up-to-date information, refer to this document as the single source of truth for SimpleCoder documentation.

**Last Updated**: January 30, 2026  
**Maintained By**: mindX Documentation System  
**For Issues**: See project repository
