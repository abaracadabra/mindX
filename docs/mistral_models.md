# Mistral AI Models Configuration

## Overview

The `models/mistral.yaml` file provides comprehensive configuration for all Mistral AI models available through their API. This configuration follows the same structure as the Gemini models configuration, ensuring consistency across the MindX system.

## Model Categories

### **Large Language Models (LLMs)**

#### **Mistral Large Models**
- **`mistral-large-latest`** - Latest large model with excellent reasoning and writing capabilities
- **`mistral-large-2402`** - Specific version from February 2024
- **`mistral-8x22b-instruct`** - Mixture of experts model with 22B parameters per expert

#### **Mistral Small Models**
- **`mistral-small-latest`** - Latest small model optimized for speed and efficiency
- **`mistral-small-2402`** - Specific version from February 2024
- **`mistral-nemo-latest`** - Ultra-fast model for high-throughput applications
- **`mistral-nemo-12b-latest`** - Larger Nemo variant with 12B parameters

#### **Code Generation Models**
- **`codestral-latest`** - Latest code generation model
- **`codestral-22b-latest`** - Larger code model with 22B parameters
- **`codestral-2405`** - Specific version from May 2024

#### **Legacy Models**
- **`mistral-7b-instruct`** - Original 7B instruction-tuned model
- **`mistral-7b-instruct-v0.3`** - Version 0.3 of the 7B model
- **`mistral-8x7b-instruct`** - Mixture of experts with 7B parameters per expert
- **`mistral-8x7b-instruct-v0.1`** - Version 0.1 of the 8x7B model

### **Embedding Models**
- **`mistral-embed`** - Original embedding model
- **`mistral-embed-v2`** - Improved embedding model with better performance

## Configuration Structure

Each model entry includes the following parameters:

### **Task Scores (0.0 - 1.0)**
- **`reasoning`** - Logical reasoning and problem-solving ability
- **`code_generation`** - Code writing and programming capabilities
- **`writing`** - Creative and technical writing quality
- **`simple_chat`** - Conversational and chat capabilities
- **`data_analysis`** - Data processing and analysis skills
- **`speed_sensitive`** - Performance in time-critical applications

### **Pricing (per 1K tokens)**
- **`cost_per_kilo_input_tokens`** - Cost for input tokens
- **`cost_per_kilo_output_tokens`** - Cost for output tokens

### **Technical Specifications**
- **`max_context_length`** - Maximum context window size
- **`supports_streaming`** - Whether the model supports streaming responses
- **`supports_function_calling`** - Whether the model supports function calling
- **`api_name`** - The actual API identifier for the model

### **Capabilities**
- **`text`** - General text processing
- **`reasoning`** - Advanced reasoning capabilities
- **`code_generation`** - Code writing and programming
- **`multilingual`** - Multi-language support
- **`fill_in_middle`** - Fill-in-the-middle code completion
- **`embedding`** - Text embedding generation

## Model Selection Guidelines

### **For General Use**
- **Best Overall**: `mistral-large-latest` - Excellent balance of capabilities
- **Fast & Efficient**: `mistral-small-latest` - Good performance with lower cost
- **Ultra-Fast**: `mistral-nemo-latest` - Maximum speed for high-throughput needs

### **For Code Generation**
- **Best Code Model**: `codestral-latest` - Specialized for programming tasks
- **Advanced Code**: `codestral-22b-latest` - More powerful for complex code
- **Fill-in-Middle**: `codestral-*` models support FIM for code completion

### **For Embeddings**
- **Latest**: `mistral-embed-v2` - Improved performance and quality
- **Legacy**: `mistral-embed` - Original embedding model

### **For Cost Optimization**
- **Budget Option**: `mistral-nemo-latest` - Lowest cost per token
- **Balanced**: `mistral-small-latest` - Good performance-to-cost ratio
- **Premium**: `mistral-large-latest` - Best quality for complex tasks

## Context Length Considerations

### **128K Context Models**
- `mistral-large-latest`
- `mistral-small-latest`
- `mistral-nemo-latest`
- `codestral-latest`
- `codestral-22b-latest`
- `mistral-nemo-12b-latest`

### **64K Context Models**
- `mistral-8x22b-instruct`

### **32K Context Models**
- `mistral-7b-instruct`
- `mistral-8x7b-instruct`
- `mistral-7b-instruct-v0.3`
- `mistral-8x7b-instruct-v0.1`

