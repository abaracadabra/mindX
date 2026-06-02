# SPDX-License-Identifier: Apache-2.0
"""bankon.eth gate backend — the server-enforced UI to bankon.eth + bankon-vault.

Mounts:
  /auth/*                       SIWE login → tier-scoped session JWT (auth.py)
  TierGate middleware           true-hide admin/member pages (gate.py)
  /vault/credentials/*          bankon-vault credential mgmt   (vault_module)
  /admin/shadow/*, /cabinet/*   shadow-overlord + cabinet      (vault_module)
  /vault/sign/*                 vault signing oracle           (vault_module)
  /gfx/*                        branding assets (StaticFiles)
  /public/*                     manifest + abis + deployments  (StaticFiles)
  /                             tier-served HTML from packages/web

Run:  uvicorn backend.app:app --port 8800   (from openagents/bankoneth/)
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import router as auth_router, session_from_request
from .gate import TierGate
from .tiers import resolve_tier  # noqa: F401  (re-exported for tests)
from .x402 import router as x402_router

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "packages" / "web"
GFX = ROOT / "gfx"
GFX_FALLBACK = ROOT.parent.parent / "gfx"  # mindX/gfx master library

# Default the vault/nonce storage under the module so it's self-contained.
os.environ.setdefault("BANKON_VAULT_DIR", str(ROOT / "vault_bankon"))
os.environ.setdefault("SHADOW_NONCES_PATH", str(ROOT / "vault_module" / "data" / "shadow_nonces.json"))
(Path(os.environ["SHADOW_NONCES_PATH"]).parent).mkdir(parents=True, exist_ok=True)

app = FastAPI(title="bankon.eth gate", version="0.1.0")
app.add_middleware(TierGate)
app.include_router(auth_router)
app.include_router(x402_router)

# bankon-vault routers (admin-tier gated by TierGate on /vault, /admin, /cabinet)
try:
    from vault_module import bankon_vault_router, vault_sign_router
    from vault_module import routes as _vault_routes
    from vault_module.admin_routes import admin_router as shadow_admin_router, public_cabinet_router
    from .auth import require_admin_tier

    # Wire the vault credential routes' admin dependency to our admin-tier session
    # (defense in depth — the TierGate already gates /vault/* to the admin tier).
    _vault_routes.require_admin_access = require_admin_tier

    app.include_router(bankon_vault_router)
    app.include_router(shadow_admin_router)
    app.include_router(public_cabinet_router)
    app.include_router(vault_sign_router)
except Exception as e:  # pragma: no cover — vault deps optional in some envs
    print(f"[gate] bankon-vault routers not mounted: {e}")

# Static surfaces
if (WEB / "public").is_dir():
    app.mount("/public", StaticFiles(directory=str(WEB / "public")), name="public")
if (WEB / "vendor").is_dir():
    app.mount("/vendor", StaticFiles(directory=str(WEB / "vendor")), name="vendor")
_gfx = GFX if GFX.is_dir() else GFX_FALLBACK
if _gfx.is_dir():
    app.mount("/gfx", StaticFiles(directory=str(_gfx)), name="gfx")


@app.get("/healthz")
async def healthz():
    return {"ok": True, "service": "bankon.eth gate"}


def _serve(name: str) -> FileResponse:
    return FileResponse(str(WEB / name))


# Tier-served pages. TierGate has already enforced access by the time we get here,
# so these handlers only run for permitted tiers.
@app.get("/")
@app.get("/index.html")
async def storefront():
    f = WEB / "index.html"
    return _serve("index.html") if f.exists() else _serve("bankoneth.html")


@app.get("/member.html")
async def member_page():
    return _serve("member.html")


@app.get("/admin.html")
async def admin_page():
    return _serve("admin.html")


# Serve loose web assets (js/css) that aren't under a mounted static dir.
@app.get("/{asset:path}")
async def web_asset(asset: str, request: Request):
    if not asset or "/" in asset.strip("/") and asset.count("/") > 3:
        return JSONResponse({"code": "not_found"}, status_code=404)
    candidate = (WEB / asset).resolve()
    try:
        candidate.relative_to(WEB.resolve())
    except ValueError:
        return JSONResponse({"code": "forbidden"}, status_code=403)
    if candidate.is_file():
        return FileResponse(str(candidate))
    return JSONResponse({"code": "not_found"}, status_code=404)
