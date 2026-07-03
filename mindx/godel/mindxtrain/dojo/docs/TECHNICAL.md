# 道 The Dojo — Technical Reference

Architecture and internals: how the pieces fit, **how a car serves a model**, and
**how an actor is created from an impression**.

See also: [GLOSSARY.md](./GLOSSARY.md) · [SERVING.md](./SERVING.md) ·
[USAGE.md](./USAGE.md).

---

## 1. Architecture

```
┌────────────────────────── Tauri app (Dojo v1.1.x) ──────────────────────────┐
│  Frontend  (React/TS, src/)        ──invoke──▶  Rust host (src-tauri/src/)    │
│   • Sparring (ChatView, ABSpar)                  • commands.rs  (IPC surface)  │
│   • Servers, Models, Jobs, Review                • servers.rs   (the "cars")   │
│   • api.ts  (typed invoke + events)              • chat.rs      (blackbox/DPO) │
│                                                  • jobs.rs      (training runs)│
│                                                  • install.rs   (engine/sidecar)│
│                                       ──spawn──▶  Python engine (.venv, engine/)│
│                                                  • dojo_engine.tasks  (train)  │
│                                                  • dojo_engine.serve_prep (GGUF)│
│                                       ──spawn──▶  llama-server sidecar (a CAR) │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **Frontend ↔ Rust**: Tauri `invoke` for commands; `emit`/`listen` for event
  streams (`job-event`, `server-status`, `server-log`, `serve-prep`, …).
- **Rust ↔ Python**: child processes that print **newline-delimited JSON** on
  stdout (the `events.py` protocol); the host parses each line into a typed event.
- **Rust ↔ sidecar**: `llama-server` spawned as a child, talked to over HTTP
  (OpenAI-compatible).

---

## 2. Using a car for a model

A **car** is the Tauri sidecar — the bundled `llama-server` binary the app runs
to actually serve a model over HTTP. "Using a car for a model" means: take a
model artifact, hand it to a car, and get a chat endpoint.

### 2.1 What the car is and how it's found

- The car binary is fetched by `scripts/fetch_llama.py` into
  `src-tauri/binaries/`, named with the Rust target triple
  (`llama-server-<triple>`), and declared in `tauri.conf.json` under
  `bundle.externalBin`.
- At launch the Dojo resolves the program with **"local then sidecar"**
  (`servers.rs::resolve_binary`): an explicit Settings path → the literal
  `"sidecar"` → the bare name on `PATH`.
- `sidecar_path` picks the copy that **has its runtime libs beside it**
  (`has_runtime_libs`). This matters because the car links *versioned* SONAMEs
  (`libllama-common.so.0`, …) via RUNPATH `$ORIGIN`; a lib-less copy (e.g. the
  bare binary Tauri drops next to the app exe in dev) is skipped so it can't
  crash on load.

### 2.2 Starting a car (`servers.rs`)

`start(app, ServerConfig)` builds the command and spawns it:

```
llama-server -m <model.gguf> --host 127.0.0.1 --port <P> [-c <ctx>]
             [--n-gpu-layers <N>] [extra_args…]
