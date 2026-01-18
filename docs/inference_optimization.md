# Inference Frequency Optimization

## Overview

MindXAgent now includes a sliding scale optimization system that automatically finds the optimal inference frequency for Ollama models based on data-driven analysis.

## Architecture

### Components

1. **InferenceOptimizer** (`agents/core/inference_optimizer.py`)
   - Sliding scale frequency optimization
   - Data collection and analysis
   - Automatic frequency adjustment
   - Performance metrics tracking

2. **OllamaChatManager Integration**
   - Automatic metrics recording
   - Optimization loop management
   - Frequency-based request spacing

## How It Works

### 1. Data Collection

Every inference request is recorded with:
- Input/output token counts
- Latency (milliseconds)
- Success/failure status
- Model used
- Timestamp

### 2. Window-Based Analysis

Metrics are collected in time windows (default: 5 minutes):
- Total requests in window
- Success/failure rates
- Average latency
- Throughput (tokens/second)
- Error rate

### 3. Frequency Scoring

Each frequency is scored based on:
- **Throughput** (40% weight): Higher is better
- **Error Rate** (-30% weight): Lower is better
- **Latency** (-20% weight): Lower is better
- **Success Rate** (10% weight): Higher is better

### 4. Sliding Scale Adjustment

The optimizer uses a sliding scale approach:
- **If performance is good** (error rate < 5%, latency < 5s):
  - Gradually increase frequency (up to 10% of range)
- **If performance is poor** (error rate > 10%, latency > 10s):
  - Reduce frequency (up to 20% of range)
- **Otherwise**: Keep current frequency

### 5. Optimization Loop

- Runs every 10 minutes (configurable)
- Analyzes last 20 windows
- Adjusts frequency based on performance
- Saves metrics for historical analysis

## Configuration

### Default Settings

```python
InferenceOptimizer(
    min_frequency=1.0,      # Minimum: 1 request/minute
    max_frequency=120.0,    # Maximum: 120 requests/minute
    initial_frequency=10.0,  # Start: 10 requests/minute
    window_duration=300,    # 5 minutes per window
    optimization_interval=600  # Optimize every 10 minutes
)
```

### Customization

```python
# In ollama_chat_manager.py initialization
self.inference_optimizer = InferenceOptimizer(
    config=self.config,
    metrics_file=Path("data/custom_metrics.json"),
    min_frequency=5.0,      # Custom minimum
    max_frequency=60.0,     # Custom maximum
    initial_frequency=20.0,  # Custom starting point
    window_duration=600,     # 10 minutes per window
    optimization_interval=1200  # Optimize every 20 minutes
)
```

## Usage

### Automatic (Default)

The optimizer runs automatically when OllamaChatManager is initialized:

```python
# Already integrated in mindXagent
mindx_agent = await MindXAgent.get_instance()
# Optimization is active automatically
```

### Manual Control

```python
# Get current optimal frequency
frequency = mindx_agent.get_optimal_inference_frequency()
print(f"Optimal frequency: {frequency} rpm")

# Get optimization metrics
metrics = mindx_agent.get_inference_optimization_metrics()
print(f"Total requests: {metrics['total_requests']}")
print(f"Success rate: {metrics['recent_success_rate']*100:.1f}%")
print(f"Avg latency: {metrics['recent_avg_latency_ms']:.0f}ms")
```

### Access via OllamaChatManager

```python
if mindx_agent.ollama_chat_manager:
    optimizer = mindx_agent.ollama_chat_manager.inference_optimizer
    if optimizer:
        # Get current frequency
        freq = optimizer.get_current_frequency()
        
        # Get metrics summary
        summary = optimizer.get_metrics_summary()
        
        # Manually trigger optimization
        optimal = await optimizer.optimize_frequency()
```

## Metrics Storage

### File Location

- Default: `data/inference_optimizer_metrics.json`
- Custom: Set via `metrics_file` parameter

### Data Structure

