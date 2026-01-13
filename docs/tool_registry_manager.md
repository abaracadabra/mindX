# Tool Registry Manager Documentation

## Overview

The `ToolRegistryManager` provides simplified tool registry management operations. It handles adding, removing, and updating tools in the official tools registry.

**File**: `tools/tool_registry_manager.py`  
**Class**: `ToolRegistryManager`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Simplicity**: Focused on basic registry operations
2. **Tool-Only**: Manages tools registry only
3. **Direct Operations**: Direct add/remove/update operations
4. **Persistent Storage**: Saves to JSON file
5. **Error Handling**: Basic error handling

### Core Components

```python
class ToolRegistryManager(BaseTool):
    - registry_path: Path - Tools registry file path
```

## Available Actions

### 1. `add`

Adds a new tool to the registry.

**Parameters**:
- `action` (str, required): "add"
- `tool_id` (str, required): Tool identifier
- `tool_config` (Dict, required): Tool configuration

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 2. `remove`

Removes a tool from the registry.

**Parameters**:
- `action` (str, required): "remove"
- `tool_id` (str, required): Tool to remove

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

### 3. `update`

Updates an existing tool in the registry.

**Parameters**:
- `action` (str, required): "update"
- `tool_id` (str, required): Tool to update
- `tool_config` (Dict, required): Updated configuration

**Returns**:
```python
Tuple[bool, str]  # (success, message)
```

## Usage

### Add Tool

```python
from tools.tool_registry_manager import ToolRegistryManager

manager = ToolRegistryManager()

# Add tool
success, message = await manager.execute(
    action="add",
    tool_id="custom_tool",
    tool_config={
        "name": "Custom Tool",
        "description": "Tool description",
        "version": "1.0.0",
        "enabled": True
    }
)
```

### Update Tool

```python
# Update tool
success, message = await manager.execute(
    action="update",
    tool_id="custom_tool",
    tool_config={
        "name": "Updated Custom Tool",
        "version": "2.0.0"
    }
)
```

### Remove Tool

```python
# Remove tool
success, message = await manager.execute(
    action="remove",
    tool_id="custom_tool"
)
```

## Features

### 1. Simple Interface

Straightforward operations:
- Add tools
- Remove tools
- Update tools

### 2. Direct Registry Access

Directly modifies:
- `data/config/official_tools_registry.json`
- No intermediate steps
- Immediate persistence

### 3. Error Handling

Basic error handling:
- Validates required parameters
- Checks for existing tools
- Returns clear error messages

## Limitations

### Current Limitations

1. **No Validation**: No config validation
2. **No Model Cards**: Doesn't create model cards
3. **No Identity**: No cryptographic identity
4. **No Backup**: No backup before changes
5. **Basic Only**: Very basic functionality

### Recommended Improvements

1. **Config Validation**: Validate tool configs
2. **Model Card Support**: Create model cards
3. **Identity Integration**: Add cryptographic identities
4. **Backup System**: Backup before changes
5. **Enhanced Features**: More comprehensive features
6. **Merge with RegistryManagerTool**: Consider consolidation

## Integration

### With Tools Registry

Directly modifies:
```
data/config/official_tools_registry.json
```

## Examples

### Basic Operations

```python
# Add, update, remove
await manager.execute("add", "tool1", {...})
await manager.execute("update", "tool1", {...})
await manager.execute("remove", "tool1")
```

## Technical Details

### Dependencies

- `core.bdi_agent.BaseTool`: Base tool class
- `utils.logging_config.get_logger`: Logging

### Registry File

Tools registry located at:
```
data/config/official_tools_registry.json
```

## Comparison with RegistryManagerTool

| Feature | ToolRegistryManager | RegistryManagerTool |
|---------|-------------------|-------------------|
| Scope | Tools only | Tools + Agents |
| Model Cards | No | Yes |
| Identity | No | Yes |
| Complexity | Simple | Comprehensive |
| Use Case | Basic operations | Full management |

## Future Enhancements

1. **Enhanced Features**: Add validation, model cards
2. **Consolidation**: Consider merging with RegistryManagerTool
3. **Backup Support**: Automatic backups
4. **Validation**: Config validation
5. **Identity Support**: Cryptographic identities



