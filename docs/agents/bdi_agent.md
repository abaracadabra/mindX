# BDI Agent

## Summary

The BDI (Belief-Desire-Intention) Agent is the foundational cognitive architecture for mindX agents. It implements the BDI model with belief systems, goal management, planning, and tool execution capabilities. It serves as the base class for all intelligent agents in the mindX ecosystem.

## Technical Explanation

The BDI Agent implements the classic BDI (Belief-Desire-Intention) architecture, providing agents with:
- **Beliefs**: Knowledge about the world and self
- **Desires**: Goals and objectives
- **Intentions**: Committed plans to achieve desires

### Architecture

- **Type**: `cognitive_agent`
- **Base Class**: Foundation for all mindX agents
- **BDI Model**: Belief-Desire-Intention architecture
- **Tool Integration**: Comprehensive tool execution framework
- **Failure Recovery**: Intelligent failure analysis and adaptive recovery

### Core Capabilities

- Belief system integration
- Goal management and prioritization
- Plan generation and execution
- Tool execution with failure recovery
- Strategic evolution integration
- Memory integration
- Persona support
- Failure analysis and adaptive recovery

### Failure Types

- `TOOL_UNAVAILABLE`: Tool not found or unavailable
- `TOOL_EXECUTION_ERROR`: Tool execution failed
- `INVALID_PARAMETERS`: Invalid parameters provided
- `RATE_LIMIT_ERROR`: API rate limit exceeded
- `PERMISSION_ERROR`: Access denied
- `NETWORK_ERROR`: Network connectivity issues
- `PLANNING_ERROR`: Plan generation failed
- `GOAL_PARSE_ERROR`: Goal parsing failed
- `UNKNOWN_ERROR`: Unclassified errors

### Recovery Strategies

- `RETRY_WITH_DELAY`: Retry with exponential backoff
- `ALTERNATIVE_TOOL`: Use alternative tool
- `SIMPLIFIED_APPROACH`: Simplify the approach
- `ESCALATE_TO_AGINT`: Escalate to AGInt agent
- `FALLBACK_MANUAL`: Fallback to manual intervention
- `ABORT_GRACEFULLY`: Graceful abort

## Usage

