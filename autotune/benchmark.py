"""Autotune orchestrator — runs three probes and emits an :class:`AutotunePlan`.

``run_autotune(dry_run=True)`` (or any box without a GPU) returns a per-vendor
reference plan that consumers can use to exercise their code path. With a GPU
visible, it runs the real attention micro-benchmark plus the documented GEMM /
collective heuristics, all inside a ~60-second budget.

AOT-only discipline: the plan is written once, before the workload starts, and
never re-tuned during the run. JIT autotune (Triton cold-start autotune,
``torch.compile(mode="max-autotune")``, MIOpen find-mode) is out of scope here.

Extracted and generalized from the mindXtrain hackathon project
(Professor-Codephreak/mindXtrain). Apache-2.0.
"""

from __future__ import annotations

from autotune.plan import AttentionBackend, AutotunePlan, GemmHeuristic, ProbeTiming
from autotune.probes.attention import probe_attention
from autotune.probes.collective import probe_collective
from autotune.probes.gemm import probe_gemm
from autotune.profile import HardwareProfile, detect_hardware

# Sane per-vendor defaults used for the dry-run / no-GPU reference plan.
_VENDOR_DEFAULTS: dict[str, tuple[AttentionBackend, GemmHeuristic]] = {
    "amd": ("flash_ck", "hipblaslt_default"),
    "nvidia": ("flash_cuda", "cublaslt_default"),
    "cpu": ("math", "reference"),
}


def _defaults_for(profile: HardwareProfile) -> tuple[AttentionBackend, GemmHeuristic]:
    return _VENDOR_DEFAULTS.get(profile.vendor, _VENDOR_DEFAULTS["cpu"])


def _reference_plan(profile: HardwareProfile) -> AutotunePlan:
    attn, gemm = _defaults_for(profile)
    return AutotunePlan(
        hardware=profile,
        attention_backend=attn,
        gemm_heuristic=gemm,
        collective_config="noop_1gpu",
        fsdp_shard_width=1,
        suggested_lora_rank=16,
        suggested_micro_batch_size=4,
        probe_timings=[ProbeTiming(label="dry-run-reference", backend=attn, median_ms=0.0, iterations=1)],
        notes=[
            f"dry-run reference plan for vendor={profile.vendor} arch={profile.arch}; "
            "replace with real probe output via `python -m autotune bench` on the target box",
        ],
    )


def run_autotune(
    device_index: int = 0,
    *,
    dry_run: bool = False,
    profile: HardwareProfile | None = None,
) -> AutotunePlan:
    """Run the AOT probe sequence and return an :class:`AutotunePlan`.

    Parameters
    ----------
    device_index:
        GPU/HIP device index to probe (ignored on CPU).
    dry_run:
        Skip all probes; return the per-vendor reference plan. Used by CI.
    profile:
        Pre-detected :class:`HardwareProfile`; auto-detected if omitted.
    """
    profile = profile or detect_hardware(device_index)

    if dry_run or not profile.has_gpu:
        return _reference_plan(profile)

    attention_backend, attention_timings = probe_attention(device_index, profile=profile)
    gemm_heuristic = probe_gemm(device_index, profile=profile)
    collective_config = probe_collective(device_index, profile=profile)

    fsdp_shard_width = profile.gpu_count if collective_config != "noop_1gpu" else 1

    return AutotunePlan(
        hardware=profile,
        attention_backend=attention_backend,
        gemm_heuristic=gemm_heuristic,
        collective_config=collective_config,
        fsdp_shard_width=fsdp_shard_width,
        suggested_lora_rank=16,
        suggested_micro_batch_size=4,
        probe_timings=attention_timings,
        notes=[
            "real probe: attention measured; GEMM/collective from documented vendor heuristics",
        ],
    )


__all__ = ["run_autotune"]
