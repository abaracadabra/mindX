#!/usr/bin/env python3
"""
Ingest the private reference corpus (docs/operations/, docs/blockchain/,
docs/publications/pdf/) into mindX awareness — WITHOUT publishing it.

Per document:
  - markdown  → pgvector doc_embeddings (doc_name = docs/-relative posix path
                sans extension, e.g. "operations/dev/Vercel AI SDK 6_ ...")
  - PDF       → text extracted via pypdf and embedded the same way, but only
                when no markdown twin (same stem) exists anywhere in the
                private trees
  - one HIGH-importance LEARNING memory via MemoryAgent (deterministic
    extract: title + headings + first paragraph — no LLM calls), tagged
    ["reference_corpus", <top_folder>]; memory.write catalogue events emit
    automatically. The stm/reference_corpus/ tree is excluded from IPFS
    offload (agents/storage/eligibility.py) — gated content never leaves
    the box.

CPU throttle: generate_embedding DEFERS (returns None) when the
ResourceGovernor says the box is hot, so bulk runs on the VPS can produce
0-chunk docs. This script therefore retries deferred docs with a cooldown,
paces between docs, and only marks a doc complete in the manifest once its
chunks actually stored. --aggressive bypasses the governor (supervised runs
only).

Manifest (data/reference_corpus_manifest.json): relpath -> {sha, chunks,
memory}. A doc is skipped only when sha matches AND chunks > 0 (or the file
is too small to chunk); the memory flag prevents duplicate memory records
across retry runs. Legacy string values (sha only, from the first throttled
run) are treated as memory-written but embedding-incomplete.

Usage: python scripts/ingest_reference_docs.py
         [--force] [--no-pdfs] [--dry-run] [--aggressive]
         [--retries N] [--cooldown SEC] [--pace SEC]
"""

import argparse
import asyncio
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import PROJECT_ROOT
from utils.reference_corpus import iter_reference_docs

MANIFEST_PATH = PROJECT_ROOT / "data" / "reference_corpus_manifest.json"
HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$")
MIN_CHUNKABLE_CHARS = 300  # below this, 0 chunks is legitimate, not a deferral

# THOT power-of-two scale: 8 … 8192. Chunk sizing walks DOWN this ladder on
# failure — embedding windows vary per model (mxbai-embed-large: 512 tokens;
# code-dense text tokenizes ~2x prose, so word counts lie), and binary
# descent finds the largest size that fits without model-specific tuning.
THOT_LADDER = [2 ** k for k in range(3, 14)]  # [8, 16, …, 4096, 8192]


def thot_descend(start: int):
    """Ladder rungs ≤ start, largest first."""
    return [s for s in sorted(THOT_LADDER, reverse=True) if s <= start]


def extract_md_summary(text: str) -> dict:
    """Deterministic summary: title, first ~20 headings, first paragraph."""
    title = ""
    headings = []
    for line in text.splitlines():
        m = HEADING_RE.match(line)
        if not m:
            continue
        if not title and len(m.group(1)) == 1:
            title = m.group(2).strip()[:160]
        headings.append(("  " * (len(m.group(1)) - 1)) + m.group(2).strip()[:120])
        if len(headings) >= 20:
            break
    first_paragraph = ""
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if block and not block.startswith(("#", "|", "```", "<", "---", "![", "- ", "* ")):
            first_paragraph = re.sub(r"\s+", " ", block)[:600]
            break
    return {"title": title, "headings": headings, "first_paragraph": first_paragraph}


