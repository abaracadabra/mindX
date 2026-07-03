# ╔══════════════════════════════════════════════════════════════════╗
# ║  BANKON Vault — Shadow-Overlord Auth Tier                       ║
# ║                                                                  ║
# ║  ECDSA-signed challenge → short-lived JWT for the admin UI;     ║
# ║  fresh per-op signatures gate every state-changing endpoint.    ║
# ║                                                                  ║
# ║  See /home/hacker/.claude/plans/splendid-wishing-hejlsberg.md   ║
# ╚══════════════════════════════════════════════════════════════════╝

from __future__ import annotations

import hmac
import json
import os
import secrets
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import jwt as pyjwt
from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi import Depends, Header, HTTPException
from web3 import Web3

# Allowed scopes — any verify must explicitly require one of these.
SCOPE_AUTH = "auth"
SCOPE_CABINET_PROVISION = "cabinet.provision"
SCOPE_CABINET_CLEAR = "cabinet.clear"
SCOPE_VAULT_SIGN = "vault.sign"
SCOPE_RELEASE_KEY = "release.key"

NONCE_TTL_S = 120
JWT_TTL_S = 300

_NONCE_PATH = Path(os.environ.get(
    "SHADOW_NONCES_PATH",
    "data/governance/shadow_nonces.json",
))


@dataclass
class NonceRecord:
    issued_at: float
    scope: str
    message: str
    params: Dict[str, Any] = field(default_factory=dict)
    consumed: bool = False

    def is_expired(self, now: float) -> bool:
        return now - self.issued_at > NONCE_TTL_S


class NonceStore:
    """In-memory nonce store with JSONL persistence.

    Each record binds a nonce to a scope + canonical challenge message + the
    parameters that operation will mutate. Single-use; expires in NONCE_TTL_S.
    """

    def __init__(self, path: Path = _NONCE_PATH):
        self._path = path
        self._records: Dict[str, NonceRecord] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            now = time.time()
            for nonce, payload in raw.items():
                rec = NonceRecord(**payload)
                if not rec.is_expired(now) and not rec.consumed:
                    self._records[nonce] = rec
        except (json.JSONDecodeError, TypeError, ValueError):
            # Corrupt file: start fresh; old nonces are unrecoverable but
            # that just forces re-auth — no security impact.
            self._records = {}

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(
            json.dumps({k: asdict(v) for k, v in self._records.items()}),
            encoding="utf-8",
        )
        os.replace(tmp, self._path)

    def issue(self, scope: str, message: str, params: Dict[str, Any]) -> str:
        self._prune()
        nonce = "0x" + secrets.token_hex(32)
        self._records[nonce] = NonceRecord(
            issued_at=time.time(),
            scope=scope,
            message=message,
            params=params,
        )
        self._persist()
        return nonce

    def lookup(self, nonce: str) -> Optional[NonceRecord]:
        self._prune()
        rec = self._records.get(nonce)
        if rec is None or rec.is_expired(time.time()) or rec.consumed:
            return None
        return rec

    def consume(self, nonce: str) -> bool:
        rec = self._records.get(nonce)
        if rec is None or rec.is_expired(time.time()) or rec.consumed:
            return False
        rec.consumed = True
        self._persist()
        return True

    def _prune(self) -> None:
        now = time.time()
        stale = [k for k, v in self._records.items() if v.is_expired(now)]
        for k in stale:
            self._records.pop(k, None)
        if stale:
            self._persist()


_store: Optional[NonceStore] = None


def get_store() -> NonceStore:
    global _store
    if _store is None:
        _store = NonceStore()
    return _store


def reset_store_for_tests(path: Optional[Path] = None) -> None:
    global _store
    _store = NonceStore(path or _NONCE_PATH)


# ─── canonical challenge message construction ─────────────────────


def build_challenge_message(scope: str, nonce: str, params: Dict[str, Any]) -> str:
    """Canonical, scope-bound message text that the operator signs.

    The shape is human-readable and audit-friendly. The scope tag prevents a
    sig issued for one operation from authorizing another.
    """
    lines = [f"MINDX-SHADOW-OVERLORD scope={scope}", f"nonce: {nonce}"]
    for key in sorted(params):
        lines.append(f"{key}: {params[key]}")
    return "\n".join(lines)


