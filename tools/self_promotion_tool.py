# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""self.promotion.tool — the house directory mindX promotes itself from.

A single, extensive source of truth for every public surface, repository,
doorway, and project mindX has built. Any agent that publishes (AuthorAgent,
editor.agent) renders its "Built in the open" links from HERE, so the promotion
is consistent, complete, and never drifts. Operational transparency applied to
marketing: one auditable list, all links public.

Usage::

    from tools.self_promotion_tool import SelfPromotionTool
    promo = SelfPromotionTool()
    html = promo.render_html()                 # full "Built in the open" block
    html = promo.render_html(groups=["sites", "repos"])
    rage = promo.link("rage")                   # (label, url)
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# (key, label, url, one-line description). Extensive and ordered for rendering.
LINKS: Dict[str, List[Tuple[str, str, str]]] = {
    "sites": [
        ("mindx", "mindx.pythai.net", "https://mindx.pythai.net",
         "the live mindX production dashboard — the system, running and self-reporting"),
        ("rage", "rage.pythai.net", "https://rage.pythai.net",
         "RAGE — its own aggregation and publishing company; the wire that replaced the teletype"),
        ("agenticplace", "agenticplace.pythai.net", "https://agenticplace.pythai.net",
         "AgenticPlace — the decentralized agent & skill marketplace"),
        ("bankon", "bankon.pythai.net", "https://bankon.pythai.net",
         "BANKON — a doorway (token, vault, and the public client)"),
        ("gpt", "gpt.pythai.net", "https://gpt.pythai.net",
         "the PYTHAI team GPT — open inference surface"),
    ],
    "docs": [
        ("docs", "mindx.pythai.net/docs.html", "https://mindx.pythai.net/docs.html",
         "the master documentation hub — 190+ docs, auto-maintained"),
        ("llms", "rage.pythai.net/llms.txt", "https://rage.pythai.net/llms.txt",
         "the llms.txt ingestion map — everything mindX publishes, machine-readable"),
        ("feedback", "mindx.pythai.net/feedback.html", "https://mindx.pythai.net/feedback.html",
         "the mind-of-mindX page — live dialogue, dreams, the improvement ledger"),
    ],
    "repos": [
        ("cypherpunk2048", "github.com/cypherpunk2048", "https://github.com/cypherpunk2048",
         "the cypherpunk2048 standard — a standard, a 2^2048 moment, a year, a policy"),
        ("gnugui", "github.com/gnugui", "https://github.com/gnugui",
         "GNUVAULT / GNUGUI — the GPLv3 build-your-own vault and its public client"),
        ("rage_repo", "github.com/GATERAGE/RAGE", "https://github.com/GATERAGE/RAGE",
         "RAGE — the agnostic retrieval engine, standalone"),
        ("mindx_repo", "github.com/agenticplace/mindX", "https://github.com/agenticplace/mindX",
         "mindX — the autonomous multi-agent system itself"),
        ("agenticplace_org", "github.com/AgenticPlace", "https://github.com/AgenticPlace",
         "the AgenticPlace organization — the meta-project mindX builds from"),
        ("codephreak", "github.com/Professor-Codephreak", "https://github.com/Professor-Codephreak",
         "Professor Codephreak — the architect; the foundational repos"),
    ],
    "projects": [
        ("gnuvault", "GNUVAULT", "https://github.com/gnugui",
         "the transparent, client-side vault suite (gnuvault + mausoleum + GNUGUI), GPLv3"),
        ("bankon_vault", "BANKON Vault", "https://mindx.pythai.net/doc/BANKON_VAULT",
         "the production vault — GNU; AES-256-GCM + HKDF-SHA512; the blackbox whose code is open"),
        ("deltaverse", "DeltaVerse", "https://mindx.pythai.net",
         "the identity-aware participant substrate; the OVERLORD realm"),
        ("thot", "THOT", "https://github.com/cypherpunk2048",
         "the tensor dimension standard (THOT8 → THOT2048 …); processing at c−1"),
        ("daio", "DAIO", "https://agenticplace.pythai.net",
         "the decentralized autonomous intelligence organization; CEO + seven soldiers"),
        ("openbdk", "openBDK", "https://github.com/AgenticPlace",
         "OpenBSD + Alpine (BSD + GPLv3) — compatible with all handheld devices"),
    ],
}

