# mindx/llm/rate_limiter.py
import asyncio
import time
import random
import json
from typing import Callable, Optional, Dict, Any
from dataclasses import dataclass, asdict
from collections import deque
from pathlib import Path

from utils.logging_config import get_logger
from utils.config import PROJECT_ROOT

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
        monitoring_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        # Free-tier safety: never touch the published cap. Default 0 preserves
        # the original behavior; free-tier providers should pass safety_margin=1.
        safety_margin: int = 0,
        tpm_limit: Optional[int] = None,
        slowdown_threshold: float = 0.80,
    ):
        # Apply the safety margin once — `requests_per_minute` is what the rest
        # of the limiter sees (and what shows in metrics).
        self._published_rpm = requests_per_minute
        self._safety_margin = max(0, int(safety_margin))
        effective_rpm = max(1, requests_per_minute - self._safety_margin)
        self.requests_per_minute = effective_rpm
        self.token_fill_rate = effective_rpm / 60.0
        self.max_tokens = float(effective_rpm)
        self.current_tokens = self.max_tokens
        self.last_fill_time = time.monotonic()
        self.lock = asyncio.Lock()

        # Optional TPM (tokens-per-minute) bucket. Off by default for backwards
        # compatibility — free-tier providers pass tpm_limit explicitly.
        self.tpm_limit = tpm_limit
        if tpm_limit is not None:
            tpm_effective = max(1, int(tpm_limit * 0.99))  # 1% TPM headroom
            self.tpm_max = float(tpm_effective)
            self.tpm_current = self.tpm_max
            self.tpm_fill_rate = tpm_effective / 60.0
            self.tpm_last_fill = time.monotonic()
        else:
            self.tpm_max = 0.0
            self.tpm_current = 0.0
            self.tpm_fill_rate = 0.0
            self.tpm_last_fill = 0.0

        self.slowdown_threshold = max(0.0, min(0.99, slowdown_threshold))

        self.max_retries = max_retries
        self.initial_backoff_s = initial_backoff_s
        self.status_callback = status_callback
        self.monitoring_callback = monitoring_callback

        # Enhanced metrics
        self.metrics = RateLimiterMetrics(
            max_tokens=self.max_tokens,
            requests_per_minute=effective_rpm,
            current_tokens=self.current_tokens
        )

        if self._safety_margin or self.tpm_limit:
            logger.info(
                f"RateLimiter initialized. Published: {self._published_rpm}/min, "
                f"effective: {effective_rpm}/min (safety_margin={self._safety_margin}), "
                f"TPM: {self.tpm_limit or 'off'}, slowdown@{self.slowdown_threshold:.0%}."
            )
        else:
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

    async def _refill_tpm(self):
        if self.tpm_limit is None:
            return
        now = time.monotonic()
        elapsed = now - self.tpm_last_fill
        self.tpm_current = min(self.tpm_max, self.tpm_current + elapsed * self.tpm_fill_rate)
        self.tpm_last_fill = now

    def headroom_pct(self) -> float:
        """Min headroom across RPM and (if configured) TPM buckets, as a 0..1 fraction."""
        rpm_h = self.current_tokens / self.max_tokens if self.max_tokens else 0.0
        if self.tpm_limit is None:
            return rpm_h
        tpm_h = self.tpm_current / self.tpm_max if self.tpm_max else 0.0
        return min(rpm_h, tpm_h)

    async def reserve(self, estimated_tokens: int) -> bool:
        """
        Atomically debit one request from RPM and `estimated_tokens` from TPM.
        Returns True when the reservation succeeds, False after retries exhausted.
        At >=slowdown_threshold utilization on either axis, sleeps proactively
        before debiting — we want to slow down well before the published cap.
        """
        if estimated_tokens < 0:
            estimated_tokens = 0
        start_time = time.monotonic()
        now = time.time()
        self.metrics.total_requests += 1
        if self.metrics.first_request_time == 0:
            self.metrics.first_request_time = now
        self.metrics.last_request_time = now

        for attempt in range(self.max_retries):
            async with self.lock:
                await self._refill_tokens()
                await self._refill_tpm()

                rpm_ok = self.current_tokens >= 1
                tpm_ok = (
                    self.tpm_limit is None
                    or self.tpm_current >= max(1, estimated_tokens)
                )
                if rpm_ok and tpm_ok:
                    # Proactive slowdown: sleep briefly when utilization is high
                    # so we never crowd the published cap. Computed under lock
                    # to keep the headroom check honest.
                    rpm_util = 1.0 - (self.current_tokens / self.max_tokens)
                    tpm_util = (
                        1.0 - (self.tpm_current / self.tpm_max)
                        if self.tpm_limit is not None and self.tpm_max
                        else 0.0
                    )
                    util = max(rpm_util, tpm_util)
                    proactive_sleep_s = 0.0
                    if util >= self.slowdown_threshold:
                        # Linear ramp from 0 at threshold to ~one fill-period at 100%.
                        over = (util - self.slowdown_threshold) / max(0.01, 1.0 - self.slowdown_threshold)
                        proactive_sleep_s = min(2.0, over * (60.0 / max(1.0, self.token_fill_rate * 60.0)))

                    self.current_tokens -= 1
                    if self.tpm_limit is not None:
                        self.tpm_current -= max(0, estimated_tokens)

            # Success path (we've reserved; sleep outside the lock if needed).
            if rpm_ok and tpm_ok:
                if proactive_sleep_s > 0:
                    await asyncio.sleep(proactive_sleep_s)
                self.metrics.successful_requests += 1
                elapsed_ms = (time.monotonic() - start_time) * 1000
                self.metrics.total_wait_time_ms += elapsed_ms
                self.metrics.wait_times_ms.append(elapsed_ms)
                self.metrics.retry_counts[attempt] = self.metrics.retry_counts.get(attempt, 0) + 1
                if self.status_callback:
                    self.status_callback(0, self.max_retries, 0)
                await self._log_metrics(elapsed_ms, True, attempt)
                return True

            # Backoff and retry.
            backoff_duration = self.initial_backoff_s * (2 ** attempt)
            jitter = backoff_duration * random.uniform(-0.1, 0.1)
            wait_time = backoff_duration + jitter
            self.metrics.blocked_requests += 1
            if self.status_callback:
                self.status_callback(attempt + 1, self.max_retries, wait_time)
            await asyncio.sleep(wait_time)

        self.metrics.failed_requests += 1
        elapsed_ms = (time.monotonic() - start_time) * 1000
        self.metrics.total_wait_time_ms += elapsed_ms
        self.metrics.wait_times_ms.append(elapsed_ms)
        await self._log_metrics(elapsed_ms, False, self.max_retries)
        return False

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


