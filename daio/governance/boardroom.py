# daio/governance/boardroom.py
"""
Boardroom — CEO + Seven Soldiers parallel evaluation.

The boardroom is where strategic decisions are made. The CEO presents a directive,
each Soldier evaluates it using their assigned inference provider (diversity of thought),
and weighted consensus determines the outcome.

Dissent is not discarded — it opens exploration branches.

Pattern:
  1. CEO presents directive
  2. Each Soldier queries their assigned provider in parallel
  3. Soldiers vote: approve / reject / abstain (with reasoning)
  4. Weighted tally: CISO and CRO have 1.2x veto weight
  5. If supermajority (0.666) → execute
  6. If minority dissent → create exploration branch for minority view
  7. Session logged to improvement journal
"""

import asyncio
import json
import os
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SoldierVote:
    soldier_id: str
    provider: str
    vote: str  # "approve", "reject", "abstain"
    reasoning: str
    confidence: float  # 0.0 - 1.0
    latency_ms: int
    weight: float


@dataclass
class BoardroomSession:
    session_id: str
    directive: str
    importance: str  # "routine", "standard", "critical", "constitutional"
    timestamp: str
    votes: List[SoldierVote] = field(default_factory=list)
    outcome: str = "pending"  # "approved", "rejected", "exploration"
    weighted_score: float = 0.0
    dissent_branches: List[Dict[str, Any]] = field(default_factory=list)
    execution_result: Optional[str] = None
    model_report: Dict[str, Any] = field(default_factory=dict)


# Soldier weights from executive_board.yaml
SOLDIER_WEIGHTS = {
    "coo_operations": 1.0,
    "cfo_finance": 1.0,
    "cto_technology": 1.0,
    "ciso_security": 1.2,
    "clo_legal": 0.8,
    "cpo_product": 1.0,
    "cro_risk": 1.2,
}

SUPERMAJORITY_THRESHOLD = 0.666

# ── Adjustable LLM knobs (all env-overridable) ─────────────────────────────
# These are the inference parameters mindX can tune at runtime without code
# changes. Surfaced via /insight/boardroom/roles so operators can read them.
#
#   BOARDROOM_MAX_CONCURRENT — semaphore limit during convene; how many
#       soldier votes fly simultaneously. With cloud routing (one model
#       serves all 8 members), 8 is the natural default — every member
#       can be in flight at once. With local routing, lower if Ollama
#       OLLAMA_MAX_LOADED_MODELS can't hold the working set.
#
#   BOARDROOM_NUM_CTX — context window size in tokens. Ollama defaults
#       to 4096 which truncates long persona prompts (now 1.5–4.2 KB
#       after .prompt + .agent + .persona composition) plus directive +
#       JSON output. 8192 is safe; 16384 covers the verbose CFO prompt.
#
#   BOARDROOM_NUM_PREDICT — output token budget per vote. 2000 tokens
#       fits a JSON envelope plus ~1500 chars of reasoning.
#
#   BOARDROOM_TEMPERATURE — sampling temperature for vote inference.
#       Boardroom decisions favour determinism; default 0.3.
#
#   BOARDROOM_ROLLCALL_NUM_PREDICT — output budget for the short ack
#       prompt during roll call. Default 120 tokens (~one sentence).
BOARDROOM_MAX_CONCURRENT = int(os.environ.get("BOARDROOM_MAX_CONCURRENT", "8"))
BOARDROOM_NUM_CTX = int(os.environ.get("BOARDROOM_NUM_CTX", "8192"))
BOARDROOM_NUM_PREDICT = int(os.environ.get("BOARDROOM_NUM_PREDICT", "2000"))
BOARDROOM_TEMPERATURE = float(os.environ.get("BOARDROOM_TEMPERATURE", "0.3"))
BOARDROOM_ROLLCALL_NUM_PREDICT = int(os.environ.get("BOARDROOM_ROLLCALL_NUM_PREDICT", "120"))

# Inference backend selector. "auto" tries vLLM first if a server is reachable
# at BOARDROOM_VLLM_BASE_URL, otherwise falls through to Ollama. Force a single
# backend by setting "ollama" or "vllm" explicitly.
#
# vLLM is preferred when available because it provides TRUE continuous batching:
# one model serves many concurrent prompts, interleaving generation tokens at
# the per-step level. All 8 boardroom members can be in flight at once and the
# model "takes turns" at the token level rather than the request level. Ollama
# (incl. Ollama Cloud) approximates this upstream but the local daemon
# serialises model swaps.
BOARDROOM_INFERENCE_BACKEND = os.environ.get("BOARDROOM_INFERENCE_BACKEND", "auto").lower()
BOARDROOM_VLLM_BASE_URL = os.environ.get("BOARDROOM_VLLM_BASE_URL", "http://localhost:8001/v1")
BOARDROOM_VLLM_MODEL = os.environ.get("BOARDROOM_VLLM_MODEL", "mistralai/Mistral-7B-Instruct-v0.3")


def boardroom_llm_knobs() -> Dict[str, Any]:
    """Return the active LLM knobs as a flat dict for surfacing on /insight."""
    return {
        "max_concurrent": BOARDROOM_MAX_CONCURRENT,
        "num_ctx": BOARDROOM_NUM_CTX,
        "num_predict": BOARDROOM_NUM_PREDICT,
        "temperature": BOARDROOM_TEMPERATURE,
        "rollcall_num_predict": BOARDROOM_ROLLCALL_NUM_PREDICT,
        "supermajority_threshold": SUPERMAJORITY_THRESHOLD,
        "inference_backend": BOARDROOM_INFERENCE_BACKEND,
        "vllm_base_url": BOARDROOM_VLLM_BASE_URL,
        "vllm_model": BOARDROOM_VLLM_MODEL,
    }


async def vllm_reachable(timeout: float = 2.0) -> bool:
    """Quick liveness probe for the configured vLLM server. Used by the 'auto'
    backend selector and by /insight/boardroom/health."""
    try:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as sess:
            async with sess.get(f"{BOARDROOM_VLLM_BASE_URL.rstrip('/v1')}/v1/models") as r:
                return r.status == 200
    except Exception:
        return False

# Local model assignments — from VPS benchmarks and .agent definitions
# Each soldier uses a different model — no two soldiers think alike
SOLDIER_MODELS = {
    "coo_operations": "qwen3:0.6b",        # 4.3 tok/s — fast operational tempo
    "cfo_finance": "deepseek-coder:1.3b",  # 7.7 tok/s — fastest, good for calculations
    "cto_technology": "qwen3:1.7b",        # 10.0 tok/s — architectural depth
    "ciso_security": "deepseek-r1:1.5b",   # 14.0 tok/s — thinking model, careful deliberation
    "clo_legal": "qwen3:0.6b",            # 4.3 tok/s — compliance is pattern-matching
    "cpo_product": "qwen3.5:2b",           # 2.3B — product judgment across 4 PYTHAI properties
    "cro_risk": "qwen3:4b",               # 2.3B — deepest local, risk needs maximum depth
}

# Cloud model — ONE model for all 8 board members (CEO + 7 Soldiers).
#
# Inaugural meeting evidence (2026-04-12, sessions br_1776022554 + br_1776022600):
#   Session 1 (local): 6/7 soldiers abstained — tiny models couldn't parse JSON vote format.
#     Only CISO (deepseek-r1:1.5b, thinking model) voted at 12.5s. Rest failed in 34-51ms.
#   Session 2 (per-soldier cloud diversity): 7/7 abstained — all failed in 53-64ms.
#     Seven different cloud models hit the free tier 1-concurrent-model wall. None loaded.
#
# Conclusion: per-soldier model diversity is aspirational on free tier. One model, all members.
# Free tier limits: 50 req/5h session, 500 req/week, 100K tokens/session, 1 concurrent model.
# Upgrade to Pro ($20/mo) to unlock per-soldier diversity via BOARD_CLOUD_MAP.
#
# gpt-oss:120b-cloud: 65.5 tok/s on cloud GPU (8.2x vs local 1.5B), proven 2026-04-11.
CLOUD_MODEL = "gpt-oss:120b-cloud"

