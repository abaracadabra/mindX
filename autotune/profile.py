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

Vendor = Literal["amd", "nvidia", "apple", "intel", "cpu"]
TorchRuntime = Literal["rocm", "cuda", "mps", "xpu", "cpu", "absent"]


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
        """A GPU this autotune layer can race vendor SDPA kernels on.

        Deliberately cuda/rocm only: the probes (attention/gemm/collective) are
        AMD/NVIDIA-specific, so MPS/XPU correctly route to the reference plan.
        Use :attr:`is_accelerator` for the honest "is there any accelerator?".
        """
        return self.gpu_count > 0 and self.torch_runtime in ("rocm", "cuda")

    @property
    def is_accelerator(self) -> bool:
        """True on any non-CPU torch accelerator (cuda/rocm/mps/xpu)."""
        return self.torch_runtime in ("rocm", "cuda", "mps", "xpu")


def _torch_available() -> bool:
    return importlib.util.find_spec("torch") is not None


def detect_hardware(device_index: int = 0) -> HardwareProfile:
    """Probe the local machine and return a :class:`HardwareProfile`.

    Never raises. If torch is missing, or no accelerator (CUDA/ROCm/MPS/XPU) is
    visible, the returned profile describes a CPU-only box. Detection follows the
    PyTorch 2.x device-agnostic order: CUDA/ROCm (the tunable path) first, then
    Intel XPU, then Apple MPS.
    """
    if not _torch_available():
        return HardwareProfile()

    try:  # pragma: no cover - exercised only where torch is installed
        import torch

        # 1) CUDA / ROCm — the only path with vendor-specific tuned kernels.
        if torch.cuda.is_available():
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

        # 2) Intel XPU (oneAPI) — exposed as ``torch.xpu`` in 2.x.
        xpu = getattr(torch, "xpu", None)
        if xpu is not None and xpu.is_available():
            gpu_count = xpu.device_count()
            idx = device_index if 0 <= device_index < gpu_count else 0
            device_name = None
            total_mem_gb = None
            try:
                props = xpu.get_device_properties(idx)
                device_name = getattr(props, "name", None)
                total_mem_gb = round(getattr(props, "total_memory", 0) / (1024**3), 1) or None
            except Exception:
                pass
            return HardwareProfile(
                vendor="intel",
                arch="xpu",
                gpu_count=gpu_count,
                total_mem_gb=total_mem_gb,
                torch_runtime="xpu",
                device_name=device_name,
            )

        # 3) Apple Silicon (Metal Performance Shaders) — unified memory, no
        # per-device count API; report a single logical accelerator.
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            return HardwareProfile(
                vendor="apple",
                arch="mps",
                gpu_count=1,
                torch_runtime="mps",
                device_name="Apple MPS",
            )

        return HardwareProfile(torch_runtime="cpu")
    except Exception:  # pragma: no cover - defensive: any torch hiccup ⇒ CPU profile
        return HardwareProfile(torch_runtime="cpu")


__all__ = ["HardwareProfile", "Vendor", "TorchRuntime", "detect_hardware"]
