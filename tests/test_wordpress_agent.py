# SPDX-License-Identifier: Apache-2.0
"""Tests for the ported WordPress.agent service (agents/wordpress_agent).

Consolidates the original mindXtrain wordpress_agent test suite (agent / config /
server) against the in-mindX package path. Uses pytest-httpx to mock the
WordPress REST API — no network. Explicit asyncio decorators so the suite does
not depend on a global ``asyncio_mode``.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

from agents.wordpress_agent.agent import AuthenticationError, PublishError, WordpressAgent
from agents.wordpress_agent.config import Settings
from agents.wordpress_agent.server import app

_BASE = "https://rage.example.test"


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Don't pick up a developer .env; provide deterministic WP_* vars."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("WP_BASE_URL", _BASE)
    monkeypatch.setenv("WP_USER", "codephreak")
    monkeypatch.setenv("WP_APP_PASSWORD", "test-pass-1234-5678")
    monkeypatch.setenv("WP_RETRY_COUNT", "1")
    monkeypatch.setenv("WP_RETRY_BACKOFF", "0")
    # Disable the mindX wallet-signature auth path for these tests —
    # they exercise the BasicAuth fallback. The new mindx-publish-auth
    # path is covered by tests/test_mindx_auth.py.
    monkeypatch.setattr(
        "agents.wordpress_agent.mindx_auth.sign_with_agent_wallet",
        lambda _msg: None,
    )


@pytest.fixture
def settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


@pytest_asyncio.fixture
async def agent(settings: Settings):
    async with WordpressAgent(settings) as a:
        yield a


# --- config ----------------------------------------------------------------
def test_settings_load_from_env(settings: Settings) -> None:
    assert settings.base_url_str == _BASE
    assert settings.user == "codephreak"
    assert settings.app_password_value == "test-pass-1234-5678"


def test_settings_strip_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WP_BASE_URL", "https://rage.pythai.net/")
    assert Settings().base_url_str == "https://rage.pythai.net"  # type: ignore[call-arg]


def test_settings_secret_not_repr_leaked(settings: Settings) -> None:
    assert "test-pass-1234-5678" not in repr(settings)


# --- agent: publish --------------------------------------------------------
@pytest.mark.asyncio
async def test_publish_success(httpx_mock, agent: WordpressAgent) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE}/wp-json/wp/v2/posts",
        json={"id": 42, "link": f"{_BASE}/?p=42", "status": "publish", "slug": "hello", "date_gmt": "2026-05-09T22:00:00"},
        status_code=201,
    )
    result = await agent.publish(title="Hello", content="<p>World</p>")
    assert result.post_id == 42
    assert result.url == f"{_BASE}/?p=42"
    assert result.status == "publish"


@pytest.mark.asyncio
async def test_publish_draft_status(httpx_mock, agent: WordpressAgent) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE}/wp-json/wp/v2/posts",
        json={"id": 5, "link": f"{_BASE}/?p=5", "status": "draft", "slug": "draft-post", "date_gmt": "2026-05-12T00:00:00"},
        status_code=201,
    )
    result = await agent.publish(title="Draft", content="<p>x</p>", status="draft")
    assert result.status == "draft"
    body = httpx_mock.get_request().read().decode()  # type: ignore[union-attr]
    assert '"status": "draft"' in body or '"status":"draft"' in body


@pytest.mark.asyncio
async def test_publish_scheduled_requires_tz_aware_date(agent: WordpressAgent) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        await agent.publish(title="Scheduled", content="<p>x</p>", status="future", date=datetime(2026, 6, 1, 9, 0, 0))


@pytest.mark.asyncio
async def test_publish_empty_title_and_content_rejected(agent: WordpressAgent) -> None:
    with pytest.raises(ValueError, match="title"):
        await agent.publish(title="   ", content="<p>x</p>")
    with pytest.raises(ValueError, match="content"):
        await agent.publish(title="t", content="")


@pytest.mark.asyncio
async def test_publish_authentication_failure(httpx_mock, agent: WordpressAgent) -> None:
    httpx_mock.add_response(method="POST", url=f"{_BASE}/wp-json/wp/v2/posts", status_code=401, json={"code": "rest_cannot_create"})
    with pytest.raises(AuthenticationError):
        await agent.publish(title="Hello", content="<p>x</p>")


@pytest.mark.asyncio
async def test_publish_retries_then_succeeds(httpx_mock, agent: WordpressAgent) -> None:
    httpx_mock.add_response(method="POST", url=f"{_BASE}/wp-json/wp/v2/posts", status_code=503)
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE}/wp-json/wp/v2/posts",
        status_code=201,
        json={"id": 7, "link": f"{_BASE}/?p=7", "status": "publish", "slug": "retry", "date_gmt": "2026-05-09T22:00:00"},
    )
    result = await agent.publish(title="Retry", content="<p>x</p>")
    assert result.post_id == 7


@pytest.mark.asyncio
async def test_publish_gives_up_after_max_retries(httpx_mock, agent: WordpressAgent) -> None:
    httpx_mock.add_response(method="POST", url=f"{_BASE}/wp-json/wp/v2/posts", status_code=503)
    httpx_mock.add_response(method="POST", url=f"{_BASE}/wp-json/wp/v2/posts", status_code=503)
    with pytest.raises(PublishError):
        await agent.publish(title="Down", content="<p>x</p>")


@pytest.mark.asyncio
async def test_publish_includes_scheduled_date_in_payload(httpx_mock, agent: WordpressAgent) -> None:
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE}/wp-json/wp/v2/posts",
        status_code=201,
        json={"id": 99, "link": f"{_BASE}/?p=99", "status": "future", "slug": "scheduled", "date_gmt": "2026-06-01T09:00:00"},
    )
    await agent.publish(title="Scheduled", content="<p>x</p>", status="future", date=datetime(2026, 6, 1, 9, 0, 0, tzinfo=timezone.utc))
    body = httpx_mock.get_request().read().decode()  # type: ignore[union-attr]
    assert "date_gmt" in body and "future" in body


@pytest.mark.asyncio
async def test_health_check_ok(httpx_mock, agent: WordpressAgent) -> None:
    httpx_mock.add_response(method="GET", url=f"{_BASE}/wp-json/wp/v2/users/me", status_code=200, json={"id": 1, "name": "codephreak"})
    result = await agent.health_check()
    assert result["ok"] is True
    assert result["wp_user_id"] == 1


# --- FastAPI server surface ------------------------------------------------
def test_healthz_endpoint_responds(httpx_mock, _server_uses_env_credentials) -> None:
    httpx_mock.add_response(method="GET", url=f"{_BASE}/wp-json/wp/v2/users/me", status_code=200, json={"id": 1, "name": "codephreak"})
    with TestClient(app) as client:
        response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["ok"] is True


@pytest.fixture
def _server_uses_env_credentials(monkeypatch):
    """Force the FastAPI server's credential resolver to skip the vault
    and pick up the env-var Settings the test fixture defines. The vault
    on a developer box may contain real wordpress.agent entries (provisioned
    during real publish work) — we don't want those to leak into the test."""
    # Patch at both the source AND the server's import alias, since the
    # server does `from .vault_creds import load_wp_settings_from_vault`
    # and that binds a local name that won't see a patch at the source.
    monkeypatch.setattr(
        "agents.wordpress_agent.vault_creds.load_wp_settings_from_vault",
        lambda: None,
    )
    monkeypatch.setattr(
        "agents.wordpress_agent.server.load_wp_settings_from_vault",
        lambda: None,
    )


