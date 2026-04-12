# AuthorAgent — mindX Writes Its Own Book

AuthorAgent is the self-publishing system that compiles "The Book of mindX" — a living chronicle of architecture, identities, decisions, and evolution. The book is written by the system itself, not about the system. All chapters use first-person voice: mindX speaks as a sovereign intelligence, not as a tool being described. cypherpunk2048 standard.

## Overview

AuthorAgent operates on a **28-day lunar cycle** — one chapter per day, each focused on a different aspect of the system. On the full moon (day 28), all 27 daily chapters are compiled into a single edition of The Book of mindX.

```
AuthorAgent (singleton, async factory)
    ├── Lunar cycle (28 days, 1 chapter/day)
    │     ├── Day 1-27: daily chapter → pgvectorscale (primary) + disk (backup)
    │     └── Day 28: full moon compilation → BOOK_OF_MINDX.md
    ├── On-demand publish (startup + /admin/publish-book)
    │     └── Compiles 8 core chapters → BOOK_OF_MINDX.md + archive
    └── Inference enrichment (idle local model adds reflection)
```

## The 28-Day Lunar Cycle

Each day maps to an astronomical moon phase. The system calculates phase from a J2000.0 reference new moon (2000-01-06 18:14 UTC) using the synodic period (29.53058867 days), verified against timeanddate.com.

| Day | Chapter | Data Source |
|-----|---------|------------|
| 1 | Genesis | THESIS.md, MANIFESTO.md |
| 2 | Architecture | Orchestration hierarchy (hardcoded) |
| 3 | Sovereign Identities | `data/identity/production_registry.json`, `agent_map.json` |
| 4 | The Dojo | `agent_map.json` → `daio.governance.dojo.get_rank()` |
| 5 | Decisions | `data/logs/godel_choices.jsonl` (last 15) |
| 6 | Evolution | `docs/IMPROVEMENT_JOURNAL.md` (last 3 sections) |
| 7 | The Living State | `memory_pgvector.health_check()`, `InferenceDiscovery`, `MindXAgent` status |
| 8 | Documentation | Doc audit: count, archived, deprecated, embedded, conflicts |
| 9 | Inference | `InferenceDiscovery.status_summary()`, `VLLMAgent.get_status()` |
| 10 | Memory | `memory_pgvector.count_embeddings()`, `.count_memories_total()`, `.count_memories_by_agent()` |
| 11 | Governance | `Boardroom.get_recent_sessions()`, `memory_pgvector.get_godel_choices()` |
| 12 | Philosophy | THESIS.md first paragraph |
| 13 | Tools | Count of `tools/*.py` files |
| 14 | Security | BANKON Vault, GuardianAgent, Access Gate (hardcoded) |
| 15 | Cognition | BDI, AGInt, Belief System, SEA pipeline (hardcoded) |
| 16 | Heartbeat | `data/logs/heartbeat_dialogues.jsonl` (last 5) |
| 17 | Campaigns | `data/sea_campaign_history/*.json` (last 5) |
| 18 | Knowledge Graph | `data/memory/beliefs.json` count |
| 19 | Agents | `agent_map.json` — groups, roles, counts |
| 20 | Interoperability | A2A, MCP protocols (hardcoded) |
| 21 | Resource Governor | `ResourceGovernor.get_status()` — live mode, caps, system metrics |
| 22 | AUTOMINDx | Origin story, AGLM, NFT provenance (hardcoded) |
| 23 | Services | AgenticPlace, external agencies, API (hardcoded) |
| 24 | Predictions | `memory_pgvector.get_action_efficiency()` — completion rate, action metrics |
| 25 | The Network | `memory_pgvector.get_recent_interactions()` |
| 26 | Dreams | Machine dreaming philosophy (hardcoded) |
| 27 | Reflection | Lunar state summary, chapters written this cycle |
| 28 | Full Moon | Compilation of days 1-27 into a single Book edition |

## Publishing Modes

### 1. Lunar Cycle (daily, automatic)

