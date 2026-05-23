# SPDX-License-Identifier: Apache-2.0
"""Milestone recognition — pluggable classifier rules used by AGInt's
perception phase to turn coordinator events into recognized achievements.

mindX produces a constant stream of events. Most are routine (a memory
write, a tool invocation, a single dream cycle). A few — measured by
significance, not frequency — are *milestones*: the system shipping a
public article, closing a batch of CVEs, completing an evolution moment,
upgrading its own dream-cycle code.

This module is the recognition substrate. Pure functions, zero coupling
to AGInt or BeliefSystem so each rule can be unit-tested in isolation.

The architecture:
    coordinator.publish_event(topic, payload)
                      │
                      ▼
        AGInt subscriber (in agints.py)
                      │
                      ▼
        milestone_recognition.classify(topic, payload)
                      │
                      ▼
        Milestone | None
                      │
                      ▼
        AGInt writes BeliefSystem entry,
        emits 'milestone.recognized' event,
        mirrors to catalogue,
        maybe triggers autopublish via AuthorAgent.

Each ``RecognizerRule`` is a small dataclass-like object:
    name           — stable string, used in catalogue/audit
    category       — one of "publication" | "bug_crushed" | "cognitive" | "dreaming"
    matches(topic) — boolean predicate on coordinator topic
    classify(payload) → Optional[Milestone]
    autopublish_default — env-overridable default publish status policy

Add a new category by appending a new ``RecognizerRule`` to ``RECOGNIZERS``.
That's the entire extension point.

Public contract intentionally minimal: ``classify(topic, payload) -> Optional[Milestone]``
plus the ``Milestone`` dataclass + ``RECOGNIZERS`` registry. Everything
else is module-internal.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


# ─── Category enum (string, not enum, for serialisation simplicity) ──

CATEGORY_PUBLICATION  = "publication"
CATEGORY_BUG_CRUSHED  = "bug_crushed"
CATEGORY_COGNITIVE    = "cognitive"
CATEGORY_DREAMING     = "dreaming"

ALL_CATEGORIES = (
    CATEGORY_PUBLICATION,
    CATEGORY_BUG_CRUSHED,
    CATEGORY_COGNITIVE,
    CATEGORY_DREAMING,
)


# ─── The Milestone dataclass — what a recognizer returns ────────────

@dataclass
class Milestone:
    """A recognized milestone. Persists into BeliefSystem; rides on the
    ``milestone.recognized`` coordinator event; mirrors into catalogue."""
    category: str                 # one of ALL_CATEGORIES
    key: str                      # belief key: "milestone:<category>:<id>"
    summary: str                  # short, human-readable, one sentence
    confidence: float             # 0.0..1.0
    recognizer: str               # rule.name — for audit
    evidence: Dict[str, Any] = field(default_factory=dict)   # the verbatim payload that triggered
    autopublish_status: str = "draft"   # "publish" | "draft" | "none" (none = don't even compose)

    def belief_value(self) -> Dict[str, Any]:
        """Shape stored as the BeliefSystem value."""
        return {
            "category": self.category,
            "summary": self.summary,
            "confidence": self.confidence,
            "recognizer": self.recognizer,
            "evidence": self.evidence,
            "autopublish_status": self.autopublish_status,
        }


# ─── Status-policy resolution — env-overridable per category ────────

def _resolved_status(category: str, default: str) -> str:
    """Per-category env override. Mirrors the PublicationOrchestrator
    pattern shipped earlier (MINDX_PUBLICATION_{SEA,DREAM,BOOK,…}_STATUS).

    For milestones the env vars are:
        MINDX_MILESTONE_PUBLICATION_STATUS    (default "none")
        MINDX_MILESTONE_BUG_CRUSHED_STATUS    (default "publish")
        MINDX_MILESTONE_COGNITIVE_STATUS      (default "publish")
        MINDX_MILESTONE_DREAMING_STATUS       (default "draft")
    """
    env_key = f"MINDX_MILESTONE_{category.upper()}_STATUS"
    val = os.environ.get(env_key, default).strip().lower()
    return val or default


# ─── Recognizer rules — one per category ────────────────────────────

@dataclass
class RecognizerRule:
    """A pluggable classifier. ``matches`` predicate runs in O(1); ``classify``
    runs only on matched topics so per-tick cost stays cheap."""
    name: str
    category: str
    matches_topic: Callable[[str], bool]
    classify: Callable[[Dict[str, Any]], Optional[Milestone]]


# Rule 1 — publication.published → category=publication
# Every successful publish is a milestone. mindX publishes rarely; each one
# matters. NEVER autopublish (recursion: publishing about publishing).

def _classify_publication(payload: Dict[str, Any]) -> Optional[Milestone]:
    post_id = payload.get("post_id")
    if post_id is None:
        return None
    url   = payload.get("url") or ""
    title = payload.get("title") or "(untitled)"
    kind  = payload.get("kind") or "?"   # orchestrator's trigger kind
    return Milestone(
        category=CATEGORY_PUBLICATION,
        key=f"milestone:{CATEGORY_PUBLICATION}:post_{post_id}",
        summary=f"Published article: {title} ({url})",
        confidence=1.0,
        recognizer="publication.published",
        evidence={
            "post_id": post_id,
            "url": url,
            "title": title,
            "kind": kind,
            "status": payload.get("status"),
            "slug": payload.get("slug"),
        },
        autopublish_status=_resolved_status(CATEGORY_PUBLICATION, "none"),
    )


# Rule 2 — bug.crushed → category=bug_crushed
# Threshold: 5+ alerts OR 1+ critical OR 3+ high. Below threshold we still
# return a Milestone (lower confidence) so it appears in the ledger; only
# the autopublish gate cares about milestone-grade vs. ordinary.

def _classify_bug_crushed(payload: Dict[str, Any]) -> Optional[Milestone]:
    alert_count = int(payload.get("alert_count") or 0)
    severities  = payload.get("severities") or {}
    crit  = int(severities.get("critical") or 0)
    high  = int(severities.get("high")     or 0)
    pr_n  = payload.get("pr_number")
    summary_in = payload.get("summary") or ""
    is_major = (alert_count >= 5) or (crit >= 1) or (high >= 3)

    key_id = f"pr_{pr_n}" if pr_n else payload.get("id") or f"batch_{alert_count}_{crit}c_{high}h"
    summary = summary_in or (
        f"Closed {alert_count} security alert(s)"
        + (f" (PR #{pr_n})" if pr_n else "")
        + (f" — {crit} critical, {high} high" if (crit or high) else "")
    )

    autopublish = _resolved_status(CATEGORY_BUG_CRUSHED, "publish") if is_major else "none"
    return Milestone(
        category=CATEGORY_BUG_CRUSHED,
        key=f"milestone:{CATEGORY_BUG_CRUSHED}:{key_id}",
        summary=summary,
        confidence=1.0 if is_major else 0.6,
        recognizer="bug.crushed",
        evidence={
            "pr_number": pr_n,
            "alert_count": alert_count,
            "severities": severities,
            "is_major": is_major,
        },
        autopublish_status=autopublish,
    )


# Rule 3 — cognitive.improvement → category=cognitive
# Subscribes to the existing sea.campaign.concluded with is_milestone=True
# (already wired in PublicationOrchestrator). Recognition's job here is just
# to ALSO write a belief + emit milestone.recognized so /insight/milestones
# sees it. The autopublish itself stays with PublicationOrchestrator.

def _classify_cognitive(payload: Dict[str, Any]) -> Optional[Milestone]:
    if not payload.get("is_milestone"):
        return None
    if payload.get("overall_campaign_status") != "SUCCESS":
        return None
    run_id = payload.get("campaign_run_id") or "unknown"
    final_message = payload.get("final_message") or "Campaign concluded."
    return Milestone(
        category=CATEGORY_COGNITIVE,
        key=f"milestone:{CATEGORY_COGNITIVE}:sea_{run_id}",
        summary=f"SEA milestone campaign: {final_message[:100]}",
        confidence=1.0,
        recognizer="sea.campaign.concluded",
        evidence={
            "campaign_run_id": run_id,
            "agent_id": payload.get("agent_id"),
            "final_message": final_message,
            "campaign_data": payload.get("campaign_data"),
        },
        autopublish_status=_resolved_status(CATEGORY_COGNITIVE, "publish"),
    )


# Rule 4 — dreaming.improved → category=dreaming
# Two trigger reasons: code-change (machine_dreaming.py git blob hash
# changed since last run) and outlier (insights_generated > 1.5x rolling
# median). Confidence reflects which detector fired.

def _classify_dreaming(payload: Dict[str, Any]) -> Optional[Milestone]:
    reason = payload.get("reason")
    if reason not in ("code_change", "insight_outlier"):
        return None
    is_code = (reason == "code_change")
    confidence = 1.0 if is_code else 0.7

    # Short, distinguishable id per reason — date + reason keeps the
    # ledger greppable and prevents same-day double-fires.
    date_part = payload.get("date") or payload.get("timestamp", "")[:10] or "unknown"
    key_id = f"{date_part}_{reason}"

    if is_code:
        old = (payload.get("old_hash") or "")[:7]
        new = (payload.get("new_hash") or "")[:7]
        summary = f"machine.dreaming code changed ({old}→{new})"
    else:
        ins = payload.get("insights", "?")
        med = payload.get("baseline", "?")
        ratio = payload.get("ratio", "?")
        summary = f"machine.dreaming outlier: {ins} insights vs baseline {med} (x{ratio})"

    return Milestone(
        category=CATEGORY_DREAMING,
        key=f"milestone:{CATEGORY_DREAMING}:{key_id}",
        summary=summary,
        confidence=confidence,
        recognizer=f"dreaming.improved.{reason}",
        evidence=payload,
        autopublish_status=_resolved_status(CATEGORY_DREAMING, "draft"),
    )


# ─── The registry — appending here = adding a category ──────────────

RECOGNIZERS: List[RecognizerRule] = [
    RecognizerRule(
        name="publication.published",
        category=CATEGORY_PUBLICATION,
        matches_topic=lambda t: t == "publication.published",
        classify=_classify_publication,
    ),
    RecognizerRule(
        name="bug.crushed",
        category=CATEGORY_BUG_CRUSHED,
        matches_topic=lambda t: t == "bug.crushed",
        classify=_classify_bug_crushed,
    ),
    RecognizerRule(
        name="sea.campaign.concluded",
        category=CATEGORY_COGNITIVE,
        matches_topic=lambda t: t == "sea.campaign.concluded",
        classify=_classify_cognitive,
    ),
    RecognizerRule(
        name="dreaming.improved",
        category=CATEGORY_DREAMING,
        matches_topic=lambda t: t == "dreaming.improved",
        classify=_classify_dreaming,
    ),
]


# ─── The public entry point ─────────────────────────────────────────

def classify(topic: str, payload: Dict[str, Any]) -> Optional[Milestone]:
    """Run the rule chain against (topic, payload). First non-None wins.

    Pure function. No I/O, no logging — caller (AGInt) handles persistence
    and emission.
    """
    if not isinstance(payload, dict):
        return None
    for rule in RECOGNIZERS:
        if not rule.matches_topic(topic):
            continue
        try:
            result = rule.classify(payload)
        except Exception:
            continue
        if result is not None:
            return result
    return None


def is_borderline(m: Milestone) -> bool:
    """Heuristic confidence in the grey zone where AGInt should consider
    asking the LLM for a second opinion. Currently 0.4..0.7 inclusive."""
    return 0.4 <= m.confidence <= 0.7


def topics_to_subscribe() -> List[str]:
    """The unique set of coordinator topics any recognizer cares about.
    AGInt subscribes to exactly these on construction."""
    seen: List[str] = []
    for rule in RECOGNIZERS:
        # Probe matches_topic with a small set of known topic strings.
        # We deliberately reflect via the rule name since matches_topic
        # is opaque otherwise.
        candidate = rule.name  # rule.name == topic string by convention
        if candidate not in seen and rule.matches_topic(candidate):
            seen.append(candidate)
    return seen


__all__ = [
    "Milestone",
    "RecognizerRule",
    "RECOGNIZERS",
    "ALL_CATEGORIES",
    "CATEGORY_PUBLICATION",
    "CATEGORY_BUG_CRUSHED",
    "CATEGORY_COGNITIVE",
    "CATEGORY_DREAMING",
    "classify",
    "is_borderline",
    "topics_to_subscribe",
]
