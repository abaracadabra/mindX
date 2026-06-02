# autotune — the agnostic ahead-of-time tuner

`autotune` is a small, composable peer module. It runs a short pre-flight
micro-benchmark and emits a reproducible **`AutotunePlan`** describing which
attention backend, GEMM heuristic, and collective topology to use — for
AMD/ROCm, NVIDIA/CUDA, or CPU. It has **no mindX dependency**; mindX is one
consumer, and `tools/autotune_tool.py` is the thin wrapper that lets agents
invoke it.

It was extracted and generalized from the [mindXtrain](https://github.com/Professor-Codephreak/mindXtrain)
project — see [`NOTICE`](NOTICE). The original was MI300X / `gfx942`-only; this
version carries a `HardwareProfile` and degrades cleanly to a CPU reference plan
on a box with no GPU (and no `torch` installed).

## The AOT-only discipline

The plan is written **once**, before the workload starts, and never re-tuned
during the run. JIT autotune — Triton cold-start autotune, `torch.compile(mode="max-autotune")`,
MIOpen find-mode — is out of scope, for three reasons:

1. **Reproducibility** — a JIT-tuned run produces different kernels on different
   invocations of the same workload, breaking deterministic benchmarks.
2. **First-batch latency** — cold-start autotune can stall the first step for
   seconds, invisible in the loss curve and very visible in `tok/s`.
3. **Statically declared paths** — production paths should be declared at
   deployment, not decided in-band at runtime.

## The probe taxonomy

`run_autotune()` runs one *real* probe and two documented heuristics inside a
~60-second budget.

| Probe | What it does | Output |
|---|---|---|
| `probes/attention.py` | Times `scaled_dot_product_attention` across 4 representative shapes on the two candidate backends for the detected vendor (CK vs Triton on ROCm; FlashAttention vs mem-efficient on CUDA) and picks the faster. Returns `("math", [])` when torch/GPU absent. | `AttentionBackend` ∈ `{flash_ck, flash_triton, flash_cuda, mem_efficient, math}` + `list[ProbeTiming]` |
| `probes/gemm.py` | Returns the documented vendor default (`hipblaslt_default` / `cublaslt_default` / `reference`). No enumeration — that blows the budget. | `GemmHeuristic` |
| `probes/collective.py` | `noop_1gpu` for 1-GPU/CPU; `rccl_8gpu_xgmi` for a full MI300X node; `nccl_nvlink` for NVIDIA multi-GPU. **Raises** on AMD 2/4-GPU (xGMI asymmetry). | `CollectiveConfig` |

## The `AutotunePlan` schema

Pure pydantic v2 data — JSON round-trippable, hand-writable for tests,
content-addressable.

```python
class AutotunePlan(BaseModel):
    schema_version: Literal["2"] = "2"
    hardware: HardwareProfile           # vendor / arch / gpu_count / total_mem_gb / torch_runtime
    attention_backend: AttentionBackend = "math"
    gemm_heuristic: GemmHeuristic = "reference"
    collective_config: CollectiveConfig = "noop_1gpu"
    fsdp_shard_width: int = 1
    suggested_lora_rank: int = 16
    suggested_micro_batch_size: int = 4
    probe_timings: list[ProbeTiming] = []
    notes: list[str] = []
```

## Consuming a plan

```python
from autotune import run_autotune
from autotune.dispatch import plan_to_env, apply_plan

plan = run_autotune()                       # auto-detects hardware
env = plan_to_env(plan)                     # NCCL_MIN_NCHANNELS, NVTE_CK_*, PYTORCH_ROCM_ARCH, …
cfg = apply_plan(launcher_cfg_dict, plan)   # overlays attention backend, lora_r, micro_batch_size
```

`plan_to_env` returns the env vars the plan implies; `apply_plan` overlays the
plan onto any launcher's config dict (Axolotl, vLLM, torchtune, …).

## CLI

```bash
python -m autotune bench --dry-run --out plan.json   # CI / CPU box: reference plan
python -m autotune bench --device 0 --out plan.json  # real probe on a GPU
python -m autotune detect                            # print the detected HardwareProfile
```

The `--dry-run` path is what makes a CPU-only CI matrix possible: it emits the
per-vendor reference plan and exercises the same downstream code path the real
probe writes.

## Tests

```bash
python -m pytest tests/test_autotune.py -v
```

Covers: dry-run reference plan validity, JSON round-trip, the AMD 2/4-GPU
collective hard-fail, `detect_hardware()` returning a CPU profile on a torch-less
box, and `plan_to_env` emitting the expected vars per backend.
