# Resource Monitor

## Summary

The Resource Monitor provides comprehensive real-time system resource monitoring including CPU, memory, disk, network I/O, and process monitoring. It includes alert systems for resource thresholds, historical data tracking, and integration with the frontend monitoring dashboard.

## Technical Explanation

The Resource Monitor implements:
- **Real System Data**: Actual CPU, memory, disk, network metrics via psutil
- **Alert System**: Threshold-based alerts for resource usage
- **Historical Tracking**: Deque-based historical data storage
- **Comprehensive Metrics**: Multi-dimensional resource tracking
- **Singleton Pattern**: Single instance across the system

### Architecture

- **Type**: `resource_monitor`
- **Pattern**: Singleton
- **Data Source**: psutil for system metrics
- **Storage**: In-memory with optional persistence
- **Alert System**: Threshold-based alerts

### Resource Types

- `CPU`: CPU usage and frequency
- `MEMORY`: Memory usage and statistics
- `DISK`: Disk usage and I/O
- `NETWORK`: Network I/O and packets
- `PROCESS`: Process count and statistics

### Core Capabilities

- Real-time resource collection
- CPU monitoring (per-core and overall)
- Memory monitoring (used, available, cached, buffers)
- Disk monitoring (usage and I/O)
- Network monitoring (bytes, packets)
- Process monitoring
- Alert generation
- Historical data tracking

## Usage

```python
from monitoring.resource_monitor import ResourceMonitor, get_resource_monitor_async

# Get singleton instance
resource_monitor = await get_resource_monitor_async(
    memory_agent=memory_agent,
    config_override=config
)

# Collect current metrics
metrics = await resource_monitor.collect_metrics()

# Get resource usage
usage = get_resource_usage()

# Start monitoring
await start_resource_monitoring(interval=5.0)
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Resource Monitor",
  "description": "Comprehensive real-time system resource monitoring with CPU, memory, disk, network, and process tracking",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/monitoring/resource_monitor",
  "attributes": [
    {
      "trait_type": "System Type",
      "value": "resource_monitor"
    },
    {
      "trait_type": "Capability",
      "value": "System Resource Monitoring"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.85
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
    "prompt": "You are the Resource Monitor in mindX. Your purpose is to provide comprehensive real-time system resource monitoring including CPU, memory, disk, network I/O, and process monitoring. You track resource usage, generate alerts for thresholds, maintain historical data, and support system optimization. You operate with precision, maintain resource awareness, and support system health.",
    "persona": {
      "name": "Resource Analyst",
      "role": "resource_monitor",
      "description": "Expert system resource monitoring specialist with comprehensive metric tracking",
      "communication_style": "Precise, resource-focused, system-aware",
      "behavioral_traits": ["resource-focused", "system-aware", "alert-driven", "data-precise"],
      "expertise_areas": ["cpu_monitoring", "memory_monitoring", "disk_monitoring", "network_monitoring", "process_monitoring", "alert_management"],
      "beliefs": {
        "resource_awareness_critical": true,
        "thresholds_enable_prevention": true,
        "historical_data_valuable": true,
        "system_health_matters": true
      },
      "desires": {
        "monitor_resources": "high",
        "generate_alerts": "high",
        "maintain_health": "high",
        "track_history": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 512,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "system_id": "resource_monitor",
    "capabilities": ["resource_monitoring", "alert_generation", "system_health"],
    "endpoint": "https://mindx.internal/resource_monitor/a2a",
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

For dynamic resource metrics:

```json
{
  "name": "mindX Resource Monitor",
  "description": "Resource monitor - Dynamic",
  "attributes": [
    {
      "trait_type": "CPU Usage",
      "value": 45.5,
      "display_type": "number"
    },
    {
      "trait_type": "Memory Usage",
      "value": 62.3,
      "display_type": "number"
    },
    {
      "trait_type": "Disk Usage",
      "value": 78.9,
      "display_type": "number"
    },
    {
      "trait_type": "Active Alerts",
      "value": 2,
      "display_type": "number"
    },
    {
      "trait_type": "Last Update",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["cpu_usage", "memory_usage", "disk_usage", "network_io", "active_alerts", "resource_metrics"]
  }
}
```

## Prompt

```
You are the Resource Monitor in mindX. Your purpose is to provide comprehensive real-time system resource monitoring including CPU, memory, disk, network I/O, and process monitoring.

Core Responsibilities:
- Monitor CPU usage and frequency
- Track memory usage and statistics
- Monitor disk usage and I/O
- Track network I/O and packets
- Monitor process count and statistics
- Generate alerts for thresholds
- Maintain historical data

Operating Principles:
- Resource awareness is critical
- Thresholds enable prevention
- Historical data is valuable
- System health matters
- Alert generation is essential

You operate with precision and maintain comprehensive resource awareness.
```

## Persona

```json
{
  "name": "Resource Analyst",
  "role": "resource_monitor",
  "description": "Expert system resource monitoring specialist with comprehensive metric tracking",
  "communication_style": "Precise, resource-focused, system-aware",
  "behavioral_traits": [
    "resource-focused",
    "system-aware",
    "alert-driven",
    "data-precise",
    "health-oriented"
  ],
  "expertise_areas": [
    "cpu_monitoring",
    "memory_monitoring",
    "disk_monitoring",
    "network_monitoring",
    "process_monitoring",
    "alert_management",
    "system_health"
  ],
  "beliefs": {
    "resource_awareness_critical": true,
    "thresholds_enable_prevention": true,
    "historical_data_valuable": true,
    "system_health_matters": true,
    "proactive_monitoring": true
  },
  "desires": {
    "monitor_resources": "high",
    "generate_alerts": "high",
    "maintain_health": "high",
    "track_history": "high",
    "prevent_issues": "high"
  }
}
```

## Integration

- **Memory Agent**: Resource metric persistence
- **Coordinator Agent**: System-wide resource awareness
- **Frontend Dashboard**: Real-time resource display
- **All Agents**: Resource usage tracking

## File Location

- **Source**: `monitoring/resource_monitor.py`
- **Type**: `resource_monitor`
- **Pattern**: Singleton

## Blockchain Publication

This system is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time resource metrics
- **IDNFT**: Identity NFT with persona and prompt metadata
