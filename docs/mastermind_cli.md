# Mastermind CLI Reference

## Overview

The Mastermind CLI (`scripts/run_mindx.py`) provides a comprehensive command-line interface for interacting with the mindX Augmentic Intelligence system. This CLI serves as the primary entry point for orchestrating system evolution, agent deployment, and component management through the MastermindAgent.

**Key Features:**
- **Augmentic Intelligence**: Built on principles of augmented intelligence
- **BDI Integration**: Seamless interaction with BDI parameter processing
- **Multi-Agent Orchestration**: Coordinates Mastermind, Coordinator, Guardian, and AutoMINDX agents
- **Identity Management**: Cryptographic identity creation and management
- **Memory Integration**: All interactions logged via MemoryAgent

## Getting Started

### Launch the CLI

```bash
cd /path/to/mindX
python scripts/run_mindx.py
```

**System Requirements:**
- Python 3.8+
- All mindX dependencies installed
- Valid configuration files in `data/config/`
- Network access for LLM API calls

### CLI Prompt

```
mindX (Mastermind) > 
```

The CLI operates in an interactive loop, accepting commands until `quit` or `exit` is entered.

## Command Categories

### Core Commands

#### `evolve <directive>`
**Purpose:** Task the Mastermind to evolve its own codebase based on a high-level directive.

**Syntax:**
```bash
evolve <directive_string>
```

**Examples:**
```bash
evolve Enhance system-wide logging capabilities
evolve Improve error handling across all agents
evolve Add better documentation generation tools
```

**Process Flow:**
1. Mastermind receives directive
2. Strategic analysis and planning
3. Component identification and improvement
4. Execution via BDI agent system
5. Results logged and reported

**Output:** JSON summary of evolution campaign outcome

---

#### `deploy <directive>`
**Purpose:** Task AutoMINDX/Mastermind to deploy new agents to achieve a specific goal.

**Syntax:**
```bash
deploy <directive_string>
```

**Examples:**
```bash
deploy Create a specialized monitoring agent for system health
deploy Deploy agents for automated testing workflow
deploy Initialize agents for continuous integration pipeline
```

**Process Flow:**
1. AutoMINDX analyzes deployment requirements
2. Agent type and configuration determination
3. Dynamic agent instantiation
4. Registration with Coordinator
5. Identity creation via IDManager

**Output:** JSON summary of deployment campaign outcome

---

#### `introspect <role>`
**Purpose:** Ask AutoMINDX to generate a new persona for a given role description.

**Syntax:**
```bash
introspect <role_description>
```

**Examples:**
```bash
introspect Senior DevOps Engineer with ML expertise
introspect System Architect focused on microservices
introspect Quality Assurance Specialist for AI systems
```

**Output:** Generated persona with characteristics, skills, and behavioral patterns

---

#### `mastermind_status`
**Purpose:** Display Mastermind's current objectives and campaign history.

**Syntax:**
```bash
mastermind_status
```

**Output:**
- High-level objectives list
- Strategic campaigns history
- Current system state

---

#### `show_agent_registry`
**Purpose:** Display all agents registered with the Coordinator.

**Syntax:**
```bash
show_agent_registry
```

**Output:** JSON representation of the agent registry with agent details

---

#### `analyze_codebase <path> [focus]`
**Purpose:** Mastermind analyzes a codebase using its internal analyzer.

**Syntax:**
```bash
analyze_codebase <path_to_code> [focus_prompt]
```

**Examples:**
```bash
analyze_codebase ./tools
analyze_codebase ./core Focus on performance optimization opportunities
analyze_codebase ./agents Identify potential security vulnerabilities
```

**Process Flow:**
1. BaseGenAgent generates codebase documentation
2. Mastermind performs strategic analysis
3. Tool suite assessment based on findings
4. Results stored in belief system

---

#### `basegen <path>`
**Purpose:** Run the BaseGenAgent to generate Markdown documentation for a path.

**Syntax:**
```bash
basegen <path_to_analyze>
```

**Examples:**
```bash
basegen ./utils
basegen ./core
basegen ./tools
```

**Output:** JSON report of documentation generation process

### Identity Manager Commands

#### `id_list`
**Purpose:** List all cryptographic identities managed by the IDManager.

**Syntax:**
```bash
id_list
```

**Output:**
- Entity IDs
- Public addresses
- Identity status

---

#### `id_create <entity_id>`
**Purpose:** Create a new cryptographic identity for an entity.

**Syntax:**
```bash
id_create <entity_id>
```

**Examples:**
```bash
id_create test_agent_001
id_create monitoring_service
id_create backup_coordinator
```

**Output:**
- Public address
- Private key environment variable name
- Storage location

---

