# 道 The Dojo — Usage

A practical, start-to-finish guide: install, **train an actor** from your data,
**serve it as a car**, spar with it, score the results, and export a dataset.

See also: [GLOSSARY.md](./GLOSSARY.md) · [SERVING.md](./SERVING.md) ·
[TECHNICAL.md](./TECHNICAL.md).

---

## 1. Install

```bash
./theway.sh          # interactive — walks every step, Enter accepts each
```

It sets up: system build deps, Node deps, the project `.venv` + PyTorch training
stack for your hardware, the **llama.cpp sidecar** (the "car"), and optional
serving backends (Ollama / vLLM). Full log under `logs/theway-*.log`.

Then run the app:

```bash
npm run tauri dev          # dev, hot-reload
npm run tauri build        # package .deb / .rpm / .AppImage
```

In the app, point **Settings → Python path** at the project `.venv` if it isn't
already (the engine needs torch/peft, which live there).

---

## 2. Train an actor (an "impression")

An **actor** is a model that carries an *impression* — a persona or skill you
imprint with a small LoRA finetune. (See TECHNICAL.md for the full concept.)

1. Go to **LoRA Training**.
2. Pick a **base model** (e.g. `Qwen/Qwen3-0.6B`) and a **dataset** of examples
   in your actor's voice.
3. Set rank/alpha/epochs (defaults are fine to start) and **Start**.
4. Watch live loss in **Jobs**. When it finishes, the adapter lands in
   `outputs/<name>/` — that's your actor.

While a run is in progress it appears at the top of the Sparring model picker
under **In training**; finished actors appear under **Trained**.

---

## 3. Serve the actor as a car

"Activating" an actor starts a **car** — a local `llama-server` process serving
it on `127.0.0.1:8888`.

- **From Sparring:** open the model picker and choose your actor under
  **Trained**. The Dojo merges the adapter, converts it to GGUF (cached after the
  first time), starts the car, and points the chat at it.
- **From the Servers page:** the **Trained models** card has a **▶ Serve**
  button per actor, with live `⚙ merge → GGUF → loading → ✅ ready` progress.

First activation does a one-time merge+convert (minutes on CPU for a 0.6B);
after that it's near-instant from cache. No GPU? It serves on CPU automatically.

### Compare an actor to its pre-imprint base

Next to each actor on the Servers page is a **▶ Base** button. It serves the
**un-imprinted base model** (the same base, same quant, same car — just *without*
the LoRA merge). Use it to answer "is this a model failure or an impression
failure?":

1. **▶ Serve** the actor and **▶ Base** the same model — two cars appear under
   *Running servers*.
2. Go to **Sparring → A/B**, pick the actor on one side and `…-base` on the
   other, ask the **same single question**, and compare.
3. If the **base also breaks**, it's a model/base limit; if only the **actor**
   breaks, it's overfitting in the impression — retrain lighter (see
   [TECHNICAL.md §5](./TECHNICAL.md#5-sampling-notes)).

---

## 4. Spar

**Sparring → Chat** — talk to the actor. The bar exposes:

- **temp** — creativity. `0.000` = pure logic, `1.000` = manic creative. Click
  the value to expand its decimals (3 → … → 18). Outline shifts blue → green →
  red with heat.
- **max** — response length cap.
- **freq / pres** — repetition & presence penalties (defaults 0.5 / 0.3 keep
  small actors from looping).
- **🪙 token counter** — click it for a metrics panel: per-interaction and total
  tokens, average per turn, and the EVM 18-decimal temperature.

**Sparring → A/B** — pit two endpoints head-to-head on the same prompt, then
pick a winner to capture a preference (DPO) pair. Same controls per run.

---

## 5. Score & export

- Rate replies (👍/👎, 1–5, tags, a corrected "preferred" answer) — each becomes
  a row in the **blackbox** dataset. Every turn also records its temperature
  (and the EVM-ready `temp_wei`).
- **Review** browses the blackbox; export a dataset to feed the next round of
  training. The loop closes: spar → score → retrain a sharper actor.

---

## 6. Troubleshooting (quick)

- **Serve does nothing / "Load Failed"** — restart `npm run tauri dev` so the
  backend recompiles; ensure nothing else holds the serving port (the coach
  backend uses 8080; the Dojo serves on 8888). More in
  [SERVING.md](./SERVING.md#4-troubleshooting).
- **Actor loops/repeats** — raise **freq** toward 0.8–1.0.
- **Empty reply on a reasoning model** — raise **max** (its `<think>` phase ate
  the budget).
