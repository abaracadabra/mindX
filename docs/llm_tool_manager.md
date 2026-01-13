# LLM Tool Manager Documentation

## Overview

The `LLMToolManager` provides specialized management for LLM tools in the official tools registry. It handles adding, removing, and updating LLM tools with automatic A2A model card creation and cryptographic identity management.

**File**: `tools/llm_tool_manager.py`  
**Class**: `LLMToolManager`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **LLM-Specific**: Focused on LLM tool management
2. **Model Card Creation**: Automatic A2A model card generation
3. **Identity Management**: Cryptographic identity integration
4. **Registry Integration**: Direct registry modification
5. **Error Handling**: Comprehensive error handling

### Core Components

```python
class LLMToolManager(BaseTool):
    - memory_agent: MemoryAgent - For workspace management
    - tool_registry_path: Path - Tools registry file path
    - model_cards_path: Path - Model cards directory
```

## Available Actions

### 1. `add`

Adds a new LLM tool to the registry.

**Parameters**:
- `action` (str, required): "add"
- `tool_id` (str, required): Tool identifier
- `tool_config` (Dict, required): Tool configuration

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 2. `remove`

Removes an LLM tool from the registry.

**Parameters**:
- `action` (str, required): "remove"
- `tool_id` (str, required): Tool to remove

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 3. `update`

Updates an existing LLM tool in the registry.

**Parameters**:
- `action` (str, required): "update"
- `tool_id` (str, required): Tool to update
- `tool_config` (Dict, required): Updated configuration

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

## Usage

### Add LLM Tool

```python
from tools.llm_tool_manager import LLMToolManager
from agents.memory_agent import MemoryAgent

manager = LLMToolManager(memory_agent=memory_agent)

# Add LLM tool
success, message = await manager.execute(
    action="add",
    tool_id="custom_llm_tool",
    tool_config={
        "name": "Custom LLM Tool",
        "description": "Specialized LLM tool",
        "version": "1.0.0",
        "enabled": True,
        "commands": [...],
        "access_control": {...}
    }
)
```

### Update LLM Tool

```python
# Update LLM tool
success, message = await manager.execute(
    action="update",
    tool_id="custom_llm_tool",
    tool_config={
        "name": "Updated LLM Tool",
        "version": "2.0.0"
    }
)
```

## Model Card Creation

### Automatic Model Card Generation

When adding or updating LLM tools:
1. Gets or creates identity via IDManagerAgent
2. Creates A2A model card
3. Signs the model card
4. Saves to model cards directory

### Model Card Structure

```json
{
    "id": "tool_id",
    "name": "Tool Name",
    "description": "Tool description",
    "type": "tool",
    "version": "1.0.0",
    "enabled": true,
    "commands": [...],
    "access_control": {...},
    "identity": {
        "public_address": "0x...",
        "signature": "..."
    },
    "a2a_endpoint": "https://mindx.internal/{tool_id}/a2a"
}
```

## Features

### 1. LLM Tool Focus

Specialized for LLM tools:
- LLM-specific configurations
- Model card generation
- Identity management

### 2. Model Card Integration

Creates A2A model cards:
- Cryptographic identity
- Endpoint definition
- Tool metadata

### 3. Identity Management

Integrates with IDManagerAgent:
- Gets existing identity
- Creates new identity if needed
- Signs model cards

## Limitations

### Current Limitations

1. **LLM-Specific Only**: Only for LLM tools
2. **No Validation**: Limited config validation
3. **No Rollback**: No rollback capability
4. **Basic Operations**: Simple add/remove/update
5. **No Versioning**: No version history

### Recommended Improvements

1. **Enhanced Validation**: Comprehensive validation
2. **Rollback Support**: Rollback failed operations
3. **Version Control**: Version history
4. **LLM Testing**: Test LLM tools
5. **Model Management**: LLM model management
6. **Performance Tracking**: Track LLM tool performance
7. **Consolidation**: Consider merging with RegistryManagerTool

## Integration

### With IDManagerAgent

Manages identities:
```python
id_manager = await IDManagerAgent.get_instance()
identity = await id_manager.get_identity(item_id)
```

### With Memory Agent

Manages model cards:
```python
self.model_cards_path = self.memory_agent.get_agent_data_directory("a2a_model_cards")
```

## Examples

### Complete LLM Tool Lifecycle

```python
# 1. Add LLM tool
await manager.execute("add", "llm_analyzer", {...})

# 2. Update LLM tool
await manager.execute("update", "llm_analyzer", {...})

# 3. Remove LLM tool
await manager.execute("remove", "llm_analyzer")
```

## Technical Details

### Dependencies

- `core.id_manager_agent.IDManagerAgent`: Identity management
- `agents.memory_agent.MemoryAgent`: Workspace management
- `core.bdi_agent.BaseTool`: Base tool class

### Registry File

Tools registry located at:
```
data/config/official_tools_registry.json
```

### Model Cards Directory

Model cards stored in:
```
data/memory/agent_workspaces/a2a_model_cards/
```

## Comparison with RegistryManagerTool

| Feature | LLMToolManager | RegistryManagerTool |
|---------|---------------|-------------------|
| Scope | LLM tools only | All tools + agents |
| Model Cards | Yes | Yes |
| Identity | Yes | Yes |
| Use Case | LLM tool management | General registry |

## Future Enhancements

1. **LLM Testing**: Test LLM tools
2. **Model Management**: Manage LLM models
3. **Performance Tracking**: Track performance
4. **Enhanced Validation**: Better validation
5. **Consolidation**: Merge with RegistryManagerTool
6. **Version Control**: Version history
7. **API Integration**: REST API access



