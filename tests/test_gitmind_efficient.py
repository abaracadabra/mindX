"""Tests for the efficient self-hosted gitmind (THOT/THlNK).

Covers: incremental basis->delta bundling, skip-on-no-change, the canon-congruent
THOT root + parent_root lineage chain, self-hosted bare origin clone, and full
reconstruction of the repo from the THlNK (the link of THOTs == distributed mindX).
All on throwaway repos in tmp_path; no network (Lighthouse/Arweave skip cleanly).
"""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

import pytest

from mindx.gitmind.gitmind import GitMind, ForgejoRemote


def _run(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


def _repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    _run("git", "init", "-q", str(path))
    _run("git", "-C", str(path), "config", "user.email", "t@t")
    _run("git", "-C", str(path), "config", "user.name", "t")
    return path


def _commit(repo: Path, name: str, content: str, msg: str):
    (repo / name).write_text(content)
    _run("git", "-C", str(repo), "add", "-A")
    _run("git", "-C", str(repo), "commit", "-q", "-m", msg)


def test_thot_root_is_canon_congruent_and_deterministic():
    # RFC-6962 prefixes, deterministic, 0x + 64 hex
    r1 = GitMind._thot_root(b"hello world")
    r2 = GitMind._thot_root(b"hello world")
    r3 = GitMind._thot_root(b"hello worlD")
    assert r1 == r2 and r1 != r3
    assert r1.startswith("0x") and len(r1) == 66


def test_basis_then_skip_then_incremental(tmp_path):
    repo = _repo(tmp_path / "repo")
    _commit(repo, "a.txt", "one", "c1")
    gm = GitMind(repo_root=repo)

    r1 = asyncio.run(gm.backup())
    assert r1["ok"] and r1["incremental"] is False and r1["seq"] == 0
    assert r1["parent_root"] == "0x" + "00" * 32          # genesis
    assert r1["thot_root"].startswith("0x")
    assert r1["self_host_ok"] is True                      # local origin synced

    # no new commits -> efficient no-op skip
    r2 = asyncio.run(gm.backup())
    assert r2.get("skipped") is True and r2["reason"] == "no new commits"

    # new commit -> incremental delta, parent chains to the basis root
    _commit(repo, "b.txt", "two", "c2")
    r3 = asyncio.run(gm.backup())
    assert r3["incremental"] is True and r3["seq"] == 1
    assert r3["parent_root"] == r1["thot_root"]            # the link of THOTs


def test_thlnk_lineage_and_id_changes(tmp_path):
    repo = _repo(tmp_path / "repo")
    _commit(repo, "a.txt", "one", "c1")
    gm = GitMind(repo_root=repo)
    asyncio.run(gm.backup())
    tk1 = gm.thlnk_summary()
    _commit(repo, "b.txt", "two", "c2")
    asyncio.run(gm.backup())
    tk2 = gm.thlnk_summary()
    assert tk1["count"] == 1 and tk2["count"] == 2
    assert tk2["thlnk_id"] != tk1["thlnk_id"]              # link changed
    # lineage spine chains: thot[1].parent == thot[0].thot_root
    lin = tk2["lineage"]
    assert lin[1]["parent_root"] == lin[0]["thot_root"]


def test_self_host_clone_restores_exact_head(tmp_path):
    repo = _repo(tmp_path / "repo")
    _commit(repo, "a.txt", "one", "c1")
    _commit(repo, "b.txt", "two", "c2")
    gm = GitMind(repo_root=repo)
    asyncio.run(gm.backup())
    dest = tmp_path / "clone"
    cl = gm.clone_self_host(dest)
    assert cl["ok"] and cl["head"] == gm.state()["head"]
    assert (dest / "a.txt").exists() and (dest / "b.txt").exists()


def test_reconstruct_from_thlnk_rebuilds_repo(tmp_path):
    """The link of THOTs IS the repo — applying the bundle chain in order rebuilds
    exactly the origin (distributed mindX)."""
    repo = _repo(tmp_path / "repo")
    _commit(repo, "a.txt", "one", "c1")
    gm = GitMind(repo_root=repo)
    asyncio.run(gm.backup())
    _commit(repo, "b.txt", "two", "c2")
    asyncio.run(gm.backup())
    origin_head = gm.state()["head"]

    dest = tmp_path / "rebuild"
    rc = gm.reconstruct_from_thlnk(dest)
    assert rc["ok"] and rc["applied"] == [0, 1]
    assert rc["head"] == origin_head
    assert (dest / "a.txt").read_text() == "one"
    assert (dest / "b.txt").read_text() == "two"


def test_report_surfaces_self_host_and_thlnk(tmp_path):
    repo = _repo(tmp_path / "repo")
    _commit(repo, "a.txt", "one", "c1")
    gm = GitMind(repo_root=repo)
    asyncio.run(gm.backup())
    rep = gm.report()
    assert rep["self_host"]["initialized"] is True
    assert rep["thlnk"]["count"] == 1 and rep["thlnk"]["head_thot_root"]
    assert "sources" in rep and "local" in rep["sources"]
    # forgejo leg is present and dormant by default (no env/vault config)
    assert rep["forgejo"]["configured"] is False


# ── Forgejo forge leg ─────────────────────────────────────────────────────
def test_forgejo_dormant_when_unconfigured(monkeypatch, tmp_path):
    for k in ("MINDX_FORGEJO_URL", "MINDX_FORGEJO_TOKEN", "MINDX_FORGEJO_USER", "MINDX_FORGEJO_REPO"):
        monkeypatch.delenv(k, raising=False)
    fr = ForgejoRemote(tmp_path)
    assert fr.configured() is False
    # push short-circuits cleanly (no network), reports not_configured
    res = fr.push()
    assert res["ok"] is False and "not_configured" in res["status"]
    # status is safe to display and contains no token
    st = fr.status()
    assert st["configured"] is False and st["url"] is None


def test_forgejo_configured_builds_redacted_urls(monkeypatch, tmp_path):
    monkeypatch.setenv("MINDX_FORGEJO_URL", "https://git.pythai.net")
    monkeypatch.setenv("MINDX_FORGEJO_TOKEN", "supersecrettoken123")
    monkeypatch.setenv("MINDX_FORGEJO_USER", "mindx")
    monkeypatch.setenv("MINDX_FORGEJO_REPO", "mindx/mindX")
    fr = ForgejoRemote(tmp_path)
    assert fr.configured() is True
    # public clone URL is token-free
    assert fr.clone_url() == "https://git.pythai.net/mindx/mindX.git"
    assert "supersecrettoken123" not in fr.clone_url()
    # auth URL embeds creds (used only as a subprocess arg, never logged)
    assert "supersecrettoken123" in fr._auth_url()
    # status never leaks the token
    assert "supersecrettoken123" not in json.dumps(fr.status())
    # _scrub defangs the token if git echoes it in an error
    leaked = "fatal: https://mindx:supersecrettoken123@git.pythai.net/... failed"
    assert "supersecrettoken123" not in fr._scrub(leaked)
    assert "***" in fr._scrub(leaked)
