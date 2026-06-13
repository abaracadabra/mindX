"""Backlog hygiene proof-suite — the 83,318→6 collapse and its guards.

Covers the pure helpers in agents/orchestration/coordinator_agent.py:
backlog_fingerprint + dedupe_backlog, and the source-tagging contract that
keeps the SystemAnalyzer heuristic echo from re-entering the backlog.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.orchestration.coordinator_agent import (  # noqa: E402
    backlog_fingerprint,
    dedupe_backlog,
)


def test_fingerprint_case_and_whitespace_insensitive():
    a = {"suggestion": "  Fix The Thing  "}
    b = {"suggestion": "fix the thing"}
    assert backlog_fingerprint(a) == backlog_fingerprint(b)


def test_fingerprint_falls_back_to_description():
    assert backlog_fingerprint({"description": "Do X"}) == "do x"
    assert backlog_fingerprint({}) == ""


def test_dedupe_collapses_prod_shape():
    # The prod pathology in miniature: 3 suggestions x thousands of copies.
    items = []
    for i in range(300):
        items.append({"suggestion": "Install Ollama and pull required models", "priority": 8})
        items.append({"suggestion": "Implement fallback provider selection", "priority": 7})
        items.append({"suggestion": "Implement comprehensive input validation", "priority": 9})
    deduped = dedupe_backlog(items)
    assert len(deduped) == 3
    assert all(d["occurrences"] == 300 for d in deduped)


def test_dedupe_preserves_best_metadata():
    items = [
        {"suggestion": "Fix X", "priority": 5, "added_at": 100.0},
        {"suggestion": "fix x", "priority": 9, "status": "attempted",
         "attempted_at": 200.0, "added_at": 200.0},
        {"suggestion": "FIX X", "priority": 2, "added_at": 300.0},
    ]
    deduped = dedupe_backlog(items)
    assert len(deduped) == 1
    kept = deduped[0]
    assert kept["priority"] == 9                  # max priority wins
    assert kept["status"] == "attempted"          # non-null status preserved
    assert kept["occurrences"] == 3
    assert kept["first_seen"] == 100.0
    assert kept["last_seen"] == 300.0


def test_dedupe_keeps_first_appearance_order():
    items = [{"suggestion": "B"}, {"suggestion": "A"}, {"suggestion": "b"}]
    deduped = dedupe_backlog(items)
    assert [d["suggestion"] for d in deduped] == ["B", "A"]


def test_dedupe_skips_garbage():
    items = [{"suggestion": "ok"}, "not-a-dict", {"no_text_fields": 1}, None]
    deduped = dedupe_backlog(items)
    assert len(deduped) == 1


class _FakeCoordinator:
    """Just enough of CoordinatorAgent to exercise add_backlog_item."""
    from agents.orchestration.coordinator_agent import CoordinatorAgent as _CA
    add_backlog_item = _CA.add_backlog_item

    def __init__(self):
        self.improvement_backlog = []


def test_add_backlog_item_rejects_echo_source():
    co = _FakeCoordinator()
    assert co.add_backlog_item({"suggestion": "anything", "source": "backlog_echo"}) is False
    assert co.improvement_backlog == []


def test_add_backlog_item_dedups_and_counts():
    co = _FakeCoordinator()
    assert co.add_backlog_item({"suggestion": "New idea", "priority": 5}) is True
    assert co.add_backlog_item({"suggestion": "new idea", "priority": 8}) is False
    assert len(co.improvement_backlog) == 1
    kept = co.improvement_backlog[0]
    assert kept["occurrences"] == 2
    assert kept["priority"] == 8   # bumped to the higher duplicate priority
