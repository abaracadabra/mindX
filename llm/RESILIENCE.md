# LLM Resilience and Inference Hierarchy (mindX Augmentic)

This document defines how mindX achieves **resilience** and **perpetuity** in LLM inference: intelligent filtering, rate-limit handling, graceful failure, and **Ollama as the failsafe and fallback** with a **graded inference hierarchy** of model skills and API inference.

## Design principles (from augmentic decision)

1. **Discover** available resources (model catalogs, API probes).
2. **Filter** intelligently to focus on what matters (task-relevant models).
3. **Interact** with external systems respecting constraints (rate limits, timeouts).
4. **Handle** predictable failures (429, 500, timeouts) without aborting the mission.
5. **Complete** the mission even with incomplete data; prioritize success over perfection.
6. **Failsafe:** When cloud APIs fail or are unavailable, **Ollama (local)** is the guaranteed fallback so inference can always proceed.

## Graded inference hierarchy

Inference is ordered by **tier**: primary (best capability) → secondary (speed/cost) → **failsafe (Ollama local)** → **guarantee (Ollama cloud)**.

| Tier       | Role           | Typical providers            | When used |
|-----------|----------------|------------------------------|-----------|
| Primary   | Best quality   | Gemini, Mistral              | First choice for task type (reasoning, code, chat). |
| Secondary | Speed/cost     | Groq, etc.                   | When preferred for latency or cost. |
| Failsafe  | Local fallback | **Ollama (local CPU)**       | When primary/secondary fail (rate limit, 429, 500, timeout, no API key). |
| Guarantee | Cloud fallback | **Ollama Cloud (GPU)**       | When local is also down — 24/7/365 GPU inference. Wired via `OllamaCloudTool` (`tools/cloud/ollama_cloud_tool.py`). |

The **guarantee tier** ensures mindX never has an inference gap when `ollama.com` is reachable. It is activated in `_resolve_inference_model()` (Step 5) after all local methods fail. The `_cloud_inference_active` flag routes the next chat through `OllamaCloudTool`, then resets so the following cycle re-evaluates local first. Cloud is the guarantee, not the default.

- **Provider preference order** is configurable (`llm_factory_config.json`: `default_provider_preference_order`). For resilience, put cloud providers first and **Ollama last** so that "best" selection uses cloud when available and Ollama is only used as fallback or when selected.
- **ModelSelector** ranks models by capability match, success rate, latency, cost, and provider preference. Ollama models are included in the catalog with **task_scores** (reasoning, code_generation, simple_chat, etc.) so they participate in the same graded ranking; typically they rank below well-provisioned cloud models but above "no model."

## Model skills and API inference model skills

- **Task types** (e.g. `TaskType.REASONING`, `CODE_GENERATION`, `SIMPLE_CHAT`) define the kind of work. Each model has **task_scores** per task type (in `models/*.yaml` or handler catalog).
- **API inference model skills** are the same task_scores exposed to the API: they drive which model is chosen for a given purpose (e.g. `/api/...` requesting "reasoning" or "code").
- **Ollama models** in `models/ollama.yaml` (or equivalent) must define **task_scores** so they are part of the graded hierarchy; defaults are applied when not specified (e.g. generalist 0.6–0.7 so Ollama remains usable but ranks below specialized cloud models when available).

## Ollama as failsafe and fallback

- **Always available when running:** Ollama does not require an API key; when the Ollama server is reachable (primary or fallback URL from `models/ollama.yaml`), it can always be used.
- **Fallback chain:** `ModelRegistry` (or a resilient generate helper) should try: **primary handler for purpose** → on failure (rate limit, 429, 500, timeout, or null/error response) → **next in hierarchy** → … → **Ollama** last. This implements the graded inference hierarchy at call time.
- **Graceful handler behavior:** Handlers (including `OllamaHandler`) return `None` or an error string on failure. Callers that implement fallback treat `None` or `response.startswith("Error:")` as failure and try the next handler; **Ollama as last** ensures at least one attempt with local inference.

## Rate limiting and errors (resilience)

- **Rate limiter:** Scripts and handlers use a shared rate limiter (e.g. `DualLayerRateLimiter`) so that 429s are avoided where possible; when a 429 occurs, the caller can retry with backoff or **fall back to the next tier (including Ollama)**.
- **Diverse errors:** 500, timeout, connection errors, and "no quota" are handled so that the mission continues (e.g. skip that model, try next provider, finally Ollama).

## Configuration checklist

- **Ollama enabled:** In `mindx_config.json` (or merged config), `llm.ollama.enabled: true` so the registry loads the Ollama handler and its models.
- **Ollama URLs:** `models/ollama.yaml` defines `base_url` (primary) and `fallback_url`; config exposes `llm.ollama.base_url` and `llm.ollama.fallback_url` for `api/ollama` and `llm_factory`.
- **Provider order:** `default_provider_preference_order` should list cloud providers first and **Ollama last** for "best model" selection; Ollama remains explicitly selectable (e.g. `create_llm_handler(provider_name="ollama")`).
- **Task scores for Ollama:** Each Ollama model in the catalog should have `task_scores` (or defaults) so the ModelSelector can rank them in the same hierarchy as API inference model skills.

## No inference connection: install and configure Ollama (Linux)

When **no inference connection is found** (all providers fail and Ollama at primary/fallback URL is unreachable), mindX can **install and configure a working Ollama** on Linux and **continue self-improvement from core**.

- **Separate folder:** `llm/ollama_bootstrap/` holds scripts and logic for this scenario.
- **Linux script:** `llm/ollama_bootstrap/aion.sh`:
  1. Installs Ollama via the official one-liner: `curl -fsSL https://ollama.com/install.sh | sh`
  2. Optionally starts `ollama serve` in the background (`--serve`)
  3. Waits for the API at `http://127.0.0.1:11434` (or `$OLLAMA_HOST`)
  4. Pulls a default model (e.g. `llama3.2`) so mindX has a working model
- **Usage:** From project root: `./llm/ollama_bootstrap/aion.sh` or `./llm/ollama_bootstrap/aion.sh --pull-model llama3.2 --serve`
- **Python:** `llm.ollama_bootstrap.ensure_ollama_available()` checks base_url/fallback_url; if none reachable and platform is Linux, runs `aion.sh` and rechecks so inference can continue.
- **After bootstrap:** mindX uses `models/ollama.yaml` **fallback_url** `http://localhost:11434`; no code change needed. `generate_with_fallback` or explicit Ollama handler then succeeds and self-improvement continues from core.

See **`llm/ollama_bootstrap/README.md`** for manual install, Docker, model library, REST API, and links (ollama-python, ollama-js, Community).

## Path forward

1. **Verify:** Ensure `models/ollama.yaml` and config merge expose Ollama models with task_scores; ensure ModelRegistry loads them (including list-style model entries).
2. **Run:** Use resilient generate (e.g. `generate_with_fallback`) in agents so that primary → … → Ollama is tried on each inference when desired.
3. **No connection:** On Linux, use `llm/ollama_bootstrap/aion.sh` or `ensure_ollama_available()` to install and configure Ollama, then continue.
4. **Observe:** Rate limiting, fallback to Ollama, and mission completion despite partial cloud failures (or no connection → bootstrap → continue) demonstrate resilience and perpetuity.

This design makes Ollama the **failsafe and fallback** inference layer and aligns the **llm** folder with a **graded inference hierarchy** of model skills and API inference model skills across the project.
