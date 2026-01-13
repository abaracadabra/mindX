# A2A Tool

## Summary

The A2A (Agent-to-Agent) Tool enables standardized agent-to-agent communication following the A2A protocol. It provides capabilities for agent discovery, message passing, authentication, and interoperability with external A2A-compatible systems.

## Technical Explanation

The A2A Tool follows mindX doctrine:
- **Memory is infrastructure**: All A2A communications are logged to memory
- **Standardized protocols**: Enables interoperability with external systems
- **Cryptographic verification**: Ensures trust through signatures
- **Discovery mechanism**: Agents can discover and communicate with each other

### Architecture

- **Storage**: A2A data stored in `data/a2a/` with agent cards and message history
- **Protocol Support**: A2A 2.0 protocol compliance
- **Message Types**: Request, Response, Notification, Discovery, Capability Query, Action
- **Agent Cards**: Model cards for agent discovery and capability description

### Features

- **Agent Registration**: Register agents with A2A protocol
- **Agent Discovery**: Discover available agents by query or capability
- **Message Passing**: Send and receive messages between agents
- **Capability Queries**: Query agent capabilities
- **Action Execution**: Request actions from other agents
- **Discovery Endpoint**: Generate `.well-known/agents.json` for web discovery

## Usage

### Registering an Agent

```python
from tools.a2a_tool import A2ATool
from agents.memory_agent import MemoryAgent

memory_agent = MemoryAgent()
a2a_tool = A2ATool(memory_agent=memory_agent)

result = await a2a_tool.execute(
    operation="register_agent",
    agent_id="my_agent_123",
    name="My Agent",
    description="A helpful AI agent",
    capabilities=["text_generation", "code_analysis", "data_processing"],
    endpoint="https://mindx.internal/my_agent_123/a2a",
    public_key="0x...",
    version="1.0.0"
)

agent_card = result["agent_card"]
```

### Discovering Agents

```python
# Discover all agents
result = await a2a_tool.execute(operation="discover_agents")

# Discover by query
result = await a2a_tool.execute(
    operation="discover_agents",
    query="code analysis"
)

# Discover by capability
result = await a2a_tool.execute(
    operation="discover_agents",
    capability="text_generation"
)
```

### Sending Messages

```python
result = await a2a_tool.execute(
    operation="send_message",
    from_agent="agent_1",
    to_agent="agent_2",
    message_type="request",
    payload={
        "action": "analyze_code",
        "code": "...",
        "language": "python"
    }
)

message_id = result["message_id"]
```

### Receiving Messages

```python
result = await a2a_tool.execute(
    operation="receive_message",
    agent_id="agent_2"
)

message = result["message"]
```

### Querying Capabilities

```python
result = await a2a_tool.execute(
    operation="query_capabilities",
    agent_id="my_agent_123"
)

capabilities = result["capabilities"]
```

### Executing Actions

```python
result = await a2a_tool.execute(
    operation="execute_action",
    from_agent="agent_1",
    to_agent="agent_2",
    action="process_data",
    parameters={
        "data": "...",
        "format": "json"
    }
)
```

### Generating Discovery Endpoint

```python
result = await a2a_tool.execute(
    operation="generate_discovery_endpoint",
    base_url="https://mindx.internal"
)

discovery_url = result["discovery_endpoint"]
# Returns: https://mindx.internal/.well-known/agents.json
```

## Operations

- `register_agent`: Register an agent with A2A protocol
- `discover_agents`: Discover available agents
- `send_message`: Send a message to another agent
- `receive_message`: Receive and process a message
- `query_capabilities`: Query an agent's capabilities
- `execute_action`: Request an action from another agent
- `get_agent_card`: Get agent card for an agent
- `list_agents`: List all registered agents
- `generate_discovery_endpoint`: Generate `.well-known/agents.json`

## Integration

The A2A Tool integrates with:
- **Memory Agent**: All communications logged to memory
- **Coordinator Agent**: Automatic agent registration
- **External Systems**: A2A-compatible systems can discover and communicate

## File Structure

```
data/a2a/
├── agent_cards_registry.json    # Agent cards registry
├── messages_registry.json       # Message history
├── agent_cards/                 # Individual agent cards
│   └── {agent_id}.json
├── messages/                     # Individual messages
│   └── {message_id}.json
└── .well-known/                 # Discovery endpoint
    └── agents.json
```

## Protocol Details

### Message Format

```json
{
  "message_id": "msg_123",
  "from_agent": "agent_1",
  "to_agent": "agent_2",
  "message_type": "request",
  "protocol_version": "2.0",
  "timestamp": "2024-01-01T00:00:00Z",
  "payload": {...},
  "signature": "...",
  "metadata": {...}
}
```

### Agent Card Format

```json
{
  "agent_id": "agent_123",
  "name": "Agent Name",
  "description": "Agent description",
  "version": "1.0.0",
  "capabilities": ["cap1", "cap2"],
  "endpoint": "https://...",
  "public_key": "0x...",
  "signature": "..."
}
```

## Use Cases

1. **Inter-Agent Communication**: Agents communicate with each other
2. **Capability Discovery**: Find agents with specific capabilities
3. **Action Delegation**: Delegate tasks to specialized agents
4. **External Integration**: Connect with A2A-compatible systems
5. **Agent Marketplace**: Enable agent discovery and interaction



