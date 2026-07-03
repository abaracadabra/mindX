"""status — the live training indicator.

A single JSON file (`data/godel/ascend/training_status.json`) records whether a
Schmidhüber ascent is training right now, since when, which recipe/generation,
and where its log is. The /insight/godel/ascend endpoint reads it (computing
elapsed seconds and verifying liveness) so the landing page and feedback.html
can show a pulsing "TRAINING" light + an elapsed timer + the live log tail.

Kept deliberately tiny and stdlib-only — it is written from inside the ascent
(which may be a subprocess driver) and read from the web process.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve().parents[3]

STATUS_PATH = PROJECT_ROOT / "data" / "godel" / "ascend" / "training_status.json"


def write_status(state: str, **fields: Any) -> None:
    """state ∈ running | done | rejected | promoted | failed. Best-effort."""
    try:
        STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
        rec: Dict[str, Any] = {"state": state, "pid": os.getpid(), "updated_ts": time.time()}
        rec.update(fields)
        STATUS_PATH.write_text(json.dumps(rec), encoding="utf-8")
    except Exception:
        pass


async def chronos_now() -> tuple:
    """(unix_18dp_str, consensus, confidence_ms) from chronos.agent — the
    verified clock, to 18 decimals. Best-effort: falls back to local
    time.time_ns()/1e9 (18dp) with consensus 'local' if chronos is unreachable."""
    try:
        from agents.chronos_agent import ChronosAgent
        ch = await ChronosAgent.get_instance()
        pt = await ch.now()
        return str(pt.unix_18dp), pt.consensus, float(pt.confidence_ms)
    except Exception:
        from decimal import Decimal as _D
        return str(_D(time.time_ns()) / _D(1_000_000_000)), "local", 0.0


def elapsed_18dp(started_unix_18dp: Optional[str], now_unix_18dp: str) -> Optional[str]:
    """High-precision elapsed = now - started, to 18 decimal places (string)."""
    if not started_unix_18dp:
        return None
    try:
        from decimal import Decimal as _D, getcontext
        getcontext().prec = 40
        d = _D(now_unix_18dp) - _D(started_unix_18dp)
        return f"{d:.18f}"
    except Exception:
        return None


def _alive(pid: Optional[int]) -> bool:
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def read_status() -> Optional[Dict[str, Any]]:
    """Read the status, enrich with elapsed_s + liveness. A 'running' record
    whose driver pid is dead is reported as 'stale' (crashed mid-train)."""
    try:
        rec = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    started = rec.get("started_ts")
    ended = rec.get("ended_ts")
    now = time.time()
    rec["elapsed_s"] = round((ended or now) - started, 1) if started else None
    if rec.get("state") == "running" and not _alive(rec.get("pid")):
        rec["state"] = "stale"
        rec["note"] = "driver process gone — training likely crashed"
    return rec
