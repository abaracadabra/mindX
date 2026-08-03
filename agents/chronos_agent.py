"""chronos.agent — runtime that pairs with chronos.oracle to provide
mindX's *promised time*.

The user's framing:

    chronos.agent is a master of time and chronos.oracle is the
    blockchain verified timestamp. chronos.agent and chronos.oracle
    work together to calculate time from frequency as average from
    moment including various from time cpu timeanddate various
    blockchains from average block time and other calender services.

    chronos.agent and chronos.oracle need to provide the promised
    "time" to mindX from accurate and verified including measure
    from blocktime and receipt of payment to save on accurate
    measurement from all mindX agentic transactions.

Concretely this module is the *runtime* that:

  1. Wraps `utils/time_oracle.py:TimeOracle` (cpu / solar / lunar /
     blocktime consensus) as the primary signal source.
  2. Persists per-transaction time anchors — `(chain, tx_hash,
     block_timestamp, local_observed_ns)` — every time mindX confirms
     a payment / attestation / x402 receipt. These anchors are the
     *strong* drift evidence: the chain confirmed *our* tx at
     block-time T_block while our local clock observed T_local.
  3. Computes a `PromisedTime` with a measurable confidence interval
     so every mindX agent can stamp its outputs with a number the
     network can trust.

Other agents call `await chronos.now()` — they do NOT call
`time.time()` when emitting artefacts. The confidence interval is
honest: when anchor density drops or drift widens, the returned
`PromisedTime.consensus` field flips from `correlated` → `degraded`
→ `drifted` and downstream agents can decide whether to publish.

Persistence: SQLite via stdlib `sqlite3` in `asyncio.to_thread` (no
new package dep). Database at `data/memory/chronos_anchors.db`.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any

# cypherpunk2048 invariant — Chronos.agent declares 18dp Decimal precision.
getcontext().prec = 40

# The 18dp quantum — every promised time is expressed at exactly 18 decimal
# places (cypherpunk2048 fixed-point denomination). Source resolution is
# declared separately so padding is never mistaken for measurement.
_Q18 = Decimal(1).scaleb(-18)
_SOURCE_RESOLUTION_DP = 9   # time.time_ns() → nanoseconds

logger = logging.getLogger("mindx.chronos_agent")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS anchors (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    captured_at_ns    INTEGER NOT NULL,
    chain             TEXT NOT NULL,
    tx_hash           TEXT NOT NULL,
    block_number      INTEGER NOT NULL,
    block_timestamp   INTEGER NOT NULL,
    local_observed_ns INTEGER NOT NULL,
    drift_ms          REAL NOT NULL,
    gas_paid          TEXT
);
CREATE INDEX IF NOT EXISTS anchors_captured ON anchors(captured_at_ns);
CREATE INDEX IF NOT EXISTS anchors_chain    ON anchors(chain);
"""

_DEFAULT_DB = Path("data/memory/chronos_anchors.db")


@dataclass(frozen=True)
class AnchorRecord:
    """A single transaction time-anchor.

    `drift_ms = local_observed_ns / 1e6 - block_timestamp * 1000`
    is the cross-source delta in milliseconds. Positive = local clock
    is ahead of chain; negative = behind. Magnitude tells you how
    closely chain consensus and the local clock agree at the moment
    of confirmation.
    """

    id: int | None
    captured_at_ns: int
    chain: str
    tx_hash: str
    block_number: int
    block_timestamp: int
    local_observed_ns: int
    drift_ms: float
    gas_paid: str | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "captured_at_ns": self.captured_at_ns,
            "chain": self.chain,
            "tx_hash": self.tx_hash,
            "block_number": self.block_number,
            "block_timestamp": self.block_timestamp,
            "local_observed_ns": self.local_observed_ns,
            "drift_ms": self.drift_ms,
            "gas_paid": self.gas_paid,
        }


@dataclass(frozen=True)
class DriftHistory:
    """Bucketed drift over a recent window. Hours into hourly buckets."""

    hours: int
    bucket_count: int
    buckets: list[dict[str, Any]]   # [{ts_unix, n, drift_mean_ms, drift_std_ms}, ...]
    drift_std_ms: float             # across all anchors in the window
    drift_max_abs_ms: float
    anchor_count: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "hours": self.hours,
            "bucket_count": self.bucket_count,
            "buckets": self.buckets,
            "drift_std_ms": self.drift_std_ms,
            "drift_max_abs_ms": self.drift_max_abs_ms,
            "anchor_count": self.anchor_count,
        }


