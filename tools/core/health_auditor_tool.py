"""
HealthAuditorTool for mindX

Audits mindX's vital signs on a periodic schedule:
- Is the autonomous improvement loop running?
- Is AuthorAgent writing chapters on the lunar cycle?
- Is at least one inference source available?
- Is pgvector memory reachable?

When a vital sign fails, the auditor can trigger recovery callbacks
to restart dead subsystems. This closes the self-monitoring loop.
"""
import asyncio
import time
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from agents.core.bdi_agent import BaseTool
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class HealthAuditorTool(BaseTool):
    """Monitors mindX vital signs and triggers recovery when subsystems fail."""

    def __init__(self, memory_agent=None, config: Optional[Config] = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.check_interval = 900  # 15 minutes
        if config and hasattr(config, "get"):
            self.check_interval = config.get("health_auditor.interval_seconds", 900)
        self._running = False
        self.last_audit: Dict[str, Any] = {}
        self.logger.info("HealthAuditorTool initialized.")

    async def execute(self, **kwargs) -> Dict[str, Any]:
        task = kwargs.get("task", "full_audit")
        dispatch = {
            "full_audit": self.full_audit,
            "check_improvement_loop": self.check_improvement_loop,
            "check_author_agent": self.check_author_agent,
            "check_inference": self.check_inference,
            "check_memory": self.check_memory,
        }
        fn = dispatch.get(task)
        if fn is None:
            return {"status": "ERROR", "message": f"Unknown task: {task}"}
        return await fn()

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "health_auditor",
            "description": "Audit mindX vital signs: improvement loop, author agent, inference, memory.",
            "parameters": {
                "task": {
                    "type": "string",
                    "enum": ["full_audit", "check_improvement_loop", "check_author_agent", "check_inference", "check_memory"],
                    "default": "full_audit",
                }
            },
        }

    # ── Individual checks ──

    async def check_improvement_loop(self) -> Dict[str, Any]:
        """Is MindXAgent's autonomous loop alive?"""
        try:
            from agents.core.mindXagent import MindXAgent
            instance = MindXAgent._instance
            if instance is None:
                return {"healthy": False, "reason": "MindXAgent not instantiated"}
            if not getattr(instance, "autonomous_mode", False):
                return {"healthy": False, "reason": "autonomous_mode is False"}
            task = getattr(instance, "autonomous_task", None)
            if task is None or task.done():
                return {"healthy": False, "reason": "autonomous_task is None or done"}
            return {"healthy": True}
        except Exception as e:
            return {"healthy": False, "reason": str(e)}

    async def check_author_agent(self) -> Dict[str, Any]:
        """Has AuthorAgent written a chapter in the last 26 hours?"""
        daily_dir = PROJECT_ROOT / "docs" / "publications" / "daily"
        if not daily_dir.exists():
            return {"healthy": False, "reason": "daily directory missing", "stale_hours": None}
        chapters = sorted(daily_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not chapters:
            return {"healthy": False, "reason": "no chapters found", "stale_hours": None}
        latest_mtime = chapters[0].stat().st_mtime
        age_hours = (time.time() - latest_mtime) / 3600
        if age_hours > 26:
            return {"healthy": False, "reason": f"latest chapter is {age_hours:.1f}h old", "stale_hours": round(age_hours, 1)}
        return {"healthy": True, "latest_chapter": chapters[0].name, "age_hours": round(age_hours, 1)}

    async def check_inference(self) -> Dict[str, Any]:
        """Is at least one inference source available?"""
        try:
            from llm.inference_discovery import InferenceDiscovery
            disc = await InferenceDiscovery.get_instance()
            statuses = await disc.probe_all()
            available = [name for name, s in statuses.items() if "AVAILABLE" in str(s)]
            if not available:
                return {"healthy": False, "reason": "no inference sources available", "sources_checked": len(statuses)}
            return {"healthy": True, "available_sources": available}
        except Exception as e:
            return {"healthy": False, "reason": str(e)}

    async def check_memory(self) -> Dict[str, Any]:
        """Is pgvector reachable?"""
        try:
            from agents.memory_pgvector import get_pool
            pool = await get_pool()
            if pool is None:
                return {"healthy": False, "reason": "pgvector pool is None"}
            row = await pool.fetchval("SELECT 1")
            return {"healthy": True} if row == 1 else {"healthy": False, "reason": "pgvector ping failed"}
        except Exception as e:
            return {"healthy": False, "reason": str(e)}

    # ── Full audit ──

    async def full_audit(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {"timestamp": time.time()}
        checks = {
            "improvement_loop": self.check_improvement_loop,
            "author_agent": self.check_author_agent,
            "inference": self.check_inference,
            "memory": self.check_memory,
        }
        for name, fn in checks.items():
            try:
                results[name] = await fn()
            except Exception as e:
                results[name] = {"healthy": False, "reason": f"check crashed: {e}"}
        results["overall_healthy"] = all(
            r.get("healthy", False) for r in results.values() if isinstance(r, dict) and "healthy" in r
        )
        self.last_audit = results
        return results

    # ── Periodic loop with recovery ──

    async def start_periodic_audit(
        self,
        recovery_callback: Optional[Callable[..., Coroutine]] = None,
    ):
        """Run audits on an interval; optionally trigger recovery on failure."""
        self._running = True
        logger.info(f"HealthAuditor: starting periodic audit every {self.check_interval}s")
        while self._running:
            try:
                results = await self.full_audit()
                logger.info(f"HealthAuditor: overall_healthy={results.get('overall_healthy')}")
                if not results.get("overall_healthy") and recovery_callback:
                    await recovery_callback(results)
                if self.memory_agent:
                    try:
                        await self.memory_agent.log_process(
                            "health_audit", results, {"agent_id": "health_auditor_tool"}
                        )
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"HealthAuditor: audit error: {e}", exc_info=True)
            await asyncio.sleep(self.check_interval)

    def stop(self):
        self._running = False
