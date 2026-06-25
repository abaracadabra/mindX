#!/usr/bin/env python3
"""gitmind — CLI for mindX's efficient, self-hosted git backup/restore.

gitmind self-hosts mindX's git (a local bare origin mindX owns, kept in sync with
native delta pushes) and links every incremental backup into a **THlNK** — the THOT
lINK. Each increment is an immutable, content-addressed THOT (Keccak Merkle
`thot_root`, chained by `parent_root`), replicated to Lighthouse (IPFS) + Arweave
(permaweb). The THlNK replicated to the permaweb IS distributed mindX: reconstructable
anywhere, no single point of failure.

Examples
--------
  python scripts/gitmind.py status            # state + self-host + THlNK head
  python scripts/gitmind.py backup             # incremental THOT (skips if unchanged)
  python scripts/gitmind.py backup --full      # force a fresh basis THOT (new THlNK root)
  python scripts/gitmind.py push               # delta-sync the self-hosted origin only
  python scripts/gitmind.py thlnk              # show the link of THOTs (lineage)
  python scripts/gitmind.py restore /tmp/clone        # clone from the self-hosted origin
  python scripts/gitmind.py reconstruct /tmp/rebuild  # rebuild from the THlNK bundle chain
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from mindx.gitmind.gitmind import GitMind  # noqa: E402


def _gm(args) -> GitMind:
    return GitMind(repo_root=Path(args.repo) if args.repo else None)


def _short(v, n=18):
    s = "" if v is None else str(v)
    return s[:n] + ("…" if len(s) > n else "")


def cmd_status(args) -> int:
    gm = _gm(args)
    rep = gm.report()
    if args.json:
        print(json.dumps(rep, indent=2, default=str)); return 0
    st, sh, tk = rep["state"], rep["self_host"], rep["thlnk"]
    print(f"repo      {gm.root}")
    print(f"head      {st.get('short')} ({st.get('branch')})  dirty={st.get('dirty')}  commits={st.get('commit_count')}")
    print(f"self-host {sh['bare']}  init={sh['initialized']}  refs={len(sh['refs'])}")
    print(f"THlNK     id={_short(tk.get('thlnk_id'))}  thots={tk.get('count')}  head_root={_short(tk.get('head_thot_root'))}")
    print(f"sources   {', '.join(rep['sources'])}   anchor_enabled={rep['anchor_enabled']}")
    lb = rep.get("last_backup")
    if lb:
        print(f"last      seq={lb.get('seq')} {'incr' if lb.get('incremental') else 'basis'} "
              f"{lb.get('asset_kind')}  {lb.get('bytes')}B  replicas={lb.get('replicas')}")
    return 0


def cmd_backup(args) -> int:
    gm = _gm(args)
    r = asyncio.run(gm.backup(full=args.full))
    if r.get("skipped"):
        print(f"skipped — {r.get('reason')} (THlNK unchanged)"); return 0
    print(f"ok={r.get('ok')} seq={r.get('seq')} {'incremental' if r.get('incremental') else 'BASIS'} "
          f"{r.get('asset_kind')} {r.get('bytes')}B")
    print(f"  thot_root  {r.get('thot_root')}")
    print(f"  parent     {_short(r.get('parent_root'), 18)}")
    print(f"  THlNK      {r.get('thlnk_id')}  ({r.get('thlnk_count')} THOTs)")
    print(f"  replicas   {r.get('replicas')}  cid={r.get('cid')}  arweave={r.get('arweave')}  self_host={r.get('self_host_ok')}")
    return 0 if r.get("ok") else 1


def cmd_push(args) -> int:
    r = _gm(args).mirror_push()
    print(json.dumps(r, indent=2, default=str)); return 0 if r.get("ok") else 1


def cmd_thlnk(args) -> int:
    tk = _gm(args).thlnk_summary()
    if args.json:
        print(json.dumps(tk, indent=2, default=str)); return 0
    print(f"THlNK {_short(tk.get('thlnk_id'))} — {tk.get('count')} THOTs, head {_short(tk.get('head'))}")
    print(f"  basis_root {_short(tk.get('basis_root'))}")
    for t in tk.get("lineage", []):
        print(f"  #{t['seq']:<3} {t['kind']:<4} root={_short(t.get('thot_root'),18)} "
              f"parent={_short(t.get('parent_root'),12)} cid={_short(t.get('cid'),16)}")
    return 0


def cmd_restore(args) -> int:
    r = _gm(args).clone_self_host(Path(args.dest))
    print(json.dumps(r, indent=2, default=str)); return 0 if r.get("ok") else 1


def cmd_reconstruct(args) -> int:
    r = _gm(args).reconstruct_from_thlnk(Path(args.dest))
    print(json.dumps(r, indent=2, default=str)); return 0 if r.get("ok") else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="gitmind", description="mindX efficient self-hosted git (THOT/THlNK)")
    p.add_argument("--repo", help="repo root (default: mindX project root)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("status", help="state + self-host + THlNK head"); s.add_argument("--json", action="store_true")
    b = sub.add_parser("backup", help="incremental THOT backup (skips if unchanged)"); b.add_argument("--full", action="store_true")
    sub.add_parser("push", help="delta-sync the self-hosted origin only")
    tk = sub.add_parser("thlnk", help="show the link of THOTs (lineage)"); tk.add_argument("--json", action="store_true")
    r = sub.add_parser("restore", help="clone from the self-hosted origin"); r.add_argument("dest")
    rc = sub.add_parser("reconstruct", help="rebuild from the THlNK bundle chain"); rc.add_argument("dest")

    args = p.parse_args(argv)
    return {"status": cmd_status, "backup": cmd_backup, "push": cmd_push, "thlnk": cmd_thlnk,
            "restore": cmd_restore, "reconstruct": cmd_reconstruct}[args.cmd](args)


if __name__ == "__main__":
    raise SystemExit(main())
