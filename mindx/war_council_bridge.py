# mindx/war_council_bridge.py
"""Wire the War Council to the live Boardroom soldiers (vote_fn) and to the
BlueprintAgent (blueprint_fn).

vote_fn convenes the **in-process** Boardroom (daio.governance.boardroom.Boardroom)
— which queries the 7 soldiers via local inference (Ollama) and needs no separate
service unless MINDX_BOARDROOM_SERVICE_ENABLED=1. Each soldier maps onto its
War-Council seat by domain; the 13-seat prime-accelerating majority then renders a
guaranteed verdict. On approval, blueprint_fn fires a blueprint run via the running
MindXAgent's BlueprintAgent — closing the live-message → decision → blueprint loop.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from mindx.war_council import get_war_council, SEAT_ROLES

# Boardroom soldier id → War-Council seat index (by domain).
#   0 vanguard 1 logistics 2 intelligence 3 security 4 risk 5 doctrine
#   6 economy 7 diplomacy 8 engineering 9 ethics 10 morale 11 reserve 12 warlord
_SEAT_OF: Dict[str, int] = {
    "coo_operations": 1, "cfo_finance": 6, "cto_technology": 8, "ciso_security": 3,
    "clo_legal": 9, "cpo_product": 7, "cro_risk": 4, "ceo": 12,
}
_IMPORTANCE = {0: "standard", 1: "elevated", 2: "executive"}


def _get(o: Any, *names: str) -> Any:
    for n in names:
        if isinstance(o, dict) and o.get(n) is not None:
            return o.get(n)
        v = getattr(o, n, None)
        if v is not None:
            return v
    return None


def _norm_vote(v: Any) -> str:
    s = str(v or "abstain").lower()
    if s in ("approve", "accept", "yes", "aye", "for"):
        return "approve"
    if s in ("reject", "no", "nay", "against", "veto"):
        return "reject"
    return "abstain"


async def boardroom_vote_fn(proposal: Dict[str, Any], stakes: int = 0) -> List[Dict[str, Any]]:
    """Convene the in-process Boardroom on the proposal; map soldier votes → seats."""
    from daio.governance.boardroom import Boardroom
    directive = (proposal.get("title") or proposal.get("text")
                 or str(proposal.get("id") or "proposal"))
    importance = _IMPORTANCE.get(int(stakes), "standard")
    bench = await Boardroom.get_instance()
    session = await bench.convene(
        directive, importance=importance,
        context={"war_council": True, "source": proposal.get("source"),
                 "detail": proposal.get("context")})
    raw = _get(session, "votes") or []
    seats: List[Dict[str, Any]] = []
    used = set()
    for v in raw:
        sid = str(_get(v, "soldier_id", "soldier", "seat") or "").lower()
        seat = _SEAT_OF.get(sid)
        if seat is None or seat in used:
            continue
        used.add(seat)
        seats.append({
            "seat": seat, "role": SEAT_ROLES[seat], "soldier": sid,
            "vote": _norm_vote(_get(v, "vote", "value", "decision")),
            "confidence": _get(v, "confidence"),
        })
    return seats


async def blueprint_fn(proposal: Dict[str, Any]) -> Any:
    """Fire a blueprint run via the running MindXAgent's BlueprintAgent."""
    from agents.core.mindXagent import MindXAgent
    agent = await MindXAgent.get_instance()
    bp_agent = getattr(agent, "blueprint_agent", None)
    if bp_agent is None:
        return {"error": "blueprint_agent not initialized on MindXAgent"}
    bp = await bp_agent.generate_next_evolution_blueprint(
        context_override={"trigger": "war_council", "proposal": proposal})
    # keep the recorded result small/serializable
    if isinstance(bp, dict):
        return {k: bp.get(k) for k in ("blueprint_id", "id", "title", "status", "goal") if k in bp} or {"generated": True}
    return {"generated": bp is not None}


def wire() -> Any:
    """Install boardroom_vote_fn + blueprint_fn on the War Council. Idempotent."""
    wc = get_war_council()
    wc.vote_fn = boardroom_vote_fn
    wc.blueprint_fn = blueprint_fn
    return wc
