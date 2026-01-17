# mindx_backend_service/vault_manager.py
"""
Vault Manager for secure credential storage.

Manages private keys, database credentials, and other sensitive data
in the vault folder structure.
"""

import os
import json
import stat
from pathlib import Path
from typing import Dict, Optional, List, Any
from dotenv import load_dotenv, set_key, unset_key

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

VAULT_ROOT = PROJECT_ROOT / "mindx_backend_service" / "vault"
VAULT_AGENTS = VAULT_ROOT / "agents"
VAULT_POSTGRESQL = VAULT_ROOT / "postgresql"
VAULT_SECRETS = VAULT_ROOT / "secrets"


class VaultManager:
    """Manages secure credential storage in vault folder."""
    
    def __init__(self):
        self.vault_root = VAULT_ROOT
        self._ensure_vault_structure()
    
    def _ensure_vault_structure(self):
        """Ensure vault directory structure exists with proper permissions."""
        try:
            for directory in [VAULT_ROOT, VAULT_AGENTS, VAULT_POSTGRESQL, VAULT_SECRETS]:
                directory.mkdir(parents=True, exist_ok=True)
                if os.name != 'nt':
                    os.chmod(directory, stat.S_IRWXU)
            logger.info(f"Vault structure ensured at {VAULT_ROOT}")
        except Exception as e:
            logger.error(f"Failed to create vault structure: {e}", exc_info=True)
            raise
    
    def store_agent_private_key(self, agent_id: str, private_key: str) -> bool:
        """
        Store agent private key in vault.
        
        Args:
            agent_id: Agent identifier
            private_key: Private key to store
            
        Returns:
            True if successful
        """
        try:
            env_file = VAULT_AGENTS / ".agent_keys.env"
            env_var_name = f"MINDX_WALLET_PK_{agent_id.upper().replace('-', '_').replace('.', '_')}"
            
            if not env_file.exists():
                env_file.touch()
                if os.name != 'nt':
                    os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)
            
            if set_key(env_file, env_var_name, private_key, quote_mode='never'):
                logger.info(f"Stored private key for agent {agent_id} in vault")
                return True
            else:
                logger.error(f"Failed to store private key for agent {agent_id}")
                return False
        except Exception as e:
            logger.error(f"Error storing agent private key: {e}", exc_info=True)
            return False
    
    def get_agent_private_key(self, agent_id: str) -> Optional[str]:
        """Retrieve agent private key from vault."""
        try:
            env_file = VAULT_AGENTS / ".agent_keys.env"
            if not env_file.exists():
                return None
            
            env_var_name = f"MINDX_WALLET_PK_{agent_id.upper().replace('-', '_').replace('.', '_')}"
            load_dotenv(dotenv_path=env_file, override=True)
            return os.getenv(env_var_name)
        except Exception as e:
            logger.error(f"Error retrieving agent private key: {e}", exc_info=True)
            return None
    
    def list_agent_keys(self) -> List[Dict[str, str]]:
        """List all agent keys stored in vault."""
        try:
            env_file = VAULT_AGENTS / ".agent_keys.env"
            if not env_file.exists():
                return []
            
            load_dotenv(dotenv_path=env_file, override=True)
            keys = []
            for key, value in os.environ.items():
                if key.startswith("MINDX_WALLET_PK_"):
                    agent_id = key.replace("MINDX_WALLET_PK_", "").lower().replace("_", "-")
                    keys.append({
                        "agent_id": agent_id,
                        "env_var": key,
                        "has_key": bool(value)
                    })
            return keys
        except Exception as e:
            logger.error(f"Error listing agent keys: {e}", exc_info=True)
            return []
    
    def store_postgresql_config(self, config: Dict[str, Any]) -> bool:
        """
        Store PostgreSQL configuration in vault.
        
        Args:
            config: Dictionary with host, port, database, user, password
            
        Returns:
            True if successful
        """
        try:
            config_file = VAULT_POSTGRESQL / "config.json"
            # Don't store password in JSON, use env file
            safe_config = {
                "host": config.get("host", "localhost"),
                "port": config.get("port", 5432),
                "database": config.get("database", "mindx_memory"),
                "user": config.get("user", "mindx")
            }
            
            with open(config_file, 'w') as f:
                json.dump(safe_config, f, indent=2)
            
            if os.name != 'nt':
                os.chmod(config_file, stat.S_IRUSR | stat.S_IWUSR)
            
            # Store password in env file
            if "password" in config:
                env_file = VAULT_POSTGRESQL / ".credentials.env"
                if not env_file.exists():
                    env_file.touch()
                    if os.name != 'nt':
                        os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)
                
                set_key(env_file, "MINDX_DB_PASSWORD", config["password"], quote_mode='never')
            
            logger.info("Stored PostgreSQL configuration in vault")
            return True
        except Exception as e:
            logger.error(f"Error storing PostgreSQL config: {e}", exc_info=True)
            return False
    
    def get_postgresql_config(self) -> Dict[str, Any]:
        """Retrieve PostgreSQL configuration from vault."""
        try:
            config_file = VAULT_POSTGRESQL / "config.json"
            if not config_file.exists():
                return {}
            
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Load password from env file
            env_file = VAULT_POSTGRESQL / ".credentials.env"
            if env_file.exists():
                load_dotenv(dotenv_path=env_file, override=True)
                password = os.getenv("MINDX_DB_PASSWORD")
                if password:
                    config["password"] = password
            
            return config
        except Exception as e:
            logger.error(f"Error retrieving PostgreSQL config: {e}", exc_info=True)
            return {}
    
    def migrate_keys_from_legacy(self, legacy_env_path: Path) -> Dict[str, Any]:
        """
        Migrate keys from legacy .wallet_keys.env to vault.
        
        Args:
            legacy_env_path: Path to legacy .wallet_keys.env file
            
        Returns:
            Migration result with counts
        """
        result = {
            "migrated": 0,
            "failed": 0,
            "errors": []
        }
        
        try:
            if not legacy_env_path.exists():
                logger.warning(f"Legacy env file not found: {legacy_env_path}")
                return result
            
            load_dotenv(dotenv_path=legacy_env_path, override=True)
            
            # Find all MINDX_WALLET_PK_* keys
            for key, value in os.environ.items():
                if key.startswith("MINDX_WALLET_PK_"):
                    agent_id = key.replace("MINDX_WALLET_PK_", "").lower().replace("_", "-")
                    if self.store_agent_private_key(agent_id, value):
                        result["migrated"] += 1
                    else:
                        result["failed"] += 1
                        result["errors"].append(f"Failed to migrate key for {agent_id}")
            
            logger.info(f"Migration complete: {result['migrated']} migrated, {result['failed']} failed")
            return result
        except Exception as e:
            logger.error(f"Error during migration: {e}", exc_info=True)
            result["errors"].append(str(e))
            return result


# Singleton instance
_vault_manager_instance: Optional[VaultManager] = None

def get_vault_manager() -> VaultManager:
    """Get singleton VaultManager instance."""
    global _vault_manager_instance
    if _vault_manager_instance is None:
        _vault_manager_instance = VaultManager()
    return _vault_manager_instance
