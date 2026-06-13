"""settings — the single CPU-processor + RAM combination training is measured on.

CPU training is measured against ONE defined hardware profile (the processor +
RAM combination) so results are comparable and portable: the same script on the
same profile should cost the same cycles and yield the same imprint. The
profile + the regimen (smallest model, 33% CPU, 24h wall ≈ 8h effective) live
in a settings file — the source of truth — with the package constants as the
fallback. The profile auto-populates from the host on first load.

settings file: data/config/mindxtrain_regimen.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from . import (CPU_SMALLEST_MODEL, CPU_TRAIN_PERCENT, CPU_TRAIN_WALL_HOURS,
               CPU_TRAIN_EFFECTIVE_HOURS, CPU_BASE_OLLAMA_TAG)

try:
    from utils.config import PROJECT_ROOT
except Exception:  # pragma: no cover
    PROJECT_ROOT = Path(__file__).resolve().parents[3]

SETTINGS_PATH = PROJECT_ROOT / "data" / "config" / "mindxtrain_regimen.json"


def _detect_hardware() -> Dict[str, Any]:
    """The single CPU + RAM combination of this host."""
    hw: Dict[str, Any] = {"cpu_cores": None, "cpu_model": None, "cpu_mhz": None,
                          "ram_gb": None}
    try:
        import psutil
        hw["cpu_cores"] = psutil.cpu_count(logical=True)
        f = psutil.cpu_freq()
        hw["cpu_mhz"] = round(f.max or f.current) if f else None
        hw["ram_gb"] = round(psutil.virtual_memory().total / (1024 ** 3), 1)
    except Exception:
        pass
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                hw["cpu_model"] = line.split(":", 1)[1].strip()
                break
    except Exception:
        pass
    return hw


def _defaults() -> Dict[str, Any]:
    return {
        "profile_name": "cpu_single_processor_ram",
        "hardware": _detect_hardware(),
        "regimen": {
            "model": CPU_SMALLEST_MODEL,
            "served_ollama_tag": CPU_BASE_OLLAMA_TAG,
            "cpu_percent": CPU_TRAIN_PERCENT,
            "wall_hours": CPU_TRAIN_WALL_HOURS,
            "effective_hours": CPU_TRAIN_EFFECTIVE_HOURS,
            "note": "smallest model; throttle to 33% of the processor over a 24h "
                    "wall window ≈ 8h effective compute; measured on the single "
                    "CPU+RAM combination in 'hardware'.",
        },
    }


def load_settings() -> Dict[str, Any]:
    """Read the settings file (source of truth); create it from defaults +
    host detection on first call. Missing keys fall back to defaults."""
    base = _defaults()
    try:
        if SETTINGS_PATH.exists():
            disk = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            # merge: disk wins, but fill any missing hardware fields from detection
            base["profile_name"] = disk.get("profile_name", base["profile_name"])
            base["regimen"].update(disk.get("regimen", {}) or {})
            hw = base["hardware"]
            hw.update({k: v for k, v in (disk.get("hardware", {}) or {}).items() if v is not None})
            base["hardware"] = hw
        else:
            SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS_PATH.write_text(json.dumps(base, indent=2), encoding="utf-8")
    except Exception:
        pass
    return base


def regimen() -> Dict[str, Any]:
    return load_settings()["regimen"]


def measure_efficiency(impact_delta, cost_cpu_seconds, cost_cycles=None,
                       peak_ram_mb=None) -> Dict[str, Any]:
    """Training impact per unit cost on this profile.

    impact_delta: the imprint recall delta (the IMPACT of training).
    cost_*: what the training consumed (the COST).
    Efficiency = impact per CPU-hour — comparable across runs on the same
    single CPU+RAM profile.
    """
    s = load_settings()
    eff = None
    try:
        if impact_delta is not None and cost_cpu_seconds:
            cpu_hours = cost_cpu_seconds / 3600.0
            eff = round(float(impact_delta) / cpu_hours, 6) if cpu_hours else None
    except Exception:
        eff = None
    return {
        "profile_name": s["profile_name"],
        "hardware": s["hardware"],
        "impact_recall_delta": impact_delta,
        "cost_cpu_seconds": cost_cpu_seconds,
        "cost_cycles": cost_cycles,
        "peak_ram_mb": peak_ram_mb,
        "efficiency_impact_per_cpu_hour": eff,
    }
