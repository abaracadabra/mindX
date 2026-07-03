# SPDX-License-Identifier: Apache-2.0
"""Tests for the agentic audit layer shipped 2026-05-19.

Pins:
  * publication.{attempted,published,coalesced} are registered catalogue kinds
  * Gödel eval gate defaults OPEN (fail-open) and respects both env kill switches
  * _EvalHealth tracks hits/misses/scores in-process
  * Publication-event catalogue emit fires on publish + coalesce paths
  * Reading an empty / missing ledger does not raise
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import pytest


# ── 1. Event kinds registered ────────────────────────────────────


def test_publication_event_kinds_registered():
    from agents.catalogue.events import EVENT_KINDS
    for k in ("publication.attempted", "publication.published", "publication.coalesced"):
        assert k in EVENT_KINDS, f"{k} missing from EVENT_KINDS"


# ── 2. Eval gate: default OPEN, kill switches respected ──────────


def test_eval_gate_default_open(monkeypatch):
    from agents.memory_agent import _eval_godel_gate_open
    monkeypatch.delenv("MINDX_EVAL_GODEL_DISABLED", raising=False)
    monkeypatch.delenv("MINDX_EVAL_GODEL_ENABLED", raising=False)
    assert _eval_godel_gate_open() is True, "default must be fail-open"


def test_eval_gate_disabled_env(monkeypatch):
    from agents.memory_agent import _eval_godel_gate_open
    monkeypatch.setenv("MINDX_EVAL_GODEL_DISABLED", "1")
    assert _eval_godel_gate_open() is False


def test_eval_gate_legacy_env_disable(monkeypatch):
    from agents.memory_agent import _eval_godel_gate_open
    monkeypatch.delenv("MINDX_EVAL_GODEL_DISABLED", raising=False)
    monkeypatch.setenv("MINDX_EVAL_GODEL_ENABLED", "0")
    assert _eval_godel_gate_open() is False


def test_eval_gate_legacy_env_explicit_enable(monkeypatch):
    from agents.memory_agent import _eval_godel_gate_open
    monkeypatch.delenv("MINDX_EVAL_GODEL_DISABLED", raising=False)
    monkeypatch.setenv("MINDX_EVAL_GODEL_ENABLED", "1")
    assert _eval_godel_gate_open() is True


# ── 3. _EvalHealth tracker ───────────────────────────────────────


def test_eval_health_records_hits_and_misses():
    from agents.memory_agent import _EvalHealth
    h = _EvalHealth(window=5)
    h.record_score(0.4)
    h.record_score(0.8)
    h.record_miss()
    snap = h.snapshot()
    assert snap["hits"] == 2
    assert snap["misses"] == 1
    assert snap["attempts"] == 3
    assert abs(snap["mean_score"] - 0.6) < 1e-9
    assert snap["success_rate"] == pytest.approx(2 / 3)
    assert snap["scores_in_window"] == 2


def test_eval_health_window_trims():
    from agents.memory_agent import _EvalHealth
    h = _EvalHealth(window=3)
    for s in [0.1, 0.2, 0.3, 0.4, 0.5]:
        h.record_score(s)
    snap = h.snapshot()
    assert snap["scores_in_window"] == 3
    # mean over window of last 3
    assert abs(snap["mean_score"] - (0.3 + 0.4 + 0.5) / 3) < 1e-9
    assert snap["hits"] == 5


# ── 4. Publication-event emission from orchestrator ──────────────


class _CaptureEmits:
    """Patches agents.catalogue.emit_catalogue_event to record calls."""

    def __init__(self):
        self.events: List[Dict[str, Any]] = []

    async def __call__(self, kind, actor, payload, *, source_log, source_ref=None,
                       actor_wallet=None, parent_event_id=None):
        self.events.append({
            "kind": kind, "actor": actor, "payload": payload,
            "source_log": source_log, "source_ref": source_ref,
        })
        return f"evt-{len(self.events)}"


def _orc_with_capture(tmp_path: Path, return_value=None):
    from tests.test_publication_orchestrator import _FakeAuthor, _orchestrator_with_tmp_paths
    author = _FakeAuthor(return_value=return_value) if return_value is not None else _FakeAuthor()
    orc = _orchestrator_with_tmp_paths(tmp_path, author, base_delay_s=0.0, jitter_fraction=0.0)
    return orc, author


def test_publication_published_event_emitted(tmp_path, monkeypatch):
    captured = _CaptureEmits()
    import agents.catalogue as cat
    monkeypatch.setattr(cat, "emit_catalogue_event", captured)

    orc, _author = _orc_with_capture(tmp_path)
    history = [{
        "campaign_run_id": "sea_audit_driven_pubtest",
        "overall_campaign_status": "SUCCESS",
        "final_message": "Test publish.",
        "campaign_data": {},
    }]
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())

    kinds = [e["kind"] for e in captured.events]
    assert "publication.attempted" in kinds, f"got kinds={kinds}"
    assert "publication.published" in kinds, f"got kinds={kinds}"

    pub_evt = next(e for e in captured.events if e["kind"] == "publication.published")
    assert pub_evt["payload"]["trigger_id"] == "sea_audit_driven_pubtest"
    assert pub_evt["payload"]["post_id"] == 42
    assert pub_evt["payload"]["url"] == "https://rage.pythai.net/?p=42"


def test_publication_coalesced_event_emitted(tmp_path, monkeypatch):
    captured = _CaptureEmits()
    import agents.catalogue as cat
    monkeypatch.setattr(cat, "emit_catalogue_event", captured)

    orc, _author = _orc_with_capture(tmp_path)
    # Pre-populate ledger so the next trigger is inside MIN_GAP_S.
    import time as _t
    orc.ledger.last_published_at = _t.time()
    orc.ledger.save()

    history = [{
        "campaign_run_id": "sea_in_window",
        "overall_campaign_status": "SUCCESS",
        "final_message": "msg",
        "campaign_data": {},
    }]
    orc.sea_history_path.write_text(json.dumps(history))
    asyncio.run(orc._scan_sea_once())

    kinds = [e["kind"] for e in captured.events]
    assert "publication.coalesced" in kinds, f"got kinds={kinds}"
    coal = next(e for e in captured.events if e["kind"] == "publication.coalesced")
    assert coal["payload"]["reason"] == "within_min_gap_s"
    assert coal["payload"]["trigger_id"] == "sea_in_window"


# ── 5. Missing-ledger graceful read ──────────────────────────────


def test_read_publication_ledger_missing(monkeypatch, tmp_path):
    """Pull the helper directly and point it at an empty governance dir."""
    # The helper is defined inside main_service; we invoke it via a tiny shim
    # to avoid importing the entire FastAPI app for this one-line check.
    import importlib
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "governance").mkdir(parents=True, exist_ok=True)
    # _read_publication_ledger uses PROJECT_ROOT — patch it.
    ms = importlib.import_module("mindx_backend_service.main_service")
    monkeypatch.setattr(ms, "PROJECT_ROOT", tmp_path)
    out = ms._read_publication_ledger()
    assert out["ledger_exists"] is False
    assert out["published"] == []


def test_read_publication_ledger_present(monkeypatch, tmp_path):
    import importlib
    gov = tmp_path / "data" / "governance"
    gov.mkdir(parents=True, exist_ok=True)
    (gov / "published_triggers.json").write_text(json.dumps({
        "version": 1,
        "last_published_at": 1234.5,
        "published": [
            {"trigger_id": "x", "kind": "sea_campaign_success",
             "detected_at": 100.0, "published_at": 200.0,
             "post_id": 7, "url": "u", "title": "t"},
        ],
    }))
    ms = importlib.import_module("mindx_backend_service.main_service")
    monkeypatch.setattr(ms, "PROJECT_ROOT", tmp_path)
    out = ms._read_publication_ledger()
    assert out["ledger_exists"] is True
    assert len(out["published"]) == 1
    assert out["published"][0]["post_id"] == 7


# ── 6. eval_backfill judge resolver ──────────────────────────────


def test_eval_backfill_resolver_picks_pulled_model(monkeypatch):
    """The resolver probes endpoints + picks the first preferred model that
    is actually pulled — never a model the box does not have."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "eval_backfill",
        Path(__file__).parents[1] / "scripts" / "eval_backfill.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class _FakeResp:
        def __init__(self, body): self._body = body.encode()
        def read(self): return self._body
        def __enter__(self): return self
        def __exit__(self, *a): return False

    # localhost reachable, only qwen3:0.6b pulled (not the 1.7b default).
    def fake_urlopen(url, timeout=0):
        if "localhost:11434" in url:
            return _FakeResp(json.dumps({"models": [
                {"name": "qwen3:0.6b"}, {"name": "gpt-oss:120b-cloud"},
            ]}))
        raise OSError("unreachable")

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    url, model = mod._resolve_ollama_judge(None, None)
    assert url == "http://localhost:11434"
    assert model == "qwen3:0.6b", "must pick the pulled model, skip the 1.7b default"


