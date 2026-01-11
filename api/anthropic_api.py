"""
Anthropic Claude API Integration for mindX

This module provides comprehensive integration with Anthropic Claude API,
including rate limit management, monitoring, and optimization based on official documentation.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import anthropic
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic library not installed. Install with: pip install anthropic")

from utils.logging_config import get_logger
from utils.config import Config
from llm.rate_limiter import RateLimiter

logger = get_logger(__name__)


@dataclass
class AnthropicRateLimits:
    """Anthropic API rate limits from official documentation"""
    # Standard tier
    requests_per_minute: int = 50
    requests_per_day: int = 1000
    tokens_per_minute: int = 40000
    tokens_per_day: int = 1000000
    
    # Pro tier
    pro_rpm: int = 100
    pro_tpm: int = 100000
    
    # Enterprise tier
    enterprise_rpm: int = 1000
    enterprise_tpm: int = 1000000


@dataclass
class AnthropicAPIMetrics:
    """Metrics for Anthropic API usage"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost: float = 0.0
    last_request_time: Optional[datetime] = None
    average_latency_ms: float = 0.0


class AnthropicAPI:
    """
    Anthropic Claude API client with rate limiting, monitoring, and optimization.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limits: Optional[AnthropicRateLimits] = None,
        config: Optional[Config] = None
    ):
        self.config = config or Config()
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or self.config.get("llm.anthropic.api_key")
        
        if not ANTHROPIC_AVAILABLE:
            logger.error("Anthropic library not available")
            self.client = None
        elif self.api_key:
            self.client = AsyncAnthropic(api_key=self.api_key)
        else:
            logger.warning("Anthropic API key not provided")
            self.client = None
        
        self.rate_limits = rate_limits or AnthropicRateLimits()
        self.metrics = AnthropicAPIMetrics()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.rate_limits.requests_per_minute,
            max_retries=5,
            initial_backoff_s=1.0
        )
        
        # Pricing per 1M tokens (as of 2024)
        self.pricing = {
            "claude-3-opus": {"input": 15.0, "output": 75.0},
            "claude-3-sonnet": {"input": 3.0, "output": 15.0},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            "claude-3-5-sonnet": {"input": 3.0, "output": 15.0},
        }
        
        logger.info(f"AnthropicAPI initialized with rate limit: {self.rate_limits.requests_per_minute} RPM")
    
    def _get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model"""
        for key, pricing in self.pricing.items():
            if key in model:
                return pricing
        return self.pricing["claude-3-sonnet"]  # Default
    
    async def generate_text(
        self,
        prompt: str,
        model: str = "claude-3-sonnet-20240229",
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        json_mode: Optional[bool] = False,
        **kwargs
    ) -> Optional[str]:
        """Generate text using Anthropic API"""
        if not self.client:
            return json.dumps({"error": "Anthropic client not configured"})
        
        if not await self.rate_limiter.wait():
            self.metrics.rate_limit_hits += 1
            return json.dumps({"error": "Rate limit exceeded"})
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            request_params = {
                "model": model,
                "max_tokens": max_tokens or 2048,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            
            if json_mode:
                request_params["response_format"] = {"type": "json_object"}
            
            request_params.update(kwargs)
            
            response = await self.client.messages.create(**request_params)
            
            content = response.content[0].text
            
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.last_request_time = datetime.now()
            self.metrics.average_latency_ms = (
                (self.metrics.average_latency_ms * (self.metrics.total_requests - 1) + latency_ms) /
                self.metrics.total_requests
            )
            
            if response.usage:
                self.metrics.total_tokens_input += response.usage.input_tokens
                self.metrics.total_tokens_output += response.usage.output_tokens
                
                pricing = self._get_model_pricing(model)
                cost = (
                    (response.usage.input_tokens / 1000000) * pricing["input"] +
                    (response.usage.output_tokens / 1000000) * pricing["output"]
                )
                self.metrics.total_cost += cost
            
            return content
            
        except anthropic.RateLimitError as e:
            self.metrics.rate_limit_hits += 1
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.warning(f"Anthropic rate limit hit: {e}")
            return json.dumps({"error": "RateLimitError", "message": str(e)})
        except Exception as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"Anthropic API error: {e}")
            return json.dumps({"error": "ApiCallFailed", "message": str(e)})
    
    def update_rate_limits(self, rpm: Optional[int] = None, tpm: Optional[int] = None, tier: Optional[str] = None):
        """Update rate limits"""
        if tier == "pro":
            self.rate_limits.requests_per_minute = self.rate_limits.pro_rpm
            self.rate_limits.tokens_per_minute = self.rate_limits.pro_tpm
        elif tier == "enterprise":
            self.rate_limits.requests_per_minute = self.rate_limits.enterprise_rpm
            self.rate_limits.tokens_per_minute = self.rate_limits.enterprise_tpm
        
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
            "total_tokens_input": self.metrics.total_tokens_input,
            "total_tokens_output": self.metrics.total_tokens_output,
            "total_tokens": self.metrics.total_tokens_input + self.metrics.total_tokens_output,
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


def create_anthropic_api(api_key: Optional[str] = None, config: Optional[Config] = None) -> AnthropicAPI:
    """Create an Anthropic API instance"""
    return AnthropicAPI(api_key=api_key, config=config)


