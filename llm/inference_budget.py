"""llm/inference_budget.py — mindX's shared inference "metabolism".

A process-wide, FAIL-OPEN ledger of per-provider rate-limit budget. Both the
rate limiters (gating) and — crucially — the model selectors (routing) consume
it, so mindX flows inference to whichever tier has budget: cloud → router →
local, and back as the windows refill. Effective limits adapt to observed 429s
(down on throttle, up on sustained success) so the organism tracks real provider
limits up *and* down without a restart.

Goal (per operator directive): consume the free tiers **fully but safely** —
maximise free cloud/router use, stop at a safety margin BEFORE the limit so we
never trigger a 429/block, then route to local for the overflow.

Real free-tier limits (multi-window) — see docs/ollama/cloud/rate_limiting.md:
- Ollama Cloud: ~50 req / 5-hour session, ~500 req/week (+ a gentle per-minute
  spread so bursts don't look like automation).
- OpenRouter (free, <10 credits): 20 req/min, 50 req/day.
A SAFETY factor (0.9 → consume to 90% of each window, the documented 10% buffer)
makes headroom hit 0 *before* the real limit, so selection shifts to local in
time. Raise SAFETY toward 1.0 to consume more aggressively.

Design constraints:
- The read path (`headroom`) is SYNC (the hot path for the sync ModelSelector).
- NEVER raise to callers. Unknown/error/unlimited provider → headroom 1.0. The
  budget can deprioritise a provider but can NEVER block all inference; local is
  always 1.0 and is the failsafe.
"""
from __future__ import annotations

import json
import random
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Providers with effectively unlimited local budget → always headroom 1.0.
_UNLIMITED = {"ollama", "vllm", "local", "ollama_local"}

# Consume to this fraction of each window before headroom hits 0 (10% buffer →
# stop before the limit, never wait for a 429). The documented Ollama Cloud
# strategy. Raise toward 1.0 to consume the free tier more aggressively.
_SAFETY = 0.9

# Operator reference (2026-06-24): "3 per hour is a conversation." The reasonable
# inquiry floor — a single autonomous thread should engage at least at a
# conversational cadence, and the per-model throttle should never look like an
# automated firehose. 3/hr = 72/day per thread. The DAILY CEILING is the sum of
# free-tier daily caps (target = ceiling − 1, "max−1"): consume the free tiers
# fully but stop one short of the wall. daily_budget() reports both bounds.
_CONVERSATIONAL_PER_HOUR = 3
_CONVERSATIONAL_PER_DAY = _CONVERSATIONAL_PER_HOUR * 24  # 72

# Real free-tier limits as (window_seconds, request_limit) tuples — headroom is
# the MIN across all windows, so the tightest binding constraint governs.
_PROVIDER_WINDOWS: Dict[str, List[Tuple[int, int]]] = {
    # Ollama Cloud free: spread per-minute, 50 per 5h session, 500 per week.
    "ollama_cloud": [(60, 10), (18000, 50), (604800, 500)],
    # OpenRouter free (<10 credits purchased): 20 req/min, 50 req/day.
    "openrouter":   [(60, 20), (86400, 50)],
    # Other free tiers (per their published docs).
    "gemini":       [(60, 15), (86400, 1500)],
    "groq":         [(60, 30), (86400, 14400)],
    "mistral":      [(60, 60)],
}
_DEFAULT_WINDOWS: List[Tuple[int, int]] = [(60, 30), (3600, 300)]  # unknown providers

_PERSIST = Path("data/monitoring/inference_budget.json")


class _Window:
    __slots__ = ("span", "base", "eff", "ts")

    def __init__(self, span: int, limit: int):
        self.span = span          # window length, seconds
        self.base = float(limit)  # configured limit
        self.eff = float(limit)   # adaptive effective limit
        self.ts: deque = deque()  # request timestamps within the window

    def trim(self, now: float) -> None:
        while self.ts and now - self.ts[0] > self.span:
            self.ts.popleft()

    def headroom(self, now: float, safety: float) -> float:
        self.trim(now)
        cap = max(1.0, self.eff * safety)
        return max(0.0, 1.0 - len(self.ts) / cap)


