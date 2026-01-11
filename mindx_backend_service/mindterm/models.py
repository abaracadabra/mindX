from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Literal, Dict, Any

RiskLevel = Literal["low", "medium", "high"]


@dataclass
class SessionMeta:
    session_id: str
    shell: str
    cwd: Optional[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskDecision:
    level: RiskLevel
    reason: str
    requires_confirm: bool


@dataclass
class CommandBlock:
    block_id: str
    session_id: str
    command: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime = field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    exit_code: Optional[int] = None
    output_len: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)

