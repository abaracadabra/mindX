# Inference Budget — the LLM Metabolism

> mindX consumes three inference tiers — **Ollama Cloud** (free tier: ~10/min, 50 per
> 5h-session, 500/week), **OpenRouter** router models (free: 20/min, 50/day), and
> **local Ollama** (unlimited but CPU-slow). The *inference budget* is a shared,
> self-adjusting ledger
> that routes every model decision toward whichever tier still has headroom — cloud →
> router → local — and back as the windows refill. It behaves like a metabolism: it
> consumes the cheap-and-fast cloud while it can, falls to local when the cloud is
> spent, backs off on throttling, and breathes back in as quotas reset.

Source: `llm/inference_budget.py`. Live state persists to
`data/monitoring/inference_budget.json` and is surfaced on `/diagnostics/live`
(`inference_budget` key) and the landing-page Inference panel.

## Why

Before this, model selection was static: it picked the highest-*capability* model with
no idea of remaining rate-limit budget. Under the autonomous loop's load that hammered
the Ollama Cloud free tier, which responds to over-use with **empty 200s** and **429s**
→ empty plans, 600s timeouts, and stalled campaigns. The crude fix was a fixed 1-hour
cadence. The budget replaces that with a real, dynamic economy: the system self-paces to
the *actual* limits and adapts when they change.

## Architecture — Sense → Decide → Adapt

### Sense — `InferenceBudget` (singleton ledger)
Per-provider state keyed by tier (`ollama_cloud`, `openrouter`, `ollama`/local, `vllm`,
`gemini`, `groq`, …):

- **Configured limits** load from `data/config/provider_registry.json` +
  `models/ollama.yaml` `cloud.rate_limits` (the authoritative free-tier 10/min, 150/hr).
- **Sliding-window counters** — requests in the last 60s and 3600s, tokens/min.
- **Adaptive `eff_rpm`** — the effective per-minute limit, which moves with reality.
- `headroom(provider) -> 0..1` — **SYNC** (the hot path; the model scorer is sync). Local
  tiers and any error → `1.0` (**fail-open**: the budget can deprioritise a provider but
  can NEVER block all inference; local is always available).
- `record(provider, ok, tokens, retry_after)`, `snapshot()`.

### Decide — budget is a scoring axis in BOTH selectors
- `llm/model_selector.py::_score_models` (registry path) multiplies each model's score by
  `max(0.05, headroom(provider))`. Ollama `:cloud` models map to the rate-limited
  `ollama_cloud` budget (vs unlimited local `ollama`). A starved tier's models collapse
  below any tier with headroom; **local rises to the top as the failsafe** — not by a
  hard-coded rule, but by budget.
- `mindx/self/improve/model_selector.py::choose_model` (self-aware path) multiplies each
  candidate's score by `slug_budget_headroom(slug)` (in
  `mindx/self/improve/handler_resolver.py`), recorded in the choice breakdown for the
  Gödel audit.
- Floor `0.05` = *deprioritise, don't exclude* — a starved tier is still reachable as a
  last resort.

### Adapt — handlers feed the ledger; the ledger self-tunes
- `llm/ollama_handler.py` records every call under `ollama_cloud` vs `ollama`. An **empty
  cloud response** is treated as the throttle symptom → `ok=False`, back off. A 429/quota
  error backs off and honours `Retry-After`.
- `llm/openrouter_handler.py` records success + 429.
- On 429: `eff_rpm × 0.7` and an exponential backoff window opens. On sustained success:
  `eff_rpm` climbs back toward (and can exceed) the configured limit — so the metabolism
  tracks a provider **raising** its limit just as it tracks one lowering it.

## Real limits + safety margin

Each provider is modelled with its **actual** free-tier limits as multiple windows;
headroom is the **min across all windows** (the tightest binding constraint governs). A
**safety factor (`_SAFETY = 0.9`)** makes headroom reach 0 at **90% of each limit**, so
selection routes to local *before* the real ceiling — the metabolism consumes the free
tier **fully but never trips a 429** (the documented "leave 10% buffer, stop before the
limit, don't wait for the 429" strategy).

| Provider | Windows (real free-tier limits) | Notes |
|---|---|---|
| `ollama_cloud` | 10/min · 50 / 5h-session · 500/week | per `docs/ollama/cloud/rate_limiting.md` + `CloudQuotaTracker` |
| `openrouter` | 20/min · 50/day | free (`<10` credits); 1000/day with `≥10` credits |
| `gemini` | 15/min · 1500/day | 2.0 Flash free |
| `groq` | 30/min · 14400/day | |
| local `ollama` / `vllm` | — | unlimited (always headroom 1.0) |

Limits live in `_PROVIDER_WINDOWS` in `llm/inference_budget.py`; `models/ollama.yaml`
`cloud.rate_limits`, if set, fold in as additional ollama_cloud windows (tighter wins).
The metabolism also adapts effective limits **upward** on sustained success, so raising
your account tier (or buying OpenRouter credits) needs no restart — and **downward** on
any observed 429. Raise `_SAFETY` toward `1.0` to consume more aggressively.

## Observe it breathe

```bash
# Live per-provider snapshot
curl -s https://mindx.pythai.net/diagnostics/live | jq .inference_budget
# Persisted ledger on the box
cat data/monitoring/inference_budget.json
```

The landing-page **Inference** panel renders a headroom bar per provider, the effective
limit when it has adapted, and any active back-off countdown.

Example live state (one `gpt-oss:120b-cloud` planning call recorded):

```
ollama_cloud  headroom=0.89  binding 1/10@1m  tokens_min=6779  total_429=0
              windows: 1/10@1m, 1/50@5h, 1/500@7d
openrouter    headroom=1.0   20/min · 50/day
... local = unlimited (headroom 1.0)
```

Each snapshot reports `headroom`, the `windows[]` (used/limit per span), and the
`binding_window` (the one currently closest to its safety threshold).

## Design guarantees

- **Fail-open everywhere.** Any ledger error → headroom `1.0`. Inference never blocks on
  the budget; local is always the failsafe.
- **Multiplier, not gate.** Selection is *advised* (rerouted) by budget; the per-handler
  `DualLayerRateLimiter` (`llm/rate_limiter.py`) remains the gating backstop.
- **Self-pacing.** Once proven, the static autonomous cadence can relax — the metabolism
  paces consumption to real limits on its own.

See also: `docs/EMBEDDING_SYSTEM.md`, `docs/AUTONOMOUS.md`, `llm/RESILIENCE.md`,
`agents/resource_governor.py` (the coexistence governor).
