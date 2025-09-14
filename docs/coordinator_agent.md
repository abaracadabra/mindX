# Coordinator Agent Documentation

## Overview

The `CoordinatorAgent` serves as the **system conductor** and **service bus** for the mindX autonomous agent ecosystem. While the `MastermindAgent` acts as the central orchestrator making strategic decisions, the Coordinator manages the operational infrastructure - handling agent lifecycle, routing communications, and providing core system services. It acts as the foundational layer that enables the distributed agent organization to function cohesively within the mindX Sovereign Intelligent Organization (SIO).

## Core Philosophy

**"Conduct the symphony, don't compose it."** The Coordinator's role is to facilitate operations, manage infrastructure, and enable seamless communication between agents. It operates as the system conductor - ensuring all components work in harmony - while strategic orchestration and decision-making is handled by the `MastermindAgent`. The Coordinator provides the operational foundation that allows the Mastermind to focus on high-level strategy and evolution.

## Architecture & Design

### Singleton Pattern
- **Single instance** ensures consistent system state
- **Async factory method** `get_instance()` for proper initialization
- **Thread-safe** with `asyncio.Lock()` for concurrent access
- **Test mode support** for development and testing scenarios

### Event-Driven Architecture
- **Pub/Sub event bus** for decoupled agent communication
- **Topic-based messaging** system for system-wide events
- **Async event handling** with callback registration
- **Event-driven interactions** for loosely coupled components

### Concurrency Management
- **Semaphore-based** task limiting for resource-intensive operations
- **Async subprocess management** for external tool invocation
- **Resource monitoring integration** to prevent system overload
- **Concurrent agent lifecycle management**

## Core Components

### 1. Interaction Management System

#### Interaction Types
```python
class InteractionType(Enum):
    QUERY = "query"                    # General LLM queries
    SYSTEM_ANALYSIS = "system_analysis"  # System-wide analysis requests
    COMPONENT_IMPROVEMENT = "component_improvement"  # Improvement delegations
    AGENT_REGISTRATION = "agent_registration"  # Agent lifecycle events
    PUBLISH_EVENT = "publish_event"    # Event bus publications
```

#### Interaction Status Tracking
```python
class InteractionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROUTED_TO_TOOL = "routed_to_tool"
```

#### Interaction Object Structure
```python
class Interaction:
    def __init__(self, interaction_id: str, interaction_type: InteractionType, content: str, **kwargs):
        self.interaction_id = interaction_id        # Unique UUID
        self.interaction_type = interaction_type    # Type enum
        self.content = content                     # Main content/request
        self.metadata = kwargs.get("metadata", {}) # Additional context
        self.status = InteractionStatus.PENDING    # Current status
        self.response = None                       # Result data
        self.error = None                         # Error information
        self.created_at = time.time()             # Creation timestamp
        self.completed_at = None                  # Completion timestamp
```

### 2. Agent Lifecycle Management

#### Agent Registration
The Coordinator maintains a comprehensive registry of all active agents:

```python
def register_agent(self, agent_id: str, agent_type: str, description: str, instance: Any):
    """Register an agent with the system."""
    self.agent_registry[agent_id] = {
        "type": agent_type,
        "description": description,
        "instance": instance,
        "registered_at": time.time(),
        "status": "active"
    }
```

#### Dynamic Agent Creation
```python
async def create_and_register_agent(self, agent_type: str, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete agent creation workflow:
    1. Validate agent doesn't already exist
    2. Create cryptographic identity via IDManagerAgent
    3. Validate with GuardianAgent
    4. Instantiate the agent
    5. Register in system
    6. Create A2A model card
    7. Update tool and model registries
    """
```

**Supported Agent Types:**
- `bdi_agent`: Belief-Desire-Intention agents with full BDI architecture
- `backup_agent`: System backup and recovery agents
- `simple_coder`: Code generation and modification agents
- **Extensible**: Framework supports adding new agent types

