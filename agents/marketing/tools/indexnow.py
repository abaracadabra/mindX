"""
indexnow — POST URLs to Bing/Copilot IndexNow endpoint.

IndexNow is a permissionless protocol for telling search engines that a URL
has been updated. Bing + Copilot honor it; Google does not. We POST in dry-run
by default — operator flips `live=True` after configuring the IndexNow key
file at the site root.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class IndexNowResult:
    host: str
    urls_count: int
    status_code: Optional[int]
    error: Optional[str]
    dry_run: bool


async def ping_indexnow(
    host: str,
    key: str,
    urls: List[str],
    *,
    live: bool = False,
    http_post=None,
) -> IndexNowResult:
    """POST `urls` to IndexNow. `http_post` is injectable for tests; production
    callers pass an aiohttp.ClientSession.post-equivalent.
    """
    if not urls:
        return IndexNowResult(host=host, urls_count=0, status_code=None, error=None, dry_run=True)
    if not live:
        return IndexNowResult(host=host, urls_count=len(urls), status_code=None, error=None, dry_run=True)
    if http_post is None:
        return IndexNowResult(
            host=host,
            urls_count=len(urls),
            status_code=None,
            error="no http_post provided",
            dry_run=False,
        )
    payload = {"host": host, "key": key, "urlList": urls}
    try:
        resp = await http_post("https://api.indexnow.org/indexnow", json=payload)
        status = getattr(resp, "status", None) or getattr(resp, "status_code", None)
        return IndexNowResult(
            host=host,
            urls_count=len(urls),
            status_code=status,
            error=None,
            dry_run=False,
        )
    except Exception as exc:
        return IndexNowResult(
            host=host,
            urls_count=len(urls),
            status_code=None,
            error=repr(exc),
            dry_run=False,
        )


__all__ = ["IndexNowResult", "ping_indexnow"]