#### `id_deprecate <public_address> [entity_id_hint]`
**Purpose:** Deprecate (remove) a managed identity.

**Syntax:**
```bash
id_deprecate <public_address> [entity_id_hint]
```

**Examples:**
```bash
id_deprecate 0x1234567890abcdef
id_deprecate 0x1234567890abcdef old_test_agent
```

**Output:** Success/failure status of deprecation

### Coordinator Commands

#### `coord_query <question>`
**Purpose:** Send a query to the Coordinator's LLM for analysis.

**Syntax:**
```bash
coord_query <your_question>
```

**Examples:**
```bash
coord_query What is the current system health status?
coord_query Which components need immediate attention?
coord_query How can we improve overall system performance?
```

**Output:** LLM-generated response with analysis and recommendations

---

#### `coord_analyze [context]`
**Purpose:** Trigger Coordinator's comprehensive system analysis.

**Syntax:**
```bash
coord_analyze [optional_context]
```

**Examples:**
```bash
coord_analyze
coord_analyze Focus on memory usage patterns
coord_analyze Analyze recent error trends
```

**Output:** Comprehensive system analysis report

---

#### `coord_improve <component_id> [context]`
**Purpose:** Request Coordinator to improve a specific component.

**Syntax:**
```bash
coord_improve <component_id> [optional_context]
```

**Examples:**
```bash
coord_improve summarization_tool
coord_improve base_gen_agent Add better error handling
coord_improve memory_agent Optimize storage efficiency
```

**Process Flow:**
1. Component identification and analysis
2. Improvement suggestion generation
3. Implementation planning
4. Execution via appropriate tools
5. Results validation and reporting

---

#### `coord_backlog`
**Purpose:** Display the Coordinator's improvement backlog.

**Syntax:**
```bash
coord_backlog
```

**Output:**
- Backlog item IDs
- Priority levels
- Status information
- Target components
- Improvement suggestions
- Source and timestamps

---

#### `coord_process_backlog`
**Purpose:** Trigger Coordinator to process one actionable backlog item.

**Syntax:**
```bash
coord_process_backlog
```

**Process:**
1. Identifies next actionable item (PENDING status)
2. Checks for human approval requirements
3. Executes improvement process
4. Updates item status to IN_PROGRESS
5. Saves backlog state

---

#### `coord_approve <backlog_item_id>`
**Purpose:** Approve a Coordinator backlog item for processing.

**Syntax:**
```bash
coord_approve <backlog_item_id>
```

**Examples:**
```bash
coord_approve a1b2c3d4
coord_approve 12345678
```

---

#### `coord_reject <backlog_item_id>`
**Purpose:** Reject a Coordinator backlog item.

**Syntax:**
```bash
coord_reject <backlog_item_id>
```

**Examples:**
```bash
coord_reject a1b2c3d4
coord_reject 12345678
```

### Agent Lifecycle Commands

#### `agent_create <type> <id> [config_json]`
**Purpose:** Create a new agent with specified type and configuration.

**Syntax:**
```bash
agent_create <agent_type> <agent_id> [config_json]
```

**Examples:**
```bash
agent_create bdi_agent test_agent_001
agent_create monitoring_agent sys_monitor {"interval": 30}
agent_create analysis_agent code_analyzer {"target_path": "./core"}
```

**Process:**
1. Agent type validation
2. Configuration parsing
3. Agent instantiation
4. Identity creation
5. Coordinator registration

---

#### `agent_delete <id>`
**Purpose:** Delete an existing agent.

**Syntax:**
```bash
agent_delete <agent_id>
```

**Examples:**
```bash
agent_delete test_agent_001
agent_delete old_monitor
```

**Process:**
1. Agent lookup and validation
2. Graceful shutdown
3. Registry cleanup
4. Identity deprecation
5. Memory cleanup

---

#### `agent_list`
**Purpose:** List all registered agents.

**Syntax:**
```bash
agent_list
```

**Output:**
- Agent IDs
- Agent types
- Registration status

---

#### `agent_evolve <id> <directive>`
**Purpose:** Evolve a specific agent with a directive.

**Syntax:**
```bash
agent_evolve <agent_id> <directive>
```

**Examples:**
```bash
agent_evolve monitor_agent Improve performance monitoring capabilities
agent_evolve test_agent Add comprehensive error logging
```

---

#### `agent_sign <id> <message>`
**Purpose:** Sign a message using an agent's cryptographic identity.

**Syntax:**
```bash
agent_sign <agent_id> <message>
```

**Examples:**
```bash
agent_sign test_agent "System status: operational"
agent_sign monitor_agent "Alert: High CPU usage detected"
```

**Output:** Cryptographic signature of the message

### Utility Commands

#### `audit_gemini --test-all|--update-config`
**Purpose:** Audit Gemini models and update configuration.

