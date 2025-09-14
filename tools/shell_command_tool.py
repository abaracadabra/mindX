# mindx/tools/shell_command_tool.py

import asyncio
from typing import Dict, Any, Tuple

from core.bdi_agent import BaseTool
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ShellCommandTool(BaseTool):
    """
    A tool for executing shell commands.
    """
    async def execute(self, command: str, **kwargs: Any) -> Tuple[bool, str]:
        """
        Executes a shell command.

        Args:
            command: The shell command to execute.

        Returns:
            A tuple containing a boolean indicating success and a string with the command's output or an error message.
        """
        self.logger.info(f"Executing shell command: {command}")
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                output = stdout.decode().strip()
                self.logger.info(f"Command executed successfully. Output:\n{output}")
                return True, output
            else:
                error_message = stderr.decode().strip()
                self.logger.error(f"Command failed with return code {process.returncode}. Error:\n{error_message}")
                return False, error_message
        except Exception as e:
            self.logger.error(f"An exception occurred while executing the command: {e}", exc_info=True)
            return False, f"An exception occurred: {e}"
