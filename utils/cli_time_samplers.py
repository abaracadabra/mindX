"""Linux terminal-command time + system samplers.

The user's framing for the chronos pair:

    optimized using linux terminal commands when possible for minimum
    and efficiency in time.

This module exposes the cheapest measurements available on a stock
Linux host — single forks of standard utilities or direct /proc reads,
no Python deps beyond stdlib. Each sampler returns a uniform record
so chronos.agent and the Coach UI can compare them side-by-side.

Sampler contract:
    {
        "name":            str,    # e.g. "nano_wall"
        "value":           Any,    # parsed reading (int, float, dict)
        "value_type":      str,    # "ns" | "iso" | "float_seconds" | "process_list" | ...
        "captured_at_ns":  int,    # time.time_ns() right before subprocess.run
        "duration_us":     int,    # microseconds the sampler took (sampler overhead)
        "ok":              bool,   # False on parse/exec failure
        "error":           str | None,
    }

Linux-only. On non-Linux platforms each sampler returns
`{"ok": False, "error": "platform not supported"}` so callers degrade
gracefully without exceptions. Tested on systemd-timesyncd (no chrony).

Reference: docs/TIME_ORACLE.md describes the four oracle classes
(cpu/solar/lunar/blocktime). These samplers feed the cpu/system half
of that consensus, replacing the slow psutil iteration with single
forks.
"""

from __future__ import annotations

import platform
import re
import subprocess
import sys
import time
from collections.abc import Callable
from typing import Any

_DEFAULT_TIMEOUT_S = 0.1  # 100 ms cap per sampler — never block the probe
_LINUX = sys.platform == "linux"


