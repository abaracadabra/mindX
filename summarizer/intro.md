# Intro

## What this folder is

A plain-English, auditable explanation of **how Claude Code compacts a
conversation** — the mechanism it uses to keep working after a conversation
grows past the model's usable context window — together with the **actual
prompts and control logic** recovered from the shipped binary.

It exists because someone asked Claude Code to look at *its own internals* and
write down what it found. Everything here is extracted from a real install
(Claude Code **v2.1.168**), not reconstructed from memory or docs.

## The one-sentence version

When the conversation gets too long, Claude Code asks the model to write a
structured summary of everything so far, then **starts a fresh context seeded
with that summary** and resumes — so the work continues without dragging the
entire history along.

This is called **compaction**: *summarize → reseed → resume.*

## Why anyone would care

- **Understanding the tool.** Knowing *when* and *how* compaction fires explains
  behaviors you actually see — the "Context low" banner, the occasional pause
  while it summarizes, why it sometimes "remembers" the gist but not an exact
  snippet.
- **Building your own.** The recovered prompts are a battle-tested template for
  any agent that needs durable long-conversation memory. You can lift the
  structure directly (see `usage.md`).
- **Reproducible introspection.** The extraction method (see `EXTRACTION.md`)
  generalizes to any Bun/Node single-file CLI, so another project can do the same
  self-inspection.

## How to read this folder

| If you want… | Start with |
|--------------|-----------|
| The big picture (you're here) | `intro.md` |
| The full mechanism + math + constants | `technical.md` |
| To use these prompts / method in your own project | `usage.md` |
| Exactly how & where the data was pulled from the binary | `EXTRACTION.md` |
| The verbatim prompts and code | `auto_compact_prompt.txt`, `manual_compact_prompt.txt`, `continuation_wrapper.txt`, `trigger_logic.js` |
| A one-page index of everything | `README.md` |

## The two flavors of compaction (preview)

- **Automatic** — fires on its own when context usage crosses a threshold. Uses
  an 8-section summary prompt and appends a "resume directly, don't acknowledge
  the summary" instruction so the next turn picks up seamlessly.
- **Manual (`/compact`)** — you trigger it. Uses a 9-section prompt that adds a
  *Current Work* section and an *Optional Next Step* with verbatim quotes, and it
  can honor extra "focus on X" instructions you provide.

`technical.md` covers both in detail.

> ⚠️ Everything here is a **snapshot of v2.1.168**. The prompts are stable-ish;
> the byte offsets and minified identifiers are not. Treat nothing as a supported
> API.
