# Audit and Improve Tool Documentation

## Overview

The `AuditAndImproveTool` provides intelligent code auditing and improvement capabilities using LLM-powered analysis. It uses BaseGenAgent summaries as context for comprehensive code understanding, with fallback to raw file content for resilience.

**File**: `tools/audit_and_improve_tool.py`  
**Class**: `AuditAndImproveTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Resilient Context**: Uses BaseGenAgent summary, falls back to raw code
2. **LLM-Powered**: Leverages LLM for intelligent code analysis
3. **Persona-Based**: Uses AutoMINDX personas for specialized analysis
4. **Comprehensive Logging**: Logs all operations for audit trail
5. **Structured Output**: Returns structured improvement results

### Core Components

```python
class AuditAndImproveTool(BaseTool):
    - memory_agent: MemoryAgent - For workspace and logging
    - base_gen_agent: BaseGenAgent - For codebase summaries
    - automindx_agent: AutoMINDXAgent - For personas
    - llm_handler: LLMHandlerInterface - For code generation
```

## Workflow

### Step 1: Generate Context (Primary)
Attempts to generate BaseGenAgent summary for comprehensive context:
- Generates markdown summary of codebase
- Provides rich context for LLM analysis
- Falls back if generation fails

### Step 2: Fallback to Raw Code
If BaseGenAgent fails:
- Reads raw file content directly
- Provides basic context for analysis
- Ensures tool remains functional

### Step 3: Apply Persona
Retrieves specialized persona from AutoMINDX:
- Uses "AUDIT_AND_IMPROVE" persona
- Provides specialized analysis perspective
- Ensures consistent improvement quality

### Step 4: Generate Improvements
Uses LLM to generate improved code:
- JSON mode for structured output
- Includes summary and limitations
- Saves improved code to workspace

### Step 5: Log Results
Logs operation for audit trail:
- Target path and prompt
- Summary and limitations
- Context source used
- Output path

## Usage

### Basic Audit and Improve

```python
from tools.audit_and_improve_tool import AuditAndImproveTool
from agents.memory_agent import MemoryAgent
from agents.base_gen_agent import BaseGenAgent
from agents.automindx_agent import AutoMINDXAgent
from llm.llm_interface import LLMHandlerInterface

tool = AuditAndImproveTool(
    memory_agent=memory_agent,
    base_gen_agent=base_gen_agent,
    automindx_agent=automindx_agent,
    llm_handler=llm_handler
)

# Audit and improve code
result = await tool.execute(
    target_path="/path/to/file.py",
    prompt="Improve error handling and add type hints"
)
```

### Response Format

**Success**:
```python
{
    "status": "SUCCESS",
    "status_details": "OK" | "DEGRADED_CONTEXT_FALLBACK",
    "summary": "Improvement summary",
    "limitations": "Known limitations",
    "output_path": "/path/to/improved_file.py",
    "context_used": "BaseGen Summary: ..." | "Raw File Content (Fallback): ..."
}
```

**Error**:
```python
{
    "status": "ERROR",
    "message": "Error description"
}
```

## Features

### 1. Resilient Context Generation

- **Primary**: BaseGenAgent summary (comprehensive)
- **Fallback**: Raw file content (basic)
- **Status Tracking**: Indicates which context was used

### 2. Persona-Based Analysis

Uses specialized personas for:
- Code quality analysis
- Best practices enforcement
- Architecture improvements
- Security enhancements

### 3. Structured Output

LLM generates JSON with:
- `updated_code`: Improved code
- `summary`: What was improved
- `limitations`: Known limitations

### 4. Workspace Management

- Creates dedicated workspace directory
- Saves improved code with naming convention
- Maintains audit trail

## Limitations

### Current Limitations

1. **Single File**: Processes one file at a time
2. **No Multi-File Context**: Doesn't consider related files
3. **No Testing**: Doesn't verify improvements work
4. **No Version Control**: Doesn't integrate with Git
5. **No Incremental**: Always generates full file

### Recommended Improvements

1. **Multi-File Analysis**: Consider related files
2. **Incremental Improvements**: Apply specific changes only
3. **Test Generation**: Generate tests for improvements
4. **Git Integration**: Create branches for improvements
5. **Review Process**: Human review before applying
6. **Diff Generation**: Show what changed
7. **Batch Processing**: Process multiple files

## Integration

### With BaseGenAgent

Uses BaseGenAgent for rich context:
```python
summary_report = self.base_gen_agent.generate_markdown_summary(
    root_path_str=target_path,
    output_file_str=str(workspace_dir / f"analysis_context_{Path(target_path).name}.md")
)
```

### With AutoMINDXAgent

Uses personas for specialized analysis:
```python
persona = self.automindx_agent.get_persona("AUDIT_AND_IMPROVE")
```

### With MemoryAgent

Logs all operations:
```python
await self.memory_agent.log_process(
    "audit_and_improve_tool_execution",
    log_data,
    {"agent_id": "audit_and_improve_tool"}
)
```

## Examples

### Improve Error Handling

```python
result = await tool.execute(
    target_path="tools/my_tool.py",
    prompt="Add comprehensive error handling with try-except blocks and proper logging"
)
```

### Add Type Hints

```python
result = await tool.execute(
    target_path="utils/helpers.py",
    prompt="Add type hints to all functions and improve docstrings"
)
```

### Refactor for Performance

```python
result = await tool.execute(
    target_path="core/processor.py",
    prompt="Optimize for performance: use async where appropriate, add caching, reduce complexity"
)
```

## Technical Details

### Dependencies

- `tools.base_gen_agent.BaseGenAgent`: Context generation
- `agents.automindx_agent.AutoMINDXAgent`: Persona management
- `llm.llm_interface.LLMHandlerInterface`: Code generation
- `agents.memory_agent.MemoryAgent`: Workspace and logging
- `core.bdi_agent.BaseTool`: Base tool class

### LLM Prompt Structure

```python
full_prompt = (
    f"{persona}\n\n"
    f"**Improvement Request:** {prompt}\n\n"
    f"**Context from {context_source}:**\n```\n{context_content}\n```"
)
```

### JSON Response Format

```json
{
    "updated_code": "...",
    "summary": "...",
    "limitations": "..."
}
```

## Future Enhancements

1. **Multi-File Context**: Analyze related files together
2. **Incremental Changes**: Apply specific improvements only
3. **Test Generation**: Auto-generate tests for improvements
4. **Code Review**: Human-in-the-loop review process
5. **Diff Visualization**: Show changes clearly
6. **Batch Mode**: Process multiple files
7. **Custom Personas**: User-defined analysis personas
8. **Integration Testing**: Verify improvements work



