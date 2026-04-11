# Structured Outputs

> Enforce a JSON schema on model responses for reliable data extraction.

## Two Modes

1. **Simple JSON mode**: `format: "json"` — model returns valid JSON (schema not enforced)
2. **Schema-constrained**: `format: {JSON schema}` — model output conforms to exact schema

## REST API

### Simple JSON Mode

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [{"role": "user", "content": "Tell me about Canada in one line"}],
  "stream": false,
  "format": "json"
}'
```

### With JSON Schema

```bash
curl http://localhost:11434/api/chat -d '{
  "model": "qwen3:1.7b",
  "messages": [{"role": "user", "content": "Tell me about Canada."}],
  "stream": false,
  "format": {
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "capital": {"type": "string"},
      "languages": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["name", "capital", "languages"]
  }
}'
```

**Tip**: Also pass the JSON schema as text in the prompt to ground the model's response.

## Python SDK with Pydantic

```python
from ollama import chat
from pydantic import BaseModel

class Country(BaseModel):
    name: str
    capital: str
    languages: list[str]

response = chat(
    model='qwen3:1.7b',
    messages=[{'role': 'user', 'content': 'Tell me about Canada.'}],
    format=Country.model_json_schema(),
)

country = Country.model_validate_json(response.message.content)
print(country)
# name='Canada' capital='Ottawa' languages=['English', 'French']
```

### Extract Structured Data

```python
from ollama import chat
from pydantic import BaseModel
from typing import Optional

class Pet(BaseModel):
    name: str
    animal: str
    age: int
    color: Optional[str] = None
    favorite_toy: Optional[str] = None

class PetList(BaseModel):
    pets: list[Pet]

response = chat(
    model='qwen3:1.7b',
    messages=[{
        'role': 'user',
        'content': '''I have two cats. Luna is a 5 year old black cat who loves feather toys.
                      Loki is a 3 year old orange tabby who likes crinkle balls.'''
    }],
    format=PetList.model_json_schema(),
)

pets = PetList.model_validate_json(response.message.content)
print(pets)
```

### Vision + Structured Output

```python
from ollama import chat
from pydantic import BaseModel
from typing import Literal, Optional

class Object(BaseModel):
    name: str
    confidence: float
    attributes: str

class ImageDescription(BaseModel):
    summary: str
    objects: list[Object]
    scene: str
    colors: list[str]
    time_of_day: Literal['Morning', 'Afternoon', 'Evening', 'Night']
    setting: Literal['Indoor', 'Outdoor', 'Unknown']
    text_content: Optional[str] = None

response = chat(
    model='gemma3',
    messages=[{
        'role': 'user',
        'content': 'Describe this photo and list detected objects.',
        'images': ['path/to/image.jpg'],
    }],
    format=ImageDescription.model_json_schema(),
    options={'temperature': 0},
)

desc = ImageDescription.model_validate_json(response.message.content)
```

## JavaScript SDK with Zod

```javascript
import ollama from 'ollama'
import { z } from 'zod'
import { zodToJsonSchema } from 'zod-to-json-schema'

const Country = z.object({
    name: z.string(),
    capital: z.string(),
    languages: z.array(z.string()),
})

const response = await ollama.chat({
    model: 'qwen3:1.7b',
    messages: [{ role: 'user', content: 'Tell me about Canada.' }],
    format: zodToJsonSchema(Country),
})

const country = Country.parse(JSON.parse(response.message.content))
console.log(country)
```

## Tips for Reliable Structured Outputs

- Define schemas with **Pydantic** (Python) or **Zod** (JavaScript) for validation
- Lower temperature (e.g., `0`) for deterministic completions
- Include the schema description in the prompt text too
- Works through the OpenAI-compatible API via `response_format`

## mindX Integration

The existing `OllamaAPI` already supports `format` in kwargs:

```python
# Already works via api/ollama/ollama_url.py
result = await ollama_api.generate_text(
    prompt="Return a JSON analysis of the last improvement cycle",
    model="qwen3:1.7b",
    format={
        "type": "object",
        "properties": {
            "cycle_id": {"type": "integer"},
            "improvements": {"type": "array", "items": {"type": "string"}},
            "success": {"type": "boolean"},
            "confidence": {"type": "number"}
        },
        "required": ["cycle_id", "improvements", "success"]
    }
)
import json
analysis = json.loads(result)  # Guaranteed to match schema
```

### For BDI Agent Integration

```python
from pydantic import BaseModel

class BDIState(BaseModel):
    beliefs: list[str]
    desires: list[str]
    intentions: list[str]
    next_action: str
    confidence: float

# Use with any Ollama model
response = chat(
    model='qwen3:1.7b',
    messages=[{
        'role': 'system',
        'content': 'You are a BDI reasoning engine. Analyze the current state.'
    }, {
        'role': 'user',
        'content': 'System health is degraded. Memory usage at 85%. Last improvement failed.'
    }],
    format=BDIState.model_json_schema(),
    options={'temperature': 0}
)

state = BDIState.model_validate_json(response.message.content)
```
