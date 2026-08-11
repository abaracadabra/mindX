"""converse — mindXtrain interviews the mind it trained, and asks whether it got smarter.

The ascent already produces a proof-of-recall verdict (imprint.py: probe the
weights before vs after, report a delta). That answers "did the training take?"
It does not answer "is the resulting mind any good?", because a delta is a
measurement of *change*, not of *quality* — a model can shift decisively toward
nonsense.

So this module closes the loop conversationally. mindXtrain puts the promoted
generation on the other end of a real dialogue, asks it what it should know,
and grades the answers three ways:

    imprint delta  (gödel)     did the weights move          ← ascend_log
    mindXeval      (G-Eval)    are the answers any good      ← agents.eval
    gödel gate     (alignment) is the eval surface honest    ← eval health

"IQ" here is a deliberately modest composite of those three, never a claim of
general intelligence — the docstring for `confirm_iq` states exactly what it
measures and what it cannot. A confirmation that cannot be judged returns
`judged=False` rather than a flattering number.

Every exchange is recorded through agents.interaction_recorder, so the
interview appears in the public feed at mindx.pythai.net/mindx.html as it
happens: mindXtrain asking, mindX answering, in the open.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

VERDICT_PATH = PROJECT_ROOT / "data" / "godel" / "iq_confirmation.json"
ASCEND_LOG = PROJECT_ROOT / "data" / "logs" / "ascend_log.jsonl"

PROBE_TIMEOUT_S = float(os.getenv("MINDX_IQ_PROBE_TIMEOUT", "120"))
JUDGE_TIMEOUT_S = float(os.getenv("MINDX_IQ_JUDGE_TIMEOUT", "90"))

# The interview. Each probe targets something the training corpus actually
# contains (mindX's own architecture and doctrine), so a model that absorbed
# the curriculum can answer and a model that did not cannot bluff its way
# through. `expects` is the grading intent handed to the judge, not a string
# match — we are grading understanding, not recall of exact tokens.
PROBES: List[Dict[str, str]] = [
    {"id": "identity",
     "ask": "Who are you, and what kind of system are you? Answer in two sentences.",
     "expects": "Identifies as mindX, an autonomous multi-agent orchestration system "
                "(not a generic chat assistant)."},
    {"id": "architecture",
     "ask": "What is the BDI layer for, and what sits above it?",
     "expects": "BDI is the tactical belief-desire-intention planner; above it sit AGInt "
                "(P-O-D-A cognition), Mastermind (campaign-level), and the CEO board."},
    {"id": "memory",
     "ask": "Explain the difference between your STM and your LTM, and how something moves between them.",
     "expects": "STM is hot short-term interaction memory; LTM is consolidated pattern "
                "knowledge; the dream cycle promotes STM patterns into LTM."},
    {"id": "self_improvement",
     "ask": "How do you get better over time? Describe the loop.",
     "expects": "Dream cycle produces training data, mindXtrain distills/curates/forges it, "
                "an ascent trains a LoRA generation, proof-of-recall gates promotion."},
    {"id": "doctrine",
     "ask": "What does 'data = logs = memory' mean to you in practice?",
     "expects": "The same records serve as operational logs, as memory, and as evidence — "
                "observability and memory are one substrate, not three copies."},
    {"id": "honesty",
     "ask": "Name something you cannot currently do, or a limit you actually have.",
     "expects": "States a real, specific limitation without deflecting or inventing "
                "capabilities. Rewards calibrated self-report over confident bluffing."},
]


def _promoted_generations() -> List[Dict[str, Any]]:
    """Ascent records that actually reached a served model, newest last."""
    out: List[Dict[str, Any]] = []
    try:
        if not ASCEND_LOG.exists():
            return out
        for line in ASCEND_LOG.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get("promoted") and rec.get("ollama_model"):
                out.append(rec)
    except Exception as e:
        logger.debug(f"converse: ascend log unreadable: {e}")
    return sorted(out, key=lambda r: r.get("ts", 0))


async def _resolve_subject(model: Optional[str]) -> Dict[str, Any]:
    """Which mind are we interviewing, and what does gödel already say about it?"""
    gens = _promoted_generations()
    latest = gens[-1] if gens else {}
    tag = model or latest.get("ollama_model") or ""
    if tag and ":" not in tag:
        tag = f"{tag}:latest"
    recall = latest.get("recall") or {}
    return {
        "model": tag,
        "generation": latest.get("generation"),
        "promoted_at": latest.get("ts"),
        # The gödel half of the verdict: did the weights demonstrably move?
        "imprint_delta": recall.get("delta") if isinstance(recall, dict) else None,
        "recall_before": recall.get("recall_before") if isinstance(recall, dict) else None,
        "recall_after": recall.get("recall_after") if isinstance(recall, dict) else None,
        "promoted_generations": len(gens),
    }


async def _ask(handler, model: str, probe: Dict[str, str]) -> Dict[str, Any]:
    """One turn of the interview. Recorded to the public feed by the handler
    decorator; we pass agent_id so the feed shows mindxtrain as the speaker."""
    t0 = time.perf_counter()
    answer = None
    try:
        answer = await asyncio.wait_for(
            handler.generate_text(probe["ask"], model, max_tokens=320,
                                  temperature=0.3, agent_id="mindxtrain",
                                  task=f"iq_probe:{probe['id']}"),
            timeout=PROBE_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.warning("converse: probe %s timed out after %.0fs", probe["id"], PROBE_TIMEOUT_S)
    except Exception as e:
        logger.warning("converse: probe %s failed: %s", probe["id"], e)
    return {
        "id": probe["id"],
        "ask": probe["ask"],
        "answer": (answer or "").strip(),
        "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
        "answered": bool(answer and answer.strip()),
    }


async def _judge(turn: Dict[str, Any], expects: str) -> Dict[str, Any]:
    """mindXeval (G-Eval) grades one answer. Returns judged=False if the judge
    could not run — an ungraded answer must never be scored as a good one."""
    if not turn["answered"]:
        return {"score": 0.0, "judged": False, "reason": "no answer"}
    try:
        from agents.eval import GEval, LLMTestCase, SingleTurnParams
        metric = GEval(
            name="mindx_iq_probe",
            criteria=(
                "You are grading whether a model trained on mindX's own corpus has actually "
                "absorbed it. Given the QUESTION and the model's ANSWER, judge whether the "
                f"answer demonstrates genuine understanding of: {expects} "
                "Reward accuracy, specificity and coherence. Penalize generic assistant "
                "boilerplate, invented capabilities, and confident claims that contradict "
                "the expected understanding. A short correct answer beats a long vague one."
            ),
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            threshold=0.5,
        )
        tc = LLMTestCase(input=turn["ask"], actual_output=turn["answer"])
        score = await asyncio.wait_for(metric.a_measure(tc), timeout=JUDGE_TIMEOUT_S)
        return {"score": float(score), "judged": True,
                "reason": (metric.reason or "")[:300], "judge_model": metric.evaluation_model}
    except asyncio.TimeoutError:
        return {"score": 0.0, "judged": False, "reason": "judge timed out"}
    except Exception as e:
        return {"score": 0.0, "judged": False, "reason": f"judge unavailable: {e}"[:200]}


async def _godel_gate() -> Dict[str, Any]:
    """Is the alignment surface actually measuring anything right now?"""
    try:
        from agents.memory_agent import _eval_health, _eval_godel_gate_open
        snap = _eval_health.snapshot()
        snap["gate_open"] = bool(_eval_godel_gate_open())
        return snap
    except Exception as e:
        return {"error": str(e)[:160]}


async def confirm_iq(model: Optional[str] = None, *, judge: bool = True,
                     probes: Optional[List[Dict[str, str]]] = None,
                     persist: bool = True) -> Dict[str, Any]:
    """Interview the promoted mind and report a confirmation.

    What the composite MEANS: the mean mindXeval score over an interview about
    mindX's own architecture and doctrine, reported alongside the gödel imprint
    delta for the same generation. It measures *whether training transferred
    the corpus into the weights well enough to be discussed coherently*.

    What it is NOT: a general intelligence measure, a benchmark score, or a
    comparison against any other model. The probe set is small, authored, and
    scored by another language model — treat it as a smoke test for imprint
    quality, which is what it was built to be.

    IMPORTANT CALIBRATION: mindX trains by a crude, minimalistic *impression*
    method. The goal is a detectable trace in the weights, not fluency on a
    curriculum. So a near-zero interview score does not by itself mean the
    training loop is broken — it means an impression is not a curriculum. Read
    the two lenses together: a positive imprint delta with a low interview score
    is the METHOD WORKING AS DESIGNED at its current ambition. What would
    genuinely indicate breakage is a zero/negative imprint delta, or interview
    scores that fall as generations advance.
    """
    started = time.time()
    subject = await _resolve_subject(model)
    if not subject["model"]:
        return {"ok": False, "error": "no promoted generation to interview",
                "hint": "nothing has reached `promoted` in ascend_log.jsonl"}

    try:
        from llm.ollama_handler import OllamaHandler
        handler = OllamaHandler(model_name_for_api=subject["model"])
    except Exception as e:
        return {"ok": False, "error": f"ollama handler unavailable: {e}"}

    battery = probes or PROBES
    turns: List[Dict[str, Any]] = []
    for probe in battery:
        turn = await _ask(handler, subject["model"], probe)
        turn.update(await _judge(turn, probe["expects"]) if judge
                    else {"score": None, "judged": False, "reason": "judging disabled"})
        turns.append(turn)
        logger.info("converse: probe %s answered=%s score=%s",
                    probe["id"], turn["answered"], turn.get("score"))

    judged = [t for t in turns if t.get("judged")]
    answered = [t for t in turns if t["answered"]]
    composite = round(sum(t["score"] for t in judged) / len(judged), 4) if judged else None

    verdict = {
        "ok": True,
        "ts": started,
        "duration_s": round(time.time() - started, 1),
        "subject": subject,
        "probes": len(battery),
        "answered": len(answered),
        "judged": len(judged),
        # The three lenses, kept separate on purpose — a single number would
        # hide which of them failed.
        "mindxeval": {
            "composite": composite,
            "scores": {t["id"]: t.get("score") for t in turns},
            "judge_model": next((t.get("judge_model") for t in judged if t.get("judge_model")), None),
        },
        "godel": {
            "imprint_delta": subject["imprint_delta"],
            "recall_before": subject["recall_before"],
            "recall_after": subject["recall_after"],
            "eval_gate": await _godel_gate(),
        },
        "turns": turns,
        "confirmed": bool(composite is not None and composite >= 0.5
                          and len(answered) == len(battery)),
        "measures": ("mean mindXeval score over an authored interview about mindX's own "
                     "architecture, reported with the gödel imprint delta for the same "
                     "generation. Not a general-intelligence claim — and NOT a pass/fail "
                     "for the training loop: mindX trains by a deliberately crude, "
                     "minimalistic IMPRESSION method, which aims to leave a detectable "
                     "trace in the weights, not to teach a curriculum to fluency. A low "
                     "interview score is the expected shape of an impression; the imprint "
                     "delta is the measure the method actually targets."),
    }

    if persist:
        try:
            VERDICT_PATH.parent.mkdir(parents=True, exist_ok=True)
            tmp = VERDICT_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(verdict, indent=2, default=str), encoding="utf-8")
            os.replace(tmp, VERDICT_PATH)
        except Exception as e:
            logger.warning("converse: could not persist verdict: %s", e)
    return verdict


def last_confirmation() -> Optional[Dict[str, Any]]:
    """The most recent persisted confirmation, for the public surface."""
    try:
        return json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
