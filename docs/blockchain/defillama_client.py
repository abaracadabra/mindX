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

"""DefiLlama DeFi-data client with a free/Pro tier split.

DefiLlama is the open DeFi data plane: TVL, prices, stablecoins, yields, fees,
volumes, and bridges. This module mirrors ``cmc_client`` for that surface and
expresses the consumption-versus-ingestion boundary as two distinct classes.
The class a caller holds *is* the access tier.

The two tiers are, by DefiLlama's own design, *entirely separate services* and
must not be mixed:

* The **free** tier takes no key and is served from several host roots —
  ``api.llama.fi`` (TVL/protocols), ``coins.llama.fi`` (prices),
  ``stablecoins.llama.fi``, ``yields.llama.fi``, and ``bridges.llama.fi``. It is
  the surface for public consumption and is rate-limited per IP. Because the
  free tier spans several hosts, this client builds absolute per-call URLs
  rather than binding a single base URL.
* The **Pro** tier is served from ``https://pro-api.llama.fi/{API_KEY}`` with the
  **API key embedded in the URL path, not a header**, and exposes the ingestion
  endpoints (emissions, hacks, raises, treasuries, ETFs, extended yields). The
  Pro client never falls back to a free host, and the full base URL — which
  carries the secret — is never logged.

DefiLlama returns raw JSON with no envelope and has no credit-exhaustion concept
(there is no analogue to CoinMarketCap's HTTP 402 / error code 1008), so the
error tree carries only rate-limit and auth failures. Coin identifiers use the
``{chain}:{address}`` format, e.g. ``ethereum:0xA0b8...``. Consumers depend on
the vendor-neutral ``tvl_data_provider`` / ``price_data_provider`` protocols
defined here, and the shared ``ttl_cache`` is reused for conservation.

The official API reference is the integration-guide PDF under
``docs/publications/``; this module documents only the client design.
"""

from __future__ import annotations

import os
import time
from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable

import httpx

from cmc_client import ttl_cache

FREE_HOSTS: dict[str, str] = {
    "tvl": "https://api.llama.fi",
    "coins": "https://coins.llama.fi",
    "stablecoins": "https://stablecoins.llama.fi",
    "yields": "https://yields.llama.fi",
    "bridges": "https://bridges.llama.fi",
}
PRO_BASE_TEMPLATE: str = "https://pro-api.llama.fi/{api_key}"
COIN_ID_FORMAT: str = "{chain}:{address}"  # e.g. ethereum:0xA0b8...