class HourlyRateLimiter:
    """
    Hourly rate limiter tracking API calls per hour.
    Provides dual-layer protection alongside per-minute rate limiting.
    """
    def __init__(
        self,
        requests_per_hour: int = 100,
        storage_path: Optional[Path] = None
    ):
        self.requests_per_hour = requests_per_hour
        self.storage_path = storage_path or (PROJECT_ROOT / "data" / "monitoring" / "hourly_rate_limits.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = asyncio.Lock()
        
        # Load existing call history
        self.call_history: list = []
        self._load_history()
        
        logger.info(f"HourlyRateLimiter initialized. Rate: {requests_per_hour}/hour")
    
    def _load_history(self):
        """Load call history from persistent storage."""
        try:
            if self.storage_path.exists():
                with self.storage_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.call_history = data.get("call_history", [])
                    # Clean old entries (older than 1 hour)
                    self._clean_old_entries()
        except Exception as e:
            logger.warning(f"Failed to load hourly rate limit history: {e}. Starting fresh.")
            self.call_history = []
    
    def _save_history(self):
        """Save call history to persistent storage."""
        try:
            with self.storage_path.open("w", encoding="utf-8") as f:
                json.dump({
                    "call_history": self.call_history,
                    "last_updated": time.time()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save hourly rate limit history: {e}")
    
    def _clean_old_entries(self):
        """Remove call timestamps older than 1 hour."""
        current_time = time.time()
        hour_ago = current_time - 3600
        self.call_history = [ts for ts in self.call_history if ts > hour_ago]
    
    async def check_and_record(self) -> bool:
        """
        Check if we can make a call (within hourly limit) and record it.
        Returns True if allowed, False if limit exceeded.
        """
        async with self.lock:
            current_time = time.time()
            hour_ago = current_time - 3600
            
            # Clean old entries
            self._clean_old_entries()
            
            # Check if we're at the limit
            if len(self.call_history) >= self.requests_per_hour:
                logger.warning(
                    f"Hourly rate limit exceeded: {len(self.call_history)}/{self.requests_per_hour} calls/hour. "
                    f"Oldest call: {time.time() - min(self.call_history):.1f}s ago"
                )
                return False
            
            # Record this call
            self.call_history.append(current_time)
            self._save_history()
            
            return True
    
    def get_remaining_calls(self) -> int:
        """Get number of remaining calls in the current hour."""
        self._clean_old_entries()
        return max(0, self.requests_per_hour - len(self.call_history))
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get hourly rate limiter metrics."""
        self._clean_old_entries()
        current_time = time.time()
        hour_ago = current_time - 3600
        
        # Calculate time until oldest call expires
        oldest_call = min(self.call_history) if self.call_history else current_time
        seconds_until_reset = max(0, 3600 - (current_time - oldest_call))
        
        return {
            "requests_per_hour": self.requests_per_hour,
            "calls_this_hour": len(self.call_history),
            "remaining_calls": self.get_remaining_calls(),
            "utilization": len(self.call_history) / self.requests_per_hour if self.requests_per_hour > 0 else 0.0,
            "seconds_until_reset": seconds_until_reset,
            "at_limit": len(self.call_history) >= self.requests_per_hour
        }
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get a human-readable status summary."""
        metrics = self.get_metrics()
        
        return {
            "rate_limit": f"{self.requests_per_hour}/hour",
            "calls_this_hour": metrics["calls_this_hour"],
            "remaining": metrics["remaining_calls"],
            "utilization": f"{metrics['utilization']:.1%}",
            "status": "at_limit" if metrics["at_limit"] else "available",
            "reset_in": f"{metrics['seconds_until_reset']:.0f}s" if metrics["seconds_until_reset"] > 0 else "now"
        }


class DualLayerRateLimiter:
    """
    Combines per-minute and per-hour rate limiting for dual-layer protection.
    Wraps both RateLimiter and HourlyRateLimiter.
    """
    def __init__(
        self,
        requests_per_minute: int,
        requests_per_hour: int = 100,
        max_retries: int = 5,
        initial_backoff_s: float = 1.0,
        status_callback: Optional[Callable[[int, int, float], None]] = None,
        monitoring_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        # Free-tier safety knobs forwarded to the inner per-minute limiter.
        # Defaults preserve existing behavior; pass safety_margin=1 for free
        # providers so we never touch the published cap (cost = ban).
        safety_margin: int = 0,
        tpm_limit: Optional[int] = None,
        slowdown_threshold: float = 0.80,
    ):
        self.minute_limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            max_retries=max_retries,
            initial_backoff_s=initial_backoff_s,
            status_callback=status_callback,
            monitoring_callback=monitoring_callback,
            safety_margin=safety_margin,
            tpm_limit=tpm_limit,
            slowdown_threshold=slowdown_threshold,
        )
        self.hourly_limiter = HourlyRateLimiter(requests_per_hour=requests_per_hour)

        logger.info(
            f"DualLayerRateLimiter initialized. "
            f"Rate: {requests_per_minute}/min, {requests_per_hour}/hour"
            + (f", TPM={tpm_limit}, safety_margin={safety_margin}" if (tpm_limit or safety_margin) else "")
        )

    async def reserve(self, estimated_tokens: int = 0) -> bool:
        """Token-aware reservation. Falls back to wait() when TPM is off."""
        if not await self.hourly_limiter.check_and_record():
            logger.warning("Hourly rate limit exceeded. Request blocked.")
            return False
        if self.minute_limiter.tpm_limit is None and estimated_tokens == 0:
            return await self.minute_limiter.wait()
        return await self.minute_limiter.reserve(estimated_tokens)

    def headroom_pct(self) -> float:
        return self.minute_limiter.headroom_pct()
    
    async def wait(self) -> bool:
        """
        Wait until both minute and hourly limits allow a request.
        Returns True if successful, False if retries exhausted.
        """
        # First check hourly limit (non-blocking check)
        if not await self.hourly_limiter.check_and_record():
            logger.warning("Hourly rate limit exceeded. Request blocked.")
            return False
        
        # Then wait for minute limit (may block with retries)
        return await self.minute_limiter.wait()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get combined metrics from both limiters."""
        minute_metrics = self.minute_limiter.get_metrics()
        hourly_metrics = self.hourly_limiter.get_metrics()
        
        return {
            "minute_limiter": minute_metrics,
            "hourly_limiter": hourly_metrics,
            "combined_status": {
                "minute_available": minute_metrics.get("success_rate", 0) > 0.5,
                "hourly_available": not hourly_metrics["at_limit"],
                "overall_available": (
                    minute_metrics.get("success_rate", 0) > 0.5 and 
                    not hourly_metrics["at_limit"]
                )
            }
        }
    
    def get_status_summary(self) -> Dict[str, Any]:
        """Get combined status summary."""
        minute_status = self.minute_limiter.get_status_summary()
        hourly_status = self.hourly_limiter.get_status_summary()
        
        return {
            "minute_limiter": minute_status,
            "hourly_limiter": hourly_status,
            "overall_status": "healthy" if (
                minute_status.get("status") == "healthy" and 
                hourly_status.get("status") == "available"
            ) else "degraded"
        }
