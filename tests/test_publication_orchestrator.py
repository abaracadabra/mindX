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
    distinguishes that from 'caller didn't specify'.

    Also implements the three canonical-author composers (compose_milestone_article,
    compose_book_edition_article, compose_journal_digest_article) so the
    orchestrator's delegation path can be exercised. Each records its call
    so tests can assert which path fired.
    """

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
        self.composer_calls: List[str] = []

    async def publish_to_rage(self, **kwargs):
        self.calls.append(kwargs)
        return self.return_value

    def compose_milestone_article(self, payload):
        self.composer_calls.append("milestone")
        return ("Milestone: test", "<p>milestone body</p>", "excerpt", "milestone")

    def compose_book_edition_article(self, payload):
        self.composer_calls.append("book")
        return ("Book: test", "<p>book body</p>", "excerpt", "book of mindX")

    def compose_journal_digest_article(self, journal_text, lunar_phase):
        self.composer_calls.append("journal")
        return ("Journal: test", "<p>journal body</p>", "excerpt", "improvement journal")


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


# ─── Hybrid status policy (SEA→publish, dreams→draft, env-overridable) ──


def test_sea_default_status_is_publish(tmp_path):
    """SEA campaign articles must default to status='publish' (mindX reports
    its own milestones publicly). This is the user-locked policy."""
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    history = [{
        "campaign_run_id": "sea_audit_driven_pubtest",
        "overall_campaign_status": "SUCCESS",
        "final_message": "ok",
    }]
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())
    assert len(author.calls) == 1
    assert author.calls[0]["status"] == "publish"


def test_dream_default_status_is_draft(tmp_path):
    """Dream-cycle book editions must default to status='draft' (deeper /
    cutting-edge material, operator review before going live)."""
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    (orc.dream_dir / "20260520_dream_report.json").write_text(json.dumps({
        "timestamp": "20260520",
        "agents_dreamed": 3, "insights_generated": 5,
        "memories_promoted_to_ltm": 10, "memories_archived": 1,
        "lunar": {"phase_name": "full moon", "is_full_moon": True},
        "book_edition_triggered": True,
    }))
    asyncio.run(orc._scan_dreams_once())
    assert len(author.calls) == 1
    assert author.calls[0]["status"] == "draft"


def test_env_overrides_per_source_status(tmp_path, monkeypatch):
    """Operator can flip defaults via env vars without code change."""
    monkeypatch.setenv("MINDX_PUBLICATION_SEA_STATUS",   "draft")
    monkeypatch.setenv("MINDX_PUBLICATION_DREAM_STATUS", "publish")
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    assert orc._default_status_for_source("sea_campaign_success") == "draft"
    assert orc._default_status_for_source("dream_book_edition")   == "publish"


# ─── Direct callback hooks via coordinator pub/sub ──────────────


class _FakeCoordinator:
    """Minimal coordinator stand-in. Records subscriptions and
    synchronously invokes them on publish_event."""

    def __init__(self):
        self.subs: Dict[str, List[Any]] = {}

    def subscribe(self, topic: str, callback):
        self.subs.setdefault(topic, []).append(callback)

    async def publish_event(self, topic: str, data: Dict[str, Any]):
        for cb in self.subs.get(topic, []):
            await cb(data)


def test_orchestrator_subscribes_to_coordinator_on_construction(tmp_path):
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path,
        ledger_path=tmp_path / "l.json",
    )
    assert "sea.campaign.concluded" in coord.subs
    assert "dream.report.written"   in coord.subs


def test_sea_campaign_concluded_event_triggers_publish(tmp_path):
    """When coordinator publishes 'sea.campaign.concluded' the orchestrator
    publishes within the same tick — no waiting on the 60s file poll."""
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
        base_delay_s=0.0,
        jitter_fraction=0.0,
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("sea.campaign.concluded", {
        "campaign_run_id": "sea_cb_test_001",
        "overall_campaign_status": "SUCCESS",
        "final_message": "callback path works",
    }))
    assert len(author.calls) == 1
    assert author.calls[0]["status"] == "publish"
    assert orc.ledger.has("sea_cb_test_001")


def test_sea_campaign_concluded_event_skips_non_success(tmp_path):
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("sea.campaign.concluded", {
        "campaign_run_id": "sea_cb_test_002",
        "overall_campaign_status": "FAILURE",
        "final_message": "noop",
    }))
    assert author.calls == []


def test_dream_report_written_event_triggers_draft_publish(tmp_path):
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
        base_delay_s=0.0,
        jitter_fraction=0.0,
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("dream.report.written", {
        "timestamp": "20260520_dream_cb",
        "agents_dreamed": 4, "insights_generated": 6,
        "memories_promoted_to_ltm": 2, "memories_archived": 1,
        "lunar": {"phase_name": "full moon", "is_full_moon": True},
        "book_edition_triggered": True,
    }))
    assert len(author.calls) == 1
    assert author.calls[0]["status"] == "draft"
    assert orc.ledger.has("20260520_dream_cb")


def test_dream_report_written_event_skips_non_book_edition(tmp_path):
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("dream.report.written", {
        "timestamp": "20260521_dream_cb",
        "book_edition_triggered": False,
    }))
    assert author.calls == []


# ─── Health snapshot for /insight/publications/health ──────────


def test_get_health_reports_orchestrator_state(tmp_path):
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
    )
    (tmp_path / "dreams").mkdir()
    h = orc.get_health()
    # Watchers haven't run yet — both are reported as not-alive.
    assert h["watch_sea_alive"]    is False
    assert h["watch_dreams_alive"] is False
    assert h["coordinator_wired"]  is True
    assert h["ledger_entries"]     == 0
    assert h["sea_status_default"]       == "publish"
    assert h["dream_status_default"]     == "draft"
    assert h["milestone_status_default"] == "publish"
    assert h["book_status_default"]      == "draft"
    assert h["journal_status_default"]   == "publish"
    assert set(h["exempt_from_min_gap"]) == {"sea_milestone", "book_edition", "journal_lunar_digest"}
    assert h["last_publish_at"]    is None


# ─── SEA milestone dispatch (richer authorship via AuthorAgent) ──


def test_sea_campaign_concluded_milestone_routes_to_sea_milestone_kind(tmp_path):
    """is_milestone=True must dispatch to 'sea_milestone' kind + delegate
    article composition to AuthorAgent.compose_milestone_article."""
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
        base_delay_s=0.0, jitter_fraction=0.0,
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("sea.campaign.concluded", {
        "campaign_run_id": "sea_milestone_test_001",
        "overall_campaign_status": "SUCCESS",
        "is_milestone": True,
        "final_message": "EXCELLENT grade campaign",
    }))
    assert len(author.calls) == 1
    assert author.calls[0]["status"] == "publish"           # milestone defaults to publish
    assert author.calls[0]["title"] == "Milestone: test"    # came from AuthorAgent composer
    assert author.composer_calls == ["milestone"]
    assert orc.ledger.has("sea_milestone_sea_milestone_test_001")  # distinct trigger_id prefix


def test_sea_campaign_concluded_routine_keeps_generic_path(tmp_path):
    """is_milestone absent/false must keep the existing 'sea_campaign_success'
    kind with the orchestrator's generic template (no composer delegation)."""
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
        base_delay_s=0.0, jitter_fraction=0.0,
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("sea.campaign.concluded", {
        "campaign_run_id": "sea_routine_002",
        "overall_campaign_status": "SUCCESS",
        "final_message": "routine improvement",
    }))
    assert len(author.calls) == 1
    assert author.calls[0]["status"] == "publish"
    # No composer delegation — generic orchestrator template was used.
    assert author.composer_calls == []
    assert "What I learned" in author.calls[0]["title"]
    assert orc.ledger.has("sea_routine_002")


