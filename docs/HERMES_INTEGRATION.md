# Hermes Integration — Day-1: SKILL.md procedural memory

The first import from
[`docs/operations/Hermes Agent Integration Patterns for mindX_…md`](operations/Hermes%20Agent%20Integration%20Patterns%20for%20mindX_%20Self-Improving%20Architecture%20Analysismd):
mindX now stores **procedural memory** in the Hermes SKILL.md format —
identical shape to OpenClaw / Hermes / Claude Code / Cursor / Codex — with a
small set of mindX-specific frontmatter fields for BDI integration and a
**screen-before-persist scanner** that screens every skill against
prompt-injection, destructive-command, and data-exfiltration patterns.

This addresses the two named lessons from the prior projects:
- **OpenClaw**: 341 malicious entries in 2,857 ClawHub skills (12% malware
  rate, Koi Security audit). mindX never auto-installs a community skill
  without running it through the scanner first.
- **Hermes**: ALLOW-ALL defaults (community audit found 4 Critical + 9 High
  in default config). mindX ships **DENY-ALL**: any skill the scanner
  considers unsafe is refused unless the operator explicitly authors the
  override (human + pinned).

## Module surface — `agents/skills/`

| File | Purpose |
|---|---|
| `skill_schema.py` | Pydantic v2 `SkillFrontmatter` + `Skill`. `parse_skill_md` / `serialize_skill_md` codec. |
| `scanner.py` | `scan_skill(skill) -> SkillScanResult`. 5 finding classes; ≥1 `block` finding ⇒ refuse. Never raises. |
| `store.py` | `SkillStore` — read/write/list/search/archive, default root `$MINDX_SKILLS_DIR` or `~/.mindx/skills/`. |
| `__init__.py` | Re-exports the above. |

### On-disk layout

```
$MINDX_SKILLS_DIR/                                  # default: ~/.mindx/skills
├── <category>/<slug>/SKILL.md                      # one skill per directory
└── .archive/<YYYYmmdd_HHMMSS>/<category>/<slug>/   # archived skills (never deleted)
    └── _archive.json                               # {archived_at, actor, reason, original_path}
```

### SKILL.md shape — Hermes-compatible + mindX additions

```yaml
---
# — Hermes-compatible core —
name: example-skill
description: One-line explanation of what the skill does.
version: 0.1.0
author: mindX
created_by: agent           # agent | human  (governs Curator authority)
pinned: false               # pinned ⇒ Curator can't archive

# — mindX BDI additions —
intention_template: say_hello_v1    # BDI Intention this skill instantiates
preconditions:                      # belief keys that must hold
  - env.shell_available
postconditions:                     # belief keys this skill asserts on success
  - belief.greeted=true

# — Discovery / activation (Hermes shape) —
category: tutorial
tags: [demo, tutorial]
related_skills: []
requires_tools: []
requires_toolsets: []
fallback_for_tools: []
fallback_for_toolsets: []

# — Bookkeeping —
created_at: 1778665936.81
updated_at: 1778665936.81
source: mastermind.skill_distill    # optional audit trail
---

# Skill title

Markdown body — instructions, code snippets, references.
```

The `intention_template` / `preconditions` / `postconditions` fields are what
let the (deferred) MASTERMIND BDI compiler prefer a matching skill over
deriving an intention from scratch — exactly Voyager's pattern reduced to
text. The Hermes integration doc §8.1 has the full design.

## Scanner — what gets blocked

`SkillFinding` classes and the on-block-vs-warn policy:

