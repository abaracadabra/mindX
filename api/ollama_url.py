"""
Ollama URL-based API Integration for mindX

This module provides comprehensive integration with Ollama via HTTP URL,
including rate limit management, monitoring, and model listing.
"""

import asyncio
import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    # Don't log here - logger not yet initialized

from utils.logging_config import get_logger
from utils.config import Config
from llm.rate_limiter import RateLimiter

logger = get_logger(__name__)


@dataclass
class OllamaRateLimits:
    """Ollama API rate limits (local server, typically no limits)"""
    requests_per_minute: int = 1000  # High limit for local
    requests_per_day: int = 1000000
    tokens_per_minute: int = 10000000
    tokens_per_day: int = 1000000000


@dataclass
class OllamaAPIMetrics:
    """Metrics for Ollama API usage"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    rate_limit_hits: int = 0
    total_tokens: int = 0
    last_request_time: Optional[datetime] = None
    average_latency_ms: float = 0.0
    available_models: List[str] = None
    
    def __post_init__(self):
        if self.available_models is None:
            self.available_models = []


class OllamaAPI:
    """
    Ollama API client via HTTP URL with rate limiting and monitoring.
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        rate_limits: Optional[OllamaRateLimits] = None,
        config: Optional[Config] = None
    ):
        self.config = config or Config()
        
        # Support both base_url and host/port configuration
        if base_url:
            self.base_url = base_url
        elif host and port:
            self.base_url = f"http://{host}:{port}"
        else:
            # Try environment/config
            env_url = os.getenv("MINDX_LLM__OLLAMA__BASE_URL")
            config_url = self.config.get("llm.ollama.base_url")
            config_host = self.config.get("llm.ollama.host", "localhost")
            config_port = self.config.get("llm.ollama.port", 11434)
            
            if env_url:
                self.base_url = env_url
            elif config_url:
                self.base_url = config_url
            else:
                self.base_url = f"http://{config_host}:{config_port}"
        
        # Ensure base_url doesn't end with /api
        self.base_url = self.base_url.rstrip('/').replace('/api', '')
        self.api_url = f"{self.base_url}/api"
        
        self.rate_limits = rate_limits or OllamaRateLimits()
        self.metrics = OllamaAPIMetrics()
        
        self.rate_limiter = RateLimiter(
            requests_per_minute=self.rate_limits.requests_per_minute,
            max_retries=5,
            initial_backoff_s=0.5  # Shorter backoff for local
        )
        
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"OllamaAPI initialized for {self.base_url} with rate limit: {self.rate_limits.requests_per_minute} RPM")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session"""
        if not AIOHTTP_AVAILABLE:
            raise RuntimeError("aiohttp not available")
        
        if self.http_session is None or self.http_session.closed:
            # Shorter timeout for connection testing
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=10,  # 10 second timeout for connection tests
                    connect=5,  # 5 second connection timeout
                    sock_read=5  # 5 second read timeout
                )
            )
        return self.http_session
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models from Ollama server"""
        try:
            session = await self._get_session()
            async with session.get(f"{self.api_url}/tags", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    models = data.get("models", [])
                    self.metrics.available_models = [m.get("name", "") for m in models]
                    return models
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to list Ollama models: {response.status} - {error_text}")
                    return []
        except asyncio.TimeoutError:
            logger.error(f"Timeout listing Ollama models from {self.base_url}")
            return []
        except aiohttp.ClientConnectorError as e:
            logger.error(f"Cannot connect to Ollama at {self.base_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}", exc_info=True)
            return []
    
    async def generate_text(
        self,
        prompt: str,
        model: str = "llama3:8b",
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        use_chat: bool = False,
        **kwargs
    ) -> Optional[str]:
        """
        Generate text using Ollama API.
        
        Args:
            prompt: The prompt text
            model: Model name
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            use_chat: If True, use /api/chat endpoint, otherwise use /api/generate
        """
        if not AIOHTTP_AVAILABLE:
            return json.dumps({"error": "aiohttp not available"})
        
        if not await self.rate_limiter.wait():
            self.metrics.rate_limit_hits += 1
            return json.dumps({"error": "Rate limit exceeded"})
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            session = await self._get_session()
            
            if use_chat:
                # Use chat endpoint (POST /api/chat)
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    }
                }
                endpoint = f"{self.api_url}/chat"
                logger.debug(f"Using Ollama chat endpoint: {endpoint}")
            else:
                # Use generate endpoint (POST /api/generate) - standard Ollama endpoint
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    }
                }
                endpoint = f"{self.api_url}/generate"
                logger.debug(f"Using Ollama generate endpoint: {endpoint}")
            
            payload["options"].update(kwargs.get("options", {}))
            
            async with session.post(endpoint, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract content based on endpoint
                    if use_chat:
                        content = data.get("message", {}).get("content", "")
                    else:
                        content = data.get("response", "")
                    
                    latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    self.metrics.total_requests += 1
                    self.metrics.successful_requests += 1
                    self.metrics.last_request_time = datetime.now()
                    self.metrics.average_latency_ms = (
                        (self.metrics.average_latency_ms * (self.metrics.total_requests - 1) + latency_ms) /
                        self.metrics.total_requests
                    )
                    
                    # Estimate tokens
                    estimated_tokens = len(prompt.split()) * 1.3 + len(content.split()) * 1.3
                    self.metrics.total_tokens += int(estimated_tokens)
                    
                    return content
                else:
                    error_text = await response.text()
                    self.metrics.total_requests += 1
                    self.metrics.failed_requests += 1
                    logger.error(f"Ollama API error: {response.status} - {error_text}")
                    return json.dumps({"error": "ApiCallFailed", "message": error_text})
                    
        except aiohttp.ClientConnectorError as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"Ollama connection error: {e}")
            return json.dumps({"error": "ConnectionError", "message": f"Cannot connect to Ollama at {self.base_url}"})
        except Exception as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"Ollama API error: {e}")
            return json.dumps({"error": "ApiCallFailed", "message": str(e)})
    
    async def get_model_info(self, model: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        try:
            session = await self._get_session()
            async with session.post(f"{self.api_url}/show", json={"name": model}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get model info: {response.status} - {error_text}")
                    return {"error": error_text}
        except Exception as e:
            logger.error(f"Error getting model info: {e}")
            return {"error": str(e)}
    
    async def generate_embeddings(self, prompt: str, model: str) -> Optional[List[float]]:
        """Generate embeddings for a prompt"""
        try:
            session = await self._get_session()
            payload = {
                "model": model,
                "prompt": prompt
            }
            async with session.post(f"{self.api_url}/embeddings", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("embedding")
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to generate embeddings: {response.status} - {error_text}")
                    return None
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            return None
    
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
            "average_latency_ms": self.metrics.average_latency_ms,
            "last_request_time": self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None,
            "available_models": self.metrics.available_models,
            "base_url": self.base_url,
            "rate_limits": {
                "rpm": self.rate_limits.requests_per_minute,
                "tpm": self.rate_limits.tokens_per_minute,
            },
            "rate_limiter_metrics": self.rate_limiter.get_metrics()
        }
    
    async def test_connection(self) -> Dict[str, Any]:
        """Test API connection with detailed feedback"""
        try:
            # First, try a simple health check
            session = await self._get_session()
            
            # Try to connect to /api/tags endpoint
            try:
                async with session.get(f"{self.api_url}/tags", timeout=aiohttp.ClientTimeout(total=5)) as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        return {
                            "success": True,
                            "message": f"Successfully connected to Ollama at {self.base_url}",
                            "model_count": len(models),
                            "base_url": self.base_url,
                            "status_code": response.status
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Server returned status {response.status}: {error_text[:200]}",
                            "base_url": self.base_url,
                            "status_code": response.status
                        }
            except asyncio.TimeoutError:
                return {
                    "success": False,
                    "error": f"Connection timeout: Ollama server at {self.base_url} did not respond within 5 seconds",
                    "base_url": self.base_url,
                    "timeout": True
                }
            except aiohttp.ClientConnectorError as e:
                return {
                    "success": False,
                    "error": f"Cannot connect to Ollama server at {self.base_url}. Check if Ollama is running and the URL is correct. Error: {str(e)}",
                    "base_url": self.base_url,
                    "connection_error": True
                }
            except aiohttp.ClientError as e:
                return {
                    "success": False,
                    "error": f"Connection error: {str(e)}",
                    "base_url": self.base_url,
                    "client_error": True
                }
        except Exception as e:
            logger.error(f"Error testing Ollama connection: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "base_url": self.base_url
            }
    
    async def shutdown(self):
        """Close HTTP session"""
        if self.http_session and not self.http_session.closed:
            await self.http_session.close()


def create_ollama_api(
    base_url: Optional[str] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
    config: Optional[Config] = None
) -> OllamaAPI:
    """Create an Ollama API instance"""
    return OllamaAPI(base_url=base_url, host=host, port=port, config=config)