class _ProviderBudget:
    __slots__ = (
        "provider", "windows", "safety", "tok", "backoff_until",
        "consec_429", "last_success", "last_429", "total_req", "total_429",
    )

    def __init__(self, provider: str, windows: List[Tuple[int, int]], safety: float):
        self.provider = provider
        self.safety = safety
        self.windows = [_Window(s, lim) for (s, lim) in windows]
        self.tok: deque = deque()   # (ts, tokens) last 60s, for display
        self.backoff_until = 0.0
        self.consec_429 = 0
        self.last_success = 0.0
        self.last_429 = 0.0
        self.total_req = 0
        self.total_429 = 0

    def headroom(self, now: float) -> float:
        if now < self.backoff_until:
            return 0.0
        if not self.windows:
            return 1.0
        return min(w.headroom(now, self.safety) for w in self.windows)

    def record(self, now: float, ok: bool, tokens: int, retry_after: Optional[float]) -> None:
        self.total_req += 1
        for w in self.windows:
            w.ts.append(now)
        if tokens:
            self.tok.append((now, tokens))
        while self.tok and now - self.tok[0][0] > 60:
            self.tok.popleft()
        if ok:
            self.consec_429 = 0
            self.last_success = now
            # Breathe: recover effective limits toward configured on sustained
            # success (a provider RAISING its limit, or recovery after a throttle).
            for w in self.windows:
                if w.eff < w.base:
                    w.eff = min(w.base, w.eff * 1.05 + 0.5)
        else:
            # 429 / quota / empty-throttle: back off + lower effective limits
            # (a provider LOWERING its limit). We aim to never get here — headroom
            # should have routed us to local first — but adapt if we do.
            self.consec_429 += 1
            self.total_429 += 1
            self.last_429 = now
            backoff = min(30 * (2 ** (self.consec_429 - 1)), 600)
            if retry_after and retry_after > 0:
                backoff = max(backoff, float(retry_after))
            backoff += backoff * random.uniform(-0.15, 0.15)
            self.backoff_until = now + backoff
            for w in self.windows:
                w.eff = max(1.0, w.eff * 0.7)

    def snapshot(self, now: float) -> Dict[str, Any]:
        hr = self.headroom(now)
        # Report the tightest (binding) window.
        binding = None
        if self.windows:
            binding = min(self.windows, key=lambda w: w.headroom(now, self.safety))
        return {
            "provider": self.provider,
            "headroom": round(hr, 3),
            "safety": self.safety,
            "windows": [
                {"span_s": w.span, "limit": round(w.base, 1), "eff": round(w.eff, 1),
                 "used": len(w.ts)} for w in self.windows
            ],
            "binding_window_s": binding.span if binding else None,
            "binding_used": (len(binding.ts) if binding else 0),
            "binding_limit": (round(binding.base, 1) if binding else None),
            "tokens_min": sum(t for _, t in self.tok),
            "backoff_s": max(0, round(self.backoff_until - now, 1)),
            "consec_429": self.consec_429,
            "total_req": self.total_req,
            "total_429": self.total_429,
        }


