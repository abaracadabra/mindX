# API Reference: Generate — POST /api/generate

> Generate text completions. For conversations, prefer `/api/chat`.

## Endpoint

```
POST http://localhost:11434/api/generate
POST https://ollama.com/api/generate  # Cloud (requires OLLAMA_API_KEY)
```

## Request Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `model` | string | — | **yes** | Model name (e.g., `qwen3:1.7b`) |
| `prompt` | string | — | no | Text prompt for generation |
| `suffix` | string | — | no | Fill-in-the-middle: text after the model response |
| `images` | string[] | — | no | Base64-encoded images for vision models |
| `format` | string\|object | — | no | `"json"` or a JSON schema object |
| `system` | string | — | no | System prompt override |
| `stream` | boolean | `true` | no | Stream partial responses |
| `think` | boolean\|string | — | no | Enable thinking trace. `true`/`false` or `"high"`/`"medium"`/`"low"` (GPT-OSS) |
| `raw` | boolean | — | no | Skip prompt templating |
| `keep_alive` | string\|number | `"5m"` | no | How long to keep model loaded. `"10m"`, `3600`, `0` (unload), `-1` (forever) |
| `options` | ModelOptions | — | no | Runtime generation controls |
| `logprobs` | boolean | — | no | Return token log probabilities |
| `top_logprobs` | integer | — | no | Number of likely tokens per position |

### ModelOptions

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `seed` | integer | 0 | Random seed for reproducibility |
| `temperature` | float | 0.8 | Randomness (0.0 = deterministic, 2.0 = very random) |
| `top_k` | integer | 40 | Limit next token to K most likely |
| `top_p` | float | 0.9 | Nucleus sampling threshold |
| `min_p` | float | 0.0 | Minimum probability threshold |
| `stop` | string\|string[] | — | Stop sequences |
| `num_ctx` | integer | 2048 | Context window size in tokens |
| `num_predict` | integer | -1 | Max tokens to generate (-1 = unlimited) |

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `model` | string | Model name |
| `created_at` | string | ISO 8601 timestamp |
| `response` | string | Generated text |
| `thinking` | string | Reasoning trace (when `think` enabled) |
| `done` | boolean | Generation complete |
| `done_reason` | string | Why generation stopped (`"stop"`, `"length"`) |
| `total_duration` | integer | Total time in **nanoseconds** |
| `load_duration` | integer | Model loading time (ns) |
| `prompt_eval_count` | integer | Input token count |
| `prompt_eval_duration` | integer | Prompt evaluation time (ns) |
| `eval_count` | integer | Output token count |
| `eval_duration` | integer | Token generation time (ns) |
| `logprobs` | Logprob[] | Token probability data (when enabled) |

### Performance Calculation

```
tokens_per_second = eval_count / eval_duration * 1e9
```

## Examples

### Basic Generation

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

### Streaming (default)

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Why is the sky blue?"
}'
# Returns newline-delimited JSON chunks
```

### With Options

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "Write a haiku about AI",
  "stream": false,
  "options": {
    "temperature": 0.3,
    "top_p": 0.9,
    "seed": 42,
    "num_ctx": 4096
  }
}'
```

### Structured Output (JSON Schema)

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen3:1.7b",
  "prompt": "What are the populations of the US and Canada?",
  "stream": false,
  "format": {
    "type": "object",
    "properties": {
      "countries": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "country": {"type": "string"},
            "population": {"type": "integer"}
          },
          "required": ["country", "population"]
        }
      }
    },
    "required": ["countries"]
  }
}'
```

### With Thinking

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "deepseek-r1:1.5b",
  "prompt": "How many r letters in strawberry?",
  "think": true,
  "stream": false
}'
```

### With Images (Vision)

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "gemma3",
  "prompt": "What is in this picture?",
  "images": ["iVBORw0KGgoAAAANSUhEUg..."],
  "stream": false
}'
```

### Fill-in-the-Middle (Code Completion)

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder:1.5b",
  "prompt": "def compute_gcd(a, b):",
  "suffix": "    return result",
  "stream": false
}'
```

### Preload Model (Empty Request)

```bash
curl http://localhost:11434/api/generate -d '{"model": "qwen3:1.7b"}'
```

### Unload Model

```bash
curl http://localhost:11434/api/generate -d '{"model": "qwen3:1.7b", "keep_alive": 0}'
```

### Keep Model Loaded Indefinitely

```bash
curl http://localhost:11434/api/generate -d '{"model": "qwen3:1.7b", "keep_alive": -1}'
```

## mindX Integration

```python
# Via OllamaAPI (api/ollama/ollama_url.py)
result = await ollama_api.generate_text(
    prompt="Why is the sky blue?",
    model="qwen3:1.7b",
    max_tokens=200,
    temperature=0.7,
    keep_alive="10m"
)

# With structured output
result = await ollama_api.generate_text(
    prompt="Describe the weather",
    model="qwen3:1.7b",
    format={"type": "object", "properties": {"temp": {"type": "integer"}}},
)

# With thinking
result = await ollama_api.generate_text(
    prompt="Solve this step by step: 17 * 23",
    model="deepseek-r1:1.5b",
    think=True
)
```
