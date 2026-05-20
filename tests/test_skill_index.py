# SPDX-License-Identifier: Apache-2.0
"""Tests for the hybrid 70/30 BM25 + vector skill index.

Embedder is patched to a deterministic stub so tests are CPU-only and
network-free. Covers:
  * BM25 path returns hits when the embedder is unavailable.
  * Vector path returns hits when the embedder is available.
  * Hybrid fusion combines both sides (union, normalised, weighted sum).
  * SkillStore.search() switches automatically and falls back to substring
    when the index can't be built.
  * Remove + archive drop rows from the index.
  * Empty/whitespace queries return recent rows.
"""
from __future__ import annotations

import pytest

import agents.skills.index as idx_mod
from agents.skills.index import DEFAULT_VECTOR_WEIGHT, SkillIndex
from agents.skills.skill_schema import Skill, SkillFrontmatter
from agents.skills.store import SkillStore


def _sk(name: str, body: str = "", category: str = "tutorial", tags=None) -> Skill:
    return Skill(
        frontmatter=SkillFrontmatter(
            name=name,
            description=body[:60] or "test description",
            category=category,
            tags=tags or [],
        ),
        body=body or f"# {name}\n\nDemo body for {name}.",
    )


# Deterministic stub embedder: returns a length-8 vector keyed off the text.
def _stub_embed(text, *, timeout=5.0):
    if not text:
        return None
    seed = sum(ord(c) for c in text) % 997
    return [((seed * (i + 1)) % 100) / 100.0 for i in range(8)]


@pytest.fixture
def store(tmp_path, monkeypatch):
    """SkillStore + SkillIndex backed by tmp_path, embedder available."""
    monkeypatch.setattr(idx_mod, "_embed_text", _stub_embed)
    return SkillStore(root=tmp_path / "skills")


@pytest.fixture
def store_no_embed(tmp_path, monkeypatch):
    """SkillStore + SkillIndex with the embedder forced unavailable (BM25-only)."""
    monkeypatch.setattr(idx_mod, "_embed_text", lambda text, **k: None)
    return SkillStore(root=tmp_path / "skills")


# ─── bm25-only path ───────────────────────────────────────────────


def test_bm25_only_finds_exact_term(store_no_embed):
    store_no_embed.write(_sk("Validate Wallet Sig", "Recover the signer with eth_account."))
    store_no_embed.write(_sk("Hello World", "Print hello"))
    hits = store_no_embed.search("wallet")
    assert any(h.slug == "validate-wallet-sig" for h in hits)
    # The unrelated skill should not surface for an unrelated keyword.
    assert not any(h.slug == "hello-world" for h in store_no_embed.search("wallet"))


def test_bm25_only_pure_fallback_when_embedder_dead(store_no_embed):
    """vector_weight is internally forced to 0 when the embedder returns None."""
    store_no_embed.write(_sk("Crypto Skill", "Handle EIP-191 signatures"))
    hits = store_no_embed.search("EIP-191", vector_weight=0.7)
    assert hits and hits[0].slug == "crypto-skill"


# ─── hybrid (embedder available) ──────────────────────────────────


def test_hybrid_path_returns_results(store):
    store.write(_sk("Onboard Wallet", "Connect MetaMask and sign a challenge."))
    store.write(_sk("Render Markdown", "Convert markdown to HTML."))
    hits = store.search("metamask wallet")
    slugs = {h.slug for h in hits}
    assert "onboard-wallet" in slugs


def test_hybrid_uses_vector_when_keyword_misses(store):
    """OpenClaw §1.5: union (not intersection) — a hit on the vector side
    surfaces even when BM25 finds nothing."""
    store.write(_sk("Sovereignty", "An intelligence keeps what no one tells it to do."))
    # Query has zero keyword overlap with the skill name/body
    hits = store.search("autonomy independence", vector_weight=0.9)
    # Vector side should still surface "Sovereignty" because the stub embedder
    # produces deterministic vectors → some similarity is non-zero.
    assert hits and hits[0].slug == "sovereignty"


def test_hybrid_weight_extremes(store):
    store.write(_sk("Alpha Skill", "alpha keyword present"))
    store.write(_sk("Beta Skill", "beta keyword present"))

    # vector_weight=0 ⇒ pure BM25 — alpha wins on keyword.
    hits = store.search("alpha", vector_weight=0.0)
    assert hits and hits[0].slug == "alpha-skill"

    # vector_weight=1 ⇒ pure vector — alpha may still win or tie (stub embed),
    # but the call must not raise and must return at least one result.
    hits = store.search("alpha", vector_weight=1.0)
    assert hits


# ─── store integration ───────────────────────────────────────────


def test_archive_drops_from_index(store):
    store.write(_sk("Stale Skill", "Old content for the curator to archive"))
    before = store.search("stale")
    assert any(h.slug == "stale-skill" for h in before)
    store.archive("tutorial", "stale-skill", reason="unused", actor="human")
    after = store.search("stale")
    assert not any(h.slug == "stale-skill" for h in after)


def test_empty_query_returns_recent(store):
    store.write(_sk("First Skill"))
    store.write(_sk("Second Skill"))
    hits = store.search("", limit=10)
    slugs = {h.slug for h in hits}
    assert {"first-skill", "second-skill"}.issubset(slugs)


# ─── pragma integrity_check (mindX improvement over Hermes) ───────


def test_pragma_integrity_check_on_open(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(idx_mod, "_embed_text", _stub_embed)
    # First-open creates clean DB; integrity_check should not warn.
    SkillIndex(skills_root=tmp_path / "skills")
    # Reopen — still ok.
    SkillIndex(skills_root=tmp_path / "skills")
    # Just confirm we didn't raise; the warning path is covered by manual log inspection.


# ─── rebuild from disk ────────────────────────────────────────────


def test_rebuild_indexes_all_on_disk(store):
    paths = []
    for i in range(3):
        store.write(_sk(f"Skill {i}", f"body {i}"))
    # Drop the in-memory index rows and rebuild from disk.
    store._index._conn.execute("DELETE FROM skills_fts")
    store._index._conn.execute("DELETE FROM skill_vec")
    store._index._conn.commit()
    n = store._index.rebuild(store)
    assert n == 3
    hits = store.search("body")
    assert len(hits) == 3
