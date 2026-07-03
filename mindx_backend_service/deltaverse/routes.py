"""DeltaVerse REALM routes — feature-flagged (MINDX_DELTAVERSE_ENABLED=1).

- GET  /deltaverse/recognize   — unverified identity → role hint (visual only)
- GET  /deltaverse/story/recent — the changing story (beats + emergence traits)
- POST /deltaverse/weave        — append a participant interaction to the story
- GET  /deltaverse/bubblerooms  — rooms annotated with what the viewer may enter
- POST /deltaverse/wish         — privilege-constrained grant-wish (payment = a path)
- GET  /realm                   — the gated REALM surface (overlord-controlled)

Real privilege is the signed overlord-session token (overlord/resolver.py). The
`recognize` hint NEVER grants access on its own; it only colors the fabric.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
)

from .config import (
    REALM_ROLES,
    bankon_eth_suffix,
    can_grant,
    is_enabled,
    known_addresses,
    rank,
    resolve_realm_identity,
)
from .weaver import CypherianWeaver
from .bubblerooms import rooms_for

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

_REALM_PAGE = PROJECT_ROOT / "mindx_frontend_ui" / "realm.html"
_ADDR_RE = re.compile(r"^0x[a-fA-F0-9]{40}$")

deltaverse_router = APIRouter(tags=["deltaverse"])

_ENGINE_JS = PROJECT_ROOT / "mindx_frontend_ui" / "deltaverse.js"


@deltaverse_router.get("/deltaverse.js", include_in_schema=False)
async def deltaverse_engine_js():
    """The fabric engine, served as a public asset so every surface (404,
    landing, /realm) is woven from one file. Not feature-gated — it is inert JS."""
    if _ENGINE_JS.exists():
        return FileResponse(str(_ENGINE_JS), media_type="application/javascript")
    raise HTTPException(status_code=404, detail="deltaverse.js not found")


def _guard() -> None:
    if not is_enabled():
        raise HTTPException(status_code=404, detail="DeltaVerse REALM not enabled on this host")


def _parse_identity(raw: str) -> Dict[str, Any]:
    s = (raw or "").strip()
    suffix = bankon_eth_suffix()          # ".bankon.eth"
    root = suffix.lstrip(".")             # "bankon.eth"
    out: Dict[str, Any] = {"address": None, "ens": None, "name": None, "label": s}
    if _ADDR_RE.match(s):
        out["address"] = s.lower()
        out["label"] = s[:6] + "…" + s[-4:]
    elif s.lower() == root or suffix in s.lower():  # the bare root OR a subname
        out["ens"] = s.lower()
        out["name"] = s.lower().replace(suffix, "")
        out["label"] = s.lower()
    elif s:
        out["name"] = s
    return out


def _viewer_role(request: Request) -> Dict[str, Any]:
    """Resolve the viewer's VERIFIED role from the overlord-session token, if
    present. Falls back to public. Token may arrive as Authorization: Bearer,
    X-Overlord-Token, or ?t=. Returns {role, level, address, verified}."""
    token = None
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
    token = token or request.headers.get("x-overlord-token") or request.query_params.get("t")
    if not token:
        return {"role": "public", "level": 0, "address": None, "verified": False}
    try:
        from mindx_backend_service.overlord.routes import verify_overlord_token
        claims = verify_overlord_token(token)
        role = (claims.get("role") or "public").lower()
        if role not in REALM_ROLES:
            role = "public"
        return {"role": role, "level": int(claims.get("level", 0)),
                "address": claims.get("sub"), "verified": True}
    except Exception:
        return {"role": "public", "level": 0, "address": None, "verified": False}


@deltaverse_router.get("/deltaverse/recognize", summary="Identity → role hint via bankon.eth ENS (visual only)")
async def recognize(id: str = ""):
    _guard()
    ident = _parse_identity(id)
    # Resolve on-chain: bankon.eth root owner → overlord; *.bankon.eth subname
    # holder → member; raw address → live tier. Reuses openagents/bankoneth
    # tiers.py; degrades to public if the RPC/module is unavailable. Still an
    # *unverified* hint — control is proven by the signed overlord token.
    res = resolve_realm_identity(ident.get("address"), ident.get("ens"))
    role = res["role"]
    if res.get("address") and not ident.get("address"):
        ident["resolved_address"] = res["address"]  # ENS name → owner address
    return {
        "identity": ident,
        "role": role,
        "level": rank(role),
        "names": res.get("names", []),
        "source": res.get("source"),
        "verified": False,  # real privilege requires the signed overlord token
        "note": "on-chain bankon.eth hint — privilege is proven via /overlord/verify",
    }


@deltaverse_router.get("/deltaverse/story/recent", summary="The changing story — beats + emergence traits")
async def story_recent(request: Request, n: int = 30):
    _guard()
    w = CypherianWeaver.instance()
    if "text/plain" in request.headers.get("accept", "") or request.query_params.get("h") == "true":
        beats = w.recent(n)
        lines = [f"{b['role']:>8} · {b['who']}: {b['text']}" for b in beats]
        t = w.traits()
        head = "traits: " + ", ".join(f"{k}={t[k]}" for k in
                                      ("intelligence", "knowledge", "wisdom", "resonance", "adaptability", "coherence"))
        return PlainTextResponse(head + " | wisdom=" + t["wisdom_band"] + "\n" + "\n".join(lines) + "\n")
    return {"beats": w.recent(n), "traits": w.traits()}


@deltaverse_router.post("/deltaverse/weave", summary="Weave a participant interaction into the story")
async def weave(request: Request):
    _guard()
    body: Dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    viewer = _viewer_role(request)
    w = CypherianWeaver.instance()
    beat = w.weave(
        kind=str(body.get("kind", "interact"))[:24],
        who=str(body.get("who", viewer.get("address") or "anon"))[:64],
        role=viewer["role"],
        text=str(body.get("text", ""))[:280],
        verified=viewer["verified"],
    )
    return {"beat": beat, "traits": w.traits()}


@deltaverse_router.get("/deltaverse/bubblerooms", summary="Rooms annotated with what the viewer may enter")
async def bubblerooms(request: Request):
    _guard()
    viewer = _viewer_role(request)
    return {"viewer": viewer, "rooms": rooms_for(viewer["role"])}


@deltaverse_router.post("/deltaverse/wish", summary="Privilege-constrained grant-wish (payment is one path)")
async def wish(request: Request):
    _guard()
    body: Dict[str, Any] = {}
    try:
        body = await request.json()
    except Exception:
        body = {}
    needed = str(body.get("needed", "public")).lower()
    if needed not in REALM_ROLES:
        needed = "public"
    viewer = _viewer_role(request)
    w = CypherianWeaver.instance()
    w.weave(kind="wish", who=viewer.get("address") or "anon", role=viewer["role"],
            text=str(body.get("wish", ""))[:200], needed=needed)
    if can_grant(viewer["role"], needed):
        return {"granted": True, "role": viewer["role"], "needed": needed,
                "action": body.get("action", "fulfill"), "reason": "privilege sufficient"}
    return {
        "granted": False, "role": viewer["role"], "needed": needed, "action": "upgrade",
        # Grant-wish is constrained only by privilege; payment is one way to gain it.
        "paths": ["connect a wallet", "acquire holdings (x402 / payment)", "earn tenure & reputation"],
        "reason": f"this wish requires {needed} privilege",
    }


@deltaverse_router.get("/realm", summary="The gated REALM surface (overlord-controlled)", include_in_schema=False)
async def realm(request: Request):
    """The REALM is both a gated surface and the privileged story layer. The
    control surface answers to the overlord alone: privileged participants enter,
    everyone else is guided home via the login gate."""
    if not is_enabled():
        # Behave like any other unknown path → the 404 fabric handles the rest.
        raise HTTPException(status_code=404, detail="REALM not enabled")
    viewer = _viewer_role(request)
    accept = request.headers.get("accept", "")
    if viewer["role"] != "overlord":
        if "text/html" in accept:
            return RedirectResponse(url="/login?from=/realm", status_code=302)
        return JSONResponse(status_code=403, content={
            "detail": "the REALM answers to the overlord alone",
            "role": viewer["role"], "code": "realm_overlord_only",
        })
    if _REALM_PAGE.exists():
        CypherianWeaver.instance().weave("realm.enter", viewer.get("address") or "overlord", "overlord",
                                         "the overlord entered the REALM")
        return HTMLResponse(_REALM_PAGE.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>REALM</h1><p>The fabric awaits its surface.</p>")