#### Agent Deregistration and Shutdown
```python
async def deregister_and_shutdown_agent(self, agent_id: str) -> Dict[str, Any]:
    """
    Safe agent shutdown workflow:
    1. Validate agent exists
    2. Call agent's shutdown() method if available
    3. Remove from registry
    4. Log all operations for audit trail
    """
```

### 3. Event-Driven Communication System

#### Event Subscription
```python
def subscribe(self, topic: str, callback: Callable[..., Coroutine[Any, Any, None]]):
    """Subscribe to events on a specific topic."""
    self.event_listeners[topic].append(callback)
```

#### Event Publishing
```python
async def publish_event(self, topic: str, data: Dict[str, Any]):
    """Publish an event to all subscribed listeners."""
    for callback in self.event_listeners[topic]:
        try:
            await callback(data)
        except Exception as e:
            self.logger.error(f"Event listener failed for topic '{topic}': {e}")
```

**Common Event Topics:**
- `agent.created` - New agent registration
- `agent.shutdown` - Agent deregistration
- `component.improvement.success` - Successful improvements
- `system.analysis.complete` - System analysis completion
- `resource.alert` - Resource monitoring alerts

### 4. Improvement Backlog Management

#### Backlog Structure
```python
improvement_backlog: List[Dict[str, Any]] = [
    {
        "id": "unique_uuid",
        "target_component_path": "mindx.module.class",
        "suggestion": "Description of improvement",
        "priority": 8,  # 1-10 scale
        "is_critical_target": False,
        "status": "pending",  # pending, pending_approval, in_progress, completed, failed
        "source": "system_analysis",
        "added_at": timestamp,
        "attempt_count": 0,
        "last_attempted_at": None,
        "approved_at": None,
        "rejected_at": None
    }
]
```

#### Backlog Operations
```python
def add_to_improvement_backlog(suggestion: Dict) -> None:
    """Add new improvement suggestions with deduplication."""

def _save_backlog() -> None:
    """Persist backlog to PROJECT_ROOT/data/improvement_backlog.json."""

def _load_backlog() -> List[Dict]:
    """Load backlog from persistent storage."""
```

### 5. System Analysis and Monitoring Integration

#### Resource Monitoring Integration
```python
# Register callbacks for resource alerts
async def handle_resource_alert(self, resource_type: str, alert_data: Dict):
    """Handle resource alerts from ResourceMonitor."""
    belief_key = f"system_health.{resource_type}.alert_active"
    await self.belief_system.add_belief(belief_key, True, confidence=0.9)

async def handle_resource_resolve(self, resource_type: str, resolve_data: Dict):
    """Handle resource alert resolution."""
    belief_key = f"system_health.{resource_type}.alert_active"
    await self.belief_system.add_belief(belief_key, False, confidence=0.9)
```

#### Performance Monitoring Integration
- **LLM performance tracking** via PerformanceMonitor
- **Success rate analysis** for different model types
- **Latency and cost monitoring** integration
- **Performance data aggregation** for system analysis

## Core Interaction Handlers

### 1. Query Processing (`_handle_query`)
```python
async def _handle_query(self, interaction: Interaction):
    """
    Processes general queries using the Coordinator's LLM handler.
    - Routes query to configured LLM
    - Handles LLM responses and errors
    - Updates interaction status and response
    """
```

### 2. System Analysis (`_handle_system_analysis`)
```python
async def _handle_system_analysis(self, interaction: Interaction):
    """
    Triggers comprehensive system analysis:
    - Delegates to SystemAnalyzerTool
    - Generates improvement suggestions
    - Adds suggestions to backlog
    - Publishes analysis completion events
    """
```

### 3. Component Improvement (`_handle_component_improvement`)
```python
async def _handle_component_improvement(self, interaction: Interaction):
    """
    Handles component improvement requests by conducting the process:
    - Validates target component
    - Invokes SystemAnalyzerTool for analysis
    - Generates improvement suggestions
    - Delegates execution to MastermindAgent for strategic implementation
    - Updates improvement campaign history
    """
```

