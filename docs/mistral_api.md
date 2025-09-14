# Mistral AI API Integration Documentation

## Overview

The `mistral_api.py` module provides comprehensive integration with Mistral AI's extensive API suite, enabling mindX agents to leverage advanced AI capabilities including reasoning, code generation, embeddings, classification, and more.

## Table of Contents

- [Architecture](#architecture)
- [Core Components](#core-components)
- [API Coverage](#api-coverage)
- [mindX Integration Methods](#mindx-integration-methods)
- [Usage Examples](#usage-examples)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Performance Considerations](#performance-considerations)
- [Security](#security)

## Architecture

### Design Principles

1. **Modular Integration** - Non-invasive additions to existing mindX codebase
2. **Async-First** - Full asynchronous operation for optimal performance
3. **Type Safety** - Comprehensive type hints for better development experience
4. **Error Resilience** - Robust error handling and retry mechanisms
5. **Rate Limiting** - Built-in request throttling to respect API limits

### Component Structure

```
mistral_api.py
├── MistralAPIClient          # Low-level API client
├── MistralIntegration        # High-level mindX integration
├── MistralConfig            # Configuration management
├── Data Classes             # Request/response structures
└── Utility Functions        # Helper functions
```

## Core Components

### MistralAPIClient

The low-level client providing access to all Mistral AI API endpoints.

**Key Features:**
- Complete API coverage (Chat, FIM, Agents, Embeddings, etc.)
- Async/await support
- Automatic retry with exponential backoff
- Rate limiting with semaphore-based throttling
- Comprehensive error handling

**Usage:**
```python
async with MistralAPIClient(config) as client:
    response = await client.chat_completion(request)
```

### MistralIntegration

High-level integration class designed specifically for mindX agents.

**Key Features:**
- Simplified interfaces for common operations
- mindX-specific helper methods
- Agent-focused functionality
- Memory system integration

**Usage:**
```python
async with MistralIntegration(config) as mistral:
    reasoning = await mistral.enhance_reasoning(context, question)
```

### MistralConfig

Configuration management for API settings.

**Parameters:**
- `api_key`: Mistral API key
- `base_url`: API base URL (default: https://api.mistral.ai/v1)
- `timeout`: Request timeout in seconds (default: 30)
- `max_retries`: Maximum retry attempts (default: 3)
- `rate_limit_delay`: Delay between requests (default: 0.1s)

## API Coverage

### 1. Chat Completion API
- **Endpoint**: `/v1/chat/completions`
- **Models**: mistral-small/medium/large-latest
- **Features**: Reasoning mode, tool calling, streaming
- **Use Cases**: Agent reasoning, conversation handling

### 2. Fill-in-the-Middle (FIM) API
- **Endpoint**: `/v1/fim/completions`
- **Models**: codestral-2405, codestral-latest
- **Features**: Code completion, context-aware generation
- **Use Cases**: Code generation, tool development

### 3. Agents API
- **Endpoints**: `/v1/agents/*`
- **Features**: Agent creation, management, completion
- **Use Cases**: Specialized agent creation, task delegation

### 4. Embeddings API
- **Endpoint**: `/v1/embeddings`
- **Models**: mistral-embed
- **Features**: Text embedding, vector search
- **Use Cases**: Memory systems, knowledge retrieval

### 5. Classification & Moderation API
- **Endpoints**: `/v1/moderations`, `/v1/classifications`
- **Features**: Content safety, intent classification
- **Use Cases**: Safety filtering, agent routing

### 6. Files API
- **Endpoints**: `/v1/files/*`
- **Features**: File upload, management, processing
- **Use Cases**: Document processing, data ingestion

### 7. Fine-tuning API
- **Endpoints**: `/v1/fine_tuning/*`
- **Features**: Custom model training, job management
- **Use Cases**: Specialized model creation

### 8. Models API
- **Endpoints**: `/v1/models/*`
- **Features**: Model listing, information retrieval
- **Use Cases**: Model selection, capability discovery

### 9. Batch API
- **Endpoints**: `/v1/batch/*`
- **Features**: Large-scale processing, job management
- **Use Cases**: Bulk operations, data processing

### 10. OCR API
- **Endpoint**: `/v1/ocr`
- **Features**: Document text extraction, image analysis
- **Use Cases**: Document processing, data extraction

### 11. Transcription API
- **Endpoints**: `/v1/audio/transcriptions`
- **Features**: Audio-to-text conversion, streaming
- **Use Cases**: Voice input processing, audio analysis

### 12. Conversations API
- **Endpoints**: `/v1/conversations/*`
- **Features**: Persistent conversations, history management
- **Use Cases**: Long-term dialogue, context preservation

### 13. Libraries API
- **Endpoints**: `/v1/libraries/*`
- **Features**: Knowledge base management, document indexing
- **Use Cases**: Knowledge storage, retrieval systems

## mindX Integration Methods

### enhance_reasoning()
Boost agent reasoning capabilities using Mistral's reasoning mode.

```python
reasoning = await mistral.enhance_reasoning(
    context="mindX autonomous system context",
    question="How to optimize agent coordination?",
    model=MistralModel.MISTRAL_LARGE_LATEST
)
```

**Use Cases:**
- BDI Agent decision making
- Strategic planning
- Complex problem solving

### generate_code()
Generate code using Mistral's specialized code models.

```python
code = await mistral.generate_code(
    prompt="def optimize_agent_performance(",
    suffix="return optimized_result",
    model=MistralModel.CODESTRAL_LATEST
)
```

**Use Cases:**
- Tool development
- Code generation
- Agent capability expansion

### create_embeddings_for_memory()
Create embeddings for memory storage and retrieval.

```python
embeddings = await mistral.create_embeddings_for_memory([
    "Agent coordination principles",
    "Memory management strategies"
])
```

**Use Cases:**
- Memory Agent knowledge storage
- Belief System integration
- Knowledge retrieval

### classify_agent_intent()
Classify agent intent for routing and decision making.

```python
classification = await mistral.classify_agent_intent(
    "I need help with code generation"
)
```

**Use Cases:**
- Coordinator Agent routing
- Task delegation
- Intent recognition

### moderate_agent_output()
Moderate agent output for safety and compliance.

```python
moderation = await mistral.moderate_agent_output(
    "Agent response content"
)
```

**Use Cases:**
- Guardian Agent safety checks
- Content filtering
- Compliance monitoring

### process_document()
Process documents with OCR and store in knowledge libraries.

```python
result = await mistral.process_document(
    file_path="/path/to/document.pdf",
    library_id="knowledge-base-123"
)
```

**Use Cases:**
- Document ingestion
- Knowledge base population
- Information extraction

### transcribe_audio_for_agent()
Transcribe audio for agent processing.

```python
transcript = await mistral.transcribe_audio_for_agent(
    file_path="/path/to/audio.wav",
    language="en"
)
```

**Use Cases:**
- Voice input processing
- Audio analysis
- Multimodal interactions

## Usage Examples

### Basic Setup

```python
from api.mistral_api import MistralIntegration, create_mistral_config

# Create configuration
config = create_mistral_config(api_key="your-api-key-here")

# Use high-level integration
async with MistralIntegration(config) as mistral:
    # Your operations here
    pass
```

### Agent Reasoning Enhancement

```python
async def enhance_agent_reasoning(agent_context, user_query):
    async with MistralIntegration(config) as mistral:
        reasoning = await mistral.enhance_reasoning(
            context=agent_context,
            question=user_query,
            model=MistralModel.MISTRAL_LARGE_LATEST
        )
        return reasoning
```

### Code Generation for Tools

```python
async def generate_agent_tool(tool_description):
    async with MistralIntegration(config) as mistral:
        code = await mistral.generate_code(
            prompt=f"def {tool_description}(",
            suffix="return result",
            model=MistralModel.CODESTRAL_LATEST
        )
        return code
```

### Memory System Integration

```python
async def store_knowledge_in_memory(knowledge_items):
    async with MistralIntegration(config) as mistral:
        embeddings = await mistral.create_embeddings_for_memory(knowledge_items)
        
        # Store in mindX memory system
        for item, embedding in zip(knowledge_items, embeddings):
            await memory_agent.store_with_embedding(item, embedding)
```

### Document Processing Pipeline

```python
async def process_document_pipeline(file_path):
    async with MistralIntegration(config) as mistral:
        # Process document
        result = await mistral.process_document(file_path)
        
        # Extract insights
        insights = await mistral.enhance_reasoning(
            context=result["ocr_result"]["document_annotation"],
            question="What are the key insights from this document?"
        )
        
        return {
            "file_info": result["file_info"],
            "extracted_text": result["ocr_result"],
            "insights": insights
        }
```

## Configuration

### Environment Variables

```bash
# Required
MISTRAL_API_KEY=your-mistral-api-key

# Optional
MISTRAL_BASE_URL=https://api.mistral.ai/v1
MISTRAL_TIMEOUT=30
MISTRAL_MAX_RETRIES=3
MISTRAL_RATE_LIMIT_DELAY=0.1
```

### Configuration Object

```python
from api.mistral_api import MistralConfig

config = MistralConfig(
    api_key="your-api-key",
    base_url="https://api.mistral.ai/v1",
    timeout=30,
    max_retries=3,
    rate_limit_delay=0.1
)
```

## Error Handling

### Exception Types

- `MistralAPIError`: Custom exception for API-related errors
- `aiohttp.ClientError`: Network and connection errors
- `json.JSONDecodeError`: Response parsing errors

### Error Recovery

```python
try:
    response = await client.chat_completion(request)
except MistralAPIError as e:
    logger.error(f"Mistral API error: {e}")
    # Handle API-specific errors
except aiohttp.ClientError as e:
    logger.error(f"Network error: {e}")
    # Handle network errors
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle unexpected errors
```

### Retry Logic

The client automatically retries failed requests with exponential backoff:
- Initial retry after 1 second
- Subsequent retries after 2, 4, 8 seconds
- Maximum of 3 retry attempts

## Performance Considerations

### Rate Limiting

- Built-in semaphore-based rate limiting
- Configurable delay between requests
- Respects Mistral API rate limits

### Async Operations

- Full async/await support
- Non-blocking I/O operations
- Concurrent request handling

### Memory Management

- Proper resource cleanup with context managers
- Efficient data structures
- Minimal memory footprint

### Caching

Consider implementing caching for:
- Model information
- Embedding vectors
- Frequently accessed data

## Security

### API Key Management

- Store API keys in environment variables
- Never hardcode sensitive information
- Use secure configuration management

### Data Privacy

- All requests go through HTTPS
- No data is stored locally by default
- Respect data retention policies

### Input Validation

- Validate all input parameters
- Sanitize user inputs
- Implement proper error handling

## Integration with mindX Components

### BDI Agent Integration

```python
class EnhancedBDIAgent(BDIAgent):
    def __init__(self, mistral_config):
        super().__init__()
        self.mistral_config = mistral_config
    
    async def enhanced_reasoning(self, context, goal):
        async with MistralIntegration(self.mistral_config) as mistral:
            return await mistral.enhance_reasoning(context, goal)
```

### Memory Agent Integration

```python
class EnhancedMemoryAgent(MemoryAgent):
    def __init__(self, mistral_config):
        super().__init__()
        self.mistral_config = mistral_config
    
    async def store_with_embeddings(self, content):
        async with MistralIntegration(self.mistral_config) as mistral:
            embeddings = await mistral.create_embeddings_for_memory([content])
            return await self.store(content, embeddings[0])
```

### Coordinator Agent Integration

```python
class EnhancedCoordinatorAgent(CoordinatorAgent):
    def __init__(self, mistral_config):
        super().__init__()
        self.mistral_config = mistral_config
    
    async def classify_and_route(self, message):
        async with MistralIntegration(self.mistral_config) as mistral:
            classification = await mistral.classify_agent_intent(message)
            return await self.route_to_agent(message, classification)
```

## Testing

### Connection Testing

```python
from api.mistral_api import test_mistral_connection

async def test_connection():
    config = create_mistral_config(api_key="test-key")
    success = await test_mistral_connection(config)
    assert success, "Failed to connect to Mistral API"
```

### Unit Testing

```python
import pytest
from api.mistral_api import MistralIntegration, MistralConfig

@pytest.mark.asyncio
async def test_enhance_reasoning():
    config = MistralConfig(api_key="test-key")
    async with MistralIntegration(config) as mistral:
        result = await mistral.enhance_reasoning("test context", "test question")
        assert isinstance(result, str)
        assert len(result) > 0
```

## Monitoring and Logging

### Logging Configuration

```python
import logging

# Configure logging for Mistral API
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('mistral_api')

# Log API calls
logger.info(f"Making API call to {endpoint}")
logger.debug(f"Request payload: {payload}")
logger.info(f"Response received: {response}")
```

### Performance Monitoring

```python
import time

async def monitored_api_call():
    start_time = time.time()
    try:
        result = await client.chat_completion(request)
        duration = time.time() - start_time
        logger.info(f"API call completed in {duration:.2f}s")
        return result
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"API call failed after {duration:.2f}s: {e}")
        raise
```

## Future Enhancements

### Planned Features

1. **Caching Layer** - Implement Redis-based caching for embeddings and responses
2. **Batch Processing** - Enhanced batch operations for large-scale processing
3. **Streaming Support** - Real-time streaming for conversations and completions
4. **Custom Models** - Integration with fine-tuned models
5. **Analytics** - Usage analytics and performance metrics

### Extension Points

1. **Custom Integrations** - Easy extension for new mindX components
2. **Plugin System** - Modular plugin architecture
3. **Configuration Management** - Advanced configuration options
4. **Monitoring Integration** - Integration with mindX monitoring system

## Troubleshooting

### Common Issues

1. **API Key Issues**
   - Verify API key is correct
   - Check API key permissions
   - Ensure sufficient credits

2. **Rate Limiting**
   - Increase `rate_limit_delay`
   - Reduce concurrent requests
   - Implement exponential backoff

3. **Timeout Issues**
   - Increase `timeout` value
   - Check network connectivity
   - Verify API endpoint availability

4. **Memory Issues**
   - Use context managers properly
   - Implement proper cleanup
   - Monitor memory usage

### Debug Mode

```python
import logging

# Enable debug logging
logging.getLogger('mistral_api').setLevel(logging.DEBUG)

# Enable request/response logging
config = MistralConfig(
    api_key="your-key",
    debug=True  # Enable debug mode
)
```

## Conclusion

The Mistral AI API integration provides mindX with comprehensive access to advanced AI capabilities while maintaining the modular, non-invasive architecture required for the hackathon. The integration supports all major Mistral AI services and provides mindX-specific helper methods for seamless agent enhancement.

For more information, refer to:
- [Mistral AI Documentation](https://docs.mistral.ai/)
- [mindX Architecture Documentation](./agents_architectural_reference.md)
- [API Server Documentation](./api_server.md)
