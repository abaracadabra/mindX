#!/usr/bin/env python
"""Publish the Knowledge-Catalogue milestone via AuthorAgent's real machinery.

This is AuthorAgent responding to a github milestone: it takes the commit batch
(payload at /tmp/cat_milestone_payload.json), scores it with ``assess_milestone``,
composes the article with ``_compose_milestone_article`` (the same path
``consider_github_milestones`` drives), and publishes it as a DRAFT to
rage.pythai.net — with the cryptographic identity footer auto-appended by
``publish_to_rage``.

Run on the VPS as the mindx user (where the wordpress.agent loopback lives):
    sudo -u mindx env PYTHONPATH=/home/mindx/mindX .mindx_env/bin/python \
        scripts/publish_catalogue_milestone.py
"""
import asyncio
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.author_agent import AuthorAgent

PAYLOAD = Path("/tmp/cat_milestone_payload.json")
# A representative headline (the auto-picker would choose a single commit subject;
# this milestone spans the whole catalogue, so we frame it accordingly).
HEADLINE = "The Knowledge Catalogue goes live: a queryable read-model, hybrid search, and provenance lineage"


async def main() -> int:
    commits = json.loads(PAYLOAD.read_text())
    if not commits:
        print("[fatal] empty payload"); return 1

    agent = await AuthorAgent.get_instance()

    # Score with the real heuristic (objects expose attrs assess_milestone reads).
    objs = [types.SimpleNamespace(**c) for c in commits]
    decision = agent.assess_milestone(objs)
    decision["headline"] = HEADLINE          # frame the whole-catalogue milestone
    decision.setdefault("labels", []).extend(["catalogue", "new-capability"])

    title, html, excerpt, topic = agent._compose_milestone_article(
        {"commits": commits, "decision": decision})

    print(f"[compose] title: {title}")
    print(f"[compose] html length: {len(html)} | topic: {topic}")

    res = await agent.publish_to_rage(
        title=title,
        content_html=html,
        status="draft",                      # staged for human review
        slug="milestone-knowledge-catalogue-live",
        excerpt=excerpt or ("mindX shipped its Knowledge Catalogue: a CQRS read-model "
                            "over its own event stream — projector, hybrid search, and a "
                            "provenance lineage graph — all on the existing pgvector stack."),
        topic="rage",                         # THOTH featured image (memory/writing)
        seo_keywords=["mindX", "knowledge catalogue", "CQRS", "pgvector", "lineage",
                      "hybrid search", "provenance", "milestone", decision.get("theme", "architecture")],
        meta={"_mindx_trigger_kind": "milestone",
              "_mindx_trigger_id": "milestone:knowledge-catalogue-" + commits[-1]["short_sha"]},
    )
    print(f"[publish] -> {res}")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
