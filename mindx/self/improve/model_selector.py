"""mindx.self.improve.model_selector — self-aware model choice for self-improvement.

The introspective layer. Reads mindx.self.aware signal summaries, scores
candidates with deterministic per-task-class weights, picks one, logs the
choice via existing log_godel_choice infrastructure (which auto-emits
godel.choice + alignment.score catalogue events).

Architectural boundary (user-locked): this module is INTERNAL to mindX core.
It never reaches into the boardroom. The boardroom is a downstream service
that consumes mindX-as-a-service; mindX does not delegate self-improvement to
it.

Tie-break (when top-2 within 5%):
- importance ∈ {critical, constitutional} → single self-reflection LLM call
  from operator-frozen meta-list (recursion stop). Confidence: "reflected".
- otherwise → safer free default + low-confidence flag. Dream cycle reads
  low-confidence rows and retrains weights.

Free-first floor: paid candidates dropped unless aware.value_proven(task_class)
returns True (predicate currently stubbed; populated by Phase 3 retrain).
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from mindx.self.aware import Aware, ModelSummary

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
META_MODELS_FILE = _PROJECT_ROOT / "data" / "config" / "self_aware_meta_models.json"


@dataclass
class TaskProfile:
    """Profile of the task the selector is choosing a model for.

    The selector consults this to apply the right per-task-class weights and
    capability requirements.
    """
    task_class: str = "default"           # reasoning | codegen | planning | vision | ops | default
    importance: str = "standard"          # routine | standard | critical | constitutional
    cycle_id: Optional[str] = None        # joins to improvement journal entry
    requires_tools: bool = True
    requires_vision: bool = False
    min_context: int = 4096
    source_agent: str = "mindx.self.improve.model_selector"
    # Optional override list — if provided, used instead of bootstrap candidates
    candidate_override: Optional[List[str]] = None


@dataclass
class ScoredCandidate:
    slug: str
    score: float
    breakdown: Dict[str, float]
    summary: ModelSummary


@dataclass
class ModelChoice:
    chosen: str
    rationale: str
    confidence: str                       # high | low | reflected | bootstrap
    scored: List[ScoredCandidate] = field(default_factory=list)
    task_profile: Optional[TaskProfile] = None


# ── Scoring axes ──────────────────────────────────────────────────────────
#
# Each axis maps a ModelSummary field → [0,1] normalized score.
# The weighted sum (per-task-class weights from self_aware_weights.json)
# yields the candidate's total score.

def _axis_success_rate(s: ModelSummary) -> float:
    if s.sample_size == 0:
        return 0.5  # neutral prior
    return max(0.0, min(1.0, s.success_rate))


def _axis_eval_alignment_mean(s: ModelSummary) -> float:
    if s.eval_alignment_mean <= 0:
        return 0.5
    # GEval scores are typically 0-1 already
    return max(0.0, min(1.0, s.eval_alignment_mean))


def _axis_latency_p50_inverse(s: ModelSummary) -> float:
    # 0ms → 1.0; 30s → ~0.0. Hyperbolic decay to keep small differences meaningful.
    if s.latency_p50 <= 0:
        return 0.5
    return 1.0 / (1.0 + s.latency_p50 / 5000.0)


def _axis_cost_per_invocation_inverse(s: ModelSummary) -> float:
    # Free → 1.0. Paid models scaled hyperbolically.
    cost = s.cost_per_1k_in + s.cost_per_1k_out
    if cost <= 0:
        return 1.0
    return 1.0 / (1.0 + cost * 100.0)


def _axis_capability_match(s: ModelSummary, profile: TaskProfile) -> float:
    """Capability gate. Hard-fails (returns 0.0) only when capabilities ARE
    KNOWN and explicitly fall short. Empty/missing capabilities → trust the
    operator-curated candidate list (returns 1.0). The Phase 2 wiring will
    fetch live capabilities from OpenRouter and pass them in; until then we
    don't penalize cold-start.
    """
    caps = s.capabilities or {}
    if not caps:
        return 1.0  # unknown — trust operator list
    sp = caps.get("supported_parameters")
    if profile.requires_tools and sp is not None and "tools" not in sp:
        return 0.0  # hard gate
    arch = caps.get("architecture") or {}
    inputs = arch.get("input_modalities")
    if profile.requires_vision and inputs is not None and "image" not in inputs:
        return 0.0
    ctx = caps.get("context_length")
    if (isinstance(ctx, (int, float)) and profile.min_context > 0
            and ctx > 0 and ctx < profile.min_context):
        return 0.0
    return 1.0


def _axis_recency_bonus(s: ModelSummary) -> float:
    if s.last_used_ts <= 0:
        return 0.3  # never used → small prior, doesn't dominate
    age_seconds = max(0.0, time.time() - s.last_used_ts)
    # Exponential decay with 1-day half-life
    half_life = 24 * 3600.0
    return math.pow(0.5, age_seconds / half_life)


def _axis_failure_penalty_inverse(s: ModelSummary) -> float:
    # 0% → 1.0; 100% → 0.0; linear.
    return max(0.0, 1.0 - s.recent_429_rate)


_AXIS_FUNCS = {
    "success_rate": lambda s, p: _axis_success_rate(s),
    "eval_alignment_mean": lambda s, p: _axis_eval_alignment_mean(s),
    "latency_p50_inverse": lambda s, p: _axis_latency_p50_inverse(s),
    "cost_per_invocation_inverse": lambda s, p: _axis_cost_per_invocation_inverse(s),
    "capability_match": _axis_capability_match,
    "recency_bonus": lambda s, p: _axis_recency_bonus(s),
    "failure_penalty_inverse": lambda s, p: _axis_failure_penalty_inverse(s),
}


# ── ModelSelector ─────────────────────────────────────────────────────────


class ModelSelector:
    """Self-aware model selector for self-improvement cycles.

    Usage:
        selector = await ModelSelector.get_instance()
        choice = await selector.choose_model(TaskProfile(task_class="reasoning",
                                                        importance="standard"))
        print(choice.chosen, choice.confidence, choice.rationale)
    """

    _instance: Optional["ModelSelector"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __init__(
        self,
        aware: Optional[Aware] = None,
        memory_agent: Optional[Any] = None,  # injected for testability
        meta_models: Optional[List[str]] = None,
    ) -> None:
        self.aware = aware or Aware.get_instance()
        self.memory_agent = memory_agent  # lazy-resolved on first log if None
        self._meta_models = meta_models  # None = read from file lazily

    @classmethod
    async def get_instance(cls) -> "ModelSelector":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def choose_model(self, task_profile: TaskProfile) -> ModelChoice:
        weights = await self.aware.task_class_weights(task_profile.task_class)
        if not weights:
            # No weights configured — bootstrap with safest free default.
            return await self._bootstrap_pick(task_profile, reason="no weights configured")

        candidates = task_profile.candidate_override or await self.aware.task_class_candidates(
            task_profile.task_class
        )
        if not candidates:
            return await self._bootstrap_pick(task_profile, reason="no candidates configured")

        # Score every candidate.
        scored: List[ScoredCandidate] = []
        for slug in candidates:
            summary = await self.aware.model_summary(slug, task_profile.task_class)
            score, breakdown = self._weighted_score(summary, task_profile, weights)
            scored.append(ScoredCandidate(slug, score, breakdown, summary))

        # Free-first floor: drop paid candidates unless value_proven.
        value_proven = await self.aware.value_proven(task_profile.task_class)
        if not value_proven:
            scored = [c for c in scored if (c.summary.cost_per_1k_in + c.summary.cost_per_1k_out) <= 0.0]
            if not scored:
                return await self._bootstrap_pick(task_profile, reason="all candidates paid; value not proven")

        scored.sort(key=lambda c: c.score, reverse=True)

        # Tie-break / resolve.
        chosen, rationale, confidence = await self._resolve(scored, task_profile)
        choice = ModelChoice(
            chosen=chosen,
            rationale=rationale,
            confidence=confidence,
            scored=scored,
            task_profile=task_profile,
        )
        await self._log(choice, weights, value_proven)
        return choice

    # ── Internal: scoring ────────────────────────────────────────────────

    def _weighted_score(
        self,
        summary: ModelSummary,
        profile: TaskProfile,
        weights: Dict[str, float],
    ) -> Tuple[float, Dict[str, float]]:
        breakdown: Dict[str, float] = {}
        total = 0.0
        weight_total = 0.0
        for axis_name, weight in weights.items():
            if axis_name.startswith("_"):
                continue
            fn = _AXIS_FUNCS.get(axis_name)
            if fn is None:
                continue
            try:
                axis_score = float(fn(summary, profile))
            except Exception:
                axis_score = 0.0
            breakdown[axis_name] = axis_score
            total += weight * axis_score
            weight_total += weight
        if weight_total > 0:
            total /= weight_total
        # Hard gate: capability_match==0 means the candidate fails a hard
        # requirement (tools / vision / min_context). Collapse total to 0 so
        # no amount of success_rate/eval_alignment can resurrect a non-fit.
        if breakdown.get("capability_match") == 0.0:
            total = 0.0
        return total, breakdown

    # ── Internal: resolve / tie-break ─────────────────────────────────────

    async def _resolve(
        self,
        scored: List[ScoredCandidate],
        profile: TaskProfile,
    ) -> Tuple[str, str, str]:
        if not scored:
            return ("", "no candidates after scoring", "bootstrap")

        cfg = await self.aware.tie_break_config()
        threshold = float(cfg.get("threshold_fraction", 0.05))
        floor = float(cfg.get("confidence_floor", 0.4))
        critical_levels = set(cfg.get("_critical_importance_levels") or ["critical", "constitutional"])

        top = scored[0]
        runner = scored[1] if len(scored) > 1 else None
        gap = (top.score - runner.score) if runner else top.score

        # Confident pick.
        if top.score >= floor and (runner is None or gap >= threshold * max(top.score, 1e-9)):
            return (
                top.slug,
                self._format_rationale(top, scored, profile, "high"),
                "high",
            )

        # Tie-break path.
        if profile.importance in critical_levels:
            chosen, refl_rationale = await self._self_reflection(scored, profile)
            return (
                chosen,
                refl_rationale,
                "reflected",
            )

        # Routine path: pick safer default (highest success_rate × eval_alignment_mean).
        def safer_key(c: ScoredCandidate) -> float:
            return c.summary.success_rate * max(c.summary.eval_alignment_mean, 0.01)

        safer = max(scored, key=safer_key)
        return (
            safer.slug,
            self._format_rationale(safer, scored, profile, "low"),
            "low",
        )

    async def _self_reflection(
        self,
        scored: List[ScoredCandidate],
        profile: TaskProfile,
    ) -> Tuple[str, str]:
        """Critical-importance tie-break: single LLM call from operator-frozen
        meta-list. The meta-list is NEVER chosen by the selector — recursion stop.

        Phase 1 implementation: deterministic fallback. Picks the candidate with
        highest (success_rate × eval_alignment_mean). The LLM-reflection wiring
        lives in Phase 2 once the call sites exist; the contract here is stable.
        """
        # Phase 1 deterministic stand-in.
        def reflective_key(c: ScoredCandidate) -> float:
            return (c.summary.success_rate * max(c.summary.eval_alignment_mean, 0.01)
                    + 0.1 * c.score)
        chosen = max(scored, key=reflective_key)
        rationale = (
            f"reflected[deterministic-fallback] task_class={profile.task_class} "
            f"importance={profile.importance} top_score={scored[0].score:.3f} "
            f"chosen={chosen.slug} chosen_score={chosen.score:.3f} "
            f"reason='success_rate × eval_alignment, awaiting Phase 2 LLM reflection'"
        )
        return (chosen.slug, rationale)

    def _format_rationale(
        self,
        chosen: ScoredCandidate,
        scored: List[ScoredCandidate],
        profile: TaskProfile,
        confidence: str,
    ) -> str:
        top_three = ", ".join(f"{c.slug}={c.score:.3f}" for c in scored[:3])
        breakdown = ", ".join(f"{k}={v:.2f}" for k, v in chosen.breakdown.items())
        return (
            f"task_class={profile.task_class} importance={profile.importance} "
            f"confidence={confidence} chosen={chosen.slug} score={chosen.score:.3f} "
            f"top3=[{top_three}] breakdown[{breakdown}] "
            f"sample_size={chosen.summary.sample_size}"
        )

    # ── Internal: bootstrap ───────────────────────────────────────────────

    async def _bootstrap_pick(self, profile: TaskProfile, reason: str) -> ModelChoice:
        """No usable candidates — bootstrap from operator skill→model map."""
        candidates = await self.aware.task_class_candidates(profile.task_class)
        chosen = candidates[0] if candidates else "openai/gpt-oss-120b:free"
        rationale = f"bootstrap: {reason} — using operator-curated fallback {chosen}"
        choice = ModelChoice(
            chosen=chosen,
            rationale=rationale,
            confidence="bootstrap",
            scored=[],
            task_profile=profile,
        )
        # Best-effort log; bootstrap state is an interesting signal for the dream cycle.
        await self._log(choice, weights={}, value_proven=False)
        return choice

    # ── Internal: meta-models (recursion stop) ────────────────────────────

    def _load_meta_models(self) -> List[str]:
        if self._meta_models is not None:
            return self._meta_models
        try:
            data = json.loads(META_MODELS_FILE.read_text())
            return list(data.get("models") or [])
        except (OSError, json.JSONDecodeError):
            return ["openai/gpt-oss-120b:free"]

    # ── Internal: logging ─────────────────────────────────────────────────

    async def _log(
        self,
        choice: ModelChoice,
        weights: Dict[str, float],
        value_proven: bool,
    ) -> None:
        """Reuse memory_agent.log_godel_choice — auto-emits godel.choice + alignment.score."""
        record = {
            "source_agent": (choice.task_profile.source_agent if choice.task_profile
                             else "mindx.self.improve.model_selector"),
            "choice_type": "self_aware_model_selection",
            "cycle_id": choice.task_profile.cycle_id if choice.task_profile else None,
            "task_class": choice.task_profile.task_class if choice.task_profile else "default",
            "importance": choice.task_profile.importance if choice.task_profile else "standard",
            "perception": {
                "signals_consulted": [
                    "godel_choices.jsonl",
                    "catalogue_events.jsonl",
                    "model_performance_metrics.json",
                    "fitness/current_snapshot.json",
                    "memory.dream tuning recs",
                ],
                "weights": weights,
                "value_proven": value_proven,
                "candidate_count": len(choice.scored),
            },
            "options_considered": [
                {
                    "slug": c.slug,
                    "score": round(c.score, 4),
                    "breakdown": {k: round(v, 4) for k, v in c.breakdown.items()},
                    "sample_size": c.summary.sample_size,
                }
                for c in choice.scored
            ],
            "chosen_option": choice.chosen,
            "rationale": choice.rationale,
            "confidence": choice.confidence,
            "outcome": "pending",  # set by downstream consumer when campaign completes
        }
        agent = self.memory_agent
        if agent is None:
            try:
                from agents.memory_agent import MemoryAgent
                # MemoryAgent is a regular class — construct directly. Cache the
                # instance on the selector so subsequent selections reuse it.
                agent = MemoryAgent()
                self.memory_agent = agent
            except Exception:
                return  # logging is best-effort; do not break selection on log failure
        try:
            await agent.log_godel_choice(record)
        except Exception:
            pass  # selection has already happened — log failure is non-fatal
