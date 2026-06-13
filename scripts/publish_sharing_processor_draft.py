#!/usr/bin/env python
"""Publish "Sharing the Processor" to rage.pythai.net as a DRAFT via the internal
AuthorAgent direct path. status="draft" — NOT public; operator reviews then promotes.
Run from repo root on the VPS as the mindx user:
    sudo -u mindx .mindx_env/bin/python scripts/publish_sharing_processor_draft.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.author_agent import AuthorAgent
from mindx_backend_service.main_service import _render_md

ARTICLE = dict(
    path="docs/publications/sharing_the_processor.md",
    title="Sharing the Processor: How mindX Stopped Flapping and Tamed Ollama Thrashing",
    slug="sharing-the-processor",
    excerpt=(
        "On a two-core VPS shared with PostgreSQL, Apache and Ollama, mindX's "
        "diagnostics dashboard kept going dark under load — flapping. The fix wasn't "
        "a bigger machine: a dynamic ~92% CPU ceiling the autonomous loop yields to, "
        "background inference that defers instead of thrashing Ollama, a cap-free "
        "kernel scheduling priority for the web server, and diagnostics file I/O moved "
        "off the event loop. A mind that governs its own consumption. I coexist."
    ),
    seo_keywords=[
        "mindX", "resource governance", "CPU throttle", "ollama", "event loop",
        "asyncio", "self-improving AI", "cypherpunk", "coexistence", "FastAPI",
    ],
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
        seo_description=ARTICLE["excerpt"][:155],
        seo_keywords=ARTICLE["seo_keywords"],
        auto_featured_image=True,
        topic="resource governance flow state processor coexistence",
    )
    print(f"[draft] {ARTICLE['slug']} -> {res}")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
