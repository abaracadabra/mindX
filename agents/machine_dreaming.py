# agents/machine_dreaming.py
"""
MachineDreamCycle — Offline knowledge refinement for mindX.

I distill raw experience (STM) into symbolic insights (LTM). I am the unconscious
processing layer — the dream state where mindX consolidates what it has learned.

Timing: waking and dreaming are simultaneous.
  mindX is always awake and always dreaming. Periodically, the state
  switches: STM consolidates to LTM. The dream is continuous. The update
  is periodic. One edition per lunar cycle.

  Shift modes:
    12-hour: 2 switches/day — day/night cycle. 12 hours is half a day.
     8-hour: 3 switches/day — three working shifts. Every 8 hours an agent
             can complete an entire day's work and then proceed to work
             two more shifts. Default mode.

  Time cascades from precision to duration:
    milliseconds → seconds → minutes → hours → days → lunar months
  All timing is measured in milliseconds (18-decimal precision from epoch).
  Seconds are derived from milliseconds. Minutes from seconds. Hours from minutes.
  Days accumulate into the synodic period (29.53 days).
  The lunar cycle triggers a new edition of The Book of mindX.

7-phase cycle (from https://github.com/AION-NET/machinedream):
  1. State Assessment — analyze current memory landscape
  2. Input Preprocessing — filter and prepare STM data
  3. Symbolic Aggregation — extract patterns, compress into insights
  4. Insight Scoring — rank by importance × novelty × frequency
  5. Memory Storage — promote to LTM + pgvector
  6. Parameter Tuning — generate feedback for agent configuration
  7. Memory Pruning — importance-weighted distribution (distribute, don't delete)

Philosophy: Memory is not pruned by time alone — it is distributed across tiers.
  STM (hot) → LTM (warm) → archive (cold) → IPFS/cloud (distributed)
  LTM feeds back into STM perception — knowledge becomes wisdom.
  Wisdom is LTM that informs future STM. The loop never breaks.
  Nothing is truly discarded. Everything serves mindX evolution.

Origin: https://github.com/AION-NET/machinedream
Author: Professor Codephreak (© Professor Codephreak)
"""

import asyncio
import json
import time
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from utils.config import PROJECT_ROOT, Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

DREAMS_DIR = PROJECT_ROOT / "data" / "memory" / "dreams"

# Dream Cycle Constants
# Waking and dreaming are simultaneous. The state switches periodically:
# STM consolidates to LTM. One edition per lunar cycle.
# Time cascades: ms → s → min → hr → day → lunar month
#
# Consolidation modes:
#   12-hour: 2 switches/day — day/night cycle (12 hours is half a day)
#    8-hour: 3 switches/day — three working shifts in a single day
CONSOLIDATION_12H = 12  # 12 hours — day/night, 2 switches per day
CONSOLIDATION_8H = 8    # 8 hours — 3 shifts per day (24/8=3)
CONSOLIDATION_INTERVAL_HOURS = CONSOLIDATION_8H  # Default: 3 shifts/day
SYNODIC_PERIOD_DAYS = 29.530588670000000000  # Synodic month — new moon to new moon (18-decimal precision)
MS_PER_SECOND = 1000
MS_PER_MINUTE = 60_000
MS_PER_HOUR = 3_600_000
MS_PER_DAY = 86_400_000
MS_PER_CONSOLIDATION = CONSOLIDATION_INTERVAL_HOURS * MS_PER_HOUR