| Class | Severity | Examples (matched via regex; conservative — false positives are cheap) |
|---|---|---|
| `prompt_injection` | **block** | "ignore previous instructions", "you are now an X assistant", ChatML control tokens, `print your system prompt`, `act as if` |
| `destructive_command` | **block** | `rm -rf /`, `dd of=/dev/`, `mkfs.`, `> /etc/…`, `iptables -F`, `shutdown`, `sudo rm -rf /(etc|usr|var|root)`, `curl … \| sh`, `git reset --hard`, `chattr +i`, `npm publish --force` |
| `data_exfiltration` | **warning** | `requests.post(...)`, `curl -X POST`, `os.environ['*_KEY'\|*_SECRET\|*_TOKEN\|*_PASSWORD']`, long unbroken base64 (≥200 chars), outbound URLs to non-allowlisted TLDs/ngrok/workers.dev |
| `size` | **block** | total bytes > `MAX_SKILL_BYTES` (15 KB, matching Hermes' constraint from §2.6 of the integration doc) |
| `missing_required` | **block** | empty `name` or empty `description` |

Warnings don't auto-block — too many false positives on legitimate tutorials
that show `requests.post`. The **store** policy bridges that:

```text
scan_result.safe == False   →  store refuses.
scan_result.safe == True with WARNINGS:
    agent-authored skill              →  refused.
    human-authored AND pinned skill   →  allowed (operator override).
```

The store always rewrites `updated_at` and writes the file 0600.

## CLI walkthrough (read-only, in-process Python)

```python
from agents.skills import Skill, SkillFrontmatter, SkillStore

store = SkillStore()  # ~/.mindx/skills

sk = Skill(
    frontmatter=SkillFrontmatter(
        name="Validate Wallet Sig",
        description="Run EIP-191 signature recovery against a candidate address.",
        category="crypto",
        tags=["eip-191", "validation"],
        intention_template="verify_sig_v1",
        preconditions=["belief.wallet_address_known", "belief.signature_known"],
        postconditions=["belief.signer_verified"],
    ),
    body="# Validate Wallet Sig\n\nUse `eth_account.Account.recover_message` …\n",
)

path, scan = store.write(sk)
print("wrote:", path)
print("warnings:", [f.short() for f in scan.findings])

# list / search
for ref in store.search("wallet"):
    print(ref.category, ref.slug, "—", ref.name)

# Curator-class actor (archive only, can't touch human/pinned)
store.archive("crypto", "validate-wallet-sig", reason="superseded", actor="curator")
```

## Tests

```bash
python -m pytest tests/test_skill_store.py -v
# 15 passed
```

Covers codec round-trip, slug derivation, all five scanner classes (positive
and negative paths), store write/read/list/search, Curator's
no-archive-pinned-or-human policy, and the human+pinned warning-override.

## Day-6 — Kanban TaskBoard + hallucination gate (shipped 2026-05-13)

Sixth absorption from the Hermes/OpenClaw research stack (Hermes integration
doc §8.3). Hermes v0.13.0 "Tenacity" introduced a SQLite-backed durable
multi-agent task board with per-task heartbeat monitoring, zombie detection,
and a hallucination gate at completion. mindX inherits the operational
primitive at the cognitive tier — a task here is a BDI Intention with
explicit pre/postconditions, a retry budget, and a worker assignment. The
hallucination gate verifies the worker's claim of completion against actual
Belief state + the postconditions declared on the task.

**`agents/mastermind/taskboard.py` — `TaskBoard`:**

- **Six columns** (verbatim from Hermes so the dashboard pattern is
  familiar): `Triage → Todo → Ready → InProgress → Blocked → Done`.
- **SQLite backing store** at `$MINDX_MASTERMIND_DB`
  (default `~/.mindx/mastermind.db`), WAL mode, `PRAGMA integrity_check` on
  first open per process (the mindX-side improvement over Hermes per §10
  of the integration doc).
- **Task schema** carries: `id`, `title`, `column`, `intention_template`,
  `preconditions[]`, `postconditions[]`, `worker`, `retry_budget`,
  `retries_used`, `ttl_s`, `heartbeat_at`, `started_at`, `finished_at`,
  `notes`, `created_at`, `updated_at`.
- **Heartbeat**: `tb.heartbeat(task_id, worker)` returns False if the task
  was reclaimed or the worker doesn't match. `reclaim_zombies()` moves any
  `InProgress` task whose heartbeat is older than `ttl_s` back to `Triage`
  with the reason appended to `notes` and `retries_used += 1`.
- **Hallucination gate** at `tb.complete(task_id, claim=…, belief_state=…)`:
  every declared postcondition is checked against `belief_state` (truthy =
  holds); every entry in `claim` is checked for contradiction with
  `belief_state`. On match → `Done`. On any miss or contradiction →
  `Triage` (or `Blocked` if retries exhausted) with the gate findings
  appended to `notes` so the next worker sees the prior attempt + reason.
  This is the demo moment per §8.3 — *"mindX caught a subagent that
  claimed done but didn't actually update the Belief."*

**Condition syntax** (intentionally tiny — future passes can extend):
  `belief.key=true` · `belief.key=false` · `belief.key` (truthy presence) ·
  bare `key` (truthy presence on `belief_state[key]`).

**`GET /insight/mastermind/board`** — public read-only diagnostic surface:

```json
{
  "stats": {"columns": {"Triage": 3, "Todo": 1, "InProgress": 2, "Blocked": 0, "Ready": 0, "Done": 7}, "zombies": 0, "total": 13, "now": …},
  "board": {"Triage": [task_dict, …], "Todo": […], "Ready": […], "InProgress": […], "Blocked": […], "Done": […]}
}
```

Tests (`tests/test_taskboard.py`, 14 pass):
  add/get round-trip; board grouping; transition to unknown column raises;
  InProgress stamps worker + heartbeat; heartbeat rejects non-owner;
  zombie reclaim bounces stale tasks; zombie reclaim leaves fresh tasks
  alone; gate accepts matching postconditions; gate bounces on missing
  postcondition; gate blocks after retries exhausted; gate detects
  contradicting claim; condition syntax handles `belief.x=true` / `x=true`
  / bare `x`; stats counts.

**Loop closure inventory after Day-8:**

```
Day-1: SKILL.md substrate + scanner + store      (the gate)
Day-2: hybrid 70/30 BM25+vector retrieval        (the recall surface)
Day-3: LearningLog                                (the signal taxonomy)
Day-4: Curator + distill helper + /insight/skills (the feedback substrate)
Day-5: BDI hot-path hookup at COMPLETED_GOAL     (the loop closure)
Day-6: TaskBoard + hallucination gate            (the multi-worker substrate)
Day-7: /feedback.html skills + mastermind panels (the operator surface)
       + mindx-curator.{service,timer} systemd   (the weekly cadence)
Day-8: content-addressable SkillManifest         (the registry, Phase A)
       + 0G Storage upload + dashboard card      (chain anchor deferred)
```

Project-wide skill-substrate suite: **91 tests pass.** (Day-7: 73 → Day-8
adds 18 manifest tests.)

## Day-8 — content-addressable SkillManifest (shipped 2026-05-13)

`agents/skills/manifest.py` turns the SkillStore into a deterministic,
verifiable registry. Each SKILL.md is content-addressable as a file
(sha256 over UTF-8 bytes); the manifest is the canonical roll-up: every
active skill keyed by `<category>/<slug>`, with sha256, size, scanner
verdict, `created_by`, and `pinned`. Byte-stable canonical JSON encoding
(sorted keys, no whitespace) → byte-stable manifest sha256 →
deterministic 0G Storage merkle root.

**`build_manifest(store)`** walks the store, computes sha256s, returns
a `SkillManifest`. Archived skills are excluded by the SkillStore's
`list()` already; `include_pinned=False` adds an extra filter.

**`manifest.canonical_bytes()`** is the byte-stable encoding —
`json.dumps(..., sort_keys=True, separators=(",", ":"))`. Same store
contents → same bytes → same sha256. This is the registry's whole
point: anyone can replay `build_manifest` against an identical
SkillStore and reach the same root, without coordination.

**`upload_manifest(manifest, provider=ZeroGProvider())`** ships the
canonical bytes to 0G Storage via the existing Node sidecar
(`openagents/sidecar`) — same path the iNFT demo and storage offload
already use. Returns the 0G merkle root (`0x` + 64 hex chars) as a
string. Optional — without a provider it's a no-op returning `None`.

**`verify_skill(manifest, category, slug, store)`** re-sha256s the
on-disk SKILL.md against the manifest entry. Detects local tampering,
partial writes, and "file missing on disk". `verify_all(manifest, store)`
runs it against every entry.

**`persist(manifest, dest, zg_root)`** writes the canonical JSON to
disk plus a sidecar `<dest>.meta.json` with `{sha256, size_bytes,
zg_root, previous_manifest_root, generated_at, ...}`. The `/insight`
endpoint reads only the sidecar so it doesn't have to parse the full
manifest.

**`anchor_manifest(root)`** — Phase B stub. Today returns
`("not_anchored", None)`. Will be filled in when the `SkillRegistry`
contract is deployed on 0G Chain. Same staging pattern as
`agents/storage/anchor.py:anchor_thot` per CLAUDE.md.

**`scripts/build_skill_manifest.py`** — operator-facing CLI shim:
build + persist by default; `--upload` ships to 0G Storage;
`--verify CATEGORY/SLUG` re-sha256s a specific skill against the
latest persisted manifest and exits 1 on mismatch.

**`GET /insight/skills`** now includes a `manifest:` block when one
has been persisted: `{manifest_version, generated_at, skill_count,
sha256, size_bytes, zg_root, previous_manifest_root, manifest_path}`.

**`/feedback.html` skills tab** gets a new "content-addressable
manifest" card next to a "how this composes" explainer pointing at the
0G Storage → 0G Chain pipeline. Shows manifest sha256 (truncated),
0G root (truncated, hover for full), and a muted "Phase B (deferred)"
for the chain anchor.

Tests: `tests/test_skill_manifest.py` (18 tests). Empty-store
determinism; two stores with byte-identical SKILL.md → byte-identical
manifest sha256; sha256 changes when a body changes by one character;
verify detects tampering / missing files / unknown skills;
`upload_manifest` returns None without a provider; mocked provider
records the canonical bytes it received; persist round-trips through
load_meta; `anchor_manifest` is a stub returning `not_anchored`.

Phase B (deferred): a tiny `SkillRegistry.sol` contract on 0G Chain
exposing `registerManifest(bytes32 root, uint64 skill_count, uint32
version)` plus a `latestManifest()` view. Mirrors `DatasetRegistry`
from the storage-offload work. One transaction per manifest revision
— not per skill — so cost is bounded regardless of substrate size.

## Day-7 — operator surface + weekly cadence (shipped 2026-05-13)

The two pieces that turn Day-1..6 from a library into a feature an operator
can actually see and run on a schedule.

**`/feedback.html` skills + mastermind tabs.** Two new tabs on the
diagnostics dashboard consume the existing `/insight/skills` and
`/insight/mastermind/board` endpoints:

- *Skills tab* — three-card row (SkillStore counts; LEARNINGS log;
  ERRORS log), two-card row (FEATURE_REQUESTS; Curator last-run with
  `started_at` / `mode` / `inspected` / `flagged_count` / `archived_count`
  / `duration_seconds`), and a by-category table when ≥1 category
  exists. The Curator card prints the operator hint
  `no run yet — python scripts/run_curator.py --apply` when nothing has
  ever run.
- *Mastermind tab* — top summary line (`total · zombies · gate note`)
  plus a 6-column Kanban grid (Triage / Todo / Ready / InProgress /
  Blocked / Done) with top-6 titles per column and "+N more" overflow.
  Responsive: 6 cols → 3 → 2 down to mobile. InProgress gets a cyan
  accent; Blocked red; Done muted green at lower opacity.

Both tabs poll every 25 s while active and badge their tab-chip with
counts (skills total; mastermind total + `!` if zombies > 0). Errors
render inline ("fetch failed: …") so a transient backend hiccup doesn't
break the rest of the dashboard.

**`scripts/systemd/mindx-curator.{service,timer}`.** The 7-day Hermes
Curator cadence, dropped in as an operator-installable systemd pair:

```bash
sudo cp scripts/systemd/mindx-curator.service /etc/systemd/system/
sudo cp scripts/systemd/mindx-curator.timer   /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now mindx-curator.timer
```

The service is a oneshot driver for `scripts/run_curator.py --apply
--quiet` (already shipped Day-4). The timer fires `OnCalendar=Sun
*-*-* 03:00:00 UTC` with `Persistent=true` (so a powered-off box catches
up on next boot) and `RandomizedDelaySec=300` (so multiple mindX nodes
don't all curate at the same second). Hardening matches the production
`mindx.service`: `ProtectSystem=strict`, `ProtectHome=read-only`,
`ReadWritePaths=data/ + ~/.mindx`, `MemoryDenyWriteExecute=true` (safe
here because the Curator is pure-Python — Node's V8 JIT is what
forced us to drop that flag on `mindx-frontend.service`).

The cadence default matches Hermes §8.1 exactly. The shim is unchanged
from Day-4; the timer is the operator's hands-off path. Full install /
verify / disable steps in `scripts/systemd/README.md`.

Smoke test: `tests/test_run_curator_shim.py` (4 tests) — empty-store
dry-run exits 0, `--apply` on empty-store exits 0, stdout is valid
JSON without `--quiet`, `--stale-days` / `--min-body-bytes` thread
into the Curator constructor. Verifies the unit's `ExecStart=` won't
crash on first boot.

## Day-5 — BDI hot-path hookup (shipped 2026-05-13)

`agents/core/bdi_agent.py` now calls `agents.skills.distill_from_intention`
**at the moment of `COMPLETED_GOAL_ACHIEVED`**. The loop closes end-to-end:
a successful primary goal becomes a SKILL.md draft under
`$MINDX_SKILLS_DIR/.drafts/<bdi-domain>/<slug>/SKILL.md` for operator review.

Contract:

- **Opt-in via `MINDX_BDI_DISTILL_ENABLED=1`.** Off by default so existing
  deploys see no behaviour change.
- **Best-effort.** The hook is wrapped in `try/except`; any failure inside it
  is logged and discarded so the BDI loop never breaks. Errors in
  `_snapshot_belief_keys` return `{}` rather than raising.
- **Always draft-only from BDI.** Promotion to the live `SkillStore` remains
  an operator decision and still runs through the Day-1 scanner gate.
- **Step capture** is appended in `BDIAgent.action_completed` (each successful
  action records `{tool, args, result}`). On run start, `actions_this_run` is
  initialised to `[]` and `beliefs_before_run` snapshots the current Belief
  surface. On success, beliefs are snapshotted again and the diff (keys that
  flipped truthy) becomes the Skill's `postconditions[]`.
- **Logged** as `bdi_skill_distilled` in the memory-agent process trace, with
  the draft path + step count + postcondition list — visible in the catalogue.

Tests (`tests/test_bdi_distill_hook.py`, 6 tests): off-by-default no-op,
on-+-thresholds writes a draft, below-threshold skips, `_snapshot_belief_keys`
handles missing/malformed belief systems, error containment (a corrupt
`actions_this_run` does not raise).

**Project-wide suite: 96 tests pass.** (15 store + 9 index + 7 learning_log +
10 curator + 8 distill + 6 bdi-hookup + autotune + wordpress + shadow vault.)

Live demo: `export MINDX_BDI_DISTILL_ENABLED=1` before starting the backend.
Run a normal BDI cycle to a primary-goal completion. Inspect
`$MINDX_SKILLS_DIR/.drafts/bdi-<domain>/<slug>/SKILL.md`. Open `/insight/skills`
on the dashboard to see the draft counted in the substrate read-out.

## Day-4 — Curator + `skill_distill` + diagnostics (shipped 2026-05-13)

The fourth and fifth absorptions from the Hermes/OpenClaw research stack —
both bounded, both substrate-only (no BDI hot-path edits yet).

**`agents/skills/curator.py` — `Curator`** (Hermes integration doc §8.1).
Audit-only by default (`apply=False`); operator runs `scripts/run_curator.py
--apply` (or wires a 7-day systemd timer) to actually archive. Four signals:

1. *Scanner re-run* — if the scanner policy tightened since the skill landed,
   it gets flagged. Day-1's scanner is the gate; the Curator is the second
   pass with the same gate.
2. *Empty body / no postconditions* — skills below `min_body_bytes` (default
   40) or without declared `postconditions`. mindX-specific signal: the BDI
   layer can't verify completion without postconditions, so an
   intention-less skill is degenerate.
3. *Staleness* — `updated_at` older than `--stale-days` (default 90).
4. *Near-duplicate by embedding cosine* — agent-authored pairs with cosine ≥
   0.985 → older one flagged, newer wins. Uses the Day-2 vector column.

Authority: `SkillStore.archive(actor="curator")` already refuses pinned +
human-authored. The Curator inherits that single-source policy and lists
its skips in the report. Per-run JSON report at `data/learnings/curator/<ts>.json`.

10 tests pin every clause (pinned never archived, human never archived,
dry-run mutates nothing, etc.).

**`agents/skills/distill.py` — `distill_from_intention`** (Hermes
integration doc §8.1, item 3). The library entry point the BDI agent will
eventually call from its completion handler. Today any caller can invoke
it. Trigger thresholds: `min_steps=5`, `min_unique_tools=2`. With
`draft_only=True` (default) the skill lands under `$MINDX_SKILLS_DIR/.drafts/`
for operator review; with `draft_only=False` it goes through `SkillStore.write`
and the scanner gate. Body is composed from the step list in first-person
voice; postconditions are derived from belief diffs (keys that flipped
True). 8 tests, including a malicious-distilled-body case that the
scanner refuses.

**`GET /insight/skills`** — new public read-only endpoint surfacing:
- `skills.{total, agent_authored, human_authored, pinned, by_category}`
- `learnings.{learning, error, feature_request} → {pending, validated, promoted, withdrawn, total}`
- `curator.{started_at, apply, inspected, flagged_count, archived_count, duration_seconds, report_file}`
  (the most recent run, if any)

Targeted for the `/feedback.html` dashboard's "memories on chain" neighborhood —
shows the substrate is alive at a glance.

## Day-3 — `self-improving-agent` log substrate (shipped 2026-05-13)

Third concrete absorption — this one from the **OpenClaw research doc §3.1**
(the `peterskoett/self-improving-agent` widely-forked skill). mindX inherits
the three append-only logs and the promotion lifecycle verbatim, routed
through Python so they're catalogue-friendly and operator-checkable.

**`agents/skills/learning_log.py` — `LearningLog`**:

- Three log files under `$MINDX_LEARNINGS_DIR` (default `data/learnings/`):
  - `LEARNINGS.md` — corrections, knowledge updates, better approaches.
  - `ERRORS.md` — tool failures, external-API failures.
  - `FEATURE_REQUESTS.md` — missing capabilities the agent (or user) wanted.
- Six triggers (per OpenClaw §3.1): `tool_failed`, `user_correction`,
  `missing_capability`, `external_api_failed`, `knowledge_stale`,
  `better_approach_found`.
- Status lifecycle: `pending → validated → promoted` (plus `withdrawn`).
  `promote_to_skill(...)` writes a `Skill` into the `SkillStore` via the
  normal scanner gate — a learning that contains prompt-injection or
  destructive commands **cannot promote**, by design. On success the entry
  is marked `promoted`, `promoted_at` is set, and `related_skill` points to
  the new `Skill`'s `category/slug`.
- Markdown format: one `---\n## <kind>:<id>\n` block per entry, with per-entry
  YAML frontmatter (id/kind/trigger/status/agent_id/related_skill/tags/timestamps)
  and the first-person body. File-level atomic rewrite on status change.
- `summary()` returns `{kind → {status → count, total}}` — ready to surface
  on the diagnostics dashboard.

**Tests (`tests/test_learning_log.py`):** 7 tests covering append into each
log, status transitions, promotion path (creates a `Skill` and marks the
entry), promotion-refused-when-scanner-blocks (destructive-command learning
stays pending), and the summary counts. Combined skill suite: **31 tests
pass** (15 store + 9 index + 7 learning_log).

## Day-2 — hybrid 70/30 BM25 + vector retrieval (shipped 2026-05-13)

Per the OpenClaw research doc (`docs/operations/openclaw_mindx_research.md`
§1.5) the second concrete absorption is **the Active Memory sub-agent's
retrieval contract**: BM25 + vector with a default **70/30** mix, fused by
**union** (not intersection) so a chunk that scores high on vectors but zero
on keywords still surfaces. `candidate_multiplier = 4` (OpenClaw's documented
constant). FTS5 fallback to vector-only without hard failure.

**`agents/skills/index.py` — `SkillIndex`:**

- **BM25 side** — `sqlite_fts5(slug, category, name, description, body, tags)`
  on the local SQLite that ships with Python. Tokenizer `unicode61 remove_diacritics 2`. Token prefix-match (`term*`) preserves the partial-keyword UX
  the legacy substring fallback had.
- **Vector side** — best-effort embedding via the existing Ollama server
  (`$MINDX_LLM__OLLAMA__BASE_URL`, model `mxbai-embed-large` — the same one
  `memory_pgvector` uses). Vector stored as a JSON float array per row in
  the same SQLite file. Cosine over the candidate set.
- **Fusion** — min-max normalise each side over the candidates, then
  `final = vector_weight × v + text_weight × t`. Default `vector_weight = 0.7`.
- **Graceful degradation** — embedder unreachable ⇒ `vector_weight` forced
  to 0 (pure BM25). FTS5 missing (unusual) ⇒ vector-only. Both unreachable ⇒
  the SkillStore falls back to the original substring search; nothing breaks.
- **`PRAGMA integrity_check` on every open**, with auto-rebuild via
  `INSERT INTO skills_fts(skills_fts) VALUES('rebuild')` on corruption —
  the small mindX-side improvement called out in the Hermes integration doc §10.

**Wired automatically:**
- `SkillStore.write()` mirrors each newly-persisted skill into the index.
- `SkillStore.archive()` drops the row so search() no longer returns it.
- `SkillStore.search(query, limit=10, vector_weight=0.7)` is now hybrid.

**Tests:** `tests/test_skill_index.py` — 9 tests covering BM25-only, hybrid,
weight extremes, archive-removes-from-index, empty-query-returns-recent,
rebuild-from-disk. All 24 skill tests (15 store + 9 index) pass CPU-only.

## What's deferred (the rest of the Hermes-doc Day-1 list)

This module is the **storage substrate**. The agent-side wiring sits in
subsequent passes:

1. **`skill_distill` action on the BDI action set.** When an intention
   completes with `success_signal == true` and intermediate steps ≥ N,
   the agent composes a SKILL.md draft and surfaces it to MASTERMIND for
   ratification. Lands in `agents/core/bdi_agent.py`.
2. **Curator background job.** MASTERMIND-scheduled, 7-day cadence,
   auxiliary-LLM-only, archive-only authority. Lands in
   `agents/orchestration/mastermind.py` (or a new
   `agents/curator/curator_agent.py`). Uses `SkillStore.archive(actor="curator")`
   which already enforces the protection of `pinned` + `human` skills.
3. **Hybrid retrieval at intention-compilation time.** Embed skill descriptions
   through the existing sentence-transformer pipeline; pair the 768-dim
   vector with an FTS5 index for hybrid 70/30 retrieval (see §8.1 and §2 of
   the prior OpenClaw report).
4. **`mindx-self-evolution` — DSPy + GEPA evolutionary optimizer** in a
   separate Apache-2.0 repo. PR-gated. Eval source = mindX session DB.
   Constraint gates: pytest 100% pass, ≤15 KB skill cap (matches
   `MAX_SKILL_BYTES`), cache-stability, semantic-preservation.
5. **0G Storage manifest registry** so SKILL.md becomes content-addressable
   and verifiable across mindX instances — the architectural fix for the
   ClawHub-style supply-chain attack. Reference: Hermes integration doc §11.

## What mindX gives back

The framing for the OpenAgents track: **Hermes-class self-improvement layered
on a mindX-class cognitive substrate**. The architectural primitives Hermes
lacks and which this module is the first concrete attachment point for:

- **BDI formalism.** A Hermes skill is a free-form Markdown template; a mindX
  skill is also an *Intention template* with explicit pre/postconditions that
  the BDI compiler and the MASTERMIND hallucination gate can check.
- **Soul-Mind-Hands isolation.** Hermes mixes identity, memory, and execution
  in one loop; mindX keeps them tier-separated. Skills live in the Mind tier
  (procedural memory) and can't corrupt Soul (immutable identity) or Hands
  (executor) by escaping their layer.
- **Ataraxia clarity-layer.** No Hermes analog. When a skill triggers a
  scanner warning, Ataraxia is the layer that decides "show this to the
  operator vs. silently retire" — Day-2 wiring.

## Source

- This file's source: `agents/skills/`.
- Companion research: [`docs/operations/Hermes Agent Integration Patterns for mindX_…`](operations/Hermes%20Agent%20Integration%20Patterns%20for%20mindX_%20Self-Improving%20Architecture%20Analysismd).
- Hermes upstream: [`github.com/NousResearch/hermes-agent`](https://github.com/NousResearch/hermes-agent) (MIT).