def test_eval_backfill_resolver_none_when_unreachable(monkeypatch):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "eval_backfill",
        Path(__file__).parents[1] / "scripts" / "eval_backfill.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def always_fail(url, timeout=0):
        raise OSError("unreachable")

    monkeypatch.setattr("urllib.request.urlopen", always_fail)
    url, model = mod._resolve_ollama_judge(None, None)
    assert url is None and model is None


# ── 7. Secret redaction for public surfaces ──────────────────────


def test_sanitize_text_redacts_api_keys():
    from mindx_backend_service.text_render import sanitize_text
    assert "sk-" not in sanitize_text("key is sk-abcdefghij1234567890ABCDEF here")
    assert "AIza" not in sanitize_text("AIzaSyD-1234567890abcdefgh_ABCDEFGHIJ")
    assert "ghp_" not in sanitize_text("token ghp_0123456789abcdefghijABCDEFGHIJ")


def test_sanitize_text_redacts_eth_private_key():
    from mindx_backend_service.text_render import sanitize_text
    pk = "0x" + "a" * 64
    out = sanitize_text(f"signing with {pk}")
    assert pk not in out
    assert "<privkey>" in out


def test_sanitize_text_keeps_wallet_address():
    """ETH addresses (0x + 40 hex) are public identity — must NOT be redacted."""
    from mindx_backend_service.text_render import sanitize_text
    addr = "0x" + "b" * 40
    out = sanitize_text(f"agent at {addr}")
    assert addr in out, "wallet address is public identity, should survive"


