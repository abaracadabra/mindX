# SPDX-License-Identifier: Apache-2.0
"""
mindx.catalogue.projector — Phase 1 entries projector.

Folds raw ``CatalogueEvent`` records from ``data/logs/catalogue_events.jsonl``
into the ``catalogue_entries`` read-model (Postgres + pgvector + tsvector). The
projection is:

  * **idempotent** — the URN is the upsert key; re-projecting a record is a
    no-op merge, so crashes / replays / rotation never duplicate rows;
  * **watermark-resumable** — a byte offset into the active log is checkpointed
    in ``catalogue_state``, so the live loop only pays for new bytes;
  * **embedding-decoupled** — rows are written first with ``embedding=NULL``;
    a text-bearing draft is embedded through ``generate_embedding(interactive=
    False)`` so the ResourceGovernor defers it under CPU load. Search degrades
    to FTS-only until embeddings land.

This is the read side of CQRS: the log stays the source of truth; drop the
read-model tables and replay to rebuild. See docs/KNOWLEDGE_CATALOGUE.md.
"""
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, List, Optional, Set

from utils.logging_config import get_logger

from agents import memory_pgvector as pg
from .model import derive_entry

logger = get_logger(__name__)

_CHECKPOINT_EVERY = 200


def _active_log_path() -> Path:
    try:
        from utils.config import PROJECT_ROOT
        base = Path(PROJECT_ROOT) / "data" / "logs"
    except Exception:
        base = Path(__file__).resolve().parents[2] / "data" / "logs"
    return base / "catalogue_events.jsonl"


@dataclass
class ProjectorRun:
    projector: str = "entries"
    started_at: float = 0.0
    finished_at: float = 0.0
    events_seen: int = 0
    entries_upserted: int = 0
    embeds_done: int = 0
    embeds_deferred: int = 0
    bad_lines: int = 0
    errors: int = 0
    final_offset: int = 0
    observed_kinds: Set[str] = field(default_factory=set)

    def as_dict(self) -> dict:
        return {
            "projector": self.projector, "events_seen": self.events_seen,
            "entries_upserted": self.entries_upserted, "embeds_done": self.embeds_done,
            "embeds_deferred": self.embeds_deferred, "bad_lines": self.bad_lines,
            "errors": self.errors, "final_offset": self.final_offset,
        }


