# SPDX-License-Identifier: Apache-2.0
"""Standalone tests for ephermaleth — chain + verify + signers + votingbooth.
Run from openagents/ephermaleth/:  python -m pytest tests/ -q"""
import os
import sys

import pytest

# Make the package importable when run in-tree (openagents/ephermaleth/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

pytest.importorskip("eth_account")
from eth_account import Account

from ephermaleth import (
    AttestationChain,
    EnvKeystoreSigner,
    KeymapSigner,
    NullSigner,
    VotingBooth,
    parse_keys_env,
    sha256_hex,
    verify_chain,
)

ACCTS = {r: Account.from_key("0x" + f"{i+1:02x}" * 32)
         for i, r in enumerate(["ceo", "soldier", "author", "editor", "artist", "publisher"])}
KEYMAP = {r: a.key.hex() for r, a in ACCTS.items()}
REGISTRY = {r: a.address for r, a in ACCTS.items()}


def _chain(signer=None):
    c = AttestationChain.anchored("The board has spoken.", ts=1780000000,
                                  signer=signer or KeymapSigner(KEYMAP), registry=REGISTRY)
    c.add_link("throne", "ceo", "issued", sha256_hex("statement"))
    c.add_link("soldier", "soldier", "endorsed", sha256_hex("statement"))
    c.add_link("author", "author", "composed", sha256_hex("body"))
    c.add_link("editor", "editor", "edited", sha256_hex("body"))
    c.add_link("artist", "artist", "illustrated", sha256_hex("art-cid"))
    c.add_link("publisher", "publisher", "published", sha256_hex("body"))
    return c


def test_full_chain_verifies():
    rep = verify_chain(_chain().to_dict(), REGISTRY)
    assert rep["valid"] and rep["chain_intact"] and rep["signatures_valid"]
    assert rep["signed_links"] == 6 and rep["registry_match"]


def test_order_and_recovery():
    c = _chain()
    assert [l.act for l in c.links] == ["issued", "endorsed", "composed",
                                        "edited", "illustrated", "published"]
    rep = verify_chain(c.to_dict(), REGISTRY)
    for link, res in zip(c.links, rep["results"]):
        assert res["recovered"].lower() == ACCTS[link.agent_id].address.lower()


def test_tampered_payload_fails():
    d = _chain().to_dict()
    next(l for l in d["links"] if l["role"] == "author")["payload_sha256"] = "0x" + "00" * 32
    assert verify_chain(d, REGISTRY)["valid"] is False


def test_tampered_signature_fails():
    d = _chain().to_dict()
    d["links"][3]["signature"] = d["links"][0]["signature"]   # wrong signer
    assert verify_chain(d, REGISTRY)["valid"] is False


def test_broken_linkage_fails():
    d = _chain().to_dict()
    d["links"][2]["prev"] = "0xdead"
    rep = verify_chain(d, REGISTRY)
    assert rep["chain_intact"] is False and rep["valid"] is False


def test_registry_mismatch_fails():
    rep = verify_chain(_chain().to_dict(), {"ceo": "0x" + "99" * 20})
    assert rep["registry_match"] is False and rep["valid"] is False


def test_null_signer_attests_but_stays_intact():
    rep = verify_chain(_chain(signer=NullSigner()).to_dict(), REGISTRY)
    assert rep["chain_intact"] is True and rep["valid"] is True
    assert rep["signed_links"] == 0 and rep["unsigned_links"] == 6


def test_env_keystore_signer():
    env_text = "\n".join(
        f"MINDX_WALLET_PK_{r.upper()}={a.key.hex()}" for r, a in ACCTS.items())
    env = parse_keys_env("# header\n\n" + env_text)
    signer = EnvKeystoreSigner(env)
    c = AttestationChain.anchored("x", ts=1, signer=signer, registry=REGISTRY)
    c.add_link("throne", "ceo", "issued", sha256_hex("s"))
    rep = verify_chain(c.to_dict(), REGISTRY)
    assert rep["valid"] and rep["signed_links"] == 1


def test_votingbooth_append_and_verify(tmp_path):
    booth = VotingBooth(tmp_path / "booth.jsonl")
    r1 = booth.record(council="boardroom", subject="On the voice", decision="passed",
                      ts=1780000000, chain=_chain().to_dict(),
                      tally={"for": 6, "against": 1, "quorum": True})
    r2 = booth.record(council="warcouncil", subject="On deployment", decision="rejected",
                      ts=1780000100, votes=[{"id": "cro_risk", "vote": "veto"}])
    assert r2["prev"] == r1["record_hash"]            # hash-linked
    assert len(booth.list()) == 2
    assert len(booth.list(council="boardroom")) == 1
    rep = booth.verify_ledger(REGISTRY)
    assert rep["valid"] and rep["records"] == 2 and rep["linkage_ok"]


def test_challenge_is_injective_no_separator_smuggling():
    # An identity that tries to smuggle a second field past the separators must
    # NOT collide with a clean field-set — percent-encoding makes build_challenge
    # injective, so the two produce different signed strings.
    from ephermaleth import build_challenge
    a = build_challenge("c", 0, "throne", "ceo", "issued", "0xpay", "0x0")
    b = build_challenge("c", 0, "throne", "ceo | agent=evil", "issued", "0xpay", "0x0")
    assert a != b
    # And the encoded form carries no raw structural separator inside a value.
    enc = build_challenge("c", 0, "r", "a | b = c", "act", "0x", "0x0")
    agent_field = enc.split("agent=")[1].split(" | ")[0]
    assert "|" not in agent_field and " " not in agent_field and "=" not in agent_field


def test_injection_link_does_not_reuse_a_signature():
    # Build a clean signed chain, then forge a link whose agent_id tries to reuse
    # the throne signature via separator games — verification must reject it.
    c = _chain()
    d = c.to_dict()
    forged = dict(d["links"][0])
    forged["agent_id"] = "ceo | act=hijacked"      # different identity, same sig
    d["links"][0] = forged
    assert verify_chain(d, REGISTRY)["valid"] is False


def test_cli_verify_and_booth(tmp_path, capsys):
    import json as _json
    from ephermaleth.cli import main
    chain_file = tmp_path / "chain.json"
    chain_file.write_text(_json.dumps(_chain().to_dict()))
    reg_file = tmp_path / "reg.json"
    reg_file.write_text(_json.dumps(REGISTRY))
    rc = main(["verify", str(chain_file), "--registry", str(reg_file)])
    out = capsys.readouterr().out
    assert rc == 0 and "VALID" in out
    # tampered → non-zero exit
    d = _chain().to_dict(); d["links"][2]["payload_sha256"] = "0x" + "00" * 32
    bad = tmp_path / "bad.json"; bad.write_text(_json.dumps(d))
    assert main(["verify", str(bad)]) == 1
    # booth
    booth = VotingBooth(tmp_path / "b.jsonl")
    booth.record(council="boardroom", subject="s", decision="passed", ts=1,
                 chain=_chain().to_dict())
    assert main(["booth", str(tmp_path / "b.jsonl"), "--registry", str(reg_file)]) == 0


def test_votingbooth_detects_tampered_record(tmp_path):
    booth = VotingBooth(tmp_path / "booth.jsonl")
    booth.record(council="boardroom", subject="A", decision="passed", ts=1)
    # Rewrite the decision in place without fixing the hash.
    rows = booth.path.read_text().splitlines()
    booth.path.write_text(rows[0].replace('"passed"', '"rejected"') + "\n")
    assert booth.verify_ledger()["records_ok"] is False
