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

# Cloud model assignments — Ollama Cloud free tier (after `ollama signin` on VPS)
# Each soldier has a unique cloud model matched to their role and reasoning style.
# Local daemon proxies to cloud — no separate API key needed.
SOLDIER_CLOUD_MODELS = {
    "coo_operations": "gemini-3-flash-preview",  # Speed + intelligence — operations need fast decisions
    "cfo_finance": "qwen3.5:8b",                 # Quantitative reasoning, vision — cost calculations
    "cto_technology": "qwen3-coder-next",        # Agentic coding — architecture and code review
    "ciso_security": "nemotron-3-super",         # 120B MoE (12B active) — NVIDIA safety-aligned, thinking
    "clo_legal": "devstral-small-2:24b",         # Code exploration — license/attribution pattern matching
    "cpo_product": "gemma4:31b",                 # Multimodal, vision — product evaluation across surfaces
    "cro_risk": "deepseek-v3.2",                 # Deepest reasoning — risk is multivariate analysis
}

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
                        # Update model assignments from registry if present
                        if cfg.get("local_model") and sid in SOLDIER_MODELS:
                            SOLDIER_MODELS[sid] = cfg["local_model"]
                        if cfg.get("cloud_model") and sid in SOLDIER_CLOUD_MODELS:
                            SOLDIER_CLOUD_MODELS[sid] = cfg["cloud_model"]
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

    async def convene(
        self,
        directive: str,
        importance: str = "standard",
        context: Optional[Dict[str, Any]] = None,
        model_mode: str = "auto",
    ) -> BoardroomSession:
        """
        Convene a boardroom session. CEO presents directive, Soldiers evaluate in parallel.

        model_mode: "local" (SOLDIER_MODELS only), "cloud" (SOLDIER_CLOUD_MODELS via cloud),
                    "auto" (try cloud, fall back to local — default)
        """
        session = BoardroomSession(
            session_id=f"br_{int(time.time())}",
            directive=directive,
            importance=importance,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # Query all soldiers in parallel
        tasks = []
        for soldier_id, provider in self.soldier_providers.items():
            weight = SOLDIER_WEIGHTS.get(soldier_id, 1.0)
            tasks.append(
                self._query_soldier(soldier_id, provider, directive, importance, weight, context, model_mode)
            )

        if tasks:
            votes = await asyncio.gather(*tasks, return_exceptions=True)
            for v in votes:
                if isinstance(v, SoldierVote):
                    session.votes.append(v)
                elif isinstance(v, Exception):
                    logger.warning(f"Boardroom: soldier query failed: {v}")

        # Tally weighted votes
        session = self._tally_votes(session)

        # Handle dissent
        if session.outcome == "exploration":
            session.dissent_branches = self._create_exploration_branches(session)

        # Build model assignment report
        session.model_report = self._build_model_report(session, model_mode)

        # Log session
        self.sessions.append(session)
        if len(self.sessions) > 100:
            self.sessions = self.sessions[-100:]
        self._log_session(session)

        logger.info(
            f"Boardroom session {session.session_id}: {session.outcome} "
            f"(score={session.weighted_score:.3f}, votes={len(session.votes)}, mode={model_mode})"
        )
        return session

    def _build_model_report(self, session: BoardroomSession, model_mode: str) -> Dict[str, Any]:
        """Build detailed report of which model each member used and inference path."""
        report = {
            "model_mode": model_mode,
            "members": {},
            "inference_summary": {"local": 0, "cloud": 0, "abstained": 0},
        }
        # CEO entry
        report["members"]["ceo_agent_main"] = {
            "role": "Chief Executive Officer",
            "assigned_local": "qwen3:0.6b",
            "assigned_cloud": None,
            "used": "directive_only",
            "path": "CEO does not deliberate — CEO directs",
            "weight": 1.0,
        }
        # Soldier entries from votes
        for v in session.votes:
            local_m = SOLDIER_MODELS.get(v.soldier_id, "?")
            cloud_m = SOLDIER_CLOUD_MODELS.get(v.soldier_id, "?")
            used = v.provider  # e.g. "vllm/deepseek-v3.2 (cloud)" or "vllm/qwen3:1.7b"
            is_cloud = "(cloud)" in used
            report["members"][v.soldier_id] = {
                "role": SOLDIER_PERSONAS.get(v.soldier_id, "")[:60],
                "assigned_local": local_m,
                "assigned_cloud": cloud_m,
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
        """Query a Soldier using VLLMHandler (vLLM → Ollama local → Ollama cloud fallback).

        model_mode: "local" (force SOLDIER_MODELS), "cloud" (force SOLDIER_CLOUD_MODELS), "auto" (cloud then local)
        Routes through the full inference stack with rate limiting on cloud.
        """
        local_model = SOLDIER_MODELS.get(soldier_id, "qwen3:1.7b")
        cloud_model = SOLDIER_CLOUD_MODELS.get(soldier_id)
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

        # Select model based on mode
        if model_mode == "local":
            model = local_model
        elif model_mode == "cloud" and cloud_model:
            model = cloud_model
        else:  # auto — prefer cloud, handler falls back to local
            model = cloud_model or local_model

        t0 = time.time()
        used_model = model
        try:
            # Route through VLLMHandler — gets vLLM → Ollama local → Ollama cloud fallback
            from llm.vllm_handler import VLLMHandler
            handler = VLLMHandler(
                model_name_for_api=model,
                base_url=OLLAMA_URL,  # Ollama local as primary base
            )
            response = await handler.generate_text(
                prompt=prompt, model=model,
                json_mode=True, max_tokens=500, temperature=0.3,
            )

            # If cloud model failed and we're in auto mode, try local explicitly
            if not response and model != local_model and model_mode == "auto":
                used_model = local_model
                response = await handler.generate_text(
                    prompt=prompt, model=local_model,
                    json_mode=True, max_tokens=500, temperature=0.3,
                )

            # Track which path succeeded
            if handler._using_cloud:
                used_model = f"{model} (cloud)"

            latency = int((time.time() - t0) * 1000)

            # Parse response
            vote_data = {"vote": "abstain", "reasoning": "Could not parse response", "confidence": 0.3}
            if response and not response.startswith("Error"):
                try:
                    parsed = json.loads(response)
                    if isinstance(parsed, dict):
                        vote_data = parsed
                except json.JSONDecodeError:
                    resp_lower = response.lower()
                    if "approve" in resp_lower:
                        vote_data = {"vote": "approve", "reasoning": response[:200], "confidence": 0.6}
                    elif "reject" in resp_lower:
                        vote_data = {"vote": "reject", "reasoning": response[:200], "confidence": 0.6}

            return SoldierVote(
                soldier_id=soldier_id,
                provider=f"vllm/{used_model}",
                vote=vote_data.get("vote", "abstain"),
                reasoning=vote_data.get("reasoning", "")[:300],
                confidence=float(vote_data.get("confidence", 0.5)),
                latency_ms=latency,
                weight=weight,
            )
        except Exception as e:
            latency = int((time.time() - t0) * 1000)
            return SoldierVote(
                soldier_id=soldier_id,
                provider=f"vllm/{local_model}",
                vote="abstain",
                reasoning=f"Inference unavailable: {str(e)[:100]}",
                confidence=0.0,
                latency_ms=latency,
                weight=weight,
            )

    def _tally_votes(self, session: BoardroomSession) -> BoardroomSession:
        """Calculate weighted consensus."""
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

            if session.weighted_score >= SUPERMAJORITY_THRESHOLD:
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