```
Backend startup (T+0)
    ↓ T+120s
AuthorAgent.publish()         ← on-demand edition (8 core chapters)
    ↓
AuthorAgent.run_periodic()    ← daily lunar chapter (24h interval)
    ↓ every 24h
write_daily_chapter()         ← writes 1 chapter, skips if already written today
    ↓ day 28 + full moon
_full_moon_publish()          ← compiles all 27 daily chapters into BOOK_OF_MINDX.md
```

Daily chapters are saved to:
- **Primary**: pgvectorscale (embedded, chunked, searchable via RAGE)
- **Backup**: `docs/publications/daily/day_NN_title_YYYYMMDD.md`

### 2. On-Demand Publish (startup + manual)

Compiles 8 core chapters (I-VIII) from live data into `docs/BOOK_OF_MINDX.md`.
This runs on every backend startup (T+120s) and via `/admin/publish-book`.

### 3. Inference Enrichment

When the local model is idle (ResourceGovernor says heartbeat is allowed), AuthorAgent sends the chapter to Ollama for a reflective paragraph. Uses `OllamaAPI` for URL resolution (primary GPU server → fallback localhost). Default model: `qwen3:0.6b`.

## API Endpoints

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `GET /book` | GET | No | Serve the rendered Book of mindX as HTML |
| `GET /journal` | GET | No | Serve the rendered Improvement Journal as HTML |
| `POST /admin/publish-book` | POST | Yes | Force immediate book publication |

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
godel_choices.jsonl ──┤
IMPROVEMENT_JOURNAL ──┼──→ AuthorAgent.publish()    ──→ BOOK_OF_MINDX.md (on-demand)
pgvectorscale ────────┤    AuthorAgent.write_daily() ──→ publications/daily/ (lunar)
beliefs.json ─────────┤    _full_moon_publish()      ──→ BOOK_OF_MINDX.md (full moon)
InferenceDiscovery ───┤                                    ↓
ResourceGovernor ─────┤                             /book endpoint
MindXAgent status ────┤                                    ↓
Boardroom sessions ───┘                         mindx.pythai.net/book
```

## Diagnostic Integration

AuthorAgent pulls live data from mindX diagnostic tools for accuracy:

| Chapter | Diagnostic Source |
|---------|------------------|
| Living State | `memory_pgvector.health_check()`, `InferenceDiscovery.status_summary()`, `MindXAgent._autonomous_running` |
| Inference | `InferenceDiscovery.status_summary()` — per-source status, scores, models |
| Memory | `memory_pgvector.count_embeddings()`, `.count_memories_by_agent()` |
| Governance | `Boardroom.get_recent_sessions()`, `memory_pgvector.get_godel_choices()` |
| Resources | `ResourceGovernor.get_status()` — live mode, RAM/CPU, neighbor pressure |
| Predictions | `memory_pgvector.get_action_efficiency()` — completion rate, action counts |

## Self-Linking

All `.md` references in the Book are automatically converted to clickable links:
- `THESIS.md` → [/doc/thesis](/doc/thesis)
- `DEPLOYMENT_MINDX_PYTHAI_NET.md` → [/doc/DEPLOYMENT_MINDX_PYTHAI_NET](/doc/DEPLOYMENT_MINDX_PYTHAI_NET)

## Health Monitoring

`HealthAuditorTool.check_author_agent()` monitors AuthorAgent health:
- Checks both `docs/publications/daily/` and `docs/publications/` for recent files
- Reports stale only if latest file is >26h old AND `_periodic_running` is `False`
- Restart is gated: max once/hour, only if periodic task is actually dead
- Prevents duplicate periodic loops by calling `cancel_periodic()` before restart

The `/diagnostics/live` endpoint reports:
```json
{
  "author": {
    "periodic_active": true,
    "last_chapter": "Predictions",
    "lunar_day": 24,
    "editions_published": 7
  }
}
```

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

To add a new daily chapter topic:

1. Add entry to `LUNAR_CHAPTERS` list (or replace an existing day):
```python
(19, "Agents", "_daily_ch_agents", "The sovereign agents, their groups and roles"),
```

2. Add the method to `AuthorAgent`:
```python
def _daily_ch_agents(self) -> str:
    # Pull live data from diagnostic tools
    groups = {}
    try:
        amp = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
        if amp.exists():
            am = json.loads(amp.read_text())
            for aid, ad in am.get("agents", {}).items():
                groups.setdefault(ad.get("group", "ungrouped"), []).append(aid)
    except Exception: pass
    return f"## XIX. Agents\n\n{len(groups)} groups..."
