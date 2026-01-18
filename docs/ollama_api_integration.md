# Ollama API Integration - Official Documentation Compliance

## Overview

This document describes the updates made to the Ollama API integration in `api/ollama_url.py` to align with the [official Ollama API documentation](https://github.com/ollama/ollama/blob/main/docs/api.md).

## Changes Made

### 1. Extended Timeout Configuration

**Previous**: 10s total, 5s sock_read (too short for large models)

**Updated**: 120s total, 60s sock_read (sufficient for large model inference)

```python
# Session timeout for inference requests
timeout=aiohttp.ClientTimeout(
    total=120,  # 120 second total timeout for large models
    connect=10,  # 10 second connection timeout
    sock_read=60  # 60 second read timeout for inference
)
```

**Impact**: Prevents premature timeouts with larger models (e.g., 30B+ parameter models)

### 2. Added `keep_alive` Parameter

**Per Ollama API Docs**: The `keep_alive` parameter controls how long the model stays loaded in memory after a request (default: `5m`).

**Implementation**:
```python
payload = {
    "model": model,
    "prompt": prompt,
    "stream": False,
    "keep_alive": kwargs.get("keep_alive", "5m"),  # Keep model loaded (default 5m)
    "options": {
        "num_predict": max_tokens,
        "temperature": temperature,
    }
}
```

**Benefits**:
- Faster subsequent requests (model already loaded)
- Configurable via `keep_alive` parameter
- Reduces model loading overhead for repeated requests

### 3. Support for Additional API Parameters

**Added Support For**:
- `format`: JSON mode or structured outputs (JSON schema)
- `system`: System message override
- `template`: Prompt template override
- `raw`: Bypass templating system
- `suffix`: Text after model response (for code completion)
- `images`: Base64-encoded images (for multimodal models)
- `think`: Enable thinking mode (for thinking models)

**Implementation**:
```python
# Add any additional top-level parameters from kwargs
for key in ["format", "system", "template", "raw", "suffix", "images", "think"]:
    if key in kwargs:
        payload[key] = kwargs[key]
```

### 4. Improved Token Counting

**Previous**: Estimated tokens using word count

**Updated**: Uses actual token counts from Ollama API response

```python
# Extract performance metrics if available (per Ollama API docs)
eval_count = data.get("eval_count", 0)
prompt_eval_count = data.get("prompt_eval_count", 0)

# Use actual token counts if available, otherwise estimate
if eval_count > 0 or prompt_eval_count > 0:
    total_tokens = eval_count + prompt_eval_count
    self.metrics.total_tokens += total_tokens
else:
    # Fallback estimation
    estimated_tokens = len(prompt.split()) * 1.3 + len(content.split()) * 1.3
    self.metrics.total_tokens += int(estimated_tokens)
```

**Benefits**:
- Accurate token tracking
- Better cost estimation
- Performance metrics alignment

### 5. Enhanced Error Handling

**Added Specific Timeout Error Handling**:

```python
except asyncio.TimeoutError as e:
    logger.error(f"Ollama API timeout: {e}")
    return json.dumps({"error": "TimeoutError", "message": "Request timed out after 120s..."})

except aiohttp.ServerTimeoutError as e:
    logger.error(f"Ollama API server timeout: {e}")
    return json.dumps({"error": "ServerTimeoutError", "message": "Server timeout reading response..."})
```

**Benefits**:
- Clearer error messages
- Better debugging information
- Distinguishes between connection and server timeouts

## API Endpoint Usage

### `/api/generate` Endpoint

**Standard Completion**:
```python
result = await ollama_api.generate_text(
    prompt="Why is the sky blue?",
    model="llama3.2",
    max_tokens=100,
    temperature=0.7
)
```

**With JSON Mode**:
```python
result = await ollama_api.generate_text(
    prompt="Return a JSON object with age and availability",
    model="llama3.1:8b",
    format="json",
    max_tokens=100
)
```

**With Structured Outputs**:
```python
result = await ollama_api.generate_text(
    prompt="Describe the weather",
    model="llama3.1:8b",
    format={
        "type": "object",
        "properties": {
            "temperature": {"type": "integer"},
            "condition": {"type": "string"}
        }
    }
)
```

**With Code Completion (suffix)**:
```python
result = await ollama_api.generate_text(
    prompt="def compute_gcd(a, b):",
    suffix="    return result",
    model="codellama:code",
    temperature=0
)
```

**With Custom keep_alive**:
```python
result = await ollama_api.generate_text(
    prompt="Analyze this data",
    model="mistral-nemo:latest",
    keep_alive="10m"  # Keep model loaded for 10 minutes
)
```

### `/api/chat` Endpoint

**Chat Completion**:
```python
result = await ollama_api.generate_text(
    prompt="What is the weather?",
    model="llama3.2",
    use_chat=True,
    messages=[
        {"role": "user", "content": "What is the weather?"}
    ]
)
```

**With Conversation History**:
```python
result = await ollama_api.generate_text(
    prompt="How is that different?",
    model="llama3.2",
    use_chat=True,
    messages=[
        {"role": "user", "content": "Why is the sky blue?"},
        {"role": "assistant", "content": "Due to Rayleigh scattering."},
        {"role": "user", "content": "How is that different?"}
    ]
)
```

## Performance Metrics

The API now tracks:
- **Actual Token Counts**: `eval_count` + `prompt_eval_count` from API response
- **Duration Metrics**: `total_duration`, `load_duration`, `eval_duration` (in nanoseconds)
- **Throughput**: Calculated as `eval_count / eval_duration * 10^9` tokens/second

## Best Practices

1. **Use `keep_alive` for Repeated Requests**: Set `keep_alive="10m"` or longer if making multiple requests to the same model
2. **Handle Timeouts Gracefully**: Large models may take 60+ seconds; ensure client code handles timeouts
3. **Use JSON Mode for Structured Data**: Set `format="json"` and instruct the model in the prompt
4. **Monitor Token Usage**: Use actual token counts from API responses for accurate tracking
5. **Use Chat Endpoint for Conversations**: Use `/api/chat` with message history for better context

## Migration Notes

**No Breaking Changes**: All existing code continues to work. New parameters are optional.

**Recommended Updates**:
- Add `keep_alive` parameter for frequently-used models
- Update timeout handling in client code to accommodate 120s timeout
- Use actual token counts instead of estimates where available

## References

- [Official Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Generate Endpoint Reference](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-completion)
- [Chat Endpoint Reference](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-a-chat-completion)
