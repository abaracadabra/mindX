"""
Thin CLI for the deployer, invoked by scripts/deployer/deploy.sh.

For LOCAL/dev use the CLI can run an unsigned deploy (it stamps a dev signer);
production deploys go through the wallet-signed backend routes. The `--signer`
flag records a deployer-of-record without signature verification — only honored
when MINDX_DEPLOYER_CLI_UNSIGNED=1 (local convenience).

Usage:
  python -m agents.deployer.cli deploy <manifest.deploy> <chain> [--signer 0x..]
  python -m agents.deployer.cli list <manifest.deploy>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from .drivers import get_driver
from .manifest import load_manifest
from .records import now, write_batch_manifest


async def _run_local(manifest_path: str, chain: str, signer: str) -> int:
    manifest = load_manifest(manifest_path)
    stages = manifest.selected_stages(chain)
    from . import keys

    results = []
    for s in stages:
        key = (await keys.resolve_deployer_key(s.deployer_entity, s.chain, s.chain_id)
               if s.driver == "foundry"
               else await keys.resolve_deployer_mnemonic(s.deployer_entity, s.chain,
                                                         s.config.get("deployer_mnemonic_env", "")))
        driver = get_driver(s.driver)
        checks = await driver.preflight(s, key)
        print(f"[preflight {s.chain}]")
        for c in checks:
            print(f"  {'OK ' if c.passed else 'FAIL'} {c.name}: {c.detail}")
        if not all(c.passed for c in checks):
            results.append({"chain": s.chain, "status": "failed", "error": "preflight"})
            continue
        dr = await driver.deploy(s, key, project=manifest.project, deployer_of_record=signer)
        status = "recorded" if dr.ok else "failed"
        print(f"[deploy {s.chain}] {status}" + (f" — {dr.error}" if dr.error else ""))
        if dr.ok:
            print(json.dumps(dr.record, indent=2))
        results.append({"chain": s.chain, "status": status, "error": dr.error, "record": dr.record})
    batch_id = f"cli-{int(now())}"
    write_batch_manifest(batch_id, {"intent_id": batch_id, "project": manifest.project,
                                    "deployer_of_record": signer, "stages": results})
    return 0 if all(r["status"] == "recorded" for r in results) else 1


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="deployer")
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("deploy")
    d.add_argument("manifest")
    d.add_argument("chain")
    d.add_argument("--signer", default="0x0000000000000000000000000000000000000000")
    l = sub.add_parser("list")
    l.add_argument("manifest")
    args = p.parse_args(argv)

    if args.cmd == "list":
        m = load_manifest(args.manifest)
        print(f"{m.project} v{m.version}  min_tier={m.required_min_tier}")
        for s in m.stages:
            print(f"  - {s.chain} (chain_id={s.chain_id}, driver={s.driver}, mainnet={s.is_mainnet})")
        return 0

    if args.cmd == "deploy":
        if os.environ.get("MINDX_DEPLOYER_CLI_UNSIGNED") != "1":
            print("Refusing unsigned CLI deploy. Set MINDX_DEPLOYER_CLI_UNSIGNED=1 for local dev, "
                  "or use the wallet-signed /deployer/intent route.", file=sys.stderr)
            return 2
        return asyncio.run(_run_local(args.manifest, args.chain, args.signer))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
