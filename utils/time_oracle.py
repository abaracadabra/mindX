# utils/time_oracle.py
"""
time.oracle — Multi-source time correlation for mindX.

Correlates four independent time sources into a consensus time object:
  - cpu.oracle       — system time at nanosecond resolution (18dp Decimal)
  - solar.oracle     — sunrise/sunset from astronomical calculation
  - lunar.oracle     — moon phase from synodic period + timeanddate.com verification
  - blocktime.oracle — blockchain block timestamps via JSON-RPC (allchain)

chronos.oracle inherits from this. Chronos speaks the time.
time.oracle measures it.

cypherpunk2048 standard: 18 decimal places. Python Decimal. No float drift.

Usage:
    from utils.time_oracle import TimeOracle
    oracle = await TimeOracle.get_instance()
    consensus = await oracle.get_time()
    lunar = await oracle.get_lunar()
"""

import os
import re
import json
import math
import time
import asyncio
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

_CACHE_DIR = PROJECT_ROOT / "data" / "governance"
_MOON_CACHE = _CACHE_DIR / "moon_cache.json"
_TIME_CACHE = _CACHE_DIR / "time_oracle_cache.json"

# Cache TTLs (seconds)
_TTL_CPU = 0
_TTL_SOLAR = 3600       # 1h
_TTL_BLOCKTIME = 120    # 2min
_TTL_LUNAR = 21600      # 6h

# Synodic month
_SYNODIC = 29.53058867
# Known new moon reference: 2000-01-06 18:14 UTC
_LUNAR_REF = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)


# ── cpu.oracle ─────────────────────────────────────────────────────

class CpuOracle:
    """System time from the CPU clock. 18dp Decimal precision (cypherpunk2048)."""

    def read(self) -> Dict[str, Any]:
        now_ns = time.time_ns()
        now = time.time()
        mono = time.monotonic()
        dt = datetime.now(timezone.utc)
        return {
            "unix": now,
            "unix_ns": now_ns,
            "unix_18dp": str(Decimal(str(now_ns)) / Decimal("1000000000")),
            "monotonic": mono,
            "utc": dt.isoformat(),
            "stale": False,
            "source": "cpu.oracle",
        }


# ── solar.oracle ───────────────────────────────────────────────────

class SolarOracle:
    """Sunrise/sunset from astronomical calculation. No external deps."""

    def __init__(self, lat: float = 0.0, lon: float = 0.0):
        self.lat = lat
        self.lon = lon
        self._cache: Optional[Dict] = None
        self._cache_ts: float = 0

    def read(self, dt: Optional[datetime] = None) -> Dict[str, Any]:
        dt = dt or datetime.now(timezone.utc)
        # Return cache if fresh
        if self._cache and (time.time() - self._cache_ts) < _TTL_SOLAR:
            return self._cache

        day_of_year = dt.timetuple().tm_yday
        # Solar declination (radians)
        declination = math.radians(23.45 * math.sin(math.radians(360 / 365 * (day_of_year - 81))))
        lat_rad = math.radians(self.lat)

        # Hour angle at sunrise/sunset
        try:
            cos_omega = -math.tan(lat_rad) * math.tan(declination)
            cos_omega = max(-1, min(1, cos_omega))  # clamp for polar regions
            omega = math.degrees(math.acos(cos_omega))
        except (ValueError, ZeroDivisionError):
            omega = 90  # fallback: equinox

        # Solar noon in UTC hours (approximate)
        solar_noon_h = 12.0 - self.lon / 15.0
        sunrise_h = solar_noon_h - omega / 15.0
        sunset_h = solar_noon_h + omega / 15.0
        daylight_h = 2 * omega / 15.0

        current_h = dt.hour + dt.minute / 60.0
        is_day = sunrise_h <= current_h <= sunset_h

        def h_to_time(h):
            h = h % 24
            return f"{int(h):02d}:{int((h % 1) * 60):02d} UTC"

        result = {
            "sunrise": h_to_time(sunrise_h),
            "sunset": h_to_time(sunset_h),
            "solar_noon": h_to_time(solar_noon_h),
            "daylight_hours": round(daylight_h, 2),
            "is_day": is_day,
            "declination_deg": round(math.degrees(declination), 2),
            "day_of_year": day_of_year,
            "latitude": self.lat,
            "longitude": self.lon,
            "stale": False,
            "source": "solar.oracle",
        }
        self._cache = result
        self._cache_ts = time.time()
        return result