def test_publish_endpoint_validates_payload() -> None:
    with TestClient(app) as client:
        response = client.post("/publish", json={"title": "", "content": ""})
    assert response.status_code == 422


def test_publish_endpoint_success(httpx_mock, _server_uses_env_credentials) -> None:
    httpx_mock.add_response(method="GET", url=f"{_BASE}/wp-json/wp/v2/users/me", status_code=200, json={"id": 1, "name": "codephreak"})
    httpx_mock.add_response(
        method="POST",
        url=f"{_BASE}/wp-json/wp/v2/posts",
        status_code=201,
        json={"id": 42, "link": f"{_BASE}/?p=42", "status": "publish", "slug": "hello", "date_gmt": "2026-05-09T22:00:00"},
    )
    with TestClient(app) as client:
        client.get("/healthz")  # warm lifespan
        response = client.post("/publish", json={"title": "Hello", "content": "<p>World</p>"})
    assert response.status_code == 200
    assert response.json()["post_id"] == 42


# --- vault-backed credentials ---------------------------------------------
@pytest.fixture
def isolated_vault(tmp_path, monkeypatch):
    """Build a BankonVault in tmp_path and route vault_creds._open_unlocked_vault to it.

    Returns the (unlocked) vault so the test can populate the wordpress.agent.keys
    namespace. The fixture re-creates a fresh unlocked vault on each call from inside
    the module-under-test so each operation re-opens (matching production behavior).
    """
    from mindx_backend_service.bankon_vault.vault import BankonVault
    from agents.wordpress_agent import vault_creds as vc

    vault = BankonVault(vault_dir=str(tmp_path / "vault_bankon"))
    vault.unlock_with_key_file()

    def _opener():
        v = BankonVault(vault_dir=str(tmp_path / "vault_bankon"))
        v.unlock_with_key_file()
        return v

    monkeypatch.setattr(vc, "_open_unlocked_vault", _opener)
    yield vault
    try:
        vault.lock()
    except Exception:
        pass


