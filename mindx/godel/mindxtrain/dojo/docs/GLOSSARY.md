# 道 The Dojo — Glossary

Plain-language definitions of the terms you'll meet in the Dojo, with a note on
*where each one shows up* in this project. Newcomers can read top to bottom;
everyone else can jump to a term.

---

## Models & training

### Base model
The pretrained model you start from (e.g. `Qwen/Qwen3-0.6B`). Training in the
Dojo never rewrites the base — it learns a small **adapter** on top of it. A
job's base is stored on `Job.base_model`.

### Finetune
Continuing training of a base model on your own data so it adopts a voice, a
skill, or a domain. The Dojo's finetune tasks live in
`engine/dojo_engine/tasks/` (`text_lora.py`, `finetune.py`, `image_lora.py`, …).

### LoRA — Low-Rank Adaptation
A finetuning method that **freezes the base model** and trains only a tiny pair
of low-rank matrices injected into each attention layer. The result is an
**adapter** of a few megabytes instead of a multi-gigabyte full model. Cheap to
train (runs on CPU for a 0.6B), cheap to store, and you can keep many adapters
for one base. In the Dojo a LoRA run produces a directory under `outputs/` (e.g.
`outputs/codephreak-qwen3/`) containing `adapter_config.json` +
`adapter_model.safetensors`. Knobs: **rank** (`r`) and **alpha** (`TrainConfig`).

### PEFT — Parameter-Efficient Fine-Tuning
The Hugging Face **library** (and the umbrella term) for methods like LoRA that
tune a small fraction of parameters. The Dojo installs `peft` into `.venv` and
uses it both to *train* adapters (`get_peft_model`, `LoraConfig`) and to *load*
them back onto a base (`PeftModel.from_pretrained`) — see
`engine/dojo_engine/serve_prep.py`, which calls `merge_and_unload()` to bake an
adapter into its base.

### Adapter
The small, swappable set of trained weights a LoRA run produces. It is *not* a
standalone model — it only means something paired with its base. "Merging" an
adapter writes its deltas into the base to produce a single full model.

### Merge (`merge_and_unload`)
Folding a LoRA adapter's weights into the base to get one self-contained model
with no separate adapter file. The Dojo merges as the first step of serving a
trained model through the llama.cpp sidecar (then converts the merged model to
**GGUF**).

---

## File formats

### safetensors
A safe, fast tensor-serialization format from Hugging Face. Unlike Python
pickles (`.bin`/`.pt`), it can't execute code on load and it memory-maps quickly.
Both base models and LoRA adapters in the Dojo are stored as `.safetensors`
(e.g. `adapter_model.safetensors`, `model.safetensors`). This is the **training
& Hugging Face** format.

### GGUF — GGML Universal Format
The single-file model format used by **llama.cpp** for *inference*. It bundles
the weights, tokenizer, and metadata, and supports **quantization** (e.g.
`q8_0`, `q4_k_m`) to shrink the model and speed up CPU/GPU serving. The Dojo
trains in safetensors and converts to GGUF only when it's time to serve:
`serve_prep.py` runs llama.cpp's `convert_hf_to_gguf.py` to emit a
`<name>.q8_0.gguf`. Rule of thumb: **safetensors to train, GGUF to serve.**

### Quantization
Storing weights at lower precision (8-bit, 4-bit, …) to cut memory and increase
throughput, at a small quality cost. Encoded in the GGUF quant type (the
`--outtype` passed to the converter; default `q8_0` in `serve_prep.py`).

---

## Serving & runtimes

### Sidecar
A helper executable the Dojo's Tauri app bundles and launches alongside itself —
here, llama.cpp's **`llama-server`**. `scripts/fetch_llama.py` downloads the
right prebuilt binary for your OS + accelerator and drops it (target-triple
named) into `src-tauri/binaries/`, where Tauri's `externalBin` picks it up. At
runtime the app resolves "local then sidecar": your own `llama-server` on `PATH`
first, the bundled sidecar as fallback (`src-tauri/src/servers.rs`). For the
full picture — how a *model* becomes a car, plus runtime ports/commands — see
[SERVING.md](./SERVING.md).

### llama.cpp / `llama-server`
The C/C++ inference engine (and its HTTP server) that runs **GGUF** models with
an OpenAI-compatible API. It's the default local inference path in the Dojo and
the target of the sidecar. Serve a model with `-m model.gguf` (optionally
`--lora adapter.gguf`, `--n-gpu-layers`, `-c` ctx size).

### Ollama
A separate local model runtime that manages its own library and exposes an
OpenAI-compatible API at `localhost:11434`. The Sparring picker lists installed
Ollama models (`ollama list`). Note: a model must be *registered* in Ollama to
be served by it — picking a trained adapter that was never imported is what
produced the old `model not found` 404, which is why trained models now serve
through the **sidecar** instead.

### vLLM
A high-throughput, GPU-oriented serving engine (`vllm serve <model>`). Optional
in the Dojo (installed via `theway.sh --vllm`), managed by the same server
manager as llama.cpp.

### Server instance
A running inference process the Dojo supervises — its runtime, model, host/port,
`base_url`, and status (`starting → ready → stopped/error`). Defined by
`ServerInstance` in `src-tauri/src/servers.rs`; the Sparring picker's "Running
servers" group and the Servers view both read from it.

---

## App & workflow

### Sparring
The Dojo's chat/evaluation view (`src/components/ChatView.tsx`, plus A/B in
`ABSpar.tsx`): chat with a model, score responses, and capture the turns as
training data. Its model picker lists, top to bottom: **In training → Trained →
Running servers → Ollama → Challenger** (cloud / custom endpoint). Choosing a
trained model *activates* it — prep to GGUF, serve via the sidecar, select it.

### Training stack
The PyTorch + Transformers + PEFT + Datasets + Accelerate environment installed
into the Dojo's `.venv` for your hardware (CPU / CUDA / ROCm), driven by
`dojo_engine.installer`.

### `theway.sh`
The one-command setup script. Walks every step in order — system build deps,
Node deps, the `.venv` + training stack, the llama.cpp **sidecar**, and optional
serving backends (Ollama / vLLM) — narrating to the screen and to
`logs/theway-*.log`.

### Job
One training run: its task, base model, dataset, output dir, config, live
`progress` (step/total/epoch/loss) and `status`
(`queued | running | completed | failed | cancelled`). Tracked in
`src-tauri/src/jobs.rs`; running jobs surface as the "In training" group in
Sparring.
