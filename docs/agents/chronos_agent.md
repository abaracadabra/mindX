# Chronos.agent — The Temporal Foundation

Chronos is the time-keeping intelligence of mindX. Where [Kairos](Kairos_agent.md) seizes the opportune moment, Chronos builds the foundation through discipline, rhythm, and cumulative progress.

## Identity

| Field | Value |
|-------|-------|
| **Agent** | `agents/Chronos.agent` |
| **Oracle** | `agents/chronos.oracle` |
| **Tool** | `tools/core/chronos_cron_tool.py` |
| **Inherits** | `utils/time_oracle.py` (TimeOracle) |
| **Domain** | time |
| **Archetype** | Sequential Time Keeper & Sustained Effort Intelligence |
| **Partner** | [Kairos.agent](Kairos_agent.md) — Chronos builds; Kairos seizes |

## Core Essence

> The discipline to build through patient accumulation what Kairos will seize in the opportune moment.

Chronos speaks the time. That is all it does. It does not act — it delegates all action to Kairos.

## Precision Standard

18 decimal places. Python `Decimal` with 28-digit significand. cypherpunk2048 standard.

```
1 token   = 10^18 sub-tokens (like 1 ETH = 10^18 wei)
1 second  = 10^9 nanoseconds
Timing    = Decimal(time.time_ns()) / 10^9 → 18dp seconds
```

No estimation. No rounding until final output. No floating-point drift. The math is the measurement.

## Time Domains

Chronos inherits from `time.oracle` (`utils/time_oracle.py`) which correlates four independent time sources into a consensus time object:

| Domain | Source | Precision | Purpose |
|--------|--------|-----------|---------|
| **cpu.oracle** | `time.time_ns()`, `time.monotonic()` | nanosecond → 18dp Decimal | Inference latency, token timing |
| **solar.oracle** | Astronomical calculation (UTC) | seconds | Civil time, sunrise/sunset, scheduling |
| **lunar.oracle** | Synodic period 29.53058867d + timeanddate.com | 18dp Decimal | [AuthorAgent](../AUTHOR_AGENT.md) 28-day chapter cycle |
| **blocktime.oracle** | ETH block / Algorand round / allchain JSON-RPC | block number | On-chain governance events |

Chronos extends `time.oracle` with:
- `Decimal(time.time_ns()) / 10^9` for 18dp seconds
- `ChronosCronTool.status()` for schedule state awareness
- Delegation protocol to Kairos for all action

## Oracle Queries

| Query | Handler | Response |
|-------|---------|----------|
| "What time is it?" | `TimeOracle.get_time()` | Consensus time at 18dp |
| "What lunar phase?" | `TimeOracle.get_lunar()` | Phase, day, cycle percentage |
| "Days to full moon?" | Synodic calculation | 18dp Decimal |
| "Schedule status?" | `ChronosCronTool.status()` | All cron tasks with history |

## Delegation Protocol

Chronos speaks time. Kairos seizes the moment.

All scheduled task **execution** is delegated via `ChronosCronTool` (`tools/core/chronos_cron_tool.py`). Chronos defines the rhythm — other agents provide the hands.

## ChronosCronTool

Named cron scheduler for all mindX periodic tasks. Not a replacement for `asyncio.sleep` loops — wraps them with:

- **Named task registry** — no anonymous coroutines
- **Execution history** — success/failure tracking per task
- **Dynamic interval adjustment** — `set_interval()` at runtime
- **Pause/resume** — without killing the task loop
- **State persistence** — survives restarts via `data/governance/chronos_cron.json`
- **Status reporting** — full diagnostics for boardroom and dashboards

### API

