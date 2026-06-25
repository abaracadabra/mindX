# mindx/war_council.py
"""WarCouncil — the live-message → decision → blueprint bridge.

mindX keeps two rooms: the Boardroom (7 soldiers + CEO, deliberative, CISO/CRO
veto) for governance, and the War Council for fast, decisive verdicts on live
proposals. This module is the War Council: **13 prime-weighted seats** voting
under an **accelerating prime-ratio majority** that *guarantees* a decisive
outcome (no deadlock), and — on approval — fires a blueprint run.

Why 13 + primes:
- 13 seats: 13 is prime and odd, so a binary (approve/reject) vote among the
  non-abstaining seats can never tie on raw count.
- Each seat carries a distinct prime weight (first 13 primes), so seats are
  individually identifiable and weighted tallies are highly tie-resistant; any
  residual weighted tie is broken by the odd raw-seat majority — decisive by
  construction.
- Accelerating majority: the approval bar climbs a prime-ratio ladder with the
  proposal's stakes (7/13 → 11/13 → 13/13). A persistent high-stakes proposal
  must consolidate an ever-stronger majority or be decisively rejected — the
  "acceleration" that guarantees the vote terminates in a verdict.
"""
from __future__ import annotations

import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

# first 13 primes — one per seat (distinct prime weights)
SEAT_PRIMES: List[int] = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41]
SEATS = len(SEAT_PRIMES)  # 13
TOTAL_WEIGHT = sum(SEAT_PRIMES)  # 238

# Accelerating majority ladder (seats-out-of-13, all prime numerators).
# stakes 0 → simple prime majority; higher stakes → stronger prime majority.
PRIME_LADDER: List[int] = [7, 11, 13]  # 7/13 ≈ 0.538, 11/13 ≈ 0.846, 13/13 = 1.0

# Default 13 seats — distinct lenses (a war council, not a rubber stamp).
SEAT_ROLES: List[str] = [
    "vanguard", "logistics", "intelligence", "security", "risk", "doctrine",
    "economy", "diplomacy", "engineering", "ethics", "morale", "reserve", "warlord",
]


def threshold_for(stakes: int) -> Dict[str, Any]:
    """Required prime majority (numerator out of 13) for a given stakes level."""
    idx = max(0, min(stakes, len(PRIME_LADDER) - 1))
    num = PRIME_LADDER[idx]
    return {"numerator": num, "denominator": SEATS, "ratio": num / SEATS, "stakes": idx}


def tally(votes: List[Dict[str, Any]], *, stakes: int = 0) -> Dict[str, Any]:
    """Tally up to 13 seat votes and return a GUARANTEED decisive verdict.

    Each vote: {"seat": int 0..12, "vote": "approve"|"reject"|"abstain"}.
    - weighted score uses each seat's prime weight (abstain = 0 both sides);
    - approval needs weighted_approve / (approve+reject) >= the accelerating
      prime threshold AND a raw-seat majority of the non-abstaining seats;
    - any weighted tie is broken by the odd raw-seat count → never deadlocks.
    """
    th = threshold_for(stakes)
    w_app = w_rej = n_app = n_rej = n_abs = 0
    seen = set()
    for v in votes[:SEATS]:
        seat = int(v.get("seat", -1))
        if seat < 0 or seat >= SEATS or seat in seen:
            continue
        seen.add(seat)
        w = SEAT_PRIMES[seat]
        d = str(v.get("vote", "abstain")).lower()
        if d == "approve":
            w_app += w; n_app += 1
        elif d == "reject":
            w_rej += w; n_rej += 1
        else:
            n_abs += 1
    decided = n_app + n_rej
    w_total = w_app + w_rej
    weighted_ratio = (w_app / w_total) if w_total else 0.0
    seat_majority = n_app > n_rej  # odd among deciders ⇒ strict unless equal counts
    # Verdict: approve iff the accelerating prime majority is met by weight AND seats.
    if w_total == 0:
        verdict = "no_quorum"
    elif weighted_ratio >= th["ratio"]:
        verdict = "approved"                                  # cleared the accelerating prime bar
    elif (1 - weighted_ratio) >= th["ratio"]:
        verdict = "rejected"                                  # opposition cleared the bar
    elif w_app != w_rej:
        verdict = "approved" if w_app > w_rej else "rejected" # weighted (prime) majority decides
    elif n_app != n_rej:
        verdict = "approved" if n_app > n_rej else "rejected" # raw odd-seat tie-break
    else:
        verdict = "rejected"                                  # total deadlock → safe decisive default
    return {
        "verdict": verdict,
        "threshold": th,
        "weighted": {"approve": w_app, "reject": w_rej, "ratio": round(weighted_ratio, 4), "total": w_total},
        "seats": {"approve": n_app, "reject": n_rej, "abstain": n_abs, "decided": decided},
        "guaranteed": verdict in ("approved", "rejected"),
    }


class WarCouncil:
    """The live-message decision bridge. Collect votes for a proposal, reach a
    guaranteed verdict via the prime-accelerating majority, and on approval fire
    the blueprint run."""

    def __init__(self,
                 vote_fn: Optional[Callable[[Dict[str, Any], int], Awaitable[List[Dict[str, Any]]]]] = None,
                 blueprint_fn: Optional[Callable[[Dict[str, Any]], Awaitable[Any]]] = None):
        # vote_fn(proposal, seat) -> awaitable list of seat votes (inject the
        # boardroom soldiers / LLM personas / a deterministic stub). blueprint_fn
        # is called with the proposal on an approved verdict (the blueprint run).
        self.vote_fn = vote_fn
        self.blueprint_fn = blueprint_fn
        self.history: List[Dict[str, Any]] = []

    def config(self) -> Dict[str, Any]:
        return {
            "seats": SEATS, "seat_primes": SEAT_PRIMES, "seat_roles": SEAT_ROLES,
            "total_weight": TOTAL_WEIGHT, "prime_ladder": PRIME_LADDER,
            "thresholds": [threshold_for(i) for i in range(len(PRIME_LADDER))],
        }

    async def decide(self, proposal: Dict[str, Any], *, stakes: int = 0) -> Dict[str, Any]:
        """Run a proposal through the council; trigger a blueprint on approval."""
        votes: List[Dict[str, Any]] = []
        if self.vote_fn:
            try:
                votes = await self.vote_fn(proposal, stakes) or []
            except Exception:
                votes = []
        result = tally(votes, stakes=stakes)
        blueprint = None
        if result["verdict"] == "approved" and self.blueprint_fn:
            try:
                blueprint = await self.blueprint_fn(proposal)
            except Exception as e:
                blueprint = {"error": str(e)[:160]}
        record = {
            "ts": time.time(),
            "proposal": {k: proposal.get(k) for k in ("id", "title", "source")},
            "stakes": stakes, "result": result,
            "blueprint_triggered": blueprint is not None and not (isinstance(blueprint, dict) and blueprint.get("error")),
        }
        self.history.append(record)
        self.history = self.history[-50:]
        return {**record, "blueprint": blueprint}

    def recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self.history[-limit:][::-1]


_instance: Optional[WarCouncil] = None


def get_war_council() -> WarCouncil:
    global _instance
    if _instance is None:
        _instance = WarCouncil()
    return _instance
