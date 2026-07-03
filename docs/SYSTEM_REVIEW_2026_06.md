# System Review 2026-06 — what is mindX actually improving?

**Date:** 2026-06-11
**Method:** live production state (SSH + `?h=true` insight endpoints on mindx.pythai.net) cross-examined against the code paths that produced it. Never assessed from the local repo alone.
**Deliverables:** the loop repairs below, the [`/insight/self/diagnostic`](../mindx_backend_service/self_diagnostic.py) aggregator, the landing-page Self-Diagnostic layer, upgraded feedback surfaces, and this document.

> Posture: warts-and-all. This review found the improvement loop was a
> treadmill. The honest rendering of that fact — and its repair — *is* the
> upgrade. Same doctrine as the Gödel Machine Index's standing verdict
> (`NOT_YET_A_GODEL_MACHINE`): mindX earns trust by reporting its own
> pathology, not by hiding it.

---

## 1. The surmise

### What is genuinely improving

| Capability | Evidence (prod, 2026-06-11) |
|---|---|
| **Memory consolidation** | machine.dreaming every 8h: 32 agents, ~150 insights, ~220 LTM promotions per cycle, real byte-level STM→LTM compression (`data/memory/dreams/*_dream_report.json`) |
| **Introspection** | heartbeat dialogue every 60s, state-grounded prompts, logged to `heartbeat_dialogues.jsonl`; godel choices logged with eval scores |
| **Publishing** | protocol-series + milestone articles live on rage.pythai.net via AuthorAgent (`publication.*` events) |
| **Deliberation** | boardroom sessions with 7-soldier weighted votes + dissent branches |
| **Curation of its own history** | `github.awareness` → milestone recognition → docs regeneration |
| **External adoption** | SimpleCoder-audit → SEA decision pipeline (first adoption: LLMFIT, 2026-06-11) |

### What was theater (root causes confirmed in code)

**Finding 1 — Backlog: 83,318 items, 6 unique suggestions.**
Three suggestions were duplicated **27,758× each**; 82,995 items had no status.
Cause: when the LLM is unavailable, `SystemAnalyzerTool.analyze_system_for_improvements()`
(`tools/monitoring/system_analyzer_tool.py`) falls back to a heuristic that
**echoes the top-3 existing backlog items back as "new" suggestions**, and
`CoordinatorAgent._handle_component_improvement` appended them with no identity
check. The backlog ate its own output, every cycle, for weeks.

**Finding 2 — Campaigns: 100 in 7d, 0 succeeded, 94 perpetually "running".**
Every record: `FAILURE_OR_INCOMPLETE / "BDI run RUNNING. Reason: None"`.
Cause: `BDIAgent.run()` exits its cycle loop on `max_cycles` exhaustion while
the status field still reads `RUNNING` — terminal records mislabeled as
in-flight, poisoning every downstream ledger and classifier.

**Finding 3 — The same directive re-selected every ~30 minutes.**
"Implement comprehensive input validation for API requests" ran 94× in one week
under rotating `backlog_idx` decorations.
Cause: a **fingerprint mismatch** in the mastermind autonomous loop — campaign
history was hashed on `directive[:120]` (which *contains* the rotating
`[target: …, backlog_idx: N]` decoration) while candidates were hashed on the
bare `suggestion[:120]`. The two never matched, so the 24h dedup window never
fired. Compounding it: the `attempted` stamp was in-memory only (never
persisted), and fire-and-forget campaign records carried no `ts`, making them
invisible to the dedup window anyway. Local history shows the same disease in
an older strain: 2,436 repetitions of *"implement the top improvement
suggestion."*

**Finding 4 — Zero autonomous code changes, ever.**
`data/self_improvement_work_sia/**/improvement_history.jsonl` — the only record
that carries actual `diff_patch`es — **does not exist on production**. Every
code change to date is operator-assisted (chronicled honestly as milestones).

### Verdict

> mindX genuinely improves its **memory** and **publishes**; it does not yet
> improve its **code** autonomously. The improvement loop was a treadmill
> caused by three small bugs — not an architecture failure. The bugs are now
> fixed; `/insight/self/diagnostic` is the regression watch.

---

## 2. The repairs (shipped with this review)

