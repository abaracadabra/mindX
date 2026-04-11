# Embeddings Feature Guide

> Turn text into numeric vectors for semantic search, RAGE, and pgvector storage.

For API reference, see [api/embeddings.md](../api/embeddings.md). This page covers practical usage patterns.

## Recommended Models

| Model | Dimensions | Use Case |
|-------|-----------|----------|
| [embeddinggemma](https://ollama.com/library/embeddinggemma) | 768 | Google's embedding model |
| [qwen3-embedding](https://ollama.com/library/qwen3-embedding) | 1024 | Multilingual |
| [all-minilm](https://ollama.com/library/all-minilm) | 384 | Lightweight, fast |
| [mxbai-embed-large](https://ollama.com/library/mxbai-embed-large) | 1024 | High quality |
| [nomic-embed-text](https://ollama.com/library/nomic-embed-text) | 768 | General purpose |

## CLI

```bash
ollama run embeddinggemma "Hello world"
# Output: JSON array of floats

echo "Hello world" | ollama run embeddinggemma
```

## Python

```python
import ollama

# Single embedding
single = ollama.embed(model='mxbai-embed-large', input='Hello world')
print(len(single['embeddings'][0]))  # 1024

# Batch embedding
batch = ollama.embed(
    model='mxbai-embed-large',
    input=[
        'The quick brown fox jumps over the lazy dog.',
        'The five boxing wizards jump quickly.',
        'Jackdaws love my big sphinx of quartz.',
    ]
)
print(len(batch['embeddings']))  # 3
```

## JavaScript

```javascript
import ollama from 'ollama'

const single = await ollama.embed({
    model: 'mxbai-embed-large',
    input: 'Hello world',
})
console.log(single.embeddings[0].length)  // 1024

const batch = await ollama.embed({
    model: 'mxbai-embed-large',
    input: ['First', 'Second', 'Third'],
})
console.log(batch.embeddings.length)  // 3
```

## Key Facts

- Embeddings are **L2-normalized** (unit-length) — cosine similarity = dot product
- Always use the **same model** for indexing and querying
- Batch embedding is more efficient than individual calls
- Use `truncate: false` to get errors instead of silent truncation

## mindX RAGE Integration

mindX uses `mxbai-embed-large` and `nomic-embed-text` (already installed) for RAGE semantic retrieval:

```python
# Embed agent memory for pgvector storage
memories = ["BDI cycle completed successfully", "Rate limiter triggered on Gemini"]
batch = ollama.embed(model='mxbai-embed-large', input=memories)

# Each embedding is a 1024-dim vector ready for pgvector
for i, embedding in enumerate(batch['embeddings']):
    # INSERT INTO memories (content, embedding) VALUES ($1, $2::vector)
    pass
```
