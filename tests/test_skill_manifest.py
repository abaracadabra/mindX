# SPDX-License-Identifier: Apache-2.0
"""Tests for the SkillManifest registry (Phase A — off-chain + 0G upload).

Contract pinned by these tests:

  1. Empty store → empty manifest, sha256 stable.
  2. Two stores with identical SKILL.md contents produce identical manifest
     bytes (byte-stable canonical encoding — the whole point of CAS).
  3. Manifest entries cover every non-archived skill (pinned + agent + human).
  4. Mutating a SKILL.md on disk changes its sha256 → verify_skill flags it.
  5. Deleting a SKILL.md on disk → verify_skill reports "missing".
  6. A skill not in the manifest → verify_skill reports "not present".
  7. ``upload_manifest`` is a no-op + returns None when no provider given.
  8. ``upload_manifest`` calls ``provider.upload(canonical_bytes, ...)`` and
     returns the 0G root the provider yields (mocked — no live sidecar).
  9. ``persist`` writes both manifest JSON + sidecar meta.
 10. ``load_meta`` round-trips the sidecar.
 11. ``anchor_manifest`` is a stub that returns ("not_anchored", None).
 12. ``previous_manifest_root`` is recorded verbatim into the manifest.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

import agents.skills.index as idx_mod
from agents.skills.manifest import (
    SkillManifest,
    anchor_manifest,
    build_manifest,
    load_meta,
    persist,
    upload_manifest,
    verify_all,
    verify_skill,
)
from agents.skills.skill_schema import Skill, SkillFrontmatter
from agents.skills.store import SkillStore


def _stub_embed(text, *, timeout=5.0):
    if not text:
        return None
    seed = sum(ord(c) for c in text[:20]) % 991
    return [((seed * (i + 1)) % 100) / 100.0 for i in range(8)]


@pytest.fixture(autouse=True)
def _patch_embedder(monkeypatch):
    monkeypatch.setattr(idx_mod, "_embed_text", _stub_embed)


@pytest.fixture
def store(tmp_path):
    return SkillStore(root=tmp_path / "skills")


def _sk(name="alpha", *, body="x" * 80, category="tutorial",
        pinned=False, created_by="agent") -> Skill:
    return Skill(
        frontmatter=SkillFrontmatter(
            name=name, description=f"desc for {name}", category=category,
            pinned=pinned, created_by=created_by,
            postconditions=["belief.done=true"],
        ),
        body=body,
    )


# ─── manifest building ──────────────────────────────────────────


def test_empty_store_yields_empty_manifest(store):
    m = build_manifest(store)
    assert m.skill_count == 0
    assert m.entries == []
    # sha256 of an empty manifest is still deterministic
    assert isinstance(m.sha256(), str) and len(m.sha256()) == 64


def test_manifest_lists_every_active_skill(store):
    store.write(_sk(name="alpha"))
    store.write(_sk(name="beta", category="crypto"))
    store.write(_sk(name="gamma", pinned=True))
    m = build_manifest(store)
    assert m.skill_count == 3
    cats = sorted((e.category, e.slug) for e in m.entries)
    assert cats == [("crypto", "beta"), ("tutorial", "alpha"), ("tutorial", "gamma")]


def test_include_pinned_false_skips_pinned(store):
    store.write(_sk(name="alpha"))
    store.write(_sk(name="locked", pinned=True))
    m = build_manifest(store, include_pinned=False)
    slugs = {e.slug for e in m.entries}
    assert slugs == {"alpha"}


def test_manifest_is_byte_stable_across_stores(tmp_path):
    """Two stores with byte-identical SKILL.md files → byte-identical
    manifest. This is the whole point of content-addressing: same bytes
    in, same root out, regardless of who builds it.

    Using ``store.write`` would stamp different ``created_at``/``updated_at``
    timestamps; the test mirrors the SKILL.md file contents directly
    instead so we're really exercising the manifest's determinism, not
    the store's write semantics."""
    from agents.skills.skill_schema import serialize_skill_md

    a = SkillStore(root=tmp_path / "a")
    b = SkillStore(root=tmp_path / "b")

    sk = _sk(name="alpha")
    # Pin the timestamps so both copies have identical on-disk bytes.
    sk.frontmatter.created_at = 1_700_000_000.0
    sk.frontmatter.updated_at = 1_700_000_000.0
    serialized = serialize_skill_md(sk)

    for s in (a, b):
        path = s._path_for("tutorial", "alpha")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(serialized, encoding="utf-8")

    ma = build_manifest(a)
    mb = build_manifest(b)
    mb.generated_at = ma.generated_at
    assert ma.canonical_bytes() == mb.canonical_bytes()
    assert ma.sha256() == mb.sha256()


def test_manifest_sha256_changes_when_skill_content_changes(store):
    path, _ = store.write(_sk(name="alpha", body="original" * 10))
    m1 = build_manifest(store)
    # Mutate the body on disk — this is exactly the local-tampering scenario.
    text = path.read_text()
    path.write_text(text.replace("original" * 10, "tampered" * 10))
    m2 = build_manifest(store)
    m2.generated_at = m1.generated_at
    assert m1.sha256() != m2.sha256()


