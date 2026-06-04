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
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from . import MINDXTRAIN_REPO, is_enabled


@dataclass
class Capability:
    installed: bool
    home: Optional[Path]
    cli: Optional[str]          # "uv run mindxtrain" | "mindxtrain" | None
    has_gpu: bool               # AMD MI300X / ROCm detected
    level: str                  # "gpu" | "cpu" | "absent"
    enabled: bool = False       # operator opt-in (MINDX_ENABLE_MINDXTRAIN)

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
    return Capability(installed=installed, home=home, cli=cli,
                      has_gpu=has_gpu, level=level, enabled=is_enabled())


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