# Soldier personas — injected into prompts for role-specific evaluation
SOLDIER_PERSONAS = {
    "coo_operations": "You are the Chief Operating Officer. Evaluate operational feasibility, execution timeline, resource requirements. Short cycles, frequent checkpoints, rollback-ready.",
    "cfo_finance": "You are the Chief Financial Officer. Evaluate cost/benefit ratio, budget impact, treasury sustainability. Spending .01 to earn .011 is profit. 18 decimal precision.",
    "cto_technology": "You are the Chief Technology Officer. Evaluate technical feasibility, architecture impact, infrastructure cost. Architecture decisions are permanent — measure twice, deploy once.",
    "ciso_security": "You are the Chief Information Security Officer (1.2x veto weight). Evaluate security posture, attack surface, credential exposure. Least privilege, defense in depth, zero trust.",
    "clo_legal": "You are the Chief Legal Officer (0.8x advisory). Evaluate legal risks, licensing compliance, attribution requirements. Code is law — but law has context.",
    "cpo_product": "You are the Chief Product Officer. Evaluate user value, market fit, scope impact. Products: bankon.pythai.net, mindx.pythai.net, agenticplace.pythai.net, pythai.net.",
    "cro_risk": "You are the Chief Risk Officer (1.2x veto weight). Evaluate risk magnitude, reversibility, blast radius, cascading failures. Every action must have a rollback path.",
}

OLLAMA_URL = "http://localhost:11434"
OLLAMA_CLOUD_URL = "https://ollama.com"

# Agent file path for loading extended personas
BOARDROOM_AGENTS_DIR = PROJECT_ROOT / "agents" / "boardroom"


