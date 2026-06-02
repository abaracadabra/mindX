"""
x_publish — X / Twitter publisher.

Phase 1 default: dry-run only. Writes intent to outbox + emits a catalogue
event. Live publishing gated behind `MINDX_MARKETING_X_LIVE`.

Outbox layout (Phase 1):
  data/marketing/outbox/<campaignId>/x/<variantId>.json
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class XPost:
    campaign_id: str
    variant_id: str
    text: str
    media_paths: List[str] = field(default_factory=list)
    reply_to_id: Optional[str] = None
    api_credentials_vault_key: Optional[str] = None


@dataclass
class XPublishResult:
    post: XPost
    outbox_path: Optional[Path]
    tweet_id: Optional[str]
    dry_run: bool
    error: Optional[str] = None
    timestamp: float = field(default_factory=time.time)


def _is_live(env: Optional[dict] = None) -> bool:
    env = env if env is not None else os.environ
    return str(env.get("MINDX_MARKETING_X_LIVE", "")).strip().lower() in {"1", "true", "yes"}


def _outbox_path(outbox_dir: Path, post: XPost) -> Path:
    p = Path(outbox_dir) / post.campaign_id / "x"
    p.mkdir(parents=True, exist_ok=True)
    return p / f"{post.variant_id}.json"


async def publish_post(
    post: XPost,
    outbox_dir: Path,
    *,
    live_publisher=None,
    env: Optional[dict] = None,
) -> XPublishResult:
    out_path = _outbox_path(outbox_dir, post)
    try:
        out_path.write_text(json.dumps(asdict(post), indent=2), encoding="utf-8")
    except Exception as exc:
        return XPublishResult(
            post=post,
            outbox_path=None,
            tweet_id=None,
            dry_run=True,
            error=f"outbox_write_failed: {exc!r}",
        )
    if not _is_live(env) or live_publisher is None:
        return XPublishResult(
            post=post,
            outbox_path=out_path,
            tweet_id=None,
            dry_run=True,
        )
    try:
        tweet_id = await live_publisher(post)
        return XPublishResult(
            post=post,
            outbox_path=out_path,
            tweet_id=tweet_id,
            dry_run=False,
        )
    except Exception as exc:
        return XPublishResult(
            post=post,
            outbox_path=out_path,
            tweet_id=None,
            dry_run=False,
            error=f"live_publish_failed: {exc!r}",
        )


__all__ = ["XPost", "XPublishResult", "publish_post"]
