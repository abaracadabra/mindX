# Agent Builder Agent Documentation

## Summary

The Agent Builder Agent builds new agents from participant prompts and agent requests. It processes prompts, analyzes requirements, and creates new agents using AgentFactoryTool with proper identity creation, Guardian validation, and registry registration. It notifies mindXagent when new agents are created so mindXagent can track them and understand their capabilities.

## Technical Explanation

The Agent Builder Agent implements:

- **Prompt Processing**: Parses participant prompts or agent requests for agent specifications
- **Agent Analysis**: Analyzes prompts to extract agent requirements (type, capabilities, roles)
- **Agent Creation**: Uses AgentFactoryTool to create new agents with full lifecycle management
- **Identity Creation**: Uses IDManagerAgent to create cryptographic identity for new agents
- **Registry Registration**: Uses RegistryManagerTool to register new agents in official registry
- **mindXagent Notification**: Notifies mindXagent when new agents are created
- **Request Tracking**: Tracks all build requests and results

### Architecture

- **Type**: `agent_builder`
- **Layer**: Orchestration layer
- **Integration**: Works with AgentFactoryTool, IDManagerAgent, RegistryManagerTool, GuardianAgent
- **Pattern**: Agent creation and registration service

### Core Components

1. **Agent Factory Tool Integration**: Uses AgentFactoryTool for agent creation
2. **Registry Manager Tool Integration**: Registers agents in official registry
3. **ID Manager Integration**: Creates identities for new agents
4. **Guardian Integration**: Validates new agents through Guardian
5. **mindXagent Integration**: Notifies mindXagent about new agents
6. **Request Tracking**: Maintains history of build requests and results

## Usage

```python
from agents.orchestration.agent_builder_agent import AgentBuilderAgent

# Get Agent Builder Agent instance
builder = await AgentBuilderAgent.get_instance(
    agent_id="agent_builder",
    config=config,
    memory_agent=memory_agent,
    belief_system=belief_system,
    coordinator_agent=coordinator_agent,
    guardian_agent=guardian_agent,
    mindx_agent=mindx_agent
)

# Build agent from participant prompt
result = await builder.build_agent_from_prompt(
    prompt="Create an agent that analyzes code quality and generates improvement suggestions",
    source="participant_prompt"
)

if result.success:
    print(f"Agent created: {result.agent_id}")
    print(f"Metadata: {result.agent_metadata}")
else:
    print(f"Error: {result.error}")
```

## Key Methods

### Agent Building

- `build_agent_from_prompt(prompt, source, agent_type)`: Build agent from prompt/request
- `_analyze_prompt(prompt, agent_type_hint)`: Analyze prompt to extract specifications
- `_generate_agent_id(agent_spec)`: Generate unique agent ID
- `_register_agent_in_registry(agent_id, metadata, spec)`: Register agent in registry
- `_notify_mindx_agent(agent_id, metadata, spec)`: Notify mindXagent about new agent

## Agent Creation Process

1. **Prompt Analysis**: Analyze prompt to extract agent specifications
2. **Agent ID Generation**: Generate unique agent ID
3. **Identity Creation**: Create cryptographic identity via IDManagerAgent
4. **Guardian Validation**: Validate through GuardianAgent
5. **Agent Creation**: Use AgentFactoryTool to create agent code and workspace
6. **Registry Registration**: Register agent in official registry via RegistryManagerTool
7. **mindXagent Notification**: Notify mindXagent so it can track the new agent
8. **Result Tracking**: Save build request and result to history

## Integration Points

- **AgentFactoryTool**: For creating agents with full lifecycle management
- **IDManagerAgent**: For creating cryptographic identities
- **GuardianAgent**: For security validation
- **RegistryManagerTool**: For registry registration
- **CoordinatorAgent**: For agent registration in coordinator
- **mindXagent**: For notification and tracking of new agents

## Prompt Analysis

The agent analyzes prompts to extract:

- **Agent Type**: orchestration, core, learning, monitoring, specialized
- **Capabilities**: List of capabilities based on keywords
- **Roles**: Agent roles and responsibilities
- **Description**: Full description from prompt

## File Location

- **Path**: `agents/orchestration/agent_builder_agent.py`
- **Documentation**: `docs/agent_builder_agent.md`

## NFT Metadata

- **Type**: `agent_builder`
- **Complexity**: 0.90
- **NFT Ready**: ✅ iNFT, dNFT, IDNFT

## Integration with mindXagent

When a new agent is created:

1. Agent Builder Agent creates the agent
2. Agent Builder Agent registers it in registry
3. Agent Builder Agent notifies mindXagent
4. mindXagent adds new agent to knowledge base
5. mindXagent analyzes new agent's capabilities
6. mindXagent updates agent relationship graph
7. mindXagent monitors new agent's performance

---

**Last Updated**: 2026-01-13  
**Status**: ✅ Active  
**Version**: 1.0.0
