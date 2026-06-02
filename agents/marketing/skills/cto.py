"""
CTO marketing skill — HBR Layer 2: experimentation (A/B + holdouts).

The CTO owns experimentation because variant generation, deterministic
variantId derivation, and holdout cohort assignment are infrastructure
problems — same lens as system reliability.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agents.marketing.content_agent import ContentDraft
from agents.marketing.experimentation_agent import ExperimentationAgent, ExperimentPlan
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    LLMCaller,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)


class CtoSkill:
    SOLDIER_ID: str = "cto_technology"
    WEIGHT: float = 1.0
    SKILL_NAME: str = "experimentation"
    HBR_LAYER: int = 2

    def __init__(
        self,
        llm_caller: LLMCaller,
        max_variants: int = 4,
        holdout_rate: float = 0.10,
        rings: Optional[List[str]] = None,
    ) -> None:
        self._exp = ExperimentationAgent(
            llm_caller=llm_caller,
            max_variants=max_variants,
            holdout_rate=holdout_rate,
            rings=rings,
        )

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        return (
            f"As CTO, evaluate the technical readiness for A/B variant generation\n"
            f"and holdout assignment for campaign '{parts.title}'.\n"
            f"Vote approve if the variant infrastructure can produce deterministic\n"
            f"per-ring variants for ring {parts.audience_ring}."
        )

    async def execute_if_approved(self, brief, brand, prior_outputs: Dict[str, Any]):
        # CTO requires the CPO's draft as input — fetch it from prior_outputs
        cpo_out = prior_outputs.get("cpo_product")
        draft: Optional[ContentDraft] = None
        if isinstance(cpo_out, SkillOutput) and isinstance(cpo_out.artifact, ContentDraft):
            draft = cpo_out.artifact
        if draft is None:
            return SkillRefusal(
                soldier_id=self.SOLDIER_ID,
                reason="missing_upstream",
                detail="CTO experimentation requires a CPO ContentDraft",
            )
        plan = await self._exp.plan(brand, draft)
        if isinstance(plan, ExperimentPlan):
            return SkillOutput(
                soldier_id=self.SOLDIER_ID,
                artifact=plan,
                notes=f"{len(plan.variants)} variants, {len(plan.holdouts)} holdouts",
            )
        return SkillRefusal(
            soldier_id=self.SOLDIER_ID,
            reason="experimentation_refused",
            detail=str(plan),
        )


__all__ = ["CtoSkill"]
