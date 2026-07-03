# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""realm_session — the mindX OVERLORD-protocol signature gate (clean-room web3).

Completes mindX's own gate rather than adopting an external dependency (Lit /
thirdweb): a SIWE-style challenge → EIP-191 signature → a scope-bound JWT that
carries the resolved tier. No cookies — the JWT is client-held and presented via
`Authorization: Bearer`, `X-Realm-Token`, or `?t=` (exactly what `_viewer_role`
already reads). This is the same shape as Lit's session-sig + access-control and
thirdweb's SIWE→JWT, built in-house.

The gap this closes: the existing `/overlord/verify` only issues a token for
PRIVILEGED roles (member/overseer/overlord). It has no notion of a bare
*participant* (any wallet that proves control of an address). This module issues
a session for ANY verified wallet, resolving the tier:

    public  → participant  → member  → overseer  → overlord
    (door)    (verified)     (token)   (mindx.algo) (bankon.eth)

- participant : any wallet that signs the challenge (proves control) — reads docs
- member      : holds the membership token OR is on the courtesy whitelist — reads the book
- overlord    : bankon.eth (the shadow-overlord address) — the realm
- overseer    : mindx.algo (resolved on the Algorand side; EVM path tops at overlord)

Tokens are minted with the existing `issue_overlord_token(address, role, level)`
so `deltaverse.routes._viewer_role` / `verify_overlord_token` validate them
unchanged.
"""
from __future__ import annotations

import os
import time
import secrets
from typing import Any, Dict, Optional

from eth_account import Account
from eth_account.messages import encode_defunct

# ── tier ladder (aligned with overlord/resolver.ROLE_ORDINAL, + participant) ──
TIER_LEVEL = {"public": 0, "participant": 1, "member": 2, "overseer": 3, "overlord": 4}

_NONCE_TTL_S = 600
_nonces: Dict[str, Dict[str, Any]] = {}   # nonce -> {address, message, ts}


def _overlord_address() -> str:
    """bankon.eth — the immutable OVERLORD address (shadow-overlord root)."""
    try:
        from mindx_backend_service.bankon_vault import shadow_overlord as _so
        a = _so._shadow_address()
        if a:
            return a.lower()
    except Exception:
        pass
    return (os.environ.get("MINDX_SHADOW_OVERLORD_ADDRESS")
            or os.environ.get("SHADOW_OVERLORD_ADDRESS")
            or "0x10f7Ee226B16bea7f365Dc1eDEF159Fc1957D169").lower()


def _courtesy_members() -> set:
    """Wallet public keys granted MEMBER as a courtesy (no token needed)."""
    raw = os.environ.get("MINDX_MEMBER_WHITELIST", "")
    return {a.strip().lower() for a in raw.split(",") if a.strip()}


def _prune() -> None:
    now = time.time()
    for n in [k for k, v in _nonces.items() if now - v["ts"] > _NONCE_TTL_S]:
        _nonces.pop(n, None)


def issue_challenge(address: str, *, domain: str = "mindx.pythai.net") -> Dict[str, str]:
    """Mint a single-use, TTL-bound EIP-4361 (SIWE) challenge for ``address``."""
    _prune()
    nonce = secrets.token_hex(16)
    addr = (address or "").strip()
    issued = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    message = (
        f"{domain}\n"
        "Welcome, recognized participant\n"
        f"{addr}\n"
        "Your signature proves your identity.\n\n"
        f"URI: https://{domain}/activity\n"
        "Version: 1\n"
        "Chain ID: 1\n"
        f"Nonce: {nonce}\n"
        f"Issued At: {issued}"
    )
    _nonces[nonce] = {"address": addr.lower(), "message": message, "ts": time.time()}
    return {"nonce": nonce, "message": message}


def _resolve_tier(address: str) -> Dict[str, Any]:
    """Resolve the tier for a VERIFIED address. participant is the floor for any
    proven wallet; member via courtesy/holdings; overlord for bankon.eth."""
    a = (address or "").lower()
    if a == _overlord_address():
        return {"role": "overlord", "level": TIER_LEVEL["overlord"]}
    if a in _courtesy_members():
        return {"role": "member", "level": TIER_LEVEL["member"]}
    # (on-chain holdings check for member could be wired here via overlord.resolver)
    return {"role": "participant", "level": TIER_LEVEL["participant"]}


def verify(address: str, nonce: str, signature: str) -> Dict[str, Any]:
    """Verify a signed challenge and mint a realm-session JWT for the resolved tier.

    Recovers the EIP-191 signer, asserts it equals the claimed address, consumes
    the nonce (single-use), resolves the tier, and issues an overlord-session
    token (validated unchanged by verify_overlord_token / _viewer_role).
    """
    _prune()
    rec = _nonces.get(nonce)
    if rec is None:
        raise ValueError("challenge not found or expired")
    addr = (address or "").strip()
    if addr.lower() != rec["address"]:
        raise ValueError("address does not match the challenge")
    try:
        recovered = Account.recover_message(encode_defunct(text=rec["message"]), signature=signature)
    except Exception as e:
        raise ValueError(f"signature recovery failed: {e}")
    if recovered.lower() != addr.lower():
        raise ValueError("recovered signer does not match address")
    _nonces.pop(nonce, None)   # single-use

    tier = _resolve_tier(addr)
    from mindx_backend_service.overlord.routes import issue_overlord_token
    token = issue_overlord_token(recovered, tier["role"], tier["level"])
    return {"address": recovered, "role": tier["role"], "level": tier["level"],
            "verified": True, "realm_token": token}
