# The embedding cascade — operations (2026-07-11)

How `agents/memory_pgvector.generate_embedding()` actually behaves on the hardware mindX runs
on, why it silently starved memory for months, and the four valves that now keep it productive.
Companion to [AGINT.md](../AGINT.md) § *The Cognition Workflow* (that one covers completions;
this one covers embeddings — the memory/RAG leg).

## The cascade

```
generate_embedding(text, interactive=False)
│
├─ 1. vLLM   {VLLM_EMBED_URL}/v1/embeddings          (default :8001)
│     └─ NEGATIVE-CACHED: after a connect error the leg is skipped for
│        MINDX_VLLM_EMBED_COOLDOWN_S (600s). One probe revives it.
│
├─ 2. Ollama {OLLAMA_EMBED_URL}/api/embeddings        (the CPU standing baseline)
│     └─ ResourceGovernor gate:
│          · interactive=True → bypass (a human is waiting)
│          · throttled       → STARVATION FLOOR lets one embed through every
│                              MINDX_EMBED_TRICKLE_S (10s) anyway
│          · otherwise       → serialized through the background inference semaphore
│     └─ timeout: MINDX_EMBED_TIMEOUT_S (180s)
│
├─ 3. HuggingFace feature-extraction                  (remote; needs HF_TOKEN)
│
└─ failure → ONE rolled-up WARNING per 60s (not one per call)
```

## The three defects this replaced

**1. The timeout was shorter than the work.** The client timeout was hard-coded to **30s** —
but a real CPU embed of a 500-word chunk takes **~57s** (bge-m3, 566M params, F16, 2-core box:
the exact class of hardware every mindX node runs on). Every over-budget embed died as
`TimeoutError → None → "0 chunks embedded"`, and the doc never landed. Measured cost: **149 of
221 surfaces failed** in the 2026-07-11 DeltaVerse backfill — a 4.5-hour run that stored 72
chunks. The CPU was burned either way; only the *result* was thrown away. Timeout is now
**180s** (`MINDX_EMBED_TIMEOUT_S`).

**2. "Defer until idle" starves a box that is never idle.** The ResourceGovernor deferred
background embeds whenever CPU was over the ceiling — but a node running a resident generation
model is *always* over the ceiling. Result on the live VPS: **698 of 727 embeds in 30 minutes
returned `cpu_throttled_deferred`** — memory and RAG quietly starved while the loop looked
healthy. The **starvation floor** now lets one embed through per `MINDX_EMBED_TRICKLE_S`
(default 10s ≈ 6/min) even under throttle: a starved memory is worse than ~10% of one core.

**3. Per-call failure WARNINGs became the log.** ~24 WARNINGs/minute, one per failed embed,
drowning every other signal. Failures now roll up into **one WARNING per 60s** with a count and
the last failure; the rest go to DEBUG.

## Knobs

| Env | Default | Meaning |
|---|---|---|
| `MINDX_EMBED_TIMEOUT_S` | `180` | client timeout — must exceed real CPU embed latency |
| `MINDX_EMBED_TRICKLE_S` | `10` | starvation floor: min seconds between throttled embeds |
| `MINDX_VLLM_EMBED_COOLDOWN_S` | `600` | how long a dead vLLM embed endpoint is skipped |
| `MINDX_EMBED_MAX_CHARS` | model-derived | hard truncation (window-overflow guard) |
| `MINDX_EMBED_MODEL` | `bge-m3` | must match the pgvector schema width (1024) |

## Health check

```bash
# failures should be ~0/min (they were ~24/min before the fix)
journalctl -u mindx --since "-10m" | grep -c "generate_embedding"

# the store is growing:
psql -U mindx -d mindx -c "SELECT count(*) FROM doc_embeddings"

# what a healthy rollup looks like (one line, not a flood):
#   generate_embedding: 1 failure(s) in the last 60s · last: … vLLM=cooldown_skip ollama=200_empty
```

**Verified 2026-07-11 on the live VPS:** embed WARNINGs **~24/min → 1 per 5 min**;
`doc_embeddings` = 34,879 rows and rising; load average **2.34 → 0.14**.

## Backfilling a corpus

`scripts/ingest_deltaverse_docs.py` is the reference maintainer (DeltaVerse docs + `/data`):

```bash
.mindx_env/bin/python scripts/ingest_deltaverse_docs.py --check       # store diagnostics only
.mindx_env/bin/python scripts/ingest_deltaverse_docs.py --interactive --resume
#   --interactive : operator-supervised, bypasses the governor
#   --resume      : skip surfaces already embedded — NEVER re-grind good work
#                   (a CPU embed is ~1 minute; a full re-run of 200 surfaces is hours)
```

Diagnostics land in `~/DeltaVerse/live/rage-ingest.json` (files · chunks · failures · backend ·
index) and are displayed by the DeltaVerse docs navigator — the verse shows the health of its
own memory.

## Where the memory is visible

Every chunk this cascade stores becomes a node in the **memory lattice** of
[THE RECOGNITION FIELD](../RECOGNITION.md) (`/recognized`) — seated by the golden angle around the
turning P-O-D-A core. A recognized participant's own node ignites gold and threads itself to the
centre: *you do not watch the mind from outside; you enter the lattice.* A memory that stops
growing is therefore visible as a lattice that stops growing.

Related: [AGINT.md](../AGINT.md) § The Cognition Workflow (the completions leg of the same repair) ·
[REALM_GATE.md](../REALM_GATE.md) (the door, and the preview it shows).
