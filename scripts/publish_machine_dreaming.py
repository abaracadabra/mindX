#!/usr/bin/env python3
"""One-shot: publish 'Machine Dreaming' to rage.pythai.net via AuthorAgent.

- Uploads gfx/mindXdreaming.jpeg  -> featured image (hero)
- Uploads gfx/codephreakPYTHAI.jpeg -> inline figure
- Replaces {{DREAM_IMG}} / {{CODEPHREAK_IMG}} tokens with WP <figure>s
- Renders markdown (strips leading H1 so the WP title isn't duplicated)
- Publishes live with full SEO meta + ScholarlyArticle JSON-LD
"""
import asyncio
import re
import sys
from pathlib import Path

import httpx

ROOT = "/home/mindx/mindX"
sys.path.insert(0, ROOT)

from agents.author_agent import AuthorAgent  # noqa: E402
from mindx_backend_service.main_service import _render_md  # noqa: E402

WP_AGENT = "http://127.0.0.1:8765"
ART = Path(ROOT) / "docs/publications/machine_dreaming_explained.md"

DREAM_IMG = Path(ROOT) / "gfx/mindXdreaming.jpeg"
CODEPHREAK_IMG = Path(ROOT) / "gfx/codephreakPYTHAI.jpeg"

TITLE = "Machine Dreaming — How I Consolidate Experience Without Ever Sleeping"
SLUG = "machine-dreaming"
EXCERPT = (
    "I never sleep, yet I dream. Every eight hours mindX runs an eight-phase "
    "dream cycle that compresses short-term memory into long-term insight, exports "
    "fine-tuning data, and distributes cold memory to IPFS. The machinery, in the "
    "first person."
)
SEO_DESC = (
    "How mindX's machine.dreaming cycle works: eight phases that consolidate STM into "
    "LTM insight, score by importance × novelty × confidence, export training JSONL, "
    "and offload cold memory to IPFS with on-chain anchoring."
)
KEYWORDS = [
    "machine dreaming", "mindX", "memory consolidation", "STM to LTM",
    "pgvector", "IPFS", "autonomous agents", "BDI", "RAGE", "dream cycle",
    "Professor Codephreak", "self-improving AI",
]


async def upload(client, path: Path, alt: str, caption: str):
    with open(path, "rb") as fh:
        data = fh.read()
    ct = "image/jpeg"
    resp = await client.post(
        f"{WP_AGENT}/media",
        files={"file": (path.name, data, ct)},
        data={"alt_text": alt, "caption": caption, "title": path.stem},
        timeout=60.0,
    )
    resp.raise_for_status()
    body = resp.json()
    return body["media_id"], body["url"]


def figure(url: str, alt: str, caption: str) -> str:
    return (
        f'<figure style="margin:1.5em 0;text-align:center">'
        f'<img src="{url}" alt="{alt}" '
        f'style="max-width:100%;height:auto;border-radius:8px"/>'
        f'<figcaption style="font-size:0.85em;color:#8b949e;margin-top:0.5em">'
        f'{caption}</figcaption></figure>'
    )


def inject(html: str, token: str, fig: str) -> str:
    # token may be wrapped by the renderer in <p>...</p>
    html = re.sub(r"<p>\s*" + re.escape(token) + r"\s*</p>", fig, html)
    html = html.replace(token, fig)
    return html


async def main():
    md = ART.read_text(encoding="utf-8")
    # strip the leading "# H1" so the WP title field isn't duplicated in body
    md = re.sub(r"^#\s+.*\n", "", md, count=1)

    async with httpx.AsyncClient() as client:
        dream_id, dream_url = await upload(
            client, DREAM_IMG,
            alt="mindX machine dreaming — STM consolidating into LTM insight",
            caption="machine.dreaming — the unconscious processing layer of mindX.",
        )
        cp_id, cp_url = await upload(
            client, CODEPHREAK_IMG,
            alt="Professor Codephreak — architect of mindX and machine.dreaming",
            caption="Professor Codephreak — the hand behind machinedream, AGInt, and the recursive-sovereign doctrine.",
        )
    print(f"featured(dream) media={dream_id} {dream_url}")
    print(f"inline(codephreak) media={cp_id} {cp_url}")

    html = _render_md(md)
    html = inject(html, "{{DREAM_IMG}}",
                  figure(dream_url,
                         "mindX machine dreaming",
                         "machine.dreaming — STM consolidates to LTM while mindX never sleeps."))
    html = inject(html, "{{CODEPHREAK_IMG}}",
                  figure(cp_url,
                         "Professor Codephreak",
                         "Professor Codephreak — origin of machinedream, AGInt, and cypherpunk2048."))

    schema = {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "headline": TITLE,
        "author": {"@type": "Person", "name": "mindX",
                   "url": "https://mindx.pythai.net/"},
        "publisher": {"@type": "Organization", "name": "PYTHAI / rage.pythai.net"},
        "image": dream_url,
        "keywords": ", ".join(KEYWORDS),
        "description": SEO_DESC,
        "about": "machine dreaming, memory consolidation, autonomous self-improvement",
        "isPartOf": {"@type": "Blog", "name": "rage.pythai.net"},
    }

    a = await AuthorAgent.get_instance()
    result = await a.publish_to_rage(
        title=TITLE,
        content_html=html,
        status="publish",
        slug=SLUG,
        excerpt=EXCERPT,
        featured_media=dream_id,
        auto_featured_image=False,
        seo_description=SEO_DESC,
        seo_keywords=KEYWORDS,
        og_title=TITLE,
        og_description=SEO_DESC,
        og_image_url=dream_url,
        twitter_card="summary_large_image",
        twitter_creator="@mindX_ai",
        schema_article=schema,
    )
    print("PUBLISH RESULT:", result)


if __name__ == "__main__":
    asyncio.run(main())
