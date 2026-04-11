"""
OllamaCloudTool — Cloud Inference as a First-Class mindX Tool

Gives any mindX agent direct access to Ollama cloud (24/7/365 GPU inference).
Supports chat, generate, embed, model discovery, web search, web fetch.

Access methods (auto-selected):
  1. Local proxy: localhost:11434 with -cloud models (daemon proxies to ollama.com)
  2. Direct API: https://ollama.com with Bearer token (OLLAMA_API_KEY)

Branch-ready: works with minimal dependencies on peripheral nodes.
Required: aiohttp, BaseTool, Config, get_logger
Optional: PrecisionMetricsTracker, InferenceDiscovery (graceful degradation)

Author: Professor Codephreak
"""

import asyncio
import json
import os
import time
import random
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False

from agents.core.bdi_agent import BaseTool

try:
    from utils.logging_config import get_logger
except ImportError:
    import logging
    def get_logger(name):
        return logging.getLogger(name)

try:
    from utils.config import Config, PROJECT_ROOT
except ImportError:
    class Config:
        def get(self, key, default=None):
            return default
    PROJECT_ROOT = Path(".")

try:
    from llm.precision_metrics import PrecisionMetricsTracker, OllamaResponseMetrics
    PRECISION_AVAILABLE = True
except ImportError:
    PRECISION_AVAILABLE = False

getcontext().prec = 36

NANO_TO_SEC = Decimal("1e-9")
NANO_TO_MS = Decimal("1e-6")
SUBTOKEN_FACTOR = Decimal(10) ** 18

logger = get_logger("tool.OllamaCloudTool")


# ---------------------------------------------------------------------------
# Embedded Rate Limiter (branch-ready — no external imports from docs/)
# ---------------------------------------------------------------------------

@dataclass
class CloudQuotaTracker:
    """Track cloud usage against free tier limits. Actual counts only."""

    max_requests_per_session: int = 50
    max_requests_per_week: int = 500
    max_tokens_per_session: int = 100_000

    session_requests: int = 0
    session_tokens: int = 0
    weekly_requests: int = 0

    session_start: float = field(default_factory=time.time)
    week_start: float = field(default_factory=time.time)
    last_request: float = 0.0

    consecutive_429s: int = 0
    backoff_until: float = 0.0

    def _reset_session_if_needed(self):
        if time.time() - self.session_start > 5 * 3600:
            self.session_requests = 0
            self.session_tokens = 0
            self.session_start = time.time()
            self.consecutive_429s = 0

    def _reset_week_if_needed(self):
        if time.time() - self.week_start > 7 * 86400:
            self.weekly_requests = 0
            self.week_start = time.time()

    def can_make_request(self) -> Tuple[bool, str]:
        self._reset_session_if_needed()
        self._reset_week_if_needed()
        now = time.time()
        if now < self.backoff_until:
            return False, f"Backing off for {self.backoff_until - now:.0f}s after rate limit"
        if self.session_requests >= self.max_requests_per_session * 0.9:
            remaining = 5 * 3600 - (now - self.session_start)
            return False, f"Session quota near limit. Resets in {remaining / 60:.0f}m"
        if self.weekly_requests >= self.max_requests_per_week * 0.9:
            remaining = 7 * 86400 - (now - self.week_start)
            return False, f"Weekly quota near limit. Resets in {remaining / 3600:.0f}h"
        return True, "OK"

    def record_request(self, eval_count: int = 0, prompt_eval_count: int = 0):
        self.session_requests += 1
        self.session_tokens += eval_count + prompt_eval_count
        self.weekly_requests += 1
        self.last_request = time.time()
        self.consecutive_429s = 0

    def record_rate_limit(self):
        self.consecutive_429s += 1
        backoff = min(30 * (2 ** (self.consecutive_429s - 1)), 600)
        jitter = backoff * random.uniform(-0.2, 0.2)
        self.backoff_until = time.time() + backoff + jitter

    @property
    def utilization(self) -> float:
        self._reset_session_if_needed()
        self._reset_week_if_needed()
        return max(
            self.session_requests / max(self.max_requests_per_session, 1),
            self.weekly_requests / max(self.max_requests_per_week, 1),
        )


