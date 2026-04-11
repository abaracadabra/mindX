# API Reference: Embeddings — POST /api/embed

> Generate vector embeddings for RAGE/semantic search and pgvector storage.

## Endpoint

```
POST http://localhost:11434/api/embed
POST https://ollama.com/api/embed  # Cloud (requires OLLAMA_API_KEY)
```

## Request Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| `model` | string | — | **yes** | Embedding model (e.g., `mxbai-embed-large`, `nomic-embed-text`) |
| `input` | string\|string[] | — | **yes** | Text(s) to embed |
| `truncate` | boolean | `true` | no | Truncate inputs exceeding context. `false` = error on overflow |
| `dimensions` | integer | — | no | Desired embedding vector size |
| `keep_alive` | string | `"5m"` | no | Model memory duration |
| `options` | ModelOptions | — | no | Runtime options |

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `model` | string | Model that produced embeddings |
| `embeddings` | float[][] | Array of embedding vectors (L2-normalized / unit-length) |
| `total_duration` | integer | Total time (nanoseconds) |
| `load_duration` | integer | Model load time (ns) |
| `prompt_eval_count` | integer | Input tokens processed |

## Examples

### Single Text

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "mxbai-embed-large",
  "input": "The quick brown fox jumps over the lazy dog."
}'
```

Response:
```json
{
  "model": "mxbai-embed-large",
  "embeddings": [[0.010071, -0.001759, 0.050072, ...]],
  "total_duration": 14143917,
  "load_duration": 1019500,
  "prompt_eval_count": 8
}
```

### Batch Embedding (Multiple Texts)

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "mxbai-embed-large",
  "input": [
    "First document to embed",
    "Second document to embed",
    "Third document to embed"
  ]
}'
```

Returns `embeddings` array with one vector per input text.

### With Dimension Control

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "mxbai-embed-large",
  "input": "Generate embeddings for this text",
  "dimensions": 128
}'
```

### Disable Truncation (Error on Overflow)

```bash
curl http://localhost:11434/api/embed -d '{
  "model": "mxbai-embed-large",
  "input": "Very long text that might exceed context...",
  "truncate": false
}'
```

## Recommended Embedding Models

| Model | Dimensions | Speed | Best For |
|-------|-----------|-------|----------|
| `mxbai-embed-large` | 1024 | Medium | High-quality semantic search |
| `nomic-embed-text` | 768 | Fast | General embeddings, smaller footprint |
| `embeddinggemma` | 768 | Medium | Google's embedding model |
| `qwen3-embedding` | 1024 | Medium | Multilingual embeddings |
| `all-minilm` | 384 | Very fast | Lightweight, fast retrieval |

## Tips

- Use **cosine similarity** for most semantic search use cases
- Always use the **same model** for both indexing and querying
- Embeddings are **L2-normalized** (unit-length) — cosine similarity = dot product
- Batch embedding is more efficient than individual calls

## mindX Integration

mindX currently uses `mxbai-embed-large` and `nomic-embed-text` for RAGE (not RAG) semantic search with pgvector.

```python
# Direct embedding via aiohttp (extend OllamaAPI)
import aiohttp, json

async def embed_texts(texts: list[str], model: str = "mxbai-embed-large") -> list[list[float]]:
    """Generate embeddings via Ollama for pgvector storage."""
    async with aiohttp.ClientSession() as session:
        payload = {"model": model, "input": texts}
        async with session.post(
            "http://localhost:11434/api/embed",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=60)
        ) as resp:
            data = await resp.json()
            return data["embeddings"]

# Usage with pgvector
embeddings = await embed_texts(["mindX autonomous improvement", "BDI reasoning engine"])
# Store in pgvector: INSERT INTO memories (content, embedding) VALUES ($1, $2)
```
