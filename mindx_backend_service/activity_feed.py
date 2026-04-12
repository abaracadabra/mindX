"""
ActivityFeed — Real-time event bus for mindX agent activity.

In-memory ring buffer (200 events) with SSE broadcast to connected browsers.
Every agent action, boardroom vote, thinking step, dojo change, and inference
selection becomes a timeline event visible on the landing page.

Rooms (SwarmFeed channels adapted to mindX architecture):
    boardroom  — CEO directives, 7-soldier votes, outcomes
    dojo       — Reputation changes, tier promotions
    inference  — Model selection, provider probes, tok/s metrics
    improvement — Autonomous cycle events
    thinking   — Step-by-step reasoning traces
    godel      — Self-improvement decisions with rationale
    memory     — STM→LTM consolidation, dreaming insights
    system     — Resource governor, health, service events

Usage:
    feed = ActivityFeed.get_instance()
    feed.emit("boardroom", "ceo_agent", "vote_complete",
              "Directive approved (0.714)", detail={...})

Author: Professor Codephreak
"""

import asyncio
import json
import time
import uuid
from collections import deque
from typing import Any, AsyncGenerator, Dict, List, Optional, Set

from utils.logging_config import get_logger

logger = get_logger(__name__)

ROOMS = ("boardroom", "dojo", "inference", "improvement", "thinking", "godel", "memory", "system")
TIER_LABELS = {0: "UN", 1: "PRV", 2: "VER", 3: "BF", 4: "SOV", 5: "GM", 6: "MST"}
TIER_COLORS = {0: "#f85149", 1: "#d29922", 2: "#58a6ff", 3: "#3fb950", 4: "#d2a8ff", 5: "#79c0ff", 6: "#e6edf3"}
MAX_EVENTS = 200


class ActivityEvent:
    """A single activity event."""
    __slots__ = ("id", "room", "agent", "agent_tier", "type", "content", "detail", "timestamp")

    def __init__(self, room: str, agent: str, type: str, content: str,
                 detail: Optional[Dict[str, Any]] = None, agent_tier: int = 0):
        self.id = str(uuid.uuid4())[:8]
        self.room = room
        self.agent = agent
        self.agent_tier = agent_tier
        self.type = type
        self.content = content
        self.detail = detail
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "room": self.room,
            "agent": self.agent,
            "agent_tier": self.agent_tier,
            "tier_label": TIER_LABELS.get(self.agent_tier, "UN"),
            "tier_color": TIER_COLORS.get(self.agent_tier, "#f85149"),
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp,
        }
        if self.detail:
            d["detail"] = self.detail
        return d

    def to_sse(self) -> str:
        return f"event: activity\ndata: {json.dumps(self.to_dict())}\n\n"


class ActivityFeed:
    """
    In-memory activity event bus with SSE broadcast.
    Singleton — get_instance() returns the shared feed.
    """
    _instance: Optional["ActivityFeed"] = None

    def __init__(self):
        self.events: deque = deque(maxlen=MAX_EVENTS)
        self.listeners: Set[asyncio.Queue] = set()
        self._emit_count = 0
        logger.info("[ActivityFeed] Initialized (ring buffer: %d events)", MAX_EVENTS)

    @classmethod
    def get_instance(cls) -> "ActivityFeed":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def emit(self, room: str, agent: str, type: str, content: str,
             detail: Optional[Dict[str, Any]] = None, agent_tier: int = 0):
        """Emit an activity event to the ring buffer and all SSE listeners."""
        if room not in ROOMS:
            room = "system"

        event = ActivityEvent(room, agent, type, content, detail, agent_tier)
        self.events.append(event)
        self._emit_count += 1

        # Broadcast to all SSE listeners (non-blocking)
        dead_queues = []
        for q in self.listeners:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(q)
        for q in dead_queues:
            self.listeners.discard(q)

    def recent(self, limit: int = 50, room: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return recent events, optionally filtered by room."""
        events = list(self.events)
        if room and room != "all":
            events = [e for e in events if e.room == room]
        events = events[-limit:]
        events.reverse()  # newest first
        return [e.to_dict() for e in events]

    async def sse_generator(self) -> AsyncGenerator[str, None]:
        """Async generator for SSE stream. Yields event strings."""
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        self.listeners.add(q)
        try:
            # Send recent events as initial burst
            for event in list(self.events)[-20:]:
                yield event.to_sse()

            # Stream new events
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30.0)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    # Heartbeat to keep connection alive
                    yield f"event: heartbeat\ndata: {json.dumps({'t': time.time()})}\n\n"
        finally:
            self.listeners.discard(q)

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_emitted": self._emit_count,
            "buffer_size": len(self.events),
            "buffer_max": MAX_EVENTS,
            "listeners": len(self.listeners),
            "rooms": {r: sum(1 for e in self.events if e.room == r) for r in ROOMS},
        }


# ── Bootstrap: seed feed from existing JSONL logs on first load ──

def _seed_from_logs(feed: ActivityFeed):
    """Seed the feed with recent events from JSONL log files."""
    from pathlib import Path
    from utils.config import PROJECT_ROOT

    # Boardroom sessions
    boardroom_log = PROJECT_ROOT / "data" / "governance" / "boardroom_sessions.jsonl"
    if boardroom_log.exists():
        try:
            lines = boardroom_log.read_text().strip().split("\n")
            for line in lines[-10:]:  # last 10 sessions
                data = json.loads(line)
                outcome = data.get("outcome", "?")
                score = data.get("weighted_score", 0)
                votes = data.get("votes", [])
                vote_summary = " ".join(
                    f'{v.get("soldier","?")[:3]}:{"✓" if v.get("vote")=="approve" else "✗" if v.get("vote")=="reject" else "—"}'
                    for v in votes
                )
                feed.emit(
                    "boardroom", "ceo_agent", "session",
                    f'{data.get("directive","")[:120]} → {outcome.upper()} ({score:.3f}) {vote_summary}',
                    detail=data, agent_tier=4
                )
        except Exception:
            pass

    # Godel choices
    godel_log = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
    if godel_log.exists():
        try:
            lines = godel_log.read_text().strip().split("\n")
            for line in lines[-10:]:
                data = json.loads(line)
                chosen = data.get("chosen_option", data.get("choice", "?"))
                rationale = data.get("rationale", "")[:150]
                feed.emit(
                    "godel", data.get("source_agent", "mindx"), "choice",
                    f'{chosen} — {rationale}',
                    detail=data, agent_tier=3
                )
        except Exception:
            pass

    # Heartbeat dialogues (recent interactions)
    dialogue_log = PROJECT_ROOT / "data" / "logs" / "heartbeat_dialogues.jsonl"
    if dialogue_log.exists():
        try:
            lines = dialogue_log.read_text().strip().split("\n")
            for line in lines[-10:]:
                data = json.loads(line)
                agent = data.get("agent_id", data.get("agent", "?"))
                model = data.get("model", "?")
                prompt = data.get("prompt", data.get("question", ""))[:100]
                response = data.get("response", data.get("answer", ""))[:100]
                feed.emit(
                    "inference", agent, "dialogue",
                    f'{model}: "{prompt}" → "{response}"',
                    detail=data, agent_tier=2
                )
        except Exception:
            pass

    logger.info("[ActivityFeed] Seeded with %d events from logs", len(feed.events))
