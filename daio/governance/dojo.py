# daio/governance/dojo.py
"""
Dojo — Agent training, reputation, and privilege management.

Maps to DojoManager.sol reputation ranks. Agents earn reputation through:
  - Task completion quality
  - Peer review scores
  - Improvement campaign success
  - Gödel decision quality
  - Boardroom participation

Ranks determine privilege:
  Novice (0-100)      → observe only, no tool access
  Apprentice (101-500) → basic tools, supervised execution
  Journeyman (501-1500) → standard tools, unsupervised
  Expert (1501-5000)   → all tools, can propose improvements
  Master (5001-15000)  → can approve improvements, mentor others
  Grandmaster (15001+) → constitutional vote participation
  Sovereign (special)  → self-governing, can modify own capabilities

BONA FIDE token (Algorand ASA) reflects on-chain verification:
  balance=1 → agent is verified (Apprentice+)
  balance=0 → agent lost verification (clawback for < 2500 reputation)
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

RANKS = [
    ("novice", 0, 100),
    ("apprentice", 101, 500),
    ("journeyman", 501, 1500),
    ("expert", 1501, 5000),
    ("master", 5001, 15000),
    ("grandmaster", 15001, 50000),
    ("sovereign", 50001, 100000),
]

# Tool access by rank
RANK_PRIVILEGES = {
    "novice": {"tools": [], "can_propose": False, "can_vote": False, "can_approve": False},
    "apprentice": {"tools": ["read_only", "analysis"], "can_propose": False, "can_vote": False, "can_approve": False},
    "journeyman": {"tools": ["read_only", "analysis", "code_generation", "web_search"], "can_propose": False, "can_vote": True, "can_approve": False},
    "expert": {"tools": ["*"], "can_propose": True, "can_vote": True, "can_approve": False},
    "master": {"tools": ["*"], "can_propose": True, "can_vote": True, "can_approve": True},
    "grandmaster": {"tools": ["*"], "can_propose": True, "can_vote": True, "can_approve": True},
    "sovereign": {"tools": ["*"], "can_propose": True, "can_vote": True, "can_approve": True},
}


def get_rank(score: int) -> str:
    for name, low, high in RANKS:
        if low <= score <= high:
            return name
    return "sovereign" if score > 50000 else "novice"


def get_privileges(rank: str) -> Dict[str, Any]:
    return RANK_PRIVILEGES.get(rank, RANK_PRIVILEGES["novice"])


@dataclass
class ReputationEvent:
    agent_id: str
    event_type: str  # "task_complete", "peer_review", "campaign_success", "boardroom_vote", "security_violation"
    delta: int  # positive or negative
    reason: str
    timestamp: float


class Dojo:
    """Agent training and reputation management."""

    _instance: Optional["Dojo"] = None

    def __init__(self):
        self.agent_map_path = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
        self.event_log_path = PROJECT_ROOT / "data" / "governance" / "dojo_events.jsonl"
        self.event_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._agent_map: Optional[Dict] = None

    @classmethod
    async def get_instance(cls) -> "Dojo":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_agent_map(self) -> Dict:
        if self._agent_map is None:
            if self.agent_map_path.exists():
                self._agent_map = json.loads(self.agent_map_path.read_text())
            else:
                self._agent_map = {"agents": {}}
        return self._agent_map

    def _save_agent_map(self):
        if self._agent_map:
            self.agent_map_path.write_text(json.dumps(self._agent_map, indent=2))

    def get_agent_reputation(self, agent_id: str) -> Dict[str, Any]:
        """Get agent's current reputation, rank, and privileges."""
        data = self._load_agent_map()
        agent = data.get("agents", {}).get(agent_id)
        if not agent:
            return {"agent_id": agent_id, "status": "unknown"}

        score = agent.get("reputation_score", 0)
        rank = get_rank(score)
        privileges = get_privileges(rank)

        return {
            "agent_id": agent_id,
            "reputation_score": score,
            "rank": rank,
            "verification_tier": agent.get("verification_tier", 0),
            "bona_fide_balance": agent.get("bona_fide_balance", 0),
            "privileges": privileges,
            "eth_address": agent.get("eth_address"),
            "algo_address": agent.get("algo_address"),
            "group": agent.get("group"),
        }

    def update_reputation(self, agent_id: str, delta: int, event_type: str, reason: str) -> Dict[str, Any]:
        """
        Update an agent's reputation score.
        Automatically adjusts rank, verification tier, and BONA FIDE status.
        """
        data = self._load_agent_map()
        agent = data.get("agents", {}).get(agent_id)
        if not agent:
            return {"error": f"Agent {agent_id} not found"}

        old_score = agent.get("reputation_score", 0)
        new_score = max(0, min(100000, old_score + delta))  # Cap at sovereign ceiling (100,000)
        old_rank = get_rank(old_score)
        new_rank = get_rank(new_score)

        agent["reputation_score"] = new_score

        # Update verification tier — aligned with RANKS thresholds
        if new_score >= 50001:
            agent["verification_tier"] = 4  # sovereign (rank: sovereign)
        elif new_score >= 5001:
            agent["verification_tier"] = 3  # bona_fide (rank: master+)
        elif new_score >= 1501:
            agent["verification_tier"] = 2  # verified (rank: expert+)
        elif new_score >= 501:
            agent["verification_tier"] = 1  # provisional (rank: journeyman+)
        else:
            agent["verification_tier"] = 0  # unverified (novice/apprentice)

        # BONA FIDE clawback check
        if new_score < 2500:
            agent["bona_fide_balance"] = 0
        elif agent.get("bona_fide_balance", 0) == 0 and new_score >= 1000:
            agent["bona_fide_balance"] = 1  # re-issue

        data["agents"][agent_id] = agent
        self._save_agent_map()

        # Log event
        event = ReputationEvent(
            agent_id=agent_id,
            event_type=event_type,
            delta=delta,
            reason=reason,
            timestamp=time.time(),
        )
        self._log_event(event)

        result = {
            "agent_id": agent_id,
            "old_score": old_score,
            "new_score": new_score,
            "delta": delta,
            "old_rank": old_rank,
            "new_rank": new_rank,
            "rank_changed": old_rank != new_rank,
            "verification_tier": agent["verification_tier"],
            "bona_fide_balance": agent["bona_fide_balance"],
        }

        if old_rank != new_rank:
            logger.info(f"Dojo: {agent_id} rank changed {old_rank} → {new_rank} (score: {old_score} → {new_score})")

        return result

    def check_privilege(self, agent_id: str, action: str) -> bool:
        """Check if agent has privilege for an action."""
        rep = self.get_agent_reputation(agent_id)
        if rep.get("status") == "unknown":
            return False

        rank = rep["rank"]
        privs = get_privileges(rank)

        if action == "propose":
            return privs["can_propose"]
        elif action == "vote":
            return privs["can_vote"]
        elif action == "approve":
            return privs["can_approve"]
        elif action in ("tool_access", "execute"):
            tools = privs["tools"]
            return "*" in tools or action in tools
        return False

    def get_all_standings(self) -> List[Dict[str, Any]]:
        """Get all agent standings sorted by reputation."""
        data = self._load_agent_map()
        standings = []
        for agent_id, agent in data.get("agents", {}).items():
            score = agent.get("reputation_score", 0)
            standings.append({
                "agent_id": agent_id,
                "score": score,
                "rank": get_rank(score),
                "tier": agent.get("verification_tier", 0),
                "bona_fide": agent.get("bona_fide_balance", 0),
                "group": agent.get("group", ""),
            })
        standings.sort(key=lambda x: x["score"], reverse=True)
        return standings

    def _log_event(self, event: ReputationEvent):
        """Log reputation event as both file AND embedded memory.

        Logs are memories and memories are logs. Every dojo event is:
        1. JSONL log line (existing, backwards compatible)
        2. Structured JSON in data/dojo/ (searchable, reviewable)
        3. Embedded in pgvectorscale (semantic search via RAGE)
        """
        entry = {
            "agent_id": event.agent_id,
            "event_type": event.event_type,
            "delta": event.delta,
            "reason": event.reason,
            "timestamp": event.timestamp,
        }

        # 1. JSONL log
        try:
            with open(self.event_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

        # 2. Structured JSON in data/dojo/
        try:
            dojo_dir = PROJECT_ROOT / "data" / "dojo"
            dojo_dir.mkdir(parents=True, exist_ok=True)
            event_file = dojo_dir / f"event_{int(event.timestamp)}.json"
            event_file.write_text(json.dumps(entry, indent=2), encoding="utf-8")
        except Exception:
            pass

        # 3. Embed in pgvectorscale — logs are memories, memories are logs
        try:
            import asyncio
            asyncio.create_task(self._embed_event(event, entry))
        except Exception:
            pass

    async def _embed_event(self, event: ReputationEvent, entry: Dict):
        """Embed dojo reputation event in pgvectorscale."""
        try:
            from agents import memory_pgvector as _mpg
            direction = "gained" if event.delta > 0 else "lost"
            doc_text = f"Dojo: {event.agent_id} {direction} {abs(event.delta)} reputation ({event.event_type}): {event.reason}"
            await _mpg.embed_and_store_doc(f"dojo_event_{int(event.timestamp)}", doc_text)
            await _mpg.store_memory(
                memory_id=f"dojo_{event.agent_id}_{int(event.timestamp)}",
                agent_id=event.agent_id,
                memory_type="reputation_event",
                importance=7 if abs(event.delta) >= 500 else 5,
                content=entry,
                context={"domain": "dojo", "event_type": event.event_type},
                tags=["dojo", event.event_type, direction],
            )
        except Exception:
            pass
