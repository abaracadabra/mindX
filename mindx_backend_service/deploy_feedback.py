# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""deploy_feedback — the OVERLORD/OVERSEER deploy-sequence feedback loop.

The deploy sequence is a handoff to the sovereigns: OVERLORD signs the EVM
suite, OVERSEER signs the Algorand suite. Each signed deploy produces on-chain
FEEDBACK — a tx hash, a deployed address or ASA id, a status. This module is the
append-only ledger of that feedback, so the handoff stops being a static plan and
becomes a live sequence: what deployed, where, with which tx, and what's next.

The feedback also flows into mindX's improvement awareness (a `deploy.feedback`
catalogue event), closing the loop from "planned" → "signed" → "confirmed" →
"recognized by the machine."
"""
from __future__ import annotations

import json
import time
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("mindx.deploy_feedback")

try:
    from utils.config import PROJECT_ROOT as _ROOT
except Exception:
    _ROOT = Path(__file__).resolve().parents[1]

_LEDGER = _ROOT / "data" / "deploy" / "deployment_feedback.jsonl"

# EVM tx: 0x + 64 hex. Algorand txid: 52-char base32. Kept permissive but bounded.
_EXPLORER = {
    "ethereum": "https://etherscan.io/tx/", "eth": "https://etherscan.io/tx/",
    "polygon": "https://polygonscan.com/tx/", "base": "https://basescan.org/tx/",
    "moonbeam": "https://moonscan.io/tx/", "blast": "https://blastscan.io/tx/",
    "algorand": "https://allo.info/tx/", "algo": "https://allo.info/tx/",
}


def _explorer(chain: str, tx: str) -> Optional[str]:
    base = _EXPLORER.get((chain or "").lower())
    return (base + tx) if base and tx else None


def record(*, step: str, contract: str, chain: str, tx_hash: str = "",
           address: str = "", asa_id: Optional[int] = None, status: str = "confirmed",
           by: str = "", note: str = "") -> Dict[str, Any]:
    """Append one deploy-feedback entry (a signed/confirmed deploy step) and mirror
    it to the catalogue for improvement awareness. Returns the stored entry."""
    entry = {
        "ts": time.time(),
        "step": str(step)[:120], "contract": str(contract)[:80],
        "chain": str(chain)[:32], "tx_hash": str(tx_hash)[:120],
        "address": str(address)[:64], "asa_id": (int(asa_id) if asa_id else None),
        "status": str(status)[:32], "by": str(by)[:80], "note": str(note)[:280],
        "explorer": _explorer(chain, tx_hash),
    }
    try:
        _LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with _LEDGER.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, separators=(",", ":")) + "\n")
    except Exception as e:  # pragma: no cover
        logger.warning(f"deploy_feedback.record: write failed: {e}")
    try:
        from agents.catalogue import emit_catalogue_event
        import asyncio
        asyncio.create_task(emit_catalogue_event(
            kind="deploy.feedback", actor=(by or "overlord"),
            payload={k: entry[k] for k in ("step", "contract", "chain", "tx_hash",
                                           "address", "asa_id", "status")},
            source_log=str(_LEDGER)))
    except Exception:
        pass  # catalogue is advisory
    logger.info(f"deploy.feedback: {entry['step']} · {entry['contract']} @ {entry['chain']} "
                f"· {entry['status']} · tx={entry['tx_hash'][:16]}")
    return entry


def recent(limit: int = 50) -> List[Dict[str, Any]]:
    """Most-recent-first deploy-feedback entries (public read; no secrets stored)."""
    if not _LEDGER.exists():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for ln in _LEDGER.read_text(encoding="utf-8").splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                out.append(json.loads(ln))
            except Exception:
                pass
    except Exception:
        return []
    return list(reversed(out))[:max(1, int(limit))]
