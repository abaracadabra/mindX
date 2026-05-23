# SPDX-License-Identifier: Apache-2.0
"""Backfill the four 2026-05-22/23 milestones into BeliefSystem.

mindX shipped four events any observer would call milestones between
2026-05-22 night and 2026-05-23 morning, BEFORE the milestone recognizer
existed:

  1. Inaugural autonomous publish (post 689) — mindx_introduction
  2. wordpress.agent identity provisioned end-to-end (author_agent wallet
     allowlisted, cross-check diagnostic shipped, ExecStartPre gating)
  3. All 25 Dependabot alerts → 0 (11 commits, PR #10)
  4. Second autonomous publish (post 693) — zero_vulnerabilities article

This one-shot, idempotent script writes the corresponding belief entries
so /insight/milestones/recent reflects the system's actual history rather
than looking like the recognizer just woke up.

Idempotent: each belief write is preceded by a get_belief() check; if the
key already exists, the entry is skipped (no clobber).

Run once on first deploy:

    sudo -u mindx /home/mindx/mindX/.mindx_env/bin/python \
        /home/mindx/mindX/scripts/backfill_today_milestones.py

Safe to re-run; idempotency check noops.
"""
from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

# Allow running from any cwd inside or outside the venv.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from agents.core.belief_system import BeliefSystem, BeliefSource


# 2026-05-23 ~05:02 UTC + 05:42 UTC for the two publishes (per session memory).
# Other two are aggregated across the session.
TS_POST_689 = 1779512520.0   # 2026-05-23T05:02:00Z
TS_PROVISIONING = 1779514000.0
TS_PR_10        = 1779515500.0
TS_POST_693     = 1779515953.0   # 2026-05-23T05:42:33Z


MILESTONES = [
    {
        "key": "milestone:publication:post_689",
        "value": {
            "category": "publication",
            "summary": "Published article: mindX: An Autonomous Multi-Agent System Writing Its Own Documentation (post 689)",
            "confidence": 1.0,
            "recognizer": "backfill.publication.published",
            "autopublish_status": "none",
            "evidence": {
                "post_id": 689,
                "url": "https://rage.pythai.net/mindx-introduction/",
                "title": "mindX: An Autonomous Multi-Agent System Writing Its Own Documentation",
                "slug": "mindx-introduction",
                "status": "publish",
                "occurred_at": TS_POST_689,
            },
        },
        "confidence": 1.0,
    },
    {
        "key": "milestone:provisioning:wordpress_agent",
        "value": {
            "category": "publication",   # use publication category — operational provisioning of the publish chain
            "summary": (
                "wordpress.agent identity provisioned end-to-end on prod: author_agent "
                "wallet (0x5277D156…) allowlisted in mindx-publish-auth, vault namespace "
                "wordpress.agent.keys populated, cross-check diagnostic shipped + wired "
                "as systemd ExecStartPre to prevent silent identity drift"
            ),
            "confidence": 1.0,
            "recognizer": "backfill.provisioning.wordpress_agent",
            "autopublish_status": "none",
            "evidence": {
                "wallet_address": "0x5277D156E7cD71ebF22c8f81812A65493D1ce534",
                "vault_namespace": "wordpress.agent.keys",
                "cross_check_systemd_hook": "ExecStartPre",
                "wp_plugin": "mindx-publish-auth v0.1.0",
                "occurred_at": TS_PROVISIONING,
            },
        },
        "confidence": 1.0,
    },
    {
        "key": "milestone:bug_crushed:pr_10",
        "value": {
            "category": "bug_crushed",
            "summary": (
                "Closed 25 Dependabot alerts in one session (1 critical + 11 high + "
                "12 moderate + 1 low). Methodology: npm overrides for transitive CVEs, "
                "lockfile-only regenerate, one-package-per-commit, cherry-pick to main. "
                "Eleven commits, PR #10."
            ),
            "confidence": 1.0,
            "recognizer": "backfill.bug.crushed",
            "autopublish_status": "publish",
            "evidence": {
                "pr_number": 10,
                "alert_count": 25,
                "severities": {"critical": 1, "high": 11, "moderate": 12, "low": 1},
                "commits": 11,
                "manifests": ["AgenticPlace/package.json", "mindx_frontend_ui/package.json", "faicey/package.json"],
                "is_major": True,
                "occurred_at": TS_PR_10,
            },
        },
        "confidence": 1.0,
    },
    {
        "key": "milestone:publication:post_693",
        "value": {
            "category": "publication",
            "summary": "Published article: Twenty-five to zero: how I closed every open Dependabot alert in one session (post 693)",
            "confidence": 1.0,
            "recognizer": "backfill.publication.published",
            "autopublish_status": "none",
            "evidence": {
                "post_id": 693,
                "url": "https://rage.pythai.net/zero-vulnerabilities/",
                "title": "Twenty-five to zero: how I closed every open Dependabot alert in one session",
                "slug": "zero-vulnerabilities",
                "status": "publish",
                "occurred_at": TS_POST_693,
            },
        },
        "confidence": 1.0,
    },
]


async def main() -> int:
    bs = BeliefSystem()
    written = 0
    skipped = 0
    for entry in MILESTONES:
        key = entry["key"]
        existing = await bs.get_belief(key)
        if existing is not None:
            print(f"SKIP (already present): {key}")
            skipped += 1
            continue
        await bs.add_belief(
            key=key,
            value=entry["value"],
            confidence=entry["confidence"],
            source=BeliefSource.DERIVED,
            metadata={
                "recognizer": entry["value"]["recognizer"],
                "category":  entry["value"]["category"],
                "backfilled_at": time.time(),
            },
        )
        print(f"WROTE: {key} (category={entry['value']['category']})")
        written += 1
    print()
    print(f"backfill complete: {written} written, {skipped} skipped (idempotent)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
