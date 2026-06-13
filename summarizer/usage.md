# Usage

How to (a) reproduce the extraction yourself, (b) reuse the recovered prompts in
your own agent, and (c) adapt this folder as a template for another project.

---

## A. Reproduce the extraction

Read-only. No patching, no running the vendor binary, no network. See
`EXTRACTION.md` for the full rationale; this is the quick path.

```bash
# 1. find the real binary
BIN=$(readlink -f "$(which claude)")
file "$BIN"          # expect: ELF ... not stripped  (Bun single-file build)

# 2. find a prompt by anchor sentence
grep -a -o -b "detailed summary of the conversation" "$BIN"

# 3. slice the region and keep only long human strings
dd if="$BIN" bs=1 skip=122825000 count=14000 2>/dev/null | strings -n 25

# 4. for the trigger CODE, keep punctuation instead
grep -a -o -b -F 'function wh$(' "$BIN"
dd if="$BIN" bs=1 skip=237412719 count=520 2>/dev/null | tr -c '[:print:]' ' '
```

Offsets are **v2.1.168-specific** — re-run step 2/`grep` to get current offsets
on your build. A reusable helper script is in `EXTRACTION.md` §4.

---

## B. Reuse the prompts in your own agent

The two `.txt` prompts are a drop-in template for any LLM agent that needs
durable long-conversation memory. Minimal loop:

```python
from pathlib import Path

HERE = Path(__file__).parent
AUTO = (HERE / "auto_compact_prompt.txt").read_text()
WRAP = (HERE / "continuation_wrapper.txt").read_text()

def maybe_compact(history, used_tokens, window, transcript_path=None):
    # mirror trigger_logic.js: fire 13k tokens before the window is full
    COMPACT_THRESHOLD = window - 13_000
    if used_tokens < COMPACT_THRESHOLD:
        return history                       # nothing to do

    # 1) summarize the old history in a SEPARATE call
    summary = llm([
        {"role": "user", "content": serialize(history)},
        {"role": "user", "content": AUTO},
    ])

    # 2) reseed: prologue + summary become the new first message
    prologue = WRAP.replace("<PATH_TO_TRANSCRIPT>", transcript_path or "")
    seed = f"{prologue}\n\n{summary}"

    # 3) optionally keep the last few turns verbatim after the seed
    return [{"role": "user", "content": seed}, *history[-KEEP_RECENT:]]
```

Recommendations carried over from the real implementation:

- **Make the summary a separate LLM call** over the old history — don't try to
  fold it into the working turn.
- **Force `<analysis>` first.** The prompts make the model reason before writing
  the sections; keep that — it materially improves recall quality.
- **Preserve user messages + security constraints verbatim** (prompt sections 6).
  This is the single most important rule: compaction is a context reset, so
  anything not in the summary is forgotten.
- **Keep a transcript on disk** and reference it in the prologue, so exact
  snippets can be re-fetched instead of bloating every summary.
- **Add a rapid-refill guard** (`st6` analogue) so you don't compact in a loop.
- Use the **manual prompt** when a human triggers it (adds *Current Work* +
  verbatim *Next Step* quotes); use the **auto prompt** for background firing
  (append the "resume directly" directive from the wrapper).

---

## C. Adapt this folder as a project template

1. Copy the folder structure: `intro.md`, `technical.md`, `usage.md`,
   `workflow.md`, `EXTRACTION.md`, `README.md`, plus your extracted `.txt`/`.js`.
2. **Pin the version** you extracted from in `README.md` and `EXTRACTION.md`.
   These bundles change weekly; offsets and mangled names are not stable.
3. Anchor extraction on **stable English / env-var names**, not minified
   identifiers (see `EXTRACTION.md` §4).
4. Keep **raw verbatim** (`.txt`) and **annotated reconstruction** (`.js`/`.md`)
   side by side, clearly labeled. Never silently "tidy" a verbatim prompt.
5. Re-include a **reproduction block** so the next reader can re-verify.

---

## D. Cautions

- **Read-only & license.** Extracting prompts for understanding/interop is fine;
  **republishing** proprietary prompt text outside your team may have
  licensing/ToS implications — check the tool's license first.
- **No secrets.** This targets prompts + control logic, not credentials. Don't
  use a blunt `grep -a` sweep to fish for tokens.
- **Performance.** `dd bs=1` is slow over large ranges — keep `count` to a few KB
  around a known offset; prefer `grep -a` for broad scans.
- **Snapshot, not API.** Nothing here is supported; expect it to change between
  releases.
