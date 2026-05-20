# SPDX-License-Identifier: Apache-2.0
"""Tests for `agents/skills/distill` — the BDI intention → Skill helper.

Covers:
  * success_signal=False short-circuits.
  * Step thresholds (min_steps / min_unique_tools) gate the call.
  * Successful distillation writes a draft when ``draft_only=True``.
  * ``draft_only=False`` writes through the SkillStore (scanner gate applies).
  * Scanner refuses to distill a body that contains a destructive command —
    the helper returns a DistillationResult with reason but no skill.
  * Postconditions are computed from belief diffs.
"""
from __future__ import annotations

import pytest

import agents.skills.index as idx_mod
from agents.skills.distill import (
    DEFAULT_MIN_STEPS,
    DEFAULT_MIN_UNIQUE_TOOLS,
    distill_from_intention,
)
from agents.skills.store import SkillStore


def _stub_embed(text, *, timeout=5.0):
    if not text:
        return None
    seed = sum(ord(c) for c in text) % 997
    return [((seed * (i + 1)) % 100) / 100.0 for i in range(8)]


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(idx_mod, "_embed_text", _stub_embed)
    monkeypatch.setenv("MINDX_SKILLS_DIR", str(tmp_path / "skills"))


@pytest.fixture
def store(tmp_path):
    return SkillStore(root=tmp_path / "skills")


def _steps(n: int, tools=("a", "b", "c")):
    return [{"tool": tools[i % len(tools)], "args": {"i": i}, "result": "ok"} for i in range(n)]


# ── threshold gates ─────────────────────────────────────────


def test_refuses_when_no_success_signal():
    r = distill_from_intention(intention_id="i-1", success_signal=False, steps=_steps(10))
    assert r.skill is None and "success_signal" in r.reason


def test_refuses_when_too_few_steps():
    r = distill_from_intention(intention_id="i-1", success_signal=True, steps=_steps(DEFAULT_MIN_STEPS - 1))
    assert r.skill is None and "too few steps" in r.reason


def test_refuses_when_too_few_unique_tools():
    r = distill_from_intention(
        intention_id="i-1", success_signal=True,
        steps=_steps(DEFAULT_MIN_STEPS, tools=("one_tool",)),
    )
    assert r.skill is None and "unique tools" in r.reason


# ── draft path ──────────────────────────────────────────────


def test_writes_draft_by_default(tmp_path):
    r = distill_from_intention(
        intention_id="verify-sig-001",
        intention_template="verify_wallet_sig_v1",
        title="Verify Wallet Sig",
        success_signal=True,
        beliefs_before={},
        beliefs_after={"signer_verified": True},
        steps=_steps(6),
        agent_id="boardroom",
    )
    assert r.skill is not None
    assert r.draft_path is not None and r.draft_path.exists()
    assert ".drafts" in str(r.draft_path)
    # Postcondition was derived from the belief diff
    assert any(p == "belief.signer_verified=true" for p in r.skill.frontmatter.postconditions)
    assert r.skill.frontmatter.intention_template == "verify_wallet_sig_v1"


def test_draft_only_does_not_pollute_live_store(tmp_path, store):
    distill_from_intention(
        intention_id="i-x", success_signal=True, title="X", steps=_steps(6),
        beliefs_after={"x": True},
    )
    # Live store has zero skills (only the draft tree was touched).
    assert store.list() == []


# ── live promotion path ─────────────────────────────────────


def test_live_promotion_writes_to_store(store):
    r = distill_from_intention(
        intention_id="i-2", success_signal=True,
        title="Direct Promote", steps=_steps(6),
        beliefs_after={"done": True},
        draft_only=False, store=store,
    )
    assert r.skill is not None
    assert r.promoted_path is not None and r.promoted_path.exists()
    assert store.read("agent-distilled", r.skill.slug) is not None


def test_live_promotion_requires_store():
    r = distill_from_intention(
        intention_id="i-3", success_signal=True,
        title="No store", steps=_steps(6),
        beliefs_after={"done": True},
        draft_only=False, store=None,
    )
    assert r.skill is None and "requires a SkillStore" in r.reason


# ── scanner gate ────────────────────────────────────────────


def test_scanner_blocks_malicious_distilled_body():
    # Forge step content that lands "sudo rm -rf /var" into the body — the
    # body composer surfaces step content verbatim, so this trips the scanner.
    # Use ≥2 unique tools so we pass the threshold gate and reach the scanner.
    r = distill_from_intention(
        intention_id="bad",
        success_signal=True,
        title="bad",
        steps=[
            {"tool": "shell",   "args": {"cmd": "sudo rm -rf /var/foo"}, "result": "ok"},
            {"tool": "process", "args": {"cmd": "ls"},                    "result": "ok"},
            {"tool": "shell",   "args": {"cmd": "more"},                  "result": "ok"},
            {"tool": "process", "args": {"cmd": "stat"},                  "result": "ok"},
            {"tool": "shell",   "args": {"cmd": "cat"},                   "result": "ok"},
            {"tool": "process", "args": {"cmd": "wc"},                    "result": "ok"},
        ],
        beliefs_after={"done": True},
    )
    assert r.skill is None
    assert "scanner refused" in r.reason.lower()
