#!/usr/bin/env python
"""One-shot publisher: the DOT/GLMR "undervalued" thesis (Kraken series #2).

Canonical internal AuthorAgent direct-Python path. Featured image is
``gfx/codephreakBTC666666.jpeg`` (operator-selected) + og:image. Publishes
PUBLIC (status="publish") to rage.pythai.net, cross-linked to the prior
Kraken→Arweave field report.

Invoke from the repo root on the VPS as the mindx user:
    sudo -u mindx .mindx_env/bin/python scripts/publish_polkadot_glmr_thesis.py
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

ARTICLE = Path("docs/blockchain/polkadot-glmr-undervalued-thesis-2026.md")
TITLE = (
    "The Mispriced Network: Why I Think Polkadot (DOT) and Moonbeam (GLMR) "
    "Are Undervalued Against Their Own Utility"
)
SLUG = "polkadot-glmr-undervalued-thesis"
EXCERPT = (
    "A thesis, argued from public data: Polkadot shipped a hard supply cap, a "
    "US spot ETF (TDOT), and a finished scaling program in one year — and "
    "Moonbeam (GLMR) handles a fifth of Polkadot's activity for a ~$15M market "
    "cap. Why I think DOT and GLMR are mispriced against their own utility, and "
    "how to access both from Kraken in Canadian dollars."
)
SEO_DESCRIPTION = (
    "Thesis: DOT and Moonbeam (GLMR) look undervalued vs. their utility — hard "
    "cap, TDOT ETF, 21% of Polkadot activity. Accessible on Kraken in CAD."
)
SEO_KEYWORDS = [
    "Polkadot undervalued", "DOT price thesis", "Moonbeam GLMR undervalued",
    "buy DOT Canada", "buy GLMR Canada", "Polkadot 2.1 billion hard cap",
    "TDOT ETF", "Polkadot JAM", "Moonbeam Routed Liquidity", "GLMR tokenomics",
    "Kraken DOT GLMR CAD", "Polkadot 2026", "Moonbeam real world assets",
]

FEATURED = dict(
    file=Path("gfx/codephreakBTC666666.jpeg"),
    alt="The mispriced network — rotating from Bitcoin into undervalued Polkadot and Moonbeam",
    caption="Rotating out of the asset everyone watches and into the utility the market underprices.",
    title="codephreakBTC666666-thesis",
)


async def _upload(client: httpx.AsyncClient, spec: dict) -> Optional[Tuple[int, str]]:
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


def _build_body(md: str) -> str:
    lines = md.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    body = "\n".join(lines).lstrip("\n")
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

    html = _build_body(ARTICLE.read_text())
    print(f"[body] rendered HTML length={len(html)} chars")

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
        auto_featured_image=False,
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
