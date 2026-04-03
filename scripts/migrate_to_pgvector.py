#!/usr/bin/env python3
"""
Migrate existing file-based memory data into pgvector PostgreSQL.

Ingests:
  - data/memory/stm/**/*.memory.json → memories table
  - data/memory/beliefs.json → beliefs table
  - data/logs/godel_choices.jsonl → godel_choices table
  - daio/agents/agent_map.json → agents table

Run: python scripts/migrate_to_pgvector.py
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import PROJECT_ROOT

DB_DSN = "postgresql://mindx:mindx_secure_2026@localhost:5432/mindx"


async def migrate():
    import asyncpg
    pool = await asyncpg.create_pool(DB_DSN, min_size=2, max_size=5)

    # 1. Migrate STM memories
    stm_path = PROJECT_ROOT / "data" / "memory" / "stm"
    mem_count = 0
    mem_errors = 0
    if stm_path.exists():
        files = list(stm_path.rglob("*.memory.json"))
        print(f"Migrating {len(files)} memory files...")
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                parts = f.relative_to(stm_path).parts
                agent_id = parts[0] if parts else "unknown"
                memory_id = data.get("memory_id") or f.stem[:16]
                await pool.execute(
                    """INSERT INTO memories (memory_id, agent_id, memory_type, importance, content, context, tags, tier, created_at)
                       VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, 'stm', $8)
                       ON CONFLICT (memory_id) DO NOTHING""",
                    memory_id,
                    agent_id,
                    data.get("memory_type", "system_state"),
                    data.get("importance", 3),
                    json.dumps(data.get("content", {})),
                    json.dumps(data.get("context", {})),
                    data.get("tags", []),
                    datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
                )
                mem_count += 1
            except Exception as e:
                mem_errors += 1
                if mem_errors <= 3:
                    print(f"  Error: {f.name}: {e}")
    print(f"  Memories: {mem_count} migrated, {mem_errors} errors")

    # 2. Migrate beliefs
    beliefs_path = PROJECT_ROOT / "data" / "memory" / "beliefs.json"
    bel_count = 0
    if beliefs_path.exists():
        try:
            beliefs = json.loads(beliefs_path.read_text())
            for key, val in beliefs.items():
                await pool.execute(
                    """INSERT INTO beliefs (key, value, confidence, source)
                       VALUES ($1, $2::jsonb, $3, $4)
                       ON CONFLICT (key) DO UPDATE SET value=$2::jsonb, confidence=$3, source=$4""",
                    key,
                    json.dumps(val.get("value", val)),
                    float(val.get("confidence", 1.0)),
                    val.get("source", "derived"),
                )
                bel_count += 1
        except Exception as e:
            print(f"  Beliefs error: {e}")
    print(f"  Beliefs: {bel_count} migrated")

    # 3. Migrate Godel choices
    godel_path = PROJECT_ROOT / "data" / "logs" / "godel_choices.jsonl"
    god_count = 0
    if godel_path.exists():
        try:
            for line in godel_path.read_text().strip().split("\n"):
                if not line.strip():
                    continue
                g = json.loads(line)
                await pool.execute(
                    """INSERT INTO godel_choices (source_agent, choice_type, perception_summary, options_considered, chosen, rationale, outcome)
                       VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7)""",
                    g.get("source_agent", "unknown"),
                    g.get("choice_type", ""),
                    g.get("perception_summary", ""),
                    json.dumps(g.get("options_considered")) if g.get("options_considered") else "null",
                    str(g.get("chosen", "")),
                    g.get("rationale", ""),
                    g.get("outcome", ""),
                )
                god_count += 1
        except Exception as e:
            print(f"  Godel error: {e}")
    print(f"  Godel choices: {god_count} migrated")

    # 4. Migrate agent registry
    agent_path = PROJECT_ROOT / "daio" / "agents" / "agent_map.json"
    ag_count = 0
    if agent_path.exists():
        try:
            am = json.loads(agent_path.read_text())
            for agent_id, data in am.get("agents", {}).items():
                await pool.execute(
                    """INSERT INTO agents (agent_id, eth_address, role, agent_group, verification_tier, reputation_score, bona_fide_balance, capabilities, inference_provider)
                       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                       ON CONFLICT (agent_id) DO UPDATE SET eth_address=$2, role=$3, agent_group=$4, verification_tier=$5, reputation_score=$6, bona_fide_balance=$7""",
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
                ag_count += 1
        except Exception as e:
            print(f"  Agent registry error: {e}")
    print(f"  Agents: {ag_count} migrated")

    # Verify
    row = await pool.fetchrow(
        """SELECT
            (SELECT COUNT(*) FROM memories) as memories,
            (SELECT COUNT(*) FROM beliefs) as beliefs,
            (SELECT COUNT(*) FROM godel_choices) as godel,
            (SELECT COUNT(*) FROM agents) as agents,
            (SELECT pg_size_pretty(pg_database_size('mindx'))) as db_size"""
    )
    print(f"\n=== pgvector database ===")
    print(f"  Memories:      {row['memories']}")
    print(f"  Beliefs:       {row['beliefs']}")
    print(f"  Godel choices: {row['godel']}")
    print(f"  Agents:        {row['agents']}")
    print(f"  Database size: {row['db_size']}")

    await pool.close()


if __name__ == "__main__":
    print("mindX → pgvector migration")
    print("=" * 40)
    asyncio.run(migrate())