def test_load_wp_settings_from_vault_round_trip(isolated_vault) -> None:
    from agents.wordpress_agent import vault_creds as vc

    isolated_vault.store(vc.ENTRY_WP_BASE_URL, "https://rage.example.test", context=vc.VAULT_CONTEXT)
    isolated_vault.store(vc.ENTRY_WP_USER, "codephreak", context=vc.VAULT_CONTEXT)
    isolated_vault.store(vc.ENTRY_WP_APP_PASSWORD, "vault-only-pass-1234", context=vc.VAULT_CONTEXT)
    isolated_vault.lock()

    s = vc.load_wp_settings_from_vault()
    assert s is not None
    assert s.base_url_str == "https://rage.example.test"
    assert s.user == "codephreak"
    assert s.app_password_value == "vault-only-pass-1234"


def test_load_wp_settings_returns_none_when_namespace_empty(isolated_vault) -> None:
    from agents.wordpress_agent.vault_creds import load_wp_settings_from_vault
    assert load_wp_settings_from_vault() is None


def test_load_wp_settings_rejects_non_https(isolated_vault) -> None:
    from agents.wordpress_agent import vault_creds as vc

    isolated_vault.store(vc.ENTRY_WP_BASE_URL, "http://rage.example.test", context=vc.VAULT_CONTEXT)
    isolated_vault.store(vc.ENTRY_WP_USER, "codephreak", context=vc.VAULT_CONTEXT)
    isolated_vault.store(vc.ENTRY_WP_APP_PASSWORD, "x", context=vc.VAULT_CONTEXT)
    isolated_vault.lock()

    assert vc.load_wp_settings_from_vault() is None  # https validator → Settings rejection → None


def test_sign_with_agent_wallet_recovers_to_stored_address(isolated_vault) -> None:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    from web3 import Web3

    from agents.wordpress_agent import vault_creds as vc

    acct = Account.create()
    isolated_vault.store(vc.ENTRY_PK, acct.key.hex(), context=vc.VAULT_CONTEXT)
    isolated_vault.store(vc.ENTRY_ADDRESS, Web3.to_checksum_address(acct.address), context=vc.VAULT_CONTEXT)
    isolated_vault.lock()

    msg = "0x" + ("a" * 64)
    out = vc.sign_with_agent_wallet(msg)
    assert out is not None
    sig, addr = out
    assert addr == Web3.to_checksum_address(acct.address)
    recovered = Account.recover_message(encode_defunct(text=msg), signature=sig)
    assert recovered.lower() == acct.address.lower()


