# SPDX-License-Identifier: Apache-2.0
"""mindX-side client for the *mindx-publish-auth* WordPress plugin.

The plugin exposes three endpoints under ``/wp-json/mindx/v1/auth/``:

  GET  /challenge                → one-time challenge text + id
  POST /verify  {id, address, sig} → short-lived HS256 JWT
  GET  /whoami  (Bearer)         → debug helper

This module drives that protocol with the vault-held wordpress.agent
wallet as the signing identity. The credential surface on the wire is
*only* the signature — no passwords, no Application Passwords, no
secrets in env vars.

Falls back gracefully when the plugin is not installed (challenge
endpoint returns 404): caller can then opt into Basic Auth with an
Application Password if available, or fail soft.

Public surface
--------------

    auth_client = MindXAuthClient(base_url="https://rage.pythai.net")
    token = await auth_client.get_token()                   # JWT, cached until ~near-exp
    headers = await auth_client.bearer_headers()            # {"Authorization": "Bearer ..."}
    is_available = await auth_client.plugin_present()       # bool, cached
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from .vault_creds import load_wp_settings_from_vault, sign_with_agent_wallet

logger = logging.getLogger("wordpress_agent.mindx_auth")

# Browser-shaped UA so Hostinger's WAF doesn't 403 the request.
_DEFAULT_UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36 mindX-wordpress-agent/0.4"
)


@dataclass
class _CachedToken:
    token: str
    expires_at: float    # unix seconds
    user_id: int

    def expiring_soon(self, skew: float = 60.0) -> bool:
        """True if the token expires within ``skew`` seconds."""
        return time.time() + skew >= self.expires_at


class MindXAuthClient:
    """Async client for the mindx-publish-auth REST endpoints.

    Thread-safe under a single asyncio loop. Tokens are cached in
    memory only — re-instantiating the client forces a fresh
    challenge/verify round-trip.
    """

    PATH_CHALLENGE = "/wp-json/mindx/v1/auth/challenge"
    PATH_VERIFY    = "/wp-json/mindx/v1/auth/verify"
    PATH_WHOAMI    = "/wp-json/mindx/v1/auth/whoami"
    PATH_DIAGNOSE  = "/wp-json/mindx/v1/auth/diagnose"

    def __init__(
        self,
        base_url: Optional[str] = None,
        *,
        timeout_s: float = 30.0,
        user_agent: str = _DEFAULT_UA,
    ):
        # If base_url is not provided, derive it from the wordpress.agent
        # vault entry — same source of truth as the rest of the wp.agent.
        self._explicit_base_url = base_url
        self._timeout = timeout_s
        self._ua = user_agent
        self._token: Optional[_CachedToken] = None
        self._lock = asyncio.Lock()
        self._plugin_present: Optional[bool] = None    # cached after first probe

    # ─── Public API ─────────────────────────────────────────────

    async def get_token(self, *, force: bool = False) -> Optional[str]:
        """Return a valid JWT for the wordpress.agent wallet. Performs
        a challenge/verify round-trip if no token is cached or the
        cached one is expiring within 60s. Returns ``None`` on any
        failure (logged); caller decides on the fallback."""
        async with self._lock:
            if not force and self._token and not self._token.expiring_soon():
                return self._token.token
            token = await self._mint_token()
            if token is None:
                return None
            self._token = token
            return token.token

    async def bearer_headers(self) -> dict:
        """Convenience: returns ``{"Authorization": "Bearer <jwt>"}``
        ready to pass to httpx. Empty dict on failure."""
        tok = await self.get_token()
        if tok is None:
            return {}
        return {"Authorization": f"Bearer {tok}"}

    async def plugin_present(self) -> bool:
        """True if the plugin's /diagnose endpoint responds with the
        expected shape. Cached after the first probe (good for the
        lifetime of the client). Used to detect "plugin not installed"
        so callers can fall back to Basic Auth where appropriate."""
        if self._plugin_present is not None:
            return self._plugin_present
        base = await self._base_url()
        if base is None:
            self._plugin_present = False
            return False
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, headers={"User-Agent": self._ua}
            ) as c:
                r = await c.get(base + self.PATH_DIAGNOSE)
            self._plugin_present = (
                r.status_code == 200
                and r.headers.get("content-type", "").startswith("application/json")
                and "plugin_version" in r.json()
            )
        except Exception as e:   # pragma: no cover — defensive
            logger.warning(f"mindx_auth: plugin probe failed: {e}")
            self._plugin_present = False
        return self._plugin_present

    # ─── Internals ──────────────────────────────────────────────

    async def _base_url(self) -> Optional[str]:
        if self._explicit_base_url:
            return self._explicit_base_url.rstrip("/")
        try:
            settings = load_wp_settings_from_vault()
        except Exception as e:
            logger.warning(f"mindx_auth: vault settings load failed: {e}")
            return None
        if settings is None:
            return None
        return str(settings.base_url).rstrip("/")

    async def _mint_token(self) -> Optional[_CachedToken]:
        base = await self._base_url()
        if base is None:
            logger.warning("mindx_auth: no base_url available (vault unconfigured)")
            return None
        # Probe the vault for wordpress.agent:pk BEFORE making any HTTP
        # request. If the vault doesn't have the wallet provisioned, we
        # can't sign anything, so issuing the challenge would be wasted.
        # This also keeps the no-vault test path silent (no unexpected
        # GETs to /auth/challenge that would trip pytest_httpx assertions).
        probe = sign_with_agent_wallet("__mindx_auth_probe__")
        if probe is None:
            logger.info(
                "mindx_auth: wordpress.agent wallet not in vault; "
                "skipping challenge round-trip"
            )
            return None
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout, headers={"User-Agent": self._ua}
            ) as c:
                # 1. Fetch a challenge.
                r = await c.get(base + self.PATH_CHALLENGE)
                if r.status_code == 404:
                    logger.warning(
                        "mindx_auth: /wp-json/mindx/v1/auth/challenge returned 404 — "
                        "mindx-publish-auth plugin is not installed or not activated"
                    )
                    self._plugin_present = False
                    return None
                if r.status_code != 200:
                    logger.warning(
                        f"mindx_auth: challenge fetch returned {r.status_code}: "
                        f"{r.text[:200]!r}"
                    )
                    return None
                chal = r.json()
                challenge_id = chal.get("challenge_id")
                message      = chal.get("message")
                if not challenge_id or not message:
                    logger.warning(
                        f"mindx_auth: challenge response missing fields: {chal!r}"
                    )
                    return None

                # 2. Sign with the vault-held wordpress.agent wallet.
                sig_result = sign_with_agent_wallet(message)
                if sig_result is None:
                    logger.warning(
                        "mindx_auth: sign_with_agent_wallet returned None — "
                        "wordpress.agent:pk is not in the vault"
                    )
                    return None
                signature, address = sig_result

                # 3. Post (challenge_id, address, signature) to /verify.
                r2 = await c.post(
                    base + self.PATH_VERIFY,
                    json={
                        "challenge_id": challenge_id,
                        "address": address,
                        "signature": signature,
                    },
                )
                if r2.status_code != 200:
                    body = r2.text[:300]
                    logger.warning(
                        f"mindx_auth: verify returned {r2.status_code}: {body!r}"
                    )
                    return None
                body = r2.json()
                tok = body.get("token")
                exp = float(body.get("expires_at") or 0)
                uid = int(body.get("user_id") or 0)
                if not tok or not exp:
                    logger.warning(
                        f"mindx_auth: verify response missing token/expires: {body!r}"
                    )
                    return None
                logger.info(
                    f"mindx_auth: JWT minted for user_id={uid}, valid for "
                    f"{int(exp - time.time())}s"
                )
                return _CachedToken(token=tok, expires_at=exp, user_id=uid)

        except httpx.HTTPError as e:
            logger.warning(f"mindx_auth: transport error: {e}")
            return None
        except Exception as e:   # pragma: no cover — defensive
            logger.warning(f"mindx_auth: unexpected error: {e}")
            return None


__all__ = ["MindXAuthClient"]
