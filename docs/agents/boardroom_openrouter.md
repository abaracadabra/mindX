# Boardroom × OpenRouter — per-soldier free model diversity

The boardroom can route through **OpenRouter's `:free` catalogue** to give each of the 8 board members a **different free model** — restoring the per-soldier diversity that is aspirational on Ollama Cloud free tier (single-concurrent-model wall) without paying any credits. This is the third inference backend, alongside Ollama and vLLM. It exists because diversity of thought is the boardroom's reason to exist, and OpenRouter's free pool is currently the only zero-cost path that delivers it at 70B+ scale.

Read [`OPENROUTER_mindX.md`](../OPENROUTER_mindX.md) first — it is the canonical reference for OpenRouter integration in mindX. This doc is the boardroom-specific operator runbook.

## Selector

```
BOARDROOM_INFERENCE_BACKEND   = ollama | vllm | openrouter | auto    (default: auto)
BOARDROOM_OPENROUTER_BASE_URL = https://openrouter.ai/api/v1         (default)
BOARDROOM_OPENROUTER_RPS      = 8                                    (default; ≤18/min throttle)
```

| Mode | Behaviour |
|---|---|
| `auto` | Try vLLM → OpenRouter (if vault key present) → Ollama Cloud → Ollama local. **Best for live operations.** |
| `openrouter` | OpenRouter only. No fallback. Use to verify the OpenRouter wiring exclusively. |
| `vllm` | Skip OpenRouter; vLLM only. |
| `ollama` | Skip OpenRouter and vLLM; Ollama only. Default behaviour pre-OpenRouter. |

The selector reads the BANKON Vault for `openrouter_api_key` to decide whether OpenRouter is reachable. **No vault key, no OpenRouter pillar** — `auto` falls through silently.

## Vault key requirement