# ── lunar.oracle ───────────────────────────────────────────────────

class LunarOracle:
    """Moon phase from astronomical calculation + timeanddate.com verification."""

    def __init__(self):
        self._cache: Optional[Dict] = None
        self._cache_ts: float = 0
        self._web_cache: Optional[Dict] = None
        self._web_cache_ts: float = 0
        self._load_web_cache()

    def _load_web_cache(self):
        try:
            if _MOON_CACHE.exists():
                data = json.loads(_MOON_CACHE.read_text())
                self._web_cache = data
                self._web_cache_ts = data.get("fetched_at", 0)
        except Exception:
            pass

    def _save_web_cache(self, data: Dict):
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _MOON_CACHE.write_text(json.dumps(data, indent=2, default=str))
        except Exception:
            pass

    def _calculate(self, dt: datetime) -> Dict[str, Any]:
        """Astronomical moon phase calculation."""
        diff = (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt) - _LUNAR_REF
        days_since = diff.total_seconds() / 86400
        phase_day = days_since % _SYNODIC
        pct = phase_day / _SYNODIC

        if pct < 0.0339:      name = "new moon"
        elif pct < 0.216:     name = "waxing crescent"
        elif pct < 0.284:     name = "first quarter"
        elif pct < 0.466:     name = "waxing gibbous"
        elif pct < 0.534:     name = "full moon"
        elif pct < 0.716:     name = "waning gibbous"
        elif pct < 0.784:     name = "last quarter"
        elif pct < 0.966:     name = "waning crescent"
        else:                 name = "new moon"

        return {
            "day": round(phase_day, 1),
            "cycle_pct": round(pct, 4),
            "phase": name,
            "is_full": 0.466 <= pct < 0.534,
            "is_new": pct < 0.0339 or pct >= 0.966,
            "days_to_full": round((0.5 - pct) * _SYNODIC % _SYNODIC, 1),
        }

    async def fetch_timeanddate(self) -> Optional[str]:
        """Fetch current moon phase from timeanddate.com/moon/phases/ (cached 6h)."""
        if self._web_cache and (time.time() - self._web_cache_ts) < _TTL_LUNAR:
            return self._web_cache.get("phase")

        try:
            def _fetch():
                r = requests.get(
                    "https://www.timeanddate.com/moon/phases/",
                    headers={"User-Agent": "mindX/1.0 (autonomous-agent-system)"},
                    timeout=10,
                )
                r.raise_for_status()
                return r.text
            html = await asyncio.to_thread(_fetch)
            # Parse the current phase from the page
            # timeanddate.com shows "Current Moon Phase: Waning Gibbous" or similar
            match = re.search(r'(?:Current Phase|current phase)[^<]*?:\s*</?\w[^>]*>\s*([^<]+)', html, re.IGNORECASE)
            if not match:
                match = re.search(r'<span[^>]*id="cur-phase"[^>]*>([^<]+)', html, re.IGNORECASE)
            if not match:
                # Broader fallback: look for known phase names near "current"
                match = re.search(r'((?:New|Full|Waxing|Waning)\s+(?:Moon|Crescent|Gibbous|Quarter))', html, re.IGNORECASE)

            phase_name = match.group(1).strip().lower() if match else None
            cache_data = {
                "fetched_at": time.time(),
                "phase": phase_name,
                "url": "https://www.timeanddate.com/moon/phases/",
            }
            self._web_cache = cache_data
            self._web_cache_ts = time.time()
            self._save_web_cache(cache_data)
            logger.info(f"lunar.oracle: fetched phase from timeanddate.com: {phase_name}")
            return phase_name
        except Exception as e:
            logger.debug(f"lunar.oracle: timeanddate.com fetch failed: {e}")
            return None

    async def read(self, dt: Optional[datetime] = None) -> Dict[str, Any]:
        dt = dt or datetime.now(timezone.utc)
        calc = self._calculate(dt)

        # Try timeanddate.com verification
        web_phase = await self.fetch_timeanddate()
        source = "astronomical_calculation"
        if web_phase:
            calc["timeanddate_phase"] = web_phase
            source = "astronomical_calculation + timeanddate.com"

        calc["source"] = "lunar.oracle"
        calc["verification"] = source
        calc["reference"] = "https://www.timeanddate.com/moon/phases/"
        calc["stale"] = False
        return calc


