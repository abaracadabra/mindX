# SPDX-License-Identifier: Apache-2.0
"""
overlord.routes — the mindX overlord/overseer login surface. Additive and gated
by MINDX_OVERLORD_ENABLED; the existing /admin/shadow/* gate is untouched.

  POST /overlord/challenge {address, scope?} → {nonce, message, exp}
  POST /overlord/verify    {nonce, signature} → {role, level, privileged, ...,
                                                  overlord_token, jwt?}

Token policy (the safety invariant): the real shadow-overlord JWT (which passes
require_shadow_jwt and gates the vault / cabinet / key release — all DESTRUCTIVE,
overlord-only) is minted ONLY for the `overlord` role. overseer/member receive a
separate `overlord.session` token that is NOT subject-locked to the overlord and
does NOT pass require_shadow_jwt — so the additive overlord model can never
escalate a member into the destructive admin gate.
"""
from __future__ import annotations

import hmac
import os
import secrets
import time
from typing import Any, Dict, Optional

import jwt as pyjwt
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .config import is_enabled, load_config
from .resolver import can, resolve_privilege

overlord_router = APIRouter(prefix="/overlord", tags=["overlord"])

OVERLORD_SESSION_SCOPE = "overlord.session"
_SESSION_TTL_S = 300


# ── overlord-session token (distinct from the shadow JWT) ───────────────────
def _overlord_secret() -> str:
    s = os.environ.get("MINDX_OVERLORD_JWT_SECRET") or os.environ.get("SHADOW_JWT_SECRET", "")
    if len(s) < 32:
        raise HTTPException(status_code=503, detail="overlord JWT secret not configured (32+ chars)")
    return s


def issue_overlord_token(address: str, role: str, level: int) -> str:
    now = int(time.time())
    claims = {
        "sub": address,
        "role": role,
        "level": level,
        "scope": OVERLORD_SESSION_SCOPE,
        "jti": secrets.token_hex(16),
        "iat": now,
        "exp": now + _SESSION_TTL_S,
    }
    return pyjwt.encode(claims, _overlord_secret(), algorithm="HS256")


def verify_overlord_token(token: str) -> Dict[str, Any]:
    try:
        claims = pyjwt.decode(token, _overlord_secret(), algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="overlord token expired")
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"invalid overlord token: {e}")
    if claims.get("scope") != OVERLORD_SESSION_SCOPE:
        raise HTTPException(status_code=403, detail="not an overlord session token")
    return claims


# ── challenge / verify ──────────────────────────────────────────────────────
class ChallengeReq(BaseModel):
    address: str
    scope: Optional[str] = None


class VerifyReq(BaseModel):
    nonce: str
    signature: str


def _build_message(domain: str, address: str, scope: str, nonce: str,
                   issued: int, exp: int) -> str:
    # Matches openagents/overlord/src/identity.ts buildChallenge exactly so the
    # TS frontend preview and this server agree on the signed bytes.
    return "\n".join([
        "OVERLORD-LOGIN",
        f"domain: {domain}",
        f"wallet: {address}",
        f"scope: {scope}",
        f"nonce: {nonce}",
        f"issued_at: {issued}",
        f"exp: {exp}",
    ])


async def _chronos_now() -> tuple[Optional[int], Dict[str, Any]]:
    """Promised time from chronos.agent. Degrades to local clock (offline)."""
    try:
        from mindx_backend_service.main_service import _get_chronos  # lazy: avoid cycle
        chronos = await _get_chronos()
        pt = (await chronos.now()).as_dict()
        unix = int(float(str(pt.get("unix_18dp", "0")).split(".")[0]))
        return unix, {
            "consensus": pt.get("consensus", "offline"),
            "promised_by": pt.get("promised_by", "chronos.agent"),
            "confidence_ms": pt.get("confidence_ms"),
        }
    except Exception:
        return int(time.time()), {"consensus": "offline", "promised_by": "local"}


