"""
CatalogueEventLog — append-only JSONL writer with daily rotation.

Output: data/logs/catalogue_events.jsonl (active)
Rotates to data/logs/catalogue_events.YYYYMMDD-HHMMSS.jsonl on size threshold
(default 100 MB) so the active file remains tail-able.

Thread-safety: a single asyncio.Lock serializes appends, which is sufficient
because the entire backend service is single-process async. Cross-process
writers would require flock; mindX does not have any today.
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles  # type: ignore[import-not-found]

from .events import CatalogueEvent

ROTATE_BYTES_DEFAULT = 100 * 1024 * 1024  # 100 MB


class CatalogueEventLog:
    """Append-only JSONL writer for CatalogueEvents."""

    _default: Optional["CatalogueEventLog"] = None

    def __init__(self, path: Path, rotate_bytes: int = ROTATE_BYTES_DEFAULT):
        self.path = Path(path)
        self.rotate_bytes = max(1024 * 1024, int(rotate_bytes))
        self._lock = asyncio.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def default(cls) -> "CatalogueEventLog":
        """Singleton anchored at <project_root>/data/logs/catalogue_events.jsonl."""
        if cls._default is not None:
            return cls._default
        try:
            from utils.config import PROJECT_ROOT
            base = PROJECT_ROOT / "data" / "logs"
        except Exception:
            # Fall back to repo-local data/logs when config is unavailable
            base = Path(__file__).resolve().parents[2] / "data" / "logs"
        cls._default = cls(base / "catalogue_events.jsonl")
        return cls._default

    async def append(self, evt: CatalogueEvent) -> None:
        """Append one event. Rotates the file if it crosses the size threshold."""
        line = evt.model_dump_json() + "\n"
        async with self._lock:
            await self._maybe_rotate()
            async with aiofiles.open(self.path, "a", encoding="utf-8") as f:
                await f.write(line)

    async def _maybe_rotate(self) -> None:
        try:
            if self.path.exists() and self.path.stat().st_size >= self.rotate_bytes:
                stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                rotated = self.path.with_name(f"{self.path.stem}.{stamp}{self.path.suffix}")
                # If a same-second rotation already happened, suffix the rotated name.
                n = 1
                while rotated.exists():
                    rotated = self.path.with_name(
                        f"{self.path.stem}.{stamp}-{n}{self.path.suffix}"
                    )
                    n += 1
                os.rename(self.path, rotated)
        except Exception:
            # Rotation failures must not block writes; swallow and continue.
            pass

    def stats(self) -> dict:
        try:
            size = self.path.stat().st_size if self.path.exists() else 0
        except OSError:
            size = 0
        return {"path": str(self.path), "size_bytes": size, "rotate_bytes": self.rotate_bytes}
