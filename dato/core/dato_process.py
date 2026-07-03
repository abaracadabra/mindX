# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato orchestrator — the canonical AO-pattern implementation (runs standalone).

Mirrors the AO DAO lifecycle (spawn → configure → join → govern → commit) as
methods, but the dato is DAIO-OWNED (not peer stake-to-vote): the DAIO is the
authority, participants request to join with a fee + settings. State persists to
``dato/data/dato_registry.json`` (atomic write, gitignored). This layer is
substrate-agnostic; the AO (`dato/ao`) and EVM (`dato/contracts`) substrates are
optional bridges driven from here.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from dato.core import naming, ownership
from dato.core.model import DataRecord, DatoInstance, Member, PermanenceTier, Settings
from dato.core.permanence import write_record

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_REGISTRY_PATH = _PROJECT_ROOT / "dato" / "data" / "dato_registry.json"


class DatoError(RuntimeError):
    pass


class DatoRegistry:
    """Append-managed store of dato instances + a shared name resolver."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = Path(path) if path else _REGISTRY_PATH
        self._instances: Dict[str, DatoInstance] = {}
        self.resolver = naming.NameResolver()
        self._load()

    # -- persistence -------------------------------------------------------
    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            raw = json.loads(self.path.read_text())
        except Exception:
            return
        for d in raw.get("instances", []):
            inst = DatoInstance.from_dict(d)
            self._instances[inst.dato_id] = inst
            for nm, rec in inst.records.items():
                try:
                    self.resolver.register(rec.name, inst.deployer_wallet, rec.proof, inst.dato_id)
                except Exception:
                    pass
            try:
                self.resolver.register(inst.name, inst.owner_daio, None, inst.dato_id)
            except Exception:
                pass

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        payload = {"v": 1, "instances": [i.to_dict() for i in self._instances.values()]}
        tmp.write_text(json.dumps(payload, indent=2))
        tmp.replace(self.path)

    # -- lifecycle (AO-pattern) -------------------------------------------
    def spawn(
        self,
        handle: str,
        *,
        tier: "PermanenceTier | str" = PermanenceTier.IMMUTABLE,
        root: str = "blockchain",
        deployer_wallet: Optional[str] = None,
        owner_daio: Optional[str] = None,
        entity_id: Optional[str] = None,
        settings: Optional[Settings] = None,
    ) -> DatoInstance:
        """Spawn a new DAIO-owned dato. Records owner + spawning wallet + name."""
        tier = PermanenceTier.coerce(tier)
        name = naming.format_name(handle, tier, root)
        owner = ownership.resolve_owner_daio(owner_daio)
        wallet = ownership.resolve_deployer_wallet(deployer_wallet, entity_id=entity_id)
        dato_id = "dato_" + hashlib.sha256(f"{name}:{owner}:{time.time()}".encode()).hexdigest()[:16]
        st = settings or Settings(default_tier=tier)
        inst = DatoInstance(
            dato_id=dato_id, name=name, owner_daio=owner, deployer_wallet=wallet, settings=st,
        )
        # The deployer is the founding member.
        inst.members[wallet] = Member(wallet=wallet, fee_paid_microusd=0)
        self._instances[dato_id] = inst
        self.resolver.register(name, owner, None, dato_id)
        self._save()
        return inst

    def configure(self, dato_id: str, settings: Settings) -> DatoInstance:
        inst = self._require(dato_id)
        inst.settings = settings
        self._save()
        return inst

    def request_join(
        self, dato_id: str, wallet: str, *, fee_paid_microusd: int = 0,
        fee_tx: Optional[str] = None, settings: Optional[Dict[str, Any]] = None,
    ) -> Member:
        """Admit a member. Fee enforcement lives in ``membership.py`` (this is the
        state mutation it calls once payment is settled / open_join allows)."""
        inst = self._require(dato_id)
        if not inst.settings.open_join and wallet not in inst.members:
            raise DatoError(f"dato {dato_id} is closed-join; admission requires owner/govern approval")
        if inst.settings.max_members is not None and len(inst.members) >= inst.settings.max_members:
            raise DatoError(f"dato {dato_id} is at capacity ({inst.settings.max_members})")
        member = Member(
            wallet=wallet, fee_paid_microusd=fee_paid_microusd, fee_tx=fee_tx, settings=settings or {},
        )
        inst.members[wallet] = member
        self._save()
        return member

    def govern(self, dato_id: str, actor: str, action: str, **kw: Any) -> Dict[str, Any]:
        """Member/owner action over the dato (extensible). Owner always allowed."""
        inst = self._require(dato_id)
        if actor != inst.owner_daio and actor not in inst.members:
            raise DatoError(f"{actor} is not a member or the owner of {dato_id}")
        # Minimal action set; extend as governance grows.
        if action == "set_open_join":
            inst.settings.open_join = bool(kw.get("value", True))
        elif action == "remove_member":
            inst.members.pop(kw.get("wallet", ""), None)
        else:
            return {"ok": False, "reason": f"unknown action {action!r}"}
        self._save()
        return {"ok": True, "action": action}

    def commit(
        self, dato_id: str, handle: str, data: bytes, *,
        tier: Optional["PermanenceTier | str"] = None,
        root: str = "blockchain", content_type: str = "application/octet-stream",
    ) -> DataRecord:
        """Commit data to the dato at a permanence tier; the name declares the tier."""
        inst = self._require(dato_id)
        tier = PermanenceTier.coerce(tier or inst.settings.default_tier)
        name = naming.format_name(handle, tier, root)
        existing = inst.records.get(name)
        record = write_record(name, data, tier, content_type=content_type, existing=existing)
        inst.records[name] = record
        self.resolver.register(name, inst.deployer_wallet, record.proof, dato_id)
        self._save()
        return record

    # -- access ------------------------------------------------------------
    def get(self, dato_id: str) -> Optional[DatoInstance]:
        return self._instances.get(dato_id)

    def list(self) -> List[DatoInstance]:
        return list(self._instances.values())

    def resolve_name(self, name: str) -> Optional[dict]:
        return self.resolver.resolve(name)

    def _require(self, dato_id: str) -> DatoInstance:
        inst = self._instances.get(dato_id)
        if inst is None:
            raise DatoError(f"unknown dato {dato_id!r}")
        return inst


__all__ = ["DatoRegistry", "DatoError"]
