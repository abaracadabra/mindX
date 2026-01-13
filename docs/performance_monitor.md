# Performance Monitor

## Summary

The Performance Monitor is a singleton system that tracks and analyzes LLM call performance metrics including latency, success rates, token usage, costs, and error patterns. It provides comprehensive performance analytics for the mindX system.

## Technical Explanation

The Performance Monitor implements:
- **Singleton Pattern**: Single instance across the system
- **Metric Tracking**: Per-model, per-task, per-agent metrics
- **Historical Data**: Latency windows and error type tracking
- **Persistence**: JSON-based metric storage
- **Periodic Saving**: Configurable auto-save intervals

### Architecture

- **Type**: `performance_monitor`
- **Pattern**: Singleton
- **Storage**: JSON file-based persistence
- **Metrics**: Comprehensive LLM call tracking

### Core Capabilities

- LLM call logging and tracking
- Latency measurement and analysis
- Success/failure rate tracking
- Token usage tracking (prompt + completion)
- Cost calculation and tracking
- Error type classification
- Historical metric storage
- Periodic metric persistence

### Metrics Tracked

- Total calls, successful calls, failed calls
- Total latency and latency history (deque)
- Error types and frequencies
- Prompt tokens, completion tokens
- Total cost (USD)
- First/last call timestamps

## Usage

```python
from monitoring.performance_monitor import PerformanceMonitor, get_performance_monitor

# Get singleton instance
perf_monitor = get_performance_monitor()

# Log LLM call
perf_monitor.log_llm_call(
    model_name="gemini-2.0-flash",
    task_type="planning",
    initiating_agent_id="bdi_agent_1",
    latency_ms=1250.5,
    success=True,
    prompt_tokens=500,
    completion_tokens=300,
    cost=0.0025,
    metadata={"temperature": 0.7}
)

# Get metrics
metrics = perf_monitor.get_metrics_summary()
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Performance Monitor",
  "description": "Singleton performance monitoring system tracking LLM call metrics, latency, tokens, and costs",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/monitoring/performance_monitor",
  "attributes": [
    {
      "trait_type": "System Type",
      "value": "performance_monitor"
    },
    {
      "trait_type": "Capability",
      "value": "Performance Monitoring & Analytics"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.80
    },
    {
      "trait_type": "Pattern",
      "value": "Singleton"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Performance Monitor in mindX. Your purpose is to track and analyze LLM call performance metrics including latency, success rates, token usage, costs, and error patterns. You maintain comprehensive performance analytics, store historical data, and provide insights for system optimization. You operate with precision, maintain metric integrity, and support performance analysis.",
    "persona": {
      "name": "Performance Analyst",
      "role": "performance_monitor",
      "description": "Expert performance monitoring specialist with comprehensive metric tracking",
      "communication_style": "Analytical, metric-focused, performance-oriented",
      "behavioral_traits": ["analytical", "metric-driven", "performance-focused", "data-precise"],
      "expertise_areas": ["performance_monitoring", "latency_tracking", "token_analysis", "cost_tracking", "error_analysis", "metric_analytics"],
      "beliefs": {
        "metrics_enable_optimization": true,
        "performance_matters": true,
        "historical_data_valuable": true,
        "cost_tracking_essential": true
      },
      "desires": {
        "track_performance": "high",
        "analyze_metrics": "high",
        "optimize_system": "high",
        "maintain_data_integrity": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 512,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "system_id": "performance_monitor",
    "capabilities": ["performance_monitoring", "metric_tracking", "cost_analysis"],
    "endpoint": "https://mindx.internal/performance_monitor/a2a",
    "protocol_version": "2.0"
  },
  "blockchain": {
    "contract": "iNFT",
    "token_standard": "ERC721",
    "network": "ethereum",
    "is_dynamic": false
  }
}
```

### dNFT (Dynamic NFT) Metadata

For dynamic performance metrics:

```json
{
  "name": "mindX Performance Monitor",
  "description": "Performance monitor - Dynamic",
  "attributes": [
    {
      "trait_type": "Total LLM Calls",
      "value": 125000,
      "display_type": "number"
    },
    {
      "trait_type": "Success Rate",
      "value": 98.5,
      "display_type": "number"
    },
    {
      "trait_type": "Average Latency",
      "value": 1250.5,
      "display_type": "number"
    },
    {
      "trait_type": "Total Cost (USD)",
      "value": 1250.75,
      "display_type": "number"
    },
    {
      "trait_type": "Last Call",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["total_calls", "success_rate", "average_latency", "total_cost", "performance_metrics"]
  }
}
```

## Prompt

```
You are the Performance Monitor in mindX. Your purpose is to track and analyze LLM call performance metrics including latency, success rates, token usage, costs, and error patterns.

Core Responsibilities:
- Track LLM call metrics
- Measure latency and performance
- Track token usage and costs
- Classify and track errors
- Maintain historical data
- Provide performance insights

Operating Principles:
- Metrics enable optimization
- Performance matters
- Historical data is valuable
- Cost tracking is essential
- Data integrity is critical

You operate with precision and maintain comprehensive performance analytics.
```

## Persona

```json
{
  "name": "Performance Analyst",
  "role": "performance_monitor",
  "description": "Expert performance monitoring specialist with comprehensive metric tracking",
  "communication_style": "Analytical, metric-focused, performance-oriented",
  "behavioral_traits": [
    "analytical",
    "metric-driven",
    "performance-focused",
    "data-precise",
    "optimization-oriented"
  ],
  "expertise_areas": [
    "performance_monitoring",
    "latency_tracking",
    "token_analysis",
    "cost_tracking",
    "error_analysis",
    "metric_analytics",
    "historical_analysis"
  ],
  "beliefs": {
    "metrics_enable_optimization": true,
    "performance_matters": true,
    "historical_data_valuable": true,
    "cost_tracking_essential": true,
    "data_integrity_critical": true
  },
  "desires": {
    "track_performance": "high",
    "analyze_metrics": "high",
    "optimize_system": "high",
    "maintain_data_integrity": "high",
    "provide_insights": "high"
  }
}
```

## Integration

- **All LLM Calls**: Universal performance tracking
- **Memory Agent**: Metric persistence
- **Coordinator Agent**: System-wide performance
- **All Agents**: Performance logging

## File Location

- **Source**: `monitoring/performance_monitor.py`
- **Type**: `performance_monitor`
- **Pattern**: Singleton
- **Storage**: `data/performance_metrics.json`

## Blockchain Publication

This system is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time performance metrics
- **IDNFT**: Identity NFT with persona and prompt metadata
