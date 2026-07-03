"""Handler-level tests for the gated reference-corpus surfaces.

/reference/ is a PUBLIC prefix in both arrival-gate modes (the localStorage
session token cannot ride a browser navigation), so every data route gates
itself via ``_require_reference_access``. These tests exercise that handler
gate directly — the middleware pass-through is covered in
tests/test_arrival_gate.py.
"""
from __future__ import annotations

import importlib
import os
from types import SimpleNamespace

import pytest
from fastapi import HTTPException


@pytest.fixture(scope="module")
def ms():
    os.environ["MINDX_HARD_GATE_ENABLED"] = "1"
    return importlib.import_module("mindx_backend_service.main_service")


def make_request(session_token: str = "", bearer: str = "", query_token: str = ""):
    headers = {}
    if session_token:
        headers["X-Session-Token"] = session_token
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    query = {"session_token": query_token} if query_token else {}
    return SimpleNamespace(headers=headers, query_params=query)


class StubVault:
    """get_user_session returns a session only for the token 'valid'."""
    def get_user_session(self, token):
        if token == "valid":
            return {"wallet_address": "0xtest", "session_id": token}
        return None


@pytest.fixture
def stub_vault(ms, monkeypatch):
    monkeypatch.setattr(ms, "get_vault_manager", lambda: StubVault())


# ----------------------------------------------------------------------
# _require_reference_access
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_credentials_401(ms, stub_vault):
    with pytest.raises(HTTPException) as exc:
        await ms._require_reference_access(make_request())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_invalid_session_401(ms, stub_vault):
    with pytest.raises(HTTPException) as exc:
        await ms._require_reference_access(make_request(session_token="bogus"))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_valid_session_header_passes(ms, stub_vault):
    assert await ms._require_reference_access(make_request(session_token="valid")) == "0xtest"


@pytest.mark.asyncio
async def test_valid_session_query_param_passes(ms, stub_vault):
    """?session_token= lets reference.html emit browser-navigable file links."""
    assert await ms._require_reference_access(make_request(query_token="valid")) == "0xtest"


@pytest.mark.asyncio
async def test_api_key_passes(ms, stub_vault, monkeypatch):
    monkeypatch.setenv("MINDX_SECURITY_API_KEYS", "k1,k2")
    assert await ms._require_reference_access(make_request(bearer="k2")) == "api_key"


@pytest.mark.asyncio
async def test_wrong_api_key_401(ms, stub_vault, monkeypatch):
    monkeypatch.setenv("MINDX_SECURITY_API_KEYS", "k1")
    with pytest.raises(HTTPException):
        await ms._require_reference_access(make_request(bearer="nope"))


@pytest.mark.asyncio
async def test_reference_access_ok_twin(ms, stub_vault):
    assert await ms._reference_access_ok(make_request(session_token="valid")) is True
    assert await ms._reference_access_ok(make_request()) is False


# ----------------------------------------------------------------------
# /reference/file — traversal + space-named files
# ----------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("relpath", [
    "../../etc/passwd",
    "../CLAUDE.md",
    "operations/../../.env",
    ".hidden/secret.md",
    "operations/__pycache__/x.pyc",
    "no/such/file.md",
])
async def test_reference_file_traversal_and_missing_404(ms, stub_vault, relpath):
    with pytest.raises(HTTPException) as exc:
        await ms.reference_file(relpath, make_request(session_token="valid"))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_reference_file_requires_auth(ms, stub_vault):
    with pytest.raises(HTTPException) as exc:
        await ms.reference_file("operations/HARD_GATE_RUNBOOK.md", make_request())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_reference_file_serves_private_md(ms, stub_vault):
    resp = await ms.reference_file("operations/HARD_GATE_RUNBOOK.md", make_request(session_token="valid"))
    assert resp.status_code == 200
    assert b"HARD_GATE_RUNBOOK" in resp.body or b"gate" in resp.body.lower()


@pytest.mark.asyncio
async def test_reference_file_serves_space_named_md(ms, stub_vault):
    """read_doc's sanitizer strips spaces — this route must not."""
    relpath = ("operations/x402 Protocol_ HTTP-Native Stablecoin Payments "
               "Engineering Reference.md")
    resp = await ms.reference_file(relpath, make_request(session_token="valid"))
    assert resp.status_code == 200


# ----------------------------------------------------------------------
# /doc/{name} — private subtrees gated, public docs untouched
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_doc_private_subtree_requires_auth(ms, stub_vault):
    with pytest.raises(HTTPException) as exc:
        await ms.read_doc("operations/HARD_GATE_RUNBOOK", make_request())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_doc_private_subtree_case_insensitive(ms, stub_vault):
    """The directory part must match on disk, but a case-variant FILE name
    resolves via read_doc's _ci_find — the gate keys off the resolved path."""
    with pytest.raises(HTTPException) as exc:
        await ms.read_doc("operations/hard_gate_runbook", make_request())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_doc_private_subtree_with_session(ms, stub_vault):
    resp = await ms.read_doc("operations/HARD_GATE_RUNBOOK", make_request(session_token="valid"))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_doc_public_doc_stays_public(ms, stub_vault):
    resp = await ms.read_doc("TECHNICAL", make_request())
    assert resp.status_code == 200


# ----------------------------------------------------------------------
# /reference/catalog
# ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_catalog_requires_auth(ms, stub_vault):
    with pytest.raises(HTTPException) as exc:
        await ms.reference_catalog(make_request())
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_catalog_groups_and_privacy_flags(ms, stub_vault):
    data = await ms.reference_catalog(make_request(session_token="valid"))
    assert data["total"] > 0
    assert "operations" in data["groups"]
    assert "blockchain" in data["groups"]
    ops = data["groups"]["operations"]
    assert all(item["private"] for item in ops)
    assert any("dev/" in item["relpath"] for item in ops)
    # publications group mixes public essays with the private pdf/ subtree
    pubs = data["groups"].get("publications", [])
    assert any(i["private"] for i in pubs) and any(not i["private"] for i in pubs)
    # every href routes through the gated file server
    assert all(i["href"].startswith("/reference/file/") for g in data["groups"].values() for i in g)
