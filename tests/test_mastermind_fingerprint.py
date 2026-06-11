"""Selector fingerprint + campaign status proof-suite.

The 2026-06 review found 100 identical campaigns/7d caused by a fingerprint
mismatch: history hashed the decorated directive (rotating backlog_idx inside
the first 120 chars) while candidates hashed the bare suggestion — the 24h
dedup window never matched. These tests pin the repair.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orchestration.mastermind_agent import (  # noqa: E402
    campaign_status_from_bdi,
    suggestion_fingerprint,
)

SUGGESTION = "Implement comprehensive input validation for API requests"


def _decorated(idx: int) -> str:
    return f"{SUGGESTION} [target: system, priority: 9, backlog_idx: {idx}]"


def test_rotating_idx_decorations_share_one_fingerprint():
    fps = {suggestion_fingerprint(_decorated(i)) for i in (964, 1075, 7, 99999)}
    assert len(fps) == 1


def test_decorated_matches_bare_suggestion():
    assert suggestion_fingerprint(_decorated(964)) == suggestion_fingerprint(SUGGESTION)


def test_fingerprint_case_insensitive_and_bounded():
    fp = suggestion_fingerprint("X" * 500)
    assert len(fp) == 120
    assert suggestion_fingerprint("ABC") == suggestion_fingerprint("abc")


def test_dedup_window_now_skips_looped_directive():
    """Pure-function rehearsal of the selector logic post-repair."""
    history = [{"directive": _decorated(964), "ts": 1_000_000.0}]
    recent = {suggestion_fingerprint(c["directive"]) for c in history}
    # A "fresh" copy of the same suggestion under a new idx must be skipped.
    assert suggestion_fingerprint(SUGGESTION) in recent
    assert suggestion_fingerprint(_decorated(1075)) in recent


def test_cooldown_eligibility_filter():
    now = 1_000_000.0
    items = [
        {"suggestion": "A", "cooldown_until": now + 100},   # cooling down
        {"suggestion": "B", "cooldown_until": now - 100},   # cooled off
        {"suggestion": "C"},                                  # never attempted
    ]
    eligible = [i for i in items
                if i.get("status") in (None, "PENDING", "pending")
                and (i.get("suggestion") or i.get("description"))
                and float(i.get("cooldown_until") or 0) <= now]
    assert [i["suggestion"] for i in eligible] == ["B", "C"]


# ── campaign terminal-status mapping ─────────────────────────────────────────
def test_status_success():
    assert campaign_status_from_bdi("BDI run COMPLETED_GOAL_ACHIEVED. Reason: N/A") == "SUCCESS"


def test_status_max_cycles():
    assert campaign_status_from_bdi(
        "BDI run MAX_CYCLES_REACHED. Reason: max_cycles=15 exhausted without terminal status"
    ) == "MAX_CYCLES_REACHED"


def test_status_timed_out_and_failed():
    assert campaign_status_from_bdi("BDI run TIMED_OUT. Reason: x") == "TIMED_OUT"
    assert campaign_status_from_bdi("BDI run FAILED_PLANNING. Reason: y") == "FAILED"
    assert campaign_status_from_bdi("BDI run FAILED_RECOVERY. Reason: z") == "FAILED"


def test_status_unknown_falls_back():
    assert campaign_status_from_bdi("") == "FAILURE_OR_INCOMPLETE"
    assert campaign_status_from_bdi("BDI run WAT") == "FAILURE_OR_INCOMPLETE"
