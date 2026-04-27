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
            # Concurrency tuned for OLLAMA_NUM_PARALLEL=4 / OLLAMA_MAX_LOADED_MODELS=4
            # set on the VPS systemd override. With 4 slots Ollama keeps the
            # working set of soldier-models resident across consecutive votes,
            # eliminating the cold-load cliff that produced 0/7 roll calls.
            MAX_CONCURRENT = int(os.environ.get("BOARDROOM_MAX_CONCURRENT", "3"))
            semaphore = asyncio.Semaphore(MAX_CONCURRENT)

            async def _limited_query(sid, prov, weight):
                async with semaphore:
                    return await self._query_soldier(sid, prov, directive, importance, weight, context, model_mode)

            tasks = []
            for soldier_id, provider in attending.items():
                weight = SOLDIER_WEIGHTS.get(soldier_id, 1.0)
                tasks.append(_limited_query(soldier_id, provider, weight))

            if tasks:
                votes = await asyncio.gather(*tasks, return_exceptions=True)
                for v in votes:
                    if isinstance(v, SoldierVote):
                        session.votes.append(v)
                    elif isinstance(v, Exception):
                        logger.warning(f"Boardroom: soldier query failed: {v}")

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

    def _load_soldier_persona(self, soldier_id: str) -> str:
        """Load full persona from .agent file, fall back to SOLDIER_PERSONAS dict."""
        # Try loading from .agent file (richer context)
        agent_file = BOARDROOM_AGENTS_DIR / f"{soldier_id.split('_')[0]}.agent"
        if agent_file.exists():
            try:
                content = agent_file.read_text(encoding="utf-8")
                # Extract DESCRIPTION and OPERATING PRINCIPLES sections
                sections = []
                current = None
                for line in content.split("\n"):
                    if line.strip() in ("DESCRIPTION", "OPERATING PRINCIPLES", "BOARDROOM ROLE"):
                        current = line.strip()
                        continue
                    elif line.strip() and not line.startswith(" ") and not line.startswith("\t") and current:
                        current = None
                    if current and line.strip():
                        sections.append(line.strip())
                if sections:
                    return " ".join(sections[:8])  # First 8 lines — enough for persona
            except Exception:
                pass
        # Fall back to hardcoded persona
        return SOLDIER_PERSONAS.get(soldier_id, f"You are {soldier_id}.")

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

        # Select model — one cloud model for all members (free tier: 1 concurrent model)
        if model_mode == "local":
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
                "options": {"temperature": 0.3, "num_predict": 2000},
            }
            response = None

            # Step 1: Try local Ollama daemon (handles both local + cloud-proxied models)
            try:
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
                        gresponse = await gemini.generate_text(prompt, temperature=0.3, max_tokens=2000)
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
            "directive": session.directive[:200],
            "importance": session.importance,
            "timestamp": session.timestamp,
            "outcome": session.outcome,
            "weighted_score": round(session.weighted_score, 3),
            "votes": [
                {"soldier": v.soldier_id, "vote": v.vote, "provider": v.provider,
                 "reasoning": v.reasoning[:200], "confidence": v.confidence, "latency_ms": v.latency_ms}
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
        for soldier_id, local_model in SOLDIER_MODELS.items():
            persona = SOLDIER_PERSONAS.get(soldier_id, f"You are the {soldier_id}.")
            weight = SOLDIER_WEIGHTS.get(soldier_id, 1.0)
            role_pretty = soldier_id.upper().replace("_", " ")
            prompt = (
                f"{persona}\n\n"
                f"The CEO is calling roll for the boardroom. Respond with EXACTLY one short sentence "
                f"acknowledging your presence, your role, and that you are ready to deliberate. "
                f'Format: "Present. I am the {role_pretty}, weight {weight}x, ready to deliberate."\n'
                f"Respond with the acknowledgment only, no JSON, no preamble."
            )
            payload = {
                "model": CLOUD_MODEL if cloud_ok else local_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0, "num_predict": 80},
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
        return {
            "results": results,
            "present": present_count,
            "total": len(SOLDIER_MODELS),
            "quorum": present_count >= 4,
            "all_present": present_count == len(SOLDIER_MODELS),
            "cloud_used": cloud_ok,
            "per_soldier_timeout": per_soldier_timeout,
            "advice": advice,
            "completed_at": time.time(),
        }
