# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""FastAPI HTTP server exposing WordpressAgent to AuthorAgent over loopback.

Credentials policy: WP API key + wordpress.agent wallet live in the BANKON vault under
``context="wordpress.agent.keys"`` (see ``vault_creds.py``). Every request opens the
vault, retrieves what it needs, and locks immediately — the secret is in memory only
for the duration of the request. The pydantic-settings ``Settings()`` env path remains
as a *dev-only* fallback (vault unavailable).
"""
from __future__ import annotations

import logging
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, AsyncIterator

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field

from .agent import (
    AuthenticationError,
    MediaUploadError,
    PublishError,
    WordpressAgent,
)
from .config import Settings
from .vault_creds import load_wp_settings_from_vault, sha256_hex, sign_with_agent_wallet

logger = logging.getLogger("wordpress_agent.server")


class PublishRequest(BaseModel):
    """Schema for the /publish endpoint."""

    title: str = Field(..., min_length=1, description="Post title.")
    content: str = Field(..., min_length=1, description="Post HTML or block content.")
    status: str = Field(default="publish")
    date: datetime | None = Field(default=None, description="Scheduled publish time.")
    categories: list[int] | None = None
    tags: list[int] | None = None
    featured_media: int | None = None
    excerpt: str | None = None
    slug: str | None = None
    author: int | None = None
    meta: dict[str, Any] | None = None


class PublishResponse(BaseModel):
    post_id: int
    url: str
    status: str
    slug: str
    date_gmt: str


class MediaResponse(BaseModel):
    media_id: int
    url: str
    mime_type: str


class HealthResponse(BaseModel):
    ok: bool
    status_code: int
    base_url: str
    user: str
    wp_user_id: int | None = None


def _resolve_settings() -> Settings:
    """Vault first; pydantic-settings env fallback for local dev.

    Vault wins whenever it can be unlocked AND contains the wordpress.agent
    namespace. Otherwise we fall back to ``Settings()`` so unit tests and local
    runs still work with ``WP_*`` env vars.
    """
    vs = load_wp_settings_from_vault()
    if vs is not None:
        return vs
    return Settings()  # type: ignore[call-arg]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # No long-lived agent: credentials are read per-request, then re-locked.
    src = "vault" if load_wp_settings_from_vault() is not None else "env-fallback"
    logger.info("WordPress.agent server starting (credential source: %s)", src)
    yield
    logger.info("WordPress.agent server stopped cleanly")


app = FastAPI(
    title="WordPress.agent",
    description="Agnostic publishing tool. Single endpoint family: publish + media.",
    version="0.2.0",
    lifespan=lifespan,
)


@app.get("/healthz", response_model=HealthResponse)
async def healthz() -> HealthResponse:
    try:
        settings = _resolve_settings()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"no credentials available: {exc}") from exc
    async with WordpressAgent(settings) as agent:
        try:
            result = await agent.health_check()
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    return HealthResponse(**result)


@app.post("/publish", response_model=PublishResponse)
async def publish(req: PublishRequest) -> PublishResponse:
    try:
        settings = _resolve_settings()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"no credentials available: {exc}") from exc

    # Provenance signature: wordpress.agent stamps each post with a signature over
    # sha256(content) recovering to its vault-stored address. Best-effort — if the
    # wallet isn't provisioned, we publish without it. (AuthorAgent already attaches
    # ``meta._mindx_content_hash``; we add ``_mindx_signature`` + ``_mindx_signer``.)
    meta = dict(req.meta or {})
    content_hash = sha256_hex(req.content)
    meta.setdefault("_mindx_content_hash", content_hash)
    signed = sign_with_agent_wallet(content_hash)
    if signed is not None:
        sig, addr = signed
        meta["_mindx_signature"] = sig
        meta["_mindx_signer"] = addr

    async with WordpressAgent(settings) as agent:
        try:
            result = await agent.publish(
                title=req.title,
                content=req.content,
                status=req.status,  # type: ignore[arg-type]
                date=req.date,
                categories=req.categories,
                tags=req.tags,
                featured_media=req.featured_media,
                excerpt=req.excerpt,
                slug=req.slug,
                author=req.author,
                meta=meta,
            )
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except PublishError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PublishResponse(
        post_id=result.post_id,
        url=result.url,
        status=result.status,
        slug=result.slug,
        date_gmt=result.date_gmt,
    )


@app.post("/media", response_model=MediaResponse)
async def upload_media(
    file: UploadFile = File(...),
    alt_text: str = Form(default=""),
    caption: str = Form(default=""),
    title: str | None = Form(default=None),
) -> MediaResponse:
    try:
        settings = _resolve_settings()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"no credentials available: {exc}") from exc
    suffix = Path(file.filename or "upload.bin").suffix or ".bin"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp_path = Path(tmp.name)
        tmp.write(await file.read())
    try:
        async with WordpressAgent(settings) as agent:
            result = await agent.upload_media(
                tmp_path,
                alt_text=alt_text,
                caption=caption,
                title=title,
            )
    except MediaUploadError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    return MediaResponse(
        media_id=result.media_id,
        url=result.url,
        mime_type=result.mime_type,
    )


def run() -> None:
    """CLI entry point: launch uvicorn with the configured host/port.

    We try to load Settings just for ``server_host``/``server_port``; both default to
    safe values (127.0.0.1:8765) when the vault path provides them too.
    """
    import uvicorn

    try:
        settings = _resolve_settings()
    except Exception:
        settings = Settings()  # type: ignore[call-arg]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    uvicorn.run(
        "agents.wordpress_agent.server:app",
        host=settings.server_host,
        port=settings.server_port,
        log_level="info",
    )


if __name__ == "__main__":
    run()
