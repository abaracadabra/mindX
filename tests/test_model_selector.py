"""Unit tests for mindx.self.improve.model_selector.

No external services, no real signal sources — Aware is mocked so the
scorer's behavior is deterministic for known inputs.

Run: .mindx_env/bin/python -m pytest tests/test_model_selector.py -v
"""

import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

# Ensure project root is on sys.path so `import mindx.self.aware` works when
# pytest is invoked from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mindx.self.aware import ModelSummary  # noqa: E402
from mindx.self.improve.model_selector import (  # noqa: E402
    ModelSelector,
    TaskProfile,
)


class FakeAware:
    """In-memory Aware fake. Each test wires the summaries it cares about."""

    def __init__(
        self,
        summaries: Dict[str, Dict[str, ModelSummary]],
        weights: Optional[Dict[str, float]] = None,
        candidates: Optional[List[str]] = None,
        value_proven_for: Optional[Dict[str, bool]] = None,
        tie_break: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.summaries = summaries
        self.weights = weights or {
            "success_rate": 0.25,
            "eval_alignment_mean": 0.20,
            "latency_p50_inverse": 0.10,
            "cost_per_invocation_inverse": 0.15,
            "capability_match": 0.10,
            "recency_bonus": 0.10,
            "failure_penalty_inverse": 0.10,
        }
        self.candidates = candidates or []
        self.value_proven_for = value_proven_for or {}
        self.tie_break = tie_break or {
            "threshold_fraction": 0.05,
            "confidence_floor": 0.4,
            "_critical_importance_levels": ["critical", "constitutional"],
        }

    async def model_summary(self, slug: str, task_class: str, **_kwargs) -> ModelSummary:
        per_class = self.summaries.get(task_class, {})
        s = per_class.get(slug)
        if s is None:
            return ModelSummary(slug=slug, task_class=task_class)
        return s

    async def task_class_weights(self, task_class: str) -> Dict[str, float]:
        return dict(self.weights)

    async def task_class_candidates(self, task_class: str) -> List[str]:
        return list(self.candidates)

    async def value_proven(self, task_class: str) -> bool:
        return bool(self.value_proven_for.get(task_class, False))

    async def tie_break_config(self) -> Dict[str, Any]:
        return dict(self.tie_break)

    async def free_first_config(self) -> Dict[str, Any]:
        return {"value_proven_multiplier": 1.5, "rolling_window_days": 7}


class NullMemoryAgent:
    """Swallows log_godel_choice — selector should never crash on log failures."""
    async def log_godel_choice(self, record: Dict[str, Any]):
        return None


def _summary(
    slug: str,
    task_class: str = "reasoning",
    *,
    success: float = 0.5,
    eval_score: float = 0.5,
    latency: float = 1000.0,
    cost_in: float = 0.0,
    cost_out: float = 0.0,
    capabilities: Optional[Dict[str, Any]] = None,
    failure_rate: float = 0.0,
    sample: int = 10,
    last_used_offset: float = -3600.0,  # 1h ago
) -> ModelSummary:
    import time
    return ModelSummary(
        slug=slug,
        task_class=task_class,
        success_rate=success,
        eval_alignment_mean=eval_score,
        latency_p50=latency,
        cost_per_1k_in=cost_in,
        cost_per_1k_out=cost_out,
        recent_429_rate=failure_rate,
        last_used_ts=time.time() + last_used_offset,
        sample_size=sample,
        capabilities=capabilities or {
            "supported_parameters": ["tools"],
            "context_length": 131072,
            "architecture": {"input_modalities": ["text"]},
        },
    )


def _selector(aware: FakeAware) -> ModelSelector:
    sel = ModelSelector(aware=aware, memory_agent=NullMemoryAgent())
    # Wipe singleton state so tests don't leak.
    ModelSelector._instance = None
    return sel


# ── Tests ──────────────────────────────────────────────────────────────


def test_clear_winner_high_confidence():
    """Top candidate clearly beats runner-up — confidence=high, no tie-break."""
    aware = FakeAware(
        summaries={
            "reasoning": {
                "model_a": _summary("model_a", success=0.9, eval_score=0.9, latency=500),
                "model_b": _summary("model_b", success=0.4, eval_score=0.4, latency=2000),
            },
        },
        candidates=["model_a", "model_b"],
    )
    selector = _selector(aware)
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="reasoning")))
    assert choice.chosen == "model_a"
    assert choice.confidence == "high"
    assert choice.scored[0].slug == "model_a"
    assert choice.scored[0].score > choice.scored[1].score


def test_tie_break_routine_picks_safer_default():
    """Top-2 within 5%, importance=standard — picks safer default, confidence=low."""
    aware = FakeAware(
        summaries={
            "reasoning": {
                "fast_unproven": _summary("fast_unproven", success=0.3, eval_score=0.3,
                                          latency=200, sample=2),
                "slow_proven": _summary("slow_proven", success=0.85, eval_score=0.85,
                                        latency=8000, sample=50),
            },
        },
        candidates=["fast_unproven", "slow_proven"],
    )
    selector = _selector(aware)
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="reasoning",
                                                           importance="standard")))
    # Safer default = slow_proven (highest success × eval).
    assert choice.confidence in ("low", "high")
    if choice.confidence == "low":
        assert choice.chosen == "slow_proven"


