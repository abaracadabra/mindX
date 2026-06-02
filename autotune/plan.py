"""AutotunePlan — output of the ahead-of-time tuner, consumed by training/runtime.

The plan is the contract between the autotune probes and any consumer (a
training dispatch, an inference launcher, the dream cycle's tuning phase). It is
pure data so a plan generated on one box can be replayed on another, and so a
plan can be hand-written for tests.

Extracted and generalized from the mindXtrain hackathon project
(Professor-Codephreak/mindXtrain). The original was MI300X/ROCm-only; this
version carries a :class:`~autotune.profile.HardwareProfile` and widens every
enum to cover AMD/ROCm, NVIDIA/CUDA, and CPU. Apache-2.0.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from autotune.profile import HardwareProfile

# Attention SDPA path. ``flash_ck`` / ``flash_triton`` are the ROCm choices
# (Composable Kernel vs AOTriton); ``flash_cuda`` is FlashAttention on NVIDIA;
# ``mem_efficient`` is the xFormers-style kernel; ``math`` is the reference
# fallback (and the only honest answer on CPU).
AttentionBackend = Literal["flash_ck", "flash_triton", "flash_cuda", "mem_efficient", "math"]

# GEMM heuristic. We do not enumerate vendor heuristics ourselves (that blows
# the 60-second budget); we pick the documented default for the detected vendor.
GemmHeuristic = Literal[
    "hipblaslt_default",
    "hipblaslt_tuned",
    "rocblas_fallback",
    "cublaslt_default",
    "cublaslt_tuned",
    "reference",
]

# Collective topology. ``noop_1gpu`` for single-GPU/CPU; ``rccl_8gpu_xgmi`` for
# a full MI300X node; ``nccl_nvlink`` for an NVLink-connected NVIDIA node;
# ``unsupported`` is never written — the probe raises instead.
CollectiveConfig = Literal["noop_1gpu", "rccl_8gpu_xgmi", "nccl_nvlink", "unsupported"]


class ProbeTiming(BaseModel):
    """Single probe measurement (one shape, one backend)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    backend: str
    median_ms: float = Field(ge=0.0)
    iterations: int = Field(ge=1)


class AutotunePlan(BaseModel):
    """Static AOT plan written by ``python -m autotune bench`` and read by consumers."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["2"] = "2"
    hardware: HardwareProfile = Field(default_factory=HardwareProfile)

    attention_backend: AttentionBackend = "math"
    gemm_heuristic: GemmHeuristic = "reference"
    collective_config: CollectiveConfig = "noop_1gpu"

    fsdp_shard_width: int = Field(default=1, ge=1)
    suggested_lora_rank: int = Field(default=16, ge=1, le=512)
    suggested_micro_batch_size: int = Field(default=4, ge=1)

    probe_timings: list[ProbeTiming] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    # --- convenience ---------------------------------------------------------
    @property
    def dry_run(self) -> bool:
        """True when this plan was produced without touching a GPU."""
        return any("dry-run" in n or "reference" in n for n in self.notes)


__all__ = [
    "AttentionBackend",
    "GemmHeuristic",
    "CollectiveConfig",
    "ProbeTiming",
    "AutotunePlan",
]
