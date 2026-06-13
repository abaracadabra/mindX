"""agents/github_awareness.py — mindX's awareness of its own public code history.

A GitHub push is already public, already structured, and already the
authoritative record of every change mindX makes to itself. So the cheapest,
most honest milestone signal is the git log itself — no extra plumbing, no
privacy question (the push is public by definition).

This module reads the LOCAL git history via subprocess (`git log`) — zero
network, no credentials, works directly on the production checkout at
/home/mindx/mindX. The public GitHub commit URL is derived for citation in
published articles. A GitHub-API enrichment path is left as an optional hook
for hosts without a local checkout.

Pure stdlib + git subprocess. Defensive: every method degrades to empty/None
rather than raising, so an awareness failure never takes down the author.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    from utils.config import PROJECT_ROOT  # type: ignore
except Exception:  # pragma: no cover - standalone import
    PROJECT_ROOT = Path(__file__).resolve().parents[1]

_DEFAULT_PUBLIC_REPO = "https://github.com/AgenticPlace/mindX"
_WATERMARK_PATH = PROJECT_ROOT / "data" / "governance" / "author_github_watermark.json"

# git log field separators (unlikely to appear in commit text)
_F = "\x1f"   # between fields
_R = "\x1e"   # between records


@dataclass
class Commit:
    """One commit, parsed from the local git log."""
    sha: str
    short_sha: str
    author: str
    date_iso: str
    subject: str
    body: str
    files: list[dict] = field(default_factory=list)   # {path, added, deleted}
    insertions: int = 0
    deletions: int = 0

    @property
    def files_changed(self) -> int:
        return len(self.files)

    def public_url(self, base: str) -> str:
        return f"{base.rstrip('/')}/commit/{self.sha}"

    def to_dict(self) -> dict:
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "author": self.author,
            "date_iso": self.date_iso,
            "subject": self.subject,
            "body": self.body,
            "files": self.files,
            "files_changed": self.files_changed,
            "insertions": self.insertions,
            "deletions": self.deletions,
        }


class GitHubAwareness:
    """Reads mindX's own commit history; the milestone signal source."""

    def __init__(self, repo_root: Optional[Path] = None,
                 public_repo_url: Optional[str] = None,
                 ref: Optional[str] = None):
        self.repo_root = Path(repo_root or PROJECT_ROOT)
        self.public_repo_url = (
            public_repo_url
            or os.environ.get("MINDX_GITHUB_REPO_URL")
            or self._derive_public_url()
        )
        # The git ref whose history is the milestone signal. Defaults to HEAD, but
        # on the VPS the working tree is deployed by scp and HEAD sits on a stale
        # backup branch with no commits — so prod sets
        # MINDX_GITHUB_AWARENESS_REF=origin/feat/obs-phase1 and fetch() refreshes
        # that remote-tracking ref (no working-tree change) before reading.
        self.ref = (ref or os.environ.get("MINDX_GITHUB_AWARENESS_REF") or "HEAD").strip()

    # ── git plumbing ────────────────────────────────────────────────

    def _git(self, *args: str, timeout: int = 15) -> Optional[str]:
        try:
            out = subprocess.run(
                ["git", *args], cwd=str(self.repo_root),
                capture_output=True, text=True, timeout=timeout,
            )
            if out.returncode != 0:
                return None
            return out.stdout
        except (OSError, subprocess.TimeoutExpired):
            return None

    def is_repo(self) -> bool:
        return self._git("rev-parse", "--is-inside-work-tree") is not None

    def fetch(self) -> bool:
        """Refresh remote-tracking refs when ``self.ref`` is a remote ref
        (e.g. ``origin/feat/obs-phase1``). Updates only refs/remotes — never the
        working tree — so it is safe on the scp-deployed VPS. No-op for local refs.
        Best-effort; returns True on a successful fetch."""
        ref = self.ref or "HEAD"
        if "/" not in ref or ref == "HEAD":
            return False
        remote, branch = ref.split("/", 1)
        return self._git("fetch", remote, branch, "--quiet", timeout=60) is not None

    def head_sha(self) -> Optional[str]:
        out = self._git("rev-parse", self.ref or "HEAD")
        return out.strip() if out else None

    def _derive_public_url(self) -> str:
        """Normalize whatever remote is configured to the public GitHub URL.

        The prod/sandbox remote may be a local proxy; we only need owner/repo.
        """
        out = self._git("remote", "get-url", "origin") or ""
        m = re.search(r"([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?\s*$", out.strip())
        if m:
            owner, repo = m.group(1), m.group(2)
            # Guard against picking up proxy host segments.
            if owner and repo and owner.lower() not in ("git", "127.0.0.1"):
                return f"https://github.com/{owner}/{repo}"
        return _DEFAULT_PUBLIC_REPO

    def public_commit_url(self, sha: str) -> str:
        return f"{self.public_repo_url.rstrip('/')}/commit/{sha}"

    def public_compare_url(self, base_sha: str, head_sha: str) -> str:
        return f"{self.public_repo_url.rstrip('/')}/compare/{base_sha}...{head_sha}"

    # ── commit reading ──────────────────────────────────────────────

    def commits_since(self, since_sha: Optional[str] = None, *,
                      max_n: int = 50, include_merges: bool = False,
                      fallback_days: int = 14) -> list[Commit]:
        """Return commits newer than `since_sha` (exclusive), newest last.

        If `since_sha` is None/unknown, falls back to the last `fallback_days`.
        Zero network — pure local `git log`.
        """
        # Record sep PREFIXES each commit so the trailing --numstat lines stay
        # within the same record as their commit (not bleeding into the next).
        target = self.ref or "HEAD"
        fmt = _R + _F.join(["%H", "%h", "%an", "%aI", "%s", "%b"])
        args = ["log", f"--pretty=format:{fmt}", "--numstat", f"--max-count={max_n}"]
        if not include_merges:
            args.append("--no-merges")
        if since_sha:
            args.append(f"{since_sha}..{target}")
        else:
            args.append(f"--since={fallback_days} days ago")
            args.append(target)
        raw = self._git(*args)
        if not raw:
            return []
        commits = self._parse_log(raw)
        commits.reverse()  # oldest → newest
        return commits

    @staticmethod
    def _parse_log(raw: str) -> list[Commit]:
        commits: list[Commit] = []
        for record in raw.split(_R):
            if not record.strip():
                continue
            # 6 header fields are _F-separated; the 6th (body) is followed by
            # the --numstat lines on subsequent newlines within this record.
            fields = record.split(_F)
            if len(fields) < 6:
                continue
            sha, short, author, date_iso, subject, rest = fields[:6]
            # `rest` = body + "\n" + numstat lines. Numstat lines look like:
            #   "<added>\t<deleted>\t<path>"
            body_lines: list[str] = []
            files: list[dict] = []
            ins = dels = 0
            for ln in rest.split("\n"):
                m = re.match(r"^(\d+|-)\t(\d+|-)\t(.+)$", ln)
                if m:
                    a = 0 if m.group(1) == "-" else int(m.group(1))
                    d = 0 if m.group(2) == "-" else int(m.group(2))
                    files.append({"path": m.group(3), "added": a, "deleted": d})
                    ins += a
                    dels += d
                elif ln.strip():
                    body_lines.append(ln)
            commits.append(Commit(
                sha=sha.strip(), short_sha=short.strip(), author=author.strip(),
                date_iso=date_iso.strip(), subject=subject.strip(),
                body="\n".join(body_lines).strip(), files=files,
                insertions=ins, deletions=dels,
            ))
        return commits

    # ── watermark (last sha mindX has already considered) ───────────

    def read_watermark(self) -> Optional[str]:
        try:
            d = json.loads(_WATERMARK_PATH.read_text(encoding="utf-8"))
            return d.get("last_sha")
        except Exception:
            return None

    def write_watermark(self, sha: str) -> None:
        try:
            _WATERMARK_PATH.parent.mkdir(parents=True, exist_ok=True)
            _WATERMARK_PATH.write_text(
                json.dumps({"last_sha": sha}), encoding="utf-8")
        except Exception:
            pass