# ── blocktime.oracle ───────────────────────────────────────────────

class BlocktimeOracle:
    """Blockchain block timestamps via JSON-RPC. Allchain: Ethereum, Algorand, Polygon, ARC."""

    def __init__(self, chains: Optional[Dict[str, str]] = None):
        # chains: {chain_name: rpc_url}
        self.chains: Dict[str, str] = chains or {}
        self._cache: Dict[str, Dict] = {}
        self._cache_ts: Dict[str, float] = {}

    async def read(self) -> Dict[str, Any]:
        if not self.chains:
            return {"stale": True, "source": "blocktime.oracle", "error": "no chains configured", "chains": {}}

        results = {}
        for chain_name, rpc_url in self.chains.items():
            if not rpc_url:
                continue
            # Return cache if fresh
            if chain_name in self._cache and (time.time() - self._cache_ts.get(chain_name, 0)) < _TTL_BLOCKTIME:
                results[chain_name] = self._cache[chain_name]
                continue
            try:
                block_data = await self._fetch_chain(chain_name, rpc_url)
                if block_data:
                    results[chain_name] = block_data
                    self._cache[chain_name] = block_data
                    self._cache_ts[chain_name] = time.time()
            except Exception as e:
                results[chain_name] = {"stale": True, "error": str(e)[:80]}

        stale_count = sum(1 for v in results.values() if v.get("stale"))
        return {
            "chains": results,
            "chain_count": len(results),
            "stale": stale_count == len(results) if results else True,
            "source": "blocktime.oracle",
        }

    async def _fetch_chain(self, chain_name: str, rpc_url: str) -> Optional[Dict]:
        """Fetch latest block from a chain. Supports EVM (eth_getBlockByNumber) and Algorand (/v2/status)."""
        if not REQUESTS_AVAILABLE:
            return {"stale": True, "error": "requests library not available"}

        if "algorand" in chain_name.lower() or "algo" in chain_name.lower():
            return await self._fetch_algorand(chain_name, rpc_url)

        # EVM chain (Ethereum, Polygon, ARC, etc.)
        try:
            def _fetch():
                payload = {"jsonrpc": "2.0", "id": 1, "method": "eth_getBlockByNumber", "params": ["latest", False]}
                r = requests.post(rpc_url, json=payload, timeout=10)
                r.raise_for_status()
                return r.json()

            data = await asyncio.to_thread(_fetch)
            result_block = data.get("result", {})
            if not result_block:
                return {"stale": True, "error": "empty result"}

            block_num = int(result_block.get("number", "0x0"), 16)
            block_ts = int(result_block.get("timestamp", "0x0"), 16)
            drift_ms = int(abs(time.time() - block_ts) * 1000)

            return {
                "chain": chain_name, "block_number": block_num, "block_timestamp": block_ts,
                "block_utc": datetime.fromtimestamp(block_ts, tz=timezone.utc).isoformat(),
                "drift_ms": drift_ms, "stale": False,
            }
        except Exception as e:
            logger.debug(f"blocktime.oracle: {chain_name} RPC failed: {e}")
            return {"stale": True, "chain": chain_name, "error": str(e)[:80]}

    async def _fetch_algorand(self, chain_name: str, rpc_url: str) -> Optional[Dict]:
        """Fetch Algorand round/status."""
        try:
            def _fetch():
                r = requests.get(f"{rpc_url.rstrip('/')}/v2/status", timeout=10)
                r.raise_for_status()
                return r.json()

            data = await asyncio.to_thread(_fetch)
            last_round = data.get("last-round", 0)
            return {
                "chain": chain_name, "block_number": last_round,
                "block_timestamp": int(time.time()),  # Algorand status doesn't return block timestamp directly
                "stale": False,
            }
        except Exception as e:
            logger.debug(f"blocktime.oracle: {chain_name} failed: {e}")
            return {"stale": True, "chain": chain_name, "error": str(e)[:80]}


