# agents/memory_pgvector.py
"""
pgvector Backend for MemoryAgent.

Provides async PostgreSQL storage for memories, beliefs, godel choices,
and agent registry. Uses pgvector for vector similarity search.

MemoryAgent calls these methods alongside file storage.
DB is primary, files are backup.

Connection: postgresql://mindx:mindx_secure_2026@localhost:5432/mindx
"""

import json
import asyncio
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone

from utils.logging_config import get_logger

logger = get_logger(__name__)

# Connection pool — shared across all MemoryAgent instances
_pool = None
_pool_lock = asyncio.Lock()

DB_DSN = "postgresql://mindx:mindx_secure_2026@localhost:5432/mindx"


async def get_pool():
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        async with _pool_lock:
            if _pool is None:
                try:
                    import asyncpg
                    _pool = await asyncpg.create_pool(
                        DB_DSN, min_size=2, max_size=10, command_timeout=30
                    )
                    logger.info("pgvector: connection pool created (min=2, max=10)")
                except Exception as e:
                    logger.warning(f"pgvector: pool creation failed: {e}")
                    return None
    return _pool


async def store_memory(
    memory_id: str,
    agent_id: str,
    memory_type: str,
    importance: int,
    content: Dict[str, Any],
    context: Dict[str, Any],
    tags: List[str],
    parent_memory_id: Optional[str] = None,
    tier: str = "stm",
) -> bool:
    """Store a memory record in PostgreSQL."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            """INSERT INTO memories (memory_id, agent_id, memory_type, importance, content, context, tags, parent_memory_id, tier)
               VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8, $9)
               ON CONFLICT (memory_id) DO UPDATE SET content=$5::jsonb, context=$6::jsonb, tags=$7""",
            memory_id, agent_id, memory_type, importance,
            json.dumps(content), json.dumps(context), tags,
            parent_memory_id, tier,
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector store_memory failed: {e}")
        return False


async def store_belief(key: str, value: Any, confidence: float, source: str) -> bool:
    """Store or update a belief."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            """INSERT INTO beliefs (key, value, confidence, source, updated_at)
               VALUES ($1, $2::jsonb, $3, $4, NOW())
               ON CONFLICT (key) DO UPDATE SET value=$2::jsonb, confidence=$3, source=$4, updated_at=NOW()""",
            key, json.dumps(value), confidence, source,
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector store_belief failed: {e}")
        return False


async def get_belief(key: str) -> Optional[Dict[str, Any]]:
    """Retrieve a belief by key."""
    pool = await get_pool()
    if not pool:
        return None
    try:
        row = await pool.fetchrow("SELECT value, confidence, source FROM beliefs WHERE key=$1", key)
        if row:
            return {"value": json.loads(row["value"]), "confidence": row["confidence"], "source": row["source"]}
        return None
    except Exception as e:
        logger.debug(f"pgvector get_belief failed: {e}")
        return None


async def get_all_beliefs() -> Dict[str, Any]:
    """Get all beliefs as a dict."""
    pool = await get_pool()
    if not pool:
        return {}
    try:
        rows = await pool.fetch("SELECT key, value, confidence, source FROM beliefs")
        return {r["key"]: {"value": json.loads(r["value"]), "confidence": r["confidence"], "source": r["source"]} for r in rows}
    except Exception as e:
        logger.debug(f"pgvector get_all_beliefs failed: {e}")
        return {}


async def store_godel_choice(
    source_agent: str, choice_type: str, perception: str,
    options: Any, chosen: str, rationale: str, outcome: str,
) -> bool:
    """Log a Godel decision."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            """INSERT INTO godel_choices (source_agent, choice_type, perception_summary, options_considered, chosen, rationale, outcome)
               VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)""",
            source_agent, choice_type, perception,
            json.dumps(options) if options else "null", chosen, rationale, outcome,
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector store_godel_choice failed: {e}")
        return False


async def get_godel_choices(limit: int = 50, source_agent: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve recent Godel choices."""
    pool = await get_pool()
    if not pool:
        return []
    try:
        if source_agent:
            rows = await pool.fetch(
                "SELECT * FROM godel_choices WHERE source_agent=$1 ORDER BY created_at DESC LIMIT $2",
                source_agent, limit,
            )
        else:
            rows = await pool.fetch(
                "SELECT * FROM godel_choices ORDER BY created_at DESC LIMIT $1", limit
            )
        return [
            {
                "source_agent": r["source_agent"],
                "choice_type": r["choice_type"],
                "perception_summary": r["perception_summary"],
                "chosen": r["chosen"],
                "rationale": r["rationale"],
                "outcome": r["outcome"],
                "timestamp": r["created_at"].isoformat() if r["created_at"] else "",
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"pgvector get_godel_choices failed: {e}")
        return []


async def store_model_perf(model: str, latency_ms: int, tokens_est: int, tps: float, cpu: float) -> bool:
    """Track model performance."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            "INSERT INTO model_perf (model, latency_ms, tokens_est, tps, cpu_at_query) VALUES ($1,$2,$3,$4,$5)",
            model, latency_ms, tokens_est, tps, cpu,
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector store_model_perf failed: {e}")
        return False


async def count_memories_by_agent() -> Dict[str, int]:
    """Count memories per agent (replaces filesystem glob)."""
    pool = await get_pool()
    if not pool:
        return {}
    try:
        rows = await pool.fetch(
            "SELECT agent_id, COUNT(*) as cnt FROM memories GROUP BY agent_id ORDER BY cnt DESC"
        )
        return {r["agent_id"]: r["cnt"] for r in rows}
    except Exception as e:
        logger.debug(f"pgvector count_memories_by_agent failed: {e}")
        return {}


async def count_memories_total() -> int:
    """Total memory count."""
    pool = await get_pool()
    if not pool:
        return 0
    try:
        row = await pool.fetchrow("SELECT COUNT(*) as cnt FROM memories")
        return row["cnt"] if row else 0
    except Exception as e:
        return 0


async def get_recent_memories(agent_id: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent memories, optionally filtered by agent."""
    pool = await get_pool()
    if not pool:
        return []
    try:
        if agent_id:
            rows = await pool.fetch(
                "SELECT memory_id, agent_id, memory_type, importance, content, tags, tier, created_at FROM memories WHERE agent_id=$1 ORDER BY created_at DESC LIMIT $2",
                agent_id, limit,
            )
        else:
            rows = await pool.fetch(
                "SELECT memory_id, agent_id, memory_type, importance, content, tags, tier, created_at FROM memories ORDER BY created_at DESC LIMIT $1",
                limit,
            )
        return [
            {
                "memory_id": r["memory_id"],
                "agent_id": r["agent_id"],
                "memory_type": r["memory_type"],
                "content": json.loads(r["content"]) if isinstance(r["content"], str) else r["content"],
                "tier": r["tier"],
                "created_at": r["created_at"].isoformat() if r["created_at"] else "",
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"pgvector get_recent_memories failed: {e}")
        return []


async def promote_to_ltm(memory_id: str) -> bool:
    """Promote a memory from STM to LTM."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            "UPDATE memories SET tier='ltm', promoted_at=NOW() WHERE memory_id=$1",
            memory_id,
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector promote_to_ltm failed: {e}")
        return False


async def sync_agent_registry(agents: Dict[str, Dict[str, Any]]) -> int:
    """Sync agent map into agents table."""
    pool = await get_pool()
    if not pool:
        return 0
    count = 0
    try:
        for agent_id, data in agents.items():
            await pool.execute(
                """INSERT INTO agents (agent_id, eth_address, role, agent_group, verification_tier, reputation_score, bona_fide_balance, capabilities, inference_provider, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                   ON CONFLICT (agent_id) DO UPDATE SET eth_address=$2, role=$3, agent_group=$4, verification_tier=$5, reputation_score=$6, bona_fide_balance=$7, capabilities=$8, inference_provider=$9, updated_at=NOW()""",
                agent_id,
                data.get("eth_address"),
                data.get("role"),
                data.get("group"),
                data.get("verification_tier", 1),
                data.get("reputation_score", 5000),
                data.get("bona_fide_balance", 1),
                data.get("capabilities", []),
                data.get("inference_provider"),
            )
            count += 1
        return count
    except Exception as e:
        logger.debug(f"pgvector sync_agent_registry failed: {e}")
        return count


async def health_check() -> Dict[str, Any]:
    """Check database health."""
    pool = await get_pool()
    if not pool:
        return {"status": "disconnected"}
    try:
        row = await pool.fetchrow(
            """SELECT
                (SELECT COUNT(*) FROM memories) as memories,
                (SELECT COUNT(*) FROM beliefs) as beliefs,
                (SELECT COUNT(*) FROM agents) as agents,
                (SELECT COUNT(*) FROM godel_choices) as godel_choices,
                (SELECT pg_size_pretty(pg_database_size('mindx'))) as db_size"""
        )
        return {
            "status": "connected",
            "memories": row["memories"],
            "beliefs": row["beliefs"],
            "agents": row["agents"],
            "godel_choices": row["godel_choices"],
            "db_size": row["db_size"],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
