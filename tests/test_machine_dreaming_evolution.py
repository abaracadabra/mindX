"""Unit test for MachineDreamCycle._write_evolution_proposals (phase 5c).

Plants synthetic DreamInsight objects with explicit pattern types and
scores, runs the proposal writer, and asserts the JSONL is well-formed
and consumable by mindXtrain's mindx_dreams data adapter.

Run from the mindX repo root:

    .mindx_env/bin/python -m pytest tests/test_machine_dreaming_evolution.py -v --no-cov
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    """Point PROJECT_ROOT at a temp tree so the writer doesn't touch the real LTM."""
    (tmp_path / "data" / "memory" / "ltm").mkdir(parents=True)
    monkeypatch.setattr("agents.machine_dreaming.PROJECT_ROOT", tmp_path)
    return tmp_path


def _make_cycle():
    """Build a bare MachineDreamCycle without touching the rest of mindX.

    The phase-5c method is self-contained — it doesn't need the LLM,
    memory agent, or pgvector — so we can construct the class via
    `object.__new__` and skip __init__.
    """
    from agents.machine_dreaming import MachineDreamCycle

    cycle = object.__new__(MachineDreamCycle)
    cycle.log_prefix = "[test]"
    return cycle


def _make_insight(*, pattern_type: str, description: str, score: float,
                  frequency: int = 5):
    """Build a DreamInsight whose computed `score` property is roughly the
    target — `score` is `importance * novelty * confidence * log10(freq+1)`,
    so we hold importance/novelty/confidence constant and let frequency
    differentiate. Exact match isn't important for these tests — only the
    relative ordering for the top-N selection.
    """
    from agents.machine_dreaming import DreamInsight
    return DreamInsight(
        pattern_type=pattern_type,
        description=description,
        importance=0.8,
        novelty=0.8,
        confidence=0.8,
        frequency=frequency,
    )


def test_writes_jsonl_for_actionable_insights(isolated_project):
    cycle = _make_cycle()
    insights = [
        _make_insight(pattern_type="failure",
                      description="tool call timeouts in slack route",
                      score=0.85),
        _make_insight(pattern_type="performance",
                      description="p50 latency creeping up",
                      score=0.74),
        _make_insight(pattern_type="behavioral",
                      description="prefers conservative model on uncertainty",
                      score=0.62),
        _make_insight(pattern_type="success",
                      description="planning cycle stable",
                      score=0.55),
    ]
    count, rel_path = asyncio.run(
        cycle._write_evolution_proposals("agent_test", insights),
    )
    assert count == 3  # success skipped, others kept
    out = isolated_project / rel_path
    assert out.exists()
    lines = out.read_text().strip().split("\n")
    assert len(lines) == 3
    for line in lines:
        row = json.loads(line)
        # Each row is OpenAI-chat shape — mindXtrain's adapter requirement.
        assert "messages" in row
        assert {m["role"] for m in row["messages"]} == {"system", "user", "assistant"}
        # The assistant turn parses to a structured proposal.
        proposal = json.loads(row["messages"][-1]["content"])
        assert proposal["type"] in {
            "strategy", "configuration", "prompt_change", "tool_change", "rollback",
        }
        assert proposal["target_agent"] == "agent_test"
        assert 0.0 <= proposal["confidence"] <= 1.0


def test_skips_when_too_few_insights(isolated_project):
    cycle = _make_cycle()
    insights = [
        _make_insight(pattern_type="failure", description="x", score=0.5),
        _make_insight(pattern_type="performance", description="y", score=0.5),
    ]
    count, rel = asyncio.run(cycle._write_evolution_proposals("agent_a", insights))
    assert count == 0
    assert rel == ""


def test_skips_when_no_actionable_insights(isolated_project):
    cycle = _make_cycle()
    # All success or cross_agent — synthesis should skip.
    insights = [
        _make_insight(pattern_type="success", description=f"s{i}", score=0.7)
        for i in range(5)
    ]
    count, rel = asyncio.run(cycle._write_evolution_proposals("agent_a", insights))
    assert count == 0
    assert rel == ""


def test_filename_lives_alongside_training_jsonl(isolated_project):
    cycle = _make_cycle()
    insights = [
        _make_insight(pattern_type="failure", description="a", score=0.9),
        _make_insight(pattern_type="failure", description="b", score=0.8),
        _make_insight(pattern_type="failure", description="c", score=0.7),
    ]
    _, rel = asyncio.run(cycle._write_evolution_proposals("agent_a", insights))
    assert rel.endswith("_evolutions.jsonl")
    assert "/ltm/agent_a/" in rel


def test_assistant_proposal_type_maps_pattern(isolated_project):
    """failure → rollback, performance → configuration, behavioral → strategy."""
    cycle = _make_cycle()
    type_to_proposal = {}
    for pt in ("failure", "performance", "behavioral"):
        insights = [
            _make_insight(pattern_type=pt, description=f"{pt}-1", score=0.9),
            _make_insight(pattern_type=pt, description=f"{pt}-2", score=0.8),
            _make_insight(pattern_type=pt, description=f"{pt}-3", score=0.7),
        ]
        # Rebuild fresh tmp so files don't clash
        _, rel = asyncio.run(cycle._write_evolution_proposals(f"agent_{pt}", insights))
        body = (isolated_project / rel).read_text().strip().split("\n")
        proposal = json.loads(json.loads(body[0])["messages"][-1]["content"])
        type_to_proposal[pt] = proposal["type"]
    assert type_to_proposal == {
        "failure": "rollback",
        "performance": "configuration",
        "behavioral": "strategy",
    }
