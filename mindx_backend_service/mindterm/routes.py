from __future__ import annotations

import asyncio
from typing import Optional, Dict, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel

from utils.logging_config import get_logger
from .service import MindTermService
from .policy import assess_command
from .transcript import append as tappend
from .events import BUS
from .blocks import STORE

logger = get_logger(__name__)

router = APIRouter(prefix="/mindterm", tags=["mindterm"])

# Service will be initialized with coordinator/monitors on first use
_svc: Optional[MindTermService] = None
_coordinator_agent = None
_resource_monitor = None
_performance_monitor = None

def get_service() -> MindTermService:
    """Get or create the mindterm service with proper integration."""
    global _svc, _coordinator_agent, _resource_monitor, _performance_monitor
    
    if _svc is None:
        # Try to get coordinator and monitors from the app context
        try:
            from orchestration.coordinator_agent import CoordinatorAgent
            # Try to get singleton instances
            _coordinator_agent = None  # Will be set when app starts
            _resource_monitor = None
            _performance_monitor = None
        except ImportError:
            logger.warning("Could not import coordinator agent for mindterm integration")
        
        _svc = MindTermService(
            coordinator_agent=_coordinator_agent,
            resource_monitor=_resource_monitor,
            performance_monitor=_performance_monitor
        )
        logger.info("MindTermService initialized")
    
    return _svc

def set_coordinator_and_monitors(coordinator=None, resource_monitor=None, performance_monitor=None):
    """Set coordinator and monitors for mindterm service."""
    global _coordinator_agent, _resource_monitor, _performance_monitor, _svc
    _coordinator_agent = coordinator
    _resource_monitor = resource_monitor
    _performance_monitor = performance_monitor
    
    # Reinitialize service if it exists
    if _svc is not None:
        _svc.coordinator_agent = coordinator
        _svc.resource_monitor = resource_monitor
        _svc.performance_monitor = performance_monitor
        logger.info("MindTermService updated with coordinator and monitors")

svc = get_service()  # Initialize on module load

class CreateSessionReq(BaseModel):
    shell: Optional[str] = None
    cwd: Optional[str] = None
    cols: Optional[int] = 120
    rows: Optional[int] = 40

class ResizeReq(BaseModel):
    cols: int
    rows: int

@router.post("/sessions")
async def create_session(req: CreateSessionReq) -> Dict[str, Any]:
    """Create a new mindterm PTY session."""
    logger.info(f"Creating mindterm session: shell={req.shell}, cwd={req.cwd}")
    svc = get_service()
    meta = await svc.create_session(
        shell=req.shell,
        cwd=req.cwd,
        cols=req.cols or 120,
        rows=req.rows or 40,
    )
    return {
        "session_id": meta.session_id,
        "shell": meta.shell,
        "cwd": meta.cwd,
        "created_at": meta.created_at.isoformat() + "Z",
    }

@router.post("/sessions/{session_id}/resize")
async def resize_session(session_id: str, req: ResizeReq) -> Dict[str, Any]:
    try:
        svc.resize(session_id, cols=req.cols, rows=req.rows)
        return {"ok": True}
    except KeyError:
        raise HTTPException(status_code=404, detail="No such session")

@router.get("/sessions/{session_id}/blocks")
async def get_blocks(session_id: str, limit: int = 50) -> Dict[str, Any]:
    blocks = STORE.get_recent(session_id, limit=max(1, min(500, limit)))
    return {
        "session_id": session_id,
        "blocks": [
            {
                "block_id": b.block_id,
                "command": b.command,
                "created_at": b.created_at.isoformat() + "Z",
                "started_at": b.started_at.isoformat() + "Z",
                "finished_at": (b.finished_at.isoformat() + "Z") if b.finished_at else None,
                "exit_code": b.exit_code,
                "output_len": b.output_len,
                "meta": b.meta,
            }
            for b in blocks
        ],
    }

