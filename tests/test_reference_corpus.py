"""Unit tests for utils.reference_corpus — the single source of truth for
which docs/ subtrees are gated reference material (ingested, not published).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from utils.reference_corpus import (
    PRIVATE_DOC_PREFIXES,
    is_private_doc,
    iter_reference_docs,
    iter_unlinked_docs,
)


# ----------------------------------------------------------------------
# is_private_doc
# ----------------------------------------------------------------------


@pytest.mark.parametrize("relpath", [
    "operations/HARD_GATE_RUNBOOK.md",
    "operations/dev/Vercel AI SDK 6_ A Framework-Agnostic Deep Dive (June 2026).md",
    "operations/dev/DAIO/spec.md",
    "blockchain/aave01062026.md",
    "blockchain/x402_rails.py",
    "publications/pdf/book-of-liquidity.pdf",
    # normalization variants
    "/operations/HARD_GATE_RUNBOOK.md",
    "./operations/HARD_GATE_RUNBOOK.md",
    "operations\\HARD_GATE_RUNBOOK.md",
    # case-insensitive (read_doc resolves filenames case-insensitively)
    "OPERATIONS/HARD_GATE_RUNBOOK.md",
    "Publications/PDF/x.pdf",
    # extensionless (how /doc/{name} refers to docs)
    "operations/HARD_GATE_RUNBOOK",
    # bare folder references (NAV.md / href de-linking)
    "operations",
    "blockchain/",
    "publications/pdf",
])
def test_private_paths(relpath):
    assert is_private_doc(relpath), relpath


@pytest.mark.parametrize("relpath", [
    "TECHNICAL.md",
    "publications/the_inference_metabolism.md",
    "publications/daily/2026-06-07.md",
    "publications/NAV.md",
    "agents/memory_agent.md",
    "ollama/api.md",
    # prefix lookalikes — docs/operations.md is a real PUBLIC top-level doc
    # (agent hierarchy, 2025) unrelated to the private operations/ folder
    "operations.md",
    "blockchain.md",
    "publications/pdfs.md",
    "publications",
])
def test_public_paths(relpath):
    assert not is_private_doc(relpath), relpath


def test_prefixes_are_normalized():
    for prefix in PRIVATE_DOC_PREFIXES:
        assert prefix.endswith("/"), prefix
        assert prefix == prefix.lower(), prefix


# ----------------------------------------------------------------------
# iter_unlinked_docs / iter_reference_docs over a synthetic tree
# ----------------------------------------------------------------------


@pytest.fixture
def docs_tree(tmp_path: Path) -> Path:
    docs = tmp_path / "docs"
    layout = {
        "TECHNICAL.md": "# Technical",                     # top-level md — linked, excluded
        "diagram.png": "x",                                 # top-level non-md — unlinked
        "operations/HARD_GATE_RUNBOOK.md": "# Gate",
        "operations/dev/Vercel AI SDK 6_ Deep Dive.md": "# Vercel",
        "operations/dev/DAIO/notes.md": "# DAIO",
        "operations/__pycache__/x.cpython-311.pyc": "x",    # excluded
        "operations/Saved Article_files/style.css": "x",    # excluded (_files asset dir)
        "operations/.hidden.md": "x",                       # excluded
        "blockchain/aave.md": "# Aave",
        "publications/essay.md": "# Essay",                 # subdir md — unlinked, public
        "publications/pdf/book.pdf": "%PDF",
    }
    for rel, content in layout.items():
        p = docs / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return docs


def test_iter_unlinked_docs(docs_tree):
    rels = {rel for rel, _ in iter_unlinked_docs(docs_tree)}
    assert rels == {
        "diagram.png",
        "operations/HARD_GATE_RUNBOOK.md",
        "operations/dev/Vercel AI SDK 6_ Deep Dive.md",
        "operations/dev/DAIO/notes.md",
        "blockchain/aave.md",
        "publications/essay.md",
        "publications/pdf/book.pdf",
    }


def test_iter_reference_docs_only_private(docs_tree):
    rels = {rel for rel, _ in iter_reference_docs(docs_tree)}
    assert rels == {
        "operations/HARD_GATE_RUNBOOK.md",
        "operations/dev/Vercel AI SDK 6_ Deep Dive.md",
        "operations/dev/DAIO/notes.md",
        "blockchain/aave.md",
        "publications/pdf/book.pdf",
    }
    # everything yielded is private by definition
    assert all(is_private_doc(r) for r in rels)


def test_iter_unlinked_docs_missing_dir():
    assert list(iter_unlinked_docs(Path("/nonexistent/docs"))) == []


# ----------------------------------------------------------------------
# IPFS offload exclusion — the corpus never leaves the local substrate
# ----------------------------------------------------------------------


def test_reference_corpus_never_offloaded(tmp_path: Path):
    """stm/reference_corpus/ must be invisible to the IPFS offload projector,
    even when explicitly requested — mindX is not replicating gated content
    across the global substrate."""
    from agents.storage.eligibility import list_eligible, OFFLOAD_EXCLUDED_AGENT_IDS

    assert "reference_corpus" in OFFLOAD_EXCLUDED_AGENT_IDS
    stm = tmp_path / "data" / "memory" / "stm"
    for agent in ("reference_corpus", "some_agent"):
        d = stm / agent / "20250101"
        d.mkdir(parents=True)
        (d / "x.memory.json").write_text("{}", encoding="utf-8")

    agents_seen = {c.agent_id for c in list_eligible(tmp_path, min_age_days=1.0)}
    assert agents_seen == {"some_agent"}
    # explicit agent_id request must not bypass the exclusion
    assert list_eligible(tmp_path, min_age_days=1.0, agent_id="reference_corpus") == []


def test_real_tree_contains_new_corpus():
    """The actual repo's private folders are picked up (guards against the
    prefix list drifting from the on-disk layout)."""
    docs = Path(__file__).parent.parent / "docs"
    rels = {rel for rel, _ in iter_reference_docs(docs)}
    assert any(r.startswith("operations/") for r in rels)
    assert any(r.startswith("operations/dev/") for r in rels)
    assert any(r.startswith("blockchain/") for r in rels)
    assert any(r.startswith("publications/pdf/") for r in rels)
