"""mindx.self.aware — read-only signal aggregator.

Reads mindX's own logs to surface per-model summaries. No decision logic —
that lives in mindx.self.improve. Other consumers (audit dashboards, future
bandit algorithms, external observers) can import this without entanglement.

Sources (all append-only or single-snapshot JSON, all already populated):
1. data/logs/godel_choices.jsonl     — past selector decisions + outcomes
2. data/logs/catalogue_events.jsonl  — universal event envelope
3. data/model_performance_metrics.json (optional) — per-model aggregates
4. data/fitness/current_snapshot.json (optional) — agent fitness axes
5. docs/IMPROVEMENT_JOURNAL.md (optional, narrative) — read for context
6. memory.dream payloads in catalogue_events — tuning recommendations

The aggregator caches for 60s. Callers MUST tolerate missing/empty sources;
mindX runs on machines where any of these may not yet exist.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Project root resolution — mindx/self/aware/__init__.py → ../../../
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

GODEL_LOG = _PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
CATALOGUE_LOG = _PROJECT_ROOT / "data" / "logs" / "catalogue_events.jsonl"
MODEL_METRICS = _PROJECT_ROOT / "data" / "model_performance_metrics.json"
FITNESS_SNAPSHOT = _PROJECT_ROOT / "data" / "fitness" / "current_snapshot.json"
WEIGHTS_FILE = _PROJECT_ROOT / "data" / "config" / "self_aware_weights.json"

CACHE_TTL_SECONDS = 60.0
SCAN_TAIL_LINES = 5000  # how many recent log lines to consider per query
RECENCY_HALF_LIFE_SECONDS = 24 * 3600  # 1 day half-life on recency_bonus


@dataclass
class ModelSummary:
    """Per-(model, task_class) self-awareness summary."""
    slug: str
    task_class: str
    success_rate: float = 0.0          # [0,1] fraction of past selections with outcome=success
    eval_alignment_mean: float = 0.0   # [0,1] mean GEval alignment.score on this model's choices
    latency_p50: float = 0.0           # ms, lower is better
    latency_p95: float = 0.0           # ms
    cost_per_1k_in: float = 0.0        # USD per 1k input tokens (0 for :free)
    cost_per_1k_out: float = 0.0       # USD per 1k output tokens
    recent_429_rate: float = 0.0       # [0,1] fraction of recent calls that 429'd
    last_used_ts: float = 0.0          # epoch seconds, 0 = never
    sample_size: int = 0               # number of historical decisions found
    capabilities: Dict[str, Any] = field(default_factory=dict)  # tools, vision, ctx_max
    dream_flags: List[str] = field(default_factory=list)  # axis names dream cycle flagged for attention


def _read_jsonl_tail(path: Path, max_lines: int = SCAN_TAIL_LINES) -> List[Dict[str, Any]]:
    """Read the last `max_lines` of a JSONL file. Returns empty list on missing file."""
    if not path.exists():
        return []
    try:
        with path.open("rb") as f:
            f.seek(0, 2)
            size = f.tell()
            block = min(size, max_lines * 1024)
            f.seek(max(0, size - block))
            data = f.read().decode("utf-8", errors="replace")
        lines = data.splitlines()[-max_lines:]
    except OSError:
        return []
    out = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _load_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


class Aware:
    """Read-only self-awareness signal aggregator. 60s cache."""

    _instance: Optional["Aware"] = None

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, str], Tuple[float, ModelSummary]] = {}
        self._weights_cache: Tuple[float, Dict[str, Any]] = (0.0, {})
        self._dream_flags_cache: Tuple[float, Dict[str, List[str]]] = (0.0, {})

    @classmethod
    def get_instance(cls) -> "Aware":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def model_summary(
        self,
        slug: str,
        task_class: str,
        catalogue_capabilities: Optional[Dict[str, Any]] = None,
    ) -> ModelSummary:
        """Per-(model, task_class) summary with 60s cache."""
        now = time.time()
        key = (slug, task_class)
        cached = self._cache.get(key)
        if cached and now - cached[0] < CACHE_TTL_SECONDS:
            return cached[1]
        summary = self._compute_summary(slug, task_class, catalogue_capabilities or {})
        self._cache[key] = (now, summary)
        return summary

    async def task_class_weights(self, task_class: str) -> Dict[str, float]:
        """Current per-axis weights for `task_class`. Cached 60s."""
        now = time.time()
        if now - self._weights_cache[0] < CACHE_TTL_SECONDS and self._weights_cache[1]:
            data = self._weights_cache[1]
        else:
            data = _load_json(WEIGHTS_FILE) or {}
            self._weights_cache = (now, data)
        classes = data.get("task_classes", {})
        return classes.get(task_class) or classes.get("default") or {}

    async def task_class_candidates(self, task_class: str) -> List[str]:
        """Bootstrap candidate slugs for `task_class` from operator-curated map."""
        now = time.time()
        if now - self._weights_cache[0] < CACHE_TTL_SECONDS and self._weights_cache[1]:
            data = self._weights_cache[1]
        else:
            data = _load_json(WEIGHTS_FILE) or {}
            self._weights_cache = (now, data)
        cands = data.get("task_class_candidates", {})
        return cands.get(task_class) or cands.get("default") or []

    async def value_proven(self, task_class: str) -> bool:
        """Free-first floor predicate. True iff rolling 7-day campaign value × success rate
        exceeds projected paid cost × multiplier. Conservative default: False until the
        retrain phase populates this signal. Lives here because the floor is a self-aware
        question, not a config one."""
        # Phase 1: stub returns False (free-first wins by default). Phase 3 retrain
        # populates a derived field on the weights file when value is proven.
        weights = _load_json(WEIGHTS_FILE) or {}
        proven = weights.get("free_first", {}).get("value_proven", {}) or {}
        return bool(proven.get(task_class, False))

    async def tie_break_config(self) -> Dict[str, Any]:
        weights = _load_json(WEIGHTS_FILE) or {}
        return weights.get("tie_break") or {"threshold_fraction": 0.05, "confidence_floor": 0.4}

    async def free_first_config(self) -> Dict[str, Any]:
        weights = _load_json(WEIGHTS_FILE) or {}
        return weights.get("free_first") or {"value_proven_multiplier": 1.5, "rolling_window_days": 7}

    # ── Internal: signal extraction ──────────────────────────────────────

    def _compute_summary(
        self,
        slug: str,
        task_class: str,
        catalogue_caps: Dict[str, Any],
    ) -> ModelSummary:
        s = ModelSummary(slug=slug, task_class=task_class, capabilities=catalogue_caps)

        # 1. Gödel choice ledger — past decisions for this (slug, task_class)
        godel_rows = _read_jsonl_tail(GODEL_LOG)
        decisions = [
            r for r in godel_rows
            if r.get("chosen_option") == slug
            and (r.get("task_class") == task_class or task_class == "default")
        ]
        if decisions:
            s.sample_size = len(decisions)
            successes = sum(1 for r in decisions if r.get("outcome") == "success")
            s.success_rate = successes / len(decisions)
            eval_scores = [r.get("eval_score") for r in decisions if r.get("eval_score") is not None]
            if eval_scores:
                s.eval_alignment_mean = sum(eval_scores) / len(eval_scores)

        # 2. Catalogue events — latency, 429 rate, last_used_ts
        cat_rows = _read_jsonl_tail(CATALOGUE_LOG)
        tool_results_for_slug = []
        last_used = 0.0
        recent_429 = 0
        recent_total = 0
        for r in cat_rows:
            kind = r.get("kind")
            payload = r.get("payload") or {}
            event_slug = payload.get("model") or payload.get("slug") or payload.get("chosen_option")
            if event_slug != slug:
                continue
            ts = float(r.get("ts") or 0.0)
            if ts > last_used:
                last_used = ts
            if kind == "tool.result":
                lat = payload.get("latency_ms")
                if isinstance(lat, (int, float)):
                    tool_results_for_slug.append(float(lat))
                if payload.get("error_code") == 429:
                    recent_429 += 1
                recent_total += 1
        if tool_results_for_slug:
            tool_results_for_slug.sort()
            s.latency_p50 = tool_results_for_slug[len(tool_results_for_slug) // 2]
            s.latency_p95 = tool_results_for_slug[min(len(tool_results_for_slug) - 1,
                                                     int(0.95 * len(tool_results_for_slug)))]
        if recent_total > 0:
            s.recent_429_rate = recent_429 / recent_total
        s.last_used_ts = last_used

        # 3. Model performance metrics — augment if file exists
        metrics = _load_json(MODEL_METRICS)
        if metrics and slug in metrics:
            m = metrics[slug]
            if s.success_rate == 0.0 and "success_rate" in m:
                s.success_rate = float(m["success_rate"])
            if s.latency_p50 == 0.0 and "avg_latency_ms" in m:
                s.latency_p50 = float(m["avg_latency_ms"])

        # 4. Costs — pull from catalogue capabilities (passed in by selector from live OR catalog)
        pricing = catalogue_caps.get("pricing") or {}
        try:
            s.cost_per_1k_in = float(pricing.get("prompt", 0.0)) * 1000.0
            s.cost_per_1k_out = float(pricing.get("completion", 0.0)) * 1000.0
        except (TypeError, ValueError):
            pass

        # 5. Dream flags — recent memory.dream payloads with tuning recommendations
        for r in reversed(cat_rows[-500:]):  # last 500 entries
            if r.get("kind") != "memory.dream":
                continue
            recs = (r.get("payload") or {}).get("tuning_recommendations") or []
            if not isinstance(recs, list):
                continue
            for rec in recs:
                axis = (rec or {}).get("axis")
                if axis and axis not in s.dream_flags:
                    s.dream_flags.append(str(axis))
            if len(s.dream_flags) >= 3:
                break

        return s
