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

EMBED_MODEL = "mxbai-embed-large"
VLLM_EMBED_URL = os.getenv("VLLM_EMBED_URL", "http://localhost:8001")  # vLLM serving embeddings
OLLAMA_EMBED_URL = "http://localhost:11434"  # Ollama fallback


async def generate_embedding(text: str, model: str = EMBED_MODEL) -> Optional[List[float]]:
    """
    Generate embedding. Tries vLLM first (OpenAI-compatible /v1/embeddings),
    falls back to Ollama /api/embeddings. Returns None on failure with a
    WARNING-level log so the operator can see the failure mode (rather
    than the previous DEBUG silence which hid 0/105 backfill failures).
    """
    import aiohttp

    vllm_status = ollama_status = None

    # 1. Try vLLM (fast, batched, production)
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

    # 2. Fallback to Ollama (reliable, CPU)
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as sess:
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

    logger.warning(
        f"generate_embedding({model}, len={len(text)}): vLLM={vllm_status} ollama={ollama_status}"
    )
    return None


# mxbai-embed-large has a 512-token context window. 200 words ≈ 260-300 tokens
# in English markdown, leaving headroom under the limit. Earlier chunk_size=500
# produced 600-900 tokens and triggered HTTP 500 from Ollama on every chunk —
# the entire failure was logged only at DEBUG, leaving 105/210 docs unembedded
# with no operator-visible signal. See: 2026-04-29 backfill diagnosis.
async def embed_and_store_doc(doc_name: str, text_content: str, chunk_size: int = 200) -> int:
    """Chunk a document and store embeddings in doc_embeddings table."""
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
        emb = await generate_embedding(chunk)
        if emb is None:
            embed_failures += 1
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


async def semantic_search_docs(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Semantic search over doc_embeddings using cosine similarity."""
    pool = await get_pool()
    if not pool:
        return []
    emb = await generate_embedding(query)
    if not emb:
        return []
    try:
        rows = await pool.fetch(
            """SELECT doc_name, chunk_idx, text_content,
                      1 - (embedding <=> $1::vector) as similarity
               FROM doc_embeddings
               WHERE embedding IS NOT NULL
               ORDER BY embedding <=> $1::vector
               LIMIT $2""",
            str(emb), top_k,
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
                EXTRACT(EPOCH FROM AVG(completed_at - created_at)) FILTER (WHERE completed_at IS NOT NULL) as avg_completion_secs
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
                (SELECT COUNT(*) FROM actions) as actions,
                (SELECT COUNT(*) FROM doc_embeddings WHERE embedding IS NOT NULL) as doc_embeddings,
                (SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL) as mem_embeddings,
                (SELECT pg_size_pretty(pg_database_size('mindx'))) as db_size"""
        )
        return {
            "status": "connected",
            "memories": row["memories"],
            "beliefs": row["beliefs"],
            "agents": row["agents"],
            "godel_choices": row["godel_choices"],
            "actions": row["actions"],
            "doc_embeddings": row["doc_embeddings"],
            "mem_embeddings": row["mem_embeddings"],
            "db_size": row["db_size"],
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}
