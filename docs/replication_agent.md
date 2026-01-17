# Replication Agent

## Summary

The Replication Agent is a lifecycle management agent that handles replication across multiple systems: local pgvectorscale database, GitHub backups, and blockchain immutable archival. It coordinates replication events triggered by agent/tool creation and manages the replication of proven entities.

## Technical Explanation

The Replication Agent ensures that agents, tools, and their metadata are replicated across multiple storage systems for redundancy, backup, and immutable archival. It subscribes to system events and automatically triggers replication when entities are created or proven effective.

### Architecture

- **Type**: `lifecycle_management_agent`
- **Location**: `agents/orchestration/replication_agent.py`
- **Lifecycle**: Always-on (critical system component)
- **Integration**: Coordinates with CoordinatorAgent, GitHubAgentTool, BlockchainAgent

### Core Capabilities

- **Local Replication**: Replicates to pgvectorscale database
- **GitHub Replication**: Replicates via GitHub agent backup
- **Blockchain Replication**: Replicates proven entities to blockchain as immutable
- **Event-Driven**: Subscribes to agent/tool creation events
- **Proven Entity Management**: Marks entities as proven and triggers blockchain archival
- **Multi-System Coordination**: Coordinates replication across all systems

### Event Subscriptions

- `agent.created`: Triggers replication when agents are created
- `agent.registered`: Logs agent registration
- `tool.created`: Triggers replication when tools are created
- `identity.created`: Logs identity creation

### Replication Targets

1. **Local (pgvectorscale)**: Fast local storage with vector search
2. **GitHub**: Version control and backup
3. **Blockchain**: Immutable archival for proven entities

## Usage

```python
from agents.orchestration.replication_agent import ReplicationAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent
from agents.memory_agent import MemoryAgent
from tools.github_agent_tool import GitHubAgentTool

# Create replication agent
replication_agent = ReplicationAgent(
    agent_id="replication_agent",
    coordinator_agent=coordinator_agent,
    memory_agent=memory_agent,
    github_agent=github_agent
)

# Replicate entity
replication_result = await replication_agent.replicate_entity(
    entity_type="agent",
    entity_id="my_agent",
    entity_data={"agent_type": "prediction_agent", "config": {}},
    proven=False,
    replicate_local=True,
    replicate_github=True,
    replicate_blockchain=False
)

# Mark entity as proven and archive to blockchain
proven_result = await replication_agent.mark_entity_as_proven(
    entity_type="agent",
    entity_id="my_agent",
    effectiveness_metrics={
        "success_rate": 0.95,
        "tasks_completed": 100
    }
)
```

## Integration with MastermindAgent

The Replication Agent is initialized by MastermindAgent during system startup:

```python
# MastermindAgent initializes lifecycle agents
await mastermind_agent._initialize_lifecycle_agents()
# Replication agent is available in mastermind_agent.lifecycle_agents["replication"]
```

## Integration with GitHubAgentTool

The Replication Agent uses GitHubAgentTool for GitHub backups:

- Creates backups when entities are created
- Uses appropriate backup types (agent_creation, tool_creation, etc.)
- Coordinates with GitHub agent for backup management

## Integration with BlockchainAgent

The Replication Agent uses BlockchainAgent for immutable archival:

- Archives proven agents/tools to blockchain
- Ensures immutability of proven entities
- Supports knowledge economy sharing

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Replication Agent",
  "description": "Lifecycle management agent for multi-system replication (local, GitHub, blockchain)",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/orchestration/replication_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "lifecycle_management_agent"
    },
    {
      "trait_type": "Capability",
      "value": "Multi-System Replication"
    },
    {
      "trait_type": "Replication Targets",
      "value": "Local, GitHub, Blockchain"
    },
    {
      "trait_type": "Lifecycle",
      "value": "always_on"
    }
  ]
}
```

## Design Decisions

- **Event-Driven**: Automatically replicates on entity creation
- **Multi-System**: Replicates to local, GitHub, and blockchain
- **Proven Entities**: Only proven entities go to blockchain
- **Always-On**: Critical system component, always active
- **Coordinated**: Coordinates with other lifecycle agents

## Future Enhancements

- Replication conflict resolution
- Replication status monitoring
- Replication retry mechanisms
- Incremental replication
- Replication verification
