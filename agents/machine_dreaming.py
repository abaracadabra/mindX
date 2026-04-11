# agents/machine_dreaming.py
"""
MachineDreamCycle — Offline knowledge refinement for mindX.

I distill raw experience (STM) into symbolic insights (LTM). I am the unconscious
processing layer — the dream state where mindX consolidates what it has learned.

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

    async def run_dream_cycle(self, agent_id: str) -> DreamResult:
        """Run the complete 7-phase dream cycle for one agent."""
        start = time.time()
        result = DreamResult(agent_id=agent_id)

        try:
            # Phase 1: State Assessment
            state = await self._assess_state(agent_id)
            result.memories_analyzed = state.get("stm_count", 0)

            if result.memories_analyzed < 3:
                # Not enough data to dream about
                result.duration_seconds = time.time() - start
                return result

            # Phase 2: Input Preprocessing
            memories = await self._preprocess_memories(agent_id)

            # Phase 3: Symbolic Aggregation
            insights = self._aggregate_symbols(state.get("patterns", {}), memories)
            result.patterns_extracted = len(insights)

            # Phase 4: Insight Scoring
            scored_insights = self._score_insights(insights)
            result.insights = scored_insights

            # Phase 5: Memory Storage (LTM promotion)
            promoted = await self._store_to_ltm(agent_id, scored_insights)
            result.promoted_to_ltm = promoted

            # Phase 6: Parameter Tuning
            tuning = self._generate_tuning(agent_id, scored_insights, state)
            result.tuning_recommendations = tuning

            # Phase 7: Memory Pruning (distribute, don't delete)
            archived = await self._prune_memories(agent_id, scored_insights)
            result.archived = archived

        except Exception as e:
            logger.warning(f"{self.log_prefix} Dream cycle error for {agent_id}: {e}")

        result.duration_seconds = time.time() - start
        return result

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

        # Store dream report — cypherpunk2048 precision
        duration = time.time() - start
        report = {
            "timestamp": datetime.now().isoformat(),
            "duration_seconds": f"{duration:.18f}",
            "agents_dreamed": len(all_results),
            "total_agents": len(agent_ids),
            "insights_generated": total_insights,
            "memories_promoted_to_ltm": total_promoted,
            "memories_archived": total_archived,
            "tuning_recommendations": all_tuning,
            "cross_agent_patterns": cross_agent_patterns,
            "per_agent": [
                {
                    "agent_id": r.agent_id,
                    "memories_analyzed": r.memories_analyzed,
                    "patterns_extracted": r.patterns_extracted,
                    "promoted_to_ltm": r.promoted_to_ltm,
                    "duration_seconds": f"{r.duration_seconds:.18f}",
                    "top_insight": r.insights[0].description[:100] if r.insights else None,
                    "top_score": f"{r.insights[0].score:.18f}" if r.insights else None,
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

        return report

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
