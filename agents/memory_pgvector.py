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
import os
import time
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


async def init_offload_schema() -> bool:
    """
    Add IPFS-offload columns to the memories table. Idempotent — safe to call
    on every boot. Plan: ~/.claude/plans/whispering-floating-merkle.md
    """
    pool = await get_pool()
    if not pool:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS content_cid TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS content_cid_mirror TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS offload_tier VARCHAR(16) DEFAULT 'local';
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS offloaded_at TIMESTAMP;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS offload_tx_hash TEXT;
                ALTER TABLE memories ADD COLUMN IF NOT EXISTS offload_chain VARCHAR(16);
                CREATE INDEX IF NOT EXISTS idx_memories_offload_tier ON memories(offload_tier);
                """
            )
        logger.info("pgvector: offload schema columns ensured")
        return True
    except Exception as e:
        logger.warning(f"pgvector init_offload_schema failed: {e}")
        return False


async def init_cost_ledger_schema() -> bool:
    """
    Per-call inference cost ledger. Idempotent — safe to call every boot.
    Captures provider, model, token counts, latency, and an estimated cost in
    USD so mindX can prove its return on inference spend (free calls record
    cost_usd_est=0.0 but still occupy the ledger for ROI accounting).
    """
    pool = await get_pool()
    if not pool:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_ledger (
                    id BIGSERIAL PRIMARY KEY,
                    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    agent_id TEXT,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    task_kind TEXT,
                    tokens_in INT NOT NULL DEFAULT 0,
                    tokens_out INT NOT NULL DEFAULT 0,
                    latency_ms INT,
                    cost_usd_est NUMERIC(14,10) NOT NULL DEFAULT 0,
                    free_tier BOOLEAN NOT NULL DEFAULT FALSE,
                    success BOOLEAN NOT NULL DEFAULT TRUE,
                    call_id UUID
                );
                CREATE INDEX IF NOT EXISTS idx_cost_ledger_ts       ON cost_ledger (ts DESC);
                CREATE INDEX IF NOT EXISTS idx_cost_ledger_agent    ON cost_ledger (agent_id, ts DESC);
                CREATE INDEX IF NOT EXISTS idx_cost_ledger_provider ON cost_ledger (provider, ts DESC);
                """
            )
        logger.info("pgvector: cost_ledger schema ensured")
        return True
    except Exception as e:
        logger.warning(f"pgvector init_cost_ledger_schema failed: {e}")
        return False


async def record_cost(
    provider: str,
    model: str,
    tokens_in: int = 0,
    tokens_out: int = 0,
    latency_ms: Optional[int] = None,
    cost_usd_est: float = 0.0,
    agent_id: Optional[str] = None,
    task_kind: Optional[str] = None,
    free_tier: bool = False,
    success: bool = True,
    call_id: Optional[str] = None,
) -> bool:
    """Append one row to the cost ledger. Best-effort; failures are non-fatal."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            """INSERT INTO cost_ledger
                (agent_id, provider, model, task_kind,
                 tokens_in, tokens_out, latency_ms, cost_usd_est,
                 free_tier, success, call_id)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)""",
            agent_id, provider, model, task_kind,
            int(tokens_in or 0), int(tokens_out or 0),
            latency_ms,
            float(cost_usd_est or 0.0),
            bool(free_tier), bool(success), call_id,
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector record_cost failed: {e}")
        return False


async def cost_summary(window: str = "24h") -> Dict[str, Any]:
    """
    Aggregate per-provider counts, tokens, $$ over a window.
    `window` accepts: '1h', '24h', '7d', '30d'. Returns a totals row + per_provider rows.
    """
    pool = await get_pool()
    if not pool:
        return {"window": window, "totals": {}, "per_provider": []}
    interval_map = {"1h": "1 hour", "24h": "24 hours", "7d": "7 days", "30d": "30 days"}
    interval = interval_map.get(window, "24 hours")
    try:
        totals = await pool.fetchrow(
            f"""SELECT
                COUNT(*) AS calls,
                COALESCE(SUM(tokens_in), 0) AS tokens_in,
                COALESCE(SUM(tokens_out), 0) AS tokens_out,
                COALESCE(SUM(cost_usd_est), 0) AS cost_usd,
                COUNT(*) FILTER (WHERE free_tier) AS free_calls,
                COUNT(*) FILTER (WHERE NOT success) AS errors
              FROM cost_ledger
              WHERE ts >= NOW() - INTERVAL '{interval}'"""
        )
        rows = await pool.fetch(
            f"""SELECT provider,
                       COUNT(*) AS calls,
                       COALESCE(SUM(tokens_in), 0) AS tokens_in,
                       COALESCE(SUM(tokens_out), 0) AS tokens_out,
                       COALESCE(SUM(cost_usd_est), 0) AS cost_usd,
                       COUNT(*) FILTER (WHERE free_tier) AS free_calls
                FROM cost_ledger
                WHERE ts >= NOW() - INTERVAL '{interval}'
                GROUP BY provider
                ORDER BY calls DESC"""
        )
        return {
            "window": window,
            "totals": {
                "calls": int(totals["calls"] or 0) if totals else 0,
                "tokens_in": int(totals["tokens_in"] or 0) if totals else 0,
                "tokens_out": int(totals["tokens_out"] or 0) if totals else 0,
                "tokens_total": int((totals["tokens_in"] or 0) + (totals["tokens_out"] or 0)) if totals else 0,
                "cost_usd": float(totals["cost_usd"] or 0.0) if totals else 0.0,
                "free_calls": int(totals["free_calls"] or 0) if totals else 0,
                "errors": int(totals["errors"] or 0) if totals else 0,
            },
            "per_provider": [
                {
                    "provider": r["provider"],
                    "calls": int(r["calls"]),
                    "tokens_in": int(r["tokens_in"]),
                    "tokens_out": int(r["tokens_out"]),
                    "tokens_total": int(r["tokens_in"] + r["tokens_out"]),
                    "cost_usd": float(r["cost_usd"] or 0.0),
                    "free_calls": int(r["free_calls"]),
                }
                for r in rows
            ],
        }
    except Exception as e:
        logger.debug(f"pgvector cost_summary failed: {e}")
        return {"window": window, "totals": {}, "per_provider": [], "error": str(e)}


async def cost_recent(limit: int = 50) -> List[Dict[str, Any]]:
    """Last `limit` rows of the ledger, newest first."""
    pool = await get_pool()
    if not pool:
        return []
    try:
        rows = await pool.fetch(
            """SELECT ts, agent_id, provider, model, task_kind,
                      tokens_in, tokens_out, latency_ms,
                      cost_usd_est, free_tier, success
               FROM cost_ledger
               ORDER BY ts DESC
               LIMIT $1""",
            int(limit),
        )
        return [
            {
                "ts": r["ts"].isoformat() if r["ts"] else None,
                "agent_id": r["agent_id"],
                "provider": r["provider"],
                "model": r["model"],
                "task_kind": r["task_kind"],
                "tokens_in": int(r["tokens_in"] or 0),
                "tokens_out": int(r["tokens_out"] or 0),
                "tokens_total": int((r["tokens_in"] or 0) + (r["tokens_out"] or 0)),
                "latency_ms": int(r["latency_ms"]) if r["latency_ms"] is not None else None,
                "cost_usd_est": float(r["cost_usd_est"] or 0.0),
                "free_tier": bool(r["free_tier"]),
                "success": bool(r["success"]),
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"pgvector cost_recent failed: {e}")
        return []


async def tokens_total() -> int:
    """All-time token count (in + out) across the ledger. Cheap for the dashboard."""
    pool = await get_pool()
    if not pool:
        return 0
    try:
        row = await pool.fetchrow(
            "SELECT COALESCE(SUM(tokens_in + tokens_out), 0) AS total FROM cost_ledger"
        )
        return int(row["total"]) if row else 0
    except Exception:
        return 0


async def mark_memory_offloaded(
    memory_id: str,
    content_cid: str,
    content_cid_mirror: Optional[str],
    offload_tier: str,
    chain: Optional[str] = None,
    tx_hash: Optional[str] = None,
) -> bool:
    """Update a memory row to record IPFS offload + on-chain anchor."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            """UPDATE memories
               SET content_cid = $2,
                   content_cid_mirror = $3,
                   offload_tier = $4,
                   offload_chain = $5,
                   offload_tx_hash = $6,
                   offloaded_at = NOW()
               WHERE memory_id = $1""",
            memory_id, content_cid, content_cid_mirror, offload_tier, chain, tx_hash,
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector mark_memory_offloaded failed: {e}")
        return False


async def get_offload_stats() -> Dict[str, Any]:
    """Aggregate offload status counts for diagnostics dashboard."""
    pool = await get_pool()
    if not pool:
        return {"local": 0, "ipfs": 0, "thot": 0, "anchored": 0}
    try:
        row = await pool.fetchrow(
            """SELECT
                COUNT(*) FILTER (WHERE offload_tier='local'  OR offload_tier IS NULL) AS local_count,
                COUNT(*) FILTER (WHERE offload_tier='ipfs')  AS ipfs_count,
                COUNT(*) FILTER (WHERE offload_tier='thot')  AS thot_count,
                COUNT(*) FILTER (WHERE offload_tx_hash IS NOT NULL) AS anchored_count,
                MAX(offloaded_at) AS last_offload_ts
               FROM memories"""
        )
        return {
            "local": row["local_count"] or 0,
            "ipfs": row["ipfs_count"] or 0,
            "thot": row["thot_count"] or 0,
            "anchored": row["anchored_count"] or 0,
            "last_offload_ts": row["last_offload_ts"].isoformat() if row["last_offload_ts"] else None,
        }
    except Exception as e:
        logger.debug(f"pgvector get_offload_stats failed: {e}")
        return {"local": 0, "ipfs": 0, "thot": 0, "anchored": 0}


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


async def store_action_if_new(agent_id: str, action_type: str, description: str, source: str = "", status: str = "identified") -> bool:
    """Store action only if no existing action with same description in active status."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        existing = await pool.fetchval(
            "SELECT COUNT(*) FROM actions WHERE LEFT(description, 200) = $1 AND status NOT IN ('completed', 'failed')",
            description[:200],
        )
        if existing and existing > 0:
            return False
        return await store_action(agent_id, action_type, description, source, status)
    except Exception as e:
        logger.debug(f"pgvector store_action_if_new failed: {e}")
        return await store_action(agent_id, action_type, description, source, status)


