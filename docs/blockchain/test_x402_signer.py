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

"""Offline tests for ``x402_signer`` and its integration with ``cmc_x402_client``.

The signature is verified cryptographically: each test recovers the signer's
address from the EIP-712 authorization it produced and asserts it matches the
account derived from the configured key. No network and no chain are touched.
"""

from __future__ import annotations

import base64
import json

import httpx
import pytest
from eth_account import Account
from eth_account.messages import encode_typed_data

from cmc_client import BASE_USDC_ASSET, BASE_USDC_NETWORK, cmc_x402_client
from x402_signer import (
    BASE_USDC_DOMAIN,
    X402SignerError,
    base_usdc_x402_signer,
    x402_wallet_signer,
)

# A throwaway key used only for offline signing — never funded, never deployed.
TEST_KEY = "0x59c6995e998f97a5a0044966f0945389dc9e86dae88c7a8412f4603b6b78690d"
TEST_ADDRESS = Account.from_key(TEST_KEY).address
RECIPIENT = "0x000000000000000000000000000000000000dEaD"


def _challenge(amount: int = 10000, *, network: str = BASE_USDC_NETWORK) -> dict:
    """Build a decoded CMC-style x402 challenge (one cent on Base by default)."""
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


def _recover_from_payment(payment_b64: str) -> tuple[str, dict]:
    """Decode an X-PAYMENT payload and recover the EIP-712 signer address."""
    envelope = json.loads(base64.b64decode(payment_b64))
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
    recovered = Account.recover_message(signable, signature=payload["signature"])
    return recovered, envelope


def test_key_read_from_env(monkeypatch):
    monkeypatch.setenv("X402_WALLET_PRIVATE_KEY", TEST_KEY)
    signer = x402_wallet_signer()  # no explicit key -> must read .env/environ
    payment = signer(_challenge())
    recovered, _ = _recover_from_payment(payment)
    assert recovered == TEST_ADDRESS


def test_signature_is_valid_and_terms_preserved(monkeypatch):
    monkeypatch.delenv("X402_WALLET_PRIVATE_KEY", raising=False)
    signer = base_usdc_x402_signer(private_key=TEST_KEY)
    payment = signer(_challenge(amount=10000))
    recovered, envelope = _recover_from_payment(payment)
    assert recovered == TEST_ADDRESS
    assert envelope["x402Version"] == 1
    assert envelope["scheme"] == "exact"
    assert envelope["network"] == BASE_USDC_NETWORK
    assert envelope["payload"]["to"] == RECIPIENT
    assert envelope["payload"]["value"] == "10000"


def test_missing_key_raises(monkeypatch):
    # Clear every env name the signer searches so the failure is deterministic.
    for name in ("X402_WALLET_PRIVATE_KEY", "BASE_WALLET_PRIVATE_KEY", "BUYER_PRIVATE_KEY"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(X402SignerError):
        x402_wallet_signer(private_key="")


def test_over_budget_declines_with_empty_signature():
    # 2_000_000 minor units = 2 USDC, over the 0.05 ceiling.
    signer = x402_wallet_signer(private_key=TEST_KEY, max_amount_usdc=0.05)
    assert signer(_challenge(amount=2_000_000)) == ""


def test_non_evm_network_rejected():
    signer = x402_wallet_signer(private_key=TEST_KEY)
    with pytest.raises(X402SignerError):
        signer(_challenge(network="algorand:mainnet"))


def test_missing_recipient_rejected():
    signer = x402_wallet_signer(private_key=TEST_KEY)
    challenge = {"accepts": [{"network": BASE_USDC_NETWORK, "amount": 10000}]}
    with pytest.raises(X402SignerError):
        signer(challenge)


def test_eip155_network_chain_id_parsed():
    signer = x402_wallet_signer(private_key=TEST_KEY)
    # eip155:8453 must be accepted as Base and sign successfully.
    payment = signer(_challenge(network="eip155:8453"))
    recovered, _ = _recover_from_payment(payment)
    assert recovered == TEST_ADDRESS


def test_integration_with_cmc_x402_client():
    """402 -> sign -> resend carries the signed X-PAYMENT, then 200 returns data."""
    seen = {}
    challenge_b64 = base64.b64encode(json.dumps(_challenge()).encode()).decode()

    def handler(request: httpx.Request) -> httpx.Response:
        payment = request.headers.get("x-payment")
        if payment is None:
            return httpx.Response(
                402, headers={"payment-required": challenge_b64}, json={}
            )
        seen["payment"] = payment
        return httpx.Response(200, json={"data": {"price": 42000}})

    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        base_url="https://pro-api.coinmarketcap.com", transport=transport
    )
    signer = x402_wallet_signer(private_key=TEST_KEY)
    client = cmc_x402_client(signer, payment_header="X-PAYMENT")
    client._http = http  # inject the mock transport

    out = client.get("/x402/v3/cryptocurrency/quotes/latest", {"id": "1"})
    assert out == {"price": 42000}
    # The retried request actually carried a valid signature.
    recovered, _ = _recover_from_payment(seen["payment"])
    assert recovered == TEST_ADDRESS