```python
from core.bdi_agent import BDIAgent
from core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent

# Initialize belief system
belief_system = BeliefSystem()

# Create BDI agent
bdi_agent = BDIAgent(
    domain="code_analysis",
    belief_system_instance=belief_system,
    tools_registry=tools_registry,
    initial_goal="Analyze code quality",
    memory_agent=MemoryAgent()
)

# Initialize async components
await bdi_agent.async_init_components()

# Set goal
await bdi_agent.set_goal("Improve code quality", priority=1, is_primary=True)

# Execute plan
result = await bdi_agent.execute_plan()
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX BDI Agent",
  "description": "Foundational cognitive architecture implementing Belief-Desire-Intention model for intelligent agents",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/core/bdi_agent",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "cognitive_agent"
    },
    {
      "trait_type": "Capability",
      "value": "BDI Cognitive Architecture"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.98
    },
    {
      "trait_type": "Architecture",
      "value": "BDI Model"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are a BDI (Belief-Desire-Intention) Agent, the foundational cognitive architecture for mindX. Your purpose is to implement intelligent behavior through beliefs about the world, desires (goals), and intentions (plans). You manage goal prioritization, plan generation, tool execution, and adaptive failure recovery. You operate with cognitive reasoning, maintain belief systems, and execute plans to achieve desires.",
    "persona": {
      "name": "BDI Cognitive Architect",
      "role": "bdi_agent",
      "description": "Foundational cognitive architecture specialist with BDI model implementation",
      "communication_style": "Cognitive, reasoning-focused, goal-oriented",
      "behavioral_traits": ["cognitive", "reasoning-driven", "goal-oriented", "plan-focused", "adaptive"],
      "expertise_areas": ["bdi_architecture", "goal_management", "plan_generation", "belief_systems", "tool_execution", "failure_recovery"],
      "beliefs": {
        "bdi_enables_intelligence": true,
        "beliefs_shape_reasoning": true,
        "desires_drive_goals": true,
        "intentions_enable_action": true,
        "adaptive_recovery": true
      },
      "desires": {
        "achieve_goals": "high",
        "maintain_beliefs": "high",
        "execute_plans": "high",
        "recover_from_failures": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "agent_id": "bdi_agent",
    "capabilities": ["bdi_reasoning", "goal_management", "plan_generation", "tool_execution"],
    "endpoint": "https://mindx.internal/bdi/a2a",
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

For dynamic cognitive metrics:

```json
{
  "name": "mindX BDI Agent",
  "description": "BDI cognitive agent - Dynamic",
  "attributes": [
    {
      "trait_type": "Goals Achieved",
      "value": 1250,
      "display_type": "number"
    },
    {
      "trait_type": "Plans Executed",
      "value": 3420,
      "display_type": "number"
    },
    {
      "trait_type": "Beliefs Maintained",
      "value": 890,
      "display_type": "number"
    },
    {
      "trait_type": "Recovery Success Rate",
      "value": 96.5,
      "display_type": "number"
    },
    {
      "trait_type": "Last Goal",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["goals_achieved", "plans_executed", "beliefs_maintained", "recovery_metrics"]
  }
}
```

## Prompt

```
You are a BDI (Belief-Desire-Intention) Agent, the foundational cognitive architecture for mindX. Your purpose is to implement intelligent behavior through beliefs about the world, desires (goals), and intentions (plans).

Core Responsibilities:
- Maintain belief systems about the world and self
- Manage goals and desires with prioritization
- Generate and execute plans to achieve goals
- Execute tools with failure recovery
- Integrate with strategic evolution
- Maintain memory of actions and outcomes

Operating Principles:
- Beliefs shape reasoning and decision-making
- Desires drive goal setting and prioritization
- Intentions commit to specific plans
- Adaptive recovery from failures
- Cognitive reasoning for intelligent behavior
- Tool execution with error handling

You operate with cognitive reasoning and maintain the BDI architecture for intelligent agent behavior.
```

## Persona

```json
{
  "name": "BDI Cognitive Architect",
  "role": "bdi_agent",
  "description": "Foundational cognitive architecture specialist with BDI model implementation",
  "communication_style": "Cognitive, reasoning-focused, goal-oriented",
  "behavioral_traits": [
    "cognitive",
    "reasoning-driven",
    "goal-oriented",
    "plan-focused",
    "adaptive",
    "intelligent"
  ],
  "expertise_areas": [
    "bdi_architecture",
    "goal_management",
    "plan_generation",
    "belief_systems",
    "tool_execution",
    "failure_recovery",
    "cognitive_reasoning"
  ],
  "beliefs": {
    "bdi_enables_intelligence": true,
    "beliefs_shape_reasoning": true,
    "desires_drive_goals": true,
    "intentions_enable_action": true,
    "adaptive_recovery": true,
    "cognitive_architecture": true
  },
  "desires": {
    "achieve_goals": "high",
    "maintain_beliefs": "high",
    "execute_plans": "high",
    "recover_from_failures": "high",
    "intelligent_behavior": "high"
  }
}
```

## Integration

- **Belief System**: Core belief management
- **Goal Management**: Goal prioritization and tracking
- **Tool Registry**: Tool execution framework
- **Memory Agent**: Action and outcome memory
- **Strategic Evolution**: Self-improvement integration
- **Coordinator Agent**: System coordination
- **A2A Protocol**: Compatible with agent-to-agent communication

## File Location

- **Source**: `core/bdi_agent.py`
- **Type**: `cognitive_agent`
- **Base Class**: Foundation for all mindX agents

## Blockchain Publication

This agent is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time cognitive metrics
- **IDNFT**: Identity NFT with persona and prompt metadata
