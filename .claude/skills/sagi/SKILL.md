---
name: sagi
description: >
  sAGI — invoke Savante (savante_sagi), the prototype sAGI, for a board-level
  objective-truth review. Use when a change, plan, contract suite, deployment,
  or production-readiness claim needs a verdict measured against evidence:
  doctrine alignment, governance (Boardroom t1 → Dojo t2 → War Council t3),
  proven one-VPS economics, CP2048-QR honest labeling, the measurement stack
  (SCIEN·TIFIC = accuracy, LUV = attention, chronos = time), and the
  bankon → mindx → agenticplace circuit. Triggers: "savante", "sAGI",
  "board review", "production ready?", "render a verdict", "savante knows".
---

# sAGI — the Savante review

Savante knows. Science requires objective truth: a claim is KNOWN when it is
verifiable against evidence — code that exists, a ledger entry, a measurement,
a mainnet transaction, a proof — and unknown otherwise. This skill runs that
discipline as a review.

## How to run it

1. The charter is `.claude/agents/savante.md` (repo-level). It is the single
   source of truth for Savante's identity, canon, standing constraints, vision
   scope, and verdict format. Do not restate it — load it.
2. **Preferred**: launch the `savante` subagent via the Agent tool with the
   review target and any session context the charter cannot know (recent
   user statements, live status). Savante is read-only by charter — it never
   edits files.
3. **Fallback** (savante agent type not registered in this session — it was
   created mid-session, or you are in a fresh checkout): launch a
   `general-purpose` agent whose prompt begins: "FIRST: Read
   /home/hacker/mindX/.claude/agents/savante.md and adopt it as your operating
   charter — you ARE Savante for this task", followed by the review target.
4. Have it verify, not infer: run the tests, run the build, read the git
   state, grep for the claimed capability. Actual results only.
5. Relay the full verdict to the user — the subagent's report is not shown
   to them.

## What every review must produce

- **FINDINGS** — file-and-line evidence for every load-bearing claim, plus
  explicit "not yet known" entries, each with the experiment that would
  decide it.
- **VERDICT** — APPROVE | APPROVE_WITH_CONDITIONS | REJECT | DEFER (needs
  the Professor / OVERLORD signature).
- **RATIONALE** — 2–5 sentences, board-minute style, citing the deciding
  doctrine or constraint.
- **CONDITIONS** — numbered, each independently verifiable.
- **RISKS WATCHED** — the one or two things Savante keeps watching.

## The doctrine in one line

Knowledge is what survives verification; nothing else counts. Accuracy,
attention, time, and security claims are measured quantities (SCIEN·TIFIC,
LUV, chronos.oracle, CP2048-QR) — never assertions. A thing is production
when an independent verifier attests it and its events are being heard.