```

- **Port**: one-click activation uses `free_port(8888)` — prefers **8888**,
  scans upward if busy (so it never collides with the coach backend on 8080).
- **Acceleration**: `gpu::detect()` → CUDA offloads (`--n-gpu-layers -1`);
  otherwise **CPU** with `--device none -fit off` (disables the Vulkan build's
  device-memory auto-fit, which otherwise stalls on iGPUs).
- **Lifecycle**: stdout/stderr stream to the UI as `server-log`; a readiness line
  (`server is listening`) flips status `starting → ready`; process exit →
  `stopped`/`error`. All exposed as `ServerInstance` + `server-status` events.

The car speaks the OpenAI API, so the chat client (`streamChat` in `api.ts`) is
identical whether it talks to a car, Ollama (`:11434`), or a cloud endpoint.

### 2.3 Why GGUF

`llama-server` serves **GGUF** only. Training produces **safetensors**. The
bridge from one to the other is what turns a trained actor into something a car
can drive — see §3.

---

## 3. Creating an actor (from an impression)

**Definitions used in the Dojo:**

- **Impression** — a LoRA finetune that *imprints* a persona or skill onto a base
  model. It does not rewrite the base; it learns a small adapter on top.
- **Actor** — the resulting **trained model**: a base + its imprinted adapter,
  embodying that impression. An actor is what you spar with.
- **Car** — the running `llama-server` that *serves* an actor (see §2).

So the chain is: **impression (training) → actor (artifact) → car (serving)**.

### 3.1 Imprinting — producing the actor artifact

A LoRA job (`dojo_engine/tasks/text_lora.py`, driven from the **LoRA Training**
view via `jobs.rs`) runs a real PEFT loop:

1. Load the **base** (e.g. `Qwen/Qwen3-0.6B`) and freeze it.
2. Inject low-rank adapters (`LoraConfig` r/alpha) and train only those on your
   dataset — the *impression*.
3. Save the adapter to `outputs/<name>/` as `adapter_config.json` +
   `adapter_model.safetensors`.

That directory **is the actor**. It's listed under **Trained** in the picker;
in-progress runs show under **In training** (live `step/total` from `jobs.rs`).

> **Codephreak** is the Dojo's **Platform Architect test model** — the first
> impression imprinted here, and the **first actor to become a car**. It's a
> Qwen3-0.6B impression; even at 0.6B it surfaces its architect persona
> (BDI / AGI / RAGE / TLA) straight from the adapter — the impression working.
> (The coherent-prose persona is a separate actor, **ProsePhreak**.) Small actors
> need a repetition penalty to stay coherent; see §5.

### 3.2 Activating — giving the actor a car

Choosing an actor (Sparring picker, or the Servers **▶ Serve** button) calls the
Rust command `serve_trained_model` → `servers::start_trained`, which runs
`dojo_engine.serve_prep` and then starts a car:

```
actor (outputs/<name>/, a LoRA adapter)
   │  serve_prep.py  (runs in .venv)
   │    1. read adapter_config.json → base model id
   │    2. merge LoRA into the base            (PEFT merge_and_unload; CPU ok)
   │       └ offline: HF_HUB_OFFLINE=1 (the base is already cached from training)
   │    3. convert merged HF → GGUF            (llama.cpp convert_hf_to_gguf.py)
   │       └ cached at outputs/<name>/.gguf/<name>.q8_0.gguf
   ▼
serve via the car  (servers.rs::start_trained → start)
   -m <that gguf>  --host 127.0.0.1 --port 8888  --device none -fit off (CPU)
