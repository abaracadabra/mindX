# SPDX-License-Identifier: Apache-2.0
"""Tier gate middleware — the server-enforced "never see those pages" rule.

Adapted from mindX's api_access_gate (main_service.py:2232). A page/route is
mapped to a minimum tier; a request below that tier is redirected (HTML) or 401'd
(API) BEFORE the static handler runs, so admin/member markup is never delivered.

tier order: visitor(0) < member(1) < admin(2)
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse

from .auth import session_from_request

TIER_RANK = {"visitor": 0, "member": 1, "admin": 2}

# Public (any tier, incl. unauthenticated). Exact paths + prefixes.
PUBLIC_EXACT = {
    "/", "/index.html", "/healthz", "/favicon.ico", "/login", "/storefront",
}
PUBLIC_PREFIXES = (
    "/auth/",            # challenge/verify/me/logout
    "/gfx/",             # branding assets
    "/public/",          # manifest + abis + deployments
    "/vendor/",          # ethers
    "/assets/", "/static/",
    "/bankon-forms.js", "/payments.js", "/styled.css", "/iNFTabi.js",
    "/inft.html", "/inft.css",  # iNFT page is public (read-mostly)
    "/quote",            # public price quote API
)

# Minimum tier required for a path. First matching prefix wins.
MEMBER_PREFIXES = ("/member", )
ADMIN_PREFIXES = (
    "/admin",            # admin pages + admin APIs
    "/vault/",           # bankon-vault credential routes
    "/cabinet",          # cabinet provisioning
)


def _required_tier(path: str) -> str:
    if path in PUBLIC_EXACT or any(path.startswith(p) for p in PUBLIC_PREFIXES):
        return "visitor"
    if any(path.startswith(p) for p in ADMIN_PREFIXES):
        return "admin"
    if any(path.startswith(p) for p in MEMBER_PREFIXES):
        return "member"
    return "visitor"  # default-open for unlisted assets (storefront shell)


class TierGate(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        required = _required_tier(path)
        if required == "visitor":
            return await call_next(request)

        claims = session_from_request(request)
        tier = (claims or {}).get("tier", "visitor")
        if TIER_RANK.get(tier, 0) >= TIER_RANK[required]:
            return await call_next(request)

        # Gated. HTML GET → redirect to storefront (the page is never served).
        accept = request.headers.get("accept", "")
        if request.method == "GET" and "text/html" in accept:
            return RedirectResponse(url="/?gated=" + required, status_code=302)
        return JSONResponse(
            status_code=401,
            content={"code": "tier_required", "required": required, "have": tier},
        )