```json
{
  "metrics": [
    {
      "timestamp": 1705536000.0,
      "model": "mistral-nemo:latest",
      "input_tokens": 50,
      "output_tokens": 100,
      "latency_ms": 1500.0,
      "success": true
    }
  ],
  "frequency_windows": [
    {
      "frequency": 10.0,
      "start_time": 1705536000.0,
      "end_time": 1705536300.0,
      "total_requests": 50,
      "successful_requests": 48,
      "failed_requests": 2,
      "avg_latency_ms": 1200.0,
      "total_input_tokens": 2500,
      "total_output_tokens": 5000,
      "throughput_tokens_per_sec": 25.0,
      "error_rate": 0.04
    }
  ],
  "current_frequency": 12.5,
  "optimal_frequency": 12.5,
  "last_updated": "2026-01-17T22:00:00"
}
```

## Optimization Algorithm

### Scoring Function

```
score = (throughput * 0.4) + 
        (error_rate * -0.3) + 
        (latency_penalty * -0.2) + 
        (success_bonus * 0.1)
```

Where:
- `throughput` = tokens per second
- `error_rate` = failed requests / total requests
- `latency_penalty` = average latency in seconds
- `success_bonus` = successful requests / total requests

### Adjustment Logic

1. **Good Performance** (error < 5%, latency < 5s):
   ```
   new_frequency = current + min(10, (max - current) * 0.1)
   ```

2. **Poor Performance** (error > 10% OR latency > 10s):
   ```
   new_frequency = current - min(10, (current - min) * 0.2)
   ```

3. **Stable Performance**:
   ```
   new_frequency = current  # No change
   ```

## Integration with Startup

The optimization system is automatically started when:
1. MindXAgent initializes
2. OllamaChatManager connects
3. First inference request is made

### Startup Flow

```
1. MindXAgent._async_init()
   ↓
2. OllamaChatManager.initialize()
   ↓
3. InferenceOptimizer.start_optimization_loop()
   ↓
4. Metrics collection begins
   ↓
5. Optimization runs every 10 minutes
```

## Monitoring

### Real-Time Metrics

```python
# Get current status
metrics = mindx_agent.get_inference_optimization_metrics()

# Check optimization status
if metrics.get("status") == "no_data":
    print("Collecting initial data...")
else:
    print(f"Frequency: {metrics['current_frequency']} rpm")
    print(f"Requests: {metrics['total_requests']}")
    print(f"Success: {metrics['recent_success_rate']*100:.1f}%")
```

### Historical Analysis

```python
# Access optimizer directly
optimizer = mindx_agent.ollama_chat_manager.inference_optimizer

# Get all windows
windows = optimizer.frequency_windows

# Analyze trends
for window in windows[-10:]:  # Last 10 windows
    print(f"{window.frequency} rpm: {window.error_rate*100:.1f}% errors, {window.throughput_tokens_per_sec:.1f} tok/s")
```

## Best Practices

1. **Let it Run**: Allow at least 3-5 windows (15-25 minutes) before expecting optimization
2. **Monitor Metrics**: Check metrics periodically to ensure optimization is working
3. **Adjust Bounds**: Set realistic min/max based on your hardware and use case
4. **Review Windows**: Analyze frequency_windows to understand performance patterns
5. **Save Metrics**: Metrics are auto-saved, but ensure disk space is available

## Troubleshooting

### Optimization Not Working

- **Check if optimizer is initialized**: `mindx_agent.ollama_chat_manager.inference_optimizer`
- **Verify metrics collection**: Check `data/inference_optimizer_metrics.json`
- **Check window duration**: Ensure enough time has passed for a complete window

### Frequency Not Changing

- **Normal**: Frequency only changes if performance significantly improves/degrades
- **Check bounds**: Ensure min/max frequencies are appropriate
- **Review metrics**: Check error rates and latencies

### High Error Rates

- **Reduce max_frequency**: Lower the maximum allowed frequency
- **Increase window_duration**: Longer windows provide more stable metrics
- **Check Ollama server**: Ensure server can handle the load

## Future Enhancements

- Machine learning-based frequency prediction
- Model-specific optimization
- Time-of-day adaptation
- Cost-aware optimization
- Multi-model load balancing
