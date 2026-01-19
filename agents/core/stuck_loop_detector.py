# agents/core/stuck_loop_detector.py
"""
Stuck loop detection for agent loops.
Detects when loops are stuck (no progress, repeated errors, same patterns).
"""
import time
from typing import Dict, Any, Optional, List
from collections import deque, defaultdict
from dataclasses import dataclass, field

from utils.logging_config import get_logger
from utils.config import Config

logger = get_logger(__name__)


@dataclass
class LoopState:
    """State tracking for a single loop cycle."""
    cycle_number: int
    timestamp: float
    has_file_changes: bool = False
    error_message: Optional[str] = None
    success: bool = False
    done_signal: bool = False
    result_data: Optional[Dict[str, Any]] = None


@dataclass
class StuckLoopConfig:
    """Configuration for stuck loop detection."""
    max_cycles_no_progress: int = 3
    max_repeated_errors: int = 5
    circuit_breaker_threshold: int = 3
    error_similarity_threshold: float = 0.8  # For detecting similar errors


class StuckLoopDetector:
    """
    Detects when agent loops are stuck by tracking:
    - Consecutive cycles with no file changes
    - Repeated error patterns
    - "Done" signals without actual completion
    """
    
    def __init__(self, config: Optional[StuckLoopConfig] = None):
        self.config = config or StuckLoopConfig()
        self.app_config = Config()
        
        # Load config from app config if available
        stuck_config = self.app_config.get("stuck_loop_detection", {})
        if stuck_config:
            self.config.max_cycles_no_progress = stuck_config.get(
                "max_cycles_no_progress", self.config.max_cycles_no_progress
            )
            self.config.max_repeated_errors = stuck_config.get(
                "max_repeated_errors", self.config.max_repeated_errors
            )
            self.config.circuit_breaker_threshold = stuck_config.get(
                "circuit_breaker_threshold", self.config.circuit_breaker_threshold
            )
        
        # State tracking
        self.cycle_history: deque = deque(maxlen=20)  # Keep last 20 cycles
        self.error_history: deque = deque(maxlen=50)  # Keep last 50 errors
        self.consecutive_no_progress: int = 0
        self.consecutive_done_signals: int = 0
        self.circuit_breaker_open: bool = False
        self.circuit_breaker_opened_at: Optional[float] = None
        
        logger.info(
            f"StuckLoopDetector initialized. "
            f"Max cycles no progress: {self.config.max_cycles_no_progress}, "
            f"Max repeated errors: {self.config.max_repeated_errors}"
        )
    
    def record_cycle(
        self,
        cycle_number: int,
        has_file_changes: bool = False,
        error_message: Optional[str] = None,
        success: bool = False,
        done_signal: bool = False,
        result_data: Optional[Dict[str, Any]] = None
    ) -> LoopState:
        """Record a cycle and return the loop state."""
        state = LoopState(
            cycle_number=cycle_number,
            timestamp=time.time(),
            has_file_changes=has_file_changes,
            error_message=error_message,
            success=success,
            done_signal=done_signal,
            result_data=result_data
        )
        
        self.cycle_history.append(state)
        
        # Update consecutive counters
        if has_file_changes:
            self.consecutive_no_progress = 0
        else:
            self.consecutive_no_progress += 1
        
        if done_signal:
            self.consecutive_done_signals += 1
        else:
            self.consecutive_done_signals = 0
        
        # Track errors
        if error_message:
            self.error_history.append({
                "message": error_message,
                "timestamp": time.time(),
                "cycle": cycle_number
            })
        
        return state
    
    def _check_repeated_errors(self) -> bool:
        """Check if we're seeing repeated errors."""
        if len(self.error_history) < self.config.max_repeated_errors:
            return False
        
        # Get recent errors
        recent_errors = list(self.error_history)[-self.config.max_repeated_errors:]
        
        # Count occurrences of each error message
        error_counts = defaultdict(int)
        for error in recent_errors:
            # Normalize error message (remove timestamps, cycle numbers, etc.)
            normalized = self._normalize_error(error["message"])
            error_counts[normalized] += 1
        
        # Check if any error appears too frequently
        for error_msg, count in error_counts.items():
            if count >= self.config.max_repeated_errors:
                logger.warning(
                    f"Repeated error detected: '{error_msg}' appears {count} times "
                    f"in last {self.config.max_repeated_errors} cycles"
                )
                return True
        
        return False
    
    def _normalize_error(self, error_msg: str) -> str:
        """Normalize error message for comparison."""
        # Remove common variable parts
        import re
        # Remove timestamps
        error_msg = re.sub(r'\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}', '', error_msg)
        # Remove cycle numbers
        error_msg = re.sub(r'cycle\s*\d+', '', error_msg, flags=re.IGNORECASE)
        # Remove file paths (keep just filename)
        error_msg = re.sub(r'/[^\s]+/', '', error_msg)
        # Normalize whitespace
        error_msg = ' '.join(error_msg.split())
        return error_msg.lower()
    
    def _check_done_without_completion(self) -> bool:
        """Check for done signals without actual completion."""
        if len(self.cycle_history) < 2:
            return False
        
        recent_cycles = list(self.cycle_history)[-3:]  # Last 3 cycles
        
        # Check if we have done signals but no file changes
        done_count = sum(1 for c in recent_cycles if c.done_signal)
        file_change_count = sum(1 for c in recent_cycles if c.has_file_changes)
        
        if done_count >= 2 and file_change_count == 0:
            logger.warning(
                f"Done signals without completion: {done_count} done signals, "
                f"{file_change_count} file changes in last 3 cycles"
            )
            return True
        
        return False
    
    def check_stuck(self) -> Dict[str, Any]:
        """
        Check if the loop is stuck.
        Returns dict with stuck status and details.
        """
        if self.circuit_breaker_open:
            # Check if we should try to close it (after some time)
            if self.circuit_breaker_opened_at:
                time_since_open = time.time() - self.circuit_breaker_opened_at
                if time_since_open > 300:  # 5 minutes
                    logger.info("Attempting to close circuit breaker after 5 minutes")
                    self.circuit_breaker_open = False
                    self.circuit_breaker_opened_at = None
        
        # Check various stuck conditions
        no_progress_stuck = (
            self.consecutive_no_progress >= self.config.max_cycles_no_progress
        )
        repeated_errors_stuck = self._check_repeated_errors()
        done_without_completion = self._check_done_without_completion()
        
        is_stuck = no_progress_stuck or repeated_errors_stuck or done_without_completion
        
        result = {
            "is_stuck": is_stuck,
            "circuit_breaker_open": self.circuit_breaker_open,
            "reasons": [],
            "metrics": {
                "consecutive_no_progress": self.consecutive_no_progress,
                "consecutive_done_signals": self.consecutive_done_signals,
                "total_cycles": len(self.cycle_history),
                "recent_errors": len([e for e in self.error_history if time.time() - e["timestamp"] < 3600])
            }
        }
        
        if no_progress_stuck:
            result["reasons"].append(
                f"No progress for {self.consecutive_no_progress} consecutive cycles"
            )
        
        if repeated_errors_stuck:
            result["reasons"].append("Repeated errors detected")
        
        if done_without_completion:
            result["reasons"].append("Done signals without actual completion")
        
        # Open circuit breaker if stuck
        if is_stuck and not self.circuit_breaker_open:
            self.circuit_breaker_open = True
            self.circuit_breaker_opened_at = time.time()
            logger.error(
                f"Circuit breaker OPENED - Loop is stuck. Reasons: {', '.join(result['reasons'])}"
            )
        
        return result
    
    def reset(self):
        """Reset the detector state."""
        self.cycle_history.clear()
        self.error_history.clear()
        self.consecutive_no_progress = 0
        self.consecutive_done_signals = 0
        self.circuit_breaker_open = False
        self.circuit_breaker_opened_at = None
        logger.info("StuckLoopDetector reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current detector status."""
        stuck_status = self.check_stuck()
        
        return {
            "is_stuck": stuck_status["is_stuck"],
            "circuit_breaker_open": self.circuit_breaker_open,
            "consecutive_no_progress": self.consecutive_no_progress,
            "consecutive_done_signals": self.consecutive_done_signals,
            "total_cycles_tracked": len(self.cycle_history),
            "recent_errors": len([e for e in self.error_history if time.time() - e["timestamp"] < 3600]),
            "reasons": stuck_status.get("reasons", []),
            "config": {
                "max_cycles_no_progress": self.config.max_cycles_no_progress,
                "max_repeated_errors": self.config.max_repeated_errors,
                "circuit_breaker_threshold": self.config.circuit_breaker_threshold
            }
        }
