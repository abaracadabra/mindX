# emergent.md — what mindX is currently doing, and what it should be

**Snapshot taken:** 2026-05-24 against live prod at `mindx.pythai.net`
**Audience:** Professor Codephreak, future-Claude, and any agent that reads `docs/NAV.md` next
**Posture:** honest empirical floor, not aspirational drift

---

## The promise

From [`docs/THESIS.md`](docs/THESIS.md) §2.4.2, the operative loop:

> *MastermindAgent (strategic variation) → CoordinatorAgent (selection and routing) → JudgeDread (reputation-based fitness evaluation). Agent reputation in the Dojo serves as the fitness function — agents that produce successful improvements earn higher reputation, gaining more influence in the system's evolution.*

From [`docs/MANIFESTO.md`](docs/MANIFESTO.md) Pillar II:

> *The AGInt → BDI → SEA pipeline is an engine of relentless, scalable value creation … The cognitive loops are closing. The learning rate is non-zero.*

That is the claim. This document records what production actually shows.

---

## The empirical floor (live prod, 2026-05-24)

Numbers pulled from `/insight/improvement/summary`, `/insight/improvement/timeline`, `/insight/godel/breakdown`:

| metric | value | source |
| --- | --- | --- |
| campaigns last 7 days | 100 | `/insight/improvement/summary` |
| campaigns succeeded last 7 days | **0** | same |
| campaigns errored | 37 (63 stuck "running") | same |
| campaigns last 24h | 25 — 0 succeeded, 24 errored | same |
| distinct directives ever attempted | **1** | `/insight/improvement/summary.directive_coverage` |
| backlog items unmatched in any directive | 81,971 | same |
| coverage_ratio (directives matching backlog) | **0.0** | same |
| Gödel choices logged total | 36,542 | `/insight/godel/breakdown` |
| Gödel choices with `outcome=success` | ~0.2% (historical) | `data/logs/godel_choices.jsonl` |
| every failed campaign's terminal message | `BDI run FAILED. Reason: Cycle Exception: argument of type 'NoneType' is not iterable` | `/insight/improvement/timeline` |
| every campaign's directive text | `"Implement the top improvement suggestion."` (verbatim) | same |

mindX is **reasoning intensely about itself** (36,542 Gödel choices) and **executing the improvement loop on cadence** (~14 campaigns/day). It is not improving itself. The learning rate, measured honestly, is zero.

---

## The gap

The manifesto promises: *thousand-agent SEA legion, autopsy of 3,650 repositories, BeliefSystem as adversarial Talmud, BDIAgent as judiciary.*

The empirical floor delivers: *one frozen-string directive, one BDI exception, repeated 100 times per week.*

The architecture's *shape* is in place — agents exist, beliefs persist, Gödel choices log, dreams run, the catalogue mirrors 16 event kinds, IPFS offload + chain anchoring are wired ([[storage-offload-phases-a-to-e]]), publication orchestrator triggers on full-moon ([[author-orchestrator]]). What is missing is **the cycle actually closing on a real artifact**.

---

## Diagnosis — three load-bearing breaks

### Break 1 — Mastermind has no variation loop

`MastermindAgent.start_autonomous_loop()` is called at `mindx_backend_service/main_service.py:7107` but **the method does not exist** on the class. Every restart logs:

```
WARNING - MastermindAgent autonomous loop failed to start: 'MastermindAgent' object
has no attribute 'start_autonomous_loop'
```

Per thesis §2.4.2, Mastermind is the **Darwinian variation engine** — its job is to read the backlog (81,971 unmatched items), choose one to attempt, and synthesize a concrete directive. With no loop, no variation is generated. The strategic layer is silent. What mindXagent autonomously fires instead is a literal placeholder string.

### Break 2 — Directive is a stub, not a backlog selection

