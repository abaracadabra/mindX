# SPDX-License-Identifier: Apache-2.0
"""Tests for agents/core/milestone_recognition.py.

Pins the recognizer contract:
  * Each rule's matches_topic + classify
  * Confidence + autopublish_status correctness per category
  * Env-override of autopublish_status
  * topics_to_subscribe enumerates all rules
  * classify returns None for unknown topics + invalid payloads
"""
from __future__ import annotations

import pytest

from agents.core.milestone_recognition import (
    ALL_CATEGORIES,
    CATEGORY_BUG_CRUSHED,
    CATEGORY_COGNITIVE,
    CATEGORY_DREAMING,
    CATEGORY_PUBLICATION,
    RECOGNIZERS,
    Milestone,
    classify,
    is_borderline,
    topics_to_subscribe,
)


# ─── Registry shape ─────────────────────────────────────────────────


def test_topics_to_subscribe_matches_recognizers():
    topics = topics_to_subscribe()
    assert set(topics) == {r.name for r in RECOGNIZERS}
    assert "publication.published" in topics
    assert "bug.crushed" in topics
    assert "sea.campaign.concluded" in topics
    assert "dreaming.improved" in topics


def test_all_categories_covered_by_recognizers():
    categories_from_rules = {r.category for r in RECOGNIZERS}
    assert categories_from_rules == set(ALL_CATEGORIES)


def test_classify_returns_none_for_unknown_topic():
    assert classify("not.a.real.topic", {"foo": "bar"}) is None


def test_classify_returns_none_for_non_dict_payload():
    assert classify("publication.published", "not a dict") is None
    assert classify("publication.published", None) is None


# ─── publication.published ──────────────────────────────────────────


def test_publication_classifier_happy_path():
    m = classify("publication.published", {
        "post_id": 689, "url": "https://rage.pythai.net/x/",
        "title": "X", "slug": "x", "status": "publish",
    })
    assert isinstance(m, Milestone)
    assert m.category == CATEGORY_PUBLICATION
    assert m.key == "milestone:publication:post_689"
    assert m.confidence == 1.0
    assert m.evidence["post_id"] == 689
    # publication NEVER auto-publishes (would loop)
    assert m.autopublish_status == "none"


def test_publication_classifier_skips_missing_post_id():
    assert classify("publication.published", {"url": "https://rage/y/"}) is None


# ─── bug.crushed ────────────────────────────────────────────────────


def test_bug_crushed_major_25_alerts():
    m = classify("bug.crushed", {
        "pr_number": 10, "alert_count": 25,
        "severities": {"critical": 1, "high": 11, "moderate": 12, "low": 1},
    })
    assert m.category == CATEGORY_BUG_CRUSHED
    assert m.key == "milestone:bug_crushed:pr_10"
    assert m.confidence == 1.0
    assert m.evidence["is_major"] is True
    assert m.autopublish_status == "publish"


def test_bug_crushed_minor_single_low():
    m = classify("bug.crushed", {
        "pr_number": 999, "alert_count": 1,
        "severities": {"low": 1},
    })
    # still recognized, but lower confidence + no auto-publish
    assert m is not None
    assert m.confidence == 0.6
    assert m.evidence["is_major"] is False
    assert m.autopublish_status == "none"


def test_bug_crushed_major_single_critical():
    m = classify("bug.crushed", {
        "pr_number": 7, "alert_count": 1,
        "severities": {"critical": 1},
    })
    assert m.evidence["is_major"] is True
    assert m.autopublish_status == "publish"


def test_bug_crushed_major_three_highs():
    m = classify("bug.crushed", {
        "pr_number": 8, "alert_count": 3,
        "severities": {"high": 3},
    })
    assert m.evidence["is_major"] is True


def test_bug_crushed_uses_id_when_no_pr_number():
    m = classify("bug.crushed", {
        "alert_count": 7,
        "severities": {"high": 7},
    })
    assert m.key.startswith("milestone:bug_crushed:batch_7_0c_7h")


# ─── cognitive.improvement (rides sea.campaign.concluded) ──────────


def test_cognitive_classifier_requires_is_milestone():
    m = classify("sea.campaign.concluded", {
        "overall_campaign_status": "SUCCESS",
        "is_milestone": False,
        "campaign_run_id": "sea_routine",
    })
    assert m is None


