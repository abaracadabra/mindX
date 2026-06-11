# Extraction methodology & provenance

This document records **exactly how and where** the contents of this folder were
obtained, so the work is auditable and **reusable as a template** by another
project that wants to introspect its own Claude Code (or any Bun-compiled CLI).

---

## 1. Where the data lives

Claude Code is **not** installed as a readable `node_modules/.../cli.js`. On this
machine it is a **single-file, Bun-compiled ELF executable** with the entire
minified JavaScript bundle embedded inside it as data.

How I located it:

```bash
which claude
#   /home/hacker/.local/bin/claude          (a launcher shim)

readlink -f "$(which claude)"
#   /home/hacker/.local/share/claude/versions/2.1.168   (the real binary)

file /home/hacker/.local/share/claude/versions/2.1.168
#   ELF 64-bit LSB executable, x86-64 ... dynamically linked ... not stripped
du -sh  /home/hacker/.local/share/claude/versions/2.1.168
#   235M
```

Key facts that shaped the approach:

- **One file, no source tree.** There is no `cli.js`; the JS is a string baked
  into the binary. So normal "open the file and read it" does not apply — you
  have to scan the binary's bytes.
- **`not stripped`** + the JS being stored as plain (uncompressed) UTF-8 means
  prompt text and minified functions are directly greppable as ASCII.
- **Versioned directory.** `versions/` held `2.1.165 … 2.1.168`. Always resolve
  the symlink / launcher first; pin the version you actually extracted from
  (this folder = **v2.1.168**) because offsets and mangled names change per build.

> ⚠️ The bundle stores **two copies** of each prompt (here around byte offsets
> ~122 MB and ~233 MB) and the runnable minified JS sits near ~237–238 MB. Don't
> assume the first hit is the one the runtime uses; cross-check.

---

## 2. The two-step extraction technique

Everything was done with read-only shell tools — no patching, no execution of
the binary, no network. The pattern is **find offset → slice bytes → make
printable**.

### Step A — find byte offsets of an anchor string

`grep -a` treats the binary as text; `-o -b` prints the **byte offset** of each
match. Pick an anchor phrase you expect in the data (a prompt sentence, a
function name, an env-var name):

```bash
BIN=/home/hacker/.local/share/claude/versions/2.1.168

grep -a -o -b "detailed summary of the conversation"  "$BIN"
grep -a -o -b "Primary Request and Intent"            "$BIN"
grep -a -o -b -F 'function wh$('                       "$BIN"   # -F: literal, '$' is not regex
```

Counting hits first is a cheap way to confirm a phrase exists and how many
copies there are:

```bash
grep -a -c "wrap your analysis in" "$BIN"
```

### Step B — slice a window around the offset and make it printable

`dd` copies a byte range without loading the 235 MB file into a tool that would
choke on it. Then normalize non-printable bytes so the text is readable.

Two normalizers, each with a purpose:

```bash
# (1) Long human-readable strings only — best for prose/prompts.
#     Filters out the surrounding bytecode noise entirely.
dd if="$BIN" bs=1 skip=122825000 count=14000 2>/dev/null | strings -n 25

# (2) Keep layout, replace non-printables with spaces — best for minified JS,
#     where you want the exact source characters incl. punctuation.
dd if="$BIN" bs=1 skip=237413400 count=2600 2>/dev/null | tr -c '[:print:]' ' '
```

- Use `strings -n N` when you want **clean English** (prompts, UI copy). A high
  `-n` threshold (20–25) skips short bytecode fragments.
- Use `tr -c '[:print:]' ' '` (or `'\n'`) when you need the **literal code**
  including `{}();=$` so you can de-minify it.

### Step C — verify, then de-minify by hand

- Re-extract from the **second copy** at a different offset and diff — if both
  regions agree, you have the real string, not a coincidental fragment.
- For code, copy the minified one-liner into a `.js` file and rename mangled
  identifiers (`cn`, `wh$`, `hE4`…) with readable aliases **in comments**, keeping
  the originals so the file stays greppable against the binary.

---

## 3. Exact commands used for each artifact in this folder

