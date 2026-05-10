"""
distribution_agent — HBR layer 3 (channel publishing).

Phase 1: writes artifacts to outbox + emits catalogue events. Live publishers
gated behind `MINDX_MARKETING_<CHANNEL>_LIVE` flags.

Channel mask bits (matches `marketinga.toml::distribution.channel_set_default_mask`):
  0b00000001 — farcaster
  0b00000010 — x
  0b00000100 — llms_txt
  0b00001000 — indexnow
  0b00010000 — wikidata (drafts to disk)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from agents.marketing.experimentation_agent import ExperimentPlan, Variant
from agents.marketing.tools.brand_code import BrandCode
from agents.marketing.tools.farcaster_publish import (
    FarcasterCast,
    FarcasterPublishResult,
    publish_cast,
)
from agents.marketing.tools.x_publish import XPost, XPublishResult, publish_post
from agents.marketing.tools.llms_txt_writer import SiteEntry, write_llms_files
from agents.marketing.tools.indexnow import IndexNowResult, ping_indexnow


CH_FARCASTER = 0b00000001
CH_X         = 0b00000010
CH_LLMS_TXT  = 0b00000100
CH_INDEXNOW  = 0b00001000
CH_WIKIDATA  = 0b00010000


@dataclass
class DistributionLedgerEntry:
    channel: str
    variant_id: str
    status: str            # "OUTBOX_ONLY" | "LIVE" | "ERROR" | "SKIPPED"
    artifact_ref: Optional[str] = None
    error: Optional[str] = None


@dataclass
class DistributionLedger:
    campaign_id: str
    entries: List[DistributionLedgerEntry] = field(default_factory=list)


class DistributionAgent:
    AGENT_ID = "marketinga.distribution"
    DID = "did:pythai:marketinga.distribution"
    ENS = "distribution.marketinga.bankon.eth"

    def __init__(
        self,
        outbox_dir: Path,
        llms_txt_dir: Path,
        sites: Iterable[SiteEntry],
        *,
        farcaster_live_publisher=None,
        x_live_publisher=None,
        indexnow_http_post=None,
    ) -> None:
        self.outbox_dir = Path(outbox_dir)
        self.outbox_dir.mkdir(parents=True, exist_ok=True)
        self.llms_txt_dir = Path(llms_txt_dir)
        self.llms_txt_dir.mkdir(parents=True, exist_ok=True)
        self.sites = list(sites)
        self.farcaster_live_publisher = farcaster_live_publisher
        self.x_live_publisher = x_live_publisher
        self.indexnow_http_post = indexnow_http_post

    async def distribute(
        self,
        brand: BrandCode,
        plan: ExperimentPlan,
        channel_set_mask: int,
        *,
        env: Optional[dict] = None,
        indexnow_key: Optional[str] = None,
    ) -> DistributionLedger:
        ledger = DistributionLedger(campaign_id=plan.campaign_id)

        # Per-variant channel publishes
        for v in plan.variants:
            if channel_set_mask & CH_FARCASTER:
                ledger.entries.append(await self._do_farcaster(v, env))
            if channel_set_mask & CH_X:
                ledger.entries.append(await self._do_x(v, env))

        # Per-campaign channels
        if channel_set_mask & CH_LLMS_TXT:
            try:
                paths = write_llms_files(self.llms_txt_dir, brand, self.sites)
                ledger.entries.append(
                    DistributionLedgerEntry(
                        channel="llms_txt",
                        variant_id="*",
                        status="LIVE",  # local file write — always real
                        artifact_ref=";".join(str(p) for p in paths),
                    )
                )
                if channel_set_mask & CH_INDEXNOW:
                    urls = [f"https://{s.domain}/llms.txt" for s in self.sites]
                    inow = await ping_indexnow(
                        host=self.sites[0].domain if self.sites else "",
                        key=indexnow_key or "",
                        urls=urls,
                        live=indexnow_key is not None and self.indexnow_http_post is not None,
                        http_post=self.indexnow_http_post,
                    )
                    ledger.entries.append(
                        DistributionLedgerEntry(
                            channel="indexnow",
                            variant_id="*",
                            status="LIVE" if not inow.dry_run and inow.error is None else (
                                "ERROR" if inow.error else "OUTBOX_ONLY"
                            ),
                            artifact_ref=f"urls={inow.urls_count} status={inow.status_code}",
                            error=inow.error,
                        )
                    )
            except Exception as exc:
                ledger.entries.append(
                    DistributionLedgerEntry(
                        channel="llms_txt",
                        variant_id="*",
                        status="ERROR",
                        error=repr(exc),
                    )
                )

        return ledger

    async def _do_farcaster(self, v: Variant, env: Optional[dict]) -> DistributionLedgerEntry:
        cast = FarcasterCast(
            campaign_id=v.campaign_id,
            variant_id=v.variant_id,
            text=v.text,
        )
        result = await publish_cast(
            cast,
            self.outbox_dir,
            live_publisher=self.farcaster_live_publisher,
            env=env,
        )
        if result.error:
            return DistributionLedgerEntry(
                channel="farcaster", variant_id=v.variant_id, status="ERROR", error=result.error
            )
        return DistributionLedgerEntry(
            channel="farcaster",
            variant_id=v.variant_id,
            status="OUTBOX_ONLY" if result.dry_run else "LIVE",
            artifact_ref=str(result.outbox_path) if result.outbox_path else result.cast_hash,
        )

    async def _do_x(self, v: Variant, env: Optional[dict]) -> DistributionLedgerEntry:
        post = XPost(campaign_id=v.campaign_id, variant_id=v.variant_id, text=v.text)
        result = await publish_post(
            post,
            self.outbox_dir,
            live_publisher=self.x_live_publisher,
            env=env,
        )
        if result.error:
            return DistributionLedgerEntry(
                channel="x", variant_id=v.variant_id, status="ERROR", error=result.error
            )
        return DistributionLedgerEntry(
            channel="x",
            variant_id=v.variant_id,
            status="OUTBOX_ONLY" if result.dry_run else "LIVE",
            artifact_ref=str(result.outbox_path) if result.outbox_path else result.tweet_id,
        )


__all__ = [
    "DistributionAgent",
    "DistributionLedger",
    "DistributionLedgerEntry",
    "CH_FARCASTER",
    "CH_X",
    "CH_LLMS_TXT",
    "CH_INDEXNOW",
    "CH_WIKIDATA",
]
