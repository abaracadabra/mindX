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
    # Reset internal caches.
    mod._pricing_cache = {}
    mod._pricing_loaded_at = 0.0
    mod._settlement_cache = {}
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
    body = r.json()["detail"]
    assert body["code"] == "x402_payment_required"
    assert body["endpoint"] == "/coordinator/query"
    rails = body["paymentRequirements"]
    networks = {r["network"] for r in rails}
    # Two rails configured in the fixture (base, algorand-mainnet).
    assert "base" in networks
    assert "algorand-mainnet" in networks
    # Pricing for /coordinator/query is 2000 microUSDC.
    assert all(r["maxAmountRequired"] == "2000" for r in rails)
    # Resource path round-trips.
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
