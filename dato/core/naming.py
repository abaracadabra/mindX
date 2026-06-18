# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato tiered, extensible naming — `<handle>.<tier>.<root>`.

The name *declares* its permanence: the middle label is the permanence tier
(immortal | immutable | mutable), e.g. ``archive.immortal.blockchain``. Roots are
extensible — ``blockchain`` ships by default and more can be added (``eth``,
``ar``, …) with :func:`add_root`, so the namespace grows without code changes.

This mirrors the ENS subname-handler shape of
``daio/contracts/ens/v1/BankonSubnameRegistrar.sol`` (and the on-chain
``DatoNamingRegistry.sol`` enforces the same grammar); here it is the pure-Python
resolver/validator the orchestrator uses and that the registry agrees with.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Set

from dato.core.model import PermanenceTier

# Default roots; extend at runtime with add_root(). A root is a DNS-ish label.
_ROOTS: Set[str] = {"blockchain"}
_LABEL_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")


class DatoNameError(ValueError):
    pass


def roots() -> Set[str]:
    return set(_ROOTS)


def add_root(root: str) -> None:
    """Register an additional name root (e.g. ``eth``, ``ar``). Idempotent."""
    root = _norm_label(root, "root")
    _ROOTS.add(root)


def _norm_label(label: str, kind: str) -> str:
    label = (label or "").strip().lower()
    if not _LABEL_RE.match(label):
        raise DatoNameError(f"invalid {kind} label {label!r} (a-z0-9-, ≤63 chars, no leading -)")
    return label


@dataclass(frozen=True)
class DatoName:
    handle: str
    tier: PermanenceTier
    root: str

    def __str__(self) -> str:
        return f"{self.handle}.{self.tier.value}.{self.root}"


def format_name(handle: str, tier: "PermanenceTier | str", root: str = "blockchain") -> str:
    """Compose + validate a tiered name. Raises DatoNameError on a bad part."""
    h = _norm_label(handle, "handle")
    t = PermanenceTier.coerce(tier)
    r = _norm_label(root, "root")
    if r not in _ROOTS:
        raise DatoNameError(f"unknown root {r!r}; known roots: {sorted(_ROOTS)} (use add_root)")
    return f"{h}.{t.value}.{r}"


def parse_name(name: str) -> DatoName:
    """Parse `<handle>.<tier>.<root>` → DatoName. Tier must be a permanence tier."""
    parts = (name or "").strip().lower().split(".")
    if len(parts) != 3:
        raise DatoNameError(f"name must be <handle>.<tier>.<root>, got {name!r}")
    handle, tier_s, root = parts
    handle = _norm_label(handle, "handle")
    root = _norm_label(root, "root")
    try:
        tier = PermanenceTier(tier_s)
    except ValueError as exc:
        raise DatoNameError(
            f"tier label {tier_s!r} is not a permanence tier {[t.value for t in PermanenceTier]}"
        ) from exc
    if root not in _ROOTS:
        raise DatoNameError(f"unknown root {root!r}; known roots: {sorted(_ROOTS)}")
    return DatoName(handle=handle, tier=tier, root=root)


def tier_of(name: str) -> PermanenceTier:
    """The permanence tier a name declares."""
    return parse_name(name).tier


def namehash(name: str) -> str:
    """ENS-style namehash (sha256 variant) — the registry key for a tiered name."""
    import hashlib

    node = b"\x00" * 32
    for label in reversed(parse_name(name).__str__().split(".")):
        node = hashlib.sha256(node + hashlib.sha256(label.encode()).digest()).digest()
    return "0x" + node.hex()


class NameResolver:
    """In-process resolver: tiered name → controller + permanence proof.

    Backed by the dato registry (the orchestrator passes records in). When an
    on-chain DatoNamingRegistry is configured the orchestrator can override this.
    """

    def __init__(self) -> None:
        self._names: dict[str, dict] = {}

    def register(self, name: str, controller: str, proof: Optional[str], dato_id: str) -> str:
        full = name if name.count(".") == 2 else format_name(*name.split("."))
        parse_name(full)  # validate
        if full in self._names and self._names[full]["controller"] != controller:
            raise DatoNameError(f"name {full!r} already controlled by another wallet")
        self._names[full] = {"controller": controller, "proof": proof, "dato_id": dato_id}
        return full

    def resolve(self, name: str) -> Optional[dict]:
        return self._names.get(name)


__all__ = [
    "DatoName", "DatoNameError", "NameResolver",
    "format_name", "parse_name", "tier_of", "namehash", "roots", "add_root",
]
