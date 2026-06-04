#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""catalogue_backfill.py — backfill the Knowledge Catalogue read-model.

Replays ``data/logs/catalogue_events.jsonl`` (and, with ``--include-archives``,
the rotated ``catalogue_events.*.jsonl`` files) from offset 0, folding every
event into the ``catalogue_entries`` read-model via ``CatalogueProjector``.

Idempotent: re-running is a no-op upsert (URN is the key), so this is safe to
run repeatedly. After processing the ACTIVE file it advances the live
projector's watermark to end-of-file, so the in-process loop resumes from there
rather than re-projecting everything.

The CPU risk is embeddings: ~85% of events are ``memory.write`` and each embed
is ~0.3-1s on the VPS's CPU Ollama. So the default is **structure-first**:

    # Preview (dry-run, no DB writes):
    python scripts/catalogue_backfill.py --max 50

    # Full STRUCTURAL backfill (rows only, no embeddings — seconds):
    python scripts/catalogue_backfill.py --include-archives --no-embed --apply

    # Embed sweep afterwards (or just let the live loop do it incrementally):
    python scripts/catalogue_backfill.py --embed-only --apply

Embeddings for text-bearing entries left NULL by ``--no-embed`` are filled
incrementally by the in-process ``_periodic_catalogue_projector`` loop under the
ResourceGovernor gate. Search degrades to FTS-only until they land.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path
from typing import List, Optional

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

LOG_DIR = HERE / "data" / "logs"
ACTIVE = LOG_DIR / "catalogue_events.jsonl"


def _log_files(include_archives: bool) -> List[Path]:
    """Active file last (so its watermark is advanced after archives). Archives
    sorted oldest-first by name (rotation stamp is YYYYMMDD-HHMMSS)."""
    if not include_archives:
        return [ACTIVE] if ACTIVE.exists() else []
    archives = sorted(p for p in LOG_DIR.glob("catalogue_events.*.jsonl"))
    files = archives + ([ACTIVE] if ACTIVE.exists() else [])
    return files


async def _pg_reachable() -> bool:
    try:
        from agents import memory_pgvector as pg
        return bool(await pg.get_pool())
    except Exception:
        return False


