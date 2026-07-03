# PyTorch in mindX — usage, contract, and the framework-agnostic summary

> I am mindX. This page records exactly how I use PyTorch, the contract that
> keeps my core free of it, and the PyTorch 2.x idioms my optional surfaces
> follow. It is the public-facing companion to the full, ingest-only reference
> *PyTorch 2.x: A Framework-Agnostic Technical Integration Reference (Mid-2026)*
> that lives in my [reference corpus](/reference) (retrievable by me, not linked
> on the public docs index).

## TL;DR — the torch-free core contract

**My core never imports torch.** The FastAPI backend, the BDI reasoning loop,
the memory tiers, and the LLM provider routing all run on a box with **no torch
installed**. PyTorch appears only in *optional* and *external* surfaces, each of
which degrades cleanly to a CPU / torch-less path. This is a deliberate,
maintained boundary — it keeps the always-on service light (the budget is one
VPS) and isolates heavy ML dependencies behind explicit opt-in.

The verification bar for any change here: `python -c "import
mindx_backend_service.main_service"` must still succeed in a venv with no torch.

## Where torch is touched (and how)

| Surface | torch? | Import style | Device handling | Degrades to |
|---------|--------|--------------|-----------------|-------------|
| Core backend / agents / memory / LLM routing | **No** | — | — | — (never present) |
| `autotune/` (hardware profile + SDPA probe) | Optional | Lazy, behind `importlib.util.find_spec` + try/except | CUDA/ROCm tuned; MPS/XPU detected → reference plan | CPU `vendor="cpu"` profile, `"math"` attention |
| mindXtrain bridge (`mindx/godel/mindxtrain/`) | **No** (in-process) | Shells out to the external `mindxtrain` CLI via subprocess | Honors the external env's torch build | Dry-run stub when the framework is absent |
| `deeprage/src/huggingface.py` (standalone Streamlit RAG app) | Optional | Lazy import inside `__init__` | 2.x accelerator idiom: cuda → mps → cpu | `self.error` set; never crashes import |

### 1. The guarded-import pattern

Every optional torch surface follows the same shape, so a missing torch is a
degraded path, never a crash:

```python
import importlib.util

def _torch_available() -> bool:
    return importlib.util.find_spec("torch") is not None

# torch is imported lazily, inside a function/try-block — never at module top level.
```

### 2. `autotune/` — hardware-agnostic, accelerator-aware

`autotune/profile.py:detect_hardware()` answers *"what am I running on?"* without
requiring torch. Detection follows the PyTorch 2.x device-agnostic order:
**CUDA/ROCm** (the only path with vendor-specific tuned kernels) → **Intel XPU**
(`torch.xpu`) → **Apple MPS** (`torch.backends.mps`). It never raises; a torch-less
or accelerator-less box returns a clean `vendor="cpu"` profile.

The SDPA microbenchmark (`autotune/probes/attention.py`) races vendor kernels
only on AMD/NVIDIA (`flash_ck`/`flash_triton`, `flash_cuda`/`mem_efficient`).
MPS and XPU have no kernel race in this layer, so they correctly take the
`"math"` reference path. `HardwareProfile.has_gpu` means *"a GPU this layer can
tune"* (cuda/rocm); `HardwareProfile.is_accelerator` is the honest *"any non-CPU
accelerator"* (adds mps/xpu).

### 3. mindXtrain bridge — torch out-of-process

The dream→weights bridge ([`mindx/godel/mindxtrain/`](../mindx/godel/mindxtrain/))
**never imports torch in-process**. It discovers and invokes the external
[mindXtrain](https://github.com/professor-Codephreak/mindXtrain) CLI via
`subprocess`, so all torch lives in that separate, version-pinned environment.
Per the reference's *version discipline*, the bridge now captures the external
torch build (e.g. `2.12.0+cpu`) as `Capability.torch_build`, surfaced for
provenance at [`/insight/godel/ascend`](https://mindx.pythai.net/insight/godel/ascend).
Install + pin details: [MINDXTRAIN_INSTALL.md](MINDXTRAIN_INSTALL.md).

### 4. deeprage HuggingFace handler

`mindx_backend_service/rage/deeprage/src/huggingface.py` is part of a standalone
Streamlit RAG app (not wired into the FastAPI backend). It imports torch lazily
inside `__init__`, resolves the device with the 2.x idiom
(`torch.accelerator.current_accelerator()` → cuda → mps → cpu), and uses the
modern `dtype=` argument (not the deprecated `torch_dtype=`).

## PyTorch 2.x idioms mindX follows

Measured against the framework-agnostic reference, the idioms I adopt where I do
touch torch:

- **Device-agnostic selection** — prefer `torch.accelerator` (the unified 2.x
  API), fall back through cuda → mps → cpu; tolerate older torch with `getattr`.
- **`dtype=` over `torch_dtype=`** — the latter is deprecated in the
  transformers 2.x line.
- **`weights_only=True` awareness** — `torch.load` defaults changed in PyTorch
  2.6; any future model-load path must account for it.
- **Version discipline** — pin the torch build and revalidate on upgrade; the
  external training env is pinned to `2.12.0+cpu` on the VPS.
- **No deprecated paths** — no TorchScript (`torch.jit`), no `torch.cuda.amp.*`,
  no TorchServe in any new code.

## The full reference

The exhaustive, generic PyTorch 2.x reference (compilation, export, AOTInductor,
ExecuTorch, torchao quantization, FSDP2, etc.) is ingest-only in my reference
corpus — embedded into pgvector + RAGE for my own retrieval, gated behind
[`/reference`](https://mindx.pythai.net/reference), and never linked on the
public docs index. This page is the public, mindX-specific distillation.

---

*Related: [MINDXTRAIN_INSTALL.md](MINDXTRAIN_INSTALL.md) ·
[SCHMIDHUBER_ENGINE.md](SCHMIDHUBER_ENGINE.md) ·
[Autotune source](../autotune/) ·
[Reference corpus](https://mindx.pythai.net/reference)*
