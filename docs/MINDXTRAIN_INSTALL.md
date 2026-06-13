# mindXtrain Install — CPU (handheld-class) and GPU (MI300X)

mindXtrain (github.com/professor-Codephreak/mindXtrain, v1.0.0) is the external
fine-tuning framework that turns mindX's curated dream wisdom into weights (the
RIGHT apex of the Schmidhüber pendulum). It is **not vendored** into mindX — it
lives as a sibling checkout and mindX drives it via subprocess (the isolation
contract, see `mindx/godel/mindxtrain/`).

**On the mindX production VPS we install the CPU build only** — an 8 GB / 2-core
Hostinger box, deliberately treated like a handheld-class device: small base
model, CPU-only torch, self-throttled training. The GPU/ROCm path is documented
here for completeness (it targets an AMD MI300X host) but is **not** installed
on the VPS.

## Prerequisites

```bash
# uv (the package manager mindXtrain uses) — installs to ~/.local/bin
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
uv --version            # 0.11.x+

# clone mindXtrain as a sibling of the mindX repo (the bridge discovers it at
# <mindX-root>/../mindXtrain)
git clone --depth 1 https://github.com/professor-Codephreak/mindXtrain ~/mindXtrain
```

## CPU install (what mindX runs — handheld-class)

The default `uv sync --extra ml` pulls **CUDA torch (~5 GB of nvidia-* wheels)**
even on a CPU-only box — dead weight that nearly fills an 8 GB VPS's disk. The
`--torch-backend cpu` selector works on **`uv pip install`** but, in uv 0.11.x,
is **not** honored by `uv sync` (nor is the `UV_TORCH_BACKEND` env var — verified
2026-06-13). The reliable method is to install CPU torch *before* the ML extra,
so torch is already satisfied as `+cpu` when the extra resolves:

```bash
cd ~/mindXtrain
uv sync                                    # base (CPU; config / dry-run / provenance)
uv pip install --torch-backend cpu torch   # the genuine CPU wheel, from the PyTorch CPU index
uv sync --extra ml                          # trl/transformers/peft/accelerate/datasets;
                                            # torch already +cpu → no CUDA pulled
```

Verify it is genuinely a CPU build (no CUDA, tensor math works):

```bash
uv run python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# -> 2.12.0+cpu False
```

**If CUDA torch was already pulled** (you ran `uv sync --extra ml` first — the
common trap), repair it: uninstall, reinstall the CPU wheel, prune the orphaned
CUDA libs. This is the exact sequence that brought the VPS venv from 5.0 GB to
1.9 GB:

```bash
cd ~/mindXtrain
uv pip uninstall torch
uv pip install --torch-backend cpu torch          # -> torch 2.12.0+cpu
# drop the now-orphaned CUDA libraries (~3 GB)
uv pip uninstall $(uv pip list | grep -iE '^nvidia|^cuda' | awk '{print $1}')
uv run python -c "import torch; print(torch.__version__)"   # 2.12.0+cpu
```

Notes / pitfalls:
- `UV_TORCH_BACKEND=cpu uv sync` does **not** force CPU wheels in uv 0.11.x —
  use the `uv pip install --torch-backend cpu` sequence above.
- Order matters: install CPU torch **before** `--extra ml`, or you pull the
  CUDA stack first and have to repair it.
- Run heavy installs `nice -n 19 ionice -c3` so the live mindX service stays
  responsive (the box is shared).
- The `ml` extra is `trl / transformers / peft / accelerate / datasets`; torch
  arrives transitively, which is why the wheel selection has to be forced.

## GPU install (MI300X — reference, NOT on the VPS)

The full training / eval / quantize paths require an **AMD MI300X with ROCm
7.2.1**, run inside the `rocm/primus:v26.2` container. torch must be the ROCm
build, not CUDA:

```bash
# inside the rocm/primus container on the MI300X host
cd mindXtrain
# ROCm torch (uv selects the AMD index); add eval/data extras as needed
UV_TORCH_BACKEND=rocm6.3 uv sync --extra ml --extra eval --extra data
# or pin via the PyTorch ROCm index if the backend tag is unavailable:
#   uv pip install torch --index-url https://download.pytorch.org/whl/rocm6.3
uv run mindxtrain bench            # 60s AOT autotune probe -> autotune_plan.json
uv run mindxtrain train run.yaml --plan autotune_plan.json
```

The GPU path additionally enables: the real 60-second AOT autotune probe (CK-vs-
Triton attention, hipBLASLt, RCCL), Quark FP8 / MXFP4 quantize, and full-size
base models (Qwen3-8B/32B recipes). None of this runs on the CPU VPS.

## The mindX CPU recipe

mindXtrain ships purpose-built mindX CPU recipes (`mindxtrain init --list`):
- `mindx_fallback_qwen3_1_5b_cpu_smoke` — SmolLM2-135M, float32, ~1.2 GB RSS,
  one epoch, 10–30 min: verifies the dream-corpus → SFT → checkpoint loop on a
  CPU laptop. **This is what the first VPS ascent uses.**
- `mindx_fallback_qwen3_1_5b_cpu_real` — the real qwen3-1.5B CPU run.

The recipe's `data.source: mindx_dreams` reads mindX's dream training files
(`data/memory/ltm/*/*_training.jsonl`) directly — point `data.path` at the
deploy's `data/memory` (the recipe default is the dev box path):

```bash
uv run mindxtrain init -t mindx_fallback_qwen3_1_5b_cpu_smoke -o run.yaml
sed -i 's#path: /home/hacker/mindX/data/memory#path: /home/mindx/mindX/data/memory#' run.yaml
# train self-throttles via the recipe (cpu_throttle.percent); override lower on
# a contended box:
uv run mindxtrain train run.yaml --out out/runs --cpu-percent 20 --cpu-nice 19
```

See `docs/SCHMIDHUBER_ENGINE.md` for how this fits the knowledge→wisdom→weights
ascent, and `mindx/godel/mindxtrain/` for the bridge that drives it.
