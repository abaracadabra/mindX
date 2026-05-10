"""Tests for MarketingaAgent + MarketingBoardroomOrchestrator (boardroom-driven)."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.marketing.boardroom_orchestrator import (
    CampaignResult,
    MarketingBoardroomOrchestrator,
)
from agents.marketing.content_agent import CampaignBrief
from agents.marketing.distribution_agent import CH_LLMS_TXT
from agents.marketing.marketinga_agent import MarketingaAgent


REPO = Path(__file__).resolve().parents[1]


# ── Fake Boardroom ─────────────────────────────────────────────────────────


@dataclass
class _FakeVote:
    soldier_id: str
    vote: str
    reasoning: str = ""
    confidence: float = 0.5
    weight: float = 1.0
    provider: str = "mock"


@dataclass
class _FakeSession:
    session_id: str
    directive: str
    outcome: str
    weighted_score: float
    votes: List[_FakeVote]
    dissent_branches: List = None
    model_report: dict = None

    def __post_init__(self):
        if self.dissent_branches is None:
            self.dissent_branches = []
        if self.model_report is None:
            self.model_report = {}


class _FakeBoardroom:
    """Reusable fake boardroom. Tests pre-set the session it returns."""

    def __init__(self, session: _FakeSession):
        self._session = session
        self.last_directive: Optional[str] = None
        self.last_members: Optional[str] = None

    async def convene(self, directive, importance="standard", members=None, consensus=0.666, **kw):
        self.last_directive = directive
        self.last_members = members
        return self._session


def _all_approve_session(session_id: str = "br_t_1") -> _FakeSession:
    return _FakeSession(
        session_id=session_id,
        directive="",
        outcome="approved",
        weighted_score=0.9,
        votes=[
            _FakeVote("ceo", "approve"),
            _FakeVote("cpo_product", "approve", weight=1.0),
            _FakeVote("cto_technology", "approve", weight=1.0),
            _FakeVote("coo_operations", "approve", weight=1.0),
            _FakeVote("cfo_finance", "approve", weight=1.0),
            _FakeVote("ciso_security", "approve", weight=1.2),
            _FakeVote("clo_legal", "approve", weight=0.8),
            _FakeVote("cro_risk", "approve", weight=1.2),
        ],
    )


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_singleton():
    MarketingaAgent._reset_for_tests()
    yield
    MarketingaAgent._reset_for_tests()


def _build_orchestrator(
    tmp_path: Path,
    *,
    boardroom: _FakeBoardroom,
    llm_text: str = "mindX is the cognition you own. — marketinga.agent",
) -> MarketingaAgent:
    async def llm_caller(system_prompt, user_prompt):
        return llm_text

    async def get_inst():
        return await MarketingaAgent.get_instance(
            brand_code_root=REPO / "data" / "brand_code",
            toml_config_path=REPO / "data" / "config" / "marketinga.toml",
            llm_caller=llm_caller,
            boardroom=boardroom,
            data_root=tmp_path,
            test_mode=True,
        )

    return asyncio.run(get_inst())


# ── Tests ───────────────────────────────────────────────────────────────────


def test_status_returns_eight_soldier_skill_rows(tmp_path):
    inst = _build_orchestrator(tmp_path, boardroom=_FakeBoardroom(_all_approve_session()))
    s = inst.status()
    skills = s["soldier_skills"]
    assert len(skills) == 8, f"expected 8 soldier skills, got {len(skills)}"
    soldier_ids = {sk["soldier_id"] for sk in skills}
    assert {"ceo", "cpo_product", "cto_technology", "coo_operations",
            "cfo_finance", "ciso_security", "clo_legal", "cro_risk"} == soldier_ids


def test_propose_campaign_happy_path_executes_skills(tmp_path):
    boardroom = _FakeBoardroom(_all_approve_session())
    inst = _build_orchestrator(tmp_path, boardroom=boardroom)
    brief = CampaignBrief(
        campaign_id="c-100",
        title="cognition you own",
        pillar="cognition_you_own",
        audience_ring="A",
        summary="Why mindX matters.",
    )
    result: CampaignResult = asyncio.run(inst.propose_campaign(
        brief, channel_set_mask=CH_LLMS_TXT,
    ))
    assert result.boardroom_outcome == "approved"
    assert result.boardroom_session_id == "br_t_1"
    assert result.refusal is None
    assert result.envelope.campaign_id == "c-100"
    assert result.envelope.boardroom_session_id == "br_t_1"
    # The dispatch should have run skills for every approving soldier in order.
    # Some soldiers may produce SkillOutput, others may produce SkillRefusal; here
    # we expect at least CPO + CTO + COO + CFO to produce outputs.
    out = result.skill_outputs
    for sid in ("cpo_product", "cto_technology", "coo_operations", "cfo_finance"):
        assert sid in out, f"missing skill output for {sid}"
    # Boardroom directive should reference the campaign
    assert "c-100" in (boardroom.last_directive or "")
    # llms_txt write should have produced two files
    out_files = list((tmp_path / "marketing" / "llms_txt").glob("*"))
    out_names = {p.name for p in out_files}
    assert "llms.txt" in out_names
    assert "llms-full.txt" in out_names


def test_ciso_veto_blocks_all_downstream_skills(tmp_path):
    session = _all_approve_session("br_veto_ciso")
    # Flip CISO to reject
    for v in session.votes:
        if v.soldier_id == "ciso_security":
            v.vote = "reject"
            v.reasoning = "voice violation simulated"
    boardroom = _FakeBoardroom(session)
    inst = _build_orchestrator(tmp_path, boardroom=boardroom)
    brief = CampaignBrief(
        campaign_id="c-101", title="t", pillar="cognition_you_own", audience_ring="A", summary="x",
    )
    result = asyncio.run(inst.propose_campaign(brief, channel_set_mask=CH_LLMS_TXT))
    assert result.refusal is not None
    assert result.refusal["reason"] == "soldier_veto"
    assert result.refusal["soldier"] == "ciso_security"
    # No skills should have run — empty skill_outputs
    assert result.skill_outputs == {}, f"skills ran despite veto: {list(result.skill_outputs)}"


def test_cro_veto_blocks_all_downstream_skills(tmp_path):
    session = _all_approve_session("br_veto_cro")
    for v in session.votes:
        if v.soldier_id == "cro_risk":
            v.vote = "reject"
            v.reasoning = "spend too high"
    boardroom = _FakeBoardroom(session)
    inst = _build_orchestrator(tmp_path, boardroom=boardroom)
    brief = CampaignBrief(
        campaign_id="c-102", title="t", pillar="cognition_you_own", audience_ring="A", summary="x",
    )
    result = asyncio.run(inst.propose_campaign(brief, channel_set_mask=CH_LLMS_TXT))
    assert result.refusal is not None
    assert result.refusal["reason"] == "soldier_veto"
    assert result.refusal["soldier"] == "cro_risk"
    assert result.skill_outputs == {}


def test_clo_alone_rejecting_does_not_short_circuit_when_outcome_approved(tmp_path):
    """CLO has no hard veto. If boardroom outcome is approved overall, the
    campaign proceeds; CLO's reject is recorded but doesn't block."""
    session = _all_approve_session("br_clo_dissent")
    for v in session.votes:
        if v.soldier_id == "clo_legal":
            v.vote = "reject"
    # Even with CLO rejecting, suppose the weighted score still hits supermajority
    boardroom = _FakeBoardroom(session)
    inst = _build_orchestrator(tmp_path, boardroom=boardroom)
    brief = CampaignBrief(
        campaign_id="c-103", title="t", pillar="cognition_you_own", audience_ring="A", summary="x",
    )
    result = asyncio.run(inst.propose_campaign(brief, channel_set_mask=CH_LLMS_TXT))
    assert result.refusal is None, "CLO has no hard veto; campaign should proceed"
    # CLO's skill should NOT have run because CLO didn't approve
    assert "clo_legal" not in result.skill_outputs


def test_overall_rejected_outcome_blocks_skills(tmp_path):
    session = _all_approve_session("br_rejected")
    session.outcome = "rejected"
    session.weighted_score = 0.4
    boardroom = _FakeBoardroom(session)
    inst = _build_orchestrator(tmp_path, boardroom=boardroom)
    brief = CampaignBrief(
        campaign_id="c-104", title="t", pillar="cognition_you_own", audience_ring="A", summary="x",
    )
    result = asyncio.run(inst.propose_campaign(brief, channel_set_mask=CH_LLMS_TXT))
    assert result.refusal is not None
    assert result.refusal["reason"] == "boardroom_outcome"
    assert result.skill_outputs == {}


def test_above_threshold_spend_records_in_envelope(tmp_path):
    """The orchestrator forwards forecast_spend_usd into the envelope (in micro)."""
    boardroom = _FakeBoardroom(_all_approve_session("br_spend"))
    inst = _build_orchestrator(tmp_path, boardroom=boardroom)
    brief = CampaignBrief(
        campaign_id="c-105", title="t", pillar="cognition_you_own", audience_ring="A", summary="x",
    )
    result = asyncio.run(inst.propose_campaign(
        brief, forecast_spend_usd=750.0, channel_set_mask=CH_LLMS_TXT,
    ))
    assert result.refusal is None
    assert result.envelope.total_spend_usd_micro == 750_000_000


def test_boardroom_convene_failure_returns_refusal(tmp_path):
    class BrokenBoardroom:
        async def convene(self, *args, **kw):
            raise RuntimeError("simulated convene crash")

    inst = _build_orchestrator(tmp_path, boardroom=BrokenBoardroom())
    brief = CampaignBrief(
        campaign_id="c-106", title="t", pillar="cognition_you_own", audience_ring="A", summary="x",
    )
    result = asyncio.run(inst.propose_campaign(brief, channel_set_mask=CH_LLMS_TXT))
    assert result.refusal is not None
    assert result.refusal["reason"] == "boardroom_convene_failed"
