#!/usr/bin/env python3
"""dojo — CLI for the Dojo consensus-arbitration service.

The Dojo is a service to the Boardroom, the War Council, and mindXtrain: it takes
their (possibly disagreeing) verdicts, resolves them under a chosen consensus model,
and records one verifiable decision. This CLI makes that callable from the shell —
e.g. mindXtrain can shell out after an imprint, or an operator can settle a dispute.

Examples
--------
  # settle inline ballots under supermajority
  python scripts/dojo.py decide --subject "promote gen7" --model supermajority \
      --inline '[{"origin":"mindxtrain","vote":"approve","confidence":0.9},
                 {"origin":"boardroom","voter":"cro_risk","vote":"reject","confidence":0.7}]'

  # arbitrate a mindXtrain imprint verdict file
  python scripts/dojo.py decide --subject "imprint:gen7" --mindxtrain verdict.json \
      --model weighted_confidence

  # tail recent decisions as plain text
  python scripts/dojo.py recent --limit 10 --h

  # list available consensus models
  python scripts/dojo.py models
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# make the mindX package importable when run as a script
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from daio.governance import dojo_arbiter as A  # noqa: E402


def _load_json_arg(val: str):
    """A JSON literal, or @path / a bare path to a .json file."""
    if val is None:
        return None
    if val.startswith("@"):
        val = val[1:]
    p = Path(val)
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return json.loads(val)


def _render_text(rec: dict) -> str:
    lines = [
        f"dojo · {rec['decision'].upper()}  ({rec['model']})",
        f"  subject   {rec['subject']}",
        f"  score     {rec['score']}  (threshold {rec['threshold']}, stakes {rec['stakes']})",
        f"  council   {rec['council']}   ·   {rec.get('ts_utc','')}",
        f"  ballots   {len(rec.get('ballots', []))} from "
        f"{sorted(set(b['origin'] for b in rec.get('ballots', [])))}",
    ]
    for b in rec.get("ballots", []):
        lines.append(f"    {b['origin']:<11} {b['voter']:<16} {b['vote']:<7} "
                     f"w={b['weight']} c={b['confidence']}")
    if rec.get("dissent"):
        lines.append(f"  dissent   {len(rec['dissent'])} branch(es)")
        for d in rec["dissent"]:
            lines.append(f"    ↯ {d['voter']}: {d.get('reasoning','')[:80]}")
    if rec.get("record_hash"):
        lines.append(f"  record    {rec['record_hash']}")
    return "\n".join(lines)


async def _cmd_decide(args) -> int:
    ballots = []
    if args.inline:
        ballots += list(_load_json_arg(args.inline))
    if args.boardroom:
        ballots += A.from_boardroom(_load_json_arg(args.boardroom))
    if args.warcouncil:
        ballots += A.from_warcouncil(_load_json_arg(args.warcouncil))
    if args.mindxtrain:
        ballots += A.from_mindxtrain(_load_json_arg(args.mindxtrain))
    if args.daio:
        ballots += A.from_daio(_load_json_arg(args.daio))
    if not ballots:
        print("error: no ballots — provide --inline/--boardroom/--warcouncil/--mindxtrain/--daio",
              file=sys.stderr)
        return 2
    rec = await A.decide(subject=args.subject, ballots=ballots, stakes=args.stakes,
                         consensus_model=args.model, council=args.council, record=not args.no_record)
    print(_render_text(rec) if args.h else json.dumps(rec, indent=2, ensure_ascii=False))
    return 0


async def _cmd_recent(args) -> int:
    recs = await A.recent(args.limit, council=args.council)
    if args.h:
        if not recs:
            print("(no dojo decisions yet)")
        for r in recs:
            d = r.get("decision", "?")
            print(f"{r.get('ts_utc','')[:19]}  {d.upper():<11} {r.get('model',''):<18} "
                  f"score={r.get('score')}  {r.get('subject','')[:50]}")
    else:
        print(json.dumps(recs, indent=2, ensure_ascii=False))
    return 0


def _cmd_models(_args) -> int:
    print("\n".join(sorted(A.CONSENSUS_MODELS.keys())))
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="dojo", description="Dojo consensus-arbitration service CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("decide", help="resolve ballots into one recorded decision")
    d.add_argument("--subject", required=True, help="what is being decided")
    d.add_argument("--model", default="supermajority", choices=sorted(A.CONSENSUS_MODELS.keys()))
    d.add_argument("--stakes", type=int, default=0, help="0 routine .. 2 critical (prime_ladder)")
    d.add_argument("--council", default="dojo")
    d.add_argument("--inline", help="JSON list of ballot dicts (or @path)")
    d.add_argument("--boardroom", help="boardroom session JSON (or @path)")
    d.add_argument("--warcouncil", help="war-council seat-votes JSON (or @path)")
    d.add_argument("--mindxtrain", help="mindXtrain imprint verdict JSON (or @path)")
    d.add_argument("--daio", help="DAIO {group:{voter:bool}} JSON (or @path)")
    d.add_argument("--no-record", action="store_true", help="do not persist the decision")
    d.add_argument("--h", action="store_true", help="human plain-text output")

    r = sub.add_parser("recent", help="tail recent dojo decisions")
    r.add_argument("--limit", type=int, default=20)
    r.add_argument("--council", default=None)
    r.add_argument("--h", action="store_true", help="human plain-text output")

    sub.add_parser("models", help="list available consensus models")

    args = p.parse_args(argv)
    if args.cmd == "decide":
        return asyncio.run(_cmd_decide(args))
    if args.cmd == "recent":
        return asyncio.run(_cmd_recent(args))
    if args.cmd == "models":
        return _cmd_models(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
