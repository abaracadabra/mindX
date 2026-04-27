"""
Offload eligibility predicate.

Decides whether an STM memory file is safe to push to IPFS + delete locally.
"""

from __future__ import annotations

import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Optional

DATE_RE = re.compile(r"^(\d{8})$")  # YYYYMMDD directory name


class OffloadCandidate(NamedTuple):
    path: Path
    agent_id: str
    date_str: str  # YYYYMMDD
    age_days: float
    size_bytes: int


def stm_root(project_root: Path) -> Path:
    return project_root / "data" / "memory" / "stm"


def parse_date_dir(name: str) -> Optional[datetime]:
    """Parse a YYYYMMDD subdirectory name into a datetime; None if invalid."""
    m = DATE_RE.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d")
    except ValueError:
        return None


def list_eligible(
    project_root: Path,
    *,
    min_age_days: float = 14.0,
    agent_id: Optional[str] = None,
) -> list[OffloadCandidate]:
    """
    Iterate STM and yield candidate files older than the cutoff.

    File-level granularity is not used here; the offload batches at the
    (agent, date_dir) level for efficiency. Returns one candidate per
    eligible *directory*, with size_bytes summed for that day.
    """
    root = stm_root(project_root)
    if not root.is_dir():
        return []
    now = time.time()
    cutoff_ts = now - (min_age_days * 86400)
    out: list[OffloadCandidate] = []
    try:
        for agent_dir in root.iterdir():
            if not agent_dir.is_dir():
                continue
            if agent_id and agent_dir.name != agent_id:
                continue
            try:
                for date_dir in agent_dir.iterdir():
                    if not date_dir.is_dir():
                        continue
                    parsed = parse_date_dir(date_dir.name)
                    if parsed is None:
                        continue
                    # Use the date directory's *parsed date* as authoritative,
                    # not mtime — directories can be touched by listing or
                    # promotion without their content changing.
                    age_days = (now - parsed.timestamp()) / 86400
                    if age_days < min_age_days:
                        continue
                    size = 0
                    file_count = 0
                    try:
                        for f in date_dir.iterdir():
                            if f.is_file():
                                file_count += 1
                                try:
                                    size += f.stat().st_size
                                except OSError:
                                    pass
                    except OSError:
                        continue
                    if file_count == 0:
                        continue
                    out.append(OffloadCandidate(
                        path=date_dir,
                        agent_id=agent_dir.name,
                        date_str=date_dir.name,
                        age_days=age_days,
                        size_bytes=size,
                    ))
            except OSError:
                continue
    except OSError:
        return []
    # Sort: largest first within the cutoff (free most space soonest)
    out.sort(key=lambda c: c.size_bytes, reverse=True)
    return out
