"""Acceptance tests for the hard arrival gate (Phase B of the tighten-up plan).

Contract documented in docs/operations/HARD_GATE_RUNBOOK.md.

These tests do **not** boot the full mindX backend (which depends on the
agent stack + vault + LLM handlers and is too heavy for a unit test).
Instead, they import the canonical public path sets from
``mindx_backend_service.main_service`` and exercise the gate contract via a
miniature FastAPI app that re-applies the same middleware shape. The single
source of truth — the strict sets — is shared with production; only the
imitator middleware lives in the test module.

If the production middleware changes, this test must change in lock-step
(that is the point — the test is the gate's executable spec).
"""
from __future__ import annotations

import importlib
import os
from typing import Iterable

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse
from starlette.testclient import TestClient


# ----------------------------------------------------------------------
# Fixtures: import the strict sets from production and build a minimal
# FastAPI app that mirrors the production gate behavior.
# ----------------------------------------------------------------------


@pytest.fixture(scope="module")
def gate_module():
    """Import the production module just for its public-set constants.

    The full ``main_service`` import is expensive but does work in CI; we
    pin the import to module scope so it only happens once.
    """
    # Force strict mode regardless of how the test environment is configured.
    os.environ["MINDX_HARD_GATE_ENABLED"] = "1"
    mod = importlib.import_module("mindx_backend_service.main_service")
    return mod


@pytest.fixture
def gate_app(gate_module):
    """Build a tiny FastAPI app that applies the same gate contract.

    The imitator middleware below uses the SAME ``_PUBLIC_EXACT_STRICT`` and
    ``_PUBLIC_PREFIXES_STRICT`` symbols as production. The session validator
    is stubbed out (X-Session-Token = ``valid`` passes; anything else fails)
    so the test stays self-contained.
    """
    PUBLIC_EXACT = gate_module._PUBLIC_EXACT_STRICT
    PUBLIC_PREFIXES = gate_module._PUBLIC_PREFIXES_STRICT

    app = FastAPI()

    @app.middleware("http")
    async def imitator(request: Request, call_next):
        path = request.url.path
        if request.method == "OPTIONS":
            return await call_next(request)
        if path in PUBLIC_EXACT:
            return await call_next(request)
        for pfx in PUBLIC_PREFIXES:
            if path.startswith(pfx):
                return await call_next(request)
        if request.method == "GET" and path.startswith("/users/") and path.endswith("/permissions"):
            return await call_next(request)

        token = request.headers.get("X-Session-Token")
        if token == "valid":
            return await call_next(request)

        from urllib.parse import quote
        accept = request.headers.get("accept", "")
        if "text/html" in accept and request.method == "GET":
            safe_from = path if path.startswith("/") and not path.startswith("//") else "/"
            qs = ("?" + request.url.query) if request.url.query else ""
            return RedirectResponse(url=f"/login?from={quote(safe_from + qs, safe='/')}", status_code=302)
        return JSONResponse(
            status_code=401,
            content={"code": "auth_required", "from": path},
        )

    # Catch-all OK route so the middleware decides everything.
    @app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def catchall(full_path: str):
        return {"ok": True, "path": "/" + full_path}

    return app


@pytest.fixture
def client(gate_app):
    return TestClient(gate_app, follow_redirects=False)


# ----------------------------------------------------------------------
# 1. Public surfaces stay public
# ----------------------------------------------------------------------


PUBLIC_PATHS_HTML: Iterable[str] = (
    "/",
    "/login",
    "/login.html",
    "/docs.html",
    "/automindx",
    "/automindx.html",
    "/shadow-overlord",
    "/shadow-overlord.html",
)


@pytest.mark.parametrize("path", PUBLIC_PATHS_HTML)
def test_public_path_is_accessible(client, path):
    r = client.get(path, headers={"accept": "text/html"})
    assert r.status_code == 200, f"public path {path} returned {r.status_code}"


