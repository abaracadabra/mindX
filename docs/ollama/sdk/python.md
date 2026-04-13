# Ollama Python SDK

> Source: [github.com/ollama/ollama-python](https://github.com/ollama/ollama-python)
> `pip install ollama` — Official Python library for Ollama (Python 3.8+)

---

## Installation

```bash
pip install ollama
```

Requires Ollama running locally (`ollama serve`) and a model pulled (`ollama pull qwen3:1.7b`).

## Quick Start

```python
from ollama import chat

response = chat(model='qwen3:1.7b', messages=[
    {'role': 'user', 'content': 'Why is the sky blue?'},
])
print(response.message.content)
```

Response objects support both dict-style and attribute access:
```python
print(response['message']['content'])  # dict style
print(response.message.content)        # attribute style
```

## Streaming

```python
from ollama import chat

stream = chat(
    model='qwen3:1.7b',
    messages=[{'role': 'user', 'content': 'Explain BDI reasoning'}],
    stream=True,
)
for chunk in stream:
    print(chunk.message.content, end='', flush=True)
```

---

## Client Types

### Functional API

```python
from ollama import chat, generate, embed, list, show, pull, ps
response = chat(model='qwen3:1.7b', messages=[...])
```

### Client Class

```python
from ollama import Client
client = Client(host='http://localhost:11434', headers={'User-Agent': 'mindX/1.0'})
response = client.chat(model='qwen3:1.7b', messages=[...])
```

### AsyncClient

```python
from ollama import AsyncClient
import asyncio

async def main():
    client = AsyncClient(host='http://localhost:11434')
    response = await client.chat(model='qwen3:1.7b', messages=[
        {'role': 'user', 'content': 'Hello'},
    ])
    print(response.message.content)

asyncio.run(main())
```

### Async Streaming

```python
async def stream_chat():
    client = AsyncClient()
    stream = await client.chat(
        model='qwen3:1.7b',
        messages=[{'role': 'user', 'content': 'Tell me about mindX'}],
        stream=True,
    )
    async for chunk in stream:
        print(chunk.message.content, end='', flush=True)
```

---

## Complete API

### chat()

```python
response = chat(
    model='qwen3:1.7b',
    messages=[
        {'role': 'system', 'content': 'You are a mindX boardroom advisor.'},
        {'role': 'user', 'content': 'Should we deploy to Algorand?'},
    ],
    stream=False,
    format='json',
    tools=[...],
    think=True,
    keep_alive='10m',
    options={'temperature': 0.3, 'num_ctx': 4096, 'num_predict': 500},
)
```

### generate()

```python
response = generate(
    model='qwen3:1.7b',
    prompt='Analyze this codebase',
    system='You are a code reviewer.',
    format='json',
    think=True,
    options={'temperature': 0.3},
)
print(response.response)
print(response.thinking)
```

### embed()

```python
result = embed(model='mxbai-embed-large', input=['text1', 'text2'], truncate=True)
print(len(result.embeddings))       # 2
print(len(result.embeddings[0]))    # 1024
```

### Model Management

```python
from ollama import list, show, create, copy, delete, pull, push, ps

models = list()
info = show('qwen3:1.7b')
create(model='custom', from_='qwen3:1.7b', system='...')
copy('qwen3:1.7b', 'backup')
delete('old-model')
for p in pull('qwen3:1.7b', stream=True):
    print(p.status, p.completed, '/', p.total)
pull('deepseek-v3.2-cloud')  # cloud model metadata
push('username/model')
running = ps()
```

### Error Handling

```python
import ollama
try:
    response = ollama.chat(model='nonexistent', messages=[...])
except ollama.ResponseError as e:
    print(f'Error {e.status_code}: {e.error}')
```

---

## Thinking Models

```python
response = chat(model='deepseek-r1:1.5b', messages=[...], think=True)
print('Thinking:', response.message.thinking)
print('Response:', response.message.content)
```

## Structured Outputs

```python
from pydantic import BaseModel

class Vote(BaseModel):
    vote: str
    reasoning: str
    confidence: float

response = chat(model='qwen3:1.7b', messages=[...], format=Vote.model_json_schema())
vote = Vote.model_validate_json(response.message.content)
```

## Tool Calling

```python
response = chat(model='qwen3:1.7b', messages=[...], tools=[{
    'type': 'function',
    'function': {
        'name': 'get_weather',
        'description': 'Get weather',
        'parameters': {'type': 'object', 'properties': {
            'location': {'type': 'string'},
        }, 'required': ['location']},
    },
}])
if response.message.tool_calls:
    for call in response.message.tool_calls:
        print(call.function.name, call.function.arguments)
```

## Vision

```python
response = chat(model='gemma4:31b', messages=[{
    'role': 'user',
    'content': 'Describe this screenshot',
    'images': ['./screenshot.png'],
}])
```

## Cloud Models

### Local Proxy (after `ollama signin`)
```python
response = chat(model='gpt-oss:120b-cloud', messages=[...])
```

### Direct API
```python
cloud = Client(host='https://ollama.com', headers={'Authorization': f'Bearer {os.environ["OLLAMA_API_KEY"]}'})
response = cloud.chat(model='gpt-oss:120b', messages=[...])
```

---

**References:**
- [ollama/ollama-python](https://github.com/ollama/ollama-python)
- [ollama/ollama](https://github.com/ollama/ollama) — Server + REST API
- [ollama.com/library](https://ollama.com/library) — Model catalog
- [Cloud docs](../cloud/cloud.md) | [JavaScript SDK](javascript.md)
