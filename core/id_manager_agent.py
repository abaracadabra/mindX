# core/id_manager_agent.py
"""
IDManagerAgent for mindX.
Manages a central, secure ledger of cryptographic identities.
"""
import os
from pathlib import Path
from typing import Dict, Optional, Tuple, Any, List
import re
import asyncio
import stat

try:
    from dotenv import load_dotenv, set_key, unset_key, find_dotenv
    from eth_account import Account
    if hasattr(Account, 'enable_unaudited_hdwallet_features'):
        Account.enable_unaudited_hdwallet_features()
except ImportError:
    import logging
    logging.basicConfig(level=logging.CRITICAL)
    logging.critical("IDManagerAgent dependencies missing. Please run 'pip install python-dotenv eth-account'.")
    class Account:
        address: str; key: Any
        @staticmethod
        def create() -> 'Account': raise NotImplementedError("eth_account not installed")
        @staticmethod
        def from_key(key: Any) -> 'Account': raise NotImplementedError("eth_account not installed")
        @staticmethod
        def sign_message(message_hash: Any, private_key: Any) -> Any: raise NotImplementedError("eth_account not installed")
        @staticmethod
        def recover_message(message_hash: Any, signature: Any) -> Any: raise NotImplementedError("eth_account not installed")
    def load_dotenv(*args, **kwargs): return True  # type: ignore
    def set_key(*args, **kwargs): return False  # type: ignore
    def unset_key(*args, **kwargs): return False  # type: ignore
    def find_dotenv(*args, **kwargs) -> str: return ""

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent
from .belief_system import BeliefSystem, BeliefSource

logger = get_logger(__name__)

