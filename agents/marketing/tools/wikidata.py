"""
wikidata — Q-item drafting (no submission).

Phase 1: drafts Wikidata Q-item payloads to disk. The Convener manually
submits via WP:AfC after review. Live submission via mwclient/pywikibot is
explicit Phase 2 work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class WikidataClaim:
    property_id: str            # e.g. "P31" (instance of)
    value: str                  # Q-id or string


@dataclass
class WikidataDraft:
    label: str
    description: str
    aliases: List[str] = field(default_factory=list)
    claims: List[WikidataClaim] = field(default_factory=list)
    source_urls: List[str] = field(default_factory=list)
    rationale: str = ""


def render_draft(draft: WikidataDraft) -> Dict[str, object]:
    return {
        "label": draft.label,
        "description": draft.description,
        "aliases": list(draft.aliases),
        "claims": [{"property_id": c.property_id, "value": c.value} for c in draft.claims],
        "source_urls": list(draft.source_urls),
        "rationale": draft.rationale,
    }


def write_draft(draft_dir: Path, draft: WikidataDraft, slug: str) -> Path:
    draft_dir = Path(draft_dir)
    draft_dir.mkdir(parents=True, exist_ok=True)
    path = draft_dir / f"{slug}.json"
    path.write_text(json.dumps(render_draft(draft), indent=2), encoding="utf-8")
    return path


__all__ = ["WikidataClaim", "WikidataDraft", "render_draft", "write_draft"]