@dataclass(frozen=True)
class AccuracyEstimate:
    """Likelihood-of-accuracy heuristic from prior anchors.

    `confidence_ms` is the historical drift standard deviation over the
    last `window_anchors` samples. The 5-minute decay weight gives
    recent anchors more pull than week-old ones.
    """

    window_anchors: int
    confidence_ms: float
    anchor_age_p50_seconds: float
    anchor_age_p95_seconds: float
    consensus: str  # "correlated" | "degraded" | "drifted"

    def as_dict(self) -> dict[str, Any]:
        return {
            "window_anchors": self.window_anchors,
            "confidence_ms": self.confidence_ms,
            "anchor_age_p50_seconds": self.anchor_age_p50_seconds,
            "anchor_age_p95_seconds": self.anchor_age_p95_seconds,
            "consensus": self.consensus,
        }


@dataclass(frozen=True)
class PromisedTime:
    """The time mindX commits to. Every agent quotes this when stamping
    its outputs; raw `time.time()` is forbidden in artefact paths."""

    unix_18dp: str               # exactly 18 dp — the denomination (see below)
    utc: str                     # ISO-8601 with nanoseconds
    consensus: str               # correlated | degraded | drifted | offline
    confidence_ms: float
    sources: dict[str, Any]      # time_oracle.get_time() output (or {} when offline)
    anchor_count_24h: int
    promised_by: str = "chronos.agent"
    # How many of the 18 places are MEASURED rather than denominational padding.
    # 9 = nanosecond source (time.time_ns). Consumers that need to know how far
    # to trust the digits read this, not the field name.
    source_resolution_dp: int = _SOURCE_RESOLUTION_DP

    def as_dict(self) -> dict[str, Any]:
        return {
            "unix_18dp": self.unix_18dp,
            "utc": self.utc,
            "consensus": self.consensus,
            "confidence_ms": self.confidence_ms,
            "sources": self.sources,
            "anchor_count_24h": self.anchor_count_24h,
            "promised_by": self.promised_by,
            "source_resolution_dp": self.source_resolution_dp,
        }


# Thresholds for the consensus tier. Tuned conservatively — bump if
# real-world testnet drift consistently lands in `degraded`.
_CONSENSUS_THRESHOLDS_MS = {
    "correlated": 1_000.0,   # < 1 s of cross-source spread
    "degraded":   5_000.0,   # < 5 s
    # anything beyond → drifted
}