### **8K Context Models**
- `mistral-embed`
- `mistral-embed-v2`

## Performance Characteristics

### **Speed vs Quality Trade-offs**

| Model | Speed | Quality | Cost | Best For |
|-------|-------|---------|------|----------|
| `mistral-nemo-latest` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | High-throughput, simple tasks |
| `mistral-small-latest` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Balanced performance |
| `mistral-large-latest` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | Complex reasoning, quality |
| `codestral-latest` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Code generation |

### **Task-Specific Recommendations**

#### **Reasoning Tasks**
- **Primary**: `mistral-large-latest` (0.92 score)
- **Alternative**: `mistral-8x22b-instruct` (0.90 score)

#### **Code Generation**
- **Primary**: `codestral-22b-latest` (0.96 score)
- **Alternative**: `codestral-latest` (0.95 score)

#### **Writing Tasks**
- **Primary**: `mistral-large-latest` (0.94 score)
- **Alternative**: `mistral-8x22b-instruct` (0.93 score)

#### **Chat/Conversation**
- **Primary**: `mistral-large-latest` (0.96 score)
- **Alternative**: `mistral-small-latest` (0.94 score)

#### **Data Analysis**
- **Primary**: `mistral-8x22b-instruct` (0.91 score)
- **Alternative**: `mistral-large-latest` (0.89 score)

## Integration with MindX

### **Default Model Selection**
The MindX system uses these models based on configuration:

```yaml
# In .env file
MINDX_LLM__MISTRAL__DEFAULT_MODEL="mistral-large-latest"
MINDX_LLM__MISTRAL__DEFAULT_MODEL_FOR_CODING="codestral-latest"
MINDX_LLM__MISTRAL__DEFAULT_MODEL_FOR_REASONING="mistral-large-latest"
```

### **Model Registry Integration**
The models are automatically registered in the MindX model registry and can be selected based on:

1. **Task requirements** - Automatic selection based on task scores
2. **Cost constraints** - Selection based on pricing tiers
3. **Performance needs** - Selection based on speed requirements
4. **Context length** - Selection based on input size

### **Graceful Degradation**
If Mistral API keys are not available, the system will:
- Log warnings about missing API keys
- Fall back to other LLM providers (Ollama, Gemini)
- Provide mock responses for testing

## Usage Examples

### **Basic Model Selection**
```python
from llm.llm_factory import LLMFactory

# Get a Mistral model
model = await LLMFactory.create_llm_handler(
    provider="mistral",
    model="mistral-large-latest"
)
```

### **Code Generation**
```python
# Use Codestral for code generation
code_model = await LLMFactory.create_llm_handler(
    provider="mistral",
    model="codestral-latest"
)
```

### **High-Speed Processing**
```python
# Use Nemo for high-throughput tasks
fast_model = await LLMFactory.create_llm_handler(
    provider="mistral",
    model="mistral-nemo-latest"
)
```

## Monitoring and Analytics

### **Performance Metrics**
The system tracks:
- **Token usage** - Input/output token consumption
- **Response times** - Model latency and throughput
- **Cost tracking** - Real-time cost monitoring
- **Quality scores** - Task-specific performance metrics

### **Model Comparison**
Built-in tools allow comparison of:
- **Performance across models** - Side-by-side capability analysis
- **Cost efficiency** - Cost per quality unit analysis
- **Speed benchmarks** - Response time comparisons

## Future Updates

The `mistral.yaml` file will be updated as new Mistral models are released. Updates include:
- **New model additions** - Latest model releases
- **Performance updates** - Refined task scores based on testing
- **Pricing updates** - Current API pricing information
- **Capability additions** - New features and capabilities

## Support and Troubleshooting

### **Common Issues**
1. **Model not found** - Check API name spelling
2. **Context length exceeded** - Use models with larger context windows
3. **Function calling not supported** - Use models that support function calling
4. **High costs** - Switch to more cost-effective models

### **Best Practices**
1. **Start with small models** - Test with `mistral-small-latest` first
2. **Monitor costs** - Use cost tracking features
3. **Choose appropriate context length** - Match model to input size
4. **Use specialized models** - Use `codestral-*` for code tasks

This configuration ensures optimal model selection and performance within the MindX system while maintaining cost efficiency and quality standards.
