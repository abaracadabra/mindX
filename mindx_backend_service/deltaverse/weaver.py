"""The Cypherian Weaver — automation that weaves participant interaction into the
changing story (the NeuralNode WEAVER seed; the Aetheric Codex idea, minimal).

Every participant interaction is a thread. The Weaver appends a *story beat* and
accrues the six on-chain-style *emergence traits* (Intelligence, Knowledge,
Wisdom, Resonance, Adaptability, Coherence) — the measurable shape of the
changing story. State is a rebuildable projection: an append-only JSONL log plus
an in-memory ring. Never the source of truth; replay the log to rebuild.
"""
from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover - defensive import
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

_STORY_LOG = PROJECT_ROOT / "data" / "governance" / "deltaverse_story.jsonl"
_RING_MAX = 200

# The six emergence traits, 0-100 (Wisdom bands NASCENT→ORACLE are derived).
_TRAITS = ("intelligence", "knowledge", "wisdom", "resonance", "adaptability", "coherence")
_WISDOM_BANDS = ("NASCENT", "AWARE", "LUCID", "SAGE", "ORACLE")


class CypherianWeaver:
    """Weaves interactions into beats + traits. Process-local singleton."""

    _instance: Optional["CypherianWeaver"] = None
    _lock = Lock()

    def __init__(self) -> None:
        self._beats: Deque[Dict[str, Any]] = deque(maxlen=_RING_MAX)
        self._traits: Dict[str, float] = {t: 0.0 for t in _TRAITS}
        self._interactions = 0
        self._wlock = Lock()
        self._load()

    @classmethod
    def instance(cls) -> "CypherianWeaver":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ── trait accrual ──
    # Interaction count lifts Intelligence/Adaptability; named roles and lineage
    # depth lift Knowledge/Wisdom; rhythm lifts Resonance/Coherence. Saturating.
    def _accrue(self, role: str, kind: str) -> None:
        self._interactions += 1
        def bump(t: str, by: float) -> None:
            self._traits[t] = min(100.0, self._traits[t] + by)
        bump("intelligence", 0.6)
        bump("adaptability", 0.4)
        if role in ("agent", "overseer", "overlord"):
            bump("knowledge", 0.8)
            bump("wisdom", 0.5)
        if kind in ("weave", "story", "interact"):
            bump("resonance", 0.5)
            bump("coherence", 0.3)

    def _wisdom_band(self) -> str:
        idx = min(len(_WISDOM_BANDS) - 1, int(self._traits["wisdom"] // 20))
        return _WISDOM_BANDS[idx]

    def weave(self, kind: str, who: str, role: str, text: str, **meta: Any) -> Dict[str, Any]:
        """Append a story beat and accrue traits. Defensive — never raises."""
        beat = {
            "ts": time.time(),
            "kind": kind or "interact",
            "who": who or "anon",
            "role": (role or "public").lower(),
            "text": (text or "")[:280],
            "meta": meta or {},
        }
        with self._wlock:
            self._accrue(beat["role"], beat["kind"])
            self._beats.append(beat)
            try:
                _STORY_LOG.parent.mkdir(parents=True, exist_ok=True)
                with _STORY_LOG.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(beat) + "\n")
            except Exception:
                pass
        return beat

    def recent(self, n: int = 30) -> List[Dict[str, Any]]:
        n = max(1, min(n, _RING_MAX))
        return list(self._beats)[-n:]

    def traits(self) -> Dict[str, Any]:
        t = {k: round(v, 2) for k, v in self._traits.items()}
        t["wisdom_band"] = self._wisdom_band()
        t["interactions"] = self._interactions
        return t

    # ── projection rebuild (the log is the source of truth) ──
    def _load(self) -> None:
        try:
            if not _STORY_LOG.exists():
                return
            lines = _STORY_LOG.read_text(encoding="utf-8").splitlines()
            for ln in lines[-_RING_MAX:]:
                try:
                    beat = json.loads(ln)
                    self._beats.append(beat)
                    self._accrue(beat.get("role", "public"), beat.get("kind", "interact"))
                except Exception:
                    continue
        except Exception:
            pass
