"""
Enhanced Encrypted Vault Manager for mindX Production
Provides encrypted storage for API keys, private keys, and sensitive configuration
"""

import os
import re
import json
import stat
import hmac
import base64
import secrets
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta, timezone
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from utils.config import PROJECT_ROOT, Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

class EncryptedVaultManager:
    """Production-grade encrypted vault for sensitive data storage"""

    def __init__(self):
        self.config = Config()
        self.vault_root = PROJECT_ROOT / "mindx_backend_service" / "vault_encrypted"
        self.key_derivation_salt_file = self.vault_root / ".salt"
        self.master_key_file = self.vault_root / ".master.key"

        # Initialize vault structure
        self._ensure_vault_structure()
        self._ensure_encryption_keys()

        # Encryption instances
        self._master_fernet = None
        self._api_fernet = None
        self._wallet_fernet = None

    def _ensure_vault_structure(self):
        """Create encrypted vault directory structure with strict permissions"""
        directories = [
            self.vault_root,
            self.vault_root / "api_keys",
            self.vault_root / "wallet_keys",
            self.vault_root / "agent_configs",
            self.vault_root / "sessions",
            self.vault_root / "user_folders",
            self.vault_root / "system_configs"
        ]

        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            if os.name != 'nt':
                # Owner read/write/execute only
                os.chmod(directory, stat.S_IRWXU)

        logger.info(f"Encrypted vault structure initialized at {self.vault_root}")

    def _ensure_encryption_keys(self):
        """Initialize or load encryption keys"""
        if not self.key_derivation_salt_file.exists():
            # Generate new salt for key derivation
            salt = secrets.token_bytes(32)
            with open(self.key_derivation_salt_file, 'wb') as f:
                f.write(salt)
            os.chmod(self.key_derivation_salt_file, stat.S_IRUSR | stat.S_IWUSR)
            logger.info("Generated new key derivation salt")

        if not self.master_key_file.exists():
            # Generate new master key
            master_key = Fernet.generate_key()
            with open(self.master_key_file, 'wb') as f:
                f.write(master_key)
            os.chmod(self.master_key_file, stat.S_IRUSR | stat.S_IWUSR)
            logger.info("Generated new master encryption key")

    def _get_salt(self) -> bytes:
        """Get key derivation salt"""
        with open(self.key_derivation_salt_file, 'rb') as f:
            return f.read()

    def _get_master_key(self) -> bytes:
        """Get master encryption key"""
        with open(self.master_key_file, 'rb') as f:
            return f.read()

    def _derive_key(self, password: str, context: str) -> Fernet:
        """Derive encryption key from password and context"""
        salt = self._get_salt()

        # Combine context with salt for domain separation
        context_salt = hashlib.sha256(salt + context.encode()).digest()

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=context_salt,
            iterations=100000,  # Strong key derivation
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)

    def _get_master_fernet(self) -> Fernet:
        """Get master encryption instance"""
        if self._master_fernet is None:
            master_key = self._get_master_key()
            self._master_fernet = Fernet(master_key)
        return self._master_fernet

    def _get_api_fernet(self) -> Fernet:
        """Get API keys encryption instance"""
        if self._api_fernet is None:
            # Use a derived key for API keys
            master_password = self._get_master_key().decode('latin1')
            self._api_fernet = self._derive_key(master_password, "api_keys_v1")
        return self._api_fernet

    def _get_wallet_fernet(self) -> Fernet:
        """Get wallet keys encryption instance"""
        if self._wallet_fernet is None:
            # Use a different derived key for wallet keys
            master_password = self._get_master_key().decode('latin1')
            self._wallet_fernet = self._derive_key(master_password, "wallet_keys_v1")
        return self._wallet_fernet

    def _encrypt_data(self, data: str, fernet: Fernet) -> str:
        """Encrypt data using provided Fernet instance"""
        return fernet.encrypt(data.encode()).decode()

    def _decrypt_data(self, encrypted_data: str, fernet: Fernet) -> str:
        """Decrypt data using provided Fernet instance"""
        return fernet.decrypt(encrypted_data.encode()).decode()

    def store_api_key(self, provider: str, api_key: str) -> bool:
        """Store encrypted API key"""
        try:
            api_keys_file = self.vault_root / "api_keys" / "keys.enc"

            # Load existing keys or create new dict
            keys_dict = {}
            if api_keys_file.exists():
                with open(api_keys_file, 'r') as f:
                    encrypted_content = f.read()
                if encrypted_content:
                    try:
                        decrypted_content = self._decrypt_data(encrypted_content, self._get_api_fernet())
                        keys_dict = json.loads(decrypted_content)
                    except Exception as e:
                        logger.warning(f"Could not decrypt existing API keys file: {e}")
                        keys_dict = {}

            # Add/update key
            keys_dict[provider] = {
                "api_key": api_key,
                "updated": datetime.utcnow().isoformat(),
                "provider": provider
            }

            # Encrypt and save
            json_content = json.dumps(keys_dict, indent=2)
            encrypted_content = self._encrypt_data(json_content, self._get_api_fernet())

            with open(api_keys_file, 'w') as f:
                f.write(encrypted_content)

            os.chmod(api_keys_file, stat.S_IRUSR | stat.S_IWUSR)
            logger.info(f"Stored encrypted API key for {provider}")
            return True

        except Exception as e:
            logger.error(f"Failed to store API key for {provider}: {e}", exc_info=True)
            return False

    def get_api_key(self, provider: str) -> Optional[str]:
        """Retrieve decrypted API key"""
        try:
            api_keys_file = self.vault_root / "api_keys" / "keys.enc"

            if not api_keys_file.exists():
                logger.warning(f"API keys file not found")
                return None

            with open(api_keys_file, 'r') as f:
                encrypted_content = f.read()

            if not encrypted_content:
                return None

            decrypted_content = self._decrypt_data(encrypted_content, self._get_api_fernet())
            keys_dict = json.loads(decrypted_content)

            provider_data = keys_dict.get(provider)
            if provider_data:
                return provider_data.get("api_key")

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve API key for {provider}: {e}", exc_info=True)
            return None

    def store_wallet_key(self, agent_id: str, private_key: str, public_address: str) -> bool:
        """Store encrypted wallet private key"""
        try:
            wallet_keys_file = self.vault_root / "wallet_keys" / "keys.enc"

            # Load existing keys or create new dict
            keys_dict = {}
            if wallet_keys_file.exists():
                with open(wallet_keys_file, 'r') as f:
                    encrypted_content = f.read()
                if encrypted_content:
                    try:
                        decrypted_content = self._decrypt_data(encrypted_content, self._get_wallet_fernet())
                        keys_dict = json.loads(decrypted_content)
                    except Exception as e:
                        logger.warning(f"Could not decrypt existing wallet keys file: {e}")
                        keys_dict = {}

            # Add/update wallet key
            keys_dict[agent_id] = {
                "private_key": private_key,
                "public_address": public_address,
                "created": datetime.utcnow().isoformat(),
                "agent_id": agent_id
            }

            # Encrypt and save
            json_content = json.dumps(keys_dict, indent=2)
            encrypted_content = self._encrypt_data(json_content, self._get_wallet_fernet())

            with open(wallet_keys_file, 'w') as f:
                f.write(encrypted_content)

            os.chmod(wallet_keys_file, stat.S_IRUSR | stat.S_IWUSR)
            logger.info(f"Stored encrypted wallet key for agent {agent_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store wallet key for {agent_id}: {e}", exc_info=True)
            return False

    def get_wallet_key(self, agent_id: str) -> Optional[Dict[str, str]]:
        """Retrieve decrypted wallet key data"""
        try:
            wallet_keys_file = self.vault_root / "wallet_keys" / "keys.enc"

            if not wallet_keys_file.exists():
                logger.warning(f"Wallet keys file not found")
                return None

            with open(wallet_keys_file, 'r') as f:
                encrypted_content = f.read()

            if not encrypted_content:
                return None

            decrypted_content = self._decrypt_data(encrypted_content, self._get_wallet_fernet())
            keys_dict = json.loads(decrypted_content)

            return keys_dict.get(agent_id)

        except Exception as e:
            logger.error(f"Failed to retrieve wallet key for {agent_id}: {e}", exc_info=True)
            return None

    def list_api_providers(self) -> List[str]:
        """List all stored API key providers"""
        try:
            api_keys_file = self.vault_root / "api_keys" / "keys.enc"

            if not api_keys_file.exists():
                return []

            with open(api_keys_file, 'r') as f:
                encrypted_content = f.read()

            if not encrypted_content:
                return []

            decrypted_content = self._decrypt_data(encrypted_content, self._get_api_fernet())
            keys_dict = json.loads(decrypted_content)

            return list(keys_dict.keys())

        except Exception as e:
            logger.error(f"Failed to list API providers: {e}", exc_info=True)
            return []

    def list_wallet_agents(self) -> List[str]:
        """List all agents with stored wallet keys"""
        try:
            wallet_keys_file = self.vault_root / "wallet_keys" / "keys.enc"

            if not wallet_keys_file.exists():
                return []

            with open(wallet_keys_file, 'r') as f:
                encrypted_content = f.read()

            if not encrypted_content:
                return []

            decrypted_content = self._decrypt_data(encrypted_content, self._get_wallet_fernet())
            keys_dict = json.loads(decrypted_content)

            return list(keys_dict.keys())

        except Exception as e:
            logger.error(f"Failed to list wallet agents: {e}", exc_info=True)
            return []

    def rotate_encryption_keys(self) -> bool:
        """Rotate encryption keys (emergency use only)"""
        try:
            logger.warning("Starting encryption key rotation - this will invalidate all stored data")

            # Backup current data
            backup_dir = self.vault_root / f"backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            backup_dir.mkdir()

            # Read and decrypt all current data
            api_keys_data = {}
            wallet_keys_data = {}

            try:
                api_keys_file = self.vault_root / "api_keys" / "keys.enc"
                if api_keys_file.exists():
                    with open(api_keys_file, 'r') as f:
                        encrypted_content = f.read()
                    if encrypted_content:
                        decrypted_content = self._decrypt_data(encrypted_content, self._get_api_fernet())
                        api_keys_data = json.loads(decrypted_content)
            except Exception as e:
                logger.error(f"Could not backup API keys: {e}")

            try:
                wallet_keys_file = self.vault_root / "wallet_keys" / "keys.enc"
                if wallet_keys_file.exists():
                    with open(wallet_keys_file, 'r') as f:
                        encrypted_content = f.read()
                    if encrypted_content:
                        decrypted_content = self._decrypt_data(encrypted_content, self._get_wallet_fernet())
                        wallet_keys_data = json.loads(decrypted_content)
            except Exception as e:
                logger.error(f"Could not backup wallet keys: {e}")

            # Generate new keys
            self.key_derivation_salt_file.unlink(missing_ok=True)
            self.master_key_file.unlink(missing_ok=True)
            self._ensure_encryption_keys()

            # Reset encryption instances
            self._master_fernet = None
            self._api_fernet = None
            self._wallet_fernet = None

            # Re-encrypt and store data with new keys
            for provider, data in api_keys_data.items():
                self.store_api_key(provider, data["api_key"])

            for agent_id, data in wallet_keys_data.items():
                self.store_wallet_key(agent_id, data["private_key"], data["public_address"])

            logger.info("Encryption key rotation completed successfully")
            return True

        except Exception as e:
            logger.error(f"Encryption key rotation failed: {e}", exc_info=True)
            return False

    def migrate_from_plaintext(self, plaintext_env_file: Path) -> Tuple[int, int]:
        """Migrate from plaintext .env file to encrypted storage"""
        try:
            if not plaintext_env_file.exists():
                logger.warning(f"Plaintext file not found: {plaintext_env_file}")
                return 0, 0

            migrated_api_keys = 0
            migrated_wallet_keys = 0

            with open(plaintext_env_file, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if '=' not in line or line.startswith('#'):
                    continue

                key, value = line.split('=', 1)
                value = value.strip('"\'')

                # Migrate API keys
                if key.endswith('_API_KEY'):
                    provider = key.replace('_API_KEY', '').lower()
                    if self.store_api_key(provider, value):
                        migrated_api_keys += 1

                # Migrate wallet keys
                elif key.startswith('MINDX_WALLET_PK_'):
                    agent_id = key.replace('MINDX_WALLET_PK_', '').lower()
                    # For migration, we don't have public address, so derive it
                    try:
                        from eth_account import Account
                        account = Account.from_key(value)
                        public_address = account.address
                        if self.store_wallet_key(agent_id, value, public_address):
                            migrated_wallet_keys += 1
                    except Exception as e:
                        logger.error(f"Failed to migrate wallet key {agent_id}: {e}")

            logger.info(f"Migration complete: {migrated_api_keys} API keys, {migrated_wallet_keys} wallet keys")
            return migrated_api_keys, migrated_wallet_keys

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return 0, 0

    def create_secure_config_template(self) -> str:
        """Create a secure configuration template without actual secrets"""
        template = f"""# mindX Production Configuration Template
# Generated: {datetime.utcnow().isoformat()}

# --- Security Configuration ---
MINDX_SECURITY_PRODUCTION_MODE=true
MINDX_SECURITY_DEVELOPMENT_MODE=false
MINDX_SECURITY_ENCRYPTION_ENABLED=true
MINDX_SECURITY_VAULT_PATH={self.vault_root}

# --- API Keys (stored encrypted in vault) ---
# Use the encrypted vault manager to store actual API keys:
# vault.store_api_key("gemini", "YOUR_ACTUAL_GEMINI_KEY")
# vault.store_api_key("groq", "YOUR_ACTUAL_GROQ_KEY")
# vault.store_api_key("openai", "YOUR_ACTUAL_OPENAI_KEY")
# vault.store_api_key("anthropic", "YOUR_ACTUAL_ANTHROPIC_KEY")

# --- Admin Configuration ---
MINDX_SECURITY_ADMIN_ADDRESSES="0x1234...admin1,0x5678...admin2"
MINDX_SECURITY_API_KEYS="secure_api_key_1,secure_api_key_2"

# --- CORS Configuration ---
MINDX_SECURITY_CORS_ALLOWED_ORIGINS="https://agenticplace.pythai.net,https://www.agenticplace.pythai.net"

# --- Rate Limiting ---
MINDX_SECURITY_RATE_LIMIT_ENABLED=true
MINDX_SECURITY_RATE_LIMIT_DEFAULT_REQUESTS=100
MINDX_SECURITY_RATE_LIMIT_DEFAULT_WINDOW=60

# --- Logging Configuration ---
MINDX_LOGGING_LEVEL=INFO
MINDX_LOGGING_FILE_ENABLED=true
MINDX_LOGGING_SECURITY_EVENTS=true

# --- Agent Configuration ---
MINDX_AGENTS_AUTO_REGISTER=false
MINDX_AGENTS_REQUIRE_APPROVAL=true

# --- VPS Configuration ---
MINDX_VPS_DEPLOYMENT=true
MINDX_VPS_HEALTH_CHECK_ENABLED=true
MINDX_VPS_METRICS_ENABLED=true

# DO NOT STORE ACTUAL SECRETS IN THIS FILE
# USE: vault.store_api_key() and vault.store_wallet_key() instead
"""
        return template

# Global instance
_encrypted_vault_instance = None

def get_encrypted_vault_manager() -> EncryptedVaultManager:
    """Get singleton encrypted vault manager instance"""
    global _encrypted_vault_instance
    if _encrypted_vault_instance is None:
        _encrypted_vault_instance = EncryptedVaultManager()
    return _encrypted_vault_instance