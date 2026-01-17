# Socratic Agent

## Summary

The Socratic Agent is a specialized cognitive sub-agent that uses the Socratic method for learning and problem-solving. It generates Socratic questions to guide learning, challenge assumptions, and deepen understanding using LogicEngine's Socratic features.

## Technical Explanation

The Socratic Agent implements the Socratic method, a form of inquiry that uses questions to stimulate critical thinking, challenge assumptions, and guide learning. It integrates with LogicEngine for Socratic questioning capabilities.

### Architecture

- **Type**: `cognitive_sub_agent`
- **Location**: `agents/learning/socratic_agent.py`
- **Parent Agent**: MastermindAgent
- **Lifecycle**: On-demand (created when needed)
- **Integration**: Uses LogicEngine for Socratic questioning

### Core Capabilities

- **Socratic Question Generation**: Generates questions that challenge assumptions
- **Learning Guidance**: Guides learning through structured questioning
- **Assumption Challenging**: Challenges assumptions in statements
- **Understanding Deepening**: Deepens understanding through questioning
- **LogicEngine Integration**: Uses LogicEngine's Socratic features

### Methods

1. **generate_socratic_questions**: Generates Socratic questions about a topic
2. **guide_learning**: Guides learning through Socratic questioning
3. **challenge_assumptions**: Challenges assumptions in statements
4. **deepen_understanding**: Deepens understanding through questioning

## Usage

```python
from agents.learning.socratic_agent import SocraticAgent
from agents.core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

# Create Socratic agent
socratic_agent = SocraticAgent(
    agent_id="socratic_agent",
    belief_system=belief_system,
    coordinator_agent=coordinator_agent,
    memory_agent=memory_agent
)

# Initialize async components
await socratic_agent._async_init()

# Generate Socratic questions
questions = await socratic_agent.generate_socratic_questions(
    topic="System architecture design",
    context={"current_approach": "monolithic"},
    num_questions=5
)

# Guide learning
learning_guide = await socratic_agent.guide_learning(
    learning_goal="Understand distributed systems",
    current_understanding="Basic knowledge of microservices"
)

# Challenge assumptions
challenges = await socratic_agent.challenge_assumptions(
    statement="Microservices are always better than monoliths",
    assumptions=["Scalability requires microservices"]
)

# Deepen understanding
understanding = await socratic_agent.deepen_understanding(
    topic="Event-driven architecture",
    current_knowledge={
        "concepts": ["events", "publishers", "subscribers"],
        "experience": "limited"
    }
)
```

## Integration with MastermindAgent

The Socratic Agent is created on-demand by MastermindAgent for augmentic development tasks:

```python
# MastermindAgent creates Socratic agent
result = await mastermind_agent._create_sub_agent(
    agent_type="socratic_agent",
    agent_id="socratic_001",
    config={}
)
```

## Integration with LogicEngine

The Socratic Agent uses LogicEngine's Socratic questioning capabilities:

```python
# LogicEngine provides:
# - Socratic question generation
# - Belief-based context for questions
# - LLM integration for question quality
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Socratic Agent",
  "description": "Specialized cognitive sub-agent for Socratic method learning and problem-solving",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/agents/learning/socratic_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "cognitive_sub_agent"
    },
    {
      "trait_type": "Capability",
      "value": "Socratic Method"
    },
    {
      "trait_type": "Question Types",
      "value": "Assumption Challenge, Learning Guide, Understanding Deepening"
    },
    {
      "trait_type": "Lifecycle",
      "value": "on_demand"
    }
  ]
}
```

## Design Decisions

- **Socratic Method**: Implements classical Socratic questioning
- **LogicEngine Integration**: Uses LogicEngine for question generation
- **LLM-Based**: Uses LLM for high-quality question generation
- **Learning Focus**: Designed for learning and understanding
- **On-Demand**: Created when needed, not always-on

## Future Enhancements

- Adaptive questioning strategies
- Multi-turn Socratic dialogues
- Question quality metrics
- Personalized learning paths
- Collaborative questioning
