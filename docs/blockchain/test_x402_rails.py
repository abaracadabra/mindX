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

"""Offline tests for ``x402_rails`` (the x402rails.agent service).

No network and no chain: the wallet signer is the real signature-based signer
with a throwaway key, and HTTP is an injected ``httpx.MockTransport``. Each
issued credential's signature is recovered cryptographically to prove the
service issues genuine authorizations, not opaque blobs.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data

from cmc_client import BASE_USDC_ASSET, BASE_USDC_NETWORK
from x402_rails import (
    PaymentCredential,
    X402BudgetExceeded,
    X402RailsService,
    X402RailUnavailable,
)
from x402_signer import BASE_USDC_DOMAIN, x402_wallet_signer

TEST_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
TEST_ADDRESS = Account.from_key(TEST_KEY).address
RECIPIENT = "0x000000000000000000000000000000000000dEaD"


def _challenge(amount: int = 10000, *, network: str = BASE_USDC_NETWORK) -> dict:
    return {
        "accepts": [
            {
                "scheme": "exact",
                "network": network,
                "asset": BASE_USDC_ASSET,
                "amount": amount,
                "payTo": RECIPIENT,
            }
        ]
    }


def _service(*, max_amount_usdc: float | None = 0.05) -> X402RailsService:
    """A service whose Base rail uses the throwaway test key."""
    svc = X402RailsService(max_amount_usdc=max_amount_usdc)
    signer = x402_wallet_signer(private_key=TEST_KEY, max_amount_usdc=max_amount_usdc)
    svc.register_rail(
        "base", signer, networks=("base", BASE_USDC_NETWORK),
        max_amount_usdc=max_amount_usdc,
    )
    return svc


def _recover(credential: PaymentCredential) -> str:
    envelope = json.loads(base64.b64decode(credential.header_value))
    payload = envelope["payload"]
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


def test_issue_from_challenge_returns_signed_credential():
    svc = _service()
    cred = svc.issue_from_challenge(_challenge(amount=10000))
    assert cred.header_name == "X-PAYMENT"
    assert cred.network == BASE_USDC_NETWORK
    assert cred.rail == "base"
    assert cred.amount_minor == 10000
    assert cred.amount_usdc == pytest.approx(0.01)
    assert cred.asset == BASE_USDC_ASSET
    assert cred.recipient == RECIPIENT
    assert cred.payer == TEST_ADDRESS
    # The credential carries a genuine signature from the rail wallet.
    assert _recover(cred) == TEST_ADDRESS


def test_credential_as_headers_is_what_a_consumer_attaches():
    svc = _service()
    cred = svc.issue_from_challenge(_challenge())
    headers = cred.as_headers()
    assert headers == {"X-PAYMENT": cred.header_value}


def test_over_budget_raises_budget_exceeded():
    svc = _service(max_amount_usdc=0.05)
    with pytest.raises(X402BudgetExceeded):
        svc.issue_from_challenge(_challenge(amount=2_000_000))  # 2 USDC


def test_unknown_network_has_no_rail():
    svc = _service()
    with pytest.raises(X402RailUnavailable):
        svc.issue_from_challenge(_challenge(network="algorand:mainnet"))


def test_ledger_records_issued_credentials():
    svc = _service()
    svc.issue_from_challenge(_challenge())
    svc.issue_from_challenge(_challenge(amount=20000))
    assert len(svc.ledger) == 2
    assert svc.ledger[1].amount_minor == 20000


def test_describe_advertises_rails():
    svc = _service()
    card = svc.describe()
    assert card["service"] == "x402.rails"
    assert card["payment_header"] == "X-PAYMENT"
    assert "base" in svc.offered_rails()
    assert any(r["name"] == "base" for r in card["rails"])


def test_base_rail_is_offered_lazily_without_a_key():
    # A fresh service advertises the base rail before any key is configured;
    # construction must not require a wallet.
    svc = X402RailsService()
    assert "base" in svc.offered_rails()
    assert svc.describe()["issued_count"] == 0


def test_register_rail_adds_a_settlement_leg():
    svc = X402RailsService()

    def fake_avm_signer(_challenge):  # a stand-in Algorand rail
        return base64.b64encode(
            json.dumps(
                {
                    "x402Version": 1,
                    "scheme": "exact",
                    "network": "algorand:mainnet",
                    "payload": {
                        "from": "ALGOADDR",
                        "to": "ALGORECIPIENT",
                        "value": "10000",
                        "validAfter": "0",
                        "validBefore": "9999999999",
                        "nonce": "0xab",
                    },
                }
            ).encode()
        ).decode()

    svc.register_rail(
        "algorand", fake_avm_signer, networks=("algorand:mainnet",)
    )
    cred = svc.issue_from_challenge(
        _challenge(network="algorand:mainnet"), rail=None
    )
    assert cred.rail == "algorand"
    assert cred.network == "algorand:mainnet"
    assert "algorand" in svc.offered_rails()


def test_settle_runs_full_402_then_200_cycle():
    svc = _service()
    challenge_b64 = base64.b64encode(json.dumps(_challenge()).encode()).decode()
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        payment = request.headers.get("x-payment")
        if payment is None:
            return httpx.Response(
                402, headers={"payment-required": challenge_b64}, json={}
            )
        seen["payment"] = payment
        return httpx.Response(200, json={"data": {"price": 42000}})

    http = httpx.Client(
        base_url="https://pro-api.coinmarketcap.com",
        transport=httpx.MockTransport(handler),
    )
    out = svc.settle("/x402/v3/cryptocurrency/quotes/latest", {"id": "1"}, http=http)
    assert out == {"price": 42000}
    # The retried request carried a credential signed by the rail wallet.
    env = json.loads(base64.b64decode(seen["payment"]))
    assert env["payload"]["from"] == TEST_ADDRESS


def test_issue_for_url_does_not_settle():
    svc = _service()
    challenge_b64 = base64.b64encode(json.dumps(_challenge()).encode()).decode()
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(
            402, headers={"payment-required": challenge_b64}, json={}
        )

    http = httpx.Client(
        base_url="https://pro-api.coinmarketcap.com",
        transport=httpx.MockTransport(handler),
    )
    cred = svc.issue_for_url("/x402/v3/cryptocurrency/quotes/latest", http=http)
    assert cred.payer == TEST_ADDRESS
    assert calls["n"] == 1  # probed once, never resent
