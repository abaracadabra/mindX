# Technical deep-dive

Full mechanism of Claude Code conversation compaction, as recovered from the
binary **v2.1.168**. For *how* the data was extracted see `EXTRACTION.md`; for
the verbatim artifacts see the `.txt` / `.js` files; this document explains how
they fit together.

---

## 1. The lifecycle: summarize → reseed → resume

```
   long conversation
          │
          ▼
   usage crosses threshold (level: "compact")   ── trigger_logic.js
          │
          ▼
   separate LLM call with the summary prompt     ── auto_/manual_compact_prompt.txt
          │  (model thinks in <analysis>…</analysis>, then emits numbered sections)
          ▼
   summary text
          │
          ▼
   new context = continuation prologue + summary (+ verbatim recent msgs)
          │                                         ── continuation_wrapper.txt
          ▼
   resume work (auto flavor: "do not acknowledge the summary, continue directly")
```

The old turn-by-turn history is dropped from the live context; the summary
becomes the new "memory." A pointer to the **full transcript on disk** is
included so exact snippets can be re-read on demand if needed.

---

## 2. The two summary prompts

Both prompts share a spine: **(a)** wrap reasoning in `<analysis>` tags first,
**(b)** chronologically walk every message, **(c)** emit a fixed set of numbered
sections, **(d)** preserve security constraints and user messages *verbatim*.

### Automatic — `auto_compact_prompt.txt` (8 sections)

Used when compaction fires on its own. Framed as "this summary will be placed at
the start of a continuing session." Sections:

1. Primary Request and Intent
2. Key Technical Concepts
3. Files and Code Sections (with full snippets + why each matters)
4. Errors and fixes
5. Problem Solving
6. **All user messages** (verbatim, incl. security constraints)
7. Pending Tasks
8. Work Completed
9. Context for Continuing Work

### Manual — `manual_compact_prompt.txt` (9 sections)

Used for `/compact`. Same spine plus two differences that matter:

- **Section 8 is *Current Work*** — precisely what was happening immediately
  before the summary request.
- **Section 9 is *Optional Next Step*** — and it must include **direct verbatim
  quotes** from the most recent messages "to ensure there's no drift in task
  interpretation," with an explicit warning not to drift onto tangential or
  already-completed work.
- It honors **extra user summarization instructions** ("focus on TypeScript
  changes", "include test output verbatim", etc.) appended via context.

### Why both insist on verbatim preservation

Both prompts call out, in nearly identical language, that **security-relevant
instructions/constraints** and **ALL non-tool-result user messages** must be
copied verbatim *"so they continue to apply after compaction."* Compaction is a
context reset; anything not carried into the summary is effectively forgotten, so
standing constraints are deliberately pinned.

---

## 3. The continuation wrapper

`continuation_wrapper.txt` is the text stitched **in front of** the generated
summary when the new session boots. It is assembled conditionally:

| Fragment | Included when |
|----------|---------------|
| `This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion…` | always |
| `…read the full transcript at: <PATH>` | a transcript path is known |
| `Recent messages are preserved verbatim.` | recent turns kept un-summarized |
| `Your REPL VM state has been cleared…redefine any you still need.` | a live REPL/VM existed (**cold compaction**) |
| `Continue the conversation…Resume directly — do not acknowledge the summary…Pick up the last task as if the break never happened.` | **automatic** compaction only |

That last directive is the reason auto-compaction feels seamless: the model is
explicitly told **not** to say "I'll continue" or recap — just keep going.

---

## 4. When compaction fires — the trigger math

All from `trigger_logic.js`. Mangled names kept so they're greppable in the
binary.

### 4.1 Resolve the window (`cn`)

Pick the effective context budget by precedence, then clamp to the model's true
max context (`tv(model)`):

```
env CLAUDE_CODE_AUTO_COMPACT_WINDOW
  → settings.json value
    → A/B experiment value (opus-4-8 only)
      → model-default (when model max < 1,000,000)
        → "auto" (per-model tuned window, else model max)
```

Window strings are parsed by `ot6`: `"auto"`, `"1m"`→×1e6, `"500k"`→×1e3, a bare
`100..1000` is read as thousands, otherwise a literal token count; result clamped
to `[rt6, CE4]`.

### 4.2 Remaining tokens (`z7H`)

```
remaining = effectiveWindow − min(usedTokens, IE4cap)
```

### 4.3 Threshold (`wh$`)

```
compactThreshold = window − 13000        # NE4 = 13000 tokens of head-room
```

A test override (`CLAUDE_AUTOCOMPACT_PCT_OVERRIDE`) can instead set the threshold
to a percentage of the window (capped at the 13k-head-room value).

### 4.4 The level state machine (`hE4`)

Given current `used` tokens, the active ceiling, and a `configured` ceiling:

| Level | Condition | Effect |
|-------|-----------|--------|
| `blocked` | `used ≥ configured − 3000` (`EE4`), or `CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE` | hard stop — must compact before continuing |
| `compact` | auto-compact enabled **and** `used ≥ compactThreshold` | fire the summarizer |
| `warn` | `used ≥ compactThreshold − 20000` | the **"Context low (N% remaining)"** banner |
| `ok` | otherwise | nothing |

`pctLeft = round((ceiling − used) / ceiling × 100)` drives the percentage shown
in the UI.

### 4.5 Accounting & guards

- **`I1A`** computes prefix tokens vs. the threshold and tallies `document`,
  `image`, and nested `tool_result` blocks — what can be snipped and what the
  compaction reports on. Returns `null` when nothing exceeds the threshold.
- **`st6`** is a *rapid-refill guard*: it counts consecutive compactions that
  recur within `at6` turns, so a conversation that instantly re-fills doesn't
  spin in a compaction loop.

---

## 5. Knobs (environment variables)

| Variable | Effect |
|----------|--------|
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | Override the auto-compact window (`auto` / `500k` / `1m` / `<tokens>`). Highest precedence; takes over the `/config` setting. |
| `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` | Force the compact threshold to a % of the window (testing). |
| `CLAUDE_CODE_BLOCKING_LIMIT_OVERRIDE` | Force the hard-block token limit (testing). |
| `CLAUDE_CODE_COLD_COMPACT` | Enable "cold" compaction — also clears REPL/VM state and emits the REPL-cleared note. |

Recovered numeric constants (v2.1.168): `NE4=13000` (compact head-room),
`EE4=3000` (block head-room), `lt6=0.2` (default `precomputeBufferFraction`),
plus build-internal `IE4`, `rt6`, `CE4`, `RE4`, `at6`.

---

## 6. What this is and isn't

- **Is:** an accurate snapshot of the v2.1.168 compaction prompts + control flow,
  good enough to reimplement the behavior or understand observed UX.
- **Isn't:** a supported API. Identifiers (`cn`, `wh$`, `hE4`…), constants, and
  byte offsets are build-specific and will change. Re-derive against the version
  you actually run.
