# Ollama Complete Reference — Local Documentation for mindX

> Self-contained reference for all [Ollama](https://ollama.com) capabilities.
> No external docs needed — resilient offline operation.
> Source: [docs.ollama.com](https://docs.ollama.com/) (fetched 2026-04-11) + mindX integration specifics.
>
> **[Back to mindX Documentation Hub](../NAV.md)**

## Operational Standards

mindX operates from **two inference pillars** — both are operational standards, not fallbacks:

| Pillar | Source | Speed | Model Scale | Availability | Cost |
|--------|--------|-------|-------------|--------------|------|
| **CPU inference** | [`localhost:11434`](setup/getting_started.md) | ~8 tok/s | 0.6B–1.7B | Always (no network) | Zero |
| **Cloud inference** | [`ollama.com`](cloud/cloud.md) via [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) | ~65 tok/s | 3B–1T | 24/7/365 (free tier) | Zero |

CPU provides **autonomy** — mindX reasons even offline, even when every API key is exhausted. Cloud provides **scale** — 120B+ parameter models on NVIDIA GPUs, [8.2x faster](#latest-benchmark-2026-04-11) than local CPU. Together they form the [resilience guarantee](#resilience-design): mindX never stops inferring.

The [5-step resolution chain](#resilience-design) in [`_resolve_inference_model()`](../../agents/core/mindXagent.py) tries the best available source first and walks down to guarantee. CPU is the failsafe. Cloud is the guarantee. Both are always ready.

---

## Quick Navigation

### API Reference

| Endpoint | Local | Cloud | Doc |
|----------|-------|-------|-----|
| `POST /api/generate` | [`localhost:11434`](setup/getting_started.md) | [`ollama.com`](cloud/cloud.md) | [generate.md](api/generate.md) |
| `POST /api/chat` | [`localhost:11434`](setup/getting_started.md) | [`ollama.com`](cloud/cloud.md) | [chat.md](api/chat.md) |
| `POST /api/embed` | [`localhost:11434`](setup/getting_started.md) | [`ollama.com`](cloud/cloud.md) | [embeddings.md](api/embeddings.md) |
| Model management | [`localhost:11434`](setup/getting_started.md) | — | [models.md](api/models.md) |
| `GET /api/ps`, `/api/version` | [`localhost:11434`](setup/getting_started.md) | — | [running.md](api/running.md) |

All endpoints documented with every parameter, response field, and curl/[Python](sdk/python.md)/[JavaScript](sdk/javascript.md) examples. See the [Ollama OpenAPI spec](https://docs.ollama.com/openapi.yaml) for the authoritative schema.

### Features

Each feature doc includes curl, [Python SDK](sdk/python.md), [JavaScript SDK](sdk/javascript.md), and mindX-specific code examples. All features work identically on both [CPU](setup/getting_started.md) and [Cloud](cloud/cloud.md) pillars.

- [Streaming](features/streaming.md) — Real-time token-by-token output via [/api/chat](api/chat.md) and [/api/generate](api/generate.md); extends [`OllamaAPI`](../../api/ollama/ollama_url.py) which currently uses `stream=False`
- [Thinking](features/thinking.md) — Chain-of-thought reasoning with the `think` parameter; [supported models](https://ollama.com/search?c=thinking) include [DeepSeek R1](https://ollama.com/library/deepseek-r1) (local) and [GPT-OSS](https://ollama.com/library/gpt-oss) (cloud, levels: `"low"`/`"medium"`/`"high"`)
- [Structured Outputs](features/structured_outputs.md) — JSON schema-constrained generation via the `format` parameter; works with [Pydantic](https://docs.pydantic.dev/) and [Zod](https://zod.dev/); used by [BDI reasoning](../../agents/core/bdi_agent.py) for structured state extraction
- [Vision](features/vision.md) — Image understanding with [multimodal models](https://ollama.com/search?c=vision); cloud models [gemma4](https://ollama.com/library/gemma4), [kimi-k2.5](https://ollama.com/library/kimi-k2.5) support vision
- [Embeddings](features/embeddings.md) — Vector embeddings for [RAGE](../../docs/AGINT.md) semantic search and [pgvector](https://github.com/pgvector/pgvector) storage; mindX uses [`mxbai-embed-large`](https://ollama.com/library/mxbai-embed-large) and [`nomic-embed-text`](https://ollama.com/library/nomic-embed-text)
- [Tool Calling](features/tool_calling.md) — Function calling / tool use; single, parallel, and [agent loop](features/tool_calling.md#multi-turn-agent-loop) patterns; bridges to mindX [`BaseTool`](../../agents/core/bdi_agent.py) via [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py)
- [Web Search](features/web_search.md) — Grounded generation via [Ollama web search API](https://ollama.com/api/web_search); requires [OLLAMA_API_KEY](cloud/cloud.md#authentication); available as [`OllamaCloudTool.execute(operation="web_search")`](../../tools/cloud/ollama_cloud_tool.py)

### Cloud & Infrastructure

- [Ollama Cloud](cloud/cloud.md) — Free/Pro/Max tiers, [API keys](https://ollama.com/settings/keys), [cloud models](https://ollama.com/search?c=cloud), [local offload](#the--cloud-suffix) vs [direct API](#three-access-paths); the cloud [operational pillar](#operational-standards)
- [Cloud Model Search](cloud/model_search.md) — Programmatic discovery via [`/api/tags`](api/models.md) and `OllamaCloudModelDiscovery` class; feeds into [Modelfile schema](#modelfile-as-canonical-schema) and [Chimaiera](../../docs/MANIFESTO.md) alignment; the [`-cloud` suffix](#the--cloud-suffix) distinction
- [Cloud Rate Limiting](cloud/rate_limiting.md) — `CloudRateLimiter` embedded in [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) with adaptive pacing (3s–30s); uses [actual token counts](mindx/precision_metrics.md) from [Ollama API](api/chat.md#response-fields); integrates with [`rate_limiter.py`](../../llm/rate_limiter.py)
- [OpenAI Compatibility](cloud/openai_compat.md) — Drop-in replacement at `/v1/chat/completions`; works with [OpenAI Python SDK](https://github.com/openai/openai-python) and [OpenAI JS SDK](https://github.com/openai/openai-node); base URL `localhost:11434/v1/` for [CPU pillar](#operational-standards), `ollama.com/v1/` for [cloud pillar](#operational-standards)

### SDKs

- [Python SDK](sdk/python.md) — [`ollama`](https://github.com/ollama/ollama-python) library (PyPI); sync, async, [cloud client](sdk/python.md#cloud-client), auto-parsed [tool schemas](sdk/python.md#tool-calling-functions-as-tools); mindX uses `aiohttp` directly via [`OllamaAPI`](../../api/ollama/ollama_url.py) for maximum control
- [JavaScript SDK](sdk/javascript.md) — [`ollama`](https://github.com/ollama/ollama-js) library (npm); browser, Node.js, [cloud](sdk/javascript.md#cloud-api), [abort](sdk/javascript.md#abort); used by [mindX frontend](../../mindx_frontend_ui/)

### Setup & Operations

- [Getting Started](setup/getting_started.md) — Installation on [Linux](https://docs.ollama.com/linux), [macOS](https://ollama.com/download), [Windows](https://ollama.com/download); first model pull; mindX quick setup for the [CPU pillar](#operational-standards)
- [GPU Support](setup/gpu.md) — [NVIDIA](https://developer.nvidia.com/cuda-gpus) (CC 5.0+), [AMD ROCm](https://rocm.docs.amd.com/), [Apple Metal](https://developer.apple.com/metal/), [Vulkan](https://www.vulkan.org/) (experimental); the [10.0.0.155 GPU server](mindx/architecture.md) when online
- [Docker](setup/docker.md) — CPU, NVIDIA, AMD, Vulkan containers; [Docker Hub](https://hub.docker.com/r/ollama/ollama); Compose with mindX
- [Modelfile](setup/modelfile.md) — Custom model creation; **canonical schema** for model collection, rating, and [agent-model alignment](#modelfile-as-canonical-schema) toward [Chimaiera](../../docs/MANIFESTO.md)
- [FAQ & Troubleshooting](setup/faq.md) — Context window, [keep_alive](api/generate.md), [Flash Attention](setup/faq.md#flash-attention), [KV cache quantization](setup/faq.md#kv-cache-quantization), [concurrency](setup/faq.md#concurrency), [VPS production notes](setup/faq.md#mindx-production-notes-from-deployment-at-mindxpythainet)

### mindX Integration

- **[OllamaCloudTool](../../tools/cloud/ollama_cloud_tool.py)** — **First-class [`BaseTool`](../../agents/core/bdi_agent.py)** for the [cloud pillar](#operational-standards). Any agent can `execute(operation="chat", model="deepseek-v3.2", message="...")`. [Dual access](#three-access-paths) (local proxy + direct API), embedded [`CloudRateLimiter`](cloud/rate_limiting.md), [18dp precision metrics](mindx/precision_metrics.md), [conversation history](cloud/cloud.md), branch-ready. Registered in [`augmentic_tools_registry.json`](../../data/config/augmentic_tools_registry.json) with `access_control: ["*"]`. Wired into [`_resolve_inference_model()`](#resilience-design) as Step 5 (guarantee).
- [Architecture](mindx/architecture.md) — Integration layer diagram; [`OllamaAPI`](../../api/ollama/ollama_url.py) → [`OllamaChatManager`](../../agents/core/ollama_chat_manager.py) → [`LLMFactory`](../../llm/llm_factory.py) → [`InferenceDiscovery`](../../llm/inference_discovery.py); [5-step resilience chain](mindx/architecture.md#resilience-chain-from-llmresiliencemd); [cloud offload](mindx/architecture.md#cloud-offload-via--cloud-suffix)
- [Configuration](mindx/configuration.md) — `MINDX_LLM__OLLAMA__BASE_URL` ([CPU pillar](#operational-standards)), `OLLAMA_API_KEY` ([cloud pillar](#operational-standards)), [`models/ollama.yaml`](../../models/ollama.yaml), [BANKON vault](../../mindx_backend_service/vault_bankon/), [`llm_factory_config.json`](../../data/config/llm_factory_config.json)
- [Precision Metrics](mindx/precision_metrics.md) — [`llm/precision_metrics.py`](../../llm/precision_metrics.py): 18-decimal-place scientific tracking; `Decimal` accumulation; [actual counts only](mindx/precision_metrics.md#what-was-removed); separate cloud file at `data/metrics/cloud_precision_metrics.json`
- [Capability Examples](mindx/capability_examples.py) — Working Python code for all 10 capabilities: [streaming](features/streaming.md), [thinking](features/thinking.md), [structured outputs](features/structured_outputs.md), [vision](features/vision.md), [embeddings](features/embeddings.md), [tool calling](features/tool_calling.md), [web search](features/web_search.md), [cloud](cloud/cloud.md), model management, rate-limited cloud client

### Test & Benchmarking

- [`scripts/test_cloud_all_models.py`](../../scripts/test_cloud_all_models.py) — **Primary benchmark**: single prompt to every model, [precision metrics](mindx/precision_metrics.md) (18dp `Decimal`), actual `eval_count`/`eval_duration` from [Ollama API](api/chat.md#response-fields); see [Latest Benchmark](#latest-benchmark-2026-04-11) and [How Cloud Works Without an API Key](#how-cloud-works-without-an-api-key)
- [`scripts/test_cloud_inference.py`](../../scripts/test_cloud_inference.py) — Original multi-source benchmark (local + cloud + vLLM)
- [`scripts/test_ollama_connection.py`](../../scripts/test_ollama_connection.py) — Connection test using [`OllamaAPI`](../../api/ollama/ollama_url.py)

### Existing mindX Ollama Docs (pre-2026-04-11)

- [`docs/ollama_api_integration.md`](../ollama_api_integration.md) — Original [API compliance](api/generate.md) notes (timeouts, [keep_alive](api/generate.md), token counting)
- [`docs/ollama_integration.md`](../ollama_integration.md) — Custom client ([`OllamaAPI`](../../api/ollama/ollama_url.py)) vs official library ([Python SDK](sdk/python.md))
- [`docs/ollama_model_capability_tool.md`](../ollama_model_capability_tool.md) — [Model discovery](cloud/model_search.md) and capability registration
- [`docs/OLLAMA_VLLM_CLOUD_RESEARCH.md`](../OLLAMA_VLLM_CLOUD_RESEARCH.md) — [Cloud](cloud/cloud.md) + vLLM research (2026-04-10); established the [dual-pillar](#operational-standards) strategy
- [`llm/RESILIENCE.md`](../../llm/RESILIENCE.md) — Graded inference hierarchy: Primary → Secondary → Failsafe ([CPU](#operational-standards)) → Guarantee ([Cloud](#operational-standards))

---

## Latest Benchmark (2026-04-11)

Prompt: *"You are mindX. In one sentence, describe what you are."*
Script: [`test_cloud_all_models.py`](../../scripts/test_cloud_all_models.py) | Results: [`data/cloud_test_results.json`](../../data/cloud_test_results.json)

| Model | Pillar | eval | prompt | total | tok/s | wall_ms | total_ms |
|-------|--------|------|--------|-------|-------|---------|----------|
| [`gpt-oss:120b-cloud`](https://ollama.com/library/gpt-oss) | [Cloud](#operational-standards) | 67 | 81 | 148 | 65.52 | 1,214 | 1,022 |
| [`deepseek-r1:1.5b`](https://ollama.com/library/deepseek-r1) | [CPU](#operational-standards) | 79 | 17 | 96 | 8.00 | 16,294 | 16,291 |
| [`deepseek-coder:latest`](https://ollama.com/library/deepseek-coder) | [CPU](#operational-standards) | 72 | 83 | 155 | 7.29 | 22,569 | 22,565 |

**Aggregate** (all values ACTUAL from [Ollama API](api/chat.md#response-fields), [18dp precision](mindx/precision_metrics.md)):
- Total tokens: **399** (218 eval + 181 prompt) = `399000000000000000000` [sub-tokens](mindx/precision_metrics.md)
- Aggregate throughput: **11.03** tok/s (`11.033658223708593293` at 18dp)
- Cloud vs CPU speedup: **8.2x** (65.52 vs ~7.6 tok/s) — [120B cloud GPU](cloud/cloud.md) vs [1.5B local CPU](setup/faq.md#mindx-production-notes-from-deployment-at-mindxpythainet)

### Cloud Timing Note

Cloud-proxied models ([`gpt-oss:120b-cloud`](https://ollama.com/library/gpt-oss)) return `eval_duration_ns: 0` — the [local offload proxy](#the--cloud-suffix) does not expose per-stage timing from the remote GPU. The `total_duration_ns` is used for tok/s calculation instead. [CPU pillar](#operational-standards) models return all duration fields. See [`test_cloud_all_models.py`](../../scripts/test_cloud_all_models.py) line 114 for the fallback logic.

### 36 Additional Cloud Models Available

The [cloud catalog](https://ollama.com/search?c=cloud) lists 36 models at [`ollama.com/api/tags`](https://ollama.com/api/tags). To test them:

```bash
# Option A: Pull with -cloud suffix for free-tier proxy (metadata only, no weights)
ollama pull deepseek-v3.2-cloud
python3 scripts/test_cloud_all_models.py --local

# Option B: Set API key for direct cloud access to all 36 models
export OLLAMA_API_KEY=your_key
python3 scripts/test_cloud_all_models.py
```

---

## How Cloud Works Without an API Key

[`test_cloud_inference.py`](../../scripts/test_cloud_inference.py) and [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) return cloud model responses without `OLLAMA_API_KEY` because of Ollama's **local offload** architecture:

### The `-cloud` Suffix

**Model names with `-cloud` appended** (e.g., `gpt-oss:120b-cloud`) are metadata-only pulls that proxy inference to `ollama.com`. Without the suffix (e.g., `gpt-oss:120b`), `ollama pull` downloads the **full model weights** (gigabytes) for [CPU pillar](#operational-standards) execution.

The [cloud catalog](https://ollama.com/api/tags) returns names without `-cloud`. Append it for [free-tier local proxy](cloud/cloud.md):

```bash
ollama pull gpt-oss:120b-cloud      # metadata only → inference proxied to cloud
ollama pull deepseek-v3.2-cloud     # metadata only → inference proxied to cloud
# vs
ollama pull gemma3:4b               # downloads 3.3GB weights for local CPU execution
```

### The Mechanism

1. **`ollama pull gpt-oss:120b-cloud`** downloads metadata (not weights) to the local daemon
2. **`ollama run gpt-oss:120b-cloud`** sends the request to [`localhost:11434`](setup/getting_started.md) like any local model
3. The **local Ollama daemon** detects the `-cloud` tag and transparently proxies to [`ollama.com`](cloud/cloud.md)
4. Authentication is handled by the daemon using credentials from **`ollama signin`** (stored at `~/.ollama/id_ed25519`; see [FAQ](setup/faq.md#where-can-i-find-my-ollama-public-key))
5. [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) calls `localhost:11434/api/chat` — **no Bearer token needed** because the local daemon is the auth proxy

```
Agent → OllamaCloudTool.execute(operation="chat") → _try_local_proxy()
    → localhost:11434/api/chat (model-cloud) → local Ollama daemon
                                                  ↓ (transparent proxy)
                                             ollama.com (auth via ed25519 key)
                                                  ↓
                                             Cloud GPU inference
                                                  ↓
Agent ← result (eval_count, tokens_per_sec, 18dp) ← ollama.com
```

### Three Access Paths

| Path | URL | Auth | Pull | When | Tool Method |
|------|-----|------|------|------|-------------|
| **Local offload** | `localhost:11434` | None (daemon) | `ollama pull model-cloud` | Free tier, no key | [`_try_local_proxy()`](../../tools/cloud/ollama_cloud_tool.py) |
| **Direct API** | `ollama.com/api/chat` | `Bearer $OLLAMA_API_KEY` | None needed | Key set | [`_try_direct_cloud()`](../../tools/cloud/ollama_cloud_tool.py) |
| **Local execution** | `localhost:11434` | None | `ollama pull model` (full weights) | Always offline | [`OllamaAPI`](../../api/ollama/ollama_url.py) |

[`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) in `auto` mode tries local proxy first, then direct cloud — matching the [dual-pillar](#operational-standards) design.

### Why `/api/tags` Works Without Auth

The [model listing endpoint](api/models.md) at `https://ollama.com/api/tags` is **publicly accessible** — it lists available cloud models for discovery. This is how [`test_cloud_all_models.py`](../../scripts/test_cloud_all_models.py), [`OllamaCloudTool.list_models`](../../tools/cloud/ollama_cloud_tool.py), and [`OllamaCloudModelDiscovery`](cloud/model_search.md) discover available models without authentication.

### Free Tier Limits

| Limit | Value | Reset | Tracked By |
|-------|-------|-------|------------|
| Session | Light usage | Every 5 hours | [`CloudRateLimiter`](../../tools/cloud/ollama_cloud_tool.py) in [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) |
| Weekly | Light usage | Every 7 days | [`CloudQuotaTracker`](../../tools/cloud/ollama_cloud_tool.py) |
| Concurrent cloud models | 1 | — | Ollama server-side |

See [Cloud Rate Limiting](cloud/rate_limiting.md) for the adaptive pacing strategy (3s–30s based on [quota utilization](cloud/rate_limiting.md)) that maximizes throughput within these limits using [actual token counts](mindx/precision_metrics.md).

---

## Modelfile as Canonical Schema

The [Ollama Modelfile](setup/modelfile.md) is mindX's canonical schema for model collection and rating across both [pillars](#operational-standards):

| Instruction | Maps To | mindX Component |
|-------------|---------|-----------------|
| [`FROM`](setup/modelfile.md#from-required) | Base architecture/weights | [`models/ollama.yaml`](../../models/ollama.yaml) `models[].name` |
| [`PARAMETER`](setup/modelfile.md#parameter) | Operational characteristics | [`models/ollama.yaml`](../../models/ollama.yaml) `model_selection` |
| [`TEMPLATE`](setup/modelfile.md#template) | Communication protocol | [Go template syntax](setup/modelfile.md#template) |
| [`SYSTEM`](setup/modelfile.md#system) | Cognitive identity | Agent system prompts in [`BDIAgent`](../../agents/core/bdi_agent.py) |
| Capabilities | Dynamic from [`/api/show`](api/models.md#show-model-details--post-apishow) | [`OllamaCloudModelDiscovery`](cloud/model_search.md) |

This feeds into:
1. [`HierarchicalModelScorer`](../../agents/core/model_scorer.py) — learned task_scores from [precision metrics](mindx/precision_metrics.md) feedback
2. [`OllamaCloudModelDiscovery`](cloud/model_search.md) — dynamic capability detection across both [CPU](setup/getting_started.md) and [cloud](cloud/cloud.md) models
3. [`InferenceDiscovery`](../../llm/inference_discovery.py) — provider routing with [cloud guarantee](#resilience-design) fallback
4. Agent-model alignment toward [Chimaiera](../../docs/MANIFESTO.md) (the ROI moment when model composition outperforms single-model inference)

See [Modelfile Reference](setup/modelfile.md) for the full instruction set and [Chimaiera alignment section](setup/modelfile.md#from-modelfile-to-agent-alignment).

---

## Precision Metrics

Token tracking at 18 decimal places using Python `Decimal`. No floating-point drift. No estimation. Applied identically to both [CPU](#operational-standards) and [Cloud](#operational-standards) pillars.

| What | Before | After | Module |
|------|--------|-------|--------|
| Token counts | `word_count * 1.3` | `eval_count` from [Ollama API](api/chat.md#response-fields) | [`precision_metrics.py`](../../llm/precision_metrics.py) |
| Timing | `float` milliseconds | `int` nanoseconds (Ollama native) | [`OllamaResponseMetrics`](../../llm/precision_metrics.py) |
| Accumulation | `float` (compounding drift) | `Decimal` (28-digit significand) | [`PrecisionAccumulator`](../../llm/precision_metrics.py) |
| Sub-token unit | none | 1 token = 10^18 sub-tokens ([wei](https://ethereum.org/en/developers/docs/intro-to-ether/#denominations) equivalent) | [`SUBTOKEN_FACTOR`](../../llm/precision_metrics.py) |
| Cloud tok/s | not tracked | `eval_count / total_duration_ns` ([cloud proxy returns `eval_duration: 0`](#cloud-timing-note)) | [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) |

Local metrics: `data/metrics/precision_metrics.json` (via [`OllamaAPI`](../../api/ollama/ollama_url.py))
Cloud metrics: `data/metrics/cloud_precision_metrics.json` (via [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py))

Full docs: [Precision Metrics](mindx/precision_metrics.md).

---

## Resilience Design

The [5-step resolution chain](../../agents/core/mindXagent.py) in `_resolve_inference_model()` ensures mindX always has inference when any network path is available:

```
Step 1: InferenceDiscovery → best provider (Gemini, Mistral, Groq, etc.)
          ↓ all keys exhausted or rate limited
Step 2: OllamaChatManager → local model selection (HierarchicalModelScorer)
          ↓ connection stale or failed
Step 3: Re-init OllamaChatManager → retry with fresh connection
          ↓ still failing
Step 4: Direct HTTP → localhost:11434/api/tags (zero dependencies)
          ↓ local Ollama completely down
Step 5: OllamaCloudTool → ollama.com GPU inference ← GUARANTEE (24/7/365)
          ↓ cloud also unreachable (network down)
     → None → fallback_decide() rule-based heuristics → 2-min backoff
```

| Tier | Role | Provider | Speed | mindX Component |
|------|------|----------|-------|-----------------|
| Primary | Best quality | Gemini, Mistral | Varies | [`LLMFactory`](../../llm/llm_factory.py) |
| Secondary | Speed/cost | Groq, Together | Fast | [`LLMFactory`](../../llm/llm_factory.py) |
| **Failsafe** | **CPU pillar** | [Ollama local](setup/getting_started.md) (`localhost:11434`) | ~8 tok/s | [`OllamaChatManager`](../../agents/core/ollama_chat_manager.py) |
| **Guarantee** | **Cloud pillar** | [Ollama Cloud](cloud/cloud.md) (`ollama.com`) | ~65 tok/s | [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) |
| Last resort | No inference | — | — | [`fallback_decide()`](../../llm/inference_discovery.py) rule-based |

**Cloud is guarantee, not default.** The `_cloud_inference_active` flag in [`mindXagent.py`](../../agents/core/mindXagent.py) routes one chat through [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py), then resets so the next cycle tries local first. This preserves [CPU pillar](#operational-standards) autonomy while ensuring the [cloud pillar](#operational-standards) catches every gap.

**[`InferenceDiscovery.get_provider_for_task()`](../../llm/inference_discovery.py)** routes tasks through the same hierarchy: preferred provider → [`ollama_local`](setup/getting_started.md) → [`ollama_cloud`](cloud/cloud.md) → any available → `None`.

Implementation: [`_resolve_inference_model()`](../../agents/core/mindXagent.py) (5 steps) → [`InferenceDiscovery`](../../llm/inference_discovery.py) (provider probing + cloud fallback) → [`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py) (cloud guarantee) → [`RESILIENCE.md`](../../llm/RESILIENCE.md) (graded hierarchy docs) → [`chat_with_ollama()`](../../agents/core/mindXagent.py) (cloud routing when active).

---

## mindX File Map

### Core Ollama Integration

| File | Role | Doc | Pillar |
|------|------|-----|--------|
| **[`tools/cloud/ollama_cloud_tool.py`](../../tools/cloud/ollama_cloud_tool.py)** | **[OllamaCloudTool](#operational-standards) — cloud inference for any agent** | This page | Cloud |
| [`api/ollama/ollama_url.py`](../../api/ollama/ollama_url.py) | HTTP API client, [rate limiter](../../llm/rate_limiter.py), [precision metrics](../../llm/precision_metrics.py), [failover](mindx/architecture.md) | [Architecture](mindx/architecture.md) | CPU |
| [`agents/core/ollama_chat_manager.py`](../../agents/core/ollama_chat_manager.py) | Connection manager, [model discovery](cloud/model_search.md), conversation history | [Architecture](mindx/architecture.md) | CPU |
| [`agents/core/mindXagent.py`](../../agents/core/mindXagent.py) | [5-step resolution chain](#resilience-design), [cloud routing](#resilience-design), autonomous loop | [Architecture](mindx/architecture.md) | Both |
| [`llm/ollama_handler.py`](../../llm/ollama_handler.py) | [`LLMFactory`](../../llm/llm_factory.py) handler interface | [Architecture](mindx/architecture.md) | CPU |
| [`llm/llm_factory.py`](../../llm/llm_factory.py) | Master factory, provider selection | [Configuration](mindx/configuration.md) | Both |
| [`llm/rate_limiter.py`](../../llm/rate_limiter.py) | Token-bucket rate limiting | [Cloud Rate Limiting](cloud/rate_limiting.md) | Both |
| [`llm/precision_metrics.py`](../../llm/precision_metrics.py) | 18dp scientific token tracking | [Precision Metrics](mindx/precision_metrics.md) | Both |
| [`llm/inference_discovery.py`](../../llm/inference_discovery.py) | Boot-time probe, [task routing](../../llm/inference_discovery.py), [cloud guarantee](#resilience-design) | [Architecture](mindx/architecture.md) | Both |
| [`models/ollama.yaml`](../../models/ollama.yaml) | Model registry, [task scores](setup/modelfile.md), [cloud config](mindx/configuration.md) | [Configuration](mindx/configuration.md) | Both |
| [`api/ollama/ollama_admin_routes.py`](../../api/ollama/ollama_admin_routes.py) | Admin endpoints (status, test, models) | [FAQ](setup/faq.md) | CPU |
| [`agents/core/model_scorer.py`](../../agents/core/model_scorer.py) | [`HierarchicalModelScorer`](../../agents/core/model_scorer.py) | [Modelfile Schema](#modelfile-as-canonical-schema) | Both |
| [`agents/core/inference_optimizer.py`](../../agents/core/inference_optimizer.py) | Sliding-scale frequency optimization | [Architecture](mindx/architecture.md) | CPU |

### Test Scripts

| File | Purpose | Pillar |
|------|---------|--------|
| [`scripts/test_cloud_all_models.py`](../../scripts/test_cloud_all_models.py) | Primary: every model, [precision metrics](mindx/precision_metrics.md), 18dp `Decimal` | Both |
| [`scripts/test_cloud_inference.py`](../../scripts/test_cloud_inference.py) | Original: local + cloud + vLLM comparison | Both |
| [`scripts/test_ollama_connection.py`](../../scripts/test_ollama_connection.py) | Connection test via [`OllamaAPI`](../../api/ollama/ollama_url.py) | CPU |
| [`data/cloud_test_results.json`](../../data/cloud_test_results.json) | Latest benchmark results (JSON, [18dp](mindx/precision_metrics.md)) | Both |

---

## External References

| Resource | URL | Relevance |
|----------|-----|-----------|
| Ollama Homepage | [ollama.com](https://ollama.com) | [Both pillars](#operational-standards) |
| Ollama Docs | [docs.ollama.com](https://docs.ollama.com/) | API reference source |
| Ollama API (OpenAPI) | [docs.ollama.com/openapi.yaml](https://docs.ollama.com/openapi.yaml) | [API docs](api/generate.md) source |
| Ollama GitHub | [github.com/ollama/ollama](https://github.com/ollama/ollama) | [Setup](setup/getting_started.md) |
| Python SDK | [github.com/ollama/ollama-python](https://github.com/ollama/ollama-python) | [SDK docs](sdk/python.md) |
| JavaScript SDK | [github.com/ollama/ollama-js](https://github.com/ollama/ollama-js) | [SDK docs](sdk/javascript.md) |
| Cloud Models | [ollama.com/search?c=cloud](https://ollama.com/search?c=cloud) | [Cloud pillar](#operational-standards) catalog |
| Thinking Models | [ollama.com/search?c=thinking](https://ollama.com/search?c=thinking) | [Thinking](features/thinking.md) feature |
| Vision Models | [ollama.com/search?c=vision](https://ollama.com/search?c=vision) | [Vision](features/vision.md) feature |
| Tool Models | [ollama.com/search?c=tools](https://ollama.com/search?c=tools) | [Tool Calling](features/tool_calling.md) feature |
| Model Library | [ollama.com/library](https://ollama.com/library) | [Modelfile](setup/modelfile.md) reference |
| API Keys | [ollama.com/settings/keys](https://ollama.com/settings/keys) | [Cloud auth](cloud/cloud.md#authentication) |
| Discord | [discord.gg/ollama](https://discord.gg/ollama) | Community |
| Docker Hub | [hub.docker.com/r/ollama/ollama](https://hub.docker.com/r/ollama/ollama) | [Docker](setup/docker.md) setup |
| OllamaFreeAPI | [github.com/mfoud444/ollamafreeapi](https://github.com/mfoud444/ollamafreeapi) | Community gateway |
| mindX Production | [mindx.pythai.net](https://mindx.pythai.net) | Live [CPU pillar](#operational-standards) |
| mindX Thesis | [`docs/THESIS.md`](../../docs/THESIS.md) | Darwin-Godel Machine synthesis |
| mindX Manifesto | [`docs/MANIFESTO.md`](../../docs/MANIFESTO.md) | [Chimaiera](#modelfile-as-canonical-schema) roadmap |
| RAGE | [`docs/AGINT.md`](../../docs/AGINT.md) | [Embeddings](features/embeddings.md) architecture |

---

## Version Info

- **Ollama docs**: Fetched 2026-04-11 from [docs.ollama.com](https://docs.ollama.com/)
- **Operational standards**: [CPU](#operational-standards) ([`OllamaAPI`](../../api/ollama/ollama_url.py) + [`OllamaChatManager`](../../agents/core/ollama_chat_manager.py)) + [Cloud](#operational-standards) ([`OllamaCloudTool`](../../tools/cloud/ollama_cloud_tool.py))
- **Resilience**: [5-step chain](#resilience-design) in [`_resolve_inference_model()`](../../agents/core/mindXagent.py) with cloud [guarantee](#resilience-design)
- **Precision**: [18dp `Decimal`](mindx/precision_metrics.md) via [`precision_metrics.py`](../../llm/precision_metrics.py), [actual counts](mindx/precision_metrics.md#what-was-removed) from [Ollama API](api/chat.md#response-fields)
- **Production**: [mindx.pythai.net](https://mindx.pythai.net) (4GB VPS, [CPU pillar](#operational-standards), dual-URL failover)
- **Benchmark**: [2026-04-11](#latest-benchmark-2026-04-11) — 3 models, 399 tokens, cloud [8.2x faster](#latest-benchmark-2026-04-11) than CPU
- **28 files, ~6,000 lines** — self-contained for resilient offline operation
