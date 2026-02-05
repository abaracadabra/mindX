# Rate Limiting & Autonomous Interaction Optimizations

## Overview

This document describes the optimizations made to rate limiting and autonomous interaction limits to improve mindX performance and throughput.

## Changes Made

### 1. Rate Limiting Configuration

**File**: `data/config/llm_factory_config.json` (newly created)

**Previous**: Default rate limit was 2 requests per minute (hardcoded in `llm_factory.py`)

**New Configuration**:
```json
{
  "rate_limit_profiles": {
    "default_rpm": 60,        // 30x increase from 2 to 60 requests/min
    "high_throughput": 120,   // For high-performance scenarios
    "conservative": 30,       // For resource-constrained environments
    "ollama_local": 1000,     // High limit for local Ollama servers
    "mistral": 50,            // Provider-specific limits
    "gemini": 40
  }
}
```

**Impact**:
- **30x increase** in default rate limit (2 → 60 requests/min)
- Provider-specific rate limits for optimal performance
- Configurable profiles for different use cases
- Ollama local server can handle up to 1000 requests/min

### 2. MindXAgent Concurrent Improvements

**File**: `agents/core/mindXagent.py`

**Previous**: `max_concurrent_improvements: 1`

**New**: `max_concurrent_improvements: 5`

**Impact**:
- **5x increase** in parallel improvement operations
- Allows mindXagent to work on multiple improvements simultaneously
- Better utilization of system resources
- Faster overall improvement cycles

### 3. Coordinator Heavy Tasks Concurrency

**File**: `data/config/mindx_config.json`

**Previous**: `max_concurrent_heavy_tasks: 2` (default)

**New**: `max_concurrent_heavy_tasks: 5`

**Impact**:
- **2.5x increase** in concurrent heavy task execution
- Better handling of resource-intensive operations
- Improved system throughput for component improvements
- More efficient use of available system resources

## Performance Improvements

### Before Optimization
- Rate Limit: 2 requests/min
- Concurrent Improvements: 1
- Heavy Tasks: 2 concurrent
- **Estimated Throughput**: ~2 operations/min

### After Optimization
- Rate Limit: 60 requests/min (default)
- Concurrent Improvements: 5
- Heavy Tasks: 5 concurrent
- **Estimated Throughput**: ~60 operations/min (30x improvement)

## Configuration Profiles

### Default Profile (`default_rpm`)
- **Rate**: 60 requests/min
- **Use Case**: Standard mindX operations
- **Best For**: General autonomous improvement cycles

### High Throughput Profile (`high_throughput`)
- **Rate**: 120 requests/min
- **Use Case**: Intensive improvement campaigns
- **Best For**: Large-scale system optimization

### Conservative Profile (`conservative`)
- **Rate**: 30 requests/min
- **Use Case**: Resource-constrained environments
- **Best For**: Systems with limited API quotas

### Ollama Local Profile (`ollama_local`)
- **Rate**: 1000 requests/min
- **Use Case**: Local Ollama server inference
- **Best For**: High-frequency local model interactions

## Usage

### Using Rate Limit Profiles

When creating LLM handlers, specify the rate limit profile:

```python
# Default profile (60 requests/min)
handler = await create_llm_handler(
    provider_name="mistral",
    rate_limit_profile="default_rpm"
)

# High throughput profile (120 requests/min)
handler = await create_llm_handler(
    provider_name="mistral",
    rate_limit_profile="high_throughput"
)

# Ollama local profile (1000 requests/min)
handler = await create_llm_handler(
    provider_name="ollama",
    rate_limit_profile="ollama_local"
)
```

### Adjusting Concurrent Limits

**MindXAgent Settings** (in code):
```python
mindx_agent.settings["max_concurrent_improvements"] = 5
```

**Coordinator Settings** (in `mindx_config.json`):
```json
{
  "coordinator": {
    "max_concurrent_heavy_tasks": 5
  }
}
```

## Monitoring (both directions)

Whether mindX is ingesting, providing inference, or services, monitoring and rate control are essential in **both directions** (inbound and outbound). See **[docs/monitoring_rate_control.md](monitoring_rate_control.md)** for scientific network and data metrics (latency ms, bytes, req/min). Inbound: `GET /api/monitoring/inbound`; outbound: rate limiter and provider `get_metrics()`.

Monitor the following metrics to ensure optimal performance:

1. **Rate Limit Hits**: Check if rate limits are being hit frequently
2. **Concurrent Task Queue**: Monitor queue depth for heavy tasks
3. **Improvement Cycle Duration**: Track time for improvement cycles
4. **System Resource Usage**: Monitor CPU, memory, and API usage

## Recommendations

1. **Start with Defaults**: Use default settings (60 RPM, 5 concurrent) for most scenarios
2. **Scale Up Gradually**: Increase limits if system can handle more load
3. **Monitor API Quotas**: Ensure provider API quotas support higher rates
4. **Adjust for Environment**: Use conservative profile for limited resources
5. **Use Ollama Local**: For local inference, use `ollama_local` profile for maximum throughput

## Rollback

If issues occur, you can rollback by:

1. **Rate Limiting**: Edit `data/config/llm_factory_config.json` and set `default_rpm` to 2
2. **Concurrent Improvements**: Edit `agents/core/mindXagent.py` and set `max_concurrent_improvements` to 1
3. **Heavy Tasks**: Edit `data/config/mindx_config.json` and set `max_concurrent_heavy_tasks` to 2

## Future Enhancements

1. **Dynamic Rate Limiting**: Adjust rates based on system load
2. **Adaptive Concurrency**: Automatically adjust concurrent limits
3. **Provider-Specific Optimization**: Fine-tune limits per provider
4. **Cost-Aware Rate Limiting**: Consider API costs in rate decisions
5. **Performance-Based Profiles**: Auto-select profiles based on performance metrics