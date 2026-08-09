# GLM 5.2 and the Latest-Generation GLM Models: Inference Sources, Pricing, and Free Access for mindX Integration

## TL;DR
- **GLM-5.2 is real and released.** Zhipu AI / Z.ai shipped GLM-5.2 to GLM Coding Plan subscribers on June 13, 2026, opened the standalone pay-per-token API on June 16, and published MIT-licensed open weights on June 16–17. It is a 753B-total / ~40B-active MoE with a 1M-token context window. So "GLM 5.2" exists — you do not need to fall back to GLM-4.6.
- **For mindX, lead with an OpenAI-compatible hosted endpoint.** The cheapest predictable route for a JWT-gated, multi-route API is Z.ai's first-party OpenAI-compatible endpoint (`https://api.z.ai/api/openai/v1`) or an aggregator like OpenRouter/DeepInfra. GLM-5.2 list price is $1.40 in / $4.40 out per 1M tokens (cached input $0.26); cheaper FP4 routes (DeepInfra, GMI, Wafer) blend to ~$0.72–$0.95.
- **Free/cheap options exist but with caveats.** There is **no `:free` GLM-5.2 slug on OpenRouter**, but GLM-4.5-Air (`z-ai/glm-4.5-air:free`), GLM-4.7-Flash and GLM-4.5-Flash are genuinely free; new BigModel accounts get **20,000,000 free tokens** ("New users get 20.00 million tokens for free!"); and the MIT weights let you self-host at zero per-token cost (but GLM-5.2 is datacenter-class — ~8×H100/H200). The GLM Coding Plan (from ~$3–18/mo) is the cheapest high-volume route but is restricted to coding tools, not general API backends.

## Key Findings

