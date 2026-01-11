from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional, Set

@dataclass
class MindTermEvent:
    type: str
    ts: str
    session_id: str
    payload: Dict[str, Any]

class EventBus:
    """
    In-memory pubsub for mindterm session events.
    - Web UI uses /ws to control PTY
    - Agents can subscribe to /events websocket to receive structured events
    """
    def __init__(self) -> None:
        self._subs: Dict[str, Set[asyncio.Queue[MindTermEvent]]] = {}

    def subscribe(self, session_id: str) -> asyncio.Queue[MindTermEvent]:
        q: asyncio.Queue[MindTermEvent] = asyncio.Queue(maxsize=2000)
        self._subs.setdefault(session_id, set()).add(q)
        return q

    def unsubscribe(self, session_id: str, q: asyncio.Queue[MindTermEvent]) -> None:
        s = self._subs.get(session_id)
        if not s:
            return
        s.discard(q)
        if not s:
            self._subs.pop(session_id, None)

    def emit(self, session_id: str, etype: str, payload: Dict[str, Any]) -> None:
        evt = MindTermEvent(
            type=etype,
            ts=datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
            session_id=session_id,
            payload=payload,
        )
        for q in list(self._subs.get(session_id, set())):
            try:
                q.put_nowait(evt)
            except asyncio.QueueFull:
                # Drop if subscriber is too slow
                pass

BUS = EventBus()

