# Tool Factory Tool Documentation

## Overview

The `ToolFactoryTool` enables BDI agents to dynamically create new tools. It handles code generation, registry registration, and tool lifecycle management, allowing mindX to extend its capabilities autonomously.

**File**: `tools/tool_factory_tool.py`  
**Class**: `ToolFactoryTool`  
**Version**: 1.0.0  
**Status**: ✅ Active (High Priority)

## Architecture

### Design Principles

1. **Dynamic Creation**: Create tools at runtime
2. **Registry Integration**: Automatic registry registration
3. **Code Generation**: Generate tool code from templates
4. **BaseTool Compliance**: All tools inherit from BaseTool
5. **Standard Interface**: Consistent tool interface

### Core Components

```python
class ToolFactoryTool(BaseTool):
    - memory_agent: MemoryAgent - For workspace management
    - tools_registry_path: Path - Tools registry file path
    - config: Config - Configuration
```

## Available Actions

### 1. `create_tool`

Creates a new tool with code generation and registry registration.

**Parameters**:
- `tool_id` (str, required): Unique tool identifier
- `tool_config` (Dict, optional): Tool configuration

**Tool Config**:
```python
{
    "name": str,              # Tool display name
    "description": str,        # Tool description
    "version": str,           # Tool version (default: "1.0.0")
    "enabled": bool,         # Enable status (default: True)
    "operations": List[str]   # Custom operations (optional)
}
```

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, tool_metadata)
```

**Tool Metadata**:
```python
{
    "tool_id": str,
    "name": str,
    "description": str,
    "code_path": str,
    "created_at": float,
    "created_by": str,
    "status": str
}
```

## Usage

### Create New Tool

```python
from tools.tool_factory_tool import ToolFactoryTool
from agents.memory_agent import MemoryAgent

tool = ToolFactoryTool(memory_agent=memory_agent)

# Create tool
success, metadata = await tool.execute(
    action="create_tool",
    tool_id="custom_analyzer",
    tool_config={
        "name": "Custom Analyzer",
        "description": "Specialized analysis tool for custom data",
        "version": "1.0.0",
        "enabled": True
    }
)

if success:
    print(f"Tool created: {metadata['tool_id']}")
    print(f"Code path: {metadata['code_path']}")
```

## Tool Creation Process

### Step 1: Code Generation
- Generates tool code from template
- Creates BaseTool-compliant class
- Includes standard operations (test, status)
- Saves to tools directory

### Step 2: Registry Registration
- Registers tool in official_tools_registry.json
- Adds tool metadata
- Sets up access control
- Updates registry timestamp

### Step 3: Metadata Creation
- Creates tool metadata
- Stores creation information
- Returns metadata to caller

## Generated Tool Code Structure

The tool generates BaseTool-compliant tools with:

**Standard Structure**:
```python
class CustomAnalyzerTool(BaseTool):
    """Dynamically created tool"""
    
    def __init__(self, memory_agent, config, **kwargs):
        super().__init__(config=config, **kwargs)
        # Initialization
    
    async def execute(self, operation: str, parameters: Dict = None, **kwargs):
        # Operation execution
```

**Standard Operations**:
- `test`: Test operation for validation
- `status`: Get tool status
- `_custom_operation`: Custom operation handler

## Registry Entry Structure

Tools are registered with:
```json
{
    "id": "tool_id",
    "name": "Tool Name",
    "description": "Tool description",
    "module_path": "tools.tool_id",
    "class_name": "ToolIdTool",
    "version": "1.0.0",
    "enabled": true,
    "commands": [...],
    "access_control": {"allowed_agents": ["*"]},
    "created_by": "tool_factory_tool",
    "created_at": 1234567890
}
```

## Features

### 1. BaseTool Compliance

All generated tools:
- Inherit from BaseTool
- Follow standard interface
- Support standard operations
- Integrate with BDI agents

### 2. Automatic Registration

Tools are automatically:
- Added to tools registry
- Made discoverable
- Configured with access control
- Versioned

### 3. Code Generation

Generates complete tool code:
- Class structure
- Standard operations
- Error handling
- Logging support

## Limitations

### Current Limitations

1. **Basic Templates**: Simple tool templates only
2. **No Custom Templates**: Cannot use custom templates
3. **No Tool Updates**: Cannot update existing tools
4. **No Tool Deletion**: No tool removal capability
5. **Limited Operations**: Basic operations only

### Recommended Improvements

1. **Custom Templates**: Support for custom tool templates
2. **Tool Updates**: Update existing tools
3. **Tool Deletion**: Safe tool removal
4. **Operation Library**: Library of common operations
5. **Template Library**: Library of tool templates
6. **Tool Versioning**: Version control for tools
7. **Testing Framework**: Auto-generate tests

## Integration

### With Tools Registry

Registers tools in:
```
data/config/official_tools_registry.json
```

### With Memory Agent

Uses memory agent for:
- Workspace management
- Tool metadata storage

### With BDI Agents

Created tools are:
- Automatically discoverable
- Available to all agents (by default)
- Can be restricted via access control

## Examples

### Create Specialized Tool

```python
# Create specialized analysis tool
success, metadata = await tool.execute(
    action="create_tool",
    tool_id="advanced_analyzer",
    tool_config={
        "name": "Advanced Analyzer",
        "description": "Advanced data analysis with ML capabilities",
        "version": "1.0.0",
        "enabled": True
    }
)
```

### Create Multiple Tools

```python
# Create multiple tools for different purposes
tools = [
    ("data_collector", "Data Collection Tool"),
    ("data_processor", "Data Processing Tool"),
    ("data_visualizer", "Data Visualization Tool")
]

for tool_id, name in tools:
    success, metadata = await tool.execute(
        action="create_tool",
        tool_id=tool_id,
        tool_config={"name": name}
    )
    if success:
        print(f"Created {tool_id}")
```

## Technical Details

### Dependencies

- `agents.memory_agent.MemoryAgent`: Workspace management
- `core.bdi_agent.BaseTool`: Base tool class (for generated tools)
- `utils.config.Config`: Configuration
- `utils.logging_config.get_logger`: Logging

### Generated Code Location

Generated tools saved to:
```
tools/{tool_id}.py
```

### Registry File

Tools registry located at:
```
data/config/official_tools_registry.json
```

### Tool Template

Basic tool template includes:
- BaseTool inheritance
- Standard __init__
- Execute method
- Test operation
- Status operation
- Custom operation handler

## Future Enhancements

1. **Template System**: Rich template library
2. **Tool Updates**: Update existing tools
3. **Tool Deletion**: Safe removal
4. **Version Control**: Tool versioning
5. **Operation Library**: Common operations
6. **Testing Framework**: Auto-generate tests
7. **Documentation Generation**: Auto-generate docs
8. **Tool Marketplace**: Share tool templates



