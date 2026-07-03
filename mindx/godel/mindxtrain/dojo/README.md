# mindXtrain/dojo — the vendored dojo core

This is **the-dojo's Python core** brought in-house so mindXtrain can take its
updates directly (LoRA adapters + curated datasets) without depending on an
external checkout. It is consumed via [`../dojo_bridge.py`](../dojo_bridge.py):
`dojo_updates()` / `latest_lora()` / `stage_datasets()`.

## What lives here
- `engine/dojo_engine/` — the Python training engine (hub, run, runtime, serve_prep,
  installer, env, events). The core that produces LoRA adapters.
- `datasets/` — curated training data (e.g. `codephreak.jsonl`).
- `scripts/`, `docs/`, `test_data/` — helpers, docs, fixtures.
- `outputs/qwen3-0.6b-lora/` — the **first successful dojo imprint** (adapter config
  kept; the `.safetensors`/`.bin` weights are git-ignored and synced per host —
  weights are never committed).

## What does NOT live here
- The **Tauri dApp** (desktop shell, `src-tauri/`, `release/`, `node_modules/`) stays
  in the standalone the-dojo repo (`~/the-dojo`) and is **buildable from deploy**
  (`npm ci && cargo tauri build`) — not vendored. The dApp is where the novel
  **model-export-as-CAR** feature lives; that is **deferred (not needed yet)**.
- Build artifacts / model weights — never committed.

## Flow
`/data` (logs = memories) → `machine.dream` → **mindXtrain** ascent, which folds in
dojo datasets (`stage_datasets`) and can warm-start from the dojo's latest LoRA
(`latest_lora`) → **mindXmodel**. Gated by the compute plant's training core +
`MINDX_ENABLE_MINDXTRAIN` (dormant by default). See
[COMPUTE_PLANT](../../../../docs/COMPUTE_PLANT.md).
