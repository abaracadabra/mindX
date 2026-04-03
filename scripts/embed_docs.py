#!/usr/bin/env python3
"""
Batch embed all docs + memories into pgvector using local Ollama.

Embeds:
  - docs/*.md → doc_embeddings table (chunked, 500 words per chunk)
  - memories table → memories.embedding column

Uses nomic-embed-text via Ollama at localhost:11434.

Usage: python scripts/embed_docs.py
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import PROJECT_ROOT


async def main():
    from agents.memory_pgvector import (
        get_pool, embed_and_store_doc, embed_memory, generate_embedding,
    )

    # Test embedding model
    print("Testing embedding model...")
    test = await generate_embedding("hello world")
    if not test:
        print("ERROR: Embedding model not available. Run: ollama pull nomic-embed-text")
        return
    print(f"  Model OK — {len(test)} dimensions")

    pool = await get_pool()
    if not pool:
        print("ERROR: Cannot connect to PostgreSQL")
        return

    # Embed all docs
    docs_dir = PROJECT_ROOT / "docs"
    doc_files = sorted(docs_dir.glob("*.md"))
    print(f"\nEmbedding {len(doc_files)} documents...")

    total_chunks = 0
    for i, f in enumerate(doc_files):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
            stored = await embed_and_store_doc(f.stem, text)
            total_chunks += stored
            if (i + 1) % 10 == 0 or i == 0:
                print(f"  [{i+1}/{len(doc_files)}] {f.stem}: {stored} chunks")
        except Exception as e:
            print(f"  ERROR {f.stem}: {e}")

    print(f"  Documents: {len(doc_files)} files → {total_chunks} embedded chunks")

    # Embed memories without embeddings
    rows = await pool.fetch(
        "SELECT memory_id, content FROM memories WHERE embedding IS NULL LIMIT 500"
    )
    print(f"\nEmbedding {len(rows)} memories...")

    mem_count = 0
    for i, row in enumerate(rows):
        try:
            import json
            content = row["content"]
            if isinstance(content, str):
                content = json.loads(content)
            # Extract text from content
            text = content.get("summary", "") or content.get("data", {}).get("summary", "") or str(content)[:2000]
            if len(text) > 50:
                ok = await embed_memory(row["memory_id"], text)
                if ok:
                    mem_count += 1
            if (i + 1) % 50 == 0:
                print(f"  [{i+1}/{len(rows)}] {mem_count} embedded")
        except Exception as e:
            if mem_count < 3:
                print(f"  ERROR: {e}")

    print(f"  Memories: {mem_count} embedded")

    # Summary
    summary = await pool.fetchrow(
        """SELECT
            (SELECT COUNT(*) FROM doc_embeddings WHERE embedding IS NOT NULL) as docs,
            (SELECT COUNT(*) FROM memories WHERE embedding IS NOT NULL) as mems,
            (SELECT pg_size_pretty(pg_database_size('mindx'))) as db_size"""
    )
    print(f"\n=== Embedding Complete ===")
    print(f"  Doc embeddings: {summary['docs']}")
    print(f"  Memory embeddings: {summary['mems']}")
    print(f"  Database size: {summary['db_size']}")

    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
