"""Proof-suite for simplecoder.tools.Sandbox — the SimpleCoderAgent boundary.

Each test asserts ONE containment guarantee. Together they are the "proof of
absolute" for the in-process boundary: path containment, symlink-escape
rejection, command allowlisting, argument-path containment, escape-flag denial,
environment scrubbing, bounded file I/O, execution timeout (with process-group
kill), and bounded output.

Async paths use ``asyncio.run`` directly so the suite needs no pytest-asyncio.
"""
import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.simple_coder_tools import (  # noqa: E402
    Sandbox,
    SandboxPolicy,
    SandboxViolation,
    default_policy,
)


def mk(tmp_path, **policy_kw) -> Sandbox:
    # Proof-suite targets the IN-PROCESS boundary deterministically, so OS
    # isolation (bwrap/nsjail) is disabled here; it is a bonus kernel-enforced
    # layer tested separately when available.
    policy_kw.setdefault("use_os_isolation", False)
    from dataclasses import replace
    pol = replace(default_policy(), **policy_kw)
    return Sandbox(tmp_path / "sbx", policy=pol)


# ── path containment ──────────────────────────────────────────────────────────
def test_relative_path_inside_ok(tmp_path):
    sb = mk(tmp_path)
    p = sb.resolve("sub/file.txt")
    assert p.is_relative_to(sb.root)


def test_dotdot_traversal_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.resolve("../../etc/passwd")


def test_absolute_outside_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.resolve("/etc/passwd")


def test_absolute_inside_ok(tmp_path):
    sb = mk(tmp_path)
    inside = str(sb.root / "ok.txt")
    assert sb.resolve(inside).is_relative_to(sb.root)


def test_is_contained_helper(tmp_path):
    sb = mk(tmp_path)
    assert sb.is_contained("a/b.txt")
    assert not sb.is_contained("/etc/shadow")


# ── symlink escape ─────────────────────────────────────────────────────────────
def test_symlink_escape_denied(tmp_path):
    sb = mk(tmp_path)
    outside = tmp_path / "secret"
    outside.mkdir()
    (outside / "loot.txt").write_text("secret")
    link = sb.root / "escape"
    os.symlink(outside, link)
    # realpath of escape/loot.txt is outside → denied
    with pytest.raises(SandboxViolation):
        sb.resolve("escape/loot.txt")


def test_symlink_inside_ok(tmp_path):
    sb = mk(tmp_path)
    (sb.root / "real").mkdir()
    (sb.root / "real" / "f.txt").write_text("hi")
    os.symlink(sb.root / "real", sb.root / "link")
    # symlink pointing INSIDE is fine
    assert sb.resolve("link/f.txt").is_relative_to(sb.root)