### 4. Event Publishing (`_handle_publish_event`)
```python
async def _handle_publish_event(self, interaction: Interaction):
    """
    Handles event publication requests from agents:
    - Validates topic and data format
    - Publishes to event bus
    - Confirms publication success
    """
```

## Configuration Management

### Key Configuration Sections
```python
# Coordinator-specific settings
coordinator:
  llm:
    provider: "gemini"              # LLM provider
    model: "gemini-1.5-flash"      # Model selection
  
  max_concurrent_heavy_tasks: 2    # Concurrency limits
  
  autonomous_improvement:
    enabled: true                   # Enable autonomous operations
    interval_seconds: 300          # Analysis interval
    max_cpu_before_sia: 80         # CPU threshold for SIA tasks
    require_human_approval_for_critical: true  # HITL for critical changes
  
  critical_components_for_approval:  # Components requiring approval
    - "mindx.orchestration.coordinator_agent"
    - "mindx.orchestration.mastermind_agent"
    - "mindx.core.config"

# Monitoring integration
monitoring:
  resource:
    enabled: true
    alert_thresholds:
      cpu_percent: 80
      memory_percent: 85
      disk_percent: 90
  
  performance:
    enabled: true
    track_llm_calls: true
```

## A2A Protocol Integration

### Model Card Generation
```python
async def _create_a2a_model_card(self, agent_id: str, agent_type: str, config: Dict[str, Any], public_key: str) -> Dict[str, Any]:
    """
    Creates A2A-compatible model cards for agent interoperability:
    - Cryptographic identity integration
    - Capability declarations
    - Access control specifications
    - Interoperability protocol definitions
    """
```

### A2A Model Card Structure
```json
{
  "id": "agent_id",
  "name": "Agent Display Name",
  "description": "Agent description",
  "type": "agent_type",
  "version": "1.0.0",
  "enabled": true,
  "capabilities": ["capability1", "capability2"],
  "commands": ["command1", "command2"],
  "access_control": {
    "public": false,
    "authorized_agents": ["authorized_agent_1"]
  },
  "identity": {
    "public_key": "cryptographic_public_key",
    "signature": "cryptographic_signature",
    "created_at": timestamp
  },
  "a2a_endpoint": "https://mindx.internal/agent_id/a2a",
  "interoperability": {
    "protocols": ["mindx_native", "a2a_standard"],
    "message_formats": ["json", "mindx_action"],
    "authentication": "cryptographic_signature"
  }
}
```

## Registry Management

### Tool Registry Integration
```python
async def _update_tool_registry_for_agent(self, agent_id: str, agent_type: str, config: Dict[str, Any]):
    """
    Updates tool registry when agents provide tools:
    - Registers agent-provided tools
    - Updates tool availability
    - Manages tool dependencies
    """
```

### Model Registry Integration
```python
async def _update_model_registry_for_agent(self, agent_id: str, agent_type: str, config: Dict[str, Any]):
    """
    Updates model registry for agents providing models:
    - Registers LLM models
    - Updates model availability
    - Manages model configurations
    """
```

## Usage Examples

### 1. Basic Coordinator Initialization
```python
from orchestration.coordinator_agent import get_coordinator_agent_mindx_async

# Initialize Coordinator
coordinator = await get_coordinator_agent_mindx_async()

# Register an agent
coordinator.register_agent(
    agent_id="custom_agent",
    agent_type="custom",
    description="Custom agent for specific tasks",
    instance=custom_agent_instance
)
```

