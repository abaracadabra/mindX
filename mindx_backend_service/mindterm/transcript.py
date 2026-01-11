from __future__ import annotations

import os
from pathlib import Path
from datetime import datetime

TRANSCRIPTS_DIR = Path(os.environ.get("MINDTERM_TRANSCRIPTS_DIR", "data/mindterm_transcripts"))


def ensure_dir() -> None:
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)


def transcript_path(session_id: str) -> Path:
    ensure_dir()
    return TRANSCRIPTS_DIR / f"{session_id}.log"


def append(session_id: str, direction: str, payload: str) -> None:
    """
    Append-only transcript line.
    direction: "in" | "out" | "sys"
    """
    p = transcript_path(session_id)
    ts = datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
    safe = payload.replace("\r", "\\r").replace("\n", "\\n")
    with p.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t{direction}\t{safe}\n")