@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> Dict[str, Any]:
    """Close and cleanup a mindterm session."""
    logger.info(f"Closing mindterm session: {session_id}")
    svc = get_service()
    await svc.close(session_id)
    return {"ok": True}

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get mindterm service metrics for monitoring."""
    svc = get_service()
    return {
        "service_metrics": svc.get_session_metrics(),
        "resource_usage": svc.get_resource_usage()
    }

@router.get("/metrics/{session_id}")
async def get_session_metrics(session_id: str) -> Dict[str, Any]:
    """Get metrics for a specific session."""
    svc = get_service()
    metrics = svc.get_session_metrics(session_id)
    if not metrics:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_id": session_id, "metrics": metrics}

@router.websocket("/sessions/{session_id}/ws")
async def session_ws(ws: WebSocket, session_id: str):
    """
    Primary UI websocket:
    - Receives keystrokes (type:"in")
    - Receives line submit (type:"line") -> policy gate -> submit as command block (sentinel wrapper)
    - Sends raw output frames (type:"out")
    - Sends risk prompts (type:"risk")
    """
    logger.info(f"MindTerm websocket connection: session={session_id}")
    svc = get_service()
    await ws.accept()
    pending_confirm: Optional[Dict[str, Any]] = None

    async def sender():
        while True:
            frame = await svc.read_frame(session_id)
            await ws.send_json({"type": "out", "data": frame})

    send_task = asyncio.create_task(sender())

    try:
        while True:
            msg = await ws.receive_json()
            mtype = msg.get("type")

            if mtype == "in":
                data = str(msg.get("data", ""))
                await svc.write_raw(session_id, data)

            elif mtype == "line":
                line = str(msg.get("data", "")).strip("\n")
                decision = assess_command(line)
                
                logger.debug(f"MindTerm command assessment: session={session_id}, line={line[:50]}, risk={decision.level}")

                if decision.requires_confirm:
                    pending_confirm = {"line": line, "level": decision.level, "reason": decision.reason}
                    tappend(session_id, "sys", f"risk flagged level={decision.level} reason={decision.reason} line={line}")
                    BUS.emit(session_id, "RiskFlagged", pending_confirm)
                    
                    # Update metrics
                    if session_id in svc._session_metrics:
                        svc._session_metrics[session_id]["risk_flags"] += 1
                    
                    logger.warning(f"MindTerm risk flagged: session={session_id}, level={decision.level}, reason={decision.reason}")
                    await ws.send_json({"type": "risk", **pending_confirm})
                else:
                    bid = await svc.write_block_line(session_id, line)
                    await ws.send_json({"type": "sys", "data": f"block started {bid}"})

            elif mtype == "confirm":
                allow = bool(msg.get("allow", False))
                if not pending_confirm:
                    await ws.send_json({"type": "sys", "data": "No pending confirmation."})
                    continue
                if allow:
                    line = pending_confirm["line"]
                    tappend(session_id, "sys", f"user confirmed run line={line}")
                    BUS.emit(session_id, "UserConfirmed", {"allow": True, "line": line})
                    bid = await svc.write_block_line(session_id, line)
                    await ws.send_json({"type": "sys", "data": f"Confirmed. Executing as block {bid}."})
                else:
                    tappend(session_id, "sys", "user denied risky command")
                    BUS.emit(session_id, "UserConfirmed", {"allow": False})
                    await ws.send_json({"type": "sys", "data": "Denied. Not executed."})
                pending_confirm = None

            else:
                await ws.send_json({"type": "sys", "data": f"Unknown message type: {mtype}"})

    except WebSocketDisconnect:
        logger.info(f"MindTerm websocket disconnected: session={session_id}")
    except KeyError:
        logger.error(f"MindTerm session not found: {session_id}")
        raise HTTPException(status_code=404, detail="No such session")
    except Exception as e:
        logger.error(f"MindTerm websocket error: session={session_id}, error={e}", exc_info=True)
    finally:
        send_task.cancel()
        try:
            await svc.close(session_id)
        except Exception as e:
            logger.warning(f"Error closing mindterm session: {e}")

@router.websocket("/sessions/{session_id}/events")
async def events_ws(ws: WebSocket, session_id: str):
    """
    Agent/observer websocket:
    - Streams structured events (CommandStarted, OutputChunk, CommandFinished, RiskFlagged, etc.)
    - Read-only (no commands executed here).
    """
    await ws.accept()
    q = BUS.subscribe(session_id)
    try:
        while True:
            evt = await q.get()
            await ws.send_json({
                "type": evt.type,
                "ts": evt.ts,
                "session_id": evt.session_id,
                "payload": evt.payload,
            })
    except WebSocketDisconnect:
        logger.info(f"MindTerm events websocket disconnected: session={session_id}")
    except Exception as e:
        logger.error(f"MindTerm events websocket error: session={session_id}, error={e}", exc_info=True)
    finally:
        BUS.unsubscribe(session_id, q)

