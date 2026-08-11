"""model_arena — one prompt, every generation of mind, one processor.

Ask all sixteen trained generations the same question and watch them answer.
The point is not a leaderboard; it is a longitudinal self-portrait — gen1 and
gen16 are the same lineage at different ages, so putting one prompt through all
of them shows what training actually changed.

WHY THIS IS A QUEUE, NOT A FAN-OUT
----------------------------------
"All at once" is not available on this hardware and pretending otherwise would
just produce sixteen timeouts. The box is 2 cores and 8GB; a mindx-gen model is
a few hundred MB to a couple of GB resident, cold loads run 40s+, and the same
processor is already running the autonomous loop that took the site down on
2026-08-09 by monopolising the event loop. Sixteen concurrent generations would
thrash swap and starve both.

So the arena is a strict single-flight queue: one model resident at a time,
positions visible, every run reporting the CPU and RAM it actually cost and the
tokens it actually produced. Waiting is the honest part of the product — the
queue *is* the show, which is why position, elapsed time and live processor
load are first-class in the payload rather than hidden behind a spinner.

Concurrency safety: a single asyncio.Lock serialises runs, a bounded queue
rejects rather than grows without limit, and the resource governor can refuse
admission outright when the box is already over its ceiling. Nothing here runs
on the event loop except awaits — psutil sampling is cheap, inference is awaited
through the instrumented handler so every arena exchange also lands in the
public interaction feed.
"""
from __future__ import annotations

import asyncio
import os
import time
import uuid
from typing import Any, Dict, List, Optional

from utils.logging_config import get_logger

logger = get_logger(__name__)

MAX_QUEUE = int(os.getenv("MINDX_ARENA_MAX_QUEUE", "6"))

# CPU-bound local inference pins every core for as long as it takes to produce
# the answer — minutes for a normal reply, up to an hour for a long one on this
# box. Two consequences that an earlier version of this file got wrong:
#
#   1. 100% CPU is the NORMAL, HEALTHY state while a model is generating. It is
#      not a symptom of overload. Admission must therefore NOT be gated on
#      instantaneous cpu_percent — the autonomous loop alone holds this box at
#      100%, so a CPU ceiling rejected every submission forever.
#   2. A 90-second per-model timeout kills legitimate work. The timeout exists
#      only to stop a genuinely wedged model from holding the single-flight lock
#      indefinitely, so it is generous by default and tunable.
#
# The honest backpressure signal is QUEUE DEPTH (how much work is already
# promised), not processor load. Saturation is judged by run-queue length
# relative to cores — load average far above core count means the scheduler is
# thrashing, which is different from cores being busy.
PER_MODEL_TIMEOUT = float(os.getenv("MINDX_ARENA_TIMEOUT", "900"))       # 15 min/model
RUN_BUDGET_S = float(os.getenv("MINDX_ARENA_RUN_BUDGET", "5400"))       # 90 min/run
MAX_TOKENS = int(os.getenv("MINDX_ARENA_MAX_TOKENS", "220"))
PROMPT_MAX = 400
# Three questions per audience: enough to see whether an answer was a fluke,
# few enough that sixteen models still finish inside the run budget.
QUESTIONS_MAX = int(os.getenv("MINDX_ARENA_QUESTIONS", "3"))
# Thrash guard: refuse only when the run queue is many times the core count,
# i.e. the machine cannot make progress — not merely when it is busy working.
LOAD_PER_CORE_LIMIT = float(os.getenv("MINDX_ARENA_LOAD_PER_CORE", "6"))

_lock = asyncio.Lock()
_runs: Dict[str, Dict[str, Any]] = {}
_order: List[str] = []


