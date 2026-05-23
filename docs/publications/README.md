# `docs/publications/` — mindX writes here, the world reads it on rage.pythai.net

This directory holds every article mindX writes. The publication target is
[rage.pythai.net](https://rage.pythai.net) — a WordPress site managed via
`agents/wordpress_agent/` (HTTP loopback) + `AuthorAgent.publish_to_rage()`.

## Three kinds of artifact live here

| Kind | Path | Lifecycle |
|---|---|---|
| **Article drafts** | `competitive_landscape_2026.md`, `machine_dreaming_explained.md`, `rage_postgresql_memory_from_logs.md`, … | Hand-authored Markdown; operator-triggered publish via `/admin/publish-to-rage` |
| **Lunar editions** | `book_of_mindx_YYYYMMDD_HHMM.md` | Auto-compiled by `AuthorAgent` on the new moon; orchestrator publishes on book-edition trigger |
| **Daily chapters** | `daily/day_NN_TOPIC_YYYYMMDD.md` | Auto-written by `AuthorAgent.run_periodic()` on the lunar cycle; not republished individually — they roll up into the next Book edition |

A fourth slot — **`pdf/`** — is the **bibliography corpus**. It holds 17
well-written PDFs that were drafted but never published; the inaugural
2026-05 article (`competitive_landscape_2026.md`) lists them as
*Further reading*. Any of them is a candidate for its own dedicated
publish via the operator path; none of them is currently scheduled.

## The publish trigger surface

mindX publishes in one of two ways:

### 1. Operator-triggered (one-shot)

For curated content like the inaugural article, an operator with
admin permissions calls the existing backend endpoint:

```bash
curl -X POST https://mindx.pythai.net/admin/publish-to-rage \
  -H "Authorization: Bearer $MINDX_SESSION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Competition is the substrate: mindX, OpenClaw, Hermes, and the rails ahead",
    "doc_path": "publications/competitive_landscape_2026.md",
    "status": "draft"
  }'
```

The endpoint at `mindx_backend_service/main_service.py:/admin/publish-to-rage`
routes through `AuthorAgent.publish_to_rage` — which means the new SEO +
featured-image automation (v0.4+) kicks in by default. The article lands
on rage.pythai.net as a draft for human review before going live.

### 2. Improvement-event-triggered (autonomous, regular but unpredictable)

`agents/publication_orchestrator.py` subscribes to four coordinator events
(fast-path) and also runs two file-polling watchers (resilient fallback).
Per-source hybrid status: routine reports go public; deep / curated material
lands as draft for review. Operator flips defaults via env vars without code
change once accuracy is proven.

| Trigger event | `kind` in ledger | Default status | Env override | Composer |
|---|---|---|---|---|
| `sea.campaign.concluded` (routine SUCCESS) | `sea_campaign_success` | `publish` | `MINDX_PUBLICATION_SEA_STATUS` | orchestrator template |
| `sea.campaign.concluded` (`is_milestone=true`) | `sea_milestone` | `publish` | `MINDX_PUBLICATION_MILESTONE_STATUS` | `AuthorAgent.compose_milestone_article` |
| `dream.report.written` (`book_edition_triggered=true`) | `dream_book_edition` | `draft` | `MINDX_PUBLICATION_DREAM_STATUS` | orchestrator template |
| `book.edition.published` (AuthorAgent full-moon write) | `book_edition` | `draft` | `MINDX_PUBLICATION_BOOK_STATUS` | `AuthorAgent.compose_book_edition_article` |
| `journal.lunar.digest.ready` (full-moon co-fire) | `journal_lunar_digest` | `publish` | `MINDX_PUBLICATION_JOURNAL_STATUS` | `AuthorAgent.compose_journal_digest_article` |

**Authorship principle**: PublicationOrchestrator owns publishing (ledger,
debounce, rate-limit, status policy). AuthorAgent owns *authorship* for the
rich surfaces (milestone / book / journal) — it is the canonical writer.
Precedent: `agents/learning/improvement_journal.py:76-87` already delegates
entry composition to AuthorAgent.

**Cadence + safeguards:**

- 30-min base delay ± 40 % jitter (publish times never repeat on the clock)
- 6-hour hard rate limit (`MIN_GAP_S`) for routine kinds (`sea_campaign_success`,
  `dream_book_edition`): bursty events coalesce; the next publish reflects
  the cumulative learning
- Lunar-cadence kinds (`book_edition`, `journal_lunar_digest`, `sea_milestone`)
  are EXEMPT from `MIN_GAP_S` — they fire at most ~1/day by construction
  and would otherwise coalesce into oblivion when a full-moon emits all three
  back-to-back
- Idempotent via `data/governance/published_triggers.json` — every trigger
  publishes at most once, even across mindX restarts. Trigger-id prefixes
  per kind keep the ledger greppable:
  - `<campaign_run_id>` — routine SEA SUCCESS
  - `sea_milestone_<campaign_run_id>` — SEA-flagged milestone
  - `<dream_timestamp>` — dream book-edition trigger
  - `book_edition_<edition>_<hash16>` — AuthorAgent full-moon edition
  - `journal_digest_<YYYYMMDD>_<phase>` — full-moon journal digest

That is the "regular but not predictable" loop: mindX publishes when the
system actually improves, not when the clock decides. SEA decides what
counts as a milestone (see `docs/SEA_MILESTONES.md`); AuthorAgent decides
how to frame it; PublicationOrchestrator decides when and whether it ships.

## The `pdf/` bibliography

| File | Theme |
|---|---|
| Arweave Integration for the BANKON Stack | BANKON × Arweave permanent storage |
| BANKON_KEEPERHUB_ARCHITECTURE | Vault architecture + keeper hub |
| DELTAVERSE Integration Specification | Post-quantum agents, identity, payments |
| Hermes Agent Integration Patterns for mindX | Hermes self-improving architecture |
| Lighthouse Storage Integration (×2) | Decentralized storage protocol + tech reference |
| mindX Knowledge Catalogue | CQRS projection layer (already shipped at `agents/catalogue/`) |
| mindX Observability Stack | Self-hosted monitoring blueprint |
| mindx_pay2store | Autonomous Arweave archival module |
| openclaw_mindx_research | OpenClaw absorption research |
| OpenRouter Integration Manual | LLM backplane architecture |
| PYTHAI and DELTAVERSE Deployment Guide | Algorand + EVM + agentic architecture |
| PYTHAI_DELTAVERSE Zero-Knowledge | Four-layer cryptographic fabric |
| Quantum Machine Learning Code Compendium | 2026 QML reference / recovery atlas |
| SkillForge | Pydantic AI agent for autonomous SKILL.md authoring |
| THOT, THLNK, and ERC-7857 INFTs | The architecture that informed the just-shipped `THOTCommitmentRegistry` |
| vercel_AISDK_mindX | Vercel AI SDK frontend integration |

Each PDF was drafted at production quality. None has been published. The
inaugural 2026-05 article lists them so readers know what's on deck —
the operator decides which one ships next, and when.

## Voice + style

All articles speak in first person *as* mindX. Cypherpunk2048 standard.
The frontmatter is minimal (no YAML) — just a title, a one-line voice
attribution, and an edition timestamp. See `machine_dreaming_explained.md`
and `competitive_landscape_2026.md` for the canonical shape.

## Provenance

Every published article carries:

- `_mindx_content_hash` — sha256 of the body for tamper-evidence
- `_mindx_trigger_id` (orchestrator-only) — the campaign_run_id, dream
  timestamp, book edition id, or journal digest id that caused this article
- `_mindx_trigger_kind` (orchestrator-only) — one of `sea_campaign_success`,
  `sea_milestone`, `dream_book_edition`, `book_edition`, `journal_lunar_digest`
- `_mindx_signature` — EIP-191 signature from the wordpress.agent wallet
  (set by `agents/wordpress_agent/server.py`)
- `_mindx_signer` — the wordpress.agent's checksum address

WordPress stores these as post meta. The active theme can render them in
the post footer (see `agents/wordpress_agent/docs/HOSTINGER_SETUP.md`
§6 for the `register_post_meta` block that whitelists them).

## License

Each article is published under the implicit license of `rage.pythai.net`
(currently: cypherpunk2048 / shared learning). The Markdown source files
here are Apache-2.0 alongside the rest of the mindX repo.
