"""
experimentation_agent — HBR layer 2 (A/B + holdouts).

Takes one ContentDraft and produces deterministic per-ring variants plus
holdout cohort assignments. Variant ids are keccak256(campaignId | ring),
so identical inputs always yield identical variantIds — a property
`reporting_a` relies on.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field
from typing import Awaitable, Callable, Dict, List, Optional

from agents.marketing.content_agent import ContentDraft, RefusedDraft
from agents.marketing.tools.brand_code import BrandCode


LLMCaller = Callable[[str, str], Awaitable[str]]


@dataclass
class Variant:
    campaign_id: str
    ring: str               # "A", "B", "C", "D"
    variant_id: str         # keccak-derived deterministic id (hex)
    text: str
    soft_warns: List[str] = field(default_factory=list)


@dataclass
class HoldoutCohort:
    ring: str
    rate: float             # 0..1
    seed: int               # for the deterministic cohort assignment


@dataclass
class ExperimentPlan:
    campaign_id: str
    variants: List[Variant]
    holdouts: List[HoldoutCohort]


def variant_id(campaign_id: str, ring: str) -> str:
    """Deterministic variant id — keccak-style sha256 over (campaignId | ring).

    sha256 is fine here; we use this id as a join key off-chain. The on-chain
    receipts use keccak256 in the contract directly — these strings line up
    semantically, not bitwise.
    """
    return hashlib.sha256(f"{campaign_id}|{ring}".encode("utf-8")).hexdigest()


class ExperimentationAgent:
    AGENT_ID = "marketinga.experimentation"
    DID = "did:pythai:marketinga.experimentation"
    ENS = "experimentation.marketinga.bankon.eth"

    DEFAULT_RINGS = ("A", "B", "C", "D")  # never E

    def __init__(
        self,
        llm_caller: LLMCaller,
        max_variants: int = 4,
        holdout_rate: float = 0.10,
        rings: Optional[List[str]] = None,
    ) -> None:
        self.llm_caller = llm_caller
        self.max_variants = max(1, int(max_variants))
        self.holdout_rate = max(0.0, min(0.5, float(holdout_rate)))
        self.rings = list(rings) if rings else list(self.DEFAULT_RINGS)

    @staticmethod
    def _system_prompt(brand: BrandCode, ring: str) -> str:
        return (
            "You are experimentation.marketinga.bankon.eth.\n"
            f"Voice register: {brand.voice_register()}.\n"
            f"Tune the draft for audience ring {ring}. Do not change the underlying claim.\n"
            "Adjust tone register only:\n"
            "  A — senior crypto-native developers (technical, citation-dense)\n"
            "  B — AI researchers, dev-tool power users (technical, empirical)\n"
            "  C — traders, onchain power users (terse, value-prop-first)\n"
            "  D — mainstream crypto users (friendly, low-jargon)\n"
            "Output the variant only. No commentary."
        )

    async def plan(self, brand: BrandCode, draft: ContentDraft):
        if isinstance(draft, RefusedDraft):
            return draft  # propagate refusal verbatim

        rings = self.rings[: self.max_variants]
        variants: List[Variant] = []
        for ring in rings:
            if ring.upper() == "E":
                continue
            try:
                v_text = await self.llm_caller(
                    self._system_prompt(brand, ring),
                    f"Base draft (do not paraphrase the claim, only retune):\n\n{draft.text}",
                )
            except Exception:
                v_text = draft.text  # fall back to base on per-ring failure
            v_text = (v_text or "").strip() or draft.text
            deny, soft = brand.forbidden.scan(v_text)
            if deny:
                # If a per-ring variant violates voice, drop that ring rather than poison the plan
                continue
            variants.append(
                Variant(
                    campaign_id=draft.campaign_id,
                    ring=ring,
                    variant_id=variant_id(draft.campaign_id, ring),
                    text=v_text,
                    soft_warns=soft,
                )
            )

        # Deterministic holdout seed per campaign
        seed_int = int(hashlib.sha256(draft.campaign_id.encode("utf-8")).hexdigest()[:8], 16)
        holdouts = [HoldoutCohort(ring=v.ring, rate=self.holdout_rate, seed=seed_int) for v in variants]

        return ExperimentPlan(
            campaign_id=draft.campaign_id,
            variants=variants,
            holdouts=holdouts,
        )


__all__ = [
    "ExperimentationAgent",
    "ExperimentPlan",
    "Variant",
    "HoldoutCohort",
    "variant_id",
    "LLMCaller",
]
