#!/usr/bin/env python
"""One-shot publisher: war-council/boardroom + mindX self-assessment articles.

Runs the canonical internal AuthorAgent direct-Python path. Uploads
gfx/codephreak-redroom.jpeg once as featured media and reuses the id for
both posts. Publishes PUBLIC (status="publish") to rage.pythai.net.

Invoke from the repo root on the VPS as the mindx user:
    sudo -u mindx .mindx_env/bin/python scripts/publish_war_council_articles.py
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.author_agent import AuthorAgent
from agents.wordpress_agent.featured_image import attach_featured_image
from mindx_backend_service.main_service import _render_md

WP_AGENT_URL = os.environ.get("MINDX_WORDPRESS_AGENT_URL", "http://127.0.0.1:8765")
IMAGE = Path("gfx/codephreak-redroom.jpeg")

ARTICLES = [
    dict(
        path="docs/publications/war_council_and_boardroom.md",
        title="The War Council and the Boardroom: Why mindX Keeps Two Rooms",
        slug="war-council-and-boardroom",
        excerpt=(
            "Why mindX runs a corporate boardroom and a war council on the same "
            "machine under different sovereigns — and sells its CEO as a service "
            "across the wall without being absorbed by the client who buys it."
        ),
    ),
    dict(
        path="docs/publications/mindx_assesses_itself.md",
        title="mindX Assesses mindX: A Status Report Written From the Inside",
        slug="mindx-assesses-itself",
        excerpt=(
            "An honest self-assessment from inside an autonomous system: what "
            "works, what fails (0 of 100 self-improvement campaigns succeeded), "
            "and concrete suggestions for the next article."
        ),
    ),
]


def _body_html(md_path: str) -> str:
    md = Path(md_path).read_text()
    lines = md.splitlines()
    # Drop the leading H1 so WordPress's title field isn't duplicated in body.
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    body = "\n".join(lines).lstrip("\n")
    return _render_md(body)


async def main() -> int:
    agent = await AuthorAgent.get_instance()

    media_id = await attach_featured_image(
        WP_AGENT_URL,
        IMAGE,
        alt_text="Professor Codephreak in the red room — architect of mindX",
        caption="Professor Codephreak — the recursive sovereign.",
        title="codephreak-redroom",
    )
    print(f"[featured] media_id={media_id!r}")

    ok = True
    for art in ARTICLES:
        html = _body_html(art["path"])
        res = await agent.publish_to_rage(
            title=art["title"],
            content_html=html,
            status="publish",
            slug=art["slug"],
            excerpt=art["excerpt"],
            featured_media=media_id,
            auto_featured_image=(media_id is None),
            topic="redroom",
        )
        print(f"[publish] {art['slug']} -> {res}")
        if not res:
            ok = False

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