def test_cognitive_classifier_requires_success():
    m = classify("sea.campaign.concluded", {
        "overall_campaign_status": "FAILURE",
        "is_milestone": True,
        "campaign_run_id": "sea_fail",
    })
    assert m is None


def test_cognitive_classifier_happy_path():
    m = classify("sea.campaign.concluded", {
        "overall_campaign_status": "SUCCESS",
        "is_milestone": True,
        "campaign_run_id": "sea_test_001",
        "final_message": "Resolved 5 audit findings.",
        "campaign_data": {"validation_results": {"passed": 7}},
    })
    assert m.category == CATEGORY_COGNITIVE
    assert m.key == "milestone:cognitive:sea_sea_test_001"
    assert m.confidence == 1.0
    assert m.autopublish_status == "publish"   # default


# ─── dreaming.improved ─────────────────────────────────────────────


def test_dreaming_classifier_code_change():
    m = classify("dreaming.improved", {
        "reason": "code_change",
        "old_hash": "aaaaaaa1111", "new_hash": "bbbbbbb2222",
        "date": "2026-05-23",
    })
    assert m.category == CATEGORY_DREAMING
    assert m.recognizer == "dreaming.improved.code_change"
    assert m.confidence == 1.0
    assert m.autopublish_status == "draft"
    assert "code changed" in m.summary


def test_dreaming_classifier_outlier():
    m = classify("dreaming.improved", {
        "reason": "insight_outlier",
        "insights": 30, "baseline": 12, "ratio": 2.5,
        "date": "2026-05-23",
    })
    assert m.recognizer == "dreaming.improved.insight_outlier"
    assert m.confidence == 0.7
    assert is_borderline(m)   # 0.7 is in the borderline band


def test_dreaming_classifier_unknown_reason_returns_none():
    m = classify("dreaming.improved", {"reason": "weather_changed"})
    assert m is None


# ─── env override of autopublish_status ────────────────────────────


def test_env_override_bug_crushed_to_draft(monkeypatch):
    monkeypatch.setenv("MINDX_MILESTONE_BUG_CRUSHED_STATUS", "draft")
    m = classify("bug.crushed", {
        "pr_number": 11, "alert_count": 5,
        "severities": {"high": 5},
    })
    assert m.autopublish_status == "draft"


def test_env_override_dreaming_to_publish(monkeypatch):
    monkeypatch.setenv("MINDX_MILESTONE_DREAMING_STATUS", "publish")
    m = classify("dreaming.improved", {
        "reason": "code_change", "old_hash": "a", "new_hash": "b",
    })
    assert m.autopublish_status == "publish"


def test_env_override_cognitive_to_draft(monkeypatch):
    monkeypatch.setenv("MINDX_MILESTONE_COGNITIVE_STATUS", "draft")
    m = classify("sea.campaign.concluded", {
        "overall_campaign_status": "SUCCESS",
        "is_milestone": True,
        "campaign_run_id": "x",
    })
    assert m.autopublish_status == "draft"


# ─── borderline detection ──────────────────────────────────────────


def test_is_borderline_band():
    base = Milestone(
        category="dreaming", key="k", summary="s",
        confidence=0.5, recognizer="r",
    )
    assert is_borderline(base) is True
    base.confidence = 0.39
    assert is_borderline(base) is False
    base.confidence = 0.71
    assert is_borderline(base) is False
    base.confidence = 0.40
    assert is_borderline(base) is True
    base.confidence = 0.70
    assert is_borderline(base) is True


# ─── Milestone.belief_value shape ───────────────────────────────────


def test_milestone_belief_value_round_trip():
    m = Milestone(
        category="bug_crushed", key="milestone:bug_crushed:pr_10",
        summary="Closed 25 alerts", confidence=1.0,
        recognizer="bug.crushed",
        evidence={"pr_number": 10, "alert_count": 25},
        autopublish_status="publish",
    )
    bv = m.belief_value()
    assert bv["category"] == "bug_crushed"
    assert bv["summary"] == "Closed 25 alerts"
    assert bv["confidence"] == 1.0
    assert bv["recognizer"] == "bug.crushed"
    assert bv["autopublish_status"] == "publish"
    assert bv["evidence"]["pr_number"] == 10
