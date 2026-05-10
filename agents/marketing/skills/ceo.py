"""
CEO marketing skill — Brief composition + post-consensus signer.

The CEO does not draft, distribute, or report. The CEO:
  1. Composes the CampaignBrief from upstream goal text.
  2. Formats the boardroom directive that the 7 soldiers vote on.
  3. After supermajority approval (and no CISO/CRO veto), signs the
     MarketingAttributionReceipt envelope as the agent of record.

The Boardroom CEO already exists as a soldier role; this skill is the
marketing-specific adapter that the orchestrator wires before/after the
8-member session.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from agents.marketing.content_agent import CampaignBrief
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)


@dataclass
class CeoSkill(SoldierSkill):
    SOLDIER_ID: str = "ceo"
    WEIGHT: float = 0.0     # CEO override only; not in SOLDIER_WEIGHTS
    SKILL_NAME: str = "brief_composition_and_signing"
    HBR_LAYER: int = -1

    @staticmethod
    def compose_brief(goal: str, *, pillar: str, audience_ring: str, campaign_id: str, title: str = "") -> CampaignBrief:
        return CampaignBrief(
            campaign_id=campaign_id,
            title=title or goal[:80],
            pillar=pillar,
            audience_ring=audience_ring,
            summary=goal,
        )

    @staticmethod
    def format_boardroom_directive(brief: CampaignBrief, *, forecast_spend_usd: float = 0.0) -> str:
        return (
            f"Marketing campaign proposed.\n"
            f"campaign_id: {brief.campaign_id}\n"
            f"title: {brief.title}\n"
            f"pillar: {brief.pillar}\n"
            f"audience_ring: {brief.audience_ring}\n"
            f"forecast_spend_usd: {forecast_spend_usd:.2f}\n\n"
            f"Brief:\n{brief.summary}\n\n"
            f"Vote whether to approve this campaign. Each soldier evaluates from their\n"
            f"functional lens (CPO=content, CTO=experimentation, COO=distribution,\n"
            f"CFO=reporting+spend, CISO=identity+voice, CLO=regulatory+competitor,\n"
            f"CRO=spend-risk). CISO and CRO carry hard veto."
        )

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        # CEO doesn't vote in the same way — the orchestrator uses
        # format_boardroom_directive() above for the seven soldiers.
        return f"Strategic alignment for campaign {parts.title} (pillar={parts.pillar})."

    async def execute_if_approved(
        self,
        brief: Any,
        brand: Any,
        prior_outputs: Dict[str, Any],
    ):
        # CEO post-consensus action: signing happens in the orchestrator
        # after this skill confirms post-consensus reachability. This method
        # returns a SkillOutput acknowledging the brief is sealed.
        return SkillOutput(
            soldier_id=self.SOLDIER_ID,
            artifact={"sealed_brief_id": brief.campaign_id, "pillar": brief.pillar},
            notes="CEO seals brief; orchestrator submits MarketingAttributionReceipt",
        )


__all__ = ["CeoSkill"]
