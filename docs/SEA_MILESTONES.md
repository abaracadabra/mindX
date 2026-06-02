# SEA Milestones — when mindX flags an evolution moment

SEA (Strategic Evolution Agent — `agents/learning/strategic_evolution_agent.py`)
runs improvement campaigns continuously. Most successful campaigns are
**routine**: an audit finds nothing actionable, or a small fix lands without
fanfare. A few are **milestones**: real evolution moments where the system
shifts meaningfully.

## Why the distinction

The autopublishing pipeline (`docs/publications/README.md`) routes routine
SEA successes through the orchestrator's terse generic template ("What I
learned: …"). Milestones get routed through `AuthorAgent.compose_milestone_article`
— a richer, first-person, cypherpunk2048-voice article that pulls BDI plan id,
validation pass/fail counts, audit findings addressed, and before/after
metrics. AuthorAgent is the canonical writer (precedent at
`agents/learning/improvement_journal.py:76-87`); the orchestrator owns the
publish, ledger, and rate-limit.

## How SEA decides

`SEA._is_milestone(status, data)` returns `True` iff **all** of these hold:

- `status == "SUCCESS"` (FAILURE / NO_WORK never qualifies)
- `campaign_data.validation_results.passed >= 1`
- `campaign_data.audit_results.findings_resolved >= 1`
- `campaign_data.validation_results.resolution_rate >= THRESHOLD`

Where `THRESHOLD` defaults to `0.8` (matching the EXCELLENT grade band at
`strategic_evolution_agent.py:1112`). Operators can tune via env:

```bash
MINDX_SEA_MILESTONE_RESOLUTION_THRESHOLD=0.9   # stricter — fewer milestones
MINDX_SEA_MILESTONE_RESOLUTION_THRESHOLD=0.6   # looser — more milestones
```

The flag is set once in `_conclude_campaign` and travels on the existing
`sea.campaign.concluded` coordinator event (`is_milestone: true|false`).
No new event topic. Backwards-compatible with any subscriber that ignores
the field.

## How publishing routes

`PublicationOrchestrator.on_sea_campaign_success` checks the flag:

```python
kind = "sea_milestone" if data.get("is_milestone") else "sea_campaign_success"
```

- Routine `sea_campaign_success` → orchestrator's internal `_compose_sea_article`
  template (300-500 words). Status defaults to `publish`. Rate-limited by `MIN_GAP_S`.
- `sea_milestone` → `AuthorAgent.compose_milestone_article(campaign_summary)`
  (600-1200 words). Status defaults to `publish` (env override:
  `MINDX_PUBLICATION_MILESTONE_STATUS`). **EXEMPT from `MIN_GAP_S`** — a
  milestone is rare by construction (~weeks apart) and must not be coalesced
  into a routine SUCCESS that happened to land in the same 6-hour window.

Trigger-id collision avoidance: routine SUCCESS uses `<campaign_run_id>`,
milestone uses `sea_milestone_<campaign_run_id>`. Same underlying campaign
can never end up published twice with the same id.

## Conservatism

The heuristic is intentionally biased toward **false negatives** (missed
milestones are silent; false positives become noisy public rage posts). If
SEA fires zero milestones for a stretch, that is fine — the routine
`sea_campaign_success` path still publishes the everyday improvements.
The bar for "milestone" should reflect real evolution moments, not normal
operation.

## Tuning loop

If milestones feel too rare or too frequent in practice, adjust
`MINDX_SEA_MILESTONE_RESOLUTION_THRESHOLD` and restart `mindx.service`.
No code change needed.

## See also

- `docs/publications/README.md` — full autopublish surface table
- `agents/learning/strategic_evolution_agent.py` `_is_milestone()` + `_conclude_campaign`
- `agents/author_agent.py` `compose_milestone_article`
- `agents/publication_orchestrator.py` `on_sea_campaign_success` + `_EXEMPT_FROM_MIN_GAP`
