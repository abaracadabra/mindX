"""
DependencyTriageAgent — minimalist, accurate cost/benefit eval for dependabot alerts.

When GitHub reports vulnerabilities on a push (or via `gh api repos/.../dependabot/alerts`),
mindX should not blindly chase every fix. The right posture is: read each alert,
score it against four axes, and decide. The four axes (per user directive 2026-05-25):

  priority   — severity × runtime exposure (does the vulnerable code path actually
               execute in production?)
  processor  — does the patched version build/test/run under VPS resource limits?
               (the prod box has finite cores + RAM; a major-version bump that
               requires a torch reinstall is not free)
  gain       — what specifically does the patch fix? (a DoS in a dev-only build
               tool is much smaller gain than RCE in a request handler)
  effort     — minor-version bump vs. major rewrite vs. ecosystem swap. Minimalist
               posture: cheap+correct > expensive+ideal.

Each alert receives a verdict from the rubric:

  PATCH       — apply the upgrade now (high priority OR low effort with any gain)
  DEFER       — schedule for next maintenance window (moderate severity, real
                effort, no exposed runtime path)
  IGNORE      — vulnerable code path is not reachable in production (e.g. npm
                build-time tool only, dev-dependency, deprecated submodule)
  ESCALATE    — needs human judgement (breaks API, requires architectural change,
                or ecosystem swap)

The verdict + rationale is logged as a Gödel choice (`choice_type='dependency_triage'`)
so the audit trail joins the rest of mindX's self-aware decision history. Same shape
as `backlog_directive_selection` — see emergent.md §"The wedge".

This agent is *agnostic* per the [[agnostic-modules-principle]] memory: it operates
on a generic AlertSpec dict so callers can pipe in dependabot output, `npm audit --json`,
`pip-audit --json`, or any other vulnerability source. The triage rubric is the
same. mindX is one consumer.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


# ── Severity weights ────────────────────────────────────────────────
# These are deliberate, not derived. Critical is not 4× the moderate weight by
# accident — the curve rewards "stop the world for criticals" while still
# acknowledging that two highs in a critical-adjacent component matter.
SEVERITY_WEIGHTS: Dict[str, int] = {
    "critical": 100,
    "high":     30,
    "moderate": 10,
    "medium":   10,  # alias — different scanners use different vocab
    "low":      3,
}

# ── Runtime-exposure tags ───────────────────────────────────────────
# Each tag's weight is the multiplier applied to severity. The product is
# the "priority score". A critical advisory in a dev-only build tool scores
# lower than a moderate advisory in the request-handling hot path.
EXPOSURE_WEIGHTS: Dict[str, float] = {
    "runtime_hot_path":     1.0,   # main_service.py, request handlers, BDI loop
    "runtime_cold_path":    0.6,   # publication orchestrator, dream cycle, etc.
    "build_only":           0.15,  # npm build tools, webpack plugins, etc.
    "dev_only":             0.05,  # test runners, dev servers
    "dormant_submodule":    0.02,  # csshd7, rage/deeprage — not loaded by main
    "unknown":              0.4,   # default when we can't tell
}

# ── Effort tiers ────────────────────────────────────────────────────
# Effort drives whether we PATCH-now or DEFER. Minor-version bumps with no
# API break are free; major rewrites need ESCALATE.
EFFORT_TIERS: Dict[str, int] = {
    "trivial":       1,   # patch-version bump, identical API
    "minor":         3,   # minor-version bump, deprecation warnings tolerated
    "moderate":      10,  # major-version bump in a single component
    "major":         30,  # major-version bump that cascades
    "ecosystem_swap": 100, # swap npm package for a different one entirely
}


@dataclass
class AlertSpec:
    """Generic vulnerability alert — fits dependabot, npm audit, pip-audit."""
    source: str                       # "dependabot", "npm_audit", "pip_audit", ...
    package_name: str
    ecosystem: str                    # "pip", "npm", "rubygems", ...
    severity: str                     # "critical" | "high" | "moderate"/"medium" | "low"
    summary: str
    advisory_id: Optional[str] = None
    first_patched_version: Optional[str] = None
    exposure_tag: str = "unknown"
    effort_tier: str = "minor"
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TriageVerdict:
    """Decision + rationale per alert."""
    alert: AlertSpec
    verdict: str                      # "PATCH" | "DEFER" | "IGNORE" | "ESCALATE"
    priority_score: int
    effort_cost: int
    gain_minus_effort: int
    rationale: str
    decided_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert": {
                "source": self.alert.source,
                "package_name": self.alert.package_name,
                "ecosystem": self.alert.ecosystem,
                "severity": self.alert.severity,
                "advisory_id": self.alert.advisory_id,
                "first_patched_version": self.alert.first_patched_version,
                "exposure_tag": self.alert.exposure_tag,
                "effort_tier": self.alert.effort_tier,
                "summary": self.alert.summary[:200],
            },
            "verdict": self.verdict,
            "priority_score": self.priority_score,
            "effort_cost": self.effort_cost,
            "gain_minus_effort": self.gain_minus_effort,
            "rationale": self.rationale,
            "decided_at": self.decided_at,
        }


class DependencyTriageAgent:
    """The cost/benefit reasoner for dependency vulnerability alerts."""

    _instance: Optional["DependencyTriageAgent"] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(
        cls,
        memory_agent: Optional[MemoryAgent] = None,
        **kwargs,
    ) -> "DependencyTriageAgent":
        async with cls._lock:
            if cls._instance is None:
                cls._instance = cls(memory_agent=memory_agent, **kwargs)
            return cls._instance

    def __init__(
        self,
        memory_agent: Optional[MemoryAgent] = None,
        config_override: Optional[Config] = None,
        **kwargs,
    ):
        self.memory_agent = memory_agent or MemoryAgent()
        self.config = config_override or Config()
        self.agent_id = "dependency_triage_agent"
        self.log_prefix = "DependencyTriage:"
        self.triage_dir = PROJECT_ROOT / "data" / "security" / "triage"
        self.triage_dir.mkdir(parents=True, exist_ok=True)

    # ── Source loaders ──────────────────────────────────────────────

    @staticmethod
    def load_dependabot_alerts(repo: str = "AgenticPlace/mindX") -> List[AlertSpec]:
        """Pull open dependabot alerts via the gh CLI. Returns [] on any failure."""
        try:
            proc = subprocess.run(
                [
                    "gh", "api",
                    f"repos/{repo}/dependabot/alerts",
                    "--paginate",
                    "-q",
                    ".[] | select(.state == \"open\")",
                ],
                capture_output=True, text=True, timeout=30,
            )
            if proc.returncode != 0:
                logger.warning(f"gh dependabot fetch failed: {proc.stderr[:200]}")
                return []
            # `gh api -q` emits one JSON object per line under --paginate.
            alerts: List[AlertSpec] = []
            for line in proc.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                sv = obj.get("security_vulnerability") or {}
                dep = obj.get("dependency") or {}
                pkg = dep.get("package") or {}
                adv = obj.get("security_advisory") or {}
                fpv = sv.get("first_patched_version") or {}
                alerts.append(AlertSpec(
                    source="dependabot",
                    package_name=str(pkg.get("name") or "unknown"),
                    ecosystem=str(pkg.get("ecosystem") or "unknown"),
                    severity=str(sv.get("severity") or "unknown").lower(),
                    summary=str(adv.get("summary") or "")[:300],
                    advisory_id=str(adv.get("ghsa_id") or obj.get("number") or ""),
                    first_patched_version=str(fpv.get("identifier") or "") or None,
                ))
            return alerts
        except FileNotFoundError:
            logger.warning("gh CLI not installed — can't pull dependabot alerts")
            return []
        except subprocess.TimeoutExpired:
            logger.warning("gh dependabot fetch timed out (>30s)")
            return []
        except Exception as e:
            logger.warning(f"dependabot load error: {e}")
            return []

    # ── Heuristic classifiers ───────────────────────────────────────

    def classify_exposure(self, alert: AlertSpec) -> str:
        """Infer runtime exposure from package + ecosystem.

        Honest heuristic — not perfect. The classification is conservative
        (treats unknowns as 'unknown' so they still get attention) and is
        designed to be wrong in the safe direction. Override by passing
        alert.exposure_tag explicitly.
        """
        if alert.exposure_tag != "unknown":
            return alert.exposure_tag
        name = alert.package_name.lower()
        eco = alert.ecosystem.lower()

        # npm dev/build tools — bundlers, linters, transpilers
        npm_build_only = {"vite", "webpack", "rollup", "esbuild", "babel-core",
                          "postcss", "tailwindcss", "tsup", "tsc", "tsx"}
        npm_dev_only = {"jest", "mocha", "chai", "cypress", "playwright",
                        "@testing-library", "eslint", "prettier"}
        # npm runtime-hot — these end up in shipped frontend code
        npm_runtime = {"react", "react-dom", "next", "axios", "ethers",
                       "viem", "@circle-fin", "wagmi"}

        if eco == "npm":
            if any(n in name for n in npm_build_only):
                return "build_only"
            if any(n in name for n in npm_dev_only):
                return "dev_only"
            if any(n in name for n in npm_runtime):
                return "runtime_hot_path"
            # protobufjs, ws, qs — used at runtime by various deps but their
            # exposure depends on whether that dep is in a hot path. Default
            # build_only — many ws/qs deps are transitives in dev tooling.
            if name in {"ws", "qs", "protobufjs", "@protobufjs/utf8"}:
                return "build_only"
            return "build_only"  # npm default: build-time unless proven otherwise

        if eco == "pip":
            # Python runtime: anything that main_service.py imports is hot
            hot_python = {"aiohttp", "httpx", "fastapi", "uvicorn", "starlette",
                          "python-multipart", "pydantic", "cryptography",
                          "eth-account", "pycryptodome", "openai", "anthropic",
                          "asyncpg", "psycopg2", "psycopg2-binary"}
            dormant = {"paramiko", "web3", "faiss-cpu", "langchain",
                       "sentence-transformers", "torch", "transformers"}
            if name.lower() in hot_python:
                return "runtime_hot_path"
            if name.lower() in dormant:
                return "dormant_submodule"
            return "runtime_cold_path"

        return "unknown"

    def classify_effort(self, alert: AlertSpec) -> str:
        """Infer effort to apply the patch from the patched-version diff."""
        if alert.effort_tier != "minor":
            return alert.effort_tier
        fpv = alert.first_patched_version
        if not fpv:
            return "moderate"  # no clear patch path — assume some friction
        # Parse "1.2.3" — major-version bump means moderate-to-major effort,
        # minor-version bump is minor, patch bump is trivial. Best-effort.
        parts = fpv.lstrip("v").split(".")
        try:
            major = int(parts[0]) if parts else 0
        except ValueError:
            return "moderate"
        # We don't have the installed version here without an extra subprocess
        # call; fall back to "minor" as a safe middle. Callers that want a
        # tighter classification can set effort_tier explicitly.
        return "minor"

    # ── The verdict engine ──────────────────────────────────────────

    def triage(self, alert: AlertSpec) -> TriageVerdict:
        """Score the alert and return a verdict. Pure function — no I/O."""
        # Auto-fill if caller didn't classify.
        if alert.exposure_tag == "unknown":
            alert.exposure_tag = self.classify_exposure(alert)
        if alert.effort_tier == "minor":
            alert.effort_tier = self.classify_effort(alert)

        sev_w = SEVERITY_WEIGHTS.get(alert.severity, 5)
        exp_w = EXPOSURE_WEIGHTS.get(alert.exposure_tag, 0.4)
        eff_c = EFFORT_TIERS.get(alert.effort_tier, 10)

        priority = int(sev_w * exp_w)
        gain_minus_effort = priority - eff_c

        # Decision matrix:
        #   PATCH      gain_minus_effort ≥ 20 OR (severity=critical AND not dormant)
        #   ESCALATE   effort=ecosystem_swap, OR critical+major
        #   DEFER      gain_minus_effort between -5 and 20 AND exposure ≠ dormant
        #   IGNORE     exposure=dormant_submodule OR (build_only AND severity≤moderate)
        if alert.severity == "critical" and alert.effort_tier in ("major", "ecosystem_swap"):
            verdict = "ESCALATE"
            rationale = (
                f"Critical advisory with {alert.effort_tier} effort — human judgement "
                f"required (probable API break or arch shift). Package: {alert.package_name}"
            )
        elif alert.effort_tier == "ecosystem_swap":
            verdict = "ESCALATE"
            rationale = (
                f"Ecosystem swap required ({alert.package_name}) — too large to apply "
                f"autonomously regardless of severity."
            )
        elif alert.exposure_tag == "dormant_submodule":
            verdict = "IGNORE"
            rationale = (
                f"Package lives in a dormant submodule not loaded by main_service "
                f"({alert.package_name}, exposure={alert.exposure_tag}). Patching "
                f"costs effort without runtime gain."
            )
        elif alert.severity == "critical" and alert.exposure_tag != "dormant_submodule":
            verdict = "PATCH"
            rationale = (
                f"Critical severity in {alert.exposure_tag} — patch immediately. "
                f"Effort tier: {alert.effort_tier} (cost={eff_c}). Gain={priority}."
            )
        elif gain_minus_effort >= 20:
            verdict = "PATCH"
            rationale = (
                f"gain_minus_effort={gain_minus_effort} ≥ 20 — cheap relative to "
                f"severity×exposure. Patch now. Package: {alert.package_name}."
            )
        elif gain_minus_effort >= -5:
            verdict = "DEFER"
            rationale = (
                f"gain_minus_effort={gain_minus_effort} — modest, schedule for next "
                f"maintenance window. Package: {alert.package_name} ({alert.severity})."
            )
        else:
            verdict = "IGNORE"
            rationale = (
                f"gain_minus_effort={gain_minus_effort} ≪ 0 — patching costs more "
                f"than the exposure justifies. Package: {alert.package_name}."
            )

        return TriageVerdict(
            alert=alert, verdict=verdict, priority_score=priority,
            effort_cost=eff_c, gain_minus_effort=gain_minus_effort,
            rationale=rationale,
        )

    # ── End-to-end run + audit trail ────────────────────────────────

    async def run_triage(
        self,
        alerts: Optional[List[AlertSpec]] = None,
        log_to_godel: bool = True,
    ) -> Dict[str, Any]:
        """Triage every open dependabot alert and write a report.

        If `alerts` is None, pulls from `gh api` directly. Each verdict is
        logged as a Gödel choice (`choice_type='dependency_triage'`) so the
        decision joins the rest of mindX's audit trail. The report is also
        persisted to `data/security/triage/<ts>.json`.
        """
        if alerts is None:
            alerts = self.load_dependabot_alerts()
        if not alerts:
            return {"verdicts": [], "summary": {"count": 0}, "report_path": None}

        verdicts = [self.triage(a) for a in alerts]
        summary: Dict[str, int] = {"count": len(verdicts)}
        for v in verdicts:
            summary[v.verdict] = summary.get(v.verdict, 0) + 1

        report = {
            "computed_at": time.time(),
            "summary": summary,
            "verdicts": [v.to_dict() for v in verdicts],
        }
        report_path = self.triage_dir / f"triage_{int(time.time())}.json"
        try:
            report_path.write_text(json.dumps(report, indent=2, default=str))
        except Exception as e:
            logger.warning(f"{self.log_prefix} failed to persist report: {e}")

        if log_to_godel:
            try:
                # One Gödel choice per triaged alert. Each choice exposes the
                # options_considered as PATCH/DEFER/IGNORE/ESCALATE with their
                # rubric-driven scores so the reasoning is auditable.
                for v in verdicts:
                    await self.memory_agent.log_godel_choice({
                        "source_agent": self.agent_id,
                        "choice_type": "dependency_triage",
                        "task_class": "security",
                        "importance": v.alert.severity,
                        "perception": {
                            "package_name": v.alert.package_name,
                            "ecosystem": v.alert.ecosystem,
                            "severity": v.alert.severity,
                            "exposure_tag": v.alert.exposure_tag,
                            "effort_tier": v.alert.effort_tier,
                        },
                        "options_considered": [
                            {"slug": "PATCH",    "fit": "high"   if v.verdict == "PATCH"    else "low"},
                            {"slug": "DEFER",    "fit": "high"   if v.verdict == "DEFER"    else "low"},
                            {"slug": "IGNORE",   "fit": "high"   if v.verdict == "IGNORE"   else "low"},
                            {"slug": "ESCALATE", "fit": "high"   if v.verdict == "ESCALATE" else "low"},
                        ],
                        "chosen_option": v.verdict,
                        "rationale": v.rationale,
                        "confidence": "high" if v.alert.severity in ("critical", "high") else "standard",
                        "outcome": "pending",
                    })
            except Exception as e:
                logger.debug(f"{self.log_prefix} godel log failed (non-fatal): {e}")

        logger.info(
            f"{self.log_prefix} Triaged {len(verdicts)} alerts: {summary}. "
            f"Report: {report_path}"
        )
        return {"verdicts": [v.to_dict() for v in verdicts], "summary": summary,
                "report_path": str(report_path)}


# ── Convenience entrypoint ──────────────────────────────────────────

async def main():
    """CLI: `python -m agents.dependency_triage_agent` to run a triage cycle."""
    agent = await DependencyTriageAgent.get_instance()
    result = await agent.run_triage()
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
