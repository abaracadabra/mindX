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
            # Try to load from settings if available (matching chatter.py pattern)
            try:
                from webmind.settings import SettingsManager
                settings = SettingsManager()
                base_url = settings.get('ollama_base_url', None)
                if base_url:
                    self.base_url = base_url
            except:
                pass
            
            # Fall back to environment/config if settings didn't provide it
            if not hasattr(self, 'base_url') or not self.base_url:
                env_url = os.getenv("MINDX_LLM__OLLAMA__BASE_URL")
                config_url = self.config.get("llm.ollama.base_url")
                # Primary: 10.0.0.155:18080 (GPU server), Fallback: localhost:11434 (CPU)
                config_host = self.config.get("llm.ollama.host", "10.0.0.155")
                config_port = self.config.get("llm.ollama.port", 18080)
                
                if env_url:
                    self.base_url = env_url
                elif config_url:
                    self.base_url = config_url
                else:
                    self.base_url = f"http://{config_host}:{config_port}"
        
        # Store fallback URL for connection failures
        self.fallback_url = self.config.get("llm.ollama.fallback_url", "http://localhost:11434")
        self.using_fallback = False
        
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
            # Get timeout from settings (matching chatter.py pattern)
            try:
                from webmind.settings import SettingsManager
                timeout_settings = SettingsManager()
                ollama_timeout = timeout_settings.get('ollama_timeout', 10.0)
                # For inference, use longer timeout if available
                ollama_inference_timeout = timeout_settings.get('ollama_inference_timeout', 120.0)
            except:
                ollama_timeout = 10.0
                ollama_inference_timeout = 120.0
            
            # Extended timeout for large model inference (per Ollama API docs)
            # Total timeout: configurable for large models, sock_read: 60s for streaming responses
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=ollama_inference_timeout,  # Configurable total timeout for large models
                    connect=10,  # 10 second connection timeout
                    sock_read=60  # 60 second read timeout for inference
                )
            )
        return self.http_session
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List all available models from Ollama server"""
        try:
            # Get timeout from settings (matching chatter.py pattern)
            try:
                from webmind.settings import SettingsManager
                timeout_settings = SettingsManager()
                ollama_timeout = timeout_settings.get('ollama_timeout', 10.0)
            except:
                ollama_timeout = 10.0
            
            session = await self._get_session()
            async with session.get(f"{self.api_url}/tags", timeout=aiohttp.ClientTimeout(total=ollama_timeout)) as response:
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
        messages: Optional[List[Dict[str, str]]] = None,
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
                # Use provided messages if available, otherwise create from prompt
                chat_messages = messages if messages else [
                    {"role": "user", "content": prompt}
                ]
                payload = {
                    "model": model,
                    "messages": chat_messages,
                    "stream": False,  # Non-streaming mode
                    "keep_alive": kwargs.get("keep_alive", "5m"),  # Keep model loaded (default 5m per API docs)
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    }
                }
                endpoint = f"{self.api_url}/chat"
                logger.debug(f"Using Ollama chat endpoint: {endpoint} with {len(chat_messages)} messages, keep_alive={payload['keep_alive']}")
            else:
                # Use generate endpoint (POST /api/generate) - standard Ollama endpoint
                # Per Ollama API docs: https://github.com/ollama/ollama/blob/main/docs/api.md
                payload = {
                    "model": model,
                    "prompt": prompt,
                    "stream": False,  # Non-streaming mode for simpler handling
                    "keep_alive": kwargs.get("keep_alive", "5m"),  # Keep model loaded (default 5m per API docs)
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    }
                }
                endpoint = f"{self.api_url}/generate"
                logger.debug(f"Using Ollama generate endpoint: {endpoint} with keep_alive={payload['keep_alive']}")
            
            # Update options with any additional parameters from kwargs
            payload["options"].update(kwargs.get("options", {}))
            
            # Add any additional top-level parameters from kwargs (e.g., format, system, template)
            for key in ["format", "system", "template", "raw", "suffix", "images", "think"]:
                if key in kwargs:
                    payload[key] = kwargs[key]
            
            # Use extended timeout for inference requests (per Ollama API docs)
            inference_timeout = aiohttp.ClientTimeout(
                total=120,  # 120 seconds total for large models
                connect=10,
                sock_read=60  # 60 seconds for reading response
            )
            
            async with session.post(endpoint, json=payload, timeout=inference_timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Extract content based on endpoint (per Ollama API docs)
                    if use_chat:
                        # Chat endpoint returns: {"message": {"role": "assistant", "content": "..."}}
                        content = data.get("message", {}).get("content", "")
                    else:
                        # Generate endpoint returns: {"response": "..."}
                        content = data.get("response", "")
                    
                    # Extract performance metrics if available (per Ollama API docs)
                    eval_count = data.get("eval_count", 0)
                    prompt_eval_count = data.get("prompt_eval_count", 0)
                    total_duration = data.get("total_duration", 0)  # nanoseconds
                    
                    latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
                    self.metrics.total_requests += 1
                    self.metrics.successful_requests += 1
                    self.metrics.last_request_time = datetime.now()
                    self.metrics.average_latency_ms = (
                        (self.metrics.average_latency_ms * (self.metrics.total_requests - 1) + latency_ms) /
                        self.metrics.total_requests
                    )
                    
                    # Use actual token counts if available, otherwise estimate
                    if eval_count > 0 or prompt_eval_count > 0:
                        total_tokens = eval_count + prompt_eval_count
                        self.metrics.total_tokens += total_tokens
                    else:
                        # Fallback estimation
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
        except asyncio.TimeoutError as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"Ollama API timeout: {e}")
            return json.dumps({"error": "TimeoutError", "message": f"Request timed out after 120s. Model may be too large or server overloaded."})
        except aiohttp.ServerTimeoutError as e:
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            logger.error(f"Ollama API server timeout: {e}")
            return json.dumps({"error": "ServerTimeoutError", "message": f"Server timeout reading response. Model may need more time to generate."})
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
            "fallback_url": getattr(self, 'fallback_url', None),
            "using_fallback": getattr(self, 'using_fallback', False),
            "rate_limits": {
                "rpm": self.rate_limits.requests_per_minute,
                "tpm": self.rate_limits.tokens_per_minute,
            },
            "rate_limiter_metrics": self.rate_limiter.get_metrics()
        }
    
    def switch_to_fallback(self):
        """Switch to fallback URL (localhost CPU server)"""
        if hasattr(self, 'fallback_url') and self.fallback_url and not self.using_fallback:
            old_url = self.base_url
            self.base_url = self.fallback_url.rstrip('/').replace('/api', '')
            self.api_url = f"{self.base_url}/api"
            self.using_fallback = True
            # Reset HTTP session to use new URL
            if self.http_session and not self.http_session.closed:
                asyncio.create_task(self.http_session.close())
            self.http_session = None
            logger.warning(f"⚠️ Switched to fallback Ollama server: {old_url} → {self.base_url} (CPU)")
            return True
        return False
    
    def switch_to_primary(self):
        """Switch back to primary URL (GPU server)"""
        if self.using_fallback:
            primary_url = self.config.get("llm.ollama.base_url", "http://10.0.0.155:18080")
            old_url = self.base_url
            self.base_url = primary_url.rstrip('/').replace('/api', '')
            self.api_url = f"{self.base_url}/api"
            self.using_fallback = False
            # Reset HTTP session to use new URL
            if self.http_session and not self.http_session.closed:
                asyncio.create_task(self.http_session.close())
            self.http_session = None
            logger.info(f"✓ Switched back to primary Ollama server: {old_url} → {self.base_url} (GPU)")
            return True
        return False
    
    async def test_connection(self, try_fallback: bool = True) -> Dict[str, Any]:
        """Test API connection with detailed feedback and optional fallback"""
        result = await self._test_single_connection()
        
        # If primary failed and fallback is enabled, try fallback
        if not result.get("success") and try_fallback and not self.using_fallback:
            logger.warning(f"Primary Ollama server ({self.base_url}) unreachable, trying fallback...")
            if self.switch_to_fallback():
                fallback_result = await self._test_single_connection()
                if fallback_result.get("success"):
                    fallback_result["switched_to_fallback"] = True
                    fallback_result["primary_error"] = result.get("error")
                    return fallback_result
                else:
                    # Both failed, switch back to primary for next attempt
                    self.switch_to_primary()
                    result["fallback_also_failed"] = True
                    result["fallback_error"] = fallback_result.get("error")
        
        return result
    
    async def _test_single_connection(self) -> Dict[str, Any]:
        """Test connection to current URL"""
        try:
            session = await self._get_session()
            
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
                            "using_fallback": self.using_fallback,
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
                    "error": f"Cannot connect to Ollama server at {self.base_url}. Error: {str(e)}",
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