| Artifact | Anchor | Commands |
|----------|--------|----------|
| `auto_compact_prompt.txt` / `manual_compact_prompt.txt` | `"detailed summary of the conversation"`, `"Primary Request and Intent"` | `grep -a -o -b` → `dd ... skip=122825000 count=14000 \| strings -n 25` |
| `continuation_wrapper.txt` | `"This session is being continued"` | `grep -a -o -b` → `dd ... skip=122841100 count=2000 \| strings -n 20`; assembly code via `dd ... skip=233935300 \| tr -c '[:print:]' ' '` |
| `trigger_logic.js` | `-F 'function wh$('`, `"CLAUDE_CODE_AUTO_COMPACT_WINDOW"`, `"precomputeBufferFraction"` | `grep -a -o -b -F` → `dd ... skip=237412719 count=520` and `dd ... skip=237413400 count=2600`, both piped through `tr -c '[:print:]' ' '` |

(Offsets are **v2.1.168-specific** — recompute them on any other build.)

---

## 4. Reusing this as a template for another project

If you want to do the same extraction in a different repo / for a different CLI:

1. **Resolve the real binary.** `readlink -f "$(which <tool>)"`, confirm with
   `file`. If `file` says `ELF ... not stripped` and the binary is tens/hundreds
   of MB, it is almost certainly a Bun/Node single-file build with embedded JS —
   this technique applies. If it's a thin shim pointing at a real `*.js`, just
   read that file instead.
2. **Pin the version.** Copy the version string into your doc and into the
   filename/commit message. These bundles change weekly; offsets and minified
   names are not stable. Re-derive, don't trust a previous run's offsets.
3. **Anchor on stable English, not mangled names.** Prompt sentences and
   env-var names (`CLAUDE_CODE_AUTO_COMPACT_WINDOW`) survive across builds far
   better than identifiers like `wh$`. Find by prose, then walk outward to code.
4. **Always cross-check duplicate copies** before trusting a string.
5. **Keep the raw + the de-minified side by side.** Store the verbatim text in
   `.txt` and your annotated reconstruction in `.js`/`.md`, and label which is
   which. Never silently "clean up" a verbatim prompt — downstream readers may
   need it byte-exact.
6. **Drop a reproduction block** (like §2 above) so anyone can re-verify against
   their own install.

### Make it a script

A minimal, project-agnostic helper:

```bash
#!/usr/bin/env bash
# extract.sh — dump the byte-region around an anchor string in a binary.
# usage: ./extract.sh <binary> <anchor> [pre_bytes] [count] [minlen]
set -euo pipefail
BIN=$1; ANCHOR=$2; PRE=${3:-200}; COUNT=${4:-4000}; MINLEN=${5:-20}
OFF=$(grep -a -o -b -F "$ANCHOR" "$BIN" | head -1 | cut -d: -f1)
[ -n "$OFF" ] || { echo "anchor not found"; exit 1; }
echo "# anchor '$ANCHOR' at byte offset $OFF" >&2
dd if="$BIN" bs=1 skip=$((OFF - PRE)) count="$COUNT" 2>/dev/null \
  | strings -n "$MINLEN"
```

```bash
./extract.sh "$(readlink -f "$(which claude)")" "detailed summary of the conversation"
```

---

## 5. Handling cautions (read before reusing)

- **Read-only.** Every command here only *reads* the binary. Do not modify,
  repack, or redistribute the vendor binary. Extracting strings for **personal
  understanding / interop** is one thing; republishing proprietary prompt text
  may carry licensing/ToS implications — check the tool's license before sharing
  the verbatim `.txt` files outside your team.
- **No secrets.** This extraction targets *prompts and control logic*, which are
  not credentials. Don't use the same blunt `grep -a` sweep to fish for tokens —
  and if you ever see something secret-shaped in a binary, don't copy it into a
  repo.
- **Performance.** `dd bs=1` is byte-granular and slow on huge ranges; keep
  `count` to a few KB around a known offset rather than scanning the whole file.
  For broad scans, prefer `grep -a` (memory-mapped) over piping the whole binary
  through `tr`.
- **Snapshot, not API.** Treat all recovered constants/identifiers as a
  point-in-time snapshot. Nothing here is a supported interface; it can change or
  vanish in the next release.