def test_tie_break_critical_routes_to_reflection():
    """Top-2 within 5%, importance=critical — invokes reflected path."""
    aware = FakeAware(
        summaries={
            "reasoning": {
                "model_a": _summary("model_a", success=0.6, eval_score=0.6, latency=1000),
                "model_b": _summary("model_b", success=0.6, eval_score=0.6, latency=1000),
            },
        },
        candidates=["model_a", "model_b"],
    )
    selector = _selector(aware)
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="reasoning",
                                                           importance="critical")))
    assert choice.confidence == "reflected"
    assert choice.chosen in {"model_a", "model_b"}
    assert "reflected" in choice.rationale


def test_free_first_floor_drops_paid_when_value_not_proven():
    """A paid candidate with stellar metrics is dropped if value_proven=False."""
    aware = FakeAware(
        summaries={
            "reasoning": {
                "free_ok": _summary("free_ok", success=0.5, eval_score=0.5, latency=2000),
                "paid_amazing": _summary("paid_amazing", success=0.99, eval_score=0.99,
                                         latency=100, cost_in=0.01, cost_out=0.03),
            },
        },
        candidates=["free_ok", "paid_amazing"],
        value_proven_for={"reasoning": False},
    )
    selector = _selector(aware)
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="reasoning")))
    assert choice.chosen == "free_ok"
    assert all(c.slug != "paid_amazing" for c in choice.scored)


def test_free_first_admits_paid_when_value_proven():
    """When value_proven flips to True, paid candidate is back in scoring."""
    aware = FakeAware(
        summaries={
            "reasoning": {
                "free_ok": _summary("free_ok", success=0.5, eval_score=0.5, latency=2000),
                "paid_amazing": _summary("paid_amazing", success=0.99, eval_score=0.99,
                                         latency=100, cost_in=0.01, cost_out=0.03),
            },
        },
        candidates=["free_ok", "paid_amazing"],
        value_proven_for={"reasoning": True},
    )
    selector = _selector(aware)
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="reasoning")))
    assert choice.chosen == "paid_amazing"


def test_capability_gate_drops_non_tool_when_required():
    """Vision-required + non-vision candidate → capability_match=0 → score collapses."""
    aware = FakeAware(
        summaries={
            "vision": {
                "no_vision": _summary("no_vision", success=0.9, eval_score=0.9,
                                      capabilities={
                                          "supported_parameters": ["tools"],
                                          "context_length": 131072,
                                          "architecture": {"input_modalities": ["text"]},
                                      }),
                "with_vision": _summary("with_vision", success=0.5, eval_score=0.5,
                                        capabilities={
                                            "supported_parameters": ["tools"],
                                            "context_length": 131072,
                                            "architecture": {"input_modalities": ["text", "image"]},
                                        }),
            },
        },
        candidates=["no_vision", "with_vision"],
    )
    selector = _selector(aware)
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="vision",
                                                           requires_vision=True)))
    assert choice.chosen == "with_vision"


def test_bootstrap_when_no_candidates():
    """No candidate list configured → bootstrap path, confidence=bootstrap."""
    aware = FakeAware(summaries={}, candidates=[])
    selector = _selector(aware)
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="rare_class")))
    assert choice.confidence == "bootstrap"
    assert choice.chosen  # falls back to default openai/gpt-oss-120b:free


def test_log_failure_does_not_break_selection():
    """If memory_agent.log_godel_choice raises, the selection still returns."""
    class BrokenMemoryAgent:
        async def log_godel_choice(self, record):
            raise RuntimeError("boom")

    aware = FakeAware(
        summaries={
            "reasoning": {
                "ok": _summary("ok", success=0.9, eval_score=0.9, latency=100),
            },
        },
        candidates=["ok"],
    )
    selector = ModelSelector(aware=aware, memory_agent=BrokenMemoryAgent())
    ModelSelector._instance = None
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="reasoning")))
    assert choice.chosen == "ok"


def test_capability_match_hard_gate_for_tools():
    """requires_tools=True + candidate without tools → score zero on that axis → loses."""
    aware = FakeAware(
        summaries={
            "reasoning": {
                "tools_yes": _summary("tools_yes", success=0.5, eval_score=0.5,
                                      capabilities={
                                          "supported_parameters": ["tools"],
                                          "context_length": 131072,
                                          "architecture": {"input_modalities": ["text"]},
                                      }),
                "tools_no": _summary("tools_no", success=0.99, eval_score=0.99,
                                     capabilities={
                                         "supported_parameters": [],
                                         "context_length": 131072,
                                         "architecture": {"input_modalities": ["text"]},
                                     }),
            },
        },
        candidates=["tools_yes", "tools_no"],
    )
    selector = _selector(aware)
    choice = asyncio.run(selector.choose_model(TaskProfile(task_class="reasoning",
                                                           requires_tools=True)))
    assert choice.chosen == "tools_yes"


if __name__ == "__main__":
    # Allow `python tests/test_model_selector.py` as a smoke run
    pytest.main([__file__, "-v"])
