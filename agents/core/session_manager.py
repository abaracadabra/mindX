# agents/core/session_manager.py
"""
Session lifecycle management for agent loops.
Tracks session state with expiration and auto-reset triggers.
"""
import time
import json
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta

from utils.logging_config import get_logger
from utils.config import Config, PROJECT_ROOT

logger = get_logger(__name__)


@dataclass
class SessionState:
    """Represents a session state."""
    session_id: str
    agent_id: str
    created_at: float
    last_activity: float
    expires_at: float
    cycle_count: int = 0
    circuit_breaker_trips: int = 0
    last_reset_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if session has expired."""
        return time.time() > self.expires_at
    
    def time_until_expiry(self) -> float:
        """Get seconds until session expires."""
        return max(0, self.expires_at - time.time())


class SessionManager:
    """
    Manages session lifecycle for agent loops.
    - Tracks session state per agent/operation
    - 24-hour expiration with configurable timeout
    - Auto-reset on circuit breaker trips
    - Session state persistence
    """
    
    def __init__(
        self,
        default_expiration_hours: int = 24,
        storage_path: Optional[Path] = None
    ):
        self.default_expiration_hours = default_expiration_hours
        self.storage_path = storage_path or (PROJECT_ROOT / "data" / "sessions")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.config = Config()
        # Load config override if available
        session_config = self.config.get("session_management", {})
        if session_config:
            self.default_expiration_hours = session_config.get(
                "default_expiration_hours", self.default_expiration_hours
            )
        
        # In-memory session cache
        self.sessions: Dict[str, SessionState] = {}
        
        # Load persisted sessions
        self._load_sessions()
        
        logger.info(
            f"SessionManager initialized. "
            f"Default expiration: {self.default_expiration_hours} hours, "
            f"Storage: {self.storage_path}"
        )
    
    def _load_sessions(self):
        """Load persisted sessions from disk."""
        try:
            sessions_file = self.storage_path / "sessions.json"
            if sessions_file.exists():
                with sessions_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for session_id, session_data in data.items():
                        # Reconstruct SessionState
                        session = SessionState(**session_data)
                        # Only load non-expired sessions
                        if not session.is_expired():
                            self.sessions[session_id] = session
                        else:
                            logger.debug(f"Session {session_id} expired, not loading")
        except Exception as e:
            logger.warning(f"Failed to load sessions: {e}")
    
    def _save_sessions(self):
        """Save sessions to disk."""
        try:
            sessions_file = self.storage_path / "sessions.json"
            data = {
                session_id: asdict(session)
                for session_id, session in self.sessions.items()
            }
            with sessions_file.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save sessions: {e}")
    
    def create_session(
        self,
        agent_id: str,
        session_id: Optional[str] = None,
        expiration_hours: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SessionState:
        """Create a new session."""
        if session_id is None:
            import uuid
            session_id = f"{agent_id}_{uuid.uuid4().hex[:8]}"
        
        now = time.time()
        expiration = expiration_hours or self.default_expiration_hours
        
        session = SessionState(
            session_id=session_id,
            agent_id=agent_id,
            created_at=now,
            last_activity=now,
            expires_at=now + (expiration * 3600),
            cycle_count=0,
            circuit_breaker_trips=0,
            metadata=metadata or {}
        )
        
        self.sessions[session_id] = session
        self._save_sessions()
        
        logger.info(
            f"Session created: {session_id} for agent {agent_id}, "
            f"expires in {expiration} hours"
        )
        
        return session
    
    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Get a session by ID."""
        session = self.sessions.get(session_id)
        
        if session and session.is_expired():
            logger.info(f"Session {session_id} expired, removing")
            self.sessions.pop(session_id, None)
            self._save_sessions()
            return None
        
        return session
    
    def update_session_activity(
        self,
        session_id: str,
        cycle_count: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update session activity timestamp."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.last_activity = time.time()
        if cycle_count is not None:
            session.cycle_count = cycle_count
        if metadata:
            session.metadata.update(metadata)
        
        self._save_sessions()
        return True
    
    def record_circuit_breaker_trip(self, session_id: str) -> bool:
        """Record a circuit breaker trip for a session."""
        session = self.get_session(session_id)
        if not session:
            return False
        
        session.circuit_breaker_trips += 1
        session.last_reset_reason = "circuit_breaker_trip"
        self._save_sessions()
        
        logger.warning(
            f"Circuit breaker trip recorded for session {session_id} "
            f"(total trips: {session.circuit_breaker_trips})"
        )
        
        return True
    
    def reset_session(
        self,
        session_id: str,
        reason: Optional[str] = None
    ) -> Optional[SessionState]:
        """Reset a session (create new one with same agent_id)."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        agent_id = session.agent_id
        metadata = session.metadata.copy()
        metadata["previous_session_id"] = session_id
        metadata["reset_reason"] = reason or "manual"
        
        # Remove old session
        self.sessions.pop(session_id, None)
        
        # Create new session
        new_session = self.create_session(
            agent_id=agent_id,
            metadata=metadata
        )
        
        logger.info(
            f"Session {session_id} reset. New session: {new_session.session_id}, "
            f"reason: {reason or 'manual'}"
        )
        
        return new_session
    
    def auto_reset_on_circuit_breaker(
        self,
        session_id: str,
        max_trips: int = 3
    ) -> Optional[SessionState]:
        """Auto-reset session if circuit breaker trips exceed threshold."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        if session.circuit_breaker_trips >= max_trips:
            return self.reset_session(
                session_id=session_id,
                reason=f"circuit_breaker_trips_exceeded_{max_trips}"
            )
        
        return None
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions."""
        expired = [
            session_id
            for session_id, session in self.sessions.items()
            if session.is_expired()
        ]
        
        for session_id in expired:
            self.sessions.pop(session_id, None)
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")
            self._save_sessions()
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get status information for a session."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        return {
            "session_id": session.session_id,
            "agent_id": session.agent_id,
            "created_at": datetime.fromtimestamp(session.created_at).isoformat(),
            "last_activity": datetime.fromtimestamp(session.last_activity).isoformat(),
            "expires_at": datetime.fromtimestamp(session.expires_at).isoformat(),
            "time_until_expiry": session.time_until_expiry(),
            "cycle_count": session.cycle_count,
            "circuit_breaker_trips": session.circuit_breaker_trips,
            "last_reset_reason": session.last_reset_reason,
            "is_expired": session.is_expired(),
            "metadata": session.metadata
        }
    
    def list_sessions(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtered by agent_id."""
        self.cleanup_expired_sessions()
        
        sessions = list(self.sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        
        return [
            self.get_session_status(s.session_id)
            for s in sessions
            if self.get_session_status(s.session_id) is not None
        ]
