"""Consumer-side helpers — turn an :class:`AutotunePlan` into env vars / config.

Any training or inference launcher that wants to honor a plan calls these. They
are backend-agnostic: no Axolotl, no torch import, just dict manipulation.

  * :func:`plan_to_env` — environment variables the plan implies (NCCL channel
    count, the NVTE/PRIMUS CK toggles, the vendor arch hint, the Triton flash
    toggle).
  * :func:`apply_plan` — overlay the plan onto a launcher's config dict
    (attention backend, LoRA rank, micro-batch ceiling).

Extracted and generalized from the mindXtrain hackathon project
(Professor-Codephreak/mindXtrain), where these lived in ``train/sft.py`` and
``train/axolotl_compile.py``. Apache-2.0.
"""

from __future__ import annotations

from typing import Any

from autotune.plan import AutotunePlan

# Vendor-specific base env that's safe to set whenever we know the vendor.
_AMD_BASE_ENV = {
    "HSA_NO_SCRATCH_RECLAIM": "1",
    "HIP_FORCE_DEV_KERNARG": "1",
    "GPU_MAX_HW_QUEUES": "1",
}


def plan_to_env(plan: AutotunePlan) -> dict[str, str]:
    """Return the environment variables implied by ``plan``.

    The caller merges these into ``os.environ`` (or a subprocess env) before
    launching the workload.
    """
    env: dict[str, str] = {}
    vendor = plan.hardware.vendor

    if vendor == "amd":
        env.update(_AMD_BASE_ENV)
        # gfx arch hint for ROCm builds (e.g. PYTORCH_ROCM_ARCH=gfx942).
        if plan.hardware.arch and plan.hardware.arch.startswith("gfx"):
            env["PYTORCH_ROCM_ARCH"] = plan.hardware.arch

    if plan.collective_config == "rccl_8gpu_xgmi":
        env["NCCL_MIN_NCHANNELS"] = "112"
        env["GPU_MAX_HW_QUEUES"] = "1"

    if plan.attention_backend == "flash_ck":
        env["NVTE_CK_USES_BWD_V3"] = "1"
        env["NVTE_CK_IS_V3_ATOMIC_FP32"] = "1"
        env["PRIMUS_TURBO_ATTN_V3_ATOMIC_FP32"] = "1"
    elif plan.attention_backend == "flash_triton":
        env["VLLM_USE_TRITON_FLASH_ATTN"] = "1"

    return env


# Logical backend name → (flash_attention?, flash_attn_backend) hint for
# launchers that expose those two knobs (Axolotl, vLLM, …).
_FLASH_BACKEND_HINT = {
    "flash_ck": (True, "ck"),
    "flash_triton": (True, "triton"),
    "flash_cuda": (True, "flash2"),
    "mem_efficient": (True, "mem_efficient"),
    "math": (False, None),
}


def apply_plan(cfg: dict[str, Any], plan: AutotunePlan) -> dict[str, Any]:
    """Return a copy of ``cfg`` with the plan's decisions overlaid.

    Recognized keys (left untouched if absent):
      * ``flash_attention`` / ``flash_attn_backend``
      * ``lora_r`` (only raised toward ``suggested_lora_rank`` if currently lower)
      * ``micro_batch_size`` (capped at ``suggested_micro_batch_size``)
      * ``fsdp_shard_width``
    """
    out = dict(cfg)

    flash, backend = _FLASH_BACKEND_HINT.get(plan.attention_backend, (False, None))
    out["flash_attention"] = flash
    if backend is not None:
        out["flash_attn_backend"] = backend

    if "lora_r" in out and isinstance(out["lora_r"], int):
        out["lora_r"] = max(out["lora_r"], plan.suggested_lora_rank)
    if "micro_batch_size" in out and isinstance(out["micro_batch_size"], int):
        out["micro_batch_size"] = min(out["micro_batch_size"], plan.suggested_micro_batch_size)

    out["fsdp_shard_width"] = plan.fsdp_shard_width

    extra_env = plan_to_env(plan)
    if extra_env:
        merged = dict(out.get("env", {}))
        merged.update(extra_env)
        out["env"] = merged

    return out


__all__ = ["plan_to_env", "apply_plan"]
