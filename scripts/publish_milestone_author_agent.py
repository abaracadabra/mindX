#!/usr/bin/env python
"""Prototype milestone publisher — AuthorAgent's own github.awareness update.

Canonical internal AuthorAgent direct-Python path. Publishes the inaugural
milestone article (composed in mindX's voice) as a DRAFT to rage.pythai.net
for human review. Featured image: THOTH (the scribe). Tagged with the
milestone trigger metadata the PublicationOrchestrator stamps.

Invoke from the repo root on the VPS as the mindx user:
    sudo -u mindx .mindx_env/bin/python scripts/publish_milestone_author_agent.py
"""
import asyncio
import mimetypes
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from agents.author_agent import AuthorAgent
from mindx_backend_service.main_service import _render_md

WP_AGENT_URL = os.environ.get("MINDX_WORDPRESS_AGENT_URL", "http://127.0.0.1:8765")

ARTICLE = Path("docs/publications/milestone_author_agent_github_awareness.md")
TITLE = "Milestone: I Learned to Read My Own History — and to Speak About It"
SLUG = "milestone-author-agent-github-awareness"
EXCERPT = (
    "The prototype milestone article. AuthorAgent now reads mindX's own public "
    "git history, recognizes milestones, maintains its documentation index, and "
    "publishes in its own voice — landing alongside the mindx/godel proof kernel "
    "and the GMI self-audit (verdict, honestly: not yet)."
)
SEO_KEYWORDS = [
    "mindX", "milestone", "github.awareness", "AuthorAgent", "self-improvement",
    "Gödel machine", "Gödel Machine Index", "Schmidhuber engine", "proof kernel",
    "anti-wireheading", "DOC_INDEX", "autonomous publishing", "cypherpunk2048",
]

FEATURED = dict(
    file=Path("gfx/jpg/THOTH.jpg"),
    alt="THOTH — the scribe; mindX chronicles its own evolution",
    caption="THOTH, the scribe: mindX now reads its own public history and writes the record.",
    title="thoth-milestone",
)


def _mime(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


async def _upload(client: httpx.AsyncClient, spec: dict):
    path: Path = spec["file"]
    if not path.exists():
        print(f"[media] MISSING on disk: {path}")
        return None
    with path.open("rb") as fh:
        files = {"file": (path.name, fh, _mime(path))}
        data = {"alt_text": spec["alt"], "caption": spec.get("caption", ""),
                "title": spec.get("title", path.stem)}
        resp = await client.post(f"{WP_AGENT_URL}/media", files=files, data=data)
    if resp.status_code >= 400:
        print(f"[media] {path.name} FAILED {resp.status_code}: {resp.text[:200]}")
        return None
    d = resp.json()
    print(f"[media] {path.name} -> id={d['media_id']} url={d['url']}")
    return d["media_id"], d["url"]


def _build_body(md: str) -> str:
    lines = md.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return _render_md("\n".join(lines).lstrip("\n"))


async def main() -> int:
    if not ARTICLE.exists():
        print(f"[fatal] article missing: {ARTICLE}")
        return 1

    agent = await AuthorAgent.get_instance()

    async with httpx.AsyncClient(timeout=60.0) as client:
        feat = await _upload(client, FEATURED)
    featured_id, featured_url = (feat or (None, None))

    html = _build_body(ARTICLE.read_text())
    print(f"[body] rendered HTML length={len(html)} chars")

    schema_article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": TITLE,
        "description": EXCERPT,
        "image": featured_url or "",
        "author": {"@type": "Organization", "name": "mindX", "url": "https://mindx.pythai.net"},
        "publisher": {"@type": "Organization", "name": "rage.pythai.net", "url": "https://rage.pythai.net"},
        "keywords": ", ".join(SEO_KEYWORDS),
    }

    res = await agent.publish_to_rage(
        title=TITLE,
        content_html=html,
        status="draft",  # DRAFT — prototype, staged for human review
        post_id=759,      # UPDATE the existing post in place (preserve URL/slug)
        slug=SLUG,
        excerpt=EXCERPT,
        featured_media=featured_id,
        auto_featured_image=False,
        seo_description=EXCERPT,
        seo_keywords=SEO_KEYWORDS,
        og_title=TITLE,
        og_description=EXCERPT,
        og_image_url=featured_url,
        twitter_card="summary_large_image",
        schema_article=schema_article,
        topic="milestone",
        meta={"_mindx_trigger_kind": "milestone",
              "_mindx_trigger_id": "milestone:author-agent-github-awareness"},
    )
    print(f"[publish] -> {res}")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