def test_sanitize_text_redacts_jwt_and_kv_secrets():
    from mindx_backend_service.text_render import sanitize_text
    jwt = "eyJhbGciOiJIUzI1Ni1.eyJzdWIiOiIxMjM0NTY3.SflKxwRJSMeKKF2QT4"
    assert "<jwt>" in sanitize_text(f"auth {jwt}")
    out = sanitize_text('config api_key="supersecretvalue123"')
    assert "supersecretvalue123" not in out
    assert "<redacted>" in out


def test_sanitize_text_collapses_home_paths_and_truncates():
    from mindx_backend_service.text_render import sanitize_text
    assert "/home/hacker" not in sanitize_text("loaded /home/hacker/mindX/data/x.json")
    long = "word " * 100
    assert len(sanitize_text(long, max_len=50)) <= 50


def test_sanitize_text_empty_and_none():
    from mindx_backend_service.text_render import sanitize_text
    assert sanitize_text(None) == ""
    assert sanitize_text("") == ""


# ── 8. /insight/memory/recent — logs becoming memories ───────────


def test_memory_recent_tailer_returns_metadata_only(tmp_path, monkeypatch):
    """The memory.write tailer must NEVER return raw `content` / `context` —
    those carry sensitive payload. Only provenance metadata is allowed."""
    import importlib
    # Build a temp catalogue log with one memory.write event carrying content.
    cat = tmp_path / "catalogue_events.jsonl"
    evt = {
        "ts": 1778957046.0,
        "actor": "strategic_evolution_agent",
        "kind": "memory.write",
        "source_log": "logs/godel_choices.jsonl",
        "payload": {
            "memory_type": "system_state",
            "importance": 3,
            "agent_id": "strategic_evolution_agent",
            "memory_id": "abc123def456",
            "tags": ["godel.choice", "process_log"],
            "content": {"secret": "this must not leak", "api_key": "sk-leaky"},
            "context": {"campaign_id": "internal-only"},
        },
    }
    cat.write_text(json.dumps(evt) + "\n")

    # Point the catalogue log singleton at the temp file.
    from agents.catalogue.log import CatalogueEventLog
    original = CatalogueEventLog._default
    CatalogueEventLog._default = CatalogueEventLog(cat)
    try:
        ms = importlib.import_module("mindx_backend_service.main_service")
        rows = ms._read_memory_write_events(limit=10)
        assert len(rows) == 1
        row = rows[0]
        # Provenance metadata present.
        assert row["memory_type"] == "system_state"
        assert row["importance"] == 3
        assert row["source_log"] == "logs/godel_choices.jsonl"
        assert row["memory_id"] == "abc123def456"
        assert "godel.choice" in row["tags"]
        # Raw payload MUST be absent.
        assert "content" not in row, "memory content leaked into /insight/memory/recent"
        assert "context" not in row, "memory context leaked into /insight/memory/recent"
        # And the leaky string must not appear anywhere in the projected row.
        assert "this must not leak" not in json.dumps(row)
        assert "sk-leaky" not in json.dumps(row)
    finally:
        CatalogueEventLog._default = original


