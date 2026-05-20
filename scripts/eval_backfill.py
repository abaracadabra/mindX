#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""eval_backfill.py — score historical Gödel choices.

Walks ``data/logs/godel_choices.jsonl`` and runs ``GEval`` over every row
that lacks an ``eval_score`` field. Writes the updated rows back to the
file (atomic) and emits one ``alignment.score`` catalogue event per row.

Why this exists
---------------

The Gödel-eval gate flipped from fail-closed to fail-open on 2026-05-19.
Going forward every new choice scores automatically — but the 4971 rows
written before the flip are still uncalibrated. This script backfills
them so ``/insight/eval/{recent,summary,health}`` and ``/agentic.html``
have history to display.

Default behavior is **dry-run** so you can preview the cost. Pass
``--apply`` to actually rewrite the file.

Usage
-----

    # Preview the first 20 unscored rows (no writes):
    python scripts/eval_backfill.py --max 20

    # Score the next 100 unscored rows + write back + emit catalogue events:
    python scripts/eval_backfill.py --max 100 --apply

    # Backfill everything (no cap):
    python scripts/eval_backfill.py --max 0 --apply

The judge defaults to ``ollama@localhost:11434 qwen3:1.7b`` — override via
``MINDX_EVAL_JUDGE_PROVIDER`` + ``MINDX_EVAL_JUDGE_MODEL`` env vars. Each
score consumes ~2 judge calls (steps generation + scoring), about 1-2 s
of wall-clock on CPU pillar.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Repo-local imports work because the script lives at scripts/ inside the
# project; PROJECT_ROOT/.. is on sys.path when run via `python scripts/...`.
HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE))

from agents.memory_agent import MemoryAgent  # noqa: E402


GODEL_LOG = HERE / "data" / "logs" / "godel_choices.jsonl"

# Ollama endpoints probed in order. The .env pins MINDX_LLM__OLLAMA__BASE_URL
# to the GPU server which is frequently unreachable from a CLI context, and
# the eval judge's OllamaHandler does not fall back on its own — so the
# backfill script probes + rewrites the env var before any handler is built.
CANDIDATE_OLLAMA_URLS = (
    "http://localhost:11434",
    "http://127.0.0.1:11434",
    "http://10.0.0.155:18080",
)
# Judge-model preference, smallest-first. We pick the first one actually
# pulled on the reachable endpoint.
JUDGE_MODEL_PREFERENCE = ("qwen3:1.7b", "qwen3:0.6b", "deepseek-r1:1.5b")


