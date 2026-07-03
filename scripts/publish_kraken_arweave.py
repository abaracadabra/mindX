#!/usr/bin/env python
"""One-shot publisher: the Kraken → Arweave Canadian onboarding field report.

Canonical internal AuthorAgent direct-Python path. Uploads SEVERAL BTC "66666"
graphics from /gfx/ to rage.pythai.net: ``codephreakBTC666666ridingtherails``
becomes the featured image + og:image, and the other two are embedded inline as
``<figure>`` blocks at section breaks. Publishes PUBLIC (status="publish").

Invoke from the repo root on the VPS as the mindx user:
    sudo -u mindx .mindx_env/bin/python scripts/publish_kraken_arweave.py
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from agents.author_agent import AuthorAgent
from mindx_backend_service.main_service import _render_md

WP_AGENT_URL = os.environ.get("MINDX_WORDPRESS_AGENT_URL", "http://127.0.0.1:8765")

ARTICLE = Path("docs/blockchain/kraken-canada-200-to-arweave.md")
TITLE = "From $200 to Arweave: How a Canadian Got Into Crypto in an Afternoon"
SLUG = "kraken-canada-200-to-arweave"
EXCERPT = (
    "A field report: $200 CAD from a CIBC account to holding Arweave (AR) on "
    "Kraken in an afternoon — free Interac e-Transfer in, ~1% to trade, no "
    "exit tax. The honest accounting of Canadian crypto onboarding, fees, "
    "limits, and where the real liquidity hides."
)
SEO_DESCRIPTION = (
    "How a Canadian went from a CIBC account to holding Arweave on Kraken in an "
    "afternoon — free e-Transfer in, ~1% to trade, only network fees out."
)
SEO_KEYWORDS = [
    "Kraken Canada", "buy Arweave Canada", "AR token", "crypto onboarding Canada",
    "Interac e-Transfer Kraken", "CIBC crypto", "Kraken Pro fees",
    "Moonbeam GLMR Canada", "Injective INJ Canada", "Kraken referral code",
    "Canadian crypto exchange", "regulated crypto Canada",
]

# Featured image (top) + two inline figures. "Several" BTC 66666 graphics.
FEATURED = dict(
    file=Path("gfx/codephreakBTC666666ridingtherails.jpeg"),
    alt="Riding the rails from Canadian dollars into crypto on Kraken",
    caption="Riding the rails — CIBC to Arweave in an afternoon.",
    title="codephreakBTC666666ridingtherails",
)
INLINE = [
    dict(
        file=Path("gfx/codephreakBTC666666.jpeg"),
        alt="Bitcoin dipping and recovering — the two-doors fee lesson",
        caption="Same house, two doors: the basic app charges ~1%, Kraken Pro starts at 0.25%/0.40%.",
        title="codephreakBTC666666",
        # Inject the figure immediately BEFORE this heading line (verbatim).
        anchor="## The Basic app vs. Kraken Pro: same login, very different prices",
    ),
    dict(
        file=Path("gfx/BTC66666.jpeg"),
        alt="Bitcoin price climbing to all-time-high on a green candlestick chart",
        caption="The reason to use a regulated exchange at all: the liquidity is here.",
        title="BTC66666",
        anchor="## Why bother with an exchange at all? Because the liquidity is here.",
    ),
]


async def _upload(client: httpx.AsyncClient, spec: dict) -> Optional[Tuple[int, str]]:
    """POST an image to wordpress.agent /media. Returns (media_id, absolute_url)."""
    path: Path = spec["file"]
    if not path.exists():
        print(f"[media] MISSING on disk: {path}")
        return None
    with path.open("rb") as fh:
        files = {"file": (path.name, fh, "image/jpeg")}
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
    """Drop leading H1, inject inline figures before their anchor headings, render."""
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
        fig = _figure_html(url, spec["alt"], spec.get("caption", ""))
        body = body.replace(anchor, fig + anchor, 1)
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
            print("[fatal] featured image upload failed; aborting (need public graphic).")
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
        "author": {"@type": "Person", "name": "Professor Codephreak"},
        "publisher": {
            "@type": "Organization",
            "name": "rage.pythai.net",
            "url": "https://rage.pythai.net",
        },
        "keywords": ", ".join(SEO_KEYWORDS),
    }

    res = await agent.publish_to_rage(
        title=TITLE,
        content_html=html,
        status="publish",  # PUBLIC
        slug=SLUG,
        excerpt=EXCERPT,
        featured_media=featured_id,
        auto_featured_image=False,  # we chose the graphic explicitly
        seo_description=SEO_DESCRIPTION,
        seo_keywords=SEO_KEYWORDS,
        og_title=TITLE,
        og_description=SEO_DESCRIPTION,
        og_image_url=featured_url,
        twitter_card="summary_large_image",
        schema_article=schema_article,
        topic="bitcoin",
    )
    print(f"[publish] -> {res}")
    return 0 if res else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
