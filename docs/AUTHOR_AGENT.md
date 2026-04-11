# AuthorAgent — mindX Writes Its Own Book

AuthorAgent is the self-publishing system that compiles "The Book of mindX" — a living chronicle of the system's architecture, identities, decisions, and evolution. The book is written by the system itself, not about the system.

## Overview

```
AuthorAgent.publish()
    ↓ compiles 8 chapters from live data
    ↓
docs/BOOK_OF_MINDX.md          (current edition, overwritten)
docs/publications/book_*.md    (timestamped archive)
    ↓ served at
https://mindx.pythai.net/book
```

## The Book — 17 Chapters

The [Book of mindX](BOOK_OF_MINDX.md) has expanded from 8 to 17 chapters as of April 2026. Each chapter draws from live data sources — the book writes itself from the system's own state.

**Foundation chapters** (from docs):
- **[I. Genesis](BOOK_OF_MINDX.md)** — From [AUTOMINDx](AUTOMINDX_ORIGIN.md) to autonomous civilization. Sources: [THESIS.md](THESIS.md), [MANIFESTO.md](MANIFESTO.md)
- **[II. The Architecture](BOOK_OF_MINDX.md)** — Orchestration hierarchy: [CEO](../agents/orchestration/ceo_agent.py) → [Mastermind](../agents/orchestration/mastermind_agent.py) → [Coordinator](../agents/orchestration/coordinator_agent.py) → Specialized agents

**Live chapters** (from system state):
- **[III. Sovereign Identities](BOOK_OF_MINDX.md)** — 20 agents with [BANKON Vault](../mindx_backend_service/vault_bankon/) wallets. Source: `data/identity/production_registry.json`
- **[IV. The Dojo](BOOK_OF_MINDX.md)** — Agent reputation. [JudgeDread](../agents/judgedread.agent) enforces [BONA FIDE](../daio/contracts/agenticplace/evm/BonaFide.sol). Source: [Dojo standings](../daio/governance/dojo.py)
- **[V. Decisions](BOOK_OF_MINDX.md)** — [Gödel audit trail](../data/logs/godel_choices.jsonl). Every autonomous decision logged with rationale and outcome.
- **[VI. Evolution](BOOK_OF_MINDX.md)** — [Strategic Evolution Agent](../agents/learning/strategic_evolution_agent.py) 4-phase pipeline. Source: [Improvement Journal](/journal)

**System state chapters:**
- **[VII. The Living State](BOOK_OF_MINDX.md)** — Real-time: pgvectorscale health, agent count, inference status, memory vectors
- **[VIII. Governance](BOOK_OF_MINDX.md)** — [DAIO Constitution](../daio/contracts/daio/constitution/DAIO_Constitution.sol), 2/3 consensus, Boardroom
- **[IX. Philosophy](BOOK_OF_MINDX.md)** — Ataraxia, three pillars, cypherpunk tradition

