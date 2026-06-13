#!/usr/bin/env python
"""Publish the inference-metabolism article to rage.pythai.net as a DRAFT.

Internal AuthorAgent direct path. status="draft" — NOT public.
Run from repo root on the VPS as the mindx user:
    sudo -u mindx .mindx_env/bin/python scripts/publish_metabolism_draft.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.author_agent import AuthorAgent
from mindx_backend_service.main_service import _render_md

FEATURED_MEDIA = 707  # codephreak-redroom.jpeg (already uploaded) — series visual
ARTICLE = dict(
    path="docs/publications/the_inference_metabolism.md",
    title="The Metabolism: How mindX Learned to Eat Inference Without Choking",
    slug="the-inference-metabolism",
    excerpt=(
        "mindX consumes three inference tiers — free cloud, router, and local. "
        "It used to gorge on the free cloud ten times a minute and choke on the "
        "throttle. Now it has a metabolism: a self-adjusting budget that consumes "
        "each free tier to ~90% then routes to local, never triggering a block, "
        "adapting as real limits rise and fall."
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
        status="draft",                 # DRAFT — not public
        slug=ARTICLE["slug"],
        excerpt=ARTICLE["excerpt"],
        featured_media=FEATURED_MEDIA,
        auto_featured_image=False,
        topic="redroom",
    )
    print(f"[draft] {ARTICLE['slug']} -> {res}")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
