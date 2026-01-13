# Registry Manager Tool Documentation

## Overview

The `RegistryManagerTool` provides comprehensive management of both tool and agent registries. It handles adding, removing, and updating registry entries, and automatically creates A2A (Agent-to-Agent) model cards with cryptographic identities.

**File**: `tools/registry_manager_tool.py`  
**Class**: `RegistryManagerTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Dual Registry Support**: Manages both tool and agent registries
2. **Model Card Creation**: Automatically creates A2A model cards
3. **Cryptographic Identity**: Integrates with IDManagerAgent for identities
4. **Persistent Storage**: Saves registries to JSON files
5. **Error Handling**: Comprehensive error handling

### Core Components

```python
class RegistryManagerTool(BaseTool):
    - memory_agent: MemoryAgent - For workspace management
    - tool_registry_path: Path - Tools registry file path
    - agent_registry_path: Path - Agents registry file path
    - model_cards_path: Path - Model cards directory
```

## Available Actions

### 1. `add`

Adds a new tool or agent to the registry.

**Parameters**:
- `registry_type` (str, required): "tool" or "agent"
- `action` (str, required): "add"
- `item_id` (str, required): Unique identifier
- `item_config` (Dict, required): Item configuration

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 2. `remove`

Removes a tool or agent from the registry.

**Parameters**:
- `registry_type` (str, required): "tool" or "agent"
- `action` (str, required): "remove"
- `item_id` (str, required): Item to remove

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 3. `update`

Updates an existing tool or agent in the registry.

**Parameters**:
- `registry_type` (str, required): "tool" or "agent"
- `action` (str, required): "update"
- `item_id` (str, required): Item to update
- `item_config` (Dict, required): Updated configuration

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

## Usage

### Add Tool to Registry

```python
from tools.registry_manager_tool import RegistryManagerTool
from agents.memory_agent import MemoryAgent

tool = RegistryManagerTool(memory_agent=memory_agent)

# Add tool
success, message = await tool.execute(
    registry_type="tool",
    action="add",
    item_id="custom_analyzer",
    item_config={
        "name": "Custom Analyzer",
        "description": "Specialized analysis tool",
        "version": "1.0.0",
        "enabled": True,
        "commands": [...],
        "access_control": {...}
    }
)
```

### Update Agent Registry

```python
# Update agent
success, message = await tool.execute(
    registry_type="agent",
    action="update",
    item_id="analysis_agent",
    item_config={
        "name": "Updated Analysis Agent",
        "description": "Enhanced analysis capabilities",
        "version": "2.0.0"
    }
)
```

### Remove from Registry

```python
# Remove tool
success, message = await tool.execute(
    registry_type="tool",
    action="remove",
    item_id="old_tool"
)
```

## Model Card Creation

### Automatic Model Card Generation

When adding or updating items, the tool automatically:
1. Creates cryptographic identity via IDManagerAgent
2. Generates public/private key pair
3. Creates A2A model card JSON
4. Signs the model card
5. Saves to model cards directory

### Model Card Structure

```json
{
    "id": "item_id",
    "name": "Item Name",
    "description": "Item description",
    "type": "tool" | "agent",
    "version": "1.0.0",
    "enabled": true,
    "commands": [...],
    "access_control": {...},
    "identity": {
        "public_key": "0x...",
        "signature": "..."
    },
    "a2a_endpoint": "https://mindx.internal/{item_id}/a2a"
}
```

## Features

### 1. Dual Registry Management

Manages both:
- **Tool Registry**: `data/config/official_tools_registry.json`
- **Agent Registry**: `data/config/official_agents_registry.json`

### 2. A2A Model Cards

Creates model cards for:
- Agent-to-Agent communication
- Cryptographic verification
- Identity management
- Endpoint definition

### 3. Identity Integration

Integrates with IDManagerAgent:
- Automatic wallet creation
- Public key generation
- Message signing
- Identity verification

### 4. Persistent Storage

Saves registries to:
- JSON files
- Model cards directory
- Maintains registry structure

## Limitations

### Current Limitations

1. **No Validation**: Limited validation of item configs
2. **No Rollback**: No rollback for failed operations
3. **No Versioning**: No version history
4. **No Conflict Resolution**: No handling of conflicts
5. **Basic Error Messages**: Simple error messages

### Recommended Improvements

1. **Enhanced Validation**: Comprehensive config validation
2. **Rollback Support**: Rollback failed operations
3. **Version Control**: Registry versioning
4. **Conflict Resolution**: Handle concurrent updates
5. **Better Error Messages**: Detailed error information
6. **Backup System**: Automatic registry backups
7. **Audit Trail**: Track all registry changes

## Integration

### With IDManagerAgent

Creates identities:
```python
id_manager = await IDManagerAgent.get_instance()
public_key, _ = await id_manager.create_new_wallet(item_id)
```

### With Memory Agent

Manages model cards directory:
```python
self.model_cards_path = self.memory_agent.get_agent_data_directory("a2a_model_cards")
```

## Examples

### Complete Registry Management

```python
# 1. Add new tool
await tool.execute("tool", "add", "new_tool", {...})

# 2. Update tool
await tool.execute("tool", "update", "new_tool", {...})

# 3. Remove tool
await tool.execute("tool", "remove", "new_tool")
```

## Technical Details

### Dependencies

- `core.id_manager_agent.IDManagerAgent`: Identity management
- `agents.memory_agent.MemoryAgent`: Workspace management
- `core.bdi_agent.BaseTool`: Base tool class

### Registry File Paths

- Tools: `data/config/official_tools_registry.json`
- Agents: `data/config/official_agents_registry.json`
- Model Cards: `data/memory/agent_workspaces/a2a_model_cards/`

## Future Enhancements

1. **Validation Framework**: Comprehensive validation
2. **Version Control**: Registry versioning
3. **Backup System**: Automatic backups
4. **Audit Logging**: Change tracking
5. **Conflict Resolution**: Concurrent update handling
6. **Schema Validation**: JSON schema validation
7. **API Integration**: REST API for registry access



