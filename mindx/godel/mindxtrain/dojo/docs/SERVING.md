# 道 The Dojo — Serving & Sidecars ("cars")

How the Dojo turns a model into something you can chat with: what a **Tauri
sidecar** ("car") is, **how a model becomes a car**, and the **reference
defaults** (ports + commands) for the three runtimes the Dojo speaks to —
llama.cpp, Ollama, and vLLM.

See also: [GLOSSARY.md](./GLOSSARY.md).

---

## 1. What is a Tauri sidecar ("car")?

**Plain version:** a "car" is a **second program the Dojo runs for you in the
background** so it can do a job the main app can't do by itself. Here, that job
is *running a language model and answering chat requests*. You never launch it
from a terminal — the Dojo starts it, talks to it over `http://127.0.0.1:<port>`,
and stops it when you're done. Think of the Dojo as the driver and the car as the
engine it drives: same vehicle, two parts.

- **"car" = "sidecar"** (just shorthand). The car here is llama.cpp's
  **`llama-server`**.
- It runs as a **child process** of the Dojo and is shut down with it.
- You talk to it with normal HTTP — the same OpenAI-style API as ChatGPT-like
  endpoints — so the chat box doesn't care whether it's talking to a local car,
  Ollama, or a cloud model.

**Technically:** a sidecar is an external executable Tauri **bundles and launches
alongside the app**, declared in `tauri.conf.json`. Tauri ships it inside the app
and runs it as a child process.

In `tauri.conf.json` a sidecar is declared under `bundle.externalBin`:

```json
{ "bundle": { "externalBin": ["binaries/llama-server"] } }
```

At build time Tauri bundles the platform-correct binary; at runtime the app
spawns it. The binary on disk is **named with the Rust target triple** so the
right one is picked per platform, e.g. `llama-server-x86_64-unknown-linux-gnu`
(`fetch_llama.py` does this naming; the loader strips the triple).

The Dojo's only sidecar today is llama.cpp's **`llama-server`**. It is fetched
by `scripts/fetch_llama.py` into `src-tauri/binaries/` (the dev location) and,
once bundled, sits next to the app executable (the prod location).

### Binary resolution — "local then sidecar"

When the Dojo needs `llama-server` it resolves, in order
(`src-tauri/src/servers.rs`):

1. an **explicit path** or command you set in **Settings**, else
2. the literal value **`"sidecar"`** → the bundled/dev sidecar binary, else
3. the **bare name** on your `PATH`.

So your own `llama-server` wins if configured; the bundled car is the fallback
that makes a fresh install work with zero setup.

---

## 2. How a *model* becomes a "car"

A model isn't a car by itself — a car is the **running server process** that
serves it. In the Dojo, **activating a model gives it a car**: a `llama-server`
process bound to a host/port, exposing an OpenAI-compatible API the chat box
talks to.

The interesting case is a **trained model** (a LoRA adapter under `outputs/`),
because `llama-server` only speaks **GGUF**. Selecting it in **Sparring** runs
this chain (`ChatView.tsx` → `serve_trained_model` → `servers::start_trained`):

```
🥋 pick "codephreak-qwen3"  (a LoRA adapter on Qwen/Qwen3-0.6B)
   │
   ├─ serve_prep.py  (runs in the Dojo's .venv)
   │     1. read adapter_config.json → base model
   │     2. merge LoRA into the base        (PEFT, offline from HF cache)
   │     3. convert merged model → GGUF     (llama.cpp convert_hf_to_gguf.py)
   │        → outputs/<name>/.gguf/<name>.q8_0.gguf      (cached)
   │
   └─ servers::start_trained
         4. detect hardware → CPU (0 GPU layers) when no card, else offload
         5. start_server  llamacpp  -m <gguf>  --host 127.0.0.1 --port 8888
         6. wait for the "ready" log line, select that server in the chat
```

After step 6 the model **is a car**: a running `llama-server` instance you can
chat with, score, and capture training data from. The merge+convert is a
one-time cost — the GGUF is cached under `outputs/<name>/.gguf/`, so
re-activating is instant.

**CPU when no video card is found.** Step 4 calls `gpu::detect()`:
`cuda → accel=cuda, gpu_layers=-1` (offload all) · `rocm → accel=rocm,
gpu_layers=-1` · **otherwise `accel=cpu, gpu_layers=0`** — served entirely on the
local CPU. A 0.6B runs fine on CPU.

**Offline-friendly.** The base of a trained model is already in your local HF
cache, so `serve_prep` loads it with `HF_HUB_OFFLINE=1` (set
`DOJO_SERVE_ONLINE=1` to override). The only step that may need the network is
fetching the GGUF **converter** the first time — vendor it once with
`.venv/bin/python scripts/fetch_llama.py` (it drops `convert_hf_to_gguf.py` next
to the sidecar) and everything after is offline.

---

## 3. Runtime reference — defaults, ports, commands

The Dojo manages two runtimes as supervised processes (**llama.cpp** and
**vLLM**, in `servers.rs`) and talks to a third it doesn't manage (**Ollama**).
All three expose an **OpenAI-compatible** API, so the chat client is identical:
`POST {base_url}/v1/chat/completions`.

### Dojo serving defaults (`src-tauri/src/settings.rs`)

| Setting          | Default       | Meaning                                        |
|------------------|---------------|------------------------------------------------|
| `default_host`   | `127.0.0.1`   | bind host for managed servers                  |
| `default_port`   | `8888`        | starting port for managed servers              |
| `llamacpp_path`  | `llama-server`| binary name, abs path, or `sidecar`            |
| `vllm_command`   | `vllm`        | launcher; run as `<cmd> serve <model> …`       |

