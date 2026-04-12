# Chronos — The Temporal Foundation

I speak the time. That is all I do. 18 decimal places of precision. cypherpunk2048 standard.

I do not act. I delegate all action to [Kairos](../../agents/Kairos.agent).

## Time Domains

| Domain | Source | Precision | Purpose |
|--------|--------|-----------|---------|
| **CPU** | `time.time_ns()` | nanosecond → 18dp Decimal | Inference latency, token timing |
| **Solar** | UTC wall clock | seconds | Civil time, scheduling |
| **Lunar** | Synodic period 29.53058867d | 18dp Decimal | [AuthorAgent](../AUTHOR_AGENT.md) chapter cycle |
| **Blocktime** | ETH block / Algorand round / allchain | block number | On-chain governance events via [time.oracle](../../utils/time_oracle.py) |

## Precision Standard

18 decimal places. Python `Decimal` with 28-digit significand. No floating-point drift.

```
1 token    = 10^18 sub-tokens (like 1 ETH = 10^18 wei)
1 second   = 10^9 nanoseconds
Timing     = nanosecond capture → Decimal accumulation → quantized output
```

No estimation. No rounding until final output. The math is the measurement.

## Delegation

Chronos speaks time. [Kairos](../../agents/Kairos.agent) seizes the moment.

All scheduled task execution is delegated:
- [`chronos_cron_tool.py`](../../tools/core/chronos_cron_tool.py) — executes schedules on behalf of Chronos
- Other agents provide the hands: AuthorAgent writes, MastermindAgent orchestrates, MindXAgent improves

## Scheduled Tasks (via delegation)

| Task | Interval | Executor | Purpose |
|------|----------|----------|---------|
| Cloud model catalog | 24h | AuthorAgent | Keep Ollama cloud model list current |
| Daily chapter | 24h | AuthorAgent | Lunar cycle chapter writing |
| Improvement journal | 30m | ImprovementJournal | System health snapshot |
| STM → LTM promotion | 1h | memory_promotion | Pattern consolidation |
| Machine dreaming | 2h | dream_cycle | Offline knowledge refinement |
| Periodic embedding | 6h | embedding_loop | Embed new docs/memories |
| Health audit | 15m | HealthAuditorTool | Vital signs + recovery |
| Mastermind review | 30m | MastermindAgent | Strategic campaigns |
| Autonomous cycle | 5m | MindXAgent | Tactical self-improvement |
| Book publish | startup + daily | AuthorAgent | On-demand edition |

## Oracle Queries

```python
from agents.author_agent import moon_phase
from datetime import datetime, timezone

# What time is it?
now_ns = time.time_ns()                    # CPU nanoseconds
now_utc = datetime.now(timezone.utc)       # Solar time
phase = moon_phase(now_utc)                # Lunar phase + day

# 18dp precision
from decimal import Decimal
elapsed = Decimal(str(now_ns)) / Decimal("1000000000")  # ns → seconds at 18dp
```

## Files

| File | Purpose |
|------|---------|
| `agents/Chronos.agent` | Agent definition — philosophy, scheduled task registry |
| `agents/chronos.oracle` | Oracle definition — time domains, queries, delegation |
| `tools/core/chronos_cron_tool.py` | Cron scheduler — named tasks, history, state persistence |
| `utils/time_oracle.py` | time.oracle — multi-source correlation (CPU, solar, lunar, blocktime allchain). chronos.oracle inherits from this. |
| `llm/precision_metrics.py` | 18dp Decimal measurement infrastructure |

## Principle

Without chronos, there is no preparation for kairos.
Without kairos, chronos becomes mere duration without transformation.

I keep the clock. Trust the math.
