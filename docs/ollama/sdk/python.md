# Python SDK Reference

> `pip install ollama` — Official Python library for Ollama (Python 3.8+)

## Installation

```bash
pip install ollama    # pip
uv add ollama         # uv
```

## Client Types

### Module-Level Functions (Simple)

```python
from ollama import chat, generate, embed, list, show, create, copy, delete, pull, push, ps
from ollama import web_search, web_fetch
```

### Client (Custom Configuration)

```python
from ollama import Client

client = Client(
    host='http://localhost:11434',
    headers={'x-custom-header': 'value'}
)
response = client.chat(model='qwen3:1.7b', messages=[...])
```

### AsyncClient (For async/await)

```python
from ollama import AsyncClient

async def main():
    client = AsyncClient()
    response = await client.chat(model='qwen3:1.7b', messages=[...])

# Streaming async
async def stream():
    async for part in await AsyncClient().chat(
        model='qwen3:1.7b', messages=[...], stream=True
    ):
        print(part['message']['content'], end='')
```

### Cloud Client

```python
import os
from ollama import Client

# Direct cloud API access
client = Client(
    host='https://ollama.com',
    headers={'Authorization': 'Bearer ' + os.environ.get('OLLAMA_API_KEY')}
)
```

## Complete API

### chat()

```python
from ollama import chat

response = chat(
    model='qwen3:1.7b',
    messages=[
        {'role': 'system', 'content': 'You are a helpful assistant.'},
        {'role': 'user', 'content': 'Why is the sky blue?'}
    ],
    stream=False,        # True for streaming
    think=True,          # Enable thinking trace
    format='json',       # Or JSON schema dict
    tools=[fn1, fn2],    # Python functions auto-parsed to schemas
    options={'temperature': 0.7, 'num_ctx': 4096},
    keep_alive='10m',
)

print(response.message.content)
print(response.message.thinking)  # If think=True
```

### generate()

```python
from ollama import generate

response = generate(
    model='qwen3:1.7b',
    prompt='Why is the sky blue?',
    system='You are a scientist.',
    suffix='',           # For fill-in-middle
    format='json',
    stream=False,
    think=True,
    raw=False,
    keep_alive='10m',
    options={'temperature': 0.7},
)
print(response.response)
```

### embed()

```python
import ollama

# Single
result = ollama.embed(model='mxbai-embed-large', input='Hello world')
vector = result['embeddings'][0]  # list[float]

# Batch
result = ollama.embed(model='mxbai-embed-large', input=['First', 'Second', 'Third'])
vectors = result['embeddings']  # list[list[float]]
```

### list()

```python
import ollama
models = ollama.list()
for model in models['models']:
    print(f"{model['name']} - {model['details']['parameter_size']}")
```

### show()

```python
import ollama
info = ollama.show('qwen3:1.7b')
print(info['details'])       # format, family, parameter_size
print(info['capabilities'])  # ["completion", "tools", "thinking"]
print(info['parameters'])    # Parameter text
```

### create()

```python
import ollama
ollama.create(
    model='mindx-agent',
    from_='qwen3:1.7b',
    system='You are mindX, an autonomous AI system.'
)
```

### copy() / delete()

```python
import ollama
ollama.copy('qwen3:1.7b', 'qwen3-backup')
ollama.delete('old-model')
```

### pull() / push()

```python
import ollama

# Pull with progress
for status in ollama.pull('qwen3:1.7b', stream=True):
    print(status)

# Push (requires auth)
ollama.push('username/my-model')
```

### ps()

```python
import ollama
running = ollama.ps()
for model in running['models']:
    print(f"{model['name']} - VRAM: {model['size_vram']} bytes")
```

### web_search() / web_fetch()

```python
import ollama

# Requires OLLAMA_API_KEY
results = ollama.web_search("What is Ollama?")
for r in results.results:
    print(f"{r.title}: {r.url}")

page = ollama.web_fetch('https://ollama.com')
print(page.title, page.content[:200])
```

## Error Handling

```python
import ollama

try:
    ollama.chat('nonexistent-model')
except ollama.ResponseError as e:
    print(f'Error: {e.error}')
    if e.status_code == 404:
        ollama.pull('nonexistent-model')
```

## Tool Calling (Functions as Tools)

The Python SDK **auto-parses function docstrings** into tool schemas:

```python
from ollama import chat

def get_weather(city: str) -> str:
    """Get the current weather for a city.
    
    Args:
        city: The name of the city
    Returns:
        Weather description
    """
    return "Sunny, 22C"

# Just pass the function — SDK extracts the schema
response = chat(model='qwen3', messages=[...], tools=[get_weather])
```

## mindX Usage

mindX uses `aiohttp` directly rather than the `ollama` SDK for maximum control. But the SDK is useful for:
- Quick scripting and testing
- Model management (pull, create, list)
- Web search integration
- The auto-parsed tool schema feature