class CatalogueProjector:
    """Folds CatalogueEvents → catalogue_entries. One instance per projector name."""

    def __init__(self, name: str = "entries", version: str = "v1"):
        self.name = name
        self.version = version

    # ── public entry points ─────────────────────────────────────────────
    async def run(self, max_events: Optional[int] = None, embed: bool = True) -> ProjectorRun:
        """Incremental projection of the ACTIVE log from the stored watermark.
        Used by the live loop. Advances + checkpoints the watermark."""
        await pg.init_catalogue_schema()
        got_lock = await pg.try_catalogue_lock()
        if not got_lock:
            logger.debug("catalogue projector: lock held elsewhere, skipping tick")
            return ProjectorRun(projector=self.name)
        try:
            return await self._project_active(max_events=max_events, embed=embed)
        finally:
            await pg.release_catalogue_lock()

    async def project_file(
        self, path: Path, *, embed: bool = False, max_events: Optional[int] = None,
        start_offset: int = 0, dry_run: bool = False,
        progress: Optional[Callable[[ProjectorRun], None]] = None,
    ) -> ProjectorRun:
        """Project a single file fully (used by the backfill for rotated archives).
        Does NOT touch the watermark — archives are one-shot. ``dry_run`` derives
        + counts but performs no DB writes."""
        run = ProjectorRun(projector=self.name)
        run.started_at = _now()
        await self._fold_file(path, run, embed=embed, max_events=max_events,
                              start_offset=start_offset, dry_run=dry_run, progress=progress)
        run.finished_at = _now()
        return run

    # ── internals ───────────────────────────────────────────────────────
    async def _project_active(self, *, max_events: Optional[int], embed: bool) -> ProjectorRun:
        path = _active_log_path()
        run = ProjectorRun(projector=self.name)
        run.started_at = _now()
        wm = await pg.get_catalogue_watermark(self.name)
        start = int(wm.get("byte_offset") or 0)
        # Version bump => full replay (upserts are idempotent; don't truncate).
        if wm.get("version") and wm.get("version") != self.version:
            logger.info("catalogue projector: version %s→%s, full replay",
                        wm.get("version"), self.version)
            start = 0
        # Rotation: active file shrank below our offset => a rotation happened;
        # restart at 0 for the new active file (URN idempotency skips dup rows).
        try:
            if path.exists() and path.stat().st_size < start:
                logger.info("catalogue projector: log rotated (size<offset), resetting offset")
                start = 0
        except OSError:
            pass

        await self._fold_file(path, run, embed=embed, max_events=max_events, start_offset=start,
                              checkpoint=True, seen0=int(wm.get("events_seen") or 0),
                              written0=int(wm.get("entries_written") or 0))
        run.finished_at = _now()
        return run

    async def _fold_file(self, path: Path, run: ProjectorRun, *, embed: bool,
                         max_events: Optional[int], start_offset: int,
                         checkpoint: bool = False, seen0: int = 0, written0: int = 0,
                         dry_run: bool = False,
                         progress: Optional[Callable[[ProjectorRun], None]] = None) -> None:
        if not path.exists():
            run.final_offset = start_offset
            return
        offset = start_offset
        batch = 0
        try:
            with path.open("rb") as fh:
                fh.seek(start_offset)
                for raw in fh:
                    offset += len(raw)
                    line = raw.strip()
                    if not line:
                        continue
                    try:
                        evt = json.loads(line)
                    except Exception:
                        run.bad_lines += 1
                        continue
                    run.events_seen += 1
                    try:
                        await self._apply(evt, embed=embed, run=run, dry_run=dry_run)
                    except Exception as e:
                        run.errors += 1
                        logger.debug(f"catalogue projector apply error: {e}")
                    batch += 1
                    run.final_offset = offset
                    if checkpoint and batch >= _CHECKPOINT_EVERY:
                        await pg.set_catalogue_watermark(
                            self.name, self.version, offset, str(evt.get("event_id") or ""),
                            seen0 + run.events_seen, written0 + run.entries_upserted,
                            observed_kinds=sorted(run.observed_kinds))
                        batch = 0
                        if progress:
                            progress(run)
                        await asyncio.sleep(0)  # yield to the web loop
                    if max_events and run.events_seen >= max_events:
                        break
        finally:
            run.final_offset = offset
            if checkpoint:
                await pg.set_catalogue_watermark(
                    self.name, self.version, offset, run_last_id(run),
                    seen0 + run.events_seen, written0 + run.entries_upserted,
                    observed_kinds=sorted(run.observed_kinds))

    async def _apply(self, evt: dict, *, embed: bool, run: ProjectorRun,
                     dry_run: bool = False) -> None:
        draft = derive_entry(evt)
        run._last_event_id = str(evt.get("event_id") or "")  # type: ignore[attr-defined]
        ek = evt.get("kind")
        if ek:
            run.observed_kinds.add(ek)
        if dry_run:
            run.entries_upserted += 1  # would-upsert count
            return
        embedding = None
        if embed and draft.is_text_bearing:
            # interactive=False => background path, deferred under CPU pressure.
            embedding = await pg.generate_embedding(draft.text, interactive=False)
            if embedding:
                run.embeds_done += 1
            else:
                run.embeds_deferred += 1
        ok = await pg.upsert_catalogue_entry(
            urn=draft.urn, kind=draft.kind, actor=draft.actor, actor_wallet=draft.actor_wallet,
            ts=draft.ts, title=draft.title, text=draft.text, payload=draft.payload,
            tags=draft.tags, links=[l.model_dump() for l in draft.links],
            source_event_id=draft.source_event_id, embedding=embedding)
        if ok:
            run.entries_upserted += 1

    async def embed_sweep(self, limit: int = 200) -> int:
        """Backfill embeddings for entries still missing one (deferred-embed path).
        Called by the live loop / backfill --embed-only."""
        pending = await pg.catalogue_unembedded(limit)
        done = 0
        for row in pending:
            emb = await pg.generate_embedding(row["text"], interactive=False)
            if emb and await pg.embed_catalogue_entry(row["urn"], emb):
                done += 1
            await asyncio.sleep(0)
        return done


def run_last_id(run: ProjectorRun) -> Optional[str]:
    return getattr(run, "_last_event_id", None)


def _now() -> float:
    import time
    return time.time()


__all__ = ["CatalogueProjector", "ProjectorRun"]
