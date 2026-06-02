"""
COO marketing skill — HBR Layer 3: distribution (channel publishing).

The COO owns distribution because channel execution, outbox/live publishing,
and indexnow ping are operational concerns — same lens as ops at large.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

from agents.marketing.distribution_agent import (
    CH_FARCASTER,
    CH_LLMS_TXT,
    CH_X,
    DistributionAgent,
    DistributionLedger,
)
from agents.marketing.experimentation_agent import ExperimentPlan
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)
from agents.marketing.tools.llms_txt_writer import SiteEntry


class CooSkill:
    SOLDIER_ID: str = "coo_operations"
    WEIGHT: float = 1.0
    SKILL_NAME: str = "distribution"
    HBR_LAYER: int = 3

    def __init__(
        self,
        outbox_dir: Path,
        llms_txt_dir: Path,
        sites: Iterable[SiteEntry],
        *,
        farcaster_live_publisher=None,
        x_live_publisher=None,
        indexnow_http_post=None,
        default_channel_mask: int = CH_FARCASTER | CH_X | CH_LLMS_TXT,
    ) -> None:
        self._dist = DistributionAgent(
            outbox_dir=outbox_dir,
            llms_txt_dir=llms_txt_dir,
            sites=sites,
            farcaster_live_publisher=farcaster_live_publisher,
            x_live_publisher=x_live_publisher,
            indexnow_http_post=indexnow_http_post,
        )
        self.default_channel_mask = int(default_channel_mask)

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        return (
            f"As COO, evaluate the operational readiness to publish campaign\n"
            f"'{parts.title}' through farcaster/x/llms_txt channels. Vote approve\n"
            f"if the outbox path is writable and feature flags are sane."
        )

    async def execute_if_approved(self, brief, brand, prior_outputs: Dict[str, Any]):
        cto_out = prior_outputs.get("cto_technology")
        plan: Optional[ExperimentPlan] = None
        if isinstance(cto_out, SkillOutput) and isinstance(cto_out.artifact, ExperimentPlan):
            plan = cto_out.artifact
        if plan is None:
            return SkillRefusal(
                soldier_id=self.SOLDIER_ID,
                reason="missing_upstream",
                detail="COO distribution requires a CTO ExperimentPlan",
            )
        ledger = await self._dist.distribute(
            brand=brand,
            plan=plan,
            channel_set_mask=self.default_channel_mask,
        )
        return SkillOutput(
            soldier_id=self.SOLDIER_ID,
            artifact=ledger,
            notes=f"{len(ledger.entries)} distribution entries",
        )


__all__ = ["CooSkill"]
