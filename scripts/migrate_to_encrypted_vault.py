#!/usr/bin/env python3
"""
Migration Script: Plaintext to Encrypted Vault
Migrates API keys and wallet keys from plaintext .env files to encrypted vault storage
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from mindx_backend_service.encrypted_vault_manager import get_encrypted_vault_manager
from utils.logging_config import setup_logging, get_logger
from utils.config import PROJECT_ROOT

# Setup logging
setup_logging()
logger = get_logger(__name__)

class VaultMigrationTool:
    """Tool for migrating secrets to encrypted vault"""

    def __init__(self):
        self.vault = get_encrypted_vault_manager()
        self.migration_log = []

    def log_migration(self, action: str, item: str, status: str, details: str = ""):
        """Log migration action"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "item": item,
            "status": status,
            "details": details
        }
        self.migration_log.append(entry)
        logger.info(f"Migration {action}: {item} - {status} {details}")

    def backup_plaintext_files(self, files: list) -> Path:
        """Create backup of plaintext files before migration"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = PROJECT_ROOT / "data" / "migration_backups" / timestamp
        backup_dir.mkdir(parents=True, exist_ok=True)

        for file_path in files:
            if file_path.exists():
                backup_file = backup_dir / file_path.name
                backup_file.write_text(file_path.read_text())
                self.log_migration("BACKUP", str(file_path), "SUCCESS", f"-> {backup_file}")

        self.log_migration("BACKUP", "Complete", "SUCCESS", f"Backup directory: {backup_dir}")
        return backup_dir

    def migrate_main_env_file(self) -> int:
        """Migrate API keys from main .env file"""
        env_file = PROJECT_ROOT / ".env"
        migrated_count = 0

        if not env_file.exists():
            self.log_migration("MIGRATE_API", "main .env", "SKIP", "File not found")
            return 0

        try:
            with open(env_file, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if '=' not in line or line.startswith('#'):
                    continue

                key, value = line.split('=', 1)
                value = value.strip('"\'')

                # Skip empty values or placeholder values
                if not value or value in ["YOUR_API_KEY_HERE", "REPLACE_WITH_FRESH_GEMINI_KEY"]:
                    continue

                # Map environment variable names to provider names
                provider_mapping = {
                    "GEMINI_API_KEY": "gemini",
                    "GROQ_API_KEY": "groq",
                    "OPENAI_API_KEY": "openai",
                    "ANTHROPIC_API_KEY": "anthropic",
                    "MISTRAL_API_KEY": "mistral",
                    "TOGETHER_API_KEY": "together"
                }

                if key in provider_mapping:
                    provider = provider_mapping[key]
                    if self.vault.store_api_key(provider, value):
                        self.log_migration("MIGRATE_API", f"{provider} API key", "SUCCESS")
                        migrated_count += 1
                    else:
                        self.log_migration("MIGRATE_API", f"{provider} API key", "FAILED")

        except Exception as e:
            self.log_migration("MIGRATE_API", "main .env", "ERROR", str(e))

        return migrated_count

    def migrate_wallet_keys_file(self, wallet_file: Path = None) -> int:
        """Migrate wallet keys from .wallet_keys.env file"""
        if wallet_file is None:
            wallet_file = PROJECT_ROOT / "data" / "identity" / ".wallet_keys.env"

        migrated_count = 0

        if not wallet_file.exists():
            self.log_migration("MIGRATE_WALLET", str(wallet_file), "SKIP", "File not found")
            return 0

        try:
            with open(wallet_file, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if '=' not in line or line.startswith('#'):
                    continue

                key, value = line.split('=', 1)
                value = value.strip('"\'')

                if key.startswith('MINDX_WALLET_PK_'):
                    agent_id = key.replace('MINDX_WALLET_PK_', '').lower()

                    try:
                        # Derive public address from private key
                        from eth_account import Account
                        if hasattr(Account, 'enable_unaudited_hdwallet_features'):
                            Account.enable_unaudited_hdwallet_features()

                        account = Account.from_key(value)
                        public_address = account.address

                        if self.vault.store_wallet_key(agent_id, value, public_address):
                            self.log_migration("MIGRATE_WALLET", f"{agent_id} wallet", "SUCCESS", public_address)
                            migrated_count += 1
                        else:
                            self.log_migration("MIGRATE_WALLET", f"{agent_id} wallet", "FAILED")

                    except Exception as e:
                        self.log_migration("MIGRATE_WALLET", f"{agent_id} wallet", "ERROR", str(e))

        except Exception as e:
            self.log_migration("MIGRATE_WALLET", str(wallet_file), "ERROR", str(e))

        return migrated_count

    def verify_migration(self) -> bool:
        """Verify that migration was successful"""
        verification_passed = True

        try:
            # Verify API keys
            api_providers = self.vault.list_api_providers()
            for provider in api_providers:
                api_key = self.vault.get_api_key(provider)
                if api_key:
                    self.log_migration("VERIFY_API", provider, "SUCCESS", "Key retrieved successfully")
                else:
                    self.log_migration("VERIFY_API", provider, "FAILED", "Could not retrieve key")
                    verification_passed = False

            # Verify wallet keys
            wallet_agents = self.vault.list_wallet_agents()
            for agent_id in wallet_agents:
                wallet_data = self.vault.get_wallet_key(agent_id)
                if wallet_data and wallet_data.get("private_key") and wallet_data.get("public_address"):
                    self.log_migration("VERIFY_WALLET", agent_id, "SUCCESS", wallet_data["public_address"])
                else:
                    self.log_migration("VERIFY_WALLET", agent_id, "FAILED", "Could not retrieve wallet data")
                    verification_passed = False

        except Exception as e:
            self.log_migration("VERIFY", "migration", "ERROR", str(e))
            verification_passed = False

        return verification_passed

    def create_secure_config_file(self) -> Path:
        """Create secure configuration file template"""
        config_template = self.vault.create_secure_config_template()
        secure_config_file = PROJECT_ROOT / ".env.production.template"

        with open(secure_config_file, 'w') as f:
            f.write(config_template)

        self.log_migration("CREATE", "secure config template", "SUCCESS", str(secure_config_file))
        return secure_config_file

    def save_migration_log(self) -> Path:
        """Save migration log to file"""
        import json

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = PROJECT_ROOT / "data" / "migration_logs" / f"vault_migration_{timestamp}.json"
        log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(log_file, 'w') as f:
            json.dump(self.migration_log, f, indent=2)

        logger.info(f"Migration log saved to: {log_file}")
        return log_file

    def run_full_migration(self, backup: bool = True) -> dict:
        """Run complete migration process"""
        migration_result = {
            "started_at": datetime.utcnow().isoformat(),
            "api_keys_migrated": 0,
            "wallet_keys_migrated": 0,
            "backup_directory": None,
            "verification_passed": False,
            "secure_config_file": None,
            "migration_log_file": None
        }

        try:
            logger.info("=== Starting Full Vault Migration ===")

            # Step 1: Backup existing files
            if backup:
                files_to_backup = [
                    PROJECT_ROOT / ".env",
                    PROJECT_ROOT / "data" / "identity" / ".wallet_keys.env"
                ]
                migration_result["backup_directory"] = str(self.backup_plaintext_files(files_to_backup))

            # Step 2: Migrate API keys
            migration_result["api_keys_migrated"] = self.migrate_main_env_file()

            # Step 3: Migrate wallet keys
            migration_result["wallet_keys_migrated"] = self.migrate_wallet_keys_file()

            # Step 4: Verify migration
            migration_result["verification_passed"] = self.verify_migration()

            # Step 5: Create secure config template
            migration_result["secure_config_file"] = str(self.create_secure_config_file())

            # Step 6: Save migration log
            migration_result["migration_log_file"] = str(self.save_migration_log())

            migration_result["completed_at"] = datetime.utcnow().isoformat()

            logger.info("=== Vault Migration Completed ===")
            logger.info(f"API Keys Migrated: {migration_result['api_keys_migrated']}")
            logger.info(f"Wallet Keys Migrated: {migration_result['wallet_keys_migrated']}")
            logger.info(f"Verification Passed: {migration_result['verification_passed']}")

            return migration_result

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            migration_result["error"] = str(e)
            migration_result["completed_at"] = datetime.utcnow().isoformat()
            return migration_result

def main():
    """Main migration script entry point"""
    parser = argparse.ArgumentParser(description="Migrate mindX secrets to encrypted vault")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating backup of original files")
    parser.add_argument("--api-keys-only", action="store_true", help="Migrate only API keys")
    parser.add_argument("--wallet-keys-only", action="store_true", help="Migrate only wallet keys")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing encrypted vault")
    parser.add_argument("--wallet-file", type=Path, help="Custom path to wallet keys file")

    args = parser.parse_args()

    migration_tool = VaultMigrationTool()

    if args.verify_only:
        print("=== Verifying Encrypted Vault ===")
        if migration_tool.verify_migration():
            print("✅ Vault verification passed")
            sys.exit(0)
        else:
            print("❌ Vault verification failed")
            sys.exit(1)

    elif args.api_keys_only:
        print("=== Migrating API Keys Only ===")
        count = migration_tool.migrate_main_env_file()
        print(f"✅ Migrated {count} API keys")

    elif args.wallet_keys_only:
        print("=== Migrating Wallet Keys Only ===")
        count = migration_tool.migrate_wallet_keys_file(args.wallet_file)
        print(f"✅ Migrated {count} wallet keys")

    else:
        print("=== Full Migration ===")
        result = migration_tool.run_full_migration(backup=not args.no_backup)

        if result.get("verification_passed"):
            print("✅ Migration completed successfully!")
        else:
            print("⚠️  Migration completed with warnings - check logs")

        print(f"\nMigration Summary:")
        print(f"  API Keys: {result['api_keys_migrated']}")
        print(f"  Wallet Keys: {result['wallet_keys_migrated']}")
        print(f"  Verification: {'PASSED' if result['verification_passed'] else 'FAILED'}")
        print(f"  Log File: {result.get('migration_log_file', 'N/A')}")

        if result.get("backup_directory"):
            print(f"  Backup: {result['backup_directory']}")

        if result.get("secure_config_file"):
            print(f"  Secure Config Template: {result['secure_config_file']}")

if __name__ == "__main__":
    main()