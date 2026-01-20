"""
Grok API Integration for mindX

This module provides comprehensive integration with xAI's Grok API,
including rate limit management, monitoring, and optimization.
Grok API is compatible with OpenAI's API format.
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
    # Don't log here - logger not yet initialized

import aiohttp

from utils.logging_config import get_logger
from utils.config import Config
from llm.rate_limiter import RateLimiter

logger = get_logger(__name__)


@dataclass
class GrokRateLimits:
    """Grok API rate limits (xAI service)"""
    # Based on xAI's current limits (may change)
    requests_per_minute: int = 30  # Conservative default
    requests_per_day: int = 10000  # High daily limit
    tokens_per_minute: int = 100000  # Estimated
    tokens_per_day: int = 10000000  # High daily limit


@dataclass
class GrokAPIMetrics:
    """Metrics for Grok API usage"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    total_tokens_input: int = 0
    total_tokens_output: int = 0
    total_cost: float = 0.0  # Grok may have different pricing
    last_request_time: Optional[datetime] = None
    average_latency_ms: float = 0.0


class GrokAPI:
    """
    Grok API client with rate limiting, monitoring, and optimization.

    Uses xAI's API endpoint which is compatible with OpenAI's format.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        rate_limits: Optional[GrokRateLimits] = None,
        config: Optional[Config] = None
    ):
        self.config = config or Config()
        self.api_key = api_key or os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY") or self.config.get("llm.grok.api_key")
        self.base_url = base_url or self.config.get("llm.grok.base_url", "https://api.x.ai/v1")

        if not OPENAI_AVAILABLE:
            logger.error("OpenAI library not available (required for Grok API)")
            self.client = None
        elif self.api_key:
            self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            logger.warning("Grok API key not provided")
            self.client = None

        self.rate_limits = rate_limits or GrokRateLimits()
        self.metrics = GrokAPIMetrics()

        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.rate_limits.requests_per_minute,
            max_retries=5,
            initial_backoff_s=1.0
        )

        # Grok model pricing (subject to change)
        self.pricing = {
            "grok-beta": {"input": 0.0, "output": 0.0},  # Free during beta
            "grok-1": {"input": 0.0, "output": 0.0},      # Free during beta
            "grok-1.5": {"input": 0.0, "output": 0.0},    # Free during beta
            "grok-1.5-vision": {"input": 0.0, "output": 0.0},  # Free during beta
        }

        logger.info(f"GrokAPI initialized with rate limit: {self.rate_limits.requests_per_minute} RPM")

    def _get_model_pricing(self, model: str) -> Dict[str, float]:
        """Get pricing for a model"""
        # Try exact match first
        if model in self.pricing:
            return self.pricing[model]

        # Try partial match
        for key, pricing in self.pricing.items():
            if key in model.lower():
                return pricing

        # Default to grok-beta pricing
        return self.pricing.get("grok-beta", {"input": 0.0, "output": 0.0})

    async def generate_text(
        self,
        prompt: str,
        model: str = "grok-beta",
        max_tokens: Optional[int] = 4096,
        temperature: Optional[float] = 0.7,
        json_mode: Optional[bool] = False,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using Grok API with rate limiting and retry logic.
        """
        if not self.client:
            return json.dumps({"error": "Grok client not configured"})

        # Wait for rate limiter
        if not await self.rate_limiter.wait():
            self.metrics.rate_limit_hits += 1
            return json.dumps({"error": "Rate limit exceeded"})

        start_time = asyncio.get_event_loop().time()

        try:
            # Prepare messages
            messages = [{"role": "user", "content": prompt}]

            # Handle system messages
            system_message = kwargs.get("system_message") or kwargs.get("system")
            if system_message:
                messages.insert(0, {"role": "system", "content": system_message})

            # Set response format for JSON mode
            response_format = {"type": "json_object"} if json_mode else None

            # Make API call
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                response_format=response_format,
                **kwargs
            )

            # Extract response content
            content = response.choices[0].message.content

            # Update metrics
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.last_request_time = datetime.now()

            # Extract token usage
            usage = response.usage
            if usage:
                self.metrics.total_tokens_input += usage.prompt_tokens or 0
                self.metrics.total_tokens_output += usage.completion_tokens or 0

                # Calculate cost (Grok may be free during beta)
                pricing = self._get_model_pricing(model)
                input_cost = (usage.prompt_tokens or 0) * pricing["input"] / 1000
                output_cost = (usage.completion_tokens or 0) * pricing["output"] / 1000
                self.metrics.total_cost += input_cost + output_cost

            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.average_latency_ms = (
                (self.metrics.average_latency_ms * (self.metrics.total_requests - 1) + latency_ms) /
                self.metrics.total_requests
            )

            return content

        except openai.RateLimitError as e:
            self.metrics.total_requests += 1
            self.metrics.rate_limit_hits += 1
            logger.warning(f"Grok API rate limit hit: {e}")
            return json.dumps({"error": "RateLimitExceeded", "message": str(e)})
        except openai.AuthenticationError as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"Grok API authentication error: {e}")
            return json.dumps({"error": "AuthenticationError", "message": str(e)})
        except openai.APIError as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"Grok API error: {e}")
            return json.dumps({"error": "ApiCallFailed", "message": str(e)})
        except Exception as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"Unexpected Grok API error: {e}")
            return json.dumps({"error": "ApiCallFailed", "message": str(e)})

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available Grok models"""
        if not self.client:
            return []

        try:
            models_response = await self.client.models.list()
            models = []
            for model in models_response.data:
                # Filter to only Grok models
                if "grok" in model.id.lower():
                    models.append({
                        "id": model.id,
                        "object": model.object,
                        "created": model.created,
                        "owned_by": model.owned_by
                    })
            return models
        except Exception as e:
            logger.error(f"Error listing Grok models: {e}")
            return []

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
            "total_tokens_input": self.metrics.total_tokens_input,
            "total_tokens_output": self.metrics.total_tokens_output,
            "total_cost": self.metrics.total_cost,
            "average_latency_ms": self.metrics.average_latency_ms,
            "last_request_time": self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None,
            "rate_limits": {
                "rpm": self.rate_limits.requests_per_minute,
                "tpm": self.rate_limits.tokens_per_minute,
            },
            "rate_limiter_metrics": self.rate_limiter.get_metrics()
        }


def create_grok_api(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    config: Optional[Config] = None
) -> GrokAPI:
    """Create a Grok API instance"""
    return GrokAPI(api_key=api_key, base_url=base_url, config=config)