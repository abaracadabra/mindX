"""
Insight Aggregator — per-agent fitness + system-level improvement metrics.

Runs as a singleton asyncio loop (60s cadence), caches results, exposes cached
values to the `/insight/*` API routes. Never recomputes inline on request.

All data sources are READ-ONLY files already maintained by the rest of mindX:

    data/memory/agent_workspaces/mastermind_prime/mastermind_campaigns_history.json
    data/memory/agent_workspaces/{agent_id}/process_trace.jsonl
    data/governance/dojo_events.jsonl
    data/governance/boardroom_sessions.jsonl
    data/logs/godel_choices.jsonl
    data/memory/beliefs.json
    data/model_performance_metrics.json
    daio/agents/agent_map.json

Missing files are handled gracefully (fitness degrades to neutral 50, verdicts
degrade to "INSUFFICIENT DATA" — same honesty stance as thesis_evidence.py).

Fitness axes (0-100 each), explicit weights:

    campaign_success       0.25   mastermind campaigns credited to agent
    trace_reliability      0.20   per-agent process_trace success rate
    latency_score          0.10   EMA of process latency
    consensus_alignment    0.15   % of votes inside weighted majority
    reputation_momentum    0.10   7-day dojo_events delta
    learning_velocity      0.10   new/updated beliefs in last 24h
    godel_selection_rate   0.10   chosen / (options_considered containing agent)

Bias is deliberate — campaign_success + trace_reliability sum to 0.45, so
noisy agents that "talk a lot without shipping" cannot rank top.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

# ─── Paths (all read-only, missing-tolerant) ────────────────────────────────
AGENT_MAP_FILE         = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
CAMPAIGNS_FILE         = PROJECT_ROOT / "data" / "memory" / "agent_workspaces" / "mastermind_prime" / "mastermind_campaigns_history.json"
AGENT_WORKSPACES_DIR   = PROJECT_ROOT / "data" / "memory" / "agent_workspaces"
DOJO_EVENTS_FILE       = PROJECT_ROOT / "data" / "governance" / "dojo_events.jsonl"
BOARDROOM_SESSIONS     = PROJECT_ROOT / "data" / "governance" / "boardroom_sessions.jsonl"
GODEL_CHOICES          = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
BELIEFS_FILE           = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
MODEL_METRICS_FILE     = PROJECT_ROOT / "data" / "model_performance_metrics.json"

# ─── Fitness output location (new) ──────────────────────────────────────────
FITNESS_DIR            = PROJECT_ROOT / "data" / "fitness"
DAILY_SNAPSHOTS_FILE   = FITNESS_DIR / "daily_snapshots.jsonl"
CURRENT_SNAPSHOT_FILE  = FITNESS_DIR / "current_snapshot.json"

# ─── Weights ────────────────────────────────────────────────────────────────
FITNESS_WEIGHTS: Dict[str, float] = {
    "campaign_success":     0.25,
    "trace_reliability":    0.20,
    "latency_score":        0.10,
    "consensus_alignment":  0.15,
    "reputation_momentum":  0.10,
    "learning_velocity":    0.10,
    "godel_selection_rate": 0.10,
}
NEUTRAL_AXIS = 50.0        # returned when insufficient data for an axis
LATENCY_TARGET_MS = 10000  # latency_score falls to 0 at this budget
EMA_ALPHA = 0.1            # matches agents/core/model_scorer.py convention
CAMPAIGNS_WINDOW = 50      # "last N campaigns"
TRACE_WINDOW = 200         # "last N process events"
SESSIONS_WINDOW = 50       # "last N boardroom sessions"
BELIEFS_WINDOW_HOURS = 24
REPUTATION_WINDOW_DAYS = 7


@dataclass
class FitnessResult:
    agent_id: str
    fitness: float                    # 0-100 scalar
    axes: Dict[str, float]            # each axis 0-100
    rank: Optional[int] = None        # 1-based leaderboard rank
    group: str = ""
    eth_address: Optional[str] = None
    tier: int = 0                     # verification_tier
    trend_7d: float = 0.0             # delta vs snapshot 7 days ago
    computed_at: float = 0.0


@dataclass
class ImprovementSummary:
    campaigns_1h:  Dict[str, int] = field(default_factory=dict)
    campaigns_24h: Dict[str, int] = field(default_factory=dict)
    campaigns_7d:  Dict[str, int] = field(default_factory=dict)
    belief_churn_per_hour: float = 0.0
    model_quality_trend: Dict[str, Any] = field(default_factory=dict)
    directive_coverage: Dict[str, Any] = field(default_factory=dict)
    computed_at: float = 0.0


def _load_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as e:
        logger.debug(f"[insight] could not read {path}: {e}")
        return None


def _load_jsonl(path: Path, tail: Optional[int] = None) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        raw = path.read_text().strip()
        if not raw:
            return []
        lines = raw.split("\n")
        if tail is not None and len(lines) > tail:
            lines = lines[-tail:]
        out: List[Dict[str, Any]] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out
    except Exception as e:
        logger.debug(f"[insight] could not read jsonl {path}: {e}")
        return []


def _iso_to_ts(s: Any) -> Optional[float]:
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    if not isinstance(s, str):
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


class InsightAggregator:
    """
    Singleton async aggregator. Call `start()` once from app startup; call
    `snapshot()` / `improvement_summary()` from request handlers.
    """
    _instance: Optional["InsightAggregator"] = None

    def __init__(self):
        self._cache_fitness: List[FitnessResult] = []
        self._cache_improvement: Optional[ImprovementSummary] = None
        self._lock = asyncio.Lock()
        self._task: Optional[asyncio.Task] = None
        self._last_daily_snapshot: float = 0.0
        self.interval_s = 60
        FITNESS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_instance(cls) -> "InsightAggregator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ─── Lifecycle ─────────────────────────────────────────────────────────
    async def start(self):
        if self._task and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())
        logger.info("[insight] aggregator loop started (interval=%ss)", self.interval_s)

    async def stop(self):
        if self._task:
            self._task.cancel()

    async def _loop(self):
        # First tick immediately so the API has data on first request.
        try:
            await self.recompute()
        except Exception as e:
            logger.warning(f"[insight] initial recompute failed: {e}")
        while True:
            try:
                await asyncio.sleep(self.interval_s)
                await self.recompute()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"[insight] loop iteration failed: {e}")

    # ─── Public cached accessors ───────────────────────────────────────────
    def snapshot(self) -> List[Dict[str, Any]]:
        return [asdict(r) for r in self._cache_fitness]

    def improvement_summary(self) -> Dict[str, Any]:
        if self._cache_improvement is None:
            return {
                "campaigns_1h": {},
                "campaigns_24h": {},
                "campaigns_7d": {},
                "belief_churn_per_hour": 0.0,
                "model_quality_trend": {},
                "directive_coverage": {},
                "computed_at": 0.0,
                "status": "warming_up",
            }
        return asdict(self._cache_improvement)

    def fitness_for(self, agent_id: str) -> Optional[Dict[str, Any]]:
        for r in self._cache_fitness:
            if r.agent_id == agent_id:
                return asdict(r)
        return None

    # ─── Recompute ─────────────────────────────────────────────────────────
    async def recompute(self):
        async with self._lock:
            agents = self._list_agents()
            now = time.time()

            # Shared raw datasets (loaded once per recompute)
            campaigns      = _load_json(CAMPAIGNS_FILE) or []
            dojo_events    = _load_jsonl(DOJO_EVENTS_FILE)
            boardroom      = _load_jsonl(BOARDROOM_SESSIONS, tail=SESSIONS_WINDOW)
            godel          = _load_jsonl(GODEL_CHOICES, tail=5000)
            beliefs        = _load_json(BELIEFS_FILE) or {}

            results: List[FitnessResult] = []
            for (agent_id, meta) in agents:
                axes = self._compute_axes(
                    agent_id, meta, campaigns, dojo_events, boardroom, godel, beliefs, now
                )
                fitness = round(
                    sum(axes[k] * FITNESS_WEIGHTS[k] for k in FITNESS_WEIGHTS), 1
                )
                results.append(FitnessResult(
                    agent_id=agent_id,
                    fitness=fitness,
                    axes={k: round(v, 1) for k, v in axes.items()},
                    group=meta.get("group", ""),
                    eth_address=meta.get("eth_address"),
                    tier=int(meta.get("verification_tier", 0) or 0),
                    computed_at=now,
                ))

            results.sort(key=lambda r: r.fitness, reverse=True)
            for i, r in enumerate(results, start=1):
                r.rank = i
                r.trend_7d = self._trend_vs_snapshot(r.agent_id, r.fitness)

            self._cache_fitness = results

            # System-level improvement metrics.
            self._cache_improvement = self._compute_improvement_summary(
                campaigns, beliefs, now
            )

            # Persist current + (once/day) a daily snapshot for trend math.
            self._persist_current(results, self._cache_improvement)
            if now - self._last_daily_snapshot > 86400:
                self._persist_daily_snapshot(results, now)
                self._last_daily_snapshot = now

    # ─── Agent enumeration ─────────────────────────────────────────────────
    def _list_agents(self) -> List[Tuple[str, Dict[str, Any]]]:
        data = _load_json(AGENT_MAP_FILE) or {}
        agents = data.get("agents") or {}
        # Sort for deterministic output
        return sorted(agents.items())

    # ─── Axes ──────────────────────────────────────────────────────────────
    def _compute_axes(
        self,
        agent_id: str,
        meta: Dict[str, Any],
        campaigns: List[Dict[str, Any]],
        dojo_events: List[Dict[str, Any]],
        boardroom: List[Dict[str, Any]],
        godel: List[Dict[str, Any]],
        beliefs: Dict[str, Any],
        now: float,
    ) -> Dict[str, float]:
        return {
            "campaign_success":     self._axis_campaign_success(agent_id, campaigns),
            "trace_reliability":    self._axis_trace_reliability(agent_id),
            "latency_score":        self._axis_latency_score(agent_id),
            "consensus_alignment":  self._axis_consensus_alignment(agent_id, boardroom),
            "reputation_momentum":  self._axis_reputation_momentum(agent_id, dojo_events, now),
            "learning_velocity":    self._axis_learning_velocity(agent_id, beliefs, now),
            "godel_selection_rate": self._axis_godel_selection(agent_id, godel),
        }

    def _axis_campaign_success(self, agent_id: str, campaigns: List[Dict[str, Any]]) -> float:
        if not campaigns:
            return NEUTRAL_AXIS
        # Credit agent if run_id mentions it, directive mentions it, or final_bdi_message mentions it.
        # Mastermind itself gets credit for every campaign since it drives them.
        credits = []
        for c in campaigns[-CAMPAIGNS_WINDOW:]:
            text_blob = " ".join(
                str(c.get(k, "")) for k in ("run_id", "directive", "final_bdi_message")
            ).lower()
            if agent_id in text_blob or agent_id == "mastermind_prime":
                credits.append(c.get("overall_campaign_status", "").upper())
        if not credits:
            return NEUTRAL_AXIS
        successes = sum(1 for s in credits if s == "SUCCESS")
        return 100.0 * successes / len(credits)

    def _axis_trace_reliability(self, agent_id: str) -> float:
        trace_path = AGENT_WORKSPACES_DIR / agent_id / "process_trace.jsonl"
        events = _load_jsonl(trace_path, tail=TRACE_WINDOW)
        if not events:
            return NEUTRAL_AXIS
        total, success = 0, 0
        for e in events:
            data = e.get("process_data") or {}
            if isinstance(data, dict):
                # Many shapes — look in common places.
                status = data.get("status") or (data.get("result") or {}).get("status")
                ok = data.get("success")
                if ok is True or (isinstance(status, str) and status.lower() in ("success", "completed", "ok", "approved")):
                    success += 1
                    total += 1
                elif ok is False or (isinstance(status, str) and status.lower() in ("failed", "error", "rejected")):
                    total += 1
        if total == 0:
            return NEUTRAL_AXIS
        return 100.0 * success / total

    def _axis_latency_score(self, agent_id: str) -> float:
        trace_path = AGENT_WORKSPACES_DIR / agent_id / "process_trace.jsonl"
        events = _load_jsonl(trace_path, tail=TRACE_WINDOW)
        if not events:
            return NEUTRAL_AXIS
        ema: Optional[float] = None
        for e in events:
            data = e.get("process_data") or {}
            ms = None
            for key in ("duration_ms", "latency_ms", "elapsed_ms"):
                if isinstance(data, dict) and key in data:
                    try:
                        ms = float(data[key])
                        break
                    except Exception:
                        pass
            if ms is None:
                continue
            ema = ms if ema is None else (EMA_ALPHA * ms + (1 - EMA_ALPHA) * ema)
        if ema is None:
            return NEUTRAL_AXIS
        return 100.0 * max(0.0, min(1.0, 1.0 - ema / LATENCY_TARGET_MS))

    def _axis_consensus_alignment(self, agent_id: str, boardroom: List[Dict[str, Any]]) -> float:
        if not boardroom:
            return NEUTRAL_AXIS
        n_votes = 0
        n_aligned = 0
        for session in boardroom:
            outcome = (session.get("outcome") or "").lower()
            # approved outcome -> majority vote was approve; rejected -> reject.
            majority_vote = "approve" if outcome == "approved" else ("reject" if outcome == "rejected" else None)
            if majority_vote is None:
                continue
            for v in session.get("votes") or []:
                if v.get("soldier") != agent_id:
                    continue
                vote = (v.get("vote") or "").lower()
                if vote in ("approve", "reject"):
                    n_votes += 1
                    if vote == majority_vote:
                        n_aligned += 1
        if n_votes == 0:
            return NEUTRAL_AXIS
        return 100.0 * n_aligned / n_votes

    def _axis_reputation_momentum(
        self, agent_id: str, dojo_events: List[Dict[str, Any]], now: float
    ) -> float:
        if not dojo_events:
            return NEUTRAL_AXIS
        cutoff = now - REPUTATION_WINDOW_DAYS * 86400
        total = 0.0
        had_any = False
        for ev in dojo_events:
            if ev.get("agent_id") != agent_id:
                continue
            ts = ev.get("timestamp")
            if isinstance(ts, str):
                ts = _iso_to_ts(ts)
            if ts is None or ts < cutoff:
                continue
            try:
                total += float(ev.get("delta", 0))
                had_any = True
            except Exception:
                continue
        if not had_any:
            return NEUTRAL_AXIS
        # Rescale: ±500 over 7 days → 0..100, neutral 50.
        return max(0.0, min(100.0, 50.0 + (total / 500.0) * 50.0))

    def _axis_learning_velocity(
        self, agent_id: str, beliefs: Dict[str, Any], now: float
    ) -> float:
        if not beliefs:
            return NEUTRAL_AXIS
        cutoff = now - BELIEFS_WINDOW_HOURS * 3600
        count = 0
        had_any = False
        for key, record in beliefs.items():
            if not isinstance(record, dict):
                continue
            source = str(record.get("source", ""))
            # Attribute a belief to an agent when its key contains the agent id
            # or the source mentions it. Broad but defensible given current shape.
            if agent_id not in key and agent_id not in source:
                continue
            had_any = True
            ts = record.get("last_updated") or record.get("timestamp")
            if isinstance(ts, (int, float)) and ts >= cutoff:
                count += 1
        if not had_any:
            return NEUTRAL_AXIS
        # log-scale: 0 → 0, 1 → 33, 10 → 66, 100+ → 100
        return max(0.0, min(100.0, 33.3 * math.log10(1 + count)))

    def _axis_godel_selection(self, agent_id: str, godel: List[Dict[str, Any]]) -> float:
        if not godel:
            return NEUTRAL_AXIS
        considered = 0
        chosen = 0
        for ev in godel:
            opts = ev.get("options_considered") or []
            if agent_id in opts:
                considered += 1
                if ev.get("chosen_option") == agent_id:
                    chosen += 1
        if considered == 0:
            return NEUTRAL_AXIS
        return 100.0 * chosen / considered

    # ─── Improvement summary ───────────────────────────────────────────────
    def _compute_improvement_summary(
        self, campaigns: List[Dict[str, Any]], beliefs: Dict[str, Any], now: float
    ) -> ImprovementSummary:
        summary = ImprovementSummary(computed_at=now)

        # Campaign buckets. The mastermind sets overall_campaign_status to
        # FAILURE_OR_INCOMPLETE for any non-COMPLETED_GOAL_ACHIEVED outcome,
        # collapsing four materially different states into one. The actual
        # outcome lives in final_bdi_message: 'BDI run RUNNING' (max-cycle
        # without crash), 'BDI run FAILED_PLANNING', 'BDI run FAILED_RECOVERY',
        # or '... Cycle Exception:' (errored). Read that message first and
        # only fall back to overall_campaign_status when message is absent.
        def bucket(slice_: List[Dict[str, Any]]) -> Dict[str, int]:
            counts = {"total": len(slice_), "succeeded": 0, "running": 0, "failed": 0, "errored": 0}
            for c in slice_:
                status = str(c.get("overall_campaign_status", "")).upper()
                msg = str(c.get("final_bdi_message", ""))
                msg_upper = msg.upper()
                # Success: explicit COMPLETED_GOAL_ACHIEVED or SUCCESS status.
                if "COMPLETED_GOAL_ACHIEVED" in msg_upper or status == "SUCCESS":
                    counts["succeeded"] += 1
                # Errored: BDI cycle hit an unhandled exception (NoneType, etc.)
                elif "CYCLE EXCEPTION" in msg_upper:
                    counts["errored"] += 1
                # Failed: explicit FAILED_PLANNING / FAILED_EXECUTION / FAILED_RECOVERY / FAILED.
                elif "FAILED" in msg_upper:
                    counts["failed"] += 1
                # Running/maxed: the BDI loop ran out of cycles cleanly. NOT a
                # crash — semantically distinct from the FAILED states above.
                elif "RUNNING" in msg_upper or status in ("IN_PROGRESS", "RUNNING"):
                    counts["running"] += 1
                else:
                    # Truly unknown — fall back to FAILURE_OR_INCOMPLETE bucket.
                    counts["failed"] += 1
            return counts

        summary.campaigns_1h  = bucket(campaigns[-5:])
        summary.campaigns_24h = bucket(campaigns[-25:])
        summary.campaigns_7d  = bucket(campaigns[-100:])

        # Belief churn per hour — uses last_updated timestamps.
        cutoff = now - 3600
        recent = 0
        for rec in beliefs.values():
            if not isinstance(rec, dict):
                continue
            ts = rec.get("last_updated") or rec.get("timestamp")
            if isinstance(ts, (int, float)) and ts >= cutoff:
                recent += 1
        summary.belief_churn_per_hour = float(recent)

        # Model quality trend — load the metrics file if present.
        metrics = _load_json(MODEL_METRICS_FILE)
        if isinstance(metrics, dict):
            out = {}
            for model, info in metrics.items():
                if not isinstance(info, dict):
                    continue
                out[model] = {
                    "success_rate":    info.get("success_rate"),
                    "avg_latency_ms":  info.get("avg_latency_ms"),
                    "avg_quality":     info.get("avg_response_quality") or info.get("avg_code_quality"),
                    "last_used":       info.get("last_used"),
                }
            summary.model_quality_trend = out

        # Directive coverage. The previous logic counted backlog entries whose
        # suggestion was a substring of any attempted directive — broken when
        # the mastermind uses a constant fallback directive across all campaigns
        # (production reality: every campaign's directive is "Implement the top
        # improvement suggestion."). Surface multiple honest measures so the
        # operator can read what's actually happening:
        #   - backlog_total: how many improvement suggestions exist on disk
        #   - distinct_directives: how many unique directive strings have ever
        #     been attempted (1 today — exposes the constant-directive bug)
        #   - total_campaigns: total campaigns ever run
        #   - matched_in_backlog: legacy substring-match count (kept for back-compat)
        #   - coverage_ratio: distinct_directives / backlog_total
        backlog_file = PROJECT_ROOT / "data" / "improvement_backlog.json"
        backlog = _load_json(backlog_file) or []
        if isinstance(backlog, list):
            attempted_directives = set()
            for c in campaigns:
                d = (c.get("directive") or "").strip().lower()
                if d:
                    attempted_directives.add(d)
            backlog_count = len(backlog)
            distinct = len(attempted_directives)
            matched_in_backlog = 0
            for entry in backlog:
                s = (entry.get("suggestion") or "").strip().lower()
                if s and any(s in d for d in attempted_directives):
                    matched_in_backlog += 1
            summary.directive_coverage = {
                "backlog_total": backlog_count,
                "distinct_directives_attempted": distinct,
                "total_campaigns": len(campaigns),
                "matched_in_backlog": matched_in_backlog,
                # Back-compat field — older clients (dashboard.html) read this name.
                "attempted": distinct,
                "coverage_ratio": round(distinct / backlog_count, 4) if backlog_count else 0.0,
            }

        return summary

    # ─── Snapshot persistence ──────────────────────────────────────────────
    def _persist_current(self, results: List[FitnessResult], improvement: ImprovementSummary):
        try:
            FITNESS_DIR.mkdir(parents=True, exist_ok=True)
            payload = {
                "computed_at": time.time(),
                "fitness": [asdict(r) for r in results],
                "improvement": asdict(improvement),
            }
            CURRENT_SNAPSHOT_FILE.write_text(json.dumps(payload, indent=2, default=str))
        except Exception as e:
            logger.debug(f"[insight] persist_current failed: {e}")

    def _persist_daily_snapshot(self, results: List[FitnessResult], now: float):
        try:
            FITNESS_DIR.mkdir(parents=True, exist_ok=True)
            line = json.dumps({
                "timestamp": now,
                "agents": {r.agent_id: r.fitness for r in results},
            }, default=str)
            with DAILY_SNAPSHOTS_FILE.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception as e:
            logger.debug(f"[insight] daily snapshot failed: {e}")

    def _trend_vs_snapshot(self, agent_id: str, current: float) -> float:
        if not DAILY_SNAPSHOTS_FILE.exists():
            return 0.0
        try:
            cutoff = time.time() - 7 * 86400
            match: Optional[float] = None
            for line in DAILY_SNAPSHOTS_FILE.read_text().strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                ts = entry.get("timestamp", 0)
                if ts >= cutoff and agent_id in (entry.get("agents") or {}):
                    match = float(entry["agents"][agent_id])
                    break
            return round(current - match, 1) if match is not None else 0.0
        except Exception:
            return 0.0

    # ─── Trajectory (per-agent history) ────────────────────────────────────
    def trajectory(self, agent_id: str, window_days: int = 7) -> List[Dict[str, Any]]:
        if not DAILY_SNAPSHOTS_FILE.exists():
            return []
        out: List[Dict[str, Any]] = []
        cutoff = time.time() - window_days * 86400
        try:
            for line in DAILY_SNAPSHOTS_FILE.read_text().strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                entry = json.loads(line)
                ts = entry.get("timestamp", 0)
                if ts < cutoff:
                    continue
                agents = entry.get("agents") or {}
                if agent_id in agents:
                    out.append({"timestamp": ts, "fitness": agents[agent_id]})
        except Exception as e:
            logger.debug(f"[insight] trajectory failed: {e}")
        return out


def get_instance() -> InsightAggregator:
    return InsightAggregator.get_instance()
