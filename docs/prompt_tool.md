# Prompt Tool

## Summary

The Prompt Tool enables the management, storage, and execution of prompts within the mindX system. Prompts are treated as first-class infrastructure, stored in memory, and can be versioned, shared, and executed by agents.

## Technical Explanation

The Prompt Tool follows mindX doctrine:
- **Memory is infrastructure**: Prompts are persisted in memory and queryable
- **Prompts are executable interfaces**: Prompts can be executed with variable substitution
- **Versioning and lineage**: Prompts can be versioned and tracked through their evolution

### Architecture

- **Storage**: Prompts are stored in `data/prompts/` with a registry in `prompt_registry.json`
- **Metadata**: Each prompt has rich metadata including type, category, tags, version, and usage statistics
- **Memory Integration**: All prompt operations are logged to the Memory Agent for auditability

### Prompt Types

- `system`: System-level prompts (inception, core instructions)
- `agent`: Agent-specific prompts
- `user`: User-defined prompts
- `template`: Reusable prompt templates with variables
- `inception`: Platform initialization prompts
- `instruction`: Instruction sets for agents

### Categories

Prompts are organized by mindX layers:
- `marketing`: Marketing and narrative prompts
- `community`: Community and governance prompts
- `development`: Development and deployment prompts
- `cognition`: Cognitive and reasoning prompts
- `execution`: Execution and orchestration prompts
- `governance`: Governance and alignment prompts

## Usage

### Creating a Prompt

```python
from tools.prompt_tool import PromptTool
from agents.memory_agent import MemoryAgent

memory_agent = MemoryAgent()
prompt_tool = PromptTool(memory_agent=memory_agent)

result = await prompt_tool.execute(
    operation="create",
    name="mindX Inception",
    content="You are mindX, an augmentic deployment platform...",
    description="Core mindX inception prompt",
    prompt_type="inception",
    category="governance",
    tags=["core", "inception", "platform"],
    author="system"
)
```

### Retrieving a Prompt

```python
result = await prompt_tool.execute(
    operation="get",
    prompt_id="prompt_id_here"
)

content = result["content"]
metadata = result["metadata"]
```

### Executing a Prompt with Variables

```python
result = await prompt_tool.execute(
    operation="execute",
    prompt_id="template_prompt_id",
    variables={
        "agent_name": "MyAgent",
        "task": "Analyze data"
    }
)

executed_content = result["executed_content"]
```

### Searching Prompts

```python
result = await prompt_tool.execute(
    operation="search",
    query="inception",
    search_content=True
)

prompts = result["results"]
```

### Ingesting from External Sources

```python
result = await prompt_tool.execute(
    operation="ingest",
    name="AgenticPlace Prompt",
    content="...",
    source="AgenticPlace",
    prompt_type="agent",
    category="development"
)
```

### Versioning Prompts

```python
result = await prompt_tool.execute(
    operation="version",
    prompt_id="original_prompt_id",
    new_content="Updated prompt content...",
    version_notes="Added new instructions"
)
```

## Operations

- `create`: Create a new prompt
- `get`: Retrieve a prompt by ID
- `update`: Update an existing prompt
- `delete`: Delete a prompt
- `list`: List all prompts (with optional filters)
- `execute`: Execute a prompt with variable substitution
- `search`: Search prompts by content or metadata
- `version`: Create a new version of a prompt
- `ingest`: Ingest a prompt from external source

## Integration

The Prompt Tool integrates with:
- **Memory Agent**: All operations are logged to memory
- **BDI Agents**: Agents can retrieve and execute prompts
- **AgenticPlace**: Prompts can be ingested from external sources

## File Structure

```
data/prompts/
├── prompt_registry.json    # Metadata registry
└── {prompt_id}.prompt      # Individual prompt files
```



