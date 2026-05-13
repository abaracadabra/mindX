# SPDX-License-Identifier: Apache-2.0
"""Smoke test for ``scripts/run_curator.py`` — the systemd-driver shim.

The mindx-curator.service unit exec's exactly this CLI; if it crashes the
weekly timer is a no-op. We don't re-test Curator's audit logic
(``tests/test_curator.py`` already does that); we just verify the shim:

  1. Returns exit 0 on an empty SkillStore in dry-run mode.
  2. Returns exit 0 on an empty SkillStore with ``--apply``.
  3. Writes a JSON report to ``--report-dir`` with the expected shape.
  4. Prints a one-line summary on stderr (the journal-friendly line).

The shim is invoked in-process via ``main(argv)`` so we don't need a
subprocess and the tests stay deterministic. Each test isolates state with
``MINDX_SKILLS_DIR``/``MINDX_SKILLS_INDEX_DB`` env vars pointing into
``tmp_path``.
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def shim_main(monkeypatch, tmp_path):
    """Reload the shim so its module-level ``SkillStore()`` picks up the
    sandboxed ``MINDX_SKILLS_DIR`` we set per-test."""
    monkeypatch.setenv("MINDX_SKILLS_DIR", str(tmp_path / "skills"))
    monkeypatch.setenv("MINDX_SKILLS_INDEX_DB", str(tmp_path / "skills.db"))
    # Ensure the repo root is on the path the same way the shim does it.
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    import scripts.run_curator as shim
    importlib.reload(shim)
    return shim.main


def test_shim_dry_run_empty_store_exits_zero(shim_main, tmp_path, capsys):
    report_dir = tmp_path / "reports"
    rc = shim_main(["--quiet", "--report-dir", str(report_dir)])
    assert rc == 0
    err = capsys.readouterr().err
    # journal-friendly summary line lands on stderr
    assert "curator dry-run" in err
    assert "0 skills inspected" in err
    # A report was persisted even on an empty run
    reports = list(report_dir.glob("*.json"))
    assert len(reports) == 1
    data = json.loads(reports[0].read_text())
    assert data["inspected"] == 0
    assert data["flagged_count"] == 0
    assert data["archived_count"] == 0
    assert data["apply"] is False


def test_shim_apply_empty_store_exits_zero(shim_main, tmp_path, capsys):
    report_dir = tmp_path / "reports"
    rc = shim_main(["--apply", "--quiet", "--report-dir", str(report_dir)])
    assert rc == 0
    err = capsys.readouterr().err
    assert "curator applied" in err
    data = json.loads(next(report_dir.glob("*.json")).read_text())
    assert data["apply"] is True
    assert data["inspected"] == 0
    assert data["archived_count"] == 0


def test_shim_prints_json_report_to_stdout_without_quiet(shim_main, tmp_path, capsys):
    report_dir = tmp_path / "reports"
    rc = shim_main(["--report-dir", str(report_dir)])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)   # stdout is valid JSON
    assert parsed["inspected"] == 0
    assert parsed["apply"] is False
    assert "duration_seconds" in parsed


def test_shim_honors_stale_days_and_min_body_bytes(shim_main, tmp_path):
    """The CLI must thread its tuning knobs into the Curator constructor.
    With no skills in the store the values are unobservable in the output,
    so we check by mocking and capturing the Curator init call."""
    import scripts.run_curator as shim
    captured: dict = {}

    real_curator = shim.Curator

    class _CapturingCurator(real_curator):
        def __init__(self, store, **kw):
            captured.update(kw)
            super().__init__(store, **kw)

    shim.Curator = _CapturingCurator
    try:
        rc = shim.main([
            "--quiet", "--stale-days", "14", "--min-body-bytes", "100",
            "--report-dir", str(tmp_path / "reports"),
        ])
    finally:
        shim.Curator = real_curator
    assert rc == 0
    assert captured["stale_days"] == 14
    assert captured["min_body_bytes"] == 100
