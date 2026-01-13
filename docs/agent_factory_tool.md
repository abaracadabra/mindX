# Agent Factory Tool Documentation

## Overview

The `AgentFactoryTool` enables BDI agents to dynamically create new agents with full lifecycle management. It handles identity creation, Guardian validation, workspace setup, code generation, and coordinator registration.

**File**: `tools/agent_factory_tool.py`  
**Class**: `AgentFactoryTool`  
**Version**: 1.0.0  
**Status**: ✅ Active (High Priority)

## Architecture

### Design Principles

1. **Full Lifecycle**: Complete agent creation from identity to registration
2. **Security-First**: Guardian validation for all new agents
3. **Identity Management**: Automatic identity and wallet creation
4. **Code Generation**: Dynamic agent code generation from templates
5. **Coordinator Integration**: Automatic registration with coordinator

### Core Components

```python
class AgentFactoryTool(BaseTool):
    - memory_agent: MemoryAgent - For workspace management
    - coordinator_ref: CoordinatorAgent - For agent registration
    - guardian_ref: GuardianAgent - For security validation
    - agent_templates_dir: Path - Agent template directory
```

## Available Actions

### 1. `create_agent`

Creates a new agent with full lifecycle management.

**Parameters**:
- `agent_type` (str, required): Type of agent to create
- `agent_id` (str, required): Unique agent identifier
- `agent_config` (Dict, optional): Agent configuration

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, agent_metadata)
```

**Agent Metadata**:
```python
{
    "agent_id": str,
    "agent_type": str,
    "public_key": str,
    "env_var_name": str,
    "workspace_path": str,
    "code_path": str,
    "created_at": float,
    "created_by": str,
    "config": Dict,
    "status": str
}
```

### 2. `validate_agent`

Validates agent identity and workspace.

**Parameters**:
- `agent_id` (str, required): Agent to validate

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, validation_result)
```

## Usage

### Create New Agent

```python
from tools.agent_factory_tool import AgentFactoryTool
from agents.memory_agent import MemoryAgent
from orchestration.coordinator_agent import CoordinatorAgent
from agents.guardian_agent import GuardianAgent

tool = AgentFactoryTool(
    memory_agent=memory_agent,
    coordinator_ref=coordinator,
    guardian_ref=guardian
)

# Create agent
success, metadata = await tool.execute(
    action="create_agent",
    agent_type="analysis_agent",
    agent_id="analysis_001",
    agent_config={
        "description": "Specialized analysis agent",
        "capabilities": ["data_analysis", "reporting"]
    }
)

if success:
    print(f"Agent created: {metadata['agent_id']}")
    print(f"Public key: {metadata['public_key']}")
    print(f"Workspace: {metadata['workspace_path']}")
```

### Validate Agent

```python
# Validate existing agent
success, validation = await tool.execute(
    action="validate_agent",
    agent_id="analysis_001"
)

if success:
    print(f"Validation: {validation['validation_status']}")
    print(f"Public key: {validation['public_key']}")
```

## Agent Creation Process

### Step 1: Identity Creation
- Creates new wallet via IDManagerAgent
- Generates public/private key pair
- Stores identity securely

### Step 2: Guardian Validation
- Gets challenge from Guardian
- Signs challenge with agent's private key
- Verifies with Guardian
- Ensures security compliance

### Step 3: Workspace Setup
- Creates agent data directory
- Sets up memory structure
- Initializes workspace

### Step 4: Code Generation
- Generates agent code from template
- Creates agent class with proper structure
- Saves to agents directory
- Includes identity initialization

### Step 5: Coordinator Registration
- Registers agent with coordinator
- Adds to agent registry
- Enables agent discovery

### Step 6: Metadata Creation
- Creates agent metadata file
- Stores in workspace
- Includes all creation details

### Step 7: Status Update
- Marks agent as active
- Logs creation event
- Returns metadata

## Generated Agent Code Structure

The tool generates agents with:
- Proper class structure
- Identity initialization
- Memory agent integration
- Task execution methods
- Logging support
- Factory function

