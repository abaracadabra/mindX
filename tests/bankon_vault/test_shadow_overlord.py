"""Unit tests for bankon_vault.shadow_overlord — NonceStore + JWT + sig recovery.

These tests do NOT touch FastAPI; they exercise the pure functions directly.
The integration story (route-level) is covered in test_cabinet.py.
"""
from __future__ import annotations

import os
import secrets
import tempfile
import time
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import HTTPException


@pytest.fixture
def overlord(monkeypatch, tmp_path):
    """Synthesize a shadow-overlord wallet + isolated nonce store."""
    acct = Account.create()
    monkeypatch.setenv("SHADOW_OVERLORD_ADDRESS", acct.address)
    monkeypatch.setenv("SHADOW_JWT_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("SHADOW_NONCES_PATH", str(tmp_path / "nonces.json"))

    # Reset module-level state so fixture is clean.
    from mindx_backend_service.bankon_vault import shadow_overlord as so
    so._store = None
    so.reset_store_for_tests(Path(os.environ["SHADOW_NONCES_PATH"]))
    return acct


def _sign(acct, msg: str) -> str:
    return acct.sign_message(encode_defunct(text=msg)).signature.hex()


def test_challenge_well_formed(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import issue_challenge

    res = issue_challenge("auth")
    assert res["nonce"].startswith("0x") and len(res["nonce"]) == 66  # 0x + 64 hex
    assert "MINDX-SHADOW-OVERLORD scope=auth" in res["message"]
    assert res["expires_at"] >= int(time.time()) + 110


def test_consume_signed_challenge_happy(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge, SCOPE_AUTH,
    )
    ch = issue_challenge(SCOPE_AUTH)
    sig = _sign(overlord, ch["message"])
    params = consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_AUTH)
    assert params == {}


def test_replay_rejected(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge, SCOPE_AUTH,
    )
    ch = issue_challenge(SCOPE_AUTH)
    sig = _sign(overlord, ch["message"])
    consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_AUTH)
    with pytest.raises(HTTPException) as exc:
        consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_AUTH)
    assert exc.value.status_code == 409


def test_wrong_signer_rejected(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge, SCOPE_AUTH,
    )
    ch = issue_challenge(SCOPE_AUTH)
    attacker = Account.create()
    sig = _sign(attacker, ch["message"])
    with pytest.raises(HTTPException) as exc:
        consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_AUTH)
    assert exc.value.status_code == 403


def test_scope_mismatch_rejected(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge,
        SCOPE_AUTH, SCOPE_CABINET_PROVISION,
    )
    ch = issue_challenge(SCOPE_AUTH)
    sig = _sign(overlord, ch["message"])
    with pytest.raises(HTTPException) as exc:
        consume_signed_challenge(ch["nonce"], sig, expected_scope=SCOPE_CABINET_PROVISION)
    assert exc.value.status_code == 403
    assert "scope mismatch" in exc.value.detail


def test_params_tamper_rejected(overlord):
    """Challenge bound to PYTHAI must NOT validate when used for ALICE."""
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        consume_signed_challenge, issue_challenge, SCOPE_CABINET_PROVISION,
    )
    ch = issue_challenge(SCOPE_CABINET_PROVISION, {"company": "PYTHAI"})
    sig = _sign(overlord, ch["message"])
    with pytest.raises(HTTPException) as exc:
        consume_signed_challenge(
            ch["nonce"], sig,
            expected_scope=SCOPE_CABINET_PROVISION,
            expected_params={"company": "ALICE"},
        )
    assert exc.value.status_code == 400


def test_jwt_round_trip(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        issue_jwt, verify_jwt, SCOPE_AUTH,
    )
    res = issue_jwt(overlord.address, scope=SCOPE_AUTH)
    claims = verify_jwt(res["jwt"], required_scope=SCOPE_AUTH)
    assert claims["sub"].lower() == overlord.address.lower()
    assert claims["scope"] == SCOPE_AUTH


def test_jwt_wrong_scope_rejected(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        issue_jwt, verify_jwt, SCOPE_AUTH, SCOPE_RELEASE_KEY,
    )
    res = issue_jwt(overlord.address, scope=SCOPE_AUTH)
    with pytest.raises(HTTPException) as exc:
        verify_jwt(res["jwt"], required_scope=SCOPE_RELEASE_KEY)
    assert exc.value.status_code == 403


def test_jwt_subject_must_be_overlord(overlord):
    """Even a valid HS256 token signed by us is rejected if `sub` is not the overlord."""
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        issue_jwt, verify_jwt, SCOPE_AUTH,
    )
    other = Account.create()
    res = issue_jwt(other.address, scope=SCOPE_AUTH)
    with pytest.raises(HTTPException) as exc:
        verify_jwt(res["jwt"])
    assert exc.value.status_code == 403


def test_concurrent_challenges_distinct(overlord):
    from mindx_backend_service.bankon_vault.shadow_overlord import issue_challenge, SCOPE_AUTH
    nonces = {issue_challenge(SCOPE_AUTH)["nonce"] for _ in range(20)}
    assert len(nonces) == 20
