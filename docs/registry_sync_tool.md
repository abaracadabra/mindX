# Registry Sync Tool Documentation

## Overview

The `RegistrySyncTool` synchronizes runtime agent registries with persistent registry files, ensuring all agents have proper cryptographic identities and signatures. It maintains consistency between in-memory and on-disk registries.

**File**: `tools/registry_sync_tool.py`  
**Class**: `RegistrySyncTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Bidirectional Sync**: Syncs runtime ↔ persistent registries
2. **Identity Management**: Ensures all agents have cryptographic identities
3. **Signature Validation**: Validates cryptographic signatures
4. **Automatic Key Creation**: Creates missing keys automatically
5. **Comprehensive Logging**: Detailed sync operation logging

### Core Components

```python
class RegistrySyncTool(BaseTool):
    - memory_agent: MemoryAgent - For workspace management
    - coordinator_ref: CoordinatorAgent - Runtime registry access
    - agents_registry_path: Path - Persistent agents registry
    - tools_registry_path: Path - Persistent tools registry
```

## Available Actions

### 1. `sync_all`

Synchronizes all registries comprehensively.

**Parameters**:
- `action` (str, default: "sync_all"): Action to perform
- `validate_signatures` (bool, default: True): Validate signatures
- `update_missing_keys` (bool, default: True): Create missing keys

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, sync_results)
```

**Sync Results**:
```python
{
    "agents_synced": int,
    "keys_updated": int,
    "signatures_validated": int,
    "errors": List[str]
}
```

### 2. `update_keys`

Updates missing public keys for all agents.

**Parameters**:
- `action` (str, required): "update_keys"

**Returns**:
```python
Tuple[bool, Dict[str, Any]]  # (success, update_results)
```

**Update Results**:
```python
{
    "keys_created": int,
    "keys_updated": int,
    "errors": List[str]
}
```

## Usage

### Sync All Registries

```python
from tools.registry_sync_tool import RegistrySyncTool
from agents.memory_agent import MemoryAgent
from orchestration.coordinator_agent import CoordinatorAgent

tool = RegistrySyncTool(
    memory_agent=memory_agent,
    coordinator_ref=coordinator
)

# Sync all registries
success, results = await tool.execute(
    action="sync_all",
    validate_signatures=True,
    update_missing_keys=True
)

if success:
    print(f"Agents synced: {results['agents_synced']}")
    print(f"Keys updated: {results['keys_updated']}")
```

### Update Missing Keys

```python
# Update missing keys only
success, results = await tool.execute(action="update_keys")

if success:
    print(f"Keys created: {results['keys_created']}")
```

## Sync Process

### Step 1: Load Registries
- Loads runtime registry from coordinator
- Loads persistent registry from file
- Compares entries

### Step 2: Identity Management
- Gets or creates public keys
- Updates missing identities
- Tracks key creation

### Step 3: Entry Updates
- Updates persistent entries with runtime info
- Adds missing public keys
- Generates signatures
- Updates metadata

### Step 4: Validation
- Validates signatures (if enabled)
- Checks identity consistency
- Reports validation results

### Step 5: Save Registry
- Saves updated persistent registry
- Updates metadata
- Logs sync completion

## Features

### 1. Automatic Key Creation

Creates missing identities:
- Generates public/private key pairs
- Signs registration messages
- Updates registry entries

### 2. Signature Validation

Validates cryptographic signatures:
- Verifies agent identities
- Ensures registry integrity
- Reports validation status

### 3. Bidirectional Sync

Syncs both directions:
- Runtime → Persistent: Updates file with runtime state
- Persistent → Runtime: Could update runtime (future)

### 4. Error Handling

Comprehensive error handling:
- Continues on individual failures
- Collects all errors
- Reports error summary

## Limitations

### Current Limitations

1. **One-Way Sync**: Only syncs runtime → persistent
2. **No Conflict Resolution**: No handling of conflicts
3. **No Rollback**: No rollback capability
4. **Basic Validation**: Simple signature validation
5. **No Incremental**: Full sync each time

### Recommended Improvements

1. **Bidirectional Sync**: Sync both directions
2. **Conflict Resolution**: Handle conflicts intelligently
3. **Incremental Sync**: Only sync changes
4. **Enhanced Validation**: Comprehensive validation
5. **Rollback Support**: Rollback failed syncs
6. **Change Detection**: Detect what changed
7. **Sync History**: Track sync operations

## Integration

### With Coordinator Agent

Accesses runtime registry:
```python
runtime_registry = self.coordinator_ref.agent_registry
```

### With IDManagerAgent

Manages identities:
```python
id_manager = await IDManagerAgent.get_instance()
public_key = await id_manager.get_public_address(agent_id)
```

## Examples

### Regular Sync

```python
# Regular sync operation
success, results = await tool.execute("sync_all")

if results["errors"]:
    print(f"Sync completed with {len(results['errors'])} errors")
```

### Key Update Only

```python
# Update missing keys without full sync
success, results = await tool.execute("update_keys")
```

## Technical Details

### Dependencies

- `core.id_manager_agent.IDManagerAgent`: Identity management
- `agents.memory_agent.MemoryAgent`: Workspace management
- `orchestration.coordinator_agent.CoordinatorAgent`: Runtime registry
- `core.bdi_agent.BaseTool`: Base tool class

### Registry File Paths

- Agents: `data/config/official_agents_registry.json`
- Tools: `data/config/official_tools_registry.json`

### Signature Generation

Signatures created for:
- Agent registration
- Registry updates
- Identity verification

## Future Enhancements

1. **Bidirectional Sync**: Full two-way synchronization
2. **Change Detection**: Only sync what changed
3. **Conflict Resolution**: Intelligent conflict handling
4. **Sync History**: Track all sync operations
5. **Rollback Support**: Rollback failed syncs
6. **Real-Time Sync**: Continuous synchronization
7. **Multi-System Sync**: Sync across systems



