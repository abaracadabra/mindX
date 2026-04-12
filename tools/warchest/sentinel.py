# tools/warchest/sentinel.py
"""
SentinelTool — real-time threat detection and behavioral anomaly analysis.

Sentinel watches request patterns, rate limit consumption, agent behavior,
and system metrics for signs of attack or internal compromise. It does not
act — it detects and reports. Action is for myoshi.agent via lockdown.py.

Threat categories:
  - PROBE: scanning, enumeration, testing boundaries
  - FLOOD: volumetric attack, rate limit saturation
  - BREACH: authentication bypass, privilege escalation
  - INSIDER: agent acting outside reputation bounds
  - RESOURCE: CPU/memory/disk exhaustion (intentional or accidental)

Containment protocol: sentinel.py is a WARCHEST asset. It observes
continuously but triggers alerts only when thresholds are crossed.
It is the eyes. suntsu.agent is the mind. myoshi.agent is the hands.

Author: Professor Codephreak
"""

import time
import asyncio
from collections import defaultdict, deque
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Dict, Any, Optional, List
from pathlib import Path

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ThreatSignal:
    """A single observation that may indicate a threat."""
    category: str          # PROBE, FLOOD, BREACH, INSIDER, RESOURCE
    severity: int          # 1-10
    source: str            # IP, agent_id, or system component
    detail: str            # Human-readable description
    timestamp: float = field(default_factory=time.time)
    evidence: Dict[str, Any] = field(default_factory=dict)


