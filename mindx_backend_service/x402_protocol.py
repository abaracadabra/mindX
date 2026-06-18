# Copyright 2026 BANKON. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

"""x402 protocol layer — version (v1/v2) + CAIP-2 single source of truth.

The one module both the server (``x402_middleware``) and the client
(``tools/x402_rails`` / ``tools/x402_avm_client``) import so version handling and
network identifiers never drift. It is pure stdlib (no FastAPI / no chain SDK) so
it imports anywhere.

x402 **v2** (shipped 2025-12-11) uses **CAIP-2** network ids and header-based
payment data (``PAYMENT-REQUIRED`` / ``PAYMENT-SIGNATURE`` / ``PAYMENT-RESPONSE``),
and is backward-compatible with **v1** (``X-PAYMENT`` request header + JSON body
``{x402Version:1, accepts|paymentRequirements:[...]}`` + ``X-PAYMENT-RESPONSE``).
Reference: ``docs/operations/dev/x402 Multi-Rail Integration Reference …``.

This module is deliberately rail-agnostic: a single ``rail_for(network)`` switch
keyed off the CAIP-2 namespace dispatches to ``evm`` | ``avm`` | ``arweave``
(reference §5), mirroring the ``allchain.html`` chain registry.
"""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, List, Mapping, Optional, Tuple

X402_VERSION = 2

# v2 headers (canonical) and the v1 aliases we still read/emit for back-compat.
HEADER_PAYMENT_REQUIRED = "PAYMENT-REQUIRED"      # v2 challenge (response)
HEADER_PAYMENT_SIGNATURE = "PAYMENT-SIGNATURE"    # v2 payment (request)
HEADER_PAYMENT_RESPONSE = "PAYMENT-RESPONSE"      # v2 settlement (response)
HEADER_X_PAYMENT = "X-PAYMENT"                    # v1 payment (request)
HEADER_X_PAYMENT_RESPONSE = "X-PAYMENT-RESPONSE"  # v1 settlement (response)

# ── CAIP-2 ↔ legacy network-name map ─────────────────────────────────────────
# Canonical CAIP-2 id (left) ↔ the legacy aliases mindX v1 config used (right).
_CAIP2_BY_ALIAS: Dict[str, str] = {
    # EVM
    "base": "eip155:8453",
    "eip155:8453": "eip155:8453",
    "8453": "eip155:8453",
    "ethereum": "eip155:1",
    "eip155:1": "eip155:1",
    "1": "eip155:1",
    "tempo": "eip155:4217",
    "eip155:4217": "eip155:4217",
    "4217": "eip155:4217",
    # Algorand (genesis-hash CAIP-2 form)
    "algorand-mainnet": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
    "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=": "algorand:wGHE2Pwdvd7S12BL5FaOP20EGYesN73ktiC1qzkkit8=",
    "algorand-testnet": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
    "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=": "algorand:SGO1GKSzyE7IEPItTxCByw9x8FmnrCDexi9/cOUJOiI=",
    # Arweave — synthetic id for the fulfillment leg (no settlement chain)
    "arweave": "arweave:permaweb",
    "arweave:permaweb": "arweave:permaweb",
    "permaweb": "arweave:permaweb",
}

# USDC asset constants (reference §3): Algorand ASA is 6-decimal.
USDC_ASA_MAINNET = 31566704
USDC_ASA_TESTNET = 10458941
USDC_BASE_MAINNET = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def to_caip2(network: str) -> str:
    """Normalize any accepted network name/alias to its CAIP-2 id.

    Unknown inputs are returned unchanged (callers treat them as opaque) so this
    never raises on a forward-compatible new network.
    """
    if not network:
        return network
    return _CAIP2_BY_ALIAS.get(network, _CAIP2_BY_ALIAS.get(network.lower(), network))


def rail_for(network: str) -> str:
    """Dispatch a network id to its rail family: ``evm`` | ``avm`` | ``arweave``.

    Keyed off the CAIP-2 namespace (reference §5). Accepts legacy aliases too.
    """
    caip2 = to_caip2(network)
    if caip2.startswith("eip155:"):
        return "evm"
    if caip2.startswith("algorand:"):
        return "avm"
    if caip2.startswith("arweave:"):
        return "arweave"
    raise ValueError(f"unsupported x402 network {network!r}")


# ── envelope codec (challenge + payment + settlement) ────────────────────────


def _b64_json(obj: Any) -> str:
    return base64.b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode()


