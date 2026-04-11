# Thinking

> Thinking-capable models emit a `thinking` field separating reasoning trace from final answer.

Use this to: audit model steps, animate "thinking" in UI, or hide the trace when you only need the final response.

## Supported Models

- [Qwen 3](https://ollama.com/library/qwen3) — `think: true`/`false`
- [GPT-OSS](https://ollama.com/library/gpt-oss) — `think: "low"`/`"medium"`/`"high"` (cannot fully disable)
- [DeepSeek-v3.1](https://ollama.com/library/deepseek-v3.1) — `think: true`/`false`
- [DeepSeek R1](https://ollama.com/library/deepseek-r1) — `think: true`/`false`
- Browse latest: [thinking models](https://ollama.com/search?c=thinking)

**Note**: Thinking is enabled by default in CLI and API for supported models.

## API Usage

### Non-Streaming

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "deepseek-r1:1.5b",
  "messages": [{"role": "user", "content": "How many r letters in strawberry?"}],
  "think": true,
  "stream": false
}'
```

Response:
```json
{
  "message": {
    "role": "assistant",
    "thinking": "Let me count: s-t-r-a-w-b-e-r-r-y. The letter r appears at positions 3, 8, 9. So 3 times.",
    "content": "There are 3 letter r's in 'strawberry'."
  }
}
```

### GPT-OSS (Level-Based)

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "gpt-oss",
  "messages": [{"role": "user", "content": "What is 1+1?"}],
  "think": "low"
}'
```

**Note**: GPT-OSS ignores `true`/`false` — must use `"low"`, `"medium"`, or `"high"`.

## Python SDK

```python
from ollama import chat

# Non-streaming
response = chat(
    model='deepseek-r1:1.5b',
    messages=[{'role': 'user', 'content': 'How many r letters in strawberry?'}],
    think=True,
    stream=False,
)
print('Thinking:\n', response.message.thinking)
print('Answer:\n', response.message.content)

# Streaming with thinking
stream = chat(
    model='qwen3',
    messages=[{'role': 'user', 'content': 'What is 17 x 23?'}],
    think=True,
    stream=True,
)

in_thinking = False
for chunk in stream:
    if chunk.message.thinking and not in_thinking:
        in_thinking = True
        print('Thinking:\n', end='')
    if chunk.message.thinking:
        print(chunk.message.thinking, end='')
    elif chunk.message.content:
        if in_thinking:
            print('\n\nAnswer:\n', end='')
            in_thinking = False
        print(chunk.message.content, end='')
```

## JavaScript SDK

```javascript
import ollama from 'ollama'

// Non-streaming
const response = await ollama.chat({
    model: 'deepseek-r1',
    messages: [{ role: 'user', content: 'How many r letters in strawberry?' }],
    think: true,
    stream: false,
})
console.log('Thinking:\n', response.message.thinking)
console.log('Answer:\n', response.message.content)
```

## CLI Quick Reference

```bash
# Enable thinking for a single run
ollama run deepseek-r1 --think "Where should I visit in Lisbon?"

# Disable thinking
ollama run deepseek-r1 --think=false "Summarize this article"

# Hide trace while still using thinking model
ollama run deepseek-r1 --hidethinking "Is 9.9 bigger or 9.11?"

# Interactive session toggle
/set think
/set nothink

# GPT-OSS levels
ollama run gpt-oss --think=low "Draft a headline"
ollama run gpt-oss --think=medium "Analyze this code"
ollama run gpt-oss --think=high "Prove this theorem"
```

## mindX Integration

The existing `OllamaAPI.generate_text()` already supports `think` via kwargs:

```python
# Already works via api/ollama/ollama_url.py line:
# for key in ["format", "system", "template", "raw", "suffix", "images", "think"]:
#     if key in kwargs:
#         payload[key] = kwargs[key]

result = await ollama_api.generate_text(
    prompt="Analyze the autonomous improvement cycle for inefficiencies",
    model="deepseek-r1:1.5b",
    think=True  # Passes through to payload
)

# The response includes thinking trace in the response text
# For chat endpoint, thinking is in message.thinking field
```

### Thinking for Agent Tasks

Different agents benefit from different thinking levels:
- **mindXagent autonomous loop**: `think=True` — full reasoning for improvement decisions
- **BlueprintAgent**: `think="high"` (GPT-OSS cloud) — deep reasoning for evolution plans
- **Heartbeat/health checks**: `think=False` — speed over reasoning
- **Self-improvement evaluation**: `think=True` with `deepseek-r1:1.5b` — chain-of-thought