### 2. Interaction Processing
```python
# Process a query
result = await coordinator.handle_user_input(
    content="What is the current system status?",
    user_id="user123",
    interaction_type=InteractionType.QUERY
)

# Trigger system analysis
analysis_result = await coordinator.handle_user_input(
    content="analyze system performance",
    user_id="admin",
    interaction_type=InteractionType.SYSTEM_ANALYSIS,
    metadata={"focus_hint": "performance optimization"}
)

# Request component improvement
improvement_result = await coordinator.handle_user_input(
    content="improve memory management",
    user_id="admin",
    interaction_type=InteractionType.COMPONENT_IMPROVEMENT,
    metadata={
        "target_component": "mindx.agents.memory_agent",
        "analysis_context": "Focus on memory efficiency"
    }
)
```

### 3. Event System Usage
```python
# Subscribe to events
async def handle_agent_creation(data):
    print(f"New agent created: {data['agent_id']}")

coordinator.subscribe("agent.created", handle_agent_creation)

# Publish events
await coordinator.publish_event("custom.event", {
    "source": "my_agent",
    "data": {"key": "value"}
})
```

### 4. Dynamic Agent Management
```python
# Create a new agent
agent_config = {
    "name": "Security Auditor",
    "description": "Specialized security analysis agent",
    "capabilities": ["security_scan", "vulnerability_detection"],
    "domain": "security",
    "tools_registry": {"security_tools": True}
}

result = await coordinator.create_and_register_agent(
    agent_type="bdi_agent",
    agent_id="security_auditor_001",
    config=agent_config
)

# Later, deregister the agent
shutdown_result = await coordinator.deregister_and_shutdown_agent("security_auditor_001")
```

## CLI Interface

### Primary CLI Script: `run_mindx_coordinator.py`

The Coordinator can be operated through a dedicated CLI interface that provides full access to system operations:

```bash
python scripts/run_mindx_coordinator.py
```

### Available CLI Commands

#### Basic Operations
```bash
# General query to the Coordinator's LLM
query <your question>

# Example
query "What is the current system status and agent count?"
```

#### System Analysis
```bash
# Trigger comprehensive system analysis
analyze_system [optional context for analysis focus]

# Examples
analyze_system
analyze_system "focus on memory optimization"
analyze_system "performance bottlenecks"
```

#### Component Improvement
```bash
# Request improvement for a specific component
improve <component_id> [optional_improvement_context]

# Examples
improve mindx.core.belief_system
improve self_improve_agent_cli_mindx "optimize performance"
improve mindx.agents.memory_agent "reduce memory usage"
```

#### Backlog Management
```bash
# View current improvement backlog
backlog

# Manually process highest priority backlog item
process_backlog

# Approve a pending improvement (for critical components)
approve <backlog_item_id>

# Reject a pending improvement
reject <backlog_item_id>

# Examples
approve 550e8400-e29b-41d4-a716-446655440000
reject 550e8400-e29b-41d4-a716-446655440001
```

#### Agent Management
```bash
# List all registered agents
list_agents

# Create a new agent
create_agent <agent_type> <agent_id> [config_json]

# Deregister and shutdown an agent
shutdown_agent <agent_id>

# Examples
create_agent bdi_agent test_agent '{"domain": "test"}'
shutdown_agent test_agent
```

#### System Control
```bash
# Display help information
help

# Graceful shutdown
quit
exit
```

