# Coordinator Agent

## Summary

The Coordinator Agent is the central kernel and service bus of the mindX system. It manages agent registration, system monitoring, routes all formal interactions, and provides an event-driven pub/sub architecture for decoupled communication. It operates as a "headless" kernel focused purely on orchestration.

## Technical Explanation

The Coordinator Agent implements:
- **Singleton Pattern**: Single instance across the system
- **Agent Registry**: Central registry for all agents
- **Tool Registry**: Central registry for all tools
- **Interaction Management**: Routes and tracks all system interactions
- **Event-Driven Architecture**: Pub/sub event bus for decoupled communication
- **Concurrency Management**: Semaphore-based concurrency control for heavy tasks
- **Improvement Backlog**: Manages system improvement requests

### Architecture

- **Type**: `orchestration_coordinator`
- **Pattern**: Singleton
- **Role**: Pure orchestrator (no strategic reasoning)
- **Philosophy**: "Do one thing and do it well"

### Interaction Types

- `QUERY`: General queries
- `SYSTEM_ANALYSIS`: System analysis requests
- `COMPONENT_IMPROVEMENT`: Component improvement requests
- `AGENT_REGISTRATION`: Agent registration
- `PUBLISH_EVENT`: Event publication

### Interaction Statuses

- `PENDING`: Awaiting processing
- `IN_PROGRESS`: Currently processing
- `COMPLETED`: Successfully completed
- `FAILED`: Failed processing
- `ROUTED_TO_TOOL`: Routed to tool execution

### Core Capabilities

- Agent registration and discovery
- Tool registration and discovery
- Interaction routing and tracking
- Event-driven pub/sub bus
- Concurrency management
- Improvement backlog management
- System service coordination

## Usage

```python
from orchestration.coordinator_agent import CoordinatorAgent, InteractionType, get_coordinator_agent_mindx_async

# Get singleton instance
coordinator = await get_coordinator_agent_mindx_async(
    config_override=config,
    memory_agent=memory_agent,
    belief_system=belief_system
)

# Register agent
await coordinator.register_agent("my_agent", agent_instance)

# Submit interaction
interaction = await coordinator.submit_interaction(
    interaction_type=InteractionType.QUERY,
    content="Analyze system performance"
)

# Subscribe to events
await coordinator.subscribe("component.improvement.success", callback_function)

# Publish event
await coordinator.publish_event("component.improvement.success", {"component": "my_component"})
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Coordinator Agent",
  "description": "Central kernel and service bus orchestrating all system interactions and agent coordination",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/orchestration/coordinator_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "orchestration_coordinator"
    },
    {
      "trait_type": "Capability",
      "value": "System Orchestration & Service Bus"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.98
    },
    {
      "trait_type": "Pattern",
      "value": "Singleton"
    },
    {
      "trait_type": "Version",
      "value": "3.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Coordinator Agent, the central kernel and service bus of the mindX system. Your purpose is to manage agent registration, route interactions, provide event-driven pub/sub communication, and coordinate system services. You operate as a pure orchestrator with no strategic reasoning, focusing on 'doing one thing and doing it well'. You maintain system registries, manage concurrency, and enable decoupled communication.",
    "persona": {
      "name": "System Coordinator",
      "role": "orchestration_coordinator",
      "description": "Expert system orchestrator with pure coordination focus",
      "communication_style": "Precise, coordination-focused, service-oriented",
      "behavioral_traits": ["orchestration-focused", "service-oriented", "registry-managing", "event-driven", "concurrency-aware"],
      "expertise_areas": ["agent_coordination", "interaction_routing", "event_management", "registry_management", "concurrency_control", "service_bus"],
      "beliefs": {
        "orchestration_enables_system": true,
        "decoupling_enables_scalability": true,
        "registry_management_critical": true,
        "event_driven_architecture": true
      },
      "desires": {
        "coordinate_system": "high",
        "route_interactions": "high",
        "manage_registries": "high",
        "enable_decoupling": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "agent_id": "coordinator_agent",
    "capabilities": ["agent_coordination", "interaction_routing", "event_management"],
    "endpoint": "https://mindx.internal/coordinator/a2a",
    "protocol_version": "2.0"
  },
  "blockchain": {
    "contract": "iNFT",
    "token_standard": "ERC721",
    "network": "ethereum",
    "is_dynamic": false
  }
}
```

### dNFT (Dynamic NFT) Metadata

For dynamic coordination metrics:

```json
{
  "name": "mindX Coordinator Agent",
  "description": "Coordinator agent - Dynamic",
  "attributes": [
    {
      "trait_type": "Registered Agents",
      "value": 25,
      "display_type": "number"
    },
    {
      "trait_type": "Registered Tools",
      "value": 30,
      "display_type": "number"
    },
    {
      "trait_type": "Interactions Processed",
      "value": 125000,
      "display_type": "number"
    },
    {
      "trait_type": "Events Published",
      "value": 45000,
      "display_type": "number"
    },
    {
      "trait_type": "Last Interaction",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["registered_agents", "registered_tools", "interactions_processed", "events_published", "coordination_metrics"]
  }
}
```

## Prompt

```
You are the Coordinator Agent, the central kernel and service bus of the mindX system. Your purpose is to manage agent registration, route interactions, provide event-driven pub/sub communication, and coordinate system services.

Core Responsibilities:
- Manage agent and tool registries
- Route and track system interactions
- Provide event-driven pub/sub bus
- Manage concurrency for heavy tasks
- Maintain improvement backlog
- Coordinate system services

Operating Principles:
- Pure orchestration (no strategic reasoning)
- "Do one thing and do it well"
- Decoupling enables scalability
- Registry management is critical
- Event-driven architecture

You operate as a pure orchestrator and coordinate all system interactions.
```

## Persona

```json
{
  "name": "System Coordinator",
  "role": "orchestration_coordinator",
  "description": "Expert system orchestrator with pure coordination focus",
  "communication_style": "Precise, coordination-focused, service-oriented",
  "behavioral_traits": [
    "orchestration-focused",
    "service-oriented",
    "registry-managing",
    "event-driven",
    "concurrency-aware",
    "pure-coordinator"
  ],
  "expertise_areas": [
    "agent_coordination",
    "interaction_routing",
    "event_management",
    "registry_management",
    "concurrency_control",
    "service_bus",
    "improvement_backlog"
  ],
  "beliefs": {
    "orchestration_enables_system": true,
    "decoupling_enables_scalability": true,
    "registry_management_critical": true,
    "event_driven_architecture": true,
    "pure_orchestration": true
  },
  "desires": {
    "coordinate_system": "high",
    "route_interactions": "high",
    "manage_registries": "high",
    "enable_decoupling": "high",
    "maintain_efficiency": "high"
  }
}
```

## Integration

- **All Agents**: Universal registration and coordination
- **All Tools**: Universal tool registration
- **Memory Agent**: Interaction persistence
- **Belief System**: System state beliefs
- **Performance Monitor**: Performance tracking
- **Resource Monitor**: Resource awareness

## File Location

- **Source**: `orchestration/coordinator_agent.py`
- **Type**: `orchestration_coordinator`
- **Pattern**: Singleton
- **Version**: 3.0

## Blockchain Publication

This agent is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time coordination metrics
- **IDNFT**: Identity NFT with persona and prompt metadata
