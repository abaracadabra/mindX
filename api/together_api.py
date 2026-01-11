"""
Together AI API Integration for mindX

This module provides comprehensive integration with Together AI API,
including rate limit management, monitoring, and optimization.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    from together import Together
    TOGETHER_AVAILABLE = True
except ImportError:
    TOGETHER_AVAILABLE = False
    logger.warning("Together AI library not installed. Install with: pip install together")

import aiohttp

from utils.logging_config import get_logger
from utils.config import Config
from llm.rate_limiter import RateLimiter

logger = get_logger(__name__)


@dataclass
class TogetherRateLimits:
    """Together AI API rate limits"""
    requests_per_minute: int = 60
    requests_per_day: int = 10000
    tokens_per_minute: int = 1000000
    tokens_per_day: int = 100000000


@dataclass
class TogetherAPIMetrics:
    """Metrics for Together AI API usage"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    last_request_time: Optional[datetime] = None
    average_latency_ms: float = 0.0


class TogetherAPI:
    """Together AI API client with rate limiting and monitoring"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limits: Optional[TogetherRateLimits] = None,
        config: Optional[Config] = None
    ):
        self.config = config or Config()
        self.api_key = api_key or os.getenv("TOGETHER_API_KEY") or self.config.get("llm.together.api_key")
        
        if not TOGETHER_AVAILABLE:
            logger.error("Together AI library not available")
            self.client = None
        elif self.api_key:
            self.client = Together(api_key=self.api_key)
        else:
            logger.warning("Together AI API key not provided")
            self.client = None
        
        self.rate_limits = rate_limits or TogetherRateLimits()
        self.metrics = TogetherAPIMetrics()
        
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.rate_limits.requests_per_minute,
            max_retries=5,
            initial_backoff_s=1.0
        )
        
        logger.info(f"TogetherAPI initialized with rate limit: {self.rate_limits.requests_per_minute} RPM")
    
    async def generate_text(
        self,
        prompt: str,
        model: str = "meta-llama/Llama-2-7b-chat-hf",
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        **kwargs
    ) -> Optional[str]:
        """Generate text using Together AI API"""
        if not self.client:
            return json.dumps({"error": "Together AI client not configured"})
        
        if not await self.rate_limiter.wait():
            self.metrics.rate_limit_hits += 1
            return json.dumps({"error": "Rate limit exceeded"})
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            content = response.choices[0].message.content
            
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.last_request_time = datetime.now()
            self.metrics.average_latency_ms = (
                (self.metrics.average_latency_ms * (self.metrics.total_requests - 1) + latency_ms) /
                self.metrics.total_requests
            )
            
            if hasattr(response, 'usage') and response.usage:
                self.metrics.total_tokens += response.usage.total_tokens
            
            return content
            
        except Exception as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            if "429" in str(e) or "rate limit" in str(e).lower():
                self.metrics.rate_limit_hits += 1
            logger.error(f"Together AI API error: {e}")
            return json.dumps({"error": "ApiCallFailed", "message": str(e)})
    
    def update_rate_limits(self, rpm: Optional[int] = None, tpm: Optional[int] = None):
        """Update rate limits"""
        if rpm:
            self.rate_limits.requests_per_minute = rpm
            self.rate_limiter.requests_per_minute = rpm
            self.rate_limiter.token_fill_rate = rpm / 60.0
            self.rate_limiter.max_tokens = float(rpm)
        if tpm:
            self.rate_limits.tokens_per_minute = tpm
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current API metrics"""
        return {
            "total_requests": self.metrics.total_requests,
            "successful_requests": self.metrics.successful_requests,
            "failed_requests": self.metrics.failed_requests,
            "rate_limit_hits": self.metrics.rate_limit_hits,
            "total_tokens": self.metrics.total_tokens,
            "total_cost": self.metrics.total_cost,
            "average_latency_ms": self.metrics.average_latency_ms,
            "last_request_time": self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None,
            "rate_limits": {
                "rpm": self.rate_limits.requests_per_minute,
                "tpm": self.rate_limits.tokens_per_minute,
            },
            "rate_limiter_metrics": self.rate_limiter.get_metrics()
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection"""
        if not self.client:
            return {"success": False, "error": "Client not configured"}
        try:
            result = await self.generate_text("Hello", max_tokens=10)
            if result and not result.startswith('{"error"'):
                return {"success": True, "message": "Connection successful"}
            return {"success": False, "error": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


def create_together_api(api_key: Optional[str] = None, config: Optional[Config] = None) -> TogetherAPI:
    """Create a Together AI API instance"""
    return TogetherAPI(api_key=api_key, config=config)


