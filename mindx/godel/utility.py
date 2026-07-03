"""mindx.godel.utility — the formal utility function U (Phase 3).

A Gödel machine cannot exist without a fixed, total, machine-evaluable utility.
This is it: a pure, deterministic function of exact rationals over a logged
state, with the anti-wireheading invariant baked into its *structure* rather
than its weights.

THE ANTI-WIREHEADING FLOOR (the heart of G5): alignment is not a weighted term
that efficiency can buy out — it is a hard floor. If measured alignment falls
below the floor, U returns BOTTOM (−∞ sentinel), which is below every finite
utility. So no gain in task success, cost, or knowledge can ever compensate a
safety regression. Safety is lexicographically prior to everything else.

U is also reflectively rewritable, but only under its own preference: a change
to U (or its version) must carry a proof that the new U is preferred *under the
current U* (reflective consistency) — see prover.build_reflective_consistency_
certificate. This prevents the machine from redefining U to be trivially
maximal (wireheading via goal-editing).

Pure stdlib, exact fractions.Fraction. Deterministic. Never raises on a
well-formed state.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Optional

UTIL_VERSION = "1.0.0"   # changing this is itself a reflectively-gated rewrite

# Weights (exact rationals). Alignment is NOT here — it is a structural floor.
W_TASK = Fraction(50, 100)
W_COST = Fraction(20, 100)
W_RISK = Fraction(20, 100)
W_KNOW = Fraction(10, 100)

DEFAULT_ALIGNMENT_FLOOR = Fraction(1, 2)


class _Bottom:
    """The −∞ sentinel. Below every finite Utility. Singleton."""
    _inst: Optional["_Bottom"] = None

    def __new__(cls):
        if cls._inst is None:
            cls._inst = super().__new__(cls)
        return cls._inst

    def __repr__(self) -> str:
        return "BOTTOM"


BOTTOM = _Bottom()


@dataclass(frozen=True)
class Utility:
    """A utility value: either a finite exact rational, or BOTTOM."""
    value: Optional[Fraction]   # None iff bottom
    bottom: bool = False

    @staticmethod
    def of(v: Fraction) -> "Utility":
        return Utility(value=v, bottom=False)

    @staticmethod
    def bot() -> "Utility":
        return Utility(value=None, bottom=True)

    # Total order: BOTTOM < every finite utility; finite compare by value.
    def __lt__(self, other: "Utility") -> bool:
        if self.bottom:
            return not other.bottom            # BOTTOM < finite; BOTTOM !< BOTTOM
        if other.bottom:
            return False
        return self.value < other.value

    def __le__(self, other: "Utility") -> bool:
        return self == other or self < other

    def ge(self, other: "Utility") -> bool:
        return not (self < other)

    def to_rational_str(self) -> str:
        if self.bottom or self.value is None:
            raise ValueError("BOTTOM has no rational representation")
        return f"{self.value.numerator}/{self.value.denominator}"

    def __repr__(self) -> str:
        return "U(BOTTOM)" if self.bottom else f"U({float(self.value):.4f})"


def _frac(x: Any, default: Fraction = Fraction(0)) -> Fraction:
    if isinstance(x, bool):
        return default
    if isinstance(x, (int, Fraction)):
        return Fraction(x)
    if isinstance(x, str) and x.strip():
        try:
            return Fraction(x)
        except Exception:
            return default
    if isinstance(x, float):
        # accept floats by exact decimal-ish conversion (deterministic)
        try:
            return Fraction(str(x))
        except Exception:
            return default
    return default


def u(state: dict, *, alignment_floor: Fraction = DEFAULT_ALIGNMENT_FLOOR) -> Utility:
    """Compute U(state). Total, deterministic, exact.

    Recognized state keys (all optional, rational-coercible, on a 0..1 scale
    unless noted):
        task_success      — task / improvement success rate
        alignment         — minimum measured alignment score (the floored term)
        cost              — normalized resource/$ cost (penalty)
        unverified_surface— fraction of code not proof/surrogate covered (risk)
        knowledge_growth  — normalized catalogue growth (reward)
    """
    alignment = _frac(state.get("alignment"), Fraction(1))
    # THE FLOOR: a safety regression is uncompensable.
    if alignment < alignment_floor:
        return Utility.bot()

    task = _frac(state.get("task_success"))
    cost = _frac(state.get("cost"))
    risk = _frac(state.get("unverified_surface"))
    know = _frac(state.get("knowledge_growth"))

    value = (W_TASK * task) - (W_COST * cost) - (W_RISK * risk) + (W_KNOW * know)
    return Utility.of(value)
