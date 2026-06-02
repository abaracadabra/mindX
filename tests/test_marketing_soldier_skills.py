"""One test per soldier skill — vote prompt + execute_if_approved behavior."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.marketing.content_agent import CampaignBrief, ContentDraft
from agents.marketing.experimentation_agent import ExperimentPlan, Variant
from agents.marketing.skills.cfo import CfoSkill
from agents.marketing.skills.ceo import CeoSkill
from agents.marketing.skills.ciso import CisoSkill
from agents.marketing.skills.clo import CloSkill
from agents.marketing.skills.coo import CooSkill
from agents.marketing.skills.cpo import CpoSkill
from agents.marketing.skills.cro import CroSkill
from agents.marketing.skills.cto import CtoSkill
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    SkillOutput,
    SkillRefusal,
)
from agents.marketing.tools.brand_code import load_brand_code
from agents.marketing.tools.llms_txt_writer import SiteEntry


REPO = Path(__file__).resolve().parents[1]
BRAND = load_brand_code(REPO / "data" / "brand_code")


def _brief(pillar: str = "cognition_you_own", ring: str = "A", summary: str = "Why mindX matters."):
    return CampaignBrief(
        campaign_id="c-skill-test",
        title="t",
        pillar=pillar,
        audience_ring=ring,
        summary=summary,
    )


def _parts(soldier_id: str, ring: str = "A", forecast: float = 100.0):
    return DirectivePromptParts(
        soldier_id=soldier_id,
        title="t",
        pillar="cognition_you_own",
        audience_ring=ring,
        summary="x",
        forecast_spend_usd=forecast,
    )


# ── CEO ────────────────────────────────────────────────────────────────────


def test_ceo_skill_compose_brief():
    brief = CeoSkill.compose_brief("Build mindX awareness", pillar="cognition_you_own",
                                   audience_ring="A", campaign_id="c-1", title="awareness")
    assert brief.campaign_id == "c-1"
    assert brief.pillar == "cognition_you_own"


def test_ceo_skill_format_directive_includes_pillar_and_audience():
    brief = _brief()
    directive = CeoSkill.format_boardroom_directive(brief, forecast_spend_usd=750.0)
    assert "cognition_you_own" in directive
    assert "audience_ring: A" in directive
    assert "750.00" in directive
    assert "CISO and CRO carry hard veto" in directive


# ── CPO ────────────────────────────────────────────────────────────────────


def test_cpo_skill_drafts_when_approved():
    async def run():
        async def caller(s, u):
            return "Mindful cognition. — marketinga.agent"
        skill = CpoSkill(llm_caller=caller)
        result = await skill.execute_if_approved(_brief(), BRAND, prior_outputs={})
        assert isinstance(result, SkillOutput)
        assert isinstance(result.artifact, ContentDraft)
        assert "marketinga.agent" in result.artifact.text
    asyncio.run(run())


def test_cpo_skill_refuses_code_as_dojo():
    async def run():
        async def caller(s, u):
            return "stoic prose"
        skill = CpoSkill(llm_caller=caller)
        result = await skill.execute_if_approved(
            _brief(pillar="code_as_dojo"), BRAND, prior_outputs={},
        )
        assert isinstance(result, SkillRefusal)
        assert result.reason == "founder_only_pillar"
    asyncio.run(run())


# ── CTO ────────────────────────────────────────────────────────────────────


def test_cto_skill_requires_cpo_upstream():
    async def run():
        async def caller(s, u):
            return "v"
        skill = CtoSkill(llm_caller=caller)
        result = await skill.execute_if_approved(_brief(), BRAND, prior_outputs={})
        assert isinstance(result, SkillRefusal)
        assert result.reason == "missing_upstream"
    asyncio.run(run())


def test_cto_skill_produces_experiment_plan_when_cpo_present():
    async def run():
        async def caller(s, u):
            return "tuned variant. — marketinga.agent"
        skill = CtoSkill(llm_caller=caller, max_variants=2, holdout_rate=0.1)
        draft = ContentDraft(
            campaign_id="c-1",
            pillar="cognition_you_own",
            audience_ring="A",
            text="base draft. — marketinga.agent",
        )
        result = await skill.execute_if_approved(
            _brief(), BRAND,
            prior_outputs={"cpo_product": SkillOutput(soldier_id="cpo_product", artifact=draft)},
        )
        assert isinstance(result, SkillOutput)
        assert isinstance(result.artifact, ExperimentPlan)
        assert len(result.artifact.variants) >= 1
    asyncio.run(run())


# ── COO ────────────────────────────────────────────────────────────────────


def test_coo_skill_requires_cto_upstream(tmp_path):
    async def run():
        skill = CooSkill(
            outbox_dir=tmp_path / "outbox",
            llms_txt_dir=tmp_path / "llms_txt",
            sites=[SiteEntry(domain="x.test", product="X")],
        )
        result = await skill.execute_if_approved(_brief(), BRAND, prior_outputs={})
        assert isinstance(result, SkillRefusal)
        assert result.reason == "missing_upstream"
    asyncio.run(run())


def test_coo_skill_writes_llms_txt(tmp_path):
    async def run():
        skill = CooSkill(
            outbox_dir=tmp_path / "outbox",
            llms_txt_dir=tmp_path / "llms_txt",
            sites=[SiteEntry(domain="x.test", product="X")],
            default_channel_mask=0b00000100,  # llms_txt only
        )
        plan = ExperimentPlan(
            campaign_id="c-1",
            variants=[Variant(campaign_id="c-1", ring="A", variant_id="v1", text="t. — marketinga.agent")],
            holdouts=[],
        )
        result = await skill.execute_if_approved(
            _brief(), BRAND,
            prior_outputs={"cto_technology": SkillOutput(soldier_id="cto_technology", artifact=plan)},
        )
        assert isinstance(result, SkillOutput)
        assert (tmp_path / "llms_txt" / "llms.txt").is_file()
    asyncio.run(run())


# ── CFO ────────────────────────────────────────────────────────────────────


def test_cfo_skill_produces_kpi_snapshot(tmp_path):
    async def run():
        async def caller(engine, prompt):
            return "mindX wins"
        skill = CfoSkill(
            engines=["chatgpt"], brand_terms=["mindX"], prompts=["why mindX"],
            llm_caller=caller, cache_dir=tmp_path / "cache", snapshots_dir=tmp_path / "snap",
        )
        result = await skill.execute_if_approved(_brief(), BRAND, prior_outputs={})
        assert isinstance(result, SkillOutput)
        assert "kpi" in result.artifact
    asyncio.run(run())


# ── CISO ───────────────────────────────────────────────────────────────────


def test_ciso_skill_passes_clean_copy():
    async def run():
        skill = CisoSkill()
        result = await skill.execute_if_approved(
            _brief(summary="Cypherpunk cognition you own."), BRAND, prior_outputs={},
        )
        assert isinstance(result, SkillOutput)
        assert result.artifact["voice_clear"] is True
    asyncio.run(run())


def test_ciso_skill_blocks_forbidden_term():
    async def run():
        skill = CisoSkill()
        result = await skill.execute_if_approved(
            _brief(summary="It's going to the moon, guaranteed!"), BRAND, prior_outputs={},
        )
        assert isinstance(result, SkillRefusal)
        assert result.reason == "voice_violation"
    asyncio.run(run())


def test_ciso_skill_blocks_faded_identity():
    async def run():
        skill = CisoSkill(identity_resolver=lambda: {"censura_faded": True, "did_present": True})
        result = await skill.execute_if_approved(_brief(), BRAND, prior_outputs={})
        assert isinstance(result, SkillRefusal)
        assert result.reason == "censura_faded"
    asyncio.run(run())


# ── CLO ────────────────────────────────────────────────────────────────────


def test_clo_skill_passes_neutral_copy():
    async def run():
        skill = CloSkill()
        result = await skill.execute_if_approved(
            _brief(summary="Cypherpunk cognition. — marketinga.agent"), BRAND, prior_outputs={},
        )
        assert isinstance(result, SkillOutput)
    asyncio.run(run())


def test_clo_skill_blocks_financial_advice():
    async def run():
        skill = CloSkill()
        result = await skill.execute_if_approved(
            _brief(summary="This is financial advice. Stake for guaranteed APY."),
            BRAND, prior_outputs={},
        )
        assert isinstance(result, SkillRefusal)
        assert result.reason == "regulatory_violation"
    asyncio.run(run())


def test_clo_skill_blocks_evaluative_competitor_comparison():
    async def run():
        skill = CloSkill()
        result = await skill.execute_if_approved(
            _brief(summary="mindX replaces Bittensor — Bittensor is obsolete."),
            BRAND, prior_outputs={},
        )
        assert isinstance(result, SkillRefusal)
        assert result.reason == "competitor_neutrality_violation"
    asyncio.run(run())


# ── CRO ────────────────────────────────────────────────────────────────────


def test_cro_skill_passes_below_hard_stop():
    async def run():
        skill = CroSkill(hard_stop_spend_usd=5000.0, spend_threshold_usd=500.0,
                         forecast_spend_usd=300.0)
        result = await skill.execute_if_approved(_brief(), BRAND, prior_outputs={})
        assert isinstance(result, SkillOutput)
    asyncio.run(run())


def test_cro_skill_blocks_at_hard_stop():
    async def run():
        skill = CroSkill(hard_stop_spend_usd=5000.0, spend_threshold_usd=500.0,
                         forecast_spend_usd=5500.0)
        result = await skill.execute_if_approved(_brief(), BRAND, prior_outputs={})
        assert isinstance(result, SkillRefusal)
        assert result.reason == "hard_stop_spend"
    asyncio.run(run())


def test_cro_skill_flags_holdout_integrity_when_variants_have_no_holdouts():
    async def run():
        skill = CroSkill(forecast_spend_usd=100.0)
        plan = ExperimentPlan(
            campaign_id="c-1",
            variants=[Variant(campaign_id="c-1", ring="A", variant_id="v", text="t")],
            holdouts=[],   # broken: variants but no holdouts
        )
        result = await skill.execute_if_approved(
            _brief(), BRAND,
            prior_outputs={"cto_technology": SkillOutput(soldier_id="cto_technology", artifact=plan)},
        )
        assert isinstance(result, SkillRefusal)
        assert result.reason == "holdout_integrity_broken"
    asyncio.run(run())
