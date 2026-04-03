# time.oracle — Multi-Source Time Correlation

A sovereign system cannot depend on a single clock. time.oracle correlates four independent time sources into a consensus time object.

## Architecture

```
time.oracle (master coordinator)
    |
    +-- cpu.oracle        time.time() + time.monotonic()
    |                     Always available. The heartbeat baseline.
    |
    +-- solar.oracle      Sunrise, sunset, solar noon
    |                     Astronomical calculation for server location.
    |                     1h cache. Pure math, no external deps.
    |
    +-- lunar.oracle      Moon phase (day 0-29.5)
    |                     Astronomical calculation + timeanddate.com verification.
    |                     6h cache. Drives the 28-day Book publishing cycle.
    |                     Reference: https://www.timeanddate.com/moon/phases/
    |
    +-- blocktime.oracle  Blockchain block timestamp
                          eth_getBlockByNumber via JSON-RPC.
                          2min cache. Immutable, decentralized reference.
                          Drift detection: |cpu_time - block_time|
```

## Consensus Output

```json
{
  "utc": "2026-04-03T20:39:00+00:00",
  "unix": 1775245140.0,
  "sources": {
    "cpu": {"unix": 1775245140.0, "monotonic": 12345.6, "stale": false},
    "solar": {"sunrise": "05:42 UTC", "sunset": "18:15 UTC", "is_day": true, "stale": false},
    "lunar": {"phase": "waning gibbous", "day": 16.2, "is_full": false, "source": "timeanddate.com", "stale": false},
    "blocktime": {"block_number": 12345678, "block_timestamp": 1775245128, "drift_ms": 12000, "stale": false}
  },
  "drift_max_ms": 12000,
  "stale_sources": [],
  "consensus": "correlated"
}
```

## Usage

```python
from utils.time_oracle import TimeOracle

oracle = await TimeOracle.get_instance()

# Full consensus
consensus = await oracle.get_time()

# Just lunar (for AuthorAgent)
lunar = await oracle.get_lunar()

# Just solar
solar = await oracle.get_solar()
```

## Configuration

| Env Var | Default | Purpose |
|---------|---------|---------|
| `MINDX_LATITUDE` | 50.1 | Server latitude for solar calculations |
| `MINDX_LONGITUDE` | 14.4 | Server longitude for solar calculations |
| `MINDX_TIME_ORACLE_RPC_URL` | (none) | Ethereum JSON-RPC URL for blocktime |
| `MINDX_ACCESS_GATE_RPC_URL` | (none) | Fallback RPC URL |

## Cache

| Oracle | TTL | Location |
|--------|-----|----------|
| cpu | 0s (always fresh) | — |
| solar | 3600s (1h) | in-memory |
| lunar | 21600s (6h) | `data/governance/moon_cache.json` |
| blocktime | 120s (2min) | in-memory |
| consensus | per-call | `data/governance/time_oracle_cache.json` + pgvectorscale |

## AuthorAgent Integration

AuthorAgent uses time.oracle for the lunar publishing cycle:
- `write_daily_chapter()` calls `oracle.get_lunar()` for moon phase
- Daily chapter headers include phase, day count, days to full moon
- Full moon compilation (day 28) triggers when `is_full == True`
- Falls back to local `moon_phase()` if time.oracle is unavailable

## Future: Oracle Correlation

time.oracle is the first step toward a broader oracle framework:
- **lunar.oracle + solar.oracle** → natural time (cycles, seasons)
- **blocktime.oracle** → decentralized consensus time (immutable)
- **cpu.oracle** → computational time (monotonic, reliable)
- **Correlation** → detect drift, identify stale sources, trust scoring

The on-chain OracleRegistry.sol (at `daio/contracts/oracles/core/`) already implements multi-source aggregation with heartbeat validation and staleness detection for price feeds. time.oracle extends this pattern to temporal data.

## Key Files

| File | Purpose |
|------|---------|
| `utils/time_oracle.py` | TimeOracle, CpuOracle, SolarOracle, LunarOracle, BlocktimeOracle |
| `agents/author_agent.py` | Consumer — lunar publishing cycle |
| `data/governance/moon_cache.json` | Lunar phase cache (timeanddate.com) |
| `data/governance/time_oracle_cache.json` | Full consensus snapshot |
| `daio/contracts/oracles/core/OracleRegistry.sol` | On-chain oracle pattern (reference) |
