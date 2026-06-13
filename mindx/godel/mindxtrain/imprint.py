"""imprint — the proof-of-recall verdict gate (mindXtrain v1.0.0).

mindXtrain's `imprint` verb measures whether a trained model actually learned:
it probes recall BEFORE vs AFTER training and reports a JSON verdict. Confirmed
output shape (2026-06-13, on-box):

    {"before": [...], "after": [...], "before_voice": 0.0415,
     "after_voice": 0.0, "imprint_delta": -0.0415, "shift": 1.0,
     "method": "lexical", "imprinted": false}

exit 0 = imprinted, non-zero (4) = no imprint. This becomes the ascent's proof
gate — a generation is promoted only when `imprinted` is true (the model
demonstrably absorbed its dream wisdom). It is the training-time analogue of
the Gödel kernel's proof check: weights are not served on faith.

NOTE: the verb is `imprint` (NOT `dcoach` — dcoach is the operator web UI only).
`imprint` takes the run config positionally: `imprint <config> --out <dir> --n N`.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Awaitable, Callable, Optional

from . import bridge as _bridge

logger = logging.getLogger(__name__)

DEFAULT_MIN_DELTA = 0.0      # `imprinted` is authoritative; delta is a tiebreak
DEFAULT_PROBES = 5


def _parse_imprint(text: str) -> dict:
    """Pull the imprint JSON verdict out of stdout (it may be surrounded by
    progress/log noise). Returns {} when no verdict is found."""
    for m in reversed(list(re.finditer(r"\{[^{}]*\"imprinted\"[^{}]*\}", text or "", re.S))):
        try:
            return json.loads(m.group(0))
        except Exception:
            continue
    out = {}
    md = re.search(r"imprint_delta[\"'\s:=]+(-?[01](?:\.\d+)?)", text or "")
    mi = re.search(r"imprinted[\"'\s:=]+(true|false)", text or "", re.I)
    if md:
        out["imprint_delta"] = float(md.group(1))
    if mi:
        out["imprinted"] = mi.group(1).lower() == "true"
    return out


def imprint_verdict_factory(
    cap,
    work_dir: Path,
    config_name: str = "run.yaml",
    *,
    n_probes: int = DEFAULT_PROBES,
    min_delta: float = DEFAULT_MIN_DELTA,
    run_out: str = "out/runs",
) -> Callable[[object], Awaitable[dict]]:
    """Build a `Verdict` callback (ascend.Verdict) that runs `mindxtrain
    imprint` and accepts the generation only on a positive imprint."""

    async def _verdict(fr) -> dict:
        cfg = config_name or getattr(getattr(fr, "config_path", None), "name", "run.yaml")
        # Stream the FULL imprint output to a file and parse that — the verdict
        # JSON embeds the before/after response arrays and easily exceeds a
        # truncated stdout window (the cause of a false "unparseable" earlier).
        from pathlib import Path as _P
        out_file = _P(work_dir) / "imprint_out.txt"
        res = _bridge.run_cli_streamed(
            ["imprint", cfg, "--out", run_out, "--n", str(n_probes)],
            cap=cap, cwd=work_dir, log_path=out_file, timeout=1800,
        )
        try:
            blob = out_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            blob = (res.get("tail") or "")
        parsed = _parse_imprint(blob)
        if "imprinted" not in parsed and "imprint_delta" not in parsed:
            return {"accepted": False, "reason": "imprint output unparseable",
                    "raw": (res.get("stdout") or "")[:400]}
        delta = parsed.get("imprint_delta")
        imprinted = parsed.get("imprinted")
        accepted = bool(imprinted) and (delta is None or delta >= min_delta)
        return {
            "accepted": accepted,
            "reason": (f"imprinted={imprinted} delta={delta} method={parsed.get('method')}"
                       f" — {'learned its dream wisdom' if accepted else 'no imprint, not served'}"),
            "recall_before": parsed.get("before_voice"),
            "recall_after": parsed.get("after_voice"),
            "delta": delta,
            "imprinted": imprinted,
        }

    return _verdict
