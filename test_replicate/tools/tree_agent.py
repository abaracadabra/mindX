import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from tools.shell_command_tool import ShellCommandTool
from core.bdi_agent import BaseTool

class TreeAgent(BaseTool):
    def __init__(self, root_path: str, **kwargs: Any):
        super().__init__(**kwargs)
        self.root_path = Path(root_path).resolve()
        self.shell = ShellCommandTool()

    async def execute(self, command: str) -> Optional[str]:
        if not command.startswith("ls") and not command.startswith("find"):
            return "Error: Only 'ls' and 'find' commands are allowed."
        
        # Correctly construct the command to be sandboxed to the root path.
        # e.g., `find . -name file.txt` becomes `find /root/path . -name file.txt`
        parts = command.split(" ")
        cmd_base = parts[0]
        cmd_args = " ".join(parts[1:])
        full_command = f"{cmd_base} {self.root_path} {cmd_args}"
        
        success, result = self.shell.execute(command=full_command)
        
        if self.memory_agent and self.bdi_agent_ref:
            await self.memory_agent.log_process(
                process_name='tree_agent_execution',
                data={'command': full_command, 'success': success, 'result': result},
                metadata={'agent_id': self.bdi_agent_ref.agent_id, 'tool_id': 'tree_agent'}
            )
            
        return result if success else f"Error: {result}"
