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
