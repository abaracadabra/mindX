# SPDX-License-Identifier: Apache-2.0
"""Hostile-archive fixtures + guard-chain smoke tests.

Helpers to craft the attack archives the Sandbox must reject, plus smoke tests
proving the guard chain is active in THIS environment. Run these alongside
``test_external_package_template.py`` — if they fail, the boundary is not
enforcing and a green package run proves nothing.

Canonical exhaustive coverage lives in ``tests/test_simple_coder_sandbox.py``;
these are the in-sandbox sanity sentinels.
"""
import asyncio
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.simple_coder_tools import Sandbox  # noqa: E402

SANDBOX_ROOT = PROJECT_ROOT / "simple_coder_sandbox"


# ── fixture builders (reusable for any future guard test) ────────────────────
def make_traversal_zip(path: Path) -> Path:
    """Archive whose member writes outside its extraction root."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("../escaped.txt", "pwned")
    return path


def make_bomb_zip(path: Path, member_mb: int = 8) -> Path:
    """Highly-compressible archive for decompressed-size-cap checks."""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("bomb.txt", "A" * (member_mb * 1024 * 1024))
    return path


def make_many_members_zip(path: Path, count: int = 64) -> Path:
    """Archive with many members for member-count-cap checks."""
    with zipfile.ZipFile(path, "w") as zf:
        for i in range(count):
            zf.writestr(f"f{i}.txt", "x")
    return path


# ── guard-chain sentinels ─────────────────────────────────────────────────────
@pytest.fixture()
def sandbox() -> Sandbox:
    return Sandbox(SANDBOX_ROOT)


@pytest.fixture()
def temp_zip(sandbox):
    p = SANDBOX_ROOT / "temp" / "hostile_fixture.zip"
    p.parent.mkdir(parents=True, exist_ok=True)
    yield p
    import shutil
    p.unlink(missing_ok=True)
    shutil.rmtree(SANDBOX_ROOT / "temp" / "hostile_out", ignore_errors=True)


def test_traversal_is_flagged_and_blocked(sandbox, temp_zip):
    make_traversal_zip(temp_zip)
    info = sandbox.inspect_zip("temp/hostile_fixture.zip")
    assert any(i.startswith("path_traversal") for i in info["potential_issues"])
    res = asyncio.run(sandbox.extract_zip("temp/hostile_fixture.zip", "temp/hostile_out"))
    assert res["status"] == "FAILURE"
    assert not (SANDBOX_ROOT / "escaped.txt").exists()
    assert not (PROJECT_ROOT / "escaped.txt").exists()


def test_decompressed_cap_enforced(sandbox, temp_zip):
    make_bomb_zip(temp_zip, member_mb=8)
    res = asyncio.run(sandbox.extract_zip(
        "temp/hostile_fixture.zip", "temp/hostile_out", max_decompressed_mb=1))
    assert res["status"] == "FAILURE"
    assert any("decompressed" in m for m in res["messages"])


def test_member_cap_enforced(sandbox, temp_zip):
    make_many_members_zip(temp_zip, count=64)
    res = asyncio.run(sandbox.extract_zip(
        "temp/hostile_fixture.zip", "temp/hostile_out", max_members=8))
    assert res["status"] == "FAILURE"
    assert any("too_many_members" in m for m in res["messages"])
