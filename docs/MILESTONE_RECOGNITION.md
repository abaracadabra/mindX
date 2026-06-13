# Milestone recognition — mindX recognizes its own achievements

mindX recognizes its own milestones. Not just SEA campaign successes
(yesterday's `is_milestone` flag) — *operational* milestones too: an
autonomous publish landing on rage.pythai.net, a batch of CVEs closed,
the dreaming substrate upgrading itself.

This document is the operator + integrator reference for the subsystem.

## Architecture

```
  coordinator pub/sub                       BeliefSystem (persistent)
  ────────────────────                      ─────────────────────────
  publication.published   ─┐                milestone:publication:post_<id>
  bug.crushed             ─┤   ┌──────┐    milestone:bug_crushed:pr_<n>
  sea.campaign.concluded  ─┼─→ │  MR  │ ─→ milestone:cognitive:sea_<id>
  dreaming.improved       ─┘   └──────┘    milestone:dreaming:<date>_<reason>
                                  │
                                  ▼  (3 side effects, each safe-fail)
                          ┌──────────────┐
                          │  Belief add  │  ← idempotent (check-then-write)
                          ├──────────────┤
                          │  Catalogue   │  ← kind=milestone.recognized
                          ├──────────────┤
                          │  Re-emit     │  ← topic=milestone.recognized
                          │  for         │     consumed by autopublish chain
                          │  downstream  │     (PublicationOrchestrator)
                          └──────────────┘
```

`MR` is the `MilestoneRecognizer` in `agents/core/milestone_recognition.py`.
Construct once at backend startup with a coordinator + belief_system handle;
subscribes to four topics; classifies inbound events via pluggable rules;
persists positive results.

**Architecture invariant**: AuthorAgent writes, PublicationOrchestrator
publishes, MilestoneRecognizer recognizes. Three single-responsibility
cognitive surfaces.

## The four categories

| Category | Trigger event | Heuristic for major / confidence | Autopublish default |
|---|---|---|---|
| `publication` | `publication.published` | Every successful publish (`post_id` present) — confidence 1.0 | `none` (never auto-publish; recursion) |
| `bug_crushed` | `bug.crushed` | ≥5 alerts OR 1+ critical OR 3+ high → major (confidence 1.0); else 0.6 | `publish` if major, `none` if minor |
| `cognitive` | `sea.campaign.concluded` with `is_milestone=true` | Already classified by SEA's `_is_milestone` (resolution_rate ≥ 0.8 + validation pass + finding resolved) — confidence 1.0 | `publish` (same wallet that authors writes the rich milestone article) |
| `dreaming` | `dreaming.improved` | `reason=code_change` → confidence 1.0; `reason=insight_outlier` → 0.7 (borderline) | `draft` (operator review) |

All defaults env-overridable:

```
MINDX_MILESTONE_PUBLICATION_STATUS    (default: none)
MINDX_MILESTONE_BUG_CRUSHED_STATUS    (default: publish)
MINDX_MILESTONE_COGNITIVE_STATUS      (default: publish)
MINDX_MILESTONE_DREAMING_STATUS       (default: draft)
```

Values: `publish` | `draft` | `none`. `none` records the belief + emits
`milestone.recognized` but the autopublish chain skips composition.

## How to fire each category

### 1. `publication.published` — emitted automatically

The `PublicationOrchestrator` fires this after every successful
`AuthorAgent.publish_to_rage()`. You do not need to do anything; the chain
runs on every public + draft publish to rage.pythai.net.

### 2. `bug.crushed` — operator-callable today, auto-bridge later

Operator fires via the admin endpoint after a CVE-batch closes:

```bash
curl -X POST https://mindx.pythai.net/admin/recognize/bug-crushed \
  -H "Authorization: Bearer $MINDX_ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "pr_number": 10,
    "alert_count": 25,
    "severities": {"critical": 1, "high": 11, "moderate": 12, "low": 1},
    "summary": "All 25 open Dependabot alerts closed in one session via PR #10"
  }'
```

The MilestoneRecognizer subscribes to `bug.crushed`, classifies based on the
heuristic, persists the belief, and — if major — fires the autopublish
chain (AuthorAgent.compose_milestone_article with category="bug_crushed").

Auto-bridge from GitHub webhook → `bug.crushed` event is a documented
follow-up.

### 3. `sea.campaign.concluded` — fires automatically on SEA SUCCESS

SEA's existing event already carries the `is_milestone` flag (shipped in
the prior cycle). MilestoneRecognizer adds belief persistence + downstream
surfaces. No new trigger plumbing needed.

### 4. `dreaming.improved` — fires automatically from machine_dreaming

`agents/machine_dreaming.py` has two detectors that fire at the end of
each dream cycle:

- **code_change**: sha256 of `machine_dreaming.py` differs from
  `data/governance/dreaming_baseline.json`'s last-recorded hash. The
  dreaming substrate itself was upgraded.
- **insight_outlier**: `insights_generated` ≥ 1.5× rolling-30 median.
  A dream produced significantly more insights than usual.

Both reasons fire the event with a `reason` field; the classifier weights
confidence by reason (code_change=1.0, insight_outlier=0.7 → borderline).

## Public surfaces

```bash
# Most-recently-recognized milestones, all categories
GET /insight/milestones/recent?limit=20

# Liveness + counts + autopublish defaults
GET /insight/milestones/health

# Filtered per category
GET /insight/milestones/publication/recent
GET /insight/milestones/bug_crushed/recent
GET /insight/milestones/cognitive/recent
GET /insight/milestones/dreaming/recent
```

