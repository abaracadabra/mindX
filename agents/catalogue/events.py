"""
CatalogueEvent — typed envelope for the unified catalogue event stream.

Every existing writer (memory_agent.save_timestamped_memory, log_godel_choice,
boardroom._log_session, machine_dreaming phases, BaseTool.execute opt-in) calls
emit_catalogue_event() alongside its existing write. Phase 0 stores the
original payload verbatim so any future projector (Phase 1+) can normalize
without back-instrumentation.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

# Time-sortable UUID approximation (UUIDv4 prefixed with millisecond timestamp
# hex). Cheap, no extra dependency. Real UUIDv7 can replace this later without
# changing the schema — sort order is preserved.
def _uuid7_like() -> str:
    ms = int(time.time() * 1000)
    return f"{ms:012x}-{uuid.uuid4().hex[:20]}"


EventKind = Literal[
    "memory.write",          # MemoryAgent.save_timestamped_memory
    "memory.consolidate",    # STM → LTM promotion
    "memory.dream",          # MachineDreamCycle phase event
    "memory.offload",        # IPFS push (storage.offload_projector)
    "memory.anchor",         # on-chain CID anchor (storage.anchor)
    "godel.choice",          # MemoryAgent.log_godel_choice
    "board.session",         # boardroom session completion
    "board.vote",            # individual vote within a session
    "tool.invoke",           # BaseTool.execute() entry (opt-in)
    "tool.result",           # BaseTool.execute() exit (opt-in)
    "skill.invoke",          # future: skill registry
    "skill.result",
    "alignment.score",       # future: alignment scoring
    "improvement.proposed",  # backlog item added
    "improvement.executed",  # campaign run
    "agent.interact",        # explicit cross-agent call
    "library.discover",      # external library awareness / adoption decision
    "admin.shadow_overlord_action",  # bankon_vault.shadow_overlord — privileged op (auth/provision/clear/sign/release)
    "admin.cabinet.provisioned",     # 8-wallet cabinet minted under company namespace
    "admin.cabinet.cleared",         # cabinet wiped under shadow-overlord authority
]

EVENT_KINDS: tuple[str, ...] = tuple(EventKind.__args__)  # type: ignore[attr-defined]


class CatalogueEvent(BaseModel):
    """
    One envelope per logical event. The `payload` is the original record from
    the source log, stored verbatim so nothing is lost in translation.

    Phase 0 deliberately uses loose typing on `payload` (Dict[str, Any]).
    Phase 1+ projectors normalize into the Dataplex six-resource model
    (EntryGroup / EntryType / AspectType / Entry / EntryLink / EntryLinkType)
    by reading this stream — no back-instrumentation required.
    """

    event_id: str = Field(default_factory=_uuid7_like, description="Time-sortable UUID")
    ts: float = Field(default_factory=lambda: time.time(), description="Unix seconds (float)")
    actor: str = Field(..., description="agent_id or system component name")
    actor_wallet: Optional[str] = Field(default=None, description="Ethereum address from IDManagerAgent if available")
    kind: EventKind  # type: ignore[valid-type]
    source_log: str = Field(..., description="Which existing log this mirrors (e.g. 'godel_choices.jsonl')")
    source_ref: Optional[str] = Field(default=None, description="Filename or memory_id of the original record")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Original record verbatim")
    parent_event_id: Optional[str] = Field(default=None, description="For tool→result and skill→result pairs")
    sig: Optional[str] = Field(default=None, description="eth_account signature (off by default)")

    model_config = {"extra": "allow"}


# ── Emit helper ────────────────────────────────────────────────────────────
#
# Importing the singleton lazily so this module remains import-safe even when
# the runtime config / project root is unavailable (tests, scripts).

_log_singleton = None
_log_lock = None
_emit_disabled = bool(os.environ.get("MINDX_CATALOGUE_DISABLE"))


def _get_log():
    """Lazy singleton accessor for the file-backed log."""
    global _log_singleton, _log_lock
    if _log_singleton is not None:
        return _log_singleton
    if _log_lock is None:
        import asyncio as _asyncio
        _log_lock = _asyncio.Lock()
    from .log import CatalogueEventLog  # local import — avoids cycles
    _log_singleton = CatalogueEventLog.default()
    return _log_singleton


async def emit_catalogue_event(
    kind: str,
    actor: str,
    payload: Dict[str, Any],
    *,
    source_log: str,
    source_ref: Optional[str] = None,
    actor_wallet: Optional[str] = None,
    parent_event_id: Optional[str] = None,
) -> Optional[str]:
    """
    Append one CatalogueEvent. Never raises. Returns the event_id on success,
    None on any failure — callers must not depend on the return value.

    Caller invariant: this MUST be called *alongside* the existing write,
    never replacing it. The original log remains the source of truth.
    """
    if _emit_disabled:
        return None
    if kind not in EVENT_KINDS:
        # Soft-validate: log and drop rather than raising in a hot path.
        try:
            from utils.logging_config import get_logger
            get_logger(__name__).warning("catalogue: unknown kind %r — dropping", kind)
        except Exception:
            pass
        return None
    try:
        evt = CatalogueEvent(
            kind=kind,           # type: ignore[arg-type]
            actor=actor,
            payload=payload or {},
            source_log=source_log,
            source_ref=source_ref,
            actor_wallet=actor_wallet,
            parent_event_id=parent_event_id,
        )
        log = _get_log()
        await log.append(evt)
        return evt.event_id
    except Exception:
        # Phase 0 invariant: emit failures must NEVER affect callers.
        try:
            from utils.logging_config import get_logger
            get_logger(__name__).debug("catalogue.emit failed", exc_info=True)
        except Exception:
            pass
        return None