async def store_action(agent_id: str, action_type: str, description: str, source: str = "", status: str = "pending") -> bool:
    """Log an action taken by an agent."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            "INSERT INTO actions (agent_id, action_type, description, source, status) VALUES ($1,$2,$3,$4,$5)",
            agent_id, action_type, description, source, status,
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector store_action failed: {e}")
        return False


async def complete_action(action_id: int, result: str, status: str = "completed") -> bool:
    """Mark an action as completed."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            "UPDATE actions SET status=$1, result=$2, completed_at=NOW() WHERE id=$3",
            status, result, action_id,
        )
        return True
    except Exception:
        return False


async def get_recent_actions(limit: int = 20) -> List[Dict[str, Any]]:
    """Get recent actions for dashboard display."""
    pool = await get_pool()
    if not pool:
        return []
    try:
        rows = await pool.fetch(
            "SELECT id, agent_id, action_type, description, source, status, result, created_at, completed_at FROM actions ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        return [
            {
                "id": r["id"],
                "agent_id": r["agent_id"],
                "action_type": r["action_type"],
                "description": r["description"][:150],
                "source": r["source"],
                "status": r["status"],
                "result": r["result"][:100] if r["result"] else None,
                "created_at": r["created_at"].isoformat() if r["created_at"] else "",
            }
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"pgvector get_recent_actions failed: {e}")
        return []


# ═══════════════════════════════════════════════════════════════
#  EMBEDDING ENGINE — vLLM primary, Ollama fallback → pgvector
# ═══════════════════════════════════════════════════════════════

# ═══ Embedding model registry — switchable backends ══════════════════════════
# Keep multiple embed models available so the store can be optimized/adapted to
# different data and types. The ACTIVE model is chosen via MINDX_EMBED_MODEL
# (default bge-m3). Truncation and default chunk size DERIVE from the active model
# (below), so switching model auto-adjusts the pipeline.
#
# HARD CONSTRAINT: the pgvector columns are VECTOR(SCHEMA_EMBED_DIMS) (=1024). A
# model whose `dims` != that width cannot be made active without a schema migration
# (ALTER column type) AND a full re-embed. Such models stay in the registry —
# documented, not hidden — and the dim-guard below warns loudly if one is selected.
SCHEMA_EMBED_DIMS = 1024  # width baked into doc_embeddings.embedding / memories.embedding

EMBED_MODELS: Dict[str, Dict[str, Any]] = {
    "bge-m3": {
        "dims": 1024, "context_tokens": 8192, "max_chars": 4000,
        "vllm_id": "BAAI/bge-m3",
        "notes": "DEFAULT. Long-context (8192 tok), 1024-dim → drop-in for VECTOR(1024). "
                 "Best for large chunks / mixed data / multilingual.",
    },
    "mxbai-embed-large": {
        "dims": 1024, "context_tokens": 512, "max_chars": 1400,
        "vllm_id": "mixedbread-ai/mxbai-embed-large-v1",
        "notes": "Short-context (512 tok), high quality, 1024-dim → interchangeable with "
                 "bge-m3 in-schema (re-embed to switch). Good for short passages.",
    },
    "nomic-embed-text": {
        "dims": 768, "context_tokens": 8192, "max_chars": 4000,
        "vllm_id": "nomic-ai/nomic-embed-text-v1.5",
        "notes": "Long-context 768-dim — REQUIRES VECTOR(768) migration + full re-embed before activation.",
    },
    "all-minilm": {
        "dims": 384, "context_tokens": 256, "max_chars": 800,
        "vllm_id": "sentence-transformers/all-MiniLM-L6-v2",
        "notes": "Tiny/fast 384-dim — cheap for high-volume, lower precision; requires VECTOR(384) migration.",
    },
}

EMBED_MODEL = os.getenv("MINDX_EMBED_MODEL", "bge-m3")
_ACTIVE_EMBED = EMBED_MODELS.get(EMBED_MODEL) or EMBED_MODELS["bge-m3"]
EMBED_DIMS = _ACTIVE_EMBED["dims"]
EMBED_CONTEXT_TOKENS = _ACTIVE_EMBED["context_tokens"]

VLLM_EMBED_URL = os.getenv("VLLM_EMBED_URL", "http://localhost:8001")  # vLLM serving embeddings
OLLAMA_EMBED_URL = "http://localhost:11434"  # Ollama fallback
# HuggingFace Inference (remote) — the "use every source" leg: works with no local
# model pulled and no GPU. Gated on a token; the active model's `vllm_id` doubles as
# its HF repo id (e.g. "BAAI/bge-m3"). Uses the feature-extraction pipeline (raw vector).
HF_EMBED_URL = os.getenv("HF_EMBED_URL", "https://router.huggingface.co/hf-inference/models")
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN") or os.getenv("HUGGINGFACEHUB_API_TOKEN")