class IDManagerAgent:
    _instances: Dict[str, 'IDManagerAgent'] = {}
    _class_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, agent_id: str = "default_identity_manager", **kwargs) -> 'IDManagerAgent':
        async with cls._class_lock:
            if agent_id not in cls._instances:
                if 'belief_system' not in kwargs:
                    kwargs['belief_system'] = BeliefSystem()
                cls._instances[agent_id] = cls(agent_id=agent_id, **kwargs)
            return cls._instances[agent_id]

    def __init__(self, agent_id: str, belief_system: BeliefSystem, config_override: Optional[Config] = None, memory_agent: Optional[MemoryAgent] = None, **kwargs):
        self.agent_id = agent_id
        self.config = config_override or Config()
        self.belief_system = belief_system
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.log_prefix = f"IDManagerAgent ({self.agent_id}):"
        
        key_store_dir_rel_str = self.config.get("id_manager.key_store_dir_relative_to_project", "data/identity")
        self.key_store_dir: Path = PROJECT_ROOT / key_store_dir_rel_str
        self.env_file_path: Path = self.key_store_dir / ".wallet_keys.env"
        self._ensure_env_setup_sync()
        logger.info(f"{self.log_prefix} Initialized. Secure central key store: {self.env_file_path}")

    def _ensure_env_setup_sync(self):
        try:
            self.key_store_dir.mkdir(parents=True, exist_ok=True)
            if os.name != 'nt':
                os.chmod(self.key_store_dir, stat.S_IRWXU)
            if not self.env_file_path.exists():
                self.env_file_path.touch()
                if os.name != 'nt':
                    os.chmod(self.env_file_path, stat.S_IRUSR | stat.S_IWUSR)
        except Exception as e:
            logger.critical(f"{self.log_prefix} CRITICAL error during secure environment setup: {e}", exc_info=True)
            raise

    def _generate_env_var_name(self, entity_id: str) -> str:
        """Generates a deterministic environment variable name from the entity ID."""
        safe_entity_id = re.sub(r'\W+', '_', entity_id).upper()
        return f"MINDX_WALLET_PK_{safe_entity_id}"

    async def get_public_address(self, entity_id: str) -> Optional[str]:
        """Checks for an existing key and returns the public address if found."""
        belief = await self.belief_system.get_belief(f"identity.map.entity_to_address.{entity_id}")
        if belief:
            # Log successful belief retrieval
            await self.memory_agent.log_process(
                process_name="id_manager_address_lookup",
                data={"entity_id": entity_id, "address": belief.value, "source": "belief_system"},
                metadata={"agent_id": self.agent_id}
            )
            return belief.value
        
        env_var_name = self._generate_env_var_name(entity_id)
        load_dotenv(dotenv_path=self.env_file_path, override=True)
        private_key_hex = os.getenv(env_var_name)
        if private_key_hex:
            try:
                address = Account.from_key(private_key_hex).address
                await self.belief_system.add_belief(f"identity.map.entity_to_address.{entity_id}", address, 1.0, BeliefSource.DERIVED)
                await self.belief_system.add_belief(f"identity.map.address_to_entity.{address}", entity_id, 1.0, BeliefSource.DERIVED)
                
                # Log successful address derivation
                await self.memory_agent.log_process(
                    process_name="id_manager_address_derived",
                    data={"entity_id": entity_id, "address": address, "source": "private_key"},
                    metadata={"agent_id": self.agent_id}
                )
                return address
            except Exception as e:
                # Log derivation failure
                await self.memory_agent.log_process(
                    process_name="id_manager_address_derivation_failed",
                    data={"entity_id": entity_id, "error": str(e)},
                    metadata={"agent_id": self.agent_id}
                )
                return None
        
        # Log address not found
        await self.memory_agent.log_process(
            process_name="id_manager_address_not_found",
            data={"entity_id": entity_id},
            metadata={"agent_id": self.agent_id}
        )
        return None

    async def get_entity_id(self, public_address: str) -> Optional[str]:
        """Retrieves the entity ID associated with a public address."""
        belief = await self.belief_system.get_belief(f"identity.map.address_to_entity.{public_address}")
        
        if belief:
            # Log successful entity lookup
            await self.memory_agent.log_process(
                process_name="id_manager_entity_lookup",
                data={"public_address": public_address, "entity_id": belief.value, "found": True},
                metadata={"agent_id": self.agent_id}
            )
            return belief.value
        else:
            # Log entity not found
            await self.memory_agent.log_process(
                process_name="id_manager_entity_lookup",
                data={"public_address": public_address, "found": False},
                metadata={"agent_id": self.agent_id}
            )
            return None

    async def create_new_wallet(self, entity_id: str) -> Tuple[str, str]:
        """
        Creates a new wallet for an entity, ONLY if one does not already exist.
        """
        existing_address = await self.get_public_address(entity_id)
        if existing_address:
            logger.warning(f"{self.log_prefix} Wallet already exists for entity '{entity_id}'. Creation skipped.")
            env_var_name = self._generate_env_var_name(entity_id)
            
            # Log wallet already exists
            await self.memory_agent.log_process(
                process_name="id_manager_wallet_exists",
                data={"entity_id": entity_id, "address": existing_address, "env_var": env_var_name},
                metadata={"agent_id": self.agent_id}
            )
            return existing_address, env_var_name

        logger.info(f"{self.log_prefix} Creating new wallet for entity '{entity_id}'.")
        try:
            account = Account.create()
            private_key_hex = account.key.hex()
            public_address = account.address
            env_var_name = self._generate_env_var_name(entity_id)
            
            if set_key(self.env_file_path, env_var_name, private_key_hex, quote_mode='never'):
                logger.info(f"{self.log_prefix} Stored new private key for '{entity_id}' in {self.env_file_path}.")
                await self.belief_system.add_belief(f"identity.map.entity_to_address.{entity_id}", public_address, 1.0, BeliefSource.DERIVED)
                await self.belief_system.add_belief(f"identity.map.address_to_entity.{public_address}", entity_id, 1.0, BeliefSource.DERIVED)
                
                # Log successful wallet creation
                await self.memory_agent.log_process(
                    process_name="id_manager_wallet_created",
                    data={
                        "entity_id": entity_id, 
                        "address": public_address, 
                        "env_var": env_var_name,
                        "success": True,
                        "key_stored": True
                    },
                    metadata={"agent_id": self.agent_id}
                )
                return account.address, env_var_name
            else:
                raise RuntimeError(f"Failed to store private key for {entity_id} using set_key.")
        except Exception as e:
            logger.critical(f"{self.log_prefix} Failed to create and store new wallet for '{entity_id}': {e}", exc_info=True)
            
            # Log wallet creation failure
            await self.memory_agent.log_process(
                process_name="id_manager_wallet_creation_failed",
                data={"entity_id": entity_id, "error": str(e)},
                metadata={"agent_id": self.agent_id}
            )
            raise

    def get_private_key_for_guardian(self, entity_id: str) -> Optional[str]:
        env_var_name = self._generate_env_var_name(entity_id)
        load_dotenv(dotenv_path=self.env_file_path, override=True)
        private_key = os.getenv(env_var_name)
        if not private_key:
            logger.warning(f"{self.log_prefix} Private key not found for entity '{entity_id}' with Guardian authorization.")
        return private_key

    async def sign_message(self, entity_id: str, message: str) -> Optional[str]:
        private_key_hex = self.get_private_key_for_guardian(entity_id)
        if not private_key_hex:
            logger.error(f"{self.log_prefix} Could not sign message. Private key for '{entity_id}' not found.")
            
            # Log signing failure - no key
            await self.memory_agent.log_process(
                process_name="id_manager_sign_failed_no_key",
                data={"entity_id": entity_id, "message_length": len(message)},
                metadata={"agent_id": self.agent_id}
            )
            return None
        try:
            from eth_account.messages import encode_defunct
            message_hash = encode_defunct(text=message)
            signed_message = Account.sign_message(message_hash, private_key=private_key_hex)
            signature = signed_message.signature.hex()
            
            # Log successful signing
            await self.memory_agent.log_process(
                process_name="id_manager_message_signed",
                data={
                    "entity_id": entity_id, 
                    "message_length": len(message),
                    "signature_length": len(signature),
                    "success": True
                },
                metadata={"agent_id": self.agent_id}
            )
            return signature
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to sign message for '{entity_id}': {e}", exc_info=True)
            
            # Log signing failure - crypto error
            await self.memory_agent.log_process(
                process_name="id_manager_sign_failed_crypto",
                data={"entity_id": entity_id, "error": str(e)},
                metadata={"agent_id": self.agent_id}
            )
            return None

    def verify_signature(self, public_address: str, message: str, signature: str) -> bool:
        try:
            from eth_account.messages import encode_defunct
            message_hash = encode_defunct(text=message)
            recovered_address = Account.recover_message(message_hash, signature=signature)
            is_valid = recovered_address.lower() == public_address.lower()
            
            # Log signature verification
            asyncio.create_task(self.memory_agent.log_process(
                process_name="id_manager_signature_verified",
                data={
                    "public_address": public_address,
                    "message_length": len(message),
                    "signature_length": len(signature),
                    "is_valid": is_valid,
                    "recovered_address": recovered_address
                },
                metadata={"agent_id": self.agent_id}
            ))
            return is_valid
        except Exception as e:
            logger.error(f"{self.log_prefix} Signature verification failed for address {public_address}: {e}", exc_info=True)
            
            # Log verification failure
            asyncio.create_task(self.memory_agent.log_process(
                process_name="id_manager_verification_failed",
                data={"public_address": public_address, "error": str(e)},
                metadata={"agent_id": self.agent_id}
            ))
            return False

    async def list_managed_identities(self) -> List[Dict[str, str]]:
        """Lists all identities by querying the belief system."""
        identities = []
        entity_beliefs = await self.belief_system.query_beliefs(partial_key="identity.map.entity_to_address.")
        for key, belief in entity_beliefs:
            entity_id = key.split('.')[-1]
            public_address = belief.value
            identities.append({
                "entity_id": entity_id,
                "public_address": public_address
            })
        
        # Log identity listing
        await self.memory_agent.log_process(
            process_name="id_manager_list_identities",
            data={"total_identities": len(identities), "identities": identities},
            metadata={"agent_id": self.agent_id}
        )
        return identities
