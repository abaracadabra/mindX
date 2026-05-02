"""Cabinet roles and quorum policy.

The protocol does not depend on the Cabinet schema specifically — any
non-empty role set with unique pubkeys is a valid conclave. This module
provides the canonical 8-member Cabinet as a default and a small
policy object that maps motion classes to quorum thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable


class Role(str, Enum):
    """Canonical Cabinet roles. Stored as strings on the wire."""

    CEO = "CEO"
    COO = "COO"
    CFO = "CFO"
    CTO = "CTO"
    CISO = "CISO"
    GC = "GC"
    COS = "COS"
    OPS = "OPS"


# Numeric encoding for on-chain storage (Conclave.sol roles[]).
ROLE_TO_U8: dict[Role, int] = {
    Role.CEO: 0,
    Role.COO: 1,
    Role.CFO: 2,
    Role.CTO: 3,
    Role.CISO: 4,
    Role.GC: 5,
    Role.COS: 6,
    Role.OPS: 7,
}
U8_TO_ROLE: dict[int, Role] = {v: k for k, v in ROLE_TO_U8.items()}


@dataclass(frozen=True)
class Member:
    """A conclave member: AXL pubkey + role + optional EVM/Algorand bindings."""

    pubkey: str            # 0x-prefixed hex (64 chars)
    role: Role
    evm_address: str | None = None
    algo_address: str | None = None

    def to_manifest_dict(self) -> dict[str, str]:
        return {"pubkey": self.pubkey, "role": self.role.value}


class MotionClass(str, Enum):
    STANDARD = "standard"
    TRADE_SECRET = "trade_secret"
    MEMBERSHIP = "membership"


@dataclass(frozen=True)
class QuorumPolicy:
    """Member count required per motion class (and for acclaim)."""

    acclaim: int
    standard: int
    trade_secret: int
    membership: int

    @classmethod
    def cabinet_default(cls) -> "QuorumPolicy":
        # 8-member Cabinet: 5/8 normal, 6/8 secrets, 7/8 membership change.
        return cls(acclaim=5, standard=5, trade_secret=6, membership=7)

    def for_class(self, cls_: MotionClass) -> int:
        if cls_ is MotionClass.STANDARD:
            return self.standard
        if cls_ is MotionClass.TRADE_SECRET:
            return self.trade_secret
        if cls_ is MotionClass.MEMBERSHIP:
            return self.membership
        raise ValueError(f"unknown motion class: {cls_}")

    def to_dict(self) -> dict[str, int]:
        return {
            "acclaim": self.acclaim,
            "motion": self.standard,
            "trade_secret": self.trade_secret,
            "membership": self.membership,
        }

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> "QuorumPolicy":
        return cls(
            acclaim=int(d["acclaim"]),
            standard=int(d["motion"]),
            trade_secret=int(d["trade_secret"]),
            membership=int(d["membership"]),
        )


def validate_member_set(members: Iterable[Member]) -> list[Member]:
    """Reject duplicate pubkeys and empty sets; preserve manifest order."""
    seen: set[str] = set()
    out: list[Member] = []
    for m in members:
        pk = m.pubkey.lower()
        if pk in seen:
            raise ValueError(f"duplicate member pubkey: {pk}")
        seen.add(pk)
        out.append(m)
    if not out:
        raise ValueError("conclave must have at least one member")
    return out
