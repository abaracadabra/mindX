# Web Search

> Augment models with live web data to reduce hallucinations. Requires Ollama account + API key.

## Authentication

1. Create account at [ollama.com](https://ollama.com)
2. Generate API key at [ollama.com/settings/keys](https://ollama.com/settings/keys)
3. Set environment variable: `export OLLAMA_API_KEY=your_api_key`

## Web Search API — POST https://ollama.com/api/web_search

### Request

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `query` | string | — | **yes** | Search query |
| `max_results` | integer | 5 | no | Max results (1-10) |

### Response

```json
{
  "results": [
    {
      "title": "Page Title",
      "url": "https://example.com",
      "content": "Relevant content snippet..."
    }
  ]
}
```

### cURL

```bash
curl https://ollama.com/api/web_search \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -d '{"query": "what is ollama?"}'
```

### Python SDK

```python
import ollama

response = ollama.web_search("What is Ollama?")
for result in response.results:
    print(f"{result.title}: {result.url}")
    print(f"  {result.content[:200]}")
```

### JavaScript SDK

```javascript
import { Ollama } from 'ollama'

const client = new Ollama()
const results = await client.webSearch("what is ollama?")
console.log(JSON.stringify(results, null, 2))
```

## Web Fetch API — POST https://ollama.com/api/web_fetch

Fetch a single web page and extract content.

### Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `url` | string | **yes** | URL to fetch |

### Response

```json
{
  "title": "Page Title",
  "content": "Extracted page content...",
  "links": ["https://example.com/page1", "https://example.com/page2"]
}
```

### Python SDK

```python
from ollama import web_fetch

result = web_fetch('https://ollama.com')
print(result.title)     # "Ollama"
print(result.content)   # Page content as markdown
print(result.links)     # Links found on page
```

### JavaScript SDK

```javascript
import { Ollama } from 'ollama'

const client = new Ollama()
const result = await client.webFetch("https://ollama.com")
console.log(result.title, result.content)
```

## Building a Search Agent

Use `web_search` and `web_fetch` as tools in an agent loop:

```python
from ollama import chat, web_fetch, web_search

available_tools = {'web_search': web_search, 'web_fetch': web_fetch}

messages = [{'role': 'user', 'content': "What is ollama's new engine?"}]

while True:
    response = chat(
        model='qwen3:4b',
        messages=messages,
        tools=[web_search, web_fetch],
        think=True
    )
    
    if response.message.thinking:
        print('Thinking:', response.message.thinking)
    if response.message.content:
        print('Answer:', response.message.content)
    
    messages.append(response.message)
    
    if response.message.tool_calls:
        for tool_call in response.message.tool_calls:
            fn = available_tools.get(tool_call.function.name)
            if fn:
                result = fn(**tool_call.function.arguments)
                # Truncate for limited context
                messages.append({
                    'role': 'tool',
                    'content': str(result)[:8000],
                    'tool_name': tool_call.function.name
                })
    else:
        break
```

### Context Length Note

Web search results can return thousands of tokens. **Increase context to 32K+ tokens** for search agents. Cloud models run at full context length automatically.

```python
response = chat(
    model='qwen3:4b',
    messages=messages,
    tools=[web_search, web_fetch],
    options={'num_ctx': 32768},  # 32K context
)
```

## mindX Integration

### Web Search Tool for RAGE Enhancement

```python
import os
import aiohttp

async def ollama_web_search(query: str, max_results: int = 5) -> list[dict]:
    """Search the web via Ollama API for RAGE augmentation."""
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        return []
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://ollama.com/api/web_search",
            json={"query": query, "max_results": max_results},
            headers={"Authorization": f"Bearer {api_key}"}
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("results", [])
            return []

async def ollama_web_fetch(url: str) -> dict:
    """Fetch and extract content from a URL via Ollama API."""
    api_key = os.environ.get("OLLAMA_API_KEY")
    if not api_key:
        return {}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://ollama.com/api/web_fetch",
            json={"url": url},
            headers={"Authorization": f"Bearer {api_key}"}
        ) as resp:
            if resp.status == 200:
                return await resp.json()
            return {}
```

### Staying Current with Model Releases

```python
async def search_latest_models(query: str = "latest") -> list[dict]:
    """Search Ollama model library for new releases."""
    results = await ollama_web_search(f"ollama {query} model", max_results=5)
    return results
```
