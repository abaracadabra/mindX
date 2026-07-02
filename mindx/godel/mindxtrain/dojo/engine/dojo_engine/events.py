"""Event protocol: structured JSON lines on stdout.

The Rust host reads stdout line by line. Every line that parses as JSON with a
``type`` field becomes a typed ``job-event`` forwarded to the UI. Anything else
is shown as a plain log line. Keep one JSON object per line and flush eagerly so
progress streams live.
"""

from __future__ import annotations

import json
import sys
from typing import Any

# On Windows, a piped stdout defaults to cp1252 — any non-ASCII (a model name,
# a path, an arrow) would raise UnicodeEncodeError and kill the process. Force
# UTF-8 so every emitted line is valid for the Rust host to read.
try:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
except Exception:
    pass


def _emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def log(message: str, level: str = "info") -> None:
    """Human-readable log line (level: info | warn | error)."""
    _emit({"type": "log", "level": level, "message": message})


def progress(step: int, total: int, epoch: int, loss: float, **extra: Any) -> None:
    """A training-step update. ``extra`` is forwarded to the UI untouched."""
    payload = {
        "type": "progress",
        "step": step,
        "total": total,
        "epoch": epoch,
        "loss": round(float(loss), 6),
    }
    payload.update(extra)
    _emit(payload)


def done(artifact: str | None = None, **summary: Any) -> None:
    """Signal successful completion and the path to the produced artifact."""
    payload: dict[str, Any] = {"type": "done"}
    if artifact is not None:
        payload["artifact"] = artifact
    if summary:
        payload["summary"] = summary
    _emit(payload)


def error(message: str) -> None:
    """Signal a fatal error. The host marks the job failed."""
    _emit({"type": "error", "message": message})
