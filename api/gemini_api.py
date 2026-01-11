"""
Google Gemini API Integration for mindX

This module provides comprehensive integration with Google Gemini API,
including rate limit management, monitoring, and optimization based on official documentation.
"""

import asyncio
import json
import os
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

import google.generativeai as genai
import aiohttp

from utils.logging_config import get_logger
from utils.config import Config
from llm.rate_limiter import RateLimiter

logger = get_logger(__name__)


@dataclass
class GeminiRateLimits:
    """Gemini API rate limits from official documentation"""
    requests_per_minute: int = 60  # Default, can be upgraded
    requests_per_day: int = 1500  # Free tier
    tokens_per_minute: int = 1000000  # 1M tokens/min
    tokens_per_day: int = 50000000  # 50M tokens/day (free tier)
    
    # Plan-specific limits (can be updated from docs)
    free_tier_rpm: int = 60
    paid_tier_rpm: int = 3600  # Can go higher with enterprise
    free_tier_tpm: int = 1000000
    paid_tier_tpm: int = 10000000


@dataclass
class GeminiAPIMetrics:
    """Metrics for Gemini API usage"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    last_request_time: Optional[datetime] = None
    average_latency_ms: float = 0.0


class GeminiAPI:
    """
    Google Gemini API client with rate limiting, monitoring, and optimization.
    
    Automatically adjusts rate limits based on plan and official documentation.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        rate_limits: Optional[GeminiRateLimits] = None,
        config: Optional[Config] = None
    ):
        self.config = config or Config()
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or self.config.get("llm.gemini.api_key")
        
        if not self.api_key:
            logger.warning("Gemini API key not provided")
        else:
            genai.configure(api_key=self.api_key)
        
        self.rate_limits = rate_limits or GeminiRateLimits()
        self.metrics = GeminiAPIMetrics()
        
        # Initialize rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.rate_limits.requests_per_minute,
            max_retries=5,
            initial_backoff_s=1.0
        )
        
        # Load model catalog
        self.model_catalog: Dict[str, Any] = {}
        self._load_model_catalog()
        
        logger.info(f"GeminiAPI initialized with rate limit: {self.rate_limits.requests_per_minute} RPM")
    
    def _load_model_catalog(self):
        """Load model catalog from gemini.yaml"""
        try:
            import yaml
            from pathlib import Path
            from utils.config import PROJECT_ROOT
            
            config_path = PROJECT_ROOT / "models" / "gemini.yaml"
            if config_path.exists():
                with open(config_path, "r") as f:
                    self.model_catalog = yaml.safe_load(f) or {}
                logger.info(f"Loaded {len(self.model_catalog)} Gemini models from catalog")
        except Exception as e:
            logger.error(f"Error loading Gemini model catalog: {e}")
    
    async def generate_text(
        self,
        prompt: str,
        model: str = "gemini-1.5-flash-latest",
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        json_mode: Optional[bool] = False,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using Gemini API with rate limiting and retry logic.
        """
        if not self.api_key:
            return json.dumps({"error": "API key not configured"})
        
        # Wait for rate limiter
        if not await self.rate_limiter.wait():
            self.metrics.rate_limit_hits += 1
            return json.dumps({"error": "Rate limit exceeded"})
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get model info from catalog
            sanitized_model = f"gemini/{model}" if not model.startswith("gemini/") else model
            model_info = self.model_catalog.get(sanitized_model, {})
            api_model_name = model_info.get("api_name", model)
            
            model_instance = genai.GenerativeModel(api_model_name)
            generation_config = genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature
            )
            
            if json_mode:
                generation_config.response_mime_type = "application/json"
            
            # Make API call
            response = await asyncio.to_thread(
                model_instance.generate_content,
                contents=prompt,
                generation_config=generation_config,
                **kwargs
            )
            
            # Update metrics
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.last_request_time = datetime.now()
            self.metrics.average_latency_ms = (
                (self.metrics.average_latency_ms * (self.metrics.total_requests - 1) + latency_ms) /
                self.metrics.total_requests
            )
            
            # Estimate tokens (Gemini doesn't always return token count)
            estimated_tokens = len(prompt.split()) * 1.3 + len(response.text.split()) * 1.3
            self.metrics.total_tokens += int(estimated_tokens)
            
            return response.text
            
        except Exception as e:
            error_message = str(e)
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            
            # Check for rate limit errors
            if "429" in error_message or "quota" in error_message.lower():
                self.metrics.rate_limit_hits += 1
                logger.warning(f"Gemini rate limit hit: {error_message}")
            
            logger.error(f"Gemini API error: {error_message}")
            return json.dumps({"error": "ApiCallFailed", "message": error_message})
    
    def update_rate_limits(self, rpm: Optional[int] = None, tpm: Optional[int] = None):
        """Update rate limits (can be called from UI or based on plan detection)"""
        if rpm:
            self.rate_limits.requests_per_minute = rpm
            self.rate_limiter.requests_per_minute = rpm
            self.rate_limiter.token_fill_rate = rpm / 60.0
            self.rate_limiter.max_tokens = float(rpm)
            logger.info(f"Updated Gemini rate limit to {rpm} RPM")
        
        if tpm:
            self.rate_limits.tokens_per_minute = tpm
            logger.info(f"Updated Gemini token limit to {tpm} TPM")
    
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
                "rpd": self.rate_limits.requests_per_day,
                "tpd": self.rate_limits.tokens_per_day
            },
            "rate_limiter_metrics": self.rate_limiter.get_metrics()
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection"""
        try:
            result = await self.generate_text("Hello", max_tokens=10)
            if result and not result.startswith('{"error"'):
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "error": result}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Factory function
def create_gemini_api(api_key: Optional[str] = None, config: Optional[Config] = None) -> GeminiAPI:
    """Create a Gemini API instance"""
    return GeminiAPI(api_key=api_key, config=config)


