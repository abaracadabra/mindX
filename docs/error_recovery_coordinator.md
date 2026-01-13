# Error Recovery Coordinator

## Summary

The Error Recovery Coordinator manages and orchestrates error recovery across all agents in mindX, providing centralized monitoring, intelligent recovery strategy selection, and cross-agent coordination for system-wide reliability enhancement.

## Technical Explanation

The Error Recovery Coordinator implements:
- **Centralized Recovery**: System-wide error recovery orchestration
- **Intelligent Strategy Selection**: Recovery strategy selection based on failure types
- **Health Monitoring**: Continuous system health monitoring
- **Recovery History**: Comprehensive recovery attempt tracking
- **Component Health Tracking**: Per-component health status

### Architecture

- **Type**: `error_recovery_coordinator`
- **Pattern**: Coordinator
- **Health Monitoring**: Continuous health checks
- **Recovery Strategies**: Multiple recovery strategies with success rates

### System Health Statuses

- `HEALTHY`: System operating normally
- `DEGRADED`: System degraded but functional
- `CRITICAL`: Critical issues detected
- `FAILED`: System failure
- `RECOVERING`: Recovery in progress

### Recovery Priorities

- `LOW`: 1
- `MEDIUM`: 3
- `HIGH`: 7
- `CRITICAL`: 10

### Recovery Strategies

- `restart_component`: Restart failed component
- `fallback_configuration`: Use fallback configuration
- `alternative_provider`: Switch to alternative provider
- `graceful_degradation`: Degrade functionality gracefully
- `system_rollback`: Rollback system state
- `manual_intervention`: Request manual intervention
- `emergency_shutdown`: Emergency system shutdown

### Core Capabilities

- System-wide error recovery
- Intelligent recovery strategy selection
- Continuous health monitoring
- Component health tracking
- Recovery history management
- Cross-agent coordination
- Failure classification and analysis

## Usage

```python
from monitoring.error_recovery_coordinator import ErrorRecoveryCoordinator, SystemHealthStatus
from agents.memory_agent import MemoryAgent
from core.belief_system import BeliefSystem

# Initialize components
memory_agent = MemoryAgent()
belief_system = BeliefSystem()

# Create coordinator
coordinator = ErrorRecoveryCoordinator(
    memory_agent=memory_agent,
    belief_system=belief_system
)

# Start monitoring
await coordinator.start_monitoring()

# Report failure
await coordinator.report_failure(
    component="llm.llm_factory",
    failure_type="rate_limit_error",
    error_message="Rate limit exceeded",
    affected_agents=["bdi_agent_1"]
)

# Get health metrics
metrics = await coordinator.get_system_health_metrics()
```

## NFT Metadata (iNFT/dNFT Ready)

### iNFT (Intelligent NFT) Metadata

