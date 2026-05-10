"""
CPO marketing skill — HBR Layer 1: content drafting.

The CPO owns content because the CPO already owns positioning + voice +
ICP at the boardroom level. Every public draft is written from the CPO's
seat through the existing `content_agent.ContentAgent` logic, preserved
verbatim — the CPO IS that agent in skill form.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from agents.marketing.content_agent import ContentAgent, ContentDraft, RefusedDraft
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    LLMCaller,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)


class CpoSkill:
    SOLDIER_ID: str = "cpo_product"
    WEIGHT: float = 1.0
    SKILL_NAME: str = "content_drafting"
    HBR_LAYER: int = 1

    def __init__(self, llm_caller: LLMCaller, drafts_dir: Optional[Path] = None) -> None:
        self._content = ContentAgent(llm_caller=llm_caller, drafts_dir=drafts_dir)

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        return (
            f"As CPO, evaluate the campaign's content/positioning fit:\n"
            f"  pillar={parts.pillar}\n"
            f"  audience_ring={parts.audience_ring}\n"
            f"  title={parts.title}\n"
            f"Vote approve if the brief is on-brand and the audience ring matches\n"
            f"the pillar. Reject if pillar=code_as_dojo or audience_ring=E (founder-only)."
        )

    async def execute_if_approved(self, brief, brand, prior_outputs: Dict[str, Any]):
        result = await self._content.draft(brand, brief)
        if isinstance(result, RefusedDraft):
            return SkillRefusal(
                soldier_id=self.SOLDIER_ID,
                reason=result.reason,
                detail=result.detail,
            )
        if isinstance(result, ContentDraft):
            return SkillOutput(
                soldier_id=self.SOLDIER_ID,
                artifact=result,
                notes=f"draft for ring {result.audience_ring}",
            )
        return SkillRefusal(soldier_id=self.SOLDIER_ID, reason="unknown_draft_type")


__all__ = ["CpoSkill"]
