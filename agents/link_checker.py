# Copyright (c) 2026 mindX / BANKON
"""
Outbound link health across everything mindX has published.

Every other check in this family reads one thing back from one authority. This
one reads the whole published corpus back from the open internet, which is a
different problem: the internet answers unreliably, and the unreliability is not
evenly distributed. A CDN returning 403 to a non-browser client is not a dead
link. A rate limiter returning 429 is not a dead link. Counting non-200s and
calling the number "broken links" produces a metric that is mostly noise and
gets ignored within a week.

So the checker **classifies** rather than counts:

* ``ok``      — 2xx/3xx. The link works.
* ``dead``    — 404, 410, or the host does not resolve. Definitely broken; alert.
* ``blocked`` — 401/403. Something is refusing *us* specifically. Reported,
                never alerted on: this is the normal response of bot protection
                to an automated client, and a reader with a browser sees the page.
* ``inconclusive`` — 429. We were rate-limited, so the link's real state is
                unknown. This is kept apart from ``blocked`` because a 429 can
                *hide a dead link*: during the first live sweep a genuine 404 on
                github.com came back 429 simply because the sweep had hit that
                host too often. Anything inconclusive is re-probed after a pause
                before the sweep reports.
* ``error``   — 5xx, timeout, connection reset. Transient by assumption; it has
                to fail across consecutive runs before it means anything.

Only ``dead`` wakes anyone. That distinction is the whole reason this is worth
running: a checker that cries wolf about Cloudflare is a checker somebody turns
off, and a checker that is off detects nothing at all.
"""

from __future__ import annotations

import asyncio
import os
import re
import time
from collections import Counter
from typing import Any, Optional
from urllib.parse import urlparse

import aiohttp

from utils.logging_config import get_logger

logger = get_logger(__name__)

WORDPRESS_AGENT_URL = os.environ.get("MINDX_WORDPRESS_AGENT_URL", "http://127.0.0.1:8765")

#: Bounded so a sweep cannot look like an attack to any single host, and cannot
#: saturate the one VPS this runs on.
CONCURRENCY = int(os.environ.get("MINDX_LINKCHECK_CONCURRENCY", "8"))
PER_HOST_DELAY_S = float(os.environ.get("MINDX_LINKCHECK_HOST_DELAY_S", "0.4"))
TIMEOUT_S = float(os.environ.get("MINDX_LINKCHECK_TIMEOUT_S", "20"))

MONITOR_ENABLED = os.environ.get("MINDX_LINKCHECK_ENABLED", "1") not in ("0", "false", "no")
MONITOR_INTERVAL_S = float(os.environ.get("MINDX_LINKCHECK_INTERVAL_S", "86400"))
MONITOR_START_DELAY_S = float(os.environ.get("MINDX_LINKCHECK_START_DELAY_S", "900"))

#: A real browser string. Not deception — an honest automated client that
#: identifies itself gets 403'd by most CDNs, which would classify half the web
#: as broken. The suffix keeps the identification.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Safari/537.36 mindX-LinkCheck/1.0 (+https://mindx.pythai.net/)"
)

STATUS_OK = "ok"
STATUS_DEAD = "dead"
STATUS_BLOCKED = "blocked"
STATUS_ERROR = "error"
STATUS_INCONCLUSIVE = "inconclusive"

#: How long to wait before re-probing rate-limited URLs, and how many times.
RETRY_AFTER_429_S = float(os.environ.get("MINDX_LINKCHECK_429_BACKOFF_S", "20"))
RETRY_429_ROUNDS = int(os.environ.get("MINDX_LINKCHECK_429_ROUNDS", "2"))

#: Hosts whose content is generated per-request or requires a session; probing
#: them says nothing useful about whether the link is good.
SKIP_HOSTS = {"localhost", "127.0.0.1"}

_HREF_RE = re.compile(r'href=["\'](https?://[^"\'>\s]+)["\']', re.IGNORECASE)

#: Boilerplate a WordPress theme injects into every page. Checking them 141 times
#: is waste; they are checked once, as themselves.
_FURNITURE_HINTS = ("/wp-content/", "/wp-includes/", "/feed", "#comment", "/author/", "?share=")


def extract_links(html: str) -> set[str]:
    """Absolute http(s) links from a rendered page, minus obvious boilerplate."""
    found = set()
    for url in _HREF_RE.findall(html or ""):
        url = url.rstrip(".,);")
        if any(hint in url for hint in _FURNITURE_HINTS):
            continue
        host = urlparse(url).hostname or ""
        if host in SKIP_HOSTS or not host:
            continue
        found.add(url)
    return found


