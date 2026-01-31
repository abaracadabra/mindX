# Non-Monotonic Agent

## Summary

The Non-Monotonic Agent is a specialized cognitive sub-agent that handles non-monotonic reasoning and belief adaptation. It manages belief revision when new information contradicts existing beliefs, handles default assumptions, manages belief conflicts, and adapts to changing environments.

## Technical Explanation

The Non-Monotonic Agent implements non-monotonic reasoning, which allows beliefs to be revised when new information contradicts existing beliefs. This is essential for adaptive systems that operate in changing environments.

### Architecture

- **Type**: `cognitive_sub_agent`
- **Location**: `agents/core/nonmonotonic_agent.py`
- **Parent Agent**: MastermindAgent
- **Lifecycle**: On-demand (created when needed)
- **Integration**: Monitors BeliefSystem for conflicts

### Core Capabilities

- **Belief Revision**: Revises beliefs when new information contradicts existing beliefs
- **Conflict Detection**: Detects conflicts between beliefs
- **Default Assumptions**: Manages default assumptions that can be overridden
- **Belief Conflict Management**: Resolves conflicts using various strategies
- **Environment Adaptation**: Adapts beliefs to changing environments
- **Event-Driven**: Subscribes to belief update events

### Conflict Types

- `DIRECT_CONTRADICTION`: Direct contradiction between beliefs
- `INCONSISTENCY`: Logical inconsistency
- `DEFAULT_OVERRIDE`: Default assumption override
- `EVIDENCE_CONFLICT`: Conflicting evidence

### Conflict Resolution Strategies

- `confidence_based`: Resolves conflicts based on confidence levels
- `recency_based`: Prefers more recent beliefs
- `source_based`: Prefers beliefs from more reliable sources

### Methods

1. **detect_conflicts**: Detects conflicts between new and existing beliefs
2. **revise_belief**: Revises a belief when new information contradicts it
3. **handle_default_assumption**: Manages default assumptions
4. **manage_belief_conflicts**: Manages all detected conflicts
5. **adapt_to_changing_environment**: Adapts beliefs to environment changes

## Usage

```python
from agents.core.nonmonotonic_agent import NonMonotonicAgent
from agents.core.belief_system import BeliefSystem, BeliefSource
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

# Create non-monotonic agent
nonmonotonic_agent = NonMonotonicAgent(
    agent_id="nonmonotonic_agent",
    belief_system=belief_system,
    coordinator_agent=coordinator_agent,
    memory_agent=memory_agent
)

# Initialize async components
await nonmonotonic_agent._async_init()

# Detect conflicts
conflicts = await nonmonotonic_agent.detect_conflicts(
    new_belief_key="system.status",
    new_belief_value="healthy",
    confidence_threshold=0.5
)

# Revise belief
revision_result = await nonmonotonic_agent.revise_belief(
    belief_key="system.status",
    new_value="degraded",
    new_confidence=0.8,
    new_source=BeliefSource.PERCEPTION,
    reason="Performance metrics indicate degradation"
)

# Handle default assumption
assumption_result = await nonmonotonic_agent.handle_default_assumption(
    assumption_key="default_timeout",
    default_value=30,
    override_value=60  # Override default
)

# Manage all conflicts
conflict_management = await nonmonotonic_agent.manage_belief_conflicts(
    conflict_resolution_strategy="confidence_based"
)

# Adapt to changing environment
adaptation = await nonmonotonic_agent.adapt_to_changing_environment(
    environment_changes={
        "system_load": "high",
        "available_resources": "limited"
    }
)
```

## Integration with MastermindAgent

The Non-Monotonic Agent is created on-demand by MastermindAgent for augmentic development tasks:

```python
# MastermindAgent creates non-monotonic agent
result = await mastermind_agent._create_sub_agent(
    agent_type="nonmonotonic_agent",
    agent_id="nonmonotonic_001",
    config={}
)
```

## Integration with BeliefSystem

The Non-Monotonic Agent monitors and manages the BeliefSystem:

- Subscribes to `belief.updated` events
- Detects conflicts automatically
- Revises beliefs when contradictions are found
- Manages default assumptions

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Non-Monotonic Agent",
  "description": "Specialized cognitive sub-agent for non-monotonic reasoning and belief adaptation",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/core/nonmonotonic_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "cognitive_sub_agent"
    },
    {
      "trait_type": "Capability",
      "value": "Non-Monotonic Reasoning"
    },
    {
      "trait_type": "Conflict Resolution",
      "value": "Confidence-Based"
    },
    {
      "trait_type": "Lifecycle",
      "value": "on_demand"
    }
  ]
}
```

## Design Decisions

- **Non-Monotonic Reasoning**: Allows belief revision when contradictions occur
- **Conflict Detection**: Automatically detects conflicts between beliefs
- **LLM-Based Revision**: Uses LLM to determine if revision is appropriate
- **Multiple Strategies**: Supports different conflict resolution strategies
- **Event-Driven**: Monitors belief updates for conflicts

## Future Enhancements

- More sophisticated conflict resolution strategies
- Belief priority systems
- Temporal belief management
- Multi-agent belief coordination
- Probabilistic belief revision
