# mindx/llm/rate_limiter.py
import asyncio
import time
import random
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass, asdict
from collections import deque

from utils.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class RateLimiterMetrics:
    """Comprehensive rate limiter metrics."""
    total_requests: int = 0
    successful_requests: int = 0
    blocked_requests: int = 0
    failed_requests: int = 0
    total_wait_time_ms: float = 0.0
    wait_times_ms: Optional[deque] = None
    current_tokens: float = 0.0
    max_tokens: float = 0.0
    requests_per_minute: int = 0
    retry_counts: Optional[Dict[int, int]] = None  # attempt_number -> count
    last_request_time: float = 0.0
    first_request_time: float = 0.0
    
    def __post_init__(self):
        if self.wait_times_ms is None:
            self.wait_times_ms = deque(maxlen=100)
        if self.retry_counts is None:
            self.retry_counts = {}

class RateLimiter:
    """
    A token-bucket style rate limiter with exponential backoff for retries.
    Enhanced with comprehensive monitoring and metrics collection.
    """
    def __init__(
        self,
        requests_per_minute: int,
        max_retries: int = 5,
        initial_backoff_s: float = 1.0,
        status_callback: Optional[Callable[[int, int, float], None]] = None,
        monitoring_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        self.requests_per_minute = requests_per_minute
        self.token_fill_rate = requests_per_minute / 60.0
        self.max_tokens = float(requests_per_minute)
        self.current_tokens = self.max_tokens
        self.last_fill_time = time.monotonic()
        self.lock = asyncio.Lock()

        self.max_retries = max_retries
        self.initial_backoff_s = initial_backoff_s
        self.status_callback = status_callback
        self.monitoring_callback = monitoring_callback
        
        # Enhanced metrics
        self.metrics = RateLimiterMetrics(
            max_tokens=self.max_tokens,
            requests_per_minute=requests_per_minute,
            current_tokens=self.current_tokens
        )
        
        logger.info(f"RateLimiter initialized. Rate: {requests_per_minute}/min, Max Retries: {max_retries}.")

    def get_metrics(self) -> Dict[str, Any]:
        """Get current rate limiter metrics."""
        self.metrics.current_tokens = self.current_tokens
        metrics_dict = asdict(self.metrics)
        
        # Calculate derived metrics
        if self.metrics.total_requests > 0:
            metrics_dict["success_rate"] = self.metrics.successful_requests / self.metrics.total_requests
            metrics_dict["block_rate"] = self.metrics.blocked_requests / self.metrics.total_requests
            metrics_dict["avg_wait_time_ms"] = self.metrics.total_wait_time_ms / self.metrics.total_requests
        else:
            metrics_dict["success_rate"] = 0.0
            metrics_dict["block_rate"] = 0.0
            metrics_dict["avg_wait_time_ms"] = 0.0
        
        # Convert deque to list for serialization
        metrics_dict["wait_times_ms"] = list(self.metrics.wait_times_ms)
        
        # Calculate percentiles if we have wait times
        if self.metrics.wait_times_ms:
            wait_times = sorted(list(self.metrics.wait_times_ms))
            n = len(wait_times)
            metrics_dict["wait_time_p50"] = wait_times[int(n * 0.5)] if n > 0 else 0
            metrics_dict["wait_time_p90"] = wait_times[int(n * 0.9)] if n > 0 else 0
            metrics_dict["wait_time_p99"] = wait_times[int(n * 0.99)] if n > 0 else 0
        else:
            metrics_dict["wait_time_p50"] = 0
            metrics_dict["wait_time_p90"] = 0
            metrics_dict["wait_time_p99"] = 0
        
        # Token utilization
        metrics_dict["token_utilization"] = 1.0 - (self.current_tokens / self.max_tokens)
        
        return metrics_dict

    async def _refill_tokens(self):
        """Refills tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_fill_time
        tokens_to_add = elapsed * self.token_fill_rate
        self.current_tokens = min(self.max_tokens, self.current_tokens + tokens_to_add)
        self.last_fill_time = now

    async def _log_metrics(self, wait_time_ms: float = 0.0, success: bool = True, retries: int = 0):
        """Log metrics to monitoring system if callback is provided."""
        if self.monitoring_callback:
            try:
                metrics = self.get_metrics()
                metrics.update({
                    "last_wait_time_ms": wait_time_ms,
                    "last_success": success,
                    "last_retries": retries,
                    "timestamp": time.time()
                })
                self.monitoring_callback(metrics)
            except Exception as e:
                logger.error(f"Failed to log rate limiter metrics: {e}")

    async def wait(self) -> bool:
        """
        Waits until a token is available. Returns True if successful, False if retries exhausted.
        Enhanced with comprehensive metrics collection.
        """
        start_time = time.monotonic()
        now = time.time()
        
        # Update request metrics
        self.metrics.total_requests += 1
        if self.metrics.first_request_time == 0:
            self.metrics.first_request_time = now
        self.metrics.last_request_time = now
        
        total_wait_time = 0.0
        
        for attempt in range(self.max_retries):
            async with self.lock:
                await self._refill_tokens()
                if self.current_tokens >= 1:
                    self.current_tokens -= 1
                    
                    # Success metrics
                    self.metrics.successful_requests += 1
                    elapsed_ms = (time.monotonic() - start_time) * 1000
                    self.metrics.total_wait_time_ms += elapsed_ms
                    self.metrics.wait_times_ms.append(elapsed_ms)
                    
                    # Update retry count statistics
                    if attempt in self.metrics.retry_counts:
                        self.metrics.retry_counts[attempt] += 1
                    else:
                        self.metrics.retry_counts[attempt] = 1
                    
                    # Clear status and log metrics
                    if self.status_callback: 
                        self.status_callback(0, self.max_retries, 0)
                    
                    await self._log_metrics(elapsed_ms, True, attempt)
                    return True
            
            # Calculate backoff
            backoff_duration = self.initial_backoff_s * (2 ** attempt)
            jitter = backoff_duration * random.uniform(-0.1, 0.1)
            wait_time = backoff_duration + jitter
            total_wait_time += wait_time
            
            # Update blocked request metrics
            self.metrics.blocked_requests += 1
            
            # Status callback
            if self.status_callback:
                self.status_callback(attempt + 1, self.max_retries, wait_time)
            
            await asyncio.sleep(wait_time)

        # Failed after all retries
        self.metrics.failed_requests += 1
        elapsed_ms = (time.monotonic() - start_time) * 1000
        self.metrics.total_wait_time_ms += elapsed_ms
        self.metrics.wait_times_ms.append(elapsed_ms)
        
        if self.status_callback:
            self.status_callback(self.max_retries + 1, self.max_retries, 0)
        
        await self._log_metrics(elapsed_ms, False, self.max_retries)
        return False

    def get_status_summary(self) -> Dict[str, Any]:
        """Get a human-readable status summary."""
        metrics = self.get_metrics()
        
        return {
            "rate_limit": f"{self.requests_per_minute}/min",
            "current_tokens": f"{self.current_tokens:.1f}/{self.max_tokens}",
            "utilization": f"{metrics['token_utilization']:.1%}",
            "total_requests": self.metrics.total_requests,
            "success_rate": f"{metrics['success_rate']:.1%}",
            "avg_wait_time": f"{metrics['avg_wait_time_ms']:.1f}ms",
            "status": "healthy" if metrics['success_rate'] > 0.9 else "degraded" if metrics['success_rate'] > 0.5 else "critical"
        }
