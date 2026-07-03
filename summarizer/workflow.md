# Workflow: from user messages to security handling

This document traces the **full path a conversation takes through compaction** —
from the raw user messages accumulating in context, through the trigger, the
summary call, the reseed, and finally **how security-relevant instructions are
carried across the context reset**. It ties together `trigger_logic.js`, the two
prompt files, and `continuation_wrapper.txt`.

---

## End-to-end pipeline

```
┌────────────────────────────────────────────────────────────────────────────┐
│ 1. ACCUMULATE                                                               │
│    User messages + assistant turns + tool results pile up in the context.   │
│    Each non-tool-result user message is "load-bearing" — it may carry a     │
│    standing instruction or a security constraint.                           │
└──────────────┬─────────────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 2. MEASURE            (trigger_logic.js: z7H, uAH)                          │
│    used = min(usedTokens, IE4cap);  remaining = window − used               │
│    window resolved by cn(): env → settings → experiment → model-default →   │
│    auto, clamped to the model's true max context.                           │
└──────────────┬─────────────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 3. CLASSIFY           (trigger_logic.js: wh$, hE4)                          │
│    compactThreshold = window − 13000                                        │
│    used ≥ threshold−20000 → "warn"  → show "Context low (N% remaining)"     │
│    used ≥ threshold       → "compact" → fire summarizer (this pipeline)     │
│    used ≥ configured−3000 → "blocked" → hard stop, must compact first       │
│    (st6 rapid-refill guard prevents back-to-back compaction loops)          │
└──────────────┬─────────────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 4. SUMMARIZE          (auto_ / manual_compact_prompt.txt)                   │
│    A SEPARATE LLM call over the old history:                                │
│      • think inside <analysis>…</analysis>                                  │
│      • walk EVERY message chronologically                                   │
│      • emit the numbered sections, including:                               │
│          §6 ALL user messages (verbatim)                                    │
│          §6 security-relevant instructions/constraints (verbatim)  ◀── KEY  │
└──────────────┬─────────────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 5. RESEED             (continuation_wrapper.txt)                            │
│    new context = prologue + summary (+ optional verbatim recent turns)      │
│    prologue notes: transcript path, "recent preserved", REPL cleared        │
│    (cold), and — for AUTO — "resume directly, do not acknowledge".          │
└──────────────┬─────────────────────────────────────────────────────────────┘
               ▼
┌────────────────────────────────────────────────────────────────────────────┐
│ 6. RESUME                                                                   │
│    Work continues. The summary IS the memory now; the old turns are gone    │
│    from live context but re-readable from the on-disk transcript.           │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Step detail

### 1. Accumulate
Every user message that is **not** a tool result is treated as potentially
load-bearing. The summary prompts later demand that **all** of them be listed —
because a single early instruction ("never touch the prod vault", "don't run
destructive commands") must outlive the messages around it.

### 2. Measure
`z7H` computes tokens remaining against the window chosen by `cn`. The window
itself is configurable (`CLAUDE_CODE_AUTO_COMPACT_WINDOW`, `/config`), but is
always clamped to the model's real max context.

### 3. Classify
`hE4` turns the raw number into a level. `warn` is the UI nudge; `compact` is the
actual fire signal; `blocked` is the safety floor that forces a compaction before
any more work. The `13000`-token head-room (`NE4`) means it summarizes *before*
hitting the wall, leaving room for the summary call itself.

### 4. Summarize
The summary is produced by a dedicated call using one of the two prompts. The
prompt structure is what makes compaction lossy-but-safe: it explicitly enumerates
what must survive (intent, files, errors, **all user messages**, pending tasks,
context to continue).

### 5. Reseed
The generated summary is wrapped by `continuation_wrapper.txt` and becomes the
first message of a fresh context. Recent turns may be appended verbatim; a
transcript-path pointer lets the agent re-fetch exact detail on demand.

### 6. Resume
For automatic compaction the wrapper tells the model to continue **without**
acknowledging the summary — so to the user it looks like the conversation never
broke.

---

## Security handling — the critical thread

Compaction is a **context reset**. Anything not carried into the summary is, for
practical purposes, *forgotten*. Both prompt files therefore single out security
content for special, **verbatim** treatment. The exact instruction (present in
both `auto_compact_prompt.txt` and `manual_compact_prompt.txt`):

> *"Note any security-relevant instructions or constraints the user stated (e.g.,
> sensitive files or data to avoid, operations that must not be performed,
> credential or secret handling rules). These MUST be preserved verbatim in the
> summary so they continue to apply after compaction."*

and, in the *All user messages* section:

> *"Preserve any security-relevant instructions or constraints verbatim so they
> remain in effect after compaction."*

### Why verbatim, not paraphrased
A paraphrase can soften or drop a constraint ("avoid the prod vault" → "be
careful with vaults"). Verbatim preservation keeps the constraint enforceable and
unambiguous after the reset.

### The chain of custody for a constraint

```
user states a constraint
   │  (e.g. "do not read the BANKON vault files")
   ▼
lives as a normal user message in context
   │
   ▼  compaction fires
summary prompt §6 copies it VERBATIM into the summary
   │
   ▼
continuation wrapper places the summary at the top of the new context
   │
   ▼
constraint is back in-context and still binding for every subsequent turn
```

### If you reimplement this (see usage.md §B)
- Treat the security-preservation rule as **non-negotiable** in your summary
  prompt — keep the verbatim language.
- Never let a summarizer *compress* security constraints; list them in full.
- Keep the on-disk transcript so a constraint can be re-verified against the
  original wording if ever in doubt.
- When in doubt about whether something is a constraint, **carry it** — false
  positives are cheap, a dropped safety rule is not.
