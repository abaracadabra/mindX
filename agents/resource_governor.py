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
        # Dynamic CPU gate: a system-CPU ceiling the autonomous loops + background
        # inference back off below, so the box stays responsive for web-serving.
        # The loop "shares the processor" — full speed when idle, yields under load.
        self.autonomous_cpu_ceiling: float = self._read_ceiling()
        self.max_cpu_temp: float = self._read_max_temp()      # °C; ceiling backs off above it
        self.inference_cores: int = self._read_inference_cores()  # cores reserved for inference/training
        self._last_cpu: float = 0.0
        self._last_cpu_ts: float = 0.0
        self._throttling: Optional[tuple] = None  # (label, started_ts) while backing off
        # Background-only inference concurrency limiter (lazily created so it binds
        # to the running event loop). Size 1 on the 2-core box: serializes the
        # background demand that pegs ollama. Interactive/web calls bypass this.
        self._inference_sem: Optional[asyncio.Semaphore] = None
        self._inference_concurrency: int = self._read_inference_concurrency()

    @staticmethod
    def _read_ceiling() -> float:
        """The dynamic autonomous-loop CPU ceiling (percent). Default 99 — run the
        box hot to maximize inference, as long as temperature is acceptable (see
        effective_ceiling / _cpu_temp). Operator override: MINDX_MAX_AUTONOMOUS_CPU."""
        v = os.getenv("MINDX_MAX_AUTONOMOUS_CPU")
        if v is None:
            try:
                from utils.config import Config
                v = Config().get("resource.max_autonomous_loop_cpu", 99.0)
            except Exception:
                v = 99.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 99.0

    @staticmethod
    def _read_max_temp() -> float:
        """Max acceptable CPU temperature (°C). Above it the ceiling backs off.
        Operator override: MINDX_MAX_CPU_TEMP (default 85)."""
        v = os.getenv("MINDX_MAX_CPU_TEMP")
        if v is None:
            try:
                from utils.config import Config
                v = Config().get("resource.max_cpu_temp", 85.0)
            except Exception:
                v = 85.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 85.0

    @staticmethod
    def _read_inference_cores() -> int:
        """Cores reserved for inference processing at all times. Default 2.
        Operator override: MINDX_INFERENCE_CORES."""
        v = os.getenv("MINDX_INFERENCE_CORES")
        if v is None:
            try:
                from utils.config import Config
                v = Config().get("resource.inference_cores", 2)
            except Exception:
                v = 2
        try:
            return max(1, int(v))
        except (TypeError, ValueError):
            return 2

    @staticmethod
    def _cpu_temp() -> Optional[float]:
        """Hottest current CPU core temperature (°C), or None if no sensor (VPS/venv)."""
        try:
            temps = psutil.sensors_temperatures()
        except Exception:
            return None
        if not temps:
            return None
        best = None
        for entries in temps.values():
            for e in entries:
                if e.current and (best is None or e.current > best):
                    best = e.current
        return best

    def effective_ceiling(self) -> float:
        """The ceiling actually enforced now: the configured ceiling (99) while
        temperature is acceptable; backed off toward 85% when the CPU runs too hot.
        Fail-open: no sensor → run at the full ceiling."""
        base = self.autonomous_cpu_ceiling
        t = self._cpu_temp()
        if t is not None and t > self.max_cpu_temp:
            over = t - self.max_cpu_temp
            return max(75.0, base - min(base - 75.0, over * 2.0))   # 2 %pts per °C over, floor 75
        return base

    @staticmethod
    def _read_inference_concurrency() -> int:
        v = os.getenv("MINDX_INFERENCE_CONCURRENCY")
        if v is None:
            try:
                from utils.config import Config
                v = Config().get("resource.inference_concurrency", 1)
            except Exception:
                v = 1
        try:
            return max(1, int(v))
        except (TypeError, ValueError):
            return 1

    def inference_slot(self) -> asyncio.Semaphore:
        """Background-only inference concurrency limiter. Acquire ONLY for
        background/non-interactive dispatch (periodic embedding, autonomous loop);
        interactive web-triggered inference must NOT acquire it (avoids starvation).
        Lazily created so it binds to the active event loop."""
        if self._inference_sem is None:
            self._inference_sem = asyncio.Semaphore(self._inference_concurrency)
        return self._inference_sem

    def _current_cpu(self) -> float:
        """Cheap, cached CPU reading. Reuses the 30s sample taken by
        check_and_adjust(); only does a single non-blocking cpu_percent() if the
        cache is stale. NEVER calls cpu_percent(interval=1) (would block). Fail-open:
        any sensor error returns 0.0 so callers proceed."""
        try:
            if (time.time() - self._last_cpu_ts) < 30 and self._last_cpu_ts > 0:
                return self._last_cpu
            cpu = psutil.cpu_percent(interval=None)
            self._last_cpu = cpu
            self._last_cpu_ts = time.time()
            return cpu
        except Exception:
            return 0.0

    def cpu_headroom(self) -> float:
        """Percentage points of CPU below the autonomous ceiling (>=0)."""
        try:
            return max(0.0, self.effective_ceiling() - self._current_cpu())
        except Exception:
            return self.autonomous_cpu_ceiling

    def should_throttle(self, ceiling: Optional[float] = None) -> bool:
        """True if current CPU is over the ceiling. Fail-open → False."""
        try:
            return self._current_cpu() > (ceiling or self.effective_ceiling())
        except Exception:
            return False

    async def throttle_for_cpu(
        self,
        ceiling: Optional[float] = None,
        *,
        label: str = "autonomous",
        max_wait: float = 180.0,
    ) -> bool:
        """Back off (asyncio.sleep) in a bounded loop while system CPU is over the
        ceiling, letting the web service have the processor. Returns True once CPU
        is under the ceiling (caller should PROCEED) or False after max_wait (caller
        should SKIP this cycle rather than pile on). Fail-open: any sensor error
        returns True (work proceeds). This is how the autonomous loop yields CPU."""
        ceiling = ceiling or self.effective_ceiling()
        try:
            waited = 0.0
            backoff = 5.0
            started = time.time()
            while waited < max_wait:
                cpu = self._current_cpu()
                if cpu <= ceiling:
                    self._throttling = None
                    return True
                self._throttling = (label, started)
                logger.info(
                    f"ResourceGovernor.throttle_for_cpu[{label}]: cpu={cpu:.0f}% "
                    f"> {ceiling:.0f}% ceiling — backing off {backoff:.0f}s"
                )
                await asyncio.sleep(backoff)
                waited += backoff
                backoff = min(backoff * 1.5, 30.0)
            proceeded = self._current_cpu() <= ceiling
            self._throttling = None
            return proceeded
        except Exception:
            self._throttling = None
            return True

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
        # Cache for the dynamic CPU gate's hot path (_current_cpu) — avoids extra
        # blocking psutil calls when the loops/inference consult the ceiling.
        self._last_cpu = cpu
        self._last_cpu_ts = now

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
            "cpu": {
                "current": round(self._current_cpu(), 1),
                "ceiling": self.autonomous_cpu_ceiling,
                "headroom": round(self.cpu_headroom(), 1),
                "throttling": self._throttling is not None,
                "throttle_label": (self._throttling[0] if self._throttling else None),
            },
        }
