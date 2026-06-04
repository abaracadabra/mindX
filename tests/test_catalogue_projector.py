# SPDX-License-Identifier: Apache-2.0
"""Tests for the Knowledge Catalogue Phase 1 read-model.

Pure-function tests (URN minting, EventKind→EntryKind mapping totality, extractor
coverage, projector dry-run idempotency) run with NO database. The DB-dependent
tests (real upsert idempotency, hybrid search) are gated behind a Postgres
reachability probe and skip — rather than fail — when pg is unavailable (the
production DB lives on the VPS, not in CI/local).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agents.catalogue.events import EVENT_KINDS
from agents.catalogue.model import (
    ENTRY_KINDS,
    EVENTKIND_TO_ENTRYKIND,
    derive_entry,
    mint_urn,
)
from agents.catalogue.projector import CatalogueProjector


# ── pure-function tests (no DB) ─────────────────────────────────────────────
def test_mint_urn_stable():
    a = mint_urn("memory", "agent X", "mem 123")
    b = mint_urn("memory", "agent X", "mem 123")
    assert a == b == "urn:mindx:memory:agent-x:mem-123"
    assert mint_urn("memory", "a", "m", version=2).endswith(":v2")


def test_every_eventkind_maps_to_valid_entrykind():
    unmapped = [k for k in EVENT_KINDS if k not in EVENTKIND_TO_ENTRYKIND]
    assert unmapped == [], f"unmapped EventKinds: {unmapped}"
    invalid = [(k, v) for k, v in EVENTKIND_TO_ENTRYKIND.items() if v not in ENTRY_KINDS]
    assert invalid == [], f"EntryKinds not in ENTRY_KINDS: {invalid}"


def test_derive_entry_handles_all_kinds_without_raising():
    payload = {"memory_id": "m", "content": "hello world", "cycle_id": "c",
               "session_id": "s", "post_id": 7, "tx_hash": "0xabc", "tags": ["t1"]}
    for k in EVENT_KINDS:
        evt = {"event_id": "019e-deadbeef", "ts": 1.0, "actor": "agent_x",
               "kind": k, "source_ref": "ref", "payload": payload}
        d = derive_entry(evt)
        assert d.urn.startswith("urn:mindx:")
        assert d.kind in ENTRY_KINDS
        assert d.source_event_id == "019e-deadbeef"


def test_memory_write_extractor_shape():
    evt = {"event_id": "e1", "ts": 100.0, "actor": "bdi_agent",
           "kind": "memory.write",
           "payload": {"memory_id": "abc123", "memory_type": "system_state",
                       "content": {"process_name": "bdi_goal_set"},
                       "parent_memory_id": "parent9", "tags": ["bdi", "process_log"]}}
    d = derive_entry(evt)
    assert d.kind == "memory"
    assert d.urn == "urn:mindx:memory:bdi_agent:abc123"
    assert d.is_text_bearing  # has content text
    assert any(l.type == "derivedFrom" for l in d.links)
    assert "bdi" in d.tags


def test_publication_published_links_to_attempted():
    evt = {"event_id": "e2", "ts": 1.0, "actor": "author_agent",
           "kind": "publication.published",
           "payload": {"post_id": 759, "title": "Milestone", "url": "https://x",
                       "trigger_id": "trig1"}}
    d = derive_entry(evt)
    assert d.kind == "publication"
    assert d.urn == "urn:mindx:publication:author_agent:759"
    assert any(l.type == "derivedFrom" and "trig1" in l.target_urn for l in d.links)


def test_dormant_kind_falls_through_to_generic():
    evt = {"event_id": "e3", "ts": 1.0, "actor": "x", "kind": "skill.invoke",
           "payload": {"foo": "bar"}}
    d = derive_entry(evt)
    assert d.kind == EVENTKIND_TO_ENTRYKIND["skill.invoke"]
    assert d.title == "skill.invoke"


def test_projector_dry_run_over_fixture(tmp_path):
    """Dry-run folds a fixture JSONL with no DB writes; counts are exact."""
    log = tmp_path / "catalogue_events.jsonl"
    events = [
        {"event_id": f"e{i}", "ts": float(i), "actor": "a", "kind": "memory.write",
         "payload": {"memory_id": f"m{i}", "content": f"text {i}"}}
        for i in range(10)
    ]
    log.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    proj = CatalogueProjector()
    run = asyncio.run(
        proj.project_file(log, embed=False, dry_run=True))
    assert run.events_seen == 10
    assert run.entries_upserted == 10  # would-upsert
    assert run.errors == 0
    assert run.final_offset == log.stat().st_size


def test_projector_skips_bad_lines(tmp_path):
    log = tmp_path / "catalogue_events.jsonl"
    log.write_text('{"event_id":"e1","ts":1.0,"actor":"a","kind":"memory.write","payload":{"memory_id":"m1","content":"x"}}\n'
                   'not json at all\n'
                   '{"event_id":"e2","ts":2.0,"actor":"a","kind":"memory.write","payload":{"memory_id":"m2","content":"y"}}\n')
    proj = CatalogueProjector()
    run = asyncio.run(
        proj.project_file(log, embed=False, dry_run=True))
    assert run.events_seen == 2
    assert run.bad_lines == 1


# ── DB-gated integration tests ──────────────────────────────────────────────
def _pg_up() -> bool:
    """Probe Postgres with a throwaway connection so we don't bind the shared
    module pool to an ephemeral event loop (which would clash with the test's
    own asyncio.run loop on the VPS)."""
    async def _probe():
        import asyncpg
        from agents.memory_pgvector import DB_DSN
        conn = await asyncpg.connect(DB_DSN, timeout=4)
        await conn.close()
        return True
    try:
        return bool(asyncio.run(_probe()))
    except Exception:
        return False


pg_required = pytest.mark.skipif(not _pg_up(), reason="Postgres/pgvector not reachable")


@pg_required
def test_lineage_traversal_real_db(tmp_path):
    from agents import memory_pgvector as pg

    async def _run():
        await pg.init_catalogue_schema()
        # child --derivedFrom--> parent ; grandchild --derivedFrom--> child
        base = "urn:mindx:test:lin"
        async def _put(urn, links):
            await pg.upsert_catalogue_entry(
                urn=urn, kind="misc", actor="ci", actor_wallet=None, ts=1.0,
                title=urn.split(":")[-1], text=None, payload={}, tags=[],
                links=links, source_event_id=urn, embedding=None)
        await _put(f"{base}:parent", [])
        await _put(f"{base}:child", [{"type": "derivedFrom", "target_urn": f"{base}:parent"}])
        await _put(f"{base}:grandchild", [{"type": "derivedFrom", "target_urn": f"{base}:child"}])
        # ancestors of grandchild = child (d1), parent (d2)
        lin = await pg.catalogue_lineage(f"{base}:grandchild", direction="ancestors", depth=6)
        anc_dsts = {e["dst_urn"] for e in lin["ancestors"]}
        assert f"{base}:child" in anc_dsts and f"{base}:parent" in anc_dsts
        # descendants of parent = child (d1), grandchild (d2)
        lin2 = await pg.catalogue_lineage(f"{base}:parent", direction="descendants", depth=6)
        desc_srcs = {e["src_urn"] for e in lin2["descendants"]}
        assert f"{base}:child" in desc_srcs and f"{base}:grandchild" in desc_srcs

    asyncio.run(_run())


@pg_required
def test_upsert_idempotent_real_db(tmp_path):
    from agents import memory_pgvector as pg

    async def _run():
        await pg.init_catalogue_schema()
        urn = "urn:mindx:test:ci:idempotency-probe"
        for _ in range(3):
            await pg.upsert_catalogue_entry(
                urn=urn, kind="misc", actor="ci", actor_wallet=None, ts=1.0,
                title="t", text="hello", payload={"k": "v"}, tags=["ci"],
                links=[], source_event_id="ev1", embedding=None)
        row = await pg.catalogue_entry_by_urn(urn)
        assert row is not None
        assert row["source_event_ids"] == ["ev1"]  # deduped
        # second source event merges
        await pg.upsert_catalogue_entry(
            urn=urn, kind="misc", actor="ci", actor_wallet=None, ts=2.0,
            title="t", text="hello", payload={"k": "v"}, tags=["ci"],
            links=[], source_event_id="ev2", embedding=None)
        row = await pg.catalogue_entry_by_urn(urn)
        assert set(row["source_event_ids"]) == {"ev1", "ev2"}
        assert row["ts"] == 2.0  # newest kept

    asyncio.run(_run())
