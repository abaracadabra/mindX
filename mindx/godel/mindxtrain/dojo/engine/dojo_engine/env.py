"""Environment detection — powers the Settings page's engine doctor."""

from __future__ import annotations

import importlib.util
import platform
import sys
from typing import Any


def _has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


def _torch_info() -> dict[str, Any]:
    if not _has("torch"):
        return {"installed": False, "cuda": False, "device": "cpu", "version": None}
    try:
        import torch  # type: ignore

        # ROCm builds of torch report availability through the same cuda API but
        # expose a HIP version string.
        hip = getattr(torch.version, "hip", None)
        cuda_avail = bool(torch.cuda.is_available())
        rocm = bool(hip) and cuda_avail
        cuda = cuda_avail and not rocm
        if rocm:
            device = "rocm"
        elif cuda:
            device = "cuda"
        elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
        return {
            "installed": True,
            "version": torch.__version__,
            "cuda": cuda,
            "rocm": rocm,
            "hip": hip,
            "device": device,
            "gpu": torch.cuda.get_device_name(0) if cuda_avail else None,
        }
    except Exception as exc:  # pragma: no cover - defensive
        return {"installed": True, "error": str(exc), "cuda": False, "device": "cpu"}


def doctor() -> dict[str, Any]:
    """Report the engine's runtime capabilities as a plain dict."""
    extras = {
        "torch": _has("torch"),
        "transformers": _has("transformers"),
        "peft": _has("peft"),
        "diffusers": _has("diffusers"),
        "datasets": _has("datasets"),
        "sentence_transformers": _has("sentence_transformers"),
        "accelerate": _has("accelerate"),
    }
    real_training_ready = extras["torch"] and extras["transformers"] and extras["peft"]

    from . import runtime

    rt = runtime.report()
    return {
        "engine_version": "0.1.0",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "torch": _torch_info(),
        "extras": extras,
        # Per-discipline real-training capability (text_lora, image_lora, …).
        "runtime": rt,
        # When False, task runners fall back to the simulated loop.
        "real_training_ready": real_training_ready,
        "mode": "real" if rt["any_real"] else "simulation",
    }