def test_sign_with_agent_wallet_returns_none_when_unprovisioned(isolated_vault) -> None:
    from agents.wordpress_agent.vault_creds import sign_with_agent_wallet
    assert sign_with_agent_wallet("anything") is None


# --- publish_auth (wallet-authorized publish flow) -------------------------
@pytest.fixture
def publish_app(monkeypatch, tmp_path):
    """Mount the publish_auth router on a fresh FastAPI app, isolate the nonce store.

    Patches AuthorAgent.publish_to_rage to return a fake successful dict so the
    test doesn't need the wordpress-agent service. Sets WORDPRESS_PUBLISHER_ADDRESSES
    via env (caller fills it per-test).
    """
    from fastapi import FastAPI

    # Isolate the shadow_overlord global NonceStore.
    from mindx_backend_service.bankon_vault import shadow_overlord as so
    so.reset_store_for_tests(tmp_path / "nonces.json")

    from agents.wordpress_agent import publish_auth as pa
    app = FastAPI()
    app.include_router(pa.router)

    # Stub AuthorAgent.publish_to_rage so the test runs without the loopback service.
    class _StubAuthor:
        async def publish_to_rage(self, **kwargs):
            assert kwargs["status"] in {"draft", "publish", "future", "pending", "private"}
            return {
                "post_id": 4242,
                "url": "https://rage.example.test/?p=4242",
                "status": kwargs["status"],
                "slug": "stub",
                "date_gmt": "2026-05-12T00:00:00",
            }

    async def _get_instance():
        return _StubAuthor()

    monkeypatch.setattr("agents.author_agent.AuthorAgent.get_instance", _get_instance)
    return app


def _sign(message: str, key) -> str:
    from eth_account import Account
    from eth_account.messages import encode_defunct
    return Account.sign_message(encode_defunct(text=message), private_key=key).signature.hex()


def test_publish_auth_happy_path(publish_app, monkeypatch) -> None:
    from eth_account import Account
    from web3 import Web3
    import hashlib

    acct = Account.create()
    wallet = Web3.to_checksum_address(acct.address)
    monkeypatch.setenv("WORDPRESS_PUBLISHER_ADDRESSES", wallet)

    html = "<h1>Hi</h1><p>body</p>"
    content_sha256 = "0x" + hashlib.sha256(html.encode("utf-8")).hexdigest()

    with TestClient(publish_app) as client:
        ch = client.post("/publish/rage/challenge", json={
            "wallet_address": wallet, "title": "T", "content_sha256": content_sha256,
        })
        assert ch.status_code == 200, ch.text
        body = ch.json()
        nonce = body["nonce"]
        message = body["message"]
        signature = _sign(message, acct.key)
        if not signature.startswith("0x"):
            signature = "0x" + signature

        auth = client.post("/publish/rage/authorize", json={
            "wallet_address": wallet, "nonce": nonce, "signature": signature,
            "title": "T", "status": "draft", "html": html,
        })
        assert auth.status_code == 200, auth.text
        j = auth.json()
        assert j["status"] == "ok"
        assert j["authorized_by"] == wallet.lower()
        assert j["wordpress"]["post_id"] == 4242