def test_public_prefix_doc_is_accessible(client):
    r = client.get("/doc/services/mindx_as_a_service.md", headers={"accept": "text/html"})
    assert r.status_code == 200


def test_public_prefix_static_is_accessible(client):
    r = client.get("/static/css/main.css")
    assert r.status_code == 200


def test_public_prefix_admin_shadow_is_accessible(client):
    # /admin/shadow/* is gated at handler level by the shadow-overlord ECDSA flow,
    # so the arrival gate must let it through.
    r = client.post("/admin/shadow/challenge", json={"address": "0xdead"})
    assert r.status_code == 200


def test_public_prefix_users_challenge_is_accessible(client):
    r = client.post("/users/challenge", json={"wallet": "0xdead"})
    assert r.status_code == 200


def test_public_prefix_wp_json_is_accessible(client):
    # WordPress plugin callbacks are signature-authed at the plugin layer.
    r = client.post("/wp-json/mindx/v1/publish", json={})
    assert r.status_code == 200


def test_public_permissions_endpoint_is_accessible(client):
    r = client.get("/users/0xabc/permissions")
    assert r.status_code == 200


# ----------------------------------------------------------------------
# 2. Gated HTML surfaces redirect to /login with from=
# ----------------------------------------------------------------------


GATED_HTML_PATHS: Iterable[str] = (
    "/feedback.html",
    "/journal",
    "/boardroom",
    "/dojo",
    "/book",
    "/cabinet",
    "/thot",
    "/agentregistry",
    "/openagents",
    "/inft7857",
)


@pytest.mark.parametrize("path", GATED_HTML_PATHS)
def test_gated_html_redirects_to_login(client, path):
    r = client.get(path, headers={"accept": "text/html"})
    assert r.status_code == 302, f"{path} should 302 but got {r.status_code}"
    loc = r.headers.get("location", "")
    assert loc.startswith("/login?from=") or loc.startswith("/login%3Ffrom%3D"), \
        f"{path} redirected to unexpected location: {loc}"


def test_gated_html_redirect_preserves_query_string(client):
    r = client.get("/feedback.html?h=true&kind=auth", headers={"accept": "text/html"})
    assert r.status_code == 302
    loc = r.headers.get("location", "")
    assert "h%3Dtrue" in loc or "h=true" in loc, f"query lost in redirect: {loc}"


def test_gated_html_open_redirect_guarded(client):
    # The middleware must sanitize the path. A path that starts with // (an
    # absolute URL) would be an open-redirect target; the production gate
    # short-circuits to "/" in that case.
    r = client.get("//evil.example.com/path", headers={"accept": "text/html"})
    assert r.status_code == 302
    loc = r.headers.get("location", "")
    assert "evil.example.com" not in loc, f"open redirect leaked: {loc}"


# ----------------------------------------------------------------------
# 3. Gated API surfaces return 401 JSON
# ----------------------------------------------------------------------


GATED_API_PATHS: Iterable[str] = (
    "/coordinator/query",
    "/coordinator/improve",
    "/agents/foo/evolve",
    "/boardroom/convene",
    "/llm/chat",
    "/insight/improvement/summary",
    "/registry/agents",
)


@pytest.mark.parametrize("path", GATED_API_PATHS)
def test_gated_api_returns_401_json(client, path):
    r = client.post(path, json={}, headers={"accept": "application/json"})
    assert r.status_code == 401, f"{path} should 401 but got {r.status_code}"
    body = r.json()
    assert body.get("code") == "auth_required"
    assert body.get("from") == path


# ----------------------------------------------------------------------
# 4. Valid session unlocks gated routes
# ----------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/feedback.html", "/insight/improvement/summary", "/coordinator/query"])
def test_valid_session_unlocks(client, path):
    r = client.post(path, json={}, headers={"X-Session-Token": "valid"})
    assert r.status_code in (200, 405), f"{path} with session got {r.status_code}"


