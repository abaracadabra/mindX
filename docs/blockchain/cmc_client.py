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

"""Provider-agnostic market-data client with a CoinMarketCap implementation.

This module defines a narrow ``market_data_provider`` protocol and a concrete
CoinMarketCap adapter against it. Consumers such as mindX depend on the
protocol, never on the vendor, so a competing source (CoinGecko, on-chain
oracle, Blockscout) can be substituted without touching call sites.

Three access models are supported by CoinMarketCap and reflected here. The
key-authenticated REST surface is the production default and is implemented in
full. The keyless public surface is the same REST shape against a different
base path and is exposed through a constructor flag. The x402 pay-per-request
surface settles in USDC on Base (eip155:8453); its challenge decoding is
implemented and verified offline, while signature attachment is delegated to an
injected wallet callable so this module carries no chain dependency.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import httpx


def load_env() -> None:
    """Load key/value pairs from a ``.env`` file into ``os.environ``.

    Every client in this package reads its credentials from the environment
    (``CMC_PRO_API_KEY``, ``COINGECKO_API_KEY``, ``DEFILLAMA_API_KEY``, and the
    x402 wallet key). This loads a project ``.env`` so those reads resolve
    without the caller having to export anything first. It is a no-op when
    ``python-dotenv`` is not installed, and it does **not** override variables
    already set in the process environment (an explicit export still wins). The
    sibling clients import this module, so calling it here covers all of them.
    """
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return
    # find_dotenv walks up from this file, so the project .env is found
    # regardless of the working directory the client is invoked from.
    load_dotenv(find_dotenv(usecwd=False), override=False)


load_env()

PRO_BASE_URL: str = "https://pro-api.coinmarketcap.com"
KEYLESS_BASE_URL: str = "https://pro-api.coinmarketcap.com/trial-pro-api"
X402_BASE_URL: str = "https://pro-api.coinmarketcap.com"
API_KEY_HEADER: str = "X-CMC_PRO_API_KEY"

BASE_USDC_NETWORK: str = "eip155:8453"
BASE_USDC_ASSET: str = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


class CmcError(RuntimeError):
    """Base error for all client failures."""


class CmcRateLimitError(CmcError):
    """Raised when the per-minute rate limit (HTTP 429) is exhausted."""


class CmcCreditError(CmcError):
    """Raised when the monthly credit allotment is exhausted (HTTP 402/1008)."""


class CmcPaymentRequired(CmcError):
    """Raised on an x402 HTTP 402 challenge so the caller can settle and retry.

    Attributes:
        challenge: Decoded ``payment-required`` payload describing the accepted
            settlement terms (network, asset, amount, payee).
    """

    def __init__(self, challenge: Mapping[str, Any]) -> None:
        self.challenge = dict(challenge)
        first = (self.challenge.get("accepts") or [{}])[0]
        super().__init__(
            f"payment required: {first.get('amount')} on {first.get('network')}"
        )


@runtime_checkable
class market_data_provider(Protocol):
    """Vendor-neutral contract consumed by mindX and other projects.

    Methods return decoded JSON ``data`` payloads. Implementations are free to
    cache, batch, or route across access models provided the shapes hold.
    """

    def quotes_latest(self, ids: str, convert: str = "USD") -> dict[str, Any]: ...

    def dex_networks_list(self) -> list[dict[str, Any]]: ...


@dataclass(slots=True)
class _cache_entry:
    """Single time-to-live cache record."""

    value: Any
    expires_at: float


@dataclass(slots=True)
class ttl_cache:
    """Minimal in-process time-to-live cache for credit conservation.

    A single avoided ``quotes_latest`` call on the Basic plan reclaims credits
    that would otherwise be spent on duplicate work. The cache is deliberately
    process-local and unbounded by count; pair it with short ttls rather than
    eviction policy for market data.
    """

    default_ttl: float = 60.0
    _store: dict[str, _cache_entry] = field(default_factory=dict)

    def get(self, key: str) -> Any | None:
        """Return a live value for ``key`` or ``None`` when absent or expired."""
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return entry.value

    def put(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store ``value`` under ``key`` for ``ttl`` seconds."""
        horizon = time.monotonic() + (self.default_ttl if ttl is None else ttl)
        self._store[key] = _cache_entry(value=value, expires_at=horizon)


