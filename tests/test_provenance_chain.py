# SPDX-License-Identifier: Apache-2.0
"""Tests for agents/provenance_chain.py — the verifiable "speech from the throne"
chain of command. Uses ephemeral eth keys so the cryptography is proven without
the BANKON vault."""
import json

import pytest

eth_account = pytest.importorskip("eth_account")
from eth_account import Account
from eth_account.messages import encode_defunct

from agents.provenance_chain import (
    ProvenanceChain,
    extract_chain_from_html,
    verify_chain,
)


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _make_signer(keymap):
    """Build a signer(agent_id, message) -> (sig, address) backed by ephemeral keys."""
    def signer(agent_id, message):
        acct = keymap.get(agent_id)
        if acct is None:
            return None
        signed = acct.sign_message(encode_defunct(text=message))
        sig = signed.signature.hex()
        if not sig.startswith("0x"):
            sig = "0x" + sig
        return sig, acct.address
    return signer


# Deterministic ephemeral keys for the full chain of command.
KEYS = {
    "ceo_agent_main": Account.from_key("0x" + "11" * 32),
    "ciso_security":  Account.from_key("0x" + "22" * 32),
    "cro_risk":       Account.from_key("0x" + "33" * 32),
    "author.agent":   Account.from_key("0x" + "44" * 32),
    "editor.agent":   Account.from_key("0x" + "55" * 32),
    "artist.agent":   Account.from_key("0x" + "66" * 32),
    "wordpress.agent": Account.from_key("0x" + "77" * 32),
}


def _full_chain():
    signer = _make_signer(KEYS)
    c = ProvenanceChain.for_statement("Let the record show the board has spoken.",
                                      ts=1780000000, signer=signer)
    c.issue("0x" + "ab" * 32, endorsers=["ciso_security", "cro_risk"])
    c.compose("0x" + "cd" * 32)
    c.edit("0x" + "ce" * 32)
    c.illustrate("0x" + "ef" * 32)
    c.publish("0x" + "f0" * 32)
    return c


def test_full_chain_verifies():
    c = _full_chain()
    # throne + 2 soldiers + author + editor + artist + wordpress = 7 links
    assert len(c.links) == 7
    report = verify_chain(c.to_dict(), registry={})
    assert report["valid"] is True
    assert report["chain_intact"] is True
    assert report["signatures_valid"] is True
    assert report["signed_links"] == 7
    # Each link recovered to exactly the signing wallet.
    for link, res in zip(c.links, report["results"]):
        assert res["signature_ok"] is True
        assert res["recovered"].lower() == KEYS[link.agent_id].address.lower()


def test_chain_of_command_order():
    c = _full_chain()
    acts = [(l.role, l.act) for l in c.links]
    assert acts[0] == ("throne", "issued")
    assert ("soldier", "endorsed") in acts
    assert ("author", "composed") in acts
    assert ("editor", "edited") in acts
    assert ("artist", "illustrated") in acts
    assert acts[-1] == ("wordpress", "published")


def test_tampered_payload_breaks_verification():
    c = _full_chain()
    d = c.to_dict()
    # An attacker rewrites what the author supposedly composed.
    author_link = next(l for l in d["links"] if l["role"] == "author")
    author_link["payload_sha256"] = "0x" + "00" * 32
    report = verify_chain(d, registry={})
    assert report["valid"] is False
    # The forged link fails its challenge reconstruction (and signature).
    bad = next(r for r in report["results"] if r["role"] == "author")
    assert bad["challenge_ok"] is False or bad["signature_ok"] is False


def test_tampered_signature_breaks_verification():
    c = _full_chain()
    d = c.to_dict()
    ed = next(l for l in d["links"] if l["role"] == "editor")
    # Swap in the CEO's would-be signature — recovers to the wrong address.
    other = c.links[0].signature
    ed["signature"] = other
    report = verify_chain(d, registry={})
    assert report["valid"] is False


def test_broken_linkage_detected():
    c = _full_chain()
    d = c.to_dict()
    d["links"][3]["prev"] = "0xdeadbeef"   # snip the hash chain
    report = verify_chain(d, registry={})
    assert report["chain_intact"] is False
    assert report["valid"] is False


def test_registry_mismatch_flagged():
    c = _full_chain()
    # Registry claims a DIFFERENT address for the CEO than the one that signed.
    fake_registry = {"ceo_agent_main": "0x" + "99" * 20}
    report = verify_chain(c.to_dict(), registry=fake_registry)
    assert report["registry_match"] is False
    assert report["valid"] is False


def test_unsigned_link_is_attested_not_fatal():
    # artist.agent has no key → its link is unsigned but the chain stays intact.
    keys = dict(KEYS); keys.pop("artist.agent")
    c = ProvenanceChain.for_statement("s", ts=1, signer=_make_signer(keys))
    c.issue("0x" + "ab" * 32)
    c.compose("0x" + "cd" * 32)
    c.illustrate("0x" + "ef" * 32)   # unsigned
    c.publish("0x" + "f0" * 32)
    report = verify_chain(c.to_dict(), registry={})
    assert report["chain_intact"] is True
    assert report["unsigned_links"] == 1
    assert report["valid"] is True   # signed links all valid; unsigned attested


def test_html_embeds_recoverable_chain():
    c = _full_chain()
    html = c.to_html(_esc)
    assert "Speech from the throne" in html
    assert "chain of command" in html
    extracted = extract_chain_from_html(html)
    assert extracted is not None
    report = verify_chain(extracted, registry={})
    assert report["valid"] is True and report["signed_links"] == 7
