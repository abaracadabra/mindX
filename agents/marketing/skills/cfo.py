"""
CFO marketing skill — HBR Layer 4: reporting + treasury.

The CFO owns reporting because measurement + ROI are finance concerns. The
CFO also reads `MarketingTreasury` state for the buyback ledger that feeds
quarterly RetroPGF — measurement and money on one desk.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.marketing.distribution_agent import DistributionLedger
from agents.marketing.reporting_agent import ReportingAgent, KpiSnapshot
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    LLMCaller,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)


class CfoSkill:
    SOLDIER_ID: str = "cfo_finance"
    WEIGHT: float = 1.0
    SKILL_NAME: str = "reporting_and_treasury"
    HBR_LAYER: int = 4

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
        treasury_client: Any = None,
    ) -> None:
        self._reporting = ReportingAgent(
            engines=engines,
            brand_terms=brand_terms,
            prompts=prompts,
            llm_caller=llm_caller,
            cascade_caller=cascade_caller,
            cache_dir=cache_dir,
            cache_seconds=cache_seconds,
            weekly_budget_usd=weekly_budget_usd,
            snapshots_dir=snapshots_dir,
        )
        self.treasury_client = treasury_client

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        return (
            f"As CFO, evaluate the campaign's spend-vs-outcome posture.\n"
            f"  forecast_spend_usd={parts.forecast_spend_usd:.2f}\n"
            f"Vote approve if the spend is justified by the expected GEO + KPI lift.\n"
            f"Vote reject if forecast spend is unbounded or no measurement is wired."
        )

    async def execute_if_approved(self, brief, brand, prior_outputs: Dict[str, Any]):
        coo_out = prior_outputs.get("coo_operations")
        ledger: Optional[DistributionLedger] = None
        if isinstance(coo_out, SkillOutput) and isinstance(coo_out.artifact, DistributionLedger):
            ledger = coo_out.artifact
        if ledger is None:
            ledger = DistributionLedger(campaign_id=brief.campaign_id)
        try:
            rollup = await self._reporting.run_geo_probe()
        except Exception:
            rollup = None
        kpi = self._reporting.compute_kpi_snapshot(
            campaign_id=brief.campaign_id,
            ledger=ledger,
            rollup=rollup,
            paid_actions=sum(1 for e in ledger.entries if e.status == "LIVE"),
        )
        treasury_snapshot = None
        if self.treasury_client is not None:
            try:
                snapshot_fn = getattr(self.treasury_client, "snapshot", None)
                if snapshot_fn is not None:
                    res = snapshot_fn()
                    if hasattr(res, "__await__"):
                        res = await res
                    treasury_snapshot = res
            except Exception:
                treasury_snapshot = None
        return SkillOutput(
            soldier_id=self.SOLDIER_ID,
            artifact={"kpi": kpi, "treasury": treasury_snapshot},
            notes="GEO probe + KPI snapshot computed",
        )


__all__ = ["CfoSkill"]
