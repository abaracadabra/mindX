# MCP Tool

## Summary

The MCP (Model Context Protocol) Tool enables structured context provision for agents. MCP allows agents to receive rich, structured context about their environment, available tools, and action requirements, enabling better decision-making and action execution.

## Technical Explanation

The MCP Tool follows mindX doctrine:
- **Memory is infrastructure**: MCP contexts are stored and versioned
- **Structured context**: Enables better agent actions through rich context
- **Protocol-based**: Ensures interoperability and standardization
- **Tool definitions**: Provides structured tool descriptions for agents

### Architecture

- **Storage**: MCP data stored in `data/mcp/` with contexts and tool definitions
- **Protocol Support**: MCP 2.0 protocol compliance
- **Context Types**: Tool definitions, action context, environment state, capability descriptions, execution parameters, result schemas
- **Tool Registry**: Structured tool definitions with schemas and examples

### Features

- **Context Creation**: Create structured contexts for agents
- **Tool Registration**: Register tools with full definitions
- **Context Retrieval**: Get context for actions or tools
- **Schema Support**: JSON schemas for parameters and results
- **Example Support**: Examples for tool usage

## Usage

### Creating a Context

```python
from tools.mcp_tool import MCPTool
from agents.memory_agent import MemoryAgent

memory_agent = MemoryAgent()
mcp_tool = MCPTool(memory_agent=memory_agent)

result = await mcp_tool.execute(
    operation="create_context",
    context_type="action_context",
    agent_id="my_agent",
    action_id="analyze_code",
    context_data={
        "code": "...",
        "language": "python",
        "requirements": ["syntax_check", "type_check"]
    },
    schema={
        "type": "object",
        "properties": {
            "code": {"type": "string"},
            "language": {"type": "string"},
            "requirements": {"type": "array"}
        }
    }
)

context_id = result["context_id"]
```

### Registering a Tool

```python
result = await mcp_tool.execute(
    operation="register_tool",
    tool_id="code_analyzer",
    name="Code Analyzer",
    description="Analyzes code for issues and improvements",
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Code to analyze"},
            "language": {"type": "string", "description": "Programming language"}
        },
        "required": ["code", "language"]
    },
    returns={
        "type": "object",
        "properties": {
            "issues": {"type": "array"},
            "suggestions": {"type": "array"}
        }
    },
    examples=[
        {
            "input": {"code": "def hello():", "language": "python"},
            "output": {"issues": [], "suggestions": ["Add docstring"]}
        }
    ]
)
```

### Getting Tool Context

```python
result = await mcp_tool.execute(
    operation="get_tool_context",
    agent_id="my_agent",
    tool_id="code_analyzer"
)

context = result["context"]
# Contains tool definition, parameters, examples, etc.
```

### Getting Action Context

```python
result = await mcp_tool.execute(
    operation="get_action_context",
    agent_id="my_agent",
    action_id="analyze_code"
)

context = result["context"]
# Contains action-specific context data
```

### Listing Contexts

```python
# List all contexts
result = await mcp_tool.execute(operation="list_contexts")

# Filter by agent
result = await mcp_tool.execute(
    operation="list_contexts",
    agent_id="my_agent"
)

# Filter by type
result = await mcp_tool.execute(
    operation="list_contexts",
    context_type="tool_definition"
)
```

## Operations

- `create_context`: Create a new MCP context
- `get_context`: Get context by ID
- `update_context`: Update an existing context
- `delete_context`: Delete a context
- `list_contexts`: List all contexts (with filters)
- `register_tool`: Register a tool definition
- `get_tool_definition`: Get tool definition
- `list_tools`: List all tool definitions
- `get_action_context`: Get context for an action
- `get_tool_context`: Get context for a tool

## Context Types

- `tool_definition`: Tool definitions with schemas
- `action_context`: Context for specific actions
- `environment_state`: Current environment state
- `capability_description`: Capability descriptions
- `execution_parameters`: Execution parameters
- `result_schema`: Result schemas

## Integration

The MCP Tool integrates with:
- **BDI Agents**: Provides context for action planning
- **Tool Registry**: Tool definitions align with registry
- **Memory Agent**: All contexts stored in memory
- **Action Execution**: Contexts guide action execution

## File Structure

```
data/mcp/
├── contexts_registry.json           # Contexts registry
├── tool_definitions_registry.json   # Tool definitions registry
├── contexts/                         # Individual contexts
│   └── {context_id}.json
└── tool_definitions/                # Individual tool definitions
    └── {tool_id}.json
```

## Use Cases

1. **Action Planning**: Provide context for agent action planning
2. **Tool Discovery**: Help agents understand available tools
3. **Parameter Validation**: Validate action parameters using schemas
4. **Result Interpretation**: Understand expected result formats
5. **Environment Awareness**: Provide environment state to agents
6. **Capability Matching**: Match agent capabilities with requirements



