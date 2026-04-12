# vLLM → Ollama Cloud Bridge

vLLM handler and Ollama cloud speak the same protocol: OpenAI-compatible `/v1/chat/completions` with Bearer token auth. When local vLLM is unreachable, the handler falls back to Ollama cloud automatically.

## How It Works

```
VLLMHandler.generate_text(prompt, model)
    ↓
1. Try local vLLM: /v1/chat/completions (primary — free, fast)
    ↓ connection error
2. Try local vLLM: /v1/completions (fallback endpoint)
    ↓ connection error
3. Try Ollama cloud: https://ollama.com/v1/chat/completions
   (same protocol, Bearer auth, cloud rate limiter)
    ↓ rate limited or no API key
4. Return None → BDI provider cascade continues
```

## Configuration

| Variable | Purpose | Default |
|----------|---------|---------|
| `VLLM_BASE_URL` | Local vLLM server | `http://localhost:8000` |
| `VLLM_API_KEY` | Local vLLM auth | `EMPTY` |
| `OLLAMA_API_KEY` | Cloud Bearer token | *(none — disables cloud fallback)* |
| `OLLAMA_CLOUD_URL` | Cloud base URL | `https://ollama.com` |

## Rate Limiting

| Endpoint | Profile | RPM | Notes |
|----------|---------|-----|-------|
| Local vLLM | `ollama_local` | 1000 | Effectively unlimited |
| Ollama Cloud (free) | `vllm_cloud` | 10 | 50 req/5h session, 500/week |
| Ollama Cloud (API key) | `vllm_cloud` | 10 | Adaptive pacing via CloudRateLimiter |

Cloud rate limiting uses `OllamaCloudTool.CloudRateLimiter` — session quotas, weekly caps, exponential backoff on 429, adaptive request intervals based on utilization.

## Available Cloud Models

Query via `VLLMHandler.list_cloud_models()` or see [cloud.md](ollama/cloud/cloud.md):
- `deepseek-v3.2` — efficient reasoning
- `qwen3.5:32b` — general purpose
- `gpt-oss:120b` — 120B, 65 tok/s (8x faster than local 1.5B)
- `qwen3-coder-next` — agentic coding
- `gemma4:31b` — vision capable
- 36+ more at `https://ollama.com/search?c=cloud`

## InferenceDiscovery Integration

When local vLLM is unreachable but `OLLAMA_API_KEY` is set, InferenceDiscovery marks the vLLM source as **DEGRADED** (not UNREACHABLE). This means:
- BDI provider cascade still considers vLLM as a fallback option
- The score drops (degraded reliability) but doesn't disappear
- When local vLLM comes back online, it's automatically preferred (higher score)

## Protocol Compatibility

Both endpoints accept identical payloads:

```json
POST /v1/chat/completions
Authorization: Bearer <token>
Content-Type: application/json

{
  "model": "deepseek-v3.2",
  "messages": [{"role": "user", "content": "..."}],
  "stream": false,
  "max_tokens": 2048,
  "temperature": 0.7
}
```

Response format (OpenAI-compatible):
```json
{
  "choices": [{
    "message": {"role": "assistant", "content": "..."}
  }],
  "usage": {"prompt_tokens": 18, "completion_tokens": 42, "total_tokens": 60}
}
```

No adapter code needed. Trust the math.
