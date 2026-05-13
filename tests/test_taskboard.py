# SPDX-License-Identifier: Apache-2.0
"""Tests for agents/mastermind/taskboard — Kanban + heartbeat + hallucination gate."""
from __future__ import annotations

import time

import pytest

from agents.mastermind.taskboard import COLUMNS, TaskBoard, TaskBoardError


@pytest.fixture
def board(tmp_path):
    return TaskBoard(db_path=tmp_path / "mastermind.db")


def _add(board, **kw):
    return board.add(
        title=kw.get("title", "verify a signature"),
        intention_template=kw.get("intention_template", "verify_sig_v1"),
        preconditions=kw.get("preconditions", ["wallet.connected"]),
        postconditions=kw.get("postconditions", ["belief.signer_verified=true"]),
        retry_budget=kw.get("retry_budget", 3),
        ttl_s=kw.get("ttl_s", 90),
        column=kw.get("column", "Triage"),
    )


# ─── CRUD ──────────────────────────────────────────────────


def test_add_and_get_round_trip(board):
    t = _add(board, title="round trip")
    got = board.get(t.id)
    assert got is not None
    assert got.title == "round trip"
    assert got.column == "Triage"
    assert got.postconditions == ["belief.signer_verified=true"]
    assert got.retry_budget == 3
    assert got.retries_used == 0


def test_list_and_board_grouping(board):
    _add(board, title="a")
    _add(board, title="b", column="Todo")
    _add(board, title="c", column="Done")
    grouped = board.board()
    assert set(grouped.keys()) >= set(COLUMNS)
    assert len(grouped["Triage"]) == 1
    assert len(grouped["Todo"]) == 1
    assert len(grouped["Done"]) == 1
    assert grouped["Triage"][0]["title"] == "a"


def test_transition_to_unknown_column_raises(board):
    t = _add(board)
    with pytest.raises(TaskBoardError):
        board.transition(t.id, to="Garbage")


def test_transition_to_inprogress_stamps_worker_and_heartbeat(board):
    t = _add(board, column="Todo")
    out = board.transition(t.id, to="InProgress", by="worker-1")
    assert out.column == "InProgress"
    assert out.worker == "worker-1"
    assert out.started_at is not None
    assert out.heartbeat_at is not None


# ─── heartbeat + zombie reclaim ───────────────────────────


def test_heartbeat_succeeds_for_owning_worker(board):
    t = _add(board)
    board.claim(t.id, worker="w1")
    assert board.heartbeat(t.id, worker="w1") is True
    refreshed = board.get(t.id)
    assert refreshed.heartbeat_at is not None


def test_heartbeat_rejected_for_other_worker(board):
    t = _add(board)
    board.claim(t.id, worker="w1")
    assert board.heartbeat(t.id, worker="impostor") is False


def test_reclaim_zombies_bounces_stale_inprogress_to_triage(board):
    t = _add(board, ttl_s=1)
    board.claim(t.id, worker="w1")
    # Simulate the worker going silent by re-running zombie reclaim with `now`
    # pushed forward.
    reclaimed = board.reclaim_zombies(now=time.time() + 5)
    assert t.id in reclaimed
    refreshed = board.get(t.id)
    assert refreshed.column == "Triage"
    assert refreshed.worker is None
    assert refreshed.retries_used == 1
    assert "zombie reclaim" in refreshed.notes


def test_reclaim_zombies_leaves_fresh_tasks_alone(board):
    t = _add(board, ttl_s=120)
    board.claim(t.id, worker="w1")
    reclaimed = board.reclaim_zombies()
    assert reclaimed == []
    assert board.get(t.id).column == "InProgress"


# ─── hallucination gate ────────────────────────────────────


def test_completion_gate_accepts_matching_postconditions(board):
    t = _add(board, postconditions=["belief.signer_verified=true", "belief.fees_paid=true"])
    board.claim(t.id, worker="w1")
    res = board.complete(
        t.id,
        claim={"signer_verified": True, "fees_paid": True},
        belief_state={"signer_verified": True, "fees_paid": True},
    )
    assert res.accepted is True
    assert set(res.matched_postconditions) == {"belief.signer_verified=true", "belief.fees_paid=true"}
    assert board.get(t.id).column == "Done"
    assert "completion gate" in board.get(t.id).notes


def test_completion_gate_bounces_on_missing_postcondition(board):
    t = _add(board, postconditions=["belief.signer_verified=true"])
    board.claim(t.id, worker="w1")
    res = board.complete(
        t.id,
        claim={"signer_verified": True},   # worker claims done
        belief_state={"signer_verified": False},   # but state contradicts
    )
    assert res.accepted is False
    assert "belief.signer_verified=true" in res.missing_postconditions
    refreshed = board.get(t.id)
    assert refreshed.column == "Triage"     # bounced, retries left
    assert refreshed.retries_used == 1
    assert "hallucination gate" in refreshed.notes


def test_completion_gate_blocks_after_retries_exhausted(board):
    t = _add(board, postconditions=["belief.x=true"], retry_budget=1)
    board.claim(t.id, worker="w1")
    board.complete(
        t.id,
        claim={"x": True},
        belief_state={"x": False},   # 1st (and last) retry — should go to Blocked
    )
    assert board.get(t.id).column == "Blocked"


def test_completion_gate_detects_contradicting_claim(board):
    t = _add(board, postconditions=[])   # no postconditions → only the claim check matters
    board.claim(t.id, worker="w1")
    res = board.complete(
        t.id,
        claim={"sent": True},
        belief_state={"sent": False},
    )
    assert res.accepted is False
    assert any("claim['sent']" in s for s in res.contradicting_claims)


def test_completion_gate_handles_belief_dot_prefix_and_bare_keys(board):
    """`belief.x=true` and `x=true` and bare `x` all mean the same thing."""
    t = _add(board, postconditions=[
        "belief.alpha=true",  # canonical
        "beta=true",          # without belief. prefix
        "gamma",              # bare key truthy
    ])
    board.claim(t.id, worker="w1")
    res = board.complete(
        t.id,
        claim={},
        belief_state={"alpha": True, "beta": True, "gamma": 1},
    )
    assert res.accepted is True
    assert board.get(t.id).column == "Done"


# ─── stats / reporting ─────────────────────────────────────


def test_stats_columns_count(board):
    _add(board, title="a")
    _add(board, title="b", column="Todo")
    _add(board, title="c", column="Done")
    s = board.stats()
    assert s["columns"]["Triage"] == 1
    assert s["columns"]["Todo"] == 1
    assert s["columns"]["Done"] == 1
    assert s["total"] == 3
    assert s["zombies"] == 0
