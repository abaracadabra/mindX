# SPDX-License-Identifier: Apache-2.0
"""Tests for agents/publication_orchestrator.py.

Pins:
  * Ledger persistence + reload round-trip
  * Idempotency: same trigger_id seen twice → publishes once
  * Rate limit: a second trigger within MIN_GAP_S is coalesced
  * Jitter bounds: delay always in [base*(1-frac), base*(1+frac)]
  * SEA payload → article composition (title, body, excerpt, topic)
  * Dream payload → article composition
  * publish_to_rage returning None does NOT update the ledger
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from agents.publication_orchestrator import (
    DEFAULT_JITTER_FRACTION,
    DEFAULT_MIN_GAP_S,
    Ledger,
    LedgerEntry,
    PublicationOrchestrator,
)


# ─── A no-op AuthorAgent stand-in for the orchestrator ───────────


_SENTINEL_DEFAULT = object()


class _FakeAuthor:
    """Records every call. ``return_value`` controls what publish_to_rage
    returns; ``calls`` captures kwargs for assertions. Pass ``None`` to
    simulate the wordpress-agent being down — the sentinel default
    distinguishes that from 'caller didn't specify'."""

    def __init__(self, return_value: Any = _SENTINEL_DEFAULT):
        if return_value is _SENTINEL_DEFAULT:
            self.return_value: Optional[Dict[str, Any]] = {
                "post_id": 42,
                "url": "https://rage.pythai.net/?p=42",
                "status": "draft",
                "slug": "test-slug",
                "date_gmt": "2026-05-13T12:00:00",
            }
        else:
            self.return_value = return_value
        self.calls: List[Dict[str, Any]] = []

    async def publish_to_rage(self, **kwargs):
        self.calls.append(kwargs)
        return self.return_value


def _orchestrator_with_tmp_paths(
    tmp_path: Path,
    author: _FakeAuthor,
    *,
    base_delay_s: float = 0.0,
    jitter_fraction: float = 0.0,
    min_gap_s: float = DEFAULT_MIN_GAP_S,
    poll_interval_s: float = 0.05,
) -> PublicationOrchestrator:
    sea_history = tmp_path / "sea_history.json"
    dream_dir   = tmp_path / "dreams"
    ledger_path = tmp_path / "ledger.json"
    dream_dir.mkdir()
    return PublicationOrchestrator(
        author_agent=author,
        sea_history_path=sea_history,
        dream_dir=dream_dir,
        ledger_path=ledger_path,
        base_delay_s=base_delay_s,
        jitter_fraction=jitter_fraction,
        min_gap_s=min_gap_s,
        poll_interval_s=poll_interval_s,
    )


# ─── Ledger persistence ─────────────────────────────────────────


def test_ledger_round_trip(tmp_path):
    path = tmp_path / "l.json"
    led = Ledger.load(path)
    assert led.published == []
    led.append_published(LedgerEntry(
        trigger_id="t1", kind="sea_campaign_success",
        detected_at=100.0, published_at=200.0,
        post_id=42, url="u", title="title",
    ))
    led2 = Ledger.load(path)
    assert len(led2.published) == 1
    assert led2.published[0].trigger_id == "t1"
    assert led2.published[0].post_id == 42
    assert led2.last_published_at == 200.0


def test_ledger_has_returns_true_for_known_trigger(tmp_path):
    led = Ledger.load(tmp_path / "l.json")
    led.append_published(LedgerEntry(
        trigger_id="t1", kind="x", detected_at=1.0, published_at=2.0,
    ))
    assert led.has("t1")
    assert not led.has("t2")


def test_ledger_handles_corrupt_file_gracefully(tmp_path):
    """Corrupt JSON on disk → start fresh, no raise."""
    path = tmp_path / "broken.json"
    path.write_text("{ not valid json")
    led = Ledger.load(path)
    assert led.published == []
    assert led.last_published_at == 0.0


def test_ledger_coalesced_recorded_but_no_last_published_bump(tmp_path):
    led = Ledger.load(tmp_path / "l.json")
    led.append_coalesced("t1", "sea_campaign_success", 100.0, "test note")
    assert led.has("t1")
    assert led.last_published_at == 0.0   # coalesced doesn't count as a publish


# ─── Idempotency: same SEA campaign seen twice ──────────────────


def test_sea_trigger_published_once(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)

    history = [{
        "campaign_run_id": "sea_audit_driven_abc12345",
        "overall_campaign_status": "SUCCESS",
        "final_message": "Improved validation coverage by 12%.",
        "campaign_data": {"detailed_actions_count": 3,
                          "validation_results": {"passed": 7, "failed": 1}},
    }]
    orc.sea_history_path.write_text(json.dumps(history))

    asyncio.run(orc._scan_sea_once())
    assert len(author.calls) == 1, "first scan must publish"

    # Second scan with the same file — no new publish.
    asyncio.run(orc._scan_sea_once())
    assert len(author.calls) == 1, "duplicate trigger must NOT publish twice"


def test_sea_failure_does_not_trigger(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    history = [{
        "campaign_run_id": "sea_audit_driven_fail00",
        "overall_campaign_status": "FAILURE",
        "final_message": "Campaign failed.",
    }]
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())
    assert author.calls == []


# ─── Rate limit (MIN_GAP_S) ─────────────────────────────────────