def classify(status: Optional[int], error: Optional[str]) -> str:
    """
    Map an outcome to a class. The judgement, not the arithmetic, is the product.
    """
    if error:
        # A hostname that does not resolve is dead in the way that matters — the
        # domain is gone, and no browser will do better. Everything else that
        # fails at the transport layer is assumed transient.
        lowered = error.lower()
        if "nxdomain" in lowered or "name or service not known" in lowered or "cannot connect to host" in lowered:
            return STATUS_DEAD if "name" in lowered or "nxdomain" in lowered else STATUS_ERROR
        return STATUS_ERROR
    if status is None:
        return STATUS_ERROR
    if 200 <= status < 400:
        return STATUS_OK
    if status in (404, 410):
        return STATUS_DEAD
    if status == 429:
        return STATUS_INCONCLUSIVE
    if status in (401, 403):
        return STATUS_BLOCKED
    if status >= 500:
        return STATUS_ERROR
    return STATUS_BLOCKED


class LinkChecker:
    """Sweeps published posts, probes their outbound links, classifies the results."""

    def __init__(self, wordpress_url: Optional[str] = None):
        self.wordpress_url = (wordpress_url or WORDPRESS_AGENT_URL).rstrip("/")
        self._host_last_hit: dict[str, float] = {}

    # ------------------------------------------------------------------ corpus

    async def published_posts(self, session: aiohttp.ClientSession) -> list[dict[str, Any]]:
        try:
            async with session.get(f"{self.wordpress_url}/catalogue") as resp:
                if resp.status != 200:
                    return []
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, OSError) as exc:
            logger.warning("link_checker: catalogue unavailable: %s", exc)
            return []
        return [p for p in (data.get("posts") or []) if p.get("status") == "publish"]

    async def links_in_post(self, session: aiohttp.ClientSession, slug: str) -> set[str]:
        url = f"https://rage.pythai.net/{slug}/"
        try:
            async with session.get(url, headers={"User-Agent": USER_AGENT}) as resp:
                if resp.status != 200:
                    return set()
                return extract_links(await resp.text())
        except (aiohttp.ClientError, TimeoutError, OSError):
            return set()

    # ------------------------------------------------------------------ probing

    async def _polite_wait(self, host: str) -> None:
        last = self._host_last_hit.get(host)
        now = time.monotonic()
        if last is not None and (now - last) < PER_HOST_DELAY_S:
            await asyncio.sleep(PER_HOST_DELAY_S - (now - last))
        self._host_last_hit[host] = time.monotonic()

    async def probe(self, session: aiohttp.ClientSession, url: str) -> dict[str, Any]:
        """
        HEAD first, GET on anything inconclusive.

        Many servers answer HEAD with 405 or 403 while serving GET perfectly well,
        so a HEAD-only checker invents broken links. HEAD is kept as the cheap
        first move, not the verdict.
        """
        host = urlparse(url).hostname or ""
        await self._polite_wait(host)

        status: Optional[int] = None
        error: Optional[str] = None
        for method in ("head", "get"):
            try:
                fn = session.head if method == "head" else session.get
                async with fn(url, headers={"User-Agent": USER_AGENT}, allow_redirects=True) as resp:
                    status, error = resp.status, None
                    if 200 <= status < 400:
                        break
                    if method == "head" and status in (403, 405, 400, 501):
                        continue  # inconclusive for HEAD; ask properly
                    break
            except (aiohttp.ClientError, TimeoutError, OSError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                if method == "get":
                    break

        return {"url": url, "status": status, "error": error, "class": classify(status, error)}

    # ------------------------------------------------------------------- sweep

    async def sweep(self, max_posts: int = 0) -> dict[str, Any]:
        started = time.time()
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_S)
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            posts = await self.published_posts(session)
            if max_posts:
                posts = posts[:max_posts]
            if not posts:
                return {
                    "checked_at": started,
                    "available": False,
                    "note": "post catalogue unavailable; nothing was checked and nothing is claimed",
                    "posts": 0,
                }

            # url -> the posts that reference it, so a dead link names its callers
            references: dict[str, list[str]] = {}

            async def collect(post: dict[str, Any]) -> None:
                async with semaphore:
                    for url in await self.links_in_post(session, post.get("slug", "")):
                        references.setdefault(url, []).append(str(post.get("id")))

            await asyncio.gather(*(collect(p) for p in posts))

            async def check(url: str) -> dict[str, Any]:
                async with semaphore:
                    result = await self.probe(session, url)
                    result["referenced_by"] = sorted(references[url])[:12]
                    result["reference_count"] = len(references[url])
                    return result

            results = await asyncio.gather(*(check(u) for u in sorted(references)))

            # A 429 means we asked too fast, not that the link is fine. Re-probe
            # those serially with a real pause: the first live sweep proved a
            # genuine 404 can hide behind rate limiting, which would make this
            # checker quietly miss the exact thing it exists to find.
            for _round in range(RETRY_429_ROUNDS):
                pending = [r for r in results if r["class"] == STATUS_INCONCLUSIVE]
                if not pending:
                    break
                logger.info("link check: re-probing %d rate-limited link(s) after %.0fs",
                            len(pending), RETRY_AFTER_429_S)
                await asyncio.sleep(RETRY_AFTER_429_S)
                for entry in pending:
                    await asyncio.sleep(PER_HOST_DELAY_S * 3)
                    fresh = await self.probe(session, entry["url"])
                    entry.update({k: fresh[k] for k in ("status", "error", "class")})

        counts = Counter(r["class"] for r in results)
        dead = [r for r in results if r["class"] == STATUS_DEAD]
        blocked = [r for r in results if r["class"] == STATUS_BLOCKED]
        inconclusive = [r for r in results if r["class"] == STATUS_INCONCLUSIVE]

        return {
            "checked_at": started,
            "duration_s": round(time.time() - started, 1),
            "available": True,
            "posts": len(posts),
            "unique_links": len(results),
            "counts": dict(counts),
            "dead": sorted(dead, key=lambda r: -r["reference_count"]),
            "blocked_sample": sorted(blocked, key=lambda r: -r["reference_count"])[:10],
            "inconclusive": [{"url": r["url"], "reference_count": r["reference_count"]} for r in inconclusive],
            "verdict": "attention" if dead else "clean",
            # Said in the payload so a clean verdict cannot be over-read.
            "not_checked": [
                "link targets that resolve but serve the wrong content — this checks reachability, not correctness",
                "links inside gated or draft posts, which the public catalogue does not list",
                "anchors within a page (#fragment) — only the document is fetched",
                "links still rate-limited after re-probing — reported as inconclusive, never as ok",
            ],
        }


