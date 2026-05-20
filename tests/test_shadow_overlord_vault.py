# SPDX-License-Identifier: Apache-2.0
"""Smoke test — shadow-overlord credentials flow vault → os.environ at startup.

Confirms the two new ``PROVIDER_ENV_MAP`` rows (``shadow_overlord_address``,
``shadow_jwt_secret``) are actually loaded by ``CredentialProvider.load_from_vault()``
and that the shadow-overlord plumbing (``_jwt_secret`` / ``issue_challenge``)
works against them.
"""
from __future__ import annotations

import os

import pytest

from mindx_backend_service.bankon_vault.credential_provider import (
    PROVIDER_ENV_MAP,
    CredentialProvider,
)
from mindx_backend_service.bankon_vault.vault import BankonVault


_ADDR = "0x" + "a" * 40   # any valid-looking 0x address
_SECRET = "x" * 64        # ≥32 chars to pass shadow_overlord._jwt_secret() guard


@pytest.fixture
def vault_with_shadow_creds(tmp_path, monkeypatch):
    """Tmp-path BankonVault seeded with shadow_overlord_address + shadow_jwt_secret."""
    v = BankonVault(vault_dir=str(tmp_path / "vault_bankon"))
    v.unlock_with_key_file()
    v.store("shadow_overlord_address", _ADDR, context="provider")
    v.store("shadow_jwt_secret", _SECRET, context="provider")
    v.store("mindx_admin_addresses", _ADDR, context="provider")
    v.lock()

    # Isolate env so we measure only what the loader sets.
    monkeypatch.delenv("SHADOW_OVERLORD_ADDRESS", raising=False)
    monkeypatch.delenv("SHADOW_JWT_SECRET", raising=False)
    monkeypatch.delenv("MINDX_SECURITY_ADMIN_ADDRESSES", raising=False)
    yield v


def test_provider_env_map_contains_shadow_overlord_rows():
    """The new PROVIDER_ENV_MAP rows exist (cheap regression-against-typo guard)."""
    assert PROVIDER_ENV_MAP["shadow_overlord_address"] == "SHADOW_OVERLORD_ADDRESS"
    assert PROVIDER_ENV_MAP["shadow_jwt_secret"] == "SHADOW_JWT_SECRET"


def test_load_from_vault_populates_shadow_env(vault_with_shadow_creds):
    """CredentialProvider.load_from_vault() decrypts and writes to os.environ."""
    fresh = BankonVault(vault_dir=vault_with_shadow_creds.vault_dir)
    cp = CredentialProvider(fresh)
    results = cp.load_from_vault()

    assert results["shadow_overlord_address"] is True
    assert results["shadow_jwt_secret"] is True
    assert results["mindx_admin_addresses"] is True

    assert os.environ.get("SHADOW_OVERLORD_ADDRESS") == _ADDR
    assert os.environ.get("SHADOW_JWT_SECRET") == _SECRET
    assert os.environ.get("MINDX_SECURITY_ADMIN_ADDRESSES") == _ADDR

    # Vault re-locked after load (no key resident).
    assert not fresh.is_unlocked()


def test_shadow_overlord_helpers_pick_up_loaded_env(vault_with_shadow_creds, monkeypatch):
    """With env populated from the vault, the shadow_overlord helpers work."""
    fresh = BankonVault(vault_dir=vault_with_shadow_creds.vault_dir)
    CredentialProvider(fresh).load_from_vault()

    from mindx_backend_service.bankon_vault import shadow_overlord as so

    # _jwt_secret() must not raise (would 503 if missing / too short)
    assert so._jwt_secret() == _SECRET

    # Isolate the nonce store so we don't write to the repo's file.
    so.reset_store_for_tests(vault_with_shadow_creds.vault_dir.parent / "nonces.json")
    ch = so.issue_challenge(so.SCOPE_AUTH)
    assert "nonce" in ch
    assert ch["message"].startswith("MINDX-SHADOW-OVERLORD scope=auth\n")
    assert ch["nonce"] in ch["message"]
