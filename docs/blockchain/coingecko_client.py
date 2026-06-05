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

"""CoinGecko market-data client with a free/Pro tier split.

This module mirrors ``cmc_client`` for the CoinGecko surface, but it expresses
the consumption-versus-ingestion boundary as two distinct classes rather than a
flag. The class a caller holds *is* the access tier: a ``coingecko_public_client``
handed to a dashboard read-path cannot reach a paid backfill endpoint, because
those methods live only on ``coingecko_pro_client``.

Two access tiers are supported. The **free/Demo** tier is served from
``https://api.coingecko.com/api/v3`` and authenticates, optionally, with an
``x-cg-demo-api-key`` header; it works fully keyless and is the surface for live
public consumption. The **Pro** tier is served from
``https://pro-api.coingecko.com/api/v3`` with an ``x-cg-pro-api-key`` header, a
required key, higher rate limits, and the bulk/range endpoints used for
ingestion and backfill.

Unlike CoinMarketCap, CoinGecko returns raw JSON with no ``{"status","data"}``
envelope, so responses are returned verbatim. Consumers depend on the
vendor-neutral ``market_data_provider`` protocol (imported from ``cmc_client``),
never on CoinGecko directly, so a competing source can be substituted without
touching call sites. The shared ``ttl_cache`` is reused for credit conservation.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

import httpx

from cmc_client import market_data_provider, ttl_cache

PUBLIC_BASE_URL: str = "https://api.coingecko.com/api/v3"
PRO_BASE_URL: str = "https://pro-api.coingecko.com/api/v3"
DEMO_KEY_HEADER: str = "x-cg-demo-api-key"
PRO_KEY_HEADER: str = "x-cg-pro-api-key"


class CoingeckoError(RuntimeError):
    """Base error for all client failures."""


class CoingeckoRateLimitError(CoingeckoError):
    """Raised when the per-minute rate limit (HTTP 429) is exhausted.

    The free/Demo tier is rate-tight (on the order of thirty calls per minute),
    so this is the dominant failure mode on the public surface; back off and
    retry rather than hammering the endpoint.
    """


class CoingeckoAuthError(CoingeckoError):
    """Raised on an authentication or entitlement failure (HTTP 401/403).

    A missing required Pro key, a Demo key sent to the Pro host (or the reverse),
    or a Pro-gated endpoint called without entitlement all surface here.
    """


class _coingecko_base:
    """Shared HTTP plumbing for the CoinGecko tier clients.

    Holds the ``httpx`` lifecycle, the TTL cache, and a ``_get`` that returns the
    decoded JSON body verbatim. CoinGecko has no response envelope, so there is
    nothing to unwrap; a non-2xx status is mapped to a typed exception.
    """

    _http: httpx.Client
    _cache: ttl_cache

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "_coingecko_base":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(
        self, path: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        """Issue a GET and return the decoded JSON body.

        Raises:
            CoingeckoRateLimitError: On HTTP 429.
            CoingeckoAuthError: On HTTP 401/403.
            CoingeckoError: On any other non-success response or a non-JSON body.
        """
        response = self._http.get(path, params=dict(params or {}))
        if response.status_code == 429:
            raise CoingeckoRateLimitError("rate limit exceeded; back off and retry")
        if response.status_code in (401, 403):
            raise CoingeckoAuthError(
                f"authentication failed (http {response.status_code})"
            )
        try:
            body = response.json()
        except ValueError as exc:
            raise CoingeckoError(
                f"non-json response (http {response.status_code})"
            ) from exc
        if response.status_code >= 400:
            # CoinGecko occasionally carries an error document on a 4xx body.
            message = "unknown error"
            if isinstance(body, Mapping):
                status = body.get("status")
                if isinstance(status, Mapping):
                    message = str(status.get("error_message", message))
                else:
                    message = str(body.get("error", message))
            raise CoingeckoError(f"http {response.status_code}: {message}")
        return body


class coingecko_public_client(_coingecko_base):
    """Free/Demo-tier adapter for public consumption.

    Implements ``market_data_provider`` over the keyless public surface. A Demo
    key is optional; when supplied it is sent as ``x-cg-demo-api-key`` and lifts
    the anonymous rate limit, but every method works without one.

    Args:
        api_key: Optional Demo key. Falls back to the ``COINGECKO_DEMO_API_KEY``
            environment variable. May be omitted entirely.
        cache: Optional shared cache; a private one is created when omitted.
        timeout: Per-request timeout in seconds.
        client: Optional preconstructed ``httpx.Client`` for connection reuse.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        cache: ttl_cache | None = None,
        timeout: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("COINGECKO_DEMO_API_KEY", "")
        self._cache = cache if cache is not None else ttl_cache()
        self._http = client or httpx.Client(
            base_url=PUBLIC_BASE_URL,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        # Apply the auth header to the live client so the key is honoured even
        # when a preconstructed client is injected.
        if self._api_key:
            self._http.headers[DEMO_KEY_HEADER] = self._api_key

    def quotes_latest(self, ids: str, convert: str = "USD") -> dict[str, Any]:
        """Return latest prices for one or more CoinGecko ids.

        Satisfies the ``market_data_provider`` protocol against ``/simple/price``.
        Pass a comma-separated id list in a single call rather than looping; the
        result is cached for sixty seconds keyed by ``ids`` and ``convert``.

        Args:
            ids: Comma-separated CoinGecko asset ids (e.g. ``"bitcoin,ethereum"``).
            convert: Comma-separated fiat or crypto vs-currencies.
        """
        return self.simple_price(ids, vs_currencies=convert.lower())

    def simple_price(
        self,
        ids: str,
        vs_currencies: str = "usd",
        *,
        include_market_cap: bool = False,
        include_24hr_vol: bool = False,
        include_24hr_change: bool = False,
    ) -> dict[str, Any]:
        """Return simple prices for ``ids`` against ``vs_currencies``.

        Each id maps to a dict of vs-currency to price. Cached for sixty seconds
        keyed by every parameter so toggled flags do not collide.
        """
        key = (
            f"simple_price:{ids}:{vs_currencies}:{include_market_cap}"
            f":{include_24hr_vol}:{include_24hr_change}"
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = self._get(
            "/simple/price",
            {
                "ids": ids,
                "vs_currencies": vs_currencies,
                "include_market_cap": str(include_market_cap).lower(),
                "include_24hr_vol": str(include_24hr_vol).lower(),
                "include_24hr_change": str(include_24hr_change).lower(),
            },
        )
        result = data if isinstance(data, dict) else {}
        self._cache.put(key, result)
        return result

    def coins_markets(
        self,
        vs_currency: str = "usd",
        *,
        ids: str | None = None,
        per_page: int = 100,
        page: int = 1,
        order: str = "market_cap_desc",
    ) -> list[dict[str, Any]]:
        """Return a ranked slice of market data.

        Prefer a wide ``per_page`` over many small pages. Cached sixty seconds.
        """
        params: dict[str, Any] = {
            "vs_currency": vs_currency,
            "per_page": per_page,
            "page": page,
            "order": order,
        }
        if ids is not None:
            params["ids"] = ids
        data = self._get("/coins/markets", params)
        return data if isinstance(data, list) else []

    def coin(
        self,
        id: str,
        *,
        localization: bool = False,
        tickers: bool = False,
        market_data: bool = True,
    ) -> dict[str, Any]:
        """Return per-asset detail for ``id``.

        Cached for two minutes keyed by ``id`` and the included sections.
        """
        key = f"coin:{id}:{localization}:{tickers}:{market_data}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = self._get(
            f"/coins/{id}",
            {
                "localization": str(localization).lower(),
                "tickers": str(tickers).lower(),
                "market_data": str(market_data).lower(),
                "community_data": "false",
                "developer_data": "false",
            },
        )
        result = data if isinstance(data, dict) else {}
        self._cache.put(key, result, ttl=120.0)
        return result

    def coins_list(self, include_platform: bool = False) -> list[dict[str, Any]]:
        """Return the full id directory.

        This is the canonical map from human symbols to CoinGecko ids; persist it
        rather than guessing ids. Cached for one hour since it changes rarely.
        """
        key = f"coins_list:{include_platform}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = self._get(
            "/coins/list", {"include_platform": str(include_platform).lower()}
        )
        rows = data if isinstance(data, list) else []
        self._cache.put(key, rows, ttl=3600.0)
        return rows

    def asset_platforms(self) -> list[dict[str, Any]]:
        """Return all asset platforms (chains) with their CoinGecko ids.

        These platform ids are the stable join key for on-chain lookups; persist
        them rather than chain slugs. Cached for one hour.
        """
        cached = self._cache.get("asset_platforms")
        if cached is not None:
            return cached
        data = self._get("/asset_platforms")
        rows = data if isinstance(data, list) else []
        self._cache.put("asset_platforms", rows, ttl=3600.0)
        return rows

    def dex_networks_list(self) -> list[dict[str, Any]]:
        """Return chain/platform ids, satisfying ``market_data_provider``.

        Thin alias over :meth:`asset_platforms` so this client conforms to the
        vendor-neutral protocol that CoinMarketCap's ``dex_networks_list`` defines.
        """
        return self.asset_platforms()

    def market_chart(
        self, id: str, vs_currency: str = "usd", days: str = "1"
    ) -> dict[str, Any]:
        """Return a price/market-cap/volume chart for ``id``.

        The free tier permits this windowed chart; range-bounded backfill is a
        Pro endpoint on :class:`coingecko_pro_client`. Cached for two minutes.
        """
        key = f"market_chart:{id}:{vs_currency}:{days}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = self._get(
            f"/coins/{id}/market_chart",
            {"vs_currency": vs_currency, "days": days},
        )
        result = data if isinstance(data, dict) else {}
        self._cache.put(key, result, ttl=120.0)
        return result


