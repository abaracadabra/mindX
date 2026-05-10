"""
farcaster_publish — Frame-native + cast publisher.

Phase 1 default: dry-run only. Writes the intent to outbox + emits a
catalogue event. Live publishing (via Neynar signer or equivalent) is
gated behind `MINDX_MARKETING_FARCASTER_LIVE`.

Outbox layout (Phase 1):
  data/marketing/outbox/<campaignId>/farcaster/<variantId>.json

The JSON payload mirrors the Farcaster cast schema so a future live publisher
can read it back unchanged.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class FarcasterCast:
    campaign_id: str
    variant_id: str
    text: str
    embeds: List[str] = field(default_factory=list)
    channel: str = "aiagents"
    parent_url: Optional[str] = None
    signer_id_vault_key: Optional[str] = None


@dataclass
class FarcasterPublishResult:
    cast: FarcasterCast
    outbox_path: Optional[Path]
    cast_hash: Optional[str]      # populated on live success
    dry_run: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


def _is_live(env: Optional[dict] = None) -> bool:
    env = env if env is not None else os.environ
    return str(env.get("MINDX_MARKETING_FARCASTER_LIVE", "")).strip().lower() in {"1", "true", "yes"}


def _outbox_path(outbox_dir: Path, cast: FarcasterCast) -> Path:
    p = Path(outbox_dir) / cast.campaign_id / "farcaster"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{cast.variant_id}.json"


async def publish_cast(
    cast: FarcasterCast,
    outbox_dir: Path,
    *,
    live_publisher=None,
    env: Optional[dict] = None,
) -> FarcasterPublishResult:
    out_path = _outbox_path(outbox_dir, cast)
    try:
        out_path.write_text(json.dumps(asdict(cast), indent=2), encoding="utf-8")
    except Exception as exc:
        return FarcasterPublishResult(
            cast=cast,
            outbox_path=None,
            cast_hash=None,
            dry_run=True,
            error=f"outbox_write_failed: {exc!r}",
        )
    if not _is_live(env) or live_publisher is None:
        return FarcasterPublishResult(
            cast=cast,
            outbox_path=out_path,
            cast_hash=None,
            dry_run=True,
        )
    try:
        cast_hash = await live_publisher(cast)
        return FarcasterPublishResult(
            cast=cast,
            outbox_path=out_path,
            cast_hash=cast_hash,
            dry_run=False,
        )
    except Exception as exc:
        return FarcasterPublishResult(
            cast=cast,
            outbox_path=out_path,
            cast_hash=None,
            dry_run=False,
            error=f"live_publish_failed: {exc!r}",
        )


__all__ = ["FarcasterCast", "FarcasterPublishResult", "publish_cast"]
