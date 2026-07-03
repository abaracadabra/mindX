"""Unit tests for the ResourceGovernor dynamic CPU gate.

The gate lets the autonomous loops + background inference "share the processor":
back off while system CPU is over a ~92% ceiling, proceed when it drops. These
tests pin the math, the fail-open contract (a sensor error must NEVER block work),
env-var precedence on the ceiling, and the background-only inference semaphore.

Plain `def test_*` + `asyncio.run(...)` per this repo's convention (cf.
tests/test_bdi_distill_hook.py).
"""
import asyncio

from agents.resource_governor import ResourceGovernor


def _fresh() -> ResourceGovernor:
    """A standalone governor instance (bypass the singleton so tests don't bleed)."""
    return ResourceGovernor()


def test_ceiling_default_and_env_precedence(monkeypatch):
    monkeypatch.delenv("MINDX_MAX_AUTONOMOUS_CPU", raising=False)
    # absent env → falls through to Config default (92.0) or the hard default
    assert _fresh().autonomous_cpu_ceiling == 92.0

    monkeypatch.setenv("MINDX_MAX_AUTONOMOUS_CPU", "88")
    assert _fresh().autonomous_cpu_ceiling == 88.0

    # garbage env → safe fallback, never crashes
    monkeypatch.setenv("MINDX_MAX_AUTONOMOUS_CPU", "not-a-number")
    assert _fresh().autonomous_cpu_ceiling == 92.0


def test_throttle_proceeds_when_cpu_drops_below_ceiling():
    g = _fresh()
    seq = [99.0, 95.0, 50.0]
    state = {"n": 0}

    def fake_cpu():
        v = seq[min(state["n"], len(seq) - 1)]
        state["n"] += 1
        return v

    g._current_cpu = fake_cpu
    proceeded = asyncio.run(g.throttle_for_cpu(ceiling=92.0, max_wait=60))
    assert proceeded is True
    assert state["n"] >= 3  # backed off twice before the third read cleared
    assert g._throttling is None  # cleared on return


def test_throttle_skips_when_cpu_stays_high():
    g = _fresh()
    g._current_cpu = lambda: 99.0
    # max_wait small so the bounded backoff loop terminates fast
    proceeded = asyncio.run(g.throttle_for_cpu(ceiling=92.0, max_wait=11))
    assert proceeded is False  # caller should SKIP this cycle
    assert g._throttling is None


def test_throttle_is_fail_open_on_sensor_error():
    g = _fresh()

    def boom():
        raise RuntimeError("psutil exploded")

    g._current_cpu = boom
    # A sensor error must NEVER hang or block work — it proceeds.
    assert asyncio.run(g.throttle_for_cpu(max_wait=5)) is True


def test_should_throttle_and_headroom_fail_open():
    g = _fresh()
    g._current_cpu = lambda: 42.0
    assert g.should_throttle(ceiling=92.0) is False
    assert g.cpu_headroom() == 92.0 - 42.0

    g._current_cpu = lambda: 95.0
    assert g.should_throttle(ceiling=92.0) is True
    assert g.cpu_headroom() == 0.0  # clamped at 0

    g._current_cpu = lambda: (_ for _ in ()).throw(RuntimeError())
    assert g.should_throttle() is False  # fail-open → don't throttle


def test_get_status_includes_cpu_block():
    g = _fresh()
    g._current_cpu = lambda: 42.0
    st = g.get_status()
    assert "cpu" in st
    assert st["cpu"]["ceiling"] == 92.0
    assert st["cpu"]["current"] == 42.0
    assert st["cpu"]["throttling"] is False
    assert st["cpu"]["throttle_label"] is None


def test_inference_slot_is_bounded_semaphore(monkeypatch):
    monkeypatch.delenv("MINDX_INFERENCE_CONCURRENCY", raising=False)

    async def go():
        g = _fresh()
        sem = g.inference_slot()
        assert sem._value == 1  # default size 1 on the 2-core box
        # same instance returned (lazy singleton per governor)
        assert g.inference_slot() is sem
        return True

    assert asyncio.run(go()) is True


def test_inference_concurrency_env_override(monkeypatch):
    monkeypatch.setenv("MINDX_INFERENCE_CONCURRENCY", "3")

    async def go():
        return _fresh().inference_slot()._value

    assert asyncio.run(go()) == 3
