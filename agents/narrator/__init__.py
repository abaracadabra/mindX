"""NarratorAgent — mindX's narrative voice.

Emits short recap messages summarizing recent catalogue activity, or accepts
operator-pinned recaps from /admin/narrator/recap. Mirrors to both the
catalogue (kind=narrative.recap) and a dedicated data/logs/recaps.jsonl.

Surfaced on /netstat #sec-narrative and via DeltaVerse dv.pulseNarrative.
"""

from .narrator import NarratorAgent, get_narrator

__all__ = ["NarratorAgent", "get_narrator"]
