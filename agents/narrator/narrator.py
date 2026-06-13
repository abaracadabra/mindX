"""NarratorAgent — emits and reads recap events.

Two write paths feed the same store:
    - autonomous summary (run_autonomous_cycle) — deterministic template over
      recent catalogue events, MVP. Phase 2: route through self.aware selector.
    - operator pin (emit_recap from /admin/narrator/recap handler) — Claude
      session or human pastes a recap; wallet-signed.

One store with two mirrors:
    - data/logs/recaps.jsonl (append-only, line-delimited JSON, easy tail/grep)
    - catalogue events.jsonl (via emit_catalogue_event, kind=narrative.recap)

Read path: tail data/logs/recaps.jsonl. The catalogue is the source-of-truth
but the dedicated jsonl is the fast read substrate.

Concurrency: the singleton (`get_narrator()`) holds a single asyncio.Lock for
writes so concurrent emit calls don't interleave.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.catalogue.events import emit_catalogue_event

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RECAPS_PATH = PROJECT_ROOT / "data" / "logs" / "recaps.jsonl"
CATALOGUE_PATH = PROJECT_ROOT / "data" / "logs" / "catalogue_events.jsonl"
MAX_TAIL_BYTES = 4 * 1024 * 1024  # cap tail-read at 4 MB

# Display caps
MAX_BODY_LEN = 4000


class NarratorAgent:
    """The narrative voice of mindX.

    Lifecycle: singleton via `get_narrator()`. Methods are async; the lock is
    per-instance so concurrent emits serialize their writes to the jsonl.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._recent_count = 0  # session-scoped emission counter
        RECAPS_PATH.parent.mkdir(parents=True, exist_ok=True)

    # ─── Write ─────────────────────────────────────────────────────────

    async def emit_recap(
        self,
        body: str,
        author: str = "narrator",
        source: str = "narrator",
        span_seconds: int = 3600,
        related_event_count: int = 0,
    ) -> Dict[str, Any]:
        """Append one recap to the jsonl + catalogue + (best-effort) ActivityFeed.

        Returns the record (with `recap_id` + `ts`) so the caller can echo it.
        """
        body = (body or "").strip()
        if not body:
            raise ValueError("recap body is empty")
        if len(body) > MAX_BODY_LEN:
            body = body[:MAX_BODY_LEN] + "…[truncated]"

        record = {
            "recap_id": uuid.uuid4().hex[:16],
            "ts": time.time(),
            "author": author,
            "source": source,  # "narrator" | "operator"
            "body": body,
            "span_seconds": int(span_seconds or 0),
            "related_event_count": int(related_event_count or 0),
        }

        async with self._lock:
            with open(RECAPS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, separators=(",", ":")) + "\n")
            self._recent_count += 1

        # Catalogue mirror (best-effort — never block recap emission on catalogue failure)
        try:
            await emit_catalogue_event(
                kind="narrative.recap",
                actor=author,
                source_log="data/logs/recaps.jsonl",
                source_ref=record["recap_id"],
                payload=record,
            )
        except Exception:
            pass

        # ActivityFeed push (best-effort — feeds the SSE stream that pulses dv.narrative)
        try:
            from mindx_backend_service.activity_feed import ActivityFeed
            feed = ActivityFeed.get_instance()
            feed.emit(
                room="narrative",
                agent=author,
                event_type=f"recap.{source}",
                content=body[:240],
                detail=record,
            )
        except Exception:
            pass

        return record

    # ─── Read ──────────────────────────────────────────────────────────

    def read_recent(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Tail the jsonl, return last N records (newest first). Cheap byte-tail."""
        if not RECAPS_PATH.exists():
            return []
        try:
            size = RECAPS_PATH.stat().st_size
            with open(RECAPS_PATH, "rb") as f:
                if size > MAX_TAIL_BYTES:
                    f.seek(size - MAX_TAIL_BYTES)
                    f.readline()  # discard partial first line
                tail = f.read().decode("utf-8", errors="replace")
        except OSError:
            return []
        out: List[Dict[str, Any]] = []
        for line in reversed([ln for ln in tail.splitlines() if ln.strip()]):
            try:
                out.append(json.loads(line))
            except Exception:
                continue
            if len(out) >= max(1, min(limit, 200)):
                break
        return out

    # ─── Autonomous summarization ──────────────────────────────────────

    async def summarize_recent(self, hours: float = 1.0) -> str:
        """Deterministic template summary over the last `hours` of catalogue events.

        MVP: kind+actor counts. Phase 2 plug an LLM through self.aware selector.
        """
        cutoff = time.time() - max(0.1, hours) * 3600.0
        kind_counts: Counter[str] = Counter()
        actor_counts: Counter[str] = Counter()
        total = 0

        if CATALOGUE_PATH.exists():
            try:
                size = CATALOGUE_PATH.stat().st_size
                with open(CATALOGUE_PATH, "rb") as f:
                    # Tail-scan up to ~8 MB; sufficient for ≥1 hour window on this VPS
                    tail_window = min(size, 8 * 1024 * 1024)
                    f.seek(size - tail_window)
                    f.readline()
                    tail = f.read().decode("utf-8", errors="replace")
                for line in tail.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except Exception:
                        continue
                    if evt.get("ts", 0) < cutoff:
                        continue
                    kind_counts[str(evt.get("kind", "?"))] += 1
                    actor_counts[str(evt.get("actor", "?"))] += 1
                    total += 1
            except OSError:
                pass

        if total == 0:
            return f"In the last {hours:g}h: no catalogue events. The substrate is quiet."

        top_kinds = ", ".join(f"{n} {k}" for k, n in kind_counts.most_common(5))
        top_actors = ", ".join(f"{a}({n})" for a, n in actor_counts.most_common(4))
        plural = "s" if total != 1 else ""
        return (
            f"In the last {hours:g}h: {total} event{plural} across "
            f"{len(kind_counts)} kinds and {len(actor_counts)} actors. "
            f"Top kinds: {top_kinds}. Most-active: {top_actors}."
        )

    async def run_autonomous_cycle(self, hours: float = 1.0) -> Dict[str, Any]:
        """Compute a recap and emit it as source=narrator. Returns the record."""
        body = await self.summarize_recent(hours=hours)
        return await self.emit_recap(
            body=body,
            author="agent.narrator",
            source="narrator",
            span_seconds=int(hours * 3600),
            related_event_count=0,  # the summary string already names the counts
        )


# ─── Singleton ─────────────────────────────────────────────────────────

_INSTANCE: Optional[NarratorAgent] = None


def get_narrator() -> NarratorAgent:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = NarratorAgent()
    return _INSTANCE