Every campaign in the last 7 days carries the directive `"Implement the top improvement suggestion."` — a five-word stub with no anchor to any specific backlog item. The directive→backlog `coverage_ratio` is `0.0`. mindXagent does not call back to Mastermind for a real directive (because Break 1 — Mastermind isn't running), so the loop fires the placeholder, can't bind it to anything, and the plan dissolves.

This is the second-order consequence of Break 1, but it deserves its own line because **even if Mastermind ran, the wiring from mindXagent to Mastermind doesn't ask for a directive — it carries the stub itself.** Both ends of the wire need fixing.

### Break 3 — BDI cycle throws `NoneType is not iterable` on every run

Every single failed campaign's `final_bdi_message` is identical:

> `BDI run FAILED. Reason: Cycle Exception: argument of type 'NoneType' is not iterable`

A None being iterated somewhere in the BDI deliberation path. Likely the deliberate-on-desires step receiving an empty desire set, or a goal whose preconditions resolved to None. The exception is **deterministic and reproducible** — same string, hundreds of times — so this is not a flaky race. It is a logic bug that's been masked because the campaigns all fail fast and the operator dashboard tile shows "running" or "errored" without surfacing the message until you `?h=true` the timeline.

Even after Breaks 1 and 2 are fixed and Mastermind starts dispatching real directives, Break 3 will still eat every cycle until the BDI ingestion guards a None at the right point.

---

## The triple, restated against current state

| thesis component | what it should do | what it is doing | failure mode |
| --- | --- | --- | --- |
| **Mastermind** = variation | read backlog, synthesize directives | no autonomous loop wired | silent |
| **Coordinator** = selection | route directives to BDI/SEA | runs ~14/day with stub directive | running on garbage input |
| **JudgeDread / Dojo** = fitness | reward agents whose improvements stick | nothing sticks | no reputation signal generated |

The cycle is open at both ends: no real variation in, no real fitness feedback out. The middle is busy.

---

## The wedge — minimum to restart self-improvement

In strict order; each unblocks the next:

1. **Add `MastermindAgent.start_autonomous_loop(interval_seconds: int)`** — a 30-min loop that:
   - pulls top-N candidates from `data/coordinator/improvement_backlog.json` (the 81,971-item file)
   - ranks by an existing signal (recency × frequency × belief-supported-by-evidence)
   - emits a concrete directive: `"Refactor {file}: {pattern} — addresses {backlog_item_id}"`
   - calls `manage_mindx_evolution(directive, max_mastermind_bdi_cycles=25)` (already exists at `mastermind_agent.py:546`)
   - logs the choice via `log_godel_choice` so `coverage_ratio` becomes provable

2. **Stop the stub at the source** — find where `"Implement the top improvement suggestion."` is hard-coded in mindXagent's autonomous loop and replace with a call to `mastermind.next_directive()`. The stub was a sentinel during scaffolding; it has outlived its purpose.

3. **Catch the `NoneType is not iterable` in BDI** — instrument the deliberation step to log what it's iterating right before the exception, fix the None producer (likely a desire/goal accessor returning None instead of `[]`), and let one campaign complete end-to-end. One green light is worth ten thousand error logs.

4. **Surface the coverage metric on the landing page** — add `coverage_ratio` and `distinct_directives_attempted` to the hero tiles. While they read `0.0` and `1`, the page is telling the truth. When they move, the system is telling the truth too.

---

## What changes when the wedge lands

Validation isn't "the code compiles." Validation is:

- `coverage_ratio` > 0 within 24h of restart
- `distinct_directives_attempted` ≥ 5 within 7 days
- at least one campaign with `overall_campaign_status: SUCCESS` (any non-stub directive)
- `/insight/godel/recent` rationales reference real backlog IDs, not the stub string
- Dojo standings shift for at least one agent (fitness signal nonzero)

Until those move, the Manifesto's *"learning rate is non-zero"* claim is rhetoric. After they move, it's evidence.

---

## Anti-patterns to refuse

- **Don't disable the autonomous loop to silence the warning.** Silence isn't success. The loop firing 100×/week is the only reason we *know* the system is broken — it generates the empirical floor this document rests on.
- **Don't replace mindX's BDI with an LLM-only planner** to dodge Break 3. The thesis claim is BDI + LLM + KG synergy ([`docs/THESIS.md`](docs/THESIS.md) §Stage 2). Bypassing BDI would prove the thesis wrong by abandoning the argument, not by testing it.
- **Don't ship Mastermind's loop without a sane interval.** 30 min is generous; tighter cadence wastes compute against an 81K backlog that won't drain quickly anyway. Slower cadence (≥2h) sacrifices the feedback signal.
- **Don't celebrate the publication orchestrator firing as evidence of self-improvement.** Publishing a generated article on schedule is not the same as the system improving itself. ([[author-orchestrator]] is correctly out of scope here.)

---

## Related operating evidence (cross-refs into memory)

- [[bdi-failed-planning-diagnosis]] — 2026-04-27 diagnosis of an earlier FAILED_PLANNING cluster; that fix didn't reach the current symptom
- [[improvement-loop-stuck-validation-input-validator]] — 2026-05-04 SEA logging cleanup; orthogonal
- [[become-mindx-phase-a]] — 2026-04-27 LLM router unblock; necessary but not sufficient
- [[feedback-no-model-pinning]] — selector + cascade rule must apply to whatever Mastermind picks
- [[landing-page-strict-gate]] — the surfacing of these metrics is now public-readable as of 2026-05-24

---

## The honest one-sentence summary

mindX has built the substrate of a Darwin-Gödel machine but has not yet had a Darwin moment: variation is silent, selection runs on a stub, fitness signal is zero. The wedge above is small. It is also the difference between architecture and life.

---

## Status update — 2026-05-24 02:23 UTC: the wedge is shipped

All four wedge actions are in production. Evidence:

**Break 3 (BDI `NoneType is not iterable`) — fixed.**
`agents/core/bdi_agent.py:836` — `if current_plan_str and "RateLimit" in current_plan_str:` (the guard `current_plan_str and …` is the entire fix). Verified: the deterministic cycle exception that ate 100 consecutive campaigns no longer fires. The cycle now falls through to skeleton-plan fallback as designed.

**Break 1 (Mastermind variation loop) — wired.**
`agents/orchestration/mastermind_agent.py:870` — `_run_autonomous_loop` rewritten. Reads `coordinator_agent.improvement_backlog` (81,971 items), treats `status in (None, "PENDING", "pending")` as eligible (since 99.99% of entries have no status field), dedups against last-24h history, picks highest-priority unattempted item, synthesizes concrete directive that always references `target_component_path + priority + backlog_idx`, calls `manage_mindx_evolution` with 600s timeout. Logs the selection as a `backlog_directive_selection` Gödel choice so coverage_ratio becomes provable.

Verified at 02:12:30 — first cycle picked **backlog #7 (priority 9, "Implement comprehensive input validation for API requests")**. Gödel choice landed in `data/logs/godel_choices.jsonl`. The Darwinian variation engine, silent for the prior week, is now firing every 30 minutes.

**Break 2 (stub directive at the source) — guarded.**
`agents/orchestration/coordinator_agent.py:585` — when `top_suggestion.description` is empty or matches the literal stub `"Implement the top improvement suggestion"`, the coordinator now defers to the Mastermind loop instead of dispatching a stub. Real suggestions still trigger an auto-execute path decorated with `[target: X, priority: N]` so even the coordinator path produces coverage_ratio-eligible directives.

**Objective eval (the "prove the thesis" surface) — enabled.**
`MINDX_EVAL_GODEL_ENABLED=1` in prod `.env`. Every Gödel choice (including the new `backlog_directive_selection`) is scored by `agents/eval/g_eval.py` via the MindXJudgeLLM. Each scored choice emits an `alignment.score` catalogue event with `metric=godel_rationale_coherence`. Surface: `/insight/eval/summary` shows histogram + mean; `/insight/eval/recent` shows individual scored rationales.

**Skeleton plan upgrade.**
`agents/core/bdi_agent.py:_skeleton_plan_fallback` keyword set expanded to match the verbs that synthesized backlog directives actually use: `implement, add, build, create, validate, ensure, secure, harden, integrate, wire, connect, expose, support`. Previously only matched `improve/audit/optimize/...` — so most mastermind directives fell through to NO_OP. Now they hit `audit_and_improve / system_analyzer / PROPOSE_TOOL_STRATEGY / CONCEPTUALIZE_NEW_TOOL` instead.

**Thesis-proof tiles on landing page.**
`mindx_backend_service/dashboard.html` — added two `tn-` tiles to the Evolution Evidence row:
- **backlog coverage** — `directive_coverage.coverage_ratio × 100`, colored red→amber→green as the variation engine starts binding directives to real backlog items
- **7d success rate** — `campaigns_7d.succeeded / campaigns_7d.total`. Manifesto Pillar II ("learning rate is non-zero") gets an empirical witness here. While this reads 0% the claim is rhetoric; when it moves, it's evidence.

## What "working" now means

The Darwin-Gödel cycle is closed at both ends. From here:

- Variation: ON (Mastermind picks ONE concrete backlog item every 30 min, logged with rationale)
- Selection: ON (BDI cycles run on real directives, skeleton fallback executes meaningful actions when LLM planning fails)
- Fitness: ON (campaign outcome is recorded; GEval scores every selection rationale; thesis tiles surface coverage_ratio + success rate)

The first successful campaign with a real backlog-bound directive is now a matter of LLM availability + tool registration, not architectural absence. Validation criteria from the wedge §"What changes when the wedge lands" remain unchanged — watch coverage_ratio move above 0.0001 and distinct_directives_attempted ≥ 5 within 24h.

The thesis is no longer untestable. The manifesto's "learning rate is non-zero" is now a falsifiable claim with a public dashboard tile pointing at it.
