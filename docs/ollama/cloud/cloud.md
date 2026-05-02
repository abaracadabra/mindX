# Ollama Cloud

> Run larger models without powerful hardware. Cloud models offload to Ollama's cloud service with the same local tool compatibility.

## Account Setup

```bash
# Create account and sign in
ollama signin

# Generate API key at: https://ollama.com/settings/keys
export OLLAMA_API_KEY=your_api_key
```

## Tiers ([ollama.com/pricing](https://ollama.com/pricing))

| Tier | Price | Cloud Usage | Concurrent Models |
|------|-------|-------------|-------------------|
| **Free** | $0 | Light (session + weekly limits) | **1** |
| **Pro** | $20/mo | 50x free | 3 |
| **Max** | $100/mo | 5x Pro | 10 |

Free tier limits reset: **session limits every 5 hours**, **weekly limits every 7 days**.

**Critical constraint — Free tier = 1 concurrent model.** This means:
- The boardroom MUST use a **single cloud model** for all soldiers (no model switching between queries)
- If soldier A uses `deepseek-v3.2-cloud` and soldier B requests `qwen3-coder-next-cloud`, the second request must wait for the first model to unload
- **Recommended**: Use one strong general model (e.g. `gpt-oss:120b-cloud` at 65 tok/s) for all boardroom cloud queries
- Local models are unlimited — mix freely on the VPS

## API Endpoints

| Endpoint | URL | Auth |
|----------|-----|------|
| Local (offloaded) | `http://localhost:11434/api/chat` | None (auto-offload) |
| Cloud direct | `https://ollama.com/api/chat` | Bearer token |
| OpenAI-compatible | `https://ollama.com/v1/chat/completions` | Bearer token |
| List cloud models | `https://ollama.com/api/tags` | None (public catalog) |

## Usage Methods

### Method 1: Local Ollama with Cloud Offload (Recommended)

Cloud models are pulled locally but inference runs in the cloud. Seamless — same API as local models.

**Critical**: Append `-cloud` to the model name when pulling. Without it, `ollama pull` downloads full weights (gigabytes) for local execution. With `-cloud`, only metadata is pulled and inference is proxied to `ollama.com` GPU servers.

```bash
# Pull cloud model (metadata only — inference proxied to cloud GPU)
ollama pull gpt-oss:120b-cloud
ollama pull deepseek-v3.2-cloud

# NOT this — downloads 3.3GB weights for local execution:
# ollama pull gemma3:4b

# Run (automatically offloads to cloud)
ollama run gpt-oss:120b-cloud
```

The [cloud catalog](https://ollama.com/api/tags) lists names without `-cloud`. Append it yourself:

```bash
# Catalog returns: gpt-oss:120b, deepseek-v3.2, qwen3-coder-next, etc.
# Pull as:         gpt-oss:120b-cloud, deepseek-v3.2-cloud, qwen3-coder-next-cloud
```

Requires `ollama signin` first (stores ed25519 key at `~/.ollama/id_ed25519`).

**Benchmark** ([test_cloud_all_models.py](../../scripts/test_cloud_all_models.py), 2026-04-11): `gpt-oss:120b-cloud` at **65.52 tok/s** vs local CPU `deepseek-r1:1.5b` at 8.00 tok/s — **8.2x speedup** on cloud GPU with a 120B model.

```python
from ollama import Client

client = Client()
for part in client.chat('gpt-oss:120b-cloud', messages=[
    {'role': 'user', 'content': 'Why is the sky blue?'}
], stream=True):
    print(part.message.content, end='', flush=True)
```

### Method 2: Direct Cloud API

Use `https://ollama.com` as a remote Ollama host:

```python
import os
from ollama import Client

client = Client(
    host='https://ollama.com',
    headers={'Authorization': 'Bearer ' + os.environ.get('OLLAMA_API_KEY')}
)

for part in client.chat('gpt-oss:120b', messages=[
    {'role': 'user', 'content': 'Why is the sky blue?'}
], stream=True):
    print(part.message.content, end='', flush=True)
```

```javascript
import { Ollama } from 'ollama'

const ollama = new Ollama({
    host: 'https://ollama.com',
    headers: { Authorization: 'Bearer ' + process.env.OLLAMA_API_KEY },
})

const response = await ollama.chat({
    model: 'gpt-oss:120b',
    messages: [{ role: 'user', content: 'Explain quantum computing' }],
    stream: true,
})
for await (const part of response) {
    process.stdout.write(part.message.content)
}
```

```bash
curl https://ollama.com/api/chat \
  -H "Authorization: Bearer $OLLAMA_API_KEY" \
  -d '{
    "model": "gpt-oss:120b",
    "messages": [{"role": "user", "content": "Why is the sky blue?"}],
    "stream": false
  }'
```

### List Available Cloud Models

```bash
curl https://ollama.com/api/tags \
  -H "Authorization: Bearer $OLLAMA_API_KEY"
```

## Cloud Models (as of 2026-04-11)

| Model | Params (Active) | Tags | Best For |
|-------|----------------|------|----------|
| glm-5.1 | — | tools, thinking | Agentic engineering, coding |
| gemma4 | 26b, 31b | vision, tools, thinking, audio | Frontier multimodal |
| minimax-m2.7 | — | tools, thinking | Coding, productivity |
| qwen3.5 | 0.8b-122b | vision, tools, thinking | General multimodal |
| qwen3-coder-next | — | tools | Agentic coding |
| ministral-3 | 3b, 8b, 14b | vision, tools | Edge deployment |
| devstral-small-2 | 24b | vision, tools | Code exploration |
| nemotron-3-super | 120b (12b active) | tools, thinking | Efficient MoE |
| qwen3-next | 80b | tools, thinking | Efficient reasoning |
| glm-5 | 744b (40b active) | tools, thinking | Complex engineering |
| kimi-k2.5 | — | vision, tools, thinking | Multimodal agentic |
| rnj-1 | 8b | tools | Code + STEM |
| nemotron-3-nano | 4b, 30b | tools, thinking | Efficient agentic |
| deepseek-v3.2 | — | tools, thinking | Efficient reasoning |
| cogito-2.1 | 671b | — | General (MIT) |
| gemini-3-flash-preview | — | vision, tools, thinking | Speed + intelligence |

Full list: [ollama.com/search?c=cloud](https://ollama.com/search?c=cloud)

## Local-Only Mode

Disable cloud features entirely:

```json
// ~/.ollama/server.json
{"disable_ollama_cloud": true}
```

Or: `OLLAMA_NO_CLOUD=1`

## mindX Cloud Strategy

See [cloud/rate_limiting.md](rate_limiting.md) for maximizing the free tier.

### Tier Assignment for mindX Agents

| Agent | Model Source | Why |
|-------|-------------|-----|
| mindXagent (autonomous) | Local `qwen3:1.7b` | Always available, no quota |
| BlueprintAgent | Cloud `qwen3-coder-next` | Coding focus, needs power |
| AuthorAgent | Cloud `qwen3.5:27b` | Prose quality |
| Heartbeat/health | Local `qwen3:0.6b` | Ultra-fast, no quota burn |
| Self-improvement eval | Local `deepseek-r1:1.5b` | Chain-of-thought local |
| Heavy reasoning | Cloud `deepseek-v3.2` | Best reasoning, cloud only |
