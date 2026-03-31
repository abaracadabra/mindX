"""
Advanced Rate Limiting System for mindX Production
Implements sliding window, token bucket, and adaptive rate limiting
"""

import time
import math
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque, defaultdict
from enum import Enum
import json
from pathlib import Path

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class RateLimitAlgorithm(Enum):
    """Rate limiting algorithm types"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    ADAPTIVE = "adaptive"

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting rules"""
    max_requests: int
    window_seconds: int
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    burst_allowance: Optional[int] = None  # For token bucket
    adaptive_factor: float = 1.0  # For adaptive limiting
    whitelist: List[str] = field(default_factory=list)
    priority_multiplier: float = 1.0

@dataclass
class ClientInfo:
    """Information about a client for rate limiting"""
    client_id: str
    ip_address: str
    user_agent: Optional[str] = None
    session_token: Optional[str] = None
    priority_level: int = 0  # 0=normal, 1=premium, 2=admin
    reputation_score: float = 1.0  # 0.1=bad, 1.0=normal, 2.0=good
    first_seen: float = field(default_factory=time.time)
    last_request: float = field(default_factory=time.time)

class SlidingWindowCounter:
    """Sliding window rate limiter implementation"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.requests: deque = deque()

    def is_allowed(self, current_time: float) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under sliding window"""
        # Remove expired requests
        window_start = current_time - self.config.window_seconds
        while self.requests and self.requests[0] < window_start:
            self.requests.popleft()

        # Check if we can accept another request
        allowed = len(self.requests) < self.config.max_requests

        metadata = {
            "current_count": len(self.requests),
            "max_requests": self.config.max_requests,
            "window_seconds": self.config.window_seconds,
            "reset_time": window_start + self.config.window_seconds
        }

        if allowed:
            self.requests.append(current_time)

        return allowed, metadata

class TokenBucket:
    """Token bucket rate limiter implementation"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.capacity = config.burst_allowance or config.max_requests
        self.tokens = float(self.capacity)
        self.refill_rate = config.max_requests / config.window_seconds
        self.last_refill = time.time()

    def is_allowed(self, current_time: float, tokens_needed: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under token bucket"""
        # Refill tokens based on elapsed time
        elapsed = current_time - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = current_time

        # Check if we have enough tokens
        allowed = self.tokens >= tokens_needed

        metadata = {
            "available_tokens": int(self.tokens),
            "capacity": self.capacity,
            "refill_rate": self.refill_rate,
            "tokens_needed": tokens_needed
        }

        if allowed:
            self.tokens -= tokens_needed

        return allowed, metadata

class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on system load and client behavior"""

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.base_limiter = SlidingWindowCounter(config)
        self.system_load_factor = 1.0
        self.error_rate_window = deque(maxlen=100)
        self.success_rate_window = deque(maxlen=100)

    def update_system_load(self, cpu_percent: float, memory_percent: float):
        """Update system load factor for adaptive limiting"""
        # Higher system load = more restrictive rate limiting
        avg_system_load = (cpu_percent + memory_percent) / 200.0  # Normalize to 0-1

        if avg_system_load > 0.8:
            self.system_load_factor = 0.5  # Very restrictive
        elif avg_system_load > 0.6:
            self.system_load_factor = 0.75  # Moderately restrictive
        elif avg_system_load > 0.4:
            self.system_load_factor = 0.9  # Slightly restrictive
        else:
            self.system_load_factor = 1.0  # Normal

    def record_request_result(self, success: bool):
        """Record whether request was successful for adaptive adjustment"""
        self.error_rate_window.append(not success)
        self.success_rate_window.append(success)

    def get_adaptive_limit(self) -> int:
        """Calculate adaptive rate limit based on current conditions"""
        base_limit = self.config.max_requests

        # Adjust for system load
        adjusted_limit = base_limit * self.system_load_factor

        # Adjust for error rate
        if len(self.error_rate_window) > 10:
            error_rate = sum(self.error_rate_window) / len(self.error_rate_window)
            if error_rate > 0.1:  # More than 10% errors
                adjusted_limit *= (1.0 - error_rate)

        return max(1, int(adjusted_limit))

    def is_allowed(self, current_time: float, client_info: ClientInfo) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed with adaptive logic"""
        # Adjust limit based on client reputation and priority
        adaptive_limit = self.get_adaptive_limit()
        adjusted_limit = adaptive_limit * client_info.reputation_score

        # Premium clients get higher limits
        if client_info.priority_level == 1:  # Premium
            adjusted_limit *= 2.0
        elif client_info.priority_level == 2:  # Admin
            adjusted_limit *= 5.0

        # Temporarily adjust the base limiter's config
        original_max = self.base_limiter.config.max_requests
        self.base_limiter.config.max_requests = int(adjusted_limit)

        allowed, metadata = self.base_limiter.is_allowed(current_time)

        # Restore original config
        self.base_limiter.config.max_requests = original_max

        # Add adaptive metadata
        metadata.update({
            "adaptive_limit": int(adjusted_limit),
            "system_load_factor": self.system_load_factor,
            "client_reputation": client_info.reputation_score,
            "priority_level": client_info.priority_level
        })

        return allowed, metadata

