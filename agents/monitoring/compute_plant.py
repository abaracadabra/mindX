# SPDX-License-Identifier: Apache-2.0
# (c) 2026 BANKON / cypherpunk2048.
"""compute_plant — mindX's power-plant model of its own hardware.

Doctrine (operator, 2026-07-02): treat each core as the computer processor it is,
and optimize for RETURN from the smallest unit — the **powerplant** = 1 core +
2.048 GB RAM. Design to scale by powers of two (RAM 2→4→8→16→32→64 GB; cores 1→2→
4→8…). On any host, allocate cores by ROLE:

  • SURFACE   — 1 core + ~25% RAM runs day-to-day + the public-facing surface.
  • TRAINING  — 1 core drives mindXtrain (one core leaves us wanting more, but we
                have time — so optimize for one core). /data → machine.dream →
                mindXtrain → **mindXmodel** shrinks /data's size into weights.
  • SPARE     — an open processor for everything else.

This module measures the plant (chip frequency + cycles + per-core load) and emits
the role allocation + the power-of-two scale ladder. Read-only; psutil-based.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

UNIT_CORES = 1
UNIT_RAM_GB = 2.048           # the powerplant unit — optimize for return on this
SURFACE_RAM_FRACTION = 0.25   # 1 core + 25% RAM handles day-to-day + public surface


def _psutil():
    import psutil
    return psutil


def frequency() -> Dict[str, Any]:
    """Chip frequency (MHz): aggregate + per-core current/min/max where available."""
    p = _psutil()
    out: Dict[str, Any] = {}
    try:
        agg = p.cpu_freq()
        if agg:
            out["current_mhz"] = round(agg.current, 1)
            out["min_mhz"] = round(agg.min, 1)
            out["max_mhz"] = round(agg.max, 1)
    except Exception:
        pass
    try:
        per = p.cpu_freq(percpu=True) or []
        out["per_core_mhz"] = [round(f.current, 1) for f in per]
    except Exception:
        out["per_core_mhz"] = []
    return out


def cycles() -> Dict[str, Any]:
    """Estimated CPU cycles in flight = Σ_core (freq_hz × utilisation). A scientific
    read of *work being done*, not just percent-busy: a core at 50% of 3 GHz is
    1.5 Gcycle/s. Per-core + total (Gcycle/s)."""
    p = _psutil()
    per_freq = frequency().get("per_core_mhz", [])
    try:
        per_util = p.cpu_percent(interval=0.3, percpu=True)
    except Exception:
        per_util = []
    n = max(len(per_freq), len(per_util))
    # if per-core freq is unavailable, fall back to the aggregate for every core
    agg_mhz = frequency().get("current_mhz")
    per_core = []
    total = 0.0
    for i in range(n):
        mhz = per_freq[i] if i < len(per_freq) else (agg_mhz or 0.0)
        util = per_util[i] if i < len(per_util) else 0.0
        gcs = (mhz * 1e6) * (util / 100.0) / 1e9    # Gcycle/s
        per_core.append({"core": i, "mhz": round(mhz, 1), "util_pct": round(util, 1),
                         "gcycles_per_s": round(gcs, 3)})
        total += gcs
    return {"per_core": per_core, "total_gcycles_per_s": round(total, 3)}


def _pow2_tier(ram_gb: float) -> int:
    """Largest power-of-two GB tier ≤ ram_gb (min 2)."""
    t = 2
    while t * 2 <= ram_gb:
        t *= 2
    return t


def scale_ladder() -> List[Dict[str, Any]]:
    """The power-of-two scaling plan from the powerplant unit up: what each RAM tier
    affords (cores assumed to scale with the tier index)."""
    ladder = []
    for gb in (2, 4, 8, 16, 32, 64):
        cores = max(1, int(math.log2(gb)))          # 2→1, 4→2, 8→3, 16→4, 32→5, 64→6
        surface = 1
        training = max(0, min(cores - surface, 1 + (cores - 2) // 2)) if cores >= 2 else 0
        spare = max(0, cores - surface - training)
        ladder.append({"ram_gb": gb, "cores": cores, "surface_cores": surface,
                       "training_cores": training, "spare_cores": spare,
                       "units": round(gb / UNIT_RAM_GB, 1)})
    return ladder


def allocation() -> Dict[str, Any]:
    """The role allocation for THIS host: surface (1 core + 25% RAM), training (1
    core when available), spare (the rest) — the open-processor-for-everything-else."""
    p = _psutil()
    cores = p.cpu_count(logical=True) or 1
    ram_gb = round(p.virtual_memory().total / 1e9, 3)
    surface_cores = 1
    training_cores = 1 if cores >= 2 else 0
    spare_cores = max(0, cores - surface_cores - training_cores)
    return {
        "cores_total": cores, "ram_gb": ram_gb, "pow2_tier_gb": _pow2_tier(ram_gb),
        "units": round(ram_gb / UNIT_RAM_GB, 1),
        "surface":  {"cores": surface_cores, "ram_gb": round(ram_gb * SURFACE_RAM_FRACTION, 3),
                     "role": "day-to-day + public-facing surface"},
        "training": {"cores": training_cores,
                     "role": "mindXtrain — /data → dream → mindXmodel (one core; we have time)"},
        "spare":    {"cores": spare_cores, "role": "open processor — everything else"},
    }


def plan() -> Dict[str, Any]:
    """The whole plant: unit, this-host allocation, chip frequency, cycles in flight,
    and the power-of-two scale ladder."""
    return {
        "powerplant_unit": {"cores": UNIT_CORES, "ram_gb": UNIT_RAM_GB,
                            "doctrine": "optimize for return from 1 core + 2.048 GB"},
        "allocation": allocation(),
        "frequency": frequency(),
        "cycles": cycles(),
        "scale_ladder": scale_ladder(),
    }
