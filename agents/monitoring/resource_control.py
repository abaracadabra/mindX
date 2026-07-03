# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""resource_control — a bounded, self-terminating load harness for TESTING the
resource governor: control each CPU core independently (pinned via affinity) and
hold a RAM target. Every load carries a hard stop time, so a worker self-exits even
if the controller is lost — it can never wedge the box.

This is the companion to agents/monitoring/resource_monitor.py (reads load) and
agents/resource_governor.py (limits load): resource_control *creates* load, on
demand, per core, so the limiter's response can be observed under known conditions.
"""
from __future__ import annotations

import time
import logging
import multiprocessing as mp
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger("mindx.resource_control")

_MAX_DURATION = 120.0   # safety cap: no single load may run longer than this


def _cpu_worker(core: int, pct: float, stop_t: float) -> None:
    """Busy-loop at `pct` duty on a single core (pinned via affinity when supported)."""
    try:
        import psutil
        psutil.Process().cpu_affinity([core])
    except Exception:
        pass
    duty = max(0.0, min(1.0, pct / 100.0))
    period = 0.04
    while time.time() < stop_t:
        t0 = time.time()
        while time.time() - t0 < duty * period:
            _ = 1 * 1
        rest = (1.0 - duty) * period
        if rest > 0:
            time.sleep(rest)


def _ram_worker(mb: float, stop_t: float) -> None:
    """Allocate + touch `mb` megabytes and hold them resident until stop_t."""
    try:
        blob = bytearray(int(mb * 1024 * 1024))
        for i in range(0, len(blob), 4096):   # touch each page → resident RSS
            blob[i] = 1
    except MemoryError:
        return
    while time.time() < stop_t:
        time.sleep(0.5)


class ResourceController:
    """Spawn/stop bounded per-core CPU load and RAM load. Test-only."""

    def __init__(self) -> None:
        self._procs: List[mp.Process] = []

    def set_cores(self, targets: Union[Dict[int, float], List[float]],
                  duration: float = 15.0) -> Dict[str, Any]:
        """Load each core to a target percent. `targets` = {core: pct} or a per-core
        list [pct0, pct1, …]. Each worker is pinned to its core and self-stops."""
        duration = min(float(duration), _MAX_DURATION)
        stop_t = time.time() + duration
        if isinstance(targets, list):
            targets = {i: p for i, p in enumerate(targets)}
        started = []
        for core, pct in targets.items():
            p = mp.Process(target=_cpu_worker, args=(int(core), float(pct), stop_t), daemon=True)
            p.start(); self._procs.append(p); started.append({"core": int(core), "pct": float(pct)})
        logger.info(f"resource_control: loading cores {started} for {duration}s")
        return {"cores": started, "duration": duration, "stops_at": stop_t}

    def set_ram(self, mb: float, duration: float = 15.0) -> Dict[str, Any]:
        """Hold `mb` megabytes resident for `duration` seconds (self-stops)."""
        duration = min(float(duration), _MAX_DURATION)
        stop_t = time.time() + duration
        p = mp.Process(target=_ram_worker, args=(float(mb), stop_t), daemon=True)
        p.start(); self._procs.append(p)
        logger.info(f"resource_control: holding {mb}MB RAM for {duration}s")
        return {"mb": mb, "duration": duration, "stops_at": stop_t}

    def stop(self) -> Dict[str, Any]:
        """Terminate every active load immediately."""
        n = 0
        for p in self._procs:
            if p.is_alive():
                p.terminate(); n += 1
        for p in self._procs:
            p.join(timeout=2)
        self._procs = []
        return {"stopped": n}

    @staticmethod
    def status() -> Dict[str, Any]:
        """Live per-core CPU + RAM (the observation side)."""
        try:
            import psutil
            vm = psutil.virtual_memory()
            return {"per_core": psutil.cpu_percent(interval=0.3, percpu=True),
                    "cpu_total": psutil.cpu_percent(interval=None),
                    "cores": psutil.cpu_count(),
                    "memory_percent": vm.percent,
                    "memory_used_gb": round(vm.used / 1e9, 2),
                    "memory_total_gb": round(vm.total / 1e9, 2)}
        except Exception as e:
            return {"error": str(e)}