class AdvancedRateLimiter:
    """Main rate limiting coordinator with multiple algorithms and client management"""

    def __init__(self, config: Config):
        self.config = config
        self.rate_configs: Dict[str, RateLimitConfig] = self._load_rate_configs()
        self.client_limiters: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.client_info: Dict[str, ClientInfo] = {}
        self.global_stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "adaptive_adjustments": 0
        }

        # Background cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
        self._stats_task: Optional[asyncio.Task] = None

    def _load_rate_configs(self) -> Dict[str, RateLimitConfig]:
        """Load rate limiting configurations"""
        default_configs = {
            "default": RateLimitConfig(
                max_requests=100,
                window_seconds=60,
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW
            ),
            "api_heavy": RateLimitConfig(
                max_requests=50,
                window_seconds=60,
                algorithm=RateLimitAlgorithm.TOKEN_BUCKET,
                burst_allowance=75
            ),
            "admin": RateLimitConfig(
                max_requests=500,
                window_seconds=60,
                algorithm=RateLimitAlgorithm.ADAPTIVE,
                adaptive_factor=2.0
            ),
            "public_read": RateLimitConfig(
                max_requests=200,
                window_seconds=60,
                algorithm=RateLimitAlgorithm.SLIDING_WINDOW
            )
        }

        # Load custom configs if available
        config_file = PROJECT_ROOT / "data" / "config" / "rate_limits.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    custom_configs = json.load(f)

                for name, config_data in custom_configs.items():
                    default_configs[name] = RateLimitConfig(
                        max_requests=config_data["max_requests"],
                        window_seconds=config_data["window_seconds"],
                        algorithm=RateLimitAlgorithm(config_data.get("algorithm", "sliding_window")),
                        burst_allowance=config_data.get("burst_allowance"),
                        adaptive_factor=config_data.get("adaptive_factor", 1.0),
                        whitelist=config_data.get("whitelist", []),
                        priority_multiplier=config_data.get("priority_multiplier", 1.0)
                    )

                logger.info(f"Loaded {len(custom_configs)} custom rate limit configurations")

            except Exception as e:
                logger.error(f"Failed to load rate limit configs: {e}")

        return default_configs

    def _get_client_key(self, client_info: ClientInfo, endpoint: str) -> str:
        """Generate unique key for client-endpoint combination"""
        return f"{client_info.client_id}:{endpoint}"

    def _create_limiter(self, config: RateLimitConfig, client_info: ClientInfo) -> Any:
        """Create appropriate rate limiter instance"""
        if config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            return SlidingWindowCounter(config)
        elif config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            return TokenBucket(config)
        elif config.algorithm == RateLimitAlgorithm.ADAPTIVE:
            return AdaptiveRateLimiter(config)
        else:
            # Default to sliding window
            return SlidingWindowCounter(config)

    def update_client_info(self, client_info: ClientInfo):
        """Update client information"""
        self.client_info[client_info.client_id] = client_info

    def update_client_reputation(self, client_id: str, success: bool, response_time: float):
        """Update client reputation based on request behavior"""
        if client_id not in self.client_info:
            return

        client = self.client_info[client_id]
        client.last_request = time.time()

        # Update reputation based on success rate and response time
        if success:
            if response_time < 1.0:  # Fast response
                client.reputation_score = min(2.0, client.reputation_score + 0.01)
            else:
                client.reputation_score = min(2.0, client.reputation_score + 0.005)
        else:
            # Penalize failures
            client.reputation_score = max(0.1, client.reputation_score - 0.02)

        # Record in adaptive limiters
        for endpoint_limiters in self.client_limiters.values():
            for limiter in endpoint_limiters.values():
                if isinstance(limiter, AdaptiveRateLimiter):
                    limiter.record_request_result(success)

    async def is_allowed(
        self,
        client_info: ClientInfo,
        endpoint: str,
        rule_name: str = "default"
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed"""
        current_time = time.time()
        self.global_stats["total_requests"] += 1

        # Check whitelist
        config = self.rate_configs.get(rule_name, self.rate_configs["default"])
        if client_info.ip_address in config.whitelist:
            return True, {"status": "whitelisted", "ip": client_info.ip_address}

        # Get or create limiter for this client-endpoint combination
        client_key = self._get_client_key(client_info, endpoint)

        if rule_name not in self.client_limiters[client_key]:
            self.client_limiters[client_key][rule_name] = self._create_limiter(config, client_info)

        limiter = self.client_limiters[client_key][rule_name]

        # Update client info
        self.update_client_info(client_info)

        # Check rate limit
        if isinstance(limiter, AdaptiveRateLimiter):
            allowed, metadata = limiter.is_allowed(current_time, client_info)
        else:
            allowed, metadata = limiter.is_allowed(current_time)

        if not allowed:
            self.global_stats["blocked_requests"] += 1

        # Add general metadata
        metadata.update({
            "client_id": client_info.client_id,
            "endpoint": endpoint,
            "rule_name": rule_name,
            "algorithm": config.algorithm.value,
            "timestamp": current_time
        })

        return allowed, metadata

    def get_client_status(self, client_id: str) -> Dict[str, Any]:
        """Get current status for a client"""
        if client_id not in self.client_info:
            return {"error": "Client not found"}

        client = self.client_info[client_id]
        status = {
            "client_id": client_id,
            "ip_address": client.ip_address,
            "priority_level": client.priority_level,
            "reputation_score": client.reputation_score,
            "first_seen": client.first_seen,
            "last_request": client.last_request,
            "limiters": {}
        }

        # Get limiter status for each endpoint
        for client_endpoint_key, endpoint_limiters in self.client_limiters.items():
            if client_endpoint_key.startswith(f"{client_id}:"):
                endpoint = client_endpoint_key.split(":", 1)[1]
                status["limiters"][endpoint] = {}

                for rule_name, limiter in endpoint_limiters.items():
                    if isinstance(limiter, SlidingWindowCounter):
                        status["limiters"][endpoint][rule_name] = {
                            "type": "sliding_window",
                            "current_count": len(limiter.requests)
                        }
                    elif isinstance(limiter, TokenBucket):
                        status["limiters"][endpoint][rule_name] = {
                            "type": "token_bucket",
                            "available_tokens": int(limiter.tokens),
                            "capacity": limiter.capacity
                        }

        return status

    def get_global_stats(self) -> Dict[str, Any]:
        """Get global rate limiting statistics"""
        return {
            **self.global_stats,
            "active_clients": len(self.client_info),
            "active_limiters": sum(len(limiters) for limiters in self.client_limiters.values()),
            "block_rate": (
                self.global_stats["blocked_requests"] / self.global_stats["total_requests"]
                if self.global_stats["total_requests"] > 0 else 0
            )
        }

    async def start_background_tasks(self):
        """Start background cleanup and statistics tasks"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Rate limiter cleanup task started")

        if self._stats_task is None or self._stats_task.done():
            self._stats_task = asyncio.create_task(self._stats_loop())
            logger.info("Rate limiter stats task started")

    async def stop_background_tasks(self):
        """Stop background tasks"""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._stats_task and not self._stats_task.done():
            self._stats_task.cancel()
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass

        logger.info("Rate limiter background tasks stopped")

    async def _cleanup_loop(self):
        """Background cleanup of expired entries"""
        cleanup_interval = self.config.get("rate_limiter.cleanup_interval", 300)  # 5 minutes

        while True:
            try:
                current_time = time.time()

                # Remove inactive clients (inactive for > 1 hour)
                inactive_clients = []
                for client_id, client in self.client_info.items():
                    if current_time - client.last_request > 3600:
                        inactive_clients.append(client_id)

                for client_id in inactive_clients:
                    del self.client_info[client_id]

                    # Also remove their limiters
                    keys_to_remove = [
                        key for key in self.client_limiters.keys()
                        if key.startswith(f"{client_id}:")
                    ]
                    for key in keys_to_remove:
                        del self.client_limiters[key]

                if inactive_clients:
                    logger.info(f"Cleaned up {len(inactive_clients)} inactive clients")

                await asyncio.sleep(cleanup_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rate limiter cleanup error: {e}")
                await asyncio.sleep(cleanup_interval)

    async def _stats_loop(self):
        """Background statistics collection"""
        stats_interval = self.config.get("rate_limiter.stats_interval", 60)  # 1 minute

        while True:
            try:
                stats = self.get_global_stats()
                logger.info(f"Rate limiter stats: {stats['active_clients']} clients, "
                          f"{stats['total_requests']} requests, "
                          f"{stats['block_rate']:.2%} block rate")

                await asyncio.sleep(stats_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Rate limiter stats error: {e}")
                await asyncio.sleep(stats_interval)

# Global instance
_rate_limiter_instance = None

def get_advanced_rate_limiter(config: Config = None) -> AdvancedRateLimiter:
    """Get singleton advanced rate limiter instance"""
    global _rate_limiter_instance
    if _rate_limiter_instance is None:
        if config is None:
            config = Config()
        _rate_limiter_instance = AdvancedRateLimiter(config)
    return _rate_limiter_instance