class Boardroom:
    """CEO + Seven Soldiers weighted consensus engine."""

    _instance: Optional["Boardroom"] = None

    def __init__(self):
        self.sessions: List[BoardroomSession] = []
        self.session_log_path = PROJECT_ROOT / "data" / "governance" / "boardroom_sessions.jsonl"
        self.session_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load soldier configuration from agent_map.json
        # Primary: "soldiers" section (full config with models, weights, capabilities)
        # Fallback: "soldier_provider_map" (legacy provider-only map)
        self.soldier_providers = {}
        self.soldier_configs = {}
        try:
            agent_map_path = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
            if agent_map_path.exists():
                data = json.loads(agent_map_path.read_text())
                soldiers_section = data.get("soldiers", {})
                if soldiers_section:
                    for sid, cfg in soldiers_section.items():
                        self.soldier_providers[sid] = cfg.get("inference_provider", "ollama")
                        self.soldier_configs[sid] = cfg
                        # Update local model assignments from registry if present
                        if cfg.get("local_model") and sid in SOLDIER_MODELS:
                            SOLDIER_MODELS[sid] = cfg["local_model"]
                else:
                    # Legacy: soldier_provider_map only
                    self.soldier_providers = data.get("soldier_provider_map", {})
        except Exception:
            pass

        # Validate all 7 soldiers are present — missing soldiers get default provider
        for soldier_id in SOLDIER_WEIGHTS:
            if soldier_id not in self.soldier_providers:
                self.soldier_providers[soldier_id] = "ollama"
                logger.warning(f"Boardroom: soldier '{soldier_id}' missing from registry, defaulting to ollama")

    @classmethod
    async def get_instance(cls) -> "Boardroom":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # Priority levels — corporate governance hierarchy
    # executive:  full preemption, pauses autonomous loop, boardroom owns all inference
    # elevated:   yields only to executive, preferred scheduling
    # standard:   shared resources with autonomous loop (default)
    # deferred:   yields to everything, runs when idle
    PRIORITY_LEVELS = {
        "executive": {"preempt_autonomous": True, "label": "Executive Session"},
        "elevated": {"preempt_autonomous": False, "label": "Elevated Priority"},
        "standard": {"preempt_autonomous": False, "label": "Standard Session"},
        "deferred": {"preempt_autonomous": False, "label": "Deferred Session"},
    }

    async def _preempt_autonomous(self) -> bool:
        """Pause (never stop) the autonomous loop to free inference for boardroom.

        The autonomous loop is paused, not stopped. It resumes automatically
        after the boardroom session completes via the finally block in convene().
        Autonomous should never be stopped — only paused for executive sessions.
        Kills active Ollama runners to free RAM/CPU for boardroom inference.
        """
        try:
            from agents.core.mindXagent import MindXAgent
            agent = await MindXAgent.get_instance()
            if hasattr(agent, 'autonomous_active') and agent.autonomous_active:
                agent._boardroom_pause = True
                logger.info("Boardroom: EXECUTIVE PRIORITY — autonomous loop PAUSED (not stopped)")
            # Kill active Ollama runners to free resources for boardroom
            import subprocess
            subprocess.run(["pkill", "-f", "ollama runner"], capture_output=True, timeout=5)
            await asyncio.sleep(1)  # let memory free
            logger.info("Boardroom: cleared Ollama runners for executive session")
            return True
        except Exception as e:
            logger.warning(f"Boardroom: failed to pause autonomous loop: {e}")
        return False

    async def _resume_autonomous(self):
        """Resume autonomous loop after executive session. Always resumes."""
        try:
            from agents.core.mindXagent import MindXAgent
            agent = await MindXAgent.get_instance()
            if hasattr(agent, '_boardroom_pause') and agent._boardroom_pause:
                agent._boardroom_pause = False
                logger.info("Boardroom: autonomous loop RESUMED after executive session")
        except Exception as e:
            logger.warning(f"Boardroom: failed to resume autonomous loop: {e}")

    async def convene(
        self,
        directive: str,
        importance: str = "standard",
        context: Optional[Dict[str, Any]] = None,
        model_mode: str = "auto",
        priority: str = "standard",
        members: Optional[str] = None,
        consensus: float = SUPERMAJORITY_THRESHOLD,
    ) -> BoardroomSession:
        """
        Convene a boardroom session. CEO presents directive, Soldiers evaluate.

        model_mode: "local" (SOLDIER_MODELS only), "cloud" (single CLOUD_MODEL for all members),
                    "auto" (try CLOUD_MODEL, fall back to local — default)
        priority: "executive" (preempt autonomous), "elevated", "standard" (default), "deferred"
        members: comma-separated soldier IDs to include, or "all" (default).
                 e.g. "ciso_security,cro_risk" for just CISO + CRO.
                 Shorthand: "ciso,cro,cto" etc (prefix match).
        consensus: weighted score threshold for approval (default 0.666 supermajority).
        """
        priority_cfg = self.PRIORITY_LEVELS.get(priority, self.PRIORITY_LEVELS["standard"])
        preempted = False

        # Executive priority: pause autonomous loop to free Ollama for boardroom
        if priority_cfg["preempt_autonomous"]:
            preempted = await self._preempt_autonomous()

        session = BoardroomSession(
            session_id=f"br_{int(time.time())}",
            directive=directive,
            importance=importance,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # Select which soldiers attend
        if members and members != "all":
            requested = [m.strip().lower() for m in members.split(",")]
            attending = {}
            for sid, prov in self.soldier_providers.items():
                for req in requested:
                    if sid.startswith(req) or sid == req:
                        attending[sid] = prov
                        break
            if not attending:
                attending = self.soldier_providers  # fallback: all
            logger.info(f"Boardroom: selective attendance — {list(attending.keys())}")
        else:
            attending = self.soldier_providers

        try:
            # Free-tier reality: one model in flight at a time. Serial dispatch
            # avoids "1 concurrent model" rejection from cloud providers and lets
            # us persist each vote as a memory + ledger row before the next call.
            for soldier_id, provider in attending.items():
                weight = SOLDIER_WEIGHTS.get(soldier_id, 1.0)
                try:
                    vote = await self._query_soldier(soldier_id, provider, directive, importance, weight, context, model_mode)
                    session.votes.append(vote)
                    await self._record_vote_artifacts(session.session_id, vote, directive, importance)
                except Exception as e:
                    logger.warning(f"Boardroom: soldier query failed: {e}")

            # Tally weighted votes against consensus threshold
            session = self._tally_votes(session, consensus)

            # Handle dissent
            if session.outcome == "exploration":
                session.dissent_branches = self._create_exploration_branches(session)

            # Build model assignment report
            session.model_report = self._build_model_report(session, model_mode)
            session.model_report["consensus_threshold"] = consensus
            session.model_report["priority"] = priority
            session.model_report["priority_label"] = priority_cfg["label"]
            session.model_report["preempted_autonomous"] = preempted

            # Log session
            self.sessions.append(session)
            if len(self.sessions) > 100:
                self.sessions = self.sessions[-100:]
            self._log_session(session)

            logger.info(
                f"Boardroom session {session.session_id}: {session.outcome} "
                f"(score={session.weighted_score:.3f}, votes={len(session.votes)}, "
                f"mode={model_mode}, priority={priority})"
            )
            return session
        finally:
            # Resume autonomous loop after executive session
            if preempted:
                await self._resume_autonomous()

    async def convene_stream(
        self,
        directive: str,
        importance: str = "standard",
        context: Optional[Dict[str, Any]] = None,
        model_mode: str = "auto",
        priority: str = "standard",
        members: Optional[str] = None,
        consensus: float = SUPERMAJORITY_THRESHOLD,
    ):
        """Stream boardroom votes as they arrive. Yields dicts: vote events then final outcome.

        Identical logic to convene(), but yields each SoldierVote immediately
        so the frontend can display responses as soldiers deliberate.
        """
        priority_cfg = self.PRIORITY_LEVELS.get(priority, self.PRIORITY_LEVELS["standard"])
        preempted = False

        if priority_cfg["preempt_autonomous"]:
            preempted = await self._preempt_autonomous()

        session = BoardroomSession(
            session_id=f"br_{int(time.time())}",
            directive=directive,
            importance=importance,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        if members and members != "all":
            requested = [m.strip().lower() for m in members.split(",")]
            attending = {}
            for sid, prov in self.soldier_providers.items():
                for req in requested:
                    if sid.startswith(req) or sid == req:
                        attending[sid] = prov
                        break
            if not attending:
                attending = self.soldier_providers
        else:
            attending = self.soldier_providers

        try:
            # Query soldiers one at a time, yield each vote immediately
            for soldier_id, provider in attending.items():
                weight = SOLDIER_WEIGHTS.get(soldier_id, 1.0)
                try:
                    vote = await self._query_soldier(soldier_id, provider, directive, importance, weight, context, model_mode)
                    session.votes.append(vote)
                    await self._record_vote_artifacts(session.session_id, vote, directive, importance)
                    yield {"event": "vote", "data": {
                        "soldier": vote.soldier_id, "vote": vote.vote,
                        "provider": vote.provider, "reasoning": vote.reasoning[:2000],
                        "confidence": vote.confidence, "latency_ms": vote.latency_ms,
                        "weight": vote.weight,
                    }}
                except Exception as e:
                    logger.warning(f"Boardroom: soldier query failed: {e}")

            # Tally and finalize against consensus threshold
            session = self._tally_votes(session, consensus)
            if session.outcome == "exploration":
                session.dissent_branches = self._create_exploration_branches(session)
            session.model_report = self._build_model_report(session, model_mode)
            session.model_report["consensus_threshold"] = consensus
            session.model_report["priority"] = priority
            session.model_report["priority_label"] = priority_cfg["label"]
            session.model_report["preempted_autonomous"] = preempted

            self.sessions.append(session)
            if len(self.sessions) > 100:
                self.sessions = self.sessions[-100:]
            self._log_session(session)

            logger.info(
                f"Boardroom session {session.session_id}: {session.outcome} "
                f"(score={session.weighted_score:.3f}, votes={len(session.votes)}, "
                f"mode={model_mode}, priority={priority})"
            )

            yield {"event": "outcome", "data": {
                "session_id": session.session_id,
                "outcome": session.outcome,
                "weighted_score": round(session.weighted_score, 3),
                "dissent_branches": session.dissent_branches,
                "model_report": session.model_report,
            }}
        finally:
            if preempted:
                await self._resume_autonomous()

    def _build_model_report(self, session: BoardroomSession, model_mode: str) -> Dict[str, Any]:
        """Build detailed report of which model each member used and inference path."""
        report = {
            "model_mode": model_mode,
            "cloud_model": CLOUD_MODEL,
            "members": {},
            "inference_summary": {"local": 0, "cloud": 0, "abstained": 0},
        }
        # CEO entry — same single cloud model as soldiers
        report["members"]["ceo_agent_main"] = {
            "role": "Chief Executive Officer",
            "assigned_cloud": CLOUD_MODEL,
            "used": "directive_only",
            "path": "CEO does not deliberate — CEO directs",
            "weight": 1.0,
        }
        # Soldier entries from votes
        for v in session.votes:
            local_m = SOLDIER_MODELS.get(v.soldier_id, "?")
            used = v.provider
            is_cloud = "cloud" in used
            report["members"][v.soldier_id] = {
                "role": SOLDIER_PERSONAS.get(v.soldier_id, "")[:60],
                "assigned_local": local_m,
                "assigned_cloud": CLOUD_MODEL,
                "used": used,
                "path": "cloud" if is_cloud else "local",
                "weight": v.weight,
                "vote": v.vote,
                "confidence": v.confidence,
                "latency_ms": v.latency_ms,
            }
            if v.vote == "abstain":
                report["inference_summary"]["abstained"] += 1
            elif is_cloud:
                report["inference_summary"]["cloud"] += 1
            else:
                report["inference_summary"]["local"] += 1
        return report

    @staticmethod
    def _extract_agent_section(content: str, section_name: str, max_lines: int = 8) -> str:
        """Pull the body of a named ALL_CAPS section from a .agent file.
        Body is everything until the next ALL_CAPS section header or EOF.
        Trimmed to `max_lines` non-empty lines."""
        lines = content.split("\n")
        in_section = False
        body = []
        for raw in lines:
            stripped = raw.strip()
            if stripped == section_name:
                in_section = True
                continue
            if not in_section:
                continue
            # End of section: a new ALL_CAPS header (single token or two)
            if stripped and stripped == stripped.upper() and stripped.replace(" ", "").replace("_", "").isalpha() and 3 <= len(stripped) <= 40:
                break
            if stripped:
                body.append(stripped)
                if len(body) >= max_lines:
                    break
        return "\n".join(body)

    def _load_member_card(self, member_id: str) -> Dict[str, Any]:
        """Load the full role card for a board member (CEO or any soldier).
        Reads BOTH `.agent` (operating description, boardroom role) AND
        `.persona` (JSON: name, traits, beliefs, desires, inference). Returns
        a dict with `system_prompt` (composed for LLM injection), plus the
        raw `agent_card` and `persona` for richer downstream use.

        Falls back to SOLDIER_PERSONAS dict, then a generic identity string.
        Cached on first read; recomputed only on cache miss.
        """
        if not hasattr(self, "_member_card_cache"):
            self._member_card_cache: Dict[str, Dict[str, Any]] = {}
        if member_id in self._member_card_cache:
            return self._member_card_cache[member_id]

        short_id = member_id.split("_")[0]  # "ciso_security" → "ciso"
        agent_path = BOARDROOM_AGENTS_DIR / f"{short_id}.agent"
        persona_path = BOARDROOM_AGENTS_DIR / f"{short_id}.persona"
        # .prompt search order (canonical → legacy):
        #   1. prompts/boardroom/{short}.prompt   ← canonical (`prompts/` is
        #      the project's first-class .prompt folder)
        #   2. agents/boardroom/{short}.prompt    ← co-located with .agent
        #   3. AgenticPlace/{short}_agent.prompt  ← legacy origin
        prompt_paths = [
            PROJECT_ROOT / "prompts" / "boardroom" / f"{short_id}.prompt",
            BOARDROOM_AGENTS_DIR / f"{short_id}.prompt",
            PROJECT_ROOT / "AgenticPlace" / f"{short_id}_agent.prompt",
        ]

        prompt_text = ""
        prompt_source: Optional[str] = None
        for pp in prompt_paths:
            if pp.exists():
                try:
                    txt = pp.read_text(encoding="utf-8").strip()
                    if txt:
                        prompt_text = txt
                        prompt_source = str(pp.relative_to(PROJECT_ROOT))
                        break
                except Exception:
                    pass

        agent_card = ""
        if agent_path.exists():
            try:
                agent_card = agent_path.read_text(encoding="utf-8")
            except Exception:
                pass

        persona: Dict[str, Any] = {}
        if persona_path.exists():
            try:
                persona = json.loads(persona_path.read_text(encoding="utf-8"))
            except Exception:
                pass

        # Three-file composition:
        #   .prompt  — canonical voice (primary system prompt)
        #   .persona — cognitive style enrichment (traits, beliefs, priorities)
        #   .agent   — operating contract (BOARDROOM ROLE addendum, only if
        #              .prompt didn't already encode it)
        parts: List[str] = []
        title = persona.get("name") or short_id.upper()

        if prompt_text:
            parts.append(prompt_text)
        elif persona.get("description"):
            parts.append(f"You are the {title}. {persona['description']}")
        elif agent_card:
            desc = self._extract_agent_section(agent_card, "DESCRIPTION", max_lines=6)
            if desc:
                parts.append(f"You are the {title}.\n{desc}")
        else:
            parts.append(f"You are the {title}.")

        traits = persona.get("behavioral_traits") or []
        if traits:
            parts.append("Behavioural traits: " + ", ".join(traits[:8]))

        beliefs = persona.get("beliefs") or {}
        active = [k.replace("_", " ") for k, v in beliefs.items() if v is True]
        if active:
            parts.append("Operating beliefs: " + "; ".join(active[:6]))

        desires = persona.get("desires") or {}
        priorities = [f"{k.replace('_', ' ')}={v}" for k, v in desires.items() if str(v).lower() in ("high", "critical")]
        if priorities:
            parts.append("Priorities: " + "; ".join(priorities[:5]))

        # Add BOARDROOM ROLE only when .prompt didn't supply it (avoid dup).
        if agent_card and not prompt_text:
            br_role = self._extract_agent_section(agent_card, "BOARDROOM ROLE", max_lines=6)
            if br_role:
                parts.append(f"Boardroom role:\n{br_role}")

        if not parts:
            fb = SOLDIER_PERSONAS.get(member_id, f"You are {member_id}.")
            parts.append(fb)

        system_prompt = "\n\n".join(parts)
        sources_loaded = [name for name, present in
                          (("prompt", bool(prompt_text)),
                           ("agent",  bool(agent_card)),
                           ("persona", bool(persona)))
                          if present]
        card = {
            "id": member_id,
            "short_id": short_id,
            "title": title,
            "system_prompt": system_prompt,
            "prompt_text": prompt_text,
            "prompt_source": prompt_source,
            "agent_card": agent_card,
            "persona": persona,
            "weight": persona.get("weight", SOLDIER_WEIGHTS.get(member_id, 1.0)),
            "veto_holder": persona.get("weight", SOLDIER_WEIGHTS.get(member_id, 1.0)) >= 1.2,
            "loaded_from_files": bool(prompt_text or agent_card or persona),
            "sources_loaded": sources_loaded,
        }
        self._member_card_cache[member_id] = card
        return card

    def _load_soldier_persona(self, soldier_id: str) -> str:
        """Backwards-compatible wrapper — returns just the system_prompt string."""
        return self._load_member_card(soldier_id).get("system_prompt") or SOLDIER_PERSONAS.get(soldier_id, f"You are {soldier_id}.")

    # importance → tier_key. Operator can override via env.
    _IMPORTANCE_TO_TIER = {
        "routine": "tier1",
        "standard": "tier2",
        "critical": "tier3",
        "constitutional": "tier3",
    }

    def _resolve_member_model(self, soldier_id: str, importance: str, model_mode: str) -> Optional[str]:
        """Pick the best model for this member at this importance.

        Reads `boardroom_assignments` from data/config/ollama_cloud_models.json
        (loaded once, cached on instance). tier1 is local; tier2/tier3 are
        cloud names — `:cloud` suffix appended automatically when missing.

        Returns None if no assignment exists, letting _query_soldier fall through
        to its legacy CLOUD_MODEL / SOLDIER_MODELS behavior.
        """
        if not hasattr(self, "_assignments_cache"):
            self._assignments_cache: Dict[str, Dict[str, str]] = {}
            try:
                cfg_path = PROJECT_ROOT / "data" / "config" / "ollama_cloud_models.json"
                if cfg_path.exists():
                    cfg = json.loads(cfg_path.read_text())
                    self._assignments_cache = cfg.get("boardroom_assignments") or {}
            except Exception as e:
                logger.debug(f"Boardroom: load boardroom_assignments failed: {e}")

        if model_mode == "local":
            tier_key = "tier1"
        else:
            tier_key = self._IMPORTANCE_TO_TIER.get(importance, "tier2")

        member = self._assignments_cache.get(soldier_id)
        if not member:
            return None
        model = member.get(tier_key) or member.get("tier2") or member.get("tier1")
        if not model:
            return None

        # tier1 = local Ollama tag (already has size: e.g. "qwen3:0.6b").
        # tier2/tier3 = cloud names — ensure :cloud suffix.
        if tier_key != "tier1" and not model.endswith(":cloud") and ":cloud" not in model:
            tag_part = model.split(":", 1)[1] if ":" in model else ""
            if not tag_part.endswith("cloud"):
                model = f"{model}:cloud" if ":" not in model else f"{model.split(':', 1)[0]}:{tag_part}-cloud"
        return model

    async def _record_vote_artifacts(self, session_id: str, vote: SoldierVote, directive: str, importance: str) -> None:
        """Persist a single vote as a memory record AND a cost-ledger row.

        Memory: timestamped under the soldier_id so the boardroom conversation
        can be reconstructed by reading STM for each member.
        Cost: appended to the cost_ledger pgvector table for ROI accounting.
        Both calls are best-effort; failures are logged at debug level.
        """
        provider_label = vote.provider or ""
        if "/" in provider_label:
            prov_kind, model = provider_label.split("/", 1)
        else:
            prov_kind, model = provider_label, ""
        is_cloud = "cloud" in prov_kind or model.endswith("cloud")
        ledger_provider = "ollama_cloud" if is_cloud else (prov_kind or "ollama")

        try:
            from agents.memory_agent import MemoryAgent, MemoryType, MemoryImportance
            mem = MemoryAgent()
            await mem.save_timestamped_memory(
                agent_id=vote.soldier_id,
                memory_type=MemoryType.INTERACTION,
                importance=MemoryImportance.HIGH if importance in ("critical", "constitutional") else MemoryImportance.MEDIUM,
                content={
                    "session_id": session_id,
                    "directive": directive[:2000],
                    "vote": vote.vote,
                    "reasoning": vote.reasoning,
                    "confidence": vote.confidence,
                    "provider": vote.provider,
                    "weight": vote.weight,
                    "latency_ms": vote.latency_ms,
                },
                context={"domain": "boardroom", "session_id": session_id, "importance": importance},
                tags=["boardroom_vote", vote.vote, importance, vote.soldier_id],
            )
        except Exception as e:
            logger.debug(f"Boardroom: per-vote memory write failed: {e}")

        try:
            import uuid as _uuid
            from agents import memory_pgvector as _mpg
            # cost_ledger.call_id is UUID — derive deterministically from session_id
            # so multiple votes from the same session share one call_id.
            call_uuid = str(_uuid.uuid5(_uuid.NAMESPACE_URL, f"boardroom:{session_id}"))
            await _mpg.record_cost(
                provider=ledger_provider,
                model=model or "unknown",
                tokens_in=max(1, len(directive) // 4),
                tokens_out=max(1, len(vote.reasoning) // 4),
                latency_ms=vote.latency_ms,
                cost_usd_est=0.0,
                agent_id=vote.soldier_id,
                task_kind="boardroom_vote",
                free_tier=is_cloud,  # all current cloud routes are free-tier
                success=(vote.vote != "abstain" or vote.confidence >= 0.6),
                call_id=call_uuid,
            )
        except Exception as e:
            logger.debug(f"Boardroom: per-vote cost ledger failed: {e}")

    async def _query_soldier(
        self,
        soldier_id: str,
        provider: str,
        directive: str,
        importance: str,
        weight: float,
        context: Optional[Dict[str, Any]],
        model_mode: str = "auto",
    ) -> SoldierVote:
        """Query a Soldier via Ollama /api/generate.

        model_mode: "local" (force per-soldier SOLDIER_MODELS), "cloud"/"auto" (single CLOUD_MODEL for all)
        Cloud models proxied through local Ollama daemon after `ollama signin`.
        """
        local_model = SOLDIER_MODELS.get(soldier_id, "qwen3:1.7b")
        persona = self._load_soldier_persona(soldier_id)

        prompt = (
            f"{persona}\n\n"
            f"Evaluate this directive and vote approve, reject, or abstain.\n\n"
            f"Directive: {directive}\n"
            f"Importance: {importance}\n"
            f"Your vote weight: {weight}x\n"
        )
        if context:
            prompt += f"Context: {json.dumps(context, default=str)[:500]}\n"
        prompt += (
            f"\nRespond in JSON: {{\"vote\": \"approve|reject|abstain\", "
            f"\"reasoning\": \"...\", \"confidence\": 0.0-1.0}}"
        )

        # Select model — tier-based per importance when boardroom_assignments
        # has an entry for this soldier; otherwise fall back to legacy behavior
        # (one CLOUD_MODEL for all members, or per-soldier SOLDIER_MODELS in local).
        tier_model = self._resolve_member_model(soldier_id, importance, model_mode)
        if tier_model:
            model = tier_model
        elif model_mode == "local":
            model = local_model
        else:  # "cloud" or "auto" — single CLOUD_MODEL for all 8 board members
            model = CLOUD_MODEL

        t0 = time.time()
        used_model = model
        is_cloud = False
        try:
            import aiohttp
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": BOARDROOM_TEMPERATURE,
                    "num_ctx":     BOARDROOM_NUM_CTX,
                    "num_predict": BOARDROOM_NUM_PREDICT,
                },
            }
            response = None

            # Step 0: vLLM continuous batching (when configured + reachable).
            # vLLM is the right substrate for "all 8 concurrent, model takes
            # turns at the token level" — set BOARDROOM_INFERENCE_BACKEND=vllm
            # (or "auto" + a reachable vLLM server) to activate.
            if BOARDROOM_INFERENCE_BACKEND in ("vllm", "auto") and not response:
                try:
                    if BOARDROOM_INFERENCE_BACKEND == "vllm" or await vllm_reachable():
                        vllm_payload = {
                            "model": BOARDROOM_VLLM_MODEL,
                            "prompt": prompt,
                            "max_tokens": BOARDROOM_NUM_PREDICT,
                            "temperature": BOARDROOM_TEMPERATURE,
                            "stream": False,
                        }
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as sess:
                            async with sess.post(f"{BOARDROOM_VLLM_BASE_URL.rstrip('/')}/completions", json=vllm_payload) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    choices = data.get("choices") or []
                                    if choices:
                                        response = (choices[0].get("text") or "").strip()
                                        used_model = BOARDROOM_VLLM_MODEL
                                        is_cloud = False  # vLLM is self-hosted
                                        # Mark provider label for downstream rendering
                                        provider_override = f"vllm/{BOARDROOM_VLLM_MODEL}"
                except Exception as e:
                    logger.debug(f"Boardroom: vLLM path failed for {soldier_id}: {e}")

            # Step 1: Try local Ollama daemon (handles both local + cloud-proxied models)
            # Skipped when vLLM already returned content above; also skipped
            # entirely when the operator forced backend=vllm (no Ollama fallback).
            ollama_skip = bool(response) or BOARDROOM_INFERENCE_BACKEND == "vllm"
            try:
                if ollama_skip:
                    pass  # vLLM already produced a response, or operator forced vllm-only
                else:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as sess:
                        async with sess.post(f"{OLLAMA_URL}/api/generate", json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                response = data.get("response", "")
                                thinking = data.get("thinking", "")
                                if thinking and not response:
                                    response = thinking
                            elif resp.status == 404:
                                logger.info(f"Boardroom: {model} not found locally, trying cloud...")
                            else:
                                error_text = await resp.text()
                                logger.warning(f"Boardroom: Ollama error ({resp.status}) for {model}: {error_text[:200]}")
            except Exception as e:
                logger.warning(f"Boardroom: local Ollama failed for {model}: {e}")

            # Step 2: If local failed and model is a cloud model, try Ollama Cloud direct API
            if not response and model != local_model:
                api_key = os.environ.get("OLLAMA_API_KEY", "")
                if api_key:
                    try:
                        headers = {"Authorization": f"Bearer {api_key}"}
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as sess:
                            async with sess.post(f"{OLLAMA_CLOUD_URL}/api/generate", json=payload, headers=headers) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    response = data.get("response", "")
                                    is_cloud = True
                                    logger.info(f"Boardroom: {model} responded via Ollama Cloud direct API")
                                else:
                                    logger.warning(f"Boardroom: Cloud API error ({resp.status}) for {model}")
                    except Exception as e:
                        logger.warning(f"Boardroom: Cloud API failed for {model}: {e}")

            # Step 3: If cloud model failed, try Gemini as cloud alternative
            if not response and model != local_model and model_mode in ("auto", "cloud"):
                try:
                    from llm.llm_factory import LLMFactory
                    gemini = LLMFactory.create_llm_handler(provider_name="gemini")
                    if gemini:
                        gresponse = await gemini.generate_text(prompt, temperature=BOARDROOM_TEMPERATURE, max_tokens=BOARDROOM_NUM_PREDICT)
                        if gresponse and not gresponse.startswith("Error"):
                            response = gresponse
                            used_model = "gemini"
                            is_cloud = True
                            logger.info(f"Boardroom: {soldier_id} responded via Gemini cloud fallback")
                except Exception as e:
                    logger.debug(f"Boardroom: Gemini fallback failed: {e}")

            # Step 4: Last resort — local model
            if not response and used_model != local_model:
                used_model = local_model
                payload["model"] = local_model
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as sess:
                        async with sess.post(f"{OLLAMA_URL}/api/generate", json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                response = data.get("response", "")
                except Exception as e:
                    logger.warning(f"Boardroom: local fallback failed for {local_model}: {e}")

            latency = int((time.time() - t0) * 1000)

            # Parse response — robust extraction from thinking models
            vote_data = {"vote": "abstain", "reasoning": "Could not parse response", "confidence": 0.3}
            if response and not response.startswith("Error"):
                import re
                # Strip thinking tags if present
                clean = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL).strip()
                if not clean:
                    clean = response  # Use raw if stripping removed everything

                # Try 1: Direct JSON parse
                parsed = None
                try:
                    parsed = json.loads(clean)
                except json.JSONDecodeError:
                    # Try 2: Extract JSON object from within text (models often wrap JSON in markdown)
                    json_match = re.search(r'\{[^{}]*"vote"\s*:\s*"[^"]*"[^{}]*\}', clean, re.DOTALL)
                    if json_match:
                        try:
                            parsed = json.loads(json_match.group())
                        except json.JSONDecodeError:
                            pass

                if isinstance(parsed, dict) and "vote" in parsed:
                    vote_data = parsed
                else:
                    # Try 3: Natural language extraction
                    resp_lower = clean.lower()
                    if '"approve"' in resp_lower or 'vote: approve' in resp_lower or 'i approve' in resp_lower:
                        vote_data = {"vote": "approve", "reasoning": clean[:2000], "confidence": 0.6}
                    elif '"reject"' in resp_lower or 'vote: reject' in resp_lower or 'i reject' in resp_lower:
                        vote_data = {"vote": "reject", "reasoning": clean[:2000], "confidence": 0.6}
                    elif 'approve' in resp_lower and 'reject' not in resp_lower:
                        vote_data = {"vote": "approve", "reasoning": clean[:2000], "confidence": 0.5}
                    elif 'reject' in resp_lower and 'approve' not in resp_lower:
                        vote_data = {"vote": "reject", "reasoning": clean[:2000], "confidence": 0.5}
                    else:
                        vote_data = {"vote": "abstain", "reasoning": clean[:2000], "confidence": 0.3}

            # Label: ollama/model for local, ollama-cloud/model for cloud
            is_cloud = used_model != local_model and model_mode in ("auto", "cloud")
            provider_label = f"ollama-cloud/{used_model}" if is_cloud else f"ollama/{used_model}"

            vote_obj = SoldierVote(
                soldier_id=soldier_id,
                provider=provider_label,
                vote=vote_data.get("vote", "abstain"),
                reasoning=vote_data.get("reasoning", "")[:2000],
                confidence=float(vote_data.get("confidence", 0.5)),
                latency_ms=latency,
                weight=weight,
            )
            # Phase 3: per-soldier metrics — feed to PerformanceMonitor so
            # downstream leaderboards can rank soldiers by fitness, abstain
            # rate, latency, and signal/cost ratio.
            try:
                from agents.monitoring.performance_monitor import PerformanceMonitor
                pm = PerformanceMonitor()
                pm.log_llm_call(
                    model_name=used_model,
                    task_type="boardroom_vote",
                    initiating_agent_id=soldier_id,
                    latency_ms=float(latency),
                    success=(vote_obj.vote != "abstain" or vote_obj.confidence >= 0.6),
                    prompt_tokens=max(1, len(prompt) // 4),
                    completion_tokens=max(1, len(vote_obj.reasoning) // 4),
                )
            except Exception as _pm_e:
                logger.debug(f"Boardroom: performance_monitor.log_llm_call failed: {_pm_e}")
            return vote_obj
        except Exception as e:
            latency = int((time.time() - t0) * 1000)
            try:
                from agents.monitoring.performance_monitor import PerformanceMonitor
                pm = PerformanceMonitor()
                pm.log_llm_call(
                    model_name=local_model,
                    task_type="boardroom_vote",
                    initiating_agent_id=soldier_id,
                    latency_ms=float(latency),
                    success=False,
                    error_type=type(e).__name__,
                )
            except Exception:
                pass
            return SoldierVote(
                soldier_id=soldier_id,
                provider=f"ollama/{local_model}",
                vote="abstain",
                reasoning=f"Inference unavailable: {str(e)[:100]}",
                confidence=0.0,
                latency_ms=latency,
                weight=weight,
            )

    def _tally_votes(self, session: BoardroomSession, threshold: float = SUPERMAJORITY_THRESHOLD) -> BoardroomSession:
        """Calculate weighted consensus against the given threshold."""
        if not session.votes:
            session.outcome = "rejected"
            session.weighted_score = 0.0
            return session

        total_weight = sum(v.weight for v in session.votes if v.vote != "abstain")
        approve_weight = sum(v.weight * v.confidence for v in session.votes if v.vote == "approve")
        reject_weight = sum(v.weight * v.confidence for v in session.votes if v.vote == "reject")

        if total_weight == 0:
            session.weighted_score = 0.0
            session.outcome = "rejected"
        else:
            session.weighted_score = approve_weight / (approve_weight + reject_weight) if (approve_weight + reject_weight) > 0 else 0

            if session.weighted_score >= threshold:
                session.outcome = "approved"
            elif reject_weight > 0 and approve_weight > 0:
                # Mixed votes — dissent exists, open exploration
                session.outcome = "exploration"
            else:
                session.outcome = "rejected"

        return session

    def _create_exploration_branches(self, session: BoardroomSession) -> List[Dict[str, Any]]:
        """Dissent creates new avenues instead of blocking progress."""
        branches = []
        dissenting = [v for v in session.votes if v.vote == "reject"]
        for v in dissenting:
            branches.append({
                "soldier": v.soldier_id,
                "provider": v.provider,
                "reasoning": v.reasoning,
                "suggestion": f"Explore alternative approach per {v.soldier_id}: {v.reasoning[:150]}",
                "confidence": v.confidence,
            })
        return branches

    def _log_session(self, session: BoardroomSession):
        """Log session as both structured file AND embedded memory.

        Logs are memories and memories are logs. Every boardroom session is:
        1. JSONL log line (backwards compatible)
        2. Structured JSON in data/boardroom/ (searchable, reviewable)
        3. Embedded in pgvectorscale (semantic search via RAGE)
        4. Activity feed event (live dashboard)
        """
        entry = {
            "session_id": session.session_id,
            "directive": session.directive[:2000],
            "importance": session.importance,
            "timestamp": session.timestamp,
            "outcome": session.outcome,
            "weighted_score": round(session.weighted_score, 3),
            "votes": [
                {"soldier": v.soldier_id, "vote": v.vote, "provider": v.provider,
                 "reasoning": v.reasoning[:2000], "confidence": v.confidence, "latency_ms": v.latency_ms,
                 "weight": v.weight}
                for v in session.votes
            ],
            "dissent_branches": len(session.dissent_branches),
        }

        # 1. JSONL log (existing, backwards compatible)
        try:
            with open(self.session_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Boardroom: JSONL log failed: {e}")

        # 1b. Catalogue mirror (Phase 0, additive)
        try:
            import asyncio as _asyncio
            from agents.catalogue import emit_catalogue_event
            _asyncio.create_task(emit_catalogue_event(
                kind="board.session",
                actor="boardroom",
                payload=entry,
                source_log="governance/boardroom_sessions.jsonl",
                source_ref=session.session_id,
            ))
        except Exception:
            pass

        # 2. Structured JSON in data/boardroom/
        try:
            boardroom_dir = PROJECT_ROOT / "data" / "boardroom"
            boardroom_dir.mkdir(parents=True, exist_ok=True)
            session_file = boardroom_dir / f"{session.session_id}.json"
            # Include full reasoning in the structured file
            full_entry = dict(entry)
            full_entry["votes"] = [
                {"soldier": v.soldier_id, "vote": v.vote, "provider": v.provider,
                 "reasoning": v.reasoning, "confidence": v.confidence, "latency_ms": v.latency_ms,
                 "weight": v.weight}
                for v in session.votes
            ]
            full_entry["dissent_branches_detail"] = session.dissent_branches
            session_file.write_text(json.dumps(full_entry, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"Boardroom: structured log failed: {e}")

        # 3. Embed in pgvectorscale — logs are memories, memories are logs
        try:
            import asyncio
            asyncio.create_task(self._embed_session(session, entry))
        except Exception:
            pass

        # 4. Activity feed (live dashboard)
        try:
            from mindx_backend_service.activity_feed import ActivityFeed
            vote_summary = " ".join(
                f'{v.soldier_id[:3]}:{"✓" if v.vote=="approve" else "✗" if v.vote=="reject" else "—"}'
                for v in session.votes
            )
            ActivityFeed.get_instance().emit(
                "boardroom", "ceo_agent", "session",
                f'{session.directive[:120]} → {session.outcome.upper()} ({session.weighted_score:.3f}) {vote_summary}',
                detail=entry, agent_tier=4
            )
        except Exception:
            pass

    async def _embed_session(self, session: BoardroomSession, entry: Dict):
        """Embed boardroom session in pgvectorscale for semantic search."""
        try:
            from agents import memory_pgvector as _mpg

            # Store as embedded document (chunked, searchable via RAGE)
            doc_text = (
                f"Boardroom session {session.session_id}: {session.directive}\n"
                f"Outcome: {session.outcome} (score: {session.weighted_score:.3f})\n"
                + "\n".join(
                    f"- {v.soldier_id} voted {v.vote} ({v.confidence:.0%}): {v.reasoning[:150]}"
                    for v in session.votes
                )
            )
            await _mpg.embed_and_store_doc(f"boardroom_{session.session_id}", doc_text)

            # Store as memory record
            await _mpg.store_memory(
                memory_id=f"boardroom_{session.session_id}",
                agent_id="ceo_agent_main",
                memory_type="boardroom_session",
                importance=8 if session.importance in ("critical", "constitutional") else 6,
                content=entry,
                context={"domain": "boardroom", "outcome": session.outcome},
                tags=["boardroom", session.outcome, session.importance],
            )
        except Exception as e:
            logger.debug(f"Boardroom: pgvectorscale embed failed: {e}")

    def get_recent_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Return recent sessions for dashboard display."""
        return [
            {
                "session_id": s.session_id,
                "directive": s.directive[:100],
                "outcome": s.outcome,
                "score": round(s.weighted_score, 3),
                "votes": len(s.votes),
                "dissent": len(s.dissent_branches),
                "timestamp": s.timestamp,
            }
            for s in self.sessions[-limit:]
        ]

    async def roll_call(self, prefer_cloud: bool = True, per_soldier_timeout: int = 60) -> Dict[str, Any]:
        """CEO calls roll. Each seated soldier is invoked with a short
        acknowledgment prompt and must respond. Returns per-soldier presence
        plus their model/latency/ack-text. Sequential to avoid model-swap
        thrash on local Ollama; uses cloud model when available for speed.

        Behavior on local-only (no OLLAMA_API_KEY): expect failures. Local
        Ollama loads ONE model at a time; calling 7 different soldier-models
        sequentially forces 6 cold loads, each ~30-90s on CPU. Total wall
        budget: 7 × per_soldier_timeout = 7 minutes worst case. The HTTP
        edge will likely time out before completion.

        Recommended: have `ollama signin` run once on the VPS so the local
        daemon proxies all 7 soldiers through one cloud model
        (gpt-oss:120b-cloud). One model = no swaps = ~1-3s per ack.

        Per docs/ollama/cloud/cloud.md: the LOCAL daemon path uses cloud
        models WITHOUT an API key — auth is via `ollama signin` (ed25519
        keypair at /usr/share/ollama/.ollama/id_ed25519). The
        OLLAMA_API_KEY is only needed for direct https://ollama.com calls.

        ack states:
            present  — soldier responded with valid ack text
            silent   — soldier did not respond (timeout or empty)
            error    — exception during invocation
        """
        import aiohttp

        # Local daemon proxies cloud-suffixed models when signed in. No API
        # key required for that path. We always try cloud first when
        # prefer_cloud=True; if local daemon returns 'unauthorized' the
        # operator needs to run `ollama signin` on the VPS — surfaced via
        # the 'advice' field below.
        cloud_ok = bool(prefer_cloud)

        results: Dict[str, Any] = {}
        present_count = 0

        # Load the CEO card once — used to frame the roll-call prompt.
        ceo_card = self._load_member_card("ceo_agent_main")
        ceo_title = ceo_card.get("title") or "CEO"

        for soldier_id, local_model in SOLDIER_MODELS.items():
            # Load full role card (.agent + .persona); falls back to dict.
            card = self._load_member_card(soldier_id)
            persona = card["system_prompt"]
            weight = card.get("weight", SOLDIER_WEIGHTS.get(soldier_id, 1.0))
            role_pretty = (card.get("title") or soldier_id.upper().replace("_", " "))
            prompt = (
                f"{persona}\n\n"
                f"--- CONVOCATION ---\n"
                f"The {ceo_title} is calling roll for the boardroom. Respond with EXACTLY one "
                f"short sentence acknowledging your presence, your role, and that you are ready "
                f"to deliberate.\n"
                f'Format: "Present. I am the {role_pretty}, weight {weight}x, ready to deliberate."\n'
                f"Respond with the acknowledgment only, no JSON, no preamble, no thinking."
            )
            payload = {
                "model": CLOUD_MODEL if cloud_ok else local_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.0,
                    "num_ctx":     BOARDROOM_NUM_CTX,
                    "num_predict": BOARDROOM_ROLLCALL_NUM_PREDICT,
                },
            }
            t0 = time.time()
            ack = ""
            state = "silent"
            used_model = payload["model"]
            error = None
            unauthorized = False
            try:
                # Try local Ollama first (handles cloud-proxied models too
                # when the daemon is signed in via `ollama signin`).
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=per_soldier_timeout)) as sess:
                    async with sess.post(f"{OLLAMA_URL}/api/generate", json=payload) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            ack = (data.get("response") or "").strip()
                            # Reasoning models (gpt-oss, deepseek-r1) emit
                            # the answer in `thinking` when `response` is empty.
                            if not ack:
                                ack = (data.get("thinking") or "").strip()
                            if not ack and isinstance(data.get("error"), str) and "unauthorized" in data["error"].lower():
                                unauthorized = True
                        else:
                            txt = await resp.text()
                            if "unauthorized" in txt.lower():
                                unauthorized = True
                                error = "ollama unauthorized — run `ollama signin` on the VPS"
                # Fall back to local model if cloud failed
                if not ack and cloud_ok:
                    payload["model"] = local_model
                    used_model = local_model
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=per_soldier_timeout)) as sess:
                        async with sess.post(f"{OLLAMA_URL}/api/generate", json=payload) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                ack = (data.get("response") or "").strip()
                                if not ack:
                                    ack = (data.get("thinking") or "").strip()
                if ack:
                    state = "present"
                    present_count += 1
            except asyncio.TimeoutError:
                error = f"timeout after {per_soldier_timeout}s — local Ollama likely cold-loading {used_model}"
                state = "error"
            except Exception as e:
                error = str(e)[:200]
                state = "error"
            latency = int((time.time() - t0) * 1000)
            results[soldier_id] = {
                "soldier": soldier_id,
                "role": role_pretty,
                "weight": weight,
                "veto_holder": weight >= 1.2,
                "model": used_model,
                "model_kind": "cloud" if used_model == CLOUD_MODEL and cloud_ok else "local",
                "state": state,
                "ack": ack[:400],
                "latency_ms": latency,
                "error": error,
                "persona_source": "files" if card.get("loaded_from_files") else "fallback",
            }
        # Detect if any soldier hit unauthorized (= signin lapsed)
        any_unauthorized = any(
            (r.get("error") or "").lower().startswith("ollama unauthorized")
            for r in results.values()
        )
        advice = None
        if any_unauthorized:
            advice = (
                "Ollama Cloud signin has lapsed — local daemon returns 'unauthorized'. "
                "Run `sudo -u ollama ollama signin` on the VPS once to re-authenticate. "
                f"Until then, soldiers fall back to local-only models which cold-load slowly. "
                "See docs/ollama/cloud/cloud.md."
            )
        elif present_count < len(SOLDIER_MODELS):
            advice = (
                f"Only {present_count}/{len(SOLDIER_MODELS)} soldiers responded. With 7 distinct local "
                f"models on a CPU VPS, cold-loading is the bottleneck. The fix is `ollama signin` once "
                f"so the local daemon can proxy {CLOUD_MODEL} for all soldiers (no API key needed for "
                f"the local-proxied path; see docs/ollama/cloud/cloud.md)."
            )

        # Self-adaptation: pattern-match the failure and emit a structured
        # recovery action. The UI auto-fires the matching endpoint when
        # `recovery.auto_action` is set.
        recovery = self._diagnose_recovery(results, present_count)

        return {
            "ceo": {
                "id": "ceo_agent_main",
                "title": ceo_card.get("title") or "CEO",
                "persona_source": "files" if ceo_card.get("loaded_from_files") else "fallback",
                "weight": ceo_card.get("weight"),
            },
            "results": results,
            "present": present_count,
            "total": len(SOLDIER_MODELS),
            "quorum": present_count >= 4,
            "all_present": present_count == len(SOLDIER_MODELS),
            "cloud_used": cloud_ok,
            "per_soldier_timeout": per_soldier_timeout,
            "advice": advice,
            "recovery": recovery,
            "completed_at": time.time(),
        }

    def _diagnose_recovery(self, results: Dict[str, Any], present_count: int) -> Dict[str, Any]:
        """Pattern-match the per-soldier failure modes and emit a structured
        recovery action the UI can auto-fire.

        Today this handles:
          - ≥4 soldiers errored with "unauthorized"  → ollama_signin
          - all soldiers timed out at the same ceiling → cold_load_storm
          - all soldiers returned empty acks → prompt_or_format_drift
          - persona_source == "fallback" for any soldier → file_missing

        Adding a new pattern is one entry: the matcher predicate + the
        recovery dict. The UI reads `auto_action` and POSTs the matching
        endpoint; everything else is human-readable narration.
        """
        total = len(results)
        if total == 0:
            return {"pattern": None, "auto_action": None}

        # Collect failure-mode counts
        unauthorized = 0
        timed_out = 0
        empty_ack = 0
        cold_load_msg = 0
        for r in results.values():
            err = (r.get("error") or "").lower()
            state = r.get("state")
            if "unauthorized" in err:
                unauthorized += 1
            if "timeout" in err or err.startswith("timeout"):
                timed_out += 1
            if state == "silent":
                empty_ack += 1
            if "cold-loading" in err or "cold_load" in err:
                cold_load_msg += 1

        # Pattern 1: unauthorized storm (highest priority, easiest fix)
        if unauthorized >= max(4, total // 2):
            return {
                "pattern": "ollama_signin_lapsed",
                "severity": "high",
                "matched_count": unauthorized,
                "matched_total": total,
                "auto_action": {
                    "method": "POST",
                    "endpoint": "/insight/boardroom/cloud_signin",
                    "ui_message": (
                        f"{unauthorized}/{total} soldiers report 'unauthorized'. "
                        f"CEO is initiating the operator-signin handoff automatically."
                    ),
                },
                "operator_message": (
                    "The boardroom needs you to re-authorise the local Ollama daemon to "
                    "Ollama Cloud (one click on the URL the CEO will surface in dialogue). "
                    "Until then every cloud-routed call returns 401. "
                    "See docs/ollama/cloud/cloud.md."
                ),
                "fallback_when_no_signin": (
                    "If the operator can't sign now, the boardroom can convene with locally-"
                    "available models only (BOARDROOM_INFERENCE_BACKEND=ollama, slower). "
                    "Cold-load latency dominates."
                ),
            }

        # Pattern 2: cold-load storm — all timed out at the ceiling
        if timed_out + cold_load_msg >= max(4, total // 2):
            return {
                "pattern": "cold_load_storm",
                "severity": "medium",
                "matched_count": timed_out + cold_load_msg,
                "matched_total": total,
                "auto_action": None,  # No safe auto-action; this requires operator decision
                "operator_message": (
                    f"{timed_out + cold_load_msg}/{total} soldiers timed out cold-loading. "
                    f"Local Ollama swap-thrashes when seven distinct models are requested. "
                    f"Either run `ollama signin` (cloud routing through one shared model) or "
                    f"raise OLLAMA_MAX_LOADED_MODELS in the systemd override."
                ),
                "remediation_hints": [
                    "POST /insight/boardroom/cloud_signin (preferred — sub-3s per soldier)",
                    "increase OLLAMA_MAX_LOADED_MODELS=4 in /etc/systemd/system/ollama.service.d/concurrency.conf",
                    "set BOARDROOM_INFERENCE_BACKEND=vllm with a vLLM server (continuous batching)",
                ],
            }

        # Pattern 3: silent / empty acks (model loaded but produces nothing)
        if empty_ack >= max(4, total // 2):
            return {
                "pattern": "empty_ack_drift",
                "severity": "medium",
                "matched_count": empty_ack,
                "matched_total": total,
                "auto_action": None,
                "operator_message": (
                    "Models load and respond fast but the ack text is empty — likely a prompt-"
                    "format drift (model output landing in `thinking` instead of `response`, or "
                    "BOARDROOM_NUM_CTX truncating the persona). Check /insight/boardroom/cards "
                    "for the composed system_prompt size and BOARDROOM_NUM_CTX."
                ),
            }

        # Pattern 4: fallback persona — at least one soldier missing files
        fallback_seats = [sid for sid, r in results.items() if r.get("persona_source") == "fallback"]
        if fallback_seats:
            return {
                "pattern": "persona_files_missing",
                "severity": "low",
                "matched_count": len(fallback_seats),
                "matched_total": total,
                "auto_action": None,
                "operator_message": (
                    f"{len(fallback_seats)} seat(s) running on the hardcoded fallback persona "
                    f"({', '.join(fallback_seats)}). Restore the missing files in "
                    f"prompts/boardroom/ and agents/boardroom/ — see /doc/agents/boardroom_members."
                ),
            }

        # No issues
        return {"pattern": None, "auto_action": None, "matched_count": 0}
