# Startup Agent

## Summary

The Startup Agent is a lifecycle management agent that controls agent startup and initialization for the mindX system. It manages the startup sequence, initializes always-on agents, loads agent registry from pgvectorscale, and restores agent state from blockchain if needed.

## Technical Explanation

The Startup Agent orchestrates the system startup process, ensuring that all components are initialized in the correct order and that agent state is properly restored from persistent storage.

### Architecture

- **Type**: `lifecycle_management_agent`
- **Location**: `agents/orchestration/startup_agent.py`
- **Lifecycle**: Always-on (critical system component)
- **Integration**: Coordinates with CoordinatorAgent, MemoryAgent, IDManagerAgent

### Core Capabilities

- **System Initialization**: Initializes the entire mindX system
- **Agent Registry Loading**: Loads agent registry from pgvectorscale
- **Blockchain State Restoration**: Restores agent state from blockchain if needed
- **Always-On Agent Initialization**: Initializes always-on agents (Coordinator, mindXagent, MemoryAgent)
- **On-Demand Agent Initialization**: Initializes agents on-demand when requested
- **Startup Sequence Coordination**: Coordinates the startup sequence

### Always-On Agents

The following agents are always initialized:
- `coordinator_agent`: Central orchestrator
- `mindxagent`: System overseer
- `memory_agent`: Memory management

### Startup Sequence

1. Load agent registry from pgvectorscale
2. Restore agent state from blockchain (if requested)
3. Initialize always-on agents
4. Coordinate startup sequence
5. System ready

## Usage

```python
from agents.orchestration.startup_agent import StartupAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent
from agents.memory_agent import MemoryAgent

# Create startup agent
startup_agent = StartupAgent(
    agent_id="startup_agent",
    coordinator_agent=coordinator_agent,
    memory_agent=memory_agent
)

# Initialize system
initialization_result = await startup_agent.initialize_system(
    restore_from_blockchain=False
)

# Initialize agent on-demand
on_demand_result = await startup_agent.initialize_agent_on_demand(
    agent_type="prediction_agent",
    agent_id="prediction_001",
    config={"time_horizon": "24h"}
)
```

## Integration with MastermindAgent

The Startup Agent is initialized by MastermindAgent during system startup:

```python
# MastermindAgent initializes lifecycle agents
await mastermind_agent._initialize_lifecycle_agents()
# Startup agent is available in mastermind_agent.lifecycle_agents["startup"]
```

## Integration with ReplicationAgent

The Startup Agent works with ReplicationAgent to restore agent state:

- Loads agent registry from pgvectorscale
- Restores agent state from blockchain if needed
- Coordinates with ReplicationAgent for state restoration

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Startup Agent",
  "description": "Lifecycle management agent for system startup and initialization",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/orchestration/startup_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "lifecycle_management_agent"
    },
    {
      "trait_type": "Capability",
      "value": "System Initialization"
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
- **Sequential Initialization**: Ensures proper initialization order
- **State Restoration**: Supports blockchain state restoration
- **On-Demand Support**: Can initialize agents on-demand
- **Registry Integration**: Loads from pgvectorscale

## Future Enhancements

- Parallel initialization where safe
- Health checks during startup
- Startup time optimization
- Startup failure recovery
- Startup metrics and monitoring