# ── time.oracle (master coordinator) ──────────────────────────────

class TimeOracle:
    """Multi-source time correlation. Correlates cpu, solar, lunar, and blocktime allchain.

    chronos.oracle inherits from this. Chronos speaks the time at 18dp.
    time.oracle measures it across cpu, solar, lunar, and blockchain domains.
    """

    _instance: Optional["TimeOracle"] = None
    _lock: Optional[asyncio.Lock] = None

    def __init__(self):
        lat = float(os.environ.get("MINDX_LATITUDE", "50.1"))   # Default: ~Hostinger VPS region
        lon = float(os.environ.get("MINDX_LONGITUDE", "14.4"))

        # Allchain: collect all configured blockchain RPC endpoints
        chains: Dict[str, str] = {}
        primary_rpc = (os.environ.get("MINDX_TIME_ORACLE_RPC_URL", "")
                       or os.environ.get("MINDX_ACCESS_GATE_RPC_URL", "")).strip()
        if primary_rpc:
            chains["ethereum"] = primary_rpc
        # Additional chains from environment
        polygon_rpc = os.environ.get("POLYGON_RPC_URL", "").strip()
        if polygon_rpc:
            chains["polygon"] = polygon_rpc
        algo_rpc = os.environ.get("ALGORAND_NODE_URL", "").strip()
        if algo_rpc:
            chains["algorand"] = algo_rpc
        arc_rpc = os.environ.get("ARC_RPC_URL", "").strip()
        if arc_rpc:
            chains["arc"] = arc_rpc

        self.cpu = CpuOracle()
        self.solar = SolarOracle(lat=lat, lon=lon)
        self.lunar = LunarOracle()
        self.blocktime = BlocktimeOracle(chains=chains)

    @classmethod
    async def get_instance(cls) -> "TimeOracle":
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    async def get_time(self) -> Dict[str, Any]:
        """Return correlated time from all sources."""
        now = datetime.now(timezone.utc)
        cpu_reading = self.cpu.read()
        solar_reading = self.solar.read(now)
        lunar_reading = await self.lunar.read(now)
        block_reading = await self.blocktime.read()

        # Compute max drift
        drifts = []
        if not block_reading.get("stale"):
            drifts.append(block_reading.get("drift_ms", 0))

        stale_sources = [s["source"] for s in [cpu_reading, solar_reading, lunar_reading, block_reading]
                         if s.get("stale")]

        consensus = {
            "utc": now.isoformat(),
            "unix": cpu_reading["unix"],
            "sources": {
                "cpu": cpu_reading,
                "solar": solar_reading,
                "lunar": lunar_reading,
                "blocktime": block_reading,
            },
            "drift_max_ms": max(drifts) if drifts else None,
            "stale_sources": stale_sources,
            "consensus": "correlated" if len(stale_sources) <= 1 else "degraded",
            "oracle": "time.oracle",
        }

        # Persist snapshot
        try:
            _CACHE_DIR.mkdir(parents=True, exist_ok=True)
            _TIME_CACHE.write_text(json.dumps(consensus, indent=2, default=str))
        except Exception:
            pass

        # Store to pgvectorscale
        try:
            from agents import memory_pgvector as _mpg
            await _mpg.store_memory(
                memory_id=f"time_oracle_{int(cpu_reading['unix'])}",
                agent_id="time_oracle",
                memory_type="time_consensus",
                importance=2,
                content={"lunar_phase": lunar_reading.get("phase"), "lunar_day": lunar_reading.get("day"),
                         "is_day": solar_reading.get("is_day"), "block": block_reading.get("block_number"),
                         "drift_ms": consensus["drift_max_ms"], "consensus": consensus["consensus"]},
                context={}, tags=["time", "oracle", "consensus"],
            )
        except Exception:
            pass

        return consensus

    async def get_lunar(self) -> Dict[str, Any]:
        """Convenience: just the lunar reading (for AuthorAgent)."""
        return await self.lunar.read()

    async def get_solar(self) -> Dict[str, Any]:
        """Convenience: just the solar reading."""
        now = datetime.now(timezone.utc)
        return self.solar.read(now)