def _unb64_json(value: str) -> Any:
    return json.loads(base64.b64decode(value).decode("utf-8"))


def encode_requirements(
    endpoint_id: str, requirements: List[Dict[str, Any]], *, message: str = ""
) -> Tuple[Dict[str, Any], str]:
    """Build the 402 challenge in BOTH forms.

    Returns ``(json_body, payment_required_header)``:
      * ``json_body`` — the v1/v2 body ``{x402Version:2, accepts, paymentRequirements, …}``
        (``accepts`` and ``paymentRequirements`` are the same list, under both keys,
        so v1 and v2 clients each find what they expect).
      * ``payment_required_header`` — the base64 v2 ``PAYMENT-REQUIRED`` value.

    Every requirement's ``network`` is normalized to CAIP-2.
    """
    reqs = [{**r, "network": to_caip2(str(r.get("network", "")))} for r in requirements]
    body = {
        "x402Version": X402_VERSION,
        "accepts": reqs,
        "paymentRequirements": reqs,  # v1 alias
        "endpoint": endpoint_id,
        "code": "x402_payment_required",
        "message": message or "Payment required. Settle on an offered rail and retry.",
    }
    header = _b64_json({"x402Version": X402_VERSION, "accepts": reqs})
    return body, header


def decode_payment(headers: Mapping[str, str]) -> Tuple[Optional[Dict[str, Any]], int]:
    """Read a payment from request headers, v2 first then v1.

    Returns ``(envelope, version)`` where ``envelope`` is the decoded
    ``{x402Version, scheme, network, payload, …}`` dict (or ``None`` if absent /
    undecodable) and ``version`` is 2 (``PAYMENT-SIGNATURE``) or 1 (``X-PAYMENT``).
    Header lookup is case-insensitive.
    """
    lower = {k.lower(): v for k, v in headers.items()}
    raw = lower.get(HEADER_PAYMENT_SIGNATURE.lower())
    version = 2
    if not raw:
        raw = lower.get(HEADER_X_PAYMENT.lower())
        version = 1
    if not raw:
        return None, version
    try:
        env = _unb64_json(raw)
        if isinstance(env, dict):
            return env, version
    except Exception:
        return None, version
    return None, version


def encode_settlement(record: Mapping[str, Any]) -> str:
    """Base64 the settlement record for the ``PAYMENT-RESPONSE`` headers."""
    return _b64_json(dict(record))


def settlement_headers(record: Mapping[str, Any]) -> Dict[str, str]:
    """Return BOTH the v2 and v1 settlement response headers for ``record``."""
    enc = encode_settlement(record)
    return {HEADER_PAYMENT_RESPONSE: enc, HEADER_X_PAYMENT_RESPONSE: enc}


def replay_key(network: str, payload: Mapping[str, Any]) -> Optional[str]:
    """Derive a stable, permanent replay key for a payment payload.

    EVM (EIP-3009): the single-use ``authorization.nonce``. AVM (Parsec): the
    ``paymentIndex`` txn's id / group hash if present, else a hash of the
    ``paymentGroup``. Returns ``"<caip2>:<key>"`` or ``None`` if no key found.
    """
    caip2 = to_caip2(network)
    fam = None
    try:
        fam = rail_for(network)
    except ValueError:
        fam = None
    key: Optional[str] = None
    if fam == "evm":
        auth = payload.get("authorization") if isinstance(payload, Mapping) else None
        if isinstance(auth, Mapping):
            key = auth.get("nonce")
        key = key or payload.get("nonce")
    elif fam == "avm":
        key = payload.get("txid") or payload.get("transaction")
        if not key:
            group = payload.get("paymentGroup")
            if isinstance(group, list) and group:
                import hashlib

                key = hashlib.sha256("".join(map(str, group)).encode()).hexdigest()
    else:
        # arweave fulfillment / unknown — hash the whole payload deterministically
        import hashlib

        key = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()
    return f"{caip2}:{key}" if key else None


__all__ = [
    "X402_VERSION",
    "HEADER_PAYMENT_REQUIRED",
    "HEADER_PAYMENT_SIGNATURE",
    "HEADER_PAYMENT_RESPONSE",
    "HEADER_X_PAYMENT",
    "HEADER_X_PAYMENT_RESPONSE",
    "USDC_ASA_MAINNET",
    "USDC_ASA_TESTNET",
    "USDC_BASE_MAINNET",
    "to_caip2",
    "rail_for",
    "encode_requirements",
    "decode_payment",
    "encode_settlement",
    "settlement_headers",
    "replay_key",
]
