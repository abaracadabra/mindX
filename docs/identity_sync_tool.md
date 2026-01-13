# Identity Sync Tool Documentation

## Overview

The `IdentitySyncTool` provides comprehensive identity synchronization for agents and tools. It manages cryptographic identities, synchronizes registries, validates identities, and ensures all entities have proper cryptographic signatures.

**File**: `tools/identity_sync_tool.py`  
**Class**: `IdentitySyncTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Comprehensive Sync**: Syncs both agents and tools
2. **Identity Management**: Creates and manages cryptographic identities
3. **Signature Validation**: Validates cryptographic signatures
4. **Registry Integration**: Updates registries automatically
5. **Status Reporting**: Provides detailed status reports

### Core Components

```python
class IdentitySyncTool(BaseTool):
    - memory_agent: MemoryAgent - For workspace management
    - agents_registry_path: Path - Agents registry file
    - tools_registry_path: Path - Tools registry file
```

## Available Actions

### 1. `sync_all`

Synchronizes all identities (agents and tools).

**Parameters**:
- `action` (str, default: "sync_all"): Action to perform

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, sync_results)
```

### 2. `sync_agents`

Synchronizes agent identities only.

**Parameters**:
- `action` (str, required): "sync_agents"

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, sync_results)
```

### 3. `sync_tools`

Synchronizes tool identities only.

**Parameters**:
- `action` (str, required): "sync_tools"

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, sync_results)
```

### 4. `validate`

Validates all identities.

**Parameters**:
- `action` (str, required): "validate"

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, validation_results)
```

### 5. `status`

Gets identity status report.

**Parameters**:
- `action` (str, required): "status"

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, status_report)
```

## Usage

### Sync All Identities

```python
from tools.identity_sync_tool import IdentitySyncTool
from agents.memory_agent import MemoryAgent

tool = IdentitySyncTool(memory_agent=memory_agent)

# Sync all identities
success, results = await tool.execute(action="sync_all")

if success:
    print(f"Agents updated: {results['agents']['updated']}")
    print(f"Tools updated: {results['tools']['updated']}")
```

### Validate Identities

```python
# Validate all identities
success, validation = await tool.execute(action="validate")

if success:
    print(f"Valid agents: {validation['agents']['valid']}")
    print(f"Valid tools: {validation['tools']['valid']}")
```

### Get Status

```python
# Get status report
success, status = await tool.execute(action="status")

if success:
    print(f"Agents with identity: {status['agents']['with_identity']}/{status['agents']['total']}")
    print(f"Tools with identity: {status['tools']['with_identity']}/{status['tools']['total']}")
```

## Sync Process

### Agent Sync

1. Load agents registry
2. For each agent:
   - Check if has valid identity
   - Get or create public key
   - Generate signature
   - Update registry entry
3. Save updated registry

### Tool Sync

1. Load tools registry
2. For each tool:
   - Check if has valid identity
   - Create tool entity ID (tool_{tool_id})
   - Get or create public key
   - Generate signature
   - Update registry entry
3. Save updated registry

## Features

### 1. Automatic Identity Creation

Creates missing identities:
- Generates public/private key pairs
- Signs registration messages
- Updates registry entries

### 2. Signature Generation

Generates signatures for:
- Agent registration: `agent_registration:{agent_id}`
- Tool registration: `tool_registration:{tool_id}:{version}`

### 3. Validation

Validates identities:
- Checks public key existence
- Verifies signature presence
- Validates key consistency
- Reports issues

### 4. Status Reporting

Provides comprehensive status:
- Total agents/tools
- With identity count
- Percentage coverage
- Wallet key count

## Limitations

### Current Limitations

1. **No Rollback**: No rollback capability
2. **Basic Validation**: Simple validation only
3. **No Conflict Resolution**: No conflict handling
4. **Single System**: Single system only
5. **No Incremental**: Full sync each time

### Recommended Improvements

1. **Rollback Support**: Rollback failed syncs
2. **Enhanced Validation**: Comprehensive validation
3. **Conflict Resolution**: Handle conflicts
4. **Incremental Sync**: Only sync changes
5. **Multi-System**: Support distributed systems
6. **Change Detection**: Detect what changed
7. **Sync History**: Track sync operations

## Integration

### With IDManagerAgent

Manages identities:
```python
id_manager = await IDManagerAgent.get_instance(...)
public_key = await id_manager.get_public_address(entity_id)
```

### With Memory Agent

Logs operations:
```python
await self.memory_agent.log_process(
    process_name="identity_sync_comprehensive",
    data=results,
    metadata={"tool": "identity_sync_tool"}
)
```

## Examples

### Complete Identity Management

```python
# 1. Sync all identities
await tool.execute("sync_all")

# 2. Validate identities
await tool.execute("validate")

# 3. Get status
await tool.execute("status")
```

## Technical Details

### Dependencies

- `core.id_manager_agent.IDManagerAgent`: Identity management
- `core.belief_system.BeliefSystem`: Belief system
- `agents.memory_agent.MemoryAgent`: Workspace management
- `core.bdi_agent.BaseTool`: Base tool class

### Registry Files

- Agents: `data/config/official_agents_registry.json`
- Tools: `data/config/official_tools_registry.json`

### Entity ID Format

- Agents: `{agent_id}`
- Tools: `tool_{tool_id}`

## Future Enhancements

1. **Rollback Support**: Rollback failed syncs
2. **Enhanced Validation**: Comprehensive validation
3. **Incremental Sync**: Only sync changes
4. **Multi-System**: Distributed sync
5. **Change Detection**: Detect changes
6. **Sync History**: Track operations
7. **Real-Time Sync**: Continuous synchronization



