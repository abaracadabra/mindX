# MindXAgent Ollama Chat Integration

## Overview

MindXAgent now includes persistent Ollama chat capabilities with dynamic model discovery and adaptation. This enables mindXagent to:

- Chat with any available Ollama model
- Maintain persistent connections with `keep_alive`
- Automatically discover new models as they emerge
- Adapt to newly trained models
- Manage conversation history across sessions

## Architecture

### Components

1. **OllamaChatManager** (`agents/core/ollama_chat_manager.py`)
   - Persistent connection management
   - Dynamic model discovery (periodic refresh every 5 minutes)
   - Chat conversation history management
   - Model selection and adaptation
   - Automatic reconnection on failures

2. **MindXAgent Integration** (`agents/core/mindXagent.py`)
   - `chat_with_ollama()` - Main chat interface
   - `get_available_ollama_models()` - List available models
   - `select_ollama_model()` - Select best model for task
   - `get_ollama_conversation_history()` - Get conversation history
   - `clear_ollama_conversation()` - Clear conversation history

## Features

### 1. Persistent Connections

- Uses `keep_alive="10m"` to keep models loaded in memory
- Automatic reconnection on connection failures
- Connection state monitoring

### 2. Dynamic Model Discovery

- Periodic model discovery every 5 minutes (configurable)
- Automatic detection of new models
- Callback system for new model notifications
- Model capability tracking (size, quantization, family, etc.)

### 3. Chat Functionality

- Full conversation history management
- Per-conversation history (by conversation_id)
- Persistent storage in `data/ollama_chat_history.json`
- System prompt support
- Configurable temperature and max_tokens

### 4. Model Selection

- Task-based model selection (chat, reasoning, coding, multimodal)
- Preferred model support
- Automatic fallback to best available model
- Model capability matching

## Usage

### Basic Chat

```python
# Get mindXagent instance
mindx_agent = await MindXAgent.get_instance()

# Chat with default model
result = await mindx_agent.chat_with_ollama(
    message="Analyze the current system state and suggest improvements",
    temperature=0.7,
    max_tokens=2000
)

if result.get("success"):
    print(f"Response: {result['content']}")
    print(f"Model: {result['model']}")
    print(f"Latency: {result['latency']:.2f}s")
```

### Chat with Specific Model

```python
result = await mindx_agent.chat_with_ollama(
    message="Explain quantum computing",
    model="mistral-nemo:latest",
    temperature=0.5
)
```

### Chat with System Prompt

```python
result = await mindx_agent.chat_with_ollama(
    message="What should I do next?",
    system_prompt="You are a helpful AI assistant specialized in software development.",
    conversation_id="dev_assistant"
)
```

### Get Available Models

```python
models = await mindx_agent.get_available_ollama_models()
for model in models:
    print(f"Model: {model['name']}")
    print(f"  Size: {model.get('size', 'unknown')}")
    print(f"  Parameters: {model.get('details', {}).get('parameter_size', 'unknown')}")
```

### Select Best Model for Task

```python
# Select best model for reasoning
model = await mindx_agent.select_ollama_model(
    task_type="reasoning",
    preferred_models=["mistral-nemo:latest", "deepseek-r1:latest"]
)
```

### Get Conversation History

```python
history = mindx_agent.get_ollama_conversation_history("dev_assistant")
for msg in history:
    print(f"{msg['role']}: {msg['content'][:100]}...")
```

### Clear Conversation

```python
mindx_agent.clear_ollama_conversation("dev_assistant")
```

## Configuration

### Environment Variables

```bash
# Ollama server URL
export MINDX_LLM__OLLAMA__BASE_URL="http://10.0.0.155:18080"
```

### Config File

```json
{
  "llm": {
    "ollama": {
      "base_url": "http://10.0.0.155:18080"
    }
  }
}
```

### OllamaChatManager Parameters

- `base_url`: Ollama server URL (default: `http://localhost:11434`)
- `model_discovery_interval`: Seconds between model discovery (default: 300)
- `keep_alive`: How long to keep models loaded (default: `"10m"`)
- `conversation_history_path`: Path to save conversation history

## Model Discovery

### Automatic Discovery

Models are automatically discovered:
- On initialization
- Every 5 minutes (configurable)
- When `discover_models(force=True)` is called