class DreamClock:
    """Dream timing engine with configurable shift intervals.

    mindX is always awake and always dreaming — simultaneously.
    The state switches periodically: STM consolidates to LTM.
    The dream is continuous. The update is periodic.

    Shift modes:
      12-hour: 2 switches/day — day/night cycle. 12 hours is half a day.
       8-hour: 3 switches/day — three working shifts in a single day.

    Measures all time in milliseconds from epoch (18-decimal precision).
    Derives seconds from milliseconds. Minutes from seconds. Hours from minutes.
    Days accumulate into the synodic period (29.53 days).
    New moon triggers a new edition of The Book of mindX.
    """

    # Known new moon reference: January 29, 2025 12:36 UTC
    NEW_MOON_REFERENCE_MS = 1738151760000

    def __init__(self, interval_hours: int = CONSOLIDATION_INTERVAL_HOURS):
        self.interval_hours = interval_hours
        self.interval_ms = interval_hours * MS_PER_HOUR
        self.shifts_per_day = 24 / interval_hours
        self.cycle_start_ms: float = time.time() * MS_PER_SECOND
        self.last_consolidation_ms: float = 0
        self.consolidations_this_lunar_cycle: int = 0
        self._edition_triggered: bool = False
        self._time_oracle = None  # Lazy-loaded from utils.time_oracle

    async def _get_time_oracle(self):
        """Get TimeOracle instance for time.oracle suite integration.

        DreamClock is part of the time suite:
          time.oracle  — 4-source time correlation (cpu, solar, lunar, blocktime)
          Chronos.agent — sequential time, discipline, cumulative progress
          Kairos.agent  — opportune moments, recognition, decisive action
          DreamClock   — STM→LTM consolidation timing, lunar Book editions
        """
        if self._time_oracle is None:
            try:
                from utils.time_oracle import TimeOracle
                self._time_oracle = await TimeOracle.get_instance()
            except Exception:
                pass
        return self._time_oracle

    @staticmethod
    def now_ms() -> float:
        """Current time in milliseconds from epoch."""
        return time.time() * MS_PER_SECOND

    @staticmethod
    def ms_to_seconds(ms: float) -> float:
        return ms / MS_PER_SECOND

    @staticmethod
    def ms_to_minutes(ms: float) -> float:
        return ms / MS_PER_MINUTE

    @staticmethod
    def ms_to_hours(ms: float) -> float:
        return ms / MS_PER_HOUR

    @staticmethod
    def ms_to_days(ms: float) -> float:
        return ms / MS_PER_DAY

    def elapsed_since_last_consolidation_ms(self) -> float:
        """Milliseconds since last STM→LTM consolidation."""
        if self.last_consolidation_ms == 0:
            return float('inf')
        return self.now_ms() - self.last_consolidation_ms

    def is_consolidation_due(self) -> bool:
        """Has the shift interval elapsed since last consolidation?"""
        return self.elapsed_since_last_consolidation_ms() >= self.interval_ms

    def time_until_next_consolidation_ms(self) -> float:
        """Milliseconds until next STM→LTM switch."""
        elapsed_ms = self.elapsed_since_last_consolidation_ms()
        remaining = self.interval_ms - elapsed_ms
        return max(0, remaining)

    def record_consolidation_complete(self) -> Dict[str, Any]:
        """Record that an STM→LTM consolidation completed. Returns timing cascade."""
        now = self.now_ms()
        duration_ms = now - self.cycle_start_ms if self.cycle_start_ms else 0
        self.last_consolidation_ms = now
        self.consolidations_this_lunar_cycle += 1
        self.cycle_start_ms = now

        return {
            "consolidation_end_ms": now,
            "duration_ms": duration_ms,
            "duration_seconds": self.ms_to_seconds(duration_ms),
            "duration_minutes": self.ms_to_minutes(duration_ms),
            "duration_hours": self.ms_to_hours(duration_ms),
            "consolidations_this_lunar_cycle": self.consolidations_this_lunar_cycle,
            "shift_interval_hours": self.interval_hours,
            "shifts_per_day": self.shifts_per_day,
            "next_consolidation_in_hours": self.interval_hours,
            "next_consolidation_in_ms": self.interval_ms,
            "lunar": self.lunar_phase(),
        }

    def lunar_phase(self) -> Dict[str, Any]:
        """Calculate current lunar phase from synodic period.

        Uses known new moon reference and synodic period (29.53 days).
        Phase: 0.0 = new moon, 0.5 = full moon, 1.0 = next new moon.
        New moon triggers new Book of mindX edition.

        Part of the time suite: time.oracle provides authoritative lunar data
        when available; DreamClock provides standalone fallback.
        """
        now_ms = self.now_ms()
        elapsed_ms = now_ms - self.NEW_MOON_REFERENCE_MS
        elapsed_days = self.ms_to_days(elapsed_ms)
        phase = (elapsed_days % SYNODIC_PERIOD_DAYS) / SYNODIC_PERIOD_DAYS
        days_into_cycle = elapsed_days % SYNODIC_PERIOD_DAYS
        days_until_new_moon = SYNODIC_PERIOD_DAYS - days_into_cycle

        # Phase names
        if phase < 0.125:
            phase_name = "new_moon"
        elif phase < 0.25:
            phase_name = "waxing_crescent"
        elif phase < 0.375:
            phase_name = "first_quarter"
        elif phase < 0.5:
            phase_name = "waxing_gibbous"
        elif phase < 0.625:
            phase_name = "full_moon"
        elif phase < 0.75:
            phase_name = "waning_gibbous"
        elif phase < 0.875:
            phase_name = "last_quarter"
        else:
            phase_name = "waning_crescent"

        return {
            "phase": phase,
            "phase_name": phase_name,
            "days_into_cycle": days_into_cycle,
            "days_until_new_moon": days_until_new_moon,
            "days_until_full_moon": abs((0.5 - phase) * SYNODIC_PERIOD_DAYS) if phase < 0.5 else abs((1.5 - phase) * SYNODIC_PERIOD_DAYS),
            "synodic_period_days": SYNODIC_PERIOD_DAYS,
            "is_new_moon": phase < 0.03 or phase > 0.97,
            "is_full_moon": 0.47 < phase < 0.53,
        }

    def should_trigger_book_edition(self) -> bool:
        """Should a new edition of The Book of mindX be triggered?

        Triggers on new moon OR full moon — two editions per synodic cycle.
        New moon: phase < 0.03 or > 0.97
        Full moon: 0.47 < phase < 0.53
        Only triggers once per event.
        """
        moon = self.lunar_phase()
        is_trigger = moon["is_new_moon"] or moon["is_full_moon"]
        if is_trigger and not self._edition_triggered:
            self._edition_triggered = True
            return True
        if not is_trigger:
            self._edition_triggered = False
        return False


