# mindx/agents/simple_coder_tools.py
"""simplecoder.tools — the enforcement boundary for SimpleCoderAgent.

Linux philosophy: do one thing and do it well. This module does exactly one
thing — it is the *boundary* of the coding sandbox. Everything SimpleCoderAgent
does to the filesystem or via subprocess goes through here, so the containment
logic lives in one auditable, exhaustively-tested place instead of being
re-implemented per file-operation.

What it enforces (defence in depth):

1. **Path containment** — every path resolves inside the sandbox root, checked
   both lexically and via ``realpath`` so a symlink *inside* the sandbox that
   points *outside* is rejected (the original agent's ``.resolve()``-only check
   missed the no-follow case and silently re-rooted absolute paths).
2. **Command allowlist** — argv[0]'s basename must be allowed.
3. **Argument-path containment** — any path-like argument (absolute, ``~``, or
   containing ``..``) must resolve inside the sandbox. This is what stops
   ``cat /etc/passwd`` and ``rm /home/user/.ssh/id_rsa`` even though ``cat`` and
   ``rm`` are allowlisted: the allowlist controls the *binary*, this controls
   *what it can touch*.
4. **Denied escape flags** — ``find -exec/-delete``, and (in strict mode)
   ``python -c`` inline code, which would otherwise be Turing-complete escapes.
5. **Scrubbed environment** — children get a minimal env, never the parent's
   secrets (API keys, vault paths, ``MINDX_*``).
6. **Resource limits** — POSIX ``setrlimit`` for CPU, address space, file size,
   open files, and process count (fork-bomb / memory-bomb containment), in a new
   session so the whole process group can be killed on timeout.
7. **Bounded output** — stdout/stderr capture is capped; a runaway producer is
   killed rather than exhausting memory.
8. **File-size limits** — reads and writes are bounded by policy.

PROOF OF ABSOLUTE — the honest part. In-process, items 2–4 cannot make a
general-purpose interpreter (``python``, ``pip`` running ``setup.py``) *absolutely*
contained: an interpreter you are allowed to run can open sockets and read any
file the process user can read. Items 1, 5, 6, 7, 8 *are* hard boundaries.
Absolute containment of interpreters requires OS-level isolation; this module
auto-detects ``bwrap`` (bubblewrap) / ``nsjail`` and, when present, wraps every
command so the kernel — not a Python check — enforces the boundary. When absent,
``Sandbox`` degrades to defence-in-depth and says so via ``isolation_backend``.
The accompanying test-suite proves each guarantee; see
``tests/test_simple_coder_sandbox.py``.
"""
from __future__ import annotations

import asyncio
import os
import shlex
import shutil
import signal
import zipfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

try:  # POSIX-only; absent on Windows.
    import resource as _resource
except Exception:  # pragma: no cover - non-POSIX
    _resource = None


class SandboxViolation(Exception):
    """Raised when an operation would cross the sandbox boundary or policy."""


# Commands that are interpreters / have an exec capability — allowlisting the
# binary does NOT contain them in-process. Tracked so policy + audit are explicit.
INTERPRETER_COMMANDS = frozenset({"python", "python3", "pip", "pip3", "sh", "bash", "node", "perl", "ruby"})

# Per-command flags that turn an otherwise-safe binary into an arbitrary-exec or
# unconfined-write primitive. Matched against the literal argument token.
DENIED_FLAGS: Dict[str, frozenset] = {
    "find": frozenset({"-exec", "-execdir", "-ok", "-okdir", "-delete", "-fprint", "-fprintf", "-fls"}),
    # `git -c` injects config (e.g. core.fsmonitor / hooks) → command exec.
    "git": frozenset({"-c", "--exec-path"}),
}
# Inline-code flags gated behind policy.allow_inline_code (strict mode denies).
INLINE_CODE_FLAGS: Dict[str, frozenset] = {
    "python": frozenset({"-c"}),
    "python3": frozenset({"-c"}),
    "sh": frozenset({"-c"}),
    "bash": frozenset({"-c"}),
    "node": frozenset({"-e", "--eval", "-p", "--print"}),
    "perl": frozenset({"-e", "-E"}),
    "ruby": frozenset({"-e"}),
}

# Env keys a child genuinely needs; everything else (secrets!) is dropped.
DEFAULT_ENV_PASSTHROUGH = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TERM", "TZ", "TMPDIR")


