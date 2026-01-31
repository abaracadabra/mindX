# mindx/tools/shell_command_tool.py
"""
Shell Command Tool for mindX agents.

Provides secure and controlled execution of shell commands with timeout support,
error handling, and execution history tracking.
"""
import asyncio
from typing import Dict, Any, Tuple, Optional, List
from datetime import datetime
from pathlib import Path

from agents.core.bdi_agent import BaseTool
from utils.logging_config import get_logger
from utils.config import Config

logger = get_logger(__name__)

class ShellCommandTool(BaseTool):
    """
    A tool for executing shell commands with enhanced security and monitoring.
    
    Features:
    - Async subprocess execution
    - Configurable timeout support
    - Command execution history
    - Comprehensive error handling
    - Output size limits
    """
    
    def __init__(self, config: Optional[Config] = None, **kwargs: Any):
        super().__init__(config=config, **kwargs)
        
        # Configuration
        self.default_timeout = self.config.get("tools.shell_command.timeout_seconds", 300)  # 5 minutes default
        self.max_output_size = self.config.get("tools.shell_command.max_output_size", 10 * 1024 * 1024)  # 10MB default
        self.max_history_size = self.config.get("tools.shell_command.max_history_size", 100)
        
        # Command execution history
        self.command_history: List[Dict[str, Any]] = []
        
        # Allowed command patterns (if configured)
        self.allowed_patterns = self.config.get("tools.shell_command.allowed_patterns", [])
        self.blocked_patterns = self.config.get("tools.shell_command.blocked_patterns", [
            "rm -rf /", "format", "mkfs", "dd if=", "shutdown", "reboot"
        ])
        
        self.logger.info(f"ShellCommandTool initialized. Timeout: {self.default_timeout}s, Max output: {self.max_output_size} bytes")

    def _validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validates command against security patterns.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not command or not isinstance(command, str):
            return False, "Command must be a non-empty string"
        
        command_lower = command.lower().strip()
        
        # Check blocked patterns
        for blocked in self.blocked_patterns:
            if blocked.lower() in command_lower:
                return False, f"Command contains blocked pattern: {blocked}"
        
        # Check allowed patterns (if whitelist is configured)
        if self.allowed_patterns:
            if not any(pattern.lower() in command_lower for pattern in self.allowed_patterns):
                return False, f"Command does not match any allowed pattern"
        
        return True, None

    def _truncate_output(self, output: str, max_size: int) -> str:
        """Truncate output if it exceeds max size."""
        if len(output.encode('utf-8')) > max_size:
            truncated = output[:max_size//2]
            return f"{truncated}\n... (output truncated, {len(output)} bytes total) ..."
        return output

    async def execute(self, command: str, timeout: Optional[float] = None, 
                     working_dir: Optional[str] = None, **kwargs: Any) -> Tuple[bool, str]:
        """
        Executes a shell command with enhanced features.

        Args:
            command: The shell command to execute
            timeout: Optional timeout in seconds (default: from config)
            working_dir: Optional working directory for command execution
            **kwargs: Additional arguments (for BaseTool compatibility)

        Returns:
            A tuple containing:
            - bool: True if command succeeded (return code 0), False otherwise
            - str: Command output (stdout) on success, error message (stderr) on failure
        """
        start_time = datetime.now()
        execution_timeout = timeout if timeout is not None else self.default_timeout
        
        self.logger.info(f"Executing shell command: {command[:100]}...")
        
        # Validate command
        is_valid, validation_error = self._validate_command(command)
        if not is_valid:
            error_msg = f"Command validation failed: {validation_error}"
            self.logger.error(error_msg)
            self._record_history(command, False, 0.0, error_msg)
            return False, error_msg
        
        try:
            # Prepare environment
            env = kwargs.get('env', None)
            cwd = Path(working_dir) if working_dir else None
            
            # Create subprocess with timeout
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env
            )
            
            # Wait for completion with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=execution_timeout
                )
            except asyncio.TimeoutError:
                # Kill the process if it times out
                process.kill()
                await process.wait()
                error_msg = f"Command timed out after {execution_timeout} seconds"
                self.logger.error(error_msg)
                execution_time = (datetime.now() - start_time).total_seconds()
                self._record_history(command, False, execution_time, error_msg)
                return False, error_msg

            # Decode output
            try:
                stdout_text = stdout.decode('utf-8', errors='replace').strip() if stdout else ""
                stderr_text = stderr.decode('utf-8', errors='replace').strip() if stderr else ""
            except Exception as decode_error:
                error_msg = f"Failed to decode command output: {decode_error}"
                self.logger.error(error_msg)
                execution_time = (datetime.now() - start_time).total_seconds()
                self._record_history(command, False, execution_time, error_msg)
                return False, error_msg

            execution_time = (datetime.now() - start_time).total_seconds()

            if process.returncode == 0:
                # Success - truncate if needed
                output = self._truncate_output(stdout_text, self.max_output_size)
                self.logger.info(f"Command executed successfully in {execution_time:.2f}s. Output length: {len(output)} chars")
                self._record_history(command, True, execution_time, output[:200])
                return True, output
            else:
                # Failure - return stderr or stdout
                error_message = stderr_text if stderr_text else stdout_text or f"Command failed with return code {process.returncode}"
                self.logger.error(f"Command failed with return code {process.returncode} in {execution_time:.2f}s. Error: {error_message[:200]}")
                self._record_history(command, False, execution_time, error_message[:200])
                return False, error_message
                
        except asyncio.CancelledError:
            error_msg = "Command execution was cancelled"
            self.logger.warning(error_msg)
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_history(command, False, execution_time, error_msg)
            return False, error_msg
            
        except Exception as e:
            error_msg = f"An exception occurred while executing the command: {e}"
            self.logger.error(error_msg, exc_info=True)
            execution_time = (datetime.now() - start_time).total_seconds()
            self._record_history(command, False, execution_time, error_msg)
            return False, error_msg

    def _record_history(self, command: str, success: bool, execution_time: float, 
                        result: str) -> None:
        """Record command execution in history."""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command[:200],  # Truncate long commands
            "success": success,
            "execution_time": execution_time,
            "result_preview": result[:200]  # Preview only
        }
        
        self.command_history.append(history_entry)
        
        # Limit history size
        if len(self.command_history) > self.max_history_size:
            self.command_history = self.command_history[-self.max_history_size:]

    def get_command_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get command execution history.
        
        Args:
            limit: Maximum number of entries to return (default: all)
            
        Returns:
            List of command history entries
        """
        if limit:
            return self.command_history[-limit:]
        return self.command_history.copy()

    def clear_history(self) -> None:
        """Clear command execution history."""
        self.command_history.clear()
        self.logger.info("Command history cleared")
