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

# Local model assignments — best model for each Soldier's role
# qwen3:1.7b = complex reasoning (CTO, CISO, CRO)
# qwen3:0.6b = fast decisions (COO, CFO, CLO, CPO)
SOLDIER_MODELS = {
    "coo_operations": "qwen3:0.6b",    # Fast operational decisions
    "cfo_finance": "qwen3:0.6b",       # Quick financial assessment
    "cto_technology": "qwen3:1.7b",    # Deep technical evaluation
    "ciso_security": "qwen3:1.7b",     # Security analysis needs reasoning
    "clo_legal": "qwen3:0.6b",         # Compliance check (fast)
    "cpo_product": "qwen3:0.6b",       # Product perspective (fast)
    "cro_risk": "qwen3:1.7b",          # Risk modeling needs depth
}

OLLAMA_URL = "http://localhost:11434"


class Boardroom:
    """CEO + Seven Soldiers weighted consensus engine."""

    _instance: Optional["Boardroom"] = None

    def __init__(self):
        self.sessions: List[BoardroomSession] = []
        self.session_log_path = PROJECT_ROOT / "data" / "governance" / "boardroom_sessions.jsonl"
        self.session_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load soldier→provider map from agent_map
        self.soldier_providers = {}
        try:
            agent_map_path = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
            if agent_map_path.exists():
                data = json.loads(agent_map_path.read_text())
                self.soldier_providers = data.get("soldier_provider_map", {})
        except Exception:
            pass

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
    ) -> BoardroomSession:
        """
        Convene a boardroom session. CEO presents directive, Soldiers evaluate in parallel.
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
                self._query_soldier(soldier_id, provider, directive, importance, weight, context)
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

        # Log session
        self.sessions.append(session)
        if len(self.sessions) > 100:
            self.sessions = self.sessions[-100:]
        self._log_session(session)

        logger.info(
            f"Boardroom session {session.session_id}: {session.outcome} "
            f"(score={session.weighted_score:.3f}, votes={len(session.votes)})"
        )
        return session

    async def _query_soldier(
        self,
        soldier_id: str,
        provider: str,
        directive: str,
        importance: str,
        weight: float,
        context: Optional[Dict[str, Any]],
    ) -> SoldierVote:
        """Query a Soldier using the best local model for their role."""
        model = SOLDIER_MODELS.get(soldier_id, "qwen3:1.7b")
        prompt = (
            f"You are {soldier_id} in the mindX executive board. "
            f"Evaluate this directive and vote approve, reject, or abstain.\n\n"
            f"Directive: {directive}\n"
            f"Importance: {importance}\n"
            f"Your role weight: {weight}x\n\n"
            f"Respond in JSON: {{\"vote\": \"approve|reject|abstain\", "
            f"\"reasoning\": \"...\", \"confidence\": 0.0-1.0}}"
        )

        t0 = time.time()
        try:
            # Query local Ollama directly with assigned model
            import aiohttp
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as sess:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "format": "json",
                }
                async with sess.post(f"{OLLAMA_URL}/api/chat", json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response = data.get("message", {}).get("content", "")
                    else:
                        response = None
            latency = int((time.time() - t0) * 1000)

            # Parse response
            vote_data = {"vote": "abstain", "reasoning": "Could not parse response", "confidence": 0.3}
            if response and not response.startswith("Error"):
                try:
                    parsed = json.loads(response)
                    vote_data = parsed
                except json.JSONDecodeError:
                    # Extract vote from text
                    resp_lower = response.lower()
                    if "approve" in resp_lower:
                        vote_data = {"vote": "approve", "reasoning": response[:200], "confidence": 0.6}
                    elif "reject" in resp_lower:
                        vote_data = {"vote": "reject", "reasoning": response[:200], "confidence": 0.6}

            return SoldierVote(
                soldier_id=soldier_id,
                provider=f"ollama/{model}",
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
                provider=f"ollama/{model}",
                vote="abstain",
                reasoning=f"Model unavailable: {str(e)[:100]}",
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
        """Append session to JSONL log."""
        try:
            entry = {
                "session_id": session.session_id,
                "directive": session.directive[:200],
                "importance": session.importance,
                "timestamp": session.timestamp,
                "outcome": session.outcome,
                "weighted_score": round(session.weighted_score, 3),
                "votes": [
                    {"soldier": v.soldier_id, "vote": v.vote, "provider": v.provider,
                     "confidence": v.confidence, "latency_ms": v.latency_ms}
                    for v in session.votes
                ],
                "dissent_branches": len(session.dissent_branches),
            }
            with open(self.session_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.warning(f"Boardroom: failed to log session: {e}")

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
