# Vision

> Vision models accept images alongside text for description, classification, and visual Q&A.

## Supported Models

- `gemma3` — Google's multimodal model
- `gemma4` — Latest with vision, tools, thinking, audio (cloud)
- `qwen3-vl` — Qwen vision-language model (cloud)
- `llava` — LLaVA series
- `kimi-k2.5` — Multimodal agentic (cloud)
- Browse: [vision models](https://ollama.com/search?c=vision)

## CLI Quick Start

```bash
ollama run gemma3 ./image.png "What's in this image?"
```

## REST API

Images must be **base64-encoded** in the REST API. SDKs accept file paths, URLs, or raw bytes.

### Chat Endpoint

```bash
# 1. Encode the image
IMG=$(base64 < photo.jpg | tr -d '\n')

# 2. Send to Ollama
curl http://localhost:11434/api/chat -d '{
  "model": "gemma3",
  "messages": [{
    "role": "user",
    "content": "What is in this image?",
    "images": ["'"$IMG"'"]
  }],
  "stream": false
}'
```

### Generate Endpoint

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "gemma3",
  "prompt": "Describe what you see",
  "images": ["iVBORw0KGgoAAAANSUhEUg...base64..."],
  "stream": false
}'
```

## Python SDK

```python
from ollama import chat

# File path (SDK handles encoding)
response = chat(
    model='gemma3',
    messages=[{
        'role': 'user',
        'content': 'What is in this image? Be concise.',
        'images': ['/path/to/image.jpg'],
    }],
)
print(response.message.content)

# Raw bytes
from pathlib import Path
img_bytes = Path('/path/to/image.jpg').read_bytes()
response = chat(
    model='gemma3',
    messages=[{
        'role': 'user',
        'content': 'Describe this image.',
        'images': [img_bytes],
    }],
)

# Base64 string
import base64
img_b64 = base64.b64encode(Path('/path/to/image.jpg').read_bytes()).decode()
response = chat(
    model='gemma3',
    messages=[{
        'role': 'user',
        'content': 'What do you see?',
        'images': [img_b64],
    }],
)
```

## JavaScript SDK

```javascript
import ollama from 'ollama'

const response = await ollama.chat({
    model: 'gemma3',
    messages: [{
        role: 'user',
        content: 'What is in this image?',
        images: ['/absolute/path/to/image.jpg']
    }],
    stream: false,
})
console.log(response.message.content)
```

## OpenAI-Compatible API

```python
from openai import OpenAI

client = OpenAI(base_url='http://localhost:11434/v1/', api_key='ollama')

response = client.chat.completions.create(
    model='gemma3',
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': "What's in this image?"},
            {'type': 'image_url', 'image_url': 'data:image/png;base64,iVBORw0KGgo...'},
        ],
    }],
    max_tokens=300,
)
print(response.choices[0].message.content)
```

## Vision + Structured Output

See [structured_outputs.md](structured_outputs.md) for combining vision with JSON schemas.

## mindX Integration

The existing `OllamaAPI` already supports `images` via kwargs:

```python
import base64
from pathlib import Path

# Encode image
img_b64 = base64.b64encode(Path("screenshot.png").read_bytes()).decode()

# Via OllamaAPI
result = await ollama_api.generate_text(
    prompt="Describe what you see in this dashboard screenshot",
    model="gemma3",  # Must be a vision model
    images=[img_b64]
)
```

### Avatar Analysis for AvatarAgent

```python
async def analyze_avatar(image_path: str) -> dict:
    """Use vision model to analyze generated avatar quality."""
    img_b64 = base64.b64encode(Path(image_path).read_bytes()).decode()
    
    from pydantic import BaseModel
    class AvatarAnalysis(BaseModel):
        style: str
        quality_score: float
        colors: list[str]
        description: str
    
    response = chat(
        model='gemma3',
        messages=[{
            'role': 'user',
            'content': 'Analyze this avatar image for quality and style.',
            'images': [img_b64],
        }],
        format=AvatarAnalysis.model_json_schema(),
        options={'temperature': 0}
    )
    return AvatarAnalysis.model_validate_json(response.message.content)
```
