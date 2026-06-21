"""Algorand deployment-suite discovery for the OVERSEER surface.

Finds compiled arc56 artifacts (deployable: approval/clear bytecode + schema) and the TealScript source
suites (``daio/contracts/algorand/*.algo.ts``). The OVERSEER deploys the compiled artifacts CLIENT-SIDE —
the Parsec/Pera wallet (holding the mindx.algo key) signs the ApplicationCreate txn and submits it to a
public algod node. The server only reads + serves the compiled programs; it never holds a deploy key.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

_ROOT = Path(__file__).resolve().parents[1]
_DAIO = _ROOT / "daio" / "contracts"


def _b64_len(b64: str) -> int:
    try:
        return len(base64.b64decode(b64))
    except Exception:
        return 0


def discover_artifacts() -> List[Dict[str, Any]]:
    """Compiled, deployable Algorand contracts (arc56) found under daio/contracts/**/out."""
    out: List[Dict[str, Any]] = []
    if not _DAIO.is_dir():
        return out
    for f in sorted(_DAIO.glob("**/*.arc56.json")):
        if "node_modules" in f.parts:
            continue
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        bc = d.get("byteCode") or {}
        schema = (d.get("state") or {}).get("schema") or {}
        out.append({
            "name": d.get("name") or f.stem.replace(".arc56", ""),
            "artifact": str(f.relative_to(_ROOT)),
            "deployable": bool(bc.get("approval")),
            "approval_bytes": _b64_len(bc.get("approval") or ""),
            "methods": len(d.get("methods") or []),
            "schema": schema,
        })
    return out


def list_source_suites() -> List[Dict[str, Any]]:
    """TealScript source suites (daio/contracts/algorand/*.algo.ts) — not yet compiled to arc56."""
    base = _DAIO / "algorand"
    out: List[Dict[str, Any]] = []
    if base.is_dir():
        for f in sorted(base.glob("*.algo.ts")):
            out.append({"name": f.stem.replace(".algo", ""), "source": str(f.relative_to(_ROOT)),
                        "deployable": False})
    return out


def load_artifact(name: str) -> Optional[Dict[str, Any]]:
    """Compiled approval/clear program (base64) + schema for a named deployable artifact, or None."""
    for a in discover_artifacts():
        if a["name"].lower() == (name or "").lower():
            d = json.loads((_ROOT / a["artifact"]).read_text(encoding="utf-8"))
            bc = d.get("byteCode") or {}
            if not bc.get("approval"):
                return None
            schema = (d.get("state") or {}).get("schema") or {}
            return {
                "name": a["name"],
                "approval_b64": bc.get("approval"),
                "clear_b64": bc.get("clear") or "",
                "global_ints": int((schema.get("global") or {}).get("ints", 0)),
                "global_bytes": int((schema.get("global") or {}).get("bytes", 0)),
                "local_ints": int((schema.get("local") or {}).get("ints", 0)),
                "local_bytes": int((schema.get("local") or {}).get("bytes", 0)),
            }
    return None
