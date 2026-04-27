# agents/cognition/wisdom_loader.py
"""
Wisdom-tier consumer — reads `*_training.jsonl` files written by the dream
cycle (`machine_dreaming._write_training_data`) and indexes them into pgvector
so they can be retrieved during BDI perception.

Per `docs/MEMORY_AUDIT_2026_04_27.md` (Gap 3): the wisdom tier is write-only
today — files exist on disk but no consumer reads them. This module is the
consumer.

Per the cognitive-ascent thesis:
    information → consolidation → knowledge → concept → wisdom → THOT → ingestion

This module implements the **ingestion** edge: a verified-from-disk wisdom
record becomes a queryable embedding in pgvector with a `wisdom:` doc-name
prefix. Future: BDI `perceive()` calls `search_wisdom(goal)` and the plan()
prompt prepends a "RELEVANT WISDOM" preamble.

Storage choice: `pgvector.embed_and_store_doc()` with `doc_embeddings` table.
The `wisdom:` prefix on `doc_name` provides the tier filter without schema
changes. Once verified-wisdom (≥3 verifications, confidence ≥0.85) is
established, those records can also be promoted to a separate `wisdom`
table or a `cognition_tier='wisdom'` column on `memories`. For now the
prefix convention is enough.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from utils.logging_config import get_logger
    from utils.config import PROJECT_ROOT
except ImportError:
    import logging
    def get_logger(name): return logging.getLogger(name)
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

logger = get_logger(__name__)

WISDOM_PREFIX = "wisdom:"
LTM_ROOT = PROJECT_ROOT / "data" / "memory" / "ltm"


def _doc_name_for(agent_id: str, training_file: Path, row_idx: int) -> str:
    """Stable doc_name so re-indexing the same file is idempotent.

    Schema: wisdom:{agent}:{ts_from_filename}:{row_idx}
    Where ts_from_filename comes from the leading timestamp of
    `YYYYMMDD_HHMMSS_training.jsonl`.
    """
    name = training_file.name  # 20260427_191234_training.jsonl
    ts = name.split("_training")[0] if "_training" in name else "unknown"
    return f"{WISDOM_PREFIX}{agent_id}:{ts}:{row_idx}"


def _extract_text_for_embedding(row: Dict[str, Any]) -> str:
    """A training row is in chat-completion shape:
        {"messages": [{"role": "system|user|assistant", "content": ...}]}
    For retrieval, embed the assistant message (the consolidated insight)
    plus the first 200 chars of the user prompt as context.
    """
    messages = row.get("messages") or []
    user = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
    asst = next((m.get("content", "") for m in messages if m.get("role") == "assistant"), "")
    if not asst:
        return ""
    # Insight first (most semantically dense), then a snippet of the prompt
    return f"{asst}\n---\nContext: {user[:200]}"


async def index_training_jsonl(
    file_path: Path,
    agent_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Index every row of a `*_training.jsonl` file into pgvector.

    Returns:
        {indexed, skipped, errors, file, agent_id, doc_names_sample}
    """
    if not file_path.exists() or not file_path.is_file():
        return {"indexed": 0, "skipped": 0, "errors": 1, "error": "file not found", "file": str(file_path)}

    if agent_id is None:
        # Inferred from path: ltm/{agent_id}/{ts}_training.jsonl
        try:
            agent_id = file_path.parent.name
        except Exception:
            agent_id = "unknown"

    try:
        from agents.memory_pgvector import embed_and_store_doc
    except Exception as e:
        return {"indexed": 0, "skipped": 0, "errors": 1, "error": f"pgvector unavailable: {e}"}

    indexed = 0
    skipped = 0
    errors = 0
    doc_names: List[str] = []
    try:
        with file_path.open("r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    errors += 1
                    continue
                text = _extract_text_for_embedding(row)
                if not text or len(text) < 60:
                    skipped += 1
                    continue
                doc_name = _doc_name_for(agent_id, file_path, idx)
                try:
                    n = await embed_and_store_doc(doc_name, text, chunk_size=400)
                    if n > 0:
                        indexed += 1
                        if len(doc_names) < 3:
                            doc_names.append(doc_name)
                    else:
                        skipped += 1
                except Exception as e:
                    errors += 1
                    logger.debug(f"wisdom_loader: embed failed {doc_name}: {e}")
    except OSError as e:
        return {"indexed": 0, "skipped": 0, "errors": 1, "error": str(e), "file": str(file_path)}

    return {
        "indexed": indexed,
        "skipped": skipped,
        "errors":  errors,
        "file":    str(file_path.relative_to(PROJECT_ROOT)) if file_path.is_relative_to(PROJECT_ROOT) else str(file_path),
        "agent_id": agent_id,
        "doc_names_sample": doc_names,
    }


async def index_recent_training(hours: int = 24, max_files: int = 200) -> Dict[str, Any]:
    """Find every `*_training.jsonl` modified in the last `hours` and index it.
    Idempotent: doc_names are deterministic from (agent, file_ts, row_idx),
    so re-indexing existing rows is an UPDATE not a duplicate insert.
    """
    if not LTM_ROOT.exists():
        return {"total_files": 0, "indexed_total": 0, "per_file": [], "status": "no_ltm_dir"}

    cutoff = time.time() - (hours * 3600)
    candidates: List[Tuple[float, Path, str]] = []
    for agent_dir in LTM_ROOT.iterdir():
        if not agent_dir.is_dir():
            continue
        agent_id = agent_dir.name
        for f in agent_dir.iterdir():
            if not f.is_file() or not f.name.endswith("_training.jsonl"):
                continue
            try:
                if f.stat().st_mtime >= cutoff:
                    candidates.append((f.stat().st_mtime, f, agent_id))
            except OSError:
                continue
    candidates.sort(reverse=True)
    candidates = candidates[:max_files]

    per_file: List[Dict[str, Any]] = []
    indexed_total = skipped_total = errors_total = 0
    for _mt, path, agent_id in candidates:
        result = await index_training_jsonl(path, agent_id=agent_id)
        per_file.append(result)
        indexed_total += result.get("indexed", 0)
        skipped_total += result.get("skipped", 0)
        errors_total  += result.get("errors", 0)

    return {
        "total_files":   len(candidates),
        "indexed_total": indexed_total,
        "skipped_total": skipped_total,
        "errors_total":  errors_total,
        "per_file":      per_file,
        "hours_window":  hours,
        "computed_at":   time.time(),
    }


async def search_wisdom(query: str, top_k: int = 3, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve the top-k most relevant wisdom rows for a query.

    Filters `doc_embeddings` to the `wisdom:` prefix. If `agent_id` is given,
    further filters to wisdom from that specific agent.

    Designed for BDI `perceive()` consumption: returns a small ranked list
    suitable for prepending as a "RELEVANT WISDOM" preamble in plan() prompts.
    """
    try:
        from agents.memory_pgvector import semantic_search_docs
    except Exception as e:
        logger.debug(f"wisdom_loader: pgvector unavailable: {e}")
        return []

    # Over-fetch to allow filtering, then trim
    over_fetch = top_k * 4
    raw = await semantic_search_docs(query, top_k=over_fetch)
    out: List[Dict[str, Any]] = []
    for r in raw:
        name = r.get("doc", "")
        if not name.startswith(WISDOM_PREFIX):
            continue
        # wisdom:{agent}:{ts}:{idx}
        try:
            _, agent, ts, idx = name.split(":", 3)
        except ValueError:
            agent, ts, idx = "unknown", "", ""
        if agent_id and agent != agent_id:
            continue
        out.append({
            "doc_name":   name,
            "agent_id":   agent,
            "ts":         ts,
            "row_idx":    idx,
            "text":       r.get("text", ""),
            "similarity": r.get("similarity", 0.0),
        })
        if len(out) >= top_k:
            break
    return out


async def count_indexed_wisdom() -> int:
    """How many wisdom rows are currently indexed in pgvector. Honest stat
    for /insight/cognition (the wisdom tier counter)."""
    try:
        from agents.memory_pgvector import get_pool
    except Exception:
        return 0
    pool = await get_pool()
    if not pool:
        return 0
    try:
        row = await pool.fetchrow(
            "SELECT COUNT(DISTINCT doc_name) AS n FROM doc_embeddings WHERE doc_name LIKE $1",
            f"{WISDOM_PREFIX}%",
        )
        return int(row["n"]) if row else 0
    except Exception:
        return 0