# ----------------------------------------------------------------------
# 5. Mode toggle: setting MINDX_HARD_GATE_ENABLED=0 returns to legacy
# ----------------------------------------------------------------------


def test_arrival_gate_mode_toggle(gate_module, monkeypatch):
    monkeypatch.setenv("MINDX_HARD_GATE_ENABLED", "1")
    assert gate_module._arrival_gate_mode() == "strict"
    monkeypatch.setenv("MINDX_HARD_GATE_ENABLED", "0")
    assert gate_module._arrival_gate_mode() == "legacy"
    monkeypatch.delenv("MINDX_HARD_GATE_ENABLED", raising=False)
    # Default = strict (the spec).
    assert gate_module._arrival_gate_mode() == "strict"


def test_current_public_sets_picks_mode(gate_module, monkeypatch):
    monkeypatch.setenv("MINDX_HARD_GATE_ENABLED", "1")
    exact, prefixes = gate_module._current_public_sets()
    assert exact is gate_module._PUBLIC_EXACT_STRICT
    assert prefixes is gate_module._PUBLIC_PREFIXES_STRICT

    monkeypatch.setenv("MINDX_HARD_GATE_ENABLED", "0")
    exact, prefixes = gate_module._current_public_sets()
    assert exact is gate_module._PUBLIC_EXACT_LEGACY
    assert prefixes is gate_module._PUBLIC_PREFIXES_LEGACY


# ----------------------------------------------------------------------
# 6. The strict sets match what the runbook documents
# ----------------------------------------------------------------------


def test_strict_public_exact_matches_runbook(gate_module):
    """The six public path families from HARD_GATE_RUNBOOK.md §What changes."""
    exact = gate_module._PUBLIC_EXACT_STRICT
    expected_present = {
        "/login", "/login.html",
        "/docs.html",
        "/automindx", "/automindx.html",
        "/shadow-overlord", "/shadow-overlord.html",
        "/health",
    }
    missing = expected_present - exact
    assert not missing, f"strict public-exact set missing entries: {missing}"


def test_strict_public_exact_excludes_gated_paths(gate_module):
    """Paths that the runbook says should be gated must NOT be in the strict
    public-exact set."""
    exact = gate_module._PUBLIC_EXACT_STRICT
    must_be_gated = {
        "/feedback", "/feedback.html", "/feedback.txt",
        "/journal", "/boardroom", "/dojo", "/book",
        "/cabinet", "/cabinet.html",
        "/thot", "/THOT", "/thot.html",
        "/agentregistry", "/openagents", "/inft7857",
        "/godel/choices", "/inference/preference",
        "/registry/agents", "/coordinator/backlog",
    }
    leaked = must_be_gated & exact
    assert not leaked, f"strict public-exact set leaks gated paths: {leaked}"


def test_strict_public_prefixes_includes_handshake(gate_module):
    """The auth handshake routes must remain public — without them, no one
    can ever sign in."""
    prefixes = gate_module._PUBLIC_PREFIXES_STRICT
    required = {"/users/challenge", "/users/register", "/users/session/"}
    missing = required - set(prefixes)
    assert not missing, f"strict prefix set missing handshake routes: {missing}"


def test_strict_public_prefixes_includes_shadow_admin(gate_module):
    """Shadow-overlord admin routes are gated at handler level — the arrival
    gate must let them through to the handler."""
    prefixes = gate_module._PUBLIC_PREFIXES_STRICT
    assert "/admin/shadow/" in prefixes


def test_strict_public_prefixes_excludes_insight_and_marketing(gate_module):
    """The insight/marketing/dojo prefixes were public in legacy mode but
    must be gated in strict mode."""
    prefixes = gate_module._PUBLIC_PREFIXES_STRICT
    must_be_gated = {"/insight/", "/marketing/", "/dojo/", "/registry/", "/cabinet/"}
    leaked = must_be_gated & set(prefixes)
    assert not leaked, f"strict prefix set leaks gated paths: {leaked}"
