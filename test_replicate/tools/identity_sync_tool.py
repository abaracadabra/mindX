#!/usr/bin/env python3
"""
Identity Sync Tool for mindX
Comprehensive identity management and synchronization for agents and tools
"""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from core.bdi_agent import BaseTool
from core.id_manager_agent import IDManagerAgent
from core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class IdentitySyncTool(BaseTool):
    """
    Comprehensive identity synchronization tool for agents and tools.
    Manages cryptographic identities, registry updates, and validation.
    """
    
    def __init__(self, 
                 memory_agent: Optional[MemoryAgent] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.config = config or Config()
        
        # Registry file paths
        self.agents_registry_path = PROJECT_ROOT / "data" / "config" / "official_agents_registry.json"
        self.tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
        
        self.log_prefix = "IdentitySyncTool:"
        logger.info(f"{self.log_prefix} Initialized with registry paths.")

    async def execute(self, action: str = "sync_all", **kwargs) -> Tuple[bool, Any]:
        """
        Execute identity synchronization operations.
        
        Args:
            action: Operation to perform
                - "sync_all": Sync both agents and tools
                - "sync_agents": Sync agent identities only
                - "sync_tools": Sync tool identities only
                - "validate": Validate all identities
                - "status": Get identity status report
        """
        logger.info(f"{self.log_prefix} Executing action: {action}")
        
        try:
            if action == "sync_all":
                return await self._sync_all_identities()
            elif action == "sync_agents":
                return await self._sync_agent_identities()
            elif action == "sync_tools":
                return await self._sync_tool_identities()
            elif action == "validate":
                return await self._validate_all_identities()
            elif action == "status":
                return await self._get_identity_status()
            else:
                return False, f"Unknown action: {action}"
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Error executing {action}: {e}", exc_info=True)
            return False, f"Error: {e}"

    async def _sync_all_identities(self) -> Tuple[bool, Any]:
        """Sync both agent and tool identities."""
        logger.info(f"{self.log_prefix} Starting comprehensive identity sync...")
        
        results = {
            "agents": {"updated": 0, "errors": []},
            "tools": {"updated": 0, "errors": []},
            "total_duration": 0
        }
        
        start_time = time.time()
        
        # Sync agents
        agent_success, agent_result = await self._sync_agent_identities()
        if agent_success:
            results["agents"] = agent_result
        else:
            results["agents"]["errors"].append(str(agent_result))
        
        # Sync tools
        tool_success, tool_result = await self._sync_tool_identities()
        if tool_success:
            results["tools"] = tool_result
        else:
            results["tools"]["errors"].append(str(tool_result))
        
        results["total_duration"] = time.time() - start_time
        
        # Log comprehensive sync
        await self.memory_agent.log_process(
            process_name="identity_sync_comprehensive",
            data=results,
            metadata={"tool": "identity_sync_tool"}
        )
        
        success = agent_success and tool_success
        logger.info(f"{self.log_prefix} Comprehensive sync complete: {results}")
        return success, results

    async def _sync_agent_identities(self) -> Tuple[bool, Any]:
        """Sync agent identities with registry."""
        logger.info(f"{self.log_prefix} Syncing agent identities...")
        
        # Load agents registry
        if not self.agents_registry_path.exists():
            return False, f"Agents registry not found: {self.agents_registry_path}"
            
        with open(self.agents_registry_path, 'r') as f:
            registry = json.load(f)
        
        # Initialize ID Manager
        belief_system = BeliefSystem()
        id_manager = await IDManagerAgent.get_instance(
            agent_id="identity_sync_tool_service",
            belief_system=belief_system
        )
        
        results = {
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "agents_processed": []
        }
        
        for agent_id, agent_info in registry["registered_agents"].items():
            try:
                identity = agent_info.get("identity", {})
                
                # Skip if already has valid identity
                if (identity.get("public_key") and 
                    identity.get("public_key") not in ["PENDING_SYNC", "0x1234567890123456789012345678901234567890"]):
                    results["skipped"] += 1
                    results["agents_processed"].append({
                        "agent_id": agent_id,
                        "status": "skipped",
                        "reason": "already_has_identity"
                    })
                    continue
                
                # Get or create public key
                public_key = await id_manager.get_public_address(agent_id)
                if not public_key:
                    public_key, env_var = await id_manager.create_new_wallet(entity_id=agent_id)
                
                # Generate signature
                signature_message = f"agent_registration:{agent_id}"
                signature = await id_manager.sign_message(agent_id, signature_message)
                
                if signature:
                    # Update registry
                    agent_info["identity"]["public_key"] = public_key
                    agent_info["identity"]["signature"] = signature
                    agent_info["last_updated"] = time.time()
                    
                    # Remove pending flags
                    agent_info.pop("registration_priority", None)
                    agent_info.pop("registration_notes", None)
                    
                    results["updated"] += 1
                    results["agents_processed"].append({
                        "agent_id": agent_id,
                        "status": "updated",
                        "public_key": public_key
                    })
                else:
                    results["errors"].append(f"Failed to generate signature for {agent_id}")
                    
            except Exception as e:
                error_msg = f"Error syncing {agent_id}: {e}"
                results["errors"].append(error_msg)
                logger.error(f"{self.log_prefix} {error_msg}")
        
        # Update registry metadata
        registry["last_updated_at"] = time.time()
        registry["last_updated_by"] = "identity_sync_tool"
        
        # Save updated registry
        with open(self.agents_registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        
        logger.info(f"{self.log_prefix} Agent sync complete: {results}")
        return True, results

    async def _sync_tool_identities(self) -> Tuple[bool, Any]:
        """Sync tool identities with registry."""
        logger.info(f"{self.log_prefix} Syncing tool identities...")
        
        # Load tools registry
        if not self.tools_registry_path.exists():
            return False, f"Tools registry not found: {self.tools_registry_path}"
            
        with open(self.tools_registry_path, 'r') as f:
            registry = json.load(f)
        
        # Initialize ID Manager
        belief_system = BeliefSystem()
        id_manager = await IDManagerAgent.get_instance(
            agent_id="identity_sync_tool_service",
            belief_system=belief_system
        )
        
        results = {
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "tools_processed": []
        }
        
        for tool_id, tool_info in registry["registered_tools"].items():
            try:
                identity = tool_info.get("identity", {})
                
                # Skip if already has valid identity
                if (identity.get("public_key") and 
                    identity.get("public_key") not in [None, "PENDING_SYNC"]):
                    results["skipped"] += 1
                    results["tools_processed"].append({
                        "tool_id": tool_id,
                        "status": "skipped",
                        "reason": "already_has_identity"
                    })
                    continue
                
                # Create tool identity with tool_ prefix
                tool_entity_id = f"tool_{tool_id}"
                
                # Get or create public key
                public_key = await id_manager.get_public_address(tool_entity_id)
                if not public_key:
                    public_key, env_var = await id_manager.create_new_wallet(entity_id=tool_entity_id)
                
                # Generate signature for tool registration
                signature_message = f"tool_registration:{tool_id}:{tool_info.get('version', '1.0.0')}"
                signature = await id_manager.sign_message(tool_entity_id, signature_message)
                
                if signature:
                    # Update tool identity
                    if "identity" not in tool_info:
                        tool_info["identity"] = {}
                    
                    tool_info["identity"]["public_key"] = public_key
                    tool_info["identity"]["signature"] = signature
                    tool_info["identity"]["entity_id"] = tool_entity_id
                    tool_info["identity"]["signature_message"] = signature_message
                    
                    # Add identity metadata
                    tool_info["identity_enabled"] = True
                    tool_info["last_identity_update"] = time.time()
                    
                    results["updated"] += 1
                    results["tools_processed"].append({
                        "tool_id": tool_id,
                        "status": "updated",
                        "public_key": public_key
                    })
                else:
                    results["errors"].append(f"Failed to generate signature for {tool_id}")
                    
            except Exception as e:
                error_msg = f"Error syncing {tool_id}: {e}"
                results["errors"].append(error_msg)
                logger.error(f"{self.log_prefix} {error_msg}")
        
        # Update registry metadata
        registry["last_updated_at"] = time.time()
        registry["last_updated_by"] = "identity_sync_tool"
        registry["identity_sync_version"] = "1.0.0"
        
        # Save updated registry
        with open(self.tools_registry_path, 'w') as f:
            json.dump(registry, f, indent=2)
        
        logger.info(f"{self.log_prefix} Tool sync complete: {results}")
        return True, results

    async def _validate_all_identities(self) -> Tuple[bool, Any]:
        """Validate all agent and tool identities."""
        logger.info(f"{self.log_prefix} Validating all identities...")
        
        validation_results = {
            "agents": {"valid": 0, "invalid": 0, "issues": []},
            "tools": {"valid": 0, "invalid": 0, "issues": []},
            "validation_timestamp": time.time()
        }
        
        # Initialize ID Manager
        belief_system = BeliefSystem()
        id_manager = await IDManagerAgent.get_instance(
            agent_id="identity_sync_tool_service",
            belief_system=belief_system
        )
        
        # Validate agents
        if self.agents_registry_path.exists():
            with open(self.agents_registry_path, 'r') as f:
                agents_registry = json.load(f)
            
            for agent_id, agent_info in agents_registry["registered_agents"].items():
                identity = agent_info.get("identity", {})
                public_key = identity.get("public_key")
                signature = identity.get("signature")
                
                if public_key and signature:
                    # Verify identity exists in ID manager
                    stored_key = await id_manager.get_public_address(agent_id)
                    if stored_key == public_key:
                        validation_results["agents"]["valid"] += 1
                    else:
                        validation_results["agents"]["invalid"] += 1
                        validation_results["agents"]["issues"].append({
                            "agent_id": agent_id,
                            "issue": "public_key_mismatch",
                            "stored": stored_key,
                            "registry": public_key
                        })
                else:
                    validation_results["agents"]["invalid"] += 1
                    validation_results["agents"]["issues"].append({
                        "agent_id": agent_id,
                        "issue": "missing_identity_data"
                    })
        
        # Validate tools
        if self.tools_registry_path.exists():
            with open(self.tools_registry_path, 'r') as f:
                tools_registry = json.load(f)
            
            for tool_id, tool_info in tools_registry["registered_tools"].items():
                identity = tool_info.get("identity", {})
                public_key = identity.get("public_key")
                signature = identity.get("signature")
                entity_id = identity.get("entity_id", f"tool_{tool_id}")
                
                if public_key and signature:
                    # Verify identity exists in ID manager
                    stored_key = await id_manager.get_public_address(entity_id)
                    if stored_key == public_key:
                        validation_results["tools"]["valid"] += 1
                    else:
                        validation_results["tools"]["invalid"] += 1
                        validation_results["tools"]["issues"].append({
                            "tool_id": tool_id,
                            "issue": "public_key_mismatch",
                            "stored": stored_key,
                            "registry": public_key
                        })
                else:
                    validation_results["tools"]["invalid"] += 1
                    validation_results["tools"]["issues"].append({
                        "tool_id": tool_id,
                        "issue": "missing_identity_data"
                    })
        
        # Log validation results
        await self.memory_agent.log_process(
            process_name="identity_validation_complete",
            data=validation_results,
            metadata={"tool": "identity_sync_tool"}
        )
        
        total_issues = len(validation_results["agents"]["issues"]) + len(validation_results["tools"]["issues"])
        success = total_issues == 0
        
        logger.info(f"{self.log_prefix} Validation complete: {validation_results}")
        return success, validation_results

    async def _get_identity_status(self) -> Tuple[bool, Any]:
        """Get comprehensive identity status report."""
        logger.info(f"{self.log_prefix} Generating identity status report...")
        
        status = {
            "agents": {"total": 0, "with_identity": 0, "percentage": 0},
            "tools": {"total": 0, "with_identity": 0, "percentage": 0},
            "wallet_keys": 0,
            "report_timestamp": time.time()
        }
        
        # Check agents
        if self.agents_registry_path.exists():
            with open(self.agents_registry_path, 'r') as f:
                agents_registry = json.load(f)
            
            status["agents"]["total"] = len(agents_registry["registered_agents"])
            status["agents"]["with_identity"] = sum(
                1 for a in agents_registry["registered_agents"].values()
                if a.get("identity", {}).get("public_key") not in [None, "PENDING_SYNC"]
            )
            if status["agents"]["total"] > 0:
                status["agents"]["percentage"] = int(
                    status["agents"]["with_identity"] / status["agents"]["total"] * 100
                )
        
        # Check tools
        if self.tools_registry_path.exists():
            with open(self.tools_registry_path, 'r') as f:
                tools_registry = json.load(f)
            
            status["tools"]["total"] = len(tools_registry["registered_tools"])
            status["tools"]["with_identity"] = sum(
                1 for t in tools_registry["registered_tools"].values()
                if t.get("identity", {}).get("public_key") not in [None, "PENDING_SYNC"]
            )
            if status["tools"]["total"] > 0:
                status["tools"]["percentage"] = int(
                    status["tools"]["with_identity"] / status["tools"]["total"] * 100
                )
        
        # Check wallet keys
        wallet_path = PROJECT_ROOT / "data" / "identity" / ".wallet_keys.env"
        if wallet_path.exists():
            with open(wallet_path, 'r') as f:
                lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
            status["wallet_keys"] = len(lines)
        
        logger.info(f"{self.log_prefix} Status report: {status}")
        return True, status 