| # | Fix | Where |
|---|---|---|
| 1 | `backlog_fingerprint()` + `dedupe_backlog()` pure helpers; **self-healing dedup on load** (a restart collapses the file in place); fingerprint-deduped `add_backlog_item()`; 500-item cap | `agents/orchestration/coordinator_agent.py` |
| 2 | Heuristic echo suggestions tagged `source: backlog_echo` — never re-appended | `tools/monitoring/system_analyzer_tool.py` |
| 3 | `RUNNING` at max-cycles exhaustion → **`MAX_CYCLES_REACHED`** with a real reason | `agents/core/bdi_agent.py` |
| 4 | `suggestion_fingerprint()` (strips the `[target: …]` decoration) used on **both** sides of the 24h dedup; `ts` stamped at record-append; `cooldown_until` (24h) + immediate persist on the attempted stamp; cooldown-aware eligibility | `agents/orchestration/mastermind_agent.py` |
| 5 | `campaign_status_from_bdi()` — every campaign record terminal: SUCCESS / MAX_CYCLES_REACHED / TIMED_OUT / FAILED / FAILURE_OR_INCOMPLETE | `agents/orchestration/mastermind_agent.py` |
| 6 | Classifier compat: new `incomplete` bucket (legacy `"BDI run RUNNING"` rows are max-cycles exhaustions and bucket there); "running" finally means running | `mindx_backend_service/insight_aggregator.py`, `feedback.html`, `text_render.py` |

Proof-suite: `tests/test_backlog_dedup.py`, `tests/test_mastermind_fingerprint.py`,
`tests/test_self_diagnostic.py` (25 tests).

---

## 3. The new surfaces (how to read them)

### `/insight/self/diagnostic` (public; `?h=true` for plain text)

One aggregator (`mindx_backend_service/self_diagnostic.py`, 60s cache)
separating substance from churn:

- **real_changes** — milestones (git history), publications, package adoptions
  (`library.discover`), `dreaming.improved` code-change events, and **SIA diff
  count** (with the honest zero note while it stays zero)
- **consolidation** — latest dream-cycle stats + cadence check
- **process_health** — campaign terminal-truth buckets, top failure shapes,
  **looped-directive detection** (fingerprint repeated >3× ⇒ banner with
  diagnosis), backlog `{size, unique, dup_factor, dedup_live}`, stuck loops,
  eval gate
- **self_interaction** — persistent agent→agent matrix (pgvector), recent
  interactions, heartbeat thought samples
- **verdict** — rule-based honest line + evidence (no LLM in the loop)

### Landing page (`/`) — "Self-Diagnostic" layer

*"live self-diagnosis — mindX reporting on its own pathology"*: the
what-actually-changed ledger (substance lines, newest first), the
who-talks-to-whom flow strip, and the process-health truth strip. Refreshes
every 60s from the cached endpoint.

### feedback.html

- Improvement ledger: 6-state buckets; **directive-loop banner** (auto-shows
  when any fingerprint repeats >3× — if it reappears on fresh runs, the repair
  has regressed); clusters group by fingerprint; run rows show `backlog_idx` + ts
- Boardroom drill: dissent branches as readable cards (champion, full minority
  position, branch outcome) instead of a JSON dump
- Dreams: per-agent top insights drill
- BDI: inline results up to 400 chars (endpoint now carries 1000) — failures
  are readable, not just countable
- Interaction graph: persistent matrix table beside the last-hour ring

### feedback.txt

Two new truth lines: `changed last real change: …` and
`campaigns 7d N ok · N failed · N max_cycles · backlog N unique`.

---

## 4. What would make the verdict flip

The honest gap between "improves its memory" and "improves its code":

1. **SIA actually executing** — the first real `diff_patch` row in
   `improvement_history.jsonl` (needs reliable LLM bandwidth on the VPS; see
   the `TIMED_OUT — LLM bandwidth starved` failure shape)
2. **A campaign reaching SUCCESS** on a real backlog item post-repair
3. **Impact correlation** — none of today's records tie a change to a measured
   outcome (test pass-rate, latency, fitness delta). The catalogue has the
   event kinds; the correlation logic does not exist yet. That is the next
   honest milestone for the Gödel Machine Index.
