"""llm/model_health.py — per-MODEL interaction health ledger (data = logs = memory).

The companion to llm/inference_budget.py. Where InferenceBudget tracks
per-PROVIDER rate-limit budget, this tracks per-MODEL (slug) *quality of
interaction*: did the model answer, was the answer usable, did it 404
(decommissioned), did it rate-limit, how fast, how many tokens.

Why this exists (2026-06-24): mindX's model lists were hand-curated and the
OpenRouter free roster silently rotted — 7 of 8 board models returned 404
("decommissioned"). Every autonomous campaign then failed because selection
kept routing to dead slugs. The fix the operator asked for: **selection must
learn from actual interaction with each and every model, and prune the dead.**

Doctrine:
- Every call is an observation. The ledger is derived from real interactions and
  is rebuildable by replaying data/logs (catalogue_events.jsonl tool.result +
  godel_choices.jsonl outcomes).
- A 404 / "decommissioned" / "no endpoints" is a HARD-DEAD signal — one is
  enough to retire the slug. Repeated soft failures (empty/parse/5xx) accumulate
  to a soft-dead. A 429 is NOT death — that is the budget's job (back off, retry).
- Dead is not forever: after a cooldown the slug enters `probing`, selection may
  try it once, and a single success revives it. The roster heals itself.
- FAIL-OPEN: any error in here returns "live"/headroom — the ledger can
  deprioritise a model but must never block all inference.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_PERSIST = Path("data/monitoring/model_health.json")

# One of these in an error body retires the slug immediately.
_DEAD_PATTERNS = (
    "decommissioned",
    "no endpoints found",
    "not a valid model",
    "is not a valid model",
    "no allowed providers",
    "model not found",
    "unknown model",
    # Long-horizon quota exhaustion is NOT a transient 429: an ollama.com
    # weekly usage limit keeps the slug dark for hours-to-days. Retiring it
    # gives the right semantics — dead now, probe every 6h, revive the moment
    # the quota resets. Observed live 2026-07-04: gpt-oss:120b-cloud returned
    # 429 "weekly usage limit" and stayed 'live', so planning kept routing to
    # it and degraded to skeletons.
    "weekly usage limit",
    "monthly usage limit",
)
# HTTP statuses that, for a *named model*, mean "this slug is gone" (not transient).
_DEAD_STATUSES = {404}

_SOFT_DEAD_AFTER = 5          # consecutive soft failures → soft-dead
_PROBE_COOLDOWN_S = 6 * 3600  # dead slug becomes `probing` after this
_LAT_EWMA_ALPHA = 0.3


def _classify(ok: bool, http_status: Optional[int], error_text: Optional[str]) -> str:
    """Return one of: 'ok' | 'dead' | 'rate_limited' | 'soft_fail'."""
    if ok:
        return "ok"
    txt = (error_text or "").lower()
    # Dead patterns win over the 429 short-circuit: a weekly/monthly usage
    # limit arrives as HTTP 429 but is a long-horizon outage, not a transient.
    if http_status in _DEAD_STATUSES or any(p in txt for p in _DEAD_PATTERNS):
        return "dead"
    if http_status == 429 or "rate" in txt or "quota" in txt or "429" in txt:
        return "rate_limited"
    return "soft_fail"


class _Model:
    __slots__ = (
        "slug", "provider", "total", "ok", "fail", "http_404", "rate_limited",
        "consec_fail", "last_ok_ts", "last_fail_ts", "last_error", "tokens_total",
        "latency_ewma", "status", "dead_since", "dead_reason", "revived",
    )

    def __init__(self, slug: str, provider: str = ""):
        self.slug = slug
        self.provider = provider
        self.total = 0
        self.ok = 0
        self.fail = 0
        self.http_404 = 0
        self.rate_limited = 0
        self.consec_fail = 0
        self.last_ok_ts = 0.0
        self.last_fail_ts = 0.0
        self.last_error = ""
        self.tokens_total = 0
        self.latency_ewma = 0.0
        self.status = "live"     # live | degraded | dead | probing
        self.dead_since = 0.0
        self.dead_reason = ""
        self.revived = 0

    def success_rate(self) -> float:
        return (self.ok / self.total) if self.total else 0.0

    def record(self, now: float, kind: str, *, tokens: int, latency_ms: Optional[float],
               error_text: Optional[str], provider: Optional[str]) -> None:
        self.total += 1
        if provider:
            self.provider = provider
        if tokens:
            self.tokens_total += int(tokens)
        if latency_ms and latency_ms > 0:
            self.latency_ewma = (latency_ms if self.latency_ewma == 0
                                 else _LAT_EWMA_ALPHA * latency_ms + (1 - _LAT_EWMA_ALPHA) * self.latency_ewma)
        if kind == "ok":
            self.ok += 1
            self.consec_fail = 0
            self.last_ok_ts = now
            # Any success revives a dead/probing slug (the roster heals).
            if self.status in ("dead", "probing"):
                self.status = "live"
                self.revived += 1
                self.dead_since = 0.0
                self.dead_reason = ""
            elif self.status == "degraded":
                self.status = "live"
            return
        # failure paths
        self.fail += 1
        self.last_fail_ts = now
        if error_text:
            self.last_error = error_text[:300]
        if kind == "rate_limited":
            self.rate_limited += 1
            return  # 429 is the budget's job, not a health signal
        # soft_fail or dead
        self.consec_fail += 1
        if kind == "dead":
            self.http_404 += 1
            self._mark_dead(now, error_text or "404/decommissioned")
        elif self.consec_fail >= _SOFT_DEAD_AFTER:
            self._mark_dead(now, f"{self.consec_fail} consecutive soft failures")
        elif self.status == "live":
            self.status = "degraded"

    def _mark_dead(self, now: float, reason: str) -> None:
        self.status = "dead"
        self.dead_since = now
        self.dead_reason = reason[:200]

    def effective_status(self, now: float) -> str:
        """Dead slugs surface as 'probing' once their cooldown elapses, so the
        selector may try them once and revive them on success."""
        if self.status == "dead" and self.dead_since and (now - self.dead_since) >= _PROBE_COOLDOWN_S:
            return "probing"
        return self.status

    def snapshot(self, now: float) -> Dict[str, Any]:
        return {
            "slug": self.slug,
            "provider": self.provider,
            "status": self.effective_status(now),
            "total": self.total,
            "ok": self.ok,
            "fail": self.fail,
            "success_rate": round(self.success_rate(), 3),
            "http_404": self.http_404,
            "rate_limited": self.rate_limited,
            "consec_fail": self.consec_fail,
            "tokens_total": self.tokens_total,
            "latency_ms": round(self.latency_ewma, 0),
            "last_ok_ts": round(self.last_ok_ts, 0),
            "last_fail_ts": round(self.last_fail_ts, 0),
            "last_error": self.last_error,
            "dead_reason": self.dead_reason,
            "revived": self.revived,
        }


class ModelHealth:
    _instance: Optional["ModelHealth"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._models: Dict[str, _Model] = {}
        self._plock = threading.Lock()
        self._last_persist = 0.0
        self._load()

    @classmethod
    def instance(cls) -> "ModelHealth":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    try:
                        cls._instance = cls()
                    except Exception:
                        inst = cls.__new__(cls)
                        inst._models = {}
                        inst._plock = threading.Lock()
                        inst._last_persist = 0.0
                        cls._instance = inst
        return cls._instance

    @staticmethod
    def _norm(slug: Optional[str]) -> str:
        return (slug or "").strip()

    def _get(self, slug: str, provider: str = "") -> Optional[_Model]:
        s = self._norm(slug)
        if not s:
            return None
        m = self._models.get(s)
        if m is None:
            m = _Model(s, provider)
            self._models[s] = m
        return m

    def _load(self) -> None:
        try:
            data = json.loads(_PERSIST.read_text())
            for slug, row in (data.get("models") or {}).items():
                m = _Model(slug, row.get("provider", ""))
                for k in ("total", "ok", "fail", "http_404", "rate_limited",
                          "consec_fail", "tokens_total", "revived"):
                    setattr(m, k, int(row.get(k, 0) or 0))
                m.latency_ewma = float(row.get("latency_ms", 0) or 0)
                m.last_ok_ts = float(row.get("last_ok_ts", 0) or 0)
                m.last_fail_ts = float(row.get("last_fail_ts", 0) or 0)
                m.last_error = row.get("last_error", "") or ""
                m.status = row.get("status_raw", row.get("status", "live")) or "live"
                if m.status == "probing":
                    m.status = "dead"  # re-derive probing from cooldown
                m.dead_since = float(row.get("dead_since", 0) or 0)
                m.dead_reason = row.get("dead_reason", "") or ""
                self._models[slug] = m
        except Exception:
            pass

    # ---- public API (all fail-open) ----
    def record(self, slug: Optional[str], *, ok: bool = True, http_status: Optional[int] = None,
               error_text: Optional[str] = None, tokens: int = 0,
               latency_ms: Optional[float] = None, provider: Optional[str] = None) -> None:
        try:
            s = self._norm(slug)
            if not s:
                return
            m = self._get(s, provider or "")
            if m is None:
                return
            now = time.time()
            kind = _classify(ok, http_status, error_text)
            m.record(now, kind, tokens=int(tokens or 0), latency_ms=latency_ms,
                     error_text=error_text, provider=provider)
            self._maybe_persist(now)
        except Exception:
            pass

    def is_dead(self, slug: Optional[str]) -> bool:
        """True only for fully-dead slugs (not probing, not degraded). Fail-open: unknown → False."""
        try:
            m = self._models.get(self._norm(slug))
            if m is None:
                return False
            return m.effective_status(time.time()) == "dead"
        except Exception:
            return False

    def status(self, slug: Optional[str]) -> str:
        try:
            m = self._models.get(self._norm(slug))
            return m.effective_status(time.time()) if m else "unknown"
        except Exception:
            return "unknown"

    def filter_alive(self, slugs: Iterable[str]) -> List[str]:
        """Drop fully-dead slugs; keep live/probing/degraded/unknown. Never returns
        empty if the input was non-empty AND all are dead — returns the least-dead
        (most recently dead) so inference is never fully blocked."""
        slugs = list(slugs or [])
        if not slugs:
            return []
        alive = [s for s in slugs if not self.is_dead(s)]
        if alive:
            return alive
        # All dead — fail-open: return the one dead longest ago (closest to reprobe).
        now = time.time()
        def deadness(s: str) -> float:
            m = self._models.get(self._norm(s))
            return m.dead_since if m else now
        return [min(slugs, key=deadness)]

    def reconcile_roster(self, provider_prefix: str, live_slugs: Iterable[str]) -> Dict[str, Any]:
        """Reconcile known slugs for a provider against the live roster.

        provider_prefix: e.g. "" matches all, or a vendor like "nvidia/".
        live_slugs: the set currently offered by the provider (e.g. OpenRouter
        :free models). Known slugs NOT in this set are marked dead (roster);
        slugs that reappear in the set are revived to 'live'.
        """
        live = set(self._norm(s) for s in (live_slugs or []))
        now = time.time()
        retired, revived = [], []
        try:
            for slug, m in list(self._models.items()):
                if provider_prefix and not slug.startswith(provider_prefix):
                    continue
                # only judge OpenRouter-style vendor/model:free slugs against the roster
                if ":free" not in slug and "/" not in slug:
                    continue
                if slug in live:
                    if m.status == "dead" and m.dead_reason.startswith("roster"):
                        m.status = "live"
                        m.dead_since = 0.0
                        m.dead_reason = ""
                        m.revived += 1
                        revived.append(slug)
                else:
                    if m.status != "dead":
                        m._mark_dead(now, "roster: absent from live provider list")
                        retired.append(slug)
            self._maybe_persist(now, force=True)
        except Exception:
            pass
        return {"retired": retired, "revived": revived, "live_count": len(live)}

    def seed(self, slug: str, provider: str = "") -> None:
        """Register a known slug without recording an interaction (so the roster
        reconciler can judge config slugs that have never been called)."""
        try:
            self._get(self._norm(slug), provider)
        except Exception:
            pass

    def snapshot(self) -> Dict[str, Any]:
        try:
            now = time.time()
            models = {s: m.snapshot(now) for s, m in self._models.items()}
            live = [s for s, r in models.items() if r["status"] == "live"]
            dead = [s for s, r in models.items() if r["status"] == "dead"]
            probing = [s for s, r in models.items() if r["status"] == "probing"]
            return {
                "models": models,
                "summary": {
                    "known": len(models),
                    "live": len(live),
                    "dead": len(dead),
                    "probing": len(probing),
                    "total_tokens": sum(r["tokens_total"] for r in models.values()),
                    "total_calls": sum(r["total"] for r in models.values()),
                },
                "dead_slugs": dead,
            }
        except Exception:
            return {"models": {}, "summary": {}, "dead_slugs": []}

    def _maybe_persist(self, now: float, force: bool = False) -> None:
        if not force and now - self._last_persist < 30:
            return
        with self._plock:
            self._last_persist = now
        try:
            _PERSIST.parent.mkdir(parents=True, exist_ok=True)
            snap = self.snapshot()
            # preserve raw status (dead vs derived probing) for reload fidelity
            for slug, m in self._models.items():
                if slug in snap["models"]:
                    snap["models"][slug]["status_raw"] = m.status
                    snap["models"][slug]["dead_since"] = m.dead_since
            _PERSIST.write_text(json.dumps(snap, indent=2))
        except Exception:
            pass


# ---- module-level convenience (hot-path API) ----
def record(slug: Optional[str], *, ok: bool = True, http_status: Optional[int] = None,
           error_text: Optional[str] = None, tokens: int = 0,
           latency_ms: Optional[float] = None, provider: Optional[str] = None) -> None:
    ModelHealth.instance().record(slug, ok=ok, http_status=http_status, error_text=error_text,
                                  tokens=tokens, latency_ms=latency_ms, provider=provider)


def is_dead(slug: Optional[str]) -> bool:
    return ModelHealth.instance().is_dead(slug)


def status(slug: Optional[str]) -> str:
    return ModelHealth.instance().status(slug)


def filter_alive(slugs: Iterable[str]) -> List[str]:
    return ModelHealth.instance().filter_alive(slugs)


def reconcile_roster(provider_prefix: str, live_slugs: Iterable[str]) -> Dict[str, Any]:
    return ModelHealth.instance().reconcile_roster(provider_prefix, live_slugs)


def snapshot() -> Dict[str, Any]:
    return ModelHealth.instance().snapshot()
