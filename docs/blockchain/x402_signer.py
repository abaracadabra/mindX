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

"""Signature-based x402 wallet signer for the Base-USDC settlement surface.

``cmc_client.cmc_x402_client`` is deliberately chain-free: it performs the HTTP
``402`` decode/resign/resend handshake but delegates the cryptographic step to an
injected ``wallet_sign`` callable, so the chain decision lives in the wallet, not
the data client. This module is that concrete wallet for the Base settlement leg
that CoinMarketCap's x402 surface names (``eip155:8453``, USDC).

Access is by **signature, not by key or account**: the payment itself is the
access control. The signer produces an EIP-712 / EIP-3009
``transferWithAuthorization`` over the USDC contract and returns the canonical
x402 ``X-PAYMENT`` payload — ``base64(JSON({x402Version, scheme, network,
payload}))`` — exactly as the repo's other x402 clients
(``tools/keeperhub_x402_client.py``, ``tools/x402_avm_client.py``) construct it.

The signing private key is **never hard-coded**: it is read from the environment
(loaded from ``.env`` by :func:`cmc_client.load_env`), trying
``X402_WALLET_PRIVATE_KEY`` first and falling back to the repo's existing
``BASE_WALLET_PRIVATE_KEY`` / ``BUYER_PRIVATE_KEY`` names. The key stays in
process memory only; it is never logged and never placed in a header or URL.

Usage::

    from cmc_client import cmc_x402_client
    from x402_signer import x402_wallet_signer

    signer = x402_wallet_signer(max_amount_usdc=0.05)   # one-cent calls, 5c cap
    with cmc_x402_client(wallet_sign=signer) as client:
        data = client.get("/x402/v3/cryptocurrency/quotes/latest", {"id": "1"})
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import time
from collections.abc import Mapping
from typing import Any

# Importing cmc_client loads the project .env so the wallet key resolves from it.
from cmc_client import BASE_USDC_ASSET, BASE_USDC_NETWORK, load_env

load_env()

# Env var names searched, in order, for the Base wallet signing key.
WALLET_KEY_ENV_VARS: tuple[str, ...] = (
    "X402_WALLET_PRIVATE_KEY",
    "BASE_WALLET_PRIVATE_KEY",
    "BUYER_PRIVATE_KEY",
)

# EIP-712 domain for the canonical USDC contract on Base (EIP-3009 capable).
BASE_USDC_DOMAIN: dict[str, Any] = {
    "name": "USD Coin",
    "version": "2",
    "chainId": 8453,
}

USDC_MINOR_UNITS: int = 1_000_000  # USDC has six decimals.
AUTHORIZATION_TTL_SECONDS: int = 3600


class X402SignerError(RuntimeError):
    """Raised when a payment cannot be signed (no key, bad terms, over budget)."""


def _resolve_private_key(explicit: str | None) -> str:
    """Return the signing key from ``explicit`` or the environment.

    Raises:
        X402SignerError: When no key is configured.
    """
    if explicit:
        return explicit
    for name in WALLET_KEY_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value
    raise X402SignerError(
        "no x402 wallet key configured; set X402_WALLET_PRIVATE_KEY in .env "
        f"(searched {', '.join(WALLET_KEY_ENV_VARS)})"
    )


def _chain_id_from_network(network: str) -> int:
    """Map an x402 network id to an EVM chain id.

    Accepts CAIP-2 ``eip155:<id>`` strings and the bare alias ``base``.

    Raises:
        X402SignerError: When the network is not an EVM/Base settlement leg.
    """
    if network in ("base", BASE_USDC_NETWORK):
        return BASE_USDC_DOMAIN["chainId"]
    if network.startswith("eip155:"):
        try:
            return int(network.split(":", 1)[1])
        except ValueError as exc:
            raise X402SignerError(f"malformed eip155 network: {network!r}") from exc
    raise X402SignerError(
        f"network {network!r} is not an EVM settlement leg; this signer settles "
        "USDC on Base only — route Algorand-native x402 elsewhere"
    )


def _first_accept(challenge: Mapping[str, Any]) -> dict[str, Any]:
    """Return the first accepted settlement term from a decoded challenge."""
    accepts = challenge.get("accepts") or challenge.get("paymentRequirements") or []
    if not accepts:
        raise X402SignerError(f"x402 challenge carried no accepted terms: {challenge}")
    first = accepts[0]
    if not isinstance(first, Mapping):
        raise X402SignerError("x402 accepted term was not an object")
    return dict(first)


class x402_wallet_signer:
    """Concrete, signature-based ``wallet_sign`` for the Base-USDC x402 leg.

    Instances are callable: ``signer(challenge) -> str`` returns the base64
    ``X-PAYMENT`` payload that :class:`cmc_client.cmc_x402_client` attaches to the
    retried request. A signer with no spendable budget left, or a challenge that
    exceeds ``max_amount_usdc``, returns the empty string, which the data client
    reads as "wallet declined" and surfaces as ``CmcPaymentRequired`` rather than
    paying silently.

    Args:
        private_key: Signing key. Falls back to the environment
            (``X402_WALLET_PRIVATE_KEY`` etc., loaded from ``.env``). Required —
            constructing without a resolvable key raises immediately so the
            failure is loud rather than at the first payment.
        max_amount_usdc: Per-call ceiling in whole USDC. A term above this is
            declined (empty signature) instead of signed. ``None`` disables the
            ceiling; prefer setting it.
        recipient: Fallback payee address used only when a challenge omits
            ``payTo``. Normally the challenge names the recipient.
    """

    def __init__(
        self,
        private_key: str | None = None,
        *,
        max_amount_usdc: float | None = 0.05,
        recipient: str | None = None,
    ) -> None:
        self._private_key = _resolve_private_key(private_key)
        self._max_amount_usdc = max_amount_usdc
        self._recipient = recipient or os.environ.get("X402_RECIPIENT_ADDRESS")

    def __call__(self, challenge: Mapping[str, Any]) -> str:
        """Sign a decoded x402 challenge and return the ``X-PAYMENT`` payload.

        Returns the empty string to decline (over budget), which the caller maps
        to ``CmcPaymentRequired``.

        Raises:
            X402SignerError: On unsigned-able terms (wrong chain, no recipient).
        """
        term = _first_accept(challenge)
        network = str(term.get("network", BASE_USDC_NETWORK))
        chain_id = _chain_id_from_network(network)

        amount = int(term.get("maxAmountRequired", term.get("amount", 0)))
        if amount <= 0:
            raise X402SignerError("x402 term named a non-positive amount")
        if (
            self._max_amount_usdc is not None
            and amount / USDC_MINOR_UNITS > self._max_amount_usdc
        ):
            # Over budget: decline by returning an empty signature.
            return ""

        recipient = term.get("payTo") or self._recipient
        if not recipient:
            raise X402SignerError(
                "x402 term omitted payTo and no fallback recipient is configured"
            )
        asset = str(term.get("asset", BASE_USDC_ASSET))
        scheme = str(term.get("scheme", "exact"))

        return self._sign_authorization(
            chain_id=chain_id,
            network=network,
            scheme=scheme,
            asset=asset,
            recipient=str(recipient),
            amount=amount,
        )

    def _sign_authorization(
        self,
        *,
        chain_id: int,
        network: str,
        scheme: str,
        asset: str,
        recipient: str,
        amount: int,
    ) -> str:
        """Build and sign the EIP-3009 authorization, returning ``X-PAYMENT``."""
        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise X402SignerError(
                "eth-account is required for x402 signing (pip install eth-account)"
            ) from exc

        account = Account.from_key(self._private_key)
        valid_after = 0
        valid_before = int(time.time()) + AUTHORIZATION_TTL_SECONDS
        nonce = bytes.fromhex(secrets.token_hex(32))

        domain = {
            "name": BASE_USDC_DOMAIN["name"],
            "version": BASE_USDC_DOMAIN["version"],
            "chainId": chain_id,
            "verifyingContract": asset,
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
            "from": account.address,
            "to": recipient,
            "value": amount,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce,
        }
        signable = encode_typed_data(
            domain_data=domain, message_types=types, message_data=message
        )
        signed = account.sign_message(signable)

        envelope = {
            "x402Version": 1,
            "scheme": scheme,
            "network": network,
            "payload": {
                "from": account.address,
                "to": recipient,
                "value": str(amount),
                "validAfter": str(valid_after),
                "validBefore": str(valid_before),
                "nonce": "0x" + nonce.hex(),
                "signature": signed.signature.to_0x_hex(),
            },
        }
        return base64.b64encode(json.dumps(envelope).encode()).decode()


def base_usdc_x402_signer(
    *,
    private_key: str | None = None,
    max_amount_usdc: float | None = 0.05,
    recipient: str | None = None,
) -> x402_wallet_signer:
    """Construct a Base-USDC :class:`x402_wallet_signer` (convenience factory)."""
    return x402_wallet_signer(
        private_key,
        max_amount_usdc=max_amount_usdc,
        recipient=recipient,
    )