@runtime_checkable
class tvl_data_provider(Protocol):
    """Vendor-neutral contract for total-value-locked data.

    DefiLlama is the reference implementation, but the protocol names only the
    shapes so an on-chain aggregator or a competing source can be substituted
    without touching call sites.
    """

    def protocols(self) -> list[dict[str, Any]]: ...

    def protocol(self, slug: str) -> dict[str, Any]: ...

    def chains(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class price_data_provider(Protocol):
    """Vendor-neutral contract for current token prices.

    Distinct from CoinMarketCap's quote-by-id seam: prices are keyed by the
    ``{chain}:{address}`` coin identifier that DefiLlama's coin surface uses.
    """

    def prices_current(self, coins: str) -> dict[str, Any]: ...


class DefillamaError(RuntimeError):
    """Base error for all client failures."""


class DefillamaRateLimitError(DefillamaError):
    """Raised when the per-minute rate limit (HTTP 429) is exhausted.

    The free tier permits roughly five hundred requests per minute per IP; back
    off and retry on exhaustion.
    """


class DefillamaAuthError(DefillamaError):
    """Raised on an authentication failure (HTTP 401/403).

    Surfaces when a Pro key embedded in the path is missing or invalid.
    """


class _defillama_base:
    """Shared HTTP plumbing for the DefiLlama tier clients.

    Holds the ``httpx`` lifecycle, the TTL cache, and a ``_get`` that accepts an
    absolute URL — the free tier spans several hosts, so no single ``base_url``
    suffices. The body is returned verbatim; DefiLlama has no envelope.
    """

    _http: httpx.Client
    _cache: ttl_cache
    _max_retries: int

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "_defillama_base":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(self, url: str, params: Mapping[str, Any] | None = None) -> Any:
        """Issue a GET to an absolute ``url`` and return the decoded JSON body.

        A bounded exponential backoff is applied to HTTP 429 and 5xx responses;
        ``_max_retries`` of zero disables it (the consumption default). After the
        retries are exhausted the terminal status is raised as a typed error.

        Raises:
            DefillamaRateLimitError: On HTTP 429 after retries.
            DefillamaAuthError: On HTTP 401/403.
            DefillamaError: On any other non-success response or a non-JSON body.
        """
        query = dict(params or {})
        attempt = 0
        while True:
            response = self._http.get(url, params=query)
            status = response.status_code
            if status == 429 or status >= 500:
                if attempt < self._max_retries:
                    time.sleep(0.5 * (2**attempt))
                    attempt += 1
                    continue
                if status == 429:
                    raise DefillamaRateLimitError(
                        "rate limit exceeded; back off and retry"
                    )
            if status in (401, 403):
                raise DefillamaAuthError(f"authentication failed (http {status})")
            if status >= 400:
                raise DefillamaError(f"request failed (http {status})")
            try:
                return response.json()
            except ValueError as exc:
                raise DefillamaError(f"non-json response (http {status})") from exc


class defillama_public_client(_defillama_base):
    """Free-tier adapter for public consumption (no key, multi-host).

    Implements ``tvl_data_provider`` and ``price_data_provider`` against the
    keyless public surface. Routes each method to the correct host root.

    Args:
        cache: Optional shared cache; a private one is created when omitted.
        timeout: Per-request timeout in seconds.
        client: Optional preconstructed ``httpx.Client``. It must be configured
            **without** a ``base_url`` because methods issue absolute URLs across
            several hosts.
    """

    def __init__(
        self,
        *,
        cache: ttl_cache | None = None,
        timeout: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._cache = cache if cache is not None else ttl_cache()
        self._max_retries = 0
        self._http = client or httpx.Client(
            headers={"Accept": "application/json"}, timeout=timeout
        )

    @staticmethod
    def _url(host_key: str, path: str) -> str:
        """Join a free-tier host root with ``path``."""
        return f"{FREE_HOSTS[host_key]}{path}"

    def _cached(
        self, key: str, host_key: str, path: str, ttl: float
    ) -> Any:
        """Return a cached body for ``key`` or fetch, cache, and return it."""
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = self._get(self._url(host_key, path))
        self._cache.put(key, data, ttl=ttl)
        return data

    # -- TVL (api.llama.fi) ------------------------------------------------

    def protocols(self) -> list[dict[str, Any]]:
        """Return all protocols with their current TVL. Cached ten minutes."""
        data = self._cached("protocols", "tvl", "/protocols", 600.0)
        return data if isinstance(data, list) else []

    def protocol(self, slug: str) -> dict[str, Any]:
        """Return historical TVL of a protocol, broken down by token and chain.

        Cached five minutes keyed by ``slug``.
        """
        data = self._cached(f"protocol:{slug}", "tvl", f"/protocol/{slug}", 300.0)
        return data if isinstance(data, dict) else {}

    def tvl(self, slug: str) -> Any:
        """Return the simplified current TVL of a protocol (a number).

        Cached sixty seconds keyed by ``slug``.
        """
        return self._cached(f"tvl:{slug}", "tvl", f"/tvl/{slug}", 60.0)

    def chains(self) -> list[dict[str, Any]]:
        """Return the current TVL of all chains. Cached ten minutes."""
        data = self._cached("chains", "tvl", "/v2/chains", 600.0)
        return data if isinstance(data, list) else []

    def historical_chain_tvl(self, chain: str | None = None) -> list[dict[str, Any]]:
        """Return historical TVL across all chains, or one chain when named.

        Cached five minutes keyed by ``chain``.
        """
        path = "/v2/historicalChainTvl"
        if chain is not None:
            path = f"{path}/{chain}"
        data = self._cached(f"hist_chain_tvl:{chain}", "tvl", path, 300.0)
        return data if isinstance(data, list) else []

    def charts(self, chain: str) -> list[dict[str, Any]]:
        """Return aggregate chart data for ``chain``. Cached five minutes."""
        data = self._cached(f"charts:{chain}", "tvl", f"/charts/{chain}", 300.0)
        return data if isinstance(data, list) else []

    def overview_fees(self, chain: str | None = None) -> dict[str, Any]:
        """Return the fees/revenue overview, optionally filtered by ``chain``.

        Cached five minutes keyed by ``chain``.
        """
        path = "/overview/fees"
        if chain is not None:
            path = f"{path}/{chain}"
        data = self._cached(f"overview_fees:{chain}", "tvl", path, 300.0)
        return data if isinstance(data, dict) else {}

    def overview_dexs(self, chain: str | None = None) -> dict[str, Any]:
        """Return the DEX-volume overview, optionally filtered by ``chain``.

        Cached five minutes keyed by ``chain``.
        """
        path = "/overview/dexs"
        if chain is not None:
            path = f"{path}/{chain}"
        data = self._cached(f"overview_dexs:{chain}", "tvl", path, 300.0)
        return data if isinstance(data, dict) else {}

    def summary_fees(self, protocol: str) -> dict[str, Any]:
        """Return per-protocol fees/revenue with history. Cached five minutes."""
        data = self._cached(
            f"summary_fees:{protocol}", "tvl", f"/summary/fees/{protocol}", 300.0
        )
        return data if isinstance(data, dict) else {}

    # -- Coins / prices (coins.llama.fi) -----------------------------------

    def prices_current(self, coins: str) -> dict[str, Any]:
        """Return current prices for comma-separated ``{chain}:{address}`` coins.

        Satisfies ``price_data_provider``. Pass a comma-separated coin list in a
        single call rather than looping. Cached sixty seconds keyed by ``coins``.
        """
        data = self._cached(
            f"prices_current:{coins}", "coins", f"/prices/current/{coins}", 60.0
        )
        return data if isinstance(data, dict) else {}

    def prices_historical(self, timestamp: int, coins: str) -> dict[str, Any]:
        """Return prices for ``coins`` at a UNIX ``timestamp``. Cached five minutes."""
        data = self._cached(
            f"prices_hist:{timestamp}:{coins}",
            "coins",
            f"/prices/historical/{timestamp}/{coins}",
            300.0,
        )
        return data if isinstance(data, dict) else {}

    def prices_first(self, coins: str) -> dict[str, Any]:
        """Return the earliest recorded price for ``coins``. Cached one hour."""
        data = self._cached(
            f"prices_first:{coins}", "coins", f"/prices/first/{coins}", 3600.0
        )
        return data if isinstance(data, dict) else {}

    def prices_chart(self, coins: str) -> dict[str, Any]:
        """Return a price chart at regular intervals for ``coins``.

        Cached five minutes keyed by ``coins``.
        """
        data = self._cached(
            f"prices_chart:{coins}", "coins", f"/chart/{coins}", 300.0
        )
        return data if isinstance(data, dict) else {}

    def prices_percentage(self, coins: str) -> dict[str, Any]:
        """Return percentage price change over time for ``coins``.

        Cached two minutes keyed by ``coins``.
        """
        data = self._cached(
            f"prices_pct:{coins}", "coins", f"/percentage/{coins}", 120.0
        )
        return data if isinstance(data, dict) else {}

    def block(self, chain: str, timestamp: int) -> dict[str, Any]:
        """Return the block closest to ``timestamp`` on ``chain``.

        Cached ten minutes keyed by ``chain`` and ``timestamp``.
        """
        data = self._cached(
            f"block:{chain}:{timestamp}",
            "coins",
            f"/block/{chain}/{timestamp}",
            600.0,
        )
        return data if isinstance(data, dict) else {}

    # -- Stablecoins (stablecoins.llama.fi) --------------------------------

    def stablecoins(self, include_prices: bool = True) -> dict[str, Any]:
        """Return all stablecoins with circulating amounts. Cached five minutes."""
        key = f"stablecoins:{include_prices}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        url = self._url("stablecoins", "/stablecoins")
        data = self._get(url, {"includePrices": str(include_prices).lower()})
        result = data if isinstance(data, dict) else {}
        self._cache.put(key, result, ttl=300.0)
        return result

    def stablecoin_charts_all(self) -> list[dict[str, Any]]:
        """Return the historical aggregate mcap of all stablecoins.

        Cached five minutes.
        """
        data = self._cached(
            "stablecoin_charts_all", "stablecoins", "/stablecoincharts/all", 300.0
        )
        return data if isinstance(data, list) else []

    def stablecoin(self, asset_id: str) -> dict[str, Any]:
        """Return historical mcap and chain distribution of a stablecoin.

        Cached five minutes keyed by ``asset_id``.
        """
        data = self._cached(
            f"stablecoin:{asset_id}",
            "stablecoins",
            f"/stablecoin/{asset_id}",
            300.0,
        )
        return data if isinstance(data, dict) else {}

    def stablecoin_chains(self) -> list[dict[str, Any]]:
        """Return the current stablecoin mcap sum per chain. Cached five minutes."""
        data = self._cached(
            "stablecoin_chains", "stablecoins", "/stablecoinchains", 300.0
        )
        return data if isinstance(data, list) else []

    # -- Yields (yields.llama.fi) ------------------------------------------

    def yield_pools(self) -> dict[str, Any]:
        """Return all yield pools with APY and TVL. Cached ten minutes."""
        data = self._cached("yield_pools", "yields", "/pools", 600.0)
        return data if isinstance(data, dict) else {}

    def yield_chart(self, pool_id: str) -> dict[str, Any]:
        """Return historical APY and TVL of a pool by UUID. Cached five minutes."""
        data = self._cached(
            f"yield_chart:{pool_id}", "yields", f"/chart/{pool_id}", 300.0
        )
        return data if isinstance(data, dict) else {}

    # -- Bridges (bridges.llama.fi) ----------------------------------------

    def bridges(self) -> dict[str, Any]:
        """Return the list of bridges with summary metadata. Cached ten minutes."""
        data = self._cached("bridges", "bridges", "/bridges", 600.0)
        return data if isinstance(data, dict) else {}


class defillama_pro_client(_defillama_base):
    """Pro-tier adapter for ingestion (key embedded in the URL path).

    The Pro tier is a separate service from the free hosts and exposes endpoints
    the free tier does not serve. The key lives in the base path; it is never
    sent as a header and the full base URL is never logged.

    Args:
        api_key: Pro API key. Falls back to the ``DEFILLAMA_API_KEY`` environment
            variable. Required.
        cache: Optional shared cache; a private one is created when omitted.
        timeout: Per-request timeout in seconds; defaults higher for ingestion.
        client: Optional preconstructed ``httpx.Client`` whose ``base_url`` is
            the Pro path; supplied chiefly for tests.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        cache: ttl_cache | None = None,
        timeout: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        resolved = api_key or os.environ.get("DEFILLAMA_API_KEY", "")
        if not resolved:
            raise DefillamaError("DEFILLAMA_API_KEY is required for the Pro tier")
        self._api_key = resolved
        self._cache = cache if cache is not None else ttl_cache()
        self._max_retries = 4
        self._http = client or httpx.Client(
            base_url=PRO_BASE_TEMPLATE.format(api_key=resolved),
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

    def _fetch(self, path: str, ttl: float) -> Any:
        """Return a cached Pro body for ``path`` or fetch, cache, and return it.

        The cache key omits the api key so the secret never lands in cache state.
        """
        cached = self._cache.get(f"pro:{path}")
        if cached is not None:
            return cached
        data = self._get(path)
        self._cache.put(f"pro:{path}", data, ttl=ttl)
        return data

    def emissions(self) -> dict[str, Any]:
        """Return unlock/emission schedules across protocols. Cached five minutes."""
        data = self._fetch("/api/emissions", 300.0)
        return data if isinstance(data, dict) else {}

    def categories(self) -> dict[str, Any]:
        """Return protocol category rankings. Cached ten minutes."""
        data = self._fetch("/api/categories", 600.0)
        return data if isinstance(data, dict) else {}

    def oracles(self) -> dict[str, Any]:
        """Return TVS secured per oracle. Cached ten minutes."""
        data = self._fetch("/api/oracles", 600.0)
        return data if isinstance(data, dict) else {}

    def hacks(self) -> list[dict[str, Any]]:
        """Return the historical hacks dataset. Cached ten minutes."""
        data = self._fetch("/api/hacks", 600.0)
        return data if isinstance(data, list) else []

    def raises(self) -> dict[str, Any]:
        """Return the funding-rounds dataset. Cached ten minutes."""
        data = self._fetch("/api/raises", 600.0)
        return data if isinstance(data, dict) else {}

    def treasuries(self) -> list[dict[str, Any]]:
        """Return protocol treasury balances. Cached ten minutes."""
        data = self._fetch("/api/treasuries", 600.0)
        return data if isinstance(data, list) else []

    def entities(self) -> list[dict[str, Any]]:
        """Return tracked entities. Cached ten minutes."""
        data = self._fetch("/api/entities", 600.0)
        return data if isinstance(data, list) else []

    def inflows(self, protocol: str, timestamp: int) -> dict[str, Any]:
        """Return token inflows for ``protocol`` since ``timestamp``.

        Cached two minutes keyed by ``protocol`` and ``timestamp``.
        """
        data = self._fetch(f"/api/inflows/{protocol}/{timestamp}", 120.0)
        return data if isinstance(data, dict) else {}

    def yields_pools_old(self) -> dict[str, Any]:
        """Return the extended (legacy-shaped) yield pools. Cached five minutes."""
        data = self._fetch("/yields/poolsOld", 300.0)
        return data if isinstance(data, dict) else {}

    def yields_perps(self) -> dict[str, Any]:
        """Return perpetuals funding/yield data. Cached two minutes."""
        data = self._fetch("/yields/perps", 120.0)
        return data if isinstance(data, dict) else {}

    def etfs_snapshot(self) -> dict[str, Any]:
        """Return the current ETF snapshot. Cached five minutes."""
        data = self._fetch("/etfs/snapshot", 300.0)
        return data if isinstance(data, dict) else {}

    def etfs_flows(self) -> dict[str, Any]:
        """Return ETF flows. Cached five minutes."""
        data = self._fetch("/etfs/flows", 300.0)
        return data if isinstance(data, dict) else {}

    def historical_liquidity(self, token: str) -> list[dict[str, Any]]:
        """Return historical on-chain liquidity for ``token``. Cached five minutes."""
        data = self._fetch(f"/api/historicalLiquidity/{token}", 300.0)
        return data if isinstance(data, list) else []
