# agents/monitoring/rate_limit_dashboard.py
"""
Live rate limit monitoring dashboard backend.
Provides real-time metrics, circuit breaker status, and stuck loop alerts.
"""
import time
from typing import Dict, Any, Optional, List
from pathlib import Path

from utils.logging_config import get_logger
from utils.config import Config, PROJECT_ROOT
from llm.rate_limiter import DualLayerRateLimiter, RateLimiter
from agents.core.stuck_loop_detector import StuckLoopDetector
from agents.core.session_manager import SessionManager

logger = get_logger(__name__)


class RateLimitDashboard:
    """
    Dashboard backend for rate limit monitoring.
    Aggregates metrics from rate limiters, circuit breakers, and stuck loop detectors.
    """
    
    def __init__(self):
        self.config = Config()
        logger.info("RateLimitDashboard initialized")
    
    def get_rate_limit_metrics(self, rate_limiter: Optional[Any] = None) -> Dict[str, Any]:
        """Get rate limit metrics from a rate limiter."""
        if rate_limiter is None:
            return {
                "status": "no_limiter",
                "message": "No rate limiter available"
            }
        
        # Handle both RateLimiter and DualLayerRateLimiter
        if isinstance(rate_limiter, DualLayerRateLimiter):
            metrics = rate_limiter.get_metrics()
            return {
                "type": "dual_layer",
                "minute_limiter": {
                    "rate_limit": f"{rate_limiter.minute_limiter.requests_per_minute}/min",
                    "current_tokens": f"{rate_limiter.minute_limiter.current_tokens:.1f}/{rate_limiter.minute_limiter.max_tokens}",
                    "metrics": rate_limiter.minute_limiter.get_metrics()
                },
                "hourly_limiter": {
                    "rate_limit": f"{rate_limiter.hourly_limiter.requests_per_hour}/hour",
                    "calls_this_hour": len(rate_limiter.hourly_limiter.call_history),
                    "remaining_calls": rate_limiter.hourly_limiter.get_remaining_calls(),
                    "metrics": rate_limiter.hourly_limiter.get_metrics()
                },
                "combined_status": metrics.get("combined_status", {})
            }
        elif isinstance(rate_limiter, RateLimiter):
            metrics = rate_limiter.get_metrics()
            return {
                "type": "single_layer",
                "rate_limit": f"{rate_limiter.requests_per_minute}/min",
                "current_tokens": f"{rate_limiter.current_tokens:.1f}/{rate_limiter.max_tokens}",
                "metrics": metrics
            }
        else:
            return {
                "status": "unknown_type",
                "message": f"Unknown rate limiter type: {type(rate_limiter)}"
            }
    
    def get_circuit_breaker_status(
        self,
        stuck_loop_detector: Optional[StuckLoopDetector] = None
    ) -> Dict[str, Any]:
        """Get circuit breaker status from stuck loop detector."""
        if stuck_loop_detector is None:
            return {
                "status": "no_detector",
                "message": "No stuck loop detector available"
            }
        
        status = stuck_loop_detector.get_status()
        stuck_status = stuck_loop_detector.check_stuck()
        
        return {
            "is_stuck": stuck_status["is_stuck"],
            "circuit_breaker_open": stuck_status["circuit_breaker_open"],
            "consecutive_no_progress": status["consecutive_no_progress"],
            "consecutive_done_signals": status["consecutive_done_signals"],
            "recent_errors": status["recent_errors"],
            "reasons": stuck_status.get("reasons", []),
            "config": status["config"]
        }
    
    def get_session_status(
        self,
        session_manager: Optional[SessionManager] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get session status."""
        if session_manager is None:
            return {
                "status": "no_manager",
                "message": "No session manager available"
            }
        
        if session_id:
            session_status = session_manager.get_session_status(session_id)
            if session_status:
                return session_status
            else:
                return {
                    "status": "not_found",
                    "message": f"Session {session_id} not found or expired"
                }
        else:
            # Return all sessions
            sessions = session_manager.list_sessions()
            return {
                "total_sessions": len(sessions),
                "sessions": sessions
            }
    
    def get_dashboard_data(
        self,
        rate_limiter: Optional[Any] = None,
        stuck_loop_detector: Optional[StuckLoopDetector] = None,
        session_manager: Optional[SessionManager] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get complete dashboard data."""
        return {
            "timestamp": time.time(),
            "rate_limits": self.get_rate_limit_metrics(rate_limiter),
            "circuit_breaker": self.get_circuit_breaker_status(stuck_loop_detector),
            "sessions": self.get_session_status(session_manager, session_id),
            "alerts": self._generate_alerts(rate_limiter, stuck_loop_detector, session_manager)
        }
    
    def _generate_alerts(
        self,
        rate_limiter: Optional[Any] = None,
        stuck_loop_detector: Optional[StuckLoopDetector] = None,
        session_manager: Optional[SessionManager] = None
    ) -> List[Dict[str, Any]]:
        """Generate alerts based on current state."""
        alerts = []
        
        # Rate limit alerts
        if rate_limiter:
            if isinstance(rate_limiter, DualLayerRateLimiter):
                hourly_metrics = rate_limiter.hourly_limiter.get_metrics()
                if hourly_metrics["at_limit"]:
                    alerts.append({
                        "level": "warning",
                        "type": "rate_limit",
                        "message": f"Hourly rate limit reached: {hourly_metrics['calls_this_hour']}/{hourly_metrics['requests_per_hour']} calls",
                        "timestamp": time.time()
                    })
                elif hourly_metrics["utilization"] > 0.8:
                    alerts.append({
                        "level": "info",
                        "type": "rate_limit",
                        "message": f"Hourly rate limit at {hourly_metrics['utilization']:.1%} utilization",
                        "timestamp": time.time()
                    })
        
        # Circuit breaker alerts
        if stuck_loop_detector:
            stuck_status = stuck_loop_detector.check_stuck()
            if stuck_status["is_stuck"]:
                alerts.append({
                    "level": "error",
                    "type": "circuit_breaker",
                    "message": f"Loop is stuck! Reasons: {', '.join(stuck_status.get('reasons', []))}",
                    "timestamp": time.time()
                })
        
        # Session alerts
        if session_manager:
            session_manager.cleanup_expired_sessions()
            sessions = session_manager.list_sessions()
            for session in sessions:
                if session and session.get("time_until_expiry", 0) < 3600:  # Less than 1 hour
                    alerts.append({
                        "level": "info",
                        "type": "session",
                        "message": f"Session {session['session_id']} expires in {session['time_until_expiry']:.0f} seconds",
                        "timestamp": time.time()
                    })
        
        return alerts
