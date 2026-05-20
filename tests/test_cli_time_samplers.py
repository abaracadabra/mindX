"""Linux terminal time + system samplers.

Each sampler is expected to return its record in < 50 ms on the dev
host so chronos.agent's 5-s refresh stays unblocking. The tests run
the *real* samplers (no mocking) because their whole purpose is to
verify the host's terminal tooling is fast and parseable — mocking
would defeat the point.
"""

from __future__ import annotations

import sys

import pytest

from utils.cli_time_samplers import (
    SAMPLERS,
    cpu_jiffies,
    is_supported,
    monotonic_boot,
    nano_wall,
    ntp_status,
    proc_snapshot,
    sample_all,
    uptime_load,
)

_LINUX_ONLY = pytest.mark.skipif(
    sys.platform != "linux",
    reason="samplers are linux-specific (timedatectl, /proc, ps -A)",
)

# Per-sampler latency budget (microseconds). Chosen well above measured
# medians on a 4-core Ryzen 3 3200U so test isn't flaky in CI.
_PER_SAMPLER_BUDGET_US = {
    "nano_wall":      50_000,    # ~3 ms typical
    "ntp_status":     500_000,   # dbus cold start can take ~100 ms
    "uptime_load":    50_000,
    "proc_snapshot":  100_000,   # ps -A walks all PIDs
    "cpu_jiffies":    10_000,    # /proc read
    "monotonic_boot": 10_000,
}


@_LINUX_ONLY
def test_is_supported_true_on_linux():
    assert is_supported() is True


@_LINUX_ONLY
def test_nano_wall_returns_int_ns_close_to_python_clock():
    """`date +%s.%N` and time.time_ns() should agree to within the fork
    latency. Anything > 1 s drift is a clock bug worth surfacing."""
    import time
    rec = nano_wall()
    assert rec["ok"] is True, rec
    assert rec["value_type"] == "ns"
    py_ns = time.time_ns()
    drift_ns = abs(rec["value"] - py_ns)
    # 500 ms is the loose cap — actual drift is typically < 5 ms.
    assert drift_ns < 500_000_000, f"date vs time.time_ns drift = {drift_ns/1e6:.1f} ms"


@_LINUX_ONLY
def test_ntp_status_reports_synchronized_or_explains_why():
    rec = ntp_status()
    if not rec["ok"]:
        pytest.skip(f"timedatectl unavailable: {rec['error']}")
    val = rec["value"]
    assert "synchronized" in val
    assert isinstance(val["synchronized"], bool)
    # If sync is False it's a host config issue, not a sampler bug —
    # surface the actual state but don't fail the test.


@_LINUX_ONLY
def test_uptime_load_parses_three_averages():
    rec = uptime_load()
    assert rec["ok"] is True, rec
    val = rec["value"]
    assert set(val) == {"load_1m", "load_5m", "load_15m"}
    for k, v in val.items():
        assert isinstance(v, float), (k, type(v))
        assert v >= 0.0


@_LINUX_ONLY
def test_proc_snapshot_returns_aggregate_and_top_n():
    rec = proc_snapshot(top_n=3)
    assert rec["ok"] is True, rec
    val = rec["value"]
    assert val["process_count"] > 10  # a normal box has dozens of procs
    assert val["total_rss_kb"] > 0
    assert isinstance(val["total_cpu_pct"], float)
    assert len(val["top"]) <= 3
    for proc in val["top"]:
        assert {"pid", "pcpu", "rss_kb", "etimes"} <= set(proc)
        assert proc["pid"] > 0


@_LINUX_ONLY
def test_cpu_jiffies_advances_on_repeat_call():
    """Two reads of /proc/stat 50 ms apart MUST show a higher total —
    if not, the kernel counter is frozen and the chronos consensus is
    untrustworthy."""
    import time as _t
    first = cpu_jiffies()
    _t.sleep(0.05)
    second = cpu_jiffies()
    assert first["ok"] and second["ok"]
    assert second["value"]["total"] > first["value"]["total"]


@_LINUX_ONLY
def test_monotonic_boot_increases_monotonically():
    import time as _t
    first = monotonic_boot()
    _t.sleep(0.01)
    second = monotonic_boot()
    assert first["ok"] and second["ok"]
    assert second["value"]["boot_seconds"] > first["value"]["boot_seconds"]


@_LINUX_ONLY
def test_sample_all_returns_every_registered_sampler():
    out = sample_all()
    assert set(out) == set(SAMPLERS)
    for name, rec in out.items():
        # The contract: keys are present even when ok=False.
        assert {"name", "value", "value_type", "captured_at_ns",
                "duration_us", "ok", "error"} <= set(rec), name


@_LINUX_ONLY
def test_each_sampler_under_per_call_budget():
    """Catches regressions where a sampler grows slow enough to
    block the 5-s UI refresh.  Skips ntp_status when the host
    doesn't have systemd-timesyncd."""
    out = sample_all()
    for name, rec in out.items():
        if not rec["ok"]:
            continue
        budget = _PER_SAMPLER_BUDGET_US[name]
        assert rec["duration_us"] < budget, (
            f"{name} took {rec['duration_us']} µs > {budget} µs budget"
        )


@_LINUX_ONLY
def test_sample_all_total_under_one_second():
    """Loose upper bound on the whole batch — anything beyond 1 s and
    the UI refresh starts feeling laggy."""
    out = sample_all()
    total_us = sum(rec["duration_us"] for rec in out.values() if rec["ok"])
    assert total_us < 1_000_000, f"batch took {total_us/1000:.1f} ms"


def test_records_always_have_contract_keys_even_on_unsupported():
    """Non-Linux hosts get error records, but the contract holds."""
    rec = nano_wall()  # safe to call cross-platform; either real result or unsupported
    assert {"name", "value", "value_type", "captured_at_ns",
            "duration_us", "ok", "error"} <= set(rec)
    assert rec["name"] == "nano_wall"
