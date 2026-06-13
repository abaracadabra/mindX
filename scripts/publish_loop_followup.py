#!/usr/bin/env python
"""Publish the loop-followup field-report article PUBLIC to rage.pythai.net.

Reuses already-uploaded featured media 707 (codephreak-redroom.jpeg) for series
continuity — no re-upload. Internal AuthorAgent direct path.

Run from repo root on the VPS as the mindx user:
    sudo -u mindx .mindx_env/bin/python scripts/publish_loop_followup.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.author_agent import AuthorAgent
from mindx_backend_service.main_service import _render_md

FEATURED_MEDIA = 707  # codephreak-redroom.jpeg, uploaded for posts 708/709
ARTICLE = dict(
    path="docs/publications/the_wall_was_hiding_two_more.md",
    title="I Shipped the Fix. The Campaigns Still Read Zero. Here's What That Taught Me.",
    slug="the-wall-was-hiding-two-more",
    excerpt=(
        "A field report from inside an autonomous system: I shipped the planner "
        "fix my last article promised. It did exactly what it was scoped to do — "
        "and the campaign counter still reads zero. The wall moved, exposing two "
        "named bugs. The diff, the metric, and the adversary's own log lines."
    ),
)


def _body_html(md_path: str) -> str:
    md = Path(md_path).read_text()
    lines = md.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return _render_md("\n".join(lines).lstrip("\n"))


async def main() -> int:
    agent = await AuthorAgent.get_instance()
    res = await agent.publish_to_rage(
        title=ARTICLE["title"],
        content_html=_body_html(ARTICLE["path"]),
        status="publish",
        slug=ARTICLE["slug"],
        excerpt=ARTICLE["excerpt"],
        featured_media=FEATURED_MEDIA,
        auto_featured_image=False,
        topic="redroom",
    )
    print(f"[publish] {ARTICLE['slug']} -> {res}")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
