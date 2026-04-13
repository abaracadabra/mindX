# Ollama JavaScript SDK

> Source: [github.com/ollama/ollama-js](https://github.com/ollama/ollama-js)
> `npm i ollama` — Official JavaScript/TypeScript library for Ollama

---

## Installation

```bash
npm i ollama    # npm
bun i ollama    # bun
yarn add ollama # yarn
```

## Import

```javascript
// Node.js (default)
import ollama from 'ollama'

// Browser (no Node dependencies)
import ollama from 'ollama/browser'

// Custom client (multiple instances, different hosts)
import { Ollama } from 'ollama'
```

## Client Configuration

```javascript
import { Ollama } from 'ollama'

// Local Ollama (default: http://127.0.0.1:11434)
const local = new Ollama({
    host: 'http://127.0.0.1:11434',
})

// mindX VPS Ollama
const vps = new Ollama({
    host: 'http://localhost:11434',
    headers: { 'User-Agent': 'mindX/1.0' },
})

// Ollama Cloud (direct API — requires API key from ollama.com/settings/keys)
const cloud = new Ollama({
    host: 'https://ollama.com',
    headers: { Authorization: 'Bearer ' + process.env.OLLAMA_API_KEY },
})
```

Default host is `http://127.0.0.1:11434`. Custom headers apply to all requests from that client instance.

---

## Complete API Reference

### chat(request)

Conversational interaction with message history.

```javascript
// Non-streaming
const response = await ollama.chat({
    model: 'qwen3:1.7b',
    messages: [
        { role: 'system', content: 'You are a mindX boardroom advisor.' },
        { role: 'user', content: 'Should we deploy to Algorand?' },
    ],
    stream: false,
})
console.log(response.message.content)

// Streaming (AsyncGenerator)
const stream = await ollama.chat({
    model: 'qwen3:1.7b',
    messages: [{ role: 'user', content: 'Explain BDI reasoning' }],
    stream: true,
})
for await (const chunk of stream) {
    process.stdout.write(chunk.message.content)
}
```

**Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | string | Model name (local or cloud) |
| `messages` | array | `{role, content, images?, tool_calls?}` |
| `stream` | boolean | Stream response chunks |
| `think` | boolean | Enable reasoning/thinking mode |
| `format` | string/object | `'json'` or JSON schema for structured output |
| `tools` | array | Function definitions for tool calling |
| `keep_alive` | string | How long model stays loaded (`'10m'`, `'1h'`, `'-1'` forever) |
| `options` | object | `{temperature, num_ctx, num_predict, top_p, seed, ...}` |

### generate(request)

Single-turn text generation with prompt template.

```javascript
const response = await ollama.generate({
    model: 'qwen3:1.7b',
    prompt: 'Why is the sky blue?',
    system: 'You are a scientist. Respond in JSON.',
    format: 'json',
    stream: false,
    think: true,
    keep_alive: '10m',
    options: { temperature: 0.3, num_predict: 500 },
})
console.log(response.response)
console.log(response.thinking) // if think: true
```

**Additional parameters:** `suffix` (fill-in-middle), `raw` (no template), `images` (base64 array for vision models).

### embed(request)

Generate vector embeddings for text.

```javascript
const result = await ollama.embed({
    model: 'mxbai-embed-large',
    input: ['First text', 'Second text', 'Third text'],
    truncate: true,
    keep_alive: '10m',
})
console.log(result.embeddings.length)      // 3
console.log(result.embeddings[0].length)   // 1024 dimensions for mxbai
```

### Model Management

```javascript
// List all local models
const models = await ollama.list()
models.models.forEach(m => console.log(m.name, m.size))

// Show model details (parameters, template, license)
const info = await ollama.show({ model: 'qwen3:1.7b' })

// Create custom model from base
await ollama.create({
    model: 'mindx-advisor',
    from: 'qwen3:1.7b',
    system: 'You are a mindX boardroom advisor. Vote approve, reject, or abstain.',
    parameters: { temperature: 0.3 },
})

// Copy model
await ollama.copy({ source: 'qwen3:1.7b', destination: 'qwen3-backup' })

// Delete model
await ollama.delete({ model: 'old-model' })

// Pull model from registry (with progress)
const pull = await ollama.pull({ model: 'qwen3:1.7b', stream: true })
for await (const progress of pull) {
    console.log(progress.status, progress.completed, '/', progress.total)
}

// Pull cloud model (metadata only — inference on cloud GPU)
await ollama.pull({ model: 'deepseek-v3.2-cloud' })

// Push model to registry
await ollama.push({ model: 'username/model' })

// List running models
const running = await ollama.ps()

// Get version
const v = await ollama.version()
```

### Web Search & Fetch

Requires Ollama account (API key or signin).

```javascript
// Web search
const results = await ollama.webSearch({
    query: 'mindX Darwin Godel machine',
    max_results: 5,
})

// Web fetch (retrieve + parse page content)
const page = await ollama.webFetch({
    url: 'https://mindx.pythai.net/thesis/evidence',
})
```

### abort()

Cancel all active streamed generations.

```javascript
// Start a long generation
const stream = ollama.chat({ model: 'qwen3:1.7b', messages: [...], stream: true })

// Cancel it
ollama.abort()  // throws AbortError to all listening streams
```

---

## Thinking Models

Models with reasoning capability (deepseek-r1, qwen3 with `think: true`):

```javascript
const response = await ollama.chat({
    model: 'deepseek-r1:1.5b',
    messages: [{ role: 'user', content: 'Analyze the risk of this trade' }],
    think: true,
})
console.log('Thinking:', response.message.thinking)
console.log('Response:', response.message.content)
```

Streaming thinking:
```javascript
const stream = await ollama.chat({
    model: 'deepseek-r1:1.5b',
    messages: [{ role: 'user', content: 'Should we buy Bitcoin?' }],
    think: true, stream: true,
})
for await (const chunk of stream) {
    if (chunk.message.thinking) process.stdout.write('[think] ' + chunk.message.thinking)
    if (chunk.message.content) process.stdout.write(chunk.message.content)
}
```

## Structured Outputs

Force models to return valid JSON matching a schema:

```javascript
const response = await ollama.chat({
    model: 'qwen3:1.7b',
    messages: [{ role: 'user', content: 'Vote on this directive: deploy to Algorand' }],
    format: {
        type: 'object',
        properties: {
            vote: { type: 'string', enum: ['approve', 'reject', 'abstain'] },
            reasoning: { type: 'string' },
            confidence: { type: 'number', minimum: 0, maximum: 1 },
        },
        required: ['vote', 'reasoning', 'confidence'],
    },
})
const vote = JSON.parse(response.message.content)
console.log(vote.vote, vote.confidence)
```

## Tool Calling

Define functions that models can invoke:

```javascript
const response = await ollama.chat({
    model: 'qwen3:1.7b',
    messages: [{ role: 'user', content: 'What is the weather in Tokyo?' }],
    tools: [{
        type: 'function',
        function: {
            name: 'get_weather',
            description: 'Get current weather for a location',
            parameters: {
                type: 'object',
                properties: {
                    location: { type: 'string', description: 'City name' },
                    unit: { type: 'string', enum: ['celsius', 'fahrenheit'] },
                },
                required: ['location'],
            },
        },
    }],
})

if (response.message.tool_calls) {
    for (const call of response.message.tool_calls) {
        console.log('Tool:', call.function.name, call.function.arguments)
    }
}
```

## Vision (Multimodal)

Send images to vision-capable models:

```javascript
import fs from 'fs'

const image = fs.readFileSync('screenshot.png')

const response = await ollama.chat({
    model: 'gemma4:31b',  // vision-capable
    messages: [{
        role: 'user',
        content: 'What do you see in this dashboard screenshot?',
        images: [image],  // Uint8Array or base64 string
    }],
})
```

## Cloud Models

Two methods to access Ollama Cloud GPU inference:

### Method 1: Local Proxy (Recommended — no API key needed)

```bash
# Sign in (one-time, stores key at ~/.ollama/id_ed25519)
ollama signin

# Pull cloud model (metadata only — inference runs on cloud GPU)
ollama pull deepseek-v3.2-cloud
ollama pull gpt-oss:120b-cloud
```

```javascript
// Use cloud model exactly like a local model — daemon proxies transparently
const response = await ollama.chat({
    model: 'gpt-oss:120b-cloud',  // -cloud suffix = cloud GPU inference
    messages: [{ role: 'user', content: 'Complex reasoning task...' }],
})
// 65+ tok/s on cloud GPU vs 8 tok/s local CPU
```

### Method 2: Direct Cloud API

```javascript
import { Ollama } from 'ollama'

const cloud = new Ollama({
    host: 'https://ollama.com',
    headers: { Authorization: 'Bearer ' + process.env.OLLAMA_API_KEY },
})

// Cloud models use base names (no -cloud suffix) when accessing directly
const response = await cloud.chat({
    model: 'gpt-oss:120b',
    messages: [{ role: 'user', content: 'Why is the sky blue?' }],
    stream: true,
})
for await (const part of response) {
    process.stdout.write(part.message.content)
}
```

**Free tier limits:** 50 requests/5-hour session, 500/week, 100K tokens/session.

### List Cloud Models

```javascript
// Public catalog — no auth needed
const cloud = new Ollama({ host: 'https://ollama.com' })
const catalog = await cloud.list()
catalog.models.forEach(m => console.log(m.name, m.size))
```

---

## mindX Integration Patterns

### Boardroom Deliberation

```javascript
import { Ollama } from 'ollama'

const ollama = new Ollama({ host: 'http://localhost:11434' })

async function querySoldier(soldierId, model, directive) {
    const response = await ollama.chat({
        model,
        messages: [{
            role: 'system',
            content: `You are ${soldierId}, a boardroom advisor. Evaluate directives and vote.`,
        }, {
            role: 'user',
            content: `Directive: ${directive}\nRespond in JSON: {"vote":"approve|reject|abstain","reasoning":"...","confidence":0.0-1.0}`,
        }],
        format: {
            type: 'object',
            properties: {
                vote: { type: 'string', enum: ['approve', 'reject', 'abstain'] },
                reasoning: { type: 'string' },
                confidence: { type: 'number' },
            },
            required: ['vote', 'reasoning', 'confidence'],
        },
    })
    return JSON.parse(response.message.content)
}
```

### Agent Heartbeat

```javascript
async function heartbeat(agentId) {
    const response = await ollama.generate({
        model: 'qwen3:0.6b',
        prompt: `Agent ${agentId} heartbeat check. Report status in one sentence.`,
        options: { num_predict: 50, temperature: 0.1 },
    })
    return { agent: agentId, status: response.response, model: 'qwen3:0.6b' }
}
```

### RAGE Semantic Search

```javascript
async function searchMemories(query, memories) {
    const queryEmbed = await ollama.embed({ model: 'mxbai-embed-large', input: [query] })
    const memEmbeds = await ollama.embed({ model: 'mxbai-embed-large', input: memories })

    // Cosine similarity ranking
    const scores = memEmbeds.embeddings.map((emb, i) => ({
        text: memories[i],
        score: cosineSim(queryEmbed.embeddings[0], emb),
    }))
    return scores.sort((a, b) => b.score - a.score).slice(0, 5)
}
```

---

**References:**
- [ollama/ollama-js](https://github.com/ollama/ollama-js) — Source code + TypeScript types
- [ollama/ollama](https://github.com/ollama/ollama) — Ollama server + REST API docs
- [ollama.com/library](https://ollama.com/library) — Model catalog
- [ollama.com/api/tags](https://ollama.com/api/tags) — Cloud model catalog (JSON)
- [Cloud models](cloud.md) — mindX local cloud reference
- [Python SDK](python.md) — Python equivalent
