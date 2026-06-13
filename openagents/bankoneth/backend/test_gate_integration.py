# SPDX-License-Identifier: Apache-2.0
"""Gate integration test against fork-equivalent chain state.

anvil mainnet-fork mirrors mainnet ENS, so pointing the gate at a mainnet RPC
(BANKON_GATE_RPC) exercises exactly the NameWrapper state a fork would have.
Run:  BANKON_GATE_SECRET=$(openssl rand -hex 24) python -m pytest backend/test_gate_integration.py -o addopts="" -q
(needs network for the ENS reads; set BANKON_GATE_RPC=http://127.0.0.1:8545 to hit a live anvil fork.)
"""
import os

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct

os.environ.setdefault("BANKON_GATE_SECRET", "x" * 40)

from fastapi.testclient import TestClient  # noqa: E402

from backend.app import app  # noqa: E402
from backend.auth import COOKIE, issue_session_jwt  # noqa: E402
from backend.tiers import resolve_tier  # noqa: E402

BANKON_OWNER = "0x54165AdA93FA752cfec95F3f3bAE2676D3752A99"
c = TestClient(app)


def test_resolve_tier_owner_is_admin():
    assert resolve_tier(BANKON_OWNER)["tier"] == "admin"


def test_resolve_tier_random_is_visitor():
    assert resolve_tier("0x1111111111111111111111111111111111111111")["tier"] == "visitor"


def test_auth_flow_real_signature_visitor():
    """Full challenge → personal_sign → verify against the live gate + RPC."""
    acct = Account.create()
    ch = c.post("/auth/challenge", json={"address": acct.address}).json()
    sig = Account.sign_message(encode_defunct(text=ch["message"]), acct.key).signature.hex()
    if not sig.startswith("0x"):
        sig = "0x" + sig
    v = c.post("/auth/verify", json={"address": acct.address, "nonce": ch["nonce"], "signature": sig}).json()
    assert v["tier"] == "visitor"  # a fresh wallet owns nothing
    assert v["token"]


def test_auth_rejects_forged_signature():
    a, b = Account.create(), Account.create()
    ch = c.post("/auth/challenge", json={"address": a.address}).json()
    sig = Account.sign_message(encode_defunct(text=ch["message"]), b.key).signature.hex()  # wrong signer
    if not sig.startswith("0x"):
        sig = "0x" + sig
    r = c.post("/auth/verify", json={"address": a.address, "nonce": ch["nonce"], "signature": sig})
    assert r.status_code == 401


def test_gate_hides_admin_from_visitor():
    r = c.get("/admin.html", headers={"accept": "text/html"}, follow_redirects=False)
    assert r.status_code == 302
    assert c.get("/vault/credentials/list").status_code == 401


def test_gate_admits_admin_session():
    cc = TestClient(app)
    cc.cookies.set(COOKIE, issue_session_jwt(BANKON_OWNER, "admin"))
    assert cc.get("/admin.html").status_code == 200
    assert cc.get("/vault/credentials/list").status_code == 200


def test_gate_member_blocked_from_admin():
    cc = TestClient(app)
    cc.cookies.set(COOKIE, issue_session_jwt("0xa1", "member"))
    assert cc.get("/member.html").status_code == 200
    assert cc.get("/admin.html", headers={"accept": "text/html"}, follow_redirects=False).status_code == 302
