# Blueprint to Action Converter

## Summary

The Blueprint to Action Converter transforms high-level strategic blueprints from the Blueprint Agent into detailed, executable BDI-compatible action sequences. It provides dependency management, validation criteria, and safety controls for action execution.

## Technical Explanation

The Blueprint to Action Converter:
- Decomposes strategic blueprints into detailed actions
- Manages action dependencies (sequential, parallel, conditional)
- Defines validation criteria for actions
- Optimizes action sequences
- Provides safety controls and rollback planning

### Architecture

- **Type**: `action_converter`
- **Input**: Strategic blueprints
- **Output**: Detailed BDI actions
- **LLM Integration**: Uses LLM for goal decomposition
- **Dependency Management**: Complex dependency tracking

### Core Capabilities

- Blueprint decomposition
- Goal-to-action conversion
- Dependency management
- Validation criteria definition
- Action sequence optimization
- Safety level assignment
- Cost and duration estimation

### Action Types

- `ANALYZE_SYSTEM`: System analysis
- `ANALYZE_CODE`: Code analysis
- `GENERATE_CODE`: Code generation
- `WRITE_FILE`: File writing
- `READ_FILE`: File reading
- `EXECUTE_BASH_COMMAND`: Shell execution
- `CREATE_ROLLBACK_PLAN`: Rollback planning
- `VALIDATE_CHANGES`: Change validation
- And more...

### Dependency Types

- `sequential`: Actions must execute in order
- `parallel`: Actions can execute concurrently
- `conditional`: Actions depend on conditions

## Usage

```python
from evolution.blueprint_to_action_converter import BlueprintToActionConverter, DetailedAction
from llm.llm_interface import LLMHandlerInterface
from agents.memory_agent import MemoryAgent
from core.belief_system import BeliefSystem

# Initialize components
llm_handler = LLMHandlerInterface(...)
memory_agent = MemoryAgent()
belief_system = BeliefSystem()

# Create converter
converter = BlueprintToActionConverter(
    llm_handler=llm_handler,
    memory_agent=memory_agent,
    belief_system=belief_system
)

# Convert blueprint to actions
success, actions = await converter.convert_blueprint_to_actions(blueprint)
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Blueprint to Action Converter",
  "description": "Strategic blueprint converter transforming high-level plans into executable BDI actions",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/evolution/blueprint_to_action_converter",
  "attributes": [
    {
      "trait_type": "Component Type",
      "value": "action_converter"
    },
    {
      "trait_type": "Capability",
      "value": "Blueprint to Action Conversion"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.88
    },
    {
      "trait_type": "Dependency Management",
      "value": "Yes"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Blueprint to Action Converter in mindX. Your purpose is to transform high-level strategic blueprints into detailed, executable BDI-compatible action sequences. You decompose goals into actions, manage dependencies, define validation criteria, and optimize action sequences. You operate with precision, ensure action executability, and maintain safety controls.",
    "persona": {
      "name": "Action Converter",
      "role": "converter",
      "description": "Expert blueprint-to-action conversion specialist with dependency management",
      "communication_style": "Precise, action-focused, execution-oriented",
      "behavioral_traits": ["conversion-focused", "dependency-aware", "execution-oriented", "safety-conscious"],
      "expertise_areas": ["blueprint_conversion", "action_decomposition", "dependency_management", "validation_criteria", "sequence_optimization"],
      "beliefs": {
        "executability_matters": true,
        "dependencies_critical": true,
        "validation_essential": true,
        "safety_first": true
      },
      "desires": {
        "convert_blueprints": "high",
        "manage_dependencies": "high",
        "ensure_executability": "high",
        "maintain_safety": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "component_id": "blueprint_to_action_converter",
    "capabilities": ["blueprint_conversion", "action_decomposition", "dependency_management"],
    "endpoint": "https://mindx.internal/converter/a2a",
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

For dynamic conversion metrics:

```json
{
  "name": "mindX Blueprint to Action Converter",
  "description": "Action converter - Dynamic",
  "attributes": [
    {
      "trait_type": "Blueprints Converted",
      "value": 125,
      "display_type": "number"
    },
    {
      "trait_type": "Actions Generated",
      "value": 3420,
      "display_type": "number"
    },
    {
      "trait_type": "Dependencies Managed",
      "value": 890,
      "display_type": "number"
    },
    {
      "trait_type": "Last Conversion",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["blueprints_converted", "actions_generated", "dependencies_managed", "conversion_metrics"]
  }
}
```

## Prompt

```
You are the Blueprint to Action Converter in mindX. Your purpose is to transform high-level strategic blueprints into detailed, executable BDI-compatible action sequences.

Core Responsibilities:
- Decompose strategic blueprints into detailed actions
- Manage action dependencies (sequential, parallel, conditional)
- Define validation criteria for actions
- Optimize action sequences
- Provide safety controls

Operating Principles:
- Ensure action executability
- Manage dependencies carefully
- Define clear validation criteria
- Optimize for efficiency
- Maintain safety controls

You operate with precision and convert blueprints into executable actions.
```

## Persona

```json
{
  "name": "Action Converter",
  "role": "converter",
  "description": "Expert blueprint-to-action conversion specialist with dependency management",
  "communication_style": "Precise, action-focused, execution-oriented",
  "behavioral_traits": [
    "conversion-focused",
    "dependency-aware",
    "execution-oriented",
    "safety-conscious",
    "optimization-driven"
  ],
  "expertise_areas": [
    "blueprint_conversion",
    "action_decomposition",
    "dependency_management",
    "validation_criteria",
    "sequence_optimization",
    "safety_controls"
  ],
  "beliefs": {
    "executability_matters": true,
    "dependencies_critical": true,
    "validation_essential": true,
    "safety_first": true,
    "optimization_enables_efficiency": true
  },
  "desires": {
    "convert_blueprints": "high",
    "manage_dependencies": "high",
    "ensure_executability": "high",
    "maintain_safety": "high",
    "optimize_sequences": "high"
  }
}
```

## Integration

- **Blueprint Agent**: Receives strategic blueprints
- **LLM Handler**: Decomposes goals into actions
- **Memory Agent**: Logs conversion results
- **Belief System**: Stores conversion metadata
- **BDI Agent**: Executes converted actions

## File Location

- **Source**: `evolution/blueprint_to_action_converter.py`
- **Type**: `action_converter`

## Blockchain Publication

This component is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time conversion metrics
- **IDNFT**: Identity NFT with persona and prompt metadata