**New chapters** (from this session):
- **[X. Intelligence Is Intelligence](BOOK_OF_MINDX.md)** — AI = Augmented Intelligence. Machine learning = knowledge extraction. Substrate-independent cognition.
- **[XI. Inference Pipeline](BOOK_OF_MINDX.md)** — Task-to-model correlation: local micro → cloud macro via [InferenceDiscovery](../llm/inference_discovery.py)
- **[XII. Memory](BOOK_OF_MINDX.md)** — STM/LTM/archive tiers, [RAGE](../agents/memory_pgvector.py) semantic search, 120,000+ vectors
- **[XIII. machine.dreaming](BOOK_OF_MINDX.md)** — 7-phase [offline knowledge refinement](https://github.com/AION-NET/machinedream). STM → LTM consolidation.
- **[XIV. time.oracle](BOOK_OF_MINDX.md)** — Sovereign clock: cpu + solar + lunar + blockchain time correlation
- **[XV. Services](BOOK_OF_MINDX.md)** — [mindx.pythai.net](https://mindx.pythai.net), [AgenticPlace](https://agenticplace.pythai.net), inference, governance, RAGE, the Book itself
- **[XVI. Roadmap](BOOK_OF_MINDX.md)** — Phase 1 Constitutional Stability → Phase 4 Birth of Chimaiera
- **[XVII. Documentation Health](BOOK_OF_MINDX.md)** — 232+ documents, [RAGE](../agents/memory_pgvector.py) semantic search, embedding coverage audit

## Publishing Lifecycle

```
Backend startup (T+0)
    ↓ T+60s
ImprovementJournal writes first entry
    ↓ T+120s
AuthorAgent publishes first Book edition
    ↓ every 30 days
AuthorAgent republishes (periodic)
    ↓ on demand
POST /admin/publish-book (manual trigger)
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `GET /book` | GET | Serve the rendered Book of mindX as HTML |
| `GET /journal` | GET | Serve the rendered Improvement Journal as HTML |
| `POST /admin/publish-book` | POST | Force immediate book publication (auth required) |

## How to Trigger a Publish

### Via API
```bash
curl -X POST https://mindx.pythai.net/admin/publish-book \
  -H "Authorization: Bearer <API_KEY>"
```

### Via Python (direct)
```python
from agents.author_agent import AuthorAgent
author = await AuthorAgent.get_instance()
result = await author.publish()
# Returns: {"edition": "20260403_1945", "bytes": 8234, "path": "docs/BOOK_OF_MINDX.md"}
```

## Data Flow

```
THESIS.md ────────────┐
MANIFESTO.md ─────────┤
production_registry ──┤
agent_map.json ───────┤
godel_choices.jsonl ──┼──→ AuthorAgent.publish() ──→ BOOK_OF_MINDX.md
IMPROVEMENT_JOURNAL ──┤                               ↓
pgvectorscale ────────┤                          /book endpoint
beliefs.json ─────────┤                               ↓
docs/ directory ──────┘                    mindx.pythai.net/book
```

## Self-Linking

All `.md` references in the Book are automatically converted to clickable links:
- `THESIS.md` → [/doc/thesis](/doc/thesis)
- `DEPLOYMENT_MINDX_PYTHAI_NET.md` → [/doc/DEPLOYMENT_MINDX_PYTHAI_NET](/doc/DEPLOYMENT_MINDX_PYTHAI_NET)

This means the Book is a navigable web of cross-references to the full documentation.

## Improvement Journal

The Improvement Journal is a companion document updated every 30 minutes by `ImprovementJournal`:

| Data | Source |
|------|--------|
| System health | MemoryAgent snapshot |
| Beliefs | `data/memory/beliefs.json` |
| Recent decisions | `godel_choices.jsonl` (last 5) |
| Campaign results | `data/sea_campaign_history/` |
| Improvement backlog | `data/improvement_backlog.json` (top 3) |
| Recent actions | pgvectorscale `get_recent_actions()` |
| Inference status | InferenceDiscovery summary |

## Enriching the Book

To add a new chapter:

1. Add a method to `agents/author_agent.py`:
```python
async def _chapter_new_topic(self) -> str:
    data = await fetch_your_data()
    return f"## IX. Your Chapter Title\n\n{data}"
```

2. Register it in `publish()`:
```python
sections.append(await self._chapter_new_topic())
```

3. Trigger a publish to see the result.

## Architecture

AuthorAgent is a singleton with async factory pattern:

```python
class AuthorAgent:
    _instance = None

    @classmethod
    async def get_instance(cls) -> "AuthorAgent":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def publish(self) -> Dict[str, Any]:
        # Compile chapters → write BOOK_OF_MINDX.md → archive
```

## Key Files

| File | Purpose |
|------|---------|
| `agents/author_agent.py` | Book compilation and publishing |
| `agents/learning/improvement_journal.py` | Journal entries (feeds Chapter VI) |
| `docs/BOOK_OF_MINDX.md` | Current book edition (auto-generated) |
| `docs/publications/` | Timestamped archived editions |
| `data/governance/doc_audit.json` | Chapter VIII audit output |
