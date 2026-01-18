# mindXagent Ollama Connection Monitoring

## Overview

This document describes the comprehensive monitoring and error handling system for mindXagent's Ollama connection, ensuring accurate, error-free network operations and efficient network sanity.

## Monitoring System

### Connection Monitor Script

**Location**: `scripts/test_mindxagent_ollama_connection_monitor.py`

The connection monitor provides:

- **Real-time Connection Monitoring**: Continuous health checks at configurable intervals
- **Error Detection**: Automatic detection and logging of connection errors
- **Log Analysis**: Scans system logs for Ollama-related errors
- **Network Sanity Validation**: Comprehensive validation of network health
- **Performance Metrics**: Tracks latency, success rates, and error rates
- **Automatic Recovery**: Attempts to reconnect on connection failures

### Features

1. **Periodic Health Checks**
   - Configurable check interval (default: 10 seconds)
   - Connection status validation
   - Model availability verification
   - Response time measurement

2. **Error Tracking**
   - Categorizes errors by type
   - Tracks error frequency and patterns
   - Logs errors to memory agent for persistence
   - Provides detailed error reports

3. **Network Sanity Validation**
   - Validates connection status
   - Checks model availability
   - Monitors error rates
   - Tracks latency metrics
   - Validates inference optimizer status

4. **Automatic Recovery**
   - Exponential backoff retry logic
   - Connection reinitialization
   - Model rediscovery on failures

## Enhanced Error Handling

### Ollama Chat Manager Improvements

**Location**: `agents/core/ollama_chat_manager.py`

#### Connection Retry Logic

- **Exponential Backoff**: Retries with increasing delays (2^attempt seconds)
- **Maximum Retries**: Configurable retry attempts (default: 3)
- **Automatic Reconnection**: Attempts to restore connection on failure
- **Error Categorization**: Identifies connection vs. application errors

#### Enhanced Error Logging

- **Error Type Tracking**: Categorizes errors by exception type
- **Memory Agent Integration**: Logs errors to persistent memory
- **Connection State Management**: Automatically marks connection as disconnected on network errors
- **Detailed Error Context**: Includes model, conversation ID, and timestamp

#### Health Check Method

New `check_health()` method provides:

```python
health = await ollama_chat_manager.check_health()
```

Returns comprehensive health status including:
- Connection status
- Available models count
- Connection test results
- Inference optimizer metrics
- Identified issues

## Usage

### Running the Connection Monitor

```bash
# Run with default settings (5 minutes, 10 second intervals)
python3 scripts/test_mindxagent_ollama_connection_monitor.py

# Monitor for custom duration
# Edit MONITOR_DURATION and CHECK_INTERVAL in the script
```

### Integration with mindXagent

The monitoring system is automatically integrated:

1. **Initialization**: Connection health is checked during mindXagent initialization
2. **Runtime Monitoring**: Errors are logged and tracked during operation
3. **Automatic Recovery**: Connection failures trigger automatic reconnection attempts
4. **Health Reporting**: Health status is available via API endpoints

## Error Categories

### Connection Errors

- **Network Timeout**: Request timeout errors
- **Connection Refused**: Server not reachable
- **Network Unreachable**: Network connectivity issues
- **DNS Resolution**: Hostname resolution failures

### Application Errors

- **Model Not Found**: Requested model unavailable
- **Invalid Request**: Malformed API requests
- **Rate Limiting**: Too many requests
- **Server Errors**: Ollama server internal errors

## Network Sanity Checks

The system performs comprehensive sanity checks:

1. **Connection Status**: Verifies active connection to Ollama server
2. **Model Availability**: Ensures at least one model is available
3. **Error Rate**: Monitors error rate (alerts if > 10%)
4. **Latency**: Tracks average latency (alerts if > 10 seconds)
5. **Optimizer Status**: Validates inference optimizer functionality

## Metrics and Reporting

### Tracked Metrics

- **Success Rate**: Percentage of successful requests
- **Error Rate**: Percentage of failed requests
- **Average Latency**: Mean response time
- **Min/Max Latency**: Response time bounds
- **Total Requests**: Cumulative request count
- **Connection Uptime**: Time since last successful connection

### Reporting

The monitor provides:

- **Real-time Status**: Live connection status updates
- **Periodic Summaries**: Summary reports at check intervals
- **Final Report**: Comprehensive summary at end of monitoring
- **Error Log**: Detailed log of all errors encountered

## Best Practices

### Configuration

- **Check Interval**: Balance between responsiveness and resource usage
  - Recommended: 10-30 seconds for production
  - Lower intervals for critical systems
  - Higher intervals for background monitoring

- **Monitor Duration**: Based on use case
  - Short tests: 1-5 minutes
  - Extended monitoring: 30+ minutes
  - Continuous monitoring: Run as background service

### Error Handling

- **Automatic Recovery**: Enabled by default
- **Manual Intervention**: Monitor logs for persistent errors
- **Alert Thresholds**: Configure alerts for high error rates
- **Log Retention**: Maintain logs for trend analysis

## Integration with AGLM

The monitoring system integrates with AGLM (a General Learning Model) framework:

- **Machine Dreaming**: Monitors creative generation tasks
- **Auto-Tuning**: Tracks hyperparameter optimization processes
- **Digital Long-Term Memory**: Validates blockchain-backed memory storage
- **Blockchain Integration**: Ensures secure, decentralized operations

## Related Documentation

- [AGLM Framework Documentation](aglm.md)
- [Ollama Chat Manager](../agents/core/ollama_chat_manager.py)
- [mindXagent Documentation](../agents/core/mindXagent.py)
- [Inference Optimization](inference_optimization.md)

---

**Last Updated**: 2026-01-17  
**Maintained By**: mindX Documentation System
