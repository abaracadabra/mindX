"""Acceptance tests for the x402 paywall middleware (Phase C of the
tighten-up plan).

Contract documented in docs/services/x402_as_a_service.md.

These tests run against a miniature FastAPI app that imports the
``x402_required`` factory directly. The vault dependency is monkey-patched
so the tests don't need a running vault.
"""
from __future__ import annotations

import base64
import importlib
import json
import os
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from starlette.testclient import TestClient


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _enable_x402_test_mode(monkeypatch):
    monkeypatch.setenv("MINDX_X402_TEST_MODE", "1")


@pytest.fixture
def x402(tmp_path, monkeypatch):
    """Import the middleware module fresh, redirecting all on-disk state
    into a tmp_path. Pricing config is materialized fresh so tests don't
    inherit production values.
    """
    cfg_dir = tmp_path / "data" / "config"
    cfg_dir.mkdir(parents=True)
    pricing_path = cfg_dir / "x402_pricing.json"
    pricing_path.write_text(json.dumps({
        "free_quota": {"calls_per_24h": 10, "anonymous_calls_per_24h": 0},
        "endpoints": {
            "/coordinator/query": {"max_amount_microusd": 2000},
            "/boardroom/convene": {"max_amount_microusd": 5000},
            "/coordinator/no_rails": {"max_amount_microusd": 2000},
        },
        "rails": {
            "base": {
                "scheme": "exact", "network": "base",
                "asset": "0xUSDC", "payTo": "0xMINDX_PAYEE_ON_BASE",
                "extra": {"chainId": 8453, "decimals": 6, "facilitator": "https://test/4022"},
            },
            "algorand-mainnet": {
                "scheme": "exact", "network": "algorand-mainnet",
                "asset": "31566704", "payTo": "ALGOPAYEE",
                "extra": {"assetId": 31566704, "decimals": 6, "facilitator": "https://test/4022"},
            },
        },
        "facilitator": {"url": "https://test/4022", "verify_endpoint": "/verify"},
        "idempotency": {"settlement_cache_ttl_seconds": 60},
    }), encoding="utf-8")

    gov_dir = tmp_path / "data" / "governance"
    gov_dir.mkdir(parents=True)

    # Force a fresh import so the module-level paths re-evaluate to tmp_path.
    import sys
    sys.modules.pop("mindx_backend_service.x402_middleware", None)
    mod = importlib.import_module("mindx_backend_service.x402_middleware")
    # Redirect on-disk paths into tmp_path.
    monkeypatch.setattr(mod, "_PRICING_PATH", pricing_path)
    monkeypatch.setattr(mod, "_QUOTA_LEDGER_PATH", gov_dir / "free_quota_ledger.json")
    # Redirect the v2 persistent ledger + SIWx sessions into tmp_path so tests
    # never touch real state and replay guards start empty per test.
    monkeypatch.setattr(mod, "_SETTLEMENT_LEDGER_PATH", gov_dir / "x402_settlement_ledger.json")
    monkeypatch.setattr(mod, "_SIWX_SESSIONS_PATH", gov_dir / "x402_siwx_sessions.json")
    # Reset internal caches.
    mod._pricing_cache = {}
    mod._pricing_loaded_at = 0.0
    mod._idem_cache = {}
    mod._seen_keys = None
    return mod


@pytest.fixture
def make_app(x402):
    def _build():
        app = FastAPI()

        @app.post("/coordinator/query", dependencies=[Depends(x402.x402_required("/coordinator/query"))])
        async def coord_query():
            return {"ok": True}

        @app.post("/boardroom/convene", dependencies=[Depends(x402.x402_required("/boardroom/convene"))])
        async def boardroom_convene():
            return {"ok": True}

        @app.post("/coordinator/no_rails", dependencies=[Depends(x402.x402_required("/coordinator/no_rails"))])
        async def no_rails():
            return {"ok": True}

        return app
    return _build


@pytest.fixture
def client(make_app):
    return TestClient(make_app())


@pytest.fixture
def stub_session(x402, monkeypatch):
    """Return a helper that registers a wallet for X-Session-Token=<wallet>."""
    def _stub(_request):
        token = _request.headers.get("X-Session-Token")
        if not token:
            return None
        return token.lower()  # treat the token itself as the wallet for tests

    monkeypatch.setattr(x402, "_wallet_from_request", _stub)
    return _stub


# ---------------------------------------------------------------------
# 1. Anonymous caller → immediate 402 with triple-rail envelope
# ---------------------------------------------------------------------


def test_anonymous_call_returns_402_with_envelope(client, x402):
    r = client.post("/coordinator/query", json={})
    assert r.status_code == 402
    # v2: the challenge also carries the base64 PAYMENT-REQUIRED response header.
    assert r.headers.get("PAYMENT-REQUIRED")
    body = r.json()["detail"]
    assert body["code"] == "x402_payment_required"
    assert body["endpoint"] == "/coordinator/query"
    assert body["x402Version"] == 2
    # Both the v2 (accepts) and v1 (paymentRequirements) keys are present.
    rails = body["paymentRequirements"]
    assert body["accepts"] == rails
    networks = {r["network"] for r in rails}
    # v2: networks are advertised in CAIP-2 form (base→eip155:8453, algorand→algorand:…).
    assert "eip155:8453" in networks
    assert any(n.startswith("algorand:") for n in networks)
    # Pricing for /coordinator/query is 2000 microUSDC (both v1 + v2 amount fields).
    assert all(r["maxAmountRequired"] == "2000" and r["amount"] == "2000" for r in rails)
    assert all(r["resource"] == "/coordinator/query" for r in rails)