class InferenceBudget:
    _instance: Optional["InferenceBudget"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._providers: Dict[str, _ProviderBudget] = {}
        self._windows: Dict[str, List[Tuple[int, int]]] = dict(_PROVIDER_WINDOWS)
        self._safety = _SAFETY
        self._plock = threading.Lock()
        self._last_persist = 0.0
        self._load_config()
        self._load_persisted()

    @classmethod
    def instance(cls) -> "InferenceBudget":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    try:
                        cls._instance = cls()
                    except Exception:
                        inst = cls.__new__(cls)
                        inst._providers = {}
                        inst._windows = dict(_PROVIDER_WINDOWS)
                        inst._safety = _SAFETY
                        inst._plock = threading.Lock()
                        inst._last_persist = 0.0
                        cls._instance = inst
        return cls._instance

    @staticmethod
    def _norm(provider: Optional[str]) -> str:
        return (provider or "").strip().lower()

    def _load_config(self) -> None:
        # ollama.yaml cloud.rate_limits — if the operator set explicit per-min /
        # per-hour cloud numbers, fold them in as additional windows (the tighter
        # of the configured vs the built-in real-tier windows governs anyway).
        try:
            import yaml  # noqa
            y = yaml.safe_load(Path("models/ollama.yaml").read_text()) or {}
            cl = ((y.get("cloud") or {}).get("rate_limits")) or {}
            extra: List[Tuple[int, int]] = []
            if cl.get("requests_per_minute"):
                extra.append((60, int(cl["requests_per_minute"])))
            if cl.get("requests_per_hour"):
                extra.append((3600, int(cl["requests_per_hour"])))
            if extra:
                base = list(self._windows.get("ollama_cloud", []))
                # de-dup by span, keep the smaller limit per span (tighter wins)
                merged: Dict[int, int] = {}
                for s, lim in base + extra:
                    merged[s] = min(merged.get(s, lim), lim)
                self._windows["ollama_cloud"] = sorted(merged.items())
        except Exception:
            pass

    def _load_persisted(self) -> None:
        # Rehydrate the ledger across restarts. A weekly/session quota that hit
        # 100% must stay noted after a service restart — the windows and the
        # hard backoff are the durable memory of "the free tier is consumed".
        try:
            raw = json.loads(_PERSIST.read_text())
            st = (raw.get("_state") or {}).get("providers") or {}
            now = time.time()
            for p, ps in st.items():
                b = self._get(p)
                if b is None:
                    continue
                b.backoff_until = float(ps.get("backoff_until", 0) or 0)
                b.consec_429 = int(ps.get("consec_429", 0) or 0)
                b.last_429 = float(ps.get("last_429", 0) or 0)
                b.total_req = int(ps.get("total_req", 0) or 0)
                b.total_429 = int(ps.get("total_429", 0) or 0)
                saved = {int(w.get("span", -1)): w for w in ps.get("windows", [])}
                for w in b.windows:
                    ws = saved.get(w.span)
                    if not ws:
                        continue
                    w.eff = max(1.0, float(ws.get("eff", w.base) or w.base))
                    for t in ws.get("ts", []):
                        # tolerate rounding/clock skew: clamp future ts to now
                        if isinstance(t, (int, float)) and now - float(t) <= w.span:
                            w.ts.append(min(float(t), now))
        except Exception:
            pass

    def _state(self) -> Dict[str, Any]:
        return {
            "providers": {
                p: {
                    "backoff_until": b.backoff_until,
                    "consec_429": b.consec_429,
                    "last_429": b.last_429,
                    "total_req": b.total_req,
                    "total_429": b.total_429,
                    "windows": [
                        {"span": w.span, "eff": w.eff, "ts": [round(t, 2) for t in w.ts]}
                        for w in b.windows
                    ],
                }
                for p, b in self._providers.items()
            }
        }

    def _get(self, provider: str) -> Optional[_ProviderBudget]:
        p = self._norm(provider)
        if not p or p in _UNLIMITED:
            return None
        b = self._providers.get(p)
        if b is None:
            wins = self._windows.get(p, _DEFAULT_WINDOWS)
            b = _ProviderBudget(p, wins, self._safety)
            self._providers[p] = b
        return b

    # ---- public API (all fail-open) ----
    def headroom(self, provider: Optional[str]) -> float:
        """0..1 fraction of budget available (after the safety margin).
        Unlimited/unknown/error → 1.0."""
        try:
            p = self._norm(provider)
            if not p or p in _UNLIMITED:
                return 1.0
            b = self._get(p)
            return b.headroom(time.time()) if b else 1.0
        except Exception:
            return 1.0

    def available(self, provider: Optional[str]) -> bool:
        return self.headroom(provider) > 0.0

    def record(self, provider: Optional[str], *, ok: bool = True,
               tokens: int = 0, retry_after: Optional[float] = None) -> None:
        try:
            p = self._norm(provider)
            # Lifetime token appetite — count ACTUAL ingested tokens from EVERY
            # provider, INCLUDING local CPU (Ollama / unlimited), so this must run
            # BEFORE the unlimited-provider early-return. Cloud vs CPU is split by
            # whether the provider is rate-limited (_UNLIMITED == local/CPU).
            if ok and tokens and tokens > 0:
                try:
                    from llm.token_appetite import add as _appetite_add
                    _appetite_add(int(tokens), cpu=(p in _UNLIMITED))
                except Exception:
                    pass
            if not p or p in _UNLIMITED:
                return
            b = self._get(p)
            if b is not None:
                now = time.time()
                b.record(now, bool(ok), int(tokens or 0), retry_after)
                self._maybe_persist(now)
        except Exception:
            pass

    def exhaust(self, provider: Optional[str], *, until: Optional[float] = None,
                for_seconds: float = 21600.0) -> None:
        """Explicit quota-consumed note: this provider's free tier is at 100%
        (e.g. the ollama.com weekly usage limit). Hard backoff → headroom 0 →
        selection routes to local until `until` (epoch) or now+for_seconds
        (default 6h, the model_health probe cadence; a failed re-probe renews
        the note). Persisted immediately so a restart cannot forget it."""
        try:
            b = self._get(self._norm(provider))
            if b is None:
                return
            now = time.time()
            b.backoff_until = max(b.backoff_until, float(until) if until else now + for_seconds)
            b.total_429 += 1
            b.last_429 = now
            self._last_persist = 0.0
            self._maybe_persist(now)
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        try:
            now = time.time()
            return {p: b.snapshot(now) for p, b in self._providers.items()}
        except Exception:
            return {}

    def daily_budget(self) -> Dict[str, Any]:
        """Aggregate daily inference budget — the overall calls/day ceiling and
        what has been consumed today (the operator's "do the math on a complete
        day" request). The ceiling is the sum of free-tier daily caps; target is
        ceiling−1 ("max−1"). Floor reference is the conversational cadence
        (3/hr = 72/day per thread).

        Per provider we take the longest-span window as the daily proxy, scaling
        sub-day windows to a full day (limit × 86400/span) so an RPM-only tier
        (e.g. mistral) still contributes a daily number.
        """
        try:
            now = time.time()
            DAY = 86400.0
            per_provider: Dict[str, Any] = {}
            ceiling = 0.0
            used = 0.0
            # Union of configured + live providers so the ceiling reflects all
            # known free tiers, not just the ones touched this process.
            names = set(self._windows) | set(self._providers)
            for name in sorted(names):
                wins = self._windows.get(name, _DEFAULT_WINDOWS)
                if not wins:
                    continue
                span, limit = max(wins, key=lambda w: w[0])  # longest-span window
                scale = DAY / span if span < DAY else 1.0
                day_limit = round(limit * scale)
                # used: count timestamps in the matching live window if present
                day_used = 0
                b = self._providers.get(name)
                if b is not None:
                    w = next((w for w in b.windows if w.span == span), None)
                    if w is not None:
                        w.trim(now)
                        day_used = round(len(w.ts) * scale)
                ceiling += day_limit
                used += day_used
                per_provider[name] = {
                    "day_limit": day_limit,
                    "day_used": day_used,
                    "remaining": max(0, day_limit - day_used),
                    "window_span_s": span,
                    "rpm_derived": span < DAY,
                }
            ceiling = int(ceiling)
            used = int(used)
            return {
                "ceiling_per_day": ceiling,
                "target_per_day": max(0, ceiling - 1),  # max−1
                "used_today": used,
                "remaining_today": max(0, ceiling - used),
                "utilization_pct": round(100.0 * used / ceiling, 2) if ceiling else 0.0,
                "conversational_floor_per_hour": _CONVERSATIONAL_PER_HOUR,
                "conversational_floor_per_day": _CONVERSATIONAL_PER_DAY,
                "concurrent_conversations_supported": (ceiling // _CONVERSATIONAL_PER_DAY) if _CONVERSATIONAL_PER_DAY else 0,
                "per_provider": per_provider,
            }
        except Exception:
            return {}

    def _maybe_persist(self, now: float) -> None:
        if now - self._last_persist < 30:
            return
        with self._plock:
            self._last_persist = now
        try:
            _PERSIST.parent.mkdir(parents=True, exist_ok=True)
            out = self.snapshot()
            out["_state"] = self._state()  # durable ledger, reloaded at startup
            _PERSIST.write_text(json.dumps(out, indent=2))
        except Exception:
            pass


# ---- module-level convenience (the hot-path API used everywhere) ----
def headroom(provider: Optional[str]) -> float:
    return InferenceBudget.instance().headroom(provider)


def available(provider: Optional[str]) -> bool:
    return InferenceBudget.instance().available(provider)


def record(provider: Optional[str], *, ok: bool = True,
           tokens: int = 0, retry_after: Optional[float] = None) -> None:
    InferenceBudget.instance().record(provider, ok=ok, tokens=tokens, retry_after=retry_after)


def exhaust(provider: Optional[str], *, until: Optional[float] = None,
            for_seconds: float = 21600.0) -> None:
    InferenceBudget.instance().exhaust(provider, until=until, for_seconds=for_seconds)


def snapshot() -> Dict[str, Any]:
    return InferenceBudget.instance().snapshot()


def daily_budget() -> Dict[str, Any]:
    return InferenceBudget.instance().daily_budget()
