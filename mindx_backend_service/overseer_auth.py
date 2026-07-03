"""OVERSEER auth — Algorand (Pera / Parsec) wallet sign-in → scope-bound OVERSEER JWT.

A signature from the configured mindx.algo address (``MINDX_ALGO_ADDRESS``, or any
Algorand address in ``MINDX_OVERSEER_ADDRESSES``) is recognized as OVERSEER and
unlocks the Algorand deployment suites. Signature verification is in-house Ed25519
over the public key embedded in the Algorand address — no ``algosdk`` dependency.

Reuses the shadow-overlord nonce store + HS256 JWT machinery (``bankon_vault.shadow_overlord``);
OVERSEER is simply a new scope alongside ``SCOPE_AUTH``. The signed challenge embeds a
single-use, 5-minute nonce, so a captured signature cannot be replayed.
"""
from __future__ import annotations

import base64
import hashlib
import os
from typing import Any, Dict

from fastapi import HTTPException

from mindx_backend_service.bankon_vault import shadow_overlord as _so

SCOPE_OVERSEER = "overseer"


def challenge_message(nonce: str) -> str:
    """Canonical OVERSEER-LOGIN message the operator signs with the mindx.algo wallet."""
    return (
        "mindX OVERSEER-LOGIN\n"
        "Sign to prove control of the mindx.algo address.\n"
        f"nonce: {nonce}\n"
        "This grants OVERSEER access to the Algorand deployment suites."
    )


def _b32_no_pad_decode(s: str) -> bytes:
    pad = "=" * ((8 - len(s) % 8) % 8)
    return base64.b32decode(s + pad)


def decode_algorand_address(addr: str) -> bytes:
    """Algorand address (58-char base32) → 32-byte Ed25519 public key, checksum-verified.

    An Algorand address encodes pubkey(32) + checksum(4), where checksum = last 4 bytes of
    SHA-512/256(pubkey). Raises HTTPException(400) on any malformed input.
    """
    a = (addr or "").strip().upper()
    if len(a) != 58:
        raise HTTPException(status_code=400, detail="invalid Algorand address length")
    try:
        raw = _b32_no_pad_decode(a)
    except Exception:
        raise HTTPException(status_code=400, detail="invalid Algorand address encoding")
    if len(raw) != 36:
        raise HTTPException(status_code=400, detail="invalid Algorand address bytes")
    pubkey, checksum = raw[:32], raw[32:]
    try:
        digest = hashlib.new("sha512_256", pubkey).digest()
    except ValueError:  # SHA-512/256 unavailable in this OpenSSL build
        raise HTTPException(status_code=503, detail="sha512_256 unavailable")
    if digest[-4:] != checksum:
        raise HTTPException(status_code=400, detail="Algorand address checksum mismatch")
    return pubkey


def encode_algorand_address(pubkey: bytes) -> str:
    """32-byte Ed25519 public key → 58-char Algorand address (used by the self-test)."""
    digest = hashlib.new("sha512_256", pubkey).digest()
    return base64.b32encode(pubkey + digest[-4:]).decode("ascii").rstrip("=")


def _ed25519_ok(pubkey: bytes, message: bytes, signature: bytes) -> bool:
    try:
        from nacl.signing import VerifyKey
        from nacl.exceptions import BadSignatureError
        try:
            VerifyKey(pubkey).verify(message, signature)
            return True
        except BadSignatureError:
            return False
    except Exception:
        try:
            from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
            from cryptography.exceptions import InvalidSignature
            try:
                Ed25519PublicKey.from_public_bytes(pubkey).verify(signature, message)
                return True
            except InvalidSignature:
                return False
        except Exception:
            return False


