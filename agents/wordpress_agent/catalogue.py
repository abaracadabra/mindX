# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""Publication catalogue + llms.txt interaction for the wordpress.tool.

Two responsibilities, both *read-side* (this module never publishes):

1. **Catalogue** — a complete, deterministic index of every publishing on a
   target WordPress site (here: rage.pythai.net). Built by paginating the WP
   REST API; normalized into a stable shape AuthorAgent and the diagnostics
   surfaces can consume.

2. **llms.txt interaction** — fetch the live ``/llms.txt`` ingestion map and
   render an up-to-date one *from the catalogue* (published posts only), per
   the llmstxt.org spec, so the two can be diffed. Rendering is a pure,
   byte-stable function of the catalogue — re-running on the same input yields
   an identical file (good for IndexNow / cache invalidation).

Boundary note: per prior operator direction, the canonical ``/llms.txt`` on
rage.pythai.net is *served by the Hostinger Tools Plugin*, not POSTed by the
wordpress.agent. This module therefore **reads** the live file and **renders**
a candidate from the catalogue (for diff/handoff) — it does not push it.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

# Statuses an operator cares about for a *complete* index. Non-public statuses
# require authentication on the WP REST call.
ALL_INDEXED_STATUSES = ("publish", "future", "draft", "pending", "private")


@dataclass(slots=True, frozen=True)
class PostRecord:
    """One publishing on the target, normalized from the WP REST payload."""

    id: int
    status: str
    slug: str
    title: str
    link: str
    date_gmt: str
    modified_gmt: str
    excerpt: str = ""

    @classmethod
    def from_wp(cls, d: dict[str, Any]) -> "PostRecord":
        def _rendered(v: Any) -> str:
            if isinstance(v, dict):
                return str(v.get("rendered", "")).strip()
            return str(v or "").strip()

        # Strip HTML tags + collapse whitespace for a clean one-line excerpt.
        import re

        raw_excerpt = _rendered(d.get("excerpt"))
        clean_excerpt = re.sub(r"<[^>]+>", "", raw_excerpt)
        clean_excerpt = re.sub(r"\s+", " ", clean_excerpt).strip()
        return cls(
            id=int(d.get("id", 0)),
            status=str(d.get("status", "")),
            slug=str(d.get("slug", "")),
            title=_rendered(d.get("title")),
            link=str(d.get("link", "")),
            date_gmt=str(d.get("date_gmt", "")),
            modified_gmt=str(d.get("modified_gmt", "")),
            excerpt=clean_excerpt,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "slug": self.slug,
            "title": self.title,
            "link": self.link,
            "date_gmt": self.date_gmt,
            "modified_gmt": self.modified_gmt,
            "excerpt": self.excerpt,
        }


@dataclass(slots=True)
class Catalogue:
    """Complete index of all publishings on a target."""

    host: str
    generated_gmt: str
    posts: list[PostRecord] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {"total": len(self.posts)}
        for p in self.posts:
            out[p.status] = out.get(p.status, 0) + 1
        return out

    def published(self) -> list[PostRecord]:
        # Newest first, published only — the public ingestion surface.
        pub = [p for p in self.posts if p.status == "publish"]
        return sorted(pub, key=lambda p: p.date_gmt, reverse=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "generated_gmt": self.generated_gmt,
            "counts": self.counts,
            "posts": [p.to_dict() for p in sorted(self.posts, key=lambda p: p.date_gmt, reverse=True)],
        }


def render_catalogue_llms_txt(cat: Catalogue) -> str:
    """Render an llms.txt ingestion map from the catalogue (published posts only).

    Deterministic: same catalogue → byte-identical output. Follows the
    llmstxt.org shape — H1 host, a blockquote summary, then an ``## Posts``
    section of ``- [Title](url): excerpt`` lines.
    """
    lines: list[str] = []
    lines.append(f"# {cat.host}")
    lines.append("")
    lines.append(
        "> mindX-published content on "
        f"{cat.host} — signed, first-person-as-mindX essays in the cypherpunk "
        "tradition. This map indexes every public post for LLM ingestion "
        "(llmstxt.org convention)."
    )
    lines.append("")
    lines.append("## Posts")
    for p in cat.published():
        suffix = f": {p.excerpt}" if p.excerpt else ""
        lines.append(f"- [{p.title}]({p.link}){suffix}")
    lines.append("")
    lines.append("## Optional")
    lines.append("- [mindX live diagnostics](https://mindx.pythai.net/)")
    lines.append("- [mindX docs](https://mindx.pythai.net/)")
    lines.append("")
    return "\n".join(lines) + "\n"


def diff_llms_txt(live_text: str, rendered_text: str) -> dict[str, Any]:
    """Compare the live /llms.txt against the catalogue-rendered candidate.

    Returns a small summary: whether they match and the set of post links
    present in one but not the other (the actionable delta for the operator).
    """
    import re

    def _links(text: str) -> set[str]:
        return set(re.findall(r"\]\((https?://[^)]+)\)", text or ""))

    live_links = _links(live_text)
    rendered_links = _links(rendered_text)
    return {
        "in_sync": (live_text or "").strip() == (rendered_text or "").strip(),
        "missing_from_live": sorted(rendered_links - live_links),
        "stale_in_live": sorted(live_links - rendered_links),
        "live_link_count": len(live_links),
        "rendered_link_count": len(rendered_links),
    }


def host_from_base_url(base_url: str) -> str:
    return urlparse(base_url).netloc or base_url


__all__ = [
    "ALL_INDEXED_STATUSES",
    "PostRecord",
    "Catalogue",
    "render_catalogue_llms_txt",
    "diff_llms_txt",
    "host_from_base_url",
]
