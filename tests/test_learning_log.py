# SPDX-License-Identifier: Apache-2.0
"""Tests for `agents/skills/learning_log` — the OpenClaw self-improving-agent
log pattern (§3.1) ported into mindX.

Covers: append into each of the three logs (LEARNINGS/ERRORS/FEATURE_REQUESTS),
parse round-trip across atomic rewrite, status transitions (pending →
validated → promoted), promotion-to-Skill path with scanner gate (the
scanner refuses to promote a learning that contains an instruction-override
or destructive command).
"""
from __future__ import annotations

import pytest

import agents.skills.index as idx_mod
from agents.skills.learning_log import LearningLog
from agents.skills.store import SkillStore, SkillStoreError


def _stub_embed(text, *, timeout=5.0):
    # Deterministic 8-dim vector so the SkillIndex never hits the network.
    if not text:
        return None
    seed = sum(ord(c) for c in text) % 997
    return [((seed * (i + 1)) % 100) / 100.0 for i in range(8)]


@pytest.fixture
def log(tmp_path):
    return LearningLog(root=tmp_path / "learnings")


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(idx_mod, "_embed_text", _stub_embed)
    return SkillStore(root=tmp_path / "skills")


# ─── append ──────────────────────────────────────────────────────


def test_append_into_each_log(log):
    a = log.append(
        kind="learning", trigger="better_approach_found",
        title="Boardroom soldier sign-in lapses after 24h",
        body="I refresh `/insight/boardroom/cloud_signin` on every 6th hour instead — the rollcall now passes 7/7.",
        agent_id="boardroom",
        tags=["boardroom", "ollama-cloud"],
    )
    b = log.append(
        kind="error", trigger="tool_failed",
        title="token_calculator_tool UnboundLocalError",
        body="`timeout` was assigned inside an `if`. Fixed at agents/monitoring/token_calculator_tool.py.",
    )
    c = log.append(
        kind="feature_request", trigger="missing_capability",
        title="Per-publisher allowlist on /publish/rage",
        body="Today: a single `WORDPRESS_PUBLISHER_ADDRESSES`. Want: per-author throttle.",
    )
    assert a.id and b.id and c.id
    assert {e.id for e in log.list()} == {a.id, b.id, c.id}
    assert log.list(kind="error")[0].id == b.id


def test_append_round_trip_preserves_fields(log):
    e = log.append(
        kind="learning", trigger="user_correction",
        title="cypherpunk vs cyberpunk",
        body="Per user: mindX uses the cypherpunk tradition (Hughes 1993), not the cyberpunk literary one.",
        agent_id="author_agent",
        tags=["voice", "identity"],
    )
    got = log.get("learning", e.id)
    assert got is not None
    assert got.title == e.title
    assert got.body == e.body
    assert got.tags == ["voice", "identity"]
    assert got.agent_id == "author_agent"
    assert got.status == "pending"


# ─── status transitions ────────────────────────────────────────


def test_status_transitions(log):
    e = log.append(
        kind="learning", trigger="better_approach_found",
        title="Stub", body="stub",
    )
    assert log.get("learning", e.id).status == "pending"
    assert log.update_status("learning", e.id, "validated")
    assert log.get("learning", e.id).status == "validated"
    assert log.update_status("learning", e.id, "promoted")
    got = log.get("learning", e.id)
    assert got.status == "promoted"
    assert got.promoted_at is not None


def test_update_unknown_returns_false(log):
    assert log.update_status("error", "no-such-id", "validated") is False


# ─── promotion → SkillStore ────────────────────────────────────


def test_promotion_creates_skill_and_marks_entry(log, store):
    e = log.append(
        kind="learning", trigger="better_approach_found",
        title="Boardroom sign-in refresh cadence",
        body="Refresh ollama-cloud signin every 6h. 7/7 soldiers pass roll-call.",
        agent_id="boardroom",
        tags=["boardroom"],
    )
    sk = log.promote_to_skill(
        "learning", e.id,
        store=store,
        category="boardroom",
        intention_template="refresh_signin_v1",
        postconditions=["belief.signin_fresh=true"],
        created_by="human",
    )
    assert sk is not None
    # The skill exists in the store
    on_disk = store.read("boardroom", sk.slug)
    assert on_disk is not None
    assert "ollama-cloud" in on_disk.body or "signin" in on_disk.body.lower()
    # The entry was marked promoted with the skill reference
    got = log.get("learning", e.id)
    assert got.status == "promoted"
    assert got.related_skill == f"boardroom/{sk.slug}"


def test_promotion_refused_when_scanner_blocks(log, store):
    """A learning whose body contains a destructive command must NOT promote —
    the SkillStore scanner is the final gate."""
    e = log.append(
        kind="learning", trigger="better_approach_found",
        title="Cleanup recipe",
        body="When the disk is full, run `sudo rm -rf /var/lib/something` then restart.",
    )
    # Even with human + pinned-ish settings, "rm -rf /var" is a `destructive_command`
    # which is a BLOCK class — scanner refuses.
    with pytest.raises(SkillStoreError):
        log.promote_to_skill("learning", e.id, store=store, created_by="human")
    # Entry remains pending (not promoted)
    assert log.get("learning", e.id).status == "pending"


# ─── summary ───────────────────────────────────────────────────


def test_summary_counts(log):
    log.append(kind="learning", trigger="user_correction", title="a", body="b")
    log.append(kind="learning", trigger="user_correction", title="c", body="d")
    log.append(kind="error",    trigger="tool_failed",     title="e", body="f")
    summary = log.summary()
    assert summary["learning"]["pending"] == 2
    assert summary["learning"]["total"] == 2
    assert summary["error"]["pending"] == 1
    assert summary["feature_request"]["total"] == 0
