# Ollama Model Capability Tool

## Overview

The Ollama Model Capability Tool (`api/ollama/ollama_model_capability_tool.py`) manages Ollama model capabilities and enables intelligent, task-specific model selection for mindX. It maintains a registry of available Ollama models with their capabilities, performance metrics, and task-specific suitability scores.

## Features

- **Automatic Model Discovery**: Discovers available Ollama models from the configured server
- **Capability Registration**: Stores model capabilities, task scores, and performance metrics
- **Intelligent Model Selection**: Selects the best model for specific task types
- **Persistent Storage**: Saves model capabilities to `data/config/ollama_model_capabilities.json`
- **Auto-Scoring**: Automatically assigns task scores based on model name patterns

## Usage

### Initialization

```python
from api.ollama.ollama_model_capability_tool import OllamaModelCapabilityTool
from utils.config import Config

config = Config()
tool = OllamaModelCapabilityTool(config=config)
```

### Discovering Models

```python
# Discover models from Ollama server
models = await tool.discover_models(base_url="http://localhost:11434")
```

### Auto-Discovery and Registration

```python
# Automatically discover and register all models with intelligent scoring
result = await tool.auto_discover_and_register(
    base_url="http://localhost:11434",
    auto_score=True
)
```

### Manual Model Registration

```python
# Register a model with specific capabilities
await tool.register_model(
    model_name="mistral-nemo:latest",
    capabilities=["code", "reasoning", "chat"],
    task_scores={
        "code_generation": 0.9,
        "reasoning": 0.85,
        "simple_chat": 0.95
    },
    size_gb=7.2,
    context_size=32768,
    notes="Excellent for coding and reasoning tasks"
)
```

### Selecting Best Model for Task

```python
# Get the best model for a specific task
best_model = tool.get_best_model_for_task("code_generation", min_score=0.7)
```

### Retrieving Model Information

```python
# Get all registered capabilities
all_caps = tool.get_all_capabilities()

# Get specific model info
model_info = tool.get_model_info("mistral-nemo:latest")
```

## Task Types

The tool supports the following task types (with auto-detection):

- **code_generation**: Code writing and generation
- **debugging**: Code debugging and error fixing
- **reasoning**: Logical reasoning and analysis
- **analysis**: Data and system analysis
- **simple_chat**: General conversation
- **conversation**: Multi-turn conversations
- **writing**: Text and content writing

## Model Capability Structure

```python
@dataclass
class ModelCapability:
    model_name: str
    size_gb: float
    context_size: int
    capabilities: List[str]  # e.g., ["code", "reasoning", "chat"]
    task_scores: Dict[str, float]  # Task type -> score (0-1)
    performance_metrics: Dict[str, Any]
    last_tested: Optional[str]
    notes: str
```

## Integration with Startup Agent

The Startup Agent automatically uses this tool when Ollama is connected:

1. **Auto-Connection**: Startup Agent connects to Ollama using saved configuration from `.env`
2. **Model Discovery**: Automatically discovers and registers all available models
3. **Capability Storage**: Stores model capabilities for future use
4. **Task Selection**: Uses stored capabilities to select best model for autonomous improvement tasks

## Configuration

Model capabilities are stored in:
- **File**: `data/config/ollama_model_capabilities.json`
- **Format**: JSON with model names as keys

## Autonomous Improvement

The Startup Agent uses this tool to:

1. Select the best Ollama model for analyzing startup logs
2. Use the selected model to generate improvement suggestions
3. Apply safe improvements automatically
4. Monitor and improve startup continuously

## Example

```python
# Initialize tool
tool = OllamaModelCapabilityTool()

# Auto-discover models
result = await tool.auto_discover_and_register(
    base_url="http://10.0.0.155:18080"
)

# Select best model for analysis
analysis_model = tool.get_best_model_for_task("analysis")
print(f"Best model for analysis: {analysis_model}")

# Get model details
model_info = tool.get_model_info(analysis_model)
print(f"Capabilities: {model_info['capabilities']}")
print(f"Task scores: {model_info['task_scores']}")
```

## See Also

- [Startup Agent Documentation](../agents/orchestration/startup_agent.md)
- [Ollama Integration](../api/ollama_url.py)
- [Model Selector](../llm/model_selector.py)