def test_boardroom_convene_priced_5000(client, x402):
    r = client.post("/boardroom/convene", json={})
    assert r.status_code == 402
    body = r.json()["detail"]
    assert all(rail["maxAmountRequired"] == "5000" for rail in body["paymentRequirements"])


def test_no_rails_configured_returns_503(client, x402, monkeypatch):
    # Strip all payTo values so no rail is settling-eligible.
    cfg = x402._load_pricing(force=True)
    for rail in cfg["rails"].values():
        rail["payTo"] = ""
    monkeypatch.setattr(x402, "_load_pricing", lambda force=False: cfg)
    r = client.post("/coordinator/no_rails", json={})
    assert r.status_code == 503
    assert r.json()["detail"]["code"] == "x402_no_rails_configured"


# ---------------------------------------------------------------------
# 2. Valid X-PAYMENT settles the call (test mode stub)
# ---------------------------------------------------------------------


def _build_payment_header(network: str = "base") -> str:
    envelope = {
        "x402Version": 1,
        "scheme": "exact",
        "network": network,
        "payload": {"signature": "0xstub", "authorization": {"value": "2000"}},
    }
    return base64.b64encode(json.dumps(envelope).encode("utf-8")).decode("utf-8")


def test_valid_x_payment_lets_request_through(client, x402, stub_session):
    # An anonymous caller paying via X-PAYMENT bypasses the 0-quota.
    r = client.post(
        "/coordinator/query",
        json={},
        headers={"X-PAYMENT": _build_payment_header("base")},
    )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_malformed_x_payment_returns_402(client, x402):
    r = client.post(
        "/coordinator/query",
        json={},
        headers={"X-PAYMENT": "not-valid-base64@@@"},
    )
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "x402_malformed_payment"


def test_x_payment_without_scheme_returns_402(client, x402):
    envelope = {"network": "base", "payload": {}}  # missing scheme
    hdr = base64.b64encode(json.dumps(envelope).encode()).decode()
    r = client.post("/coordinator/query", json={}, headers={"X-PAYMENT": hdr})
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "x402_malformed_payment"


# ---------------------------------------------------------------------
# 3. Idempotency cache: same X-PAYMENT twice within window → both accepted
# ---------------------------------------------------------------------


def test_idempotent_payment_within_window(client, x402, stub_session):
    hdr = _build_payment_header()
    r1 = client.post("/coordinator/query", json={}, headers={"X-PAYMENT": hdr})
    r2 = client.post("/coordinator/query", json={}, headers={"X-PAYMENT": hdr})
    assert r1.status_code == 200
    assert r2.status_code == 200


# ---------------------------------------------------------------------
# 4. v2 — PAYMENT-SIGNATURE header + PAYMENT-RESPONSE echo
# ---------------------------------------------------------------------


def _build_payment_header_v2(nonce: str, network: str = "base") -> str:
    envelope = {
        "x402Version": 2, "scheme": "exact", "network": network,
        "payload": {"signature": "0xstub", "authorization": {"value": "2000", "from": "0xP", "to": "0xR", "nonce": nonce}},
    }
    return base64.b64encode(json.dumps(envelope).encode("utf-8")).decode("utf-8")


def test_v2_payment_signature_header_accepted_and_response_echoed(client, x402, stub_session):
    r = client.post(
        "/coordinator/query", json={},
        headers={"PAYMENT-SIGNATURE": _build_payment_header_v2("0xnonce-aa")},
    )
    assert r.status_code == 200
    # success echoes the settlement in both v2 + v1 headers
    assert r.headers.get("PAYMENT-RESPONSE")
    assert r.headers.get("X-PAYMENT-RESPONSE")


# ---------------------------------------------------------------------
# 5. permanent replay guard — a settled nonce is rejected forever (409)
# ---------------------------------------------------------------------


def test_replay_of_settled_nonce_is_rejected_permanently(client, x402, stub_session):
    hdr = _build_payment_header_v2("0xnonce-replay-1")
    r1 = client.post("/coordinator/query", json={}, headers={"PAYMENT-SIGNATURE": hdr})
    assert r1.status_code == 200
    # Expire the short idempotency window so the only thing that can stop a
    # replay is the permanent on-disk ledger guard.
    x402._idem_cache.clear()
    r2 = client.post("/coordinator/query", json={}, headers={"PAYMENT-SIGNATURE": hdr})
    assert r2.status_code == 409
    assert r2.json()["detail"]["code"] == "x402_replay"


# ---------------------------------------------------------------------
# 6. SIWx session — a valid session skips re-payment
# ---------------------------------------------------------------------


def test_siwx_session_skips_payment(client, x402, stub_session):
    import json as _json
    import time as _time
    x402._SIWX_SESSIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    x402._SIWX_SESSIONS_PATH.write_text(_json.dumps({
        "sess-token-1": {"account": "eip155:8453:0xP", "issued": _time.time(), "expires": _time.time() + 3600}
    }))
    r = client.post("/coordinator/query", json={}, headers={"X-SIWX-SESSION": "sess-token-1"})
    assert r.status_code == 200
    assert r.json() == {"ok": True}
