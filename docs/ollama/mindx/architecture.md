# mindX Ollama Architecture

> How mindX uses Ollama — from production deployment at mindx.pythai.net to local development.

## Integration Layer

```
┌─────────────────────────────────────────────────────────────┐
│                   mindX Agent Layer                          │
│  MindXAgent · BlueprintAgent · AuthorAgent · CEOAgent       │
│                                                              │
│  ┌────────────────────┐  ┌──────────────────────────────┐   │
│  │ OllamaChatManager  │  │ InferenceDiscovery           │   │
│  │ (agents/core/)     │  │ (llm/inference_discovery.py) │   │
│  │                    │  │                               │   │
│  │ • Model discovery  │  │ • Probes all sources at boot │   │
│  │ • Best model select│  │ • Validates before each cycle│   │
│  │ • Chat history     │  │ • Feeds HierarchicalScorer   │   │
│  │ • Auto-retry       │  │                               │   │
│  └────────┬───────────┘  └──────────────┬───────────────┘   │
│           │                              │                    │
│  ┌────────┴──────────────────────────────┴───────────────┐   │
│  │              OllamaAPI (api/ollama/ollama_url.py)      │   │
│  │                                                        │   │
│  │  • /api/generate and /api/chat endpoints               │   │
│  │  • Token-bucket rate limiter (1000 RPM local)          │   │
│  │  • Dual-URL failover (primary → fallback)              │   │
│  │  • 120s timeout, keep_alive, format, think support     │   │
│  │  • Actual token counting from API response             │   │
│  └───────────┬────────────────────────┬──────────────────┘   │
│              │                        │                       │
│  ┌───────────┴───────┐  ┌────────────┴──────────────────┐   │
│  │ OllamaHandler     │  │ LLMFactory                    │   │
│  │ (llm/ollama_      │  │ (llm/llm_factory.py)          │   │
│  │  handler.py)      │  │                                │   │
│  │                   │  │ • Provider preference order    │   │
│  │ • LLMHandlerIface │  │ • DualLayerRateLimiter        │   │
│  │ • /api/generate   │  │ • Handler caching              │   │
│  │ • Returns None on │  │ • Ollama = last resort fallback│   │
│  │   failure (→ next) │  │ • Default: phi3:mini          │   │
│  └───────────────────┘  └───────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                    │                    │
        ┌───────────┘                    └──────────┐
        ▼                                           ▼
┌───────────────────┐                    ┌──────────────────┐
│ Primary: GPU      │                    │ Cloud: ollama.com│
│ 10.0.0.155:18080  │                    │ (OLLAMA_API_KEY) │
│ (when available)  │                    │ Free/Pro/Max tier│
└───────────────────┘                    └──────────────────┘
        │ (unreachable?)
        ▼
┌───────────────────┐
│ Fallback: CPU     │
│ localhost:11434   │
│ (always available)│
└───────────────────┘
```

## File Map

| File | Role |
|------|------|
| `api/ollama/ollama_url.py` | HTTP API client, rate limiter, metrics, failover |
| `agents/core/ollama_chat_manager.py` | Connection manager, model discovery, conversation history |
| `llm/ollama_handler.py` | LLMFactory handler interface implementation |
| `llm/llm_factory.py` | Master factory, provider selection, Ollama as fallback |
| `llm/rate_limiter.py` | Token-bucket rate limiting with metrics |
| `llm/inference_discovery.py` | Boot-time probe of all inference sources |
| `models/ollama.yaml` | Model registry with task scores |
| `api/ollama/ollama_admin_routes.py` | Admin endpoints (status, test, generate, models) |
| `api/ollama/ollama_model_capability_tool.py` | Dynamic capability detection |

## Configuration Cascade

```
ENV: MINDX_LLM__OLLAMA__BASE_URL
  → explicit base_url parameter
    → models/ollama.yaml base_url
      → data/config/*.json settings
        → localhost:11434 (default)
```

## Model Selection Hierarchy

1. **HierarchicalModelScorer** — learned from feedback (success rate, latency, token throughput)
2. **Task keyword matching** — chat→mistral/llama, reasoning→nemo/deepseek, coding→codegemma
3. **First available** — whatever's loaded

## Resilience Chain (from [llm/RESILIENCE.md](../../../llm/RESILIENCE.md))

