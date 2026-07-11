#!/usr/bin/env python3
"""
RAGE maintenance — ingest the DeltaVerse docs + /data into the pgvector(scale) store.

The DeltaVerse (~/DeltaVerse) carries 123+ docs (see docs/NAV.md / nav.html) plus machine
/data (deploy/*.json manifests, live/*.json snapshots). This script maintains them in the
mindX RAGE memory (doc_embeddings, bge-m3 @ 1024 dims via Ollama) so retrieval spans the
whole verse:

  doc_name convention:  deltaverse/<tier>/<relpath>     (tier from live/docs-access.json —
                        the OVERLORD hierarchy rides into retrieval metadata)
                        deltaverse/data/<deploy|live>/<file>   (machine data, JSON→text)

  - Ensures schema: CREATE EXTENSION vector; TRIES vectorscale (pgvectorscale) and records
    availability in diagnostics; creates doc_embeddings (vector(1024)) + a DiskANN index
    when vectorscale is present, else HNSW (pgvector ≥0.8) — graceful degradation, reported.
  - Upsert-safe (ON CONFLICT per doc_name+chunk_idx) — re-run any time; this IS maintenance.
  - DIAGNOSTICS: per-tier/per-kind counts, chunk totals, failures, dims, elapsed, index
    backend — printed AND written to ~/DeltaVerse/live/rage-ingest.json so the verse can
    display the health of its own memory.

Usage:
  .mindx_env/bin/python scripts/ingest_deltaverse_docs.py [--interactive] [--check] [--docs-only]

  --interactive  bypass the ResourceGovernor throttle (operator-supervised backfill)
  --check        diagnostics only: report store counts, no ingestion
  --docs-only    skip the /data JSON surfaces
  --resume       skip surfaces already embedded (default OFF = full re-embed).
                 CPU embeds cost ~1 min/chunk — never re-grind good work.
"""

import sys, json, time, asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

DELTAVERSE = Path.home() / "DeltaVerse"
DIAG_OUT = DELTAVERSE / "live" / "rage-ingest.json"
INTERACTIVE = "--interactive" in sys.argv
CHECK = "--check" in sys.argv
DOCS_ONLY = "--docs-only" in sys.argv
RESUME = "--resume" in sys.argv
MAX_DATA_BYTES = 200_000          # cap per JSON data file (pretty-printed)

DDL = """
CREATE TABLE IF NOT EXISTS doc_embeddings (
    doc_name     TEXT NOT NULL,
    chunk_idx    INTEGER NOT NULL,
    text_content TEXT NOT NULL,
    embedding    vector(1024),
    PRIMARY KEY (doc_name, chunk_idx)
);
"""


def deltaverse_docs():
    """(doc_name, path) for every DeltaVerse doc, tier-prefixed from docs-access.json."""
    tiers = {}
    try:
        access = json.loads((DELTAVERSE / "live" / "docs-access.json").read_text())
        tiers = {d["path"]: d["tier"] for d in access.get("docs", [])}
    except Exception:
        pass
    out = []
    for f in sorted((DELTAVERSE / "docs").rglob("*.md")):
        rel = f.relative_to(DELTAVERSE).as_posix()            # docs/…
        tier = tiers.get(rel, "overlord")                      # unclassified stays locked
        out.append((f"deltaverse/{tier}/{rel[5:-3]}", f))      # strip 'docs/' + '.md'
    return out


def deltaverse_data():
    """(doc_name, path) for the machine /data surfaces — deploy/*.json + live/**/*.json."""
    out = []
    for base, pat in (("deploy", "*.json"), ("live", "**/*.json")):
        root = DELTAVERSE / base
        if not root.exists():
            continue
        for f in sorted(root.glob(pat)):
            if f.stat().st_size > 2_000_000:                   # zips/pdfs stray large — data files are lean
                continue
            rel = f.relative_to(DELTAVERSE).as_posix()
            out.append((f"deltaverse/data/{rel[:-5]}", f))     # strip '.json'
    return out


