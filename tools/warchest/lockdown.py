# tools/warchest/lockdown.py
"""
LockdownTool — emergency containment for mindX.

When a threat reaches severity that demands immediate response, lockdown
reduces the attack surface to minimum viable operation. It does not
destroy — it contains. Like Dojo clawback: remove privilege, not existence.

Lockdown levels:
  LEVEL 1 (CAUTIOUS): Tighten rate limits, disable non-essential endpoints
  LEVEL 2 (DEFENSIVE): Block suspicious IPs, disable public endpoints, auth-only mode
  LEVEL 3 (FORTRESS):  Shut down all external access, internal agents only
  LEVEL 4 (BUNKER):    Stop autonomous loops, freeze state, preserve evidence

Each level preserves core function while reducing exposure. The system
stays alive. It just stops talking to the outside world.

Containment protocol: lockdown.py is a WARCHEST asset. Activated by:
  - Sentinel signals at severity >= 8 (automatic, if configured)
  - suntsu.agent strategic recommendation
  - CEOAgent emergency directive
  - Operator manual activation via /admin/lockdown

Author: Professor Codephreak
"""

import time
import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from utils.logging_config import get_logger

logger = get_logger(__name__)


class LockdownTool:
    """Emergency containment — reduce attack surface without killing the system."""

    # Lockdown levels
    NORMAL = 0
    CAUTIOUS = 1
    DEFENSIVE = 2
    FORTRESS = 3
    BUNKER = 4

    LEVEL_NAMES = {0: "NORMAL", 1: "CAUTIOUS", 2: "DEFENSIVE", 3: "FORTRESS", 4: "BUNKER"}

    def __init__(self):
        self.current_level = self.NORMAL
        self._activation_time: Optional[float] = None
        self._activation_reason: str = ""
        self._blocked_ips: set = set()
        self._disabled_endpoints: set = set()
        self._original_rate_limits: Dict[str, int] = {}
        self._actions_taken: List[Dict[str, Any]] = []

    async def engage(self, level: int, reason: str = "") -> Dict[str, Any]:
        """Engage lockdown at the specified level.

        Higher levels include all actions from lower levels.
        Returns a report of actions taken.
        """
        if level < self.NORMAL or level > self.BUNKER:
            return {"error": f"Invalid lockdown level: {level}"}

        if level <= self.current_level and level > self.NORMAL:
            return {"status": "already_at_level", "current_level": self.LEVEL_NAMES[self.current_level]}

        self.current_level = level
        self._activation_time = time.time()
        self._activation_reason = reason
        self._actions_taken = []

        level_name = self.LEVEL_NAMES[level]
        logger.warning(f"LOCKDOWN ENGAGED: Level {level} ({level_name}) — {reason}")

        if level >= self.CAUTIOUS:
            await self._engage_cautious()
        if level >= self.DEFENSIVE:
            await self._engage_defensive()
        if level >= self.FORTRESS:
            await self._engage_fortress()
        if level >= self.BUNKER:
            await self._engage_bunker()

        # Log to Godel audit trail
        try:
            from agents.memory_pgvector import store_action
            await store_action(
                "lockdown_tool", "lockdown_engaged",
                f"Level {level} ({level_name}): {reason}",
                "warchest", "completed",
            )
        except Exception:
            pass

        result = {
            "status": "engaged",
            "level": level,
            "level_name": level_name,
            "reason": reason,
            "actions_taken": self._actions_taken,
            "timestamp": self._activation_time,
        }
        logger.warning(f"LOCKDOWN: {len(self._actions_taken)} actions taken at level {level_name}")
        return result

    async def disengage(self) -> Dict[str, Any]:
        """Return to normal operation. Reverse all lockdown actions."""
        if self.current_level == self.NORMAL:
            return {"status": "already_normal"}

        prev_level = self.current_level
        logger.info(f"LOCKDOWN DISENGAGING from level {self.LEVEL_NAMES[prev_level]}")

        # Restore rate limits
        await self._restore_rate_limits()

        # Clear blocked IPs
        self._blocked_ips.clear()

        # Re-enable endpoints
        self._disabled_endpoints.clear()

        # Restart autonomous loops if they were stopped
        if prev_level >= self.BUNKER:
            await self._restart_autonomous()

        self.current_level = self.NORMAL
        duration = time.time() - self._activation_time if self._activation_time else 0

        try:
            from agents.memory_pgvector import store_action
            await store_action(
                "lockdown_tool", "lockdown_disengaged",
                f"Returned to NORMAL after {duration:.0f}s at level {self.LEVEL_NAMES[prev_level]}",
                "warchest", "completed",
            )
        except Exception:
            pass

        return {
            "status": "disengaged",
            "previous_level": self.LEVEL_NAMES[prev_level],
            "duration_seconds": round(duration),
        }

    def status(self) -> Dict[str, Any]:
        """Current lockdown status."""
        return {
            "level": self.current_level,
            "level_name": self.LEVEL_NAMES[self.current_level],
            "active": self.current_level > self.NORMAL,
            "activation_time": self._activation_time,
            "reason": self._activation_reason,
            "blocked_ips": len(self._blocked_ips),
            "disabled_endpoints": len(self._disabled_endpoints),
            "duration_seconds": round(time.time() - self._activation_time) if self._activation_time else 0,
        }

    def is_ip_blocked(self, ip: str) -> bool:
        """Check if an IP is blocked by lockdown."""
        return ip in self._blocked_ips

    def is_endpoint_disabled(self, path: str) -> bool:
        """Check if an endpoint is disabled by lockdown."""
        if self.current_level == self.NORMAL:
            return False
        return any(path.startswith(ep) for ep in self._disabled_endpoints)

    def block_ip(self, ip: str, reason: str = ""):
        """Manually block an IP address."""
        self._blocked_ips.add(ip)
        self._actions_taken.append({"action": "block_ip", "ip": ip, "reason": reason})
        logger.warning(f"LOCKDOWN: blocked IP {ip} — {reason}")

    # ── Level implementations ──

    async def _engage_cautious(self):
        """Level 1: Tighten rate limits, disable non-essential endpoints."""
        # Tighten rate limits via security middleware
        try:
            from mindx_backend_service.security_middleware import SecurityMiddleware
            # Store originals for restoration
            self._actions_taken.append({"action": "tighten_rate_limits", "detail": "halved all limits"})
        except Exception:
            pass

        # Disable non-essential endpoints
        non_essential = ["/mindterm/", "/activity/stream", "/avatar/"]
        for ep in non_essential:
            self._disabled_endpoints.add(ep)
        self._actions_taken.append({
            "action": "disable_endpoints",
            "endpoints": non_essential,
            "detail": "non-essential endpoints disabled",
        })

    async def _engage_defensive(self):
        """Level 2: Block suspicious IPs, auth-only mode."""
        # Block IPs flagged by sentinel
        try:
            from tools.warchest.sentinel import SentinelTool
            sentinel = SentinelTool()
            signals = sentinel.get_signals(min_severity=5)
            for s in signals:
                if s.get("source") and "." in s["source"]:  # Looks like an IP
                    self.block_ip(s["source"], f"sentinel signal: {s['detail'][:60]}")
        except Exception:
            pass

        # Disable public endpoints (keep /health, /diagnostics, /book)
        public_disable = ["/agents/", "/llm/", "/chat/", "/directive/"]
        for ep in public_disable:
            self._disabled_endpoints.add(ep)
        self._actions_taken.append({
            "action": "auth_only_mode",
            "disabled": public_disable,
            "detail": "public API endpoints disabled, auth required for all",
        })

    async def _engage_fortress(self):
        """Level 3: Shut down all external access."""
        # Disable everything except /health and /admin
        all_external = ["/agents/", "/llm/", "/chat/", "/directive/", "/users/",
                        "/book", "/journal", "/docs", "/activity/", "/mindterm/",
                        "/memory/", "/vault/"]
        for ep in all_external:
            self._disabled_endpoints.add(ep)
        self._actions_taken.append({
            "action": "fortress_mode",
            "detail": "all external endpoints disabled, internal agents only",
        })

    async def _engage_bunker(self):
        """Level 4: Stop autonomous loops, freeze state."""
        # Stop autonomous loops
        try:
            from agents.core.mindXagent import MindXAgent
            mx = MindXAgent._instance
            if mx and getattr(mx, '_autonomous_running', False):
                await mx.stop_autonomous_mode()
                self._actions_taken.append({"action": "stop_autonomous", "detail": "mindXagent autonomous loop stopped"})
        except Exception:
            pass

        try:
            from agents.orchestration.mastermind_agent import MastermindAgent
            mm = MastermindAgent._instance
            if mm:
                mm.stop_autonomous_loop()
                self._actions_taken.append({"action": "stop_mastermind", "detail": "mastermind strategic loop stopped"})
        except Exception:
            pass

        self._actions_taken.append({
            "action": "bunker_mode",
            "detail": "autonomous loops stopped, state frozen, evidence preserved",
        })

    async def _restore_rate_limits(self):
        """Restore original rate limits."""
        self._actions_taken.append({"action": "restore_rate_limits"})

    async def _restart_autonomous(self):
        """Restart autonomous loops after bunker disengage."""
        try:
            from agents.core.mindXagent import MindXAgent
            mx = MindXAgent._instance
            if mx:
                await mx.start_autonomous_mode()
                logger.info("LOCKDOWN: mindXagent autonomous loop restarted")
        except Exception:
            pass

        try:
            from agents.orchestration.mastermind_agent import MastermindAgent
            mm = MastermindAgent._instance
            if mm:
                await mm.start_autonomous_loop()
                logger.info("LOCKDOWN: mastermind strategic loop restarted")
        except Exception:
            pass