# ─── book.edition.published + journal.lunar.digest.ready ─────────


def test_book_edition_published_event_triggers_draft_publish(tmp_path):
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
        base_delay_s=0.0, jitter_fraction=0.0,
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("book.edition.published", {
        "edition": "20260522_2204",
        "edition_hash": "a1b2c3d4e5f6a7b8",
        "chapters_included": 27,
        "bytes": 60000,
        "lunar": {"phase_name": "full moon", "is_full_moon": True},
    }))
    assert len(author.calls) == 1
    assert author.calls[0]["status"] == "draft"             # book defaults to draft
    assert author.calls[0]["title"] == "Book: test"
    assert author.composer_calls == ["book"]
    assert orc.ledger.has("book_edition_20260522_2204_a1b2c3d4e5f6a7b8")


def test_journal_lunar_digest_event_triggers_publish_status(tmp_path):
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
        base_delay_s=0.0, jitter_fraction=0.0,
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("journal.lunar.digest.ready", {
        "edition_id": "20260522_2204",
        "lunar": {"phase_name": "full moon", "is_full_moon": True},
    }))
    assert len(author.calls) == 1
    assert author.calls[0]["status"] == "publish"            # journal defaults to publish
    assert author.calls[0]["title"] == "Journal: test"
    assert author.composer_calls == ["journal"]
    assert orc.ledger.has("journal_digest_20260522_full")