def decode_payment_challenge(header_value: str) -> dict[str, Any]:
    """Decode a base64 ``payment-required`` header into its JSON terms.

    The CoinMarketCap x402 surface returns settlement terms as a base64url
    blob in the ``payment-required`` response header alongside the HTTP 402
    status. The decoded document carries an ``accepts`` array; the first entry
    names the chain (``network``), token (``asset``), and minor-unit ``amount``.

    Args:
        header_value: Raw header string from the 402 response.

    Returns:
        The decoded challenge document.

    Raises:
        CmcError: If the header is not valid base64 or not valid JSON.
    """
    padded = header_value + "=" * (-len(header_value) % 4)
    try:
        raw = base64.b64decode(padded)
    except (binascii.Error, ValueError) as exc:
        raise CmcError("malformed x402 payment-required header") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CmcError("x402 challenge is not valid json") from exc


class cmc_client:
    """CoinMarketCap adapter implementing ``market_data_provider``.

    Args:
        api_key: Pro API key. Falls back to the ``CMC_PRO_API_KEY`` environment
            variable. May be omitted only when ``keyless`` is set.
        keyless: Route against the keyless public base path. The endpoint
            subset is fixed by CoinMarketCap and historical data is excluded.
        cache: Optional shared cache; a private one is created when omitted.
        timeout: Per-request timeout in seconds.
        client: Optional preconstructed ``httpx.Client`` for connection reuse.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        keyless: bool = False,
        cache: ttl_cache | None = None,
        timeout: float = 15.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._keyless = keyless
        self._api_key = api_key or os.environ.get("CMC_PRO_API_KEY", "")
        if not keyless and not self._api_key:
            raise CmcError("CMC_PRO_API_KEY is required unless keyless=True")
        self._base = KEYLESS_BASE_URL if keyless else PRO_BASE_URL
        self._cache = cache if cache is not None else ttl_cache()
        headers = {"Accept": "application/json"}
        if not keyless:
            headers[API_KEY_HEADER] = self._api_key
        self._http = client or httpx.Client(
            base_url=self._base, headers=headers, timeout=timeout
        )

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "cmc_client":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(
        self, path: str, params: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        """Issue a GET and unwrap the CoinMarketCap envelope.

        The vendor wraps every payload as ``{"status": {...}, "data": {...}}``.
        A non-zero ``status.error_code`` is surfaced as a typed exception; the
        bare ``data`` body is returned on success.

        Raises:
            CmcRateLimitError: On HTTP 429.
            CmcCreditError: On credit exhaustion (HTTP 402 or error_code 1008).
            CmcError: On any other non-success response.
        """
        response = self._http.get(path, params=dict(params or {}))
        if response.status_code == 429:
            raise CmcRateLimitError("rate limit exceeded; back off and retry")
        if response.status_code == 402:
            raise CmcCreditError("monthly credit allotment exhausted")
        try:
            body = response.json()
        except ValueError as exc:
            raise CmcError(f"non-json response (http {response.status_code})") from exc
        status = body.get("status", {})
        code = status.get("error_code", 0)
        if code:
            message = status.get("error_message", "unknown error")
            if code == 1008:
                raise CmcCreditError(message)
            raise CmcError(f"cmc error {code}: {message}")
        return body.get("data", {})

    def quotes_latest(self, ids: str, convert: str = "USD") -> dict[str, Any]:
        """Return latest quotes for one or more CoinMarketCap ids.

        Each conversion currency beyond the first consumes additional credits,
        so ``convert`` is kept single by default. Results are cached for the
        provider default ttl keyed by ``ids`` and ``convert``.

        Args:
            ids: Comma-separated CoinMarketCap numeric ids (e.g. ``"1,1027"``).
            convert: Comma-separated fiat or crypto symbols.
        """
        key = f"quotes:{ids}:{convert}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        data = self._get(
            "/v2/cryptocurrency/quotes/latest", {"id": ids, "convert": convert}
        )
        self._cache.put(key, data)
        return data

    def listings_latest(
        self, start: int = 1, limit: int = 100, convert: str = "USD"
    ) -> list[dict[str, Any]]:
        """Return a ranked slice of the latest market listings.

        Pagination beyond a single page consumes credits per page; prefer wide
        ``limit`` values over many small pages.
        """
        data = self._get(
            "/v1/cryptocurrency/listings/latest",
            {"start": start, "limit": limit, "convert": convert},
        )
        return data if isinstance(data, list) else []

    def dex_networks_list(self) -> list[dict[str, Any]]:
        """Return all DEX networks with their CoinMarketCap ids.

        These ids are the canonical join key for chain mapping; persist them
        rather than chain slugs so downstream DEX calls remain stable. The list
        is cached for one hour since it changes rarely.
        """
        cached = self._cache.get("dex:networks")
        if cached is not None:
            return cached
        data = self._get("/v4/dex/networks/list")
        rows = data if isinstance(data, list) else []
        self._cache.put("dex:networks", rows, ttl=3600.0)
        return rows

    def dex_listings_quotes(
        self, network_id: int | None = None, convert: str = "USD"
    ) -> list[dict[str, Any]]:
        """Return decentralized-exchange listings with aggregate market data."""
        params: dict[str, Any] = {"convert": convert}
        if network_id is not None:
            params["network_id"] = network_id
        data = self._get("/v4/dex/listings/quotes", params)
        return data if isinstance(data, list) else []

    def dex_pairs_ohlcv_historical(
        self,
        contract_address: str,
        network_id: int,
        time_period: str = "daily",
        convert: str = "USD",
    ) -> dict[str, Any]:
        """Return historical OHLCV candles for a spot pair.

        Historical depth is plan-gated; the Basic plan returns no history.
        """
        return self._get(
            "/v4/dex/pairs/ohlcv/historical",
            {
                "contract_address": contract_address,
                "network_id": network_id,
                "time_period": time_period,
                "convert": convert,
            },
        )

    def dex_pairs_trade_latest(
        self, contract_address: str, network_id: int, convert: str = "USD"
    ) -> list[dict[str, Any]]:
        """Return up to the latest 100 trades for a spot pair.

        Each trade carries an on-chain transaction hash for settlement audit.
        """
        data = self._get(
            "/v4/dex/pairs/trade/latest",
            {
                "contract_address": contract_address,
                "network_id": network_id,
                "convert": convert,
            },
        )
        return data if isinstance(data, list) else []


class cmc_x402_client:
    """Pay-per-request client for the x402 surface (USDC on Base).

    No API key or account is used; access control is the settlement itself.
    Signing is delegated to ``wallet_sign`` so this class holds no chain or key
    material — see ``x402_signer.x402_wallet_signer`` for the concrete,
    signature-based Base-USDC wallet that reads its key from ``.env``. The flow
    is: issue the request, receive HTTP 402 with a ``payment-required`` header,
    decode the terms, sign them with the wallet, and resend the identical
    request carrying the signed authorization in the x402 ``X-PAYMENT`` header.

    Args:
        wallet_sign: Callable mapping a decoded challenge to the ``X-PAYMENT``
            payload string — ``base64(JSON({x402Version, scheme, network,
            payload}))`` carrying an EIP-3009 ``transferWithAuthorization``
            signature. An empty return means the wallet declined. Algorand x402
            rails (Parsec, GoPlausible) cannot settle this surface because the
            challenge names Base; route Algorand-native payment flows elsewhere.
        timeout: Per-request timeout in seconds.
        payment_header: Header carrying the signed payload. Defaults to the
            canonical x402 ``X-PAYMENT``; override only if a server documents a
            different name.
    """

    def __init__(
        self,
        wallet_sign: Callable[[Mapping[str, Any]], str],
        *,
        timeout: float = 30.0,
        payment_header: str = "X-PAYMENT",
    ) -> None:
        self._sign = wallet_sign
        self._payment_header = payment_header
        self._http = httpx.Client(
            base_url=X402_BASE_URL,
            headers={"Accept": "application/json"},
            timeout=timeout,
        )

    def close(self) -> None:
        """Release the underlying HTTP connection pool."""
        self._http.close()

    def __enter__(self) -> "cmc_x402_client":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        """Fetch ``path`` settling payment on demand.

        Raises:
            CmcPaymentRequired: If a 402 is returned without a decodable header
                or the wallet declines to sign.
            CmcError: On any non-success terminal response.
        """
        query = dict(params or {})
        first = self._http.get(path, params=query)
        if first.status_code != 402:
            return self._unwrap(first)
        header = first.headers.get("payment-required", "")
        challenge = decode_payment_challenge(header)
        payment = self._sign(challenge)
        if not payment:
            raise CmcPaymentRequired(challenge)
        second = self._http.get(
            path, params=query, headers={self._payment_header: payment}
        )
        return self._unwrap(second)

    @staticmethod
    def _unwrap(response: httpx.Response) -> dict[str, Any]:
        """Validate and unwrap an x402 terminal response."""
        if response.status_code != 200:
            raise CmcError(f"x402 request failed (http {response.status_code})")
        body = response.json()
        return body.get("data", body)
