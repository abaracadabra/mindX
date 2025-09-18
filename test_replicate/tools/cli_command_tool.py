# mindx/tools/cli_command_tool.py
"""
A meta-tool that allows a BDI agent to execute the system's top-level CLI commands.
"""
from typing import Dict, Any, Optional

from core.bdi_agent import BaseTool
from orchestration.mastermind_agent import MastermindAgent
from orchestration.coordinator_agent import CoordinatorAgent

class CLICommandTool(BaseTool):
    """
    A tool that exposes the main CLI commands to an agent's planning process.
    """

    def __init__(self, mastermind: MastermindAgent, coordinator: CoordinatorAgent, **kwargs: Any):
        super().__init__(**kwargs)
        self.mastermind = mastermind
        self.coordinator = coordinator
        self.command_map = {
            "evolve": self.mastermind.manage_mindx_evolution,
            "deploy": self.mastermind.manage_agent_deployment,
            "agent_create": self.coordinator.create_and_register_agent,
            "agent_delete": self.coordinator.deregister_and_shutdown_agent,
            "agent_evolve": self.coordinator.handle_user_input, # This needs adaptation
        }

    async def execute(self, command_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a CLI command by calling the appropriate agent method.
        """
        if command_name not in self.command_map:
            return {"status": "ERROR", "message": f"Unknown CLI command: {command_name}"}

        handler = self.command_map[command_name]
        
        # Special handling for agent_evolve which expects an Interaction object
        if command_name == "agent_evolve":
            # This is a simplification; a real implementation would need to construct
            # a proper Interaction object.
            return await handler(
                content=f"Evolve agent '{args.get('id')}' with directive: {args.get('directive')}",
                user_id=self.bdi_agent_ref.agent_id if self.bdi_agent_ref else "unknown",
                interaction_type="component_improvement",
                metadata={"target_component": args.get('id'), "analysis_context": args.get('directive')}
            )

        try:
            # Call the handler with the provided arguments
            result = await handler(**args)
            return {"status": "SUCCESS", "result": result}
        except Exception as e:
            self.logger.error(f"Error executing CLI command '{command_name}': {e}", exc_info=True)
            return {"status": "ERROR", "message": str(e)}
