# tools/core/chronos_cron_tool.py
"""
ChronosCronTool — Scheduled task execution for mindX.

Chronos defines the rhythm. This tool executes it.
Manages all periodic tasks with named schedules, intervals,
last-run tracking, and execution history.

Does not duplicate asyncio.sleep loops — wraps them with:
  - Named task registry (no anonymous coroutines)
  - Execution history with success/failure tracking
  - Dynamic interval adjustment
  - Pause/resume without killing tasks
  - Status reporting for diagnostics

Chronos keeps the clock. Other agents provide the hands.

Author: Professor Codephreak
"""

import asyncio
import time
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine, Dict, List, Optional

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class CronEntry:
    """A single scheduled task."""
    name: str
    interval_seconds: int
    executor: Callable[[], Coroutine]  # async callable
    description: str = ""
    enabled: bool = True
    last_run: float = 0.0
    last_status: str = "pending"
    run_count: int = 0
    fail_count: int = 0
    task: Optional[asyncio.Task] = field(default=None, repr=False)


class ChronosCronTool:
    """Named cron scheduler for mindX periodic tasks.

    Usage:
        cron = ChronosCronTool()
        cron.register("catalog_refresh", 86400, author.refresh_cloud_model_catalog,
                       description="Refresh Ollama cloud model catalog")
        await cron.start_all()
        ...
        cron.status()  # see all tasks
        cron.pause("catalog_refresh")
        cron.resume("catalog_refresh")
        await cron.stop_all()
    """

    def __init__(self):
        self.entries: Dict[str, CronEntry] = {}
        self._state_path = PROJECT_ROOT / "data" / "governance" / "chronos_cron.json"

    def register(self, name: str, interval_seconds: int,
                 executor: Callable, description: str = "") -> CronEntry:
        """Register a named periodic task."""
        entry = CronEntry(
            name=name,
            interval_seconds=interval_seconds,
            executor=executor,
            description=description,
        )
        self.entries[name] = entry
        logger.info(f"Chronos: registered '{name}' ({interval_seconds}s interval)")
        return entry

    async def start(self, name: str):
        """Start a single named task."""
        entry = self.entries.get(name)
        if not entry:
            logger.warning(f"Chronos: task '{name}' not registered")
            return
        if entry.task and not entry.task.done():
            logger.debug(f"Chronos: task '{name}' already running")
            return
        entry.task = asyncio.create_task(self._run_loop(entry), name=f"chronos_{name}")
        logger.info(f"Chronos: started '{name}'")

    async def start_all(self):
        """Start all registered tasks."""
        for name in self.entries:
            await self.start(name)

    def pause(self, name: str):
        """Pause a task (stops execution but preserves registration)."""
        entry = self.entries.get(name)
        if entry:
            entry.enabled = False
            logger.info(f"Chronos: paused '{name}'")

    def resume(self, name: str):
        """Resume a paused task."""
        entry = self.entries.get(name)
        if entry:
            entry.enabled = True
            logger.info(f"Chronos: resumed '{name}'")

    async def stop(self, name: str):
        """Stop a single task."""
        entry = self.entries.get(name)
        if entry and entry.task and not entry.task.done():
            entry.task.cancel()
            entry.task = None
            logger.info(f"Chronos: stopped '{name}'")

    async def stop_all(self):
        """Stop all running tasks."""
        for name in list(self.entries.keys()):
            await self.stop(name)

    def set_interval(self, name: str, interval_seconds: int):
        """Dynamically adjust a task's interval."""
        entry = self.entries.get(name)
        if entry:
            old = entry.interval_seconds
            entry.interval_seconds = interval_seconds
            logger.info(f"Chronos: '{name}' interval {old}s → {interval_seconds}s")

    def status(self) -> Dict[str, Any]:
        """Full status report — all tasks with execution history."""
        now = time.time()
        tasks = {}
        for name, entry in self.entries.items():
            age = now - entry.last_run if entry.last_run > 0 else None
            tasks[name] = {
                "interval_s": entry.interval_seconds,
                "enabled": entry.enabled,
                "running": entry.task is not None and not entry.task.done() if entry.task else False,
                "last_run_ago_s": round(age) if age else None,
                "last_status": entry.last_status,
                "run_count": entry.run_count,
                "fail_count": entry.fail_count,
                "description": entry.description,
            }
        return {
            "total_tasks": len(self.entries),
            "running": sum(1 for e in self.entries.values() if e.task and not e.task.done()),
            "paused": sum(1 for e in self.entries.values() if not e.enabled),
            "tasks": tasks,
        }

    async def _run_loop(self, entry: CronEntry):
        """Internal loop for a single cron entry."""
        while True:
            try:
                if entry.enabled:
                    t0 = time.time()
                    try:
                        await entry.executor()
                        entry.last_status = "success"
                        entry.run_count += 1
                        elapsed = time.time() - t0
                        logger.debug(f"Chronos: '{entry.name}' completed in {elapsed:.1f}s")
                    except Exception as e:
                        entry.last_status = f"error: {str(e)[:80]}"
                        entry.fail_count += 1
                        logger.warning(f"Chronos: '{entry.name}' failed: {e}")
                    entry.last_run = time.time()
                await asyncio.sleep(entry.interval_seconds)
            except asyncio.CancelledError:
                logger.info(f"Chronos: '{entry.name}' cancelled")
                return

    def save_state(self):
        """Persist cron state for recovery across restarts."""
        try:
            self._state_path.parent.mkdir(parents=True, exist_ok=True)
            state = {}
            for name, entry in self.entries.items():
                state[name] = {
                    "interval_seconds": entry.interval_seconds,
                    "enabled": entry.enabled,
                    "last_run": entry.last_run,
                    "last_status": entry.last_status,
                    "run_count": entry.run_count,
                    "fail_count": entry.fail_count,
                    "description": entry.description,
                }
            self._state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Chronos: state save failed: {e}")

    def load_state(self):
        """Restore cron state from disk."""
        if not self._state_path.exists():
            return
        try:
            state = json.loads(self._state_path.read_text(encoding="utf-8"))
            for name, data in state.items():
                if name in self.entries:
                    entry = self.entries[name]
                    entry.last_run = data.get("last_run", 0)
                    entry.last_status = data.get("last_status", "pending")
                    entry.run_count = data.get("run_count", 0)
                    entry.fail_count = data.get("fail_count", 0)
        except Exception as e:
            logger.debug(f"Chronos: state load failed: {e}")
