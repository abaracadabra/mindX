# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""ephermaleth.cli — verify a chain or a voting booth from the command line.

    python -m ephermaleth verify <chain.json | post.html>   [--registry r.json]
    python -m ephermaleth booth  <booth.jsonl>              [--registry r.json]

Exit code 0 = valid, 1 = invalid/broken, 2 = usage/IO error. Anyone can audit a
published "speech from the throne" with nothing but this file and public keys.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from .verify import extract_chain_from_html, verify_chain
from .votingbooth import VotingBooth


def _load_registry(path: Optional[str]) -> Dict[str, str]:
    if not path:
        return {}
    try:
        return json.loads(Path(path).read_text())
    except Exception as e:
        print(f"warn: could not read registry {path}: {e}", file=sys.stderr)
        return {}


def _load_chain(path: str) -> Optional[Dict[str, Any]]:
    raw = Path(path).read_text(encoding="utf-8")
    if path.endswith((".html", ".htm")) or "<script" in raw:
        return extract_chain_from_html(raw)
    return json.loads(raw)


def _fmt(report: Dict[str, Any]) -> str:
    head = (f"chain {report['chain_id'][:20]}… — {report['links']} links, "
            f"{report['signed_links']} signed, {report['unsigned_links']} attested")
    lines = [head, f"  intact={report['chain_intact']} signatures_valid={report['signatures_valid']} "
                   f"registry_match={report['registry_match']}  =>  "
                   f"{'VALID ✓' if report['valid'] else 'INVALID ✗'}"]
    for r in report["results"]:
        sig = "signed" if r["signed"] else "attested"
        ok = "✓" if r["valid"] else "✗"
        lines.append(f"   [{ok}] seq {r['seq']:>2} {r['role']}:{r['agent_id']} "
                     f"{r['act']} ({sig}) {r.get('address') or '—'}")
    return "\n".join(lines)


def main(argv: Optional[list] = None) -> int:
    p = argparse.ArgumentParser(prog="ephermaleth", description="Verify attestation chains + voting booths.")
    sub = p.add_subparsers(dest="cmd", required=True)
    pv = sub.add_parser("verify", help="verify a chain JSON or post HTML")
    pv.add_argument("path"); pv.add_argument("--registry", default=None)
    pb = sub.add_parser("booth", help="verify a voting-booth ledger (JSONL)")
    pb.add_argument("path"); pb.add_argument("--registry", default=None)
    args = p.parse_args(argv)

    try:
        registry = _load_registry(getattr(args, "registry", None))
        if args.cmd == "verify":
            chain = _load_chain(args.path)
            if not isinstance(chain, dict) or not chain.get("links"):
                print("no chain found", file=sys.stderr); return 2
            report = verify_chain(chain, registry)
            print(_fmt(report))
            return 0 if report["valid"] else 1
        if args.cmd == "booth":
            report = VotingBooth(args.path).verify_ledger(registry)
            print(f"booth {args.path} — {report['records']} records · "
                  f"linkage={report['linkage_ok']} records_ok={report['records_ok']} "
                  f"chains_ok={report['chains_ok']}  =>  "
                  f"{'VALID ✓' if report['valid'] else 'INVALID ✗'}")
            return 0 if report["valid"] else 1
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr); return 2
    except Exception as e:
        print(f"error: {e}", file=sys.stderr); return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
