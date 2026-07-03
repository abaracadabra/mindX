# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON — all rights reserved.
#
# llmfit_tool.py — node capability oracle for mindX.
#
# Wraps AlexsJones/llmfit (MIT) as a first-class BaseTool, mirroring the shape
# of tools/cloud/ollama_cloud_tool.py. llmfit answers the *prospective* question
# "what can this node actually run?" as JSON — the input InferenceDiscovery and
# the ResourceGovernor lack today. The resulting fit profile is published as a
# node capability descriptor (A2A agent card / AgenticPlace registry).
#
# Zero new pip dependencies: stdlib subprocess + urllib only. The llmfit binary
# is a separately-installed, separately-licensed (MIT) artifact — invoked, never
# vendored — so the Apache-2.0 boundary of the protocol is preserved.
#
# Two transports:
#   * one-shot CLI   — `llmfit recommend --json`, `llmfit --json system`, `plan`
#   * REST sidecar   — GET http://127.0.0.1:8787/api/v1/...  (llmfit serve)
# The sidecar is preferred when reachable; CLI is the always-available fallback.

from __future__ import annotations

import asyncio
import json
import shutil
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# NOTE: align this import with the canonical base used by
# tools/cloud/ollama_cloud_tool.py. The thin wrapper below keeps all real logic
# in module-level functions so the tool is usable even if BaseTool differs.
try:
    from agents.core.bdi_agent import BaseTool  # type: ignore
except Exception:  # pragma: no cover - allows standalone use / unit tests
    class BaseTool:  # minimal shim
        id: str = ""
        description: str = ""

        async def execute(self, **kwargs: Any) -> dict[str, Any]:
            raise NotImplementedError


LLMFIT_BIN = "llmfit"
SIDECAR_BASE = "http://127.0.0.1:8787"
SIDECAR_TIMEOUT_S = 4.0
CLI_TIMEOUT_S = 60.0

USE_CASES = {"general", "coding", "reasoning", "chat", "multimodal", "embedding"}
FIT_LEVELS = {"perfect", "good", "marginal", "too_tight"}
RUNTIMES = {"any", "mlx", "llamacpp", "vllm"}


def binary_available() -> bool:
    """True when the llmfit MIT binary is on PATH."""
    return shutil.which(LLMFIT_BIN) is not None


async def _run_cli(args: list[str]) -> dict[str, Any]:
    """Invoke `llmfit <args>` and parse stdout as JSON."""
    if not binary_available():
        return {"ok": False, "error": "llmfit_not_installed", "hint": "uv tool install -U llmfit"}
    proc = await asyncio.create_subprocess_exec(
        LLMFIT_BIN, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=CLI_TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": "llmfit_timeout", "args": args}
    if proc.returncode != 0:
        return {"ok": False, "error": "llmfit_nonzero_exit",
                "code": proc.returncode, "stderr": err.decode(errors="replace")[:2000]}
    try:
        return {"ok": True, "data": json.loads(out.decode())}
    except json.JSONDecodeError:
        return {"ok": False, "error": "llmfit_bad_json", "raw": out.decode(errors="replace")[:2000]}


def _sidecar_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """GET against a running `llmfit serve` sidecar. None => unreachable, fall back to CLI."""
    url = f"{SIDECAR_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    try:
        with urllib.request.urlopen(url, timeout=SIDECAR_TIMEOUT_S) as resp:  # noqa: S310 (loopback only)
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return None


# ── operations ────────────────────────────────────────────────────────────────

async def op_system() -> dict[str, Any]:
    """Detected node hardware (CPU, RAM, GPU, VRAM, backend)."""
    live = _sidecar_get("/api/v1/system")
    if live is not None:
        return {"ok": True, "source": "sidecar", "data": live}
    return await _run_cli(["--json", "system"])


async def op_recommend(use_case: str = "general", limit: int = 5,
                       force_runtime: str | None = None) -> dict[str, Any]:
    """Top-N models that fit this node, ranked by composite score."""
    if use_case not in USE_CASES:
        return {"ok": False, "error": "bad_use_case", "allowed": sorted(USE_CASES)}
    live = _sidecar_get("/api/v1/models/top",
                        {"limit": limit, "min_fit": "good", "use_case": use_case})
    if live is not None:
        return {"ok": True, "source": "sidecar", "data": live}
    args = ["recommend", "--json", "--use-case", use_case, "--limit", str(limit)]
    if force_runtime in RUNTIMES and force_runtime != "any":
        args += ["--force-runtime", force_runtime]
    return await _run_cli(args)


async def op_plan(model: str, context: int = 8192,
                 quant: str | None = None, target_tps: int | None = None) -> dict[str, Any]:
    """Inverse fit: what hardware would `model` need at this config."""
    args = ["plan", model, "--context", str(context), "--json"]
    if quant:
        args += ["--quant", quant]
    if target_tps:
        args += ["--target-tps", str(target_tps)]
    return await _run_cli(args)


async def fit_profile(use_case: str = "general", limit: int = 8) -> dict[str, Any]:
    """
    Compact, publishable node-capability descriptor for the protocol layer.
    Attaches to the A2A agent card and the AgenticPlace node registry so the
    network can route a model-class request to a node that can actually serve it.
    """
    sys_res = await op_system()
    rec_res = await op_recommend(use_case=use_case, limit=limit)
    if not sys_res.get("ok"):
        return sys_res
    sysd = sys_res["data"]
    models = (rec_res.get("data") or {}).get("models", []) if rec_res.get("ok") else []
    runnable = [
        {"name": m.get("name"), "fit": m.get("fit"),
         "quant": m.get("quant"), "tok_s": m.get("tok_s"), "use_case": m.get("use_case")}
        for m in models if m.get("fit") in {"perfect", "good", "marginal"}
    ]
    return {
        "ok": True,
        "schema": "mindx.node.fit_profile.v1",
        "hardware": {
            "backend": sysd.get("backend"),
            "vram_gb": sysd.get("vram_gb") or sysd.get("vram"),
            "ram_gb": sysd.get("ram_gb") or sysd.get("ram"),
            "cpu_cores": sysd.get("cpu_cores") or sysd.get("cores"),
            "gpu": sysd.get("gpu_name") or sysd.get("gpu"),
        },
        "runnable": runnable,
        "source": rec_res.get("source", "cli"),
    }


class LLMFitTool(BaseTool):
    """Hardware-aware model-fit oracle. Operations: system, recommend, plan, fit_profile."""

    id = "llmfit"
    description = (
        "Right-sizes local models to this node's CPU/RAM/GPU via llmfit (MIT). "
        "Produces a publishable node fit_profile consumed by InferenceDiscovery "
        "and the A2A/AgenticPlace node registry."
    )

    async def execute(self, operation: str = "fit_profile", **kwargs: Any) -> dict[str, Any]:
        dispatch = {
            "system": op_system,
            "recommend": op_recommend,
            "plan": op_plan,
            "fit_profile": fit_profile,
        }
        fn = dispatch.get(operation)
        if fn is None:
            return {"ok": False, "error": "unknown_operation", "allowed": sorted(dispatch)}
        return await fn(**kwargs)
