# Copyright 2026 BANKON. All rights reserved.
# Licensed under the Apache License, Version 2.0.
"""dato suite tests — process lifecycle, permanence tiers, naming, membership, AO spawn.

All offline: temp registry (never touches dato/data/), immortal Arweave upload is
monkeypatched, AO spawn runs dry-run.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from dato.core import membership, naming, permanence
from dato.core.dato_process import DatoError, DatoRegistry
from dato.core.model import DataRecord, PermanenceTier, Settings


@pytest.fixture
def reg():
    return DatoRegistry(path=Path(tempfile.mktemp(suffix=".json")))


# ── naming ───────────────────────────────────────────────────────────────────
def test_name_grammar_and_tier_declared():
    assert str(naming.parse_name("archive.immortal.blockchain")) == "archive.immortal.blockchain"
    assert naming.tier_of("doc.immutable.blockchain") is PermanenceTier.IMMUTABLE
    assert naming.format_name("x", "mutable") == "x.mutable.blockchain"


def test_name_root_is_extensible():
    with pytest.raises(naming.DatoNameError):
        naming.format_name("x", "immortal", "eth")  # eth not a root yet
    naming.add_root("eth")
    assert naming.format_name("x", "immortal", "eth") == "x.immortal.eth"
    assert "eth" in naming.roots()


def test_name_rejects_non_tier_middle_label():
    with pytest.raises(naming.DatoNameError):
        naming.parse_name("x.forever.blockchain")


# ── permanence tiers ──────────────────────────────────────────────────────────
def test_immutable_hash_lock(monkeypatch):
    r1 = permanence.write_record("d.immutable.blockchain", b"v1", "immutable")
    assert r1.proof.startswith("anchor:")
    # same bytes ok
    permanence.write_record("d.immutable.blockchain", b"v1", "immutable", existing=r1)
    # different bytes rejected
    with pytest.raises(permanence.PermanenceError):
        permanence.write_record("d.immutable.blockchain", b"v2", "immutable", existing=r1)


def test_mutable_versions():
    r1 = permanence.write_record("n.mutable.blockchain", b"a", "mutable")
    r2 = permanence.write_record("n.mutable.blockchain", b"b", "mutable", existing=r1)
    assert (r1.version, r2.version) == (1, 2)
    assert r2.mutable_value is not None


def test_immortal_uses_arweave_turbo(monkeypatch):
    class _FakeDesk:
        def upload(self, data, **kw):
            assert ("Dato-Tier", "immortal") in kw["extra_tags"]
            return {"arweaveId": "TXID_200YR"}
    monkeypatch.setattr("tools.arweave_turbo.ArweaveTurboDesk", lambda *a, **k: _FakeDesk())
    rec = permanence.write_record("v.immortal.blockchain", b"forever", "immortal")
    assert rec.tier is PermanenceTier.IMMORTAL and rec.proof == "TXID_200YR"


# ── process lifecycle (spawn → join → govern → commit) ─────────────────────────
def test_spawn_records_owner_and_deployer(reg):
    inst = reg.spawn("archive", tier="immutable", deployer_wallet="0x" + "ab" * 20, owner_daio="daio")
    assert inst.owner_daio == "daio"
    assert inst.deployer_wallet == "0x" + "ab" * 20
    assert inst.deployer_wallet in inst.members  # founding member
    assert inst.name == "archive.immutable.blockchain"


def test_commit_and_resolve(reg):
    inst = reg.spawn("archive", tier="immutable", deployer_wallet="0xabc")
    rec = reg.commit(inst.dato_id, "doc1", b"hello", tier="immutable")
    assert reg.resolve_name("doc1.immutable.blockchain")["dato_id"] == inst.dato_id
    assert rec.sha256


def test_closed_join_requires_owner(reg):
    inst = reg.spawn("vault", deployer_wallet="0xowner", settings=Settings(open_join=False))
    with pytest.raises(DatoError):
        reg.request_join(inst.dato_id, "0xstranger")


def test_persistence_round_trip(reg):
    inst = reg.spawn("keep", tier="mutable", deployer_wallet="0xdead")
    reg.commit(inst.dato_id, "k", b"x", tier="mutable")
    reg2 = DatoRegistry(path=reg.path)  # reload from disk
    assert reg2.get(inst.dato_id) is not None
    assert reg2.resolve_name("k.mutable.blockchain") is not None


# ── membership (request-to-join fee + settings) ────────────────────────────────
def test_paid_join_requires_settled_fee(reg):
    inst = reg.spawn("paid", deployer_wallet="0xo", settings=Settings(join_fee_microusd=10000))
    q = membership.quote_join(reg, inst.dato_id)
    assert q["fee_microusd"] == 10000 and q["x402_endpoint"] == "/dato/join"
    with pytest.raises(membership.JoinFeeRequired):
        membership.join(reg, inst.dato_id, "0xmember")
    m = membership.join(reg, inst.dato_id, "0xmember", fee_tx="0xrcpt",
                        fee_paid_microusd=10000, settings={"role": "reader"})
    assert m.fee_paid_microusd == 10000 and m.settings == {"role": "reader"}


def test_free_open_join_admits_directly(reg):
    inst = reg.spawn("free", deployer_wallet="0xo", settings=Settings(join_fee_microusd=0, open_join=True))
    m = membership.join(reg, inst.dato_id, "0xfriend")
    assert m.wallet == "0xfriend"


# ── AO substrate (dry-run safe) ────────────────────────────────────────────────
def test_ao_spawn_dry_run_and_message_envelope():
    from dato.ao import spawn as ao
    res = ao.spawn_dato_process("archive.immortal.blockchain", owner_daio="daio",
                                deployer_wallet="0x" + "11" * 20, default_tier="immortal", join_fee=10000)
    assert res.dry_run and len(res.process_id) == 43 and res["owner"] == "daio"
    env = ao.message(res.process_id, "Join", {"Fee-Paid": "10000", "Fee-Tx": "0xr"})
    assert env["dry_run"] and env["envelope"]["Action"] == "Join"
