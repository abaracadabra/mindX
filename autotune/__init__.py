"""autotune — an agnostic ahead-of-time tuner.

A small, composable peer module (see the mindX Agnostic Modules Principle). It
runs a short pre-flight micro-benchmark and emits a reproducible
:class:`AutotunePlan` describing the attention backend, GEMM heuristic, and
collective topology to use — for AMD/ROCm, NVIDIA/CUDA, or CPU. mindX is one
consumer; the module has no mindX dependency.

Public API::

    from autotune import run_autotune, AutotunePlan, HardwareProfile, detect_hardware
    from autotune.dispatch import plan_to_env, apply_plan

Extracted and generalized from the mindXtrain hackathon project
(Professor-Codephreak/mindXtrain). Apache-2.0 — see NOTICE.
"""

from autotune.benchmark import run_autotune
from autotune.plan import AutotunePlan, ProbeTiming
from autotune.profile import HardwareProfile, detect_hardware

__all__ = ["run_autotune", "AutotunePlan", "ProbeTiming", "HardwareProfile", "detect_hardware"]