### New Model Detection

When new models are discovered:
- Logged to mindXagent's memory
- Callbacks are notified
- Model capabilities are tracked
- Available for immediate use

### Model Capabilities

Each model's capabilities are tracked:
- Size (bytes)
- Parameter size (e.g., "7.6B")
- Quantization level (e.g., "Q4_K_M")
- Model family (e.g., "llama", "mistral")
- Last modified date
- Discovery timestamp

## Conversation Management

### Conversation IDs

- Default: `{agent_id}_default`
- Custom: Any string identifier
- Per-conversation history is maintained separately

### History Storage

- Stored in: `data/ollama_chat_history.json`
- Format: JSON with sessions dictionary
- Auto-saved after each message
- Loaded on initialization

### History Structure

```json
{
  "sessions": {
    "mindx_meta_agent_default": [
      {"role": "user", "content": "Hello"},
      {"role": "assistant", "content": "Hi! How can I help?"}
    ]
  },
  "last_saved": "2026-01-17T22:00:00"
}
```

## Task-Based Model Selection

### Task Types

- `chat`: General conversation (default)
- `reasoning`: Complex reasoning tasks
- `coding`: Code generation and analysis
- `multimodal`: Vision and image tasks

### Selection Logic

1. Check preferred models (if provided)
2. Match task keywords to model names
3. Prefer smaller models (avoid 30b+ for speed)
4. Fallback to first available model

### Example

```python
# For reasoning task
model = await mindx_agent.select_ollama_model("reasoning")
# Prefers: nemo, reasoning, thinking, deepseek models

# For coding task
model = await mindx_agent.select_ollama_model("coding")
# Prefers: code, codellama, deepseek-coder models
```

## Error Handling

### Connection Errors

- Automatic retry (up to 3 attempts)
- Graceful degradation
- Connection state tracking

### Model Errors

- Fallback to alternative models
- Error logging
- User-friendly error messages

### Timeout Handling

- Extended timeouts (120s total, 60s read)
- Clear timeout error messages
- Automatic model selection for faster models

## Integration with MindXAgent

### Initialization

OllamaChatManager is automatically initialized during mindXagent's `_async_init()`:
- Connection test
- Model discovery
- Best model selection
- Periodic discovery task started

### Memory Integration

All chat interactions are logged to MemoryAgent:
- Message and response
- Model used
- Conversation ID
- Timestamps
- Tags: `["chat", "ollama", "interaction"]`

### Thinking Process

Chat requests are logged to thinking process:
- `ollama_chat_request`: Request details
- `ollama_chat_response`: Response metadata
- `ollama_chat_error`: Error information

## Best Practices

1. **Use Conversation IDs**: Maintain separate conversations for different contexts
2. **Select Appropriate Models**: Use task-based selection for best results
3. **Monitor Model Discovery**: Check for new models periodically
4. **Clear Old Conversations**: Free memory by clearing unused conversations
5. **Use System Prompts**: Provide context for better responses
6. **Adjust Temperature**: Lower for factual, higher for creative

## Example: Complete Chat Session

```python
# Initialize
mindx_agent = await MindXAgent.get_instance()

# Discover models
models = await mindx_agent.get_available_ollama_models()
print(f"Available models: {[m['name'] for m in models]}")

# Select best model for reasoning
model = await mindx_agent.select_ollama_model("reasoning")
print(f"Selected model: {model}")

# Start conversation
result = await mindx_agent.chat_with_ollama(
    message="What are the key principles of self-improving AI systems?",
    model=model,
    conversation_id="ai_discussion",
    system_prompt="You are an expert in AI systems and self-improvement.",
    temperature=0.7
)

# Continue conversation
result = await mindx_agent.chat_with_ollama(
    message="How can these principles be applied to mindX?",
    conversation_id="ai_discussion"
)

# View history
history = mindx_agent.get_ollama_conversation_history("ai_discussion")
print(f"Conversation has {len(history)} messages")

# Clear when done
mindx_agent.clear_ollama_conversation("ai_discussion")
```

## Future Enhancements

- Streaming responses
- Tool calling support
- Structured outputs (JSON schemas)
- Multimodal chat (images)
- Model performance tracking
- Cost estimation
- Conversation summarization
