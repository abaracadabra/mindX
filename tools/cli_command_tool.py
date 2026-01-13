# mindx/tools/cli_command_tool.py
"""
A meta-tool that allows a BDI agent to execute the system's top-level CLI commands.

This tool provides a standardized interface for agents to execute high-level system
operations through the MastermindAgent and CoordinatorAgent. It includes command
validation, error handling, and execution history tracking.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from agents.core.bdi_agent import BaseTool
from agents.orchestration.mastermind_agent import MastermindAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

class CLICommandTool(BaseTool):
    """
    A tool that exposes the main CLI commands to an agent's planning process.
    
    Provides controlled access to system-level operations including:
    - System evolution management
    - Agent deployment
    - Agent lifecycle operations (create, delete, evolve)
    """

    def __init__(self, mastermind: MastermindAgent, coordinator: CoordinatorAgent, **kwargs: Any):
        super().__init__(**kwargs)
        self.mastermind = mastermind
        self.coordinator = coordinator
        
        # Command map with metadata
        self.command_map = {
            "evolve": {
                "handler": self.mastermind.manage_mindx_evolution,
                "description": "Manages mindX system evolution and improvements",
                "required_args": ["directive"],
                "optional_args": ["focus_areas", "iterations"]
            },
            "deploy": {
                "handler": self.mastermind.manage_agent_deployment,
                "description": "Manages agent deployment operations",
                "required_args": [],
                "optional_args": ["agent_type", "config"]
            },
            "agent_create": {
                "handler": self.coordinator.create_and_register_agent,
                "description": "Creates and registers new agents in the system",
                "required_args": ["agent_type"],
                "optional_args": ["agent_id", "config"]
            },
            "agent_delete": {
                "handler": self.coordinator.deregister_and_shutdown_agent,
                "description": "Deregisters and shuts down existing agents",
                "required_args": ["agent_id"],
                "optional_args": []
            },
            "agent_evolve": {
                "handler": self._handle_agent_evolve,
                "description": "Evolves an existing agent based on directives",
                "required_args": ["id", "directive"],
                "optional_args": ["metadata"]
            }
        }
        
        # Command execution history for auditing
        self.command_history: List[Dict[str, Any]] = []
        self.max_history_size = 100

    def _validate_command_args(self, command_name: str, args: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validates command arguments against required and optional parameters.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if command_name not in self.command_map:
            return False, f"Unknown CLI command: {command_name}. Available commands: {list(self.command_map.keys())}"
        
        command_info = self.command_map[command_name]
        required_args = command_info.get("required_args", [])
        
        # Check for required arguments
        missing_args = [arg for arg in required_args if arg not in args or args[arg] is None]
        if missing_args:
            return False, f"Missing required arguments for '{command_name}': {', '.join(missing_args)}"
        
        return True, None

    async def _handle_agent_evolve(self, **kwargs) -> Any:
        """
        Handles agent_evolve command by constructing proper Interaction object.
        
        This method adapts the agent_evolve command to work with the coordinator's
        handle_user_input method which expects an Interaction object.
        """
        agent_id = kwargs.get('id')
        directive = kwargs.get('directive')
        metadata = kwargs.get('metadata', {})
        
        if not agent_id or not directive:
            raise ValueError("Both 'id' and 'directive' are required for agent_evolve")
        
        # Construct interaction content
        content = f"Evolve agent '{agent_id}' with directive: {directive}"
        
        # Get user_id from bdi_agent_ref if available
        user_id = self.bdi_agent_ref.agent_id if self.bdi_agent_ref else "system"
        
        # Call coordinator's handle_user_input with proper Interaction structure
        return await self.coordinator.handle_user_input(
            content=content,
            user_id=user_id,
            interaction_type="component_improvement",
            metadata={
                "target_component": agent_id,
                "analysis_context": directive,
                **metadata
            }
        )

    async def execute(self, command_name: str, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes a CLI command by calling the appropriate agent method.
        
        Args:
            command_name: Name of the command to execute
            args: Dictionary of arguments for the command
            
        Returns:
            Dictionary with status and result/error message
        """
        args = args or {}
        start_time = time.time()
        
        # Validate command name
        if command_name not in self.command_map:
            error_msg = f"Unknown CLI command: {command_name}. Available: {list(self.command_map.keys())}"
            self.logger.error(error_msg)
            return {"status": "ERROR", "message": error_msg}
        
        # Validate arguments
        is_valid, validation_error = self._validate_command_args(command_name, args)
        if not is_valid:
            self.logger.error(f"Command validation failed for '{command_name}': {validation_error}")
            return {"status": "ERROR", "message": validation_error}
        
        command_info = self.command_map[command_name]
        handler = command_info["handler"]
        
        # Log command execution
        self.logger.info(f"Executing CLI command: {command_name} with args: {list(args.keys())}")
        
        try:
            # Execute the handler
            result = await handler(**args)
            execution_time = time.time() - start_time
            
            # Record successful execution
            self._record_command_history(command_name, args, "SUCCESS", execution_time)
            
            return {
                "status": "SUCCESS",
                "result": result,
                "execution_time": execution_time,
                "command": command_name
            }
            
        except TypeError as e:
            # Handle argument mismatch errors
            error_msg = f"Argument mismatch for '{command_name}': {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            execution_time = time.time() - start_time
            self._record_command_history(command_name, args, "ERROR", execution_time, error_msg)
            return {"status": "ERROR", "message": error_msg}
            
        except Exception as e:
            # Handle general errors
            error_msg = f"Error executing CLI command '{command_name}': {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            execution_time = time.time() - start_time
            self._record_command_history(command_name, args, "ERROR", execution_time, error_msg)
            return {"status": "ERROR", "message": str(e)}

    def _record_command_history(self, command_name: str, args: Dict[str, Any], 
                                status: str, execution_time: float, 
                                error: Optional[str] = None) -> None:
        """Record command execution in history."""
        history_entry = {
            "timestamp": datetime.now().isoformat(),
            "command": command_name,
            "args": {k: str(v)[:100] for k, v in args.items()},  # Truncate long values
            "status": status,
            "execution_time": execution_time,
            "error": error
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
    
    def get_available_commands(self) -> Dict[str, Dict[str, Any]]:
        """
        Get information about all available commands.
        
        Returns:
            Dictionary mapping command names to their metadata
        """
        return {
            cmd_name: {
                "description": info["description"],
                "required_args": info["required_args"],
                "optional_args": info["optional_args"]
            }
            for cmd_name, info in self.command_map.items()
        }