def _record(
    name: str,
    *,
    value: Any,
    value_type: str,
    captured_at_ns: int,
    started_at_ns: int,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "value": value,
        "value_type": value_type,
        "captured_at_ns": captured_at_ns,
        "duration_us": max(0, (time.time_ns() - started_at_ns) // 1000),
        "ok": error is None,
        "error": error,
    }


def _unsupported(name: str) -> dict[str, Any]:
    now_ns = time.time_ns()
    return _record(
        name,
        value=None,
        value_type="none",
        captured_at_ns=now_ns,
        started_at_ns=now_ns,
        error="platform not supported (linux-only)",
    )


def _run(cmd: list[str], *, timeout_s: float = _DEFAULT_TIMEOUT_S) -> subprocess.CompletedProcess:
    """subprocess.run wrapper with our standard caps. Caller handles errors."""
    return subprocess.run(
        cmd,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )


def _read_proc(path: str) -> str:
    """Single open/read/close on /proc — no fork."""
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---- nano_wall: ns-precision wall via `date +%s.%N` ---------------------


def nano_wall() -> dict[str, Any]:
    """Single fork of `date +%s.%N`. Returns nanoseconds since epoch as int.

    Coach uses this as the "external" wall-clock reference to cross-check
    Python's `time.time_ns()` — they should agree to within the fork
    latency (~ a few hundred µs).
    """
    if not _LINUX:
        return _unsupported("nano_wall")
    started_ns = captured_ns = time.time_ns()
    try:
        result = _run(["date", "+%s.%N"])
    except subprocess.TimeoutExpired:
        return _record(
            "nano_wall", value=None, value_type="ns",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error="timeout",
        )
    out = (result.stdout or "").strip()
    try:
        sec, nano = out.split(".")
        value_ns = int(sec) * 1_000_000_000 + int(nano.ljust(9, "0")[:9])
    except (ValueError, IndexError) as exc:
        return _record(
            "nano_wall", value=None, value_type="ns",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error=f"parse: {exc!r}; raw={out!r}",
        )
    return _record(
        "nano_wall", value=value_ns, value_type="ns",
        captured_at_ns=captured_ns, started_at_ns=started_ns,
    )


# ---- ntp_status: timedatectl ---------------------------------------------


_TIMEDATECTL_KEYS = ("NTPSynchronized", "TimeUSec", "NTP", "CanNTP")


def ntp_status() -> dict[str, Any]:
    """Read systemd-timesyncd state via `timedatectl show`.

    Returns a parsed dict like `{NTPSynchronized: True, NTP: True, ...}`.
    `synchronized` is the headline boolean the UI surfaces; the rest is
    diagnostic detail. Reports `ok=False` when timedatectl isn't on PATH.
    """
    if not _LINUX:
        return _unsupported("ntp_status")
    started_ns = captured_ns = time.time_ns()
    try:
        # timedatectl talks to systemd over dbus; first-call cold start
        # can briefly exceed the default 100 ms cap on a sleepy laptop.
        result = _run(["timedatectl", "show"], timeout_s=0.5)
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return _record(
            "ntp_status", value=None, value_type="dict",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error=f"{type(exc).__name__}: {exc}",
        )
    out: dict[str, Any] = {}
    for line in (result.stdout or "").splitlines():
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key in _TIMEDATECTL_KEYS:
            if val in ("yes", "no"):
                out[key] = val == "yes"
            else:
                out[key] = val
    out["synchronized"] = bool(out.get("NTPSynchronized", False))
    return _record(
        "ntp_status", value=out, value_type="dict",
        captured_at_ns=captured_ns, started_at_ns=started_ns,
    )


# ---- uptime_load: one fork, three load averages --------------------------


_LOAD_RE = re.compile(
    r"load average: ([\d.]+),\s*([\d.]+),\s*([\d.]+)",
)


def uptime_load() -> dict[str, Any]:
    """`uptime` parsed into {load_1m, load_5m, load_15m}."""
    if not _LINUX:
        return _unsupported("uptime_load")
    started_ns = captured_ns = time.time_ns()
    try:
        result = _run(["uptime"])
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return _record(
            "uptime_load", value=None, value_type="dict",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error=f"{type(exc).__name__}: {exc}",
        )
    match = _LOAD_RE.search(result.stdout or "")
    if not match:
        return _record(
            "uptime_load", value=None, value_type="dict",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error=f"unparseable: {(result.stdout or '').strip()!r}",
        )
    one, five, fifteen = (float(x) for x in match.groups())
    return _record(
        "uptime_load",
        value={"load_1m": one, "load_5m": five, "load_15m": fifteen},
        value_type="dict",
        captured_at_ns=captured_ns, started_at_ns=started_ns,
    )


# ---- proc_snapshot: ps -A whole-system process stats --------------------


def proc_snapshot(*, top_n: int = 5) -> dict[str, Any]:
    """`ps -A -o pid,pcpu,rss,etimes --no-headers`.

    Returns:
        {
          "process_count":   total processes,
          "total_rss_kb":    sum of RSS across all processes,
          "total_cpu_pct":   sum of pcpu (can exceed 100 on multi-core),
          "top":             list of {pid, pcpu, rss_kb, etimes} for the
                             top_n by CPU.
        }

    Cross-checks psutil's per-process iteration with a single ps fork.
    Coach uses the totals to flag drift vs psutil; the top_n list helps
    explain *which* processes account for the load.
    """
    if not _LINUX:
        return _unsupported("proc_snapshot")
    started_ns = captured_ns = time.time_ns()
    try:
        result = _run(["ps", "-A", "-o", "pid,pcpu,rss,etimes", "--no-headers"])
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return _record(
            "proc_snapshot", value=None, value_type="dict",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error=f"{type(exc).__name__}: {exc}",
        )
    rows: list[dict[str, Any]] = []
    total_rss = 0
    total_cpu = 0.0
    for line in (result.stdout or "").splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        try:
            pid = int(parts[0])
            pcpu = float(parts[1])
            rss_kb = int(parts[2])
            etimes = int(parts[3])
        except ValueError:
            continue
        rows.append({"pid": pid, "pcpu": pcpu, "rss_kb": rss_kb, "etimes": etimes})
        total_rss += rss_kb
        total_cpu += pcpu
    rows.sort(key=lambda r: r["pcpu"], reverse=True)
    return _record(
        "proc_snapshot",
        value={
            "process_count": len(rows),
            "total_rss_kb": total_rss,
            "total_cpu_pct": round(total_cpu, 2),
            "top": rows[:top_n],
        },
        value_type="dict",
        captured_at_ns=captured_ns, started_at_ns=started_ns,
    )


# ---- cpu_jiffies: /proc/stat kernel counters ----------------------------


_CPU_JIFFY_FIELDS = (
    "user", "nice", "system", "idle", "iowait",
    "irq", "softirq", "steal", "guest", "guest_nice",
)


def cpu_jiffies() -> dict[str, Any]:
    """Read /proc/stat, parse the aggregate `cpu` line.

    Returns per-state jiffies + the derived total. The ratio
    `(total - idle) / total` over two samples gives instantaneous CPU
    utilisation — but a single sample is enough to verify the counters
    are advancing (chronos.agent sanity check that the clock hasn't
    frozen).
    """
    if not _LINUX:
        return _unsupported("cpu_jiffies")
    started_ns = captured_ns = time.time_ns()
    try:
        text = _read_proc("/proc/stat")
    except OSError as exc:
        return _record(
            "cpu_jiffies", value=None, value_type="dict",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error=f"OSError: {exc}",
        )
    fields = text.split("\n", 1)[0].split()
    # First token is "cpu", remaining are jiffies.
    parts = fields[1:]
    out: dict[str, int] = {}
    for name, raw in zip(_CPU_JIFFY_FIELDS, parts):
        try:
            out[name] = int(raw)
        except ValueError:
            out[name] = 0
    out["total"] = sum(out.values())
    return _record(
        "cpu_jiffies", value=out, value_type="dict",
        captured_at_ns=captured_ns, started_at_ns=started_ns,
    )


# ---- monotonic_boot: /proc/uptime ---------------------------------------


def monotonic_boot() -> dict[str, Any]:
    """Read /proc/uptime → {boot_seconds, idle_seconds}.

    boot_seconds is *monotonic since boot* — untouched by NTP, untouched
    by user clock adjustment. Useful as a sanity reference: the
    difference between two `monotonic_boot` reads must equal the
    difference between two `nano_wall` reads (modulo NTP). When they
    diverge, the system clock was nudged — Coach surfaces that.
    """
    if not _LINUX:
        return _unsupported("monotonic_boot")
    started_ns = captured_ns = time.time_ns()
    try:
        text = _read_proc("/proc/uptime")
    except OSError as exc:
        return _record(
            "monotonic_boot", value=None, value_type="dict",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error=f"OSError: {exc}",
        )
    parts = text.split()
    try:
        boot_s = float(parts[0])
        idle_s = float(parts[1]) if len(parts) > 1 else 0.0
    except (IndexError, ValueError) as exc:
        return _record(
            "monotonic_boot", value=None, value_type="dict",
            captured_at_ns=captured_ns, started_at_ns=started_ns,
            error=f"parse: {exc}; raw={text!r}",
        )
    return _record(
        "monotonic_boot",
        value={"boot_seconds": boot_s, "idle_seconds": idle_s},
        value_type="dict",
        captured_at_ns=captured_ns, started_at_ns=started_ns,
    )


# ---- public registry / batch run ----------------------------------------


SAMPLERS: dict[str, Callable[[], dict[str, Any]]] = {
    "nano_wall": nano_wall,
    "ntp_status": ntp_status,
    "uptime_load": uptime_load,
    "proc_snapshot": proc_snapshot,
    "cpu_jiffies": cpu_jiffies,
    "monotonic_boot": monotonic_boot,
}


def sample_all() -> dict[str, dict[str, Any]]:
    """Run every registered sampler sequentially. Returns name → record.

    Sequential because total overhead is ~30–50 ms on the dev host —
    cheaper than the thread-pool dispatch overhead a parallel
    implementation would add for six sub-100 ms shell calls.
    """
    return {name: fn() for name, fn in SAMPLERS.items()}


def is_supported() -> bool:
    """Return True when the host is Linux (samplers will produce real data)."""
    return _LINUX


__all__ = [
    "SAMPLERS",
    "cpu_jiffies",
    "is_supported",
    "monotonic_boot",
    "nano_wall",
    "ntp_status",
    "proc_snapshot",
    "sample_all",
    "uptime_load",
]
