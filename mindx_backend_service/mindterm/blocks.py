from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from .models import CommandBlock

BLOCKS_DIR = Path(os.environ.get("MINDTERM_BLOCKS_DIR", "data/mindterm_blocks"))


def _ensure_dir() -> None:
    BLOCKS_DIR.mkdir(parents=True, exist_ok=True)


def blocks_path(session_id: str) -> Path:
    _ensure_dir()
    return BLOCKS_DIR / f"{session_id}.jsonl"


class BlockStore:
    """
    Simple JSONL store per session for blocks.
    v0.0.4: append-only, fetch last N blocks by scanning tail in memory cache.
    """
    def __init__(self) -> None:
        self._cache: Dict[str, List[CommandBlock]] = {}
        self._cache_limit = 500  # keep last N blocks in memory

    def add_block(self, b: CommandBlock) -> None:
        self._append(b.session_id, self._serialize(b))
        self._cache.setdefault(b.session_id, []).append(b)
        self._cache[b.session_id] = self._cache[b.session_id][-self._cache_limit:]

    def update_block(self, session_id: str, block_id: str, **kwargs) -> Optional[CommandBlock]:
        # Update in cache only, then append a patch record to JSONL.
        lst = self._cache.get(session_id, [])
        for b in lst:
            if b.block_id == block_id:
                for k, v in kwargs.items():
                    setattr(b, k, v)
                self._append(session_id, json.dumps({"type": "patch", "block_id": block_id, "patch": kwargs}, ensure_ascii=False))
                return b
        # If not in cache, still persist patch
        self._append(session_id, json.dumps({"type": "patch", "block_id": block_id, "patch": kwargs}, ensure_ascii=False))
        return None

    def get_recent(self, session_id: str, limit: int = 50) -> List[CommandBlock]:
        return list(self._cache.get(session_id, []))[-limit:]

    def _append(self, session_id: str, line: str) -> None:
        p = blocks_path(session_id)
        with p.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    def _serialize(self, b: CommandBlock) -> str:
        return json.dumps(
            {
                "type": "block",
                "block_id": b.block_id,
                "session_id": b.session_id,
                "command": b.command,
                "created_at": b.created_at.isoformat() + "Z",
                "started_at": b.started_at.isoformat() + "Z",
                "finished_at": (b.finished_at.isoformat() + "Z") if b.finished_at else None,
                "exit_code": b.exit_code,
                "output_len": b.output_len,
                "meta": b.meta,
            },
            ensure_ascii=False,
        )

STORE = BlockStore()