**Example Generated Code**:
```python
class Analysis001Agent:
    """Dynamically created analysis_agent agent."""
    
    def __init__(self, agent_id: str = "analysis_001", ...):
        # Initialization code
        
    async def execute_task(self, task: str, context: Dict[str, Any] = None):
        # Task execution logic
```

## Security Features

### 1. Guardian Validation

All agents must pass Guardian validation:
- Challenge-response authentication
- Cryptographic verification
- Security policy compliance

### 2. Identity Management

Secure identity creation:
- Cryptographic key generation
- Secure key storage
- Environment variable management

### 3. Workspace Isolation

Each agent gets isolated workspace:
- Separate data directory
- Isolated memory storage
- Secure file permissions

## Limitations

### Current Limitations

1. **Basic Templates**: Simple agent templates only
2. **No Custom Templates**: Cannot use custom templates
3. **No Agent Updates**: Cannot update existing agents
4. **No Agent Deletion**: No agent removal capability
5. **Limited Validation**: Basic validation only

### Recommended Improvements

1. **Custom Templates**: Support for custom agent templates
2. **Agent Updates**: Update existing agents
3. **Agent Deletion**: Safe agent removal
4. **Enhanced Validation**: Comprehensive validation
5. **Template Library**: Library of agent templates
6. **Agent Versioning**: Version control for agents
7. **Rollback Support**: Rollback failed creations

## Integration

### With IDManagerAgent

Creates agent identities:
```python
id_manager = await IDManagerAgent.get_instance()
public_key, env_var_name = await id_manager.create_new_wallet(entity_id=agent_id)
```

### With GuardianAgent

Validates agent security:
```python
guardian_validation = await self._validate_with_guardian(agent_id, public_key)
```

### With CoordinatorAgent

Registers agents:
```python
registration_result = await self.coordinator_ref.create_and_register_agent(
    agent_type, agent_id, agent_config
)
```

### With MemoryAgent

Manages agent workspaces:
```python
agent_workspace = self.memory_agent.get_agent_data_directory(agent_id)
```

## Examples

### Create Specialized Agent

```python
# Create specialized analysis agent
success, metadata = await tool.execute(
    action="create_agent",
    agent_type="data_analysis_agent",
    agent_id="data_analyst_001",
    agent_config={
        "description": "Advanced data analysis agent",
        "capabilities": ["statistical_analysis", "ml_modeling", "visualization"],
        "memory_limit": "10GB",
        "priority": "high"
    }
)
```

### Create Multiple Agents

```python
# Create multiple agents for different tasks
agents = [
    ("data_collection", "collector_001"),
    ("data_processing", "processor_001"),
    ("data_analysis", "analyzer_001")
]

for agent_type, agent_id in agents:
    success, metadata = await tool.execute(
        action="create_agent",
        agent_type=agent_type,
        agent_id=agent_id
    )
    if success:
        print(f"Created {agent_id}")
```

## Technical Details

### Dependencies

- `core.id_manager_agent.IDManagerAgent`: Identity management
- `agents.guardian_agent.GuardianAgent`: Security validation
- `orchestration.coordinator_agent.CoordinatorAgent`: Agent registration
- `agents.memory_agent.MemoryAgent`: Workspace management
- `core.bdi_agent.BaseTool`: Base tool class

### Agent Templates

Templates stored in:
```
agents/templates/
```

### Generated Code Location

Generated agents saved to:
```
agents/{agent_id}.py
```

### Metadata Storage

Agent metadata stored in:
```
data/memory/agent_workspaces/{agent_id}/agent_metadata.json
```

## Future Enhancements

1. **Template System**: Rich template library
2. **Agent Updates**: Update existing agents
3. **Agent Deletion**: Safe removal
4. **Version Control**: Agent versioning
5. **Testing Framework**: Auto-generate tests
6. **Documentation Generation**: Auto-generate docs
7. **Agent Marketplace**: Share agent templates



