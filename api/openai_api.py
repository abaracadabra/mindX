"""
OpenAI API Integration for mindX

This module provides comprehensive integration with OpenAI API,
including rate limit management, monitoring, and optimization based on official documentation.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import openai
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not installed. Install with: pip install openai")

import aiohttp

from utils.logging_config import get_logger
from utils.config import Config
from llm.rate_limiter import RateLimiter

logger = get_logger(__name__)


@dataclass
class OpenAIRateLimits:
    """OpenAI API rate limits from official documentation"""
    # Tier 1 (Free tier) - Default
    requests_per_minute: int = 3
    requests_per_day: int = 200
    tokens_per_minute: int = 40000
    tokens_per_day: int = 100000
    
    # Tier 2 (Pay-as-you-go)
    tier2_rpm: int = 60
    tier2_tpm: int = 60000
    
    # Tier 3 (Enterprise)
    tier3_rpm: int = 500
    tier3_tpm: int = 500000
    
    # Tier 4 (Enterprise Plus)
    tier4_rpm: int = 10000
    tier4_tpm: int = 10000000


@dataclass
class OpenAIAPIMetrics:
    """Metrics for OpenAI API usage"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost: float = 0.0
    last_request_time: Optional[datetime] = None
    average_latency_ms: float = 0.0


class OpenAIAPI:
    """
    OpenAI API client with rate limiting, monitoring, and optimization.
    
    Automatically adjusts rate limits based on plan and official documentation.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        rate_limits: Optional[OpenAIRateLimits] = None,
        config: Optional[Config] = None
    ):
        self.config = config or Config()
        self.api_key = api_key or os.getenv("OPENAI_API_KEY") or self.config.get("llm.openai.api_key")
        self.base_url = base_url or self.config.get("llm.openai.base_url", "https://api.openai.com/v1")
        
        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not available")
            self.client = None
        elif self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            logger.warning("OpenAI API key not provided")
            self.client = None
        
        self.rate_limits = rate_limits or OpenAIRateLimits()
        self.metrics = OpenAIAPIMetrics()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.rate_limits.requests_per_minute,
            max_retries=5,
            initial_backoff_s=1.0
        )
        
        # Pricing per 1K tokens (as of 2024)
        self.pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-4o": {"input": 0.005, "output": 0.015},
        }
        
        logger.info(f"OpenAIAPI initialized with rate limit: {self.rate_limits.requests_per_minute} RPM")
    
    def _get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model"""
        # Try exact match first
        if model in self.pricing:
            return self.pricing[model]
        
        # Try partial match
        for key, pricing in self.pricing.items():
            if key in model:
                return pricing
        
        # Default to gpt-3.5-turbo pricing
        return self.pricing["gpt-3.5-turbo"]
    
    async def generate_text(
        self,
        prompt: str,
        model: str = "gpt-3.5-turbo",
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        json_mode: Optional[bool] = False,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using OpenAI API with rate limiting and retry logic.
        """
        if not self.client:
            return json.dumps({"error": "OpenAI client not configured"})
        
        # Wait for rate limiter
        if not await self.rate_limiter.wait():
            self.metrics.rate_limit_hits += 1
            return json.dumps({"error": "Rate limit exceeded"})
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Prepare request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            if json_mode:
                request_params["response_format"] = {"type": "json_object"}
            
            request_params.update(kwargs)
            
            # Make API call
            response = await self.client.chat.completions.create(**request_params)
            
            # Extract response
            content = response.choices[0].message.content
            
            # Update metrics
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.last_request_time = datetime.now()
            self.metrics.average_latency_ms = (
                (self.metrics.average_latency_ms * (self.metrics.total_requests - 1) + latency_ms) /
                self.metrics.total_requests
            )
            
            # Get token usage
            if response.usage:
                self.metrics.total_tokens_input += response.usage.prompt_tokens
                self.metrics.total_tokens_output += response.usage.completion_tokens
                
                # Calculate cost
                pricing = self._get_model_pricing(model)
                cost = (
                    (response.usage.prompt_tokens / 1000) * pricing["input"] +
                    (response.usage.completion_tokens / 1000) * pricing["output"]
                )
                self.metrics.total_cost += cost
            
            return content
            
        except openai.RateLimitError as e:
            self.metrics.rate_limit_hits += 1
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.warning(f"OpenAI rate limit hit: {e}")
            return json.dumps({"error": "RateLimitError", "message": str(e)})
        except Exception as e:
            error_message = str(e)
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"OpenAI API error: {error_message}")
            return json.dumps({"error": "ApiCallFailed", "message": error_message})
    
    def update_rate_limits(self, rpm: Optional[int] = None, tpm: Optional[int] = None, tier: Optional[int] = None):
        """Update rate limits based on tier or explicit values"""
        if tier:
            if tier == 1:
                self.rate_limits.requests_per_minute = self.rate_limits.requests_per_minute
            elif tier == 2:
                self.rate_limits.requests_per_minute = self.rate_limits.tier2_rpm
                self.rate_limits.tokens_per_minute = self.rate_limits.tier2_tpm
            elif tier == 3:
                self.rate_limits.requests_per_minute = self.rate_limits.tier3_rpm
                self.rate_limits.tokens_per_minute = self.rate_limits.tier3_tpm
            elif tier == 4:
                self.rate_limits.requests_per_minute = self.rate_limits.tier4_rpm
                self.rate_limits.tokens_per_minute = self.rate_limits.tier4_tpm
        
        if rpm:
            self.rate_limits.requests_per_minute = rpm
            self.rate_limiter.requests_per_minute = rpm
            self.rate_limiter.token_fill_rate = rpm / 60.0
            self.rate_limiter.max_tokens = float(rpm)
            logger.info(f"Updated OpenAI rate limit to {rpm} RPM")
        
        if tpm:
            self.rate_limits.tokens_per_minute = tpm
            logger.info(f"Updated OpenAI token limit to {tpm} TPM")
    
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
                "rpd": self.rate_limits.requests_per_day,
                "tpd": self.rate_limits.tokens_per_day
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
            else:
                return {"success": False, "error": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Factory function
def create_openai_api(api_key: Optional[str] = None, base_url: Optional[str] = None, config: Optional[Config] = None) -> OpenAIAPI:
    """Create an OpenAI API instance"""
    return OpenAIAPI(api_key=api_key, base_url=base_url, config=config)


