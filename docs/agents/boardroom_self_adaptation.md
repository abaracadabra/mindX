# Boardroom self-adaptation — pattern→action recovery registry

When the boardroom roll-call fails, the failure is rarely random. Seven soldiers tend to fail for the **same** reason — a lapsed Ollama Cloud signin, a cold-model storm, a prompt-format drift, a missing persona file. mindX recognises these patterns and emits a structured **recovery** action the UI can auto-fire (or the operator can click). This is the foundation of mindX adapting to its own errors.

## The shape

Every roll-call response now carries a `recovery` block:

```json
{
  "results":   { ... per-soldier acks ... },
  "present":   0,
  "total":     7,
  "advice":    "Ollama Cloud signin has lapsed ...",
  "recovery": {
    "pattern":          "ollama_signin_lapsed",
    "severity":         "high",
    "matched_count":    7,
    "matched_total":    7,
    "auto_action": {
      "method":         "POST",
      "endpoint":       "/insight/boardroom/cloud_signin",
      "ui_message":     "7/7 soldiers report 'unauthorized'. CEO is initiating ..."
    },
    "operator_message": "The boardroom needs you to re-authorise the local Ollama daemon ...",
    "fallback_when_no_signin": "If the operator can't sign now, ...",
    "remediation_hints": [ "..." ]
  }
}
```

**`pattern`** identifies the failure mode. **`auto_action`** (when present) is the endpoint the UI auto-fires — today only the `ollama_signin_lapsed` pattern has a safe automation; others surface remediation hints the operator chooses from. **`operator_message`** is always present and is human-readable; it goes into the boardroom dialogue as a CEO → SELF message and onto `/feedback.html#sec-board` as a banner above the per-soldier results.

## Patterns wired today

Four patterns ship in `Boardroom._diagnose_recovery()`. Priority order is the order shown — the first match wins.

### 1. `ollama_signin_lapsed`  (severity: high)

**Trigger:** ≥ 4/7 soldiers errored with text containing `"unauthorized"`.

**Auto-action:** `POST /insight/boardroom/cloud_signin` — spawns `ollama signin` on the VPS, captures the connect URL, surfaces it as a CEO → OPERATOR dialogue message with a one-click button. The operator clicks the link, the daemon re-authorises, and the next roll-call comes back clean.

**Why automatic:** the recovery action is itself read-only against system state (it just runs a CLI tool that prints a URL); the actual mutation (operator clicking ollama.com) is gated by the operator's browser session. There's no way for this to misbehave silently — the worst case is a wasted CLI invocation.

### 2. `cold_load_storm`  (severity: medium)

**Trigger:** ≥ 4/7 soldiers timed out at the per-soldier ceiling, OR errored with `"cold-loading"` in the message.

**Auto-action:** none — the right fix depends on operator policy:

- preferred: run `ollama signin` (cloud routing through one shared model = sub-3s per soldier, no swap)
- alt: increase `OLLAMA_MAX_LOADED_MODELS` in `/etc/systemd/system/ollama.service.d/concurrency.conf`
- alt: deploy a vLLM server and set `BOARDROOM_INFERENCE_BACKEND=vllm` (continuous batching)

The roll-call surfaces all three as `remediation_hints`; the operator picks one.

### 3. `empty_ack_drift`  (severity: medium)

**Trigger:** ≥ 4/7 soldiers responded silently (model loaded, returned an empty body).

**Auto-action:** none. Likely root causes:

- prompt-format drift — model output landing in `thinking` instead of `response` (we already fall back to `thinking`; this would mean both are empty)
- `BOARDROOM_NUM_CTX` truncating the persona before any tokens are generated
- model corruption — re-pull via `ollama pull <model>`

The recovery surfaces a diagnosis pointing at `/insight/boardroom/cards` for prompt-size verification.

### 4. `persona_files_missing`  (severity: low)

**Trigger:** any seat reports `persona_source == "fallback"` — the loader didn't find the `.prompt` / `.agent` / `.persona` files and fell through to the hardcoded `SOLDIER_PERSONAS` dict.

**Auto-action:** none. The recovery names the affected seats and points at [`docs/agents/boardroom_members.md`](boardroom_members.md) for the file layout.

### 5. `openrouter_rate_limited`  (severity: high)