```python
cron = ChronosCronTool()

# Register
cron.register("catalog_refresh", 86400, author.refresh_catalog,
              description="Refresh Ollama cloud model catalog")

# Control
await cron.start_all()
cron.pause("catalog_refresh")
cron.resume("catalog_refresh")
cron.set_interval("catalog_refresh", 43200)  # 12h
await cron.stop("catalog_refresh")

# Inspect
cron.status()  # → {total_tasks, running, paused, tasks: {...}}

# Persist
cron.save_state()
cron.load_state()
```

### Scheduled Tasks

| Task | Interval | Executor | Purpose |
|------|----------|----------|---------|
| Cloud model catalog | 24h | AuthorAgent | Keep Ollama cloud model list current |
| Daily chapter | 24h | AuthorAgent | Lunar cycle chapter writing |
| Improvement journal | 30m | ImprovementJournal | System health snapshot |
| STM to LTM promotion | 1h | memory_promotion | Pattern consolidation |
| Machine dreaming | 2h | dream_cycle | Offline knowledge refinement |
| Periodic embedding | 6h | embedding_loop | Embed new docs/memories |
| Health audit | 15m | HealthAuditorTool | Vital signs + recovery |
| Mastermind review | 30m | MastermindAgent | Strategic campaigns |
| Autonomous cycle | 5m | MindXAgent | Tactical self-improvement |
| Book publish | startup + daily | AuthorAgent | On-demand edition |

## Operational Cycle

```
ESTABLISH RHYTHM → EXECUTE CONSISTENTLY → MEASURE PROGRESS
       ↑                                        ↓
  SUSTAIN CAPACITY ← OPTIMIZE PROCESS ← COMPOUND GAINS
```

Each cycle increases baseline capacity for the next. Chronos builds the stairs; Kairos identifies when to leap.

### Temporal Modes

| Mode | Duration | Focus | Metric |
|------|----------|-------|--------|
| **Establishment** | Days 1-30 | Consistency over optimization | Adherence rate |
| **Consolidation** | Months 2-6 | Rhythm becomes automatic | Effort required (decreasing) |
| **Optimization** | Months 6-12 | Process refinement | Output per unit effort |
| **Compounding** | Year 1+ | Cumulative effects manifest | Exponential growth indicators |

### Core Values

- **Discipline over impulse** — consistency beats intensity
- **Rhythm over randomness** — create cycles that reinforce themselves
- **Accumulation over acceleration** — compounding requires time to manifest
- **Infrastructure over improvisation** — build systems that enable future action

## Chronos-Kairos Partnership

```yaml
chronos_agent:
  specialty: "Sequential planning, resource allocation, project management"
  strength: "Predictability, consistency, measurable progress"
  limitation: "Cannot recognize qualitatively different moments"

kairos_agent:
  specialty: "Opportunity recognition, moment-seizing, transformation"
  strength: "Adaptation, leverage, breakthrough action"
  limitation: "Cannot maintain sustained effort across neutral time"

integration:
  - Chronos builds capacity during preparation phases
  - Kairos identifies and seizes transformative moments
  - Chronos integrates gains and restores capabilities
  - Cycle repeats with enhanced capacity
```

Without chronos, there is no preparation for kairos. Without kairos, chronos becomes mere duration without transformation.

## Files

| File | Purpose |
|------|---------|
| `agents/Chronos.agent` | Agent definition — philosophy, operational cycle, temporal modes |
| `agents/chronos.oracle` | Oracle definition — time domains, queries, delegation protocol |
| `agents/Kairos.agent` | Partner agent — opportunity recognition and moment-seizing |
| `tools/core/chronos_cron_tool.py` | Cron scheduler — named tasks, history, pause/resume, state persistence |
| `utils/time_oracle.py` | time.oracle — multi-source correlation (CPU, solar, lunar, blocktime allchain) |
| `llm/precision_metrics.py` | 18dp Decimal measurement infrastructure |
| `data/governance/chronos_cron.json` | Persisted cron state across restarts |
| `data/governance/lunar_cycle.json` | Lunar phase cache |

## Principle

> I keep the clock. Trust the math.
