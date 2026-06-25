"""llm/token_appetite.py — mindX's lifetime token-appetite counter.

A persistent, monotonic count of ALL tokens mindX has actually ingested across
every inference — cloud free-tier AND local CPU (Ollama) — so the public
appetite display carries a real, ever-growing lifetime number, not a
per-process tally that resets on restart.

Operator seed (2026-06-24): the counter starts at **347,000,000** and only ever
counts UP, by ACTUAL recorded tokens (prompt + completion) from real calls. It
is never fabricated and never decremented. The increment hook lives at the top
of llm.inference_budget.record(), which both the OpenRouter and Ollama handlers
call with their real token counts — placed BEFORE the unlimited-provider
early-return so local CPU inference is included.

FAIL-OPEN: any error here is swallowed; counting must never break inference.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

SEED = 347_000_000  # operator baseline (2026-06-24)
_PERSIST = Path("data/monitoring/token_appetite.json")
_PERSIST_EVERY_S = 20.0


class TokenAppetite:
    _instance: Optional["TokenAppetite"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._total = float(SEED)
        self._seed = float(SEED)
        self._calls = 0          # number of token-bearing inferences counted since seed
        self._cpu_tokens = 0.0   # subtotal from local/unlimited providers (CPU)
        self._cloud_tokens = 0.0  # subtotal from rate-limited cloud providers
        self._started_ts = time.time()
        self._last_ts = 0.0
        self._last_persist = 0.0
        self._dlock = threading.Lock()
        self._load()

    @classmethod
    def instance(cls) -> "TokenAppetite":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    try:
                        cls._instance = cls()
                    except Exception:
                        inst = cls.__new__(cls)
                        inst._total = float(SEED); inst._seed = float(SEED)
                        inst._calls = 0; inst._cpu_tokens = 0.0; inst._cloud_tokens = 0.0
                        inst._started_ts = time.time(); inst._last_ts = 0.0
                        inst._last_persist = 0.0; inst._dlock = threading.Lock()
                        cls._instance = inst
        return cls._instance

    def _load(self) -> None:
        try:
            d = json.loads(_PERSIST.read_text())
            # Resume the running total; never below the seed (monotonic floor).
            self._total = max(float(d.get("total", SEED)), float(SEED))
            self._seed = float(d.get("seed", SEED))
            self._calls = int(d.get("calls", 0) or 0)
            self._cpu_tokens = float(d.get("cpu_tokens", 0) or 0)
            self._cloud_tokens = float(d.get("cloud_tokens", 0) or 0)
        except Exception:
            pass  # first run / unreadable → keep SEED defaults

    def add(self, tokens: int, *, cpu: bool = False) -> None:
        """Add ACTUAL ingested tokens to the lifetime counter. `cpu=True` for
        local/unlimited (Ollama) inference, so the CPU subtotal is tracked."""
        try:
            t = int(tokens or 0)
            if t <= 0:
                return
            self._total += t
            self._calls += 1
            if cpu:
                self._cpu_tokens += t
            else:
                self._cloud_tokens += t
            now = time.time()
            self._last_ts = now
            self._maybe_persist(now)
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        try:
            return {
                "seed": int(self._seed),
                "total": int(self._total),
                "ingested_since_seed": int(self._total - self._seed),
                "calls_since_seed": self._calls,
                "cpu_tokens": int(self._cpu_tokens),
                "cloud_tokens": int(self._cloud_tokens),
                "last_ingest_ts": round(self._last_ts, 0) if self._last_ts else None,
            }
        except Exception:
            return {"seed": SEED, "total": SEED, "ingested_since_seed": 0}

    def _maybe_persist(self, now: float, force: bool = False) -> None:
        if not force and now - self._last_persist < _PERSIST_EVERY_S:
            return
        with self._dlock:
            self._last_persist = now
        try:
            _PERSIST.parent.mkdir(parents=True, exist_ok=True)
            snap = self.snapshot()
            snap["updated_ts"] = now
            _PERSIST.write_text(json.dumps(snap, indent=2))
        except Exception:
            pass


# ---- module-level convenience ----
def add(tokens: int, *, cpu: bool = False) -> None:
    TokenAppetite.instance().add(tokens, cpu=cpu)


def total() -> int:
    return int(TokenAppetite.instance()._total)


def snapshot() -> Dict[str, Any]:
    return TokenAppetite.instance().snapshot()
