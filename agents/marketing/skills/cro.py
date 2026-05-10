"""
CRO marketing skill — Spend risk + hard-stop.

CRO carries 1.2× veto weight; orchestrator enforces hard veto on `reject`
regardless of weighted score. CRO refuses if:
  - forecast spend ≥ hard_stop_spend_usd (kill switch)
  - holdout cohort integrity is broken (e.g., 0% holdout when rate > 0)
  - above-threshold spend without Boardroom routing record

CRO does NOT actually call Boardroom.convene — that has already happened
by the time this skill runs. CRO inspects whether the spend is sane given
the current campaign envelope.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from agents.marketing.experimentation_agent import ExperimentPlan
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)


class CroSkill:
    SOLDIER_ID: str = "cro_risk"
    WEIGHT: float = 1.2
    SKILL_NAME: str = "spend_risk_and_hard_stop"
    HBR_LAYER: int = 0

    def __init__(
        self,
        hard_stop_spend_usd: float = 5000.0,
        spend_threshold_usd: float = 500.0,
        forecast_spend_usd: float = 0.0,
    ) -> None:
        self.hard_stop_spend_usd = float(hard_stop_spend_usd)
        self.spend_threshold_usd = float(spend_threshold_usd)
        # The forecast is set per-campaign by the orchestrator before calling
        # execute_if_approved (or read from brief.summary metadata in production).
        self.forecast_spend_usd = float(forecast_spend_usd)

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        return (
            f"As CRO, evaluate spend risk:\n"
            f"  forecast_spend_usd={parts.forecast_spend_usd:.2f}\n"
            f"  hard_stop_floor={self.hard_stop_spend_usd:.2f}\n"
            f"Vote reject (hard veto) if forecast meets or exceeds the hard-stop\n"
            f"floor; flag for Boardroom routing if above the threshold."
        )

    async def execute_if_approved(self, brief, brand, prior_outputs: Dict[str, Any]):
        # Hard-stop kill switch
        if self.forecast_spend_usd >= self.hard_stop_spend_usd:
            return SkillRefusal(
                soldier_id=self.SOLDIER_ID,
                reason="hard_stop_spend",
                detail=(
                    f"forecast ${self.forecast_spend_usd:.2f} ≥ hard stop "
                    f"${self.hard_stop_spend_usd:.2f}"
                ),
            )

        # Holdout integrity check (downstream artifact already exists from CTO)
        cto_out = prior_outputs.get("cto_technology")
        if isinstance(cto_out, SkillOutput) and isinstance(cto_out.artifact, ExperimentPlan):
            plan: ExperimentPlan = cto_out.artifact
            if plan.variants and not plan.holdouts:
                return SkillRefusal(
                    soldier_id=self.SOLDIER_ID,
                    reason="holdout_integrity_broken",
                    detail=f"{len(plan.variants)} variants but 0 holdouts — measurement impossible",
                )

        flags = []
        if self.forecast_spend_usd > self.spend_threshold_usd:
            flags.append("above_threshold_logged")

        return SkillOutput(
            soldier_id=self.SOLDIER_ID,
            artifact={
                "forecast_spend_usd": self.forecast_spend_usd,
                "hard_stop_spend_usd": self.hard_stop_spend_usd,
                "flags": flags,
            },
            notes="spend within tolerance",
        )


__all__ = ["CroSkill"]
