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

"""Offline tests for ``coingecko_client``.

Every request is served by an injected ``httpx.MockTransport``; no network is
touched. The injected-client seam in each constructor is the test boundary.
"""

from __future__ import annotations

import httpx
import pytest

from cmc_client import market_data_provider, ttl_cache
from coingecko_client import (
    DEMO_KEY_HEADER,
    PRO_KEY_HEADER,
    CoingeckoAuthError,
    CoingeckoError,
    CoingeckoRateLimitError,
    coingecko_pro_client,
    coingecko_public_client,
)


def _client(handler, **kwargs):
    """Build a public client whose transport is driven by ``handler``."""
    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        base_url="https://api.coingecko.com/api/v3",
        transport=transport,
    )
    return coingecko_public_client(client=http, **kwargs)


def test_public_conforms_to_market_data_provider():
    assert isinstance(coingecko_public_client(), market_data_provider)


def test_quotes_latest_returns_raw_json_no_unwrap():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        # CoinGecko returns a bare body, never a {"status","data"} envelope.
        return httpx.Response(200, json={"bitcoin": {"usd": 42000}})

    client = _client(handler)
    out = client.quotes_latest("bitcoin", convert="USD")
    assert out == {"bitcoin": {"usd": 42000}}
    assert "/simple/price" in captured["url"]
    assert "ids=bitcoin" in captured["url"]
    assert "vs_currencies=usd" in captured["url"]


def test_demo_key_header_sent_when_present():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["demo"] = request.headers.get(DEMO_KEY_HEADER)
        seen["pro"] = request.headers.get(PRO_KEY_HEADER)
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        base_url="https://api.coingecko.com/api/v3", transport=transport
    )
    client = coingecko_public_client("demo-key-123", client=http)
    client.simple_price("bitcoin")
    assert seen["demo"] == "demo-key-123"
    assert seen["pro"] is None


def test_public_client_works_keyless():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get(DEMO_KEY_HEADER) is None
        return httpx.Response(200, json={"ethereum": {"usd": 3000}})

    client = _client(handler)
    assert client.simple_price("ethereum") == {"ethereum": {"usd": 3000}}


def test_cache_hit_avoids_second_request():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"bitcoin": {"usd": 1}})

    cache = ttl_cache()
    client = _client(handler, cache=cache)
    client.simple_price("bitcoin")
    client.simple_price("bitcoin")
    assert calls["n"] == 1


def test_cache_expiry_refetches():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json={"bitcoin": {"usd": 1}})

    cache = ttl_cache()
    client = _client(handler, cache=cache)
    client.simple_price("bitcoin")
    # Force the entry stale without sleeping.
    for entry in cache._store.values():
        entry.expires_at = 0.0
    client.simple_price("bitcoin")
    assert calls["n"] == 2


def test_rate_limit_raises_typed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, text="slow down")

    client = _client(handler)
    with pytest.raises(CoingeckoRateLimitError):
        client.simple_price("bitcoin")


def test_auth_failure_raises_typed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    client = _client(handler)
    with pytest.raises(CoingeckoAuthError):
        client.simple_price("bitcoin")


def test_server_error_carries_message():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"status": {"error_message": "bad id"}})

    client = _client(handler)
    with pytest.raises(CoingeckoError) as exc:
        client.simple_price("nope")
    assert "bad id" in str(exc.value)


def test_dex_networks_list_aliases_asset_platforms():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/asset_platforms" in str(request.url)
        return httpx.Response(200, json=[{"id": "ethereum"}])

    client = _client(handler)
    assert client.dex_networks_list() == [{"id": "ethereum"}]


def test_pro_client_requires_key():
    with pytest.raises(CoingeckoAuthError):
        coingecko_pro_client(api_key="")


def test_pro_client_sends_pro_header_and_uses_pro_host():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["host"] = request.url.host
        seen["pro"] = request.headers.get(PRO_KEY_HEADER)
        seen["demo"] = request.headers.get(DEMO_KEY_HEADER)
        return httpx.Response(200, json=[[1, 2, 3, 4, 5]])

    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        base_url="https://pro-api.coingecko.com/api/v3", transport=transport
    )
    client = coingecko_pro_client("pro-key-xyz", client=http)
    out = client.ohlc("bitcoin")
    assert out == [[1, 2, 3, 4, 5]]
    assert seen["host"] == "pro-api.coingecko.com"
    assert seen["pro"] == "pro-key-xyz"
    assert seen["demo"] is None
