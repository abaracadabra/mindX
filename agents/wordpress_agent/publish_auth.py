# SPDX-License-Identifier: Apache-2.0
"""Public, wallet-authorized publish flow for rage.pythai.net.

Caller presents a wallet address → server issues a scoped challenge → caller signs
(EIP-191) → server verifies the recovered address matches the request, checks the
``WORDPRESS_PUBLISHER_ADDRESSES`` allowlist, and forwards the publish to
``AuthorAgent.publish_to_rage`` (which routes through the wordpress-agent service,
which unlocks the BANKON vault on-demand for the WP API key — see vault_creds.py).

Reuses the existing ``shadow_overlord`` nonce machinery but uses a *generic*
EIP-191 signer recovery (``recover_signer``) so any allowlisted wallet — not only
the shadow-overlord — can authorize a publish. Each published post carries both
``meta._mindx_authorized_by`` (the external requester) and ``meta._mindx_signer``
(wordpress.agent's own provenance signature, stamped by the wordpress-agent).
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from mindx_backend_service.bankon_vault.shadow_overlord import (
    NONCE_TTL_S,
    build_challenge_message,
    get_store,
    recover_signer,
)

SCOPE_WORDPRESS_PUBLISH = "wordpress.publish"
ALLOWLIST_ENV = "WORDPRESS_PUBLISHER_ADDRESSES"

logger = logging.getLogger("wordpress_agent.publish_auth")

router = APIRouter(prefix="/publish/rage", tags=["publish"])


# ─── schemas ──────────────────────────────────────────────────────


class ChallengeRequest(BaseModel):
    wallet_address: str = Field(..., min_length=42, max_length=42, description="0x-EOA")
    title: str = Field(..., min_length=1)
    content_sha256: str = Field(..., min_length=66, max_length=66, description="0x + 64 hex")


class ChallengeResponse(BaseModel):
    nonce: str
    message: str
    expires_at: int


class AuthorizeRequest(BaseModel):
    wallet_address: str = Field(..., min_length=42, max_length=42)
    nonce: str = Field(..., min_length=66, max_length=66)
    signature: str = Field(..., min_length=132)  # 0x + 130 hex (65 bytes)
    title: str = Field(..., min_length=1)
    status: str = Field(default="draft")  # draft | publish | future | pending | private
    doc_path: Optional[str] = None
    markdown: Optional[str] = None
    html: Optional[str] = None
    excerpt: Optional[str] = None
    slug: Optional[str] = None


class WordpressResult(BaseModel):
    post_id: int
    url: str
    status: str
    slug: str
    date_gmt: str


class AuthorizeResponse(BaseModel):
    status: str
    authorized_by: str
    wordpress: WordpressResult


# ─── helpers ──────────────────────────────────────────────────────


def _allowlist() -> set[str]:
    raw = os.environ.get(ALLOWLIST_ENV, "")
    return {a.strip().lower() for a in raw.split(",") if a.strip()}


def _normalize_addr(addr: str) -> str:
    if not (addr.startswith("0x") and len(addr) == 42):
        raise HTTPException(status_code=400, detail="wallet_address must be a 0x-prefixed 20-byte EOA")
    return addr.lower()


def _render_html(req: AuthorizeRequest) -> str:
    """Resolve the content source — exactly one of doc_path / markdown / html — to HTML."""
    sources = [s for s in (req.doc_path, req.markdown, req.html) if s is not None]
    if len(sources) != 1:
        raise HTTPException(status_code=400, detail="provide exactly one of: doc_path, markdown, html")

    if req.html is not None:
        return req.html

    # Lazy import: main_service is heavy and circular-ish if imported at module top.
    from mindx_backend_service.main_service import _render_md  # type: ignore
    from utils.config import PROJECT_ROOT

    if req.doc_path:
        safe = (PROJECT_ROOT / "docs" / req.doc_path).resolve()
        docs_root = (PROJECT_ROOT / "docs").resolve()
        if docs_root not in safe.parents and safe != docs_root:
            raise HTTPException(status_code=400, detail="doc_path must resolve under docs/")
        if not safe.is_file():
            raise HTTPException(status_code=404, detail=f"docs/{req.doc_path} not found")
        md_text = safe.read_text(encoding="utf-8")
    else:
        md_text = req.markdown or ""
    return _render_md(md_text)


def _content_sha256_hex(html: str) -> str:
    return "0x" + hashlib.sha256(html.encode("utf-8")).hexdigest()


def _emit_audit(event: dict[str, Any]) -> None:
    """Best-effort: mirror an event into the catalogue. Never raises."""
    try:
        from agents.catalogue.log import append_event  # type: ignore
    except Exception:
        try:
            from agents.catalogue import log as _cat  # type: ignore
            append_event = getattr(_cat, "append_event", None) or getattr(_cat, "write_event", None)
        except Exception:
            append_event = None
    if append_event is None:
        logger.info("audit: %s", event)
        return
    try:
        append_event(event)
    except Exception as e:  # pragma: no cover
        logger.warning(f"catalogue append_event failed: {e}")


# Lightweight diagnostics counter — read by /diagnostics/live
_last_authorized_by: Optional[str] = None


def get_last_authorized_by() -> Optional[str]:
    return _last_authorized_by


# ─── routes ───────────────────────────────────────────────────────


@router.post("/challenge", response_model=ChallengeResponse, summary="Issue a publish-authorization challenge")
async def issue_publish_challenge(req: ChallengeRequest) -> ChallengeResponse:
    wallet = _normalize_addr(req.wallet_address)
    if not (req.content_sha256.startswith("0x") and len(req.content_sha256) == 66):
        raise HTTPException(status_code=400, detail="content_sha256 must be 0x + 64 hex")
    params = {
        "wallet": wallet,
        "title": req.title,
        "content_sha256": req.content_sha256.lower(),
    }
    store = get_store()
    # Pre-allocate nonce so it can be interpolated into the message.
    import secrets as _s
    nonce = "0x" + _s.token_hex(32)
    message = build_challenge_message(SCOPE_WORDPRESS_PUBLISH, nonce, params)
    from mindx_backend_service.bankon_vault.shadow_overlord import NonceRecord
    store._records[nonce] = NonceRecord(
        issued_at=time.time(),
        scope=SCOPE_WORDPRESS_PUBLISH,
        message=message,
        params=params,
    )
    store._persist()
    return ChallengeResponse(nonce=nonce, message=message, expires_at=int(time.time()) + NONCE_TTL_S)


@router.post("/authorize", response_model=AuthorizeResponse, summary="Verify the signed challenge and publish")
async def authorize_publish(req: AuthorizeRequest) -> AuthorizeResponse:
    global _last_authorized_by

    wallet = _normalize_addr(req.wallet_address)

    # 1. Render content, compute hash.
    html = _render_html(req)
    content_sha256 = _content_sha256_hex(html).lower()

    # 2. Lookup the nonce; verify scope + bound params (wallet/title/content hash).
    store = get_store()
    rec = store.lookup(req.nonce)
    if rec is None:
        raise HTTPException(status_code=409, detail="nonce expired, unknown, or already consumed")
    if rec.scope != SCOPE_WORDPRESS_PUBLISH:
        raise HTTPException(status_code=403, detail=f"scope mismatch: nonce was issued for {rec.scope!r}")
    if rec.params.get("wallet") != wallet:
        raise HTTPException(status_code=400, detail="wallet mismatch on nonce")
    if rec.params.get("title") != req.title:
        raise HTTPException(status_code=400, detail="title mismatch on nonce")
    if rec.params.get("content_sha256") != content_sha256:
        raise HTTPException(status_code=400, detail="content hash differs from what was signed")

    # 3. Verify signature recovers to the caller-presented wallet (not shadow-overlord).
    recovered = recover_signer(rec.message, req.signature)
    if recovered.lower() != wallet:
        raise HTTPException(status_code=401, detail=f"signature recovered to {recovered}, expected {wallet}")

    # 4. Allowlist check (empty allowlist ⇒ deny all).
    allowlist = _allowlist()
    if wallet not in allowlist:
        raise HTTPException(status_code=403, detail=f"{wallet} is not in {ALLOWLIST_ENV}")

    # 5. Burn the nonce.
    if not store.consume(req.nonce):
        raise HTTPException(status_code=409, detail="nonce was consumed concurrently")

    # 6. Hand to AuthorAgent → wordpress-agent → (vault decrypt on demand) → WordPress.
    try:
        from agents.author_agent import AuthorAgent  # type: ignore
        author = await AuthorAgent.get_instance()
        result = await author.publish_to_rage(
            title=req.title,
            content_html=html,
            status=req.status,
            excerpt=req.excerpt,
            slug=req.slug,
            meta={"_mindx_authorized_by": wallet, "_mindx_content_hash": content_sha256},
        )
    except Exception as e:
        logger.error(f"publish_to_rage raised: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"publish_to_rage failed: {e}")
    if result is None:
        raise HTTPException(status_code=502, detail="wordpress-agent unreachable or refused the post")

    _last_authorized_by = wallet
    _emit_audit({
        "event": "wordpress.publish.authorize",
        "wallet": wallet,
        "title": req.title,
        "status": req.status,
        "content_sha256": content_sha256,
        "post_id": result.get("post_id"),
        "url": result.get("url"),
        "ts": int(time.time()),
    })

    return AuthorizeResponse(
        status="ok",
        authorized_by=wallet,
        wordpress=WordpressResult(
            post_id=int(result["post_id"]),
            url=str(result["url"]),
            status=str(result["status"]),
            slug=str(result["slug"]),
            date_gmt=str(result["date_gmt"]),
        ),
    )


__all__ = ["router", "SCOPE_WORDPRESS_PUBLISH", "get_last_authorized_by"]