def test_second_trigger_within_min_gap_is_coalesced(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author, min_gap_s=3600)

    history = [
        {"campaign_run_id": "t1", "overall_campaign_status": "SUCCESS",
         "final_message": "first"},
    ]
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())
    assert len(author.calls) == 1

    # Add a second SUCCESS while last_published_at is still very recent.
    history.append(
        {"campaign_run_id": "t2", "overall_campaign_status": "SUCCESS",
         "final_message": "second, within 1h of the first"}
    )
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())

    # No second publish — but ledger now records t2 as coalesced.
    assert len(author.calls) == 1
    assert orc.ledger.has("t2")
    # Confirm the coalesced entry isn't counted as a publish.
    t2 = next(e for e in orc.ledger.published if e.trigger_id == "t2")
    assert t2.kind == "coalesced"
    assert t2.published_at is None


def test_second_trigger_outside_min_gap_publishes(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author, min_gap_s=1)   # ~1s gap

    history = [
        {"campaign_run_id": "t1", "overall_campaign_status": "SUCCESS",
         "final_message": "first"},
    ]
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())
    assert len(author.calls) == 1

    # Wait past min_gap_s, then add another.
    time.sleep(1.5)
    history.append(
        {"campaign_run_id": "t2", "overall_campaign_status": "SUCCESS",
         "final_message": "second, after the gap"}
    )
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())
    assert len(author.calls) == 2


# ─── Jitter bounds ──────────────────────────────────────────────


def test_compute_delay_bounded_by_jitter_fraction(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(
        tmp_path, author,
        base_delay_s=100.0, jitter_fraction=0.4,
    )
    for _ in range(200):
        d = orc._compute_delay()
        assert 60.0 <= d <= 140.0, f"delay {d} out of [60, 140]"


def test_compute_delay_zero_jitter_returns_base(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(
        tmp_path, author,
        base_delay_s=42.0, jitter_fraction=0.0,
    )
    assert orc._compute_delay() == 42.0


def test_compute_delay_minimum_is_one(tmp_path):
    """Even if base_delay_s + max negative jitter is negative, return ≥ 1."""
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(
        tmp_path, author,
        base_delay_s=0.5, jitter_fraction=1.0,
    )
    for _ in range(50):
        assert orc._compute_delay() >= 1.0


# ─── Composition ────────────────────────────────────────────────


def test_compose_sea_article_uses_telemetry(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    payload = {
        "campaign_run_id": "sea_audit_driven_xyz98765",
        "final_message": "Reduced unhandled-exception rate from 4.2% to 0.3%.",
        "campaign_data": {
            "detailed_actions_count": 11,
            "validation_results": {"passed": 25, "failed": 0},
            "audit_results": {"findings_count": 9},
        },
    }
    title, html, excerpt, topic = orc._compose_sea_article(payload)
    assert "What I learned" in title
    assert "xyz98765" in title
    assert "Reduced unhandled-exception" in html
    assert "Actions executed: <b>11</b>" in html
    assert "<b>25</b> passed" in html
    assert "Audit findings addressed: <b>9</b>" in html
    assert "Reduced unhandled-exception" in excerpt
    assert topic == "self-healing"


def test_compose_dream_article_full_moon(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    payload = {
        "timestamp": "20260513_102412",
        "agents_dreamed": 17,
        "insights_generated": 81,
        "memories_promoted_to_ltm": 134,
        "memories_archived": 6,
        "lunar": {"phase_name": "full moon", "is_full_moon": True},
        "tuning_recommendations": [
            {"parameter": "dream.consolidation_threshold",
             "direction": "+0.05",
             "rationale": "Promotion rate trending up; absorb the headroom."},
        ],
        "book_edition_triggered": True,
    }
    title, html, excerpt, topic = orc._compose_dream_article(payload)
    assert "full moon" in title
    assert "Agents dreamed: <b>17</b>" in html
    assert "consolidation_threshold" in html
    assert excerpt
    assert topic == "machine dreaming"


# ─── publish_to_rage returning None must NOT advance the ledger ──


def test_publish_failure_leaves_ledger_unchanged(tmp_path):
    """If wordpress-agent is down (publish returns None), the trigger is
    NOT marked as published — so the next scan will retry."""
    author = _FakeAuthor(return_value=None)
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    history = [{
        "campaign_run_id": "t1", "overall_campaign_status": "SUCCESS",
        "final_message": "ok",
    }]
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())
    assert len(author.calls) == 1
    assert not orc.ledger.has("t1"), "failed publish must NOT consume the trigger"

    # Next scan should retry the same trigger.
    asyncio.run(orc._scan_sea_once())
    assert len(author.calls) == 2


# ─── Dream scan ────────────────────────────────────────────────


def test_dream_book_edition_triggers_publish(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    (orc.dream_dir / "20260513_102412_dream_report.json").write_text(json.dumps({
        "timestamp": "20260513_102412",
        "agents_dreamed": 5,
        "insights_generated": 12,
        "memories_promoted_to_ltm": 30,
        "memories_archived": 2,
        "lunar": {"phase_name": "new moon", "is_new_moon": True},
        "book_edition_triggered": True,
    }))
    asyncio.run(orc._scan_dreams_once())
    assert len(author.calls) == 1
    assert orc.ledger.has("20260513_102412")


def test_dream_without_book_edition_does_not_trigger(tmp_path):
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    (orc.dream_dir / "20260513_140000_dream_report.json").write_text(json.dumps({
        "timestamp": "20260513_140000",
        "agents_dreamed": 5,
        "insights_generated": 12,
        "memories_promoted_to_ltm": 8,
        "memories_archived": 1,
        "lunar": {"phase_name": "waxing gibbous", "is_full_moon": False,
                  "is_new_moon": False},
        "book_edition_triggered": False,
    }))
    asyncio.run(orc._scan_dreams_once())
    assert author.calls == []
