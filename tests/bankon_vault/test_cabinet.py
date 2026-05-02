"""Integration tests for the Cabinet provisioning + signing-oracle endpoints.

Spins up a FastAPI app with just our routers + a tmp BankonVault, exercises:
  - auth → JWT round-trip
  - provision creates 16 vault entries (8 pk + 8 addr)
  - public read strips vault_pk_id
  - sign-as-agent returns a signature that verifies to the agent's public address
  - re-provision rejected (idempotency)
  - sign rejected when message_sha256 doesn't match the request body (tamper guard)
  - clear refuses without DESTROY-{COMPANY}-CABINET literal
"""
from __future__ import annotations

import hashlib
import os
import secrets
import tempfile
from pathlib import Path

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Isolated tmp vault + registry + nonces + synthetic shadow-overlord."""
    overlord = Account.create()
    monkeypatch.setenv("SHADOW_OVERLORD_ADDRESS", overlord.address)
    monkeypatch.setenv("SHADOW_JWT_SECRET", secrets.token_hex(32))
    monkeypatch.setenv("MINDX_PRODUCTION_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.setenv("MINDX_AGENT_MAP", str(tmp_path / "agent_map.json"))
    monkeypatch.setenv("SHADOW_NONCES_PATH", str(tmp_path / "nonces.json"))

    from mindx_backend_service.bankon_vault.vault import BankonVault
    vault = BankonVault(vault_dir=str(tmp_path / "vault"))
    vault.unlock_with_key_file()

    # Inject the tmp vault into the routes module (lazy lookup via _routes._vault)
    from mindx_backend_service.bankon_vault import routes as _r
    _r._vault = vault

    # Reset module-level singletons so the fixture is clean per test
    from mindx_backend_service.bankon_vault import shadow_overlord as so, admin_routes as ar
    so._store = None
    so.reset_store_for_tests(Path(os.environ["SHADOW_NONCES_PATH"]))
    ar._provisioner = None  # forces _get_provisioner() to rebuild against tmp vault

    from mindx_backend_service.bankon_vault.admin_routes import admin_router, public_cabinet_router
    from mindx_backend_service.bankon_vault.sign_routes import sign_router
    app = FastAPI()
    app.include_router(admin_router)
    app.include_router(public_cabinet_router)
    app.include_router(sign_router)
    client = TestClient(app)

    return {"client": client, "overlord": overlord, "vault": vault, "tmp": tmp_path}


def _sign(acct, msg: str) -> str:
    return acct.sign_message(encode_defunct(text=msg)).signature.hex()


def _auth(env) -> str:
    """Helper: full auth flow → returns JWT."""
    client, overlord = env["client"], env["overlord"]
    ch = client.post("/admin/shadow/challenge", json={"scope": "auth"}).json()
    sig = _sign(overlord, ch["message"])
    return client.post("/admin/shadow/verify", json={"nonce": ch["nonce"], "signature": sig}).json()["jwt"]


def _provision(env, company: str = "PYTHAI"):
    client, overlord = env["client"], env["overlord"]
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    ch = client.post("/admin/shadow/challenge", json={
        "scope": "cabinet.provision", "params": {"company": company},
    }).json()
    sig = _sign(overlord, ch["message"])
    return client.post(
        f"/admin/cabinet/{company}/provision",
        headers=H,
        json={"nonce": ch["nonce"], "signature": sig},
    )


# ─── tests ────────────────────────────────────────────────────────


def test_auth_round_trip_issues_jwt(env):
    jwt = _auth(env)
    assert isinstance(jwt, str) and jwt.count(".") == 2  # JWT has 3 dot-separated segments


def test_provision_creates_8_wallets_and_registry_block(env):
    r = _provision(env)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "provisioned"
    assert body["company"] == "PYTHAI"
    assert body["ceo"].startswith("0x")
    assert len(body["soldiers"]) == 7
    # Vault entries: 8 pk + 8 addr = 16, plus whatever else was there.
    info = env["vault"].info()
    assert info["entries"] >= 16


def test_public_read_strips_vault_pk_id(env):
    _provision(env)
    public = env["client"].get("/cabinet/PYTHAI").json()
    assert "vault_pk_id" not in public["ceo"]
    for body in public["soldiers"].values():
        assert "vault_pk_id" not in body


def test_sign_as_agent_returns_valid_sig_no_pk_leak(env):
    _provision(env)
    public = env["client"].get("/cabinet/PYTHAI").json()
    cfo_addr = public["soldiers"]["cfo_finance"]["address"]
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    msg = "PYTHAI CFO endorses 2026-Q2 budget"
    msg_sha = "0x" + hashlib.sha256(msg.encode()).hexdigest()
    agent_id = "company:PYTHAI:cabinet:cfo_finance"

    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "vault.sign", "params": {"agent_id": agent_id, "message_sha256": msg_sha},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        f"/vault/sign/{agent_id}", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "message": msg},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "private_key" not in r.text and "private_key_hex" not in r.text  # KEY MUST NOT LEAK
    # Recovered signer == cfo public address — proves the vault signed with cfo's pk.
    recovered = Account.recover_message(encode_defunct(text=msg), signature=body["signature"])
    assert recovered.lower() == cfo_addr.lower()


def test_sign_message_tamper_rejected(env):
    """If the request's message doesn't hash to the value bound in the challenge, reject."""
    _provision(env)
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    real_msg = "real message"
    real_hash = "0x" + hashlib.sha256(real_msg.encode()).hexdigest()
    agent_id = "company:PYTHAI:cabinet:cfo_finance"

    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "vault.sign", "params": {"agent_id": agent_id, "message_sha256": real_hash},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    # Submit a *different* message — server recomputes sha256, sees mismatch.
    r = env["client"].post(
        f"/vault/sign/{agent_id}", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "message": "evil different message"},
    )
    assert r.status_code == 400, r.text


def test_provision_idempotent(env):
    r1 = _provision(env)
    assert r1.status_code == 200
    r2 = _provision(env)
    assert r2.status_code == 409, r2.text


def test_clear_requires_destroy_string(env):
    _provision(env)
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "cabinet.clear", "params": {"company": "PYTHAI"},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        "/admin/cabinet/PYTHAI/clear", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "confirm": "wrong"},
    )
    assert r.status_code == 400, r.text


def test_clear_with_correct_confirm_succeeds(env):
    _provision(env)
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "cabinet.clear", "params": {"company": "PYTHAI"},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        "/admin/cabinet/PYTHAI/clear", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "confirm": "DESTROY-PYTHAI-CABINET"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cleared"
    # Re-read should now 404
    assert env["client"].get("/cabinet/PYTHAI").status_code == 404


def test_no_jwt_blocked(env):
    """Endpoints requiring shadow JWT must reject missing bearer."""
    r = env["client"].get("/admin/cabinet/PYTHAI/preflight")
    assert r.status_code == 401


def test_addresses_match_pk_derivation(env):
    """Each public address must equal Account.from_key(pk).address."""
    _provision(env)
    public = env["client"].get("/cabinet/PYTHAI").json()
    vault = env["vault"]
    vault.unlock_with_key_file()
    try:
        for role, body in [("ceo", public["ceo"]), *public["soldiers"].items()]:
            pk = vault.retrieve(f"company:PYTHAI:cabinet:{role}:pk")
            addr = Account.from_key(pk).address
            assert addr.lower() == body["address"].lower(), f"role {role} mismatch"
    finally:
        vault.lock()


def test_release_key_returns_pk_with_correct_confirm(env):
    """The emergency release-key path returns plaintext pk only with the literal
    RELEASE-PRIVATE-KEY confirm + a fresh shadow signature on a release.key
    scope challenge bound to the agent_id."""
    _provision(env)
    public = env["client"].get("/cabinet/PYTHAI").json()
    cfo_addr = public["soldiers"]["cfo_finance"]["address"]
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    agent_id = "company:PYTHAI:cabinet:cfo_finance"

    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "release.key", "params": {"agent_id": agent_id},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        f"/admin/shadow/release-key/{agent_id}", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "confirm": "RELEASE-PRIVATE-KEY"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    pk_hex = body["private_key_hex"]
    # Accept both with and without 0x prefix (eth_account.Account.from_key handles either)
    pk_normalized = pk_hex if pk_hex.startswith("0x") else "0x" + pk_hex
    assert len(pk_normalized) == 66  # 0x + 32 bytes hex
    # The released key, derived back to its address, MUST match the CFO's published address.
    derived = Account.from_key(pk_normalized).address
    assert derived.lower() == cfo_addr.lower()


def test_release_key_rejects_wrong_confirm(env):
    """Without the literal 'RELEASE-PRIVATE-KEY' string, the release path 400s."""
    _provision(env)
    jwt = _auth(env)
    H = {"Authorization": f"Bearer {jwt}"}
    agent_id = "company:PYTHAI:cabinet:cfo_finance"

    ch = env["client"].post("/admin/shadow/challenge", json={
        "scope": "release.key", "params": {"agent_id": agent_id},
    }).json()
    sig = _sign(env["overlord"], ch["message"])
    r = env["client"].post(
        f"/admin/shadow/release-key/{agent_id}", headers=H,
        json={"nonce": ch["nonce"], "signature": sig, "confirm": "wrong-string"},
    )
    assert r.status_code == 400, r.text
    assert "RELEASE-PRIVATE-KEY" in r.text


def test_public_read_404_for_unprovisioned_company(env):
    """GET /cabinet/<company> must return 404 when no cabinet exists for that name."""
    r = env["client"].get("/cabinet/NEVER_PROVISIONED_CO")
    assert r.status_code == 404, r.text


def test_two_companies_coexist_with_isolated_namespaces(env):
    """Provision PYTHAI and ALICE; vault entries and registry blocks must not collide."""
    # First company
    r1 = _provision(env, "PYTHAI")
    assert r1.status_code == 200
    pythai_ceo = r1.json()["ceo"]

    # Second company — gets its own JWT + challenges
    r2 = _provision(env, "ALICE")
    assert r2.status_code == 200
    alice_ceo = r2.json()["ceo"]

    # CEOs must be distinct (probability of collision ~ 1/2^160)
    assert pythai_ceo != alice_ceo

    # Both public reads succeed
    pythai_pub = env["client"].get("/cabinet/PYTHAI").json()
    alice_pub = env["client"].get("/cabinet/ALICE").json()
    assert pythai_pub["ceo"]["address"] == pythai_ceo
    assert alice_pub["ceo"]["address"] == alice_ceo

    # Vault entries: 16 per company × 2 companies = ≥32 cabinet entries
    info = env["vault"].info()
    assert info["entries"] >= 32

    # Each company's CEO entity_id is namespaced
    assert pythai_pub["ceo"]["entity_id"] == "company:PYTHAI:cabinet:ceo"
    assert alice_pub["ceo"]["entity_id"] == "company:ALICE:cabinet:ceo"


def test_agent_map_soldiers_backfilled_after_provision(env):
    """Provisioning PYTHAI must backfill the 7 soldier eth_address fields in
    daio/agents/agent_map.json (if the file exists on the test fixture path)."""
    import json as _json
    from pathlib import Path

    # Seed an agent_map.json with the 7 soldier slots having null addresses
    agent_map_path = Path(env["tmp"] / "agent_map.json")
    seed = {
        "version": "test",
        "soldiers": {
            role: {"role": role, "eth_address": None, "weight": 1.0}
            for role in [
                "coo_operations", "cfo_finance", "cto_technology",
                "ciso_security", "clo_legal", "cpo_product", "cro_risk",
            ]
        },
    }
    agent_map_path.write_text(_json.dumps(seed), encoding="utf-8")

    _provision(env, "PYTHAI")
    public = env["client"].get("/cabinet/PYTHAI").json()

    after = _json.loads(agent_map_path.read_text(encoding="utf-8"))
    for role in ["coo_operations", "cfo_finance", "cto_technology",
                 "ciso_security", "clo_legal", "cpo_product", "cro_risk"]:
        addr_in_map = after["soldiers"][role]["eth_address"]
        addr_in_registry = public["soldiers"][role]["address"]
        assert addr_in_map is not None
        assert addr_in_map.lower() == addr_in_registry.lower(), f"role {role}: map {addr_in_map} ≠ registry {addr_in_registry}"
