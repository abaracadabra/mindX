"""
Selection Engine — Darwinian fitness-driven agent lifecycle events.

Reads fitness from `InsightAggregator` and, on each tournament tick, identifies:
  - **Retire candidates** — agents under a floor fitness that are in the
    bottom quartile and have enough history that a low score is meaningful.
  - **Mutation parents**  — top-quartile agents from which a bounded-delta
    child could be spawned.

Modes (env `MINDX_SELECTION_MODE`, prod default `shadow`):

    shadow      Writes candidate_retire / candidate_spawn events only.
                Never modifies daio/agents/agent_map.json.  Safe default.

    advisory    Shadow + emits boardroom activity events so the 7-soldier
                board can vote on proposals. No agent_map.json write yet.

    autonomous  Applies decisions on weighted-majority boardroom approval.
                Gated. NOT SAFE for week one.

Tournament trigger: earlier of (N=25 new campaigns since last run) or T=24h.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

# Reuse aggregator paths to avoid drift
from mindx_backend_service.insight_aggregator import (
    InsightAggregator,
    CAMPAIGNS_FILE,
    FITNESS_DIR,
)

SELECTION_EVENTS_FILE = FITNESS_DIR / "selection_events.jsonl"
SELECTION_STATE_FILE = FITNESS_DIR / "selection_state.json"

TOURNAMENT_CAMPAIGN_DELTA = 25
TOURNAMENT_HOURS = 24
RETIRE_FITNESS_FLOOR = 20.0
MUTATION_FITNESS_CEILING = 70.0
MIN_CAMPAIGNS_BEFORE_RETIRE = 10  # no infanticide on fresh agents

MUTATIONS = (
    "prefer_conservative_planning",
    "prefer_faster_models",
    "prefer_peer_review_before_action",
)


@dataclass
class SelectionEvent:
    timestamp_utc: str
    event: str
    agent_id: str
    mode: str
    reason: str
    fitness_before: float
    fitness_after: Optional[float] = None
    parent_agent_id: Optional[str] = None
    mutation: Optional[str] = None


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _get_mode() -> str:
    mode = os.environ.get("MINDX_SELECTION_MODE", "shadow").strip().lower()
    if mode not in ("shadow", "advisory", "autonomous"):
        mode = "shadow"
    return mode


def _load_state() -> Dict[str, Any]:
    if SELECTION_STATE_FILE.exists():
        try:
            return json.loads(SELECTION_STATE_FILE.read_text())
        except Exception:
            pass
    return {"last_run_ts": 0.0, "last_campaign_count": 0, "mutation_counter": 0}


def _save_state(state: Dict[str, Any]):
    try:
        FITNESS_DIR.mkdir(parents=True, exist_ok=True)
        SELECTION_STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception as e:
        logger.debug(f"[selection] save_state failed: {e}")


def _append_event(event: SelectionEvent):
    try:
        FITNESS_DIR.mkdir(parents=True, exist_ok=True)
        with SELECTION_EVENTS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")
    except Exception as e:
        logger.debug(f"[selection] append event failed: {e}")


def _current_campaign_count() -> int:
    if not CAMPAIGNS_FILE.exists():
        return 0
    try:
        data = json.loads(CAMPAIGNS_FILE.read_text())
        return len(data) if isinstance(data, list) else 0
    except Exception:
        return 0


def _campaigns_credited(agent_id: str) -> int:
    """Rough count of campaigns credited to agent — for the min-history floor."""
    try:
        data = json.loads(CAMPAIGNS_FILE.read_text()) if CAMPAIGNS_FILE.exists() else []
    except Exception:
        return 0
    count = 0
    for c in data or []:
        blob = " ".join(str(c.get(k, "")) for k in ("run_id", "directive", "final_bdi_message")).lower()
        if agent_id in blob or agent_id == "mastermind_prime":
            count += 1
    return count


class SelectionEngine:
    _instance: Optional["SelectionEngine"] = None

    def __init__(self):
        FITNESS_DIR.mkdir(parents=True, exist_ok=True)
        self._task: Optional[asyncio.Task] = None
        self.aggregator = InsightAggregator.get_instance()
        self.poll_interval_s = 600  # check every 10min whether to run tournament
        self.mode = _get_mode()

    @classmethod
    def get_instance(cls) -> "SelectionEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("[selection] engine loop started mode=%s", self.mode)

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self):
        while True:
            try:
                await asyncio.sleep(self.poll_interval_s)
                await self.maybe_run_tournament()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[selection] loop iteration failed: {e}")

    async def maybe_run_tournament(self):
        state = _load_state()
        now = time.time()
        campaign_count = _current_campaign_count()
        by_count = campaign_count - state.get("last_campaign_count", 0) >= TOURNAMENT_CAMPAIGN_DELTA
        by_time = (now - state.get("last_run_ts", 0.0)) >= TOURNAMENT_HOURS * 3600
        if not (by_count or by_time):
            return
        await self.run_tournament()
        state["last_run_ts"] = now
        state["last_campaign_count"] = campaign_count
        _save_state(state)

    async def run_tournament(self) -> Dict[str, Any]:
        """Evaluate fitness, identify candidates, emit events per mode."""
        fitness = self.aggregator.snapshot()
        if not fitness:
            logger.info("[selection] tournament skipped — no fitness data yet")
            return {"skipped": True, "reason": "no_fitness_data"}

        fitness_sorted = sorted(fitness, key=lambda r: r["fitness"])
        n = len(fitness_sorted)
        q_size = max(1, n // 4)
        bottom_q = fitness_sorted[:q_size]
        top_q = fitness_sorted[-q_size:]

        retire_candidates: List[SelectionEvent] = []
        spawn_candidates: List[SelectionEvent] = []

        # Retirement proposals — bottom-quartile AND under floor AND has history.
        for r in bottom_q:
            agent_id = r["agent_id"]
            fit = r["fitness"]
            if fit >= RETIRE_FITNESS_FLOOR:
                continue
            if _campaigns_credited(agent_id) < MIN_CAMPAIGNS_BEFORE_RETIRE:
                continue
            event = SelectionEvent(
                timestamp_utc=_now_iso(),
                event="candidate_retire",
                agent_id=agent_id,
                mode=self.mode,
                reason=f"bottom_quartile_under_floor_{RETIRE_FITNESS_FLOOR}",
                fitness_before=fit,
            )
            retire_candidates.append(event)
            _append_event(event)

        # Spawn proposals — top-quartile AND above ceiling AND positive momentum.
        mutation_counter = _load_state().get("mutation_counter", 0)
        for r in top_q:
            agent_id = r["agent_id"]
            fit = r["fitness"]
            if fit < MUTATION_FITNESS_CEILING:
                continue
            axes = r.get("axes") or {}
            if axes.get("reputation_momentum", 50.0) <= 50.0:
                continue
            mutation = MUTATIONS[mutation_counter % len(MUTATIONS)]
            mutation_counter += 1
            event = SelectionEvent(
                timestamp_utc=_now_iso(),
                event="candidate_spawn",
                agent_id=f"{agent_id}_v{mutation_counter}",
                mode=self.mode,
                reason=f"top_quartile_above_ceiling_{MUTATION_FITNESS_CEILING}",
                fitness_before=fit,
                parent_agent_id=agent_id,
                mutation=mutation,
            )
            spawn_candidates.append(event)
            _append_event(event)

        # Update mutation counter
        state = _load_state()
        state["mutation_counter"] = mutation_counter
        _save_state(state)

        # Emit activity feed notification (shadow: info-only; advisory: board vote request)
        try:
            from mindx_backend_service.activity_feed import ActivityFeed
            feed = ActivityFeed.get_instance()
            feed.emit(
                "improvement",
                "selection_engine",
                "tournament",
                f"Tournament complete: {len(retire_candidates)} retire / {len(spawn_candidates)} spawn candidates (mode={self.mode})",
                detail={
                    "mode": self.mode,
                    "retire": [asdict(e) for e in retire_candidates],
                    "spawn":  [asdict(e) for e in spawn_candidates],
                },
                agent_tier=4,
            )
            if self.mode in ("advisory", "autonomous") and (retire_candidates or spawn_candidates):
                feed.emit(
                    "boardroom",
                    "selection_engine",
                    "proposal",
                    "Darwinian selection tournament proposes agent-map changes. Board vote required.",
                    detail={"retire": [asdict(e) for e in retire_candidates],
                            "spawn":  [asdict(e) for e in spawn_candidates]},
                    agent_tier=4,
                )
        except Exception as e:
            logger.debug(f"[selection] activity emit failed: {e}")

        # Autonomous mode would mutate agent_map.json here under a lock.
        # Intentionally NOT implemented — a plan-mandated gate. Anyone reading
        # this later: do not remove the gate without boardroom approval.
        if self.mode == "autonomous":
            logger.warning("[selection] autonomous mode active but agent_map writes are intentionally not implemented yet")

        logger.info(
            "[selection] tournament complete — mode=%s retire_candidates=%d spawn_candidates=%d",
            self.mode, len(retire_candidates), len(spawn_candidates),
        )
        return {
            "mode": self.mode,
            "retire_candidates": [asdict(e) for e in retire_candidates],
            "spawn_candidates":  [asdict(e) for e in spawn_candidates],
        }

    def recent_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        if not SELECTION_EVENTS_FILE.exists():
            return []
        try:
            lines = SELECTION_EVENTS_FILE.read_text().strip().split("\n")
            lines = lines[-limit:]
            out: List[Dict[str, Any]] = []
            for line in reversed(lines):
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
            return out
        except Exception:
            return []


def get_instance() -> SelectionEngine:
    return SelectionEngine.get_instance()
