"""
reporting_agent — HBR layer 4 (GEO + KPI rollups).

Drives `tools.geo_probe` weekly under a budget cap. Computes the
`outcomeMetricCid` payload for the MarketingAttributionReceipt.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional

from agents.marketing.distribution_agent import DistributionLedger
from agents.marketing.tools.geo_probe import GeoProbe, GeoProbeRollup, LLMCaller


@dataclass
class KpiSnapshot:
    campaign_id: str
    geo_share_of_voice: Dict[str, float] = field(default_factory=dict)
    paid_actions_completed: int = 0
    tessera_credentials_issued: int = 0
    distribution_outcomes: Dict[str, int] = field(default_factory=dict)
    holdout_lift_proxy: Optional[float] = None
    diminished_share: float = 0.0
    error_share: float = 0.0
    cached_share: float = 0.0


def kpi_snapshot_cid(snapshot: KpiSnapshot) -> str:
    """Stable content hash of a KpiSnapshot. Used as `outcomeMetricCid`.

    sha256 hex; the `MarketingAttributionReceipt` accepts a bytes32 CID.
    Translation to bytes32 happens in the on-chain client layer.
    """
    payload = json.dumps(asdict(snapshot), sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ReportingAgent:
    AGENT_ID = "marketinga.reporting"
    DID = "did:pythai:marketinga.reporting"
    ENS = "reporting.marketinga.bankon.eth"

    def __init__(
        self,
        engines: List[str],
        brand_terms: List[str],
        prompts: List[str],
        llm_caller: LLMCaller,
        *,
        cascade_caller: Optional[LLMCaller] = None,
        cache_dir: Optional[Path] = None,
        cache_seconds: int = 86400,
        weekly_budget_usd: float = 20.0,
        snapshots_dir: Optional[Path] = None,
    ) -> None:
        self.geo = GeoProbe(
            engines=engines,
            brand_terms=brand_terms,
            prompts=prompts,
            llm_caller=llm_caller,
            cascade_caller=cascade_caller,
            cache_dir=cache_dir,
            cache_seconds=cache_seconds,
            weekly_budget_usd=weekly_budget_usd,
        )
        self.snapshots_dir = Path(snapshots_dir) if snapshots_dir else None
        if self.snapshots_dir is not None:
            self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    async def run_geo_probe(self) -> GeoProbeRollup:
        _, rollup = await self.geo.run()
        return rollup

    def compute_kpi_snapshot(
        self,
        campaign_id: str,
        ledger: DistributionLedger,
        rollup: Optional[GeoProbeRollup],
        tessera_credentials: int = 0,
        paid_actions: int = 0,
    ) -> KpiSnapshot:
        outcomes: Dict[str, int] = {}
        for e in ledger.entries:
            outcomes[e.channel] = outcomes.get(e.channel, 0) + 1
        snap = KpiSnapshot(
            campaign_id=campaign_id,
            geo_share_of_voice=dict(rollup.share_of_voice) if rollup else {},
            paid_actions_completed=paid_actions,
            tessera_credentials_issued=tessera_credentials,
            distribution_outcomes=outcomes,
            diminished_share=rollup.diminished_share if rollup else 0.0,
            error_share=rollup.error_share if rollup else 0.0,
            cached_share=rollup.cached_share if rollup else 0.0,
        )
        if self.snapshots_dir is not None:
            (self.snapshots_dir / f"{campaign_id}.json").write_text(
                json.dumps(asdict(snap), indent=2), encoding="utf-8"
            )
        return snap


__all__ = ["ReportingAgent", "KpiSnapshot", "kpi_snapshot_cid"]
