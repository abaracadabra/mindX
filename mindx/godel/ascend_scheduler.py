"""ascend_scheduler — the gated, autonomous RIGHT-apex trigger.

mindXtrain v1.0.0 describes "autonomous training gated by mindX SEA agent
decisions". This is that gate. It connects today's objective self-eval
feedback loop (agents/core/self_eval_feedback.py) to a Schmidhüber ascent —
but behind a deliberately conservative set of guards so the system never
trains itself by accident:

  1. BOTH flags set — MINDX_ENABLE_MINDXTRAIN (bridge armed) AND
     MINDX_ENABLE_AUTONOMOUS_TRAIN (autonomous opted in). Arming the bridge for
     a supervised operator ascent alone is NOT enough.
  2. mindXtrain installed and CPU-train-active (v1.0.0+).
  3. NOT resource_bound — never train on a saturated box (mirrors the
     self_eval_feedback doctrine exactly: contention is not the moment to add
     the heaviest possible work).
  4. Past the 24h ascend watermark — lunar-like cadence; weight consolidation
     is a slow rhythm, not a per-cycle reflex.

When all gates pass, it runs ONE bounded CPU ascent (dcoach-gated, promoting
to an Ollama model) and stamps the watermark. Everything is best-effort and
swallows its own errors — the autonomous loop must never crash on it.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional, Tuple

from .mindxtrain import (autonomous_train_enabled, is_enabled,
                         ASCEND_COOLDOWN_S, CPU_RECIPE_REAL)
from .mindxtrain import bridge as _bridge
from .mindxtrain.ascend import ascend_recipe, read_watermark, write_watermark

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

logger = logging.getLogger(__name__)

DATA_MEMORY = PROJECT_ROOT / "data" / "memory"   # mindx_dreams adapter reads here
ASCEND_WORK = PROJECT_ROOT / "data" / "godel" / "ascend"
ASCEND_LOG = PROJECT_ROOT / "data" / "logs" / "ascend_log.jsonl"


def should_ascend(self_eval: Optional[dict], cap=None) -> Tuple[bool, str]:
    """Decide whether an autonomous ascent may run now. Returns (ok, reason)."""
    if not autonomous_train_enabled():
        return False, "autonomous training not armed (needs both flags)"
    cap = cap or _bridge.discover()
    if not cap.installed:
        return False, "mindXtrain not installed"
    if not cap.cpu_train_active:
        return False, f"mindXtrain not CPU-train-active (version {cap.version})"
    if self_eval and self_eval.get("resource_bound"):
        return False, "resource_bound — not training on a saturated box"
    last = read_watermark(ASCEND_WORK)
    if last is not None and (time.time() - last) < ASCEND_COOLDOWN_S:
        hrs = round((ASCEND_COOLDOWN_S - (time.time() - last)) / 3600, 1)
        return False, f"within ascend cooldown ({hrs}h remaining)"
    return True, "all gates passed"


def _next_generation() -> int:
    """Generation counter persisted alongside the watermark."""
    gpath = ASCEND_WORK / ".generation"
    try:
        return int(gpath.read_text().strip()) + 1
    except Exception:
        return 1


def _record_generation(n: int) -> None:
    try:
        ASCEND_WORK.mkdir(parents=True, exist_ok=True)
        (ASCEND_WORK / ".generation").write_text(str(n))
    except Exception:
        pass


async def run_ascent_if_due(self_eval: Optional[dict] = None, *, sea=None) -> Optional[dict]:
    """Run one autonomous ascent when all gates pass; else return None.

    Best-effort: never raises. Emits a train.ascended catalogue event and
    appends to data/logs/ascend_log.jsonl so /insight/godel/ascend can show it.
    """
    cap = _bridge.discover()
    ok, reason = should_ascend(self_eval, cap)
    if not ok:
        logger.debug("ascend_scheduler: skipping — %s", reason)
        return None

    generation = _next_generation()
    # CPU training regimen from settings: smallest model, 33% of the processor,
    # 24h wall window (≈8h effective), measured on the single CPU+RAM profile.
    from .mindxtrain.settings import regimen, measure_efficiency
    _reg = regimen()
    logger.info("ascend_scheduler: autonomous ascent generation %d (regimen %s%% / %sh)",
                generation, _reg.get("cpu_percent"), _reg.get("wall_hours"))
    try:
        result = await ascend_recipe(
            work_dir=ASCEND_WORK / f"gen{generation}",
            generation=generation,
            data_memory_dir=DATA_MEMORY,
            recipe=CPU_RECIPE_REAL,
            cpu_percent=int(_reg.get("cpu_percent", 33)), cpu_nice=19,
            use_imprint=True,
            promote=True,
            register_fallback=False,   # served but not auto-routed to production
            train_timeout=int(_reg.get("wall_hours", 24)) * 3600,
        )
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("ascend_scheduler: ascent failed: %s", e)
        return None

    write_watermark(ASCEND_WORK, time.time())
    _record_generation(generation)
    rec = result.as_dict()
    rec["ts"] = time.time()
    rec["trigger"] = "autonomous_self_eval"
    delta = (result.recall or {}).get("delta")
    cost = round(result.wall_seconds * int(_reg.get("cpu_percent", 33)) / 100.0, 1) or None
    rec["measurement"] = measure_efficiency(delta, cost)
    _append_log(rec)
    _emit(result)
    return rec


def _append_log(rec: dict) -> None:
    try:
        ASCEND_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ASCEND_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, default=str) + "\n")
    except Exception:
        pass


def _emit(result) -> None:
    try:
        import asyncio
        from agents.catalogue.events import emit_catalogue_event
        kind = "train.promoted" if result.promoted else "train.ascended"
        payload = {"generation": result.generation, "stage": result.stage,
                   "recall": result.recall, "ollama_model": result.ollama_model,
                   "rows": result.forge_result.row_count if result.forge_result else 0}
        asyncio.create_task(emit_catalogue_event(
            kind=kind, actor="ascend_scheduler", payload=payload,
            source_log="mindx.godel.ascend_scheduler.run_ascent_if_due"))
    except Exception:
        pass
