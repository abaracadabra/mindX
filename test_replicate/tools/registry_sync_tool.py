# mindx/tools/registry_sync_tool.py
"""
Registry Synchronization Tool for MindX.

This tool handles synchronization between runtime agent registry and persistent 
agent registry files, ensuring all agents have proper cryptographic identities 
and signatures.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from core.bdi_agent import BaseTool
from core.id_manager_agent import IDManagerAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class RegistrySyncTool(BaseTool):
    """
    Tool for synchronizing and validating agent registries with cryptographic identities.
    """
    
    def __init__(self, 
                 memory_agent: MemoryAgent,
                 coordinator_ref: Optional[Any] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.coordinator_ref = coordinator_ref
        self.config = config or Config()
        
        # Registry file paths
        self.agents_registry_path = PROJECT_ROOT / "data" / "config" / "official_agents_registry.json"
        self.tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
        
        self.log_prefix = "RegistrySyncTool:"
        logger.info(f"{self.log_prefix} Initialized with registry paths.")

    async def execute(self, 
                     action: str = "sync_all",
                     validate_signatures: bool = True,
                     update_missing_keys: bool = True,
                     **kwargs) -> Tuple[bool, Any]:
        """
        Execute registry synchronization operations.
        """
        try:
            if action == "sync_all":
                return await self._sync_all_registries(validate_signatures, update_missing_keys)
            elif action == "update_keys":
                return await self._update_missing_keys()
            else:
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Error during {action}: {e}", exc_info=True)
            return False, f"Registry sync failed: {e}"

    async def _sync_all_registries(self, validate_signatures: bool, update_missing_keys: bool) -> Tuple[bool, Any]:
        """Perform comprehensive registry synchronization."""
        logger.info(f"{self.log_prefix} Starting comprehensive registry synchronization...")
        
        results = {
            "agents_synced": 0,
            "keys_updated": 0,
            "signatures_validated": 0,
            "errors": []
        }
        
        try:
            # 1. Load current registries
            runtime_registry = self._get_runtime_registry()
            persistent_registry = self._load_persistent_agents_registry()
            
            # 2. Get ID manager instance
            id_manager = await IDManagerAgent.get_instance()
            
            # 3. Sync each agent
            for agent_id, runtime_info in runtime_registry.items():
                try:
                    # Get or create public key
                    public_key = await id_manager.get_public_address(agent_id)
                    if not public_key and update_missing_keys:
                        public_key, _ = await id_manager.create_new_wallet(entity_id=agent_id)
                        results["keys_updated"] += 1
                        logger.info(f"{self.log_prefix} Created new identity for {agent_id}")
                    
                    # Update existing entry
                    if agent_id in persistent_registry.get("registered_agents", {}):
                        await self._update_persistent_entry(
                            persistent_registry["registered_agents"][agent_id],
                            runtime_info, public_key, id_manager
                        )
                        results["agents_synced"] += 1
                            
                except Exception as e:
                    error_msg = f"Failed to sync agent {agent_id}: {e}"
                    results["errors"].append(error_msg)
                    logger.error(f"{self.log_prefix} {error_msg}")
            
            # 4. Update registry metadata
            persistent_registry["last_updated_at"] = time.time()
            persistent_registry["last_updated_by"] = "registry_sync_tool"
            
            # 5. Save updated registry
            await self._save_persistent_agents_registry(persistent_registry)
            
            logger.info(f"{self.log_prefix} Registry sync complete: {results}")
            return True, results
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Registry sync failed: {e}", exc_info=True)
            return False, f"Sync failed: {e}"

    async def _update_persistent_entry(self,
                                     persistent_entry: Dict[str, Any],
                                     runtime_info: Dict[str, Any],
                                     public_key: Optional[str],
                                     id_manager: IDManagerAgent):
        """Update an existing persistent registry entry."""
        
        # Update public key if missing
        if not persistent_entry.get("identity", {}).get("public_key") and public_key:
            persistent_entry.setdefault("identity", {})["public_key"] = public_key
            
            # Generate new signature
            signature = await id_manager.sign_message(
                persistent_entry["id"], 
                f"agent_registration:{persistent_entry['id']}"
            )
            persistent_entry["identity"]["signature"] = signature
            
        # Update other fields
        persistent_entry["type"] = runtime_info.get("agent_type", persistent_entry.get("type", "unknown"))
        persistent_entry["description"] = runtime_info.get("description", persistent_entry.get("description"))
        persistent_entry["last_updated"] = time.time()
        
        logger.debug(f"{self.log_prefix} Updated persistent entry for {persistent_entry['id']}")

    def _get_runtime_registry(self) -> Dict[str, Any]:
        """Get the current runtime agent registry from coordinator."""
        if self.coordinator_ref:
            return self.coordinator_ref.agent_registry
        return {}

    def _load_persistent_agents_registry(self) -> Dict[str, Any]:
        """Load the persistent agents registry from file."""
        if self.agents_registry_path.exists():
            try:
                with self.agents_registry_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"{self.log_prefix} Failed to load agents registry: {e}")
        
        # Return default structure
        return {
            "last_updated_at": time.time(),
            "last_updated_by": "registry_sync_tool",
            "registered_agents": {},
            "agents_schema_version": "2.0"
        }

    async def _save_persistent_agents_registry(self, registry: Dict[str, Any]):
        """Save the persistent agents registry to file."""
        try:
            with self.agents_registry_path.open("w", encoding="utf-8") as f:
                json.dump(registry, f, indent=2)
            logger.info(f"{self.log_prefix} Saved persistent agents registry")
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to save agents registry: {e}")
            raise

    async def _update_missing_keys(self) -> Tuple[bool, Any]:
        """Update missing public keys for all agents."""
        logger.info(f"{self.log_prefix} Updating missing public keys...")
        
        results = {
            "keys_created": 0,
            "keys_updated": 0,
            "errors": []
        }
        
        try:
            registry = self._load_persistent_agents_registry()
            id_manager = await IDManagerAgent.get_instance()
            
            for agent_id, agent_info in registry.get("registered_agents", {}).items():
                identity = agent_info.setdefault("identity", {})
                
                if not identity.get("public_key"):
                    # Create new identity
                    public_key, _ = await id_manager.create_new_wallet(entity_id=agent_id)
                    signature = await id_manager.sign_message(agent_id, f"agent_registration:{agent_id}")
                    
                    identity["public_key"] = public_key
                    identity["signature"] = signature
                    
                    results["keys_created"] += 1
                    logger.info(f"{self.log_prefix} Created identity for {agent_id}")
            
            # Save updated registry
            await self._save_persistent_agents_registry(registry)
            
            logger.info(f"{self.log_prefix} Key update complete: {results}")
            return True, results
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Key update failed: {e}", exc_info=True)
            return False, f"Key update failed: {e}" 