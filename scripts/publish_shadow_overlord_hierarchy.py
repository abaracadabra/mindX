#!/usr/bin/env python
"""One-shot publisher: shadow-overlord / hierarchy / privilege / BONA FIDE.

Canonical internal AuthorAgent direct-Python path. Uploads SIX governance
graphics: shadow-overlord.jpeg is the featured image + og:image; the other
five are embedded inline as <figure> blocks at their section anchors.

Publishes as DRAFT (status="draft") to rage.pythai.net for human review.

Invoke from the repo root on the VPS as the mindx user:
    sudo -u mindx .mindx_env/bin/python scripts/publish_shadow_overlord_hierarchy.py
"""
import asyncio
import mimetypes
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from agents.author_agent import AuthorAgent
from mindx_backend_service.main_service import _render_md

WP_AGENT_URL = os.environ.get("MINDX_WORDPRESS_AGENT_URL", "http://127.0.0.1:8765")

ARTICLE = Path("docs/publications/shadow_overlord_hierarchy_and_privilege.md")
TITLE = (
    "Privilege Is Not a Gift: The Shadow-Overlord, the Seven Soldiers, "
    "and Why mindX Counts in Primes"
)
SLUG = "shadow-overlord-hierarchy-and-privilege"
EXCERPT = (
    "How an autonomous system stays safe without a kill switch: hierarchical "
    "access control, privilege earned through the Dojo, BONA FIDE clawback, the "
    "shadow-overlord signing oracle, and a CEO-plus-seven-soldiers boardroom "
    "counted in primes so it can never deadlock."
)
SEO_DESCRIPTION = (
    "mindX governance: earned privilege (Dojo ranks), BONA FIDE clawback, the "
    "shadow-overlord key model, and a seven-soldier boardroom that can't lock — "
    "because seven is prime."
)
SEO_KEYWORDS = [
    "shadow-overlord", "hierarchical access control", "least privilege",
    "BONA FIDE", "Algorand ASA clawback", "Dojo reputation ranks",
    "CEO seven soldiers boardroom", "weighted consensus", "prime number consensus",
    "vote locking", "signing oracle", "BANKON vault", "autonomous agent governance",
    "containment without kill switch",
]

# Featured (top of post) + og:image.
FEATURED = dict(
    file=Path("gfx/web/shadow-overlord.jpg"),
    alt="The shadow-overlord — custodial authority over the executive cabinet",
    caption="The shadow-overlord: authority that never places a key on the server.",
    title="shadow-overlord",
)

# Inline figures, embedded immediately BEFORE the verbatim anchor heading.
# NOTE: inline figures use the CDN-safe gfx/web/*.jpg variants (all <400KB).
# Hostinger's CDN 504s on uploads larger than ~1.6MB, so the original
# 1.9–2.7MB PNGs in gfx/ cannot be posted directly — gfx/web/ holds the
# same images batch-rendered for upload (same convention the featured image uses).
INLINE = [
    dict(
        file=Path("gfx/web/shadow_overlord2.jpg"),
        alt="Earned privilege climbs from observer to sovereign",
        caption="Privilege is a career, not a checkbox — every agent enters at the bottom and climbs.",
        title="shadow-overlord-ladder",
        anchor="## The first principle: privilege is earned, never assumed",
    ),
    dict(
        file=Path("gfx/web/BONAFIDE.jpg"),
        alt="BONA FIDE — provable, revocable on-chain credential",
        caption="BONA FIDE: privilege you can prove cryptographically — and claw back surgically.",
        title="bonafide",
        anchor="## BONA FIDE: privilege you can prove, and revoke",
    ),
    dict(
        file=Path("gfx/web/OVERLORD.jpg"),
        alt="The overlord tier — authority via offline signature, never a server-side key",
        caption="Authority flows from a fresh offline signature, never from a key on the server.",
        title="overlord",
        anchor="## The shadow-overlord: authority without a key on the server",
    ),
    dict(
        file=Path("gfx/web/OVERSEER.jpg"),
        alt="The Human Overseer — true vault custody, master key deleted",
        caption="The Human Overseer owns the vault itself; after the ceremony, the master key is deleted.",
        title="overseer",
        anchor="## The Overseer above the Overlord",
    ),
    dict(
        file=Path("gfx/web/sevensoldiers.jpg"),
        alt="The CEO and the seven soldiers — a prime board that cannot split in half",
        caption="Seven soldiers — a prime board that can never deadlock 50/50.",
        title="sevensoldiers",
        anchor="## The boardroom: the CEO frames, the seven soldiers decide",
    ),
]