class SentinelTool:
    """Continuous threat detection for mindX.

    Watches:
      - Request patterns (rate, distribution, anomalies)
      - Agent reputation changes (Dojo score drops)
      - System resource consumption (CPU, memory, disk)
      - Authentication failures and session anomalies
      - Rate limit saturation across providers

    Reports threat signals with category, severity, and evidence.
    Does not take action — reports to the operator or to suntsu.agent.
    """

    def __init__(self):
        # Sliding windows for pattern detection
        self._request_log: deque = deque(maxlen=10000)  # (timestamp, ip, endpoint, status)
        self._auth_failures: deque = deque(maxlen=1000)  # (timestamp, ip, detail)
        self._signals: deque = deque(maxlen=500)          # ThreatSignal history
        self._ip_counters: Dict[str, int] = defaultdict(int)  # requests per IP in window
        self._endpoint_counters: Dict[str, int] = defaultdict(int)  # requests per endpoint

        # Thresholds (configurable)
        self.flood_threshold_rpm = 200     # requests per minute from single IP
        self.probe_threshold = 10          # distinct 404 endpoints from single IP in 5 min
        self.auth_failure_threshold = 5    # failures from single IP in 10 min
        self.cpu_threshold = 95.0          # percent
        self.memory_threshold = 95.0       # percent
        self.disk_threshold = 95.0         # percent

    def record_request(self, ip: str, endpoint: str, status_code: int, latency_ms: float = 0):
        """Record an inbound request for pattern analysis."""
        now = time.time()
        self._request_log.append((now, ip, endpoint, status_code))
        self._ip_counters[ip] += 1

        if status_code == 401 or status_code == 403:
            self._auth_failures.append((now, ip, endpoint))

        if status_code == 404:
            self._endpoint_counters[f"{ip}:{endpoint}"] += 1

    async def analyze(self) -> List[ThreatSignal]:
        """Run all threat detection checks. Returns new signals since last analyze."""
        signals = []
        now = time.time()

        signals.extend(self._check_flood(now))
        signals.extend(self._check_probe(now))
        signals.extend(self._check_auth_failures(now))
        signals.extend(await self._check_resources())
        signals.extend(await self._check_insider())
        signals.extend(await self._check_rate_limit_saturation())

        for s in signals:
            self._signals.append(s)

        if signals:
            logger.warning(f"Sentinel: {len(signals)} threat signals detected")
            for s in signals:
                logger.warning(f"  [{s.category}] severity={s.severity} source={s.source}: {s.detail}")

        return signals

    def _check_flood(self, now: float) -> List[ThreatSignal]:
        """Detect volumetric flood from single IP."""
        signals = []
        window = 60  # 1 minute
        ip_counts: Dict[str, int] = defaultdict(int)

        for ts, ip, endpoint, status in self._request_log:
            if now - ts <= window:
                ip_counts[ip] += 1

        for ip, count in ip_counts.items():
            if count >= self.flood_threshold_rpm:
                signals.append(ThreatSignal(
                    category="FLOOD",
                    severity=min(10, count // self.flood_threshold_rpm + 5),
                    source=ip,
                    detail=f"{count} requests in {window}s (threshold: {self.flood_threshold_rpm})",
                    evidence={"rpm": count, "threshold": self.flood_threshold_rpm},
                ))
        return signals

    def _check_probe(self, now: float) -> List[ThreatSignal]:
        """Detect scanning/enumeration (many 404s from single IP)."""
        signals = []
        window = 300  # 5 minutes
        ip_404s: Dict[str, set] = defaultdict(set)

        for ts, ip, endpoint, status in self._request_log:
            if now - ts <= window and status == 404:
                ip_404s[ip].add(endpoint)

        for ip, endpoints in ip_404s.items():
            if len(endpoints) >= self.probe_threshold:
                signals.append(ThreatSignal(
                    category="PROBE",
                    severity=min(8, len(endpoints) // 5 + 3),
                    source=ip,
                    detail=f"{len(endpoints)} distinct 404 endpoints in {window}s",
                    evidence={"endpoints": list(endpoints)[:20], "count": len(endpoints)},
                ))
        return signals

    def _check_auth_failures(self, now: float) -> List[ThreatSignal]:
        """Detect brute force authentication attempts."""
        signals = []
        window = 600  # 10 minutes
        ip_failures: Dict[str, int] = defaultdict(int)

        for ts, ip, detail in self._auth_failures:
            if now - ts <= window:
                ip_failures[ip] += 1

        for ip, count in ip_failures.items():
            if count >= self.auth_failure_threshold:
                signals.append(ThreatSignal(
                    category="BREACH",
                    severity=min(9, count + 3),
                    source=ip,
                    detail=f"{count} auth failures in {window}s — possible brute force",
                    evidence={"failure_count": count, "window_seconds": window},
                ))
        return signals

    async def _check_resources(self) -> List[ThreatSignal]:
        """Detect resource exhaustion (CPU, memory, disk)."""
        signals = []
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0)
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            if cpu >= self.cpu_threshold:
                signals.append(ThreatSignal(
                    category="RESOURCE", severity=7, source="system",
                    detail=f"CPU at {cpu:.1f}% (threshold: {self.cpu_threshold}%)",
                    evidence={"cpu_percent": cpu},
                ))
            if mem.percent >= self.memory_threshold:
                signals.append(ThreatSignal(
                    category="RESOURCE", severity=8, source="system",
                    detail=f"Memory at {mem.percent:.1f}% (threshold: {self.memory_threshold}%)",
                    evidence={"memory_percent": mem.percent, "available_mb": mem.available // (1024*1024)},
                ))
            if disk.percent >= self.disk_threshold:
                signals.append(ThreatSignal(
                    category="RESOURCE", severity=6, source="system",
                    detail=f"Disk at {disk.percent:.1f}% (threshold: {self.disk_threshold}%)",
                    evidence={"disk_percent": disk.percent, "free_gb": disk.free // (1024**3)},
                ))
        except ImportError:
            pass  # psutil not available — skip resource checks
        except Exception as e:
            logger.debug(f"Sentinel: resource check failed: {e}")
        return signals

    async def _check_insider(self) -> List[ThreatSignal]:
        """Detect agents acting outside reputation bounds (Dojo score drop)."""
        signals = []
        try:
            from daio.governance.dojo import get_all_standings
            standings = get_all_standings()
            for agent_id, data in standings.items():
                score = data.get("reputation_score", 0)
                # Flag agents that dropped below verified threshold
                if score < 500 and data.get("verification_tier", 0) >= 2:
                    signals.append(ThreatSignal(
                        category="INSIDER", severity=6, source=agent_id,
                        detail=f"Agent reputation {score} below tier-2 threshold (500)",
                        evidence={"reputation_score": score, "tier": data.get("verification_tier")},
                    ))
        except Exception:
            pass
        return signals

    async def _check_rate_limit_saturation(self) -> List[ThreatSignal]:
        """Detect providers approaching rate limit exhaustion."""
        signals = []
        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            for name, source in disc.sources.items():
                rate_info = disc.rate_limits.get(name, {})
                daily = rate_info.get("daily")
                if daily and hasattr(disc, '_cloud_call_count'):
                    utilization = disc._cloud_call_count / daily
                    if utilization >= 0.9:
                        signals.append(ThreatSignal(
                            category="RESOURCE", severity=5, source=name,
                            detail=f"Rate limit {utilization:.0%} exhausted ({disc._cloud_call_count}/{daily})",
                            evidence={"used": disc._cloud_call_count, "limit": daily, "utilization": utilization},
                        ))
        except Exception:
            pass
        return signals

    def get_signals(self, category: Optional[str] = None, min_severity: int = 0) -> List[Dict[str, Any]]:
        """Get recent threat signals, optionally filtered."""
        results = []
        for s in self._signals:
            if category and s.category != category:
                continue
            if s.severity < min_severity:
                continue
            results.append({
                "category": s.category,
                "severity": s.severity,
                "source": s.source,
                "detail": s.detail,
                "timestamp": s.timestamp,
                "evidence": s.evidence,
            })
        return results

    def threat_level(self) -> Dict[str, Any]:
        """Current overall threat assessment."""
        now = time.time()
        recent = [s for s in self._signals if now - s.timestamp < 300]  # Last 5 min
        if not recent:
            return {"level": "GREEN", "signals": 0, "max_severity": 0}

        max_sev = max(s.severity for s in recent)
        level = "GREEN"
        if max_sev >= 8:
            level = "RED"
        elif max_sev >= 5:
            level = "AMBER"
        elif max_sev >= 3:
            level = "YELLOW"

        return {
            "level": level,
            "signals": len(recent),
            "max_severity": max_sev,
            "categories": list(set(s.category for s in recent)),
        }
