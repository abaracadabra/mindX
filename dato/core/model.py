# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato data model — pure dataclasses, JSON round-trippable, no chain/AO deps.

The shape every substrate agrees on: a DatoInstance (the data-DAO the DAIO owns),
its Members, its DataRecords (each at a permanence tier), and its Settings.
"""
from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class PermanenceTier(str, Enum):
    """Per-record / per-dato data-permanence spectrum.

    IMMORTAL  — permanent ANS-104 Arweave upload (the ~200-yr data-integrity
                guarantee); the proof is the Arweave tx id. Never changes.
    IMMUTABLE — content sha256 is hash-locked and anchored (recorded on
                DatoCore / the local ledger), but the bytes are NOT Arweave-stored;
                re-submitting different bytes under the same handle is rejected.
    MUTABLE   — editable bytes kept in dato state (local/off-chain); versioned.
    """

    IMMORTAL = "immortal"
    IMMUTABLE = "immutable"
    MUTABLE = "mutable"

    @classmethod
    def coerce(cls, value: "PermanenceTier | str") -> "PermanenceTier":
        if isinstance(value, cls):
            return value
        try:
            return cls(str(value).lower())
        except ValueError as exc:
            raise ValueError(
                f"unknown permanence tier {value!r}; expected one of "
                f"{[t.value for t in cls]}"
            ) from exc


@dataclass
class Settings:
    """Modular dato settings — extensible bag with a few first-class knobs.

    Mirrors the DAIO `GovernanceSettings.projectSettings[...]` idea: a dato (and
    each member) can carry its own settings without touching global config.
    """

    default_tier: PermanenceTier = PermanenceTier.IMMUTABLE
    join_fee_microusd: int = 0
    open_join: bool = True              # False ⇒ admission requires owner/govern approval
    max_members: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["default_tier"] = self.default_tier.value
        return d

    @classmethod
    def from_dict(cls, d: Optional[Dict[str, Any]]) -> "Settings":
        d = dict(d or {})
        if "default_tier" in d:
            d["default_tier"] = PermanenceTier.coerce(d["default_tier"])
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        extra = {k: d.pop(k) for k in list(d) if k not in known}
        d.setdefault("extra", {}).update(extra)
        return cls(**d)


@dataclass
class Member:
    """A participant admitted to a dato via request-to-join."""

    wallet: str
    joined_at: float = field(default_factory=time.time)
    fee_paid_microusd: int = 0
    fee_tx: Optional[str] = None        # x402 settlement tx/receipt id
    settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DataRecord:
    """One piece of data committed to a dato, at a permanence tier.

    ``proof`` is the Arweave tx id (IMMORTAL), the anchor reference (IMMUTABLE),
    or None (MUTABLE — bytes live in ``mutable_value``).
    """

    name: str                            # the tiered name <handle>.<tier>.<root>
    sha256: str
    tier: PermanenceTier
    proof: Optional[str] = None
    content_type: str = "application/octet-stream"
    bytes_len: int = 0
    version: int = 1
    created_at: float = field(default_factory=time.time)
    mutable_value: Optional[str] = None  # base64 bytes for MUTABLE tier only

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tier"] = self.tier.value
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DataRecord":
        d = dict(d)
        d["tier"] = PermanenceTier.coerce(d.get("tier", "mutable"))
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})  # type: ignore[attr-defined]


@dataclass
class DatoInstance:
    """A data-DAO the DAIO spawns and owns."""

    dato_id: str
    name: str                            # the dato's own tiered name
    owner_daio: str                      # the owning DAIO (address or id)
    deployer_wallet: str                 # participant/client who spawned it
    settings: Settings = field(default_factory=Settings)
    members: Dict[str, Member] = field(default_factory=dict)
    records: Dict[str, DataRecord] = field(default_factory=dict)
    substrate: str = "python"            # python | ao | evm
    process_ref: Optional[str] = None    # AO process id / DatoCore address when bridged
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dato_id": self.dato_id,
            "name": self.name,
            "owner_daio": self.owner_daio,
            "deployer_wallet": self.deployer_wallet,
            "settings": self.settings.to_dict(),
            "members": {k: m.to_dict() for k, m in self.members.items()},
            "records": {k: r.to_dict() for k, r in self.records.items()},
            "substrate": self.substrate,
            "process_ref": self.process_ref,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DatoInstance":
        inst = cls(
            dato_id=d["dato_id"],
            name=d["name"],
            owner_daio=d["owner_daio"],
            deployer_wallet=d["deployer_wallet"],
            settings=Settings.from_dict(d.get("settings")),
            substrate=d.get("substrate", "python"),
            process_ref=d.get("process_ref"),
            created_at=d.get("created_at", time.time()),
        )
        inst.members = {k: Member(**v) for k, v in (d.get("members") or {}).items()}
        inst.records = {k: DataRecord.from_dict(v) for k, v in (d.get("records") or {}).items()}
        return inst


__all__ = ["PermanenceTier", "Settings", "Member", "DataRecord", "DatoInstance"]