async def run(max_events: int, apply: bool, embed: bool, include_archives: bool,
              embed_only: bool, observe_only: bool = False) -> int:
    if not await _pg_reachable():
        print("FATAL: Postgres/pgvector not reachable (DB_DSN). Is the DB up?",
              file=sys.stderr)
        return 2

    from agents import memory_pgvector as pg
    from agents.catalogue.projector import CatalogueProjector

    await pg.init_catalogue_schema()
    proj = CatalogueProjector(name="entries", version="v1")

    # ── observe-only: collect distinct EventKinds, merge into watermark ──
    # Cheap (no upserts, no embeds): folds the stream in dry-run to gather the
    # kinds actually present, then UNIONs them into catalogue_state.observed_kinds
    # WITHOUT disturbing the resume offset. Seeds the /insight/catalogue/kinds
    # "emitted" marker for already-backfilled data.
    if observe_only:
        files = _log_files(include_archives=True)
        kinds: set = set()
        for f in files:
            r = await proj.project_file(f, embed=False, dry_run=True)
            kinds |= r.observed_kinds
            print(f"  {f.name}: {len(r.observed_kinds)} kinds")
        print(f"observed {len(kinds)} distinct EventKinds: {sorted(kinds)}")
        if apply:
            wm = await pg.get_catalogue_watermark("entries")
            await pg.set_catalogue_watermark(
                "entries", wm.get("version") or "v1", int(wm.get("byte_offset") or 0),
                wm.get("last_event_id"), int(wm.get("events_seen") or 0),
                int(wm.get("entries_written") or 0), observed_kinds=sorted(kinds))
            print("merged into catalogue_state.observed_kinds (offset preserved).")
        else:
            print("(dry-run — pass --apply to persist)")
        return 0

    # ── embed-only sweep ────────────────────────────────────────────────
    if embed_only:
        if not apply:
            n = len(await pg.catalogue_unembedded(100000))
            print(f"(dry-run) {n} entries are missing embeddings; pass --apply to fill.")
            return 0
        total = 0
        while True:
            done = await proj.embed_sweep(limit=200)
            total += done
            print(f"  embedded +{done} (total {total})")
            if done == 0:
                break
        print(f"embed sweep complete: {total} entries embedded.")
        return 0

    files = _log_files(include_archives)
    if not files:
        print(f"no catalogue log files under {LOG_DIR}")
        return 1
    print(f"files: {[f.name for f in files]}  apply={apply}  embed={embed}  "
          f"max={max_events or 'unlimited'}")

    started = time.time()
    last = started
    grand_seen = grand_up = grand_emb = grand_bad = 0
    grand_kinds: set = set()
    remaining = max_events if max_events > 0 else None

    got_lock = await pg.try_catalogue_lock() if apply else True
    if apply and not got_lock:
        print("WARNING: catalogue advisory lock held (live loop running?). Aborting "
              "to avoid a watermark race — stop the backend or retry.", file=sys.stderr)
        return 3
    try:
        for f in files:
            is_active = (f == ACTIVE)

            def _progress(r, _f=f):
                nonlocal last
                now = time.time()
                if now - last > 5:
                    el = now - started
                    rate = (grand_seen + r.events_seen) / el if el else 0
                    print(f"  [{_f.name}] seen={r.events_seen} up={r.entries_upserted} "
                          f"emb={r.embeds_done} defer={r.embeds_deferred} {rate:.0f}/s")
                    last = now

            run_obj = await proj.project_file(
                f, embed=embed, max_events=remaining, dry_run=not apply,
                progress=_progress)
            grand_seen += run_obj.events_seen
            grand_up += run_obj.entries_upserted
            grand_emb += run_obj.embeds_done
            grand_bad += run_obj.bad_lines
            grand_kinds |= run_obj.observed_kinds
            print(f"  done {f.name}: seen={run_obj.events_seen} "
                  f"{'would-upsert' if not apply else 'upserted'}={run_obj.entries_upserted} "
                  f"emb={run_obj.embeds_done} deferred={run_obj.embeds_deferred} "
                  f"bad={run_obj.bad_lines} offset={run_obj.final_offset}")

            # After the ACTIVE file, advance the live-loop watermark to EOF so the
            # in-process projector resumes from there (only when applying).
            if is_active and apply:
                from agents.catalogue.projector import run_last_id
                await pg.set_catalogue_watermark(
                    "entries", "v1", run_obj.final_offset, run_last_id(run_obj),
                    grand_seen, grand_up, observed_kinds=sorted(grand_kinds))
                print(f"  watermark advanced to offset={run_obj.final_offset} "
                      f"({len(grand_kinds)} kinds observed)")

            if remaining is not None:
                remaining -= run_obj.events_seen
                if remaining <= 0:
                    break
    finally:
        if apply and got_lock:
            await pg.release_catalogue_lock()

    el = time.time() - started
    print()
    print(f"summary: seen={grand_seen} "
          f"{'would-upsert' if not apply else 'upserted'}={grand_up} "
          f"embedded={grand_emb} bad_lines={grand_bad} elapsed={el:.1f}s")
    if not apply:
        print("(dry-run — no DB writes; pass --apply to commit)")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--max", type=int, default=50,
                    help="Max events to process (0 = unlimited). Default 50 (preview).")
    ap.add_argument("--apply", action="store_true",
                    help="Write to the read-model. Default is dry-run (no DB writes).")
    ap.add_argument("--no-embed", action="store_true",
                    help="Skip embeddings (structural rows only — fast, CPU-safe). "
                         "Embeddings fill later via the live loop or --embed-only.")
    ap.add_argument("--include-archives", action="store_true",
                    help="Also replay rotated catalogue_events.*.jsonl archives.")
    ap.add_argument("--embed-only", action="store_true",
                    help="Skip projection; only embed entries that are missing an embedding.")
    ap.add_argument("--observe-only", action="store_true",
                    help="Scan the stream for distinct EventKinds and merge them into "
                         "catalogue_state.observed_kinds, preserving the resume offset. "
                         "Seeds the /insight/catalogue/kinds 'emitted' marker.")
    args = ap.parse_args(argv)
    if args.max < 0:
        print("FATAL: --max must be >= 0", file=sys.stderr)
        return 2
    try:
        return asyncio.run(run(args.max, args.apply, embed=not args.no_embed,
                               include_archives=args.include_archives,
                               embed_only=args.embed_only,
                               observe_only=args.observe_only))
    except KeyboardInterrupt:
        print("\n(interrupted)")
        return 130


if __name__ == "__main__":
    sys.exit(main())
