# SPDX-License-Identifier: Apache-2.0
"""Tests for the BDI ``_maybe_distill_skill`` hook.

The hook itself is a small bound method on ``BDIAgent`` that wraps
``distill_from_intention`` (already covered by ``tests/test_distill.py``).
The contract these tests pin:

  1. Opt-in via ``MINDX_BDI_DISTILL_ENABLED`` — off ⇒ no draft, no error.
  2. On ⇒ draft is written when thresholds are met.
  3. ``_snapshot_belief_keys`` survives a missing / malformed belief system
     (returns ``{}``).
  4. Hook never raises into the run loop on any internal failure.

We don't construct a real ``BDIAgent`` (it needs a full Coordinator stack +
memory_agent + LLM handler). Instead, we instantiate a stub that has just
the attributes the hook touches, and call the unbound methods directly.
"""
from __future__ import annotations

import asyncio
import logging
import types

import pytest

import agents.skills.index as idx_mod
from agents.core.bdi_agent import BDIAgent


def _stub_embed(text, *, timeout=5.0):
    if not text:
        return None
    return [0.1] * 8


def _make_stub_bdi(domain: str = "test_bdi") -> object:
    """Return an object that quacks like a BDIAgent for the hook's purposes."""
    self = types.SimpleNamespace()
    self.agent_id = "stub_agent"
    self.domain = domain
    self._internal_state = {}
    self.belief_system = types.SimpleNamespace()
    self.memory_agent = None
    self.logger = logging.getLogger("test.stub_bdi")
    # Bind the two helpers as unbound coroutines on this stub instance.
    self._snapshot_belief_keys = BDIAgent._snapshot_belief_keys.__get__(self, type(self))
    self._maybe_distill_skill = BDIAgent._maybe_distill_skill.__get__(self, type(self))
    return self


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(idx_mod, "_embed_text", _stub_embed)
    monkeypatch.setenv("MINDX_SKILLS_DIR", str(tmp_path / "skills"))


# ── opt-in gate ─────────────────────────────────────────────


def test_hook_is_no_op_when_disabled(monkeypatch, tmp_path):
    monkeypatch.delenv("MINDX_BDI_DISTILL_ENABLED", raising=False)
    bdi = _make_stub_bdi()
    bdi._internal_state["actions_this_run"] = [
        {"tool": "a"}, {"tool": "b"}, {"tool": "a"}, {"tool": "b"}, {"tool": "a"}, {"tool": "b"},
    ]
    bdi._internal_state["beliefs_before_run"] = {}
    asyncio.run(bdi._maybe_distill_skill({"goal": "demo"}, "run-1"))
    # No draft on disk
    drafts = (tmp_path / "skills" / ".drafts")
    assert not drafts.exists() or not any(drafts.rglob("SKILL.md"))


def test_hook_writes_draft_when_enabled_and_thresholds_met(monkeypatch, tmp_path):
    monkeypatch.setenv("MINDX_BDI_DISTILL_ENABLED", "1")
    bdi = _make_stub_bdi()
    bdi._internal_state["actions_this_run"] = [
        {"tool": "a"}, {"tool": "b"}, {"tool": "a"}, {"tool": "b"}, {"tool": "a"}, {"tool": "b"},
    ]
    bdi._internal_state["beliefs_before_run"] = {}
    asyncio.run(bdi._maybe_distill_skill({"goal": "verify a signature"}, "run-2"))
    drafts = tmp_path / "skills" / ".drafts"
    found = list(drafts.rglob("SKILL.md")) if drafts.exists() else []
    assert found, f"expected a draft under {drafts}; got nothing"


def test_hook_skips_when_below_step_threshold(monkeypatch, tmp_path):
    monkeypatch.setenv("MINDX_BDI_DISTILL_ENABLED", "1")
    bdi = _make_stub_bdi()
    bdi._internal_state["actions_this_run"] = [{"tool": "a"}]   # 1 < min_steps=5
    bdi._internal_state["beliefs_before_run"] = {}
    asyncio.run(bdi._maybe_distill_skill({"goal": "tiny"}, "run-3"))
    drafts = tmp_path / "skills" / ".drafts"
    assert not drafts.exists() or not any(drafts.rglob("SKILL.md"))


# ── snapshot_belief_keys defensive paths ──────────────────


def test_snapshot_returns_empty_when_belief_system_missing_methods():
    bdi = _make_stub_bdi()
    # bdi.belief_system has no get_all_beliefs / list_beliefs ⇒ {}
    out = asyncio.run(bdi._snapshot_belief_keys())
    assert out == {}


def test_snapshot_handles_get_all_beliefs(monkeypatch):
    bdi = _make_stub_bdi(domain="test_dom")

    async def fake_get_all_beliefs():
        return [
            {"key": "bdi.test_dom.beliefs.signer_verified", "value": True},
            {"key": "bdi.test_dom.beliefs.fee_known",       "value": 0.0},      # falsy
            {"key": "bdi.other_dom.beliefs.elsewhere",       "value": "ignored"},
        ]
    bdi.belief_system.get_all_beliefs = fake_get_all_beliefs
    out = asyncio.run(bdi._snapshot_belief_keys())
    assert out.get("signer_verified") is True
    assert out.get("fee_known") is False
    # Cross-domain keys still come through (we don't filter strictly), but the
    # prefix-stripping only applies to keys in our domain.
    assert "bdi.other_dom.beliefs.elsewhere" in out or "elsewhere" in out


# ── error containment ─────────────────────────────────────


def test_hook_swallows_internal_errors(monkeypatch):
    """Any failure inside _maybe_distill_skill must not raise to the caller."""
    monkeypatch.setenv("MINDX_BDI_DISTILL_ENABLED", "1")
    bdi = _make_stub_bdi()
    # Force a corrupt actions list — non-dict entries — and make sure no exception escapes.
    bdi._internal_state["actions_this_run"] = ["not a dict", None, 42]
    bdi._internal_state["beliefs_before_run"] = None       # also wrong type
    # Should complete without raising.
    asyncio.run(bdi._maybe_distill_skill({"goal": "robust"}, "run-bad"))