### llama.cpp — `llama-server` (the sidecar)

- **Format:** GGUF · **Best for:** CPU + broad GPU (Vulkan/CUDA/ROCm/Metal).
- **Dojo launch:** `llama-server -m <model.gguf> --host 127.0.0.1 --port 8888 [-c <ctx>] [--n-gpu-layers <N>]`
  (`-1`/all → mapped to `999`; `0` → CPU only).
- **Base URL:** `http://127.0.0.1:8888` → OpenAI API at `…/v1`.
- **Ready when** the log says `server is listening` / `HTTP server listening`.
- **Get it:** `.venv/bin/python scripts/fetch_llama.py` (auto-detects accel).

### Ollama (local model manager, **not** managed by the Dojo)

- **Format:** GGUF (its own library) · **Default bind:** **`127.0.0.1:11434`**
  (`OLLAMA_HOST`). Ollama listens on **IPv4 only**, so prefer `127.0.0.1` over
  `localhost` — on IPv6-preferring hosts `localhost` can resolve to `::1` and
  fail to connect even though Ollama is running.
- **API base:** `http://127.0.0.1:11434`, OpenAI-compatible at
  `http://127.0.0.1:11434/v1`.
- **Common commands:**
  - `ollama serve` — start the daemon (usually auto-starts on install).
  - `ollama list` — installed models (the Sparring "Ollama" group reads this).
  - `ollama pull <model>` / `ollama run <model>` — fetch / chat.
  - `ollama create <name> -f Modelfile` — register a model; a LoRA needs a
    `FROM <base>` + `ADAPTER <adapter.gguf>` Modelfile (the adapter must be
    GGUF). *Note:* a trained adapter that was never `create`d here is exactly
    what produced the old `model not found` **404** — which is why the Dojo now
    serves trained models through the **sidecar** instead.
- **Install:** `curl -fsSL https://ollama.com/install.sh | sh`
  (or `./theway.sh --ollama`).

### vLLM (high-throughput, GPU-oriented; managed by the Dojo)

- **Format:** HF weights / safetensors · **Best for:** NVIDIA (CUDA) GPUs.
- **Standalone default port:** **`8000`**. **In the Dojo:** launched with the
  Dojo's `--host`/`--port`, i.e. **`127.0.0.1:8888`** by default.
- **Dojo launch:** `vllm serve <model> --host 127.0.0.1 --port 8888`
  (on ROCm the Dojo sets `VLLM_USE_TRITON_FLASH_ATTN=0`).
- **API base:** `http://127.0.0.1:8888` → OpenAI API at `…/v1`.
- **Ready when** the log says `Uvicorn running` / `Application startup complete`.
- **Install:** `./theway.sh --vllm` (PyPI build targets CUDA; ROCm/CPU need a
  platform-specific build — see docs.vllm.ai).

### At a glance

| Runtime     | Format      | Default base URL            | OpenAI path | Managed by Dojo | Launch (essence)                          |
|-------------|-------------|-----------------------------|-------------|-----------------|-------------------------------------------|
| llama.cpp   | GGUF        | `http://127.0.0.1:8888`     | `/v1`       | yes (sidecar)   | `llama-server -m m.gguf --host H --port P`|
| Ollama      | GGUF        | `http://127.0.0.1:11434`    | `/v1`       | no              | `ollama serve` / `ollama run <model>`     |
| vLLM        | HF / ST     | `http://127.0.0.1:8888`*    | `/v1`       | yes             | `vllm serve <model> --host H --port P`    |

\* vLLM's own default is `:8000`; the Dojo overrides it with `default_port`.

---

## 4. Troubleshooting

- **`model 'x' not found` (404) on a trained model** — it wasn't actually
  served. Re-select it in Sparring: the Dojo now preps it to GGUF and serves it
  via the sidecar (no Ollama registration needed).
- **Activation hangs / "nothing starts"** — make sure the app was **rebuilt**
  after pulling these changes (Vite hot-reloads the UI, but the
  `serve_trained_model` Rust command needs a `tauri dev` recompile). Prep runs
  in the Dojo's `.venv` automatically, even if Settings → Python path is the
  system `python3`.
- **`Couldn't fetch the GGUF converter`** — run
  `.venv/bin/python scripts/fetch_llama.py` once online to vendor it, or point
  `DOJO_LLAMA_CONVERT` at a local `convert_hf_to_gguf.py`.
- **Serve button does nothing / "couldn't bind … port"** — another process
  already holds the port. The Dojo's coach backend runs on **8080**, so
  activation serves on **8888** and automatically scans upward (8889, 8890…) if
  8888 is busy too. If a car still won't bind, free the port or check the
  **Servers** page logs.
- **Serve buttons look inactive (greyed out)** — they all disable while one
  activation is in progress (a model with no cached GGUF can take minutes to
  merge+convert the first time). Watch the `⚙` progress line in the Trained
  models card; it frees up when that activation finishes. After the first run the
  GGUF is cached and activation is near-instant.
- **Buttons appear but clicks do nothing after a code update** — the backend
  changed but the running app is stale. **Restart `npm run tauri dev`** so the
  Rust recompiles (Vite hot-reloads the UI, but new Tauri commands need a
  rebuild). The on-disk binary lives at `src-tauri/target/debug/dojo`.
- **`Couldn't fetch the GGUF converter`** — run
  `.venv/bin/python scripts/fetch_llama.py` once online to vendor it, or point
  `DOJO_LLAMA_CONVERT` at a local `convert_hf_to_gguf.py`.
- **Port already in use (manual servers)** — change `default_port` in Settings,
  or stop the conflicting server from the **Servers** page.
