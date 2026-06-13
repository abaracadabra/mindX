# Copyright 2026 BANKON. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""HTTP surface for ``x402rails.agent`` — credential issuance over the wire.

This exposes :class:`x402_rails.X402RailsService` as an HTTP service so any
agent or external consumer can request payment credentials without holding a
key. It ships as a self-contained, mountable router so the agnostic module
stays decoupled from mindX's backend (mindX is one consumer, not the only home):

* **Mount into an existing app** — ``mount(app, spend_guard=require_admin_access)``
  folds the routes into the mindX backend and reuses its shadow-overlord JWT gate.
* **Run standalone** — ``uvicorn x402_rails_service:app`` serves the rails on
  their own port, gated by an ``X402_RAILS_ADMIN_TOKEN`` bearer token from ``.env``.

The spend boundary is explicit. Read-only capability advertisement
(``GET /describe``, ``GET /rails``) is public; every credential-minting route
(``POST /issue``, ``/issue-for-url``, ``/settle``) is behind the injected
``spend_guard``, because a signed credential *is* spend authority.
"""

from __future__ import annotations

import hmac
import inspect
import os
from collections.abc import Awaitable, Callable
from typing import Any, Optional

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel

from cmc_client import decode_payment_challenge
from x402_rails import (
    X402BudgetExceeded,
    X402RailsError,
    X402RailsService,
    X402RailUnavailable,
)

# A spend guard is a FastAPI-style dependency: it receives the request and
# either returns a subject string or raises HTTPException. Sync or async.
spend_guard_t = Callable[[Request], "str | Awaitable[str]"]

ADMIN_TOKEN_ENV: str = "X402_RAILS_ADMIN_TOKEN"


class IssueBody(BaseModel):
    """Request to mint a credential from a challenge."""

    challenge: Optional[dict] = None
    payment_required: Optional[str] = None  # base64 header, decoded server-side
    rail: Optional[str] = None


class UrlBody(BaseModel):
    """Request to probe a gated URL and mint (or settle) against it."""

    url: str
    params: Optional[dict] = None
    rail: Optional[str] = None


def env_bearer_guard(request: Request) -> str:
    """Default spend gate: an opaque bearer token from ``X402_RAILS_ADMIN_TOKEN``.

    Refuses everything when the token is unset, so a misconfigured standalone
    deployment fails closed rather than minting credentials for anyone. Mount
    with a stronger guard (e.g. the backend's ``require_admin_access``) in
    production.
    """
    token = os.environ.get(ADMIN_TOKEN_ENV, "")
    if not token:
        raise HTTPException(
            status_code=503,
            detail=f"x402 rails spend gate not configured (set {ADMIN_TOKEN_ENV})",
        )
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer ") or not hmac.compare_digest(
        authorization[7:], token
    ):
        raise HTTPException(
            status_code=401,
            detail="spend gate: Authorization: Bearer <token> required",
        )
    return "env-admin"


def _guard_dependency(guard: spend_guard_t) -> Callable[..., Awaitable[str]]:
    """Wrap a sync-or-async guard into an awaitable FastAPI dependency."""

    async def _dep(request: Request) -> str:
        result = guard(request)
        if inspect.isawaitable(result):
            result = await result
        return str(result)

    return _dep


def build_router(
    *,
    rails: X402RailsService | None = None,
    spend_guard: spend_guard_t | None = None,
    prefix: str = "/x402/rails",
) -> APIRouter:
    """Build the rails router.

    Args:
        rails: The service instance to expose; a default one is created when
            omitted (its Base rail reads ``X402_WALLET_PRIVATE_KEY`` lazily).
        spend_guard: Dependency gating the credential-minting routes; defaults
            to :func:`env_bearer_guard`. Inject the backend's
            ``require_admin_access`` when mounting into mindX.
        prefix: URL prefix for the routes.
    """
    service = rails if rails is not None else X402RailsService()
    guard = _guard_dependency(spend_guard or env_bearer_guard)
    router = APIRouter(prefix=prefix, tags=["x402 rails"])

    @router.get("/describe")
    async def describe() -> dict[str, Any]:
        """Advertise the rails, payment header, and budget (public, no spend)."""
        return service.describe()

    @router.get("/rails")
    async def rails_list() -> dict[str, Any]:
        """List the settlement rails this service can sign on (public)."""
        return {"rails": service.offered_rails()}

    @router.post("/issue")
    async def issue(body: IssueBody, _subject: str = Depends(guard)) -> dict[str, Any]:
        """Mint a signed credential from a decoded challenge (spend-gated)."""
        challenge = _challenge_from_body(body)
        return _issue(service, challenge, body.rail)

    @router.post("/issue-for-url")
    async def issue_for_url(
        body: UrlBody, _subject: str = Depends(guard)
    ) -> dict[str, Any]:
        """Probe a gated URL, mint a credential, but do not settle (spend-gated)."""
        try:
            credential = service.issue_for_url(
                body.url, body.params or {}, rail=body.rail
            )
        except (X402BudgetExceeded, X402RailUnavailable, X402RailsError) as exc:
            raise _http_error(exc)
        return credential.to_dict()

    @router.post("/settle")
    async def settle(body: UrlBody, _subject: str = Depends(guard)) -> dict[str, Any]:
        """Mint a credential and complete the paid request end to end (spend-gated)."""
        try:
            data = service.settle(body.url, body.params or {}, rail=body.rail)
        except (X402BudgetExceeded, X402RailUnavailable, X402RailsError) as exc:
            raise _http_error(exc)
        return {"data": data}

    return router


def _challenge_from_body(body: IssueBody) -> dict[str, Any]:
    """Resolve a decoded challenge from an issue request body."""
    if body.challenge is not None:
        return body.challenge
    if body.payment_required:
        try:
            return decode_payment_challenge(body.payment_required)
        except Exception as exc:  # noqa: BLE001 - surfaced as a 422
            raise HTTPException(
                status_code=422, detail=f"undecodable payment-required: {exc}"
            )
    raise HTTPException(
        status_code=422, detail="provide either 'challenge' or 'payment_required'"
    )


def _issue(
    service: X402RailsService, challenge: dict[str, Any], rail: str | None
) -> dict[str, Any]:
    try:
        return service.issue_from_challenge(challenge, rail=rail).to_dict()
    except (X402BudgetExceeded, X402RailUnavailable, X402RailsError) as exc:
        raise _http_error(exc)


def _http_error(exc: Exception) -> HTTPException:
    """Map a rails error to the right HTTP status."""
    if isinstance(exc, X402BudgetExceeded):
        return HTTPException(status_code=402, detail=str(exc))
    if isinstance(exc, X402RailUnavailable):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


def build_app(
    *,
    rails: X402RailsService | None = None,
    spend_guard: spend_guard_t | None = None,
    prefix: str = "/x402/rails",
) -> FastAPI:
    """Build a standalone ASGI app exposing the rails router."""
    app = FastAPI(title="x402 rails", version="0.1.0")
    app.include_router(
        build_router(rails=rails, spend_guard=spend_guard, prefix=prefix)
    )
    return app


def mount(
    app: FastAPI,
    *,
    rails: X402RailsService | None = None,
    spend_guard: spend_guard_t | None = None,
    prefix: str = "/x402/rails",
) -> None:
    """Fold the rails routes into an existing app.

    From the mindX backend::

        from mindx_backend_service.security_middleware import require_admin_access
        import x402_rails_service
        x402_rails_service.mount(app, spend_guard=require_admin_access)
    """
    app.include_router(
        build_router(rails=rails, spend_guard=spend_guard, prefix=prefix)
    )


# Standalone entrypoint: `uvicorn x402_rails_service:app`
app = build_app()