class CloudRateLimiter:
    """Adaptive rate limiter for Ollama cloud free tier."""

    def __init__(self):
        self.quota = CloudQuotaTracker()
        self._lock = asyncio.Lock()

    def _interval(self) -> float:
        u = self.quota.utilization
        if u < 0.3:
            return 3.0
        elif u < 0.5:
            return 6.0
        elif u < 0.8:
            return 15.0
        return 30.0

    async def acquire(self) -> Tuple[bool, str]:
        async with self._lock:
            allowed, reason = self.quota.can_make_request()
            if not allowed:
                return False, reason
            interval = self._interval()
            elapsed = time.time() - self.quota.last_request
            if elapsed < interval and self.quota.last_request > 0:
                wait = interval - elapsed + random.uniform(0, interval * 0.3)
                await asyncio.sleep(wait)
            return True, "OK"

    @property
    def status(self) -> dict:
        return {
            "session_requests": self.quota.session_requests,
            "session_max": self.quota.max_requests_per_session,
            "session_tokens": self.quota.session_tokens,
            "weekly_requests": self.quota.weekly_requests,
            "weekly_max": self.quota.max_requests_per_week,
            "utilization": f"{self.quota.utilization:.1%}",
            "interval_s": f"{self._interval():.1f}",
            "backing_off": time.time() < self.quota.backoff_until,
        }


# ---------------------------------------------------------------------------
# OllamaCloudTool
# ---------------------------------------------------------------------------

