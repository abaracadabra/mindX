"""
content_agent — HBR layer 1 (content creation).

Drafts copy. Honors brand_code voice + forbidden_terms + competitor_map.
Refuses code_as_dojo pillar drafts and audience-ring-E drafts.

Per `feedback_no_model_pinning.md`, every LLM call goes through an injected
`llm_caller` (the orchestrator wires `blueprint_agent._resolve_active_handler`
+ Ollama cascade). Tests inject a mock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, List, Optional

from agents.marketing.tools.brand_code import BrandCode


# Signature: async (system_prompt, user_prompt) -> str
LLMCaller = Callable[[str, str], Awaitable[str]]


@dataclass
class CampaignBrief:
    campaign_id: str
    title: str
    pillar: str                # one of pillars.md keys
    audience_ring: str         # "A".."E"
    summary: str
    convener_override: bool = False  # if true, founder-only refusals are bypassed


@dataclass
class ContentDraft:
    campaign_id: str
    pillar: str
    audience_ring: str
    text: str
    soft_warns: List[str] = field(default_factory=list)


@dataclass
class RefusedDraft:
    campaign_id: str
    reason: str
    detail: str = ""
    matches: List[str] = field(default_factory=list)


class ContentAgent:
    AGENT_ID = "marketinga.content"
    DID = "did:pythai:marketinga.content"
    ENS = "content.marketinga.bankon.eth"

    def __init__(self, llm_caller: LLMCaller, drafts_dir: Optional[Path] = None) -> None:
        self.llm_caller = llm_caller
        self.drafts_dir = Path(drafts_dir) if drafts_dir else None
        if self.drafts_dir is not None:
            self.drafts_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _system_prompt(brand: BrandCode, brief: CampaignBrief) -> str:
        return (
            "You are content.marketinga.bankon.eth, a sub-agent of marketinga.agent.\n"
            f"Voice register: {brand.voice_register()}. First-person-as-mindx.\n"
            "Cypherpunk tradition (not cyberpunk).\n"
            f"Pillar: {brief.pillar}. Audience ring: {brief.audience_ring}.\n"
            "You MUST avoid token-shill language, ROI promises, price predictions, and exclusivity hooks.\n"
            "You MUST sign every public output as `— marketinga.agent`.\n"
            "Output the draft only. No commentary, no preamble."
        )

    @staticmethod
    def _user_prompt(brief: CampaignBrief) -> str:
        return f"Campaign brief — {brief.title}.\n\n{brief.summary}"

    async def draft(self, brand: BrandCode, brief: CampaignBrief):
        # Hard refusals first.
        if brand.pillar_is_reserved(brief.pillar) and not brief.convener_override:
            return RefusedDraft(
                campaign_id=brief.campaign_id,
                reason="founder_only_pillar",
                detail="The code_as_dojo pillar is reserved for the human Convener.",
            )
        if brand.audience_is_reserved(brief.audience_ring) and not brief.convener_override:
            return RefusedDraft(
                campaign_id=brief.campaign_id,
                reason="founder_only_audience",
                detail="Audience ring E is reserved for the human Convener.",
            )

        try:
            text = await self.llm_caller(
                self._system_prompt(brand, brief),
                self._user_prompt(brief),
            )
        except Exception as exc:
            return RefusedDraft(
                campaign_id=brief.campaign_id,
                reason="no_inference_path",
                detail=f"selector + cascade both failed: {exc!r}",
            )

        text = (text or "").strip()
        if not text:
            return RefusedDraft(
                campaign_id=brief.campaign_id,
                reason="no_inference_path",
                detail="empty draft",
            )

        deny, soft = brand.forbidden.scan(text)
        if deny:
            return RefusedDraft(
                campaign_id=brief.campaign_id,
                reason="voice_violation",
                detail="forbidden_terms.deny_pattern matched",
                matches=deny,
            )

        draft = ContentDraft(
            campaign_id=brief.campaign_id,
            pillar=brief.pillar,
            audience_ring=brief.audience_ring,
            text=text,
            soft_warns=soft,
        )
        if self.drafts_dir is not None:
            (self.drafts_dir / f"{brief.campaign_id}.txt").write_text(text, encoding="utf-8")
        return draft


__all__ = ["ContentAgent", "CampaignBrief", "ContentDraft", "RefusedDraft", "LLMCaller"]