def extract_pdf_text(path: Path) -> str:
    from pypdf import PdfReader  # import here so md-only runs don't need it
    reader = PdfReader(str(path))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def load_manifest() -> dict:
    """Load and normalize: legacy str values become embedding-incomplete dicts."""
    try:
        raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out = {}
    for rel, v in raw.items():
        if isinstance(v, str):
            # first (throttled) run: memory records written, embeddings not
            out[rel] = {"sha": v, "chunks": 0, "memory": True}
        else:
            out[rel] = v
    return out


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                             encoding="utf-8")


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-ingest everything (embeds + memories)")
    ap.add_argument("--no-pdfs", action="store_true", help="skip PDF text extraction")
    ap.add_argument("--dry-run", action="store_true", help="list what would be ingested")
    ap.add_argument("--aggressive", action="store_true",
                    help="bypass the CPU governor (supervised backfill only)")
    ap.add_argument("--retries", type=int, default=5, help="retries per doc when embeds defer")
    ap.add_argument("--cooldown", type=float, default=60.0, help="seconds between retries")
    ap.add_argument("--pace", type=float, default=3.0, help="seconds between docs")
    ap.add_argument("--chunk-start", type=int, default=256,
                    help="starting chunk size in words — descends the THOT power-of-two "
                         "ladder (8..8192) on failure; 256 because 512 overflows "
                         "mxbai-embed-large on code-dense text")
    args = ap.parse_args()

    docs_dir = PROJECT_ROOT / "docs"
    all_files = list(iter_reference_docs(docs_dir))
    md_files = [(r, p) for r, p in all_files if p.suffix.lower() == ".md"]
    md_stems = {p.stem.lower() for _, p in md_files}
    pdf_files = [] if args.no_pdfs else [
        (r, p) for r, p in all_files
        if p.suffix.lower() == ".pdf" and p.stem.lower() not in md_stems
        # "foo.md.pdf" twins "foo.md" too
        and p.stem.lower().removesuffix(".md") not in md_stems
    ]
    print(f"Reference corpus: {len(all_files)} files — "
          f"{len(md_files)} markdown, {len(pdf_files)} PDFs without md twin")

    manifest = {} if args.force else load_manifest()
    work = []
    for relpath, path in md_files + pdf_files:
        sha = hashlib.sha256(path.read_bytes()).hexdigest()
        entry = manifest.get(relpath)
        if entry and entry.get("sha") == sha and (entry.get("chunks", 0) > 0 or entry.get("small")):
            continue  # fully ingested and unchanged
        work.append((relpath, path, sha))
    print(f"To ingest (new/changed/embedding-incomplete): {len(work)}")
    if args.dry_run:
        for relpath, _, _ in work:
            print(f"  {relpath}")
        return
    if not work:
        print("Nothing to do.")
        return

    from agents.memory_pgvector import get_pool, embed_and_store_doc, generate_embedding
    from agents.memory_agent import MemoryAgent, MemoryType, MemoryImportance

    test = await generate_embedding("hello world", interactive=args.aggressive)
    if not test:
        print("ERROR: Embedding model not available (see memory_pgvector log line "
              "above for the model it tried — e.g. `ollama pull mxbai-embed-large`).")
        return
    print(f"Embedding model OK — {len(test)} dimensions"
          + (" [aggressive: governor bypassed]" if args.aggressive else " [governor-respecting]"))
    pool = await get_pool()
    if not pool:
        print("ERROR: Cannot connect to PostgreSQL")
        return

    memory_agent = MemoryAgent(log_level="WARNING")
    total_chunks = 0
    complete = 0
    deferred = 0
    for i, (relpath, path, sha) in enumerate(work):
        try:
            if path.suffix.lower() == ".pdf":
                text = extract_pdf_text(path)
                if len(text.strip()) < 200:
                    print(f"  SKIP {relpath}: no extractable text (scanned PDF?)")
                    manifest[relpath] = {"sha": sha, "chunks": 0, "memory": False, "small": True}
                    continue
            else:
                text = path.read_text(encoding="utf-8", errors="replace")

            doc_name = relpath.rsplit(".", 1)[0]
            stored = 0
            # Walk the THOT ladder down from --chunk-start: each failed
            # attempt halves the chunk size (256 → 128 → … → 8 words) until
            # the embedding window accepts it. CPU-governor deferrals retry
            # at the same descent position after the cooldown.
            ladder = thot_descend(args.chunk_start)
            for attempt in range(args.retries + 1):
                csize = ladder[min(attempt, len(ladder) - 1)]
                # purge first so a shrunken doc doesn't keep stale tail chunks
                # (embed_and_store_doc upserts per (doc_name, chunk_idx))
                await pool.execute("DELETE FROM doc_embeddings WHERE doc_name = $1", doc_name)
                # bail on the first overflow so the ladder descends after one
                # failed embed, not after failing every chunk at an oversized
                # window. Last rung embeds in full (best effort, no bail).
                is_last = csize == ladder[-1]
                stored = await embed_and_store_doc(doc_name, text, chunk_size=csize,
                                                   interactive=args.aggressive,
                                                   bail_on_first_failure=not is_last)
                if stored > 0 or len(text) < MIN_CHUNKABLE_CHARS:
                    break
                if attempt < args.retries:
                    # aggressive mode bypasses the governor, so 0 chunks there
                    # means context overflow — deterministic, no point waiting
                    cool = min(args.cooldown, 5.0) if args.aggressive else args.cooldown
                    print(f"  ... {relpath}: 0 chunks at chunk_size={csize}, "
                          f"descending THOT ladder, retry {attempt+1}/{args.retries} in {cool:.0f}s")
                    await asyncio.sleep(cool)
            total_chunks += stored

            entry = manifest.get(relpath, {})
            memory_done = bool(entry.get("memory")) and entry.get("sha") == sha
            if not memory_done:
                summary = extract_md_summary(text)
                top_folder = relpath.split("/", 1)[0]
                await memory_agent.save_timestamped_memory(
                    agent_id="reference_corpus",
                    memory_type=MemoryType.LEARNING,
                    importance=MemoryImportance.HIGH,
                    content={
                        "title": summary["title"] or path.stem,
                        "relpath": relpath,
                        "headings": summary["headings"],
                        "first_paragraph": summary["first_paragraph"],
                        "size_kb": round(path.stat().st_size / 1024, 1),
                        "sha256": sha,
                        "embedded_chunks": stored,
                        "policy": "ingest-only — gated reference material, not for publication",
                    },
                    tags=["reference_corpus", top_folder],
                )
            new_entry = {"sha": sha, "chunks": stored, "memory": True}
            if len(text) < MIN_CHUNKABLE_CHARS:
                new_entry["small"] = True
            if stored == 0 and not new_entry.get("small"):
                deferred += 1   # left incomplete in manifest → retried next run
                new_entry["chunks"] = 0
            else:
                complete += 1
            manifest[relpath] = new_entry
            save_manifest(manifest)  # checkpoint — survives kills
            print(f"  [{i+1}/{len(work)}] {relpath}: {stored} chunks")
            await asyncio.sleep(args.pace)
        except Exception as e:
            print(f"  ERROR {relpath}: {e}")

    save_manifest(manifest)
    print(f"\n=== Ingestion run done: {complete} complete, {deferred} deferred "
          f"(re-run to retry), {total_chunks} chunks this run; "
          f"manifest at {MANIFEST_PATH.relative_to(PROJECT_ROOT)} ===")
    await pool.close()


if __name__ == "__main__":
    asyncio.run(main())