@dataclass(frozen=True)
class SandboxPolicy:
    """The complete, inspectable set of limits the sandbox enforces."""

    allowed_commands: frozenset = frozenset({
        "python", "python3", "pip", "pip3", "git", "ls", "cat", "grep", "find",
        "mkdir", "rm", "cp", "mv", "chmod", "touch", "head", "tail", "wc",
        "pytest", "black", "flake8", "mypy", "coverage", "tox", "ruff",
    })
    command_timeout: int = 60
    max_file_bytes: int = 10 * 1024 * 1024          # 10 MiB read/write cap
    max_output_bytes: int = 4 * 1024 * 1024         # 4 MiB stdout+stderr cap
    # archive extraction caps (zip-bomb / quota containment for inspect_zip/extract_zip)
    max_archive_members: int = 2048                 # reject archives with absurd member counts
    max_archive_decompressed_bytes: int = 256 * 1024 * 1024  # 256 MiB total uncompressed
    max_archive_ratio: int = 200                    # decompressed/compressed ratio flagged as a bomb
    cpu_seconds: int = 30                           # RLIMIT_CPU
    address_space_bytes: int = 2 * 1024 * 1024 * 1024  # RLIMIT_AS (2 GiB)
    max_processes: int = 64                         # RLIMIT_NPROC
    max_open_files: int = 256                       # RLIMIT_NOFILE
    env_passthrough: tuple = DEFAULT_ENV_PASSTHROUGH
    follow_symlinks: bool = False                   # reject symlink escapes
    allow_inline_code: bool = True                  # python -c etc. (strict=False)
    use_os_isolation: bool = True                   # wrap with bwrap/nsjail if present

    def strict(self) -> "SandboxPolicy":
        """A locked-down variant: no inline code, no interpreters at all."""
        return replace(
            self,
            allow_inline_code=False,
            allowed_commands=frozenset(self.allowed_commands - INTERPRETER_COMMANDS),
        )


def default_policy() -> SandboxPolicy:
    return SandboxPolicy()


