"""OVERLORD auth — EVM (bankon.eth) wallet sign-in → scope-bound OVERLORD JWT.

The EVM mirror of ``overseer_auth`` (the Algorand OVERSEER, mindx.algo). bankon.eth — the
``SHADOW_OVERLORD_ADDRESS`` — is the EVM admin for mindX's contracts and deployment. This module exposes
the symmetric ``/auth/evm`` doorway by reusing ``shadow_overlord``'s ECDSA recover + single-use nonce store
+ HS256 JWT: the OVERLORD scope IS the shadow-overlord auth scope, so the JWT this mints is the same admin
credential the existing ``require_admin_access`` gate already accepts. Two chains, one ladder:

    OVERLORD  = bankon.eth   (EVM,      ECDSA   → here)            — EVM admin / contracts / deployment
    OVERSEER  = mindx.algo   (Algorand, Ed25519 → overseer_auth)  — Algorand hierarchy / deploy suites
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException

from mindx_backend_service.bankon_vault import shadow_overlord as _so

# The OVERLORD scope is the shadow-overlord auth scope — the OVERLORD login mints the admin JWT.
SCOPE_OVERLORD = _so.SCOPE_AUTH


def challenge_message(nonce: str) -> str:
    """Canonical OVERLORD-LOGIN message the operator signs with the bankon.eth wallet (EIP-191)."""
    return (
        "mindX OVERLORD-LOGIN\n"
        "Sign to prove control of bankon.eth.\n"
        f"nonce: {nonce}\n"
        "This grants OVERLORD (EVM admin) access to mindX's contracts and deployment."
    )


def issue_challenge() -> Dict[str, str]:
    """Mint a single-use OVERLORD-LOGIN challenge bound to a fresh nonce (shared shadow-overlord store)."""
    store = _so.get_store()
    nonce = store.issue(SCOPE_OVERLORD, "PENDING", {})
    msg = challenge_message(nonce)
    rec = store._records.get(nonce)
    if rec is not None:                 # bind the nonce-embedding message before the signer sees it
        rec.message = msg
        store._persist()
    return {"nonce": nonce, "message": msg}


def consume_overlord_login(nonce: str, signature: str, address: str = "", wallet: str = "evm") -> Dict[str, Any]:
    """Validate a signed OVERLORD-LOGIN and, on success, return the OVERLORD (admin) JWT.

    ``shadow_overlord.consume_signed_challenge`` looks up the nonce (single-use, unexpired), recovers the
    EVM signer from the EIP-191 signature, asserts it is bankon.eth (the shadow-overlord), and consumes the
    nonce. We then mint the scope-bound JWT for that address.
    """
    _so.consume_signed_challenge(nonce, signature, SCOPE_OVERLORD)
    addr = _so._shadow_address()        # the verified signer == bankon.eth
    tok = _so.issue_jwt(addr, scope=SCOPE_OVERLORD)
    return {"address": addr, "wallet": wallet, "role": "overlord", **tok}


def verify_overlord_jwt(token: str) -> Dict[str, Any]:
    """Verify an OVERLORD Bearer JWT — shadow_overlord.verify_jwt binds sub == bankon.eth + checks scope."""
    return _so.verify_jwt(token, required_scope=SCOPE_OVERLORD)
