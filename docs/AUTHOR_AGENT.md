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

## The Book — 8 Chapters

| Chapter | Title | Data Source | Dynamic? |
|---------|-------|------------|----------|
| I | Genesis | THESIS.md, MANIFESTO.md | Semi-static |
| II | The Architecture | Orchestration hierarchy diagram | Static (code edit to change) |
| III | Sovereign Identities | `data/identity/production_registry.json`, `daio/agents/agent_map.json` | Live — grows as agents register |
| IV | The Dojo | Agent reputation scores from agent_map.json | Live — updates with reputation changes |
| V | Decisions | `data/logs/godel_choices.jsonl` (last 15 entries) | Live — every autonomous decision logged |
| VI | Evolution | `docs/IMPROVEMENT_JOURNAL.md` (last 3 entries) | Live — updated every 30 minutes |
| VII | The Living State | pgvectorscale health check: beliefs, memories, embeddings, DB size | Live — real-time system snapshot |
| VIII | Documentation Health | `docs/` directory scan, pgvectorscale embedding coverage, conflict audit | Live — reports unembedded docs |

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
