# Epistemic Agent

## Summary

The Epistemic Agent is a specialized cognitive sub-agent that provides knowledge and belief management capabilities. It wraps BeliefSystem with an agent interface, providing knowledge base management, belief certainty tracking, knowledge dynamics, and epistemic state queries.

## Technical Explanation

The Epistemic Agent provides a high-level interface for managing the epistemic state (what is known) of the system. It tracks knowledge statistics, manages belief certainty levels, and provides queries about the knowledge base.

### Architecture

- **Type**: `cognitive_sub_agent`
- **Location**: `agents/core/epistemic_agent.py`
- **Parent Agent**: MastermindAgent
- **Lifecycle**: On-demand (created when needed)
- **Integration**: Wraps BeliefSystem with agent interface

### Core Capabilities

- **Epistemic State Queries**: Query what is known about the system
- **Knowledge Base Management**: Add, update, query beliefs
- **Belief Certainty Tracking**: Track certainty levels of beliefs
- **Knowledge Statistics**: Get statistics about the knowledge base
- **Knowledge Dynamics**: Analyze how knowledge changes over time
- **Belief Filtering**: Filter beliefs by source, certainty, etc.

### Certainty Levels

- `VERY_HIGH`: 0.9-1.0 confidence
- `HIGH`: 0.7-0.9 confidence
- `MEDIUM`: 0.5-0.7 confidence
- `LOW`: 0.3-0.5 confidence
- `VERY_LOW`: 0.0-0.3 confidence

### Methods

1. **query_epistemic_state**: Query the epistemic state (what is known)
2. **get_knowledge_statistics**: Get statistics about the knowledge base
3. **track_belief_certainty**: Track the certainty level of a belief
4. **manage_knowledge_base**: Manage knowledge base (add, update, query beliefs)
5. **analyze_knowledge_dynamics**: Analyze how knowledge changes over time
6. **get_beliefs_by_certainty**: Get beliefs filtered by certainty level
7. **get_beliefs_by_source**: Get beliefs filtered by source

## Usage

```python
from agents.core.epistemic_agent import EpistemicAgent, CertaintyLevel
from agents.core.belief_system import BeliefSystem, BeliefSource
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

# Create epistemic agent
epistemic_agent = EpistemicAgent(
    agent_id="epistemic_agent",
    belief_system=belief_system,
    coordinator_agent=coordinator_agent,
    memory_agent=memory_agent
)

# Initialize async components
await epistemic_agent._async_init()

# Query epistemic state
result = await epistemic_agent.query_epistemic_state(
    query="What do we know about system performance?",
    filters={"source": BeliefSource.PERCEPTION.value}
)

# Get knowledge statistics
stats = await epistemic_agent.get_knowledge_statistics()

# Track belief certainty
certainty_result = await epistemic_agent.track_belief_certainty(
    belief_key="system.status",
    certainty_level=CertaintyLevel.HIGH
)

# Manage knowledge base
kb_result = await epistemic_agent.manage_knowledge_base(
    operation="add",
    belief_key="new_knowledge",
    belief_data={
        "value": "System is healthy",
        "confidence": 0.9,
        "source": BeliefSource.PERCEPTION.value
    }
)

# Analyze knowledge dynamics
dynamics = await epistemic_agent.analyze_knowledge_dynamics(
    time_window=3600  # Last hour
)

# Get beliefs by certainty
high_certainty_beliefs = await epistemic_agent.get_beliefs_by_certainty(
    certainty_level=CertaintyLevel.HIGH
)

# Get beliefs by source
perception_beliefs = await epistemic_agent.get_beliefs_by_source(
    source=BeliefSource.PERCEPTION
)
```

## Integration with MastermindAgent

The Epistemic Agent is created on-demand by MastermindAgent for augmentic development tasks:

```python
# MastermindAgent creates epistemic agent
result = await mastermind_agent._create_sub_agent(
    agent_type="epistemic_agent",
    agent_id="epistemic_001",
    config={}
)
```

## Integration with BeliefSystem

The Epistemic Agent wraps BeliefSystem with an agent interface:

- Provides high-level knowledge management
- Tracks knowledge statistics
- Manages belief certainty levels
- Provides epistemic state queries

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Epistemic Agent",
  "description": "Specialized cognitive sub-agent for knowledge and belief management",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/core/epistemic_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "cognitive_sub_agent"
    },
    {
      "trait_type": "Capability",
      "value": "Knowledge Management"
    },
    {
      "trait_type": "Certainty Tracking",
      "value": "5 Levels"
    },
    {
      "trait_type": "Lifecycle",
      "value": "on_demand"
    }
  ]
}
```

## Design Decisions

- **BeliefSystem Wrapper**: Wraps BeliefSystem with agent interface
- **Certainty Tracking**: Tracks belief certainty levels
- **Knowledge Statistics**: Maintains knowledge base statistics
- **Epistemic Queries**: Provides natural language queries about knowledge
- **On-Demand**: Created when needed, not always-on

## Future Enhancements

- Advanced knowledge graph queries
- Knowledge provenance tracking
- Knowledge quality metrics
- Multi-agent knowledge sharing
- Knowledge versioning