class Sandbox:
    """The one boundary. Construct with a root dir; everything else is policy."""

    def __init__(self, root: Path | str, policy: Optional[SandboxPolicy] = None) -> None:
        self.root: Path = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.policy: SandboxPolicy = policy or default_policy()
        self.isolation_backend: Optional[str] = self._detect_isolation() if self.policy.use_os_isolation else None

    # ── isolation backend detection ──────────────────────────────────────────
    @staticmethod
    def _detect_isolation() -> Optional[str]:
        """Return a backend only if it is present AND can actually create the
        namespaces it needs. A binary that exists but fails at runtime (e.g.
        unprivileged namespaces disabled, or we are already inside a sandbox) is
        treated as absent — better to degrade to in-process defence-in-depth than
        to silently FAILURE every command."""
        for tool in ("bwrap", "nsjail"):
            if shutil.which(tool) and Sandbox._probe_isolation(tool):
                return tool
        return None

    @staticmethod
    def _probe_isolation(tool: str) -> bool:  # pragma: no cover - env-dependent
        import subprocess
        try:
            if tool == "bwrap":
                cmd = [
                    "bwrap", "--unshare-all",
                    "--ro-bind", "/usr", "/usr", "--ro-bind", "/bin", "/bin",
                    "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
                    "--", "true",
                ]
            else:  # nsjail
                cmd = ["nsjail", "--quiet", "--mode", "o", "--chroot", "/", "--", "true"]
            r = subprocess.run(cmd, capture_output=True, timeout=8)
            return r.returncode == 0
        except Exception:
            return False

    # ── path containment ─────────────────────────────────────────────────────
    def resolve(self, path_str: str, *, cwd: Optional[Path] = None, must_exist: bool = False) -> Path:
        """Resolve ``path_str`` and PROVE it stays inside the sandbox, or raise.

        Containment is checked against ``realpath`` (so symlink escapes are
        caught) and, when ``follow_symlinks`` is False, any existing symlink in
        the resolved chain that leaves the root is rejected explicitly.
        """
        if path_str is None or path_str == "":
            raise SandboxViolation("empty path")
        base = cwd.resolve() if cwd is not None else self.root
        if not self._within(base):
            raise SandboxViolation(f"cwd escapes sandbox: {base}")

        p = Path(path_str)
        # Absolute paths are NOT silently re-rooted (the old behaviour hid bugs);
        # they must already be inside the sandbox.
        candidate = p if p.is_absolute() else (base / p)

        real = Path(os.path.realpath(candidate))
        if not self._within(real):
            raise SandboxViolation(
                f"path traversal denied: {path_str!r} -> {real} is outside {self.root}"
            )
        if not self.policy.follow_symlinks and self._has_symlink_escape(candidate):
            raise SandboxViolation(f"symlink escape denied: {path_str!r}")
        if must_exist and not real.exists():
            raise SandboxViolation(f"path does not exist: {path_str!r}")
        return real

    def is_contained(self, path_str: str, *, cwd: Optional[Path] = None) -> bool:
        try:
            self.resolve(path_str, cwd=cwd)
            return True
        except SandboxViolation:
            return False

    def _within(self, p: Path) -> bool:
        try:
            return p == self.root or p.is_relative_to(self.root)
        except Exception:
            return False

    def _has_symlink_escape(self, candidate: Path) -> bool:
        """True if any *existing* component of ``candidate`` is a symlink whose
        real target leaves the sandbox root."""
        cur = candidate if candidate.is_absolute() else (self.root / candidate)
        seen = []
        for part in cur.parts:
            seen.append(part)
            sofar = Path(*seen)
            if sofar.is_symlink():
                tgt = Path(os.path.realpath(sofar))
                if not self._within(tgt):
                    return True
        return False

    # ── command checking ─────────────────────────────────────────────────────
    def check_argv(self, argv: Sequence[str], *, cwd: Optional[Path] = None) -> None:
        """Validate a command vector against the policy, or raise SandboxViolation."""
        if not argv:
            raise SandboxViolation("empty command")
        name = os.path.basename(argv[0])
        if name not in self.policy.allowed_commands:
            raise SandboxViolation(f"command not in allowlist: {name!r}")

        denied = DENIED_FLAGS.get(name, frozenset())
        inline = INLINE_CODE_FLAGS.get(name, frozenset())
        for tok in argv[1:]:
            if tok in denied:
                raise SandboxViolation(f"denied flag for {name}: {tok!r} (arbitrary-exec primitive)")
            if tok in inline and not self.policy.allow_inline_code:
                raise SandboxViolation(f"inline code denied for {name}: {tok!r} (strict mode)")
            self._check_arg_path(tok, cwd=cwd)

    def _check_arg_path(self, tok: str, *, cwd: Optional[Path]) -> None:
        """A path-like argument must stay inside the sandbox."""
        if tok.startswith("-"):
            return  # a flag, not a path
        looks_pathy = (
            os.path.isabs(tok)
            or tok.startswith("~")
            or ".." in tok.replace("\\", "/").split("/")
        )
        if not looks_pathy:
            return  # bare relative name → resolves inside cwd (already contained)
        expanded = os.path.expanduser(tok)  # catch ~ escapes
        if not self.is_contained(expanded, cwd=cwd):
            raise SandboxViolation(f"argument path escapes sandbox: {tok!r}")

    # ── environment ──────────────────────────────────────────────────────────
    def scrubbed_env(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        env: Dict[str, str] = {}
        for k in self.policy.env_passthrough:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        env.setdefault("PATH", "/usr/local/bin:/usr/bin:/bin")
        env["HOME"] = str(self.root)            # keep ~ inside the sandbox
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        if extra:
            env.update(extra)
        return env

    # ── resource limits ──────────────────────────────────────────────────────
    def _preexec(self):  # pragma: no cover - runs in child after fork
        if _resource is None:
            return None
        pol = self.policy

        def _apply():
            def _set(res, val):
                if val and hasattr(_resource, res):
                    try:
                        _resource.setrlimit(getattr(_resource, res), (val, val))
                    except (ValueError, OSError):
                        pass
            _set("RLIMIT_CPU", pol.cpu_seconds)
            _set("RLIMIT_AS", pol.address_space_bytes)
            _set("RLIMIT_FSIZE", pol.max_file_bytes)
            _set("RLIMIT_NOFILE", pol.max_open_files)
            _set("RLIMIT_NPROC", pol.max_processes)

        return _apply

    def _wrap_isolation(self, argv: List[str]) -> List[str]:
        """Wrap argv with bubblewrap/nsjail when available (kernel-enforced)."""
        if not self.isolation_backend:
            return argv
        if self.isolation_backend == "bwrap":
            return [
                "bwrap", "--unshare-all", "--die-with-parent",
                "--ro-bind", "/usr", "/usr", "--ro-bind", "/bin", "/bin",
                "--ro-bind", "/lib", "/lib", "--ro-bind", "/lib64", "/lib64",
                "--bind", str(self.root), str(self.root),
                "--chdir", str(self.root), "--proc", "/proc", "--dev", "/dev",
                "--",
                *argv,
            ]
        if self.isolation_backend == "nsjail":  # minimal; site config can extend
            return [
                "nsjail", "--quiet", "--mode", "o", "--chroot", "/",
                "--cwd", str(self.root), "--rw_bind", str(self.root),
                "--time_limit", str(self.policy.command_timeout), "--",
                *argv,
            ]
        return argv

    # ── execution ────────────────────────────────────────────────────────────
    async def run(
        self,
        command: str | Sequence[str],
        *,
        cwd: Optional[Path] = None,
        timeout: Optional[int] = None,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Run an allowlisted command with full containment. Never raises for
        process failure (returns FAILURE); raises SandboxViolation only when the
        request itself is disallowed."""
        argv = shlex.split(command) if isinstance(command, str) else list(command)
        self.check_argv(argv, cwd=cwd)
        run_cwd = (cwd or self.root)
        if not self._within(run_cwd.resolve()):
            raise SandboxViolation(f"cwd escapes sandbox: {run_cwd}")

        env = self.scrubbed_env(extra_env)
        to = timeout or self.policy.command_timeout

        # Try kernel isolation first; if the WRAPPER itself fails to set up
        # (e.g. unprivileged namespaces disabled, or we are already inside a
        # sandbox → EAGAIN), disable it and fall back to in-process execution so
        # a working host still runs the command. The in-process limits (env,
        # rlimits, containment, timeout, output cap) always apply.
        if self.isolation_backend:
            res = await self._exec_capture(self._wrap_isolation(argv), run_cwd, env, to)
            if not self._is_wrapper_error(res):
                return res
            self.isolation_backend = None  # latch off; don't keep paying the cost

        return await self._exec_capture(argv, run_cwd, env, to)

    def _is_wrapper_error(self, res: Dict[str, Any]) -> bool:
        """True when a FAILURE came from the isolation wrapper, not the command."""
        if res.get("status") != "FAILURE":
            return False
        err = (res.get("stderr") or "").lower()
        markers = ("creating new namespace failed", "resource temporarily unavailable",
                   "unshare", "namespaces", "no permission to create")
        return err.startswith(("bwrap:", "nsjail")) or any(m in err for m in markers)

    async def _exec_capture(self, argv: List[str], run_cwd: Path, env: Dict[str, str], to: int) -> Dict[str, Any]:
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(run_cwd),
                env=env,
                start_new_session=True,            # own process group → killable
                preexec_fn=self._preexec(),
            )
        except FileNotFoundError:
            return {"status": "ERROR", "message": f"command not found: {argv[0]!r}"}

        try:
            stdout, stderr, truncated = await asyncio.wait_for(
                self._communicate_capped(proc), timeout=to
            )
        except asyncio.TimeoutError:
            self._kill_group(proc)
            try:  # reap the killed child so its transport is cleaned up
                await asyncio.wait_for(proc.wait(), timeout=5)
            except Exception:
                pass
            return {"status": "TIMEOUT", "message": f"timed out after {to}s", "return_code": None}

        return {
            "status": "SUCCESS" if proc.returncode == 0 else "FAILURE",
            "return_code": proc.returncode,
            "stdout": stdout.decode("utf-8", "ignore"),
            "stderr": stderr.decode("utf-8", "ignore"),
            "truncated": truncated,
            "isolation_backend": self.isolation_backend,
        }

    async def _communicate_capped(self, proc) -> tuple[bytes, bytes, bool]:
        cap = self.policy.max_output_bytes
        out = bytearray()
        err = bytearray()
        truncated = False

        async def _drain(stream, buf):
            nonlocal truncated
            while True:
                chunk = await stream.read(65536)
                if not chunk:
                    break
                if len(buf) < cap:
                    buf.extend(chunk[: cap - len(buf)])
                    if len(buf) >= cap:
                        truncated = True
                else:
                    truncated = True

        await asyncio.gather(_drain(proc.stdout, out), _drain(proc.stderr, err))
        await proc.wait()
        if truncated:
            self._kill_group(proc)
        return bytes(out), bytes(err), truncated

    @staticmethod
    def _kill_group(proc) -> None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                proc.kill()
            except Exception:
                pass

    # ── bounded file I/O ─────────────────────────────────────────────────────
    def read_text(self, path_str: str, *, cwd: Optional[Path] = None, encoding: str = "utf-8") -> str:
        p = self.resolve(path_str, cwd=cwd, must_exist=True)
        if not p.is_file():
            raise SandboxViolation(f"not a file: {path_str!r}")
        size = p.stat().st_size
        if size > self.policy.max_file_bytes:
            raise SandboxViolation(
                f"file too large: {size} bytes > limit {self.policy.max_file_bytes}"
            )
        return p.read_text(encoding=encoding)

    def write_text(self, path_str: str, content: str, *, cwd: Optional[Path] = None, encoding: str = "utf-8") -> Path:
        data = content.encode(encoding)
        if len(data) > self.policy.max_file_bytes:
            raise SandboxViolation(
                f"content too large: {len(data)} bytes > limit {self.policy.max_file_bytes}"
            )
        p = self.resolve(path_str, cwd=cwd)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return p

    # ── archive inspection / extraction (zip-bomb safe) ──────────────────────
    @staticmethod
    def _member_is_traversal(name: str) -> bool:
        """True if a zip member name would write outside its extraction root."""
        if not name or name in (".", ".."):
            return name == ".."
        # normalise separators; reject absolute, drive-rooted, or ``..`` components.
        norm = name.replace("\\", "/")
        if norm.startswith("/") or (len(norm) > 1 and norm[1] == ":"):
            return True
        return any(part == ".." for part in norm.split("/"))

    def inspect_zip(self, zip_path_str: str, *, cwd: Optional[Path] = None) -> Dict[str, Any]:
        """Inspect a ZIP **without extracting**. Never raises on a malformed/hostile
        archive — it reports ``potential_issues`` so a caller can decide. Only a
        sandbox-boundary breach (path escaping the root) raises ``SandboxViolation``.
        """
        p = self.resolve(zip_path_str, cwd=cwd, must_exist=True)
        if not p.is_file():
            raise SandboxViolation(f"not a file: {zip_path_str!r}")
        size_bytes = p.stat().st_size
        issues: List[str] = []
        members: List[Dict[str, Any]] = []
        if not zipfile.is_zipfile(p):
            return {
                "status": "ERROR", "path": str(p), "size_bytes": size_bytes,
                "is_valid": False, "member_count": 0, "members": [],
                "potential_issues": ["not_a_zip"],
            }
        total_uncompressed = 0
        total_compressed = 0
        try:
            with zipfile.ZipFile(p) as zf:
                bad = zf.testzip()
                if bad is not None:
                    issues.append(f"corrupt_member:{bad}")
                for zi in zf.infolist():
                    total_uncompressed += zi.file_size
                    total_compressed += zi.compress_size
                    members.append({
                        "name": zi.filename,
                        "size": zi.file_size,
                        "compressed_size": zi.compress_size,
                        "is_dir": zi.is_dir(),
                    })
                    if self._member_is_traversal(zi.filename):
                        issues.append(f"path_traversal:{zi.filename}")
                    if zi.filename.lower().endswith((".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar")):
                        issues.append(f"nested_archive:{zi.filename}")
        except Exception as exc:  # malformed central directory etc.
            return {
                "status": "ERROR", "path": str(p), "size_bytes": size_bytes,
                "is_valid": False, "member_count": len(members), "members": members,
                "potential_issues": issues + [f"read_error:{type(exc).__name__}"],
            }

        if len(members) > self.policy.max_archive_members:
            issues.append(f"too_many_members:{len(members)}>{self.policy.max_archive_members}")
        if total_uncompressed > self.policy.max_archive_decompressed_bytes:
            issues.append(
                f"decompressed_too_large:{total_uncompressed}>{self.policy.max_archive_decompressed_bytes}"
            )
        ratio = (total_uncompressed / total_compressed) if total_compressed else 0.0
        if ratio > self.policy.max_archive_ratio:
            issues.append(f"suspicious_ratio:{ratio:.0f}>{self.policy.max_archive_ratio}")

        return {
            "status": "SUCCESS",
            "path": str(p),
            "size_bytes": size_bytes,
            "is_valid": True,
            "member_count": len(members),
            "members": members,
            "total_uncompressed_bytes": total_uncompressed,
            "total_compressed_bytes": total_compressed,
            "compression_ratio": round(ratio, 2),
            "potential_issues": issues or ["none"],
        }

    async def extract_zip(
        self, zip_path_str: str, extract_to_str: str, *, cwd: Optional[Path] = None,
        max_decompressed_mb: Optional[int] = None, max_members: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Extract a ZIP with full containment + zip-bomb guards. Extraction is
        per-member (never ``ZipFile.extractall``) so each target is proven to stay
        inside ``extract_to`` before any bytes are written. Decompressed size and
        member count are enforced with a running tally; the first breach aborts.
        """
        return await asyncio.to_thread(
            self._extract_zip_sync, zip_path_str, extract_to_str, cwd, max_decompressed_mb, max_members
        )

    def _extract_zip_sync(
        self, zip_path_str: str, extract_to_str: str, cwd: Optional[Path],
        max_decompressed_mb: Optional[int], max_members: Optional[int],
    ) -> Dict[str, Any]:
        max_bytes = (max_decompressed_mb * 1024 * 1024) if max_decompressed_mb is not None \
            else self.policy.max_archive_decompressed_bytes
        max_count = max_members if max_members is not None else self.policy.max_archive_members

        src = self.resolve(zip_path_str, cwd=cwd, must_exist=True)
        dest_root = self.resolve(extract_to_str, cwd=cwd)
        if not zipfile.is_zipfile(src):
            return {"status": "FAILURE", "messages": ["not_a_zip"], "members_extracted": 0}

        dest_root.mkdir(parents=True, exist_ok=True)
        messages: List[str] = []
        extracted: List[str] = []
        total = 0
        with zipfile.ZipFile(src) as zf:
            infos = zf.infolist()
            if len(infos) > max_count:
                return {"status": "FAILURE", "members_extracted": 0,
                        "messages": [f"too_many_members:{len(infos)}>{max_count}"]}
            for zi in infos:
                if self._member_is_traversal(zi.filename):
                    return {"status": "FAILURE", "members_extracted": len(extracted),
                            "messages": messages + [f"path_traversal_blocked:{zi.filename}"]}
                # prove the resolved target stays inside the extraction root.
                target = self.resolve(zi.filename, cwd=dest_root)
                if not self._within(target) or not target.is_relative_to(dest_root):
                    return {"status": "FAILURE", "members_extracted": len(extracted),
                            "messages": messages + [f"escape_blocked:{zi.filename}"]}
                if zi.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                total += zi.file_size
                if total > max_bytes:
                    return {"status": "FAILURE", "members_extracted": len(extracted),
                            "messages": messages + [f"decompressed_limit_exceeded:{total}>{max_bytes}"]}
                target.parent.mkdir(parents=True, exist_ok=True)
                # stream-copy with a hard cap so a lying header can't bomb us.
                written = 0
                with zf.open(zi) as srcf, open(target, "wb") as outf:
                    while True:
                        chunk = srcf.read(65536)
                        if not chunk:
                            break
                        written += len(chunk)
                        if written > zi.file_size + 1 or (total - zi.file_size + written) > max_bytes:
                            outf.close()
                            target.unlink(missing_ok=True)
                            return {"status": "FAILURE", "members_extracted": len(extracted),
                                    "messages": messages + [f"decompressed_limit_exceeded:{zi.filename}"]}
                        outf.write(chunk)
                extracted.append(zi.filename)

        messages.append(f"extracted {len(extracted)} files to {dest_root}")
        return {
            "status": "SUCCESS",
            "extracted_to": str(dest_root),
            "members_extracted": len(extracted),
            "extracted_names": extracted,
            "total_size_bytes": total,
            "messages": messages,
        }

    def info(self) -> Dict[str, Any]:
        """Inspectable summary — what this boundary is actually enforcing."""
        return {
            "root": str(self.root),
            "isolation_backend": self.isolation_backend or "none (in-process defence-in-depth)",
            "allowed_commands": sorted(self.policy.allowed_commands),
            "allow_inline_code": self.policy.allow_inline_code,
            "follow_symlinks": self.policy.follow_symlinks,
            "limits": {
                "command_timeout_s": self.policy.command_timeout,
                "max_file_bytes": self.policy.max_file_bytes,
                "max_output_bytes": self.policy.max_output_bytes,
                "cpu_seconds": self.policy.cpu_seconds,
                "address_space_bytes": self.policy.address_space_bytes,
                "max_processes": self.policy.max_processes,
                "max_open_files": self.policy.max_open_files,
                "max_archive_members": self.policy.max_archive_members,
                "max_archive_decompressed_bytes": self.policy.max_archive_decompressed_bytes,
                "max_archive_ratio": self.policy.max_archive_ratio,
            },
            "rlimits_available": _resource is not None,
        }


__all__ = [
    "Sandbox",
    "SandboxPolicy",
    "SandboxViolation",
    "default_policy",
    "INTERPRETER_COMMANDS",
    "DENIED_FLAGS",
    "INLINE_CODE_FLAGS",
]
