# SPDX-License-Identifier: Apache-2.0
"""Tests for agents/wordpress_agent/mindx_auth.py — the mindX-side client
of the mindx-publish-auth WordPress plugin.

Pins:
  * Happy path: challenge → sign → verify → JWT cached
  * Plugin not installed (challenge endpoint 404) → None + cached negative
  * Plugin allowlist rejects the address → None
  * Vault wallet missing → None (no NPE)
  * Cached token reused on second call (no duplicate round-trip)
  * Cached token refreshed when within 60s of expiry
  * bearer_headers() returns ``{}`` on failure (not None, not partial)
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Optional
from unittest.mock import patch

import httpx
import pytest

from agents.wordpress_agent.mindx_auth import MindXAuthClient, _CachedToken


# ─── Helper: build a httpx.MockTransport from a handler dict ────


def _make_transport(handlers: dict):
    """``handlers`` is ``{(method, path_suffix): (status_code, json_dict)}``.
    Returns an httpx.MockTransport that dispatches on path-suffix match."""
    def dispatch(request: httpx.Request) -> httpx.Response:
        for (method, suffix), spec in handlers.items():
            if request.method == method and request.url.path.endswith(suffix):
                if callable(spec):
                    res = spec(request)
                    if isinstance(res, httpx.Response):
                        return res
                    status, payload = res
                else:
                    status, payload = spec
                content = b'' if payload is None else json.dumps(payload).encode()
                return httpx.Response(
                    status,
                    content=content,
                    headers={"content-type": "application/json"},
                )
        return httpx.Response(404, content=b'{"error":"not stubbed"}',
                               headers={"content-type": "application/json"})
    return httpx.MockTransport(dispatch)


@pytest.fixture
def fake_signature():
    """Deterministic sig + address for sign_with_agent_wallet."""
    return (
        "0x" + "ab" * 65,                              # 130-hex (65 bytes)
        "0x1f0F44a5d800C060084A58525B717AC156Ab070b",  # wordpress.agent
    )


@pytest.fixture(autouse=True)
def patch_sign_with_agent_wallet(fake_signature):
    with patch("agents.wordpress_agent.mindx_auth.sign_with_agent_wallet",
                return_value=fake_signature) as m:
        yield m


@pytest.fixture(autouse=True)
def patch_load_wp_settings():
    """Stub the vault settings loader — gives the client a base_url
    without needing a real vault entry."""
    class _Settings:
        @property
        def base_url(self):
            return "https://rage.pythai.net/"
    with patch("agents.wordpress_agent.mindx_auth.load_wp_settings_from_vault",
                return_value=_Settings()):
        yield


def _client_with(handlers: dict) -> MindXAuthClient:
    """Construct a MindXAuthClient that routes httpx through our mock
    transport. We monkey-patch httpx.AsyncClient at the call site (the
    mindx_auth module) so MindXAuth's own ``async with`` constructs the
    mocked client without touching every other httpx user in the test
    process."""
    real_async_client = httpx.AsyncClient

    def _factory(*args, **kwargs):
        kwargs["transport"] = _make_transport(handlers)
        return real_async_client(*args, **kwargs)

    patcher = patch("agents.wordpress_agent.mindx_auth.httpx.AsyncClient",
                    side_effect=_factory)
    patcher.start()
    client = MindXAuthClient(base_url="https://rage.pythai.net")
    # Stash the patcher so the test can stop it if it wants; we also
    # auto-stop in a finalizer via the addfinalizer pattern, but for
    # simplicity the test fixture below handles cleanup at session end.
    client._test_patcher = patcher    # type: ignore[attr-defined]
    return client


@pytest.fixture(autouse=True)
def cleanup_patches():
    """Stop any httpx.AsyncClient patches between tests."""
    yield
    # Reset module-level patches so they don't leak.
    try:
        patch.stopall()
    except Exception:
        pass


# ─── Happy path ─────────────────────────────────────────────────


def test_happy_path_mint_token(fake_signature):
    """Full challenge → sign → verify → JWT round trip succeeds."""
    expiry = int(time.time()) + 1800
    captured = {}

    def verify_handler(req: httpx.Request):
        body = json.loads(req.content)
        captured.update(body)
        return 200, {
            "token": "eyJ0ZXN0LWp3dCJ9",
            "token_type": "Bearer",
            "expires_at": expiry,
            "expires_in": 1800,
            "user_id": 6,
        }

    client = _client_with({
        ("GET",  "/auth/challenge"): (200, {
            "challenge_id": "abc123",
            "message": "mindX-Publish-Auth:1\nsite:test\nchallenge:abc123",
            "expires_at": expiry,
        }),
        ("POST", "/auth/verify"): verify_handler,
    })

    token = asyncio.run(client.get_token())
    assert token == "eyJ0ZXN0LWp3dCJ9"
    assert captured["challenge_id"] == "abc123"
    assert captured["address"] == fake_signature[1]
    assert captured["signature"] == fake_signature[0]
    assert client._token is not None
    assert client._token.user_id == 6


def test_bearer_headers_format():
    client = _client_with({
        ("GET",  "/auth/challenge"): (200, {
            "challenge_id": "x",
            "message": "msg",
            "expires_at": int(time.time()) + 600,
        }),
        ("POST", "/auth/verify"): (200, {
            "token": "JWT-VAL",
            "expires_at": int(time.time()) + 600,
            "user_id": 1,
        }),
    })
    headers = asyncio.run(client.bearer_headers())
    assert headers == {"Authorization": "Bearer JWT-VAL"}


# ─── Plugin not installed ───────────────────────────────────────


def test_plugin_not_installed_returns_none():
    client = _client_with({
        ("GET", "/auth/challenge"): (404, {
            "code": "rest_no_route", "message": "No route was found.",
        }),
    })
    token = asyncio.run(client.get_token())
    assert token is None
    assert client._plugin_present is False


def test_bearer_headers_empty_on_failure():
    client = _client_with({
        ("GET", "/auth/challenge"): (404, {"code": "rest_no_route"}),
    })
    assert asyncio.run(client.bearer_headers()) == {}


# ─── Verify rejection paths ─────────────────────────────────────


def test_verify_403_address_not_allowlisted():
    client = _client_with({
        ("GET", "/auth/challenge"): (200, {
            "challenge_id": "x", "message": "msg",
            "expires_at": int(time.time()) + 600,
        }),
        ("POST", "/auth/verify"): (403, {
            "code": "mindx_auth_address_not_allowlisted",
            "message": "Address is not on the allowlist.",
        }),
    })
    assert asyncio.run(client.get_token()) is None
    assert client._token is None


# ─── Vault wallet missing ───────────────────────────────────────


def test_no_vault_wallet_returns_none():
    verify_calls = {"n": 0}

    def verify_handler(req):
        verify_calls["n"] += 1
        return 200, {"token": "x", "expires_at": int(time.time()) + 600, "user_id": 1}

    client = _client_with({
        ("GET",  "/auth/challenge"): (200, {
            "challenge_id": "x", "message": "msg",
            "expires_at": int(time.time()) + 600,
        }),
        ("POST", "/auth/verify"): verify_handler,
    })
    with patch("agents.wordpress_agent.mindx_auth.sign_with_agent_wallet",
                return_value=None):
        token = asyncio.run(client.get_token())
    assert token is None
    assert verify_calls["n"] == 0   # never reached /verify


# ─── Token caching ──────────────────────────────────────────────


def test_token_cached_between_calls():
    counts = {"chal": 0, "verify": 0}

    def chal(req):
        counts["chal"] += 1
        return 200, {
            "challenge_id": "x", "message": "msg",
            "expires_at": int(time.time()) + 600,
        }

    def verify(req):
        counts["verify"] += 1
        return 200, {"token": "tk", "expires_at": int(time.time()) + 600, "user_id": 1}

    client = _client_with({
        ("GET",  "/auth/challenge"): chal,
        ("POST", "/auth/verify"):    verify,
    })
    asyncio.run(client.get_token())
    asyncio.run(client.get_token())
    asyncio.run(client.get_token())
    assert counts["chal"]   == 1
    assert counts["verify"] == 1


def test_token_refreshed_when_near_expiry():
    counts = {"chal": 0, "verify": 0}

    def chal(req):
        counts["chal"] += 1
        return 200, {
            "challenge_id": "x", "message": "msg",
            "expires_at": int(time.time()) + 600,
        }

    def verify(req):
        counts["verify"] += 1
        return 200, {
            "token": f"tk{counts['verify']}",
            "expires_at": int(time.time()) + 600,
            "user_id": 1,
        }

    client = _client_with({
        ("GET",  "/auth/challenge"): chal,
        ("POST", "/auth/verify"):    verify,
    })
    t1 = asyncio.run(client.get_token())
    client._token.expires_at = time.time() + 10   # within 60s skew
    t2 = asyncio.run(client.get_token())
    assert t1 != t2
    assert counts["chal"]   == 2
    assert counts["verify"] == 2


def test_cached_token_expiring_soon_method():
    tok = _CachedToken(token="x", expires_at=time.time() + 30, user_id=1)
    assert tok.expiring_soon()
    tok2 = _CachedToken(token="x", expires_at=time.time() + 600, user_id=1)
    assert not tok2.expiring_soon()


# ─── Diagnose / plugin presence ─────────────────────────────────


def test_plugin_present_uses_diagnose_endpoint():
    counts = {"n": 0}

    def diag(req):
        counts["n"] += 1
        return 200, {"plugin_version": "0.1.0", "gmp_loaded": True}

    client = _client_with({
        ("GET", "/auth/diagnose"): diag,
    })
    assert asyncio.run(client.plugin_present()) is True
    assert asyncio.run(client.plugin_present()) is True   # cached
    assert counts["n"] == 1


def test_plugin_absent_when_diagnose_404():
    client = _client_with({
        ("GET", "/auth/diagnose"): (404, {"code": "rest_no_route"}),
    })
    assert asyncio.run(client.plugin_present()) is False