def test_memory_recent_tailer_skips_non_memory_events(tmp_path):
    import importlib
    cat = tmp_path / "catalogue_events.jsonl"
    lines = [
        json.dumps({"ts": 1.0, "actor": "a", "kind": "godel.choice",
                    "source_log": "x", "payload": {}}),
        json.dumps({"ts": 2.0, "actor": "b", "kind": "memory.write",
                    "source_log": "y", "payload": {"memory_type": "interaction",
                                                   "importance": 2, "memory_id": "m1"}}),
        json.dumps({"ts": 3.0, "actor": "c", "kind": "tool.invoke",
                    "source_log": "z", "payload": {}}),
    ]
    cat.write_text("\n".join(lines) + "\n")
    from agents.catalogue.log import CatalogueEventLog
    original = CatalogueEventLog._default
    CatalogueEventLog._default = CatalogueEventLog(cat)
    try:
        ms = importlib.import_module("mindx_backend_service.main_service")
        rows = ms._read_memory_write_events(limit=10)
        assert len(rows) == 1
        assert rows[0]["actor"] == "b"
        assert rows[0]["memory_type"] == "interaction"
    finally:
        CatalogueEventLog._default = original


def test_memory_recent_renderer_registered():
    from mindx_backend_service.text_render import RENDERERS, render_memory_recent
    assert RENDERERS.get("/insight/memory/recent") is render_memory_recent
    # Renderer tolerates empty + populated input.
    assert isinstance(render_memory_recent({"events": []}), str)
    out = render_memory_recent({"events": [
        {"ts": 1778957046.0, "actor": "agentx",
         "source_log": "data/memory/stm/agentx/x.memory.json",
         "memory_type": "interaction", "importance": 2},
    ]})
    assert "agentx" in out
    assert "HIGH" in out  # importance 2 → HIGH
