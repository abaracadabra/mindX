# mindx/tools/llm_tool_manager.py

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from core.bdi_agent import BaseTool
from core.id_manager_agent import IDManagerAgent
from agents.memory_agent import MemoryAgent
from utils.logging_config import get_logger

logger = get_logger(__name__)

class LLMToolManager(BaseTool):
    """
    A tool for managing the LLM tools in the official tools registry.
    """
    def __init__(self, memory_agent: MemoryAgent, **kwargs: Any):
        super().__init__(memory_agent=memory_agent, **kwargs)
        self.tool_registry_path = Path(self.config.get("mastermind_agent.tools_registry_path", "data/config/official_tools_registry.json"))
        self.model_cards_path = self.memory_agent.get_agent_data_directory("a2a_model_cards")

    def _load_registry(self) -> Dict[str, Any]:
        """Loads the tool registry from a JSON file."""
        if self.tool_registry_path.exists():
            try:
                with self.tool_registry_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading tool registry from {self.tool_registry_path}: {e}")
        return {"registered_tools": {}}

    def _save_registry(self, registry: Dict[str, Any]):
        """Saves the tool registry to a JSON file."""
        try:
            with self.tool_registry_path.open("w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving tool registry to {self.tool_registry_path}: {e}")

    async def _create_model_card(self, item_id: str, item_config: Dict[str, Any]) -> Dict[str, Any]:
        """Creates an A2A model card for a tool."""
        id_manager = await IDManagerAgent.get_instance()
        identity = await id_manager.get_identity(item_id)
        model_card = {
            "id": item_id,
            "name": item_config.get("name", item_id),
            "description": item_config.get("description", ""),
            "type": "tool",
            "version": item_config.get("version", "1.0.0"),
            "enabled": item_config.get("enabled", True),
            "commands": item_config.get("commands", []),
            "access_control": item_config.get("access_control", {}),
            "identity": {
                "public_address": identity.get("public_address") if identity else None,
                "signature": await id_manager.sign_message(item_id, json.dumps(item_config)) if identity else None,
            },
            "a2a_endpoint": f"https://mindx.internal/{item_id}/a2a",
        }
        return model_card

    async def execute(self, action: str, tool_id: str, tool_config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Tuple[bool, Any]:
        """
        Executes an action on the LLM tools in the registry.

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
            
            model_card = await self._create_model_card(tool_id, tool_config)
            tool_config["model_card"] = f"{tool_id}.json"
            self.model_cards_path.mkdir(parents=True, exist_ok=True)
            with (self.model_cards_path / f"{tool_id}.json").open("w", encoding="utf-8") as f:
                json.dump(model_card, f, indent=2)
            
            registry["registered_tools"][tool_id] = tool_config
            self._save_registry(registry)
            return True, f"Tool '{tool_id}' added successfully."
        elif action == "remove":
            if tool_id not in registry["registered_tools"]:
                return False, f"Tool '{tool_id}' not found."
            
            model_card_path = self.model_cards_path / registry["registered_tools"][tool_id]["model_card"]
            if model_card_path.exists():
                model_card_path.unlink()
            
            del registry["registered_tools"][tool_id]
            self._save_registry(registry)
            return True, f"Tool '{tool_id}' removed successfully."
        elif action == "update":
            if not tool_config:
                return False, "Missing 'tool_config' parameter for 'update' action."
            if tool_id not in registry["registered_tools"]:
                return False, f"Tool '{tool_id}' not found."

            model_card = await self._create_model_card(tool_id, tool_config)
            tool_config["model_card"] = f"{tool_id}.json"
            self.model_cards_path.mkdir(parents=True, exist_ok=True)
            with (self.model_cards_path / f"{tool_id}.json").open("w", encoding="utf-8") as f:
                json.dump(model_card, f, indent=2)

            registry["registered_tools"][tool_id] = tool_config
            self._save_registry(registry)
            return True, f"Tool '{tool_id}' updated successfully."
        else:
            return False, f"Unknown action: {action}"