# ------------------------------------------------------------ periodic monitor

_LAST_SWEEP: dict[str, Any] = {}
_KNOWN_DEAD: set[str] = set()


def last_sweep() -> dict[str, Any]:
    return dict(_LAST_SWEEP)


async def run_link_monitor(
    interval_s: Optional[float] = None, start_delay_s: Optional[float] = None
) -> None:
    """
    Sweep on a schedule, alerting only on links that have *newly* died.

    A link that was dead last week and is dead this week is not news; re-reporting
    it every cycle is how a report becomes wallpaper. The first sweep establishes
    a baseline and alerts on nothing.
    """
    global _LAST_SWEEP

    await asyncio.sleep(start_delay_s if start_delay_s is not None else MONITOR_START_DELAY_S)
    checker = LinkChecker()
    first_run = True

    while True:
        try:
            report = await checker.sweep()
            if report.get("available"):
                dead_now = {r["url"] for r in report.get("dead", [])}
                newly_dead = dead_now - _KNOWN_DEAD
                revived = _KNOWN_DEAD - dead_now

                if first_run:
                    logger.info(
                        "link check baseline: %d links across %d posts — %s",
                        report["unique_links"], report["posts"], report["counts"],
                    )
                    first_run = False
                else:
                    for url in sorted(newly_dead):
                        entry = next((r for r in report["dead"] if r["url"] == url), {})
                        logger.error(
                            "LINK DIED: %s (HTTP %s) referenced by %d published post(s): %s",
                            url, entry.get("status"), entry.get("reference_count"),
                            ", ".join(entry.get("referenced_by", [])),
                        )
                    for url in sorted(revived):
                        logger.info("link recovered: %s", url)
                    if not newly_dead and not revived:
                        logger.info(
                            "link check: %s (%d links, %d dead, %d blocked)",
                            report["verdict"], report["unique_links"],
                            report["counts"].get(STATUS_DEAD, 0), report["counts"].get(STATUS_BLOCKED, 0),
                        )

                _KNOWN_DEAD.clear()
                _KNOWN_DEAD.update(dead_now)
                report["newly_dead"] = sorted(newly_dead)
                report["revived"] = sorted(revived)
                await _emit_catalogue(report)
            else:
                logger.info("link check: catalogue unavailable — nothing checked")

            _LAST_SWEEP = report
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 — a monitor must outlive its own bugs
            logger.warning("link monitor cycle failed: %s", exc)

        await asyncio.sleep(interval_s if interval_s is not None else MONITOR_INTERVAL_S)


async def _emit_catalogue(report: dict[str, Any]) -> None:
    """Mirror the sweep into the catalogue. Logged at warning on failure — a silent
    emitter is indistinguishable from a working one."""
    try:
        from agents.catalogue.events import emit_catalogue_event

        await emit_catalogue_event(
            kind="links.checked",
            actor="link_checker",
            payload={
                "posts": report.get("posts"),
                "unique_links": report.get("unique_links"),
                "counts": report.get("counts"),
                "verdict": report.get("verdict"),
                "dead": [{"url": r["url"], "status": r["status"], "refs": r["reference_count"]}
                         for r in report.get("dead", [])],
                "newly_dead": report.get("newly_dead", []),
            },
            source_log="insight/links/health",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("link_checker: catalogue emit failed: %s", exc)


async def check_links(max_posts: int = 0) -> dict[str, Any]:
    """Entry point for the insight route: a live sweep plus the last scheduled one."""
    report = await LinkChecker().sweep(max_posts=max_posts)
    report["monitor"] = {
        "enabled": MONITOR_ENABLED,
        "interval_s": MONITOR_INTERVAL_S,
        "last_scheduled_sweep": _LAST_SWEEP.get("checked_at"),
        "known_dead": sorted(_KNOWN_DEAD),
    }
    return report
