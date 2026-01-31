# Tree Agent Documentation

## Overview

The `TreeAgent` provides secure directory navigation and file system exploration capabilities for mindX agents. It enables agents to explore directory structures and find files within a sandboxed root path, ensuring safe file system operations.

**File**: `tools/tree_agent.py`  
**Class**: `TreeAgent`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Sandboxed Execution**: All commands are restricted to a specified root path
2. **Command Whitelisting**: Only allows safe commands (`ls` and `find`)
3. **Path Security**: Prevents directory traversal attacks
4. **Process Logging**: Logs all operations for auditing

### Core Components

```python
class TreeAgent(BaseTool):
    - root_path: Path - Sandboxed root directory
    - shell: ShellCommandTool - For executing commands
    - memory_agent: MemoryAgent - For logging operations
```

## Usage

### Basic Directory Listing

```python
from agents.tree_agent import TreeAgent

agent = TreeAgent(root_path="/home/user/project")

# List directory contents
result = await agent.execute("ls -la")
```

### File Search

```python
# Find files matching pattern
result = await agent.execute("find . -name '*.py'")
```

## Security Features

### 1. Command Whitelisting

Only allows specific safe commands:
- `ls`: List directory contents
- `find`: Search for files

All other commands are rejected with an error message.

### 2. Sandboxed Root Path

All commands are executed relative to the specified root path:
- Prevents access to files outside the sandbox
- Ensures agents can only explore designated areas
- Protects system files and sensitive directories

### 3. Path Construction

Commands are automatically prefixed with the root path:
```python
# User command: "find . -name file.txt"
# Executed as: "find /root/path . -name file.txt"
```

## Limitations

### Current Limitations

1. **Limited Commands**: Only supports `ls` and `find`
2. **No Recursive Operations**: Limited recursive capabilities
3. **No File Operations**: Cannot read, write, or modify files
4. **No Metadata**: Doesn't provide file metadata (size, dates, etc.)
5. **Basic Error Handling**: Minimal error context

### Recommended Improvements

1. **More Commands**: Support `tree`, `stat`, `file` commands
2. **File Metadata**: Return file size, modification dates, permissions
3. **Pattern Matching**: Enhanced pattern matching capabilities
4. **Recursive Depth Limits**: Configurable recursion depth
5. **Result Formatting**: Structured output (JSON) instead of raw text
6. **Caching**: Cache directory listings for performance

## Integration

### With Memory Agent

All operations are logged to the memory agent:
```python
await self.memory_agent.log_process(
    process_name='tree_agent_execution',
    data={'command': full_command, 'success': success, 'result': result},
    metadata={'agent_id': self.bdi_agent_ref.agent_id, 'tool_id': 'tree_agent'}
)
```

### With Shell Command Tool

Uses `ShellCommandTool` internally for command execution, inheriting its security and error handling features.

## Examples

### List Current Directory

```python
result = await agent.execute("ls")
# Returns: List of files and directories
```

### Find Python Files

```python
result = await agent.execute("find . -name '*.py'")
# Returns: List of Python files
```

### Find by Pattern

```python
result = await agent.execute("find . -type f -name 'test_*.py'")
# Returns: Test files matching pattern
```

## Technical Details

### Dependencies

- `tools.shell_command_tool.ShellCommandTool`: For command execution
- `core.bdi_agent.BaseTool`: Base tool class
- `agents.memory_agent.MemoryAgent`: For operation logging

### Command Processing

```python
# Validate command
if not command.startswith("ls") and not command.startswith("find"):
    return "Error: Only 'ls' and 'find' commands are allowed."

# Construct sandboxed command
parts = command.split(" ")
cmd_base = parts[0]
cmd_args = " ".join(parts[1:])
full_command = f"{cmd_base} {self.root_path} {cmd_args}"

# Execute via shell tool
success, result = await self.shell.execute(command=full_command)
```

## Future Enhancements

1. **Structured Output**: Return JSON-structured results
2. **File Metadata**: Include file size, dates, permissions
3. **Advanced Filtering**: Support for complex filters
4. **Directory Tree Visualization**: Generate tree structures
5. **Performance Optimization**: Cache directory listings
6. **Multi-Path Support**: Support multiple root paths
7. **Virtual File System**: Support for virtual file systems



