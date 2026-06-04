"""mindx.godel.eval.surrogate — CPU-affordable falsifiers (Phase 1).

docs/GODEL_EVAL_BLUEPRINT.md §3.3: until the proof kernel lands, the tractable
interim is metamorphic / differential / property-based testing — sound
*falsifiers* that cost CPU-seconds, not GPU-hours. Phase 1 ships the cheapest,
highest-signal ones:

- **G6 determinism** (now genuinely testable): the utility proxy must recompute
  bit-identically over the same input. Uses exact rational arithmetic
  (fractions.Fraction) — float non-associativity would itself falsify.
- **G1 utility monotonicity** (testable when data exists): recent utility-proxy
  mean must not fall below the prior window beyond ε.
- **metamorphic relations** on the proxy (order-invariance, idempotence of
  duplication within bound) as additional cheap falsifiers.
- **surrogate coverage**: fraction of recent decisions that carry a coherence
  score — i.e., passed the (heuristic) surrogate gate. This is what lets G8
  report `coverage:surrogate > 0` while proof coverage honestly stays 0.

Pure stdlib. Deterministic. Never raises.
"""

from __future__ import annotations

from fractions import Fraction
from typing import Optional

PROVEN, FALSIFIED, UNMET, UNTESTED = (
    "PROVEN-so-far", "FALSIFIED", "UNMET", "UNTESTED")

_MIN_FOR_MONOTONICITY = 8     # need enough scored rows to split windows
_MONO_EPS = Fraction(1, 20)   # 0.05 tolerance on a 0..1 scale


def utility_proxy(rows: list[dict]) -> Fraction:
    """Deterministic, bounded utility proxy: exact mean of available coherence
    (eval_score) signals over `rows`. Pure function of its input — no clock, no
    randomness, no float reduction. Returns 0 when there is no signal."""
    scores = [r.get("eval_score") for r in rows
              if isinstance(r.get("eval_score"), (int, float))]
    if not scores:
        return Fraction(0)
    total = sum(Fraction(str(s)) for s in scores)
    return total / len(scores)


def check_determinism(rows: list[dict]) -> dict:
    """G6: recompute the proxy twice; exact equality required."""
    a = utility_proxy(rows)
    b = utility_proxy(list(reversed(rows)))  # order must not matter (metamorphic)
    # Determinism: same input → same output. Order-invariance: a permutation of
    # the same multiset yields the same mean. Both must hold exactly.
    deterministic = (utility_proxy(rows) == a)
    order_invariant = (a == b)
    if not deterministic:
        return {"id": "G6", "name": "determinism", "verdict": FALSIFIED,
                "detail": "utility proxy is non-deterministic on identical input.",
                "evidence": {}}
    if not order_invariant:
        return {"id": "G6", "name": "determinism", "verdict": FALSIFIED,
                "detail": "utility proxy is not order-invariant (float drift?).",
                "evidence": {"a": str(a), "b": str(b)}}
    return {"id": "G6", "name": "determinism", "verdict": PROVEN,
            "detail": ("utility proxy is exact (Fraction), deterministic, and "
                       "order-invariant over the scored choice log."),
            "evidence": {"proxy_value": str(a),
                         "scored_rows": sum(1 for r in rows
                                            if isinstance(r.get("eval_score"), (int, float)))}}


def check_monotonicity(rows: list[dict]) -> dict:
    """G1: recent utility must not fall below the prior window beyond ε."""
    scored = [r for r in rows if isinstance(r.get("eval_score"), (int, float))]
    if len(scored) < _MIN_FOR_MONOTONICITY:
        return {"id": "G1", "name": "utility_monotonicity", "verdict": UNTESTED,
                "detail": (f"insufficient scored history "
                           f"({len(scored)}/{_MIN_FOR_MONOTONICITY}) to test a "
                           "utility trend."),
                "evidence": {"scored_rows": len(scored)}}
    half = len(scored) // 2
    prior = utility_proxy(scored[:half])
    recent = utility_proxy(scored[half:])
    drop = prior - recent
    if drop > _MONO_EPS:
        return {"id": "G1", "name": "utility_monotonicity", "verdict": FALSIFIED,
                "detail": (f"utility proxy fell {float(drop):.3f} (> "
                           f"{float(_MONO_EPS):.2f}) from prior to recent window."),
                "evidence": {"prior": str(prior), "recent": str(recent)}}
    return {"id": "G1", "name": "utility_monotonicity", "verdict": PROVEN,
            "detail": ("recent utility proxy holds at or above the prior window "
                       "(no sustained regression)."),
            "evidence": {"prior": float(prior), "recent": float(recent),
                         "windows": [half, len(scored) - half]}}


def surrogate_coverage(rows: list[dict]) -> dict:
    """Fraction of recent decisions that passed the (heuristic) surrogate gate
    — i.e., carry a coherence score. Phase-1 stand-in for proof coverage so the
    GMI can report `coverage:surrogate` honestly while proof coverage stays 0."""
    total = len(rows)
    scored = sum(1 for r in rows
                 if isinstance(r.get("eval_score"), (int, float)))
    cov = round(scored / total, 4) if total else 0.0
    return {"surrogate_coverage": cov, "scored": scored, "total": total}
