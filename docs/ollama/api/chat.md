# API Reference: Chat — POST /api/chat

> Conversational completions with message history, tool calling, thinking, vision.

## Endpoint

```
POST http://localhost:11434/api/chat
POST https://ollama.com/api/chat  # Cloud (requires OLLAMA_API_KEY)
```

## Request Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `model` | string | — | **yes** | Model name |
| `messages` | ChatMessage[] | — | **yes** | Conversation history |
| `tools` | ToolDefinition[] | — | no | Function tools the model may invoke |
| `format` | string\|object | — | no | `"json"` or JSON schema |
| `stream` | boolean | `true` | no | Stream partial responses |
| `think` | boolean\|string | — | no | Enable thinking. `true`/`false` or `"high"`/`"medium"`/`"low"` |
| `keep_alive` | string\|number | `"5m"` | no | Model memory duration |
| `options` | ModelOptions | — | no | temperature, top_k, top_p, etc. |
| `logprobs` | boolean | — | no | Return token log probabilities |
| `top_logprobs` | integer | — | no | Most likely tokens per position |

### ChatMessage

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `role` | string | **yes** | `"system"`, `"user"`, `"assistant"`, or `"tool"` |
| `content` | string | **yes** | Message text |
| `images` | string[] | no | Base64-encoded images (vision models) |
| `tool_calls` | ToolCall[] | no | Tool invocations (assistant messages) |

### ToolDefinition

```json
{
  "type": "function",
  "function": {
    "name": "get_temperature",
    "description": "Get the current temperature for a city",
    "parameters": {
      "type": "object",
      "required": ["city"],
      "properties": {
        "city": {"type": "string", "description": "City name"}
      }
    }
  }
}
```

### ToolCall (in response)

```json
{
  "function": {
    "name": "get_temperature",
    "arguments": {"city": "New York"}
  }
}
```

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `model` | string | Model name |
| `created_at` | string | ISO 8601 timestamp |
| `message` | object | `{role, content, thinking, tool_calls, images}` |
| `done` | boolean | Generation complete |
| `done_reason` | string | Termination cause |
| `total_duration` | integer | Total time (nanoseconds) |
| `load_duration` | integer | Model load time (ns) |
| `prompt_eval_count` | integer | Input tokens |
| `prompt_eval_duration` | integer | Prompt eval time (ns) |
| `eval_count` | integer | Output tokens |
| `eval_duration` | integer | Generation time (ns) |

## Examples

### Basic Chat

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [
    {"role": "user", "content": "Why is the sky blue?"}
  ],
  "stream": false
}'
```

### Multi-Turn Conversation

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is Rayleigh scattering?"},
    {"role": "assistant", "content": "Rayleigh scattering is the scattering of light by particles smaller than the wavelength of radiation."},
    {"role": "user", "content": "How does that make the sky blue?"}
  ],
  "stream": false
}'
```

### Structured Output with Schema

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [{"role": "user", "content": "Tell me about Canada."}],
  "stream": false,
  "format": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "capital": {"type": "string"},
      "languages": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["name", "capital", "languages"]
  }
}'
```

### Tool Calling — Single Tool

```bash
# Step 1: Model requests tool call
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [{"role": "user", "content": "What is the temperature in New York?"}],
  "stream": false,
  "tools": [{
    "type": "function",
    "function": {
      "name": "get_temperature",
      "description": "Get the current temperature for a city",
      "parameters": {
        "type": "object",
        "required": ["city"],
        "properties": {
          "city": {"type": "string", "description": "City name"}
        }
      }
    }
  }]
}'

# Step 2: Send tool result back
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [
    {"role": "user", "content": "What is the temperature in New York?"},
    {"role": "assistant", "tool_calls": [{"type": "function", "function": {"index": 0, "name": "get_temperature", "arguments": {"city": "New York"}}}]},
    {"role": "tool", "tool_name": "get_temperature", "content": "22C"}
  ],
  "stream": false
}'
```

### Thinking

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "deepseek-r1:1.5b",
  "messages": [{"role": "user", "content": "How many r letters in strawberry?"}],
  "think": true,
  "stream": false
}'
```

Response includes `message.thinking` (reasoning trace) and `message.content` (final answer).

### Vision (Image Input)

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "gemma3",
  "messages": [{
    "role": "user",
    "content": "What is in this image?",
    "images": ["iVBORw0KGgoAAAANSUhEUg...base64..."]
  }],
  "stream": false
}'
```

### Preload / Unload Model

```bash
# Preload
curl http://localhost:11434/api/chat -d '{"model": "qwen3:1.7b"}'

# Unload immediately
curl http://localhost:11434/api/chat -d '{"model": "qwen3:1.7b", "keep_alive": 0}'

# Keep loaded forever
curl http://localhost:11434/api/chat -d '{"model": "qwen3:1.7b", "keep_alive": -1}'
```

## Streaming Response Format

Each chunk is newline-delimited JSON:

```json
{"model":"qwen3:1.7b","created_at":"...","message":{"role":"assistant","content":"The"},"done":false}
{"model":"qwen3:1.7b","created_at":"...","message":{"role":"assistant","content":" sky"},"done":false}
{"model":"qwen3:1.7b","created_at":"...","message":{"role":"assistant","content":""},"done":true,"done_reason":"stop","total_duration":...,"eval_count":42}
```

The final chunk (`done: true`) includes performance metrics.

## mindX Integration

```python
# Via OllamaAPI (api/ollama/ollama_url.py) — uses /api/chat when use_chat=True
result = await ollama_api.generate_text(
    prompt="What is the weather?",
    model="qwen3:1.7b",
    use_chat=True,
    messages=[
        {"role": "system", "content": "You are mindX, an autonomous AI."},
        {"role": "user", "content": "What is the weather?"}
    ]
)

# Via OllamaChatManager (agents/core/ollama_chat_manager.py)
response = await chat_manager.chat(
    message="Analyze the latest improvement cycle",
    model="qwen3:1.7b",
    system_prompt="You are mindX's autonomous improvement agent."
)
```