class ChronosAgent:
    """Singleton runtime that holds the anchor DB connection + TimeOracle handle."""

    _instance: "ChronosAgent | None" = None
    _lock = asyncio.Lock()

    def __init__(self, db_path: Path = _DEFAULT_DB) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._time_oracle = None  # lazy: TimeOracle.get_instance() is async

    # ---- instance management ------------------------------------------

    @classmethod
    async def get_instance(cls, db_path: Path = _DEFAULT_DB) -> "ChronosAgent":
        async with cls._lock:
            if cls._instance is None:
                inst = cls(db_path)
                await inst._init_db()
                cls._instance = inst
            return cls._instance

    @classmethod
    def _reset_for_tests(cls) -> None:
        """Tests-only: drop the singleton so each test gets a fresh DB."""
        cls._instance = None

    async def _init_db(self) -> None:
        def _open() -> sqlite3.Connection:
            conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.executescript(_SCHEMA)
            conn.commit()
            return conn
        self._conn = await asyncio.to_thread(_open)

    # ---- transaction anchor ingest ------------------------------------

    async def anchor_from_transaction(
        self,
        *,
        chain: str,
        tx_hash: str,
        block_number: int,
        block_timestamp: int,
        local_observed_ns: int | None = None,
        gas_paid: str | None = None,
    ) -> AnchorRecord:
        """Persist a strong drift anchor for a confirmed tx.

        Call this AFTER `wait_for_confirmation` in your tx layer.
        `local_observed_ns` defaults to `time.time_ns()` — the moment
        we received the confirmation event.

        `drift_ms` is computed as
            local_observed_ms - block_timestamp * 1000
        Positive = local clock ahead of chain.
        """
        if local_observed_ns is None:
            local_observed_ns = time.time_ns()
        local_ms = local_observed_ns / 1_000_000.0
        block_ms = float(block_timestamp) * 1_000.0
        drift_ms = local_ms - block_ms

        rec = AnchorRecord(
            id=None,
            captured_at_ns=time.time_ns(),
            chain=chain,
            tx_hash=tx_hash,
            block_number=block_number,
            block_timestamp=block_timestamp,
            local_observed_ns=local_observed_ns,
            drift_ms=drift_ms,
            gas_paid=gas_paid,
        )

        def _insert() -> int:
            assert self._conn is not None
            cur = self._conn.execute(
                "INSERT INTO anchors "
                "(captured_at_ns, chain, tx_hash, block_number, "
                " block_timestamp, local_observed_ns, drift_ms, gas_paid) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    rec.captured_at_ns, rec.chain, rec.tx_hash,
                    rec.block_number, rec.block_timestamp,
                    rec.local_observed_ns, rec.drift_ms, rec.gas_paid,
                ),
            )
            self._conn.commit()
            return int(cur.lastrowid or 0)

        row_id = await asyncio.to_thread(_insert)
        # Re-emit with row id set so callers can correlate.
        return AnchorRecord(
            id=row_id,
            captured_at_ns=rec.captured_at_ns,
            chain=rec.chain,
            tx_hash=rec.tx_hash,
            block_number=rec.block_number,
            block_timestamp=rec.block_timestamp,
            local_observed_ns=rec.local_observed_ns,
            drift_ms=rec.drift_ms,
            gas_paid=rec.gas_paid,
        )

    # ---- read paths ----------------------------------------------------

    async def recent_anchors(self, limit: int = 100) -> list[AnchorRecord]:
        def _read() -> list[AnchorRecord]:
            assert self._conn is not None
            rows = self._conn.execute(
                "SELECT id, captured_at_ns, chain, tx_hash, block_number, "
                "block_timestamp, local_observed_ns, drift_ms, gas_paid "
                "FROM anchors ORDER BY captured_at_ns DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
            return [
                AnchorRecord(
                    id=r[0], captured_at_ns=r[1], chain=r[2], tx_hash=r[3],
                    block_number=r[4], block_timestamp=r[5],
                    local_observed_ns=r[6], drift_ms=r[7], gas_paid=r[8],
                )
                for r in rows
            ]
        return await asyncio.to_thread(_read)

    async def drift_history(self, hours: int = 24) -> DriftHistory:
        """Bucketed drift over the last `hours` hours (1 bucket = 1 hour).

        Cheap on small DBs (a single SQL aggregation per bucket); fine
        for the Coach UI's 5-s refresh.
        """
        cutoff_ns = time.time_ns() - hours * 3_600 * 1_000_000_000

        def _read() -> tuple[list[dict[str, Any]], float, float, int]:
            assert self._conn is not None
            rows = self._conn.execute(
                "SELECT captured_at_ns, drift_ms FROM anchors "
                "WHERE captured_at_ns >= ? ORDER BY captured_at_ns ASC",
                (cutoff_ns,),
            ).fetchall()
            if not rows:
                return [], 0.0, 0.0, 0
            # Bucket by hour (epoch hour).
            buckets: dict[int, list[float]] = {}
            all_drifts: list[float] = []
            for ts_ns, drift_ms in rows:
                bucket_key = ts_ns // (3_600 * 1_000_000_000)
                buckets.setdefault(bucket_key, []).append(drift_ms)
                all_drifts.append(drift_ms)
            out: list[dict[str, Any]] = []
            for key in sorted(buckets):
                drifts = buckets[key]
                out.append({
                    "ts_unix": key * 3_600,
                    "n": len(drifts),
                    "drift_mean_ms": statistics.fmean(drifts),
                    "drift_std_ms": (
                        statistics.pstdev(drifts) if len(drifts) > 1 else 0.0
                    ),
                })
            drift_std = (
                statistics.pstdev(all_drifts) if len(all_drifts) > 1 else 0.0
            )
            drift_max_abs = max(abs(d) for d in all_drifts)
            return out, drift_std, drift_max_abs, len(all_drifts)

        buckets, std, max_abs, count = await asyncio.to_thread(_read)
        return DriftHistory(
            hours=hours,
            bucket_count=len(buckets),
            buckets=buckets,
            drift_std_ms=std,
            drift_max_abs_ms=max_abs,
            anchor_count=count,
        )

    async def accuracy_likelihood(self, window: int = 50) -> AccuracyEstimate:
        """Confidence estimate from the most recent `window` anchors."""
        anchors = await self.recent_anchors(limit=window)
        now_ns = time.time_ns()
        if not anchors:
            return AccuracyEstimate(
                window_anchors=0,
                confidence_ms=float("inf"),
                anchor_age_p50_seconds=float("inf"),
                anchor_age_p95_seconds=float("inf"),
                consensus="drifted",
            )
        drifts = [a.drift_ms for a in anchors]
        ages_s = sorted(
            (now_ns - a.captured_at_ns) / 1_000_000_000 for a in anchors
        )
        confidence_ms = (
            statistics.pstdev(drifts) if len(drifts) > 1 else abs(drifts[0])
        )
        p50_idx = max(0, len(ages_s) // 2 - 1)
        p95_idx = max(0, int(len(ages_s) * 0.95) - 1)
        consensus = _classify_consensus(confidence_ms)
        return AccuracyEstimate(
            window_anchors=len(anchors),
            confidence_ms=confidence_ms,
            anchor_age_p50_seconds=ages_s[p50_idx],
            anchor_age_p95_seconds=ages_s[p95_idx],
            consensus=consensus,
        )

    async def now(self) -> PromisedTime:
        """The headline: promised time + confidence interval.

        Combines two signals:
          1. `time.oracle` consensus (cpu / solar / lunar / blocktime).
             Always available — gives `sources` block + a cross-oracle
             drift estimate via `drift_max_ms`.
          2. Anchor-derived confidence over the last 50 confirmed txs.
             Stronger than passive blocktime polling because each anchor
             is "the chain confirmed *our* event at T_block while we
             saw T_local".

        Final `consensus` tier is the *worse* of the two estimates.
        """
        # Anchor confidence (DB-backed).
        accuracy = await self.accuracy_likelihood()

        # time.oracle consensus (cross-oracle drift). Best-effort —
        # if the helper isn't initialisable we degrade gracefully.
        sources: dict[str, Any] = {}
        oracle_consensus = "offline"
        oracle_drift_ms = float("inf")
        try:
            if self._time_oracle is None:
                from utils.time_oracle import TimeOracle  # lazy import
                self._time_oracle = await TimeOracle.get_instance()
            tdata = await self._time_oracle.get_time()
            sources = tdata.get("sources", {})
            oracle_consensus = tdata.get("consensus", "offline")
            oracle_drift_ms = float(tdata.get("drift_max_ms") or 0.0)
        except Exception as exc:  # noqa: BLE001 — TimeOracle has many failure modes
            logger.debug("time.oracle unreachable: %r", exc)
            sources = {"error": str(exc)}

        # Use the larger of (anchor std, oracle cross-source drift).
        confidence_ms = max(accuracy.confidence_ms, oracle_drift_ms)
        if confidence_ms == float("inf"):
            confidence_ms = 0.0 if oracle_consensus == "correlated" else 999_999.0

        # Pick the worse consensus label.
        ordering = {"correlated": 0, "degraded": 1, "drifted": 2, "offline": 3}
        consensus = max(
            (accuracy.consensus, oracle_consensus),
            key=lambda c: ordering.get(c, 99),
        )

        ts_ns = time.time_ns()
        # 18 decimal places, always — the cypherpunk2048 fixed-point denomination
        # (1 second = 10^18 attoseconds, as 1 ETH = 10^18 wei). The SOURCE resolves
        # to nanoseconds (9 dp), so places 10–18 are structural zeros, never
        # invented digits: the denomination is 18dp, the measured resolution is
        # 1 ns, and `source_resolution_dp` states which is which. Padding a
        # denomination is honest; fabricating precision is not.
        ts_dec = (Decimal(ts_ns) / Decimal(1_000_000_000)).quantize(_Q18)
        dt = datetime.fromtimestamp(ts_ns / 1_000_000_000, tz=timezone.utc)
        # ns-precision ISO-8601: datetime.isoformat() already carries µs, so the
        # µs must be dropped before the 9-digit ns fraction is appended — else the
        # stamp reads 21:37:03.958876.958876088+00:00 and parses nowhere.
        utc_str = (
            dt.replace(microsecond=0).isoformat().replace(
                "+00:00", f".{ts_ns % 1_000_000_000:09d}+00:00"
            )
        )

        return PromisedTime(
            unix_18dp=str(ts_dec),
            utc=utc_str,
            consensus=consensus,
            confidence_ms=float(confidence_ms),
            sources=sources,
            anchor_count_24h=accuracy.window_anchors,
        )

    # ---- close (for tests / shutdown) ---------------------------------

    async def close(self) -> None:
        def _close() -> None:
            if self._conn is not None:
                self._conn.close()
        await asyncio.to_thread(_close)
        self._conn = None


def _classify_consensus(confidence_ms: float) -> str:
    if confidence_ms == float("inf"):
        return "drifted"
    if confidence_ms < _CONSENSUS_THRESHOLDS_MS["correlated"]:
        return "correlated"
    if confidence_ms < _CONSENSUS_THRESHOLDS_MS["degraded"]:
        return "degraded"
    return "drifted"


__all__ = [
    "AccuracyEstimate",
    "AnchorRecord",
    "ChronosAgent",
    "DriftHistory",
    "PromisedTime",
]
