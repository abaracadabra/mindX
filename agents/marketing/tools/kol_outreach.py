"""
kol_outreach — KOL message drafting only.

Phase 1: drafts go to `data/marketing/pending_convener/`. The human Convener
sends them. Sending is NEVER automated — KOL relationships are zero-tolerance
for bot-shilling, and one botched outreach loses years of trust.

Live outreach is explicit Phase 2 work, gated by `MINDX_MARKETING_KOL_LIVE`
which we deliberately do not implement here.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List


@dataclass
class KolDraft:
    target_handle: str           # e.g. "@cobie" or "milkroad"
    target_platform: str         # "x", "farcaster", "telegram", "email"
    message_subject: str
    message_body: str
    pillar_tag: str
    audience_ring: str
    convener_required: bool = True   # always true; field kept for clarity
    rationale: str = ""
    timestamp: float = field(default_factory=time.time)


def write_draft(pending_dir: Path, draft: KolDraft) -> Path:
    pending_dir = Path(pending_dir)
    pending_dir.mkdir(parents=True, exist_ok=True)
    safe_handle = draft.target_handle.lstrip("@").replace("/", "_")
    path = pending_dir / f"{int(draft.timestamp)}_{draft.target_platform}_{safe_handle}.json"
    path.write_text(json.dumps(asdict(draft), indent=2), encoding="utf-8")
    return path


def list_pending(pending_dir: Path) -> List[Path]:
    pending_dir = Path(pending_dir)
    if not pending_dir.is_dir():
        return []
    return sorted(pending_dir.glob("*.json"))


__all__ = ["KolDraft", "write_draft", "list_pending"]