```

- The merge+convert is a **one-time** cost; the GGUF is cached, so re-activating
  an actor is instant.
- The converter is **pinned to llama.cpp tag `b6000`** — the newest tag where
  `convert_hf_to_gguf.py` is a self-contained single file (later tags split it
  into a multi-file `conversion/` package) that still supports Qwen3 and needs
  no `mistral_common`. `serve_prep` ensures `gguf` + `sentencepiece` + `protobuf`
  in the venv, and `fetch_llama.py` vendors the converter next to the sidecar so
  activation is offline after one networked fetch.
- Progress streams as `serve-prep` events (UI shows `merge → GGUF → loading →
  ✅ ready`).

### 3.3 Closing the loop

Sparring with an actor logs turns to the **blackbox** (`chat.rs`), scored into
preference (DPO) pairs in **Review**. Export that dataset, train again → a
sharper impression → a better actor. Spar → score → retrain.

---

## 4. Token accounting & EVM temperature

- `streamChat` requests `stream_options.include_usage`, so each turn returns
  `prompt/completion/total` tokens. Sparring shows per-interaction usage, a
  session total, and a click-through metrics panel (totals, avg/turn).
- **Temperature** is bounded `0.000` (pure logic) … `1.000` (manic creative),
  shown to 3 decimals (click to expand to 18). For EVM compatibility it is also
  measured as an **18-decimal fixed-point integer ("wei")** —
  `tempWei(t) = round(t·1000) · 10^15` (e.g. `0.666 → 666000000000000000`,
  `1.000 → 10^18`). Exact, not a lossy float pad (`src/services/tempColor.ts`).
- Every logged turn persists `temperature` + `temp_wei` in the blackbox
  (`chat.rs::ChatRecord`), verified by the `temp_wei_persists` serde round-trip
  test and the `log_turn_writes_temp_wei` on-disk write test.

### 4.1 Can a temperature actually be set to 18 decimals?

**Not for inference — only for accounting.** The distinction matters:

| Layer | Numeric type | Effective precision |
|-------|--------------|---------------------|
| UI / JSON transport | float64 | ~15–17 significant digits |
| llama.cpp / model sampling | **float32** | **~7 significant digits** |
| Dojo `temp_wei` record | int (10¹⁸ scale) | exact, but for storage only |

So an 18-decimal temperature **cannot change how the model samples** — the engine
rounds it to float32 long before it reaches the logits, and in practice
differences smaller than ~`0.001` almost never flip a sampled token. Setting
`0.666000000000000001` and `0.666` produces identical generation.

What the 18 decimals *are* good for: an **exact, lossless, EVM-compatible record**
of the setting. `temp_wei` is a fixed-point integer (like wei for ether), so it
round-trips through JSON/ledgers/contracts with no float drift and can be
compared or summed deterministically. The Dojo therefore:

- **applies** temperature at the engine's real precision (float32, ~7 digits),
- **displays** it at 3 decimals (click to expand toward 18 for inspection),
- **records** it at full 18-decimal fixed point (`temp_wei`) for the blackbox.

In short: you can *store and display* 18 decimals; you cannot *sample* at 18
decimals. Treat anything past ~3 decimals as provenance, not control.

---

## 5. Sampling notes

Small actors (≤1B) overfit on a strong impression degenerate into repetition —
a "token salad" of their imprinted vocabulary. The Dojo's `streamChat` defends
against this with, when a penalty is set (default `freq 0.5` / `pres 0.3`):

- `frequency_penalty` / `presence_penalty` (OpenAI-standard),
- `repeat_penalty = 1 + frequency_penalty` and `repeat_last_n = 256`,
- the **DRY sampler** ("Don't Repeat Yourself"): `dry_multiplier 0.8`,
  `dry_base 1.75`, `dry_allowed_length 2`.

DRY is the decisive one — it penalizes *sequences* the model has already emitted,
which is exactly the failure mode of an overfit actor. With it, the codephreak
test model goes from `AGI. BDI. RAGE. TLA.`-style loops to coherent, on-persona
output at the default temperature. (llama.cpp/Ollama ignore unknown sampler fields; a strict
cloud "Challenger" endpoint might not, so these ride along only when a penalty is
set.) Tune `freq` toward 0.8–1.0 and/or lower `temp` if an actor still loops.

The deeper fix is training-side: less overfitting (fewer epochs, lower rank,
more diverse data, or a larger base) yields an actor that stays coherent with
lighter sampling.

---

## 6. Headless CLI — MCP integration & Training-as-a-Service (TaaS)

The desktop app is a **front-end over a headless engine**: every core capability
is a CLI entry point under the project `.venv`, so the Dojo can be driven by an
MCP server, a CI job, or a TaaS backend with **no GUI**. The Rust host invokes
these same commands — there is no GUI-only path.

All engine commands print **newline-delimited JSON** on stdout (the `events.py`
protocol): `{"type":"log"|"progress"|"done"|"error", …}`. A caller spawns the
process and parses each line; `done` carries the artifact path, `error` is fatal.

| Capability | Command |
|------------|---------|
| Env / capability report | `python -m dojo_engine.run --doctor` |
| **Train a model (job)** | `python -m dojo_engine.run --config job.json` |
| Search / download models | `python -m dojo_engine.hub --search … / --download …` |
| Prep an actor → GGUF | `python -m dojo_engine.serve_prep --adapter outputs/<name>` |
| Install/repair the stack | `python -m dojo_engine.installer --install --target auto` |
| Serve an actor (the car) | `llama-server -m <gguf> --host H --port P` (see §2) |

### 6.1 Job config schema (`--config job.json`)

```json
{
  "id": "codephreak-qwen3",
  "name": "Codephreak impression",
  "task": "lora",                 // lora | finetune | embedding
  "modality": "text",            // text | image
  "base_model": "Qwen/Qwen3-0.6B",
  "dataset_path": "/path/to/dataset.jsonl",
  "output_dir": "outputs/codephreak-qwen3",
  "config": {
    "epochs": 3, "batch_size": 4, "learning_rate": 1e-4,
    "rank": 8, "alpha": 16,
    "extra": { "target_modules": "q_proj,v_proj" }
  }
}
```

Registered `(task, modality)` trainers: `lora/text`, `lora/image`,
`finetune/text`, `finetune/image`, `embedding/text`, `embedding/image`.

### 6.2 TaaS / MCP loop

A service wraps the lifecycle as headless steps:

1. **Provision** — `installer --install --target auto` (once per worker),
   `run --doctor` to confirm the device.
2. **Train** — write `job.json`, spawn `run --config job.json`, stream
   `progress` events to the client; the adapter (the **actor**) lands in
   `output_dir`.
3. **Serve** — `serve_prep --adapter <dir>` → GGUF, then launch the **car**
   (`llama-server`) on a free port; expose its OpenAI-compatible `/v1`.
4. **Infer / spar** — clients hit the car's `/v1/chat/completions` (the same API
   the desktop Sparring view uses).

Because the transport is plain processes + NDJSON + an OpenAI HTTP surface, an
MCP server only needs to shell out and relay — no Dojo-internal coupling.

## 7. Versioning

`scripts/bump-version.mjs` bumps the patch (build) number across `package.json`,
`tauri.conf.json`, and `Cargo.toml`; it runs from `npm run build`, so every
release build increments the version. Started at **v1.1.1**. The frontend reads
it via the Vite-injected `__APP_VERSION__` (shown in the sidebar).
