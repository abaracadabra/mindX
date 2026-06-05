# Copyright 2026 BANKON. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Offline tests for the x402 rails HTTP service.

The app is driven through ``httpx.ASGITransport`` (async-only) wrapped in a sync
helper so the tests stay synchronous — no socket, no network. The rails service
is built with the real signature-based signer on a throwaway key, so an issued
credential's signature is recovered to prove the HTTP route mints a genuine
authorization, and the spend gate is exercised both ways.
"""

from __future__ import annotations

import asyncio
import base64
import json

import httpx
from eth_account import Account
from eth_account.messages import encode_typed_data

from cmc_client import BASE_USDC_ASSET, BASE_USDC_NETWORK
from x402_rails import X402RailsService
from x402_rails_service import build_app
from x402_signer import BASE_USDC_DOMAIN, x402_wallet_signer

TEST_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
TEST_ADDRESS = Account.from_key(TEST_KEY).address
RECIPIENT = "0x000000000000000000000000000000000000dEaD"
TOKEN = "test-admin-token"


def _challenge(amount: int = 10000) -> dict:
    return {
        "accepts": [
            {
                "scheme": "exact",
                "network": BASE_USDC_NETWORK,
                "asset": BASE_USDC_ASSET,
                "amount": amount,
                "payTo": RECIPIENT,
            }
        ]
    }


def _app(spend_guard=None):
    """An app whose Base rail signs with the throwaway test key."""
    svc = X402RailsService(max_amount_usdc=0.05)
    signer = x402_wallet_signer(private_key=TEST_KEY, max_amount_usdc=0.05)
    svc.register_rail("base", signer, networks=("base", BASE_USDC_NETWORK))
    return build_app(rails=svc, spend_guard=spend_guard)


def _request(app, method: str, path: str, **kwargs) -> httpx.Response:
    """Drive the ASGI app once and return the response (sync wrapper)."""

    async def _go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport, base_url="http://rails.test"
        ) as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(_go())


def _recover(header_value: str) -> str:
    payload = json.loads(base64.b64decode(header_value))["payload"]
    domain = {
        "name": BASE_USDC_DOMAIN["name"],
        "version": BASE_USDC_DOMAIN["version"],
        "chainId": BASE_USDC_DOMAIN["chainId"],
        "verifyingContract": BASE_USDC_ASSET,
    }
    types = {
        "TransferWithAuthorization": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"},
        ],
    }
    message = {
        "from": payload["from"],
        "to": payload["to"],
        "value": int(payload["value"]),
        "validAfter": int(payload["validAfter"]),
        "validBefore": int(payload["validBefore"]),
        "nonce": bytes.fromhex(payload["nonce"][2:]),
    }
    signable = encode_typed_data(
        domain_data=domain, message_types=types, message_data=message
    )
    return Account.recover_message(signable, signature=payload["signature"])


def test_describe_is_public():
    resp = _request(_app(), "GET", "/x402/rails/describe")
    assert resp.status_code == 200
    body = resp.json()
    assert body["service"] == "x402.rails"
    assert body["payment_header"] == "X-PAYMENT"


def test_rails_list_is_public():
    resp = _request(_app(), "GET", "/x402/rails/rails")
    assert resp.status_code == 200
    assert "base" in resp.json()["rails"]


def test_issue_requires_spend_gate(monkeypatch):
    monkeypatch.setenv("X402_RAILS_ADMIN_TOKEN", TOKEN)
    # No Authorization header -> rejected before any signing.
    resp = _request(_app(), "POST", "/x402/rails/issue", json={"challenge": _challenge()})
    assert resp.status_code == 401


def test_issue_fails_closed_when_token_unset(monkeypatch):
    monkeypatch.delenv("X402_RAILS_ADMIN_TOKEN", raising=False)
    resp = _request(
        _app(),
        "POST",
        "/x402/rails/issue",
        json={"challenge": _challenge()},
        headers={"Authorization": "Bearer anything"},
    )
    assert resp.status_code == 503  # gate not configured -> fail closed


def test_issue_with_token_mints_signed_credential(monkeypatch):
    monkeypatch.setenv("X402_RAILS_ADMIN_TOKEN", TOKEN)
    resp = _request(
        _app(),
        "POST",
        "/x402/rails/issue",
        json={"challenge": _challenge(amount=10000)},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status_code == 200
    cred = resp.json()
    assert cred["header_name"] == "X-PAYMENT"
    assert cred["amount_minor"] == 10000
    assert cred["recipient"] == RECIPIENT
    assert cred["payer"] == TEST_ADDRESS
    # The HTTP route returned a genuinely signed authorization.
    assert _recover(cred["header_value"]) == TEST_ADDRESS


def test_issue_accepts_base64_payment_required(monkeypatch):
    monkeypatch.setenv("X402_RAILS_ADMIN_TOKEN", TOKEN)
    header_b64 = base64.b64encode(json.dumps(_challenge()).encode()).decode()
    resp = _request(
        _app(),
        "POST",
        "/x402/rails/issue",
        json={"payment_required": header_b64},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status_code == 200
    assert _recover(resp.json()["header_value"]) == TEST_ADDRESS


def test_issue_over_budget_returns_402(monkeypatch):
    monkeypatch.setenv("X402_RAILS_ADMIN_TOKEN", TOKEN)
    resp = _request(
        _app(),
        "POST",
        "/x402/rails/issue",
        json={"challenge": _challenge(amount=2_000_000)},  # 2 USDC > 0.05
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status_code == 402


def test_issue_missing_body_is_422(monkeypatch):
    monkeypatch.setenv("X402_RAILS_ADMIN_TOKEN", TOKEN)
    resp = _request(
        _app(),
        "POST",
        "/x402/rails/issue",
        json={},
        headers={"Authorization": f"Bearer {TOKEN}"},
    )
    assert resp.status_code == 422


def test_injected_guard_is_used():
    # A custom guard replaces the env bearer entirely.
    def deny(_request):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="nope")

    resp = _request(
        _app(spend_guard=deny), "POST", "/x402/rails/issue", json={"challenge": _challenge()}
    )
    assert resp.status_code == 403
