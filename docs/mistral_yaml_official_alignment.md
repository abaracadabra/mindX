# Mistral YAML Configuration - Official API Alignment

## Overview

The `mistral.yaml` configuration file has been updated to align with the official Mistral AI API specification (OpenAPI 3.1.0). This document explains how our configuration maps to the official API capabilities and model specifications.

## Official API Capabilities Mapping

### Model Capabilities (from ModelCapabilities schema)

Our YAML configuration now includes comprehensive capability flags that map directly to the official API:

```yaml
supports_streaming: true          # Maps to completion_chat streaming
supports_function_calling: true   # Maps to function_calling capability
supports_fim: true               # Maps to completion_fim capability
supports_vision: true            # Maps to vision capability
supports_classification: false   # Maps to classification capability
supports_fine_tuning: true       # Maps to fine_tuning capability
```

### Model Types

Based on the official API, we now distinguish between:

- **Base Models** (`model_type: base`): Standard Mistral models
- **Fine-tuned Models** (`model_type: fine-tuned`): Custom fine-tuned models
- **Embedding Models**: Specialized for vector embeddings

### Official Model Registry

Our configuration includes all models from the official Mistral AI API:

#### Chat Completion Models
- `mistral-large-latest` - Latest large model
- `mistral-small-latest` - Latest small model  
- `mistral-medium-latest` - Latest medium model
- `mistral-nemo-latest` - Latest Nemo model

#### Code Generation Models (FIM)
- `codestral-latest` - Latest Codestral model
- `codestral-22b-latest` - 22B parameter Codestral
- `codestral-2405` - Specific Codestral version

#### Vision Models
- `pixtral-12b-latest` - 12B parameter vision model

#### Embedding Models
- `mistral-embed` - Standard embedding model
- `mistral-embed-v2` - Version 2 embedding model

#### Fine-tunable Models
- `ministral-3b-latest` - 3B parameter fine-tunable
- `ministral-8b-latest` - 8B parameter fine-tunable
- `open-mistral-7b` - Open source 7B model
- `open-mistral-nemo` - Open source Nemo model

## API Endpoint Mapping

### Chat Completions (`/v1/chat/completions`)
```yaml
assessed_capabilities:
  - chat_completion
  - streaming
  - function_calling
```

### FIM Completions (`/v1/fim/completions`)
```yaml
assessed_capabilities:
  - fim_completion
  - fill_in_middle
```

### Embeddings (`/v1/embeddings`)
```yaml
assessed_capabilities:
  - embedding
  - text_embedding
  - vector_search
```

### Agents API (`/v1/agents/*`)
```yaml
assessed_capabilities:
  - chat_completion
  - function_calling
  - streaming
```

### OCR API (`/v1/ocr`)
```yaml
assessed_capabilities:
  - vision
  - image_analysis
  - ocr
```

## Enhanced Model Information

### Comprehensive Capability Flags

Each model now includes detailed capability information:

```yaml
mistral/mistral-large-latest:
  # Core capabilities
  supports_streaming: true
  supports_function_calling: true
  supports_fim: false
  supports_vision: false
  supports_classification: false
  supports_fine_tuning: false
  
  # Model metadata
  model_type: base
  owned_by: mistralai
  api_name: mistral-large-latest
  
  # Comprehensive capabilities
  assessed_capabilities:
    - text
    - reasoning
    - code_generation
    - multilingual
    - chat_completion
    - function_calling
    - streaming
```

### Task-Specific Scoring

Our task scoring system aligns with common use cases:

- **reasoning**: Complex problem-solving tasks
- **code_generation**: Programming and development
- **writing**: Content creation and editing
- **simple_chat**: Basic conversational AI
- **data_analysis**: Data processing and analysis
- **speed_sensitive**: Low-latency requirements

## Official API Integration Benefits

### 1. Accurate Model Selection
The enhanced configuration enables precise model selection based on:
- Required capabilities (vision, FIM, function calling)
- Performance requirements (reasoning scores)
- Cost optimization (pricing information)
- Context length requirements

### 2. API Compatibility
Direct mapping to official API endpoints ensures:
- Correct model names for API calls
- Proper capability validation
- Accurate parameter handling

### 3. Future-Proof Design
The configuration structure supports:
- New model additions
- Capability updates
- API version changes
- Fine-tuned model integration

## Usage Examples

### Model Selection by Capability
```python
# Select best model for vision tasks
vision_models = [model for model in models 
                if model.get('supports_vision', False)]

# Select best model for code generation
code_models = [model for model in models 
              if 'fim_completion' in model.get('assessed_capabilities', [])]

# Select fine-tunable models
fine_tunable = [model for model in models 
               if model.get('supports_fine_tuning', False)]
```

### Task-Based Selection
```python
# Get best model for reasoning tasks
best_reasoning = max(models, key=lambda m: m['task_scores']['reasoning'])

# Get fastest model for speed-sensitive tasks
fastest = max(models, key=lambda m: m['task_scores']['speed_sensitive'])
```

## Configuration Validation

The updated configuration includes validation against the official API:

1. **Model Name Validation**: All model names match official API
2. **Capability Validation**: Capabilities align with API specifications
3. **Pricing Validation**: Costs reflect official pricing
4. **Context Length Validation**: Max context lengths are accurate

## Migration from Previous Version

### Added Fields
- `supports_fim`: Fill-in-the-middle capability
- `supports_vision`: Vision/image processing capability
- `supports_classification`: Content classification capability
- `supports_fine_tuning`: Fine-tuning capability
- `model_type`: Base or fine-tuned model type
- `owned_by`: Model ownership information

### Enhanced Capabilities
- More comprehensive `assessed_capabilities` lists
- Better task scoring granularity
- Official API endpoint mapping

### Backward Compatibility
- All existing fields maintained
- Existing functionality preserved
- Enhanced with additional information

## Conclusion

The updated `mistral.yaml` configuration provides comprehensive alignment with the official Mistral AI API specification, enabling:

- **Accurate Model Selection**: Based on official capabilities
- **API Compatibility**: Direct mapping to official endpoints
- **Future-Proof Design**: Supports new models and capabilities
- **Enhanced Integration**: Better model selection and routing

This alignment ensures that the MindX system can fully leverage Mistral AI's capabilities while maintaining compatibility with the official API specification.