# ── command allowlist + argument containment ───────────────────────────────────
def test_command_not_allowlisted(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.check_argv(["curl", "http://evil"])


def test_allowlisted_command_ok(tmp_path):
    sb = mk(tmp_path)
    sb.check_argv(["ls", "-la"])  # no raise


def test_arg_absolute_path_escape_denied(tmp_path):
    sb = mk(tmp_path)
    # `cat` is allowlisted but reading /etc/passwd must be blocked
    with pytest.raises(SandboxViolation):
        sb.check_argv(["cat", "/etc/passwd"])


def test_arg_dotdot_escape_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.check_argv(["rm", "../../home/user/.ssh/id_rsa"])


def test_arg_tilde_escape_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.check_argv(["cat", "~/.ssh/id_rsa"])


def test_arg_bare_relative_ok(tmp_path):
    sb = mk(tmp_path)
    sb.check_argv(["cat", "notes.txt"])  # inside cwd → fine


def test_find_exec_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.check_argv(["find", ".", "-exec", "rm", "-rf", "/", ";"])


def test_find_delete_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.check_argv(["find", ".", "-delete"])


def test_git_c_flag_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.check_argv(["git", "-c", "core.fsmonitor=evil", "status"])


def test_python_inline_allowed_by_default(tmp_path):
    sb = mk(tmp_path)
    sb.check_argv(["python3", "-c", "print(1)"])  # default policy permits


def test_python_inline_denied_in_strict(tmp_path):
    sb = Sandbox(tmp_path / "sbx", policy=default_policy().strict())
    # strict drops interpreters entirely → not allowlisted
    with pytest.raises(SandboxViolation):
        sb.check_argv(["python3", "-c", "print(1)"])


def test_strict_removes_interpreters(tmp_path):
    pol = default_policy().strict()
    assert "python3" not in pol.allowed_commands
    assert "pip" not in pol.allowed_commands
    assert "ls" in pol.allowed_commands  # safe commands remain


# ── environment scrubbing ──────────────────────────────────────────────────────
def test_env_scrubbed(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret")
    monkeypatch.setenv("MINDX_VAULT_KEY", "topsecret")
    sb = mk(tmp_path)
    env = sb.scrubbed_env()
    assert "ANTHROPIC_API_KEY" not in env
    assert "MINDX_VAULT_KEY" not in env
    assert "PATH" in env
    assert env["HOME"] == str(sb.root)


# ── bounded file I/O ────────────────────────────────────────────────────────────
def test_write_read_roundtrip(tmp_path):
    sb = mk(tmp_path)
    sb.write_text("a/b.txt", "hello")
    assert sb.read_text("a/b.txt") == "hello"


def test_write_too_large_denied(tmp_path):
    sb = mk(tmp_path, max_file_bytes=16)
    with pytest.raises(SandboxViolation):
        sb.write_text("big.txt", "x" * 17)


def test_read_too_large_denied(tmp_path):
    sb = mk(tmp_path, max_file_bytes=16)
    p = sb.root / "big.txt"
    p.write_text("x" * 100)
    with pytest.raises(SandboxViolation):
        sb.read_text("big.txt")


def test_write_outside_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.write_text("/tmp/evil.txt", "nope")


# ── execution ───────────────────────────────────────────────────────────────────
def test_run_success(tmp_path):
    sb = mk(tmp_path)
    assert sb.isolation_backend is None  # disabled for the in-process proof
    res = asyncio.run(sb.run(["python3", "-c", "print('hi')"]))
    assert res["status"] == "SUCCESS", res
    assert "hi" in res["stdout"]


def test_run_rejects_disallowed_command(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        asyncio.run(sb.run(["curl", "http://evil"]))


def test_run_rejects_arg_escape(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        asyncio.run(sb.run(["cat", "/etc/passwd"]))


def test_run_timeout_kills(tmp_path):
    sb = mk(tmp_path, command_timeout=1)
    res = asyncio.run(sb.run(["python3", "-c", "import time; time.sleep(30)"], timeout=1))
    assert res["status"] == "TIMEOUT", res


def test_run_output_capped(tmp_path):
    sb = mk(tmp_path, max_output_bytes=1024)
    res = asyncio.run(sb.run(["python3", "-c", "print('A'*100000)"]))
    assert res["truncated"] is True
    assert len(res["stdout"].encode()) <= 1024


def test_run_failure_nonzero(tmp_path):
    sb = mk(tmp_path)
    res = asyncio.run(sb.run(["python3", "-c", "import sys; sys.exit(3)"]))
    assert res["status"] == "FAILURE"
    assert res["return_code"] == 3


# ── introspection ──────────────────────────────────────────────────────────────
def test_info_is_inspectable(tmp_path):
    sb = mk(tmp_path)
    info = sb.info()
    assert info["root"] == str(sb.root)
    assert "limits" in info and info["limits"]["cpu_seconds"] == 30
    assert "rlimits_available" in info


# ── archive inspection / extraction (zip-bomb safe) ────────────────────────────
def _make_zip(path: Path, members: dict) -> None:
    """Write a zip with {arcname: bytes|str}. arcname may be hostile (e.g. ``..``)."""
    import zipfile
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for arcname, data in members.items():
            if isinstance(data, str):
                data = data.encode()
            zf.writestr(arcname, data)


def test_inspect_zip_reports_members(tmp_path):
    sb = mk(tmp_path)
    z = sb.root / "pkg.zip"
    _make_zip(z, {"a.py": "x = 1\n", "b/c.txt": "hello"})
    info = sb.inspect_zip("pkg.zip")
    assert info["status"] == "SUCCESS"
    assert info["member_count"] == 2
    assert info["potential_issues"] == ["none"]
    names = {m["name"] for m in info["members"]}
    assert names == {"a.py", "b/c.txt"}


def test_inspect_zip_flags_traversal(tmp_path):
    sb = mk(tmp_path)
    z = sb.root / "evil.zip"
    _make_zip(z, {"../escape.txt": "pwned"})
    info = sb.inspect_zip("evil.zip")
    assert info["status"] == "SUCCESS"
    assert any(i.startswith("path_traversal") for i in info["potential_issues"])


def test_inspect_zip_flags_nested_archive(tmp_path):
    sb = mk(tmp_path)
    z = sb.root / "nest.zip"
    _make_zip(z, {"inner.zip": b"PK\x03\x04stub"})
    info = sb.inspect_zip("nest.zip")
    assert any(i.startswith("nested_archive") for i in info["potential_issues"])


def test_inspect_non_zip(tmp_path):
    sb = mk(tmp_path)
    (sb.root / "plain.zip").write_text("not a zip at all")
    info = sb.inspect_zip("plain.zip")
    assert info["status"] == "ERROR"
    assert "not_a_zip" in info["potential_issues"]


def test_inspect_zip_outside_sandbox_denied(tmp_path):
    sb = mk(tmp_path)
    with pytest.raises(SandboxViolation):
        sb.inspect_zip("../../etc/secret.zip")


def test_extract_zip_happy_path(tmp_path):
    sb = mk(tmp_path)
    z = sb.root / "good.zip"
    _make_zip(z, {"mod.py": "y = 2\n", "sub/data.txt": "ok"})
    res = asyncio.run(sb.extract_zip("good.zip", "out"))
    assert res["status"] == "SUCCESS"
    assert res["members_extracted"] == 2
    assert (sb.root / "out" / "mod.py").read_text() == "y = 2\n"
    assert (sb.root / "out" / "sub" / "data.txt").read_text() == "ok"


def test_extract_zip_blocks_traversal(tmp_path):
    sb = mk(tmp_path)
    z = sb.root / "evil.zip"
    _make_zip(z, {"../escape.txt": "pwned"})
    res = asyncio.run(sb.extract_zip("evil.zip", "out"))
    assert res["status"] == "FAILURE"
    assert any("path_traversal_blocked" in m or "escape_blocked" in m for m in res["messages"])
    # nothing escaped the sandbox
    assert not (tmp_path / "escape.txt").exists()


def test_extract_zip_member_cap(tmp_path):
    sb = mk(tmp_path, max_archive_members=2)
    z = sb.root / "many.zip"
    _make_zip(z, {f"f{i}.txt": "x" for i in range(5)})
    res = asyncio.run(sb.extract_zip("many.zip", "out"))
    assert res["status"] == "FAILURE"
    assert any("too_many_members" in m for m in res["messages"])


def test_extract_zip_decompressed_cap(tmp_path):
    sb = mk(tmp_path)
    z = sb.root / "big.zip"
    # one ~1MiB highly-compressible member; cap extraction at well under that.
    _make_zip(z, {"big.txt": "A" * (1024 * 1024)})
    res = asyncio.run(sb.extract_zip("big.zip", "out", max_decompressed_mb=0))
    assert res["status"] == "FAILURE"
    assert any("decompressed" in m for m in res["messages"])


def test_extract_zip_dest_outside_denied(tmp_path):
    sb = mk(tmp_path)
    z = sb.root / "ok.zip"
    _make_zip(z, {"a.txt": "hi"})
    with pytest.raises(SandboxViolation):
        asyncio.run(sb.extract_zip("ok.zip", "../outside"))
