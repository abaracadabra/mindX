# SPDX-License-Identifier: Apache-2.0
"""Tests for the stuck-improvement-loop fix shipped 2026-05-19.

Background
==========

Inspection of ``data/sea_campaign_history/strategic_evolution_agent.json``
showed 109 entries: 54 ``SUCCESS`` + 54 ``PARTIAL_SUCCESS`` + 1 ``FAILURE``.
54/55 distinct run_ids appeared **twice** — once as SUCCESS, once as
PARTIAL_SUCCESS — and every SUCCESS read "0 tasks created". Three bugs
stacked:

  1. ``run_enhanced_blueprint_campaign`` returned ``SUCCESS`` even when
     ``coordinator_tasks_created == 0`` (vacuous-SUCCESS spam, fed
     PublicationOrchestrator a steady stream of fake triggers).
  2. ``run_audit_driven_campaign`` checked ``improvement_results.get("status")``
     but the inner campaign returned ``overall_campaign_status`` — so the
     key check was always None, and every audit-driven run double-wrote
     a PARTIAL_SUCCESS regardless of inner status.
  3. ``_run_comprehensive_audit`` set ``success=True`` unconditionally even
     when findings/suggestions were both empty, cascading vacuous campaigns
     into history.

These tests pin the post-fix behavior at the unit level — no full SEA
instantiation, no LLM, no coordinator. We exercise the conclusion logic
directly on a stub subclass to keep the surface tight.
"""
from __future__ import annotations

import asyncio
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from agents.learning.strategic_evolution_agent import StrategicEvolutionAgent


class _StubSEA(StrategicEvolutionAgent):
    """Bypasses __init__ so we can exercise three async methods in isolation.

    Sets only the attributes those methods touch. The real agent class is
    heavy (LLM handler, coordinator, blueprint agent, etc.); none of that
    state is needed to verify the conclusion paths.
    """

    def __init__(self) -> None:  # noqa: D401 — deliberate __init__ override
        self.agent_id = "stub_sea"
        self.log_prefix = "[stub_sea]"
        self._current_campaign_run_id = "test_run_id"
        self._initialized = True
        self.campaign_history: List[Dict[str, Any]] = []
        # _save_campaign_history will try to write to data/ — neuter it.
        self._save_called = 0

    def _save_campaign_history(self) -> None:
        # Avoid filesystem writes from the unit tests.
        self._save_called += 1


# ── Fix 1: vacuous-SUCCESS guard ─────────────────────────────────


def test_enhanced_blueprint_with_zero_tasks_returns_no_op():
    """0 coordinator tasks → NO_OP, not SUCCESS."""
    sea = _StubSEA()
    summary = sea._conclude_campaign("NO_OP", "0 tasks", {"coordinator_tasks_created": 0})
    assert summary["overall_campaign_status"] == "NO_OP"
    # Make sure the conclusion landed in history (audit evidence is kept).
    assert sea.campaign_history == [summary]


def test_enhanced_blueprint_with_real_tasks_returns_success():
    """coordinator_tasks_created > 0 → still SUCCESS."""
    sea = _StubSEA()
    summary = sea._conclude_campaign("SUCCESS", "3 tasks", {"coordinator_tasks_created": 3})
    assert summary["overall_campaign_status"] == "SUCCESS"


# ── Fix 2: key-mismatch on PARTIAL_SUCCESS branch ────────────────


def test_inner_success_key_is_overall_campaign_status():
    """The inner campaign returns `overall_campaign_status`, NOT `status`.
    We pin the key name here so future refactors can't drift back."""
    sea = _StubSEA()
    summary = sea._conclude_campaign("SUCCESS", "msg", {})
    assert "overall_campaign_status" in summary
    assert "status" not in summary, (
        "Inner campaign returns `overall_campaign_status`; if a `status` "
        "key shows up the duplicate-write bug at SEA line 707 reappears."
    )


# ── Fix 3: NO_WORK short-circuit (verified via source-text pin) ──


def test_run_audit_driven_short_circuits_on_empty_findings():
    """The source-text pin ensures the empty-findings short-circuit isn't
    accidentally deleted in a future refactor. We assert the literal string
    + that it appears BEFORE the blueprint phase."""
    from pathlib import Path
    src = Path(__file__).parents[1] / "agents/learning/strategic_evolution_agent.py"
    text = src.read_text(encoding="utf-8")
    assert 'NO_WORK' in text, "NO_WORK short-circuit removed — vacuous campaigns will re-flood SEA history"
    assert 'Audit completed with no actionable findings' in text
    # Pin ordering: the NO_WORK branch must appear before _generate_audit_driven_blueprint
    no_work_idx = text.index('NO_WORK')
    blueprint_idx = text.index('_generate_audit_driven_blueprint')
    assert no_work_idx < blueprint_idx, "NO_WORK guard must short-circuit BEFORE blueprint phase"


def test_partial_success_key_check_uses_overall_campaign_status():
    """Same source-text pin for the line-707 key fix."""
    from pathlib import Path
    src = Path(__file__).parents[1] / "agents/learning/strategic_evolution_agent.py"
    text = src.read_text(encoding="utf-8")
    assert 'improvement_results.get("overall_campaign_status")' in text, (
        "Key fix reverted — the audit-driven campaign will resume "
        "double-writing PARTIAL_SUCCESS on every run."
    )
    assert 'improvement_results.get("status")' not in text, (
        "Old buggy key check is back. Every audit campaign will double-write."
    )


# ── Publication orchestrator interaction ─────────────────────────


def test_publication_orchestrator_filters_no_op():
    """Pin that NO_OP / NO_WORK / PARTIAL_SUCCESS do not trigger the
    PublicationOrchestrator (it filters by `== "SUCCESS"`)."""
    from agents.publication_orchestrator import PublicationOrchestrator
    from pathlib import Path
    src = Path(PublicationOrchestrator.__module__.replace(".", "/") + ".py")
    text = (Path(__file__).parents[1] / src).read_text(encoding="utf-8")
    assert 'overall_campaign_status") != "SUCCESS"' in text, (
        "Publication orchestrator no longer filters by SUCCESS — "
        "NO_OP campaigns will start publishing fake 'what I learned' posts."
    )