### 1. Model version availability (confirmed vs. speculative)
- **GLM-5.2 — CONFIRMED RELEASED.** Released to GLM Coding Plan subscribers June 13, 2026; standalone API June 16, 2026 (per Lushbinary, June 25 2026: "Z.ai turned on the standalone pay-per-token API on June 16, 2026, priced at $1.40 per million input tokens and $4.40 per million output tokens"); open weights on Hugging Face (`zai-org/GLM-5.2`) and ModelScope June 16–17, 2026. Official Z.ai blog "GLM-5.2: Built for Long-Horizon Tasks" published June 17, 2026.
- **Specs (primary-source, official Hugging Face model card + Z.ai blog):**
  - **753B total parameters / ~40B activated** (MoE). The official zai-org card states "Model size: 753B params"; the 40B-active figure is confirmed by the first-party NVIDIA-quantized card (`nvidia/GLM-5.2-NVFP4`), which states "753B in total and 40B activated." Note a documented conflict: an arXiv generative-AI survey describes the GLM-5 backbone as "a mixture-of-experts architecture with 744 billion total parameters and 40 billion active parameters per forward pass" — the 744B figure reflects the GLM-5 foundation, while the official GLM-5.2 card says 753B. Use **753B total / 40B active** as the authoritative GLM-5.2 figure.
  - Architecture class `GlmMoeDsaForCausalLM` (tag `glm_moe_dsa`), using DeepSeek Sparse Attention (DSA) plus a new **IndexShare** mechanism that reuses one indexer across every four sparse-attention layers, cutting per-token FLOPs by 2.9× at 1M context. An improved Multi-Token Prediction (MTP) layer raises speculative-decoding acceptance length by ~20% (4.56 → 5.47). Technical report: arXiv 2602.15763 ("GLM-5: from Vibe Coding to Agentic Engineering"); IndexShare paper arXiv 2603.12201.
  - **Context window: 1M tokens** ("solid 1M-token context," up from 200K in GLM-5.1). **Max output 128K tokens per response** (per Requesty's GLM-5.2 model page: "glm-5.2 has a context window of 1M tokens, with a maximum output of 128K tokens per response"). Together AI's reseller page lists "256K context / 131,072 output" — this is a reseller error; the official figure is 1M.
  - Two thinking-effort levels: **High** and **Max** (OpenRouter exposes these as `high` / `xhigh`, where xhigh maps to max). Thinking is enabled by default.
  - License: **MIT** ("Pure Open: An MIT open-source license — no regional limits"). Covers the open weights; code repo (github.com/zai-org/GLM-5) is also MIT.
  - Supported inference frameworks: transformers, vLLM (0.23.0+), SGLang (0.5.13+), KTransformers, xLLM, Unsloth, llama.cpp (GGUF community builds), plus Ascend NPU paths.
  - Text-only (no vision). Benchmarks (self-reported / early third-party): 81.0 on Terminal-Bench 2.1, 62.1% on SWE-bench Pro (vs GPT-5.5's 58.6%, Gemini 3.1 Pro's 54.2%); positioned as the strongest open-source model on long-horizon coding benchmarks (FrontierSWE, SWE-Marathon). Treat benchmark superiority claims as vendor-reported pending independent confirmation.

- **The broader GLM lineage (all confirmed, MIT-licensed open weights):** GLM-4.5 / GLM-4.5-Air (Jul 2025), GLM-4.5V (Aug 2025), GLM-4.6 (Sep 30, 2025), GLM-4.7 (Dec 2025), GLM-5 (Feb 11, 2026), GLM-5.1 (Apr 7, 2026), GLM-5.2 (Jun 2026). GLM-4.6V is the current vision model; **GLM-4.6 (355B total params per the zai-org/GLM-4.6 Hugging Face model card, ~32B active, 200K context)** remains a very cost-effective workhorse.

### 2. Sources of inference and pricing

**First-party (Z.ai / BigModel):** OpenAI-compatible endpoint `https://api.z.ai/api/openai/v1` and Anthropic-compatible endpoint `https://api.z.ai/api/anthropic`. Mainland: `https://open.bigmodel.cn/api/paas/v4`. Official per-1M-token list prices (USD), from docs.z.ai/guides/overview/pricing:

| Model | Input | Cached input | Output | Context |
|---|---|---|---|---|
| GLM-5.2 | $1.40 | $0.26 | $4.40 | 1M |
| GLM-5.1 | $1.40 | $0.26 | $4.40 | ~200K |
| GLM-5 | $1.00 | $0.20 | $3.20 | 200K |
| GLM-5-Turbo | $1.20 | $0.24 | $4.00 | — |
| GLM-4.7 | $0.60 | $0.11 | $2.20 | ~200K |
| GLM-4.7-FlashX | $0.07 | $0.01 | $0.40 | ~200K |
| GLM-4.6 | $0.60 | $0.11 | $2.20 | 200K |
| GLM-4.5-Air | $0.20 | $0.03 | $1.10 | 128K |
| GLM-4.5-X | $2.20 | $0.45 | $8.90 | — |
| GLM-4.7-Flash | Free | Free | Free | ~200K |
| GLM-4.5-Flash | Free | Free | Free | 128K |
| GLM-4.6V-Flash | Free | Free | Free | 131K (vision) |

Web Search built-in tool: $0.01/use. Cached-input storage is currently "limited-time free."

**Third-party providers (all OpenAI-compatible) — GLM-5.2 and GLM-4.6:**

| Provider | GLM-5.2 input/output (per 1M) | GLM-4.6 input/output | Context | OpenAI-compat | Notes |
|---|---|---|---|---|---|
| Z.ai (first-party) | $1.40 / $4.40 | $0.60 / $2.20 | 1M / 200K | Yes (+ Anthropic) | Cached input $0.26; FP8 |
| OpenRouter (router) | list $1.40 / $4.40; auto-route ~$0.95 / $3.00 | ~$0.43 / $1.74 | 1M | Yes | 22+ providers; **no `:free` for 5.2** |
| DeepInfra | $0.95 / $3.00 (FP4) | ~$0.55–0.60 / $2.20 | 1M | Yes | Cheapest output; FP4; explicit cached pricing |
| GMI Cloud | ~$1.12 / $3.52 (FP8) | — | 1M | Yes | Cheapest blended (~$0.72) |
| Wafer | $1.20 / $4.10 | — | 1M | Yes | Fast cheap (>200 t/s); FP4 |
| Fireworks AI | $1.40 / $4.40 (FP8) | $0.55 / $2.19 | 1M / 203K | Yes | Fastest (315 t/s); fixed 6,000 RPM ceiling |
| Together AI | $1.40 / $4.40 (FP4); cached $0.26 | $1.00 blended | 1M (reseller page lists 256K) | Yes | LoRA fine-tune, downloadable weights |
| Novita AI | FP8 tier (~$1.40 / $4.40 class) | $0.60 / $2.20 | 200K–1M | Yes | `base_url=https://api.novita.ai/openai` |
| SiliconFlow | FP8 tier | $0.50 / $1.90 (page lists $0.39/$1.90) | 205K | Yes (**no JSON mode**) | JSON mode missing — blocker for structured output |
| Parasail | FP8 tier | — | 1M | Yes | |
| Baseten / CoreWeave / Nebius / FriendliAI / Databricks / Makora | ~$1.40 / $4.40 class (varies; Nebius highest ~$1.70 blended) | — | 1M | Yes | FriendliAI supports both OpenAI + Anthropic |

GLM-5.2 (max) blended price ranges ~$0.72 (GMI) to $1.70 (Nebius) per 1M on a 7:2:1 mix. FP4 routes (DeepInfra, Wafer) trade some quality for price; Z.ai/Fireworks/Novita serve FP8.

### 3. Free access options
- **OpenRouter:** No `:free` variant for GLM-5.2, GLM-5, or GLM-4.6. **GLM-4.5-Air is available free** at slug `z-ai/glm-4.5-air:free` (confirmed live on OpenRouter; 131K context, up to 96K output). Free-tier limits: 20 req/min; 50 req/day under $10 lifetime credit, 1,000 req/day after a one-time $10 purchase.
- **Z.ai / BigModel free tiers:** New BigModel (open.bigmodel.cn) accounts get **20,000,000 free tokens** automatically — the console states "New users get 20.00 million tokens for free!" (plus ~120 image/video credits). **Zhipu's ZCode 3.0 provides 3 million free GLM-5.2 tokens per day for eligible users** (per Avenchat, June 22 2026). Z.ai's three always-free Flash models (GLM-4.7-Flash, GLM-4.5-Flash text; GLM-4.6V-Flash vision) are genuinely free but rate-limited and tuned for speed over depth.
- **Self-hosting (MIT):** Weights at `huggingface.co/zai-org/GLM-5.2` and ModelScope; FP8, BF16, NVFP4 (NVIDIA), W4AFP8 (Phala) and GGUF (Unsloth) builds exist. Zero per-token cost.
- **GLM Coding Plan launch promo:** First-month promo rates were as low as $3 (Lite) / $15 (Pro) at launch week (now expired/stepped up).
- **Other free/near-free routes (mostly coding-tool-bound):** OpenCode Go referral credits, Devin Pro bundling, and a limited Hugging Face Inference Providers window. There is **no permanent, unlimited free hosted GLM-5.2 API.**

### 4. GLM Coding Plan subscriptions
Flat-fee, prompt-quota subscription usable only inside ~20+ supported coding tools (Claude Code, Cline, Roo Code, Cursor, OpenClaw, Kilo Code, etc.). All tiers include GLM-5.2, GLM-5-Turbo, GLM-4.7, GLM-4.5-Air.

| Tier | Standard /mo | Promo / annual | Quota |
|---|---|---|---|
| Lite | $18 | ~$12.60/mo (yearly); $3 launch promo | ~80 prompts / 5h, ~400/week, 100 MCP calls/mo |
| Pro | $72 | ~$50.40/mo (yearly); $15 launch promo | ~400 prompts / 5h, ~2,000/week, 1,000 MCP calls/mo (5× Lite) |
| Max | $160 | ~$112/mo (yearly) | ~1,600 prompts / 5h, ~8,000/week, 4,000 MCP calls/mo (20× Lite) |

Quotas reset on 5-hour rolling windows. GLM-5.2 consumes ~3× quota at peak / 2× off-peak vs lighter models. The Coding Plan ships both OpenAI- and Anthropic-compatible endpoints, but the OpenAI URL must be the coding-only endpoint `https://api.z.ai/api/coding/paas/v4` (not the general `/api/paas/v4`). **Important:** the Coding Plan license forbids use through unauthorized third-party tools / custom integrations — for mindX's API backend you must use the standalone pay-per-token API, not the Coding Plan.

### 5. Self-hosting requirements
- **GLM-5.2 (753B/40B MoE):** ~744–753 GB VRAM at FP8 (weights only), ~1.49 TB at BF16, ~372 GB at INT4 — plus KV cache for 1M context and ~10–20% overhead. Practically **8×H200** (~1,128 GB aggregate) at FP8, ~16 GPUs at BF16. NVFP4 build targets B200/B300; W4AFP8 needs Hopper (SM90). Datacenter-class; not a laptop/prosumer model.
- **GLM-4.5-Air (106B/12B MoE, 128K context):** runs on **2×H100 or 1×H200 at FP8**. The practical self-host sweet spot for cost-sensitive teams; ~2× faster than full-size models.
- **GLM-4.6 (355B/32B, 200K):** ~8×H200 FP8 / 16×H100 territory.
- Serve with `vllm serve zai-org/GLM-5.2 --tensor-parallel-size 8 --tool-call-parser glm47 --reasoning-parser glm45` (or SGLang with EAGLE speculative decoding). vLLM prefers power-of-two tensor-parallel sizes; size for the memory budget, then round up.

## Details

### Integration into mindX (OpenAI-compatible router, JWT-gated, 350+ routes)
mindX already exposes an OpenAI-compatible surface, so GLM integration is a base-URL + key + model-slug change. Recommended wiring:

**OpenAI-compatible (lead with this — matches mindX's existing stack):**
```
base_url = "https://api.z.ai/api/openai/v1"   # or https://api.novita.ai/openai,
                                              #    https://openrouter.ai/api/v1,
                                              #    https://api.deepinfra.com/v1/openai
api_key  = <provider key>                      # store server-side, never expose to JWT clients
model    = "glm-5.2"                            # Z.ai; "zai-org/GLM-5.2" on Novita/Together/DeepInfra;
                                                #        "z-ai/glm-5.2" on OpenRouter
```
For the 1M-context mode in some tools, the model id is `glm-5.2[1m]`.

**Anthropic-compatible (only if a route needs Claude-style Messages API):**
```
ANTHROPIC_BASE_URL   = "https://api.z.ai/api/anthropic"
ANTHROPIC_AUTH_TOKEN = <z.ai key>
```
Z.ai is the only major provider besides Anthropic offering a true Anthropic-compatible endpoint; FriendliAI also supports both OpenAI and Anthropic Messages formats.

**Multi-route, JWT-gated considerations:**
- Keep provider API keys server-side in mindX; mint your own JWTs for downstream callers and never pass the upstream GLM key through. GLM endpoints authenticate with a simple bearer key, so a thin proxy route inside mindX is the clean pattern.
- Set a long client/server timeout: first-token latency for 1M-context GLM calls is reported at 30–90s. The Z.ai docs recommend `API_TIMEOUT_MS=3000000` for long calls — apply an equivalent at your gateway so JWT-gated routes don't kill long agentic loops.
- For BDI/agentic loops that resend a large stable system prompt or world-state, exploit cached input ($0.26/1M on Z.ai, ~$0.18–0.205/1M on DeepInfra) — it cuts repeated-context cost ~80%.
- GLM-5.2 has thinking enabled by default (reasoning tokens billed at output rate). Disable per-turn with `reasoning={"enabled": False}` for cheap/simple routes; reserve High/Max effort for hard tasks.
- For resilience across 350+ routes, OpenRouter (auto-router + automatic failover across 22+ hosts) or a small internal fallback list (Z.ai → DeepInfra → Fireworks) avoids single-provider outages. Avoid SiliconFlow for structured-output routes — it lacks JSON mode.

## Recommendations

**Stage 1 — Prototype (this week, near-zero cost):**
- Sign up at BigModel (20,000,000 free tokens) or use Z.ai's free Flash models (GLM-4.7-Flash / GLM-4.5-Flash) to validate the OpenAI-compatible wiring into mindX.
- For free experimentation through one key, add `z-ai/glm-4.5-air:free` via OpenRouter (20 req/min, 50–1,000 req/day).

**Stage 2 — Low-volume production:**
- Use Z.ai first-party OpenAI-compatible API with GLM-5.2 ($1.40/$4.40) for quality-critical routes and GLM-4.7 or GLM-4.5-Air ($0.60/$2.20 and $0.20/$1.10) for routine routes. Turn on prompt caching for your stable BDI system prompt.
- If you want passthrough pricing + failover, route through OpenRouter or DeepInfra (FP4, cheapest output) instead.

**Stage 3 — Scale / cost optimization:**
- Tier your model routing: GLM-4.5-Air or GLM-4.7-Flash for classification/cheap turns, GLM-5.2 only for hard reasoning/coding. This is the single biggest cost lever (a workload can be ~5× cheaper on Air than on 5.2).
- Benchmark FP4 (DeepInfra/Wafer, ~$0.72–0.95 blended) vs FP8 (Z.ai/Fireworks) on your own tasks before optimizing purely on price.

**Stage 4 — Self-host (only at high, steady volume or strict data residency):**
- Self-host GLM-4.5-Air on 1×H200/2×H100 for the best cost/effort balance; reserve full GLM-5.2 self-hosting (8×H200) for genuinely high sustained throughput or air-gapped compliance.

**Thresholds that change the recommendation:**
- If monthly standalone-API token spend exceeds ~$72–160 and your usage is coding-tool-shaped, the GLM Coding Plan is cheaper — but only if you can run inside a supported tool (not a custom backend).
- If sustained throughput exceeds what amortized 8×H200 rental covers vs per-token billing, self-hosting wins.
- If a route needs vision, switch to GLM-4.6V ($0.30/$0.90) or the free GLM-4.6V-Flash.

## Caveats
- **Pricing volatility:** GLM pricing and Coding Plan tiers change frequently (Z.ai notes "prices refreshed weekly"; launch promos have already expired). Verify at z.ai/subscribe, docs.z.ai/guides/overview/pricing, and openrouter.ai before committing.
- **Parameter-count conflict:** Official zai-org card says 753B total; an arXiv survey and several trackers cite 744B (the GLM-5 backbone figure). 40B active is consistent across sources.
- **Benchmark claims are largely vendor-reported.** Z.ai initially published no full benchmark suite for GLM-5.2; the SWE-bench Pro / Terminal-Bench numbers are self-reported or early third-party and await broad independent verification.
- **Coding Plan ≠ API backend.** The Coding Plan's terms restrict use to officially supported coding tools; using its quota through mindX's custom API would violate terms. Use the standalone pay-per-token API for backend integration.
- **Quantization affects quality.** The cheapest FP4 routes can differ subtly from FP8/BF16 on agentic/coding tasks — test on your workload.
- **Latency & region:** Z.ai servers are primarily in China (~100–200ms from US/EU; slower during Chinese business hours). For latency-sensitive routes, a US-hosted aggregator (Fireworks, Together, DeepInfra) may be preferable.
- **Reseller-page errors exist:** e.g., Together AI's GLM-5.2 page lists "256K context / 131,072 output," contradicting the official 1M-context spec. Prefer first-party sources (Z.ai docs, Hugging Face, OpenRouter, provider docs) where they conflict with secondary trackers.