def test_book_edition_missing_edition_id_is_ignored(tmp_path):
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
    )
    (tmp_path / "dreams").mkdir()
    asyncio.run(coord.publish_event("book.edition.published", {"foo": "bar"}))
    assert author.calls == []


# ─── Lunar-cadence kinds bypass MIN_GAP_S ───────────────────────


def test_lunar_kinds_bypass_min_gap_after_recent_publish(tmp_path):
    """A book/journal/milestone trigger must NOT be coalesced even when a
    recent routine publish has bumped last_published_at within MIN_GAP_S."""
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
        base_delay_s=0.0, jitter_fraction=0.0,
        min_gap_s=21600.0,  # 6h — production value
    )
    (tmp_path / "dreams").mkdir()
    # Prime the ledger: simulate a recent routine publish (last_published_at NOW).
    orc.ledger.last_published_at = time.time()
    # Fire all three lunar kinds back-to-back; each must publish, not coalesce.
    asyncio.run(coord.publish_event("book.edition.published", {
        "edition": "20260522_2200", "edition_hash": "x" * 16,
        "lunar": {"is_full_moon": True},
    }))
    asyncio.run(coord.publish_event("journal.lunar.digest.ready", {
        "edition_id": "20260522_2200",
        "lunar": {"is_full_moon": True},
    }))
    asyncio.run(coord.publish_event("sea.campaign.concluded", {
        "campaign_run_id": "sea_milestone_test_lunar",
        "overall_campaign_status": "SUCCESS",
        "is_milestone": True,
        "final_message": "milestone",
    }))
    # All three must have published — none coalesced.
    assert len(author.calls) == 3
    coalesced = [e for e in orc.ledger.published if e.kind == "coalesced"]
    assert coalesced == []


def test_routine_kinds_still_respect_min_gap(tmp_path):
    """Routine sea_campaign_success + dream_book_edition must still coalesce
    when MIN_GAP_S would be violated — only lunar kinds are exempt."""
    coord = _FakeCoordinator()
    author = _FakeAuthor()
    orc = PublicationOrchestrator(
        author_agent=author,
        coordinator=coord,
        sea_history_path=tmp_path / "sea.json",
        dream_dir=tmp_path / "dreams",
        ledger_path=tmp_path / "l.json",
        base_delay_s=0.0, jitter_fraction=0.0,
        min_gap_s=21600.0,
    )
    (tmp_path / "dreams").mkdir()
    orc.ledger.last_published_at = time.time()
    asyncio.run(coord.publish_event("sea.campaign.concluded", {
        "campaign_run_id": "sea_routine_X",
        "overall_campaign_status": "SUCCESS",
        "final_message": "noop",
    }))
    assert author.calls == []
    coalesced = [e for e in orc.ledger.published if e.kind == "coalesced"]
    assert len(coalesced) == 1


# ─── Trigger-id uniqueness across kinds ─────────────────────────


def test_trigger_id_prefixes_keep_kinds_distinct(tmp_path):
    """A single campaign_run_id used both as routine SUCCESS AND as a
    milestone elsewhere must produce DISTINCT ledger entries (different
    trigger_id prefixes). Cheap insurance against accidental collisions."""
    author = _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author)
    # Hand-fire both with the same underlying campaign id.
    asyncio.run(orc._schedule_publish(
        trigger_id="campaign_X", kind="sea_campaign_success",
        payload={"campaign_run_id": "campaign_X", "final_message": "ok"},
    ))
    asyncio.run(orc._schedule_publish(
        trigger_id="sea_milestone_campaign_X", kind="sea_milestone",
        payload={"campaign_run_id": "campaign_X", "final_message": "ok",
                 "campaign_data": {"validation_results": {"passed": 5}}},
    ))
    assert orc.ledger.has("campaign_X")
    assert orc.ledger.has("sea_milestone_campaign_X")
    # The orchestrator coalesces the second one because MIN_GAP_S applies to
    # sea_campaign_success but sea_milestone is exempt — only one real publish
    # but BOTH trigger_ids land in the ledger (one as "coalesced" or both as
    # published depending on timing). The point of this test is no collision.
    kinds = {e.kind for e in orc.ledger.published}
    assert "sea_milestone" in kinds or "coalesced" in kinds
