# Ollama Integration Guide

mindX supports multiple ways to connect to Ollama servers:

1. **Custom Implementation** (`api/ollama_url.py`) - Default, includes rate limiting and metrics
2. **Official Ollama Python Library** (`api/ollama_official.py`) - Optional, better compatibility

## Official Ollama Python Library

The official [ollama-python](https://github.com/ollama/ollama-python) library provides:
- Better compatibility with Ollama API updates
- Official support and maintenance
- AsyncClient for async operations
- Streaming support
- Cloud model support (ollama.com)

### Installation

```bash
pip install ollama
```

### Usage

```python
from api.ollama_official import create_ollama_client, OfficialOllamaAdapter

# Create client (auto-detects if official library is available)
client = create_ollama_client(base_url="http://localhost:11434")

if client:
    # Use official library
    models = await client.list_models()
    response = await client.generate_text(
        prompt="Hello, world!",
        model="llama3:8b"
    )
else:
    # Fallback to custom implementation
    from api.ollama_url import create_ollama_api
    api = create_ollama_api()
    models = await api.list_models()
```

### Cloud Models

The official library supports Ollama Cloud models:

```python
import os
from api.ollama_official import OfficialOllamaAdapter

# Connect to Ollama Cloud
client = OfficialOllamaAdapter(
    base_url="https://ollama.com",
    api_key=os.environ.get("OLLAMA_API_KEY")
)

# Use cloud models
response = await client.generate_text(
    prompt="Hello!",
    model="gpt-oss:120b-cloud"
)
```

## Custom Implementation

The custom implementation (`api/ollama_url.py`) provides:
- Rate limiting
- Metrics tracking
- Better integration with mindX config system
- SettingsManager support

This is the default implementation and works without additional dependencies.

## Configuration

Both implementations respect the same configuration:

### Environment Variables
```bash
export MINDX_LLM__OLLAMA__BASE_URL=http://localhost:11434
export OLLAMA_API_KEY=your_key_here  # For cloud
```

### SettingsManager
```python
from webmind.settings import SettingsManager

settings = SettingsManager()
base_url = settings.get('ollama_base_url', 'http://localhost:11434')
```

### Config System
```python
from utils.config import Config

config = Config()
base_url = config.get('llm.ollama.base_url', 'http://localhost:11434')
```

## References

- [Official Ollama Python Library](https://github.com/ollama/ollama-python)
- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Ollama Cloud Models](https://ollama.com/models)
