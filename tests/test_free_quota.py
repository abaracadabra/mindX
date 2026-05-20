"""Acceptance tests for the x402 free-quota path.

Contract: per-wallet free-quota allowance (10 calls per 24h rolling window
for logged-in wallets, 0 for anonymous). After exceeding the quota, the
middleware falls through to the standard 402 path.

Documented in docs/services/x402_as_a_service.md §6 +
docs/services/mindx_as_a_service.md §4.2.
"""
from __future__ import annotations

import importlib
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi import Depends, FastAPI
from starlette.testclient import TestClient


@pytest.fixture(autouse=True)
def _enable_x402_test_mode(monkeypatch):
    monkeypatch.setenv("MINDX_X402_TEST_MODE", "1")


@pytest.fixture
def x402(tmp_path, monkeypatch):
    cfg_dir = tmp_path / "data" / "config"
    cfg_dir.mkdir(parents=True)
    pricing_path = cfg_dir / "x402_pricing.json"
    pricing_path.write_text(json.dumps({
        "free_quota": {"calls_per_24h": 3, "anonymous_calls_per_24h": 0},
        "endpoints": {"/coordinator/query": {"max_amount_microusd": 2000}},
        "rails": {
            "base": {
                "scheme": "exact", "network": "base",
                "asset": "0xUSDC", "payTo": "0xMINDX_PAYEE",
                "extra": {"chainId": 8453, "decimals": 6, "facilitator": "https://test/4022"},
            },
        },
        "facilitator": {"url": "https://test/4022"},
        "idempotency": {"settlement_cache_ttl_seconds": 60},
    }), encoding="utf-8")
    gov_dir = tmp_path / "data" / "governance"
    gov_dir.mkdir(parents=True)

    sys.modules.pop("mindx_backend_service.x402_middleware", None)
    mod = importlib.import_module("mindx_backend_service.x402_middleware")
    monkeypatch.setattr(mod, "_PRICING_PATH", pricing_path)
    monkeypatch.setattr(mod, "_QUOTA_LEDGER_PATH", gov_dir / "free_quota_ledger.json")
    mod._pricing_cache = {}
    mod._pricing_loaded_at = 0.0
    mod._settlement_cache = {}
    return mod


@pytest.fixture
def stubbed_session(x402, monkeypatch):
    """Wallet = X-Session-Token (lowercased) for the duration of the test."""
    def _stub(request):
        token = request.headers.get("X-Session-Token")
        return token.lower() if token else None
    monkeypatch.setattr(x402, "_wallet_from_request", _stub)


@pytest.fixture
def client(x402, stubbed_session):
    app = FastAPI()

    @app.post("/coordinator/query", dependencies=[Depends(x402.x402_required("/coordinator/query"))])
    async def coord_query():
        return {"ok": True}

    return TestClient(app)


# ---------------------------------------------------------------------
# 1. Logged-in wallet gets N free calls, then 402
# ---------------------------------------------------------------------


def test_logged_in_wallet_gets_three_free_calls_then_402(client):
    headers = {"X-Session-Token": "0xWalletA"}
    for i in range(3):
        r = client.post("/coordinator/query", json={}, headers=headers)
        assert r.status_code == 200, f"call {i+1} should be free but got {r.status_code}"
    # Fourth call exceeds the quota.
    r = client.post("/coordinator/query", json={}, headers=headers)
    assert r.status_code == 402
    assert r.json()["detail"]["code"] == "x402_payment_required"


def test_anonymous_wallet_gets_zero_free_calls(client):
    # No X-Session-Token → anonymous → quota 0 → first call already 402.
    r = client.post("/coordinator/query", json={})
    assert r.status_code == 402


def test_separate_wallets_have_independent_quotas(client):
    a = {"X-Session-Token": "0xWalletA"}
    b = {"X-Session-Token": "0xWalletB"}
    # Burn A's quota.
    for _ in range(3):
        assert client.post("/coordinator/query", json={}, headers=a).status_code == 200
    # A is now over.
    assert client.post("/coordinator/query", json={}, headers=a).status_code == 402
    # B is still fresh.
    assert client.post("/coordinator/query", json={}, headers=b).status_code == 200


# ---------------------------------------------------------------------
# 2. Ledger persistence: re-reading the ledger across module reloads keeps
#    the count.
# ---------------------------------------------------------------------


def test_quota_persists_across_lookups(client, x402):
    headers = {"X-Session-Token": "0xWalletC"}
    for _ in range(3):
        client.post("/coordinator/query", json={}, headers=headers)
    used, limit = x402._quota_status("0xwalletc")
    assert used == 3
    assert limit == 3


def test_quota_prunes_entries_older_than_24h(x402, monkeypatch):
    """Stale timestamps (>24h old) must not count against the quota."""
    ledger_path = x402._QUOTA_LEDGER_PATH
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    old_ts = time.time() - 25 * 3600  # 25 hours ago
    fresh_ts = time.time() - 60        # 1 minute ago
    ledger_path.write_text(json.dumps({
        "0xwalletd": [old_ts, old_ts, fresh_ts]
    }), encoding="utf-8")
    used, limit = x402._quota_status("0xWalletD")
    assert used == 1  # only the fresh timestamp survives the prune
    assert limit == 3


# ---------------------------------------------------------------------
# 3. Out-of-quota caller can still pay via X-PAYMENT
# ---------------------------------------------------------------------


def test_out_of_quota_caller_can_settle_via_x_payment(client):
    import base64, json as _j
    headers = {"X-Session-Token": "0xWalletE"}
    # Burn quota.
    for _ in range(3):
        client.post("/coordinator/query", json={}, headers=headers)
    # Now 402-only without payment.
    assert client.post("/coordinator/query", json={}, headers=headers).status_code == 402
    # Same wallet with X-PAYMENT settles.
    envelope = {
        "x402Version": 1, "scheme": "exact", "network": "base",
        "payload": {"signature": "0xstub", "authorization": {"value": "2000"}},
    }
    hdr = base64.b64encode(_j.dumps(envelope).encode()).decode()
    r = client.post(
        "/coordinator/query",
        json={},
        headers={**headers, "X-PAYMENT": hdr},
    )
    assert r.status_code == 200