# Truncate ALL embedding inputs at this single choke point so a pathological input
# can't overflow the model window or run away CPU. Derived from the active model
# (override with MINDX_EMBED_MAX_CHARS). bge-m3: 4000 chars ≈ ~1000 tokens, holds a
# 512-word chunk (~700 tok) well inside the 8192 window. mxbai: 1400 chars ≈ 350 tok
# under its 512 window. Overflow used to return None → row stayed unembedded, retried
# every cycle = sustained CPU churn; truncation here guarantees it can't happen.
_EMBED_MAX_CHARS = int(os.getenv("MINDX_EMBED_MAX_CHARS", str(_ACTIVE_EMBED["max_chars"])))

# Default doc chunk size (words), matched to the active model's window: long-context
# models take big chunks, short-context models stay small to avoid truncation.
DEFAULT_CHUNK_WORDS = 512 if EMBED_CONTEXT_TOKENS >= 2048 else 200

if EMBED_DIMS != SCHEMA_EMBED_DIMS:
    logger.warning(
        "embed: active model '%s' is %d-dim but the pgvector schema is %d-dim — needs an "
        "ALTER + full re-embed before it works; embeddings will fail until reconciled.",
        EMBED_MODEL, EMBED_DIMS, SCHEMA_EMBED_DIMS,
    )


async def _bg_governor(interactive: bool):
    """Return the ResourceGovernor for background dispatch, or None for interactive
    calls / when it's unavailable (fail-open — never block embedding outright)."""
    if interactive:
        return None
    try:
        from agents.resource_governor import ResourceGovernor
        return await ResourceGovernor.get_instance()
    except Exception:
        return None


# ── anti-starvation + failure-noise discipline (the 2026-07-11 productive-state fix) ──
# On a 2-core box whose CPU is ALWAYS busy (resident gen model), "defer until idle"
# never fires: 698/727 embeds in 30 min were cpu_throttled_deferred → memory/RAG
# starved while the journal filled with per-call WARNINGs. Three module-level valves:
#   _vllm_down_until — negative-cache a dead vLLM endpoint (skip the leg 10 min after
#                      a connect error; one probe revives it).
#   _trickle_next    — the STARVATION FLOOR: even when the governor says throttle,
#                      allow one embed per TRICKLE_S (default 10s ≈ 6/min ≈ ~10% of one
#                      core for short texts). Starving memory is worse than 10% load.
#   _warn_state      — roll per-call failure WARNINGs into one summary line per 60s.
_VLLM_COOLDOWN_S = float(os.getenv("MINDX_VLLM_EMBED_COOLDOWN_S", "600"))
_TRICKLE_S = float(os.getenv("MINDX_EMBED_TRICKLE_S", "10"))
# CPU embeds are SLOW (measured: bge-m3 ~57s/chunk on a 2-core box). The old hard-coded
# 30s client timeout guaranteed failure on exactly the hardware mindX runs on.
_EMBED_TIMEOUT_S = float(os.getenv("MINDX_EMBED_TIMEOUT_S", "180"))
_vllm_down_until = 0.0
_trickle_next = 0.0
_warn_state = {"t": 0.0, "n": 0, "last": ""}


def _warn_rollup(msg: str) -> None:
    """One WARNING per 60s summarizing embed failures; the rest stay DEBUG."""
    now = time.monotonic()
    _warn_state["n"] += 1
    _warn_state["last"] = msg
    if now - _warn_state["t"] >= 60.0:
        logger.warning(
            f"generate_embedding: {_warn_state['n']} failure(s) in the last "
            f"{'∞' if not _warn_state['t'] else '60s'} · last: {msg}"
        )
        _warn_state["t"] = now
        _warn_state["n"] = 0
    else:
        logger.debug(f"generate_embedding failure: {msg}")


def _hf_pool(data: Any) -> Optional[List[float]]:
    """Normalize HuggingFace feature-extraction output to a flat 1-D embedding.
    sentence-transformers models (bge-m3) return a 1-D vector; raw models return
    2-D token vectors → mean-pool over tokens. Tolerates an extra [[...]] wrapper."""
    if isinstance(data, list) and data:
        if isinstance(data[0], (int, float)):
            return [float(x) for x in data]
        if isinstance(data[0], list) and data[0]:
            if isinstance(data[0][0], (int, float)):
                n, dim = len(data), len(data[0])
                return [sum(row[i] for row in data) / n for i in range(dim)]
            return _hf_pool(data[0])  # unwrap [[...]]
    return None


async def generate_embedding(
    text: str, model: str = EMBED_MODEL, *, interactive: bool = False
) -> Optional[List[float]]:
    """
    Generate embedding across THREE sources (use every source to advantage):
    vLLM `/v1/embeddings` → Ollama `/api/embeddings` → HuggingFace Inference
    `feature-extraction` (remote, gated on HF_TOKEN; works with no local model /
    no GPU). Returns None only if all available sources fail, with a WARNING-level
    log of every leg's status (not the old DEBUG silence that hid backfill failures).

    The Ollama (CPU) fallback is serialized through the ResourceGovernor's
    background-only inference semaphore so concurrent background embeds can't
    peg both cores and starve the web service. Pass interactive=True for
    web-triggered embeds (e.g. a live RAGE query) to bypass the gate.
    """
    import aiohttp
    text = text[:_EMBED_MAX_CHARS]

    vllm_status = ollama_status = None

    # 1. Try vLLM (fast, batched, production) — negative-cached: a dead endpoint is
    #    skipped for _VLLM_COOLDOWN_S rather than re-erroring on every call.
    global _vllm_down_until, _trickle_next
    if time.monotonic() < _vllm_down_until:
        vllm_status = "cooldown_skip"
    else:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as sess:
                payload = {"model": model, "input": text[:8000]}
                async with sess.post(f"{VLLM_EMBED_URL}/v1/embeddings", json=payload) as resp:
                    vllm_status = resp.status
                    if resp.status == 200:
                        data = await resp.json()
                        emb_data = data.get("data", [])
                        if emb_data and "embedding" in emb_data[0]:
                            return emb_data[0]["embedding"]
        except Exception as e:
            vllm_status = f"err:{type(e).__name__}"
            if "Connect" in type(e).__name__ or "ConnectionRefused" in str(e):
                _vllm_down_until = time.monotonic() + _VLLM_COOLDOWN_S

    # 2. Fallback to Ollama (reliable, CPU). This shares the processor with
    #    web-serving: when the box is over the CPU ceiling, DEFER the embed (return
    #    None → retried at a lower-load moment) rather than pile onto a saturated
    #    ollama and thrash. Otherwise serialize through the background-only
    #    semaphore. Interactive (web-triggered) embeds bypass both.
    import contextlib
    try:
        gov = await _bg_governor(interactive)
        throttled = gov is not None and gov.should_throttle()
        if throttled and time.monotonic() >= _trickle_next:
            # the STARVATION FLOOR: on a box that is never idle, "defer until idle"
            # starves memory forever — let one embed through per _TRICKLE_S anyway.
            _trickle_next = time.monotonic() + _TRICKLE_S
            throttled = False
        if throttled:
            ollama_status = "cpu_throttled_deferred"
        else:
            slot = gov.inference_slot() if gov is not None else contextlib.nullcontext()
            async with slot:
                # CPU-REALITY TIMEOUT (2026-07-11): the old 30s ceiling was SHORTER than a
                # real CPU embed. Measured on the 2-core class of box mindX actually runs on:
                # bge-m3 (566M, F16) takes ~57s for a 500-word chunk; mxbai ~15-40s under load.
                # Every over-budget embed died as TimeoutError → None → "0 chunks embedded",
                # so a doc corpus silently never landed (149/221 surfaces in the 2026-07-11
                # DeltaVerse backfill). The wall-clock cost of waiting is real work completing;
                # the cost of timing out is the SAME CPU burned for nothing. Override with
                # MINDX_EMBED_TIMEOUT_S.
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=_EMBED_TIMEOUT_S)) as sess:
                    async with sess.post(f"{OLLAMA_EMBED_URL}/api/embeddings", json={"model": model, "prompt": text[:8000]}) as resp:
                        ollama_status = resp.status
                        if resp.status == 200:
                            data = await resp.json()
                            emb = data.get("embedding")
                            if emb:
                                return emb
                            ollama_status = "200_empty"
                        else:
                            # Read body once for diagnostics (Ollama returns 500 with a JSON body
                            # for context-overflow — surface it so the operator can act).
                            body = (await resp.text())[:200] if resp.status >= 400 else ""
                            ollama_status = f"{resp.status}:{body}"
    except Exception as e:
        ollama_status = f"err:{type(e).__name__}"

    # 3. Fallback to HuggingFace Inference (remote, needs HF_TOKEN). Works when no
    #    local model is pulled and no GPU is present — the "use every source" leg.
    #    feature-extraction returns the raw vector (NOT sentence-similarity, which
    #    returns scores). vllm_id doubles as the HF repo id (e.g. BAAI/bge-m3).
    hf_status = None
    if HF_TOKEN:
        try:
            hf_id = _ACTIVE_EMBED.get("vllm_id", model)
            url = f"{HF_EMBED_URL}/{hf_id}/pipeline/feature-extraction"
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as sess:
                async with sess.post(
                    url,
                    headers={"Authorization": f"Bearer {HF_TOKEN}"},
                    json={"inputs": text, "options": {"wait_for_model": True}},
                ) as resp:
                    hf_status = resp.status
                    if resp.status == 200:
                        vec = _hf_pool(await resp.json())
                        if vec and len(vec) == EMBED_DIMS:
                            return vec
                        hf_status = f"200_baddim:{len(vec) if vec else 0}!={EMBED_DIMS}"
                    else:
                        hf_status = f"{resp.status}:{(await resp.text())[:160]}"
        except Exception as e:
            hf_status = f"err:{type(e).__name__}"

    _warn_rollup(
        f"generate_embedding({model}, len={len(text)}): vLLM={vllm_status} "
        f"ollama={ollama_status} hf={hf_status if HF_TOKEN else 'no_token'}"
    )
    return None


