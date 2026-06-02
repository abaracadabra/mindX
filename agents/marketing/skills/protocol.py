"""
SoldierSkill protocol + shared dataclasses.

A SoldierSkill is the marketing capability bound to one boardroom soldier.
The orchestrator runs the boardroom; for each soldier with `vote == "approve"`,
it invokes that soldier's skill via `execute_if_approved()`.

Skills are composable but not chained inside themselves — the orchestrator owns
the dispatch order. Skills receive `prior_outputs` (a Dict[soldier_id, Any])
so they can read what earlier soldiers produced.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Optional, Protocol, runtime_checkable


# Async (system_prompt, user_prompt) -> str
LLMCaller = Callable[[str, str], Awaitable[str]]


@dataclass
class DirectivePromptParts:
    """The pieces a soldier formats into its vote prompt for THIS campaign."""
    soldier_id: str
    title: str
    pillar: str
    audience_ring: str
    summary: str
    forecast_spend_usd: float
    extra_context: str = ""


@dataclass
class SkillRefusal:
    """Returned by a skill when its hard-refusal conditions trip."""
    soldier_id: str
    reason: str
    detail: str = ""


@dataclass
class SkillOutput:
    """Returned by a skill that produced a real artifact."""
    soldier_id: str
    artifact: Any
    notes: str = ""


SkillResult = Any  # Union[SkillOutput, SkillRefusal] — kept loose by design


@runtime_checkable
class SoldierSkill(Protocol):
    """Contract for every soldier marketing skill."""

    SOLDIER_ID: str       # e.g. "cpo_product"
    WEIGHT: float         # mirrors boardroom.SOLDIER_WEIGHTS
    SKILL_NAME: str       # human label, e.g. "content_drafting"
    HBR_LAYER: int        # 0=governance, 1..4=HBR layers, -1=ceo

    def directive_prompt(self, parts: DirectivePromptParts) -> str:
        """Format the per-soldier vote prompt for this campaign."""
        ...

    async def execute_if_approved(
        self,
        brief: Any,
        brand: Any,
        prior_outputs: Dict[str, Any],
    ) -> SkillResult:
        """Run the marketing capability after this soldier voted approve.

        Must NEVER raise — return SkillRefusal on failure or refusal.
        """
        ...


def is_veto_soldier(soldier_id: str) -> bool:
    """CISO and CRO carry hard-veto contract semantics (1.2× weight in
    `boardroom.SOLDIER_WEIGHTS` — this module also enforces hard veto on
    `vote == "reject"` regardless of weighted score)."""
    return soldier_id in {"ciso_security", "cro_risk"}


__all__ = [
    "SoldierSkill",
    "DirectivePromptParts",
    "SkillOutput",
    "SkillRefusal",
    "SkillResult",
    "LLMCaller",
    "is_veto_soldier",
]
