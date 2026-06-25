"""Tests for the Dojo consensus-arbitration service (daio/governance/dojo_arbiter.py).

Covers each variable consensus model, every source normalizer, the dissent path,
and the three-sink recording (own ledger + hash-linked VotingBooth) with isolated
tmp paths and the catalogue emitter disabled.
"""
from __future__ import annotations

import asyncio
import json
import os

import pytest

from daio.governance import dojo_arbiter as A
from daio.governance.dojo_arbiter import Ballot, DojoArbiter


def _b(origin, vote, *, voter="x", weight=1.0, confidence=1.0, seat=None, group=None):
    return Ballot(origin=origin, voter=voter, vote=vote, weight=weight,
                  confidence=confidence, seat=seat, group=group)


# ── consensus models ────────────────────────────────────────────────────────
def test_supermajority_approves_above_threshold():
    ballots = [_b("boardroom", "approve", confidence=0.95) for _ in range(3)]
    decision, score, threshold, _ = A._cm_supermajority(ballots)
    assert decision == "approved" and score >= threshold == A.SUPERMAJORITY_THRESHOLD


def test_supermajority_mixed_below_threshold_is_exploration():
    # approve weight ~ 1.0, reject weight ~ 1.0 → score 0.5 < 0.666, both sides > 0
    ballots = [_b("boardroom", "approve", confidence=1.0),
               _b("boardroom", "reject", confidence=1.0)]
    decision, score, _, _ = A._cm_supermajority(ballots)
    assert decision == "exploration" and abs(score - 0.5) < 1e-9


def test_supermajority_all_reject_is_rejected():
    decision, *_ = A._cm_supermajority([_b("boardroom", "reject")])
    assert decision == "rejected"


def test_no_quorum_when_all_abstain():
    decision, score, *_ = A._cm_supermajority([_b("boardroom", "abstain")])
    assert decision == "no_quorum" and score == 0.0


def test_weighted_confidence_is_decisive_no_exploration():
    d_app, *_ = A._cm_weighted_confidence([_b("mindxtrain", "approve", confidence=0.9),
                                           _b("boardroom", "reject", confidence=0.4)])
    d_rej, *_ = A._cm_weighted_confidence([_b("mindxtrain", "reject", confidence=0.9),
                                           _b("boardroom", "approve", confidence=0.4)])
    assert d_app == "approved" and d_rej == "rejected"


def test_prime_ladder_delegates_and_never_deadlocks():
    # 2 approve seats vs 1 reject → war-council guarantees a decisive verdict
    ballots = [_b("warcouncil", "approve", seat=0), _b("warcouncil", "approve", seat=6),
               _b("warcouncil", "reject", seat=3)]
    decision, score, threshold, detail = A._cm_prime_ladder(ballots, stakes=0)
    assert decision in ("approved", "rejected")  # never exploration / no_quorum on a real split
    assert "weighted" in detail


def test_two_of_three_groups():
    ballots = [
        _b("daio", "approve", group="marketing"), _b("daio", "approve", group="marketing"),
        _b("daio", "approve", group="community"), _b("daio", "reject", group="community"),
        _b("daio", "reject", group="development"), _b("daio", "reject", group="development"),
    ]
    # marketing approves (2-0), community ties (1-1 → not approved), development rejects
    decision, score, threshold, _ = A._cm_two_of_three(ballots)
    assert threshold == pytest.approx(2 / 3)
    assert decision == "rejected" and score == pytest.approx(1 / 3)


def test_quorum_headcount_majority():
    decision, score, *_ = A._cm_quorum([_b("manual", "approve"), _b("manual", "approve"),
                                        _b("manual", "reject")])
    assert decision == "approved" and score == pytest.approx(2 / 3)


# ── normalizers ─────────────────────────────────────────────────────────────
def test_from_boardroom_dict_session():
    session = {"votes": [{"soldier_id": "cro_risk", "vote": "reject", "confidence": 0.7,
                          "reasoning": "risk"}, {"soldier_id": "cto_technology", "vote": "approve",
                          "confidence": 0.8}]}
    ballots = A.from_boardroom(session)
    assert len(ballots) == 2 and all(b.origin == "boardroom" for b in ballots)
    # cro_risk default weight comes from SOLDIER_WEIGHTS
    assert ballots[0].weight == A.SOLDIER_WEIGHTS["cro_risk"]


def test_from_warcouncil_preserves_seat():
    ballots = A.from_warcouncil([{"seat": 3, "role": "security", "vote": "reject"}])
    assert ballots[0].seat == 3 and ballots[0].voter == "security" and ballots[0].origin == "warcouncil"


def test_from_mindxtrain_accept_and_reject():
    acc = A.from_mindxtrain({"accepted": True, "delta": 0.05})
    rej = A.from_mindxtrain({"accepted": False, "delta": -0.01})
    assert acc[0].vote == "approve" and acc[0].origin == "mindxtrain"
    assert rej[0].vote == "reject"
    # confidence scales with |delta|
    assert acc[0].confidence == pytest.approx(min(1.0, 0.05 * 10.0))


def test_from_daio_groups():
    ballots = A.from_daio({"marketing": {"human_1": True, "ai": False}})
    assert {b.vote for b in ballots} == {"approve", "reject"}
    assert all(b.group == "marketing" for b in ballots)


# ── dissent ─────────────────────────────────────────────────────────────────
def test_dissent_branches_from_rejects():
    ballots = [_b("boardroom", "approve"), _b("boardroom", "reject", voter="cro_risk",
                                              confidence=0.6)]
    branches = A._dissent_branches(ballots, "exploration")
    assert len(branches) == 1 and branches[0]["voter"] == "cro_risk"


# ── end-to-end decide + recording (isolated tmp) ────────────────────────────
def test_decide_records_to_ledger_and_booth(tmp_path, monkeypatch):
    monkeypatch.setenv("MINDX_CATALOGUE_DISABLE", "1")
    # isolate the booth
    from openagents.ephermaleth.ephermaleth.votingbooth import VotingBooth
    booth = VotingBooth(tmp_path / "votingbooth.jsonl")
    import agents.provenance_chain as pc
    monkeypatch.setattr(pc, "council_booth", lambda: booth)

    arb = DojoArbiter()
    arb.decisions_file = tmp_path / "dojo_decisions.jsonl"

    rec = asyncio.run(arb.decide(
        subject="promote gen7",
        ballots=[{"origin": "mindxtrain", "vote": "approve", "confidence": 0.9},
                 {"origin": "boardroom", "voter": "cro_risk", "vote": "reject", "confidence": 0.7}],
        consensus_model="supermajority"))

    assert rec["decision"] in ("approved", "rejected", "exploration")
    assert rec["record_hash"].startswith("0x")
    # ledger line written, and it carries the record_hash (ordering fix)
    lines = (tmp_path / "dojo_decisions.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["record_hash"] == rec["record_hash"]
    # booth recorded + hash-linked from genesis
    booth_recs = booth.list(council="dojo")
    assert len(booth_recs) == 1 and booth_recs[0]["prev"] == "0x0"
    # recent() reads it back
    assert arb.recent(5)[0]["subject"] == "promote gen7"


def test_decide_unknown_model_raises():
    with pytest.raises(ValueError):
        asyncio.run(A.decide(subject="x", ballots=[{"origin": "manual", "vote": "approve"}],
                             consensus_model="nope", record=False))