async def ensure_schema(pool, diag):
    async with pool.acquire() as c:
        await c.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        try:
            await c.execute("CREATE EXTENSION IF NOT EXISTS vectorscale;")
            diag["backend"] = "pgvectorscale"
        except Exception as e:
            diag["backend"] = "pgvector"
            diag["vectorscale"] = f"unavailable ({type(e).__name__}) — run scripts/install_pgvectorscale.sh for DiskANN"
        await c.execute(DDL)
        try:
            if diag["backend"] == "pgvectorscale":
                await c.execute("CREATE INDEX IF NOT EXISTS doc_embeddings_diskann "
                                "ON doc_embeddings USING diskann (embedding vector_cosine_ops);")
                diag["index"] = "diskann (StreamingDiskANN)"
            else:
                await c.execute("CREATE INDEX IF NOT EXISTS doc_embeddings_hnsw "
                                "ON doc_embeddings USING hnsw (embedding vector_cosine_ops);")
                diag["index"] = "hnsw (pgvector)"
        except Exception as e:
            diag["index"] = f"none ({e})"


async def main():
    from agents.memory_pgvector import get_pool, embed_and_store_doc, generate_embedding, SCHEMA_EMBED_DIMS

    t0 = time.time()
    diag = {"v": 1, "kind": "rage-ingest-diagnostics", "source": "mindX/scripts/ingest_deltaverse_docs.py",
            "dims": SCHEMA_EMBED_DIMS, "interactive": INTERACTIVE, "tiers": {}, "kinds": {},
            "files": 0, "chunks": 0, "failures": [], "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}

    pool = await get_pool()
    if not pool:
        print("ERROR: no PostgreSQL pool"); return 1
    await ensure_schema(pool, diag)

    if CHECK:
        async with pool.acquire() as c:
            rows = await c.fetch("SELECT split_part(doc_name,'/',2) AS grp, count(DISTINCT doc_name) docs, count(*) chunks "
                                 "FROM doc_embeddings WHERE doc_name LIKE 'deltaverse/%' GROUP BY 1 ORDER BY 1")
            total = await c.fetchval("SELECT count(*) FROM doc_embeddings")
        print(f"backend: {diag['backend']} · index: {diag['index']} · dims: {diag['dims']}")
        for r in rows:
            print(f"  deltaverse/{r['grp']}: {r['docs']} docs · {r['chunks']} chunks")
        print(f"  store total: {total} chunks")
        return 0

    probe = await generate_embedding("the substrate of the changing story", interactive=INTERACTIVE)
    if not probe:
        print("ERROR: embedding model unavailable (Ollama bge-m3?) — try --interactive"); return 1
    print(f"embed model OK — {len(probe)} dims · backend {diag['backend']} · index {diag['index']}")

    work = deltaverse_docs() + ([] if DOCS_ONLY else deltaverse_data())
    if RESUME:
        async with pool.acquire() as c:
            have = {r["doc_name"] for r in await c.fetch(
                "SELECT DISTINCT doc_name FROM doc_embeddings WHERE doc_name LIKE 'deltaverse/%'")}
        before = len(work)
        work = [(n, p) for (n, p) in work if n not in have]
        diag["resumed"] = {"already_embedded": len(have), "skipped": before - len(work)}
        print(f"resume: {len(have)} surfaces already in the store · {len(work)} remain")
    print(f"maintaining {len(work)} DeltaVerse surfaces in RAGE…")
    for i, (name, path) in enumerate(work):
        try:
            if path.suffix == ".json":
                text = json.dumps(json.loads(path.read_text()), indent=1)[:MAX_DATA_BYTES]
            else:
                text = path.read_text()
            n = await embed_and_store_doc(name, text, interactive=INTERACTIVE)
            diag["files"] += 1; diag["chunks"] += n
            grp = name.split("/")[1]
            diag["tiers"][grp] = diag["tiers"].get(grp, 0) + 1
            diag["kinds"]["data" if path.suffix == ".json" else "doc"] = \
                diag["kinds"].get("data" if path.suffix == ".json" else "doc", 0) + 1
            if n == 0:
                diag["failures"].append({"doc": name, "why": "0 chunks embedded"})
            if (i + 1) % 20 == 0:
                print(f"  {i+1}/{len(work)} · {diag['chunks']} chunks · {time.time()-t0:.0f}s")
        except Exception as e:
            diag["failures"].append({"doc": name, "why": f"{type(e).__name__}: {e}"})

    diag["seconds"] = round(time.time() - t0, 1)
    diag["ok"] = len(diag["failures"]) == 0
    try:
        DIAG_OUT.write_text(json.dumps(diag, indent=1) + "\n")
        print(f"diagnostics → {DIAG_OUT}")
    except Exception as e:
        print(f"(diagnostics not written: {e})")
    print(f"\nRAGE maintenance: {diag['files']} surfaces · {diag['chunks']} chunks · "
          f"{len(diag['failures'])} failures · {diag['seconds']}s · {diag['backend']}/{diag['index']}")
    return 0 if diag["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
