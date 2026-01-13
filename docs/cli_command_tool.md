# CLI Command Tool Documentation

## Overview

The `CLICommandTool` is a meta-tool that enables BDI agents to execute the system's top-level CLI commands through a standardized interface. It acts as a bridge between agent planning and system-level operations, providing controlled access to critical mindX management functions.

**File**: `tools/cli_command_tool.py`  
**Class**: `CLICommandTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Command Mapping**: Maps high-level command names to specific agent methods
2. **Type Safety**: Validates command names before execution
3. **Error Handling**: Comprehensive error handling with structured responses
4. **Agent Integration**: Requires references to MastermindAgent and CoordinatorAgent

### Core Components

```python
class CLICommandTool(BaseTool):
    - mastermind: MastermindAgent reference
    - coordinator: CoordinatorAgent reference
    - command_map: Dict[str, Callable] - Maps command names to handlers
```

## Available Commands

### 1. `evolve`
- **Handler**: `mastermind.manage_mindx_evolution`
- **Purpose**: Manages mindX system evolution and improvements
- **Usage**: `{"command_name": "evolve", "args": {...}}`

### 2. `deploy`
- **Handler**: `mastermind.manage_agent_deployment`
- **Purpose**: Manages agent deployment operations
- **Usage**: `{"command_name": "deploy", "args": {...}}`

### 3. `agent_create`
- **Handler**: `coordinator.create_and_register_agent`
- **Purpose**: Creates and registers new agents in the system
- **Usage**: `{"command_name": "agent_create", "args": {"agent_type": "...", ...}}`

### 4. `agent_delete`
- **Handler**: `coordinator.deregister_and_shutdown_agent`
- **Purpose**: Deregisters and shuts down existing agents
- **Usage**: `{"command_name": "agent_delete", "args": {"agent_id": "..."}}`

### 5. `agent_evolve`
- **Handler**: `coordinator.handle_user_input` (adapted)
- **Purpose**: Evolves an existing agent based on directives
- **Usage**: `{"command_name": "agent_evolve", "args": {"id": "...", "directive": "..."}}`
- **Note**: Requires special handling to construct Interaction object

## Usage

### Basic Execution

```python
from tools.cli_command_tool import CLICommandTool
from orchestration.mastermind_agent import MastermindAgent
from orchestration.coordinator_agent import CoordinatorAgent

# Initialize tool
tool = CLICommandTool(
    mastermind=mastermind_agent,
    coordinator=coordinator_agent
)

# Execute command
result = await tool.execute(
    command_name="evolve",
    args={"directive": "Improve system performance"}
)
```

### Response Format

```python
# Success
{
    "status": "SUCCESS",
    "result": {...}  # Command-specific result
}

# Error
{
    "status": "ERROR",
    "message": "Error description"
}
```

## Integration

### With BDI Agents

The tool is designed to be used by BDI agents in their planning and execution phases:

```python
# In agent plan
plan = [
    {
        "action": "execute_cli_command",
        "command": "agent_create",
        "args": {"agent_type": "analysis_agent"}
    }
]
```

### With Mastermind Agent

The tool requires active MastermindAgent and CoordinatorAgent instances, making it suitable for high-level orchestration tasks.

## Security Considerations

1. **Access Control**: Only agents with proper references can use this tool
2. **Command Validation**: Unknown commands are rejected
3. **Error Isolation**: Errors are caught and returned as structured responses
4. **No Direct System Access**: All operations go through agent methods

## Limitations & Improvements

### Current Limitations

1. **agent_evolve Simplification**: The `agent_evolve` command uses a simplified Interaction object construction
2. **No Command History**: No tracking of executed commands
3. **No Validation**: Input validation is minimal
4. **Synchronous Dependencies**: Requires synchronous agent references

### Recommended Improvements

1. **Enhanced Validation**: Add input validation for command arguments
2. **Command History**: Track executed commands for auditing
3. **Async Initialization**: Support async agent initialization
4. **Better Error Messages**: More descriptive error messages with context
5. **Command Documentation**: Auto-generate command documentation from handlers

## Technical Details

### Dependencies

- `core.bdi_agent.BaseTool` - Base tool class
- `orchestration.mastermind_agent.MastermindAgent` - Mastermind agent
- `orchestration.coordinator_agent.CoordinatorAgent` - Coordinator agent

### Error Handling

All errors are caught and returned as structured error responses:

```python
try:
    result = await handler(**args)
    return {"status": "SUCCESS", "result": result}
except Exception as e:
    logger.error(f"Error executing CLI command '{command_name}': {e}")
    return {"status": "ERROR", "message": str(e)}
```

## Examples

### Creating an Agent

```python
result = await tool.execute(
    command_name="agent_create",
    args={
        "agent_type": "analysis_agent",
        "agent_id": "analysis_001",
        "config": {...}
    }
)
```

### Evolving the System

```python
result = await tool.execute(
    command_name="evolve",
    args={
        "directive": "Improve memory management efficiency",
        "focus_areas": ["memory", "performance"]
    }
)
```

## Future Enhancements

1. **Command Chaining**: Support for command pipelines
2. **Conditional Execution**: Support for conditional command execution
3. **Rollback Support**: Ability to rollback command effects
4. **Performance Monitoring**: Track command execution times
5. **Command Templates**: Pre-defined command templates for common operations



