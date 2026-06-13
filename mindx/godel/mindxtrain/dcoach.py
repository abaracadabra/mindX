"""dcoach — the proof-of-recall verdict gate (mindXtrain v1.0.0).

mindXtrain's dcoach loop proves a CPU model actually recalls what it was
trained on: a classroom measures recall BEFORE and AFTER training, a boardroom
casts a success/fail verdict. Example from the project: recall 0.07 -> 0.28.

This wraps the `mindxtrain dcoach` CLI verb (headless — NOT the port-8080
operator web UI) and turns its recall delta into the ascent's proof gate: a
generation is promoted only when the model demonstrably learned (positive
imprint above a threshold). It is the training-time analogue of the Gödel
kernel's proof check — weights are not promoted on faith.

The exact dcoach flags are confirmed at runtime via
`bridge.discover_verb_flags("dcoach")` and logged on first use, because the
v1.0.0 flag surface was not documented when this was written.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Awaitable, Callable, Optional

from . import bridge as _bridge

logger = logging.getLogger(__name__)

DEFAULT_MIN_RECALL_DELTA = 0.15   # conservative vs the 0.07->0.28 (Δ0.21) example
_LOGGED_FLAGS = set()             # log discovered flags once per verb


def _parse_recall(text: str):
    """Pull (before, after) recall floats and a verdict token from dcoach
    stdout. Defensive — returns (None, None, None) when the shape is unknown."""
    text = text or ""
    before = after = None
    # "recall 0.07 -> 0.28" / "0.07 → 0.28" / before=0.07 after=0.28
    m = re.search(r"([01](?:\.\d+)?)\s*(?:->|→|to)\s*([01](?:\.\d+)?)", text)
    if m:
        before, after = float(m.group(1)), float(m.group(2))
    else:
        mb = re.search(r"recall[_\s]*before[\"'\s:=]+([01](?:\.\d+)?)", text, re.I)
        ma = re.search(r"recall[_\s]*after[\"'\s:=]+([01](?:\.\d+)?)", text, re.I)
        if mb:
            before = float(mb.group(1))
        if ma:
            after = float(ma.group(1))
    verdict = None
    if re.search(r"\b(pass(ed)?|success|accept(ed)?|positive imprint)\b", text, re.I):
        verdict = True
    elif re.search(r"\b(fail(ed)?|reject(ed)?|negative imprint)\b", text, re.I):
        verdict = False
    return before, after, verdict


def dcoach_verdict_factory(
    cap,
    work_dir: Path,
    *,
    min_recall_delta: float = DEFAULT_MIN_RECALL_DELTA,
    config_name: Optional[str] = None,
) -> Callable[[object], Awaitable[dict]]:
    """Build a `Verdict` callback (matches ascend.Verdict) that runs dcoach and
    accepts the generation only on a positive recall delta + boardroom pass."""

    async def _verdict(fr) -> dict:
        flags = _bridge.discover_verb_flags("dcoach", cap)
        if "dcoach" not in _LOGGED_FLAGS:
            _LOGGED_FLAGS.add("dcoach")
            logger.info("mindXtrain dcoach flags discovered: %s", sorted(flags))
        args = ["dcoach"]
        cfg = config_name or getattr(getattr(fr, "config_path", None), "name", None)
        # Adapt to whatever the verb actually accepts; never hard-fail on a
        # missing flag — dcoach can usually infer from the run dir / config.
        if cfg and "--config" in flags:
            args += ["--config", cfg]
        if "--json" in flags:
            args += ["--json"]
        res = _bridge.run_cli(args, cap=cap, cwd=work_dir, timeout=900)
        if not res.get("ok"):
            return {"accepted": False,
                    "reason": f"dcoach did not run cleanly: {res.get('reason') or res.get('stderr','')[:200]}",
                    "raw": res}
        before, after, board = _parse_recall((res.get("stdout") or "") + (res.get("stderr") or ""))
        if before is None or after is None:
            return {"accepted": False, "reason": "dcoach output unparseable",
                    "raw": (res.get("stdout") or "")[:400]}
        delta = round(after - before, 4)
        accepted = (delta >= min_recall_delta) and (board is not False)
        return {
            "accepted": accepted,
            "reason": (f"recall {before}->{after} (Δ{delta}) "
                       f"{'>=' if accepted else '<'} {min_recall_delta}"
                       f"{'' if board is None else f'; boardroom={board}'}"),
            "recall_before": before,
            "recall_after": after,
            "delta": delta,
            "boardroom": board,
        }

    return _verdict
