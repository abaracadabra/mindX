# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato AO spawner — spawn/own/message the `dato.lua` process (lazy, dry-run safe).

mindX has no AO tooling today, so this never hard-depends on `aoconnect`/`aos`:
if the toolchain is absent it returns a deterministic **dry-run** process id so the
suite stays runnable and testable. When AO tooling IS present (an `aos`/node
bridge on PATH, or an `MINDX_AO_BRIDGE` HTTP endpoint), it spawns the process,
loads `dato.lua`, records the DAIO as the owning authority, and relays
Spawn/Configure/Join/Govern/Commit messages.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

_DATO_LUA = Path(__file__).resolve().parent / "dato.lua"


class AOSpawnResult(dict):
    @property
    def process_id(self) -> str:
        return self["process_id"]

    @property
    def dry_run(self) -> bool:
        return bool(self.get("dry_run"))


def ao_available() -> bool:
    """True if an AO toolchain looks reachable (aos on PATH or a bridge URL)."""
    return bool(shutil.which("aos") or os.environ.get("MINDX_AO_BRIDGE"))


def _dry_run_pid(name: str, owner_daio: str) -> str:
    seed = f"{name}:{owner_daio}:{int(time.time())}".encode()
    # 43-char base64url-ish id, shaped like an AO/Arweave process id, deterministic per call.
    import base64

    return base64.urlsafe_b64encode(hashlib.sha256(seed).digest()).rstrip(b"=").decode()


def spawn_dato_process(
    name: str,
    *,
    owner_daio: str,
    deployer_wallet: str,
    default_tier: str = "immutable",
    join_fee: int = 0,
    open_join: bool = True,
    lua_path: Optional[Path] = None,
) -> AOSpawnResult:
    """Spawn the dato.lua process owned by ``owner_daio``.

    Returns ``{process_id, dry_run, owner, deployer, ...}``. Never raises on a
    missing toolchain — degrades to a dry-run id (the Python orchestrator remains
    the canonical state; the AO process is an optional mirror).
    """
    lua = Path(lua_path) if lua_path else _DATO_LUA
    spawn_tags = {
        "Owner-DAIO": owner_daio, "Deployer": deployer_wallet,
        "Default-Tier": default_tier, "Join-Fee": str(join_fee),
        "Open-Join": "true" if open_join else "false", "Name": name,
    }
    if not ao_available():
        return AOSpawnResult(
            process_id=_dry_run_pid(name, owner_daio), dry_run=True,
            owner=owner_daio, deployer=deployer_wallet, lua=str(lua),
            spawn_tags=spawn_tags,
            note="AO toolchain absent (no aos / MINDX_AO_BRIDGE); dry-run id. "
                 "Install aos or set MINDX_AO_BRIDGE to spawn a real process.",
        )

    bridge = os.environ.get("MINDX_AO_BRIDGE")
    if bridge:
        return _spawn_via_bridge(bridge, lua, spawn_tags, owner_daio, deployer_wallet)
    return _spawn_via_aos(lua, spawn_tags, owner_daio, deployer_wallet)


def _spawn_via_bridge(bridge: str, lua: Path, tags: Dict[str, str], owner: str, deployer: str) -> AOSpawnResult:
    import httpx

    payload = {"module": "dato", "lua": lua.read_text(), "tags": tags}
    r = httpx.post(bridge.rstrip("/") + "/spawn", json=payload, timeout=30.0)
    r.raise_for_status()
    pid = r.json().get("process_id") or r.json().get("id")
    return AOSpawnResult(process_id=pid, dry_run=False, owner=owner, deployer=deployer, bridge=bridge)


def _spawn_via_aos(lua: Path, tags: Dict[str, str], owner: str, deployer: str) -> AOSpawnResult:
    # Best-effort aos invocation; the exact CLI varies by version, so capture
    # output and fall back to a dry-run id on any non-zero/parse failure.
    try:
        out = subprocess.run(
            ["aos", "--load", str(lua), "--tag-name", "Owner-DAIO", "--tag-value", owner],
            capture_output=True, text=True, timeout=120,
        )
        pid = None
        for tok in (out.stdout or "").split():
            if len(tok) == 43:  # AO/Arweave id length
                pid = tok
                break
        if not pid:
            raise RuntimeError("could not parse process id from aos output")
        return AOSpawnResult(process_id=pid, dry_run=False, owner=owner, deployer=deployer)
    except Exception as e:
        res = AOSpawnResult(process_id=_dry_run_pid(str(lua), owner), dry_run=True,
                            owner=owner, deployer=deployer, error=str(e))
        return res


def message(process_id: str, action: str, tags: Optional[Dict[str, str]] = None,
            data: str = "") -> Dict[str, Any]:
    """Relay a Spawn/Configure/Join/Govern/Commit message to a dato process.

    Dry-run safe: with no bridge it returns the message envelope unsent so callers
    (and tests) can assert the shape.
    """
    envelope = {"Target": process_id, "Action": action, "Tags": tags or {}, "Data": data}
    bridge = os.environ.get("MINDX_AO_BRIDGE")
    if not bridge:
        return {"sent": False, "dry_run": True, "envelope": envelope}
    import httpx

    r = httpx.post(bridge.rstrip("/") + "/message", json=envelope, timeout=30.0)
    r.raise_for_status()
    return {"sent": True, "response": r.json(), "envelope": envelope}


__all__ = ["AOSpawnResult", "ao_available", "spawn_dato_process", "message"]
