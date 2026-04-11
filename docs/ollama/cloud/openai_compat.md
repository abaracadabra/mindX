# OpenAI API Compatibility

> Drop-in replacement for OpenAI SDK. Use existing OpenAI code with Ollama models.

## Setup

```
Base URL: http://localhost:11434/v1/
API Key:  "ollama"  (required by SDK but ignored by server)
```

Models must be pulled locally first: `ollama pull qwen3:1.7b`

## Supported Endpoints

| Endpoint | Features |
|----------|----------|
| `POST /v1/chat/completions` | Streaming, JSON mode, vision, tools, thinking |
| `POST /v1/completions` | Streaming, JSON mode |
| `POST /v1/embeddings` | String/array input, dimensions |
| `POST /v1/images/generations` | Experimental, b64_json only |
| `POST /v1/responses` | Tools, reasoning (non-stateful) |
| `GET /v1/models` | List available models |

### Not Supported

- `logprobs` in chat completions
- `tool_choice` (model decides)
- Stateful responses

## Python (OpenAI SDK)

```python
from openai import OpenAI

client = OpenAI(
    base_url='http://localhost:11434/v1/',
    api_key='ollama',
)

# Chat completion
response = client.chat.completions.create(
    model='qwen3:1.7b',
    messages=[{'role': 'user', 'content': 'Why is the sky blue?'}],
)
print(response.choices[0].message.content)

# Streaming
stream = client.chat.completions.create(
    model='qwen3:1.7b',
    messages=[{'role': 'user', 'content': 'Tell me a story'}],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end='')

# Vision
response = client.chat.completions.create(
    model='gemma3',
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': "What's in this image?"},
            {'type': 'image_url', 'image_url': 'data:image/png;base64,...'},
        ],
    }],
    max_tokens=300,
)

# Embeddings
response = client.embeddings.create(
    model='mxbai-embed-large',
    input=['Hello world', 'Goodbye world'],
)
print(len(response.data[0].embedding))

# Thinking (reasoning_effort)
response = client.chat.completions.create(
    model='deepseek-r1:1.5b',
    messages=[{'role': 'user', 'content': 'Solve: 17 * 23'}],
    reasoning_effort='high',  # "high", "medium", "low", "none"
)
```

## JavaScript (OpenAI SDK)

```javascript
import OpenAI from 'openai'

const client = new OpenAI({
    baseURL: 'http://localhost:11434/v1/',
    apiKey: 'ollama',
})

const response = await client.chat.completions.create({
    model: 'qwen3:1.7b',
    messages: [{ role: 'user', content: 'Why is the sky blue?' }],
})
console.log(response.choices[0].message.content)
```

## cURL

```bash
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3:1.7b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Cloud via OpenAI SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url='https://ollama.com/v1/',
    api_key=os.environ['OLLAMA_API_KEY'],
)

response = client.chat.completions.create(
    model='gpt-oss:120b',
    messages=[{'role': 'user', 'content': 'Explain quantum computing'}],
)
```

## Model Aliases for Compatibility

Some tools expect OpenAI model names. Create aliases:

```bash
ollama cp qwen3:1.7b gpt-3.5-turbo
ollama cp qwen3.5:27b gpt-4
```

## mindX Integration

mindX already uses multiple LLM providers via `llm_factory.py`. The OpenAI-compatible endpoint means any provider handler written for OpenAI works with Ollama:

```python
# In llm_factory.py, Ollama can serve as a drop-in for OpenAI
# by pointing base_url to localhost:11434/v1/
# This enables using the same OpenAI handler code for local inference
```
