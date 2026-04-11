# Streaming

> Render text as it is produced by the model. Enabled by default in REST API, disabled by default in SDKs.

## Key Concepts

1. **Chat streaming**: Each chunk includes partial `content` — render as it arrives
2. **Thinking streaming**: `thinking` field interleaves reasoning before `content` arrives
3. **Tool calling streaming**: Watch for streamed `tool_calls`, execute tools, append results

**Critical**: Accumulate partial fields (`thinking`, `content`, `tool_calls`) to maintain conversation history for the next request.

## Python SDK

```python
from ollama import chat

stream = chat(
    model='qwen3',
    messages=[{'role': 'user', 'content': 'What is 17 x 23?'}],
    stream=True,
)

in_thinking = False
content = ''
thinking = ''
for chunk in stream:
    if chunk.message.thinking:
        if not in_thinking:
            in_thinking = True
            print('Thinking:\n', end='', flush=True)
        print(chunk.message.thinking, end='', flush=True)
        thinking += chunk.message.thinking
    elif chunk.message.content:
        if in_thinking:
            in_thinking = False
            print('\n\nAnswer:\n', end='', flush=True)
        print(chunk.message.content, end='', flush=True)
        content += chunk.message.content

# Append accumulated fields to messages for next request
new_messages = [{'role': 'assistant', 'thinking': thinking, 'content': content}]
```

## JavaScript SDK

```javascript
import ollama from 'ollama'

const stream = await ollama.chat({
    model: 'qwen3',
    messages: [{ role: 'user', content: 'What is 17 x 23?' }],
    stream: true,
})

let inThinking = false
let content = ''
let thinking = ''

for await (const chunk of stream) {
    if (chunk.message.thinking) {
        if (!inThinking) {
            inThinking = true
            process.stdout.write('Thinking:\n')
        }
        process.stdout.write(chunk.message.thinking)
        thinking += chunk.message.thinking
    } else if (chunk.message.content) {
        if (inThinking) {
            inThinking = false
            process.stdout.write('\n\nAnswer:\n')
        }
        process.stdout.write(chunk.message.content)
        content += chunk.message.content
    }
}

const newMessages = [{ role: 'assistant', thinking, content }]
```

## REST API (cURL)

```bash
# Streaming is default (stream: true)
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [{"role": "user", "content": "Why is the sky blue?"}]
}'

# Each line is a JSON object:
# {"model":"qwen3:1.7b","message":{"role":"assistant","content":"The"},"done":false}
# {"model":"qwen3:1.7b","message":{"role":"assistant","content":" sky"},"done":false}
# ...final chunk has done:true + metrics
```

## mindX Integration — Streaming with aiohttp

The existing `OllamaAPI.generate_text()` uses `stream=False`. Here's how to add streaming:

```python
import aiohttp
import json
from typing import AsyncGenerator

async def stream_chat(
    base_url: str,
    model: str,
    messages: list[dict],
    think: bool = False,
    options: dict | None = None
) -> AsyncGenerator[dict, None]:
    """Stream chat responses from Ollama, yielding each chunk."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if think:
        payload["think"] = True
    if options:
        payload["options"] = options

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"{base_url}/api/chat",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=120, sock_read=60)
        ) as resp:
            async for line in resp.content:
                line = line.strip()
                if line:
                    chunk = json.loads(line)
                    yield chunk
                    if chunk.get("done"):
                        break

# Usage in mindX
async def demo_streaming():
    thinking = ""
    content = ""
    async for chunk in stream_chat(
        "http://localhost:11434",
        "qwen3:1.7b",
        [{"role": "user", "content": "Explain BDI architecture"}],
        think=True
    ):
        msg = chunk.get("message", {})
        if msg.get("thinking"):
            thinking += msg["thinking"]
        if msg.get("content"):
            content += msg["content"]
    
    return {"thinking": thinking, "content": content}
```
