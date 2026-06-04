"""ChronosAgent — anchor ingest, drift history, accuracy estimate, now().

Imports chronos_agent.py directly (importlib spec_from_file_location)
because `agents/__init__.py` star-imports modules that need optional
deps (aiofiles, etc.) which we don't want to pull into the test path.
"""

from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path

import pytest

_MODNAME = "chronos_agent_under_test"
_spec = importlib.util.spec_from_file_location(
    _MODNAME,
    Path(__file__).parent.parent / "agents" / "chronos_agent.py",
)
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
# Register in sys.modules BEFORE exec so dataclass(frozen=True) can
# resolve cls.__module__ on the imported types.
sys.modules[_MODNAME] = _mod
_spec.loader.exec_module(_mod)

AnchorRecord = _mod.AnchorRecord
ChronosAgent = _mod.ChronosAgent
PromisedTime = _mod.PromisedTime
_classify_consensus = _mod._classify_consensus

import pytest_asyncio


@pytest_asyncio.fixture
async def chronos(tmp_path):
    """Fresh ChronosAgent + isolated DB per test."""
    ChronosAgent._reset_for_tests()
    db = tmp_path / "anchors.db"
    inst = await ChronosAgent.get_instance(db)
    yield inst
    await inst.close()
    ChronosAgent._reset_for_tests()


@pytest.mark.asyncio
async def test_anchor_from_transaction_persists_with_id(chronos):
    rec = await chronos.anchor_from_transaction(
        chain="algorand", tx_hash="ABCD1234",
        block_number=42, block_timestamp=int(time.time()),
    )
    assert rec.id is not None and rec.id > 0
    assert rec.chain == "algorand"
    # No explicit local_observed_ns → defaults to time.time_ns().
    assert rec.local_observed_ns > 0


@pytest.mark.asyncio
async def test_drift_ms_signed_correctly(chronos):
    """local_ms ahead of block_ms → positive drift; behind → negative."""
    block_ts = 1_700_000_000  # arbitrary epoch second
    # Local clock ahead of chain by 1500 ms.
    rec = await chronos.anchor_from_transaction(
        chain="eth", tx_hash="ahead",
        block_number=1, block_timestamp=block_ts,
        local_observed_ns=(block_ts * 1_000 + 1500) * 1_000_000,
    )
    assert rec.drift_ms == pytest.approx(1500.0, abs=1.0)

    # Local clock behind chain by 800 ms.
    rec2 = await chronos.anchor_from_transaction(
        chain="eth", tx_hash="behind",
        block_number=2, block_timestamp=block_ts,
        local_observed_ns=(block_ts * 1_000 - 800) * 1_000_000,
    )
    assert rec2.drift_ms == pytest.approx(-800.0, abs=1.0)


@pytest.mark.asyncio
async def test_recent_anchors_returns_newest_first(chronos):
    for i in range(5):
        await chronos.anchor_from_transaction(
            chain="algorand", tx_hash=f"tx-{i}",
            block_number=i, block_timestamp=int(time.time()),
        )
    recent = await chronos.recent_anchors(limit=3)
    assert len(recent) == 3
    # Newest first → tx-4, tx-3, tx-2.
    assert [r.tx_hash for r in recent] == ["tx-4", "tx-3", "tx-2"]


@pytest.mark.asyncio
async def test_drift_history_buckets_and_std(chronos):
    """A spread of drifts should produce a non-zero standard deviation."""
    block_ts = int(time.time())
    for drift_ms in (100, 200, 300, 400, 500):
        await chronos.anchor_from_transaction(
            chain="algorand", tx_hash=f"d{drift_ms}",
            block_number=drift_ms, block_timestamp=block_ts,
            local_observed_ns=(block_ts * 1_000 + drift_ms) * 1_000_000,
        )
    hist = await chronos.drift_history(hours=24)
    assert hist.anchor_count == 5
    assert hist.bucket_count >= 1
    assert hist.drift_std_ms > 0
    assert hist.drift_max_abs_ms == 500.0


@pytest.mark.asyncio
async def test_accuracy_likelihood_with_low_drift_reports_correlated(chronos):
    block_ts = int(time.time())
    # 5 anchors all within ±5 ms → confidence should be small.
    for i, d in enumerate((-5, -2, 0, 2, 5)):
        await chronos.anchor_from_transaction(
            chain="algorand", tx_hash=f"low{i}",
            block_number=i, block_timestamp=block_ts,
            local_observed_ns=(block_ts * 1_000 + d) * 1_000_000,
        )
    est = await chronos.accuracy_likelihood()
    assert est.window_anchors == 5
    assert est.confidence_ms < 100
    assert est.consensus == "correlated"


@pytest.mark.asyncio
async def test_accuracy_likelihood_no_anchors_returns_drifted(chronos):
    est = await chronos.accuracy_likelihood()
    assert est.window_anchors == 0
    assert est.consensus == "drifted"
    # No history → infinite confidence interval.
    assert est.confidence_ms == float("inf")


@pytest.mark.asyncio
async def test_now_returns_promised_time_with_18dp(chronos):
    """now() always returns a PromisedTime — even with zero anchors."""
    pt = await chronos.now()
    assert isinstance(pt, PromisedTime)
    assert pt.promised_by == "chronos.agent"
    # 18dp Decimal precision: dot present, fractional part ≥ 9 digits.
    assert "." in pt.unix_18dp
    frac = pt.unix_18dp.split(".", 1)[1]
    assert len(frac) >= 9
    # Headline UTC carries nanosecond fraction.
    assert "+00:00" in pt.utc


@pytest.mark.asyncio
async def test_now_consensus_reflects_anchor_quality(chronos):
    """Tight anchors → correlated; no anchors → drifted/offline (worse)."""
    block_ts = int(time.time())
    for i in range(10):
        await chronos.anchor_from_transaction(
            chain="algorand", tx_hash=f"tight{i}",
            block_number=i, block_timestamp=block_ts,
            local_observed_ns=(block_ts * 1_000 + (i - 5)) * 1_000_000,
        )
    pt = await chronos.now()
    # Anchor confidence is well below the correlated threshold (1 s).
    # But oracle consensus may be offline if TimeOracle init fails here
    # — in that case the final tier degrades to "offline". Both are
    # acceptable as long as the anchor accounting is honest.
    assert pt.consensus in {"correlated", "offline"}
    assert pt.anchor_count_24h == 10


@pytest.mark.asyncio
async def test_as_dict_round_trip(chronos):
    rec = await chronos.anchor_from_transaction(
        chain="eth", tx_hash="0xdead",
        block_number=1, block_timestamp=int(time.time()),
    )
    d = rec.as_dict()
    assert set(d) >= {
        "id", "chain", "tx_hash", "block_number",
        "block_timestamp", "local_observed_ns", "drift_ms",
    }
    assert d["chain"] == "eth"


def test_consensus_classifier_thresholds():
    assert _classify_consensus(0.5) == "correlated"
    assert _classify_consensus(999.0) == "correlated"
    assert _classify_consensus(2_000.0) == "degraded"
    assert _classify_consensus(10_000.0) == "drifted"
    assert _classify_consensus(float("inf")) == "drifted"