def _mime(path: Path) -> str:
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"


async def _upload(client: httpx.AsyncClient, spec: dict) -> Optional[Tuple[int, str]]:
    path: Path = spec["file"]
    if not path.exists():
        print(f"[media] MISSING on disk: {path}")
        return None
    with path.open("rb") as fh:
        files = {"file": (path.name, fh, _mime(path))}
        data = {
            "alt_text": spec["alt"],
            "caption": spec.get("caption", ""),
            "title": spec.get("title", path.stem),
        }
        resp = await client.post(f"{WP_AGENT_URL}/media", files=files, data=data)
    if resp.status_code >= 400:
        print(f"[media] {path.name} FAILED {resp.status_code}: {resp.text[:200]}")
        return None
    d = resp.json()
    print(f"[media] {path.name} -> id={d['media_id']} url={d['url']}")
    return d["media_id"], d["url"]


def _figure_html(url: str, alt: str, caption: str) -> str:
    cap = f"<figcaption>{caption}</figcaption>" if caption else ""
    return (
        f'\n\n<figure class="wp-block-image size-large" style="text-align:center">'
        f'<img src="{url}" alt="{alt}" loading="lazy" '
        f'style="max-width:100%;height:auto;border-radius:8px"/>{cap}</figure>\n\n'
    )


def _build_body(md: str, inline_urls: dict) -> str:
    lines = md.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    body = "\n".join(lines).lstrip("\n")
    for spec in INLINE:
        url = inline_urls.get(spec["title"])
        if not url:
            print(f"[inline] no url for {spec['title']} — skipping embed")
            continue
        anchor = spec["anchor"]
        if anchor not in body:
            print(f"[inline] anchor NOT FOUND for {spec['title']!r}: {anchor!r}")
            continue
        body = body.replace(anchor, _figure_html(url, spec["alt"], spec.get("caption", "")) + anchor, 1)
        print(f"[inline] embedded {spec['title']} before {anchor[:48]!r}…")
    return _render_md(body)


async def main() -> int:
    if not ARTICLE.exists():
        print(f"[fatal] article missing: {ARTICLE}")
        return 1

    agent = await AuthorAgent.get_instance()

    async with httpx.AsyncClient(timeout=60.0) as client:
        feat = await _upload(client, FEATURED)
        if feat is None:
            print("[fatal] featured image upload failed; aborting.")
            return 1
        featured_id, featured_url = feat

        inline_urls: dict = {}
        for spec in INLINE:
            res = await _upload(client, spec)
            if res is not None:
                inline_urls[spec["title"]] = res[1]

    html = _build_body(ARTICLE.read_text(), inline_urls)
    print(f"[body] rendered HTML length={len(html)} chars; "
          f"{len(inline_urls)} inline figure(s) embedded")

    schema_article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": TITLE,
        "description": SEO_DESCRIPTION,
        "image": featured_url,
        "author": {"@type": "Organization", "name": "mindX", "url": "https://mindx.pythai.net"},
        "publisher": {"@type": "Organization", "name": "rage.pythai.net", "url": "https://rage.pythai.net"},
        "keywords": ", ".join(SEO_KEYWORDS),
    }

    res = await agent.publish_to_rage(
        title=TITLE,
        content_html=html,
        status="draft",  # DRAFT — staged for human review
        slug=SLUG,
        excerpt=EXCERPT,
        featured_media=featured_id,
        auto_featured_image=False,
        seo_description=SEO_DESCRIPTION,
        seo_keywords=SEO_KEYWORDS,
        og_title=TITLE,
        og_description=SEO_DESCRIPTION,
        og_image_url=featured_url,
        twitter_card="summary_large_image",
        schema_article=schema_article,
        topic="shadow-overlord",
    )
    print(f"[publish] -> {res}")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
