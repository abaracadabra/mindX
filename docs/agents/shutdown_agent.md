# Shutdown Agent

## Summary

The Shutdown Agent is a lifecycle management agent that controls graceful shutdown and cleanup for the mindX system. It manages graceful agent shutdown, saves state to pgvectorscale, creates final backup via GitHub agent, and archives proven agents/tools to blockchain.

## Technical Explanation

The Shutdown Agent orchestrates the system shutdown process, ensuring that all components are shut down gracefully, state is saved, backups are created, and proven entities are archived to blockchain before the system terminates.

### Architecture

- **Type**: `lifecycle_management_agent`
- **Location**: `agents/orchestration/shutdown_agent.py`
- **Lifecycle**: Always-on (critical system component)
- **Integration**: Coordinates with CoordinatorAgent, GitHubAgentTool, BlockchainAgent

### Core Capabilities

- **Graceful Shutdown**: Shuts down all agents gracefully
- **State Saving**: Saves system state to pgvectorscale
- **Final Backup**: Creates final backup via GitHub agent
- **Proven Entity Archival**: Archives proven agents/tools to blockchain
- **Cleanup**: Performs final cleanup operations
- **Shutdown Sequence**: Coordinates shutdown sequence

### Shutdown Sequence

1. Save state to pgvectorscale
2. Create final backup via GitHub agent
3. Archive proven entities to blockchain
4. Shutdown agents gracefully
5. Perform cleanup
6. System shutdown complete

## Usage

```python
from agents.orchestration.shutdown_agent import ShutdownAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent
from agents.memory_agent import MemoryAgent
from tools.github_agent_tool import GitHubAgentTool

# Create shutdown agent
shutdown_agent = ShutdownAgent(
    agent_id="shutdown_agent",
    coordinator_agent=coordinator_agent,
    memory_agent=memory_agent,
    github_agent=github_agent
)

# Shutdown system
shutdown_result = await shutdown_agent.shutdown_system(
    save_state=True,
    create_backup=True,
    archive_proven=True
)
```

## Integration with MastermindAgent

The Shutdown Agent is initialized by MastermindAgent during system startup and called during shutdown:

```python
# MastermindAgent initializes lifecycle agents
await mastermind_agent._initialize_lifecycle_agents()
# Shutdown agent is available in mastermind_agent.lifecycle_agents["shutdown"]

# During shutdown
if "shutdown" in mastermind_agent.lifecycle_agents:
    shutdown_agent = mastermind_agent.lifecycle_agents["shutdown"]
    await shutdown_agent.shutdown_system(
        save_state=True,
        create_backup=True,
        archive_proven=True
    )
```

## Integration with ReplicationAgent

The Shutdown Agent works with ReplicationAgent to ensure all entities are properly replicated before shutdown:

- Archives proven entities to blockchain
- Ensures all replication is complete
- Coordinates with ReplicationAgent

## Integration with GitHubAgentTool

The Shutdown Agent uses GitHubAgentTool for final backup:

- Creates shutdown backup
- Ensures all changes are backed up
- Coordinates with GitHub agent

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Shutdown Agent",
  "description": "Lifecycle management agent for graceful system shutdown and cleanup",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/orchestration/shutdown_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "lifecycle_management_agent"
    },
    {
      "trait_type": "Capability",
      "value": "Graceful Shutdown"
    },
    {
      "trait_type": "Lifecycle",
      "value": "always_on"
    },
    {
      "trait_type": "Critical Component",
      "value": "true"
    }
  ]
}
```

## Design Decisions

- **Always-On**: Critical system component, always initialized
- **Graceful**: Ensures graceful shutdown of all components
- **State Preservation**: Saves state before shutdown
- **Backup Creation**: Creates final backup before shutdown
- **Proven Archival**: Archives proven entities to blockchain

## Future Enhancements

- Shutdown timeout handling
- Forced shutdown fallback
- Shutdown health checks
- Shutdown metrics
- Shutdown recovery mechanisms
