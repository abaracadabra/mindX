"""Unit tests for the x402 payment-rails credential service.

Contract documented in docs/cypherpunk2048/x402_rails.md.

These tests use a fake in-process signer, so they need neither a wallet key,
``eth-account``, nor any network. They exercise the parts that make the service
a cypherpunk2048-conforming credential issuer: challenge decode, rail routing,
budget decline, credential shape, and the audit ledger.
"""

from __future__ import annotations

import base64
import json

import pytest

from tools.cmc_client import CMCClientError, decode_payment_challenge
from tools.x402_rails import (
    PaymentCredential,
    X402BudgetExceeded,
    X402RailsService,
    X402RailUnavailable,
)
from tools.x402_signer import USDC_MINOR_UNITS

PAYER = "0x000000000000000000000000000000000000bEEF"
PAYEE = "0x000000000000000000000000000000000000dEaD"
USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def _challenge(amount_minor: int = 2000, network: str = "eip155:8453") -> dict:
    return {
        "accepts": [
            {
                "scheme": "exact",
                "network": network,
                "asset": USDC,
                "maxAmountRequired": str(amount_minor),
                "payTo": PAYEE,
            }
        ]
    }


def _fake_base_signer(amount_minor: int):
    """A signer that emits a valid envelope without a key, for the named amount."""

    def _sign(challenge):  # noqa: ANN001 - test double
        envelope = {
            "x402Version": 1,
            "scheme": "exact",
            "network": "eip155:8453",
            "payload": {
                "from": PAYER,
                "to": PAYEE,
                "value": str(amount_minor),
                "validAfter": "0",
                "validBefore": "9999999999",
                "nonce": "0x" + "11" * 32,
                "signature": "0x" + "22" * 65,
            },
        }
        return base64.b64encode(json.dumps(envelope).encode()).decode()

    return _sign


# --- cmc_client.decode_payment_challenge ------------------------------------


def test_decode_accepts_dict_json_and_base64():
    challenge = _challenge()
    as_json = json.dumps(challenge)
    as_b64 = base64.b64encode(as_json.encode()).decode()

    for source in (challenge, as_json, as_b64):
        decoded = decode_payment_challenge(source)
        assert decoded["accepts"][0]["network"] == "eip155:8453"


def test_decode_normalises_payment_requirements_key():
    decoded = decode_payment_challenge({"paymentRequirements": _challenge()["accepts"]})
    assert decoded["accepts"][0]["payTo"] == PAYEE


def test_decode_rejects_empty_terms():
    with pytest.raises(CMCClientError):
        decode_payment_challenge({"accepts": []})


# --- X402RailsService.issue_from_challenge ----------------------------------


def test_issue_produces_auditable_credential():
    rails = X402RailsService(max_amount_usdc=0.05)
    rails.register_rail("base", _fake_base_signer(2000), networks=("eip155:8453",))

    cred = rails.issue_from_challenge(_challenge(2000))

    assert isinstance(cred, PaymentCredential)
    assert cred.header_name == "X-PAYMENT"
    assert cred.rail == "base"
    assert cred.asset == USDC
    assert cred.amount_minor == 2000
    assert cred.amount_usdc == 2000 / USDC_MINOR_UNITS
    assert cred.payer == PAYER
    assert cred.recipient == PAYEE
    assert cred.as_headers() == {"X-PAYMENT": cred.header_value}
    # self-auditing wire form round-trips
    assert cred.to_dict()["nonce"] == cred.nonce


def test_ledger_records_every_issue():
    rails = X402RailsService()
    rails.register_rail("base", _fake_base_signer(2000), networks=("eip155:8453",))

    assert rails.ledger == []
    rails.issue_from_challenge(_challenge(2000))
    rails.issue_from_challenge(_challenge(2000))
    assert len(rails.ledger) == 2
    assert rails.describe()["issued_count"] == 2


def test_budget_decline_raises_when_signer_returns_empty():
    rails = X402RailsService(max_amount_usdc=0.001)
    # A signer that declines (returns "") signals over-budget by convention.
    rails.register_rail("base", lambda _c: "", networks=("eip155:8453",))

    with pytest.raises(X402BudgetExceeded):
        rails.issue_from_challenge(_challenge(2000))


def test_unknown_network_raises_rail_unavailable():
    rails = X402RailsService()
    rails.register_rail("base", _fake_base_signer(2000), networks=("eip155:8453",))

    with pytest.raises(X402RailUnavailable):
        rails.issue_from_challenge(_challenge(network="eip155:1"))


def test_register_rail_is_advertised_and_routed():
    rails = X402RailsService()
    rails.register_rail("base", _fake_base_signer(2000), networks=("eip155:8453",))
    rails.register_rail(
        "algorand", _fake_base_signer(2000), networks=("algorand-mainnet",)
    )

    assert set(rails.offered_rails()) >= {"algorand", "base"}
    described = {r["name"] for r in rails.describe()["rails"]}
    assert {"algorand", "base"} <= described
