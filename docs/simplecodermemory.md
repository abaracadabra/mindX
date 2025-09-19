# SimpleCoder Memory Integration Documentation

## Overview

The SimpleCoder agent has been enhanced with comprehensive memory integration capabilities using the `memory_agent.py` system. This integration allows SimpleCoder to store, track, and learn from all its operations by logging them to structured memory files in the data folder.

## Table of Contents

1. [Architecture](#architecture)
2. [Memory System Structure](#memory-system-structure)
3. [File System Organization](#file-system-organization)
4. [Memory Types and Categories](#memory-types-and-categories)
5. [Technical Implementation](#technical-implementation)
6. [Memory Data Format](#memory-data-format)
7. [Usage Examples](#usage-examples)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

## Architecture

### Core Components

- **SimpleCoder**: Main agent with memory integration
- **MemoryAgent**: Handles memory storage and retrieval
- **Memory Types**: STM (Short-Term Memory) and LTM (Long-Term Memory)
- **Categories**: Organized by operation type (cycles, file_operations, etc.)

### Integration Flow

```
SimpleCoder Operation → Memory Logging Method → MemoryAgent → JSON File Storage
```

## Memory System Structure

### Directory Hierarchy

```
/home/hacker/mindX/data/memory/
├── stm/                          # Short-Term Memory
│   ├── cycles/                   # Cycle operations
│   ├── file_operations/          # File operations
│   ├── update_requests/          # Update request operations
│   ├── errors/                   # Error logs
│   └── agent_workspaces/         # Agent-specific workspaces
├── ltm/                          # Long-Term Memory
│   └── pattern_learning/         # Pattern learning data
├── context/                      # Context management
└── analytics/                    # Memory analytics
```

## File System Organization

### Memory File Naming Convention

Memory files follow a consistent naming pattern:
```
{timestamp}_{random_id}.{category}.mem.json
```

**Examples:**
- `20250919135247_993627.cycles.mem.json`
- `20250919135247_997570.cycles.mem.json`
- `20250919135248_123456.file_operations.mem.json`

### Directory Structure Details

#### Short-Term Memory (STM)
- **Purpose**: Stores recent operations and temporary data
- **Retention**: Configurable (default: 30 days)
- **Categories**:
  - `cycles/` - Processing cycles and iterations
  - `file_operations/` - File creation, modification, backup operations
  - `update_requests/` - Update request creation and management
  - `errors/` - Error logs and exception tracking

#### Long-Term Memory (LTM)
- **Purpose**: Stores persistent knowledge and patterns
- **Retention**: Permanent
- **Categories**:
  - `pattern_learning/` - Learned patterns and success rates

## Memory Types and Categories

### 1. Cycles Memory (`cycles/`)

**Purpose**: Track processing cycles and their outcomes

**Data Structure**:
```json
{
  "timestamp_utc": "2025-09-19T20:52:47.997604",
  "memory_type": "STM",
  "category": "cycles",
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

### 2. File Operations Memory (`file_operations/`)

**Purpose**: Track file operations (backups, modifications, creations)

**Data Structure**:
```json
{
  "timestamp_utc": "2025-09-19T20:52:48.123456",
  "memory_type": "STM",
  "category": "file_operations",
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

### 3. Update Requests Memory (`update_requests/`)

**Purpose**: Track update request creation and management

**Data Structure**:
```json
{
  "timestamp_utc": "2025-09-19T20:52:48.234567",
  "memory_type": "STM",
  "category": "update_requests",
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

### 4. Errors Memory (`errors/`)

**Purpose**: Track errors and exceptions for debugging and learning

**Data Structure**:
```json
{
  "timestamp_utc": "2025-09-19T20:52:48.345678",
  "memory_type": "STM",
  "category": "errors",
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

## Technical Implementation

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

4. **Error Logging**:
   - `_log_error()` - Logs errors and exceptions

### Initialization

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

## Memory Data Format

### Standard Memory Record Structure

```json
{
  "timestamp_utc": "ISO 8601 timestamp",
  "memory_type": "STM|LTM",
  "category": "cycles|file_operations|update_requests|errors",
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

### Metadata Fields

- **agent**: Always "simple_coder"
- **sandbox_mode**: Whether sandbox mode is enabled
- **autonomous_mode**: Whether autonomous mode is enabled
- **cycle_count**: Current cycle count when operation occurred

## Usage Examples

### Basic Memory Logging

```python
from agents.simple_coder import SimpleCoder

# Initialize SimpleCoder with memory integration
simple_coder = SimpleCoder(sandbox_mode=True, autonomous_mode=True)

# Process a directive (automatically logs to memory)
results = await simple_coder.process_directive("evolve test_file.py")

# Manual memory logging
await simple_coder._log_cycle_start(1, "test_directive")
await simple_coder._log_cycle_completion(1, "test_directive", results)
```

### Memory Retrieval

```python
# Get memory agent instance
memory_agent = simple_coder.memory_agent

# Retrieve cycle memories
cycle_memories = await memory_agent.get_memories_by_category("cycles")

# Retrieve file operation memories
file_memories = await memory_agent.get_memories_by_category("file_operations")
```

## Configuration

### Memory Agent Configuration

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

### Environment Variables

```bash
# .env
MEMORY_ENABLED=true
MEMORY_STM_RETENTION_DAYS=30
MEMORY_LTM_RETENTION_DAYS=-1
MEMORY_COMPRESSION=true
```

## Troubleshooting

### Common Issues

1. **Memory Agent Not Initialized**
   - **Symptom**: `self.memory_agent` is `None`
   - **Cause**: Import error or configuration issue
   - **Solution**: Check `agents.memory_agent` import and configuration

2. **Memory Files Not Created**
   - **Symptom**: No files in memory directories
   - **Cause**: Permission issues or directory not created
   - **Solution**: Check directory permissions and ensure data folder exists

3. **Memory Logging Errors**
   - **Symptom**: `Failed to log to memory` errors
   - **Cause**: Memory agent save operation failed
   - **Solution**: Check memory agent logs and disk space

### Debug Commands

```bash
# Check memory directory structure
ls -la /home/hacker/mindX/data/memory/stm/

# Check specific category
ls -la /home/hacker/mindX/data/memory/stm/cycles/

# View memory file content
cat /home/hacker/mindX/data/memory/stm/cycles/*.json | jq .

# Check memory agent logs
tail -f /home/hacker/mindX/logs/memory_agent.log
```

### Log Analysis

```python
# Analyze memory patterns
import json
import os
from collections import Counter

def analyze_memory_patterns():
    memory_dir = "/home/hacker/mindX/data/memory/stm/cycles"
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

## Benefits

1. **Comprehensive Logging**: All SimpleCoder operations are tracked
2. **Structured Data**: Memory is organized for easy analysis
3. **Learning Capability**: Patterns can be identified and learned
4. **Debugging Support**: Detailed error and operation logs
5. **Integration Ready**: Memory can be used by other agents
6. **Scalable Storage**: Efficient file-based storage system

## Future Enhancements

1. **Memory Analytics**: Built-in analysis tools for memory patterns
2. **Memory Compression**: Automatic compression of old memories
3. **Memory Search**: Full-text search across memory files
4. **Memory Visualization**: Dashboard for memory analysis
5. **Memory Cleanup**: Automatic cleanup of old memories
6. **Memory Export**: Export memories for external analysis

---

*This documentation covers the complete SimpleCoder memory integration system. For technical support or questions, refer to the mindX development team.*

## Updated Memory Structure (Agent-Specific)

### Agent-Specific Organization

The memory system has been updated to organize memories by agent name for better clarity and organization:

```
/home/hacker/mindX/data/memory/stm/
├── simple_coder/                 # SimpleCoder agent memories
│   ├── cycles/                   # Cycle operations
│   ├── file_operations/          # File operations
│   ├── update_requests/          # Update request operations
│   └── errors/                   # Error logs
├── id_manager_for_mastermind_prime/  # ID Manager agent memories
├── automindx_agent_main/         # AutoMindX agent memories
└── [other_agents]/               # Other agent memories
```

### Memory Category Paths

Memory categories now use agent-specific paths:
- **SimpleCoder cycles**: `simple_coder/cycles`
- **SimpleCoder file operations**: `simple_coder/file_operations`
- **SimpleCoder update requests**: `simple_coder/update_requests`
- **SimpleCoder errors**: `simple_coder/errors`

### Benefits of Agent-Specific Organization

1. **Clear Separation**: Each agent's memories are isolated
2. **Easy Navigation**: Quick access to specific agent's logs
3. **Scalable**: Easy to add new agents without conflicts
4. **Maintainable**: Clean organization for debugging and analysis
5. **Multi-Agent Support**: Multiple agents can run simultaneously

### Current SimpleCoder Memory Structure

```
/home/hacker/mindX/data/memory/stm/simple_coder/
└── cycles/
    ├── 20250919142630_123456.cycles.mem.json
    ├── 20250919142649_789012.cycles.mem.json
    └── ...
```

Each memory file contains:
- **Category**: `simple_coder/cycles`
- **Agent**: `simple_coder`
- **Memory Type**: `STM`
- **Data**: Cycle information with building parameters