### CLI Example Session
```bash
$ python scripts/run_mindx_coordinator.py

🧠 MindX Coordinator Agent CLI
Type 'help' for available commands or 'quit' to exit.

coordinator> analyze_system "memory optimization"
✅ System analysis triggered. Generated 3 improvement suggestions.
   - Priority 8: mindx.agents.memory_agent - Optimize memory cleanup cycles
   - Priority 7: mindx.core.belief_system - Implement belief garbage collection
   - Priority 6: mindx.monitoring.resource_monitor - Add memory prediction

coordinator> backlog
📋 Improvement Backlog (3 items):
   1. [PENDING] Priority 8: mindx.agents.memory_agent
      Suggestion: Optimize memory cleanup cycles
      Added: 2025-06-25 10:30:15
   
   2. [PENDING] Priority 7: mindx.core.belief_system  
      Suggestion: Implement belief garbage collection
      Added: 2025-06-25 10:30:15
   
   3. [PENDING] Priority 6: mindx.monitoring.resource_monitor
      Suggestion: Add memory prediction
      Added: 2025-06-25 10:30:15

coordinator> process_backlog
🔄 Processing highest priority backlog item...
✅ Successfully initiated improvement campaign for mindx.agents.memory_agent

 coordinator> list_agents
 🤖 Registered Agents (5):
    - coordinator_agent_main: System conductor and service bus
    - mastermind_agent_main: Central orchestrator and strategic brain
    - memory_agent_main: Memory management agent
    - guardian_agent_main: Security and validation agent
    - resource_monitor_main: System resource monitoring

coordinator> quit
👋 Shutting down Coordinator Agent...
```

## Integration with Other Components

### MastermindAgent Integration
```python
# The Coordinator serves as the operational foundation for the MastermindAgent
from orchestration.mastermind_agent import MastermindAgent

# MastermindAgent receives the Coordinator instance for infrastructure access
mastermind = await MastermindAgent.get_instance(
    coordinator_agent_instance=coordinator
)

# Coordinator conducts the infrastructure while Mastermind orchestrates strategy
await mastermind.manage_mindx_evolution(top_level_directive=directive)
```

### MemoryAgent Integration
```python
# All operations are logged via MemoryAgent
await self.memory_agent.log_process(
    process_name="coordinator_operation",
    data=operation_data,
    metadata={"agent_id": self.agent_id}
)
```

### BeliefSystem Integration
```python
# System state is tracked in BeliefSystem
await self.belief_system.add_belief(
    key="system.restart_required.reason", 
    value="Critical component updated",
    confidence=0.95
)
```

### GuardianAgent Integration
```python
# Security validation for all agent operations
validation_result = await guardian.validate_new_agent(
    agent_id=agent_id,
    agent_type=agent_type,
    public_key=public_key,
    config=config
)
```

## Error Handling and Resilience

### Interaction Error Handling
```python
try:
    # Process interaction
    await self.process_interaction(interaction)
except Exception as e:
    interaction.status = InteractionStatus.FAILED
    interaction.error = str(e)
    self.logger.error(f"Interaction failed: {e}", exc_info=True)
```

### Async Task Management
```python
# Proper cleanup of background tasks
async def shutdown(self):
    """Gracefully shutdown the Coordinator."""
    # Cancel all background tasks
    for task in self.background_tasks:
        task.cancel()
    
    # Save state
    self._save_backlog()
    
    # Shutdown monitoring
    if self.resource_monitor:
        await self.resource_monitor.shutdown()
```

### Concurrency Safety
```python
# Semaphore-based concurrency control
async with self.heavy_task_semaphore:
    # Execute resource-intensive operations
    result = await heavy_operation()
```

## Performance and Monitoring

### Resource Usage Tracking
- **CPU monitoring** with configurable thresholds
- **Memory usage** tracking and alerting
- **Disk space** monitoring for data persistence
- **Network usage** for distributed operations

### Performance Metrics
- **Interaction processing times** for performance analysis
- **Agent creation/destruction rates** for lifecycle management
- **Event bus throughput** for communication efficiency
- **LLM call success rates** and latency tracking

### Logging and Observability
```python
# Comprehensive logging at all levels
self.logger.info("Operation completed successfully")
self.logger.warning("Resource threshold approaching")
self.logger.error("Critical system error", exc_info=True)

# Memory agent integration for persistent logging
await self.memory_agent.log_process(
    process_name="coordinator_operation",
    data={"operation": "agent_creation", "result": "success"},
    metadata={"agent_id": self.agent_id, "timestamp": time.time()}
)
```

## Security Considerations

