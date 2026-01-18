# mindx_backend_service/vault_manager.py
"""
Vault Manager for secure credential storage.

Manages private keys, database credentials, and other sensitive data
in the vault folder structure.
"""

import os
import json
import stat
import hashlib
from pathlib import Path
from typing import Dict, Optional, List, Any
from datetime import datetime, timedelta
from dotenv import load_dotenv, set_key, unset_key

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

VAULT_ROOT = PROJECT_ROOT / "mindx_backend_service" / "vault"
VAULT_AGENTS = VAULT_ROOT / "agents"
VAULT_POSTGRESQL = VAULT_ROOT / "postgresql"
VAULT_SECRETS = VAULT_ROOT / "secrets"
VAULT_CREDENTIALS = VAULT_ROOT / "credentials"  # Access credentials (API keys, tokens)
VAULT_ACCESS_LOG = VAULT_ROOT / "access_log"  # URL and IP access tracking


class VaultManager:
    """Manages secure credential storage in vault folder."""
    
    def __init__(self):
        self.vault_root = VAULT_ROOT
        self._ensure_vault_structure()
    
    def _ensure_vault_structure(self):
        """Ensure vault directory structure exists with proper permissions."""
        try:
            for directory in [VAULT_ROOT, VAULT_AGENTS, VAULT_POSTGRESQL, VAULT_SECRETS, 
                             VAULT_CREDENTIALS, VAULT_ACCESS_LOG]:
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
    
    # ================================
    # ACCESS CREDENTIALS MANAGEMENT
    # ================================
    
    def store_access_credential(
        self,
        credential_id: str,
        credential_type: str,
        credential_value: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store access credential (API key, token, etc.) in vault.
        
        Args:
            credential_id: Unique identifier for the credential
            credential_type: Type of credential (api_key, token, oauth_token, etc.)
            credential_value: The actual credential value
            metadata: Additional metadata (provider, scope, expiry, etc.)
            
        Returns:
            True if successful
        """
        try:
            # Create hash of credential for storage
            credential_hash = hashlib.sha256(credential_value.encode()).hexdigest()[:16]
            
            # Store credential in env file (secure)
            env_file = VAULT_CREDENTIALS / ".credentials.env"
            env_var_name = f"MINDX_CRED_{credential_id.upper().replace('-', '_').replace('.', '_')}"
            
            if not env_file.exists():
                env_file.touch()
                if os.name != 'nt':
                    os.chmod(env_file, stat.S_IRUSR | stat.S_IWUSR)
            
            if not set_key(env_file, env_var_name, credential_value, quote_mode='never'):
                logger.error(f"Failed to store credential {credential_id}")
                return False
            
            # Store metadata in JSON file
            metadata_file = VAULT_CREDENTIALS / f"{credential_id}.json"
            credential_metadata = {
                "credential_id": credential_id,
                "credential_type": credential_type,
                "credential_hash": credential_hash,
                "env_var": env_var_name,
                "created_at": datetime.now().isoformat(),
                "last_used": None,
                "use_count": 0,
                "metadata": metadata or {}
            }
            
            # Load existing if exists to preserve last_used and use_count
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        existing = json.load(f)
                    credential_metadata["last_used"] = existing.get("last_used")
                    credential_metadata["use_count"] = existing.get("use_count", 0)
                except:
                    pass
            
            with open(metadata_file, 'w') as f:
                json.dump(credential_metadata, f, indent=2)
            
            if os.name != 'nt':
                os.chmod(metadata_file, stat.S_IRUSR | stat.S_IWUSR)
            
            logger.info(f"Stored access credential {credential_id} ({credential_type}) in vault")
            return True
        except Exception as e:
            logger.error(f"Error storing access credential: {e}", exc_info=True)
            return False
    
    def get_access_credential(self, credential_id: str, mark_used: bool = True) -> Optional[str]:
        """
        Retrieve access credential from vault.
        
        Args:
            credential_id: Unique identifier for the credential
            mark_used: Whether to update last_used timestamp
            
        Returns:
            Credential value or None if not found
        """
        try:
            env_file = VAULT_CREDENTIALS / ".credentials.env"
            if not env_file.exists():
                return None
            
            env_var_name = f"MINDX_CRED_{credential_id.upper().replace('-', '_').replace('.', '_')}"
            load_dotenv(dotenv_path=env_file, override=True)
            credential_value = os.getenv(env_var_name)
            
            if credential_value and mark_used:
                # Update metadata
                metadata_file = VAULT_CREDENTIALS / f"{credential_id}.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                        metadata["last_used"] = datetime.now().isoformat()
                        metadata["use_count"] = metadata.get("use_count", 0) + 1
                        with open(metadata_file, 'w') as f:
                            json.dump(metadata, f, indent=2)
                    except Exception as e:
                        logger.warning(f"Failed to update credential metadata: {e}")
            
            return credential_value
        except Exception as e:
            logger.error(f"Error retrieving access credential: {e}", exc_info=True)
            return None
    
    def list_access_credentials(self) -> List[Dict[str, Any]]:
        """List all access credentials stored in vault."""
        try:
            credentials = []
            for metadata_file in VAULT_CREDENTIALS.glob("*.json"):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    # Don't include actual credential value
                    safe_metadata = {
                        "credential_id": metadata.get("credential_id"),
                        "credential_type": metadata.get("credential_type"),
                        "created_at": metadata.get("created_at"),
                        "last_used": metadata.get("last_used"),
                        "use_count": metadata.get("use_count", 0),
                        "metadata": metadata.get("metadata", {})
                    }
                    credentials.append(safe_metadata)
                except Exception as e:
                    logger.warning(f"Failed to load credential metadata {metadata_file}: {e}")
                    continue
            return credentials
        except Exception as e:
            logger.error(f"Error listing access credentials: {e}", exc_info=True)
            return []
    
    # ================================
    # URL AND IP ACCESS TRACKING
    # ================================
    
    def log_url_access(
        self,
        url: str,
        ip_address: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log URL access for ML inference tracking.
        
        Args:
            url: The URL that was accessed
            ip_address: IP address of the access point
            agent_id: Agent that made the access
            metadata: Additional metadata (response_time, status_code, etc.)
            
        Returns:
            True if successful
        """
        try:
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y%m%d")
            
            # Create daily log file
            log_file = VAULT_ACCESS_LOG / f"url_access_{date_str}.jsonl"
            
            # Create access record
            access_record = {
                "timestamp": timestamp.isoformat(),
                "url": url,
                "ip_address": ip_address,
                "agent_id": agent_id,
                "metadata": metadata or {}
            }
            
            # Append to JSONL file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(access_record) + '\n')
            
            # Update URL index for quick lookup
            self._update_url_index(url, ip_address, timestamp)
            
            logger.debug(f"Logged URL access: {url} from {ip_address}")
            return True
        except Exception as e:
            logger.error(f"Error logging URL access: {e}", exc_info=True)
            return False
    
    def _update_url_index(self, url: str, ip_address: Optional[str], timestamp: datetime):
        """Update URL index for quick lookup."""
        try:
            index_file = VAULT_ACCESS_LOG / "url_index.json"
            
            # Load existing index
            url_index = {}
            if index_file.exists():
                try:
                    with open(index_file, 'r') as f:
                        url_index = json.load(f)
                except:
                    url_index = {}
            
            # Update index
            if url not in url_index:
                url_index[url] = {
                    "first_seen": timestamp.isoformat(),
                    "last_seen": timestamp.isoformat(),
                    "access_count": 0,
                    "ip_addresses": set(),
                    "agents": set()
                }
            
            url_index[url]["last_seen"] = timestamp.isoformat()
            url_index[url]["access_count"] = url_index[url].get("access_count", 0) + 1
            
            if ip_address:
                if "ip_addresses" not in url_index[url]:
                    url_index[url]["ip_addresses"] = set()
                url_index[url]["ip_addresses"].add(ip_address)
            
            # Convert sets to lists for JSON serialization
            for url_key in url_index:
                if isinstance(url_index[url_key].get("ip_addresses"), set):
                    url_index[url_key]["ip_addresses"] = list(url_index[url_key]["ip_addresses"])
                if isinstance(url_index[url_key].get("agents"), set):
                    url_index[url_key]["agents"] = list(url_index[url_key]["agents"])
            
            # Save index
            with open(index_file, 'w') as f:
                json.dump(url_index, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update URL index: {e}")
    
    def log_ip_access(
        self,
        ip_address: str,
        url: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Log IP access point for ML inference tracking.
        
        Args:
            ip_address: IP address that was accessed
            url: URL associated with the IP access
            agent_id: Agent that made the access
            metadata: Additional metadata (port, protocol, etc.)
            
        Returns:
            True if successful
        """
        try:
            timestamp = datetime.now()
            date_str = timestamp.strftime("%Y%m%d")
            
            # Create daily log file
            log_file = VAULT_ACCESS_LOG / f"ip_access_{date_str}.jsonl"
            
            # Create access record
            access_record = {
                "timestamp": timestamp.isoformat(),
                "ip_address": ip_address,
                "url": url,
                "agent_id": agent_id,
                "metadata": metadata or {}
            }
            
            # Append to JSONL file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(access_record) + '\n')
            
            # Update IP index
            self._update_ip_index(ip_address, url, timestamp)
            
            logger.debug(f"Logged IP access: {ip_address}")
            return True
        except Exception as e:
            logger.error(f"Error logging IP access: {e}", exc_info=True)
            return False
    
    def _update_ip_index(self, ip_address: str, url: Optional[str], timestamp: datetime):
        """Update IP index for quick lookup."""
        try:
            index_file = VAULT_ACCESS_LOG / "ip_index.json"
            
            # Load existing index
            ip_index = {}
            if index_file.exists():
                try:
                    with open(index_file, 'r') as f:
                        ip_index = json.load(f)
                except:
                    ip_index = {}
            
            # Update index
            if ip_address not in ip_index:
                ip_index[ip_address] = {
                    "first_seen": timestamp.isoformat(),
                    "last_seen": timestamp.isoformat(),
                    "access_count": 0,
                    "urls": set(),
                    "agents": set()
                }
            
            ip_index[ip_address]["last_seen"] = timestamp.isoformat()
            ip_index[ip_address]["access_count"] = ip_index[ip_address].get("access_count", 0) + 1
            
            if url:
                if "urls" not in ip_index[ip_address]:
                    ip_index[ip_address]["urls"] = set()
                ip_index[ip_address]["urls"].add(url)
            
            # Convert sets to lists for JSON serialization
            for ip_key in ip_index:
                if isinstance(ip_index[ip_key].get("urls"), set):
                    ip_index[ip_key]["urls"] = list(ip_index[ip_key]["urls"])
                if isinstance(ip_index[ip_key].get("agents"), set):
                    ip_index[ip_key]["agents"] = list(ip_index[ip_key]["agents"])
            
            # Save index
            with open(index_file, 'w') as f:
                json.dump(ip_index, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to update IP index: {e}")
    
    def get_url_access_history(
        self,
        url: Optional[str] = None,
        days_back: int = 7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get URL access history for ML inference.
        
        Args:
            url: Optional URL to filter by
            days_back: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            List of access records
        """
        try:
            records = []
            for day_offset in range(days_back):
                date_str = (datetime.now() - timedelta(days=day_offset)).strftime("%Y%m%d")
                log_file = VAULT_ACCESS_LOG / f"url_access_{date_str}.jsonl"
                
                if not log_file.exists():
                    continue
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if len(records) >= limit:
                            break
                        try:
                            record = json.loads(line.strip())
                            if url is None or record.get("url") == url:
                                records.append(record)
                        except:
                            continue
                
                if len(records) >= limit:
                    break
            
            return records[:limit]
        except Exception as e:
            logger.error(f"Error getting URL access history: {e}", exc_info=True)
            return []
    
    def get_ip_access_history(
        self,
        ip_address: Optional[str] = None,
        days_back: int = 7,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get IP access history for ML inference.
        
        Args:
            ip_address: Optional IP address to filter by
            days_back: Number of days to look back
            limit: Maximum number of records to return
            
        Returns:
            List of access records
        """
        try:
            records = []
            for day_offset in range(days_back):
                date_str = (datetime.now() - timedelta(days=day_offset)).strftime("%Y%m%d")
                log_file = VAULT_ACCESS_LOG / f"ip_access_{date_str}.jsonl"
                
                if not log_file.exists():
                    continue
                
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if len(records) >= limit:
                            break
                        try:
                            record = json.loads(line.strip())
                            if ip_address is None or record.get("ip_address") == ip_address:
                                records.append(record)
                        except:
                            continue
                
                if len(records) >= limit:
                    break
            
            return records[:limit]
        except Exception as e:
            logger.error(f"Error getting IP access history: {e}", exc_info=True)
            return []
    
    def get_access_summary_for_inference(self) -> Dict[str, Any]:
        """
        Get comprehensive access summary for ML inference.
        
        Returns:
            Dictionary with URLs, IPs, and statistics
        """
        try:
            # Load indices
            url_index_file = VAULT_ACCESS_LOG / "url_index.json"
            ip_index_file = VAULT_ACCESS_LOG / "ip_index.json"
            
            url_index = {}
            if url_index_file.exists():
                try:
                    with open(url_index_file, 'r') as f:
                        url_index = json.load(f)
                except:
                    pass
            
            ip_index = {}
            if ip_index_file.exists():
                try:
                    with open(ip_index_file, 'r') as f:
                        ip_index = json.load(f)
                except:
                    pass
            
            return {
                "timestamp": datetime.now().isoformat(),
                "urls": {
                    "total_unique": len(url_index),
                    "index": url_index
                },
                "ip_addresses": {
                    "total_unique": len(ip_index),
                    "index": ip_index
                },
                "statistics": {
                    "total_url_accesses": sum(u.get("access_count", 0) for u in url_index.values()),
                    "total_ip_accesses": sum(i.get("access_count", 0) for i in ip_index.values()),
                    "most_accessed_urls": sorted(
                        [(url, data.get("access_count", 0)) for url, data in url_index.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:10],
                    "most_accessed_ips": sorted(
                        [(ip, data.get("access_count", 0)) for ip, data in ip_index.items()],
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                }
            }
        except Exception as e:
            logger.error(f"Error getting access summary: {e}", exc_info=True)
            return {"error": str(e)}


# Singleton instance
_vault_manager_instance: Optional[VaultManager] = None

def get_vault_manager() -> VaultManager:
    """Get singleton VaultManager instance."""
    global _vault_manager_instance
    if _vault_manager_instance is None:
        _vault_manager_instance = VaultManager()
    return _vault_manager_instance
