"""
Tests for the /vault/credentials/reunlock route handler.

The endpoint recovers credential loading after a service restart under
HumanOverseer custody. Two flows:
  - Flow A: replay .overseer_proof.json from disk (default)
  - Flow B: caller supplies fresh {address, signature, message}

Both must inject PROVIDER_ENV_MAP entries into os.environ on success.
The endpoint must refuse cleanly when the vault is not under HumanOverseer
custody (no sentinel) or when neither proof file nor body evidence is
available.
"""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
sys.path.insert(0, str(_REPO_ROOT))


def _seed_handed_off_vault(vault_dir: Path) -> dict:
    """
    Build a disposable vault, store a known PROVIDER_ENV_MAP entry, perform
    a Machine→Human rotation, then return the sig materials so tests can
    construct Flow B requests.
    """
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from mindx_backend_service.bankon_vault.vault import BankonVault
    from mindx_backend_service.bankon_vault.overseer import HumanOverseer

    os.environ["MINDX_VAULT_ALLOW_OVERSEER_ROTATION"] = "1"
    test_priv = "0x" + "33" * 32
    acct = Account.from_key(test_priv)

    v = BankonVault(vault_dir=str(vault_dir))
    v.unlock_with_key_file()
    # Use a real PROVIDER_ENV_MAP key so the env-injection loop hits it.
    v.store("openai_api_key", "sk-test-injected-by-reunlock", context="provider")

    overseer = HumanOverseer(eth_address=acct.address, vault_salt=v._salt)
    challenge_text = "BANKON Vault Custody Handoff v1 — reunlock test"
    msg = encode_defunct(text=challenge_text)
    sig_hex = Account.sign_message(msg, private_key=test_priv).signature.hex()
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex
    evidence = {"kind": "human", "signature": sig_hex, "message": challenge_text}
    challenge_bytes = challenge_text.encode("utf-8")

    v.rotate_overseer(overseer, challenge_bytes, evidence,
                      reason="reunlock_test_setup", dry_run=True)
    v.rotate_overseer(overseer, challenge_bytes, evidence,
                      reason="reunlock_test_commit", dry_run=False)
    # Vault is now under HumanOverseer custody, key in memory.
    v.lock()

    return {
        "address": acct.address,
        "signature": sig_hex,
        "message": challenge_text,
    }


@pytest.fixture
def handed_off_vault(monkeypatch):
    """
    Stand up a disposable vault, complete the handoff, then point the
    routes-module singleton at it for the duration of the test.
    """
    from mindx_backend_service.bankon_vault import routes
    from mindx_backend_service.bankon_vault.vault import BankonVault
    from mindx_backend_service.bankon_vault.credential_provider import CredentialProvider

    tmp = Path(tempfile.mkdtemp(prefix="reunlock-test-"))
    parent = tmp / "run"
    parent.mkdir()
    vault_dir = parent / "vault_bankon"

    # Clear any pre-existing env from prior tests so we can verify injection
    pre_env = os.environ.pop("OPENAI_API_KEY", None)
    try:
        sig_materials = _seed_handed_off_vault(vault_dir)

        # Swap the routes-module singletons to point at the disposable vault.
        # The handed-off vault is already locked; the route's reunlock handler
        # will load it under the proof file (Flow A) or body evidence (Flow B).
        test_vault = BankonVault(vault_dir=str(vault_dir))
        test_provider = CredentialProvider(test_vault)
        monkeypatch.setattr(routes, "_vault", test_vault)
        monkeypatch.setattr(routes, "_provider", test_provider)

        yield sig_materials, vault_dir
    finally:
        if pre_env is not None:
            os.environ["OPENAI_API_KEY"] = pre_env
        else:
            os.environ.pop("OPENAI_API_KEY", None)
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_reunlock_flow_a_proof_file(handed_off_vault):
    """No body — handler reads .overseer_proof.json and re-unlocks."""
    from mindx_backend_service.bankon_vault.routes import reunlock
    sig, vault_dir = handed_off_vault
    assert (vault_dir / ".overseer_proof.json").exists()

    res = await reunlock(req=None, wallet="0xadmin_test")
    assert res["status"] == "unlocked"
    assert res["source"] == "proof_file"
    assert "OPENAI_API_KEY" in res["env_vars"]
    assert os.environ.get("OPENAI_API_KEY") == "sk-test-injected-by-reunlock"


@pytest.mark.asyncio
async def test_reunlock_flow_b_body_evidence(handed_off_vault):
    """Caller supplies fresh evidence; handler ignores the proof file."""
    from mindx_backend_service.bankon_vault.routes import reunlock, ReunlockRequest
    sig, vault_dir = handed_off_vault
    # Even with proof on disk, an explicit body should take precedence.
    req = ReunlockRequest(
        address=sig["address"],
        signature=sig["signature"],
        message=sig["message"],
    )
    res = await reunlock(req=req, wallet="0xadmin_test")
    assert res["status"] == "unlocked"
    assert res["source"] == "body_evidence"
    assert os.environ.get("OPENAI_API_KEY") == "sk-test-injected-by-reunlock"


@pytest.mark.asyncio
async def test_reunlock_refuses_without_sentinel(monkeypatch):
    """If the vault is not under HumanOverseer custody, the route refuses."""
    from fastapi import HTTPException
    from mindx_backend_service.bankon_vault import routes
    from mindx_backend_service.bankon_vault.vault import BankonVault
    from mindx_backend_service.bankon_vault.credential_provider import CredentialProvider

    tmp = Path(tempfile.mkdtemp(prefix="reunlock-no-sentinel-"))
    parent = tmp / "run"; parent.mkdir()
    vault_dir = parent / "vault_bankon"
    try:
        v = BankonVault(vault_dir=str(vault_dir))
        v.unlock_with_key_file()  # machine custody — no sentinel
        v.lock()
        monkeypatch.setattr(routes, "_vault", v)
        monkeypatch.setattr(routes, "_provider", CredentialProvider(v))

        from mindx_backend_service.bankon_vault.routes import reunlock
        with pytest.raises(HTTPException) as exc:
            await reunlock(req=None, wallet="0xadmin_test")
        assert exc.value.status_code == 409
        assert "not under HumanOverseer custody" in exc.value.detail
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


@pytest.mark.asyncio
async def test_reunlock_refuses_without_proof_or_body(monkeypatch, handed_off_vault):
    """Sentinel present + proof file deleted + no body → 404."""
    from fastapi import HTTPException
    from mindx_backend_service.bankon_vault.routes import reunlock
    sig, vault_dir = handed_off_vault
    # Delete the proof file to simulate a recovery scenario without backup.
    (vault_dir / ".overseer_proof.json").unlink()
    with pytest.raises(HTTPException) as exc:
        await reunlock(req=None, wallet="0xadmin_test")
    assert exc.value.status_code == 404
    assert "missing" in exc.value.detail.lower()