@overlord_router.post("/challenge", summary="Issue an overlord login challenge")
async def overlord_challenge(req: ChallengeReq) -> Dict[str, Any]:
    if not is_enabled():
        raise HTTPException(status_code=404, detail="overlord model disabled")
    from eth_utils import is_address, to_checksum_address
    if not is_address(req.address):
        raise HTTPException(status_code=400, detail="invalid wallet address")
    cfg = load_config()
    address = to_checksum_address(req.address)
    scope = (req.scope or cfg.domain).strip()

    # Reuse the shadow NonceStore for single-use, TTL'd replay protection.
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        get_store, NonceRecord, NONCE_TTL_S,
    )
    nonce = "0x" + secrets.token_hex(32)
    issued = int(time.time())
    exp = issued + NONCE_TTL_S
    message = _build_message(cfg.domain, address, scope, nonce, issued, exp)
    store = get_store()
    store._records[nonce] = NonceRecord(
        issued_at=time.time(), scope=OVERLORD_SESSION_SCOPE, message=message,
        params={"address": address, "scope": scope},
    )
    store._persist()
    return {"nonce": nonce, "message": message, "exp": exp}


@overlord_router.post("/verify", summary="Verify signature → resolve overlord privilege")
async def overlord_verify(req: VerifyReq) -> Dict[str, Any]:
    if not is_enabled():
        raise HTTPException(status_code=404, detail="overlord model disabled")
    from mindx_backend_service.bankon_vault.shadow_overlord import (
        get_store, issue_jwt, emit_shadow_audit, SCOPE_AUTH,
    )
    store = get_store()
    rec = store.lookup(req.nonce)
    if rec is None or rec.scope != OVERLORD_SESSION_SCOPE:
        raise HTTPException(status_code=401, detail="challenge not found or expired")
    address = str(rec.params.get("address", ""))
    if not store.consume(req.nonce):  # single-use
        raise HTTPException(status_code=409, detail="challenge already consumed")

    now_unix, chronos = await _chronos_now()
    cfg = load_config()
    priv = await resolve_privilege(
        address, rec.message, req.signature, cfg, now_unix=now_unix, chronos=chronos
    )

    # The real shadow-overlord admin session is minted ONLY for the overlord role
    # (sub == SHADOW_OVERLORD_ADDRESS, so it is identical to today's gate).
    shadow_jwt: Optional[str] = None
    if priv["role"] == "overlord":
        shadow_jwt = issue_jwt(priv["address"], scope=SCOPE_AUTH)["jwt"]

    # All privileged roles get an overlord-session token (role/level-carrying,
    # NOT the shadow JWT → cannot pass the destructive overlord-only gate).
    overlord_token: Optional[str] = None
    if priv["privileged"]:
        overlord_token = issue_overlord_token(priv["address"], priv["role"], priv["level"])

    await emit_shadow_audit(
        "overlord.verify", priv["address"],
        {"role": priv["role"], "level": priv["level"], "reason": priv["reason"]},
    )
    return {**priv, "overlord_token": overlord_token, "jwt": shadow_jwt}


@overlord_router.get("/config", summary="Public overlord config (no secrets)")
async def overlord_config() -> Dict[str, Any]:
    if not is_enabled():
        raise HTTPException(status_code=404, detail="overlord model disabled")
    cfg = load_config()
    h = cfg.holding
    return {
        "enabled": True,
        "domain": cfg.domain,
        "overlord": cfg.overlord,
        "overseers": list(cfg.overseers),
        "holding": None if not h else {
            "chain_id": h.chain_id, "token": h.token, "standard": h.standard,
            "threshold": str(h.threshold), "decimals": h.decimals,
            "level_bands": [
                {"level": b.level, "min_amount": str(b.min_amount), "min_tenure_sec": b.min_tenure_sec}
                for b in h.level_bands
            ],
        },
    }
