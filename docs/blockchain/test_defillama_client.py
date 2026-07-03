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

"""Offline tests for ``defillama_client``.

Every request is served by an injected ``httpx.MockTransport``; no network is
touched. The free client issues absolute multi-host URLs (no ``base_url``); the
Pro client carries the key in the URL path.
"""

from __future__ import annotations

import httpx
import pytest

from cmc_client import ttl_cache
from defillama_client import (
    FREE_HOSTS,
    DefillamaAuthError,
    DefillamaError,
    DefillamaRateLimitError,
    defillama_pro_client,
    defillama_public_client,
    price_data_provider,
    tvl_data_provider,
)


def _public(handler, **kwargs):
    """Build a free client whose transport is driven by ``handler``."""
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)  # deliberately base-url-less
    return defillama_public_client(client=http, **kwargs)


def _pro(handler, api_key="prokey", **kwargs):
    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        base_url=f"https://pro-api.llama.fi/{api_key}", transport=transport
    )
    return defillama_pro_client(api_key, client=http, **kwargs)


def test_public_conforms_to_protocols():
    client = defillama_public_client()
    assert isinstance(client, tvl_data_provider)
    assert isinstance(client, price_data_provider)


def test_protocols_hits_tvl_host_raw_json():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=[{"name": "Aave", "tvl": 1.0}])

    client = _public(handler)
    out = client.protocols()
    assert out == [{"name": "Aave", "tvl": 1.0}]
    assert captured["url"] == f"{FREE_HOSTS['tvl']}/protocols"


def test_multi_host_routing():
    hosts = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        return httpx.Response(200, json={})

    client = _public(handler)
    client.prices_current("ethereum:0xabc")
    client.stablecoins()
    client.yield_pools()
    client.bridges()
    assert hosts == [
        "coins.llama.fi",
        "stablecoins.llama.fi",
        "yields.llama.fi",
        "bridges.llama.fi",
    ]


def test_prices_current_satisfies_price_provider_path():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(
            f"{FREE_HOSTS['coins']}/prices/current/"
        )
        return httpx.Response(200, json={"coins": {"ethereum:0xabc": {"price": 1}}})

    client = _public(handler)
    out = client.prices_current("ethereum:0xabc")
    assert "coins" in out


def test_cache_hit_avoids_second_request():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=[{"x": 1}])

    cache = ttl_cache()
    client = _public(handler, cache=cache)
    client.protocols()
    client.protocols()
    assert calls["n"] == 1


def test_cache_expiry_refetches():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(200, json=[{"x": 1}])

    cache = ttl_cache()
    client = _public(handler, cache=cache)
    client.protocols()
    for entry in cache._store.values():
        entry.expires_at = 0.0
    client.protocols()
    assert calls["n"] == 2


def test_public_rate_limit_raises_without_retry():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, text="slow down")

    client = _public(handler)
    with pytest.raises(DefillamaRateLimitError):
        client.protocols()
    assert calls["n"] == 1  # consumption tier does not retry


def test_public_auth_failure_raises_typed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="nope")

    client = _public(handler)
    with pytest.raises(DefillamaAuthError):
        client.protocols()


def test_pro_requires_key():
    with pytest.raises(DefillamaError):
        defillama_pro_client(api_key="")


def test_pro_key_in_path_never_in_header():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json={"emissions": []})

    client = _pro(handler, api_key="SECRET123")
    client.emissions()
    assert "/SECRET123/api/emissions" in captured["url"]
    # The key must never travel in a header.
    assert all("SECRET123" not in v for v in captured["headers"].values())


def test_pro_cache_key_excludes_secret():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    cache = ttl_cache()
    client = _pro(handler, api_key="SECRET123", cache=cache)
    client.emissions()
    assert all("SECRET123" not in k for k in cache._store)


def test_pro_retries_then_raises_on_persistent_429():
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, text="slow down")

    client = _pro(handler)
    # Shrink retries so the test does not sleep through real backoff.
    client._max_retries = 2
    with pytest.raises(DefillamaRateLimitError):
        client.hacks()
    assert calls["n"] == 3  # initial + 2 retries
