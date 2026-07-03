# How Claude Code compacts a conversation

This folder is the result of asking Claude Code to **read its own internals** and
explain how it summarizes ("compacts") a conversation when it runs low on context.

Everything here was extracted directly from the shipped binary:

```
/home/hacker/.local/share/claude/versions/2.1.168
```

That file is a **Bun-compiled, single-file ELF executable (~235 MB, not stripped)**
with the entire minified JS bundle embedded as a string. There is no readable
`cli.js` on disk — the source lives inside the binary. The prompts and logic
below were recovered with `grep -a` / `dd` byte-slicing over that binary, then
de-minified by hand.

## What "compaction" actually is

When a conversation approaches the model's usable context window, Claude Code
does **not** truncate blindly. It makes a separate LLM call that asks the model
to write a structured, lossless-as-possible summary of the conversation so far,
then **starts a fresh context** whose first message is that summary wrapped in a
short "this session is being continued…" prologue. Recent messages can be kept
verbatim after the summary.

So compaction = **summarize → reseed → resume**. There are two flavors:

| Flavor | Trigger | Prompt used | Continuation directive |
|--------|---------|-------------|------------------------|
| **Auto** | usage crosses the threshold (`level: "compact"`) | `auto_compact_prompt.txt` (8 sections) | appends a "resume directly, don't acknowledge the summary" instruction |
| **Manual** (`/compact`) | user runs the command | `manual_compact_prompt.txt` (9 sections, incl. *Optional Next Step* with verbatim quotes) | no auto-resume directive |

Both prompts force the model to first think inside `<analysis>...</analysis>`,
then emit the numbered sections. Both **explicitly require security-relevant
constraints and ALL user messages to be preserved verbatim** so instructions
survive the context reset.

## Files in this folder

### Docs (read these)

| Doc | What it covers |
|-----|----------------|
| `intro.md` | Plain-English overview — what compaction is and how to navigate this folder. **Start here.** |
| `technical.md` | Full mechanism: the two prompts, the continuation wrapper, the trigger math, env knobs, constants. |
| `workflow.md` | End-to-end pipeline from user messages → trigger → summarize → reseed → **security-constraint handling** across the reset. |
| `usage.md` | How to reproduce the extraction, reuse the prompts in your own agent, and adapt this folder as a template. |
| `EXTRACTION.md` | Provenance & methodology — exactly **how and where** the data was pulled from the binary, with a reusable script and handling cautions. |
| `README.md` | This index. |

### Extracted artifacts (verbatim / reconstructed)

| File | What it is |
|------|------------|
| `auto_compact_prompt.txt` | Verbatim prompt for **automatic** compaction (placed at the start of a continuing session). 8 required sections + analysis scaffold + worked example. |
| `manual_compact_prompt.txt` | Verbatim prompt for **`/compact`**. 9 sections — adds *Current Work* and *Optional Next Step* (with verbatim quotes), and honors extra user "focus on X" summarization instructions. |
| `continuation_wrapper.txt` | The prologue text stitched **in front of** the generated summary when the new session boots, including the transcript-path pointer, the "Recent messages are preserved verbatim" note, the REPL/VM-cleared note (cold compaction), and the auto-resume directive. |
| `trigger_logic.js` | De-minified, annotated reconstruction of **when** compaction fires: window resolution (`cn`), threshold (`wh$`), the `ok → warn → compact → blocked` state machine (`hE4`), token accounting (`I1A`), and the rapid-refill guard (`st6`). |

## The decision in one paragraph (see `trigger_logic.js` for the real code)

1. **Resolve the window** (`cn`): pick the effective context budget by precedence
   `env CLAUDE_CODE_AUTO_COMPACT_WINDOW` → `settings` → `A/B experiment` →
   `model-default` → `"auto"`, then clamp to the model's true max context.
2. **Compute remaining** (`z7H`): `window − min(usedTokens, cap)`.
3. **Compute the threshold** (`wh$`): fire compaction with **13,000 tokens of
   head-room** (`window − 13000`), unless `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` sets a
   percentage instead.
4. **Classify** (`hE4`): `blocked` at `configured − 3000` (hard stop), `compact`
   at the threshold (fires the summarizer), `warn` 20,000 tokens earlier (the
   "Context low (N% remaining)" banner), else `ok`.
5. A **rapid-refill guard** (`st6`) counts back-to-back compactions to avoid a
   compaction loop on a conversation that re-fills instantly.

## Reproducing the extraction

```bash
BIN=/home/hacker/.local/share/claude/versions/2.1.168

# the prompts
grep -a -o -b "detailed summary of the conversation" "$BIN"
dd if="$BIN" bs=1 skip=122825000 count=14000 2>/dev/null | strings -n 25

# the continuation wrapper
grep -a -o -b "This session is being continued" "$BIN"

# the trigger / threshold logic
grep -a -o -b -F 'function wh$(' "$BIN"
dd if="$BIN" bs=1 skip=237412719 count=520 2>/dev/null | tr -c '[:print:]' ' '
dd if="$BIN" bs=1 skip=237413400 count=2600 2>/dev/null | tr -c '[:print:]' ' '
```

> Notes
> - The bundle contains **two copies** of each prompt (offsets ~122 MB and ~233 MB),
>   and the runnable minified JS lives around the ~237–238 MB region.
> - Mangled identifiers (`cn`, `wh$`, `hE4`, `ot6`, `z7H`, `I1A`, `st6`,
>   constants `NE4=13000`, `EE4=3000`, `lt6=0.2`) are kept so you can grep the
>   binary yourself. They are build-specific and will differ across versions.
> - Verbatim text and constants are exact for **v2.1.168**; treat them as a
>   snapshot, not a stable API.
