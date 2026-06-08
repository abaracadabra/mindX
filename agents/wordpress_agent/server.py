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
from fastapi.responses import PlainTextResponse
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
    post_id: int | None = None  # update an existing post in place (None = create)


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


class GateRequest(BaseModel):
    """Schema for the /gate endpoint — a DeltaVerse.gate.event.

    Crossing the DeltaVerse turnstile creates a NeuralNode *room*
    (BubbleRoomV4.mintRoom) and a *bubbleroom* (BubbleRoomSpawn.spawnFromRoom)
    on Polygon. Fails CLOSED: if the contracts aren't deployed / no RPC / no
    spawner key, the gate is recorded as ``blocked`` and nothing is broadcast.
    """

    theme: str = Field(..., min_length=1, description="Room theme (e.g. article title).")
    origin_event: str = Field(..., min_length=1, description="What opened the gate, e.g. 'publication:<slug>'.")
    metadata_uri: str = Field(default="", description="Room metadata URI (post URL or IPFS CID).")
    chain_id: int = Field(default=137, description="Target chain (137 = Polygon mainnet).")
    participants: list[str] = Field(default_factory=list)
    roles: list[int] = Field(default_factory=list)
    is_private: bool = False
    room_type: int = 0
    storage_cid: str = ""
    ai_seed: str = "mindX"
    tone: str = "genesis"
    seed_mutation: str = "emergence"
    evolves: bool = True
    actor_wallet: str | None = None


class GateResponse(BaseModel):
    ok: bool
    blocked: bool = False
    reason: str | None = None
    chain_id: int
    room_id: int | None = None
    bubbleroom_id: int | None = None
    room_tx: str | None = None
    bubbleroom_tx: str | None = None
    spawner: str | None = None
    links: dict[str, str] = Field(default_factory=dict)


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
                post_id=req.post_id,
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


@app.get("/post/{post_id}")
async def get_post(post_id: int) -> dict:
    """Confirm a publication straight from WordPress (authoritative read-back).

    AuthorAgent publishes, then calls this to verify status/link/slug. Returns
    the live WP record (id, status, link, slug, title, dates, excerpt).
    """
    try:
        settings = _resolve_settings()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"no credentials available: {exc}") from exc
    async with WordpressAgent(settings) as agent:
        try:
            return await agent.get_post(post_id)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/catalogue")
async def catalogue(statuses: str | None = None) -> dict:
    """Complete index catalogue of all publishings on the target (rage.pythai.net).

    ``statuses`` is an optional comma list (default: all indexed statuses incl.
    drafts/private — requires auth). Returns host, counts-by-status, and a
    newest-first list of post records.
    """
    try:
        settings = _resolve_settings()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"no credentials available: {exc}") from exc
    status_tuple = tuple(s.strip() for s in statuses.split(",") if s.strip()) if statuses else None
    async with WordpressAgent(settings) as agent:
        try:
            return await agent.build_catalogue(statuses=status_tuple)
        except AuthenticationError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt() -> str:
    """Render an llms.txt ingestion map from the live catalogue (published posts).

    This is the wordpress.tool's *candidate* map (deterministic, byte-stable).
    The canonical /llms.txt on rage.pythai.net is served by the host plugin;
    use ``/llms.txt/report`` to diff this candidate against the live file.
    """
    try:
        settings = _resolve_settings()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"no credentials available: {exc}") from exc
    from .catalogue import Catalogue, PostRecord, render_catalogue_llms_txt
    async with WordpressAgent(settings) as agent:
        cat_dict = await agent.build_catalogue()
    cat = Catalogue(
        host=cat_dict["host"],
        generated_gmt=cat_dict["generated_gmt"],
        posts=[PostRecord(**{k: p[k] for k in (
            "id", "status", "slug", "title", "link", "date_gmt", "modified_gmt", "excerpt"
        )}) for p in cat_dict["posts"]],
    )
    return render_catalogue_llms_txt(cat)