def verify_algorand_signature(message: str, signature_b64: str, address: str) -> bool:
    """True iff ``signature_b64`` is a valid Ed25519 signature by ``address`` over ``message``.

    Accepts BOTH the algosdk ``signBytes`` convention (``b"MX"`` domain prefix, used by Pera's
    legacy signing) and a raw-message signature — so Pera and Parsec both verify.
    """
    pubkey = decode_algorand_address(address)
    try:
        sig = base64.b64decode(signature_b64)
    except Exception:
        raise HTTPException(status_code=400, detail="signature not valid base64")
    if len(sig) != 64:
        raise HTTPException(status_code=400, detail="signature must be 64 bytes")
    msg = message.encode("utf-8")
    return _ed25519_ok(pubkey, b"MX" + msg, sig) or _ed25519_ok(pubkey, msg, sig)


def overseer_addresses() -> set:
    """The configured set of Algorand addresses recognized as OVERSEER (uppercased)."""
    out: set = set()
    one = (os.environ.get("MINDX_ALGO_ADDRESS") or "").strip().upper()
    if len(one) == 58:
        out.add(one)
    for a in (os.environ.get("MINDX_OVERSEER_ADDRESSES") or "").split(","):
        a = a.strip().upper()
        if len(a) == 58:  # Algorand addresses only (EVM 0x… overseers handled elsewhere)
            out.add(a)
    return out


def issue_challenge() -> Dict[str, str]:
    """Mint a single-use OVERSEER-LOGIN challenge bound to a fresh nonce."""
    store = _so.get_store()
    nonce = store.issue(SCOPE_OVERSEER, "PENDING", {})
    msg = challenge_message(nonce)
    rec = store._records.get(nonce)
    if rec is not None:                 # bind the nonce-embedding message before the signer sees it
        rec.message = msg
        store._persist()
    return {"nonce": nonce, "message": msg}


def verify_overseer_jwt(token: str) -> Dict[str, Any]:
    """Verify an OVERSEER Bearer JWT: valid HS256 signature + scope=overseer + sub is a configured OVERSEER.

    Reuses shadow_overlord's HS256 secret + pyjwt, but (unlike ``shadow_overlord.verify_jwt``, which is bound
    to the shadow-overlord EVM address) the subject here must be one of the configured Algorand OVERSEER
    addresses. Raises HTTPException on any failure.
    """
    try:
        claims = _so.pyjwt.decode(token, _so._jwt_secret(), algorithms=["HS256"])
    except _so.pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="overseer jwt expired")
    except _so.pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"invalid overseer jwt: {e}")
    if claims.get("scope") != SCOPE_OVERSEER:
        raise HTTPException(status_code=403, detail="not an overseer jwt (scope mismatch)")
    sub = (claims.get("sub") or "").strip().upper()
    if sub not in overseer_addresses():
        raise HTTPException(status_code=403, detail="jwt subject is not an OVERSEER")
    return claims


def consume_overseer_login(nonce: str, signature: str, address: str, wallet: str = "pera") -> Dict[str, Any]:
    """Validate a signed OVERSEER-LOGIN and, on success, return an OVERSEER JWT.

    Steps: lookup nonce (single-use, unexpired) → verify the Ed25519 signature over the STORED
    message → require the address to be a configured OVERSEER → consume the nonce → issue the JWT.
    """
    store = _so.get_store()
    rec = store.lookup(nonce)
    if rec is None:
        raise HTTPException(status_code=409, detail="nonce expired, unknown, or already consumed")
    if rec.scope != SCOPE_OVERSEER:
        raise HTTPException(status_code=403, detail="scope mismatch")
    addr_norm = (address or "").strip().upper()
    if not verify_algorand_signature(rec.message, signature, addr_norm):
        raise HTTPException(status_code=401, detail="invalid Algorand signature")
    allowed = overseer_addresses()
    if not allowed:
        raise HTTPException(status_code=503, detail="MINDX_ALGO_ADDRESS / MINDX_OVERSEER_ADDRESSES not configured")
    if addr_norm not in allowed:
        raise HTTPException(status_code=403, detail="address is not an OVERSEER")
    if not store.consume(nonce):
        raise HTTPException(status_code=409, detail="nonce consumed concurrently")
    tok = _so.issue_jwt(addr_norm, scope=SCOPE_OVERSEER)
    return {"address": addr_norm, "wallet": wallet, **tok}
