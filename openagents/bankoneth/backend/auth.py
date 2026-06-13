# SPDX-License-Identifier: Apache-2.0
"""SIWE-style login that mints a tier-scoped session JWT.

Flow (adapted from shadow-overlord's challenge→sign→recover):
  POST /auth/challenge {address}        -> {nonce, message}
  (wallet personal_sign the message)
  POST /auth/verify {address, nonce, signature, label?}
                                        -> {tier, token, names?}  (+ httponly cookie)

The JWT is the ONLY thing the gate trusts; the tier inside it is resolved
on-chain at verify time (tiers.resolve_tier), never supplied by the client.
"""
from __future__ import annotations

import os
import secrets
import time
from typing import Optional

import jwt as pyjwt
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from .tiers import resolve_tier

COOKIE = "bankon_session"
TTL_S = 24 * 3600
NONCE_TTL_S = 300

# nonce -> (issued_at, address)
_nonces: dict[str, tuple[float, str]] = {}


def _secret() -> str:
    s = os.environ.get("BANKON_GATE_SECRET") or os.environ.get("SHADOW_JWT_SECRET")
    if not s:
        # Dev fallback — sessions survive within a process. Set BANKON_GATE_SECRET in prod.
        s = _DEV_SECRET
    if len(s) < 32:
        raise RuntimeError("BANKON_GATE_SECRET/SHADOW_JWT_SECRET must be >=32 chars")
    return s


_DEV_SECRET = "bankon-dev-" + secrets.token_hex(16)  # per-process; prod must set env


def _prune() -> None:
    now = time.time()
    for n in [n for n, (t, _) in _nonces.items() if now - t > NONCE_TTL_S]:
        _nonces.pop(n, None)


def issue_session_jwt(address: str, tier: str, names: Optional[list[str]] = None) -> str:
    now = int(time.time())
    claims = {"sub": address, "tier": tier, "iat": now, "exp": now + TTL_S}
    if names:
        claims["names"] = names[:25]
    return pyjwt.encode(claims, _secret(), algorithm="HS256")


def verify_session(token: str) -> Optional[dict]:
    try:
        return pyjwt.decode(token, _secret(), algorithms=["HS256"])
    except Exception:
        return None


def session_from_request(request: Request) -> Optional[dict]:
    tok = request.cookies.get(COOKIE)
    if not tok:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            tok = auth[7:].strip()
    return verify_session(tok) if tok else None


router = APIRouter(prefix="/auth", tags=["bankon-gate"])


class ChallengeReq(BaseModel):
    address: str


class VerifyReq(BaseModel):
    address: str
    nonce: str
    signature: str
    label: Optional[str] = None


def _challenge_message(address: str, nonce: str) -> str:
    return (
        "bankon.eth — sign in to prove wallet control.\n"
        f"address: {address}\n"
        f"nonce: {nonce}\n"
        "This signature is gas-free and grants no token approvals."
    )


@router.post("/challenge")
async def challenge(req: ChallengeReq):
    _prune()
    nonce = secrets.token_hex(16)
    _nonces[nonce] = (time.time(), req.address.lower())
    return {"nonce": nonce, "message": _challenge_message(req.address, nonce)}


@router.post("/verify")
async def verify(req: VerifyReq, response: Response):
    _prune()
    rec = _nonces.pop(req.nonce, None)
    if rec is None:
        raise HTTPException(409, "nonce expired or unknown")
    _, addr_lower = rec
    if addr_lower != req.address.lower():
        raise HTTPException(400, "address mismatch")
    message = _challenge_message(req.address, req.nonce)
    try:
        recovered = Account.recover_message(encode_defunct(text=message), signature=req.signature)
    except Exception:
        raise HTTPException(400, "bad signature")
    if recovered.lower() != req.address.lower():
        raise HTTPException(401, "signature does not match address")

    info = resolve_tier(recovered, label=req.label)
    token = issue_session_jwt(info["address"], info["tier"], info.get("names"))
    response.set_cookie(
        COOKIE, token, max_age=TTL_S, httponly=True, samesite="lax", secure=False
    )
    # Holding a *.bankon.eth (member) or owning bankon.eth (admin) is a signed,
    # on-chain proof agenticplace.pythai.net trusts to grant verified privilege.
    verified = info["tier"] in ("member", "admin")
    return {
        "tier": info["tier"], "token": token, "address": info["address"],
        "names": info.get("names", []),
        "agenticplace_verified": verified,
        "agenticplace": "https://agenticplace.pythai.net/marketspace" if verified else None,
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE)
    return {"ok": True}


@router.get("/me")
async def me(request: Request):
    claims = session_from_request(request)
    if not claims:
        return {"tier": "visitor", "agenticplace_verified": False}
    tier = claims.get("tier")
    return {
        "tier": tier, "address": claims.get("sub"), "names": claims.get("names", []),
        "agenticplace_verified": tier in ("member", "admin"),
    }


async def require_admin_tier(request: Request) -> dict:
    """FastAPI dependency: 403 unless the session is the admin tier (owns bankon.eth).
    Injected into the bankon-vault routes so they are self-protected behind the gate."""
    claims = session_from_request(request)
    if not claims or claims.get("tier") != "admin":
        raise HTTPException(status_code=403, detail="admin tier (bankon.eth owner) required")
    return claims