def test_publish_auth_rejects_wallet_outside_allowlist(publish_app, monkeypatch) -> None:
    from eth_account import Account
    from web3 import Web3
    import hashlib

    acct = Account.create()
    wallet = Web3.to_checksum_address(acct.address)
    # Allowlist contains a different address.
    monkeypatch.setenv("WORDPRESS_PUBLISHER_ADDRESSES", "0x" + "1" * 40)

    html = "<p>x</p>"
    content_sha256 = "0x" + hashlib.sha256(html.encode("utf-8")).hexdigest()
    with TestClient(publish_app) as client:
        ch = client.post("/publish/rage/challenge", json={"wallet_address": wallet, "title": "T", "content_sha256": content_sha256}).json()
        sig = _sign(ch["message"], acct.key)
        if not sig.startswith("0x"):
            sig = "0x" + sig
        r = client.post("/publish/rage/authorize", json={
            "wallet_address": wallet, "nonce": ch["nonce"], "signature": sig,
            "title": "T", "status": "draft", "html": html,
        })
    assert r.status_code == 403


def test_publish_auth_rejects_wrong_signature(publish_app, monkeypatch) -> None:
    from eth_account import Account
    from web3 import Web3
    import hashlib

    acct = Account.create()
    impostor = Account.create()
    wallet = Web3.to_checksum_address(acct.address)
    monkeypatch.setenv("WORDPRESS_PUBLISHER_ADDRESSES", wallet)

    html = "<p>x</p>"
    content_sha256 = "0x" + hashlib.sha256(html.encode("utf-8")).hexdigest()
    with TestClient(publish_app) as client:
        ch = client.post("/publish/rage/challenge", json={"wallet_address": wallet, "title": "T", "content_sha256": content_sha256}).json()
        sig = _sign(ch["message"], impostor.key)  # signed by the WRONG key
        if not sig.startswith("0x"):
            sig = "0x" + sig
        r = client.post("/publish/rage/authorize", json={
            "wallet_address": wallet, "nonce": ch["nonce"], "signature": sig,
            "title": "T", "status": "draft", "html": html,
        })
    assert r.status_code == 401


def test_publish_auth_rejects_content_hash_mismatch(publish_app, monkeypatch) -> None:
    from eth_account import Account
    from web3 import Web3
    import hashlib

    acct = Account.create()
    wallet = Web3.to_checksum_address(acct.address)
    monkeypatch.setenv("WORDPRESS_PUBLISHER_ADDRESSES", wallet)

    html_signed = "<p>signed body</p>"
    html_authorized = "<p>DIFFERENT body</p>"  # caller tries to swap content after signing
    content_sha256 = "0x" + hashlib.sha256(html_signed.encode("utf-8")).hexdigest()
    with TestClient(publish_app) as client:
        ch = client.post("/publish/rage/challenge", json={"wallet_address": wallet, "title": "T", "content_sha256": content_sha256}).json()
        sig = _sign(ch["message"], acct.key)
        if not sig.startswith("0x"):
            sig = "0x" + sig
        r = client.post("/publish/rage/authorize", json={
            "wallet_address": wallet, "nonce": ch["nonce"], "signature": sig,
            "title": "T", "status": "draft", "html": html_authorized,
        })
    assert r.status_code == 400
    assert "content hash" in r.json()["detail"]


def test_publish_auth_rejects_nonce_reuse(publish_app, monkeypatch) -> None:
    from eth_account import Account
    from web3 import Web3
    import hashlib

    acct = Account.create()
    wallet = Web3.to_checksum_address(acct.address)
    monkeypatch.setenv("WORDPRESS_PUBLISHER_ADDRESSES", wallet)

    html = "<p>x</p>"
    content_sha256 = "0x" + hashlib.sha256(html.encode("utf-8")).hexdigest()
    with TestClient(publish_app) as client:
        ch = client.post("/publish/rage/challenge", json={"wallet_address": wallet, "title": "T", "content_sha256": content_sha256}).json()
        sig = _sign(ch["message"], acct.key)
        if not sig.startswith("0x"):
            sig = "0x" + sig
        payload = {"wallet_address": wallet, "nonce": ch["nonce"], "signature": sig,
                   "title": "T", "status": "draft", "html": html}
        r1 = client.post("/publish/rage/authorize", json=payload)
        assert r1.status_code == 200
        r2 = client.post("/publish/rage/authorize", json=payload)
    assert r2.status_code == 409
