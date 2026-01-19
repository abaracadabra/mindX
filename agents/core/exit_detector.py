# agents/core/exit_detector.py
"""
Dual-condition exit detection for agent loops.
Requires both heuristic indicators AND explicit exit signal before terminating loops.
"""
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from collections import deque

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ExitCondition:
    """Represents an exit condition check."""
    heuristic_met: bool = False
    explicit_signal: bool = False
    consecutive_done_signals: int = 0
    file_changes_detected: bool = False
    tests_passed: bool = False
    timestamp: float = field(default_factory=time.time)


class ExitDetector:
    """
    Dual-condition exit detector.
    Requires both heuristic indicators AND explicit EXIT_SIGNAL before allowing exit.
    """
    
    def __init__(
        self,
        min_consecutive_done_signals: int = 2,
        require_file_changes: bool = True,
        require_tests_pass: bool = False
    ):
        self.min_consecutive_done_signals = min_consecutive_done_signals
        self.require_file_changes = require_file_changes
        self.require_tests_pass = require_tests_pass
        
        # State tracking
        self.consecutive_done_signals: int = 0
        self.heuristic_indicators: deque = deque(maxlen=10)  # Last 10 heuristic checks
        self.explicit_exit_signals: deque = deque(maxlen=10)  # Last 10 explicit signals
        self.file_changes_history: deque = deque(maxlen=10)
        self.test_results_history: deque = deque(maxlen=10)
        
        logger.info(
            f"ExitDetector initialized. "
            f"Min consecutive done signals: {min_consecutive_done_signals}, "
            f"Require file changes: {require_file_changes}, "
            f"Require tests pass: {require_tests_pass}"
        )
    
    def record_heuristic(
        self,
        file_changes: bool = False,
        tests_passed: bool = False,
        completion_indicators: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Record heuristic indicators.
        Returns True if heuristics suggest completion.
        """
        heuristic_met = True
        
        # Check file changes requirement
        if self.require_file_changes and not file_changes:
            heuristic_met = False
        
        # Check tests requirement
        if self.require_tests_pass and not tests_passed:
            heuristic_met = False
        
        # Record in history
        self.heuristic_indicators.append({
            "timestamp": time.time(),
            "heuristic_met": heuristic_met,
            "file_changes": file_changes,
            "tests_passed": tests_passed,
            "completion_indicators": completion_indicators or {}
        })
        
        self.file_changes_history.append(file_changes)
        self.test_results_history.append(tests_passed)
        
        return heuristic_met
    
    def record_explicit_signal(self, exit_signal: bool, signal_source: Optional[str] = None) -> None:
        """
        Record explicit EXIT_SIGNAL from agent/model.
        """
        self.explicit_exit_signals.append({
            "timestamp": time.time(),
            "exit_signal": exit_signal,
            "source": signal_source or "unknown"
        })
        
        if exit_signal:
            self.consecutive_done_signals += 1
            logger.info(
                f"Explicit exit signal received from {signal_source or 'unknown'}. "
                f"Consecutive done signals: {self.consecutive_done_signals}"
            )
        else:
            self.consecutive_done_signals = 0
    
    def check_exit_conditions(self) -> Dict[str, Any]:
        """
        Check if both conditions are met for exit.
        Returns dict with exit status and details.
        """
        # Check heuristic condition
        recent_heuristics = list(self.heuristic_indicators)[-3:] if len(self.heuristic_indicators) >= 3 else list(self.heuristic_indicators)
        heuristic_met = (
            len(recent_heuristics) > 0 and
            all(h.get("heuristic_met", False) for h in recent_heuristics)
        )
        
        # Check explicit signal condition
        recent_signals = list(self.explicit_exit_signals)[-self.min_consecutive_done_signals:] if len(self.explicit_exit_signals) >= self.min_consecutive_done_signals else list(self.explicit_exit_signals)
        explicit_signal_met = (
            self.consecutive_done_signals >= self.min_consecutive_done_signals and
            all(s.get("exit_signal", False) for s in recent_signals[-self.min_consecutive_done_signals:])
        )
        
        # Both conditions must be met
        should_exit = heuristic_met and explicit_signal_met
        
        result = {
            "should_exit": should_exit,
            "heuristic_met": heuristic_met,
            "explicit_signal_met": explicit_signal_met,
            "consecutive_done_signals": self.consecutive_done_signals,
            "reasons": []
        }
        
        if not heuristic_met:
            missing = []
            if self.require_file_changes and not any(self.file_changes_history):
                missing.append("file_changes")
            if self.require_tests_pass and not any(self.test_results_history):
                missing.append("tests_passed")
            if missing:
                result["reasons"].append(f"Missing heuristic indicators: {', '.join(missing)}")
        
        if not explicit_signal_met:
            result["reasons"].append(
                f"Explicit exit signal not met: need {self.min_consecutive_done_signals} consecutive, "
                f"have {self.consecutive_done_signals}"
            )
        
        if should_exit:
            logger.info(
                f"Exit conditions met! Heuristic: {heuristic_met}, "
                f"Explicit signal: {explicit_signal_met}, "
                f"Consecutive done: {self.consecutive_done_signals}"
            )
        
        return result
    
    def parse_exit_signal_from_response(self, response: Any) -> bool:
        """
        Parse EXIT_SIGNAL from agent/model response.
        Looks for EXIT_SIGNAL: true in various formats.
        """
        if isinstance(response, dict):
            # Check for explicit EXIT_SIGNAL field
            if response.get("EXIT_SIGNAL") is True or response.get("exit_signal") is True:
                return True
            
            # Check in nested structures
            if "status" in response and isinstance(response["status"], dict):
                if response["status"].get("EXIT_SIGNAL") is True:
                    return True
            
            # Check in metadata
            if "metadata" in response and isinstance(response["metadata"], dict):
                if response["metadata"].get("EXIT_SIGNAL") is True:
                    return True
        
        elif isinstance(response, str):
            # Check for EXIT_SIGNAL in string response
            import json
            try:
                parsed = json.loads(response)
                if isinstance(parsed, dict):
                    return self.parse_exit_signal_from_response(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
            
            # Check for explicit text patterns
            if "EXIT_SIGNAL: true" in response.upper() or '"EXIT_SIGNAL": true' in response:
                return True
        
        return False
    
    def reset(self):
        """Reset the exit detector state."""
        self.consecutive_done_signals = 0
        self.heuristic_indicators.clear()
        self.explicit_exit_signals.clear()
        self.file_changes_history.clear()
        self.test_results_history.clear()
        logger.info("ExitDetector reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current exit detector status."""
        exit_check = self.check_exit_conditions()
        
        return {
            "should_exit": exit_check["should_exit"],
            "heuristic_met": exit_check["heuristic_met"],
            "explicit_signal_met": exit_check["explicit_signal_met"],
            "consecutive_done_signals": self.consecutive_done_signals,
            "recent_file_changes": list(self.file_changes_history)[-5:],
            "recent_test_results": list(self.test_results_history)[-5:],
            "reasons": exit_check.get("reasons", []),
            "config": {
                "min_consecutive_done_signals": self.min_consecutive_done_signals,
                "require_file_changes": self.require_file_changes,
                "require_tests_pass": self.require_tests_pass
            }
        }