**Trigger:** ≥ 4/7 soldiers errored with HTTP 429 from the OpenRouter API. The shape that matches: error body has `error.code == 429` AND `error.metadata.headers["X-RateLimit-Reset"]` is present (epoch milliseconds, parsed as such — **not** seconds, **not** delta-seconds, see [OPENROUTER_mindX.md §Rate limits](../OPENROUTER_mindX.md#rate-limits-the-10-unlock-and-what-429-actually-means)).

**Auto-action:** none today (matcher is in the [boardroom_openrouter backlog](boardroom_openrouter.md#backlog)). When implemented, the auto-action will be a 60-second account-wide dispatch deny on OpenRouter, with the boardroom falling through to Ollama Cloud or local for the remainder of the session — the existing `auto` mode in `BOARDROOM_INFERENCE_BACKEND` already handles the fallback once OpenRouter is marked unreachable.

**Why this fires reliably**: OpenRouter free tier permits **50 requests per day** until the [$10 unlock](../OPENROUTER_mindX.md#rate-limits-the-10-unlock-and-what-429-actually-means) lifts the cap to 1000. At 8 votes per session, that is ~6 convene sessions before exhaustion. After exhaustion, every soldier on OpenRouter 429s until 00:00 UTC reset.

**Two operator remediations** (recovery surfaces both as `remediation_hints`):

- **Preferred**: deposit $10 once at openrouter.ai/credits to lift the daily cap from 50 → 1000. Persistent — survives later balance drops. Documented as the highest-leverage reliability lever in [OPENROUTER_mindX.md](../OPENROUTER_mindX.md#rate-limits-the-10-unlock-and-what-429-actually-means).
- **Alt**: stay on free tier and reduce convene rate to ≤6 sessions/hour (per the table in [boardroom_openrouter §Convene rate discipline](boardroom_openrouter.md#convene-rate-discipline)).

A subtler 429 shape — `{error: {code: 429, message: "Provider returned error", metadata: {raw: "<slug> is temporarily rate-limited upstream...", provider_name: "Chutes"}}}` — signals an **upstream provider** cap rather than the OpenRouter account hitting the global cap. The matcher should distinguish these: upstream caps are fixed by injecting `provider.ignore: ["Chutes"]` (or whichever provider) on the next request, not by sleeping the account. Backlog item.

**Where the operator hits it first**: `/insight/boardroom/recent` shows soldiers with `provider=openrouter/<slug>` and `error.code=429`; `/feedback.html#sec-board` shows the recovery banner once the matcher ships. Until then, manual diagnosis via `curl /insight/boardroom/recent | jq '.sessions[0].votes[] | select(.error.code == 429)'`.

## Adding a new pattern

The registry lives in `Boardroom._diagnose_recovery()` at `daio/governance/boardroom.py`. Adding a fifth pattern is one entry:

```python
# inside _diagnose_recovery, before the final "no issues" return
if SOME_PREDICATE(results):
    return {
        "pattern": "your_pattern_name",
        "severity": "high|medium|low",
        "matched_count": N,
        "matched_total": total,
        "auto_action": None,    # or { method, endpoint, ui_message }
        "operator_message": "Plain-English diagnosis ...",
        "remediation_hints": ["...", "...", "..."],
    }
```

The UI handlers are dispatched on `recovery.pattern` in `boardroom.html`'s `maybeAutoRecover()`:

```js
if (rec.pattern === 'ollama_signin_lapsed') {
    requestCloudSignin(rec.operator_message);
}
// add new handlers here for your pattern
```

If your new pattern has no auto-action, you don't need to add a handler — the operator banner narrates the diagnosis automatically and surfaces any `remediation_hints` as a collapsible list.

## Where the recovery surfaces

| Surface | Behaviour |
|---|---|
| `/feedback.html#sec-board` rollcall card | Red/amber/blue banner above per-soldier results showing pattern · severity · matched count · operator_message · clickable auto-action button (when present) · collapsible remediation hints |
| `/boardroom` deliberation stream | CEO → SELF message naming the pattern + matched count, followed by the auto-fired CEO → OPERATOR handoff message when applicable |
| `GET /insight/boardroom/rollcall?h=true` | Plain-text rendering shows the recovery block beneath the advice line |
| `data/governance/boardroom_sessions.jsonl` | Not persisted — recovery is computed per-rollcall, not per-session, since it relates to inference health, not decision history |

## Verification

```bash
# 1. Trigger a rollcall while everything is healthy → recovery.pattern = null
curl -X POST https://mindx.pythai.net/insight/boardroom/rollcall | jq '.recovery'
# {"pattern": null, "auto_action": null, "matched_count": 0}

# 2. Synthesise a failure case in Python (from any host with the repo)
python3 -c "
import sys; sys.path.insert(0, '.')
from daio.governance.boardroom import Boardroom
class _D(Boardroom): __init__ = lambda self: None
fake = {f'soldier_{i}': {'state':'error','error':'ollama unauthorized'}
        for i in range(7)}
import json; print(json.dumps(_D()._diagnose_recovery(fake, 0), indent=2))
"
# → pattern: ollama_signin_lapsed, severity: high, auto_action: cloud_signin, ...

# 3. When a real lapse happens, watch the boardroom dialogue auto-fire:
#    /boardroom shows CEO → SELF then CEO → OPERATOR with the click URL.
```

## Roadmap

This is **tier 1** self-adaptation — narrow pattern matching of inference-health failures during roll-call. Future tiers:

- **Tier 2** — pattern matching across full convene sessions (e.g. "every soldier abstained" → BOARDROOM_NUM_PREDICT too low; "every approve has confidence < 0.5" → prompt clarity issue).
- **Tier 3** — pattern matching across BDI loops and dream cycles (e.g. "BDI repeated NO_OP 12× in 6 hours" → stuck-loop pattern with auto-skeleton-fallback nudge).
- **Tier 4** — pattern matching across the whole substrate (e.g. "STM growth > 5GB/day with no archive activity" → flag for the storage-offload projector).

Each tier reuses the same `recovery` shape and the same UI dispatcher; only the matchers grow.

## Related

- [`daio/governance/boardroom.py`](../../daio/governance/boardroom.py) — `_diagnose_recovery`, `roll_call`, `request_cloud_signin`
- [`mindx_backend_service/feedback.html`](../../mindx_backend_service/feedback.html) — the banner UI + `fireRecovery()`
- [`mindx_backend_service/boardroom.html`](../../mindx_backend_service/boardroom.html) — the dialogue dispatcher + `maybeAutoRecover()`
- [Boardroom members — three-file role architecture](boardroom_members.md) — what fails when `persona_files_missing` triggers
- [Boardroom × vLLM](boardroom_vllm.md) — what `cold_load_storm` recommends as alternatives
- [Boardroom × OpenRouter](boardroom_openrouter.md) — what `openrouter_rate_limited` recovers from
- [`docs/OPENROUTER_mindX.md`](../OPENROUTER_mindX.md) — the canonical OpenRouter reference, including the JSON-body 429 shape
- [`docs/ollama/cloud/cloud.md`](../ollama/cloud/cloud.md) — the canonical signin doc the recovery message points at
