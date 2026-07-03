"""Runtime/device detection — the single source of truth for "can we train for
real, and on what device?".

Mirrors the pattern proven in skybreaker: **the CUDA device covers ROCm** (an
AMD ROCm build of torch reports `torch.cuda.is_available() == True` and exposes
the GPU through the same API). So we never branch on vendor at runtime — we ask
torch for the device and pick a dtype.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass, field
from typing import Any


def _has(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


# Dependency groups per discipline — these list ONLY what the runner actually
# imports, so a task goes "real" the moment its true deps are present (plus
# torch). The text trainers use a hand-rolled dataloader + optimizer, so they
# need nothing beyond transformers (+ peft for LoRA); `datasets`/`accelerate`
# are not required. Embeddings prefer sentence-transformers but fall back to a
# transformers-only SimCSE loop, so transformers alone is enough.
DEP_GROUPS: dict[str, list[str]] = {
    "text_lora": ["transformers", "peft"],
    "text_finetune": ["transformers"],
    "text_embedding": ["transformers"],
    "image_lora": ["diffusers", "transformers", "peft", "safetensors"],
    "image_finetune": ["diffusers", "transformers", "safetensors"],
    "image_embedding": ["diffusers", "transformers", "safetensors"],
}


@dataclass
class Runtime:
    torch_available: bool
    device: str  # "cuda" (covers ROCm) | "mps" | "cpu"
    dtype: str  # "float16" | "float32"
    backend: str  # "cuda" | "rocm" | "mps" | "cpu"
    gpu_name: str | None = None
    torch_version: str | None = None
    extras: dict[str, bool] = field(default_factory=dict)

    @property
    def is_gpu(self) -> bool:
        return self.device in ("cuda", "mps")

    def can_run(self, group_key: str) -> bool:
        if not self.torch_available:
            return False
        for mod in DEP_GROUPS.get(group_key, []):
            if not self.extras.get(mod, False):
                return False
        return True


def detect() -> Runtime:
    """Probe torch + optional deps. Honors SKYBREAKER-style env overrides."""
    extras = {mod: _has(mod) for group in DEP_GROUPS.values() for mod in group}

    if not _has("torch"):
        return Runtime(
            torch_available=False,
            device="cpu",
            dtype="float32",
            backend="cpu",
            extras=extras,
        )

    import torch  # type: ignore

    hip = getattr(torch.version, "hip", None)
    cuda_avail = bool(torch.cuda.is_available())
    forced = os.environ.get("DOJO_DEVICE")  # "cuda" | "cpu" | "mps"

    if forced:
        device = forced
    elif cuda_avail:
        device = "cuda"
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        device = "mps"
    else:
        device = "cpu"

    backend = ("rocm" if hip else "cuda") if device == "cuda" else device
    # fp16 pays off on GPU; CPU stays fp32 (fp16 on CPU is slow/unsupported).
    dtype = "float16" if device in ("cuda",) else "float32"

    gpu_name = None
    if cuda_avail:
        try:
            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            gpu_name = None

    return Runtime(
        torch_available=True,
        device=device,
        dtype=dtype,
        backend=backend,
        gpu_name=gpu_name,
        torch_version=torch.__version__,
        extras=extras,
    )


def grad_scaler(enabled: bool):
    """AMP GradScaler that works across torch versions.

    `torch.cuda.amp.GradScaler` is deprecated in torch >= 2.3 (we pin 2.9.x);
    the supported form is `torch.amp.GradScaler("cuda", ...)`.
    """
    import torch

    try:
        return torch.amp.GradScaler("cuda", enabled=enabled)
    except (AttributeError, TypeError):
        return torch.cuda.amp.GradScaler(enabled=enabled)


def report() -> dict[str, Any]:
    """JSON-friendly snapshot for the engine doctor / UI."""
    rt = detect()
    caps = {key: rt.can_run(key) for key in DEP_GROUPS}
    return {
        "torch_available": rt.torch_available,
        "torch_version": rt.torch_version,
        "device": rt.device,
        "backend": rt.backend,
        "dtype": rt.dtype,
        "gpu_name": rt.gpu_name,
        "extras": rt.extras,
        "capabilities": caps,
        "any_real": any(caps.values()),
    }