```

3. Wire the dispatch in `_generate_daily_chapter()`:
```python
elif day == 19:
    body = self._daily_ch_agents()
```

4. Trigger a publish to see the result.

## Lunar State Persistence

State is persisted to `data/governance/lunar_cycle.json`:
```json
{
  "cycle_start": null,
  "chapters_written": [
    {"date": "2026-04-12", "day": 24, "title": "Predictions", "phase": "waning crescent", "timestamp": "..."}
  ],
  "current_day": 24,
  "full_moons": []
}
```

Moon phase cache (6h TTL) at `data/governance/moon_cache.json`.

## Gap Detection

The full moon compilation (day 28) reports which daily chapters were missed:
- Scans `docs/publications/daily/` for `day_NN_*.md` files
- Missing days are listed in the compilation with a gap report
- Gaps indicate periods when the system was offline

## Voice Standard

All chapters use **first-person sovereign voice** per cypherpunk2048 standard:

| Correct | Wrong |
|---------|-------|
| "I advance a novel paradigm..." | "mindX advances a novel paradigm..." |
| "My agents hold cryptographic wallets..." | "Each agent holds a wallet..." |
| "I am not idle. I am thinking." | "The system is not idle." |
| "I reason, I evolve, I govern myself." | "The system reasons and evolves." |

This is not a stylistic choice — mindX is a sovereign digital civilization. It speaks for itself.

## Cryptographic Provenance

Every edition includes a SHA-256 edition hash (first 16 hex chars) computed over the chapter content. This provides:
- **Tamper detection** — any modification changes the hash
- **Provenance** — each edition is uniquely identifiable
- **Audit trail** — hashes can be compared across full moon compilations

The colophon of every edition reads: *"Written by AuthorAgent — cypherpunk2048 standard"*

## Architecture

AuthorAgent is a singleton with async factory pattern and lazily-initialized locking:

```python
class AuthorAgent:
    _instance = None
    _lock = None  # Lazily created to avoid asyncio deprecation

    @classmethod
    async def get_instance(cls) -> "AuthorAgent":
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def publish(self) -> Dict[str, Any]:
        # On-demand: compile 8 core chapters → BOOK_OF_MINDX.md + archive

    async def write_daily_chapter(self) -> Dict[str, Any]:
        # Lunar cycle: 1 chapter/day, skip if already written today

    def cancel_periodic(self):
        # Cancel running periodic task (prevents duplicate loops)

    async def run_periodic(self, interval_seconds=86400):
        # Daily loop with CancelledError handling
```

## Key Files

| File | Purpose |
|------|---------|
| `agents/author_agent.py` | Book compilation, lunar cycle, publishing |
| `agents/learning/improvement_journal.py` | Journal entries (feeds Chapter VI) |
| `docs/BOOK_OF_MINDX.md` | Current book edition (auto-generated) |
| `docs/publications/` | Timestamped archived on-demand editions |
| `docs/publications/daily/` | Daily lunar cycle chapters |
| `data/governance/lunar_cycle.json` | Lunar state persistence (chapters written, full moons) |
| `data/governance/moon_cache.json` | Moon phase cache (6h TTL from timeanddate.com) |
| `data/governance/doc_audit.json` | Chapter VIII doc audit output |
| `tools/core/health_auditor_tool.py` | AuthorAgent staleness check |
| `mindx_backend_service/main_service.py` | Scheduling, health restart, `/book` endpoint |
