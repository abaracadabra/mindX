# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
"""Core WordpressAgent. Single responsibility: publish finished content to WordPress."""
from __future__ import annotations

import asyncio
import mimetypes
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import httpx

from .config import Settings

PostStatus = Literal["publish", "future", "draft", "pending", "private"]


class WordpressAgentError(Exception):
    """Base exception for all WordPress.agent failures."""


class AuthenticationError(WordpressAgentError):
    """Raised when the WordPress API rejects credentials."""


class PublishError(WordpressAgentError):
    """Raised when a publish call fails after all retries."""


class MediaUploadError(WordpressAgentError):
    """Raised when a media upload fails after all retries."""


@dataclass(slots=True, frozen=True)
class PublishResult:
    """Result of a publish call. Stable shape for AuthorAgent consumers."""

    post_id: int
    url: str
    status: str
    slug: str
    date_gmt: str
    raw: dict[str, Any]


@dataclass(slots=True, frozen=True)
class MediaResult:
    """Result of a media upload."""

    media_id: int
    url: str
    mime_type: str
    raw: dict[str, Any]


class WordpressAgent:
    """Publish finished articles to WordPress via the REST API.

    The agent does one thing: take a fully formed article and put it on the
    target WordPress site. It does not generate content, manage style, schedule
    via in-process timers (WordPress's `future` status handles that), or anchor
    on-chain. Those concerns belong upstream in AuthorAgent and the broader
    PYTHAI/DELTAVERSE tooling.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # JWT auth via the mindx-publish-auth plugin (preferred path).
        # Constructed lazily so test fixtures don't need vault access.
        self._mindx_auth: Any = None
        self._client = self._build_client()

    def _build_client(self) -> httpx.AsyncClient:
        transport = httpx.AsyncHTTPTransport(retries=0)
        return httpx.AsyncClient(
            base_url=f"{self.settings.base_url_str}/wp-json/wp/v2",
            # No default `auth=`; we add the right header per request in
            # `_auth_headers` so the JWT path can take precedence over
            # Basic Auth when the mindx-publish-auth plugin is installed.
            timeout=self.settings.timeout,
            headers={"User-Agent": self.settings.user_agent},
            transport=transport,
        )

    def _get_mindx_auth_client(self):
        """Lazy-construct the mindX-Auth client (which reads vault entries).

        Returns ``None`` if the wordpress_agent.mindx_auth module is
        missing or the vault entries aren't provisioned — caller falls
        back to Basic Auth.
        """
        if self._mindx_auth is False:
            return None
        if self._mindx_auth is None:
            try:
                from .mindx_auth import MindXAuthClient
                self._mindx_auth = MindXAuthClient(
                    base_url=self.settings.base_url_str,
                    user_agent=self.settings.user_agent,
                )
            except Exception:
                self._mindx_auth = False
                return None
        return self._mindx_auth

    async def _auth_headers(self) -> dict:
        """Pick the best available auth header for the current request.

        Order:
          1. Bearer JWT from mindx-publish-auth (preferred — no password
             on the wire)
          2. HTTP Basic Auth via WordPress Application Password
             (fallback — works when the plugin isn't installed)
        """
        client = self._get_mindx_auth_client()
        if client is not None:
            headers = await client.bearer_headers()
            if headers:
                return headers
        # Basic-Auth fallback: build the header manually so we don't have
        # to swap the AsyncClient's `auth=` attribute (which would not
        # apply per-request anyway).
        import base64
        token = base64.b64encode(
            f"{self.settings.user}:{self.settings.app_password_value}".encode("utf-8")
        ).decode("ascii")
        return {"Authorization": f"Basic {token}"}

    async def __aenter__(self) -> WordpressAgent:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    async def close(self) -> None:
        await self._client.aclose()

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> httpx.Response:
        """Send a request with exponential backoff on transient failures.

        Per-request auth: we pick a header (JWT preferred, Basic Auth
        fallback) and merge it into the request's headers. Callers that
        supply their own ``Authorization`` header win.
        """
        auth_headers = await self._auth_headers()
        if auth_headers:
            req_headers = dict(kwargs.pop("headers", {}) or {})
            for k, v in auth_headers.items():
                req_headers.setdefault(k, v)
            kwargs["headers"] = req_headers

        last_exc: Exception | None = None
        for attempt in range(self.settings.retry_count + 1):
            try:
                response = await self._client.request(method, path, **kwargs)
                if response.status_code == 401:
                    raise AuthenticationError(
                        f"WordPress rejected credentials for user "
                        f"{self.settings.user!r} at {self.settings.base_url_str}"
                    )
                if response.status_code >= 500 or response.status_code == 429:
                    response.raise_for_status()
                return response
            except (httpx.TransportError, httpx.HTTPStatusError) as exc:
                last_exc = exc
                if attempt >= self.settings.retry_count:
                    break
                delay = self.settings.retry_backoff * (2**attempt)
                await asyncio.sleep(delay)
        raise PublishError(
            f"Request {method} {path} failed after "
            f"{self.settings.retry_count + 1} attempts: {last_exc!r}"
        ) from last_exc

    async def publish(
        self,
        title: str,
        content: str,
        *,
        status: PostStatus = "publish",
        date: datetime | None = None,
        categories: list[int] | None = None,
        tags: list[int] | None = None,
        featured_media: int | None = None,
        excerpt: str | None = None,
        slug: str | None = None,
        author: int | None = None,
        meta: dict[str, Any] | None = None,
    ) -> PublishResult:
        """Publish a finished article.

        Scheduling is handled by WordPress itself: pass ``status="future"`` with
        a future ``date`` and WordPress's cron will publish at that time. No
        in-process scheduler is required.
        """
        if not title.strip():
            raise ValueError("title must be non-empty")
        if not content.strip():
            raise ValueError("content must be non-empty")

        payload: dict[str, Any] = {
            "title": title,
            "content": content,
            "status": status,
        }
        if date is not None:
            if date.tzinfo is None:
                raise ValueError("date must be timezone-aware")
            payload["date_gmt"] = date.astimezone(timezone.utc).isoformat()
        if categories:
            payload["categories"] = categories
        if tags:
            payload["tags"] = tags
        if featured_media is not None:
            payload["featured_media"] = featured_media
        if excerpt:
            payload["excerpt"] = excerpt
        if slug:
            payload["slug"] = slug
        if author is not None:
            payload["author"] = author
        if meta:
            payload["meta"] = meta

        response = await self._request_with_retry("POST", "/posts", json=payload)
        if response.status_code >= 400:
            raise PublishError(
                f"Publish failed with status {response.status_code}: {response.text}"
            )
        data = response.json()
        return PublishResult(
            post_id=int(data["id"]),
            url=str(data["link"]),
            status=str(data["status"]),
            slug=str(data["slug"]),
            date_gmt=str(data["date_gmt"]),
            raw=data,
        )

    async def upload_media(
        self,
        file_path: str | Path,
        *,
        alt_text: str = "",
        caption: str = "",
        title: str | None = None,
    ) -> MediaResult:
        """Upload a media file (typically a featured image) to WordPress."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Media file not found: {path}")
        if not path.is_file():
            raise ValueError(f"Media path is not a file: {path}")

        mime, _ = mimetypes.guess_type(str(path))
        if mime is None:
            mime = "application/octet-stream"

        with path.open("rb") as fh:
            data = fh.read()

        headers = {
            "Content-Disposition": f'attachment; filename="{path.name}"',
            "Content-Type": mime,
        }
        response = await self._request_with_retry(
            "POST",
            "/media",
            content=data,
            headers=headers,
        )
        if response.status_code >= 400:
            raise MediaUploadError(
                f"Media upload failed with status {response.status_code}: {response.text}"
            )
        media = response.json()
        media_id = int(media["id"])

        if alt_text or caption or title:
            update_payload: dict[str, Any] = {}
            if alt_text:
                update_payload["alt_text"] = alt_text
            if caption:
                update_payload["caption"] = caption
            if title:
                update_payload["title"] = title
            update_response = await self._request_with_retry(
                "POST",
                f"/media/{media_id}",
                json=update_payload,
            )
            if update_response.status_code < 400:
                media = update_response.json()

        return MediaResult(
            media_id=media_id,
            url=str(media["source_url"]),
            mime_type=str(media.get("mime_type", mime)),
            raw=media,
        )

    async def health_check(self) -> dict[str, Any]:
        """Verify connectivity and authentication against the WordPress API."""
        response = await self._client.get("/users/me")
        ok = response.status_code == 200
        return {
            "ok": ok,
            "status_code": response.status_code,
            "base_url": self.settings.base_url_str,
            "user": self.settings.user,
            "wp_user_id": response.json().get("id") if ok else None,
        }
