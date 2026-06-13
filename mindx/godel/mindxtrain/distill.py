"""distill — gather machine.dream output into the `mindx_dreams` corpus.

machine.dream (agents/machine_dreaming.py) already writes one
`*_training.jsonl` per dream cycle, each line a chat-completion example:

    {"messages": [
        {"role": "system",    "content": <consolidation persona>},
        {"role": "user",      "content": <raw STM excerpt>},
        {"role": "assistant", "content": <consolidated insight>}
    ]}

and a `*_dream_report.json` carrying the scored DreamInsights (pattern_type,
importance, novelty, confidence, frequency, score). distill() walks the
dreams directory, joins each training row to the report metadata it came from,
and emits a single normalized JSONL stream in the shape mindXtrain's
`mindx_dreams` adapter consumes — chat messages plus a `meta` block the
curator can filter on.

This is pure stdlib I/O; it neither trains nor mutates the source dreams.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Iterator, Optional


@dataclass
class DreamRow:
    """One normalized training example, dream-provenance attached."""
    messages: list[dict]
    meta: dict = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps({"messages": self.messages, "meta": self.meta},
                          ensure_ascii=False)


def _load_report_scores(report_path: Path) -> dict:
    """Extract per-insight scores keyed by description prefix for joining."""
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    scores: dict[str, dict] = {}
    # dream reports nest insights under agents/results; be liberal in parsing.
    candidates: list[dict] = []
    if isinstance(report, dict):
        for key in ("insights", "results", "agents"):
            val = report.get(key)
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, dict) and "insights" in item:
                        candidates.extend(item.get("insights", []))
                    elif isinstance(item, dict):
                        candidates.append(item)
    for ins in candidates:
        desc = str(ins.get("description", ""))[:64]
        if not desc:
            continue
        scores[desc] = {
            "pattern_type": ins.get("pattern_type"),
            "importance": ins.get("importance"),
            "novelty": ins.get("novelty"),
            "confidence": ins.get("confidence"),
            "frequency": ins.get("frequency"),
            "score": ins.get("score"),
            "source_agents": ins.get("source_agents", []),
        }
    return scores


def _iter_training_files(dreams_dir: Path) -> Iterator[Path]:
    # Recursive: dreams_dir may be a single agent dir OR the ltm root, in which
    # case every agent's *_training.jsonl is consolidated into one curriculum.
    yield from sorted(dreams_dir.rglob("*_training.jsonl"))


def distill(
    dreams_dir: Path,
    *,
    since_ts: Optional[float] = None,
) -> Iterator[DreamRow]:
    """Yield normalized DreamRows from every dream training file.

    `since_ts` (epoch seconds) restricts to dream files modified after a
    watermark — so an ascent only consumes dreams produced since the last
    generation (the rebound carries new momentum, not the whole history again).
    """
    dreams_dir = Path(dreams_dir)
    if not dreams_dir.exists():
        return
    for tf in _iter_training_files(dreams_dir):
        if since_ts is not None and tf.stat().st_mtime < since_ts:
            continue
        # Pair the training file with its sibling dream report for metadata
        # (next to the training file — files may live in per-agent subdirs).
        stem = tf.name.replace("_training.jsonl", "")
        report = tf.parent / f"{stem}_dream_report.json"
        scores = _load_report_scores(report) if report.exists() else {}
        try:
            lines = tf.read_text(encoding="utf-8").splitlines()
        except Exception:
            continue
        for ln in lines:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            messages = obj.get("messages")
            if not isinstance(messages, list) or not messages:
                continue
            # Join to the insight scores via the assistant turn (the insight).
            assistant = next(
                (m.get("content", "") for m in messages
                 if m.get("role") == "assistant"), ""
            )
            score_meta = scores.get(str(assistant)[:64], {})
            yield DreamRow(
                messages=messages,
                meta={
                    "source_file": tf.name,
                    "dream_stem": stem,
                    "data_source": "mindx_dreams",
                    **score_meta,
                },
            )


def write_corpus(rows: Iterable[DreamRow], out_path: Path) -> int:
    """Materialize a normalized corpus JSONL. Returns row count."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(row.to_json() + "\n")
            n += 1
    return n
