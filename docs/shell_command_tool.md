# Shell Command Tool Documentation

## Overview

The `ShellCommandTool` provides a secure and controlled interface for executing shell commands within the mindX system. It enables agents to perform system operations while maintaining proper error handling and logging.

**File**: `tools/shell_command_tool.py`  
**Class**: `ShellCommandTool`  
**Version**: 1.0.0  
**Status**: ✅ Active

## Architecture

### Design Principles

1. **Async Execution**: Uses `asyncio` for non-blocking command execution
2. **Error Isolation**: Captures and returns errors without crashing
3. **Comprehensive Logging**: Logs all command executions and results
4. **Security**: Executes commands in controlled environment

### Core Components

```python
class ShellCommandTool(BaseTool):
    - logger: Logger instance for command tracking
    - execute(): Main execution method
```

## Usage

### Basic Execution

```python
from tools.shell_command_tool import ShellCommandTool

tool = ShellCommandTool()

# Execute a command
success, output = await tool.execute(command="ls -la")

if success:
    print(f"Command output: {output}")
else:
    print(f"Command failed: {output}")
```

### Response Format

The tool returns a tuple:
- **First element** (bool): `True` if command succeeded (return code 0), `False` otherwise
- **Second element** (str): Command output (stdout) on success, error message (stderr) on failure

## Features

### 1. Async Subprocess Execution

Uses `asyncio.create_subprocess_shell` for non-blocking execution:

```python
process = await asyncio.create_subprocess_shell(
    command,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE
)
```

### 2. Output Capture

- Captures both stdout and stderr
- Decodes output to UTF-8 strings
- Strips whitespace for clean output

### 3. Error Handling

- Catches subprocess errors
- Returns structured error messages
- Logs all errors with full context

## Security Considerations

### Current Implementation

1. **No Sandboxing**: Commands execute with full system permissions
2. **No Input Validation**: Command strings are not validated before execution
3. **No Command Whitelisting**: Any command can be executed

### Recommended Security Enhancements

1. **Command Whitelisting**: Only allow specific safe commands
2. **Path Validation**: Validate file paths in commands
3. **User Permissions**: Execute commands with limited user permissions
4. **Timeout Enforcement**: Add command execution timeouts
5. **Resource Limits**: Limit CPU and memory usage

## Integration

### With BDI Agents

```python
# In agent plan
plan = [
    {
        "action": "execute_shell_command",
        "command": "git status",
        "expected_result": "success"
    }
]
```

### With Other Tools

The ShellCommandTool is used by other tools like `TreeAgent` for file system operations.

## Limitations

### Current Limitations

1. **No Timeout**: Commands can run indefinitely
2. **No Resource Limits**: No CPU or memory constraints
3. **No Command Validation**: Any command string is accepted
4. **No Output Parsing**: Raw string output only
5. **No Command History**: No tracking of executed commands

### Recommended Improvements

1. **Add Timeout Support**: Prevent hanging commands
2. **Resource Limits**: Set CPU and memory limits
3. **Command Validation**: Validate commands before execution
4. **Output Parsing**: Parse structured output (JSON, YAML, etc.)
5. **Command History**: Track command execution history
6. **Retry Logic**: Automatic retry for transient failures

## Examples

### Simple Command

```python
success, output = await tool.execute("pwd")
# Returns: (True, "/home/user/mindX")
```

### Command with Error

```python
success, output = await tool.execute("nonexistent_command")
# Returns: (False, "Command 'nonexistent_command' not found")
```

### Complex Command

```python
success, output = await tool.execute("find . -name '*.py' | head -10")
# Returns: (True, "file1.py\nfile2.py\n...")
```

## Technical Details

### Dependencies

- `asyncio` - Async subprocess execution
- `core.bdi_agent.BaseTool` - Base tool class
- `utils.logging_config.get_logger` - Logging utility

### Error Handling

```python
try:
    process = await asyncio.create_subprocess_shell(...)
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        return True, stdout.decode().strip()
    else:
        return False, stderr.decode().strip()
except Exception as e:
    return False, f"An exception occurred: {e}"
```

## Future Enhancements

1. **Command Templates**: Pre-defined command templates
2. **Output Formatting**: Structured output parsing
3. **Command Chaining**: Support for command pipelines
4. **Environment Variables**: Configurable environment setup
5. **Working Directory**: Support for changing working directory
6. **Interactive Commands**: Support for interactive command execution