```
_resolve_inference_model() — 5-step chain:

Step 1: InferenceDiscovery → best provider (Gemini, Mistral, Groq, etc.)
Step 2: OllamaChatManager → local model selection
Step 3: Re-init OllamaChatManager → retry with fresh connection
Step 4: Direct HTTP → localhost:11434/api/tags (zero dependencies)
Step 5: OllamaCloudTool → ollama.com GPU inference ← GUARANTEE (24/7/365)
     → None → fallback_decide() → 2-min backoff
```

| Tier | Role | Provider | When |
|------|------|----------|------|
| Primary | Best quality | Gemini, Mistral | First choice |
| Secondary | Speed/cost | Groq, Together | Latency or cost |
| Failsafe | Local fallback | Ollama CPU (`localhost:11434`) | When cloud APIs fail |
| **Guarantee** | **Cloud fallback** | **[OllamaCloudTool](../../../tools/cloud/ollama_cloud_tool.py)** (`ollama.com`) | **When local is also down — 24/7/365** |

mindX never has an inference gap when `ollama.com` is reachable. Cloud is the guarantee, not the default — the `_cloud_inference_active` flag in [`mindXagent.py`](../../../agents/core/mindXagent.py) resets after one use so the next cycle tries local first.

## Cloud Offload (via `-cloud` suffix)

Cloud models accessed through the local daemon use the `-cloud` tag suffix. This is a metadata-only pull — inference is proxied to `ollama.com` GPU servers. See [How Cloud Works Without an API Key](../INDEX.md#how-cloud-works-without-an-api-key) and the [latest benchmark](../INDEX.md#latest-benchmark-2026-04-11).

```
ollama pull gpt-oss:120b-cloud    → metadata only, inference on cloud GPU (65 tok/s)
ollama pull deepseek-r1:1.5b      → full weights, inference on local CPU (8 tok/s)
```

Test script: [`scripts/test_cloud_all_models.py`](../../../scripts/test_cloud_all_models.py)

## Production Deployment Notes (mindx.pythai.net)

### VPS: 4GB RAM, No GPU, Hostinger

- Only 1 model loaded at a time
- `qwen3:1.7b` as autonomous default (~2GB RAM)
- `qwen3:0.6b` for lightweight tasks (~1GB)
- Embedding models: `mxbai-embed-large` (0.7GB), `nomic-embed-text` (0.3GB)
- `keep_alive: 5m` — free memory between cycles
- Autonomous cycle: 300s interval with inference pre-check

### Known Issues (from audit 2026-04-10)

1. **OllamaHandler ignores rate limiting** — uses direct aiohttp, not rate_limiter
2. **No streaming in OllamaAPI** — `stream: False` hardcoded
3. **MastermindAgent.autonomous_loop_task never created** — declared but not wired
4. **blueprint_agent crashes on None LLM response** — no null check before json.loads
5. **MemoryAgent missing get_memories_by_agent** — RAGE route fallback fails

### What's Working Well

- Dual-URL failover is production-proven
- Token counting from API response (not estimation)
- Model discovery with 24h refresh
- Conversation history persistence to JSON
- Admin routes for diagnostics
- HierarchicalModelScorer feedback loop

## Cloud Integration (Implemented)

- [`OllamaCloudTool`](../../../tools/cloud/ollama_cloud_tool.py) — cloud inference as a first-class BaseTool
- Wired into [`_resolve_inference_model()`](../../../agents/core/mindXagent.py) as Step 5 (guarantee)
- Rate limited at 10 RPM via embedded `CloudRateLimiter`
- 18dp precision metrics at `data/metrics/cloud_precision_metrics.json`

## VPS Deployment (HostingerVPSAgent)

[`agents/hostinger_vps_agent.py`](../../../agents/hostinger_vps_agent.py) manages the production VPS through three MCP channels:

| Channel | Transport | Auth | Capabilities |
|---------|-----------|------|-------------|
| SSH | `root@168.231.126.58` | `~/.ssh/id_rsa` | deploy, health, restart, logs, models, disk |
| [Hostinger API](https://developers.hostinger.com) | HTTPS | `HOSTINGER_API_KEY` | restart (no SSH), metrics, backups, VPS info |
| [mindX Backend](https://mindx.pythai.net) | HTTPS | None (public) | health, diagnostics, inference, dojo, activity |

`full_health_check()` queries all three in parallel. `register_mcp_context()` publishes tool definitions for agent discovery. See [`.agent` definition](../../../agents/hostinger.vps.agent).
