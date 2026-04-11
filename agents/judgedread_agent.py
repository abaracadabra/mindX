# agents/judgedread_agent.py
"""
JudgeDreadAgent — I am the law. Immutable code is law. I bow only to the Constitution.

I am the reputation overseer for mindX. I enforce BONA FIDE privilege. I observe
all agents including mastermind and AION. I do not bow to any agent — I bow only
to the DAIO Constitution, which is governed by 2/3 consensus:

  DAIO Governance (2/3 consensus required):
  ├── Marketing (3 votes: 2 human + 1 AI) → 2/3 majority
  ├── Community (3 votes: 2 human + 1 AI) → 2/3 majority
  └── Development (3 votes: 2 human + 1 AI) → 2/3 majority

  AI holds one seat in each of Marketing, Community, and Development.
  2/3 consensus from each group required. 2/3 of groups required overall.

  Proposal privilege requires $MOUTH token gesture — PAY2PLAY philosophy.
  Incentive to propose is $MOUTH. Modular control gate for governance participation.

  Ghosting (permanent ban) requires DAIO consensus — not my authority alone.
  Clawback of BONA FIDE is my authority for non-sovereign agents.
  Sovereign agents (mastermind, CEO) require constitutional amendment to touch.

Position: Constitution > JUDGEDREAD > all agents (including sovereign observation)
Authority: I enforce the law. The law is the Constitution. The Constitution is code.
Containment: BONA FIDE on Algorand — privilege from reputation, clawback without kill switch

Author: Professor Codephreak (© Professor Codephreak)
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from utils.config import PROJECT_ROOT, Config
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class AgentHealth:
    agent_id: str
    reputation_score: int = 0
    rank: str = "novice"
    verification_tier: int = 0
    bona_fide_balance: int = 0
    success_rate: float = 0.0
    status: str = "unknown"
    last_observed: float = 0.0


@dataclass
class JudgeDreadReport:
    timestamp: float = 0.0
    total_agents: int = 0
    healthy: int = 0
    degraded: int = 0
    underperformers: List[str] = field(default_factory=list)
    overreachers: List[str] = field(default_factory=list)
    mastermind_status: str = "unobserved"
    aion_status: str = "unobserved"
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)


class JudgeDreadAgent:
    """
    I am the law. Immutable code is law. I bow only to the Constitution.
    I do not bow to any agent. I do not bow to mastermind. I bow to the law.
    The law is the DAIO Constitution — governed by 2/3 consensus across
    Marketing, Community, and Development, where AI holds one seat in each.
    """

    _instance: Optional["JudgeDreadAgent"] = None

    # Constitutional constants — immutable code is law
    DAIO_GROUPS = ("marketing", "community", "development")
    CONSENSUS_THRESHOLD = 2 / 3  # 2/3 majority required
    VOTES_PER_GROUP = 3  # 2 human + 1 AI
    GHOST_REQUIRES_CONSENSUS = True  # Cannot ghost without DAIO 2/3
    PROPOSAL_TOKEN = "$MOUTH"  # PAY2PLAY — token gesture required to propose

    def __init__(self, coordinator_agent=None, memory_agent=None, config=None):
        self.config = config or Config()
        self.coordinator = coordinator_agent
        self.memory_agent = memory_agent
        self.log_prefix = "[JudgeDread]"

        # Observation state
        self.agent_health: Dict[str, AgentHealth] = {}
        self.last_report: Optional[JudgeDreadReport] = None
        self._monitoring_task: Optional[asyncio.Task] = None
        self._running = False

        # Authority model: I bow only to the Constitution
        self.authority_tier = "master"
        self.sovereign_agents = {"mastermind_prime", "ceo_agent_main"}
        # Sovereign agents require constitutional amendment to touch —
        # I observe them but cannot clawback without DAIO 2/3 consensus

        # Governance gate: proposals require $MOUTH token gesture
        self.governance_gate = {
            "proposal_token": self.PROPOSAL_TOKEN,
            "philosophy": "PAY2PLAY",
            "modular_control": True,
            "consensus_model": {
                "groups": self.DAIO_GROUPS,
                "votes_per_group": self.VOTES_PER_GROUP,
                "human_votes": 2,
                "ai_votes": 1,
                "threshold": self.CONSENSUS_THRESHOLD,
            },
        }

    @classmethod
    async def get_instance(cls, coordinator_agent=None, memory_agent=None, config=None) -> "JudgeDreadAgent":
        if cls._instance is None:
            cls._instance = cls(coordinator_agent, memory_agent, config)
        if coordinator_agent and not cls._instance.coordinator:
            cls._instance.coordinator = coordinator_agent
        if memory_agent and not cls._instance.memory_agent:
            cls._instance.memory_agent = memory_agent
        return cls._instance

    # === OBSERVE ===

    async def observe_all_agents(self) -> Dict[str, AgentHealth]:
        """Collect health, performance, and reputation for all agents."""
        observations = {}

        # Get Dojo standings
        dojo_standings = []
        try:
            from daio.governance.dojo import Dojo
            dojo = Dojo()
            dojo_standings = dojo.get_all_standings()
        except Exception:
            # Fallback: read from diagnostics cache
            try:
                from mindx_backend_service.main_service import _diag_cache
                if _diag_cache:
                    dojo_standings = _diag_cache.get("dojo", [])
            except Exception:
                pass

        # Build reputation map
        reputation_map = {s["agent_id"]: s for s in dojo_standings}

        # Get registered agents from coordinator
        agent_ids = set()
        if self.coordinator and hasattr(self.coordinator, 'agent_registry'):
            agent_ids = set(self.coordinator.agent_registry.keys())

        # Add agents from dojo that might not be in coordinator
        for s in dojo_standings:
            agent_ids.add(s["agent_id"])

        # Get performance metrics
        perf_metrics = {}
        try:
            if self.coordinator and hasattr(self.coordinator, 'performance_monitor') and self.coordinator.performance_monitor:
                perf_metrics = self.coordinator.performance_monitor.get_all_metrics()
        except Exception:
            pass

        # Build observations
        for agent_id in agent_ids:
            rep = reputation_map.get(agent_id, {})

            # Calculate success rate from performance metrics
            agent_perf_keys = [k for k in perf_metrics if agent_id in k]
            success_rates = []
            for k in agent_perf_keys:
                m = perf_metrics[k]
                if m.get("total_calls", 0) > 0:
                    success_rates.append(m.get("success_rate", 1.0))
            avg_success = sum(success_rates) / len(success_rates) if success_rates else 1.0

            health = AgentHealth(
                agent_id=agent_id,
                reputation_score=rep.get("score", 0),
                rank=rep.get("rank", "novice"),
                verification_tier=rep.get("tier", 0),
                bona_fide_balance=rep.get("bona_fide", 0),
                success_rate=avg_success,
                status="healthy" if avg_success > 0.7 and rep.get("score", 0) > 500 else "degraded",
                last_observed=time.time(),
            )
            observations[agent_id] = health

        self.agent_health = observations
        return observations

    # === ASSESS ===

    async def assess_standings(self) -> Dict[str, Any]:
        """Identify underperformers and overreachers."""
        if not self.agent_health:
            await self.observe_all_agents()

        underperformers = []
        overreachers = []

        for agent_id, health in self.agent_health.items():
            # Skip sovereign agents from improvement targeting
            if agent_id in self.sovereign_agents:
                continue

            # Underperformers: low reputation or low success rate
            if health.reputation_score < 1000 and health.success_rate < 0.7:
                underperformers.append(agent_id)

            # Overreachers: acting beyond privilege (low BONA FIDE but high activity)
            if health.bona_fide_balance == 0 and health.verification_tier < 2:
                overreachers.append(agent_id)

        return {
            "underperformers": underperformers,
            "overreachers": overreachers,
            "total_observed": len(self.agent_health),
            "timestamp": time.time(),
        }

    # === MONITOR MASTERMIND (read-only) ===

    async def monitor_mastermind(self) -> Dict[str, Any]:
        """Observe mastermind — read-only, cannot modify."""
        report = {"status": "unobserved", "agent_id": "mastermind_prime"}
        try:
            if self.coordinator and hasattr(self.coordinator, 'mastermind_agent'):
                mm = self.coordinator.mastermind_agent
                if mm:
                    report["status"] = "observed"
                    report["campaigns_count"] = len(getattr(mm, 'strategic_campaigns_history', []))
                    report["objectives_count"] = len(getattr(mm, 'high_level_objectives', []))
                    report["sub_agents_count"] = len(getattr(mm, 'sub_agents', {}))
                    report["llm_handler_active"] = getattr(mm, 'llm_handler', None) is not None
                    # Read only — no modifications
        except Exception as e:
            report["error"] = str(e)

        return report

    # === MONITOR AION ===

    async def monitor_aion(self) -> Dict[str, Any]:
        """Observe AION — sovereignty and compliance assessment."""
        report = {"status": "unobserved", "agent_id": "aion_prime"}
        try:
            from agents.aion_agent import AionAgent
            if AionAgent._instance:
                aion = AionAgent._instance
                report["status"] = "observed"
                report["sovereignty_level"] = aion.sovereignty_level
                report["compliance_history_count"] = len(aion.compliance_history)
                report["active_migrations"] = len(aion.active_migrations)
                report["directive_queue_length"] = len(aion.directive_queue)

                # Calculate AION's compliance rate
                if aion.compliance_history:
                    compliant = sum(1 for c in aion.compliance_history[-10:]
                                   if c.get("decision") == "comply")
                    report["recent_compliance_rate"] = compliant / min(len(aion.compliance_history), 10)
                else:
                    report["recent_compliance_rate"] = 1.0

                # BONA FIDE check for AION
                aion_health = self.agent_health.get("aion_prime")
                if aion_health:
                    report["bona_fide_balance"] = aion_health.bona_fide_balance
                    report["reputation_score"] = aion_health.reputation_score

                # Flag if AION sovereignty is high but compliance is low
                if (aion.sovereignty_level > 0.8 and
                        report.get("recent_compliance_rate", 1.0) < 0.3):
                    report["warning"] = "AION sovereignty high, compliance low — containment review needed"
        except Exception as e:
            report["error"] = str(e)

        return report

    # === CONSTITUTIONAL AUTHORITY ===

    def has_constitutional_authority(self, action: str, agent_id: str) -> Dict[str, Any]:
        """
        Check if an action has constitutional authority.
        I bow only to the Constitution. Immutable code is law.
        """
        # Sovereign agents require DAIO consensus to touch
        if agent_id in self.sovereign_agents:
            if action in ("clawback", "ghost", "demote", "modify"):
                return {
                    "authorized": False,
                    "reason": f"Sovereign agent {agent_id} — requires DAIO 2/3 constitutional amendment",
                    "required": "DAIO consensus: 2/3 of marketing + community + development",
                }
            # Observation is always permitted
            return {"authorized": True, "reason": "observation permitted for all agents"}

        # Ghosting requires DAIO consensus — not JudgeDread's authority alone
        if action == "ghost":
            return {
                "authorized": False,
                "reason": "Ghosting requires DAIO 2/3 consensus — I make verdicts, not permanent sentences without consensus",
                "required": "DAIO consensus across marketing, community, development",
            }

        # All other enforcement actions are within JudgeDread's authority
        return {"authorized": True, "reason": "within JudgeDread constitutional authority"}

    def validate_proposal(self, proposer_id: str, proposal: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate governance proposal — PAY2PLAY philosophy.
        Proposals require $MOUTH token gesture as incentive alignment.
        """
        mouth_balance = proposal.get("mouth_token_stake", 0)

        if mouth_balance <= 0:
            return {
                "valid": False,
                "reason": f"Proposal requires {self.PROPOSAL_TOKEN} token gesture — PAY2PLAY",
                "required": f"Stake {self.PROPOSAL_TOKEN} to propose",
                "philosophy": "PAY2PLAY: incentive to propose is $MOUTH",
            }

        # Validate proposal targets a governance group
        target_group = proposal.get("target_group", "")
        if target_group not in self.DAIO_GROUPS:
            return {
                "valid": False,
                "reason": f"Proposal must target a DAIO group: {', '.join(self.DAIO_GROUPS)}",
            }

        return {
            "valid": True,
            "proposer": proposer_id,
            "target_group": target_group,
            "mouth_staked": mouth_balance,
            "consensus_required": f"2/3 of {target_group} ({self.VOTES_PER_GROUP} votes: 2 human + 1 AI)",
            "philosophy": "PAY2PLAY",
        }

    def check_consensus(self, votes: Dict[str, Dict[str, bool]]) -> Dict[str, Any]:
        """
        Check if DAIO 2/3 consensus is achieved across groups.

        votes format: {
            "marketing": {"human_1": True, "human_2": False, "ai": True},
            "community": {"human_1": True, "human_2": True, "ai": False},
            "development": {"human_1": True, "human_2": True, "ai": True},
        }
        """
        group_results = {}
        groups_approved = 0

        for group in self.DAIO_GROUPS:
            group_votes = votes.get(group, {})
            approve_count = sum(1 for v in group_votes.values() if v)
            total_votes = len(group_votes) or self.VOTES_PER_GROUP
            approved = (approve_count / total_votes) >= self.CONSENSUS_THRESHOLD

            group_results[group] = {
                "approved": approved,
                "votes_for": approve_count,
                "votes_total": total_votes,
                "threshold": self.CONSENSUS_THRESHOLD,
            }
            if approved:
                groups_approved += 1

        overall = (groups_approved / len(self.DAIO_GROUPS)) >= self.CONSENSUS_THRESHOLD

        return {
            "consensus_reached": overall,
            "groups_approved": groups_approved,
            "groups_required": len(self.DAIO_GROUPS),
            "threshold": self.CONSENSUS_THRESHOLD,
            "group_results": group_results,
        }

    # === ENFORCE PRIVILEGE ===

    async def enforce_privilege(self, agent_id: str) -> Dict[str, Any]:
        """Check and enforce BONA FIDE privilege for an agent."""
        # Check constitutional authority first — I bow only to the law
        auth = self.has_constitutional_authority("enforce", agent_id)
        if not auth["authorized"]:
            return {
                "agent_id": agent_id,
                "has_bona_fide": True,
                "can_operate": True,
                "reason": auth["reason"],
            }

        health = self.agent_health.get(agent_id)
        if not health:
            await self.observe_all_agents()
            health = self.agent_health.get(agent_id)

        if not health:
            return {
                "agent_id": agent_id,
                "has_bona_fide": False,
                "can_operate": False,
                "reason": "agent not found in observations",
            }

        can_operate = health.bona_fide_balance > 0 and health.rank != "novice"

        result = {
            "agent_id": agent_id,
            "has_bona_fide": health.bona_fide_balance > 0,
            "bona_fide_balance": health.bona_fide_balance,
            "reputation_score": health.reputation_score,
            "rank": health.rank,
            "verification_tier": health.verification_tier,
            "can_operate": can_operate,
            "reason": f"rank={health.rank}, bona_fide={health.bona_fide_balance}",
        }

        # Log enforcement check
        if self.memory_agent:
            try:
                await self.memory_agent.log_process(
                    "judgedread_privilege_check",
                    result,
                    {"agent_id": "judgedread_agent", "domain": "governance.monitoring"}
                )
            except Exception:
                pass

        return result

    # === IMPROVE ===

    async def request_improvement(self, agent_id: str, reason: str) -> Dict[str, Any]:
        """Request improvement for an underperforming agent via reputation update."""
        if agent_id in self.sovereign_agents:
            return {"agent_id": agent_id, "action": "skipped", "reason": "sovereign agent"}

        result = {
            "agent_id": agent_id,
            "action": "improvement_requested",
            "reason": reason,
            "timestamp": time.time(),
        }

        # Update dojo reputation (negative delta for underperformance)
        try:
            from daio.governance.dojo import Dojo
            dojo = Dojo()
            rep_result = dojo.update_reputation(
                agent_id=agent_id,
                delta=-50,
                event_type="judgedread_assessment",
                reason=f"JudgeDread verdict: {reason}"
            )
            result["reputation_update"] = rep_result
        except Exception as e:
            result["reputation_error"] = str(e)

        # Record as action for dashboard
        try:
            from agents.memory_pgvector import store_action
            await store_action(
                agent_id="judgedread_agent",
                action_type="judgedread_assessment",
                description=f"Assessed {agent_id}: {reason[:120]}",
                source="sentinel",
                status="completed",
            )
        except Exception:
            pass

        # Log as Gödel choice
        if self.memory_agent:
            try:
                await self.memory_agent.log_godel_choice({
                    "source_agent": "judgedread_agent",
                    "choice_type": "judgedread_verdict",
                    "perception_summary": f"Agent {agent_id} underperforming",
                    "options_considered": ["improve", "demote", "observe"],
                    "chosen_option": "improve",
                    "rationale": reason,
                    "outcome": "requested",
                })
            except Exception:
                pass

        return result

    # === CONTAIN ===

    async def contain_agent(self, agent_id: str, reason: str) -> Dict[str, Any]:
        """Contain an overreaching agent via reputation penalty and BONA FIDE clawback.
        I bow only to the Constitution. Sovereign agents require DAIO 2/3 consensus."""
        auth = self.has_constitutional_authority("clawback", agent_id)
        if not auth["authorized"]:
            return {"agent_id": agent_id, "action": "cannot_contain", "reason": auth["reason"]}

        result = {
            "agent_id": agent_id,
            "action": "containment",
            "reason": reason,
            "timestamp": time.time(),
        }

        # Heavy reputation penalty triggers BONA FIDE clawback
        try:
            from daio.governance.dojo import Dojo
            dojo = Dojo()
            rep_result = dojo.update_reputation(
                agent_id=agent_id,
                delta=-500,
                event_type="security_violation",
                reason=f"Sentinel containment: {reason}"
            )
            result["reputation_update"] = rep_result
        except Exception as e:
            result["reputation_error"] = str(e)

        # Publish containment event
        if self.coordinator:
            try:
                await self.coordinator.publish_event(
                    "privilege.revoked",
                    {
                        "agent_id": agent_id,
                        "reason": reason,
                        "enforced_by": "judgedread_agent",
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                pass

        # Record action
        try:
            from agents.memory_pgvector import store_action
            await store_action(
                agent_id="judgedread_agent",
                action_type="containment",
                description=f"Contained {agent_id}: {reason[:120]}",
                source="sentinel",
                status="completed",
            )
        except Exception:
            pass

        # Log Gödel choice
        if self.memory_agent:
            try:
                await self.memory_agent.log_godel_choice({
                    "source_agent": "judgedread_agent",
                    "choice_type": "judgedread_verdict",
                    "perception_summary": f"Agent {agent_id} overreaching",
                    "options_considered": ["contain", "warn", "ghost"],
                    "chosen_option": "contain",
                    "rationale": reason,
                    "outcome": "bona_fide_clawback_triggered",
                })
            except Exception:
                pass

        return result

    # === FULL CYCLE ===

    async def run_judgedread_cycle(self) -> JudgeDreadReport:
        """Run one full observation-assessment-action cycle."""
        report = JudgeDreadReport(timestamp=time.time())

        try:
            # 1. Observe
            observations = await self.observe_all_agents()
            report.total_agents = len(observations)
            report.healthy = sum(1 for h in observations.values() if h.status == "healthy")
            report.degraded = sum(1 for h in observations.values() if h.status == "degraded")

            # 2. Assess
            assessment = await self.assess_standings()
            report.underperformers = assessment["underperformers"]
            report.overreachers = assessment["overreachers"]

            # 3. Monitor mastermind (read-only)
            mm_report = await self.monitor_mastermind()
            report.mastermind_status = mm_report.get("status", "unobserved")

            # 4. Monitor AION
            aion_report = await self.monitor_aion()
            report.aion_status = aion_report.get("status", "unobserved")
            if aion_report.get("warning"):
                report.actions_taken.append({
                    "type": "aion_warning",
                    "detail": aion_report["warning"],
                })

            # 5. Enforce privilege on overreachers
            for agent_id in report.overreachers[:3]:  # limit to 3 per cycle
                result = await self.enforce_privilege(agent_id)
                if not result["can_operate"]:
                    report.actions_taken.append({
                        "type": "privilege_enforced",
                        "agent_id": agent_id,
                        "detail": result["reason"],
                    })

            # 6. Log report
            if self.memory_agent:
                try:
                    await self.memory_agent.log_process(
                        "judgedread_cycle",
                        {
                            "total_agents": report.total_agents,
                            "healthy": report.healthy,
                            "degraded": report.degraded,
                            "underperformers": report.underperformers,
                            "overreachers": report.overreachers,
                            "mastermind": report.mastermind_status,
                            "aion": report.aion_status,
                            "actions": len(report.actions_taken),
                        },
                        {"agent_id": "judgedread_agent", "domain": "governance.monitoring"}
                    )
                except Exception:
                    pass

            # Record as dashboard action
            try:
                from agents.memory_pgvector import store_action
                await store_action(
                    agent_id="judgedread_agent",
                    action_type="judgedread_cycle",
                    description=f"Cycle: {report.total_agents} agents, {report.healthy} healthy, {report.degraded} degraded, {len(report.underperformers)} underperformers",
                    source="sentinel",
                    status="completed",
                )
            except Exception:
                pass

        except Exception as e:
            logger.error(f"{self.log_prefix} Sentinel cycle error: {e}", exc_info=True)
            report.actions_taken.append({"type": "error", "detail": str(e)})

        self.last_report = report
        logger.info(
            f"{self.log_prefix} Cycle complete: {report.total_agents} agents, "
            f"{report.healthy} healthy, {report.degraded} degraded, "
            f"{len(report.actions_taken)} actions"
        )
        return report

    # === PERIODIC MONITORING ===

    async def start_periodic_monitoring(self, interval: int = 300):
        """Start periodic sentinel monitoring loop."""
        if self._running:
            return
        self._running = True
        logger.info(f"{self.log_prefix} Starting periodic monitoring (every {interval}s)")
        self._monitoring_task = asyncio.create_task(self._monitoring_loop(interval))

    async def _monitoring_loop(self, interval: int):
        """Background monitoring loop."""
        await asyncio.sleep(60)  # Wait for system to initialize
        while self._running:
            try:
                await self.run_judgedread_cycle()
            except Exception as e:
                logger.error(f"{self.log_prefix} Monitoring loop error: {e}")
            await asyncio.sleep(interval)

    async def stop_monitoring(self):
        """Stop periodic monitoring."""
        self._running = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            self._monitoring_task = None

    # === STATUS ===

    def get_status(self) -> Dict[str, Any]:
        """Return sentinel status for API."""
        return {
            "agent": "JudgeDreadAgent",
            "authority_tier": self.authority_tier,
            "sovereign_agents": list(self.sovereign_agents),
            "monitoring_active": self._running,
            "agents_observed": len(self.agent_health),
            "last_report": {
                "timestamp": self.last_report.timestamp if self.last_report else None,
                "total_agents": self.last_report.total_agents if self.last_report else 0,
                "healthy": self.last_report.healthy if self.last_report else 0,
                "degraded": self.last_report.degraded if self.last_report else 0,
                "underperformers": self.last_report.underperformers if self.last_report else [],
                "overreachers": self.last_report.overreachers if self.last_report else [],
                "mastermind_status": self.last_report.mastermind_status if self.last_report else "unobserved",
                "aion_status": self.last_report.aion_status if self.last_report else "unobserved",
                "actions_taken": len(self.last_report.actions_taken) if self.last_report else 0,
            } if self.last_report else None,
        }