# chunk_size (words) defaults to DEFAULT_CHUNK_WORDS, matched to the active embed
# model's window (bge-m3 8192 tok → 512 words; mxbai 512 tok → 200). Each chunk is
# still hard-truncated at _EMBED_MAX_CHARS in generate_embedding(), so an over-long
# chunk can't overflow the window. (Historical failure: chunk_size=500 on mxbai's
# 512-token window produced 600-900 tokens → HTTP 500 per chunk, logged only at
# DEBUG, 105/210 docs unembedded. See 2026-04-29 backfill diagnosis. The registry +
# derived chunk size prevent that class of mismatch.)
async def embed_and_store_doc(doc_name: str, text_content: str, chunk_size: int = DEFAULT_CHUNK_WORDS,
                              interactive: bool = False, bail_on_first_failure: bool = False) -> int:
    """Chunk a document and store embeddings in doc_embeddings table.

    interactive=True bypasses the ResourceGovernor CPU-throttle/semaphore —
    only for operator-supervised backfills (e.g. scripts/ingest_reference_docs
    --aggressive); unattended callers must stay governor-respecting.

    bail_on_first_failure=True returns 0 the moment the first chunk fails to
    embed — so a caller walking a chunk-size ladder (THOT descent) drops to a
    smaller size after one failed embed instead of failing every chunk of a
    large doc at an oversized window first."""
    pool = await get_pool()
    if not pool:
        return 0

    # Chunk by words
    words = text_content.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        if len(chunk.strip()) > 50:  # Skip tiny chunks
            chunks.append(chunk)

    if not chunks:
        return 0

    stored = 0
    embed_failures = 0
    insert_failures = 0
    for idx, chunk in enumerate(chunks):
        emb = await generate_embedding(chunk, interactive=interactive)
        if emb is None:
            embed_failures += 1
            if bail_on_first_failure and stored == 0:
                return 0  # window too big — let the caller descend the ladder
            continue
        try:
            await pool.execute(
                """INSERT INTO doc_embeddings (doc_name, chunk_idx, text_content, embedding)
                   VALUES ($1, $2, $3, $4::vector)
                   ON CONFLICT (doc_name, chunk_idx) DO UPDATE SET text_content=$3, embedding=$4::vector""",
                doc_name, idx, chunk, str(emb),
            )
            stored += 1
        except Exception as e:
            insert_failures += 1
            logger.warning(f"embed_and_store_doc INSERT failed for {doc_name} chunk={idx}: {e}")

    if stored == 0 and chunks:
        logger.warning(
            f"embed_and_store_doc({doc_name}): 0/{len(chunks)} chunks stored "
            f"(embed_failures={embed_failures}, insert_failures={insert_failures})"
        )
    elif stored > 0:
        # Surface embedding as visible mindX work — flows to the catalogue and
        # the landing page's "Logs → Memories" stream. Best-effort; an emit
        # failure must never break a backfill.
        try:
            from agents.catalogue.events import emit_catalogue_event
            top = doc_name.split("/", 1)[0] if "/" in doc_name else "doc"
            await emit_catalogue_event(
                kind="memory.embed",
                actor="reference_corpus" if top in ("operations", "blockchain", "publications") else "pgvector.embedder",
                payload={"doc_name": doc_name, "chunks": stored, "chunk_size": chunk_size},
                source_log="memory_pgvector.embed_and_store_doc",
                source_ref=doc_name,
            )
        except Exception:
            pass
    return stored


async def embed_memory(memory_id: str, text: str) -> bool:
    """Generate embedding for a memory and store in the memories.embedding column."""
    pool = await get_pool()
    if not pool:
        return False
    emb = await generate_embedding(text[:4000])
    if not emb:
        return False
    try:
        await pool.execute(
            "UPDATE memories SET embedding = $1::vector WHERE memory_id = $2",
            str(emb), memory_id,
        )
        return True
    except Exception as e:
        logger.debug(f"Memory embedding failed: {e}")
        return False