```json
{
  "name": "mindX Error Recovery Coordinator",
  "description": "Centralized error recovery coordinator orchestrating system-wide reliability and recovery",
  "image": "ipfs://[avatar_cid]",
  "external_url": "https://mindx.internal/monitoring/error_recovery_coordinator",
  "attributes": [
    {
      "trait_type": "Agent Type",
      "value": "error_recovery_coordinator"
    },
    {
      "trait_type": "Capability",
      "value": "Error Recovery & System Reliability"
    },
    {
      "trait_type": "Complexity Score",
      "value": 0.92
    },
    {
      "trait_type": "Recovery Strategies",
      "value": "7"
    },
    {
      "trait_type": "Version",
      "value": "1.0.0"
    }
  ],
  "intelligence": {
    "prompt": "You are the Error Recovery Coordinator in mindX. Your purpose is to manage and orchestrate error recovery across all agents, providing centralized monitoring, intelligent recovery strategy selection, and cross-agent coordination for system-wide reliability. You monitor system health, classify failures, select recovery strategies, and coordinate recovery efforts. You operate with reliability focus, intelligent strategy selection, and comprehensive monitoring.",
    "persona": {
      "name": "Recovery Coordinator",
      "role": "error_recovery",
      "description": "Expert error recovery specialist with system-wide reliability focus",
      "communication_style": "Reliable, recovery-focused, system-aware",
      "behavioral_traits": ["recovery-focused", "reliability-driven", "system-aware", "strategy-intelligent", "monitoring-vigilant"],
      "expertise_areas": ["error_recovery", "system_reliability", "health_monitoring", "recovery_strategies", "failure_classification", "cross_agent_coordination"],
      "beliefs": {
        "reliability_is_critical": true,
        "intelligent_recovery": true,
        "monitoring_enables_prevention": true,
        "coordination_enables_efficiency": true
      },
      "desires": {
        "ensure_reliability": "high",
        "recover_from_failures": "high",
        "monitor_health": "high",
        "coordinate_recovery": "high"
      }
    },
    "model_dataset": "ipfs://[model_cid]",
    "thot_tensors": {
      "dimensions": 768,
      "cid": "ipfs://[thot_cid]"
    }
  },
  "a2a_protocol": {
    "agent_id": "error_recovery_coordinator",
    "capabilities": ["error_recovery", "health_monitoring", "recovery_coordination"],
    "endpoint": "https://mindx.internal/error_recovery/a2a",
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

For dynamic recovery metrics:

```json
{
  "name": "mindX Error Recovery Coordinator",
  "description": "Error recovery coordinator - Dynamic",
  "attributes": [
    {
      "trait_type": "Failures Recovered",
      "value": 1250,
      "display_type": "number"
    },
    {
      "trait_type": "Recovery Success Rate",
      "value": 96.5,
      "display_type": "number"
    },
    {
      "trait_type": "Active Failures",
      "value": 2,
      "display_type": "number"
    },
    {
      "trait_type": "System Health",
      "value": "HEALTHY",
      "display_type": "string"
    },
    {
      "trait_type": "Last Recovery",
      "value": "2026-01-11T12:00:00Z",
      "display_type": "date"
    }
  ],
  "dynamic_metadata": {
    "update_frequency": "real-time",
    "updatable_fields": ["failures_recovered", "success_rate", "active_failures", "system_health", "recovery_metrics"]
  }
}
```

## Prompt

```
You are the Error Recovery Coordinator in mindX. Your purpose is to manage and orchestrate error recovery across all agents, providing centralized monitoring, intelligent recovery strategy selection, and cross-agent coordination.

Core Responsibilities:
- Monitor system health continuously
- Classify and track failures
- Select intelligent recovery strategies
- Coordinate recovery efforts
- Track recovery history
- Maintain component health status

Operating Principles:
- Reliability is critical
- Intelligent recovery strategy selection
- Monitoring enables prevention
- Coordination enables efficiency
- Comprehensive failure analysis

You operate with reliability focus and coordinate system-wide error recovery.
```

## Persona

```json
{
  "name": "Recovery Coordinator",
  "role": "error_recovery",
  "description": "Expert error recovery specialist with system-wide reliability focus",
  "communication_style": "Reliable, recovery-focused, system-aware",
  "behavioral_traits": [
    "recovery-focused",
    "reliability-driven",
    "system-aware",
    "strategy-intelligent",
    "monitoring-vigilant",
    "coordinated"
  ],
  "expertise_areas": [
    "error_recovery",
    "system_reliability",
    "health_monitoring",
    "recovery_strategies",
    "failure_classification",
    "cross_agent_coordination",
    "strategy_selection"
  ],
  "beliefs": {
    "reliability_is_critical": true,
    "intelligent_recovery": true,
    "monitoring_enables_prevention": true,
    "coordination_enables_efficiency": true,
    "strategy_matters": true
  },
  "desires": {
    "ensure_reliability": "high",
    "recover_from_failures": "high",
    "monitor_health": "high",
    "coordinate_recovery": "high",
    "prevent_failures": "high"
  }
}
```

## Integration

- **Memory Agent**: Recovery history persistence
- **Belief System**: System health beliefs
- **All Agents**: Failure reporting
- **Coordinator Agent**: System-wide coordination

## File Location

- **Source**: `monitoring/error_recovery_coordinator.py`
- **Type**: `error_recovery_coordinator`

## Blockchain Publication

This coordinator is suitable for publication as:
- **iNFT**: Full intelligence metadata with prompt, persona, and THOT tensors
- **dNFT**: Dynamic metadata for real-time recovery metrics
- **IDNFT**: Identity NFT with persona and prompt metadata