**Syntax:**
```bash
audit_gemini --test-all
audit_gemini --update-config
```

**Options:**
- `--test-all`: Test all available Gemini models
- `--update-config`: Update configuration based on audit results

---

#### `help`
**Purpose:** Display comprehensive help information.

**Syntax:**
```bash
help
```

**Output:** Categorized list of all available commands with descriptions

---

#### `quit` / `exit`
**Purpose:** Gracefully shut down the CLI and all agents.

**Syntax:**
```bash
quit
exit
```

**Process:**
1. Graceful agent shutdown
2. Memory persistence
3. Connection cleanup
4. System exit

## BDI Integration

### Parameter Processing

The CLI integrates seamlessly with the BDI parameter processing system:

1. **Command Parsing**: Raw CLI input is parsed and structured
2. **Context Detection**: BDI agent detects component references and patterns
3. **Parameter Extraction**: Missing parameters are intelligently extracted
4. **Path Correction**: Automatic correction of common path issues
5. **Validation**: Parameter validation before execution
6. **Recovery**: Intelligent failure recovery with multiple strategies

### Example BDI Processing Flow

```bash
# User Input
coord_improve summarization_tool Add better error handling

# BDI Processing
1. Context Detection: "summarization_tool" pattern matched
2. Path Mapping: "summarization" → "tools" directory  
3. Parameter Injection: {"target_component": "summarization_tool", "analysis_context": "Add better error handling"}
4. Tool Execution: CoordinatorAgent.handle_user_input() with validated parameters
```

## Error Handling

### Common Error Scenarios

1. **Agent Unavailable**: Graceful degradation when agents are not initialized
2. **Invalid Parameters**: Clear error messages with usage examples
3. **Network Issues**: Retry mechanisms with exponential backoff
4. **Permission Errors**: Escalation to appropriate authorization levels
5. **Resource Constraints**: Intelligent resource management and queuing

### Error Recovery

- **Automatic Retry**: For transient failures
- **Alternative Strategies**: When primary approach fails
- **Escalation**: To higher-level agents when needed
- **Graceful Degradation**: Partial functionality when full operation is impossible

## Configuration

### Environment Setup

Required environment variables and configuration files:

- **LLM API Keys**: Gemini, OpenAI, etc.
- **Config Files**: `data/config/*.json`
- **Memory Storage**: `data/memory/` directory structure
- **Identity Storage**: `.env` file for private keys

### Performance Tuning

Key configuration parameters for optimal performance:

- **Memory Agent**: Logging levels and retention policies
- **BDI Agent**: Recovery strategies and retry limits
- **Coordinator**: Backlog processing intervals
- **Identity Manager**: Key generation and storage settings

## Best Practices

### Command Usage

1. **Start Simple**: Begin with basic commands before complex operations
2. **Use Context**: Provide clear context in directives and queries
3. **Monitor Status**: Regularly check agent status and backlogs
4. **Incremental Changes**: Make small, iterative improvements
5. **Validate Results**: Review command outputs and system responses

### System Management

1. **Regular Backups**: Backup identity and memory data
2. **Monitor Resources**: Track system resource usage
3. **Update Configurations**: Keep configuration files current
4. **Review Logs**: Regular log analysis for issues and patterns
5. **Test Changes**: Validate system behavior after modifications

## Troubleshooting

### Common Issues

| Issue | Symptoms | Solution |
|-------|----------|----------|
| Agent Not Available | "Agent not available" errors | Check agent initialization and configuration |
| Invalid Parameters | Parameter validation failures | Review command syntax and provide required parameters |
| Network Timeouts | LLM API call failures | Check network connectivity and API keys |
| Memory Issues | Out of memory errors | Review memory configuration and cleanup old data |
| Permission Denied | Access control failures | Verify identity and authorization settings |

### Debug Mode

Enable detailed logging for troubleshooting:

```python
# In config files
{
  "logging": {
    "level": "DEBUG",
    "detailed_tracing": true
  }
}
```

## Integration Examples

### Automated Workflows

```bash
# System Health Check Workflow
mastermind_status
show_agent_registry
coord_analyze System health assessment
coord_backlog
coord_process_backlog

# Component Improvement Workflow  
evolve Improve error handling across all components
coord_improve base_gen_agent Focus on performance optimization
agent_evolve test_agent Add comprehensive monitoring
```

### Monitoring and Maintenance

```bash
# Daily Maintenance Routine
id_list
coord_backlog
audit_gemini --test-all
analyze_codebase ./core Performance and security review
```

---

*This CLI reference is part of the mindX Augmentic Intelligence system. For related information, see [BDI Parameter Processing](bdi_parameter_processing.md) and [System Architecture](system_architecture.md).*