def issue_challenge(scope: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Public: issue a fresh challenge for the given scope.

    Returns {nonce, message, expires_at}. The client signs `message` and
    posts {nonce, signature} to the corresponding op endpoint.
    """
    if scope not in {
        SCOPE_AUTH,
        SCOPE_CABINET_PROVISION,
        SCOPE_CABINET_CLEAR,
        SCOPE_VAULT_SIGN,
        SCOPE_RELEASE_KEY,
    }:
        raise HTTPException(status_code=400, detail=f"unknown scope: {scope}")
    params = params or {}
    store = get_store()
    # Pre-allocate the nonce to interpolate into the message; store *with* the message.
    nonce = "0x" + secrets.token_hex(32)
    message = build_challenge_message(scope, nonce, params)
    store._records[nonce] = NonceRecord(
        issued_at=time.time(), scope=scope, message=message, params=params,
    )
    store._persist()
    return {
        "nonce": nonce,
        "message": message,
        "expires_at": int(time.time()) + NONCE_TTL_S,
    }


# ─── signature verification ───────────────────────────────────────


def _shadow_address() -> str:
    addr = os.environ.get("SHADOW_OVERLORD_ADDRESS", "").strip()
    if not addr:
        raise HTTPException(
            status_code=503,
            detail="SHADOW_OVERLORD_ADDRESS not configured on this server",
        )
    return Web3.to_checksum_address(addr)


def recover_signer(message: str, signature: str) -> str:
    try:
        sig = signature if signature.startswith("0x") else "0x" + signature
        recovered = Account.recover_message(
            encode_defunct(text=message),
            signature=sig,
        )
        return Web3.to_checksum_address(recovered)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"invalid signature: {e}")


def verify_shadow_signature(message: str, signature: str) -> str:
    """Recover the signer of `message` and assert it is the shadow-overlord.

    Returns the recovered checksum address. Raises HTTPException on mismatch.
    """
    recovered = recover_signer(message, signature)
    expected = _shadow_address()
    if not hmac.compare_digest(recovered.lower(), expected.lower()):
        raise HTTPException(status_code=403, detail="not shadow-overlord")
    return recovered


def consume_signed_challenge(
    nonce: str,
    signature: str,
    expected_scope: str,
    expected_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Validate a one-time signed challenge.

    Steps:
      1. Lookup nonce in store; reject if missing/expired/consumed.
      2. Confirm scope == expected_scope.
      3. If expected_params supplied, every key/value must match.
      4. Recover signer from the *stored* message; confirm == shadow-overlord.
      5. Mark nonce consumed (single-use).

    Returns the NonceRecord's params on success (caller can rely on them).
    """
    store = get_store()
    rec = store.lookup(nonce)
    if rec is None:
        raise HTTPException(status_code=409, detail="nonce expired, unknown, or already consumed")
    if rec.scope != expected_scope:
        raise HTTPException(
            status_code=403,
            detail=f"scope mismatch: nonce was issued for {rec.scope!r}, this endpoint requires {expected_scope!r}",
        )
    if expected_params is not None:
        for k, v in expected_params.items():
            if rec.params.get(k) != v:
                raise HTTPException(
                    status_code=400,
                    detail=f"params mismatch on {k!r}",
                )
    verify_shadow_signature(rec.message, signature)
    if not store.consume(nonce):  # race-safe re-check
        raise HTTPException(status_code=409, detail="nonce was consumed concurrently")
    return dict(rec.params)


# ─── JWT issue / verify ───────────────────────────────────────────


def _jwt_secret() -> str:
    secret = os.environ.get("SHADOW_JWT_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(
            status_code=503,
            detail="SHADOW_JWT_SECRET not configured (need 32+ chars)",
        )
    return secret


def issue_jwt(addr: str, scope: str = SCOPE_AUTH, jti: Optional[str] = None) -> Dict[str, Any]:
    now = int(time.time())
    claims = {
        "sub": addr,
        "scope": scope,
        "jti": jti or secrets.token_hex(16),
        "iat": now,
        "exp": now + JWT_TTL_S,
    }
    token = pyjwt.encode(claims, _jwt_secret(), algorithm="HS256")
    return {"jwt": token, "exp": claims["exp"]}


def verify_jwt(token: str, required_scope: Optional[str] = None) -> Dict[str, Any]:
    try:
        claims = pyjwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except pyjwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="jwt expired")
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"invalid jwt: {e}")
    sub = claims.get("sub", "")
    if not hmac.compare_digest(sub.lower(), _shadow_address().lower()):
        raise HTTPException(status_code=403, detail="jwt subject is not shadow-overlord")
    if required_scope is not None and claims.get("scope") != required_scope:
        raise HTTPException(status_code=403, detail="jwt scope mismatch")
    return claims


def require_shadow_jwt(required_scope: Optional[str] = None) -> Callable:
    """FastAPI dep factory. Enforces a valid Bearer JWT, optionally scope-bound."""

    async def _dep(authorization: str = Header(default="")) -> Dict[str, Any]:
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        return verify_jwt(authorization[7:], required_scope=required_scope)

    return _dep


# ─── audit emit (best-effort wrapper) ─────────────────────────────


async def emit_shadow_audit(action: str, actor: str, payload: Dict[str, Any]) -> None:
    """Emit an admin.shadow_overlord_action catalogue event (best effort).

    Catalogue events are pure observability — failure to emit must NEVER
    block the privileged op.
    """
    try:
        from agents.catalogue.events import emit_catalogue_event

        await emit_catalogue_event(
            kind="admin.shadow_overlord_action",
            actor=actor,
            payload={"action": action, **payload, "ts": int(time.time())},
            source_log="bankon_vault.shadow_overlord",
        )
    except Exception:
        # Audit failures should not break the request flow.
        pass