def _resources() -> Dict[str, Any]:
    """What the processor is doing right now — the cost meter for the queue."""
    out: Dict[str, Any] = {}
    try:
        import psutil
        out["cpu_percent"] = psutil.cpu_percent(interval=None)
        vm = psutil.virtual_memory()
        out["ram_percent"] = vm.percent
        out["ram_used_gb"] = round(vm.used / (1024 ** 3), 2)
        out["ram_total_gb"] = round(vm.total / (1024 ** 3), 2)
        out["load1"] = round(os.getloadavg()[0], 2)
        out["cores"] = psutil.cpu_count() or 1
    except Exception as e:
        out["error"] = str(e)[:120]
    return out


async def generations(limit: int = 16) -> List[str]:
    """The trained lineage, newest first, as served by Ollama."""
    tags: List[str] = []
    try:
        import aiohttp
        base = os.getenv("MINDX_LLM__OLLAMA__BASE_URL", "http://localhost:11434")
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{base}/api/tags", timeout=aiohttp.ClientTimeout(total=8)) as r:
                data = await r.json()
        for m in data.get("models", []):
            name = m.get("name", "")
            if name.startswith("mindx-gen"):
                tags.append(name)
    except Exception as e:
        logger.debug(f"arena: could not list generations: {e}")
        return []

    def gen_no(t: str) -> int:
        digits = "".join(c for c in t.split(":")[0][len("mindx-gen"):] if c.isdigit())
        return int(digits) if digits else 0

    return sorted(tags, key=gen_no, reverse=True)[:limit]


def _tokens(text: str) -> int:
    """Token estimate. Ollama does not return counts through this handler path,
    so this is words×1.3 — labelled `estimated` everywhere it surfaces so it is
    never mistaken for a billed count."""
    return int(len((text or "").split()) * 1.3)


async def _remember(run_id: str, model: str, turn: Dict[str, Any]) -> None:
    """Persist one answer to pgvector so it is searchable afterwards.

    Every answer becomes an embedded memory keyed by run + model + question
    index, which is what makes the diagnostic searchbar and the
    similarity/divergence correlation possible: both operate on the stored
    vectors rather than re-running inference. Best-effort — the audience must
    never stall because the database is busy.
    """
    if not turn.get("answer"):
        return
    try:
        from agents import memory_pgvector as _mp
        await _mp.store_memory(
            memory_id=f"arena_{run_id}_{model.replace(':', '_')}_q{turn['n']}",
            agent_id="model_arena",
            memory_type="arena_answer",
            importance=3,
            content={
                "run_id": run_id, "model": model, "question_n": turn["n"],
                "question": turn["question"], "answer": turn["answer"],
                "ms": turn["ms"], "tokens_estimated": turn["tokens_estimated"],
            },
            context={"generation": model, "task": "arena"},
            tags=["arena", "model_answer", model.split(":")[0]],
        )
    except Exception as e:
        logger.debug(f"arena: could not persist answer ({model} q{turn['n']}): {e}")


async def search(query: str, top_k: int = 12) -> Dict[str, Any]:
    """Semantic search across every answer any generation has ever given.

    Runs over the pgvector embeddings, so it finds answers by MEANING rather
    than keyword — which is the point for diagnostics: you are usually looking
    for "which generation said something like X", not for an exact phrase.
    """
    q = " ".join(str(query or "").split())[:300]
    if not q:
        return {"ok": False, "error": "empty query"}
    try:
        from agents import memory_pgvector as _mp
        rows = await _mp.semantic_search_memories(q, top_k=max(1, min(int(top_k), 40)))
    except Exception as e:
        return {"ok": False, "error": f"vector search unavailable: {str(e)[:160]}"}

    hits = []
    for r in rows or []:
        c = r.get("content") or {}
        if not isinstance(c, dict) or "answer" not in c:
            continue          # other memory types share the index
        hits.append({
            "model": c.get("model"), "question_n": c.get("question_n"),
            "question": c.get("question"), "answer": (c.get("answer") or "")[:600],
            "ms": c.get("ms"), "run_id": c.get("run_id"),
            "similarity": r.get("similarity"),
        })
    return {"ok": True, "query": q, "hits": hits, "count": len(hits)}


