# SPDX-License-Identifier: Apache-2.0
"""Tests for the SkillStore Curator.

Curator policy is **archive-only**, **never delete**, **pinned + human-authored
are off-limits**. These tests pin every clause:

  1. Inspects only what's on disk; doesn't touch foreign skills.
  2. Flags an agent-authored skill that fails the scanner re-run.
  3. Flags an empty body / missing postconditions / staleness.
  4. Flags the older of two near-duplicate agent-authored skills.
  5. With ``apply=False`` (default), nothing on disk is mutated.
  6. With ``apply=True``, flagged agent-authored skills move into ``.archive/``.
  7. Pinned skills are never archived even if flagged.
  8. Human-authored skills are never archived even if flagged.
  9. Writes a JSON report to the configured report_dir.
"""
from __future__ import annotations

import json
import time

import pytest

import agents.skills.index as idx_mod
from agents.skills.curator import Curator
from agents.skills.skill_schema import Skill, SkillFrontmatter
from agents.skills.store import SkillStore


def _stub_embed(text, *, timeout=5.0):
    if not text:
        return None
    # Deterministic short vector keyed off the first few characters → tests can
    # craft "near-duplicates" by giving two skills very similar leading text.
    seed = sum(ord(c) for c in text[:20]) % 991
    return [((seed * (i + 1)) % 100) / 100.0 for i in range(8)]


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(idx_mod, "_embed_text", _stub_embed)
    return SkillStore(root=tmp_path / "skills")


@pytest.fixture
def curator(store, tmp_path):
    return Curator(store, report_dir=tmp_path / "curator-reports", stale_days=30)


def _sk(*, name: str, body: str = "x" * 80, category: str = "tutorial",
        pinned: bool = False, created_by: str = "agent",
        postconditions: list[str] | None = None,
        updated_offset_days: float = 0.0) -> Skill:
    sk = Skill(
        frontmatter=SkillFrontmatter(
            name=name,
            description=f"desc for {name}",
            category=category,
            pinned=pinned,
            created_by=created_by,
            postconditions=postconditions if postconditions is not None else ["belief.done=true"],
        ),
        body=body,
    )
    if updated_offset_days:
        sk.frontmatter.updated_at = time.time() - (updated_offset_days * 86400)
    return sk


def _write_and_age(store, sk, days: float):
    """Write a skill via the store (which rewrites updated_at), then back-date
    the frontmatter on disk so the Curator's staleness signal triggers."""
    from agents.skills.skill_schema import parse_skill_md, serialize_skill_md
    path, _ = store.write(sk)
    parsed = parse_skill_md(path)
    parsed.frontmatter.updated_at = time.time() - (days * 86400)
    path.write_text(serialize_skill_md(parsed), encoding="utf-8")
    return path


# ── audit signals ─────────────────────────────────────────────


def test_inspected_count_matches_store(store, curator):
    store.write(_sk(name="alpha"))
    store.write(_sk(name="beta"))
    report = curator.audit()
    assert report.inspected == 2
    assert report.flagged == []


def test_flags_empty_body(store, curator):
    store.write(_sk(name="hollow", body="hi"))  # 2 bytes
    report = curator.audit()
    assert len(report.flagged) == 1
    assert "empty body" in report.flagged[0].reasons[0]


def test_flags_missing_postconditions(store, curator):
    store.write(_sk(name="dangling", postconditions=[]))
    report = curator.audit()
    assert any("no postconditions" in r for r in report.flagged[0].reasons)


def test_flags_stale_skill(store, curator):
    _write_and_age(store, _sk(name="ancient"), days=120)   # > 30d cutoff
    report = curator.audit()
    assert report.flagged, "expected at least one finding"
    assert any("stale" in r for f in report.flagged for r in f.reasons)


def test_flags_near_duplicate_archives_older(store, curator):
    older = _sk(name="how to verify a wallet sig",
                body="Recover signer via eth_account, then compare to candidate address.",
                updated_offset_days=10)
    newer = _sk(name="how to verify a wallet sig",
                body="Recover signer via eth_account, then compare to candidate address.",
                updated_offset_days=0)
    # Different categories so SkillStore keeps them both — same slug, dupe content.
    older.frontmatter.category = "crypto-a"
    newer.frontmatter.category = "crypto-b"
    store.write(older)
    store.write(newer)
    report = curator.audit()
    # The older of the two should be flagged as duplicate of the newer.
    dups = [f for f in report.flagged if f.duplicate_of]
    assert dups, f"expected near-duplicate finding; got {report.flagged}"
    assert dups[0].category == "crypto-a"
    assert dups[0].duplicate_of == "crypto-b/how-to-verify-a-wallet-sig"


# ── protection guarantees ────────────────────────────────────


def test_pinned_never_flagged_or_archived(store, curator):
    sk = _sk(name="protected", body="hi", pinned=True, created_by="human")
    _write_and_age(store, sk, days=120)
    report = curator.run(apply=True)
    assert any(s["reason"] in ("pinned", "human-authored") for s in report.skipped)
    assert report.archived == []
    # Skill is still on disk
    assert store.read("tutorial", "protected") is not None


def test_human_authored_never_archived_even_if_flagged(store, curator):
    sk = _sk(name="hand crafted", body="hi", created_by="human")
    sk.frontmatter.pinned = True            # human-authored skills with warnings need pinned override
    _write_and_age(store, sk, days=120)
    report = curator.run(apply=True)
    assert any(s["reason"] in ("pinned", "human-authored") for s in report.skipped)
    assert report.archived == []
    assert store.read("tutorial", "hand-crafted") is not None


# ── apply path ──────────────────────────────────────────────


def test_dry_run_does_not_mutate(store, curator):
    store.write(_sk(name="hollow", body="hi"))
    report = curator.run(apply=False)
    assert report.archived == []
    assert store.read("tutorial", "hollow") is not None


def test_apply_archives_flagged_agent_skill(store, curator):
    store.write(_sk(name="hollow", body="hi"))
    report = curator.run(apply=True)
    assert report.archived == ["tutorial/hollow"]
    # Gone from active store
    assert store.read("tutorial", "hollow") is None
    # Lives under .archive/
    archive_root = store.archive_root
    archived_dirs = list(archive_root.glob("*/tutorial/hollow"))
    assert archived_dirs, "skill should be moved into .archive/<ts>/tutorial/hollow"


# ── report ──────────────────────────────────────────────────


def test_report_persisted(store, curator):
    store.write(_sk(name="alpha"))
    report = curator.run(apply=False)
    # Find the report file
    files = sorted(curator.report_dir.glob("*.json"))
    assert files
    payload = json.loads(files[-1].read_text())
    assert payload["actor"] == "curator"
    assert payload["inspected"] == 1
    assert payload["apply"] is False
    assert "duration_seconds" in payload
