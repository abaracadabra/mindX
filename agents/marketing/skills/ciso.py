"""
CISO marketing skill — Identity gate + voice violation scan.

CISO carries 1.2× veto weight; orchestrator further enforces hard veto on
`vote == "reject"` regardless of weighted score. CISO refuses if:
  - Censura reports the agent identity as faded/ghosted/blocked
  - Forbidden_terms.deny_pattern matches the proposed copy

The skill executes BEFORE downstream skills, so a CISO refusal blocks
distribution, reporting, and attestation.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from agents.marketing.content_agent import ContentDraft
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)


class CisoSkill:
    SOLDIER_ID: str = "ciso_security"
    WEIGHT: float = 1.2
    SKILL_NAME: str = "identity_and_voice_gate"
    HBR_LAYER: int = 0

    def __init__(self, identity_resolver: Optional[Callable[[], dict]] = None) -> None:
        self.identity_resolver = identity_resolver

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        return (
            f"As CISO, evaluate identity + voice security:\n"
            f"  - Tessera DID present and unrevoked?\n"
            f"  - Censura reputation above the fade floor?\n"
            f"  - Brief copy free of forbidden_terms.deny_pattern matches?\n"
            f"Vote reject (hard veto) on any failure."
        )

    async def execute_if_approved(self, brief, brand, prior_outputs: Dict[str, Any]):
        # Identity check
        if self.identity_resolver is not None:
            try:
                state = dict(self.identity_resolver() or {})
                if state.get("censura_faded"):
                    return SkillRefusal(
                        soldier_id=self.SOLDIER_ID,
                        reason="censura_faded",
                        detail="agent reputation below fade floor",
                    )
                if not state.get("did_present"):
                    return SkillRefusal(
                        soldier_id=self.SOLDIER_ID,
                        reason="did_pending",
                        detail="agent Tessera DID not yet bound",
                    )
            except Exception as exc:
                return SkillRefusal(
                    soldier_id=self.SOLDIER_ID,
                    reason="identity_resolver_error",
                    detail=repr(exc),
                )
        # Voice scan against the brief summary + any prior CPO draft text
        text_to_scan = brief.summary or ""
        cpo_out = prior_outputs.get("cpo_product")
        if isinstance(cpo_out, SkillOutput) and isinstance(cpo_out.artifact, ContentDraft):
            text_to_scan = (text_to_scan + "\n\n" + cpo_out.artifact.text).strip()
        deny, soft = brand.forbidden.scan(text_to_scan)
        if deny:
            return SkillRefusal(
                soldier_id=self.SOLDIER_ID,
                reason="voice_violation",
                detail="; ".join(deny),
            )
        return SkillOutput(
            soldier_id=self.SOLDIER_ID,
            artifact={"soft_warns": soft, "voice_clear": True},
            notes="identity OK, voice clear" + (f", {len(soft)} soft warnings" if soft else ""),
        )


__all__ = ["CisoSkill"]