All support `?h=true` for plain-text rendering. Auth-gated.

## Adding a new category

Append to `RECOGNIZERS` in `agents/core/milestone_recognition.py`. Each
recognizer is a small `RecognizerRule`:

```python
RecognizerRule(
    name="my.new.topic",                              # == coordinator topic
    category="my_category",                           # short ASCII id
    matches_topic=lambda t: t == "my.new.topic",
    classify=_classify_my_new,                        # (payload) → Optional[Milestone]
),
```

Where `_classify_my_new(payload)` returns a `Milestone` instance with
`category`, `key` (prefixed `milestone:<category>:<id>`), `summary`,
`confidence`, `recognizer`, `evidence`, `autopublish_status`.

The rule is automatically subscribed by `MilestoneRecognizer.__init__`
via `topics_to_subscribe()`. No other wiring needed.

To autopublish: add a per-category composer to `AuthorAgent`
(`_compose_<category>_article`) and route the new `category` value in
`compose_milestone_article`'s dispatcher.

## File reference

- `agents/core/milestone_recognition.py` — classifier rules, `Milestone`
  dataclass, `MilestoneRecognizer` class, `classify()` entry point.
- `agents/core/agint.py` — `DecisionType.RECOGNIZE_MILESTONE` reserved
  for Q-learning over the classifier; `_record_milestone` + 
  `get_milestone_health` retained as the cognitive integration hook for
  future LLM-judgment on borderline events.
- `agents/core/belief_system.py` — persistence (read-only here).
- `agents/catalogue/events.py` — `milestone.recognized`,
  `bug.crushed`, `dreaming.improved`, `publication.{attempted,published,coalesced}`
  added to `EventKind`.
- `agents/author_agent.py` — `compose_milestone_article` dispatcher +
  three per-category composers (SEA, bug_crushed, dreaming).
- `agents/publication_orchestrator.py` — emits `publication.*` events
  via `_emit_pub` helper at the three lifecycle points.
- `agents/machine_dreaming.py` — `_maybe_emit_dreaming_improved`
  (code-change + outlier detectors).
- `mindx_backend_service/main_service.py` — startup spawn of
  `MilestoneRecognizer`; `/insight/milestones/*` endpoints;
  `/admin/recognize/bug-crushed` admin endpoint.
- `scripts/backfill_today_milestones.py` — one-shot, idempotent. Writes
  the four 2026-05-22/23 milestones so the ledger starts honest.
- `tests/test_milestone_recognition.py` — 22 tests covering each rule's
  happy/edge paths + env overrides + Milestone shape.
- `data/memory/beliefs.json` — milestone keys `milestone:*` persist here
  via `BeliefSystem._save_beliefs_if_path`.
- `data/governance/dreaming_baseline.json` — file-hash + insight-history
  baseline for the `dreaming.improved` detectors.

## Why this is in `agents/core/`

The user's direction during planning: **use core**. Recognition is the
cognitive layer's job, not a peripheral concern. The MilestoneRecognizer
sits alongside `belief_system.py`, `agint.py`, `bdi_agent.py`. AGInt
holds the hooks for future Q-learning over the classifier
(`DecisionType.RECOGNIZE_MILESTONE`) and for LLM judgment on borderline
events (`is_borderline()` from the recognition module + AGInt's
`_execute_cognitive_task()`). The standalone MilestoneRecognizer fires
during the perception phase regardless of AGInt's lifecycle (AGInt is
constructed on-demand for directives, not at backend boot).

## Deploy-time gotcha (one historical note)

The first deploy of this subsystem wired the subscriber into AGInt's
`__init__`. That subscription never fired because AGInt isn't
constructed at backend startup — it's constructed lazily when a
directive arrives, by which time system events have already happened.
Fix: extract a small `MilestoneRecognizer` class from AGInt; construct
it once at backend startup with the long-lived coordinator. AGInt's
hooks (`_record_milestone`, `get_milestone_health`,
`DecisionType.RECOGNIZE_MILESTONE`) remain as the cognitive-integration
seam.

## Verification

```bash
# 1. Liveness on prod
curl -s https://mindx.pythai.net/insight/milestones/health?h=true \
     -H "Authorization: Bearer $MINDX_ADMIN_API_KEY"

# Expected: recognizer_alive=True, subscribed_topics has 4 entries,
# milestones_total >= 4 (the backfilled set).

# 2. Recent milestones
curl -s https://mindx.pythai.net/insight/milestones/recent?h=true \
     -H "Authorization: Bearer $MINDX_ADMIN_API_KEY"

# 3. Force-trigger a recognition end-to-end
curl -X POST https://mindx.pythai.net/admin/recognize/bug-crushed \
     -H "Authorization: Bearer $MINDX_ADMIN_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"pr_number": 11, "alert_count": 6, "severities": {"high": 6}}'

# 4. Confirm belief written
grep "milestone:bug_crushed:pr_11" /home/mindx/mindX/data/memory/beliefs.json
```

## See also

- `docs/publications/README.md` — the autopublish pipeline (the recognition's
  downstream consumer).
- `docs/WORDPRESS_PUBLISHING.md` — `wordpress.agent` identity + recovery runbook.
- `docs/SEA_MILESTONES.md` — SEA's per-campaign `is_milestone` heuristic
  (the `cognitive` category's trigger).
- `docs/AUTHOR_AGENT.md` — the canonical writer; per-category composers.
