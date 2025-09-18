# mindx/tools/registry_manager_tool.py

import json
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

from core.bdi_agent import BaseTool
from core.id_manager_agent import IDManagerAgent
from agents.memory_agent import MemoryAgent
from utils.logging_config import get_logger

logger = get_logger(__name__)

class RegistryManagerTool(BaseTool):
    """
    A tool for managing the official tool and agent registries.
    """
    def __init__(self, memory_agent: MemoryAgent, **kwargs: Any):
        super().__init__(**kwargs)
        self.memory_agent = memory_agent
        self.tool_registry_path = Path(self.config.get("mastermind_agent.tools_registry_path", "data/config/official_tools_registry.json"))
        self.agent_registry_path = Path(self.config.get("mastermind_agent.agents_registry_path", "data/config/official_agents_registry.json"))
        self.model_cards_path = self.memory_agent.get_agent_data_directory("a2a_model_cards")

    def _load_registry(self, registry_path: Path) -> Dict[str, Any]:
        """Loads a registry from a JSON file."""
        if registry_path.exists():
            try:
                with registry_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading registry from {registry_path}: {e}")
        return {"registered_tools": {}, "registered_agents": {}}

    def _save_registry(self, registry: Dict[str, Any], registry_path: Path):
        """Saves a registry to a JSON file."""
        try:
            with registry_path.open("w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving registry to {registry_path}: {e}")

    async def _create_model_card(self, item_id: str, item_config: Dict[str, Any], item_type: str) -> Dict[str, Any]:
        """Creates an A2A model card for an agent or tool."""
        id_manager = await IDManagerAgent.get_instance()
        public_key, _ = await id_manager.create_new_wallet(item_id)
        model_card = {
            "id": item_id,
            "name": item_config.get("name", item_id),
            "description": item_config.get("description", ""),
            "type": item_type,
            "version": item_config.get("version", "1.0.0"),
            "enabled": item_config.get("enabled", True),
            "commands": item_config.get("commands", []),
            "access_control": item_config.get("access_control", {}),
            "identity": {
                "public_key": public_key,
                "signature": await id_manager.sign_message(item_id, json.dumps(item_config)) if public_key else None,
            },
            "a2a_endpoint": f"https://mindx.internal/{item_id}/a2a",
        }
        return model_card

    async def execute(self, registry_type: str, action: str, item_id: str, item_config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> Tuple[bool, Any]:
        """
        Executes an action on a registry.

        Args:
            registry_type: The type of registry to act on. Can be 'tool' or 'agent'.
            action: The action to perform. Can be 'add', 'remove', or 'update'.
            item_id: The ID of the item to act on.
            item_config: The configuration of the item. Required for 'add' and 'update' actions.

        Returns:
            A tuple containing a boolean indicating success and a result.
        """
        if registry_type == "tool":
            registry_path = self.tool_registry_path
            registry_key = "registered_tools"
        elif registry_type == "agent":
            registry_path = self.agent_registry_path
            registry_key = "registered_agents"
        else:
            return False, f"Unknown registry type: {registry_type}"

        registry = self._load_registry(registry_path)

        if action == "add":
            if not item_config:
                return False, f"Missing 'item_config' parameter for 'add' action."
            if item_id in registry[registry_key]:
                return False, f"{registry_type.capitalize()} '{item_id}' already exists."
            
            model_card = await self._create_model_card(item_id, item_config, registry_type)
            item_config["model_card"] = f"{item_id}.json"
            self.model_cards_path.mkdir(parents=True, exist_ok=True)
            with (self.model_cards_path / f"{item_id}.json").open("w", encoding="utf-8") as f:
                json.dump(model_card, f, indent=2)
            
            registry[registry_key][item_id] = item_config
            self._save_registry(registry, registry_path)
            return True, f"{registry_type.capitalize()} '{item_id}' added successfully."
        elif action == "remove":
            if item_id not in registry[registry_key]:
                return False, f"{registry_type.capitalize()} '{item_id}' not found."
            
            model_card_path = self.model_cards_path / registry[registry_key][item_id]["model_card"]
            if model_card_path.exists():
                model_card_path.unlink()
            
            del registry[registry_key][item_id]
            self._save_registry(registry, registry_path)
            return True, f"{registry_type.capitalize()} '{item_id}' removed successfully."
        elif action == "update":
            if not item_config:
                return False, f"Missing 'item_config' parameter for 'update' action."
            if item_id not in registry[registry_key]:
                return False, f"{registry_type.capitalize()} '{item_id}' not found."

            model_card = await self._create_model_card(item_id, item_config, registry_type)
            item_config["model_card"] = f"{item_id}.json"
            self.model_cards_path.mkdir(parents=True, exist_ok=True)
            with (self.model_cards_path / f"{item_id}.json").open("w", encoding="utf-8") as f:
                json.dump(model_card, f, indent=2)

            registry[registry_key][item_id] = item_config
            self._save_registry(registry, registry_path)
            return True, f"{registry_type.capitalize()} '{item_id}' updated successfully."
        else:
            return False, f"Unknown action: {action}"
