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

"""x402_signer — wallet-held EIP-3009 signing for x402 settlement.

A *signer* is a ``callable(challenge) -> X-PAYMENT payload`` that turns a
decoded x402 ``402`` challenge into a single-use, base64-encoded ``X-PAYMENT``
authorization. The wallet private key stays inside this module's closure; what
crosses the boundary is the signature. This is the leg
:class:`tools.x402_rails.X402RailsService` registers as the built-in ``base``
rail (via :func:`base_usdc_x402_signer`).

The signature this produces is, by the books:

* an **ERC-3009 ``TransferWithAuthorization``** — *Transfer With Authorization*,
  a transfer of fungible assets via a signed authorization with a random 32-byte
  ``nonce`` (single-use), ``validAfter`` / ``validBefore`` window, and no gas
  held by the payer. https://eips.ethereum.org/EIPS/eip-3009
* hashed and signed under **EIP-712** — *Typed structured data hashing and
  signing* — over the ``TransferWithAuthorization`` struct, domain-separated by
  the ERC-20 token's name/version and its **EIP-155** ``chainId``.
  https://eips.ethereum.org/EIPS/eip-712 · https://eips.ethereum.org/EIPS/eip-155
* the value moved is an **ERC-20** *Token Standard* asset (USDC on Base).
  https://eips.ethereum.org/EIPS/eip-20

See ``docs/cypherpunk2048/EIP_REFERENCES.md`` for the full reference table and
``docs/cypherpunk2048/x402_rails.md`` for how this composes into a credential.

The signer honours the *no-trapdoors* and *vault-as-oracle* rules of the
cypherpunk2048 standard: the key is reached only from the vault or an explicit
environment deposit, it is never returned, and a challenge whose amount exceeds
the configured ceiling is **declined** (the signer returns an empty string)
rather than silently overpaying.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import time
from collections.abc import Callable, Mapping
from typing import Any

# ERC-20 USDC carries 6 decimals; one whole USDC is 1_000_000 minor units.
USDC_MINOR_UNITS: int = 1_000_000

# Canonical Base mainnet USDC (ERC-20) contract — the verifyingContract for the
# EIP-712 domain when a challenge term omits ``asset``.
BASE_USDC_ASSET: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# EIP-712 domain template for USDC on Base. ``chainId`` is the EIP-155 chain id.
_BASE_USDC_DOMAIN: dict[str, Any] = {
    "name": "USD Coin",
    "version": "2",
    "chainId": 8453,
}

# x402 networks the Base rail settles (plain name + CAIP-2 / eip155 form).
_BASE_NETWORKS = frozenset({"base", "eip155:8453", "8453"})

# Environment deposits checked, in order, when no key is passed explicitly.
_KEY_ENV_VARS = (
    "BASE_X402_PRIVATE_KEY",
    "MINDX_BASE_X402_PRIVATE_KEY",
    "BUYER_PRIVATE_KEY",
)

# A signer maps a decoded challenge to an X-PAYMENT payload string (or "" when
# it declines — by convention, over its budget ceiling).
wallet_signer = Callable[[Mapping[str, Any]], str]


class X402SignerError(RuntimeError):
    """Raised when signing is impossible (no key, malformed terms, bad network)."""


def _resolve_key(explicit: str | None) -> str:
    """Resolve the signing key from an explicit value, env, then BANKON vault.

    The key is never returned to a caller; it is read here and closed over by
    the signer. A missing key fails at *issuance* (when this is called), never
    at construction — so the rails service can advertise the Base rail before a
    key is configured.
    """
    if explicit:
        return explicit
    for name in _KEY_ENV_VARS:
        value = os.environ.get(name)
        if value:
            return value
    # Best-effort BANKON vault deposit (vault-as-oracle): never hard-import.
    try:  # pragma: no cover - depends on deployment vault wiring
        from mindx_backend_service.bankon_vault import get_credential  # type: ignore

        value = get_credential("base_x402_private_key")
        if value:
            return value
    except Exception:
        pass
    raise X402SignerError(
        "no Base signing key configured; set BASE_X402_PRIVATE_KEY or deposit "
        "'base_x402_private_key' in the BANKON vault"
    )


def _first_term(challenge: Mapping[str, Any]) -> dict[str, Any]:
    accepts = challenge.get("accepts") or challenge.get("paymentRequirements") or []
    if not accepts or not isinstance(accepts[0], Mapping):
        raise X402SignerError("challenge carried no usable accepted terms")
    return dict(accepts[0])


def base_usdc_x402_signer(
    *,
    max_amount_usdc: float | None = None,
    private_key: str | None = None,
) -> wallet_signer:
    """Build the built-in Base-USDC signer for :class:`X402RailsService`.

    Returns a ``callable(challenge) -> str`` that signs an ERC-3009
    ``TransferWithAuthorization`` (EIP-712, EIP-155 domain) for the Base USDC
    rail and returns the base64 ``X-PAYMENT`` envelope. The returned envelope is
    ``{x402Version, scheme, network, payload}`` where ``payload`` carries
    ``from``/``to``/``value``/``validAfter``/``validBefore``/``nonce``/``signature``
    — the shape :meth:`X402RailsService._credential_from_payload` decodes.

    Budget rule: when the challenge's ``maxAmountRequired`` exceeds
    ``max_amount_usdc``, the signer returns ``""`` (declines). The rails service
    reads an empty return as :class:`X402BudgetExceeded`.

    Args:
        max_amount_usdc: Per-call ceiling in whole USDC. ``None`` disables it.
        private_key: Override the resolved signing key (test/embed use).
    """

    def _sign(challenge: Mapping[str, Any]) -> str:
        term = _first_term(challenge)
        network = str(term.get("network", "base"))
        if network not in _BASE_NETWORKS:
            raise X402SignerError(
                f"base signer cannot settle network {network!r} "
                f"(handles: {sorted(_BASE_NETWORKS)})"
            )

        amount = int(term.get("maxAmountRequired", term.get("amount", 0)))
        if amount <= 0:
            raise X402SignerError("challenge named a non-positive amount")
        if max_amount_usdc is not None and amount / USDC_MINOR_UNITS > max_amount_usdc:
            # Decline — over the ceiling. The rails service maps "" to budget.
            return ""

        try:
            from eth_account import Account
            from eth_account.messages import encode_typed_data
        except ImportError as exc:  # pragma: no cover - env without eth-account
            raise X402SignerError(
                "eth-account is required to sign (pip install eth-account)"
            ) from exc

        key = _resolve_key(private_key)
        asset = str(term.get("asset") or BASE_USDC_ASSET)
        recipient = str(term["payTo"])
        valid_after = 0
        valid_before = int(time.time()) + 3600
        nonce_bytes = secrets.token_bytes(32)

        account = Account.from_key(key)
        from_address = account.address

        domain = {**_BASE_USDC_DOMAIN, "verifyingContract": asset}
        # ERC-3009 TransferWithAuthorization typed-data struct (EIP-712).
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
            "from": from_address,
            "to": recipient,
            "value": amount,
            "validAfter": valid_after,
            "validBefore": valid_before,
            "nonce": nonce_bytes,
        }
        signable = encode_typed_data(
            domain_data=domain, message_types=types, message_data=message
        )
        signed = account.sign_message(signable)

        payload = {
            "from": from_address,
            "to": recipient,
            "value": str(amount),
            "validAfter": str(valid_after),
            "validBefore": str(valid_before),
            "nonce": "0x" + nonce_bytes.hex(),
            "signature": signed.signature.to_0x_hex(),
        }
        # x402 v2 envelope: CAIP-2 network id + version 2. The server reads both
        # v2 (PAYMENT-SIGNATURE) and v1 (X-PAYMENT) and both envelope versions, so
        # this stays backward-compatible while advertising as v2.
        envelope = {
            "x402Version": 2,
            "scheme": str(term.get("scheme", "exact")),
            "network": "eip155:8453",  # CAIP-2 for Base mainnet (this is the Base rail)
            "payload": payload,
        }
        return base64.b64encode(json.dumps(envelope).encode()).decode()

    return _sign


__all__ = [
    "USDC_MINOR_UNITS",
    "BASE_USDC_ASSET",
    "X402SignerError",
    "wallet_signer",
    "base_usdc_x402_signer",
]
