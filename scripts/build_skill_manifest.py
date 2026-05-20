#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Build (and optionally upload) the SkillStore content-addressable manifest.

Phase A: walk every SKILL.md in the SkillStore, hash it, build a deterministic
manifest JSON, persist to disk, and optionally upload to 0G Storage.

Phase B (chain anchor) is deferred — the SkillRegistry contract is not yet
deployed. ``--anchor`` is a placeholder that returns ``not_anchored``.

Examples
--------

    # Build + persist, no upload
    python scripts/build_skill_manifest.py

    # Build + persist + 0G Storage upload (sidecar must be running locally)
    python scripts/build_skill_manifest.py --upload

    # Custom destination + chain the previous manifest as parent
    python scripts/build_skill_manifest.py \\
        --dest /var/lib/mindx/skills.manifest.json \\
        --previous-root 0xabc...

Verify a specific skill against the most recent manifest:

    python scripts/build_skill_manifest.py --verify tutorial/alpha
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.skills.manifest import (
    DEFAULT_MANIFEST_PATH,
    anchor_manifest,
    build_manifest,
    load_meta,
    persist,
    upload_manifest,
    verify_skill,
)
from agents.skills.store import SkillStore


async def _maybe_upload(manifest):
    try:
        from agents.storage.zerog_provider import ZeroGProvider
    except Exception as e:
        print(f"build_skill_manifest: ZeroGProvider unavailable: {e}", file=sys.stderr)
        return None
    provider = ZeroGProvider()
    try:
        return await upload_manifest(manifest, provider=provider)
    finally:
        try:
            await provider.close()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dest",
                   help=f"Manifest destination path (default: {DEFAULT_MANIFEST_PATH})")
    p.add_argument("--upload", action="store_true",
                   help="Upload manifest bytes to 0G Storage via the sidecar")
    p.add_argument("--anchor", action="store_true",
                   help="(Phase B placeholder — currently a no-op stub)")
    p.add_argument("--previous-root",
                   help="Record this 0G root as the previous manifest in the chain")
    p.add_argument("--exclude-pinned", action="store_true",
                   help="Exclude pinned skills from the manifest (default: include)")
    p.add_argument("--verify", metavar="CATEGORY/SLUG",
                   help="Verify the on-disk SKILL.md against the most recent persisted manifest")
    p.add_argument("--quiet", action="store_true", help="Suppress the full JSON manifest on stdout")
    args = p.parse_args(argv)

    store = SkillStore()

    # ── verify-only mode ────────────────────────────────────────
    if args.verify:
        if "/" not in args.verify:
            p.error("--verify expects 'CATEGORY/SLUG'")
        category, slug = args.verify.split("/", 1)
        meta = load_meta(args.dest)
        if meta is None:
            print("no manifest persisted yet — run without --verify first", file=sys.stderr)
            return 2
        # Reload the manifest body
        manifest_path = Path(meta["manifest_path"])
        if not manifest_path.exists():
            print(f"manifest body missing at {manifest_path}", file=sys.stderr)
            return 2
        body = json.loads(manifest_path.read_text(encoding="utf-8"))
        from agents.skills.manifest import ManifestEntry, SkillManifest
        m = SkillManifest(
            manifest_version=body["manifest_version"],
            generated_at=body["generated_at"],
            skill_count=body["skill_count"],
            entries=[ManifestEntry(**e) for e in body["entries"]],
            previous_manifest_root=body.get("previous_manifest_root"),
        )
        result = verify_skill(m, category, slug, store)
        print(json.dumps(result.to_dict(), indent=2))
        return 0 if result.matched else 1

    # ── build mode ──────────────────────────────────────────────
    previous_root = args.previous_root
    if previous_root is None:
        prev_meta = load_meta(args.dest)
        if prev_meta is not None:
            previous_root = prev_meta.get("zg_root")  # chain even when no upload happened

    manifest = build_manifest(
        store,
        previous_manifest_root=previous_root,
        include_pinned=not args.exclude_pinned,
    )

    zg_root: str | None = None
    if args.upload:
        zg_root = asyncio.run(_maybe_upload(manifest))

    chain_status, tx_hash = ("skipped", None)
    if args.anchor and zg_root is not None:
        chain_status, tx_hash = anchor_manifest(zg_root)

    dest = persist(manifest, dest=args.dest, zg_root=zg_root)

    if not args.quiet:
        print(json.dumps(manifest.to_dict(), indent=2, sort_keys=True))

    print(
        f"manifest: {manifest.skill_count} skills · sha256={manifest.sha256()[:16]}… "
        f"· path={dest} · zg_root={zg_root or '∅'} "
        f"· anchor={chain_status} tx={tx_hash or '∅'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
