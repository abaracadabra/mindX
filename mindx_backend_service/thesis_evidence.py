"""
Thesis Evidence Collector — Scientific proof that the Darwin-Godel Machine works.

Collects empirical data from across the system and aggregates it into
structured evidence for the Thesis claims:

  1. Self-improvement: Does the system actually improve over time?
  2. Godel self-reference: Does the improvement mechanism reference itself?
  3. Darwinian selection: Do fitter agents/models get selected?
  4. Resilience: Does the system recover from failures?
  5. Autonomy: Does the system operate without human intervention?

Data sources:
  - data/logs/godel_choices.jsonl       — decision audit trail
  - pgvector actions table              — improvement outcomes (success/fail)
  - /diagnostics/live                   — system metrics snapshots
  - agents/core/model_scorer.py         — model performance evolution
  - data/memory/dreams/                 — pattern extraction from dreaming
  - llm/precision_metrics.py            — token tracking at 18dp
  - data/deployment/vps_state.json      — deployment history

Persistence: data/evidence/thesis_evidence.jsonl (append-only experiment log)
             data/evidence/thesis_metrics.json   (rolling aggregate)

Endpoints:
  GET /thesis/evidence    — structured experiment log (JSON)
  GET /thesis/summary     — human-readable evidence summary

Author: Professor Codephreak
"""

import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import defaultdict

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

EVIDENCE_DIR = PROJECT_ROOT / "data" / "evidence"
EVIDENCE_LOG = EVIDENCE_DIR / "thesis_evidence.jsonl"
METRICS_FILE = EVIDENCE_DIR / "thesis_metrics.json"


@dataclass
class ThesisExperiment:
    """A single experiment record — hypothesis → intervention → measurement → outcome."""
    id: str
    timestamp: float
    cycle: int
    hypothesis: str            # What the system believed would improve
    intervention: str          # What was actually done
    measurement_before: Dict   # Metrics before the intervention
    measurement_after: Dict    # Metrics after the intervention
    outcome: str               # "improved", "degraded", "neutral", "failed"
    delta: Dict                # Quantified change
    agent: str                 # Which agent drove this
    model: str                 # Which model was used
    thesis_claims: List[str]   # Which thesis claims this supports


@dataclass
class ThesisMetrics:
    """Rolling aggregate metrics for thesis evidence."""
    total_cycles: int = 0
    total_improvements_attempted: int = 0
    total_improvements_succeeded: int = 0
    total_improvements_failed: int = 0
    improvement_success_rate: float = 0.0

    total_godel_choices: int = 0
    godel_self_referential: int = 0    # Choices about the choice-making process

    total_actions: int = 0
    actions_completed: int = 0
    actions_failed: int = 0
    action_completion_rate: float = 0.0

    total_memories: int = 0
    memory_growth_rate: float = 0.0    # Memories per hour

    total_dream_cycles: int = 0
    total_insights_extracted: int = 0
    total_patterns_stored: int = 0

    inference_switches: int = 0        # Times the system switched models
    provider_failovers: int = 0        # Times resilience chain activated

    uptime_seconds: int = 0
    autonomous_cycles_without_human: int = 0

    first_evidence_timestamp: float = 0.0
    last_evidence_timestamp: float = 0.0
    evidence_span_hours: float = 0.0

    thesis_verdicts: Dict[str, str] = field(default_factory=dict)


