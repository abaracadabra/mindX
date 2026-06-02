"""Hardware profile detection for the agnostic autotune layer.

This module answers one question: *what am I running on?* — and it answers it
without requiring torch, a GPU, or any vendor SDK to be installed. On a CPU dev
box with no torch, it returns a clean ``vendor="cpu", torch_runtime="absent"``
profile, which is the canonical degraded path that keeps ``--dry-run`` parity.

Extracted and generalized from the mindXtrain hackathon project
(Professor-Codephreak/mindXtrain). Apache-2.0.
"""

from __future__ import annotations

import importlib.util
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Vendor = Literal["amd", "nvidia", "cpu"]
TorchRuntime = Literal["rocm", "cuda", "cpu", "absent"]


class HardwareProfile(BaseModel):
    """Static description of the box the tuner is running on.

    Pure data — content-addressable, JSON round-trippable, hand-writable for
    tests. ``arch`` is the vendor-specific architecture string (``gfx942`` for
    MI300X, ``sm_90`` for H100, ``x86_64`` for a CPU-only box).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    vendor: Vendor = "cpu"
    arch: str = "x86_64"
    gpu_count: int = Field(default=0, ge=0)
    total_mem_gb: Optional[float] = Field(default=None, ge=0.0)
    torch_runtime: TorchRuntime = "absent"
    device_name: Optional[str] = None

    @property
    def has_gpu(self) -> bool:
        return self.gpu_count > 0 and self.torch_runtime in ("rocm", "cuda")


def _torch_available() -> bool:
    return importlib.util.find_spec("torch") is not None


def detect_hardware(device_index: int = 0) -> HardwareProfile:
    """Probe the local machine and return a :class:`HardwareProfile`.

    Never raises. If torch is missing, or no CUDA/ROCm device is visible, the
    returned profile describes a CPU-only box.
    """
    if not _torch_available():
        return HardwareProfile()

    try:  # pragma: no cover - exercised only where torch is installed
        import torch

        if not torch.cuda.is_available():
            return HardwareProfile(torch_runtime="cpu")

        gpu_count = torch.cuda.device_count()
        # torch reports ROCm builds via ``torch.version.hip``.
        is_rocm = getattr(torch.version, "hip", None) is not None
        vendor: Vendor = "amd" if is_rocm else "nvidia"
        runtime: TorchRuntime = "rocm" if is_rocm else "cuda"

        idx = device_index if 0 <= device_index < gpu_count else 0
        props = torch.cuda.get_device_properties(idx)
        device_name = getattr(props, "name", None)
        total_mem_gb = round(getattr(props, "total_memory", 0) / (1024**3), 1) or None

        if is_rocm:
            arch = getattr(props, "gcnArchName", None) or "gfx_unknown"
        else:
            major = getattr(props, "major", 0)
            minor = getattr(props, "minor", 0)
            arch = f"sm_{major}{minor}"

        return HardwareProfile(
            vendor=vendor,
            arch=str(arch),
            gpu_count=gpu_count,
            total_mem_gb=total_mem_gb,
            torch_runtime=runtime,
            device_name=device_name,
        )
    except Exception:  # pragma: no cover - defensive: any torch hiccup ⇒ CPU profile
        return HardwareProfile(torch_runtime="cpu")


__all__ = ["HardwareProfile", "Vendor", "TorchRuntime", "detect_hardware"]
