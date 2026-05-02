# ╔══════════════════════════════════════════════════════════════════╗
# ║  BANKON Vault — Cabinet Provisioner                             ║
# ║                                                                  ║
# ║  Provisions the 8-wallet executive cabinet (CEO + 7 soldiers)   ║
# ║  for a company, stores keys under namespaced vault entries,     ║
# ║  publishes public addresses to the production registry.         ║
# ║                                                                  ║
# ║  See /home/hacker/.claude/plans/splendid-wishing-hejlsberg.md   ║
# ╚══════════════════════════════════════════════════════════════════╝

from __future__ import annotations

import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from eth_account import Account
from web3 import Web3

from mindx_backend_service.bankon_vault.vault import BankonVault

# Single source of truth: 1 CEO + 7 soldiers, weights mirror
# daio/governance/boardroom.py:SOLDIER_WEIGHTS.
CABINET_ROLES: Tuple[str, ...] = (
    "ceo",
    "coo_operations",
    "cfo_finance",
    "cto_technology",
    "ciso_security",
    "clo_legal",
    "cpo_product",
    "cro_risk",
)

ROLE_LABELS: Dict[str, str] = {
    "ceo": "Chief Executive Officer",
    "coo_operations": "Chief Operating Officer",
    "cfo_finance": "Chief Financial Officer",
    "cto_technology": "Chief Technology Officer",
    "ciso_security": "Chief Information Security Officer",
    "clo_legal": "Chief Legal Officer",
    "cpo_product": "Chief Product Officer",
    "cro_risk": "Chief Risk Officer",
}

ROLE_WEIGHTS: Dict[str, float] = {
    "ceo": 1.0,
    "coo_operations": 1.0,
    "cfo_finance": 1.0,
    "cto_technology": 1.0,
    "ciso_security": 1.2,
    "clo_legal": 0.8,
    "cpo_product": 1.0,
    "cro_risk": 1.2,
}


def vault_pk_id(company: str, role: str) -> str:
    return f"company:{company}:cabinet:{role}:pk"


def vault_addr_id(company: str, role: str) -> str:
    return f"company:{company}:cabinet:{role}:address"


def entity_id(company: str, role: str) -> str:
    return f"company:{company}:cabinet:{role}"


_REGISTRY_PATH = Path(os.environ.get(
    "MINDX_PRODUCTION_REGISTRY",
    "data/identity/production_registry.json",
))
_AGENT_MAP_PATH = Path(os.environ.get(
    "MINDX_AGENT_MAP",
    "daio/agents/agent_map.json",
))


def _atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


class CabinetExists(Exception):
    """Raised when provision is called for a company that already has a cabinet."""


class CabinetMissing(Exception):
    """Raised when read/clear is called for a company with no cabinet."""


