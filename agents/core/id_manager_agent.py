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

# Try to import vault manager, fallback to legacy if not available
try:
    from mindx_backend_service.vault_manager import get_vault_manager
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False
    get_vault_manager = None

# BANKON Vault — primary encrypted key storage for production
try:
    from mindx_backend_service.bankon_vault.vault import BankonVault
    BANKON_VAULT_AVAILABLE = True
except ImportError:
    BANKON_VAULT_AVAILABLE = False
    BankonVault = None

# agentID unified issuance: ERC-8004 mint + BANKON IDNFT + Algorand bonafide opt-in
# in one call. Optional — mindX continues to work without it.
try:
    from agentid_identity import (
        issue_agent_identity,
        IssueIdentityOptions,
        IssueRuntime,
        AgentIdentity as AgentIdIdentity,
    )
    from .agentid_bridge import BankonVaultAgentIDAdapter
    AGENTID_AVAILABLE = True
except ImportError:
    AGENTID_AVAILABLE = False
    issue_agent_identity = None
    IssueIdentityOptions = None
    IssueRuntime = None
    AgentIdIdentity = None
    BankonVaultAgentIDAdapter = None

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

        # Sync-readable cache: entity_id → agentID agent-wallet vault ref.
        # Populated on create_new_agent_identity; the async belief_system is the
        # canonical store, but sync callers (get_private_key_for_guardian) need
        # an in-memory shortcut.
        self._entity_to_agent_vault_ref: Dict[str, str] = {}
        self._entity_to_operator_vault_ref: Dict[str, str] = {}
        
        # BANKON Vault — primary encrypted key storage (AES-256-GCM + HKDF-SHA512)
        self.bankon_vault = None
        if BANKON_VAULT_AVAILABLE and BankonVault:
            try:
                self.bankon_vault = BankonVault()
                self.bankon_vault.unlock_with_key_file()
                logger.info(f"{self.log_prefix} BANKON Vault available for encrypted key storage")
            except Exception as e:
                logger.warning(f"{self.log_prefix} BANKON Vault init failed: {e}")
                self.bankon_vault = None

        # Legacy vault manager (fallback)
        self.use_vault = VAULT_AVAILABLE and self.config.get("id_manager.use_vault", True)
        if self.use_vault and get_vault_manager:
            try:
                self.vault_manager = get_vault_manager()
                logger.info(f"{self.log_prefix} Using vault for key storage")
            except Exception as e:
                logger.warning(f"{self.log_prefix} Failed to initialize vault, falling back to legacy storage: {e}")
                self.use_vault = False
                self.vault_manager = None
        else:
            self.use_vault = False
            self.vault_manager = None
        
        self._ensure_env_setup_sync()
        logger.info(f"{self.log_prefix} Initialized. Secure central key store: {self.env_file_path} (vault: {self.use_vault})")

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
        
        # Key retrieval chain: BANKON Vault → legacy vault → .env file
        private_key_hex = None

        # 1. BANKON Vault (AES-256-GCM encrypted — production primary)
        if not private_key_hex and self.bankon_vault:
            vault_id = f"agent_pk_{entity_id}"
            try:
                private_key_hex = self.bankon_vault.retrieve(vault_id)
            except Exception:
                pass

        # 2. Legacy vault manager
        if not private_key_hex and self.use_vault and self.vault_manager:
            private_key_hex = self.vault_manager.get_agent_private_key(entity_id)

        # 3. Legacy .env file (last resort)
        if not private_key_hex:
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

    async def create_new_agent_identity(
        self,
        entity_id: str,
        role: str = "user",
        chain: str = "baseSepolia",
        dry_run: bool = True,
        algorand: bool = False,
    ) -> "AgentIdIdentity":
        """
        Full two-wallet agent identity issuance via agentID.

        Generates operator + agent EVM keypairs stored under HKDF-domain-separated
        refs in BANKON Vault (NO hardcoded salts — that path belonged to the
        deleted coral_id_agent.py). When `dry_run=False` and RPC config is
        available, also mints an ERC-8004 identity NFT on-chain; when `algorand=True`,
        opts the Algorand side into the bonafide app.

        `dry_run=True` (default) skips all on-chain calls — keys are still
        generated and stored in the vault, so this is safe to call from any
        mindX bootstrap path where funded deployer keys aren't configured.

        Returns the full `AgentIdentity` record. For legacy callers needing only
        `(address, env_var_name)`, use `create_new_wallet()`.
        """
        if not AGENTID_AVAILABLE:
            raise RuntimeError(
                "create_new_agent_identity requires agentid_identity. "
                "Install via: pip install -e /home/hacker/agentID/packages/identity/python"
            )
        if not self.bankon_vault:
            raise RuntimeError(
                "create_new_agent_identity requires an unlocked BANKON Vault — "
                "no other vault backend satisfies the HKDF-SHA512 key derivation "
                "guarantee that replaces coral_id_agent's hardcoded salt."
            )

        adapter = BankonVaultAgentIDAdapter(self.bankon_vault, context=f"agentid:{entity_id}")
        runtime = IssueRuntime(
            vault=adapter,
            evm_rpc_url=os.environ.get("BASE_SEPOLIA_RPC", "https://sepolia.base.org"),
            algod_url=os.environ.get("ALGOD_TESTNET_URL"),
            algod_token=os.environ.get("ALGOD_TESTNET_TOKEN", ""),
            pinata_jwt=os.environ.get("PINATA_JWT"),
            discovery_api_url=os.environ.get("DISCOVERY_API_URL"),
        )
        identity = await issue_agent_identity(
            IssueIdentityOptions(
                role=role,
                chain=chain,
                dry_run=dry_run,
                algorand=algorand,
                publish_to_discovery=not dry_run,
                metadata={"mindx_entity_id": entity_id},
            ),
            runtime,
        )

        # Sync cache for guardian key lookup.
        self._entity_to_agent_vault_ref[entity_id] = identity.agent.vault_ref
        self._entity_to_operator_vault_ref[entity_id] = identity.operator.vault_ref

        # Belief system entries so downstream callers can resolve by entity_id.
        await self.belief_system.add_belief(
            f"identity.map.entity_to_address.{entity_id}",
            identity.agent.address, 1.0, BeliefSource.DERIVED,
        )
        await self.belief_system.add_belief(
            f"identity.map.address_to_entity.{identity.agent.address}",
            entity_id, 1.0, BeliefSource.DERIVED,
        )
        await self.belief_system.add_belief(
            f"identity.map.entity_to_operator.{entity_id}",
            identity.operator.address, 1.0, BeliefSource.DERIVED,
        )
        await self.belief_system.add_belief(
            f"identity.map.entity_to_agent_vault_ref.{entity_id}",
            identity.agent.vault_ref, 1.0, BeliefSource.DERIVED,
        )
        await self.belief_system.add_belief(
            f"identity.map.entity_to_operator_vault_ref.{entity_id}",
            identity.operator.vault_ref, 1.0, BeliefSource.DERIVED,
        )
        if identity.algorand:
            await self.belief_system.add_belief(
                f"identity.map.entity_to_algorand.{entity_id}",
                identity.algorand.address, 1.0, BeliefSource.DERIVED,
            )
        if identity.agent_id >= 0:
            await self.belief_system.add_belief(
                f"identity.map.entity_to_erc8004_id.{entity_id}",
                str(identity.agent_id), 1.0, BeliefSource.DERIVED,
            )

        await self.memory_agent.log_process(
            process_name="id_manager_agent_identity_created",
            data={
                "entity_id": entity_id,
                "role": role,
                "chain": chain,
                "operator": identity.operator.address,
                "agent": identity.agent.address,
                "agent_id_erc8004": str(identity.agent_id) if identity.agent_id >= 0 else None,
                "algorand": identity.algorand.address if identity.algorand else None,
                "bankon_idnft": None if not identity.bankon_idnft else {
                    "contract": identity.bankon_idnft.contract,
                    "token_id": str(identity.bankon_idnft.token_id),
                },
                "dry_run": dry_run,
            },
            metadata={"agent_id": self.agent_id},
        )
        return identity

    async def create_new_wallet(self, entity_id: str) -> Tuple[str, str]:
        """
        Create a new wallet for an entity, ONLY if one does not already exist.

        Backward-compatible façade. When `agentid_identity` + BANKON Vault are
        available, routes through the two-wallet `create_new_agent_identity`
        flow — the agent (hot) address is what's returned, operator key is
        stored alongside in the vault, no `.wallet_keys.env` write. When the
        modern stack isn't available, falls back to the legacy single-wallet
        flow for compatibility with environments pre-agentID.
        """
        existing_address = await self.get_public_address(entity_id)
        if existing_address:
            logger.warning(f"{self.log_prefix} Wallet already exists for entity '{entity_id}'. Creation skipped.")
            env_var_name = self._generate_env_var_name(entity_id)
            await self.memory_agent.log_process(
                process_name="id_manager_wallet_exists",
                data={"entity_id": entity_id, "address": existing_address, "env_var": env_var_name},
                metadata={"agent_id": self.agent_id}
            )
            return existing_address, env_var_name

        env_var_name = self._generate_env_var_name(entity_id)

        # Modern path: agentID unified issuance (two-wallet, vault-stored,
        # optional on-chain ERC-8004 mint). Requires BANKON Vault unlocked.
        if AGENTID_AVAILABLE and self.bankon_vault:
            logger.info(f"{self.log_prefix} Creating new wallet for entity '{entity_id}' via agentID (two-wallet, BANKON Vault).")
            try:
                identity = await self.create_new_agent_identity(
                    entity_id,
                    role="user",
                    chain="baseSepolia",
                    dry_run=True,           # keys only; no on-chain mint from this legacy entry point
                    algorand=False,
                )
                return identity.agent.address, env_var_name
            except Exception as e:
                logger.warning(
                    f"{self.log_prefix} agentID issuance failed for '{entity_id}': {e}. "
                    "Falling through to legacy single-wallet path."
                )

        # Legacy fallback: single Ethereum wallet, vault → .env.
        logger.info(f"{self.log_prefix} Creating new wallet for entity '{entity_id}' (legacy single-wallet path).")
        try:
            account = Account.create()
            private_key_hex = account.key.hex()
            public_address = account.address

            stored = False
            if not stored and self.bankon_vault:
                try:
                    vault_id = f"agent_pk_{entity_id}"
                    stored = self.bankon_vault.store(vault_id, private_key_hex, context="agent_identity")
                    if stored:
                        logger.info(f"{self.log_prefix} Stored private key for '{entity_id}' in BANKON Vault (AES-256-GCM)")
                except Exception as e:
                    logger.warning(f"{self.log_prefix} BANKON Vault store failed for '{entity_id}': {e}")

            if not stored and self.use_vault and self.vault_manager:
                stored = self.vault_manager.store_agent_private_key(entity_id, private_key_hex)
                if stored:
                    logger.info(f"{self.log_prefix} Stored private key for '{entity_id}' in legacy vault.")

            if not stored:
                stored = set_key(self.env_file_path, env_var_name, private_key_hex, quote_mode='never')
                if stored:
                    logger.info(f"{self.log_prefix} Stored private key for '{entity_id}' in {self.env_file_path} (plaintext — migrate to vault).")

            if stored:
                await self.belief_system.add_belief(f"identity.map.entity_to_address.{entity_id}", public_address, 1.0, BeliefSource.DERIVED)
                await self.belief_system.add_belief(f"identity.map.address_to_entity.{public_address}", entity_id, 1.0, BeliefSource.DERIVED)
                await self.memory_agent.log_process(
                    process_name="id_manager_wallet_created",
                    data={
                        "entity_id": entity_id,
                        "address": public_address,
                        "env_var": env_var_name,
                        "success": True,
                        "key_stored": True,
                        "path": "legacy",
                    },
                    metadata={"agent_id": self.agent_id}
                )
                return account.address, env_var_name
            raise RuntimeError(f"Failed to store private key for {entity_id} using any available backend.")
        except Exception as e:
            logger.critical(f"{self.log_prefix} Failed to create and store new wallet for '{entity_id}': {e}", exc_info=True)
            await self.memory_agent.log_process(
                process_name="id_manager_wallet_creation_failed",
                data={"entity_id": entity_id, "error": str(e)},
                metadata={"agent_id": self.agent_id}
            )
            raise

    def get_private_key_for_guardian(self, entity_id: str) -> Optional[str]:
        # Key retrieval chain:
        #   0. agentID vault_ref (from belief_system) — two-wallet scheme
        #   1. BANKON Vault with legacy agent_pk_<entity_id> ref
        #   2. Legacy vault manager
        #   3. .env file (last resort)
        private_key = None

        # 0. agentID scheme — look up the per-entity agent vault ref from the
        #    sync cache populated by create_new_agent_identity.
        agent_ref = self._entity_to_agent_vault_ref.get(entity_id)
        if agent_ref and self.bankon_vault:
            try:
                private_key = self.bankon_vault.retrieve(agent_ref)
            except Exception:
                pass

        # 1. Legacy BANKON Vault ref (agent_pk_<entity_id>)
        if not private_key and self.bankon_vault:
            try:
                private_key = self.bankon_vault.retrieve(f"agent_pk_{entity_id}")
            except Exception:
                pass

        # 2. Legacy vault manager
        if not private_key and self.use_vault and self.vault_manager:
            private_key = self.vault_manager.get_agent_private_key(entity_id)

        # 3. Legacy .env file
        if not private_key:
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
