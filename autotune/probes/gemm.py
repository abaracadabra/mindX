"""GEMM heuristic selection — a documented default, not an enumeration.

We deliberately do not run a vendor heuristic enumeration (hipBLASLt or
cuBLASLt) here: a real enumeration is ~1.5 minutes and would blow the
60-second probe budget. Instead we pick the documented default for the detected
vendor, which AMD and NVIDIA both publish as being within a few percent of
hand-tuned for the BF16/FP16 GEMM shapes a LoRA/SFT job hits (rank 16–64,
hidden 2048–8192).

  * AMD/ROCm   : ``hipblaslt_default`` (AMD ROCm 7.x release notes, hipBLASLt
                 default heuristic for gfx942).
  * NVIDIA/CUDA: ``cublaslt_default`` (cuBLASLt default algo selection).
  * CPU        : ``reference``.

Revisit post-hoc only if an MMLU/eval pass shows GEMM-bound throughput
regression on a specific recipe.

Extracted and generalized from the mindXtrain hackathon project
(Professor-Codephreak/mindXtrain). Apache-2.0.
"""

from __future__ import annotations

from autotune.plan import GemmHeuristic
from autotune.profile import HardwareProfile, detect_hardware


def probe_gemm(
    device_index: int = 0,
    profile: HardwareProfile | None = None,
) -> GemmHeuristic:
    """Return the GEMM heuristic for the autotune plan."""
    profile = profile or detect_hardware(device_index)
    if profile.vendor == "amd":
        return "hipblaslt_default"
    if profile.vendor == "nvidia":
        return "cublaslt_default"
    return "reference"


__all__ = ["probe_gemm"]