class OllamaCloudTool(BaseTool):
    """
    Cloud inference via Ollama — chat, generate, embed, model discovery.

    Provides any mindX agent with access to 120B+ parameter models via
    Ollama cloud, with adaptive rate limiting, precision metrics (18dp),
    quota tracking, and graceful local fallback.

    Branch-ready: works on peripheral nodes with minimal dependencies.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        llm_handler: Optional[Any] = None,
        bdi_agent_ref: Optional[Any] = None,
        **kwargs: Any,
    ):
        super().__init__(config=config, llm_handler=llm_handler, bdi_agent_ref=bdi_agent_ref, **kwargs)

        # Access configuration
        self._api_key = os.getenv("OLLAMA_API_KEY", "")
        self._local_url = os.getenv("MINDX_LLM__OLLAMA__BASE_URL", "http://localhost:11434")
        self._fallback_url = "http://localhost:11434"  # Always try localhost as fallback
        self._cloud_url = "https://ollama.com"
        self._access_mode = "auto"  # "auto", "local_proxy", "direct"

        # HTTP session (created lazily)
        self._session: Optional[aiohttp.ClientSession] = None
        self._timeout = aiohttp.ClientTimeout(total=180, connect=15, sock_read=120)

        # Rate limiting
        self._rate_limiter = CloudRateLimiter()

        # Precision metrics (optional)
        self._precision_tracker = None
        if PRECISION_AVAILABLE:
            try:
                self._precision_tracker = PrecisionMetricsTracker(
                    persistence_path="data/metrics/cloud_precision_metrics.json"
                )
            except Exception:
                pass

        # Model catalog cache
        self._catalog: List[str] = []
        self._catalog_details: List[dict] = []
        self._catalog_last_refresh: float = 0.0
        self._catalog_ttl: int = 300  # 5 minutes

        # Conversation history
        self._conversations: Dict[str, List[Dict[str, str]]] = defaultdict(list)
        self._conversations_path = Path(
            getattr(self.config, '_project_root', PROJECT_ROOT)
            if hasattr(self.config, '_project_root')
            else PROJECT_ROOT
        ) / "data" / "cloud_chat_history.json"
        self._load_conversations()

        # Discovery registered flag
        self._discovery_registered = False

        self.logger.info(
            f"OllamaCloudTool initialized — local: {self._local_url}, "
            f"cloud: {self._cloud_url}, api_key: {'set' if self._api_key else 'not set'}"
        )

    # -----------------------------------------------------------------------
    # BaseTool interface
    # -----------------------------------------------------------------------

    async def execute(self, operation: str = "", **kwargs) -> Dict[str, Any]:
        """Dispatch to operation handler. Returns dict with 'success' key."""
        if not AIOHTTP_AVAILABLE:
            return {"success": False, "error": "aiohttp not installed"}

        # Lazy init: register with InferenceDiscovery on first call
        if not self._discovery_registered:
            await self._register_with_discovery()
            self._discovery_registered = True

        handlers = {
            "chat": self._chat,
            "generate": self._generate,
            "embed": self._embed,
            "list_models": self._list_models,
            "show_model": self._show_model,
            "web_search": self._web_search,
            "web_fetch": self._web_fetch,
        }

        if operation == "get_metrics":
            return {"success": True, "metrics": self._get_metrics()}
        if operation == "get_status":
            return {"success": True, "status": self._get_status()}

        handler = handlers.get(operation)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown operation: '{operation}'",
                "available": list(handlers.keys()) + ["get_metrics", "get_status"],
            }

        try:
            return await handler(**kwargs)
        except Exception as e:
            self.logger.error(f"OllamaCloudTool.{operation} failed: {e}", exc_info=True)
            return {"success": False, "error": str(e), "operation": operation}

    def get_schema(self) -> Dict[str, Any]:
        return {
            "name": "ollama_cloud_tool",
            "description": (
                "Cloud inference via Ollama — chat, generate, embed, model discovery. "
                "Provides any mindX agent with access to 120B+ parameter models via "
                "Ollama cloud, with rate limiting, quota tracking, and local fallback."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "The operation to perform",
                        "enum": [
                            "chat", "generate", "embed",
                            "list_models", "show_model",
                            "web_search", "web_fetch",
                            "get_metrics", "get_status",
                        ],
                    },
                    "model": {"type": "string", "description": "Model name (e.g., deepseek-v3.2, gpt-oss:120b-cloud)"},
                    "message": {"type": "string", "description": "User message (for chat)"},
                    "prompt": {"type": "string", "description": "Prompt text (for generate)"},
                    "conversation_id": {"type": "string", "description": "Conversation ID for multi-turn chat"},
                    "system_prompt": {"type": "string", "description": "System prompt override"},
                },
                "required": ["operation"],
            },
        }

    # -----------------------------------------------------------------------
    # Operations
    # -----------------------------------------------------------------------

    async def _chat(
        self,
        model: str = "deepseek-v3.2",
        message: str = "",
        conversation_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        think: Optional[bool] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Multi-turn chat with a cloud model."""
        allowed, reason = await self._rate_limiter.acquire()
        if not allowed:
            return {"success": False, "error": f"Rate limited: {reason}", "rate_limited": True}

        conv_id = conversation_id or model
        messages = self._get_conversation(conv_id)

        if system_prompt and not any(m.get("role") == "system" for m in messages):
            messages.insert(0, {"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": message})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }
        if think is not None:
            payload["think"] = think

        data = await self._make_request("/api/chat", payload)
        if not data:
            return {"success": False, "error": "No response from cloud or local proxy"}

        if "error" in data:
            return {"success": False, "error": data["error"]}

        content = data.get("message", {}).get("content", "")
        thinking = data.get("message", {}).get("thinking", "")
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        total_duration_ns = data.get("total_duration", 0)
        eval_duration_ns = data.get("eval_duration", 0)

        # tok/s: prefer eval_duration (local), fall back to total_duration (cloud proxy)
        if eval_duration_ns > 0:
            tps = Decimal(str(eval_count)) / (Decimal(str(eval_duration_ns)) * NANO_TO_SEC)
        elif total_duration_ns > 0 and eval_count > 0:
            tps = Decimal(str(eval_count)) / (Decimal(str(total_duration_ns)) * NANO_TO_SEC)
        else:
            tps = Decimal("0")

        # Record metrics
        self._rate_limiter.quota.record_request(eval_count, prompt_eval_count)
        self._record_precision_metrics(data, model)

        # Update conversation history
        self._append_to_conversation(conv_id, "user", message)
        self._append_to_conversation(conv_id, "assistant", content)

        result = {
            "success": True,
            "content": content,
            "model": model,
            "conversation_id": conv_id,
            "eval_count": eval_count,
            "prompt_eval_count": prompt_eval_count,
            "total_tokens": eval_count + prompt_eval_count,
            "tokens_per_sec": str(tps.quantize(Decimal("1e-18"))),
            "total_duration_ns": total_duration_ns,
            "total_ms": str((Decimal(str(total_duration_ns)) * NANO_TO_MS).quantize(Decimal("1e-6"))),
            "done_reason": data.get("done_reason", ""),
        }
        if thinking:
            result["thinking"] = thinking
        return result

    async def _generate(
        self,
        model: str = "deepseek-v3.2",
        prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        think: Optional[bool] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Single-shot text generation."""
        allowed, reason = await self._rate_limiter.acquire()
        if not allowed:
            return {"success": False, "error": f"Rate limited: {reason}", "rate_limited": True}

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
        }
        if think is not None:
            payload["think"] = think

        data = await self._make_request("/api/generate", payload)
        if not data:
            return {"success": False, "error": "No response from cloud or local proxy"}
        if "error" in data:
            return {"success": False, "error": data["error"]}

        content = data.get("response", "")
        eval_count = data.get("eval_count", 0)
        prompt_eval_count = data.get("prompt_eval_count", 0)
        total_duration_ns = data.get("total_duration", 0)
        eval_duration_ns = data.get("eval_duration", 0)

        if eval_duration_ns > 0:
            tps = Decimal(str(eval_count)) / (Decimal(str(eval_duration_ns)) * NANO_TO_SEC)
        elif total_duration_ns > 0 and eval_count > 0:
            tps = Decimal(str(eval_count)) / (Decimal(str(total_duration_ns)) * NANO_TO_SEC)
        else:
            tps = Decimal("0")

        self._rate_limiter.quota.record_request(eval_count, prompt_eval_count)
        self._record_precision_metrics(data, model)

        return {
            "success": True,
            "content": content,
            "model": model,
            "eval_count": eval_count,
            "prompt_eval_count": prompt_eval_count,
            "total_tokens": eval_count + prompt_eval_count,
            "tokens_per_sec": str(tps.quantize(Decimal("1e-18"))),
            "total_duration_ns": total_duration_ns,
        }

    async def _embed(
        self,
        model: str = "mxbai-embed-large",
        input: str = "",
        **kwargs,
    ) -> Dict[str, Any]:
        """Generate vector embeddings."""
        allowed, reason = await self._rate_limiter.acquire()
        if not allowed:
            return {"success": False, "error": f"Rate limited: {reason}"}

        texts = input if isinstance(input, list) else [input]
        payload = {"model": model, "input": texts}

        data = await self._make_request("/api/embed", payload)
        if not data:
            return {"success": False, "error": "No response"}
        if "error" in data:
            return {"success": False, "error": data["error"]}

        self._rate_limiter.quota.record_request(0, data.get("prompt_eval_count", 0))

        return {
            "success": True,
            "embeddings": data.get("embeddings", []),
            "model": model,
            "dimensions": len(data["embeddings"][0]) if data.get("embeddings") else 0,
        }

    async def _list_models(self, force_refresh: bool = False, **kwargs) -> Dict[str, Any]:
        """List available cloud models. No rate limit — catalog is public."""
        catalog = await self._refresh_catalog(force=force_refresh)
        return {
            "success": True,
            "models": catalog,
            "count": len(catalog),
            "source": "cache" if not force_refresh else "fresh",
        }

    async def _show_model(self, model: str = "", **kwargs) -> Dict[str, Any]:
        """Get model details and capabilities."""
        if not model:
            return {"success": False, "error": "model parameter required"}

        payload = {"model": model}
        data = await self._make_request("/api/show", payload)
        if not data:
            return {"success": False, "error": "No response"}
        if "error" in data:
            return {"success": False, "error": data["error"]}

        return {
            "success": True,
            "model": model,
            "capabilities": data.get("capabilities", []),
            "details": data.get("details", {}),
            "parameters": data.get("parameters", ""),
            "template": data.get("template", ""),
        }

    async def _web_search(self, query: str = "", max_results: int = 5, **kwargs) -> Dict[str, Any]:
        """Search the web via Ollama's web search API. Requires API key."""
        if not self._api_key:
            return {"success": False, "error": "OLLAMA_API_KEY required for web_search"}

        session = await self._ensure_session()
        try:
            async with session.post(
                f"{self._cloud_url}/api/web_search",
                json={"query": query, "max_results": min(max_results, 10)},
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {"success": True, "results": data.get("results", []), "query": query}
                return {"success": False, "error": f"HTTP {resp.status}", "query": query}
        except Exception as e:
            return {"success": False, "error": str(e), "query": query}

    async def _web_fetch(self, url: str = "", **kwargs) -> Dict[str, Any]:
        """Fetch URL content via Ollama's web fetch API. Requires API key."""
        if not self._api_key:
            return {"success": False, "error": "OLLAMA_API_KEY required for web_fetch"}

        session = await self._ensure_session()
        try:
            async with session.post(
                f"{self._cloud_url}/api/web_fetch",
                json={"url": url},
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "title": data.get("title", ""),
                        "content": data.get("content", ""),
                        "links": data.get("links", []),
                    }
                return {"success": False, "error": f"HTTP {resp.status}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # -----------------------------------------------------------------------
    # HTTP Layer — Dual Access (local proxy + direct cloud)
    # -----------------------------------------------------------------------

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if not self._session or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
        return self._session

    async def _make_request(self, endpoint: str, payload: dict, method: str = "POST") -> Optional[dict]:
        """Route request through local proxy or direct cloud API."""
        if self._access_mode == "local_proxy":
            return await self._try_local_proxy(endpoint, payload, method)
        elif self._access_mode == "direct":
            return await self._try_direct_cloud(endpoint, payload, method)
        else:
            # Auto: try local first, fall back to direct
            result = await self._try_local_proxy(endpoint, payload, method)
            if result is not None:
                return result
            return await self._try_direct_cloud(endpoint, payload, method)

    async def _try_local_proxy(self, endpoint: str, payload: dict, method: str = "POST") -> Optional[dict]:
        """Try local Ollama daemon (proxies -cloud models to ollama.com).
        Tries primary URL first, then localhost fallback (same pattern as OllamaAPI)."""
        urls = [self._local_url]
        if self._fallback_url and self._fallback_url != self._local_url:
            urls.append(self._fallback_url)

        session = await self._ensure_session()
        for url_base in urls:
            url = f"{url_base}{endpoint}"
            try:
                if method == "GET":
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                        if resp.status == 200:
                            return await resp.json()
                else:
                    async with session.post(url, json=payload) as resp:
                        if resp.status == 200:
                            return await resp.json()
                        elif resp.status == 404:
                            return None  # Model not found — try next URL or fall through
                        else:
                            body = await resp.text()
                            return {"error": f"Local proxy HTTP {resp.status}: {body[:200]}"}
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError, OSError):
                continue  # Try next URL
            except Exception as e:
                self.logger.debug(f"Local proxy error at {url_base}: {e}")
                continue

        return None  # All local URLs exhausted

    async def _try_direct_cloud(self, endpoint: str, payload: dict, method: str = "POST") -> Optional[dict]:
        """Try direct cloud API at ollama.com."""
        # /api/tags is public, everything else needs a key
        needs_auth = endpoint != "/api/tags"
        if needs_auth and not self._api_key:
            return {"error": "OLLAMA_API_KEY required for direct cloud access (or pull model with -cloud suffix for local proxy)"}

        session = await self._ensure_session()
        url = f"{self._cloud_url}{endpoint}"
        headers: Dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            if method == "GET":
                async with session.get(url, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 401:
                        return {"error": "Unauthorized — check OLLAMA_API_KEY"}
                    elif resp.status == 429:
                        self._rate_limiter.quota.record_rate_limit()
                        return {"error": "Rate limited by Ollama cloud"}
                    return None
            else:
                async with session.post(url, json=payload, headers=headers) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status == 401:
                        return {"error": "Unauthorized — check OLLAMA_API_KEY"}
                    elif resp.status == 429:
                        self._rate_limiter.quota.record_rate_limit()
                        return {"error": "Rate limited by Ollama cloud"}
                    else:
                        body = await resp.text()
                        return {"error": f"Cloud HTTP {resp.status}: {body[:200]}"}
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError) as e:
            return {"error": f"Cannot reach Ollama cloud: {e}"}
        except Exception as e:
            self.logger.debug(f"Direct cloud error: {e}")
            return {"error": str(e)}

    # -----------------------------------------------------------------------
    # Model Catalog
    # -----------------------------------------------------------------------

    async def _refresh_catalog(self, force: bool = False) -> List[str]:
        now = time.time()
        if not force and (now - self._catalog_last_refresh) < self._catalog_ttl and self._catalog:
            return self._catalog

        # Try local first (includes both local and cloud-pulled models)
        data = await self._try_local_proxy("/api/tags", {}, method="GET")
        if not data or "models" not in data:
            # Fall back to cloud catalog (public, no auth)
            data = await self._try_direct_cloud("/api/tags", {}, method="GET")

        if data and "models" in data:
            self._catalog_details = data["models"]
            self._catalog = [m["name"] for m in data["models"]]
            self._catalog_last_refresh = now

        return self._catalog

    # -----------------------------------------------------------------------
    # Conversation History
    # -----------------------------------------------------------------------

    def _get_conversation(self, conversation_id: str) -> List[Dict[str, str]]:
        return self._conversations[conversation_id].copy()

    def _append_to_conversation(self, conversation_id: str, role: str, content: str):
        self._conversations[conversation_id].append({"role": role, "content": content})
        msgs = self._conversations[conversation_id]
        if len(msgs) > 50:
            system = [m for m in msgs if m["role"] == "system"]
            non_system = [m for m in msgs if m["role"] != "system"]
            self._conversations[conversation_id] = system + non_system[-49:]
        self._save_conversations()

    def _clear_conversation(self, conversation_id: str):
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            self._save_conversations()

    def _save_conversations(self):
        try:
            self._conversations_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "sessions": dict(self._conversations),
                "last_saved": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }
            self._conversations_path.write_text(json.dumps(data, indent=2))
        except Exception:
            pass

    def _load_conversations(self):
        if self._conversations_path.exists():
            try:
                data = json.loads(self._conversations_path.read_text())
                for k, v in data.get("sessions", {}).items():
                    self._conversations[k] = v
            except Exception:
                pass

    # -----------------------------------------------------------------------
    # Precision Metrics
    # -----------------------------------------------------------------------

    def _record_precision_metrics(self, data: dict, model: str):
        if not self._precision_tracker:
            return
        try:
            response_metrics = OllamaResponseMetrics.from_api_response(data, model=model)
            self._precision_tracker.record(response_metrics)
        except Exception:
            pass

    def _get_metrics(self) -> dict:
        if self._precision_tracker:
            return self._precision_tracker.summary()
        return {"precision": "unavailable (PrecisionMetricsTracker not loaded)"}

    # -----------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------

    def _get_status(self) -> dict:
        return {
            "access_mode": self._access_mode,
            "local_url": self._local_url,
            "cloud_url": self._cloud_url,
            "api_key_set": bool(self._api_key),
            "catalog_size": len(self._catalog),
            "catalog_age_s": int(time.time() - self._catalog_last_refresh) if self._catalog_last_refresh else None,
            "conversations": len(self._conversations),
            "precision_available": PRECISION_AVAILABLE and self._precision_tracker is not None,
            "rate_limiter": self._rate_limiter.status,
        }

    # -----------------------------------------------------------------------
    # InferenceDiscovery Integration
    # -----------------------------------------------------------------------

    async def _register_with_discovery(self):
        try:
            from llm.inference_discovery import InferenceDiscovery, ProviderStatus
            discovery = await InferenceDiscovery.get_instance()
            if "ollama_cloud" in discovery.sources:
                source = discovery.sources["ollama_cloud"]
                try:
                    catalog = await self._refresh_catalog(force=True)
                    if catalog:
                        source.status = ProviderStatus.AVAILABLE
                        source.models = catalog[:20]
                        source.last_checked = time.time()
                        source.success_count += 1
                        self.logger.info(f"Registered with InferenceDiscovery: {len(catalog)} cloud models")
                except Exception:
                    pass
        except ImportError:
            pass  # Branch-ready: InferenceDiscovery may not exist

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    async def shutdown(self):
        if self._session and not self._session.closed:
            await self._session.close()
        self._save_conversations()
        if self._precision_tracker:
            self._precision_tracker._save()
        self.logger.info("OllamaCloudTool shutdown complete")