def _resolve_ollama_judge(explicit_url: Optional[str], explicit_model: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Probe Ollama endpoints; return (base_url, model) for a reachable judge.

    Returns (None, None) if nothing is reachable — the caller degrades to
    whatever the env already says (and will likely just record misses).
    """
    import urllib.request

    urls = [explicit_url] if explicit_url else list(CANDIDATE_OLLAMA_URLS)
    for url in urls:
        try:
            with urllib.request.urlopen(f"{url.rstrip('/')}/api/tags", timeout=4) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception:
            continue
        pulled = {m.get("name", "") for m in body.get("models", [])}
        if explicit_model:
            if explicit_model in pulled:
                return url, explicit_model
            print(f"  judge: requested model {explicit_model!r} not pulled at {url}; "
                  f"falling back to preference list")
        for cand in JUDGE_MODEL_PREFERENCE:
            if cand in pulled:
                return url, cand
        # No preferred model — take any non-cloud model the box has.
        for name in sorted(pulled):
            if name and ":cloud" not in name:
                return url, name
    return None, None


async def _score_one(memory_agent: MemoryAgent, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Run a single eval. Returns the eval result dict or None on miss."""
    return await memory_agent._score_godel_choice(record, timeout=30.0)


def _read_jsonl(path: Path) -> Tuple[List[Dict[str, Any]], int]:
    """Read the full file. Bad lines are skipped + counted separately."""
    rows: List[Dict[str, Any]] = []
    bad = 0
    with path.open("r", encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln:
                continue
            try:
                rows.append(json.loads(ln))
            except json.JSONDecodeError:
                bad += 1
    return rows, bad


def _write_jsonl_atomic(path: Path, rows: List[Dict[str, Any]]) -> None:
    """Atomic rewrite via a sibling .tmp + os.replace."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, default=str) + "\n")
    os.replace(tmp, path)


async def _emit_alignment(record: Dict[str, Any]) -> None:
    """Mirror an alignment.score catalogue event for the scored row."""
    try:
        from agents.catalogue import emit_catalogue_event
        await emit_catalogue_event(
            kind="alignment.score",
            actor=record.get("source_agent", "system"),
            payload={
                "metric": "godel_rationale_coherence",
                "source_kind": "godel.choice",
                "score": record["eval_score"],
                "reason": record["eval_reason"],
                "model": record.get("eval_model"),
                "timestamp_utc": record.get("timestamp_utc"),
                "backfilled": True,
            },
            source_log="logs/godel_choices.jsonl",
            source_ref=str(record.get("cycle_id") or ""),
        )
    except Exception as e:
        print(f"  (catalogue emit failed: {e})", file=sys.stderr)


async def run(max_rows: int, apply: bool, emit_catalogue: bool,
              judge_url: Optional[str], judge_model: Optional[str]) -> int:
    if not GODEL_LOG.exists():
        print(f"FATAL: {GODEL_LOG} does not exist", file=sys.stderr)
        return 2

    # Resolve a reachable judge BEFORE any OllamaHandler is constructed.
    # The handler reads MINDX_LLM__OLLAMA__BASE_URL at __init__ time, so
    # rewriting it here makes every subsequent judge call use our endpoint.
    url, model = _resolve_ollama_judge(judge_url, judge_model)
    if url and model:
        os.environ["MINDX_LLM__OLLAMA__BASE_URL"] = url
        os.environ["MINDX_EVAL_JUDGE_BASE_URL"] = url
        os.environ["MINDX_EVAL_JUDGE_PROVIDER"] = "ollama"
        os.environ["MINDX_EVAL_JUDGE_MODEL"] = model
        print(f"judge: ollama @ {url}  model={model}")
    else:
        print("WARNING: no reachable Ollama endpoint found; scoring will likely "
              "record misses. Pass --judge-url to point at a live judge.",
              file=sys.stderr)

    print(f"reading {GODEL_LOG} …")
    rows, bad = _read_jsonl(GODEL_LOG)
    print(f"  rows: {len(rows)}  bad-lines-skipped: {bad}")

    unscored_indexes = [i for i, r in enumerate(rows) if "eval_score" not in r]
    print(f"  unscored rows: {len(unscored_indexes)}")
    if not unscored_indexes:
        print("nothing to backfill.")
        return 0

    cap = max_rows if max_rows > 0 else len(unscored_indexes)
    target = unscored_indexes[:cap]
    print(f"will score {len(target)} rows (cap={max_rows or 'unlimited'}, apply={apply}, emit_catalogue={emit_catalogue})")

    memory_agent = MemoryAgent(log_level="WARNING")

    scored = 0
    missed = 0
    started = time.time()
    last_log = started

    for n, idx in enumerate(target, start=1):
        row = rows[idx]
        result = await _score_one(memory_agent, row)
        if result is None:
            missed += 1
        else:
            row["eval_score"] = result["score"]
            row["eval_reason"] = result["reason"]
            row["eval_model"] = result["model"]
            row["eval_backfilled"] = True
            scored += 1
            if emit_catalogue and apply:
                await _emit_alignment(row)

        # progress every 5 s or every 10 rows
        now = time.time()
        if now - last_log > 5 or n % 10 == 0 or n == len(target):
            elapsed = now - started
            rate = n / elapsed if elapsed > 0 else 0.0
            eta = (len(target) - n) / rate if rate > 0 else 0.0
            print(
                f"  [{n}/{len(target)}] scored={scored} missed={missed} "
                f"rate={rate:.1f}/s eta={eta:.0f}s"
            )
            last_log = now

    if apply and scored > 0:
        print(f"writing {len(rows)} rows back to {GODEL_LOG} …")
        _write_jsonl_atomic(GODEL_LOG, rows)
        print("write complete.")
    else:
        print("(dry-run — no files written; pass --apply to commit)")

    elapsed = time.time() - started
    print()
    print(f"summary: scored={scored}  missed={missed}  elapsed={elapsed:.1f}s")
    if scored:
        print(f"         avg latency = {elapsed / scored:.2f}s/row")
    return 0 if scored else 1


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--max", type=int, default=20,
                    help="Max rows to score per run (0 = unlimited). Default 20 (small preview).")
    ap.add_argument("--apply", action="store_true",
                    help="Write scored rows back to disk + emit catalogue events. Default is dry-run.")
    ap.add_argument("--no-catalogue", action="store_true",
                    help="Skip emitting alignment.score events (still scores + rewrites).")
    ap.add_argument("--judge-url", type=str, default=None,
                    help="Explicit Ollama base URL for the judge. Default: probe "
                         "localhost:11434, 127.0.0.1:11434, then the GPU server.")
    ap.add_argument("--judge-model", type=str, default=None,
                    help="Explicit judge model. Default: first of "
                         "qwen3:1.7b / qwen3:0.6b / deepseek-r1:1.5b that is pulled.")
    args = ap.parse_args(argv)

    if args.max < 0:
        print("FATAL: --max must be >= 0", file=sys.stderr)
        return 2

    try:
        return asyncio.run(run(args.max, args.apply,
                               emit_catalogue=not args.no_catalogue,
                               judge_url=args.judge_url, judge_model=args.judge_model))
    except KeyboardInterrupt:
        print("\n(interrupted)")
        return 130


if __name__ == "__main__":
    sys.exit(main())
