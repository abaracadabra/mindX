#!/usr/bin/env python3
"""Operator driver for LTM retention — the right end of KNOWLEDGE→WISDOM→WEIGHTS.

machine.dream promotes STM patterns into LTM; mindXtrain distills those dreams
into a corpus, forges it and ascends a LoRA generation. When a generation is
*promoted* (trained, proof-of-recall passed, served to Ollama) the model itself
carries that memory — so the individual pattern-promotion files behind it can
collapse into one ROLLUP_YYYYMM file per month.

Nothing pruned LTM before 2026-08-09 (the dream's prune step only ever called
prune_stm), so 67,309 files had accumulated, every one of them re-read on each
get_ltm_insights() call. The dream cycle now compacts incrementally; this script
is for clearing that backlog in one pass, and for dry-running the policy.

Two gates must BOTH pass before a record is folded away:
  1. older than --days (default MINDX_LTM_RETENTION_DAYS=90)
  2. older than the last *promoted* ascent (ascend_scheduler.trained_through_ts)

Gate 2 is deliberately not the ascend watermark: the watermark advances on
failed generations too, so it runs ahead of what any model actually learned.
With no promoted generation this script is a no-op by design.

Usage:
  python scripts/compact_ltm.py --dry-run            # report, change nothing
  python scripts/compact_ltm.py                      # compact every agent
  python scripts/compact_ltm.py --agent mindx_meta_agent
  python scripts/compact_ltm.py --days 30 --dry-run
"""
import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import PROJECT_ROOT
from agents.memory_agent import MemoryAgent, LTM_RETENTION_DAYS
from mindx.godel.ascend_scheduler import trained_through_ts


async def main() -> int:
    ap = argparse.ArgumentParser(description="Compact aged, already-trained LTM records")
    ap.add_argument("--agent", help="single agent id (default: every agent with LTM)")
    ap.add_argument("--days", type=int, default=LTM_RETENTION_DAYS,
                    help=f"retention window in days (default {LTM_RETENTION_DAYS})")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be compacted, write nothing")
    args = ap.parse_args()

    through = trained_through_ts()
    if through is None:
        print("No promoted ascent found in data/logs/ascend_log.jsonl.")
        print("Nothing is provably in the weights, so nothing is prunable — exiting.")
        return 0

    print(f"trained through : {datetime.fromtimestamp(through).isoformat()}  (last promoted generation)")
    print(f"retention window: {args.days} days")
    print(f"mode            : {'DRY RUN' if args.dry_run else 'LIVE'}\n")

    memory = MemoryAgent()
    ltm_root = memory.ltm_path
    if args.agent:
        agent_ids = [args.agent]
    else:
        agent_ids = sorted(p.name for p in ltm_root.iterdir() if p.is_dir()) if ltm_root.exists() else []

    if not agent_ids:
        print(f"No agent LTM directories under {ltm_root}")
        return 0

    totals = {"compacted": 0, "rollups": 0, "zero_byte_removed": 0,
              "quarantined": 0, "skipped_untrained": 0}
    files_before = len(list(ltm_root.rglob("*_pattern_promotion.json")))

    for agent_id in agent_ids:
        res = await memory.compact_ltm(agent_id, max_age_days=args.days,
                                       trained_through_ts=through, dry_run=args.dry_run)
        if res.get("status") not in ("ok",):
            continue
        for k in totals:
            totals[k] += res.get(k, 0)
        if res.get("compacted") or res.get("zero_byte_removed") or res.get("quarantined"):
            print(f"  {agent_id:<40} {res['compacted']:>6} compacted -> {res['rollups']:>3} rollup(s), "
                  f"{res['zero_byte_removed']:>4} zero-byte, {res['quarantined']:>3} quarantined, "
                  f"{res['skipped_untrained']:>5} untrained kept")

    files_after = len(list(ltm_root.rglob("*_pattern_promotion.json")))
    print(f"\n{'DRY RUN — no changes written' if args.dry_run else 'DONE'}")
    print(f"  records compacted : {totals['compacted']}")
    print(f"  rollups written   : {totals['rollups']}")
    print(f"  zero-byte removed : {totals['zero_byte_removed']}")
    print(f"  quarantined       : {totals['quarantined']}")
    print(f"  untrained retained: {totals['skipped_untrained']}  (not in any promoted model — kept)")
    print(f"  LTM files         : {files_before} -> {files_after}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