OpenRouter API keys live in the [BANKON Vault](../BANKON_VAULT.md) only. **Never `.env`, never `data/config/`, never git.** See [vault provisioning in OPENROUTER_mindX.md](../OPENROUTER_mindX.md#vault-provisioning--the-mindx-way-to-hold-this-key) for the full operator runbook.

```bash
# Local
python manage_credentials.py store openrouter_api_key "sk-or-v1-…"

# VPS
ssh root@168.231.126.58
sudo -u mindx bash -c 'cd /home/mindx/mindX && \
  .mindx_env/bin/python manage_credentials.py store openrouter_api_key "sk-or-v1-…"'
```

If the disclosed key has been seen in any chat transcript or screen-share, **rotate first** at https://openrouter.ai/keys, then store the rotated value. Treat the original as compromised regardless of whether it has been used — chat transcripts are not a secret-handling channel.

## Per-soldier model map

The empirically-verified mapping at [`data/config/board_openrouter_map.json`](../../data/config/board_openrouter_map.json), produced by [`scripts/test_openrouter_boardroom.py --write`](../../scripts/test_openrouter_boardroom.py) on 2026-05-03 against the live catalogue:

```json
{
  "ceo":              "openai/gpt-oss-120b:free",
  "ciso_security":    "nvidia/nemotron-3-super-120b-a12b:free",
  "cfo_finance":      "z-ai/glm-4.5-air:free",
  "cto_technology":   "poolside/laguna-m.1:free",
  "cro_risk":         "nvidia/nemotron-3-super-120b-a12b:free",
  "clo_legal":        "inclusionai/ling-2.6-1t:free",
  "cpo_product":      "nvidia/nemotron-nano-12b-v2-vl:free",
  "coo_operations":   "nvidia/nemotron-3-nano-30b-a3b:free"
}
```

**5 distinct upstreams** across 8 seats: OpenAI · NVIDIA · Z.AI · Poolside · InclusionAI. CISO and CRO deliberately share `nvidia/nemotron-3-super-120b-a12b:free` — both are 1.2× veto seats wanting the same maximum-depth reasoner. Full per-seat rationale (capability tags, fallback tail) is in the [skill→model map](../OPENROUTER_mindX.md#skill--model-map-which-free-slug-for-which-mindx-task).

**The map was probed, not guessed.** A first pass of plausible-looking slugs (`meta-llama/llama-3.3-70b-instruct:free`, `qwen/qwen3-next-80b-a3b-instruct:free`, `qwen/qwen3-coder:free`, `google/gemma-4-31b-it:free`) all 429'd within seconds — these are hosted by upstream **`Venice`**, which throttles free traffic hard. The empirical second pass swapped in non-Venice upstreams for every seat. **Never hard-code the map** — re-run the probe whenever the live catalogue shifts:

```bash
.mindx_env/bin/python scripts/test_openrouter_boardroom.py --write
```

The script throttles at 8 RPS / 18 RPM (well under OpenRouter's global 20 RPM cap), reads the key from BANKON Vault, validates against the live `/api/v1/models` catalogue, and refuses to write a partial map. OpenRouter's `:free` catalogue churns aggressively (39 deprecations in February 2026 alone); the model registry's 6-hour poll detects deprecations automatically, and the operator-tunable JSON allows manual reroute without code edits.

## Health verification

```bash
# 1. confirm vault key present
python manage_credentials.py list | grep openrouter
# openrouter_api_key

# 2. confirm OpenRouter reachable from boardroom side (without leaking key)
curl -s -H "Authorization: Bearer $(.mindx_env/bin/python -c \
  'from mindx_backend_service.vault_bankon import unlock; print(unlock(\"openrouter_api_key\"))')" \
  https://openrouter.ai/api/v1/key | jq '.data | {label, is_free_tier, usage, limit_remaining}'
# {"label": "mindx-prod-…", "is_free_tier": true, "usage": 0.0, "limit_remaining": 50}

# 3. confirm boardroom sees it
curl https://mindx.pythai.net/insight/boardroom/health?h=true | grep OpenRouter
# OpenRouter (auto):  ✓ key vaulted, free_tier=true, 50 RPD remaining
# or
# OpenRouter (auto):  ○ no vault key — Ollama in use

# 4. force OpenRouter-only and convene a session
sudo systemctl edit mindx
#   Environment="BOARDROOM_INFERENCE_BACKEND=openrouter"
sudo systemctl restart mindx

curl -X POST "https://mindx.pythai.net/boardroom/convene?directive=Test"

# 5. inspect persisted session — provider field should read openrouter/<slug>
curl https://mindx.pythai.net/insight/boardroom/recent | jq '.sessions[0].votes[].provider'
# "openrouter/nvidia/nemotron-3-super-120b-a12b:free"
# "openrouter/qwen/qwen3-coder:free"
# ...
```

## Comparison vs other pillars

| | Ollama local | Ollama Cloud | vLLM | OpenRouter |
|---|---|---|---|---|
| Per-soldier diversity | ✅ qwen3 family | ❌ one shared model | ✅ per-port deploy | ✅ per-soldier slug |
| Capability ceiling | 4B params | 120B params | self-set | 120B+ free |
| Concurrency | serialised swap | 1 concurrent (free) | true continuous batching | 18 RPM client throttle |
| Latency | 4–14 tok/s | 65 tok/s | 50–100 tok/s GPU | 30–80 tok/s typical |
| Cost | zero | zero (free tier limited) | self-host (~$0.50/h GPU) | zero (free tier) |
| Daily cap | none | 50 req/5h | none | 50 RPD / 1000 RPD after $10 unlock |
| Sovereignty | full | external dep | full | external dep |
| Per-vote audit trail | local logs | ollama.com logs | local logs | OpenRouter `gen_id` + provider name |
| Setup work | none | `ollama signin` | deploy vLLM server | vault `openrouter_api_key` |

For everyday convene cycles, OpenRouter is the sweet spot — diversity + capability + zero cost. For sovereignty audits, vLLM. For maximum capability per single vote when diversity doesn't matter, Ollama Cloud's `gpt-oss:120b-cloud`.

## Failure modes

OpenRouter's free tier has well-understood failure modes documented in [`OPENROUTER_mindX.md` §Production reliability](../OPENROUTER_mindX.md#production-reliability-the-gotchas-that-bite). The boardroom-specific cases:

### Rate limit (429)

A 429 from OpenRouter has a specific shape: HTTP `429 Too Many Requests`, body `{"error": {"code": 429, "message": "Rate limit exceeded: limit_rpd/<slug>/<id>", "metadata": {"headers": {"X-RateLimit-Limit": "50", "X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1746234000000"}}}}`.

**Reset is epoch milliseconds**, not seconds, not delta-seconds. **The headers live inside `error.metadata.headers`**, not as actual HTTP headers — naive consumers reading only `response.headers` miss them.

When ≥4/7 soldiers receive a 429, the boardroom triggers the `openrouter_rate_limited` recovery pattern (see [`boardroom_self_adaptation.md`](boardroom_self_adaptation.md)) — denies dispatch for ≤60s, falls through to Ollama Cloud or local for the remainder of the session.

### Model deprecation

A `:free` slug can disappear from `/api/v1/models` between polls. The boardroom logs `provider=openrouter/<deprecated-slug>` with `vote=abstain` and `error="deprecated"`, then routes that soldier's vote through the next entry in its fallback tail per the [skill→model map](../OPENROUTER_mindX.md#skill--model-map-which-free-slug-for-which-mindx-task). Operator action: edit `data/config/board_openrouter_map.json` to point at a current free slug.

### Mid-stream SSE error

**HTTP stays 200** when an upstream error hits mid-stream because headers were already flushed. The error arrives as an SSE event with a top-level `error` field on the final delta. The boardroom's stream consumer must parse every chunk for `error` even on `200 OK` — naive `httpx`/`requests` consumers that only check status codes silently drop responses. Documented at length in `OPENROUTER_mindX.md` and in the streaming-coroutine addendum.

### Tool-use 404 on `:free`

Some `:free` slugs return `404 No endpoints found that support tool use` (e.g. older DeepSeek variants). The boardroom uses tools (the JSON vote envelope is a structured output, often surfaced as a tool call). When this fires, the recovery falls through to a free slug that supports tools — every entry in `BOARD_OPENROUTER_MAP` is verified tool-capable, but registry churn can break this assumption. The 6-hour registry poll updates capability flags; operators should re-verify after deprecation events.

### Free-tier daily exhaustion

50 RPD on the free tier exhausts in ~6 sessions × 8 votes. After exhaustion, all OpenRouter calls 429 until 00:00 UTC reset. The auto pillar falls through to Ollama Cloud for the remainder of the day.

**Single highest-leverage fix**: deposit $10 once. Lifts the daily cap from 50 → 1000 forever (the unlock persists even when the balance later drops below $10). This is documented as mandatory for production in `OPENROUTER_mindX.md`. Operator authorisation required — do not auto-purchase.

## Convene rate discipline

Free-tier rate caps for the boardroom:

| Account state | Daily cap | Recommended convene rate | Reasoning |
|---|---|---|---|
| Free tier (50 RPD) | 50 requests | ≤6 sessions/hour | 8 votes × 6 = 48 requests; small headroom for retries |
| $10-unlocked (1000 RPD) | 1000 requests | ≤120 sessions/hour | 8 votes × 120 = 960; per-soldier diversity becomes routine |
| Critical/constitutional | bypass cap | route OpenRouter; fallback to Ollama Cloud on 429 | safety net |

The cap is enforced client-side at `aiolimiter.AsyncLimiter(rps=8, time_period=1.0)` — well below the global 20 RPM cap, leaving headroom for the rate-limit-tracker coroutine to detect upstream provider throttles and inject `provider.ignore` directives.

## Backlog

This doc is **design-shipped, code-pending**. The implementation is tracked in [`OPENROUTER_mindX.md` § Backlog](../OPENROUTER_mindX.md#backlog). The boardroom-specific items:

| Item | Status |
|---|---|
| Per-soldier slug map (this doc) | ✅ shipped |
| `BOARDROOM_INFERENCE_BACKEND=openrouter` selector branch | ❌ not built |
| `BOARD_OPENROUTER_MAP` constant + JSON loader | ❌ not built |
| `openrouter_rate_limited` recovery pattern | ❌ not built (documented in `boardroom_self_adaptation.md`) |
| `/insight/boardroom/health` OpenRouter line | ❌ not built |
| Vault key reachability check at startup | ❌ not built |

Implementation lands as a follow-up PR after these docs are reviewed.

## Related

- [`OPENROUTER_mindX.md`](../OPENROUTER_mindX.md) — canonical OpenRouter reference for mindX
- [`BOARDROOM.md` §3.X Model Selection Policy](../BOARDROOM.md) — the free-first principle, three-pillar strategy, value > cost trigger
- [`agents/boardroom_vllm.md`](boardroom_vllm.md) — vLLM as the sovereignty pillar (sibling to this doc)
- [`agents/boardroom_self_adaptation.md`](boardroom_self_adaptation.md) — recovery patterns including `openrouter_rate_limited`
- [`agents/boardroom_members.md`](boardroom_members.md) — three-file role architecture
- [`BANKON_VAULT.md`](../BANKON_VAULT.md) — credential storage canonical reference
- [`daio/governance/boardroom.py`](../../daio/governance/boardroom.py) — boardroom implementation
- https://openrouter.ai/models — live free-model catalogue (snapshot at OPENROUTER_mindX.md is May 2026)
- https://openrouter.ai/docs/quickstart#using-the-openrouter-api — upstream API quickstart
- https://openrouter.ai/docs/quickstart#using-the-agent-sdk — Claude Agent SDK pathway for paid escalation
