# Reasoning Agent

## Summary

The Reasoning Agent is a specialized cognitive sub-agent that provides advanced logical reasoning capabilities for augmentic development. It implements deductive, inductive, and abductive reasoning using LogicEngine and LLM-based reasoning.

## Technical Explanation

The Reasoning Agent implements three types of logical reasoning:
- **Deductive Reasoning**: General to specific (syllogistic reasoning)
- **Inductive Reasoning**: Specific to general (pattern finding)
- **Abductive Reasoning**: Best explanation (inference to best explanation)

### Architecture

- **Type**: `cognitive_sub_agent`
- **Location**: `agents/core/reasoning_agent.py`
- **Parent Agent**: MastermindAgent
- **Lifecycle**: On-demand (created when needed)
- **Integration**: Uses LogicEngine for logical inference

### Core Capabilities

- **Deductive Reasoning**: Derives specific conclusions from general premises
- **Inductive Reasoning**: Generalizes patterns from specific observations
- **Abductive Reasoning**: Finds best explanations for observations
- **Logical Inference**: Uses LogicEngine for rule-based inference
- **Belief Integration**: Stores reasoning results in BeliefSystem

### Reasoning Methods

1. **deductive_reasoning**: Performs deductive reasoning (general → specific)
2. **inductive_reasoning**: Performs inductive reasoning (specific → general)
3. **abductive_reasoning**: Performs abductive reasoning (best explanation)
4. **logical_inference**: Uses LogicEngine for rule-based inference

## Usage

```python
from agents.core.reasoning_agent import ReasoningAgent
from agents.core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

# Create reasoning agent
reasoning_agent = ReasoningAgent(
    agent_id="reasoning_agent",
    belief_system=belief_system,
    coordinator_agent=coordinator_agent,
    memory_agent=memory_agent
)

# Initialize async components
await reasoning_agent._async_init()

# Deductive reasoning
result = await reasoning_agent.deductive_reasoning(
    premises=[
        "All agents are intelligent",
        "BDI agent is an agent"
    ],
    conclusion_hint="What can we conclude about BDI agent?"
)

# Inductive reasoning
result = await reasoning_agent.inductive_reasoning(
    observations=[
        "Agent A succeeded with approach X",
        "Agent B succeeded with approach X",
        "Agent C succeeded with approach X"
    ],
    pattern_hint="What pattern emerges?"
)

# Abductive reasoning
result = await reasoning_agent.abductive_reasoning(
    observations=[
        "System performance decreased",
        "Memory usage increased",
        "CPU usage increased"
    ],
    possible_explanations=[
        "Memory leak",
        "Resource contention",
        "Inefficient algorithm"
    ]
)
```

## Integration with MastermindAgent

The Reasoning Agent is created on-demand by MastermindAgent for augmentic development tasks:

```python
# MastermindAgent creates reasoning agent
result = await mastermind_agent._create_sub_agent(
    agent_type="reasoning_agent",
    agent_id="reasoning_001",
    config={}
)
```

## Integration with LogicEngine

The Reasoning Agent uses LogicEngine for rule-based logical inference:

```python
# LogicEngine provides:
# - Rule-based inference
# - Forward chaining
# - Safe expression evaluation
# - Socratic questioning support
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Reasoning Agent",
  "description": "Specialized cognitive sub-agent for advanced logical reasoning (deductive, inductive, abductive)",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/core/reasoning_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "cognitive_sub_agent"
    },
    {
      "trait_type": "Capability",
      "value": "Logical Reasoning"
    },
    {
      "trait_type": "Reasoning Types",
      "value": "Deductive, Inductive, Abductive"
    },
    {
      "trait_type": "Lifecycle",
      "value": "on_demand"
    }
  ]
}
```

## Design Decisions

- **Three Reasoning Types**: Supports deductive, inductive, and abductive reasoning
- **LogicEngine Integration**: Uses LogicEngine for rule-based inference
- **LLM-Based**: Uses LLM for complex reasoning tasks
- **Belief Integration**: Stores results in BeliefSystem for persistence
- **On-Demand**: Created when needed, not always-on

## Future Enhancements

- Probabilistic reasoning
- Temporal reasoning
- Causal reasoning
- Multi-agent reasoning
- Reasoning chain validation