### Cryptographic Identity Management
- **Public/private key pairs** for all agents
- **Digital signatures** for operation validation
- **IDManagerAgent integration** for identity lifecycle

### Access Control
- **Agent authorization** for sensitive operations
- **Command validation** before execution
- **Guardian agent integration** for security validation

### Audit Trail
- **Complete operation logging** for security audits
- **Interaction history** for forensic analysis
- **Agent lifecycle tracking** for compliance

## Best Practices

### 1. Proper Initialization
```python
# Always use the async factory method
coordinator = await get_coordinator_agent_mindx_async()

# Ensure async initialization is complete
await coordinator.async_init()
```

### 2. Event-Driven Design
```python
# Use events for loose coupling
await coordinator.publish_event("operation.completed", {
    "operation_id": "uuid",
    "result": "success"
})

# Subscribe to relevant events
coordinator.subscribe("system.alert", handle_system_alert)
```

### 3. Error Handling
```python
# Always handle potential errors
try:
    result = await coordinator.handle_user_input(content, user_id, interaction_type)
    if result.get("status") == "FAILURE":
        # Handle failure case
        handle_failure(result)
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

### 4. Resource Management
```python
# Respect concurrency limits
async with coordinator.heavy_task_semaphore:
    # Perform resource-intensive operation
    result = await expensive_operation()
```

### 5. Configuration Management
```python
# Use configuration for behavior control
if coordinator.config.get("coordinator.autonomous_improvement.enabled"):
    # Enable autonomous operations
    await start_autonomous_loop()
```

## Troubleshooting

### Common Issues

#### 1. Agent Creation Failures
```bash
# Check Guardian validation
coordinator> create_agent bdi_agent test_agent '{}'
❌ Guardian validation failed: Missing required configuration

# Solution: Provide complete configuration
coordinator> create_agent bdi_agent test_agent '{"domain": "test", "capabilities": ["test"]}'
```

#### 2. Resource Alerts
```bash
# Monitor resource usage
coordinator> query "What is the current system resource status?"
⚠️ CPU usage at 85%, memory at 78%

# Solution: Check resource monitor logs
tail -f data/memory/stm/resource_monitor/latest.json
```

#### 3. Interaction Failures
```bash
# Check interaction status
coordinator> backlog
📋 Several items marked as FAILED

# Solution: Review logs for specific errors
grep "ERROR" logs/coordinator_agent.log
```

### Debug Mode
```python
# Enable debug logging
coordinator = await get_coordinator_agent_mindx_async(
    config_override=Config(debug_mode=True)
)
```

## Future Enhancements

### Planned Features
1. **Advanced Analytics** - Enhanced system analysis with ML-based insights
2. **Multi-Node Coordination** - Distributed coordinator instances
3. **Plugin Architecture** - Dynamic loading of coordination plugins
4. **Advanced Security** - Enhanced cryptographic protocols
5. **Performance Optimization** - Improved concurrency and resource management

### Extension Points
1. **Custom Interaction Types** - Add new interaction categories
2. **Custom Agent Types** - Register new agent implementations
3. **Custom Event Handlers** - Extend event processing capabilities
4. **Custom Analysis Tools** - Integrate specialized analysis tools

## Conclusion

The `CoordinatorAgent` serves as the foundational **conductor** for the mindX autonomous agent ecosystem. While the `MastermindAgent` handles strategic orchestration and decision-making, the Coordinator provides the operational infrastructure that makes complex multi-agent systems possible. Through its event-driven design, powerful CLI interface, and extensive monitoring capabilities, it conducts the symphony of agent interactions that enable sophisticated autonomous organizations.

The Coordinator's design emphasizes **reliability**, **extensibility**, and **observability**, ensuring that it can scale to support large numbers of agents while maintaining system stability and providing complete operational visibility. Its role as the system conductor - managing infrastructure, facilitating communication, and maintaining operational integrity - creates the stable foundation upon which strategic agents like the Mastermind can build sophisticated autonomous behaviors.
