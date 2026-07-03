# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato ownership + participant/deployer wallet capture.

A dato is owned by the DAIO and spawned by a participant/client. This module
resolves both: the owning DAIO (explicit, env, or default) and the spawning
wallet (explicit, or via mindX's identity layer — ``IDManagerAgent`` /
session-token recognition), reusing existing primitives rather than inventing a
new wallet system.
"""
from __future__ import annotations

import os
import re
from typing import Optional

_ADDR_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


def resolve_owner_daio(explicit: Optional[str] = None) -> str:
    """The owning DAIO address/id: explicit > env > a stable default label."""
    return (
        explicit
        or os.environ.get("MINDX_DAIO_ADDRESS")
        or os.environ.get("DAIO_OWNER")
        or "daio"
    )


def resolve_deployer_wallet(
    explicit: Optional[str] = None, *, entity_id: Optional[str] = None
) -> str:
    """Resolve the spawning participant/client wallet.

    Priority: explicit address → mindX identity (``IDManagerAgent`` for
    ``entity_id``) → env (``MINDX_DEPLOYER_WALLET``) → ``"anon"``. Never raises.
    """
    if explicit and _ADDR_RE.match(explicit):
        return explicit
    if explicit:  # a non-address handle is still accepted (e.g. an ENS name)
        return explicit
    if entity_id:
        addr = _wallet_via_id_manager(entity_id)
        if addr:
            return addr
    return os.environ.get("MINDX_DEPLOYER_WALLET") or "anon"


def _wallet_via_id_manager(entity_id: str) -> Optional[str]:
    """Best-effort address via mindX's IDManagerAgent; never hard-imports."""
    try:  # pragma: no cover - depends on a running identity layer
        import asyncio

        from agents.core.id_manager_agent import IDManagerAgent

        async def _get() -> Optional[str]:
            mgr = await IDManagerAgent.get_instance()
            return await mgr.get_public_address(entity_id)

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return None  # can't block inside a running loop; caller passes explicit
        return asyncio.run(_get())
    except Exception:
        return None


def is_address(value: str) -> bool:
    return bool(value and _ADDR_RE.match(value))


__all__ = ["resolve_owner_daio", "resolve_deployer_wallet", "is_address"]
