from __future__ import annotations

import asyncio
import contextlib
import fcntl
import json
import os
import pty
import signal
import struct
import termios
import uuid
import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Any

from utils.logging_config import get_logger
from .models import SessionMeta, CommandBlock
from .transcript import append as tappend
from .events import BUS
from .blocks import STORE

logger = get_logger(__name__)

# Sentinel format emitted by shell wrapper
# Example: __MINDTERM__END__:abcd1234:0
SENTINEL_RE = re.compile(r"__MINDTERM__END__:(?P<bid>[a-f0-9]+):(?P<code>-?\d+)\s*$")


@dataclass
class PtySession:
    meta: SessionMeta
    master_fd: int
    child_pid: int
    out_queue: "asyncio.Queue[str]"
    reader_installed: bool = False
    current_block_id: Optional[str] = None


class MindTermService:
    """
    v0.0.4:
    - True PTY (pty.fork) for interactive TUIs.
    - Command blocks:
      When client submits a line, we wrap it so shell prints a sentinel with exit code.
    - Structured events for agents via EventBus:
      CommandStarted, OutputChunk, CommandFinished, RiskFlagged, UserConfirmed, Sys.
    - Integrated with mindX logging, monitoring, and orchestration systems.
    """

    def __init__(self, coordinator_agent=None, resource_monitor=None, performance_monitor=None) -> None:
        self._sessions: Dict[str, PtySession] = {}
        self.coordinator_agent = coordinator_agent
        self.resource_monitor = resource_monitor
        self.performance_monitor = performance_monitor
        self._session_metrics: Dict[str, Dict[str, Any]] = {}
        self._knowledge_base: Dict[str, Any] = {}
        self._load_knowledge_base()
        logger.info("MindTermService initialized with mindX integration")

    def _load_knowledge_base(self) -> None:
        """Load knowledge base from JSON file."""
        knowledge_base_path = Path(__file__).parent / "knowledge_base.json"
        try:
            if knowledge_base_path.exists():
                with open(knowledge_base_path, 'r', encoding='utf-8') as f:
                    self._knowledge_base = json.load(f)
                repo_count = len(self._knowledge_base.get('repositories', {}))
                integration_count = len(self._knowledge_base.get('integrations', {}))
                logger.info(f"MindTerm: Loaded knowledge base with {repo_count} repositories and {integration_count} integrations")
                
                # Log xterm.js integration status if available
                xterm_info = self._knowledge_base.get('integrations', {}).get('xtermjs')
                if xterm_info:
                    logger.info(f"MindTerm: xterm.js integration status: {xterm_info.get('status', 'unknown')} (v{xterm_info.get('version', 'unknown')})")
            else:
                logger.warning(f"MindTerm: Knowledge base file not found at {knowledge_base_path}")
                self._knowledge_base = {"repositories": {}, "knowledge_entries": [], "integrations": {}}
        except Exception as e:
            logger.error(f"MindTerm: Failed to load knowledge base: {e}")
            self._knowledge_base = {"repositories": {}, "knowledge_entries": [], "integrations": {}}
    
    def get_knowledge_base(self) -> Dict[str, Any]:
        """Get the knowledge base."""
        return self._knowledge_base
    
    def get_repository_info(self, repo_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a repository from the knowledge base."""
        return self._knowledge_base.get("repositories", {}).get(repo_name)
    
    def get_integration_info(self, integration_name: str) -> Optional[Dict[str, Any]]:
        """Get information about an integration (e.g., xterm.js) from the knowledge base."""
        return self._knowledge_base.get("integrations", {}).get(integration_name)
    
    def get_all_integrations(self) -> Dict[str, Any]:
        """Get all integrations from the knowledge base."""
        return self._knowledge_base.get("integrations", {})

    def get(self, session_id: str) -> Optional[PtySession]:
        return self._sessions.get(session_id)

    async def create_session(
        self,
        shell: Optional[str] = None,
        cwd: Optional[str] = None,
        cols: int = 120,
        rows: int = 40,
    ) -> SessionMeta:
        session_id = uuid.uuid4().hex
        shell = shell or os.environ.get("SHELL", "/bin/bash")

        pid, master_fd = pty.fork()
        if pid == 0:
            try:
                if cwd:
                    os.chdir(cwd)
                env = dict(os.environ)
                env.setdefault("TERM", "xterm-256color")
                # Interactive shell for consistent behavior
                os.execvpe(shell, [shell, "-i"], env)
            except Exception:
                os._exit(1)

        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        meta = SessionMeta(session_id=session_id, shell=shell, cwd=cwd)
        out_q: asyncio.Queue[str] = asyncio.Queue()

        sess = PtySession(meta=meta, master_fd=master_fd, child_pid=pid, out_queue=out_q)
        self._sessions[session_id] = sess

        # Initialize session metrics
        self._session_metrics[session_id] = {
            "created_at": time.time(),
            "commands_executed": 0,
            "commands_failed": 0,
            "total_output_bytes": 0,
            "risk_flags": 0,
            "last_activity": time.time()
        }

        self.resize(session_id, cols=cols, rows=rows)
        self._install_reader(session_id)

        tappend(session_id, "sys", f"session created pid={pid} shell={shell} cwd={cwd or ''} size={cols}x{rows}")
        BUS.emit(session_id, "Sys", {"msg": "session_created", "pid": pid, "shell": shell, "cwd": cwd, "cols": cols, "rows": rows})
        
        # Log to mindX system
        logger.info(f"MindTerm session created: {session_id} (pid={pid}, shell={shell}, cwd={cwd})")
        
        # Publish event to coordinator if available
        if self.coordinator_agent:
            try:
                self.coordinator_agent.publish_event("mindterm.session_created", {
                    "session_id": session_id,
                    "pid": pid,
                    "shell": shell,
                    "cwd": cwd
                })
            except Exception as e:
                logger.warning(f"Failed to publish mindterm event to coordinator: {e}")
        
        return meta

    def _install_reader(self, session_id: str) -> None:
        sess = self._sessions.get(session_id)
        if not sess or sess.reader_installed:
            return

        loop = asyncio.get_running_loop()

        def _on_readable():
            try:
                while True:
                    data = os.read(sess.master_fd, 8192)
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace")

                    # Always transcript + raw output stream
                    tappend(session_id, "out", text)
                    try:
                        sess.out_queue.put_nowait(text)
                    except asyncio.QueueFull:
                        pass

                    # Parse sentinel lines to close blocks
                    self._process_output_for_blocks(session_id, text)

            except BlockingIOError:
                return
            except OSError:
                self._safe_close_fd(sess.master_fd)
                with contextlib.suppress(Exception):
                    loop.remove_reader(sess.master_fd)

        loop.add_reader(sess.master_fd, _on_readable)
        sess.reader_installed = True

    def _process_output_for_blocks(self, session_id: str, text: str) -> None:
        """
        Parse text for sentinel lines. If detected, emit CommandFinished.
        Also emit OutputChunk events for agent subscribers.
        """
        sess = self._sessions.get(session_id)
        if not sess:
            return

        BUS.emit(session_id, "OutputChunk", {
            "block_id": sess.current_block_id,
            "data": text,
        })

        # We check per line for sentinel
        lines = text.splitlines()
        for ln in lines:
            m = SENTINEL_RE.search(ln)
            if not m:
                continue

            bid = m.group("bid")
            code = int(m.group("code"))
            now = datetime.utcnow()

            # close block
            STORE.update_block(session_id, bid, finished_at=now, exit_code=code)
            BUS.emit(session_id, "CommandFinished", {
                "block_id": bid,
                "exit_code": code,
                "finished_at": now.isoformat() + "Z",
            })

            # Update metrics
            if session_id in self._session_metrics:
                metrics = self._session_metrics[session_id]
                metrics["commands_executed"] += 1
                metrics["last_activity"] = time.time()
                if code != 0:
                    metrics["commands_failed"] += 1

            # Log command completion
            logger.info(f"MindTerm command finished: session={session_id}, block={bid}, exit_code={code}")
            
            # Track performance if monitor available
            if self.performance_monitor:
                try:
                    # Track as API call for monitoring
                    self.performance_monitor.record_call(
                        "mindterm.command",
                        success=(code == 0),
                        latency_ms=0,  # Could track actual execution time
                        error_type=None if code == 0 else f"exit_code_{code}"
                    )
                except Exception as e:
                    logger.warning(f"Failed to record performance metric: {e}")

            # clear current
            if sess.current_block_id == bid:
                sess.current_block_id = None

    async def write_raw(self, session_id: str, data: str) -> None:
        sess = self._sessions.get(session_id)
        if not sess:
            raise KeyError("no such session")
        if not data:
            return
        tappend(session_id, "in", data)
        b = data.encode("utf-8", errors="replace")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._write_all, sess.master_fd, b)

    async def submit_line_as_block(self, session_id: str, line: str) -> Tuple[str, str]:
        """
        Wrap a command line so shell prints a sentinel with exit code.
        Returns (block_id, wrapped_command).
        """
        sess = self._sessions.get(session_id)
        if not sess:
            raise KeyError("no such session")

        block_id = uuid.uuid4().hex
        now = datetime.utcnow()

        b = CommandBlock(
            block_id=block_id,
            session_id=session_id,
            command=line,
            created_at=now,
            started_at=now,
            meta={"wrapper": "sentinel_v1"},
        )
        STORE.add_block(b)

        sess.current_block_id = block_id

        BUS.emit(session_id, "CommandStarted", {
            "block_id": block_id,
            "command": line,
            "started_at": now.isoformat() + "Z",
        })

        # Log command start
        logger.info(f"MindTerm command started: session={session_id}, block={block_id}, command={line[:100]}")
        
        # Publish event to coordinator
        if self.coordinator_agent:
            try:
                self.coordinator_agent.publish_event("mindterm.command_started", {
                    "session_id": session_id,
                    "block_id": block_id,
                    "command": line
                })
            except Exception as e:
                logger.warning(f"Failed to publish mindterm command event: {e}")

        # IMPORTANT: bash-compatible wrapper:
        # Execute the line, capture exit code, then print sentinel.
        # Uses printf to avoid echo quirks.
        wrapped = f"""{line}; __ec=$?; printf "\\n__MINDTERM__END__:{block_id}:%d\\n" "$__ec" """
        return block_id, wrapped

    async def write_block_line(self, session_id: str, line: str) -> str:
        bid, wrapped = await self.submit_line_as_block(session_id, line)
        await self.write_raw(session_id, wrapped + "\n")
        return bid

    def _write_all(self, fd: int, b: bytes) -> None:
        view = memoryview(b)
        total = 0
        while total < len(b):
            try:
                n = os.write(fd, view[total:])
                total += n
            except BlockingIOError:
                continue
            except OSError:
                break

    async def read_frame(self, session_id: str) -> str:
        sess = self._sessions.get(session_id)
        if not sess:
            raise KeyError("no such session")
        return await sess.out_queue.get()

    def resize(self, session_id: str, cols: int, rows: int) -> None:
        sess = self._sessions.get(session_id)
        if not sess:
            raise KeyError("no such session")

        cols = int(max(20, cols))
        rows = int(max(5, rows))
        winsz = struct.pack("HHHH", rows, cols, 0, 0)
        try:
            fcntl.ioctl(sess.master_fd, termios.TIOCSWINSZ, winsz)
            tappend(session_id, "sys", f"resize {cols}x{rows}")
            BUS.emit(session_id, "Resize", {"cols": cols, "rows": rows})
        except OSError:
            pass

    async def close(self, session_id: str) -> None:
        sess = self._sessions.pop(session_id, None)
        if not sess:
            return

        tappend(session_id, "sys", "session closing")
        BUS.emit(session_id, "Sys", {"msg": "session_closing"})
        
        # Log session closure
        metrics = self._session_metrics.pop(session_id, {})
        logger.info(f"MindTerm session closing: {session_id}, metrics={metrics}")
        
        # Publish event to coordinator
        if self.coordinator_agent:
            try:
                self.coordinator_agent.publish_event("mindterm.session_closed", {
                    "session_id": session_id,
                    "metrics": metrics
                })
            except Exception as e:
                logger.warning(f"Failed to publish mindterm close event: {e}")

        loop = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and sess.reader_installed:
            with contextlib.suppress(Exception):
                loop.remove_reader(sess.master_fd)

        with contextlib.suppress(ProcessLookupError):
            os.kill(sess.child_pid, signal.SIGTERM)

        await self._waitpid_with_timeout(sess.child_pid, timeout=1.5)
        with contextlib.suppress(ProcessLookupError):
            os.kill(sess.child_pid, signal.SIGKILL)
        await self._waitpid_with_timeout(sess.child_pid, timeout=0.8)

        self._safe_close_fd(sess.master_fd)
        tappend(session_id, "sys", "session closed")
        BUS.emit(session_id, "Sys", {"msg": "session_closed"})

    async def _waitpid_with_timeout(self, pid: int, timeout: float) -> None:
        loop = asyncio.get_running_loop()

        def _wait():
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                return

        try:
            await asyncio.wait_for(loop.run_in_executor(None, _wait), timeout=timeout)
        except asyncio.TimeoutError:
            return

    def _safe_close_fd(self, fd: int) -> None:
        with contextlib.suppress(Exception):
            os.close(fd)

    def get_session_metrics(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get metrics for a specific session or all sessions."""
        if session_id:
            return self._session_metrics.get(session_id, {})
        return {
            "total_sessions": len(self._sessions),
            "active_sessions": len([s for s in self._sessions.values() if s.reader_installed]),
            "sessions": {sid: metrics for sid, metrics in self._session_metrics.items()}
        }

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get resource usage for all mindterm sessions."""
        if not self.resource_monitor:
            return {}
        
        try:
            # Get current system resources
            resource_usage = self.resource_monitor.get_resource_usage()
            
            # Add mindterm-specific metrics
            total_output = sum(m.get("total_output_bytes", 0) for m in self._session_metrics.values())
            total_commands = sum(m.get("commands_executed", 0) for m in self._session_metrics.values())
            
            return {
                "system": resource_usage,
                "mindterm": {
                    "active_sessions": len(self._sessions),
                    "total_commands": total_commands,
                    "total_output_bytes": total_output,
                    "sessions": len(self._session_metrics)
                }
            }
        except Exception as e:
            logger.warning(f"Failed to get resource usage: {e}")
            return {}