class ThesisEvidenceCollector:
    """
    Collects and aggregates empirical evidence for the Darwin-Godel Machine thesis.
    Singleton — shared across the application.
    """
    _instance: Optional["ThesisEvidenceCollector"] = None

    def __init__(self):
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        self.metrics = ThesisMetrics()
        self._load_metrics()
        self._experiments: List[Dict] = []
        self._load_recent_experiments()

    @classmethod
    def get_instance(cls) -> "ThesisEvidenceCollector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # -----------------------------------------------------------------------
    # Collection: gather evidence from all sources
    # -----------------------------------------------------------------------

    def collect_all(self) -> Dict[str, Any]:
        """Collect evidence from every available source. Returns summary."""
        self._collect_godel_choices()
        self._collect_actions()
        self._collect_dream_reports()
        self._collect_system_metrics()
        self._compute_verdicts()
        self._save_metrics()
        return self.summary()

    def _collect_godel_choices(self):
        """Analyze godel_choices.jsonl for self-referential decision patterns."""
        log_path = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
        if not log_path.exists():
            return

        choices = []
        for line in log_path.read_text().strip().split("\n"):
            if line.strip():
                try:
                    choices.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

        self.metrics.total_godel_choices = len(choices)

        # Count self-referential choices (Godel property)
        self_ref_types = {"mindx_improvement_selection", "mindx_improvement_execution",
                         "ollama_model_selection", "startup_ollama_bootstrap"}
        self.metrics.godel_self_referential = sum(
            1 for c in choices if c.get("choice_type", "") in self_ref_types
        )

        # Count successful improvements
        improvements = [c for c in choices if "improvement" in c.get("choice_type", "")]
        succeeded = [c for c in improvements if c.get("outcome") == "success"]
        self.metrics.total_improvements_attempted = len(improvements)
        self.metrics.total_improvements_succeeded = len(succeeded)
        self.metrics.total_improvements_failed = len(improvements) - len(succeeded)
        if improvements:
            self.metrics.improvement_success_rate = len(succeeded) / len(improvements)

    def _collect_actions(self):
        """Analyze actions from pgvector or diagnostics cache."""
        try:
            import aiohttp
            import asyncio
            # Try to read from local diagnostics cache
            diag_path = PROJECT_ROOT / "data" / "logs" / "diagnostics_cache.json"
            if diag_path.exists():
                data = json.loads(diag_path.read_text())
                actions = data.get("actions", [])
            else:
                actions = []
        except Exception:
            actions = []

        # Also try reading from the last diagnostics/live response
        # (In production, this would query pgvector directly)
        if not actions:
            try:
                import urllib.request
                resp = urllib.request.urlopen("http://localhost:8000/diagnostics/live", timeout=5)
                data = json.loads(resp.read())
                actions = data.get("actions", [])
            except Exception:
                pass

        if actions:
            self.metrics.total_actions = len(actions)
            self.metrics.actions_completed = sum(1 for a in actions if a.get("status") == "completed")
            self.metrics.actions_failed = sum(1 for a in actions if a.get("status") == "failed")
            if self.metrics.total_actions > 0:
                self.metrics.action_completion_rate = self.metrics.actions_completed / self.metrics.total_actions

    def _collect_dream_reports(self):
        """Analyze machine.dreaming outputs."""
        dreams_dir = PROJECT_ROOT / "data" / "memory" / "dreams"
        if not dreams_dir.exists():
            return

        total_insights = 0
        total_patterns = 0
        dream_count = 0

        for f in sorted(dreams_dir.glob("*_dream_report.json")):
            try:
                report = json.loads(f.read_text())
                dream_count += 1
                total_insights += report.get("insights_generated", 0)
                total_patterns += report.get("memories_promoted_to_ltm", 0)
                # Count agent-level pattern extraction
                for agent_data in report.get("agent_reports", {}).values():
                    if isinstance(agent_data, dict):
                        total_patterns += agent_data.get("patterns_extracted", 0)
            except Exception:
                pass

        self.metrics.total_dream_cycles = dream_count
        self.metrics.total_insights_extracted = total_insights
        self.metrics.total_patterns_stored = total_patterns

    def _collect_system_metrics(self):
        """Collect system-level metrics."""
        # Memory count from stm
        stm_dir = PROJECT_ROOT / "data" / "memory" / "stm"
        if stm_dir.exists():
            try:
                total = sum(1 for _ in stm_dir.rglob("*.json"))
                self.metrics.total_memories = total
            except Exception:
                pass

        # Evidence timespan
        log_path = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
        if log_path.exists():
            try:
                lines = log_path.read_text().strip().split("\n")
                if lines:
                    first = json.loads(lines[0])
                    last = json.loads(lines[-1])
                    t1 = first.get("timestamp_utc", "")
                    t2 = last.get("timestamp_utc", "")
                    if t1 and t2:
                        from datetime import datetime
                        dt1 = datetime.fromisoformat(t1.replace("Z", "+00:00"))
                        dt2 = datetime.fromisoformat(t2.replace("Z", "+00:00"))
                        span = (dt2 - dt1).total_seconds()
                        self.metrics.evidence_span_hours = span / 3600
                        self.metrics.first_evidence_timestamp = dt1.timestamp()
                        self.metrics.last_evidence_timestamp = dt2.timestamp()
                        if span > 0:
                            self.metrics.memory_growth_rate = self.metrics.total_memories / (span / 3600)
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # Verdicts: does the evidence support each thesis claim?
    # -----------------------------------------------------------------------

    def _compute_verdicts(self):
        """Evaluate thesis claims against collected evidence."""
        m = self.metrics
        verdicts = {}

        # Claim 1: Self-improvement — system actually improves
        if m.total_improvements_attempted > 0:
            if m.improvement_success_rate > 0.5:
                verdicts["self_improvement"] = f"SUPPORTED — {m.total_improvements_succeeded}/{m.total_improvements_attempted} improvements succeeded ({m.improvement_success_rate:.0%})"
            elif m.improvement_success_rate > 0:
                verdicts["self_improvement"] = f"PARTIAL — {m.total_improvements_succeeded}/{m.total_improvements_attempted} succeeded ({m.improvement_success_rate:.0%}), needs higher rate"
            else:
                verdicts["self_improvement"] = f"NOT SUPPORTED — 0/{m.total_improvements_attempted} succeeded"
        else:
            verdicts["self_improvement"] = "INSUFFICIENT DATA — no improvement cycles recorded"

        # Claim 2: Godel self-reference — improvement mechanism references itself
        if m.godel_self_referential > 0:
            ratio = m.godel_self_referential / max(m.total_godel_choices, 1)
            verdicts["godel_self_reference"] = f"SUPPORTED — {m.godel_self_referential}/{m.total_godel_choices} choices are self-referential ({ratio:.0%})"
        else:
            verdicts["godel_self_reference"] = "INSUFFICIENT DATA — no self-referential choices logged"

        # Claim 3: Darwinian selection — fitter entities survive
        if m.total_actions > 0 and m.action_completion_rate > 0.5:
            verdicts["darwinian_selection"] = f"PARTIAL — {m.action_completion_rate:.0%} action completion rate suggests selection pressure"
        else:
            verdicts["darwinian_selection"] = "INSUFFICIENT DATA — need per-agent fitness tracking"

        # Claim 4: Resilience — system recovers from failures
        if m.total_improvements_failed > 0 and m.total_improvements_succeeded > 0:
            verdicts["resilience"] = f"SUPPORTED — system recovered from {m.total_improvements_failed} failures, continued to achieve {m.total_improvements_succeeded} successes"
        elif m.total_actions > 0:
            verdicts["resilience"] = f"PARTIAL — {m.actions_completed} actions completed, {m.actions_failed} failed, system continued operating"
        else:
            verdicts["resilience"] = "INSUFFICIENT DATA"

        # Claim 5: Autonomy — operates without human intervention
        if m.total_godel_choices > 5:
            verdicts["autonomy"] = f"SUPPORTED — {m.total_godel_choices} autonomous decisions logged across {m.evidence_span_hours:.1f} hours"
        else:
            verdicts["autonomy"] = "INSUFFICIENT DATA — need more autonomous decision cycles"

        # Claim 6: Knowledge accumulation — memories grow and consolidate
        if m.total_memories > 1000:
            verdicts["knowledge_accumulation"] = f"SUPPORTED — {m.total_memories:,} memories, {m.total_dream_cycles} dream cycles, {m.total_patterns_stored} patterns extracted"
        elif m.total_memories > 0:
            verdicts["knowledge_accumulation"] = f"PARTIAL — {m.total_memories:,} memories accumulated, growth rate {m.memory_growth_rate:.0f}/hour"
        else:
            verdicts["knowledge_accumulation"] = "INSUFFICIENT DATA"

        self.metrics.thesis_verdicts = verdicts

    # -----------------------------------------------------------------------
    # Record experiment
    # -----------------------------------------------------------------------

    def record_experiment(self, experiment: ThesisExperiment):
        """Append an experiment to the evidence log."""
        entry = asdict(experiment)
        try:
            with open(EVIDENCE_LOG, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            self._experiments.append(entry)
            if len(self._experiments) > 100:
                self._experiments = self._experiments[-100:]
        except Exception as e:
            logger.debug(f"Failed to record experiment: {e}")

    # -----------------------------------------------------------------------
    # Output: summary and structured evidence
    # -----------------------------------------------------------------------

    def summary(self) -> Dict[str, Any]:
        """Full evidence summary — dashboard section + experiment log."""
        m = self.metrics
        return {
            "thesis": "Darwin-Godel Machine: mindX as practical implementation",
            "source": "docs/THESIS.md",
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evidence_span_hours": round(m.evidence_span_hours, 1),
            "claims": {
                "self_improvement": {
                    "verdict": m.thesis_verdicts.get("self_improvement", "NOT EVALUATED"),
                    "evidence": {
                        "cycles_attempted": m.total_improvements_attempted,
                        "cycles_succeeded": m.total_improvements_succeeded,
                        "cycles_failed": m.total_improvements_failed,
                        "success_rate": round(m.improvement_success_rate, 4),
                    },
                },
                "godel_self_reference": {
                    "verdict": m.thesis_verdicts.get("godel_self_reference", "NOT EVALUATED"),
                    "evidence": {
                        "total_choices": m.total_godel_choices,
                        "self_referential_choices": m.godel_self_referential,
                        "self_reference_ratio": round(m.godel_self_referential / max(m.total_godel_choices, 1), 4),
                    },
                },
                "darwinian_selection": {
                    "verdict": m.thesis_verdicts.get("darwinian_selection", "NOT EVALUATED"),
                    "evidence": {
                        "total_actions": m.total_actions,
                        "actions_completed": m.actions_completed,
                        "actions_failed": m.actions_failed,
                        "completion_rate": round(m.action_completion_rate, 4),
                    },
                },
                "resilience": {
                    "verdict": m.thesis_verdicts.get("resilience", "NOT EVALUATED"),
                    "evidence": {
                        "failures_survived": m.total_improvements_failed,
                        "recoveries": m.total_improvements_succeeded,
                    },
                },
                "autonomy": {
                    "verdict": m.thesis_verdicts.get("autonomy", "NOT EVALUATED"),
                    "evidence": {
                        "autonomous_decisions": m.total_godel_choices,
                        "span_hours": round(m.evidence_span_hours, 1),
                    },
                },
                "knowledge_accumulation": {
                    "verdict": m.thesis_verdicts.get("knowledge_accumulation", "NOT EVALUATED"),
                    "evidence": {
                        "total_memories": m.total_memories,
                        "growth_rate_per_hour": round(m.memory_growth_rate, 1),
                        "dream_cycles": m.total_dream_cycles,
                        "patterns_extracted": m.total_patterns_stored,
                    },
                },
            },
            "aggregate": {
                "total_godel_choices": m.total_godel_choices,
                "total_actions": m.total_actions,
                "total_memories": m.total_memories,
                "total_dream_cycles": m.total_dream_cycles,
                "total_insights": m.total_insights_extracted,
            },
            "recent_experiments": self._experiments[-10:],
        }

    # -----------------------------------------------------------------------
    # Persistence
    # -----------------------------------------------------------------------

    def _save_metrics(self):
        try:
            EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
            data = asdict(self.metrics)
            data["_saved_at"] = time.time()
            METRICS_FILE.write_text(json.dumps(data, indent=2, default=str))
        except Exception as e:
            logger.debug(f"Failed to save thesis metrics: {e}")

    def _load_metrics(self):
        if METRICS_FILE.exists():
            try:
                data = json.loads(METRICS_FILE.read_text())
                for k, v in data.items():
                    if hasattr(self.metrics, k) and not k.startswith("_"):
                        setattr(self.metrics, k, v)
            except Exception:
                pass

    def _load_recent_experiments(self):
        if EVIDENCE_LOG.exists():
            try:
                lines = EVIDENCE_LOG.read_text().strip().split("\n")
                self._experiments = [json.loads(line) for line in lines[-20:] if line.strip()]
            except Exception:
                pass
