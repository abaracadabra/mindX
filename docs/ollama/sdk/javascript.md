# JavaScript SDK Reference

> `npm i ollama` — Official JavaScript/TypeScript library

## Installation

```bash
npm i ollama    # npm
bun i ollama    # bun
```

## Import

```javascript
// Node.js
import ollama from 'ollama'

// Browser
import ollama from 'ollama/browser'

// Custom client
import { Ollama } from 'ollama'
```

## Custom Client

```javascript
import { Ollama } from 'ollama'

const ollama = new Ollama({
    host: 'http://127.0.0.1:11434',
    headers: {
        Authorization: 'Bearer <api key>',
        'User-Agent': 'mindX/1.0',
    },
})
```

## Complete API

### chat()

```javascript
// Non-streaming
const response = await ollama.chat({
    model: 'qwen3:1.7b',
    messages: [{ role: 'user', content: 'Why is the sky blue?' }],
    stream: false,
    think: true,
    format: 'json',  // or JSON schema object
    tools: [...],
    keep_alive: '10m',
    options: { temperature: 0.7, num_ctx: 4096 },
})
console.log(response.message.content)

// Streaming
const stream = await ollama.chat({ ...opts, stream: true })
for await (const chunk of stream) {
    process.stdout.write(chunk.message.content)
}
```

### generate()

```javascript
const response = await ollama.generate({
    model: 'qwen3:1.7b',
    prompt: 'Why is the sky blue?',
    system: 'You are a scientist.',
    suffix: '',
    format: 'json',
    stream: false,
    think: true,
    raw: false,
    keep_alive: '10m',
})
```

### embed()

```javascript
const result = await ollama.embed({
    model: 'mxbai-embed-large',
    input: ['First text', 'Second text'],
    truncate: true,
    keep_alive: '10m',
})
console.log(result.embeddings.length)
```

### Model Management

```javascript
await ollama.list()
await ollama.show({ model: 'qwen3:1.7b' })
await ollama.create({ model: 'custom', from: 'qwen3:1.7b', system: '...' })
await ollama.copy({ source: 'qwen3:1.7b', destination: 'backup' })
await ollama.delete({ model: 'old-model' })
await ollama.pull({ model: 'qwen3:1.7b' })
await ollama.push({ model: 'user/model' })
await ollama.ps()
await ollama.version()
```

### Web Search & Fetch

```javascript
const results = await ollama.webSearch({ query: 'what is ollama?', max_results: 5 })
const page = await ollama.webFetch({ url: 'https://ollama.com' })
```

### abort()

```javascript
ollama.abort()  // Cancels all active streams
```

## Cloud API

```javascript
import { Ollama } from 'ollama'

const cloud = new Ollama({
    host: 'https://ollama.com',
    headers: { Authorization: 'Bearer ' + process.env.OLLAMA_API_KEY },
})

const response = await cloud.chat({
    model: 'gpt-oss:120b',
    messages: [{ role: 'user', content: 'Explain quantum computing' }],
})
```
