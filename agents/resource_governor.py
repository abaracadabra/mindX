# agents/resource_governor.py
"""
Resource Governor — mindX controls its own power consumption.

Modes:
  greedy    — use up to 85% RAM, 90% CPU. Maximum inference speed. Other services get minimum.
  balanced  — use up to 65% RAM, 70% CPU. Normal operations. Fair to pmVPN and PostgreSQL.
  generous  — use up to 45% RAM, 50% CPU. Yield to other services. Reduce model loading.
  minimal   — use up to 30% RAM, 30% CPU. Survival mode. Unload models, skip heartbeat.

The governor:
  1. Monitors system resources every 30 seconds
  2. Checks other VPS services (pmVPN, PostgreSQL, Apache) activity
  3. Adjusts Ollama keep_alive and model loading based on mode
  4. Reports efficiency metrics to diagnostics
  5. Can be set via API or auto-adjusts based on system pressure

mindX recognizes it shares the VPS with pmVPN, PostgreSQL, Apache, and Ollama.
It plays mostly nice — greedy when idle, generous when neighbors are busy.
"""

import os
import time
import asyncio
import psutil
from typing import Optional, Dict, Any
from dataclasses import dataclass

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ResourceProfile:
    name: str
    max_ram_pct: float
    max_cpu_pct: float
    ollama_keep_alive: str  # How long to keep models loaded
    heartbeat_interval: int  # Seconds between heartbeat queries
    description: str


PROFILES = {
    "greedy": ResourceProfile(
        "greedy", 85.0, 90.0, "30m",  60,
        "Maximum inference. Use most resources. Other services get minimum."
    ),
    "balanced": ResourceProfile(
        "balanced", 65.0, 70.0, "10m", 60,
        "Normal operations. Fair share with pmVPN and PostgreSQL."
    ),
    "generous": ResourceProfile(
        "generous", 45.0, 50.0, "3m", 120,
        "Yield to other services. Reduce model loading. Slower inference."
    ),
    "minimal": ResourceProfile(
        "minimal", 30.0, 30.0, "1m", 300,
        "Survival mode. Unload models quickly. Skip non-essential tasks."
    ),
}

# VPS neighbor services to monitor
VPS_SERVICES = ["pmvpn", "apache2", "postgresql"]


class ResourceGovernor:
    """Controls mindX resource appetite based on VPS load and policy."""

    _instance: Optional["ResourceGovernor"] = None

    def __init__(self):
        self.mode = "balanced"
        self.profile = PROFILES["balanced"]
        self.auto_adjust = True  # Auto-switch modes based on pressure
        self._last_check = 0.0
        self._neighbor_load: Dict[str, float] = {}

    @classmethod
    async def get_instance(cls) -> "ResourceGovernor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_mode(self, mode: str) -> Dict[str, Any]:
        """Set resource mode manually."""
        if mode not in PROFILES:
            return {"error": f"Unknown mode: {mode}. Use: {list(PROFILES.keys())}"}
        self.mode = mode
        self.profile = PROFILES[mode]
        logger.info(f"ResourceGovernor: mode set to {mode} — {self.profile.description}")
        return {"mode": mode, "profile": self._profile_dict()}

    def _profile_dict(self) -> Dict[str, Any]:
        return {
            "name": self.profile.name,
            "max_ram_pct": self.profile.max_ram_pct,
            "max_cpu_pct": self.profile.max_cpu_pct,
            "ollama_keep_alive": self.profile.ollama_keep_alive,
            "heartbeat_interval": self.profile.heartbeat_interval,
            "description": self.profile.description,
        }

    async def check_and_adjust(self) -> Dict[str, Any]:
        """Check system pressure and auto-adjust mode if enabled."""
        now = time.time()
        if now - self._last_check < 30:
            return self.get_status()
        self._last_check = now

        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=None)

        # Check neighbor service load
        neighbor_rss = 0
        for proc in psutil.process_iter(["pid", "name", "memory_info", "cmdline"]):
            try:
                name = proc.info["name"] or ""
                cmdline = " ".join(proc.info.get("cmdline") or [])
                if any(svc in name.lower() or svc in cmdline.lower() for svc in VPS_SERVICES):
                    rss = proc.info["memory_info"].rss if proc.info["memory_info"] else 0
                    neighbor_rss += rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        neighbor_pct = (neighbor_rss / mem.total) * 100 if mem.total > 0 else 0
        mindx_pct = mem.percent
        available_pct = 100 - mindx_pct

        self._neighbor_load = {
            "neighbor_ram_pct": round(neighbor_pct, 1),
            "system_ram_pct": round(mem.percent, 1),
            "available_ram_pct": round(available_pct, 1),
            "cpu_pct": round(cpu, 1),
        }

        # Auto-adjust if enabled
        if self.auto_adjust:
            old_mode = self.mode
            if neighbor_pct > 30 or available_pct < 20:
                self.mode = "generous"
            elif neighbor_pct > 15 or available_pct < 35:
                self.mode = "balanced"
            elif available_pct > 60 and cpu < 30:
                self.mode = "greedy"
            else:
                self.mode = "balanced"

            self.profile = PROFILES[self.mode]
            if old_mode != self.mode:
                logger.info(f"ResourceGovernor: auto-adjusted {old_mode} → {self.mode} (neighbors={neighbor_pct:.0f}%, available={available_pct:.0f}%)")

        return self.get_status()

    def should_skip_heartbeat(self) -> bool:
        """Check if heartbeat should be skipped based on resource pressure."""
        try:
            mem = psutil.virtual_memory()
            if mem.percent > self.profile.max_ram_pct:
                return True
            cpu = psutil.cpu_percent(interval=None)
            if cpu > self.profile.max_cpu_pct:
                return True
        except Exception:
            pass
        return False

    def should_unload_models(self) -> bool:
        """Check if Ollama models should be unloaded to free RAM."""
        try:
            mem = psutil.virtual_memory()
            return mem.percent > (self.profile.max_ram_pct + 10)
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "auto_adjust": self.auto_adjust,
            "profile": self._profile_dict(),
            "system": self._neighbor_load,
        }