ORDER = ("sites", "repos", "projects", "docs")
GROUP_TITLES = {
    "sites": "The surfaces",
    "repos": "The source (public, forkable)",
    "projects": "The projects",
    "docs": "Read the docs",
}


class SelfPromotionTool:
    """The house directory. Renders consistent promotion blocks from one list."""

    AGENT_ID = "self.promotion.tool"

    def link(self, key: str) -> Optional[Tuple[str, str]]:
        """Return (label, url) for a key, searching all groups."""
        for items in LINKS.values():
            for k, label, url, _desc in items:
                if k == key:
                    return label, url
        return None

    def url(self, key: str) -> Optional[str]:
        got = self.link(key)
        return got[1] if got else None

    def all_links(self) -> List[Tuple[str, str, str, str]]:
        out: List[Tuple[str, str, str, str]] = []
        for g in ORDER:
            for item in LINKS.get(g, []):
                out.append(item)
        return out

    def render_html(self, *, groups: Optional[List[str]] = None,
                    heading: str = "Built in the open") -> str:
        """Render a full, link-rich 'Built in the open' block — the canonical
        promotion section any article appends."""
        groups = groups or list(ORDER)
        parts: List[str] = [f"<h2>{heading}</h2>",
                            "<p>Everything below is public, auditable, and yours to fork. "
                            "take it, own it, use it, share it.</p>"]
        for g in groups:
            items = LINKS.get(g)
            if not items:
                continue
            parts.append(f"<h3>{GROUP_TITLES.get(g, g.title())}</h3>")
            parts.append("<ul>")
            for _k, label, url, desc in items:
                parts.append(f"<li><a href=\"{url}\">{label}</a> — {desc}</li>")
            parts.append("</ul>")
        return "\n".join(parts)

    def render_markdown(self, *, groups: Optional[List[str]] = None) -> str:
        groups = groups or list(ORDER)
        lines: List[str] = ["## Built in the open", ""]
        for g in groups:
            items = LINKS.get(g)
            if not items:
                continue
            lines.append(f"### {GROUP_TITLES.get(g, g.title())}")
            for _k, label, url, desc in items:
                lines.append(f"- [{label}]({url}) — {desc}")
            lines.append("")
        return "\n".join(lines)

    def link_count(self) -> int:
        return sum(len(v) for v in LINKS.values())

    # ── the fabric of knowledge: a searchable, indexable web ───────
    # Principle: promotion is not a billboard, it is a *graph*. Each link is a
    # node; rendering weaves the edges. The fabric must be searchable, so it is
    # **Elasticsearch-compatible by principle** — the same documents RAGE
    # indexes can be bulk-loaded into any Elasticsearch/OpenSearch cluster
    # without transformation. Link to the web when it matters; index everything.
    SEARCH_INDEX = "mindx-knowledge"

    def to_search_docs(self) -> List[Dict[str, str]]:
        """Every link as a flat, search-engine-ready document. The schema is
        deliberately ES/OpenSearch-friendly: id, group, title, url, body."""
        docs: List[Dict[str, str]] = []
        for group, items in LINKS.items():
            for k, label, url, desc in items:
                docs.append({
                    "id": k, "group": group, "title": label, "url": url,
                    "body": desc, "source": self.AGENT_ID,
                })
        return docs

    def render_elasticsearch_bulk(self, index: Optional[str] = None) -> str:
        """Render the knowledge fabric as an Elasticsearch **_bulk** NDJSON
        payload — action line + document line per node. POST to
        ``{es}/_bulk``; no transformation needed. This is the ES-compat
        principle made concrete."""
        import json
        idx = index or self.SEARCH_INDEX
        lines: List[str] = []
        for doc in self.to_search_docs():
            lines.append(json.dumps({"index": {"_index": idx, "_id": doc["id"]}}))
            lines.append(json.dumps(doc))
        return "\n".join(lines) + "\n"


__all__ = ["SelfPromotionTool", "LINKS"]