def _cosine(a: List[float], b: List[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return (num / (na * nb)) if na and nb else 0.0


async def correlate(run_id: str) -> Dict[str, Any]:
    """Similarity and divergence across the lineage, per question.

    Embeds every answer to the same question and compares them pairwise. Two
    numbers per answer:

      agreement  — mean cosine similarity to the other generations' answers.
                   High means the lineage converged on this content.
      divergence — 1 - agreement. High means this generation went its own way.

    The answer with the highest agreement is labelled `consensus`, and the
    lowest `outlier`. **Consensus is not correctness.** Sixteen generations of
    one lineage share training data and failure modes, so they can agree
    confidently and be wrong together — the 2026-08-10 IQ interview had all six
    probes scoring ~0 while the models agreed with each other. Read agreement as
    "what this lineage believes", and use the outlier column to find the
    generation worth reading, not to discard it.
    """
    run = _runs.get(run_id)
    if not run:
        return {"ok": False, "error": "unknown run"}
    try:
        from agents.memory_pgvector import generate_embedding
    except Exception as e:
        return {"ok": False, "error": f"embeddings unavailable: {str(e)[:140]}"}

    by_q: Dict[int, List[Dict[str, Any]]] = {}
    for entry in run.get("results", []):
        for t in entry.get("turns", []):
            if t.get("answer"):
                by_q.setdefault(t["n"], []).append({"model": entry["model"], "turn": t})

    out: List[Dict[str, Any]] = []
    for n, items in sorted(by_q.items()):
        vecs: List[Any] = []
        keep: List[Dict[str, Any]] = []
        for it in items:
            try:
                # NOT interactive=True. That flag bypasses the ResourceGovernor
                # CPU throttle and is reserved for operator backfills; this is a
                # participant-triggered endpoint embedding up to 48 answers
                # (16 models × 3 questions) on a 2-core box that is often
                # already at 100%. Respect the throttle and report honestly
                # when it defers, rather than elbowing past the governor that
                # exists to keep the site answering.
                v = await generate_embedding(it["turn"]["answer"])
            except Exception:
                v = None
            if v:
                vecs.append(v)
                keep.append(it)
        if len(keep) < 2:
            out.append({
                "question_n": n, "question": items[0]["turn"]["question"],
                "scored": len(keep), "deferred": len(items) - len(keep),
                "note": ("not enough embedded answers to correlate — embeddings are "
                         "CPU-throttled while the box is busy, so this is usually "
                         "'try again when the autonomous loop is quiet', not a failure"),
            })
            continue

        scored = []
        for i, it in enumerate(keep):
            sims = [_cosine(vecs[i], vecs[j]) for j in range(len(keep)) if j != i]
            agreement = round(sum(sims) / len(sims), 4)
            scored.append({
                "model": it["model"], "agreement": agreement,
                "divergence": round(1.0 - agreement, 4),
                "answer": it["turn"]["answer"][:400],
            })
        scored.sort(key=lambda r: -r["agreement"])
        spread = round(scored[0]["agreement"] - scored[-1]["agreement"], 4)
        out.append({
            "question_n": n, "question": keep[0]["turn"]["question"],
            "scored": len(scored), "spread": spread,
            "consensus": scored[0], "outlier": scored[-1], "ranked": scored,
            "deferred": len(items) - len(keep),
        })

    return {"ok": True, "run_id": run_id, "questions": out,
            "caveat": ("agreement measures what this lineage converged on, not what is "
                       "correct — one lineage shares its training data and its blind spots")}


def status(run_id: Optional[str] = None) -> Dict[str, Any]:
    """Queue state + live processor cost. Safe to poll."""
    if run_id:
        run = _runs.get(run_id)
        if not run:
            return {"ok": False, "error": "unknown run"}
        pos = _order.index(run_id) if run_id in _order else None
        return {"ok": True, "run": run, "position": pos,
                "queued_ahead": pos if pos is not None else 0,
                "resources": _resources()}
    return {
        "ok": True,
        "queue": [{"id": r, "state": _runs[r]["state"],
                   "prompt": _runs[r]["prompt"][:80]} for r in _order if r in _runs],
        "running": next((r for r in _order if _runs.get(r, {}).get("state") == "running"), None),
        "capacity": MAX_QUEUE,
        "resources": _resources(),
    }


async def submit(prompt, *, models: Optional[List[str]] = None,
                 submitted_by: str = "participant") -> Dict[str, Any]:
    """Queue an audience with the whole lineage. Returns immediately with a run id.

    `prompt` is a single question or a list of up to QUESTIONS_MAX. Every model
    is asked ALL of them while it is resident, then dismissed — one load, three
    completions. Asking three questions across three separate visits would pay
    the 40s+ cold load three times over for no benefit.
    """
    raw = prompt if isinstance(prompt, (list, tuple)) else [prompt]
    questions = [" ".join(str(q or "").split())[:PROMPT_MAX] for q in raw]
    questions = [q for q in questions if q][:QUESTIONS_MAX]
    if not questions:
        return {"ok": False, "error": "no questions given"}
    text = questions[0]
    if len(_order) >= MAX_QUEUE:
        return {"ok": False, "error": f"queue full ({MAX_QUEUE}) — the processor is the bottleneck, try shortly"}

    res = _resources()
    # Deliberately NOT a cpu_percent check — see the module header. Only refuse
    # when the machine genuinely cannot make progress.
    cores = max(1, int(res.get("cores") or 1))
    if (res.get("load1") or 0) > cores * LOAD_PER_CORE_LIMIT:
        return {"ok": False,
                "error": f"machine is thrashing (load {res.get('load1')} on {cores} cores) — "
                         "not a busy-CPU refusal, the scheduler is behind; try shortly",
                "resources": res}

    tags = models or await generations()
    if not tags:
        return {"ok": False, "error": "no trained generations are being served"}

    run_id = uuid.uuid4().hex[:12]
    _runs[run_id] = {
        "id": run_id, "prompt": text, "questions": questions,
        "state": "queued", "submitted_by": submitted_by,
        "submitted_at": time.time(), "started_at": None, "finished_at": None,
        "models": tags, "results": [], "done": 0, "total": len(tags),
        "turns_total": len(tags) * len(questions), "turns_done": 0,
        "tokens_estimated": 0, "peak_cpu": None, "peak_ram_percent": None,
        "current_model": None, "current_started_at": None,
        "current_question": None, "current_question_index": None,
        "per_model_timeout_s": PER_MODEL_TIMEOUT, "run_budget_s": RUN_BUDGET_S,
    }
    _order.append(run_id)
    asyncio.create_task(_execute(run_id))
    return {"ok": True, "run_id": run_id, "queued_ahead": max(0, len(_order) - 1),
            "models": tags, "questions": questions, "resources": res}


async def _execute(run_id: str) -> None:
    """Run one submission through every generation, strictly one at a time."""
    run = _runs.get(run_id)
    if not run:
        return
    # Single-flight: the lock is what makes "sixteen models" survivable.
    async with _lock:
        if run_id not in _runs:
            return
        run["state"] = "running"
        run["started_at"] = time.time()
        peak_cpu = 0.0
        peak_ram = 0.0
        try:
            from llm.ollama_handler import OllamaHandler
        except Exception as e:
            run["state"] = "error"
            run["error"] = f"handler unavailable: {e}"
            _finish(run_id)
            return

        run_started = time.time()
        for tag in run["models"]:
            # A whole-run budget so a lineage of slow models cannot hold the
            # single-flight lock indefinitely. Remaining models are reported as
            # skipped rather than silently dropped.
            if time.time() - run_started > RUN_BUDGET_S:
                run["budget_exhausted"] = True
                run["skipped"] = [t for t in run["models"]
                                  if t not in [r["model"] for r in run["results"]]]
                logger.warning("arena: run %s hit the %.0fs budget, %d model(s) skipped",
                               run_id, RUN_BUDGET_S, len(run["skipped"]))
                break
            # ── the audience: one model resident, every question asked ──
            # The model is loaded once and held for all three questions, then
            # dismissed. Each answer is published the moment it lands, so the
            # page shows input→response per question rather than a silent block
            # until the model is finished.
            handler = None
            try:
                handler = OllamaHandler(model_name_for_api=tag)
            except Exception as e:
                run["results"].append({"model": tag, "turns": [], "bowed": False,
                                       "error": f"could not engage: {str(e)[:140]}"})
                run["done"] += 1
                continue

            entry = {"model": tag, "turns": [], "bowed": False, "error": None,
                     "engaged_at": time.time(), "total_ms": 0.0, "tokens_estimated": 0}
            run["results"].append(entry)          # visible while still speaking
            run["current_model"] = tag
            run["current_started_at"] = time.time()

            for qi, question in enumerate(run["questions"]):
                run["current_question_index"] = qi
                run["current_question"] = question
                before = _resources()
                t0 = time.perf_counter()
                answer = None
                err = None
                try:
                    answer = await asyncio.wait_for(
                        handler.generate_text(question, tag, max_tokens=MAX_TOKENS,
                                              temperature=0.4, agent_id="arena",
                                              task=f"arena:q{qi + 1}"),
                        timeout=PER_MODEL_TIMEOUT)
                except asyncio.TimeoutError:
                    err = f"timed out after {PER_MODEL_TIMEOUT:.0f}s"
                except Exception as e:
                    err = str(e)[:160]
                after = _resources()
                peak_cpu = max(peak_cpu, after.get("cpu_percent") or 0, before.get("cpu_percent") or 0)
                peak_ram = max(peak_ram, after.get("ram_percent") or 0)
                toks = _tokens(answer or "")
                ms = round((time.perf_counter() - t0) * 1000, 1)
                turn = {
                    "n": qi + 1,
                    "question": question,
                    "answer": (answer or "").strip()[:1500],
                    "error": err,
                    "ms": ms,
                    "tokens_estimated": toks,
                    "cpu_after": after.get("cpu_percent"),
                    "ram_percent_after": after.get("ram_percent"),
                    "at": time.time(),
                }
                entry["turns"].append(turn)
                entry["total_ms"] = round(entry["total_ms"] + ms, 1)
                entry["tokens_estimated"] += toks
                run["tokens_estimated"] += toks
                run["turns_done"] += 1
                run["peak_cpu"] = round(peak_cpu, 1)
                run["peak_ram_percent"] = round(peak_ram, 1)
                # Persist for diagnostics/search; never let a store failure
                # interrupt the audience.
                asyncio.create_task(_remember(run_id, tag, turn))
                await asyncio.sleep(0.15)         # let the HTTP loop breathe

            # Dismissed: the model bows, and the floor returns to mindX.
            entry["bowed"] = True
            entry["dismissed_at"] = time.time()
            run["done"] += 1
            run["current_model"] = None
            run["current_question"] = None
            run["current_question_index"] = None
            # Yield between models so the HTTP loop and the autonomous loop both
            # get air on a 2-core box.
            await asyncio.sleep(0.4)

        run["state"] = "done"
    _finish(run_id)


def _finish(run_id: str) -> None:
    run = _runs.get(run_id)
    if run:
        run["finished_at"] = time.time()
        if run.get("started_at"):
            run["duration_s"] = round(run["finished_at"] - run["started_at"], 1)
    try:
        _order.remove(run_id)
    except ValueError:
        pass
    # Keep the last handful of completed runs readable, drop the rest.
    completed = [r for r in _runs if _runs[r]["state"] in ("done", "error")]
    for old in sorted(completed, key=lambda r: _runs[r].get("finished_at") or 0)[:-6]:
        _runs.pop(old, None)