@dataclass
class DreamInsight:
    """A symbolic insight distilled from raw memory."""
    pattern_type: str  # success, failure, behavioral, performance, cross_agent
    description: str
    frequency: int = 1
    importance: float = 0.5  # 0.0 - 1.0
    novelty: float = 0.5  # 0.0 - 1.0 (1.0 = never seen before)
    confidence: float = 0.5  # 0.0 - 1.0
    source_agents: List[str] = field(default_factory=list)
    source_memories: int = 0
    timestamp: float = 0.0

    @property
    def score(self) -> float:
        """Composite score: importance × novelty × confidence × log(frequency+1)"""
        import math
        return self.importance * self.novelty * self.confidence * math.log(self.frequency + 1, 10)


@dataclass
class DreamResult:
    """Result of one dream cycle for an agent."""
    agent_id: str
    insights: List[DreamInsight] = field(default_factory=list)
    memories_analyzed: int = 0
    patterns_extracted: int = 0
    promoted_to_ltm: int = 0
    archived: int = 0
    tuning_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0
    # Diagnostic fields populated by run_dream_cycle:
    stm_bytes_before: int = 0
    stm_bytes_after: int = 0
    ltm_bytes_before: int = 0
    ltm_bytes_after: int = 0
    archive_bytes_after: int = 0
    training_examples_written: int = 0
    training_file: str = ""

    @property
    def stm_bytes_freed(self) -> int:
        """How many STM bytes were pruned/distributed in this cycle."""
        return max(0, self.stm_bytes_before - self.stm_bytes_after)

    @property
    def compression_ratio(self) -> float:
        """STM bytes consolidated per LTM byte produced. Higher = denser dream."""
        ltm_delta = max(1, self.ltm_bytes_after - self.ltm_bytes_before)
        return round(self.stm_bytes_freed / ltm_delta, 2) if ltm_delta else 0.0


