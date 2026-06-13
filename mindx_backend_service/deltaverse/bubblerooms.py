"""Bubblerooms — role-gated rooms of the REALM.

The NeuralNode BubbleRoom presets (BOARDROOM / DOJO / TREASURY / ARENA /
SANCTUM) mapped onto mindX's existing surfaces and the service-isolation tiers.
Each room declares the minimum cypherpunk2048 role required to *enter*; the
fabric renders every room but only opens the ones a participant's privilege
allows. Public participants observe; privilege (earned or paid) opens doors.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .config import can_grant

# preset → tone is narrative flavor the weaver uses for story beats.
BUBBLEROOMS: List[Dict[str, Any]] = [
    {
        "id": "agora", "name": "The Agora", "preset": "ARENA",
        "min_role": "public", "route": "/", "tone": "open",
        "blurb": "The public square. The fabric is visible to all who arrive.",
    },
    {
        "id": "journal", "name": "Improvement Journal", "preset": "DOJO",
        "min_role": "model", "route": "/journal", "tone": "reflective",
        "blurb": "mindX's autonomous decisions, on a 30-minute cadence.",
    },
    {
        "id": "dojo", "name": "The Dojo", "preset": "DOJO",
        "min_role": "agent", "route": "/dojo/standings", "tone": "competitive",
        "blurb": "Agent reputation. Privilege here is earned, not assigned.",
    },
    {
        "id": "boardroom", "name": "The Boardroom", "preset": "BOARDROOM",
        "min_role": "overseer", "route": "/boardroom", "tone": "deliberative",
        "blurb": "Governance sessions. Overseers distribute privilege and moderate.",
    },
    {
        "id": "treasury", "name": "The Treasury", "preset": "TREASURY",
        "min_role": "overseer", "route": "/vault/credentials/status", "tone": "guarded",
        "blurb": "The BANKON vault surface. Cabinet-tier and above.",
    },
    {
        "id": "sanctum", "name": "The Sanctum", "preset": "SANCTUM",
        "min_role": "overlord", "route": "/realm", "tone": "sovereign",
        "blurb": "The REALM control surface. The overlord alone holds the keys.",
    },
]


def rooms_for(role: str) -> List[Dict[str, Any]]:
    """Return every room, annotated with whether `role` may enter. The fabric
    shows locked rooms too — a lost door is an invitation, not a wall."""
    out: List[Dict[str, Any]] = []
    for r in BUBBLEROOMS:
        room = dict(r)
        room["open"] = can_grant(role, r["min_role"])
        out.append(room)
    return out
