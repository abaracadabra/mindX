#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Run the SkillStore Curator.

Defaults to dry-run (audit only). Pass ``--apply`` to archive flagged
skills (the SkillStore enforces archive-only / refuses pinned + human).

Examples
--------

    python scripts/run_curator.py                # audit, no writes
    python scripts/run_curator.py --apply        # audit + archive
    python scripts/run_curator.py --stale-days 30 --apply

Crontab (operator):
    0 3 * * 0 /home/mindx/mindX/.mindx_env/bin/python /home/mindx/mindX/scripts/run_curator.py --apply

Per the Hermes integration doc §8.1 the cadence default is **7 days**; pair
this with the systemd ``OnCalendar=Sun *-*-* 03:00:00`` of a
``mindx-curator.timer`` unit if running on systemd-only boxes.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make repo root importable when invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.skills.curator import Curator
from agents.skills.store import SkillStore


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--apply", action="store_true",
                   help="Archive flagged skills (default: audit-only / dry run)")
    p.add_argument("--stale-days", type=int, default=90,
                   help="Days since updated_at after which an agent-authored skill is stale (default 90)")
    p.add_argument("--min-body-bytes", type=int, default=40,
                   help="Skills with body shorter than this many bytes are flagged (default 40)")
    p.add_argument("--report-dir",
                   help="Directory to write the JSON report into (default: data/learnings/curator/)")
    p.add_argument("--quiet", action="store_true", help="Don't print the JSON report to stdout")
    args = p.parse_args(argv)

    store = SkillStore()
    curator = Curator(
        store,
        report_dir=args.report_dir,
        stale_days=args.stale_days,
        min_body_bytes=args.min_body_bytes,
    )
    report = curator.run(apply=args.apply)
    out = report.to_dict()

    if not args.quiet:
        print(json.dumps(out, indent=2))

    msg = "applied" if args.apply else "dry-run"
    print(
        f"curator {msg}: {out['inspected']} skills inspected, "
        f"{out['flagged_count']} flagged, {out['archived_count']} archived, "
        f"{out['skipped_count']} skipped.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