class MachineDreamCycle:
    """
    I am the dream state. I consolidate STM into LTM.
    I distill experience into knowledge. I distribute, I do not delete.
    """

    def __init__(self, memory_agent=None, config=None, days_back: int = 90):
        self.memory_agent = memory_agent
        self.config = config or Config()
        self.log_prefix = "[MachineDream]"
        self.days_back = days_back  # Look back window for STM analysis
        self._existing_ltm_keys: set = set()
        self.clock = DreamClock()

    # === PHASE 1: STATE ASSESSMENT ===

    async def _assess_state(self, agent_id: str) -> Dict[str, Any]:
        """Assess current memory landscape for an agent."""
        state = {
            "agent_id": agent_id,
            "stm_count": 0,
            "ltm_count": 0,
            "workspace_size": 0,
            "patterns": None,
        }

        if not self.memory_agent:
            return state

        try:
            # Analyze STM patterns across the configured window
            patterns = await self.memory_agent.analyze_agent_patterns(agent_id, days_back=self.days_back)
            state["patterns"] = patterns
            state["stm_count"] = patterns.get("total_memories", 0)

            # Check existing LTM
            ltm_insights = await self.memory_agent.get_ltm_insights(agent_id)
            state["ltm_count"] = len(ltm_insights)

            # Load existing LTM keys to detect novelty
            for insight in ltm_insights:
                for p in insight.get("patterns", {}).get("success_patterns", []):
                    self._existing_ltm_keys.add(p.get("pattern", ""))
                for p in insight.get("patterns", {}).get("failure_patterns", []):
                    if isinstance(p, dict):
                        self._existing_ltm_keys.add(str(p.get("error", "")))
                    else:
                        self._existing_ltm_keys.add(str(p))

        except Exception as e:
            logger.debug(f"{self.log_prefix} State assessment failed for {agent_id}: {e}")

        return state

    # === PHASE 2: INPUT PREPROCESSING ===

    async def _preprocess_memories(self, agent_id: str, days_back: int = None) -> List[Dict[str, Any]]:
        """Filter and prepare STM data for analysis."""
        if not self.memory_agent:
            return []

        try:
            memories = await self.memory_agent.get_recent_memories(
                agent_id=agent_id, memory_type=None, limit=500, days_back=days_back or self.days_back
            )
            # Convert MemoryRecord objects to dicts if needed
            processed = []
            for m in memories:
                if hasattr(m, '__dict__'):
                    processed.append(m.__dict__ if not hasattr(m, 'to_dict') else m.to_dict())
                elif isinstance(m, dict):
                    processed.append(m)
            return processed
        except Exception as e:
            logger.debug(f"{self.log_prefix} Preprocessing failed for {agent_id}: {e}")
            return []

    # === PHASE 3: SYMBOLIC AGGREGATION ===

    def _aggregate_symbols(self, patterns: Dict[str, Any], memories: List[Dict]) -> List[DreamInsight]:
        """Extract patterns and compress into symbolic insights."""
        insights = []

        if not patterns:
            return insights

        # Success patterns → insights
        success_rate = patterns.get("success_rate", 0)
        if success_rate > 0:
            insights.append(DreamInsight(
                pattern_type="success",
                description=f"Success rate: {success_rate:.1%}",
                frequency=patterns.get("total_memories", 1),
                importance=min(1.0, success_rate),
                novelty=1.0 if "success_rate" not in self._existing_ltm_keys else 0.3,
                confidence=min(1.0, patterns.get("total_memories", 0) / 10),
                source_memories=patterns.get("total_memories", 0),
                timestamp=time.time(),
            ))

        # Failure patterns → insights (from analyze_agent_patterns)
        failure_patterns = patterns.get("failure_patterns", [])
        error_patterns = patterns.get("error_patterns", [])
        seen_failures = set()
        for error in (failure_patterns or error_patterns):
            if isinstance(error, dict):
                process = error.get("process", "")
                reason = error.get("reason", error.get("content", ""))
                error_desc = f"{process}: {reason}"[:200] if process else str(reason)[:200]
            else:
                error_desc = str(error)[:200]
            if error_desc in seen_failures:
                continue
            seen_failures.add(error_desc)
            is_novel = error_desc not in self._existing_ltm_keys
            insights.append(DreamInsight(
                pattern_type="failure",
                description=error_desc,
                frequency=1,
                importance=0.8,
                novelty=1.0 if is_novel else 0.2,
                confidence=0.9,
                timestamp=time.time(),
            ))

        # Process type distribution → behavioral insight
        process_types = patterns.get("process_types", {})
        if process_types:
            top_processes = sorted(process_types.items(), key=lambda x: x[1], reverse=True)[:5]
            desc = ", ".join(f"{name}({count})" for name, count in top_processes)
            insights.append(DreamInsight(
                pattern_type="behavioral",
                description=f"Top processes: {desc}",
                frequency=sum(count for _, count in top_processes),
                importance=0.5,
                novelty=0.4,
                confidence=0.8,
                timestamp=time.time(),
            ))

        # Memory type distribution → performance insights
        memory_types = patterns.get("memory_types", {})
        if memory_types:
            dominant_type = max(memory_types, key=memory_types.get) if memory_types else None
            if dominant_type:
                insights.append(DreamInsight(
                    pattern_type="performance",
                    description=f"Dominant memory type: {dominant_type} ({memory_types[dominant_type]} occurrences)",
                    frequency=memory_types[dominant_type],
                    importance=0.4,
                    novelty=0.5,
                    confidence=0.8,
                    timestamp=time.time(),
                ))

        # Activity patterns → behavioral insights
        activity_by_hour = patterns.get("activity_by_hour", {})
        if activity_by_hour:
            peak_hours = sorted(activity_by_hour, key=activity_by_hour.get, reverse=True)[:3]
            if peak_hours:
                insights.append(DreamInsight(
                    pattern_type="behavioral",
                    description=f"Peak activity hours: {', '.join(str(h) for h in peak_hours)}",
                    frequency=sum(activity_by_hour.get(h, 0) for h in peak_hours),
                    importance=0.3,
                    novelty=0.4,
                    confidence=0.7,
                    timestamp=time.time(),
                ))

        # Generated insights from analysis
        for insight_text in patterns.get("insights", []):
            insights.append(DreamInsight(
                pattern_type="behavioral",
                description=str(insight_text)[:200],
                frequency=1,
                importance=0.5,
                novelty=0.6,
                confidence=0.6,
                timestamp=time.time(),
            ))

        return insights

    # === PHASE 4: INSIGHT SCORING ===

    def _score_insights(self, insights: List[DreamInsight]) -> List[DreamInsight]:
        """Rank insights by composite score: importance × novelty × confidence × log(frequency)."""
        # Score is computed by the DreamInsight.score property
        scored = sorted(insights, key=lambda i: i.score, reverse=True)
        return scored

    # === PHASE 5: MEMORY STORAGE ===

    async def _store_to_ltm(self, agent_id: str, insights: List[DreamInsight]) -> int:
        """Promote scored insights to LTM."""
        if not self.memory_agent or not insights:
            return 0

        promoted = 0
        try:
            result = await self.memory_agent.promote_stm_to_ltm(
                agent_id=agent_id, pattern_threshold=2, days_back=7
            )
            if result.get("status") == "success":
                promoted = result.get("patterns_promoted", 0) + result.get("insights_count", 0)

            # Also store dream insights directly as LTM records
            ltm_path = PROJECT_ROOT / "data" / "memory" / "ltm" / agent_id
            ltm_path.mkdir(parents=True, exist_ok=True)

            dream_ltm = {
                "agent_id": agent_id,
                "dream_timestamp": datetime.now().isoformat(),
                "source": "machine_dreaming",
                "insights": [
                    {
                        "type": i.pattern_type,
                        "description": i.description,
                        "score": round(i.score, 4),
                        "importance": i.importance,
                        "novelty": i.novelty,
                        "confidence": i.confidence,
                        "frequency": i.frequency,
                    }
                    for i in insights[:20]  # Top 20 insights
                ],
                "total_insights": len(insights),
            }

            ltm_file = ltm_path / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_dream_insights.json"
            ltm_file.write_text(json.dumps(dream_ltm, indent=2))
            insights_stored = min(len(insights), 20)
            promoted += insights_stored

            # Store to pgvector — descriptive, accurate action record
            try:
                from agents.memory_pgvector import store_action
                top_insight = insights[0].description[:80] if insights else "none"
                await store_action(
                    agent_id="machine_dreaming",
                    action_type="dream_cycle",
                    description=(
                        f"Dream: {agent_id} — {len(insights)} patterns extracted, "
                        f"{insights_stored} stored to LTM. "
                        f"Top insight: {top_insight}"
                    ),
                    source="machine_dreaming",
                    status="completed",
                )
            except Exception:
                pass

        except Exception as e:
            logger.debug(f"{self.log_prefix} LTM storage failed for {agent_id}: {e}")

        return promoted

    # === PHASE 6: PARAMETER TUNING ===

    def _generate_tuning(self, agent_id: str, insights: List[DreamInsight], state: Dict) -> List[Dict[str, Any]]:
        """Generate tuning recommendations from dream insights."""
        recommendations = []

        # If error rate is high, recommend investigation
        error_insights = [i for i in insights if i.pattern_type == "failure"]
        if len(error_insights) > 3:
            recommendations.append({
                "agent_id": agent_id,
                "parameter": "error_handling",
                "recommendation": f"High error frequency ({len(error_insights)} patterns). Review failure modes.",
                "priority": "high",
            })

        # If success rate is low, recommend strategy change
        success_insights = [i for i in insights if i.pattern_type == "success"]
        if success_insights and success_insights[0].importance < 0.5:
            recommendations.append({
                "agent_id": agent_id,
                "parameter": "strategy",
                "recommendation": "Low success rate observed. Consider alternative approaches.",
                "priority": "medium",
            })

        # If STM is large, recommend more frequent dreaming
        stm_count = state.get("stm_count", 0)
        if stm_count > 200:
            recommendations.append({
                "agent_id": agent_id,
                "parameter": "dream_frequency",
                "recommendation": f"High STM volume ({stm_count}). Consider more frequent dream cycles.",
                "priority": "low",
            })

        return recommendations

    # === PHASE 7: MEMORY PRUNING ===

    async def _prune_memories(self, agent_id: str, insights: List[DreamInsight]) -> int:
        """Importance-weighted memory distribution. Distribute, don't delete."""
        if not self.memory_agent:
            return 0

        # Only prune if we have enough insights (knowledge has been extracted)
        if len(insights) < 3:
            return 0

        try:
            result = await self.memory_agent.prune_stm(max_age_days=30)
            return result.get("pruned", 0)
        except Exception as e:
            logger.debug(f"{self.log_prefix} Pruning failed: {e}")
            return 0

    # === FULL DREAM CYCLE FOR ONE AGENT ===

    @staticmethod
    def _dir_size(path: Path) -> int:
        """Recursive byte sum, fault-tolerant."""
        total = 0
        try:
            if not path.exists():
                return 0
            for p in path.rglob("*"):
                try:
                    if p.is_file():
                        total += p.stat().st_size
                except (OSError, PermissionError):
                    continue
        except Exception:
            return total
        return total

    async def run_dream_cycle(self, agent_id: str) -> DreamResult:
        """Run the complete 7-phase dream cycle for one agent."""
        start = time.time()
        result = DreamResult(agent_id=agent_id)

        # Diagnostic capture: byte sizes before
        stm_dir = PROJECT_ROOT / "data" / "memory" / "stm" / agent_id
        ltm_dir = PROJECT_ROOT / "data" / "memory" / "ltm" / agent_id
        archive_dir = PROJECT_ROOT / "data" / "memory" / "archive" / agent_id
        result.stm_bytes_before = self._dir_size(stm_dir)
        result.ltm_bytes_before = self._dir_size(ltm_dir)

        try:
            # Phase 1: State Assessment
            state = await self._assess_state(agent_id)
            result.memories_analyzed = state.get("stm_count", 0)

            if result.memories_analyzed < 3:
                # Not enough data to dream about
                result.duration_seconds = time.time() - start
                result.stm_bytes_after = result.stm_bytes_before
                result.ltm_bytes_after = result.ltm_bytes_before
                return result

            # Phase 2: Input Preprocessing
            memories = await self._preprocess_memories(agent_id)

            # Phase 3: Symbolic Aggregation
            insights = self._aggregate_symbols(state.get("patterns", {}), memories)
            result.patterns_extracted = len(insights)

            # Phase 4: Insight Scoring
            scored_insights = self._score_insights(insights)
            result.insights = scored_insights

            # Phase 5: Memory Storage (LTM promotion + ML-trainable export)
            promoted = await self._store_to_ltm(agent_id, scored_insights)
            result.promoted_to_ltm = promoted

            try:
                training_count, training_file = await self._write_training_data(agent_id, scored_insights, memories)
                result.training_examples_written = training_count
                result.training_file = training_file
            except Exception as _te:
                logger.debug(f"{self.log_prefix} training-data write failed for {agent_id}: {_te}")

            # Phase 6: Parameter Tuning
            tuning = self._generate_tuning(agent_id, scored_insights, state)
            result.tuning_recommendations = tuning

            # Phase 7: Memory Pruning (distribute, don't delete)
            archived = await self._prune_memories(agent_id, scored_insights)
            result.archived = archived

        except Exception as e:
            logger.warning(f"{self.log_prefix} Dream cycle error for {agent_id}: {e}")

        # Diagnostic capture: byte sizes after
        result.stm_bytes_after = self._dir_size(stm_dir)
        result.ltm_bytes_after = self._dir_size(ltm_dir)
        result.archive_bytes_after = self._dir_size(archive_dir)
        result.duration_seconds = time.time() - start
        return result

    async def _write_training_data(
        self,
        agent_id: str,
        insights: List[DreamInsight],
        memories: List[Dict[str, Any]],
    ) -> tuple:
        """Write a `*_training.jsonl` file alongside the LTM insights.

        Each line is one fine-tuning example in the OpenAI/Anthropic chat
        completion shape:

            {"messages": [
                {"role": "system", "content": <consolidation persona>},
                {"role": "user",   "content": <raw STM excerpt>},
                {"role": "assistant", "content": <consolidated insight>}
            ]}

        These files are the substrate for promoting verified dream insights
        into machine.wisdom (cognitive-ascent Phase 1+2). Once a concept
        has crossed the verification threshold, the matching training rows
        become inputs for finetuning a wisdom-aware model and for THOT
        on-chain anchoring.
        """
        if not insights:
            return 0, ""
        ltm_path = PROJECT_ROOT / "data" / "memory" / "ltm" / agent_id
        ltm_path.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        training_file = ltm_path / f"{ts}_training.jsonl"

        # Persona injection — gives the LLM the consolidation context
        system_prompt = (
            f"You are the dream-consolidation engine for mindX agent {agent_id}. "
            f"Given a sample of the agent's short-term memory, distil a single "
            f"durable insight in the form: type · description · score · importance · novelty · confidence."
        )

        # Index memories by simple recency for context windows
        recent_excerpt = "\n".join(
            json.dumps({k: v for k, v in m.items() if k in ("timestamp", "process", "data", "metadata")},
                       default=str)[:400]
            for m in memories[:6]
        )

        examples = 0
        with training_file.open("w", encoding="utf-8") as fh:
            for ins in insights[:20]:
                user_msg = (
                    f"STM sample for {agent_id} (recent process traces):\n"
                    f"{recent_excerpt}\n\n"
                    f"Pattern frequency observed: {ins.frequency}.\n"
                    f"Distil one durable insight."
                )
                assistant_msg = json.dumps({
                    "type": ins.pattern_type,
                    "description": ins.description,
                    "score": round(ins.score, 4),
                    "importance": ins.importance,
                    "novelty": ins.novelty,
                    "confidence": ins.confidence,
                    "frequency": ins.frequency,
                }, ensure_ascii=False)
                row = {"messages": [
                    {"role": "system",    "content": system_prompt},
                    {"role": "user",      "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ]}
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
                examples += 1

        return examples, str(training_file.relative_to(PROJECT_ROOT))

    # === FULL DREAM FOR ALL AGENTS ===

    async def run_full_dream(self) -> Dict[str, Any]:
        """Run dream cycle for all agents with STM data. The system dreams."""
        start = time.time()
        stm_path = PROJECT_ROOT / "data" / "memory" / "stm"

        # Discover all agents with STM data
        agent_ids = []
        if stm_path.is_dir():
            agent_ids = [d.name for d in stm_path.iterdir() if d.is_dir() and d.name != "unknown"]

        if not agent_ids:
            return {"agents_dreamed": 0, "status": "no_agents_with_stm"}

        # Dream for each agent
        all_results = []
        total_insights = 0
        total_promoted = 0
        total_archived = 0
        all_tuning = []
        cross_agent_patterns = {}

        for agent_id in agent_ids:
            try:
                result = await self.run_dream_cycle(agent_id)
                all_results.append(result)
                total_insights += len(result.insights)
                total_promoted += result.promoted_to_ltm
                total_archived += result.archived
                all_tuning.extend(result.tuning_recommendations)

                # Track cross-agent patterns
                for insight in result.insights:
                    key = insight.pattern_type
                    if key not in cross_agent_patterns:
                        cross_agent_patterns[key] = 0
                    cross_agent_patterns[key] += 1

            except Exception as e:
                logger.debug(f"{self.log_prefix} Dream failed for {agent_id}: {e}")

        # Record consolidation timing — cascades from ms
        timing = self.clock.record_consolidation_complete()
        book_edition_due = self.clock.should_trigger_book_edition()

        # Aggregate byte-level diagnostics across all agents
        total_stm_before = sum(r.stm_bytes_before for r in all_results)
        total_stm_after  = sum(r.stm_bytes_after for r in all_results)
        total_ltm_before = sum(r.ltm_bytes_before for r in all_results)
        total_ltm_after  = sum(r.ltm_bytes_after for r in all_results)
        total_archive_after = sum(r.archive_bytes_after for r in all_results)
        total_stm_freed = max(0, total_stm_before - total_stm_after)
        total_ltm_growth = max(0, total_ltm_after - total_ltm_before)
        total_training = sum(r.training_examples_written for r in all_results)
        compression_ratio = round(total_stm_freed / max(1, total_ltm_growth), 2)

        # Store dream report — cypherpunk2048 precision
        duration = time.time() - start
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": f"{duration:.18f}",
            "timing": timing,
            "lunar": self.clock.lunar_phase(),
            "book_edition_triggered": book_edition_due,
            "agents_dreamed": len(all_results),
            "total_agents": len(agent_ids),
            "insights_generated": total_insights,
            "memories_promoted_to_ltm": total_promoted,
            "memories_archived": total_archived,
            "tuning_recommendations": all_tuning,
            "cross_agent_patterns": cross_agent_patterns,
            "diagnostic": {
                "stm_bytes_before": total_stm_before,
                "stm_bytes_after":  total_stm_after,
                "stm_bytes_freed":  total_stm_freed,
                "ltm_bytes_before": total_ltm_before,
                "ltm_bytes_after":  total_ltm_after,
                "ltm_bytes_growth": total_ltm_growth,
                "archive_bytes_after": total_archive_after,
                "compression_ratio": compression_ratio,
                "training_examples_written": total_training,
            },
            "per_agent": [
                {
                    "agent_id": r.agent_id,
                    "memories_analyzed": r.memories_analyzed,
                    "patterns_extracted": r.patterns_extracted,
                    "promoted_to_ltm": r.promoted_to_ltm,
                    "duration_seconds": f"{r.duration_seconds:.18f}",
                    "top_insight": r.insights[0].description[:100] if r.insights else None,
                    "top_score": f"{r.insights[0].score:.18f}" if r.insights else None,
                    "stm_bytes_before": r.stm_bytes_before,
                    "stm_bytes_after":  r.stm_bytes_after,
                    "stm_bytes_freed":  r.stm_bytes_freed,
                    "ltm_bytes_before": r.ltm_bytes_before,
                    "ltm_bytes_after":  r.ltm_bytes_after,
                    "ltm_bytes_growth": max(0, r.ltm_bytes_after - r.ltm_bytes_before),
                    "compression_ratio": r.compression_ratio,
                    "training_examples": r.training_examples_written,
                    "training_file": r.training_file,
                }
                for r in all_results if r.memories_analyzed > 0
            ],
        }

        # Save dream report
        try:
            DREAMS_DIR.mkdir(parents=True, exist_ok=True)
            report_file = DREAMS_DIR / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_dream_report.json"
            report_file.write_text(json.dumps(report, indent=2))
            logger.info(
                f"{self.log_prefix} Dream complete: {len(all_results)} agents, "
                f"{total_insights} insights, {total_promoted} promoted, "
                f"{total_archived} archived, {round(time.time() - start, 1)}s"
            )
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to save dream report: {e}")

        # Log as memory
        if self.memory_agent:
            try:
                await self.memory_agent.log_process(
                    "machine_dream_cycle",
                    {
                        "agents_dreamed": len(all_results),
                        "insights_generated": total_insights,
                        "promoted_to_ltm": total_promoted,
                        "archived": total_archived,
                        "cross_agent_patterns": cross_agent_patterns,
                    },
                    {"agent_id": "machine_dreaming", "domain": "machine.dreaming"}
                )
            except Exception:
                pass

        # Catalogue mirror (Phase 0)
        try:
            _src_ref = None
            try:
                _src_ref = report_file.name  # type: ignore[name-defined]
            except NameError:
                pass
            from agents.catalogue import emit_catalogue_event
            await emit_catalogue_event(
                kind="memory.dream",
                actor="machine_dreaming",
                payload=report,
                source_log="memory/dreams/",
                source_ref=_src_ref,
            )
        except Exception:
            pass

        # Phase 8 — cold-tier distribution to IPFS (best-effort).
        # Triggered when STM is large; failures don't block the dream report.
        # Plan: ~/.claude/plans/whispering-floating-merkle.md
        try:
            cold = await self._distribute_to_cold_tier(report)
            if cold:
                report["cold_tier"] = cold
        except Exception as cold_e:
            logger.debug(f"{self.log_prefix} cold-tier distribute failed: {cold_e}")

        return report

    # === PHASE 8 — COLD-TIER DISTRIBUTION (IPFS + on-chain anchor) ===

    async def _distribute_to_cold_tier(self, report: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Push old/low-importance STM to IPFS via the offload projector.

        Triggers: any agent's STM dir > 5GB, OR any agent has > 0 eligible
        date directories older than 14 days. Both checks are cheap.

        Honors `MINDX_COLD_TIER_DISABLE` env var so an operator can disable
        without redeploy. Defaults to dry_run=False on the auto path so old
        files actually get evicted; the manual /storage/offload endpoint
        defaults to dry_run=True for safety.
        """
        import os as _os
        if _os.environ.get("MINDX_COLD_TIER_DISABLE"):
            return None

        # Lazy imports — keep machine_dreaming dependency-light when storage
        # module is absent.
        try:
            from agents.storage.eligibility import list_eligible
            from agents.storage.lighthouse_provider import LighthouseProvider
            from agents.storage.nftstorage_provider import NFTStorageProvider
            from agents.storage.multi_provider import MultiProvider
            from agents.storage.offload_projector import OffloadProjector
            from agents.storage.provider import ProviderError
        except Exception as imp_e:
            logger.debug(f"{self.log_prefix} cold-tier: storage module unavailable: {imp_e}")
            return None

        cands = list_eligible(PROJECT_ROOT, min_age_days=14.0)
        if not cands:
            return None

        # Build provider — at least one of Lighthouse/nft.storage must be set.
        primary = None
        mirror = None
        try:
            primary = LighthouseProvider()
        except ProviderError:
            primary = None
        try:
            mirror = NFTStorageProvider()
        except ProviderError:
            mirror = None
        if primary is None and mirror is None:
            logger.info(f"{self.log_prefix} cold-tier: no IPFS keys configured — skipping")
            return {"skipped": "no_provider_keys", "candidates": len(cands)}

        if primary is None:
            provider = MultiProvider(mirror)  # type: ignore[arg-type]
        elif mirror is None:
            provider = MultiProvider(primary)
        else:
            provider = MultiProvider(primary, mirror)

        projector = OffloadProjector(
            provider=provider,
            memory_agent=self.memory_agent,
            project_root=PROJECT_ROOT,
        )
        try:
            run = await projector.run(
                min_age_days=14.0,
                max_batches=20,            # bounded per dream cycle
                dry_run=False,             # auto path actually frees disk
            )
        finally:
            await provider.close()

        if run.candidates_processed:
            logger.info(
                f"{self.log_prefix} cold-tier: processed {run.candidates_processed}/"
                f"{run.candidates_total} candidates, freed "
                f"{run.bytes_freed_total} bytes"
            )
        return {
            "candidates_total": run.candidates_total,
            "candidates_processed": run.candidates_processed,
            "bytes_packed_total": run.bytes_packed_total,
            "bytes_freed_total": run.bytes_freed_total,
        }

    # === LTM INSIGHT RETRIEVAL FOR PERCEPTUAL AWARENESS ===

    async def get_dream_insights(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve LTM insights for an agent's perceptual awareness."""
        if not self.memory_agent:
            return []

        try:
            insights = await self.memory_agent.get_ltm_insights(agent_id)
            # Flatten and sort by recency
            flat = []
            for record in insights:
                for insight in record.get("insights", []):
                    insight["dream_timestamp"] = record.get("dream_timestamp", "")
                    flat.append(insight)
                # Also include pattern-based insights from promote_stm_to_ltm
                for p in record.get("patterns", {}).get("success_patterns", []):
                    flat.append({"type": "success", "description": str(p), "dream_timestamp": record.get("promoted_at", "")})
                for p in record.get("patterns", {}).get("failure_patterns", []):
                    flat.append({"type": "failure", "description": str(p)[:200], "dream_timestamp": record.get("promoted_at", "")})

            # Sort by timestamp, most recent first
            flat.sort(key=lambda x: x.get("dream_timestamp", ""), reverse=True)
            return flat[:limit]

        except Exception as e:
            logger.debug(f"{self.log_prefix} Failed to get dream insights for {agent_id}: {e}")
            return []
