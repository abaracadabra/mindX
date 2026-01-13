<<<<<<< Current (Your changes)
=======
"""
Tree Agent for mindX - Secure directory navigation and file system exploration.

Provides sandboxed directory navigation capabilities with command whitelisting
and comprehensive logging for security and auditing.
"""
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from tools.shell_command_tool import ShellCommandTool
from agents.core.bdi_agent import BaseTool
from utils.logging_config import get_logger

logger = get_logger(__name__)

class TreeAgent(BaseTool):
    """
    Secure directory navigation tool with sandboxed root path.
    
    Features:
    - Command whitelisting (ls, find only)
    - Sandboxed execution within root path
    - Comprehensive operation logging
    - Error handling and validation
    """
    
    ALLOWED_COMMANDS = ["ls", "find"]
    
    def __init__(self, root_path: str, config=None, **kwargs: Any):
        super().__init__(config=config, **kwargs)
        self.root_path = Path(root_path).resolve()
        
        # Validate root path exists
        if not self.root_path.exists():
            raise ValueError(f"Root path does not exist: {self.root_path}")
        if not self.root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {self.root_path}")
        
        # Initialize shell command tool
        self.shell = ShellCommandTool(config=self.config)
        
        self.logger.info(f"TreeAgent initialized with root path: {self.root_path}")

    def _validate_command(self, command: str) -> tuple[bool, Optional[str]]:
        """
        Validate command against whitelist.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not command or not isinstance(command, str):
            return False, "Command must be a non-empty string"
        
        command_stripped = command.strip()
        command_lower = command_stripped.lower()
        
        # Check if command starts with allowed command
        is_allowed = any(command_lower.startswith(cmd) for cmd in self.ALLOWED_COMMANDS)
        
        if not is_allowed:
            return False, f"Only '{', '.join(self.ALLOWED_COMMANDS)}' commands are allowed. Got: {command_stripped[:50]}"
        
        return True, None

    def _construct_sandboxed_command(self, command: str) -> str:
        """
        Construct command with root path sandboxing.
        
        Example:
            Input: "find . -name '*.py'"
            Output: "find /root/path . -name '*.py'"
        """
        parts = command.strip().split(" ", 1)
        cmd_base = parts[0]
        cmd_args = parts[1] if len(parts) > 1 else ""
        
        # Construct full command with root path
        if cmd_base == "find" and cmd_args:
            # For find, insert root path after 'find'
            full_command = f"{cmd_base} {self.root_path} {cmd_args}"
        elif cmd_base == "ls" and cmd_args:
            # For ls, append root path to arguments
            full_command = f"{cmd_base} {cmd_args} {self.root_path}"
        else:
            # Default: append root path
            full_command = f"{cmd_base} {self.root_path} {cmd_args}".strip()
        
        return full_command

    async def execute(self, command: str) -> Optional[str]:
        """
        Execute a directory navigation command.
        
        Args:
            command: Command to execute (must start with 'ls' or 'find')
            
        Returns:
            Command output on success, error message on failure
        """
        self.logger.info(f"TreeAgent executing command: {command[:100]}")
        
        # Validate command
        is_valid, validation_error = self._validate_command(command)
        if not is_valid:
            error_msg = f"Command validation failed: {validation_error}"
            self.logger.error(error_msg)
            return error_msg
        
        # Construct sandboxed command
        full_command = self._construct_sandboxed_command(command)
        self.logger.debug(f"Sandboxed command: {full_command}")
        
        try:
            # Execute via shell tool
            success, result = await self.shell.execute(command=full_command, working_dir=str(self.root_path))
            
            # Log operation
            if hasattr(self, 'memory_agent') and self.memory_agent and self.bdi_agent_ref:
                try:
                    await self.memory_agent.log_process(
                        process_name='tree_agent_execution',
                        data={
                            'command': command,
                            'full_command': full_command,
                            'success': success,
                            'result_preview': str(result)[:500] if result else None
                        },
                        metadata={
                            'agent_id': self.bdi_agent_ref.agent_id,
                            'tool_id': 'tree_agent',
                            'root_path': str(self.root_path)
                        }
                    )
                except Exception as log_error:
                    self.logger.warning(f"Failed to log tree agent operation: {log_error}")
            
            if success:
                self.logger.info(f"TreeAgent command executed successfully")
                return result
            else:
                error_msg = f"Command execution failed: {result}"
                self.logger.error(error_msg)
                return error_msg
                
        except Exception as e:
            error_msg = f"Exception during command execution: {e}"
            self.logger.error(error_msg, exc_info=True)
            return error_msg

    def get_root_path(self) -> Path:
        """Get the sandboxed root path."""
        return self.root_path

    def get_allowed_commands(self) -> List[str]:
        """Get list of allowed commands."""
        return self.ALLOWED_COMMANDS.copy()
>>>>>>> Incoming (Background Agent changes)
