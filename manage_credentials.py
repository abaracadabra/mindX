#!/usr/bin/env python3
"""
BANKON Vault — CLI credential manager for mindX

Usage:
  python manage_credentials.py store <provider_id> <value>
  python manage_credentials.py list
  python manage_credentials.py delete <provider_id>
  python manage_credentials.py providers
  python manage_credentials.py load         # Load vault → environment (for testing)

Examples:
  python manage_credentials.py store gemini_api_key AIzaSy...
  python manage_credentials.py store groq_api_key gsk_...
  python manage_credentials.py store mindx_api_keys "key1,key2,key3"
  python manage_credentials.py list
  python manage_credentials.py providers
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mindx_backend_service.bankon_vault.vault import BankonVault
from mindx_backend_service.bankon_vault.credential_provider import (
    CredentialProvider,
    PROVIDER_ENV_MAP,
)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1]
    vault = BankonVault()
    provider = CredentialProvider(vault)

    if command == "store":
        if len(sys.argv) < 4:
            print("Usage: manage_credentials.py store <provider_id> <value>")
            sys.exit(1)
        provider_id = sys.argv[2]
        value = sys.argv[3]
        try:
            provider.store_credential(provider_id, value)
            env_var = PROVIDER_ENV_MAP.get(provider_id, "?")
            print(f"Stored: {provider_id} → {env_var} (AES-256-GCM encrypted)")
        except ValueError as e:
            print(f"Error: {e}")
            sys.exit(1)

    elif command == "list":
        entries = provider.list_credentials()
        if not entries:
            print("Vault empty — no credentials stored")
        else:
            print(f"{'ID':<30} {'Context':<12} {'Accessed':<10}")
            print("-" * 52)
            for e in entries:
                print(f"{e['id']:<30} {e['context']:<12} {e['access_count']}x")

    elif command == "delete":
        if len(sys.argv) < 3:
            print("Usage: manage_credentials.py delete <provider_id>")
            sys.exit(1)
        provider_id = sys.argv[2]
        result = provider.remove_credential(provider_id)
        if result:
            print(f"Deleted: {provider_id}")
        else:
            print(f"Not found: {provider_id}")

    elif command == "providers":
        print(f"{'Provider ID':<30} {'Environment Variable':<40}")
        print("-" * 70)
        for pid, env_var in sorted(PROVIDER_ENV_MAP.items()):
            print(f"{pid:<30} {env_var:<40}")

    elif command == "load":
        results = provider.load_from_vault()
        loaded = [k for k, v in results.items() if v]
        missing = [k for k, v in results.items() if not v]
        if loaded:
            print(f"Loaded {len(loaded)} credentials:")
            for k in loaded:
                print(f"  + {k} → {PROVIDER_ENV_MAP[k]}")
        if missing:
            print(f"\nNot configured ({len(missing)}):")
            for k in missing:
                print(f"  - {k}")

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
