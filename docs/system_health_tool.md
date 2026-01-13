# System Health Tool Documentation

## Overview

The `SystemHealthTool` provides comprehensive system monitoring and health management capabilities for mindX. It monitors system resources (CPU, memory, disk, network, temperatures) and performs basic remediation actions to maintain system health.

**File**: `tools/system_health_tool.py`  
**Class**: `SystemHealthTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Modular Tasks**: Each monitoring function is a discrete, callable task
2. **Structured Responses**: All functions return structured dictionaries
3. **Configurable Thresholds**: Alert thresholds configurable via Config
4. **Email Alerts**: Optional email notifications for critical issues
5. **Self-Healing**: Automatic remediation for common issues

### Core Components

```python
class SystemHealthTool(BaseTool):
    - tasks: Dict[str, Callable] - Task dispatcher
    - config: Config - Configuration object
    - _send_email_alert(): Email notification helper
```

## Available Tasks

### 1. `monitor_cpu`
Monitors CPU usage and alerts if threshold is exceeded.

**Parameters**: None (uses config thresholds)

**Returns**:
```python
{
    "status": "OK" | "ALERT",
    "cpu_usage": float,
    "threshold": float,
    "message": str  # Only if ALERT
}
```

### 2. `monitor_memory_disk`
Monitors memory and disk usage.

**Parameters**: None

**Returns**:
```python
{
    "status": "OK" | "ALERT",
    "memory_usage": float,
    "disk_usage": float,
    "message": str  # Only if ALERT
}
```

### 3. `monitor_network`
Monitors network I/O over 1-second interval.

**Parameters**: None

**Returns**:
```python
{
    "status": "OK" | "ALERT",
    "sent_kbs": float,
    "recv_kbs": float,
    "message": str  # Only if ALERT
}
```

### 4. `monitor_temperatures`
Monitors system temperatures (if available).

**Parameters**: None

**Returns**: Temperature data (implementation may vary)

### 5. `get_top_cpu_processes`
Returns top 10 CPU-consuming processes.

**Parameters**: None

**Returns**:
```python
{
    "status": "SUCCESS" | "ERROR",
    "processes": List[str],
    "message": str  # Only if ERROR
}
```

### 6. `clean_log_directory`
Removes files from specified log directory.

**Parameters**:
- `directory` (str, optional): Log directory path (default: "/var/log/aion")

**Returns**:
```python
{
    "status": "SUCCESS" | "ERROR",
    "removed_count": int,
    "errors": List[str],
    "message": str
}
```

### 7. `update_man_db`
Updates manual page database if CPU usage is low.

**Parameters**: None

**Returns**:
```python
{
    "status": "SUCCESS" | "ERROR" | "SKIPPED",
    "executed": bool,
    "message": str
}
```

### 8. `kill_stale_processes` (self_healing)
Kills stale processes running longer than threshold.

**Parameters**:
- `max_runtime_hours` (int, optional): Max runtime in hours (default: 1)
- `process_name` (str, optional): Process name filter (default: "python")

**Returns**:
```python
{
    "status": "SUCCESS",
    "killed_count": int,
    "details": List[Dict[str, Any]]
}
```

## Usage

### Basic Monitoring

```python
from tools.system_health_tool import SystemHealthTool
from utils.config import Config

config = Config()
tool = SystemHealthTool(config=config)

# Monitor CPU
result = await tool.execute(task="monitor_cpu")
if result["status"] == "ALERT":
    print(f"CPU Alert: {result['message']}")

# Monitor memory and disk
result = await tool.execute(task="monitor_memory_disk")
```

### Self-Healing

```python
# Kill stale processes
result = await tool.execute(
    task="kill_stale_processes",
    max_runtime_hours=2,
    process_name="python"
)
print(f"Killed {result['killed_count']} stale processes")
```

### Log Cleanup

```python
# Clean log directory
result = await tool.execute(
    task="clean_log_directory",
    directory="/var/log/mindx"
)
```

## Configuration

### Config Options

```python
# Alert thresholds
tools.system_health.cpu_alert_threshold: 90  # CPU % threshold
tools.system_health.mem_alert_threshold: 90  # Memory % threshold
tools.system_health.disk_alert_threshold: 80  # Disk % threshold
tools.system_health.network_alert_threshold: 1000  # KB/s threshold

# Email alerts
tools.system_health.email_alerts: false  # Enable email alerts
tools.system_health.email_recipient: "admin@example.com"

# Self-healing
tools.system_health.cpu_permit_man_update: 50  # CPU % for man update
```

## Features

### 1. Email Alerts

Optional email notifications for critical issues:
- High CPU usage
- High memory/disk usage
- High network usage

Configure via:
```python
tools.system_health.email_alerts: true
tools.system_health.email_recipient: "admin@example.com"
```

### 2. Self-Healing

Automatic remediation:
- Kills stale processes
- Cleans log directories
- Updates system databases when safe

### 3. Process Monitoring

- Top CPU processes
- Process filtering
- Runtime tracking

## Limitations

### Current Limitations

1. **Synchronous Email**: Uses synchronous smtplib (should use async)
2. **Limited Metrics**: Basic metrics only
3. **No Historical Data**: No trend tracking
4. **No Custom Actions**: Fixed set of actions
5. **No Distributed Monitoring**: Single system only

### Recommended Improvements

1. **Async Email**: Use aioesmtp for async email
2. **Historical Tracking**: Store metrics over time
3. **Custom Thresholds**: Per-task threshold configuration
4. **Distributed Monitoring**: Monitor multiple systems
5. **Advanced Metrics**: More detailed system metrics
6. **Alert Aggregation**: Prevent alert flooding
7. **Predictive Alerts**: Predict issues before they occur

## Integration

### With BDI Agents

```python
# In agent plan
plan = [
    {
        "action": "monitor_system_health",
        "task": "monitor_cpu"
    },
    {
        "action": "self_heal",
        "task": "kill_stale_processes",
        "max_runtime_hours": 2
    }
]
```

### With Other Tools

The SystemHealthTool can be used with:
- **Memory Analysis Tool**: Correlate health with memory patterns
- **Strategic Analysis Tool**: Include health in strategic decisions

## Examples

### Complete Health Check

```python
# Check all system resources
cpu_result = await tool.execute(task="monitor_cpu")
mem_result = await tool.execute(task="monitor_memory_disk")
net_result = await tool.execute(task="monitor_network")

# Get top processes if CPU is high
if cpu_result["status"] == "ALERT":
    processes = await tool.execute(task="get_top_cpu_processes")
```

### Automated Cleanup

```python
# Clean logs if disk is high
disk_result = await tool.execute(task="monitor_memory_disk")
if disk_result["status"] == "ALERT" and disk_result["disk_usage"] > 85:
    cleanup = await tool.execute(
        task="clean_log_directory",
        directory="/var/log/mindx"
    )
```

## Technical Details

### Dependencies

- `psutil`: System and process utilities
- `smtplib`: Email notifications (synchronous)
- `subprocess`: Process management
- `core.bdi_agent.BaseTool`: Base tool class

### Error Handling

All tasks return structured error responses:
```python
{
    "status": "ERROR",
    "message": "Error description"
}
```

## Future Enhancements

1. **Metrics Dashboard**: Real-time metrics visualization
2. **Historical Analysis**: Trend analysis and forecasting
3. **Custom Actions**: User-defined remediation actions
4. **Multi-System**: Monitor distributed systems
5. **ML-Based Predictions**: Predict issues using ML
6. **Integration APIs**: REST API for external monitoring
7. **Alert Rules Engine**: Configurable alert rules



