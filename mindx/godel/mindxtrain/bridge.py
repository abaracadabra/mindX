"""bridge — locate and drive the external mindXtrain CLI.

github.com/professor-codephreak/mindXtrain exposes a `mindxtrain` CLI with
nine subcommands (init, bench, train, eval, quantize, serve, operator, ...).
This module finds an installation, reports capability (CPU dry-run vs MI300X
training), and shells out to it. When mindXtrain is not installed or no
MI300X is present, every call returns a structured dry-run result instead of
raising — so an ascent degrades gracefully to the project's CPU training level.

Discovery order for MINDXTRAIN_HOME:
  1. explicit `home` argument
  2. $MINDXTRAIN_HOME
  3. a `mindxtrain` checkout adjacent to the mindX repo
  4. an installed `mindxtrain` console entry-point on PATH
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from . import MINDXTRAIN_REPO, is_enabled, autonomous_train_enabled

# v1.0.0 verb set (init/bench/train/eval/quantize/serve/coach/dcoach). The
# real set is confirmed by _probe(); this is the fallback expectation.
KNOWN_VERBS = ("init", "bench", "train", "eval", "quantize", "serve", "coach", "dcoach")

_FLAG_CACHE: dict = {}   # per-process cache: (cli, verb) -> set[str] of --flags
_PROBE_CACHE: dict = {}  # cli -> (ts, version, verbs) — TTL'd so the public
_PROBE_TTL_S = 300       # /insight endpoint can't spawn the slow probe per hit


def _parse_version(text: str) -> Optional[str]:
    m = re.search(r"(\d+\.\d+\.\d+)", text or "")
    return m.group(1) if m else None


def _ge_version(v: Optional[str], floor: str = "1.0.0") -> bool:
    if not v:
        return False
    try:
        return tuple(int(x) for x in v.split(".")[:3]) >= tuple(int(x) for x in floor.split("."))
    except Exception:
        return False


@dataclass
class Capability:
    installed: bool
    home: Optional[Path]
    cli: Optional[str]          # "uv run mindxtrain" | "mindxtrain" | None
    has_gpu: bool               # AMD MI300X / ROCm detected
    level: str                  # "gpu" | "cpu" | "absent"
    enabled: bool = False       # operator opt-in (MINDX_ENABLE_MINDXTRAIN)
    version: Optional[str] = None
    verbs: tuple = ()
    cpu_train_active: bool = False   # mindXtrain >= 1.0.0 (CPU training active)
    autonomous_enabled: bool = False # second flag — autonomous training opted in

    @property
    def armed(self) -> bool:
        """Recognized AND opted-in AND actually installed."""
        return self.enabled and self.installed

    def as_dict(self) -> dict:
        return {
            "installed": self.installed,
            "home": str(self.home) if self.home else None,
            "cli": self.cli,
            "has_gpu": self.has_gpu,
            "level": self.level,
            "enabled": self.enabled,
            "armed": self.armed,
            "version": self.version,
            "verbs": list(self.verbs),
            "cpu_train_active": self.cpu_train_active,
            "autonomous_enabled": self.autonomous_enabled,
            "repo": MINDXTRAIN_REPO,
        }


def _detect_rocm() -> bool:
    if shutil.which("rocm-smi") or shutil.which("rocminfo"):
        return True
    return Path("/opt/rocm").exists()


def discover(home: Optional[Path] = None) -> Capability:
    home = Path(home) if home else None
    if home is None:
        env_home = os.environ.get("MINDXTRAIN_HOME")
        if env_home:
            home = Path(env_home)
    if home is None:
        # sibling checkout next to the mindX repo root
        guess = Path(__file__).resolve().parents[3].parent / "mindXtrain"
        if guess.exists():
            home = guess

    cli: Optional[str] = None
    installed = False
    if home and (home / "pyproject.toml").exists():
        installed = True
        cli = "uv run mindxtrain" if shutil.which("uv") else None
    if cli is None and shutil.which("mindxtrain"):
        installed = True
        cli = "mindxtrain"

    has_gpu = _detect_rocm()
    level = "gpu" if (installed and has_gpu) else ("cpu" if installed else "absent")
    cap = Capability(installed=installed, home=home, cli=cli,
                     has_gpu=has_gpu, level=level, enabled=is_enabled(),
                     autonomous_enabled=autonomous_train_enabled())
    # Version/verb probe — only when installed (dormant/absent hosts pay
    # nothing: no subprocess, no cold `uv` resolve). TTL-cached so a public
    # endpoint hitting discover() repeatedly does not re-spawn the slow probe.
    if installed and cli:
        cached = _PROBE_CACHE.get(cli)
        if cached and (time.time() - cached[0]) < _PROBE_TTL_S:
            version, verbs = cached[1], cached[2]
        else:
            version, verbs = _probe(cli, home)
            _PROBE_CACHE[cli] = (time.time(), version, verbs)
        cap.version = version
        cap.verbs = verbs or KNOWN_VERBS
        cap.cpu_train_active = _ge_version(version, "1.0.0")
    return cap


def _probe(cli: str, home: Optional[Path]) -> tuple:
    """Run `mindxtrain --version` + `--help` to learn version + verb set.

    First `uv run` can be cold (env resolve) so the timeout is generous.
    Never raises — returns (None, ()) on any failure."""
    try:
        out = subprocess.run(
            cli.split() + ["--version"],
            cwd=str(home or Path.cwd()),
            capture_output=True, text=True, timeout=180,
        )
        version = _parse_version((out.stdout or "") + (out.stderr or ""))
    except Exception:
        version = None
    verbs: tuple = ()
    try:
        h = subprocess.run(
            cli.split() + ["--help"],
            cwd=str(home or Path.cwd()),
            capture_output=True, text=True, timeout=60,
        )
        found = [v for v in KNOWN_VERBS if re.search(rf"(?m)^\s+{v}\b", h.stdout or "")]
        verbs = tuple(found) if found else ()
    except Exception:
        pass
    return version, verbs


def discover_verb_flags(verb: str, cap: Optional["Capability"] = None) -> set:
    """Return the set of `--flags` a verb accepts, by parsing `<verb> --help`.

    Lets the dcoach/train callers ADAPT to v1.0.0's real flags rather than
    hard-coding guesses. Per-process cached; empty set on any failure (caller
    then falls back to the forged YAML / no extra flags)."""
    cap = cap or discover()
    if not cap.installed or not cap.cli:
        return set()
    key = (cap.cli, verb)
    if key in _FLAG_CACHE:
        return _FLAG_CACHE[key]
    flags: set = set()
    try:
        h = subprocess.run(
            cap.cli.split() + [verb, "--help"],
            cwd=str(cap.home or Path.cwd()),
            capture_output=True, text=True, timeout=60,
        )
        flags = set(re.findall(r"(--[a-zA-Z0-9][a-zA-Z0-9\-]*)", h.stdout or ""))
    except Exception:
        flags = set()
    _FLAG_CACHE[key] = flags
    return flags


def run_cli(
    args: Sequence[str],
    *,
    cap: Optional[Capability] = None,
    cwd: Optional[Path] = None,
    timeout: int = 600,
) -> dict:
    """Invoke `mindxtrain <args>`. Returns {ok, returncode, stdout, stderr}.

    Never raises on a missing install — returns a dry-run stub so callers can
    continue the pendulum swing on CPU-only hosts.
    """
    cap = cap or discover()
    if not cap.enabled:
        return {"ok": False, "dormant": True,
                "reason": "mindXtrain bridge not armed; set MINDX_ENABLE_MINDXTRAIN=1 "
                          "once mindXtrain is validated in isolation",
                "repo": MINDXTRAIN_REPO, "args": list(args)}
    if not cap.installed or cap.cli is None:
        return {"ok": False, "dry_run": True, "reason": "mindXtrain not installed",
                "repo": MINDXTRAIN_REPO, "args": list(args)}
    cmd = cap.cli.split() + list(args)
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd or cap.home or Path.cwd()),
            capture_output=True, text=True, timeout=timeout,
        )
        return {"ok": proc.returncode == 0, "returncode": proc.returncode,
                "stdout": proc.stdout[-8000:], "stderr": proc.stderr[-4000:],
                "cmd": " ".join(cmd)}
    except (subprocess.TimeoutExpired, OSError) as e:
        return {"ok": False, "error": str(e), "cmd": " ".join(cmd)}
