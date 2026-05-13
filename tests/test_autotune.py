"""autotune — agnostic ahead-of-time tuner: plan round-trip, dry-run, probes, dispatch."""

from __future__ import annotations

import json

import pytest

from autotune import AutotunePlan, detect_hardware, run_autotune
from autotune.dispatch import apply_plan, plan_to_env
from autotune.plan import ProbeTiming
from autotune.probes.collective import probe_collective
from autotune.profile import HardwareProfile


# --- detection -------------------------------------------------------------
def test_detect_hardware_cpu_box_without_torch():
    """On a torch-less dev box, detection returns a clean CPU profile, never raises."""
    profile = detect_hardware()
    assert isinstance(profile, HardwareProfile)
    assert profile.vendor == "cpu"
    assert profile.torch_runtime in ("absent", "cpu")
    assert profile.has_gpu is False


# --- dry-run reference plan ------------------------------------------------
def test_dry_run_returns_reference_plan():
    plan = run_autotune(dry_run=True)
    assert isinstance(plan, AutotunePlan)
    assert plan.schema_version == "2"
    assert plan.dry_run is True
    assert plan.collective_config == "noop_1gpu"
    assert plan.fsdp_shard_width == 1
    # On the CPU CI box the vendor default is the math kernel.
    assert plan.attention_backend in ("math", "flash_ck", "flash_cuda")


def test_no_gpu_box_falls_back_to_reference_plan_even_without_dry_run():
    plan = run_autotune(dry_run=False)
    assert plan.dry_run is True  # no GPU ⇒ reference plan, marked as such in notes


def test_reference_plan_for_explicit_vendor_profiles():
    amd = run_autotune(dry_run=True, profile=HardwareProfile(vendor="amd", arch="gfx942", gpu_count=8, torch_runtime="rocm"))
    assert amd.attention_backend == "flash_ck"
    assert amd.gemm_heuristic == "hipblaslt_default"
    nv = run_autotune(dry_run=True, profile=HardwareProfile(vendor="nvidia", arch="sm_90", gpu_count=8, torch_runtime="cuda"))
    assert nv.attention_backend == "flash_cuda"
    assert nv.gemm_heuristic == "cublaslt_default"


# --- JSON round-trip -------------------------------------------------------
def test_plan_json_round_trip():
    original = run_autotune(dry_run=True)
    restored = AutotunePlan.model_validate(json.loads(original.model_dump_json()))
    assert restored == original


def test_probe_timing_is_frozen():
    t = ProbeTiming(label="x", backend="math", median_ms=1.0, iterations=3)
    with pytest.raises(Exception):
        t.median_ms = 2.0  # type: ignore[misc]


# --- collective probe ------------------------------------------------------
def test_collective_single_gpu_is_noop():
    cpu = HardwareProfile(vendor="cpu")
    assert probe_collective(profile=cpu, gpu_count=1) == "noop_1gpu"


def test_collective_amd_8gpu_xgmi():
    amd = HardwareProfile(vendor="amd", arch="gfx942", gpu_count=8, torch_runtime="rocm")
    assert probe_collective(profile=amd, gpu_count=8) == "rccl_8gpu_xgmi"


def test_collective_amd_rejects_2_and_4_gpu():
    amd = HardwareProfile(vendor="amd", arch="gfx942", gpu_count=4, torch_runtime="rocm")
    with pytest.raises(RuntimeError, match="xGMI"):
        probe_collective(profile=amd, gpu_count=2)
    with pytest.raises(RuntimeError):
        probe_collective(profile=amd, gpu_count=4)


def test_collective_nvidia_multigpu_nvlink():
    nv = HardwareProfile(vendor="nvidia", arch="sm_90", gpu_count=4, torch_runtime="cuda")
    assert probe_collective(profile=nv, gpu_count=4) == "nccl_nvlink"


# --- dispatch helpers ------------------------------------------------------
def test_plan_to_env_ck_backend_sets_nvte_toggles():
    plan = run_autotune(dry_run=True, profile=HardwareProfile(vendor="amd", arch="gfx942", gpu_count=1, torch_runtime="rocm"))
    # reference plan picks flash_ck for amd
    env = plan_to_env(plan)
    assert env["NVTE_CK_USES_BWD_V3"] == "1"
    assert env["PYTORCH_ROCM_ARCH"] == "gfx942"


def test_plan_to_env_8gpu_sets_nccl_channels():
    plan = AutotunePlan(
        hardware=HardwareProfile(vendor="amd", arch="gfx942", gpu_count=8, torch_runtime="rocm"),
        attention_backend="flash_ck",
        gemm_heuristic="hipblaslt_default",
        collective_config="rccl_8gpu_xgmi",
        fsdp_shard_width=8,
    )
    env = plan_to_env(plan)
    assert env["NCCL_MIN_NCHANNELS"] == "112"


def test_apply_plan_overlays_attention_and_caps_micro_batch():
    plan = AutotunePlan(attention_backend="flash_cuda", suggested_lora_rank=32, suggested_micro_batch_size=2)
    cfg = {"flash_attention": False, "lora_r": 8, "micro_batch_size": 16, "env": {"FOO": "bar"}}
    out = apply_plan(cfg, plan)
    assert out["flash_attention"] is True
    assert out["flash_attn_backend"] == "flash2"
    assert out["lora_r"] == 32  # raised toward the suggestion
    assert out["micro_batch_size"] == 2  # capped at the suggestion
    assert out["fsdp_shard_width"] == 1
    assert out["env"]["FOO"] == "bar"  # caller env preserved