@app.get("/llms.txt/report")
async def llms_txt_report() -> dict:
    """Full llms.txt interaction: catalogue + rendered candidate + live fetch + diff."""
    try:
        settings = _resolve_settings()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"no credentials available: {exc}") from exc
    async with WordpressAgent(settings) as agent:
        try:
            return await agent.llms_txt_report()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=502, detail=str(exc)) from exc


class SoundCloudEmbedRequest(BaseModel):
    """Schema for /soundcloud/embed — mint a player iframe for a track or set.

    Supply exactly one of ``playlist_id``, ``track_id``, ``permalink``, or
    ``album`` (a known-album key: ``takit`` / ``music4robots2dance2``).
    """

    album: str | None = Field(default=None, description="Known album key.")
    playlist_id: int | str | None = None
    track_id: int | str | None = None
    permalink: str | None = Field(default=None, description="Public soundcloud.com URL.")
    color: str = Field(default="ff5500")
    height: int | None = None
    visual: bool = False
    auto_play: bool = False
    hide_related: bool = False
    show_comments: bool = True
    show_user: bool = True
    show_reposts: bool = False
    show_teaser: bool = True
    # Attribution (optional; album key supplies its own).
    author_name: str | None = None
    author_url: str | None = None
    title: str | None = None
    title_url: str | None = None


@app.post("/soundcloud/embed", response_class=PlainTextResponse)
async def soundcloud_embed(req: SoundCloudEmbedRequest) -> str:
    """Render SoundCloud embed HTML (iframe + attribution). Pure — no auth/network.

    This is the wordpress.tool's audio-embed surface: AuthorAgent and the
    music4robots2dance2 plugin call it to mint consistent players. Returns the
    HTML blob ready to drop into post content.
    """
    from . import soundcloud as sc

    flags = dict(
        color=req.color,
        auto_play=req.auto_play,
        visual=req.visual,
        hide_related=req.hide_related,
        show_comments=req.show_comments,
        show_user=req.show_user,
        show_reposts=req.show_reposts,
        show_teaser=req.show_teaser,
    )
    if req.height is not None:
        flags["height"] = req.height

    if req.album:
        try:
            return sc.album_embed(req.album, **{k: v for k, v in flags.items()
                                                if k in ("color", "height", "visual", "auto_play")})
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    attribution = None
    if req.author_name and req.author_url:
        attribution = sc.Attribution(
            author_name=req.author_name, author_url=req.author_url,
            title=req.title or "", title_url=req.title_url or "",
        )
    flags["attribution"] = attribution

    if req.playlist_id is not None:
        return sc.playlist_embed(req.playlist_id, **flags)
    if req.track_id is not None:
        return sc.track_embed(req.track_id, **flags)
    if req.permalink:
        return sc.embed_from_url(req.permalink, **flags)
    raise HTTPException(status_code=400, detail="supply one of: album, playlist_id, track_id, permalink")


@app.post("/gate", response_model=GateResponse)
async def gate(req: GateRequest) -> GateResponse:
    """Open a DeltaVerse gate → mint a NeuralNode room + spawn a bubbleroom.

    Wired to the catalogue (``deltaverse.gate.event`` + ``deltaverse.room.created``
    + ``deltaverse.bubbleroom.spawned``). Never broadcasts a partial result; if
    the on-chain prerequisites are absent the gate is recorded as blocked.
    """
    try:
        from agents.deltaverse import DeltaVerseGate
        from agents.deltaverse.neuralnode_gate import GateSpec
    except Exception as exc:  # pragma: no cover - import guard
        raise HTTPException(status_code=503, detail=f"deltaverse gate unavailable: {exc}") from exc

    spec = GateSpec(
        theme=req.theme,
        origin_event=req.origin_event,
        metadata_uri=req.metadata_uri,
        participants=req.participants,
        roles=req.roles,
        is_private=req.is_private,
        room_type=req.room_type,
        storage_cid=req.storage_cid,
        ai_seed=req.ai_seed,
        tone=req.tone,
        seed_mutation=req.seed_mutation,
        evolves=req.evolves,
    )
    g = DeltaVerseGate(chain_id=req.chain_id)
    result = await g.open_gate(spec, actor="wordpress_agent_gate", actor_wallet=req.actor_wallet)
    return GateResponse(**result.to_dict())


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
