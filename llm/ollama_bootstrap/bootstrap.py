"""
Ollama bootstrap when no inference connection is found.

mindX uses this to install and configure a working Ollama on Linux so
self-improvement can continue from core. See llm/ollama_bootstrap/README.md
and llm/RESILIENCE.md.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

try:
    import aiohttp
except ImportError:
    aiohttp = None

NO_INFERENCE_CONNECTION = "no_inference_connection"

# Default base URL for local Ollama (used after bootstrap)
OLLAMA_DEFAULT_HOST = "http://127.0.0.1:11434"


def _script_dir() -> Path:
    return Path(__file__).resolve().parent


def _aion_sh_path() -> Path:
    return _script_dir() / "aion.sh"


async def _check_ollama_reachable(base_url: str = OLLAMA_DEFAULT_HOST, timeout: float = 5.0) -> bool:
    """Return True if Ollama API at base_url is reachable."""
    if not aiohttp:
        return False
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                return resp.status == 200
    except Exception:
        return False


def run_ollama_bootstrap_linux(
    pull_model: str = "llama3.2",
    serve: bool = True,
    script_path: Optional[Path] = None,
) -> Tuple[bool, str]:
    """
    Run the Linux bootstrap script (aion.sh) to install Ollama and pull a model.
    Returns (success, message).
    """
    script = script_path or _aion_sh_path()
    if not script.exists():
        return False, f"Bootstrap script not found: {script}"
    if not os.access(script, os.X_OK):
        try:
            script.chmod(script.stat().st_mode | 0o111)
        except OSError:
            return False, f"Script not executable: {script}"
    cmd = [str(script)]
    if pull_model:
        cmd.extend(["--pull-model", pull_model])
    if serve:
        cmd.append("--serve")
    try:
        result = subprocess.run(
            cmd,
            cwd=_script_dir(),
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            return True, result.stdout or "Ollama bootstrap completed."
        return False, result.stderr or result.stdout or f"Exit code {result.returncode}"
    except subprocess.TimeoutExpired:
        return False, "Bootstrap script timed out."
    except Exception as e:
        return False, str(e)


async def ensure_ollama_available(
    base_url: Optional[str] = None,
    fallback_url: Optional[str] = None,
    try_bootstrap_linux: bool = True,
    bootstrap_pull_model: str = "llama3.2",
) -> Tuple[bool, str]:
    """
    Check if Ollama is reachable at base_url or fallback_url.
    If not and try_bootstrap_linux is True on Linux, run aion.sh and recheck.
    Returns (available, message). When available is True, message indicates which URL works.
    """
    urls = [u for u in (base_url, fallback_url, OLLAMA_DEFAULT_HOST) if u]
    for url in urls:
        if await _check_ollama_reachable(url):
            return True, f"Ollama reachable at {url}"
    if try_bootstrap_linux and sys.platform.startswith("linux"):
        loop = asyncio.get_event_loop()
        ok, msg = await loop.run_in_executor(
            None,
            lambda: run_ollama_bootstrap_linux(pull_model=bootstrap_pull_model, serve=True),
        )
        if ok:
            if await _check_ollama_reachable(OLLAMA_DEFAULT_HOST):
                return True, f"Ollama bootstrap succeeded; reachable at {OLLAMA_DEFAULT_HOST}"
        return False, f"Bootstrap failed: {msg}"
    return False, NO_INFERENCE_CONNECTION
