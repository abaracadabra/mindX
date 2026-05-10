"""
CLO marketing skill — Regulatory + competitor neutrality.

The CLO holds 0.8 weight — the lightest soldier. Their domain is compliance:
  - regulatory_constraints.md rules against the brief + draft
  - competitor_map.json neutrality (no evaluative comparisons)

CLO does NOT carry hard veto. A CLO reject still requires the weighted score
to fall below supermajority for the campaign to fail. But CLO findings always
land in the soft_warns bag where the Convener can review.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from agents.marketing.content_agent import ContentDraft
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)


# Phrases that strongly imply financial advice or jurisdictional claims —
# checked even though they may not be in forbidden_terms (which targets
# token-shill copy specifically).
_REGULATORY_RED_FLAGS = (
    re.compile(r"\b(?:investment|financial)\s+advice\b", re.IGNORECASE),
    re.compile(r"\bguaranteed\s+(?:apy|apr|yield|returns?)\b", re.IGNORECASE),
    re.compile(r"\bnot\s+a\s+security\b", re.IGNORECASE),
    re.compile(r"\bSEC[-\s]?compliant\b", re.IGNORECASE),
    re.compile(r"\bavailable\s+(?:everywhere|in\s+all\s+jurisdictions)\b", re.IGNORECASE),
)


def _scan_regulatory(text: str) -> List[str]:
    found = []
    for pat in _REGULATORY_RED_FLAGS:
        m = pat.search(text)
        if m:
            found.append(m.group(0))
    return found


class CloSkill:
    SOLDIER_ID: str = "clo_legal"
    WEIGHT: float = 0.8
    SKILL_NAME: str = "regulatory_and_competitor"
    HBR_LAYER: int = 0

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        return (
            f"As CLO, evaluate compliance + competitor-neutrality:\n"
            f"  - Brief avoids regulatory red flags (financial advice, ROI, jurisdiction)?\n"
            f"  - Comparisons to Bittensor/Olas/Virtuals/ai16z stay neutral?\n"
            f"Vote approve if both, reject if either trips."
        )

    async def execute_if_approved(self, brief, brand, prior_outputs: Dict[str, Any]):
        text = brief.summary or ""
        cpo_out = prior_outputs.get("cpo_product")
        if isinstance(cpo_out, SkillOutput) and isinstance(cpo_out.artifact, ContentDraft):
            text = (text + "\n\n" + cpo_out.artifact.text).strip()

        regulatory_hits = _scan_regulatory(text)
        if regulatory_hits:
            return SkillRefusal(
                soldier_id=self.SOLDIER_ID,
                reason="regulatory_violation",
                detail="; ".join(regulatory_hits),
            )

        # Competitor neutrality: scan for mentions paired with eval verbs
        competitor_findings: List[str] = []
        text_lower = text.lower()
        for comp_name in brand.competitors.by_name.keys():
            if comp_name in text_lower:
                # Look for evaluative copy near the competitor mention
                if re.search(
                    rf"\b{re.escape(comp_name)}\b.{{0,40}}\b(?:replaces?|obsolete|inferior|loser|failed|killer)\b",
                    text_lower,
                ):
                    competitor_findings.append(comp_name)

        if competitor_findings:
            return SkillRefusal(
                soldier_id=self.SOLDIER_ID,
                reason="competitor_neutrality_violation",
                detail="; ".join(competitor_findings),
            )

        return SkillOutput(
            soldier_id=self.SOLDIER_ID,
            artifact={"clean": True},
            notes="regulatory + competitor clear",
        )


__all__ = ["CloSkill"]
