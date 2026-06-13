"""mindXtrain v1.0.0 bridge — capability/version detection, CPU-train path,
dcoach verdict, the two-flag autonomous gate, and Ollama promotion.

All subprocess/network is mocked — no real uv / ollama / mindXtrain needed.
The load-bearing safety test is `test_arming_bridge_alone_does_not_train`.
"""
from __future__ import annotations

import asyncio
import types

import pytest

from mindx.godel.mindxtrain import bridge as B
from mindx.godel.mindxtrain import dcoach as D


# ── capability / version ────────────────────────────────────────────────


def test_version_parse_and_compare():
    assert B._parse_version("mindxtrain 1.0.0") == "1.0.0"
    assert B._parse_version("v1.2.3-rc") == "1.2.3"
    assert B._parse_version("no version here") is None
    assert B._ge_version("1.0.0", "1.0.0") is True
    assert B._ge_version("0.9.9", "1.0.0") is False
    assert B._ge_version(None) is False


def test_dormant_host_does_no_subprocess(monkeypatch):
    """absent install → discover() must not shell out at all."""
    called = {"n": 0}
    def _boom(*a, **k):
        called["n"] += 1
        raise AssertionError("subprocess must not run on a dormant host")
    monkeypatch.setattr(B.subprocess, "run", _boom)
    monkeypatch.setattr(B.shutil, "which", lambda *_: None)
    monkeypatch.setenv("MINDXTRAIN_HOME", "/nonexistent/mindxtrain")
    cap = B.discover()
    assert cap.installed is False and cap.level == "absent"
    assert called["n"] == 0


def test_probe_detects_cpu_train_active(monkeypatch):
    def fake_run(cmd, **k):
        out = types.SimpleNamespace(returncode=0, stderr="")
        if "--version" in cmd:
            out.stdout = "mindxtrain 1.0.0"
        else:  # --help lists the verbs
            out.stdout = "Commands:\n  init\n  bench\n  train\n  dcoach\n  serve\n"
        return out
    monkeypatch.setattr(B.subprocess, "run", fake_run)
    version, verbs = B._probe("uv run mindxtrain", None)
    assert version == "1.0.0"
    assert "train" in verbs and "dcoach" in verbs


def test_discover_verb_flags(monkeypatch):
    B._FLAG_CACHE.clear()
    def fake_run(cmd, **k):
        return types.SimpleNamespace(
            returncode=0, stderr="",
            stdout="Usage: mindxtrain train\n  --config TEXT\n  --max-minutes INT\n")
    monkeypatch.setattr(B.subprocess, "run", fake_run)
    cap = B.Capability(installed=True, home=None, cli="mindxtrain", has_gpu=False, level="cpu")
    flags = B.discover_verb_flags("train", cap)
    assert "--config" in flags and "--max-minutes" in flags


# ── dcoach verdict ──────────────────────────────────────────────────────


def test_dcoach_parse_recall():
    assert D._parse_recall("recall 0.07 -> 0.28")[:2] == (0.07, 0.28)
    assert D._parse_recall("0.10 → 0.40")[:2] == (0.10, 0.40)
    b, a, v = D._parse_recall("recall_before: 0.05 recall_after: 0.30 PASSED")
    assert (b, a, v) == (0.05, 0.30, True)
    assert D._parse_recall("garbage")[:2] == (None, None)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_dcoach_verdict_accept_reject(monkeypatch):
    cap = B.Capability(installed=True, home=None, cli="mindxtrain", has_gpu=False,
                       level="cpu", verbs=("dcoach",))
    monkeypatch.setattr(B, "discover_verb_flags", lambda *a, **k: {"--config", "--json"})
    fr = types.SimpleNamespace(config_path=types.SimpleNamespace(name="mindx-gen1.yaml"))

    # positive imprint → accept
    monkeypatch.setattr(B, "run_cli", lambda *a, **k: {"ok": True, "stdout": "recall 0.07 -> 0.28 success"})
    v = _run(D.dcoach_verdict_factory(cap, "/tmp")(fr))
    assert v["accepted"] is True and v["delta"] == pytest.approx(0.21, abs=1e-6)

    # sub-threshold → reject
    monkeypatch.setattr(B, "run_cli", lambda *a, **k: {"ok": True, "stdout": "recall 0.20 -> 0.25"})
    v = _run(D.dcoach_verdict_factory(cap, "/tmp")(fr))
    assert v["accepted"] is False

    # unparseable → reject with reason
    monkeypatch.setattr(B, "run_cli", lambda *a, **k: {"ok": True, "stdout": "nonsense"})
    v = _run(D.dcoach_verdict_factory(cap, "/tmp")(fr))
    assert v["accepted"] is False and "unparseable" in v["reason"]


# ── the two-flag autonomous gate (load-bearing safety) ──────────────────


def test_arming_bridge_alone_does_not_train(monkeypatch):
    """Setting ONLY MINDX_ENABLE_MINDXTRAIN must NOT enable autonomous training.
    The autonomous ascent needs the SECOND flag too."""
    from mindx.godel import ascend_scheduler as S
    monkeypatch.setenv("MINDX_ENABLE_MINDXTRAIN", "1")
    monkeypatch.delenv("MINDX_ENABLE_AUTONOMOUS_TRAIN", raising=False)
    ok, reason = S.should_ascend({"resource_bound": False})
    assert ok is False and "both flags" in reason


def test_autonomous_gate_matrix(monkeypatch):
    from mindx.godel import ascend_scheduler as S
    monkeypatch.setenv("MINDX_ENABLE_MINDXTRAIN", "1")
    monkeypatch.setenv("MINDX_ENABLE_AUTONOMOUS_TRAIN", "1")
    cpu_cap = B.Capability(installed=True, home=None, cli="mindxtrain", has_gpu=False,
                           level="cpu", version="1.0.0", cpu_train_active=True)

    # resource_bound → never train
    ok, reason = S.should_ascend({"resource_bound": True}, cpu_cap)
    assert ok is False and "resource_bound" in reason

    # not cpu_train_active (old version) → no
    old_cap = B.Capability(installed=True, home=None, cli="mindxtrain", has_gpu=False,
                           level="cpu", version="0.9.0", cpu_train_active=False)
    ok, reason = S.should_ascend({"resource_bound": False}, old_cap)
    assert ok is False and "CPU-train-active" in reason

    # all gates pass (fresh watermark) → yes
    monkeypatch.setattr(S, "read_watermark", lambda *_: None)
    ok, reason = S.should_ascend({"resource_bound": False}, cpu_cap)
    assert ok is True

    # within cooldown → no
    import time as _t
    monkeypatch.setattr(S, "read_watermark", lambda *_: _t.time() - 3600)  # 1h ago, cooldown 24h
    ok, reason = S.should_ascend({"resource_bound": False}, cpu_cap)
    assert ok is False and "cooldown" in reason