class coingecko_pro_client(coingecko_public_client):
    """Pro-tier adapter for ingestion and backfill.

    Inherits the consumption methods but routes them against the Pro host with
    the ``x-cg-pro-api-key`` header, and adds the bulk/range endpoints that the
    free tier does not serve. The Pro key is required; the constructor raises
    :class:`CoingeckoAuthError` when it is absent.

    Args:
        api_key: Pro API key. Falls back to the ``COINGECKO_API_KEY`` environment
            variable. Required.
        cache: Optional shared cache; a private one is created when omitted.
        timeout: Per-request timeout in seconds; defaults higher for backfill.
        client: Optional preconstructed ``httpx.Client`` for connection reuse.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        cache: ttl_cache | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        resolved = api_key or os.environ.get("COINGECKO_API_KEY", "")
        if not resolved:
            raise CoingeckoAuthError("COINGECKO_API_KEY is required for the Pro tier")
        # Bypass the public constructor: the Pro tier uses a different host,
        # header, and key, and must not fall back to the keyless public base.
        self._api_key = resolved
        self._cache = cache if cache is not None else ttl_cache()
        self._http = client or httpx.Client(
            base_url=PRO_BASE_URL,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )
        # Apply the Pro key header to the live client (covers injected clients).
        self._http.headers[PRO_KEY_HEADER] = resolved

    def market_chart_range(
        self, id: str, vs_currency: str, from_ts: int, to_ts: int
    ) -> dict[str, Any]:
        """Return a range-bounded price chart for backfill.

        Pro-gated; a Demo key yields :class:`CoingeckoAuthError`. Not cached,
        since backfill windows are addressed once.

        Args:
            id: CoinGecko asset id.
            vs_currency: Quote currency.
            from_ts: Inclusive UNIX start timestamp (seconds).
            to_ts: Inclusive UNIX end timestamp (seconds).
        """
        data = self._get(
            f"/coins/{id}/market_chart/range",
            {"vs_currency": vs_currency, "from": from_ts, "to": to_ts},
        )
        return data if isinstance(data, dict) else {}

    def ohlc(
        self, id: str, vs_currency: str = "usd", days: str = "1"
    ) -> list[list[Any]]:
        """Return OHLC candles for ``id``.

        Pro-gated. Each row is ``[timestamp, open, high, low, close]``.
        """
        data = self._get(
            f"/coins/{id}/ohlc", {"vs_currency": vs_currency, "days": days}
        )
        return data if isinstance(data, list) else []

    def coins_markets_paged(
        self, vs_currency: str = "usd", *, page: int = 1, per_page: int = 250
    ) -> list[dict[str, Any]]:
        """Return a wide ingestion page of market data.

        Pro-gated paging convenience: ``per_page`` defaults to the Pro maximum to
        minimise the number of calls a full-market sweep requires.
        """
        data = self._get(
            "/coins/markets",
            {"vs_currency": vs_currency, "page": page, "per_page": per_page},
        )
        return data if isinstance(data, list) else []

    def onchain(
        self, path_suffix: str, params: Mapping[str, Any] | None = None
    ) -> Any:
        """Call an on-chain (GeckoTerminal) endpoint under ``/onchain``.

        Pro-gated. The on-chain sub-paths shift over time, so the suffix is
        passed through rather than enumerated here; supply the path beneath
        ``/onchain`` (e.g. ``"networks"`` or ``"networks/eth/pools"``).
        """
        suffix = path_suffix.lstrip("/")
        return self._get(f"/onchain/{suffix}", params)