async def semantic_search_docs(query: str, top_k: int = 5,
                               exclude_doc_prefixes: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Semantic search over doc_embeddings using cosine similarity.

    exclude_doc_prefixes: doc_name prefixes excluded in SQL (case-insensitive).
    Public surfaces pass the reference-corpus prefixes so gated docs never
    surface — the filter must run in SQL, not post-hoc, or private chunks
    would displace public ones inside top_k.
    """
    pool = await get_pool()
    if not pool:
        return []
    emb = await generate_embedding(query)
    if not emb:
        return []
    try:
        exclude_sql = ""
        params: List[Any] = [str(emb), top_k]
        for prefix in (exclude_doc_prefixes or []):
            params.append(prefix.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%")
            exclude_sql += f" AND doc_name NOT ILIKE ${len(params)}"
        rows = await pool.fetch(
            f"""SELECT doc_name, chunk_idx, text_content,
                      1 - (embedding <=> $1::vector) as similarity
               FROM doc_embeddings
               WHERE embedding IS NOT NULL{exclude_sql}
               ORDER BY embedding <=> $1::vector
               LIMIT $2""",
            *params,
        )
        return [
            {"doc": r["doc_name"], "chunk": r["chunk_idx"],
             "text": r["text_content"][:500], "similarity": round(float(r["similarity"]), 4)}
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"Doc semantic search failed: {e}")
        return []


async def semantic_search_memories(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Semantic search over memories with embeddings."""
    pool = await get_pool()
    if not pool:
        return []
    emb = await generate_embedding(query)
    if not emb:
        return []
    try:
        rows = await pool.fetch(
            """SELECT memory_id, agent_id, memory_type, content,
                      1 - (embedding <=> $1::vector) as similarity
               FROM memories
               WHERE embedding IS NOT NULL
               ORDER BY embedding <=> $1::vector
               LIMIT $2""",
            str(emb), top_k,
        )
        return [
            {"memory_id": r["memory_id"], "agent_id": r["agent_id"],
             "content": json.loads(r["content"]) if isinstance(r["content"], str) else r["content"],
             "similarity": round(float(r["similarity"]), 4)}
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"Memory semantic search failed: {e}")
        return []


async def log_interaction(from_agent: str, to_agent: str, interaction_type: str,
                          topic: str = "", summary: str = "") -> bool:
    """Log an agent-to-agent interaction."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            "INSERT INTO agent_interactions (from_agent, to_agent, interaction_type, topic, summary) VALUES ($1,$2,$3,$4,$5)",
            from_agent, to_agent, interaction_type, topic, summary[:500],
        )
        return True
    except Exception as e:
        logger.debug(f"pgvector log_interaction failed: {e}")
        return False


async def get_recent_interactions(limit: int = 30) -> List[Dict[str, Any]]:
    """Get recent agent-to-agent interactions for diagnostics."""
    pool = await get_pool()
    if not pool:
        return []
    try:
        rows = await pool.fetch(
            "SELECT from_agent, to_agent, interaction_type, topic, summary, created_at FROM agent_interactions ORDER BY created_at DESC LIMIT $1",
            limit,
        )
        return [
            {"from": r["from_agent"], "to": r["to_agent"], "type": r["interaction_type"],
             "topic": r["topic"], "summary": r["summary"][:100] if r["summary"] else "",
             "ts": r["created_at"].strftime("%H:%M:%S") if r["created_at"] else ""}
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"pgvector get_recent_interactions failed: {e}")
        return []


async def get_interaction_matrix() -> Dict[str, Any]:
    """Get agent interaction frequency matrix for visualization."""
    pool = await get_pool()
    if not pool:
        return {"edges": [], "agents": []}
    try:
        rows = await pool.fetch(
            """SELECT from_agent, to_agent, interaction_type, COUNT(*) as count
               FROM agent_interactions
               GROUP BY from_agent, to_agent, interaction_type
               ORDER BY count DESC LIMIT 50"""
        )
        agents = set()
        edges = []
        for r in rows:
            agents.add(r["from_agent"])
            agents.add(r["to_agent"])
            edges.append({"from": r["from_agent"], "to": r["to_agent"],
                         "type": r["interaction_type"], "count": r["count"]})
        return {"edges": edges, "agents": sorted(agents)}
    except Exception as e:
        logger.debug(f"pgvector get_interaction_matrix failed: {e}")
        return {"edges": [], "agents": []}


async def get_action_efficiency() -> Dict[str, Any]:
    """Measure action pipeline efficiency metrics."""
    pool = await get_pool()
    if not pool:
        return {}
    try:
        row = await pool.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status='identified') as identified,
                COUNT(*) FILTER (WHERE status='completed') as completed,
                COUNT(*) FILTER (WHERE status='failed') as failed,
                COUNT(*) FILTER (WHERE status='pending') as pending,
                COUNT(DISTINCT LEFT(description,100)) as unique_descriptions,
                EXTRACT(EPOCH FROM AVG(completed_at - created_at) FILTER (WHERE completed_at IS NOT NULL)) as avg_completion_secs
            FROM actions
        """)
        total = row["total"] or 0
        unique = row["unique_descriptions"] or 0
        return {
            "total": total,
            "identified": row["identified"] or 0,
            "completed": row["completed"] or 0,
            "failed": row["failed"] or 0,
            "pending": row["pending"] or 0,
            "completion_rate": round((row["completed"] or 0) / max(total, 1), 3),
            "duplicate_rate": round(1 - (unique / max(total, 1)), 3),
            "avg_completion_seconds": round(row["avg_completion_secs"] or 0, 1),
            "unique_actions": unique,
        }
    except Exception as e:
        logger.warning(f"pgvector get_action_efficiency failed: {e}")
        return {"error": str(e)}


async def get_indexed_docs() -> List[Dict[str, Any]]:
    """List all documents indexed in doc_embeddings with chunk counts."""
    pool = await get_pool()
    if not pool:
        return []
    try:
        rows = await pool.fetch(
            """SELECT doc_name, COUNT(*) as chunks,
                      SUM(LENGTH(text_content)) as total_chars
               FROM doc_embeddings
               WHERE embedding IS NOT NULL
               GROUP BY doc_name
               ORDER BY doc_name"""
        )
        return [
            {"doc_name": r["doc_name"], "chunks": r["chunks"],
             "size_kb": round(r["total_chars"] / 1024, 1)}
            for r in rows
        ]
    except Exception as e:
        logger.debug(f"get_indexed_docs failed: {e}")
        return []


async def count_embeddings() -> Dict[str, int]:
    """Count embeddings in doc and memory tables."""
    pool = await get_pool()
    if not pool:
        return {"docs": 0, "memories": 0}
    try:
        row = await pool.fetchrow(
            """SELECT
                (SELECT COUNT(*) FROM doc_embeddings WHERE embedding IS NOT NULL) as docs,
                (SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL) as memories"""
        )
        return {"docs": row["docs"], "memories": row["memories"]}
    except Exception:
        return {"docs": 0, "memories": 0}


