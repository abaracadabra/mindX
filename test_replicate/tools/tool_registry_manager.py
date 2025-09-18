# mindx/tools/tool_registry_manager.py

import json
from pathlib import Path
from typing import Dict, Any, Tuple

from core.bdi_agent import BaseTool
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ToolRegistryManager(BaseTool):
    """
    A tool for managing the official tools registry.
    """
    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self.registry_path = Path(self.config.get("mastermind_agent.tools_registry_path", "data/config/official_tools_registry.json"))

    def _load_registry(self) -> Dict[str, Any]:
        """Loads the tool registry from a JSON file."""
        if self.registry_path.exists():
            try:
                with self.registry_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading tool registry from {self.registry_path}: {e}")
        return {"registered_tools": {}}

    def _save_registry(self, registry: Dict[str, Any]):
        """Saves the tool registry to a JSON file."""
        try:
            with self.registry_path.open("w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving tool registry to {self.registry_path}: {e}")

    async def execute(self, action: str, tool_id: str, tool_config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Tuple[bool, Any]:
        """
        Executes an action on the tool registry.

        Args:
            action: The action to perform. Can be 'add', 'remove', or 'update'.
            tool_id: The ID of the tool to act on.
            tool_config: The configuration of the tool. Required for 'add' and 'update' actions.

        Returns:
            A tuple containing a boolean indicating success and a result.
        """
        registry = self._load_registry()
        if action == "add":
            if not tool_config:
                return False, "Missing 'tool_config' parameter for 'add' action."
            if tool_id in registry["registered_tools"]:
                return False, f"Tool '{tool_id}' already exists."
            registry["registered_tools"][tool_id] = tool_config
            self._save_registry(registry)
            return True, f"Tool '{tool_id}' added successfully."
        elif action == "remove":
            if tool_id not in registry["registered_tools"]:
                return False, f"Tool '{tool_id}' not found."
            del registry["registered_tools"][tool_id]
            self._save_registry(registry)
            return True, f"Tool '{tool_id}' removed successfully."
        elif action == "update":
            if not tool_config:
                return False, "Missing 'tool_config' parameter for 'update' action."
            if tool_id not in registry["registered_tools"]:
                return False, f"Tool '{tool_id}' not found."
            registry["registered_tools"][tool_id] = tool_config
            self._save_registry(registry)
            return True, f"Tool '{tool_id}' updated successfully."
        else:
            return False, f"Unknown action: {action}"
