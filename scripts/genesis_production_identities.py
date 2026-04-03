#!/usr/bin/env python3
"""
mindX Genesis — Production Identity Generation

Creates fresh cryptographic identities for all core agents and stores them
in the BANKON Vault (AES-256-GCM + HKDF-SHA512). Removes all legacy
plaintext key storage.

This is a one-time operation for production deployment.
Every agent gets a new Ethereum-compatible wallet — a fresh start,
a new sovereign identity for the production civilization.

Usage:
    python scripts/genesis_production_identities.py

What this does:
    1. Generates 12 new Ethereum wallets (one per core agent)
    2. Stores each private key in BANKON Vault (encrypted)
    3. Creates an identity registry (public addresses only)
    4. Removes the legacy plaintext .wallet_keys.env
    5. Clears stale belief system caches
"""

import os
import sys
import json
import stat
import time
from pathlib import Path
from datetime import datetime, timezone

# Add project root
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from eth_account import Account

if hasattr(Account, "enable_unaudited_hdwallet_features"):
    Account.enable_unaudited_hdwallet_features()

from mindx_backend_service.bankon_vault.vault import BankonVault

# ══════════════════════════════════════════════════════════════════
#  THE TWELVE — Core agents of the mindX civilization
# ══════════════════════════════════════════════════════════════════

CORE_AGENTS = [
    {
        "entity_id": "guardian_agent_main",
        "role": "Security Infrastructure — access control, threat detection, identity verification",
    },
    {
        "entity_id": "coordinator_agent_main",
        "role": "Service Bus Kernel — pub/sub routing, task queues, rate limiting",
    },
    {
        "entity_id": "mastermind_prime",
        "role": "Strategic Executive — orchestration center, directive management",
    },
    {
        "entity_id": "mindx_agint",
        "role": "Cognitive Core — P-O-D-A loop, perception-orientation-decision-action",
    },
    {
        "entity_id": "automindx_agent_main",
        "role": "Autonomous Operations — self-directed task execution",
    },
    {
        "entity_id": "sea_for_mastermind",
        "role": "Strategic Evolution — 4-phase audit-driven self-improvement campaigns",
    },
    {
        "entity_id": "blueprint_agent_mindx_v2",
        "role": "Architecture Planning — system design, blueprint generation",
    },
    {
        "entity_id": "ceo_agent_main",
        "role": "Board-Level Governance — strategic planning, resource allocation, shutdown authority",
    },
    {
        "entity_id": "inference_agent_main",
        "role": "Inference Optimization — model selection, provider routing, performance tuning",
    },
    {
        "entity_id": "memory_agent_main",
        "role": "Persistent Memory — STM/LTM promotion, belief system integration",
    },
    {
        "entity_id": "validator_agent_main",
        "role": "Validation Authority — output verification, quality assurance",
    },
    {
        "entity_id": "system_state_tracker",
        "role": "State Observer — system snapshots, health monitoring, metrics",
    },
]


def generate_env_var_name(entity_id: str) -> str:
    """Match IDManagerAgent._generate_env_var_name format."""
    import re
    safe = re.sub(r"\W+", "_", entity_id).upper()
    return f"MINDX_WALLET_PK_{safe}"


def main():
    print("=" * 66)
    print("  mindX Genesis — Production Identity Generation")
    print("  AES-256-GCM + HKDF-SHA512 encrypted vault storage")
    print("=" * 66)
    print()

    # Paths
    vault_dir = project_root / "mindx_backend_service" / "vault_bankon"
    legacy_env = project_root / "data" / "identity" / ".wallet_keys.env"
    registry_path = project_root / "data" / "identity" / "production_registry.json"
    legacy_vault_agents = project_root / "mindx_backend_service" / "vault" / "agents" / ".agent_keys.env"

    # Initialize BANKON Vault
    vault = BankonVault(vault_dir=str(vault_dir))
    vault.unlock_with_key_file()

    registry = {
        "genesis_timestamp": datetime.now(timezone.utc).isoformat(),
        "deployment": "production",
        "domain": "mindx.pythai.net",
        "vault_cipher": "aes-256-gcm",
        "vault_kdf": "hkdf-sha512",
        "agents": [],
    }

    print(f"Generating {len(CORE_AGENTS)} fresh production identities...\n")

    for agent_def in CORE_AGENTS:
        entity_id = agent_def["entity_id"]
        role = agent_def["role"]

        # Generate fresh Ethereum wallet
        account = Account.create()
        private_key_hex = account.key.hex()
        public_address = account.address

        # Store private key in BANKON Vault
        vault_id = f"agent_pk_{entity_id}"
        vault.store(vault_id, private_key_hex, context="agent_identity")

        # Record public address in registry (no secrets)
        registry["agents"].append({
            "entity_id": entity_id,
            "role": role,
            "address": public_address,
            "vault_id": vault_id,
        })

        print(f"  {entity_id:<35} {public_address}")

    # Save public registry (no private keys — safe to store)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(registry, indent=2))
    if os.name != "nt":
        os.chmod(registry_path, stat.S_IRUSR | stat.S_IWUSR)
    print(f"\nPublic registry saved: {registry_path}")

    # Lock vault
    vault.lock()
    print("BANKON Vault locked — all encryption keys zeroized from memory")

    # Remove legacy plaintext storage
    removed = []
    if legacy_env.exists():
        legacy_env.unlink()
        removed.append(str(legacy_env))
    if legacy_vault_agents.exists() and legacy_vault_agents.stat().st_size > 0:
        legacy_vault_agents.write_text("")
        removed.append(str(legacy_vault_agents))

    # Clear stale belief system persistence files
    belief_files = list((project_root / "data").rglob("*.beliefs.json"))
    for bf in belief_files:
        try:
            bf.unlink()
            removed.append(str(bf))
        except Exception:
            pass

    # Clear stale STM identity logs
    stm_dirs = [
        project_root / "data" / "memory" / "stm" / "default_identity_manager",
        project_root / "data" / "memory" / "stm" / "id_manager_for_mastermind_prime",
        project_root / "data" / "memory" / "stm" / "id_manager_for_coordinator_agent_main",
        project_root / "data" / "memory" / "stm" / "id_manager_for_mindx_meta_agent",
    ]
    for stm_dir in stm_dirs:
        if stm_dir.exists():
            import shutil
            shutil.rmtree(stm_dir, ignore_errors=True)
            removed.append(str(stm_dir))

    if removed:
        print(f"\nLegacy/stale data removed:")
        for r in removed:
            print(f"  - {r}")

    print(f"\n{'=' * 66}")
    print(f"  Genesis complete. {len(CORE_AGENTS)} sovereign identities created.")
    print(f"  Private keys encrypted in BANKON Vault (AES-256-GCM)")
    print(f"  No plaintext keys remain on disk.")
    print(f"{'=' * 66}")


if __name__ == "__main__":
    main()