def test_previous_manifest_root_is_recorded(store):
    m = build_manifest(store, previous_manifest_root="0xdead" + "00" * 30)
    assert m.previous_manifest_root.startswith("0xdead")
    parsed = json.loads(m.canonical_bytes())
    assert parsed["previous_manifest_root"] == "0xdead" + "00" * 30


# ─── verification ───────────────────────────────────────────────


def test_verify_matches_unchanged_skill(store):
    store.write(_sk(name="alpha"))
    m = build_manifest(store)
    res = verify_skill(m, "tutorial", "alpha", store)
    assert res.matched is True
    assert res.expected_sha256 == res.actual_sha256


def test_verify_detects_tampered_skill(store):
    path, _ = store.write(_sk(name="alpha", body="original" * 10))
    m = build_manifest(store)
    path.write_text(path.read_text().replace("original" * 10, "tampered" * 10))
    res = verify_skill(m, "tutorial", "alpha", store)
    assert res.matched is False
    assert "diverges" in (res.reason or "")
    assert res.expected_sha256 != res.actual_sha256


def test_verify_detects_missing_skill(store):
    path, _ = store.write(_sk(name="alpha"))
    m = build_manifest(store)
    path.unlink()
    res = verify_skill(m, "tutorial", "alpha", store)
    assert res.matched is False
    assert "missing" in (res.reason or "")
    assert res.actual_sha256 is None


def test_verify_flags_unknown_skill(store):
    store.write(_sk(name="alpha"))
    store.write(_sk(name="beta"))
    m = build_manifest(store)
    # Now write a third skill that's not in the manifest
    store.write(_sk(name="gamma"))
    res = verify_skill(m, "tutorial", "gamma", store)
    assert res.matched is False
    assert "not present" in (res.reason or "")


def test_verify_all_runs_against_every_entry(store):
    store.write(_sk(name="alpha"))
    store.write(_sk(name="beta", category="crypto"))
    m = build_manifest(store)
    results = verify_all(m, store)
    assert len(results) == 2
    assert all(r.matched for r in results)


# ─── 0G upload (mocked) ─────────────────────────────────────────


class _MockProvider:
    """Stands in for ZeroGProvider — records the bytes it was asked to upload."""

    def __init__(self, root="0x" + "ab" * 32, fail=False):
        self.root = root
        self.fail = fail
        self.calls: list[tuple[bytes, str]] = []

    async def upload(self, data: bytes, name: str = "blob"):
        self.calls.append((data, name))
        if self.fail:
            raise RuntimeError("simulated 0G failure")
        return self.root, "0xtxhash"


def test_upload_returns_none_with_no_provider(store):
    store.write(_sk(name="alpha"))
    m = build_manifest(store)
    result = asyncio.run(upload_manifest(m))
    assert result is None


def test_upload_ships_canonical_bytes_to_provider(store):
    store.write(_sk(name="alpha"))
    m = build_manifest(store)
    provider = _MockProvider()
    root = asyncio.run(upload_manifest(m, provider=provider))
    assert root == provider.root
    assert len(provider.calls) == 1
    sent_bytes, sent_name = provider.calls[0]
    assert sent_bytes == m.canonical_bytes()
    assert sent_name == "skill_manifest.json"


def test_upload_failure_returns_none_not_raises(store):
    store.write(_sk(name="alpha"))
    m = build_manifest(store)
    provider = _MockProvider(fail=True)
    root = asyncio.run(upload_manifest(m, provider=provider))
    assert root is None


# ─── persistence ────────────────────────────────────────────────


def test_persist_writes_manifest_and_meta(store, tmp_path):
    store.write(_sk(name="alpha"))
    m = build_manifest(store)
    dest = tmp_path / "out" / "current.json"
    written = persist(m, dest=dest, zg_root="0x" + "cd" * 32)
    assert written == dest
    assert dest.exists()
    assert dest.read_bytes() == m.canonical_bytes()
    meta_path = Path(str(dest) + ".meta.json")
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["sha256"] == m.sha256()
    assert meta["skill_count"] == 1
    assert meta["zg_root"] == "0x" + "cd" * 32
    assert meta["manifest_path"] == str(dest)


def test_load_meta_returns_none_when_no_manifest(tmp_path):
    assert load_meta(tmp_path / "nothing.json") is None


def test_load_meta_round_trips(store, tmp_path):
    store.write(_sk(name="alpha"))
    m = build_manifest(store)
    dest = tmp_path / "current.json"
    persist(m, dest=dest, zg_root="0x" + "ef" * 32)
    meta = load_meta(dest)
    assert meta is not None
    assert meta["sha256"] == m.sha256()
    assert meta["zg_root"] == "0x" + "ef" * 32


# ─── chain anchor (Phase B stub) ────────────────────────────────


def test_anchor_manifest_is_stub_returning_not_anchored():
    """Phase B — should return ("not_anchored", None) until the SkillRegistry
    contract is deployed. Callers can compose against the final shape now."""
    status, tx = anchor_manifest("0x" + "11" * 32)
    assert status == "not_anchored"
    assert tx is None
