"""Collective-communication topology selection.

Single-GPU and CPU runs are a no-op. A full 8-GPU MI300X node uses xGMI with
``NCCL_MIN_NCHANNELS=112``. An NVLink-connected NVIDIA node uses the default
NCCL path.

The MI300X gotcha is preserved verbatim from the hackathon code: xGMI bandwidth
between *subsets* of 2 or 4 GPUs is asymmetric, so an FSDP shard on those
topologies silently bottlenecks. We hard-fail (``RuntimeError``) rather than
write an ``unsupported`` plan, so the caller refuses to launch the run.

Extracted and generalized from the mindXtrain hackathon project
(Professor-Codephreak/mindXtrain). Apache-2.0.
"""

from __future__ import annotations

from autotune.plan import CollectiveConfig
from autotune.profile import HardwareProfile, detect_hardware


def probe_collective(
    device_index: int = 0,
    gpu_count: int | None = None,
    profile: HardwareProfile | None = None,
) -> CollectiveConfig:
    """Pick the collective config; refuse unsafe 2/4-GPU AMD sharding."""
    profile = profile or detect_hardware(device_index)
    n = gpu_count if gpu_count is not None else profile.gpu_count

    if n <= 1:
        return "noop_1gpu"

    if profile.vendor == "amd":
        if n == 8:
            return "rccl_8gpu_xgmi"
        raise RuntimeError(
            f"FSDP on {n} GPUs is unsafe on MI300X-class nodes due to xGMI bandwidth "
            "asymmetry between GPU subsets. Use 1 or 8 GPUs."
        )

    if profile.vendor == "nvidia":
        return "nccl_nvlink"

    # CPU with n>1 doesn't really happen, but be explicit.
    return "noop_1gpu"


__all__ = ["probe_collective"]
