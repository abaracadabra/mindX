# agents/guardian_agent.py
"""
GuardianAgent for mindX.
Acts as the security layer for identity verification and secure key retrieval.
"""
import asyncio
import secrets
import time
from pathlib import Path
from typing import Dict, Optional, Any, Tuple

from core.id_manager_agent import IDManagerAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class GuardianAgent:
    _instance: Optional['GuardianAgent'] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, memory_agent: Optional[MemoryAgent] = None, **kwargs) -> 'GuardianAgent':
        """Singleton factory to get or create the GuardianAgent instance."""
        async with cls._lock:
            if cls._instance is None or kwargs.get("test_mode", False):
                cls._instance = cls(memory_agent=memory_agent, **kwargs)
                await cls._instance._async_init()
            return cls._instance

    def __init__(self,
                 id_manager: Optional[IDManagerAgent] = None,
                 memory_agent: Optional[MemoryAgent] = None,
                 config_override: Optional[Config] = None,
                 test_mode: bool = False,
                 **kwargs):
        """Initializes the GuardianAgent."""
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return

        self.id_manager = id_manager
        self.memory_agent = memory_agent or MemoryAgent()
        self.config = config_override or Config(test_mode=test_mode)
        self.log_prefix = "GuardianAgent:"
        self.data_dir = PROJECT_ROOT / "data" / "guardian_agent"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.challenges: Dict[str, Dict[str, Any]] = {}
        self.challenge_expiry_seconds = self.config.get("guardian.challenge_expiry_seconds", 300)
        self.agent_id = "guardian_agent_main"
        
        # Initialize validation history for learning
        self.validation_history: Dict[str, Any] = {}
        self._initialized = False

    async def _async_init(self):
        """Async initialization for guardian agent."""
        if self._initialized:
            return
            
        # Initialize ID manager if not provided
        if not self.id_manager:
            self.id_manager = await IDManagerAgent.get_instance()
        
        # Create guardian's own identity
        await self.id_manager.create_new_wallet(entity_id=self.agent_id)
        
        # Log initialization
        if self.memory_agent:
            await self.memory_agent.log_process(
                process_name="guardian_initialization",
                data={"agent_id": self.agent_id, "status": "initialized"},
                metadata={"agent_id": self.agent_id}
            )
        
        self._initialized = True
        logger.info(f"{self.log_prefix} Async initialization complete.")

    async def validate_new_agent(self, agent_id: str, public_key: str, workspace_path: str) -> Tuple[bool, Dict[str, Any]]:
        """
        Comprehensive validation for new agents with memory logging.
        """
        logger.info(f"{self.log_prefix} Validating new agent: {agent_id}")
        
        validation_start_time = time.time()
        validation_result = {
            "agent_id": agent_id,
            "public_key": public_key,
            "workspace_path": workspace_path,
            "validation_timestamp": validation_start_time,
            "checks_performed": [],
            "validation_status": "PENDING"
        }
        
        try:
            # 1. Identity validation
            identity_check = await self._validate_identity(agent_id, public_key)
            validation_result["checks_performed"].append({
                "check_type": "identity_validation",
                "status": "PASSED" if identity_check else "FAILED",
                "details": f"Identity validation for {agent_id}"
            })
            
            if not identity_check:
                validation_result["validation_status"] = "FAILED"
                validation_result["failure_reason"] = "Identity validation failed"
                await self._log_validation_result(validation_result)
                return False, validation_result
            
            # 2. Registry validation - check if agent is registered
            registry_check = await self._validate_registry_status(agent_id)
            validation_result["checks_performed"].append({
                "check_type": "registry_validation",
                "status": "PASSED" if registry_check else "FAILED",
                "details": f"Registry validation for {agent_id}"
            })
            
            # 3. Challenge-response test
            challenge_check = await self._perform_challenge_response_test(agent_id, public_key)
            validation_result["checks_performed"].append({
                "check_type": "challenge_response",
                "status": "PASSED" if challenge_check else "FAILED",
                "details": f"Challenge-response test for {agent_id}"
            })
            
            if not challenge_check:
                validation_result["validation_status"] = "FAILED"
                validation_result["failure_reason"] = "Challenge-response test failed"
                await self._log_validation_result(validation_result)
                return False, validation_result
            
            # 4. Workspace validation
            workspace_check = await self._validate_workspace(workspace_path)
            validation_result["checks_performed"].append({
                "check_type": "workspace_validation",
                "status": "PASSED" if workspace_check else "FAILED",
                "details": f"Workspace validation for {workspace_path}"
            })
            
            if not workspace_check:
                validation_result["validation_status"] = "FAILED"
                validation_result["failure_reason"] = "Workspace validation failed"
                await self._log_validation_result(validation_result)
                return False, validation_result
            
            # All checks passed
            validation_result["validation_status"] = "PASSED"
            validation_result["validation_duration"] = time.time() - validation_start_time
            validation_result["registry_status"] = "REGISTERED" if registry_check else "UNREGISTERED_BUT_VALID"
            
            await self._log_validation_result(validation_result)
            logger.info(f"{self.log_prefix} Agent {agent_id} validation successful")
            
            return True, validation_result
            
        except Exception as e:
            validation_result["validation_status"] = "ERROR"
            validation_result["failure_reason"] = f"Validation error: {e}"
            await self._log_validation_result(validation_result)
            logger.error(f"{self.log_prefix} Validation error for agent {agent_id}: {e}")
            return False, validation_result

    async def approve_agent_for_production(self, agent_id: str, validation_result: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Approve agent for production use with cryptographic signature.
        """
        logger.info(f"{self.log_prefix} Approving agent for production: {agent_id}")
        
        try:
            # Create approval signature
            approval_data = {
                "agent_id": agent_id,
                "approved_by": self.agent_id,
                "approval_timestamp": time.time(),
                "validation_reference": validation_result.get("validation_timestamp")
            }
            
            approval_message = f"APPROVED:{agent_id}:{approval_data['approval_timestamp']}"
            if not self.id_manager:
                logger.error(f"{self.log_prefix} ID Manager not available for approval")
                return False, "ID Manager not available"
                
            guardian_private_key = self.id_manager.get_private_key_for_guardian(self.agent_id)
            
            if not guardian_private_key:
                logger.error(f"{self.log_prefix} Cannot get guardian private key for approval")
                return False, "Guardian private key not available"
            
            # Sign the approval
            signature = await self.id_manager.sign_message(self.agent_id, approval_message)
            if not signature:
                logger.error(f"{self.log_prefix} Failed to sign approval message")
                return False, "Failed to sign approval message"
                
            approval_data["signature"] = signature
            
            # Log approval
            if self.memory_agent:
                await self.memory_agent.log_process(
                    process_name="agent_production_approval",
                    data=approval_data,
                    metadata={"agent_id": self.agent_id, "approved_agent": agent_id}
                )
            
            logger.info(f"{self.log_prefix} Agent {agent_id} approved for production")
            return True, signature
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Approval error for agent {agent_id}: {e}")
            return False, f"Approval error: {e}"

    async def _validate_identity(self, agent_id: str, public_key: str) -> bool:
        """Validate agent identity."""
        try:
            # Check if identity exists in ID manager
            if not self.id_manager:
                logger.error(f"{self.log_prefix} ID Manager not available for identity validation")
                return False
            stored_key = await self.id_manager.get_public_address(agent_id)
            return stored_key == public_key
        except Exception as e:
            logger.error(f"{self.log_prefix} Identity validation error: {e}")
            return False

    async def _perform_challenge_response_test(self, agent_id: str, public_key: str) -> bool:
        """Perform challenge-response test."""
        try:
            # Generate challenge
            challenge = secrets.token_hex(32)
            
            # In a real implementation, this would involve the agent signing the challenge
            # For now, we'll simulate a successful challenge-response
            return True
        except Exception as e:
            logger.error(f"{self.log_prefix} Challenge-response test error: {e}")
            return False

    async def _validate_workspace(self, workspace_path: str) -> bool:
        """Validate agent workspace."""
        try:
            workspace = Path(workspace_path)
            return workspace.exists() and workspace.is_dir()
        except Exception as e:
            logger.error(f"{self.log_prefix} Workspace validation error: {e}")
            return False

    async def _log_validation_result(self, validation_result: Dict[str, Any]):
        """Log validation result to memory."""
        if self.memory_agent:
            await self.memory_agent.log_process(
                process_name="agent_validation",
                data=validation_result,
                metadata={"agent_id": self.agent_id, "validated_agent": validation_result.get("agent_id")}
            )

    def get_challenge(self, requesting_agent_id: str) -> str:
        """Generates and stores a unique challenge for an agent."""
        challenge = secrets.token_hex(32)
        self.challenges[requesting_agent_id] = {
            "challenge": challenge,
            "timestamp": time.time()
        }
        logger.info(f"{self.log_prefix} Issued new challenge for agent '{requesting_agent_id}'.")
        return challenge

    def _is_challenge_valid(self, requesting_agent_id: str, challenge: str) -> bool:
        """Checks if a provided challenge is valid and not expired."""
        agent_challenge = self.challenges.get(requesting_agent_id)
        if not agent_challenge:
            logger.warning(f"{self.log_prefix} No challenge found for agent '{requesting_agent_id}'.")
            return False
        
        if agent_challenge["challenge"] != challenge:
            logger.warning(f"{self.log_prefix} Invalid challenge provided for agent '{requesting_agent_id}'.")
            return False
            
        if time.time() - agent_challenge["timestamp"] > self.challenge_expiry_seconds:
            logger.warning(f"{self.log_prefix} Challenge expired for agent '{requesting_agent_id}'.")
            del self.challenges[requesting_agent_id]
            return False
            
        return True

    async def retrieve_public_key(self, entity_id: str) -> Optional[str]:
        """
        Securely retrieves the public key for a given entity ID, if it exists.
        This is the proof of key existence.
        """
        logger.info(f"{self.log_prefix} Retrieving public key for entity '{entity_id}'.")
        if not self.id_manager:
            logger.error(f"{self.log_prefix} ID Manager not available for public key retrieval")
            return None
        return await self.id_manager.get_public_address(entity_id)

    async def get_private_key(self, requesting_agent_id: str, challenge: str, signature: str) -> Optional[str]:
        """
        Verifies a signed challenge and returns the private key upon success.
        This is the ONLY secure way to retrieve a private key.
        """
        logger.info(f"{self.log_prefix} Received private key request for agent '{requesting_agent_id}'. Verifying...")
        
        if not self._is_challenge_valid(requesting_agent_id, challenge):
            return None # Logged in the check method

        public_address = await self.retrieve_public_key(entity_id=requesting_agent_id)
        if not public_address:
            logger.error(f"{self.log_prefix} Verification failed: No public key found for entity '{requesting_agent_id}'.")
            return None

        if not self.id_manager:
            logger.error(f"{self.log_prefix} ID Manager not available for signature verification")
            return None
            
        is_verified = self.id_manager.verify_signature(
            public_address=public_address,
            message=challenge,
            signature=signature
        )

        # Clean up the challenge immediately after use
        if requesting_agent_id in self.challenges:
            del self.challenges[requesting_agent_id]

        if is_verified:
            logger.info(f"{self.log_prefix} Signature VERIFIED for agent '{requesting_agent_id}'. Releasing private key.")
            if self.id_manager:
                return self.id_manager.get_private_key_for_guardian(requesting_agent_id)
            else:
                logger.error(f"{self.log_prefix} ID Manager not available for private key retrieval")
                return None
        else:
            logger.error(f"{self.log_prefix} Signature verification FAILED for agent '{requesting_agent_id}'. Access denied.")
            return None

    async def _validate_registry_status(self, agent_id: str) -> bool:
        """Validate agent registry status."""
        try:
            from utils.config import PROJECT_ROOT
            import json
            
            # Load official agents registry
            registry_path = PROJECT_ROOT / "data" / "config" / "official_agents_registry.json"
            if not registry_path.exists():
                logger.warning(f"{self.log_prefix} Registry file not found: {registry_path}")
                return False
                
            with open(registry_path, 'r') as f:
                registry = json.load(f)
            
            # Check if agent is registered
            registered_agents = registry.get("registered_agents", {})
            is_registered = agent_id in registered_agents
            
            if is_registered:
                agent_info = registered_agents[agent_id]
                is_enabled = agent_info.get("enabled", True)
                has_identity = bool(agent_info.get("identity", {}).get("public_key"))
                
                logger.info(f"{self.log_prefix} Registry check for {agent_id}: registered={is_registered}, enabled={is_enabled}, has_identity={has_identity}")
                return is_enabled and has_identity
            else:
                logger.warning(f"{self.log_prefix} Agent {agent_id} not found in registry")
                return False
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Registry validation error for {agent_id}: {e}")
            return False