class CabinetProvisioner:
    """Provisions / reads / clears an 8-wallet executive cabinet for a company.

    Storage:
      - vault entries: `company:{co}:cabinet:{role}:pk` (private) and
        `company:{co}:cabinet:{role}:address` (public, also redundantly in registry).
      - data/identity/production_registry.json `cabinet[company]`: public addresses + metadata.
      - daio/agents/agent_map.json `soldiers[role].eth_address`: backfills the 7 soldier slots.

    All mutations occur under `BankonVault._vault_dir_lock()` so a single rotation
    or sibling provisioning cannot race us.
    """

    def __init__(
        self,
        vault: Optional[BankonVault] = None,
        registry_path: Optional[Path] = None,
        agent_map_path: Optional[Path] = None,
    ):
        self._vault = vault or BankonVault()
        # Re-read env at construction so test fixtures (and config reloads) are honored.
        self._registry_path = registry_path or Path(os.environ.get(
            "MINDX_PRODUCTION_REGISTRY",
            "data/identity/production_registry.json",
        ))
        self._agent_map_path = agent_map_path or Path(os.environ.get(
            "MINDX_AGENT_MAP",
            "daio/agents/agent_map.json",
        ))

    # ─── public API ─────────────────────────────────────────────

    def preflight(self, company: str) -> Dict[str, Any]:
        registry = _read_json(self._registry_path)
        cabinet = (registry.get("cabinet") or {}).get(company)
        agent_map = _read_json(self._agent_map_path)
        soldiers = agent_map.get("soldiers", {}) if isinstance(agent_map, dict) else {}
        soldiers_with_addresses = [
            role for role, body in soldiers.items()
            if isinstance(body, dict) and body.get("eth_address")
        ]
        return {
            "exists": cabinet is not None,
            "vault_unlocked": self._vault.is_unlocked(),
            "registry_writable": os.access(self._registry_path.parent, os.W_OK),
            "soldiers_with_existing_addresses": soldiers_with_addresses,
        }

    def provision(self, company: str, shadow_address: str) -> Dict[str, Any]:
        """Mint 8 wallets, store keys in vault, publish addresses to registry.

        Atomic-or-rollback: any failure restores the snapshot. The vault must
        already be unlocked (we cannot unlock here — that's the operator's job
        through the existing /vault/credentials/reunlock flow).
        """
        if not self._vault.is_unlocked():
            raise RuntimeError("vault must be unlocked before provisioning a cabinet")

        registry = _read_json(self._registry_path)
        if (registry.get("cabinet") or {}).get(company):
            raise CabinetExists(f"cabinet for {company!r} already exists")

        snapshot_dir = Path(f"/tmp/cabinet-provision-{int(time.time())}")
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Take snapshots of every file we may mutate.
        registry_snap = snapshot_dir / "production_registry.json"
        agent_map_snap = snapshot_dir / "agent_map.json"
        entries_snap = snapshot_dir / "entries.json"
        if self._registry_path.exists():
            shutil.copy2(self._registry_path, registry_snap)
        if self._agent_map_path.exists():
            shutil.copy2(self._agent_map_path, agent_map_snap)
        entries_path = self._vault.vault_dir / "entries.json"
        if entries_path.exists():
            shutil.copy2(entries_path, entries_snap)

        with self._vault._vault_dir_lock():
            try:
                wallets: Dict[str, Tuple[str, str]] = {}  # role -> (privkey_hex, addr)
                for role in CABINET_ROLES:
                    acct = Account.create()
                    privkey_hex = acct.key.hex()
                    addr = Web3.to_checksum_address(acct.address)
                    self._vault.store(
                        vault_pk_id(company, role),
                        privkey_hex,
                        context="cabinet_provision",
                    )
                    self._vault.store(
                        vault_addr_id(company, role),
                        addr,
                        context="cabinet_public",
                    )
                    wallets[role] = (privkey_hex, addr)

                # Build the cabinet block in the registry.
                cabinet_block = self._build_registry_block(company, shadow_address, wallets)
                registry.setdefault("cabinet", {})[company] = cabinet_block
                _atomic_write_json(self._registry_path, registry)

                # Backfill soldier addresses in agent_map.
                self._backfill_agent_map(wallets)

                return {
                    "status": "provisioned",
                    "company": company,
                    "ceo": cabinet_block["ceo"]["address"],
                    "soldiers": {
                        r: cabinet_block["soldiers"][r]["address"]
                        for r in CABINET_ROLES if r != "ceo"
                    },
                }

            except Exception:
                # Roll back every file we mutated, then re-raise.
                if registry_snap.exists():
                    shutil.copy2(registry_snap, self._registry_path)
                if agent_map_snap.exists():
                    shutil.copy2(agent_map_snap, self._agent_map_path)
                if entries_snap.exists():
                    shutil.copy2(entries_snap, entries_path)
                raise

    def read_public(self, company: str) -> Dict[str, Any]:
        """Return only public-side fields. Private ids are stripped."""
        registry = _read_json(self._registry_path)
        cabinet = (registry.get("cabinet") or {}).get(company)
        if cabinet is None:
            raise CabinetMissing(f"no cabinet for {company!r}")

        def strip(slot: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "address": slot["address"],
                "entity_id": slot["entity_id"],
                "role_label": slot["role_label"],
                **({"boardroom_weight": slot["boardroom_weight"]} if "boardroom_weight" in slot else {}),
            }

        return {
            "company": company,
            "provisioned_at": cabinet.get("provisioned_at"),
            "shadow_overlord_address": cabinet.get("shadow_overlord_address"),
            "ceo": strip(cabinet["ceo"]),
            "soldiers": {r: strip(body) for r, body in cabinet["soldiers"].items()},
        }

    def clear(self, company: str) -> Dict[str, Any]:
        """Wipe a cabinet: delete vault entries, remove registry block, null out agent_map."""
        if not self._vault.is_unlocked():
            raise RuntimeError("vault must be unlocked to clear a cabinet")

        registry = _read_json(self._registry_path)
        if (registry.get("cabinet") or {}).get(company) is None:
            raise CabinetMissing(f"no cabinet for {company!r}")

        with self._vault._vault_dir_lock():
            cleared = 0
            for role in CABINET_ROLES:
                for entry in (vault_pk_id(company, role), vault_addr_id(company, role)):
                    try:
                        if self._vault.delete(entry):
                            cleared += 1
                    except Exception:
                        # delete may raise on missing — non-fatal.
                        pass

            cabinet_block = registry["cabinet"].pop(company)
            if not registry["cabinet"]:
                registry.pop("cabinet")
            _atomic_write_json(self._registry_path, registry)

            # Null out agent_map soldier addresses (only if they match the cleared cabinet's).
            self._null_out_agent_map(cabinet_block)

            return {"status": "cleared", "company": company, "vault_entries_removed": cleared}

    # ─── internals ──────────────────────────────────────────────

    def _build_registry_block(
        self,
        company: str,
        shadow_address: str,
        wallets: Dict[str, Tuple[str, str]],
    ) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat(timespec="seconds")
        ceo_priv, ceo_addr = wallets["ceo"]
        block: Dict[str, Any] = {
            "provisioned_at": now_iso,
            "shadow_overlord_address": Web3.to_checksum_address(shadow_address),
            "ceo": {
                "entity_id": entity_id(company, "ceo"),
                "address": ceo_addr,
                "vault_pk_id": vault_pk_id(company, "ceo"),
                "role_label": ROLE_LABELS["ceo"],
                "boardroom_weight": ROLE_WEIGHTS["ceo"],
            },
            "soldiers": {},
        }
        for role in CABINET_ROLES:
            if role == "ceo":
                continue
            _, addr = wallets[role]
            block["soldiers"][role] = {
                "entity_id": entity_id(company, role),
                "address": addr,
                "vault_pk_id": vault_pk_id(company, role),
                "role_label": ROLE_LABELS[role],
                "boardroom_weight": ROLE_WEIGHTS[role],
            }
        return block

    def _backfill_agent_map(self, wallets: Dict[str, Tuple[str, str]]) -> None:
        if not self._agent_map_path.exists():
            return
        agent_map = _read_json(self._agent_map_path)
        soldiers_section = agent_map.setdefault("soldiers", {}) if isinstance(agent_map, dict) else {}
        if not isinstance(soldiers_section, dict):
            return
        changed = False
        for role, (_, addr) in wallets.items():
            if role == "ceo":
                continue
            slot = soldiers_section.get(role)
            if isinstance(slot, dict) and slot.get("eth_address") is None:
                slot["eth_address"] = addr
                changed = True
        if changed:
            _atomic_write_json(self._agent_map_path, agent_map)

    def _null_out_agent_map(self, cleared_block: Dict[str, Any]) -> None:
        if not self._agent_map_path.exists():
            return
        agent_map = _read_json(self._agent_map_path)
        soldiers_section = agent_map.get("soldiers") if isinstance(agent_map, dict) else None
        if not isinstance(soldiers_section, dict):
            return
        cleared_addrs = {
            body["address"].lower()
            for body in cleared_block.get("soldiers", {}).values()
        }
        changed = False
        for role, slot in soldiers_section.items():
            if not isinstance(slot, dict):
                continue
            existing = (slot.get("eth_address") or "").lower()
            if existing and existing in cleared_addrs:
                slot["eth_address"] = None
                changed = True
        if changed:
            _atomic_write_json(self._agent_map_path, agent_map)