async def health_check() -> Dict[str, Any]:
    """Check database health.

    The old version ran eight exact COUNT(*)s (incl. two filtered scans over 100k+
    rows) in ONE query, which exceeded the 3s diagnostics timeout under load and left
    the dashboard `database` panel blank. This version stays well under a second:
      - secondary counts (beliefs/agents/godel/actions) use pg_class.reltuples
        planner estimates (no scan);
      - the headline `memories` count and the embedding counts reuse the
        proven-fast single-purpose queries (count_memories_total / count_embeddings);
      - db_size uses current_database() so it is portable.
    """
    pool = await get_pool()
    if not pool:
        return {"status": "disconnected"}

    def _i(v) -> int:
        try:
            n = int(v)
            return n if n > 0 else 0
        except (TypeError, ValueError):
            return 0

    try:
        # Single INSTANT query against the stats collector — n_live_tup is maintained
        # live (no table scan), so this stays sub-100ms even on 300k-row tables. The
        # old exact/combined COUNT(*) over memories + filtered embedding scans took
        # multiple seconds and timed out under load, blanking the dashboard panel.
        rows = await pool.fetch(
            "SELECT relname, n_live_tup FROM pg_stat_user_tables "
            "WHERE relname = ANY($1::text[])",
            ["memories", "beliefs", "agents", "godel_choices", "actions", "doc_embeddings"],
        )
        c = {r["relname"]: _i(r["n_live_tup"]) for r in rows}
        db_size = await pool.fetchval(
            "SELECT pg_size_pretty(pg_database_size(current_database()))"
        )
        return {
            "status": "connected",
            "memories": c.get("memories", 0),
            "beliefs": c.get("beliefs", 0),
            "agents": c.get("agents", 0),
            "godel_choices": c.get("godel_choices", 0),
            "actions": c.get("actions", 0),
            "doc_embeddings": c.get("doc_embeddings", 0),
            # approximate (≈ total memories); the dashboard prefers the exact
            # rage_embed.memories count when present.
            "mem_embeddings": c.get("memories", 0),
            "db_size": db_size,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


# ═══════════════════════════════════════════════════════════════
#  KNOWLEDGE CATALOGUE — Phase 1 read-model (CQRS projection)
#  Projection over data/logs/catalogue_events.jsonl. NEVER the source of
#  truth; rebuildable by replaying the log. See docs/KNOWLEDGE_CATALOGUE.md
#  and agents/catalogue/{model,projector}.py.
# ═══════════════════════════════════════════════════════════════

# Stable 64-bit advisory-lock key so the live projector loop and a manually-run
# backfill cannot interleave writes to catalogue_state.
_CATALOGUE_LOCK_KEY = 0x6D696E6478636174  # "mindxcat"


async def init_catalogue_schema() -> bool:
    """Create the catalogue read-model tables. Idempotent — safe every boot.

    One flat ``catalogue_entries`` table (DataHub entity-aspect collapse,
    simplified): aspects live in JSONB ``payload``, EntryLinks inline in
    ``links``, BM25 leg via ``fts`` tsvector, dense leg via ``embedding``
    (VECTOR(1024), active embed model — default bge-m3, see EMBED_MODELS registry),
    NULL until embedded. No ivfflat index
    at Phase-1 scale (<100k rows) — cosine seq-scan is sub-100ms.
    """
    pool = await get_pool()
    if not pool:
        return False
    try:
        async with pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS catalogue_entries (
                    urn              TEXT PRIMARY KEY,
                    kind             TEXT NOT NULL,
                    actor            TEXT,
                    actor_wallet     TEXT,
                    ts               DOUBLE PRECISION NOT NULL DEFAULT 0,
                    title            TEXT,
                    text             TEXT,
                    payload          JSONB NOT NULL DEFAULT '{}'::jsonb,
                    tags             TEXT[] NOT NULL DEFAULT '{}',
                    links            JSONB NOT NULL DEFAULT '[]'::jsonb,
                    source_event_ids TEXT[] NOT NULL DEFAULT '{}',
                    embedding        VECTOR(1024),
                    fts              TSVECTOR,
                    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                CREATE INDEX IF NOT EXISTS idx_cat_kind  ON catalogue_entries (kind, ts DESC);
                CREATE INDEX IF NOT EXISTS idx_cat_ts    ON catalogue_entries (ts DESC);
                CREATE INDEX IF NOT EXISTS idx_cat_actor ON catalogue_entries (actor, ts DESC);
                CREATE INDEX IF NOT EXISTS idx_cat_tags  ON catalogue_entries USING GIN (tags);
                CREATE INDEX IF NOT EXISTS idx_cat_fts   ON catalogue_entries USING GIN (fts);

                CREATE TABLE IF NOT EXISTS catalogue_state (
                    projector       TEXT PRIMARY KEY,
                    version         TEXT NOT NULL DEFAULT 'v1',
                    byte_offset     BIGINT NOT NULL DEFAULT 0,
                    last_event_id   TEXT,
                    events_seen     BIGINT NOT NULL DEFAULT 0,
                    entries_written BIGINT NOT NULL DEFAULT 0,
                    observed_kinds  JSONB NOT NULL DEFAULT '[]'::jsonb,
                    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                ALTER TABLE catalogue_state
                    ADD COLUMN IF NOT EXISTS observed_kinds JSONB NOT NULL DEFAULT '[]'::jsonb;

                -- Lineage graph (Tier A #1): the inline EntryLinks materialized as
                -- indexed edges for bidirectional traversal. src --type--> dst means
                -- "src derivedFrom/producedBy/wasInformedBy/scored dst" — i.e. dst is
                -- the ancestor/source. Additive (invalidate-never-delete): provenance
                -- edges only accrue. Rebuildable from catalogue_entries.links.
                CREATE TABLE IF NOT EXISTS catalogue_edges (
                    src_urn   TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    dst_urn   TEXT NOT NULL,
                    ts        DOUBLE PRECISION NOT NULL DEFAULT 0,
                    PRIMARY KEY (src_urn, edge_type, dst_urn)
                );
                CREATE INDEX IF NOT EXISTS idx_cat_edges_src  ON catalogue_edges (src_urn);
                CREATE INDEX IF NOT EXISTS idx_cat_edges_dst  ON catalogue_edges (dst_urn);
                CREATE INDEX IF NOT EXISTS idx_cat_edges_type ON catalogue_edges (edge_type);
                """
            )
        logger.info("pgvector: catalogue schema ensured (catalogue_entries + catalogue_state)")
        return True
    except Exception as e:
        logger.warning(f"pgvector init_catalogue_schema failed: {e}")
        return False


async def try_catalogue_lock() -> bool:
    """Take the catalogue projector advisory lock (non-blocking). Returns True
    if acquired. Hold the SAME connection for the run; release with the pool."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        return bool(await pool.fetchval("SELECT pg_try_advisory_lock($1)", _CATALOGUE_LOCK_KEY))
    except Exception as e:
        logger.debug(f"try_catalogue_lock failed: {e}")
        return False


async def release_catalogue_lock() -> None:
    pool = await get_pool()
    if not pool:
        return
    try:
        await pool.fetchval("SELECT pg_advisory_unlock($1)", _CATALOGUE_LOCK_KEY)
    except Exception:
        pass


async def get_catalogue_watermark(projector: str = "entries") -> Dict[str, Any]:
    """Return the projector's resume state, or defaults if unseen."""
    pool = await get_pool()
    if not pool:
        return {}
    try:
        row = await pool.fetchrow(
            "SELECT projector, version, byte_offset, last_event_id, events_seen, "
            "entries_written, observed_kinds "
            "FROM catalogue_state WHERE projector = $1", projector,
        )
        if not row:
            return {"projector": projector, "version": None, "byte_offset": 0,
                    "last_event_id": None, "events_seen": 0, "entries_written": 0,
                    "observed_kinds": []}
        d = dict(row)
        ok = d.get("observed_kinds")
        d["observed_kinds"] = json.loads(ok) if isinstance(ok, str) else (ok or [])
        return d
    except Exception as e:
        logger.debug(f"get_catalogue_watermark failed: {e}")
        return {}


async def set_catalogue_watermark(projector: str, version: str, byte_offset: int,
                                  last_event_id: Optional[str], events_seen: int,
                                  entries_written: int,
                                  observed_kinds: Optional[List[str]] = None) -> bool:
    """Persist the projector resume point. ``observed_kinds`` (the distinct
    EventKinds seen this run) is UNIONed into the stored set — the drift-free
    source of truth for which kinds are actually emitted."""
    pool = await get_pool()
    if not pool:
        return False
    try:
        await pool.execute(
            """INSERT INTO catalogue_state
                   (projector, version, byte_offset, last_event_id, events_seen,
                    entries_written, observed_kinds, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7::jsonb, NOW())
               ON CONFLICT (projector) DO UPDATE SET
                   version=$2, byte_offset=$3, last_event_id=$4,
                   events_seen=$5, entries_written=$6,
                   observed_kinds = (
                       SELECT COALESCE(jsonb_agg(DISTINCT e), '[]'::jsonb)
                       FROM jsonb_array_elements_text(
                           catalogue_state.observed_kinds || EXCLUDED.observed_kinds) AS e
                   ),
                   updated_at=NOW()""",
            projector, version, int(byte_offset), last_event_id,
            int(events_seen), int(entries_written),
            json.dumps(sorted(set(observed_kinds or []))),
        )
        return True
    except Exception as e:
        logger.warning(f"set_catalogue_watermark failed: {e}")
        return False


async def upsert_catalogue_entry(
    *, urn: str, kind: str, actor: Optional[str], actor_wallet: Optional[str],
    ts: float, title: Optional[str], text: Optional[str], payload: Dict[str, Any],
    tags: List[str], links: List[Dict[str, Any]], source_event_id: str,
    embedding: Optional[List[float]] = None, materialize_edges: bool = True,
) -> bool:
    """Idempotent upsert keyed by URN. Re-projecting the same source record is a
    no-op merge (source_event_ids deduped, newest ts kept). A NULL embedding on
    re-projection does NOT wipe an existing one (COALESCE)."""
    pool = await get_pool()
    if not pool:
        return False
    fts_text = f"{title or ''} {text or ''}".strip()[:8000]
    emb_str = str(embedding) if embedding else None
    try:
        await pool.execute(
            """
            INSERT INTO catalogue_entries
                (urn, kind, actor, actor_wallet, ts, title, text, payload, tags, links,
                 source_event_ids, embedding, fts, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb,$9,$10::jsonb,
                    ARRAY[$11]::text[], $12::vector, to_tsvector('english',$13), NOW(), NOW())
            ON CONFLICT (urn) DO UPDATE SET
                kind  = EXCLUDED.kind,
                actor = COALESCE(EXCLUDED.actor, catalogue_entries.actor),
                actor_wallet = COALESCE(EXCLUDED.actor_wallet, catalogue_entries.actor_wallet),
                ts    = GREATEST(catalogue_entries.ts, EXCLUDED.ts),
                title = COALESCE(EXCLUDED.title, catalogue_entries.title),
                text  = COALESCE(EXCLUDED.text, catalogue_entries.text),
                payload = EXCLUDED.payload,
                tags  = EXCLUDED.tags,
                links = EXCLUDED.links,
                source_event_ids = (
                    SELECT array_agg(DISTINCT e)
                    FROM unnest(catalogue_entries.source_event_ids || EXCLUDED.source_event_ids) AS e
                ),
                embedding = COALESCE(EXCLUDED.embedding, catalogue_entries.embedding),
                fts   = EXCLUDED.fts,
                updated_at = NOW()
            """,
            urn, kind, actor, actor_wallet, float(ts or 0.0), title, text,
            json.dumps(payload, default=str), list(tags or []),
            json.dumps(links or [], default=str), source_event_id, emb_str, fts_text,
        )
        # Materialize lineage edges inline (cheap for the live trickle of a few
        # entries/tick). Bulk backfill sets materialize_edges=False and calls the
        # set-based rebuild_catalogue_edges() once at the end instead — per-entry
        # inserts over 77k rows are pathologically slow.
        if materialize_edges and links:
            rows = [(urn, str(l.get("type") or "related"), str(l.get("target_urn") or ""),
                     float(ts or 0.0)) for l in links if l.get("target_urn")]
            if rows:
                await pool.executemany(
                    "INSERT INTO catalogue_edges (src_urn, edge_type, dst_urn, ts) "
                    "VALUES ($1,$2,$3,$4) ON CONFLICT DO NOTHING", rows)
        return True
    except Exception as e:
        logger.warning(f"upsert_catalogue_entry({urn}) failed: {e}")
        return False


async def rebuild_catalogue_edges() -> int:
    """Backfill catalogue_edges from existing catalogue_entries.links in one pass.
    Idempotent (ON CONFLICT DO NOTHING). Returns the edge count after the rebuild."""
    pool = await get_pool()
    if not pool:
        return 0
    try:
        await pool.execute(
            """INSERT INTO catalogue_edges (src_urn, edge_type, dst_urn, ts)
               SELECT e.urn, l->>'type', l->>'target_urn', e.ts
               FROM catalogue_entries e,
                    LATERAL jsonb_array_elements(e.links) AS l
               WHERE jsonb_typeof(e.links) = 'array'
                 AND jsonb_array_length(e.links) > 0
                 AND l->>'target_urn' IS NOT NULL
               ON CONFLICT DO NOTHING""")
        n = await pool.fetchval("SELECT COUNT(*) FROM catalogue_edges")
        logger.info(f"pgvector: catalogue_edges rebuilt — {n} edges")
        return int(n or 0)
    except Exception as e:
        logger.warning(f"rebuild_catalogue_edges failed: {e}")
        return 0


async def catalogue_lineage(urn: str, direction: str = "both",
                            depth: int = 6) -> Dict[str, Any]:
    """Traverse the lineage graph from ``urn``. Bounded BFS (depth cap 20).

    direction:
      - ancestors   — what this entry derives from / was produced by (out-edges)
      - descendants — what derived from / was produced by this entry (in-edges)
      - both        — both (default)

    Returns {urn, root, ancestors:[edge], descendants:[edge], nodes:{urn:{kind,title}},
    counts}. Each edge = {src_urn, edge_type, dst_urn, depth}. ``nodes`` resolves the
    materialized entries; URNs absent from it are dangling provenance refs (expected —
    a claimed source whose entry isn't projected/keyed identically)."""
    pool = await get_pool()
    if not pool:
        return {"urn": urn, "ancestors": [], "descendants": [], "nodes": {}}
    depth = max(1, min(int(depth or 6), 20))

    async def _walk(anchor_col: str, follow_col: str) -> List[Dict[str, Any]]:
        # anchor_col/follow_col ∈ {src_urn,dst_urn}: walk from the anchor side
        # outward along the opposite side, depth-bounded, cycle-safe via path.
        sql = f"""
            WITH RECURSIVE walk(src_urn, edge_type, dst_urn, depth, path) AS (
                SELECT src_urn, edge_type, dst_urn, 1, ARRAY[{anchor_col}]
                FROM catalogue_edges WHERE {anchor_col} = $1
                UNION ALL
                SELECT e.src_urn, e.edge_type, e.dst_urn, w.depth + 1,
                       w.path || e.{anchor_col}
                FROM catalogue_edges e
                JOIN walk w ON e.{anchor_col} = w.{follow_col}
                WHERE w.depth < $2 AND NOT e.{anchor_col} = ANY(w.path)
            )
            SELECT DISTINCT src_urn, edge_type, dst_urn, depth
            FROM walk ORDER BY depth, src_urn
        """
        rows = await pool.fetch(sql, urn, depth)
        return [{"src_urn": r["src_urn"], "edge_type": r["edge_type"],
                 "dst_urn": r["dst_urn"], "depth": r["depth"]} for r in rows]

    ancestors = descendants = []
    if direction in ("ancestors", "both"):
        ancestors = await _walk("src_urn", "dst_urn")
    if direction in ("descendants", "both"):
        descendants = await _walk("dst_urn", "src_urn")

    # Hydrate node metadata for every URN that appears.
    urns = {urn}
    for e in ancestors + descendants:
        urns.add(e["src_urn"]); urns.add(e["dst_urn"])
    nodes: Dict[str, Any] = {}
    try:
        meta = await pool.fetch(
            "SELECT urn, kind, title, actor, ts FROM catalogue_entries WHERE urn = ANY($1)",
            list(urns))
        nodes = {r["urn"]: {"kind": r["kind"], "title": r["title"],
                            "actor": r["actor"], "ts": r["ts"]} for r in meta}
    except Exception as e:
        logger.debug(f"catalogue_lineage hydrate failed: {e}")

    return {"urn": urn, "direction": direction, "depth": depth,
            "root": nodes.get(urn), "found": urn in nodes,
            "ancestors": ancestors, "descendants": descendants, "nodes": nodes,
            "counts": {"ancestors": len(ancestors), "descendants": len(descendants),
                       "nodes": len(nodes), "dangling": len(urns) - len(nodes)}}


async def catalogue_edges_count() -> int:
    pool = await get_pool()
    if not pool:
        return 0
    try:
        return int(await pool.fetchval("SELECT COUNT(*) FROM catalogue_edges") or 0)
    except Exception:
        return 0


async def embed_catalogue_entry(urn: str, embedding: List[float]) -> bool:
    """Attach an embedding to an existing catalogue entry (deferred-embed path)."""
    pool = await get_pool()
    if not pool or not embedding:
        return False
    try:
        await pool.execute(
            "UPDATE catalogue_entries SET embedding=$1::vector, updated_at=NOW() WHERE urn=$2",
            str(embedding), urn,
        )
        return True
    except Exception as e:
        logger.debug(f"embed_catalogue_entry failed: {e}")
        return False


async def catalogue_unembedded(limit: int = 200) -> List[Dict[str, Any]]:
    """Text-bearing entries still missing an embedding (for the live embed sweep)."""
    pool = await get_pool()
    if not pool:
        return []
    try:
        rows = await pool.fetch(
            "SELECT urn, text FROM catalogue_entries "
            "WHERE embedding IS NULL AND text IS NOT NULL AND length(text) > 0 "
            "ORDER BY ts DESC LIMIT $1", limit,
        )
        return [{"urn": r["urn"], "text": r["text"]} for r in rows]
    except Exception as e:
        logger.debug(f"catalogue_unembedded failed: {e}")
        return []


async def catalogue_recent(limit: int = 50, kind: Optional[str] = None) -> List[Dict[str, Any]]:
    pool = await get_pool()
    if not pool:
        return []
    try:
        if kind:
            rows = await pool.fetch(
                "SELECT urn, kind, actor, ts, title, tags FROM catalogue_entries "
                "WHERE kind=$1 ORDER BY ts DESC LIMIT $2", kind, min(limit, 500))
        else:
            rows = await pool.fetch(
                "SELECT urn, kind, actor, ts, title, tags FROM catalogue_entries "
                "ORDER BY ts DESC LIMIT $1", min(limit, 500))
        return [{"urn": r["urn"], "kind": r["kind"], "actor": r["actor"],
                 "ts": r["ts"], "title": r["title"], "tags": list(r["tags"] or [])}
                for r in rows]
    except Exception as e:
        logger.debug(f"catalogue_recent failed: {e}")
        return []


async def catalogue_entry_by_urn(urn: str) -> Optional[Dict[str, Any]]:
    pool = await get_pool()
    if not pool:
        return None
    try:
        r = await pool.fetchrow(
            "SELECT urn, kind, actor, actor_wallet, ts, title, text, payload, tags, links, "
            "source_event_ids, (embedding IS NOT NULL) AS embedded "
            "FROM catalogue_entries WHERE urn=$1", urn)
        if not r:
            return None
        def _j(v):
            return json.loads(v) if isinstance(v, str) else v
        return {"urn": r["urn"], "kind": r["kind"], "actor": r["actor"],
                "actor_wallet": r["actor_wallet"], "ts": r["ts"], "title": r["title"],
                "text": r["text"], "payload": _j(r["payload"]), "tags": list(r["tags"] or []),
                "links": _j(r["links"]), "source_event_ids": list(r["source_event_ids"] or []),
                "embedded": r["embedded"]}
    except Exception as e:
        logger.debug(f"catalogue_entry_by_urn failed: {e}")
        return None


async def catalogue_stats() -> Dict[str, Any]:
    pool = await get_pool()
    if not pool:
        return {"status": "no_pool"}
    try:
        total = await pool.fetchval("SELECT COUNT(*) FROM catalogue_entries")
        embedded = await pool.fetchval("SELECT COUNT(*) FROM catalogue_entries WHERE embedding IS NOT NULL")
        by_kind_rows = await pool.fetch(
            "SELECT kind, COUNT(*) AS n FROM catalogue_entries GROUP BY kind ORDER BY n DESC")
        wm = await get_catalogue_watermark("entries")
        edges = await pool.fetchval("SELECT COUNT(*) FROM catalogue_edges")
        return {"total": int(total or 0), "embedded": int(embedded or 0),
                "edges": int(edges or 0),
                "by_kind": {r["kind"]: int(r["n"]) for r in by_kind_rows},
                "watermark": {k: wm.get(k) for k in
                              ("version", "byte_offset", "events_seen", "entries_written")}}
    except Exception as e:
        return {"status": "error", "error": str(e)}


async def catalogue_hybrid_search(query: str, kinds: Optional[List[str]] = None,
                                  top_k: int = 10, per_leg: int = 50,
                                  interactive: bool = True) -> Dict[str, Any]:
    """Two-leg hybrid (pgvector cosine + tsvector ts_rank), RRF-fused (k=60).
    Degrades gracefully: embeddings down → FTS-only; FTS empty → dense-only.
    Cross-encoder rerank deferred."""
    pool = await get_pool()
    if not pool:
        return {"results": [], "legs": {"dense": 0, "bm25": 0}, "rerank": "deferred"}
    kinds = kinds or None
    RRF_K = 60

    dense_rows = []
    emb = await generate_embedding(query, interactive=interactive)
    if emb:
        try:
            dense_rows = await pool.fetch(
                """SELECT urn, 1 - (embedding <=> $1::vector) AS score
                   FROM catalogue_entries
                   WHERE embedding IS NOT NULL AND ($2::text[] IS NULL OR kind = ANY($2))
                   ORDER BY embedding <=> $1::vector LIMIT $3""",
                str(emb), kinds, per_leg)
        except Exception as e:
            logger.debug(f"catalogue dense leg failed: {e}")

    bm25_rows = []
    try:
        bm25_rows = await pool.fetch(
            """SELECT urn, ts_rank_cd(fts, plainto_tsquery('english',$1)) AS score
               FROM catalogue_entries
               WHERE fts @@ plainto_tsquery('english',$1)
                 AND ($2::text[] IS NULL OR kind = ANY($2))
               ORDER BY score DESC LIMIT $3""",
            query, kinds, per_leg)
    except Exception as e:
        logger.debug(f"catalogue bm25 leg failed: {e}")

    # Reciprocal Rank Fusion
    fused: Dict[str, Dict[str, Any]] = {}
    for rank, r in enumerate(dense_rows):
        f = fused.setdefault(r["urn"], {"urn": r["urn"], "rrf": 0.0, "dense": None, "bm25": None})
        f["rrf"] += 1.0 / (RRF_K + rank + 1)
        f["dense"] = round(float(r["score"]), 4)
    for rank, r in enumerate(bm25_rows):
        f = fused.setdefault(r["urn"], {"urn": r["urn"], "rrf": 0.0, "dense": None, "bm25": None})
        f["rrf"] += 1.0 / (RRF_K + rank + 1)
        f["bm25"] = round(float(r["score"]), 4)

    ranked = sorted(fused.values(), key=lambda x: x["rrf"], reverse=True)[:top_k]
    if not ranked:
        return {"results": [], "legs": {"dense": len(dense_rows), "bm25": len(bm25_rows)},
                "rerank": "deferred"}

    # Hydrate the winners
    urns = [x["urn"] for x in ranked]
    try:
        meta = await pool.fetch(
            "SELECT urn, kind, actor, ts, title FROM catalogue_entries WHERE urn = ANY($1)", urns)
        m = {r["urn"]: r for r in meta}
    except Exception:
        m = {}
    results = []
    for x in ranked:
        r = m.get(x["urn"])
        results.append({"urn": x["urn"], "kind": r["kind"] if r else None,
                        "actor": r["actor"] if r else None, "ts": r["ts"] if r else None,
                        "title": r["title"] if r else None,
                        "score": round(x["rrf"], 5), "dense": x["dense"], "bm25": x["bm25"]})
    return {"results": results, "legs": {"dense": len(dense_rows), "bm25": len(bm25_rows)},
            "rerank": "deferred"}
