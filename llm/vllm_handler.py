# mindx/llm/vllm_handler.py
"""
LLM Handler for vLLM — production inference server.
Uses vLLM's OpenAI-compatible API (/v1/chat/completions, /v1/completions).

vLLM advantages over Ollama for production:
  - PagedAttention (efficient GPU memory)
  - Continuous batching (concurrent agent requests)
  - Tensor/pipeline parallelism (multi-GPU)
  - Speculative decoding, prefix caching

Serves as PRIMARY local inference; Ollama remains as CPU/dev fallback.

Cloud fallback: when local vLLM is unreachable, falls back to Ollama cloud
(https://ollama.com/v1/) which speaks the same OpenAI-compatible protocol.
Cloud access uses OllamaCloudTool's rate limiter (50 req/session, adaptive
pacing) — realistic API consumption, not shotgunning.
"""
import json
import os
import time
from typing import Dict, Any, Optional, List

try:
    import aiohttp
except ImportError:
    aiohttp = None

from utils.logging_config import get_logger
from .llm_interface import LLMHandlerInterface

logger = get_logger(__name__)


class VLLMHandler(LLMHandlerInterface):
    """
    Handles interactions with a vLLM server via its OpenAI-compatible API.
    """

    # Class-level negative cache: when no vLLM server answers, every handler instance
    # stops dialing the local legs until the cooldown lapses (see generate_text).
    _down_until: float = 0.0
    _DOWN_COOLDOWN_S: float = float(os.getenv("MINDX_VLLM_DOWN_COOLDOWN_S", "300"))

    def __init__(
        self,
        model_name_for_api: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        super().__init__("vllm", model_name_for_api, api_key, base_url)

        # SELF-CALL GUARD (2026-07-11). vLLM's OpenAI server conventionally listens on
        # :8000 — but that is ALSO mindX's own FastAPI port. On any node where the backend
        # serves :8000, the old default made every "vLLM" call POST to mindX ITSELF, where
        # the api_access_gate answered 401 auth_required. Result on the live VPS: vllm sits
        # FIRST in default_provider_preference_order, so every inference burned a round-trip
        # into our own gate, logged a WARNING, and cascaded to "All model attempts failed"
        # in AGInt. The embed leg already used :8001 (VLLM_EMBED_URL) — this aligns the
        # completion leg with it, and refuses any base_url that points back at ourselves.
        _self_port = os.getenv("MINDX_BACKEND_PORT", "8000")
        self.api_base_url = (
            self.base_url
            or os.getenv("VLLM_BASE_URL")
            or "http://localhost:8001"
        )
        self.api_base_url = self.api_base_url.rstrip("/")
        if f":{_self_port}" in self.api_base_url and "localhost" in self.api_base_url or \
           f":{_self_port}" in self.api_base_url and "127.0.0.1" in self.api_base_url:
            logger.warning(
                "vLLM base_url %s points at mindX's OWN backend port (%s) — a self-call that "
                "the access gate answers with 401. Redirecting to :8001 (the vLLM convention "
                "used by VLLM_EMBED_URL). Set VLLM_BASE_URL explicitly to override.",
                self.api_base_url, _self_port,
            )
            self.api_base_url = self.api_base_url.replace(f":{_self_port}", ":8001")

        # vLLM supports optional API key via --api-key flag
        self.vllm_api_key = (
            self.api_key
            or os.getenv("VLLM_API_KEY")
            or "EMPTY"
        )

        self._session: Optional[aiohttp.ClientSession] = None

        # Ollama cloud fallback — same protocol, Bearer auth
        self.cloud_base_url = os.getenv("OLLAMA_CLOUD_URL", "https://ollama.com").rstrip("/")
        self.cloud_api_key = os.getenv("OLLAMA_API_KEY", "")
        self._using_cloud = False  # True when currently falling back to cloud
        self._cloud_rate_limiter = None  # Lazy-initialized from OllamaCloudTool

        logger.info(
            f"VLLMHandler initialized: base={self.api_base_url}, "
            f"cloud_fallback={'available' if self.cloud_api_key else 'no API key'}, "
            f"model={self.model_name_for_api}"
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                json_serialize=json.dumps,
                timeout=aiohttp.ClientTimeout(total=300),
            )
        return self._session

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.vllm_api_key and self.vllm_api_key != "EMPTY":
            h["Authorization"] = f"Bearer {self.vllm_api_key}"
        return h

    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,  # handler defaults to self.model_name_for_api when omitted
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        json_mode: Optional[bool] = False,
        **kwargs: Any,
    ) -> Optional[str]:
        """
        Generate text using vLLM's OpenAI-compatible /v1/chat/completions.
        Falls back to /v1/completions if chat endpoint fails.
        """
        if not model:
            model = self.model_name_for_api or "default"
        if not aiohttp:
            return "Error: aiohttp not installed for VLLMHandler."

        session = await self._get_session()

        # Enforce rate limiting if configured
        if self.rate_limiter and not await self.rate_limiter.wait():
            logger.warning(f"VLLMHandler: Rate limiter retries exhausted for '{model}'")
            return None

        # NEGATIVE CACHE (2026-07-11): when no vLLM server is listening, both local legs
        # dial a refused socket on EVERY inference — two failed round-trips + two WARNINGs
        # per call, forever (26 in 4 min on the live VPS). A dead endpoint is skipped for
        # _DOWN_COOLDOWN_S; the first call after the cooldown probes again, so a vLLM server
        # coming up is picked back up within a cooldown window with no operator action.
        local_dark = time.monotonic() < VLLMHandler._down_until
        result = None
        if not local_dark:
            # Try local vLLM first (primary — free, fast, no rate limits)
            result = await self._try_chat_completions(
                session, prompt, model, max_tokens, temperature, json_mode, **kwargs
            )
        if result is not None:
            self._using_cloud = False
            VLLMHandler._down_until = 0.0   # alive → clear the cache
            return result

        # Fallback to raw completions endpoint (still local)
        if not local_dark:
            result = await self._try_completions(
                session, prompt, model, max_tokens, temperature, json_mode, **kwargs
            )
        if result is not None:
            self._using_cloud = False
            VLLMHandler._down_until = 0.0
            return result
        if not local_dark:
            # both local legs failed just now → mark dark and stop dialing for a while
            VLLMHandler._down_until = time.monotonic() + VLLMHandler._DOWN_COOLDOWN_S
            logger.info(
                "vLLM local (%s) is not serving — skipping the local legs for %.0fs "
                "(auto-reprobes after the cooldown; cloud fallback continues).",
                self.api_base_url, VLLMHandler._DOWN_COOLDOWN_S,
            )

        # Local vLLM unreachable — fall back to Ollama cloud (same protocol)
        return await self._try_cloud_fallback(
            session, prompt, model, max_tokens, temperature, json_mode, **kwargs
        )

    async def _try_chat_completions(
        self,
        session: aiohttp.ClientSession,
        prompt: str,
        model: str,
        max_tokens: Optional[int],
        temperature: Optional[float],
        json_mode: Optional[bool],
        **kwargs,
    ) -> Optional[str]:
        endpoint = f"{self.api_base_url}/v1/chat/completions"

        # Build messages from prompt
        messages = kwargs.get("messages")
        if not messages:
            system_prompt = kwargs.get("system_prompt")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Pass through stop sequences
        stop = kwargs.get("stop_sequences") or kwargs.get("stop")
        if stop:
            payload["stop"] = stop

        # vLLM-specific extras (top_k, repetition_penalty, etc.)
        extra_body = kwargs.get("extra_body")
        if extra_body and isinstance(extra_body, dict):
            payload.update(extra_body)

        try:
            async with session.post(
                endpoint, json=payload, headers=self._headers()
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.warning(
                        f"vLLM chat completions error ({resp.status}): "
                        f"{error_text[:300]}"
                    )
                    return None

                data = await resp.json(loads=json.loads)
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                    if content:
                        usage = data.get("usage", {})
                        logger.debug(
                            f"vLLM response: {len(content)} chars, "
                            f"tokens={usage.get('total_tokens', '?')}"
                        )
                        return content
                return None
        except aiohttp.ClientError as e:
            logger.warning(f"vLLM connection error (chat): {e}")
            return None
        except Exception as e:
            logger.error(f"vLLM unexpected error (chat): {e}", exc_info=True)
            return None

    async def _try_completions(
        self,
        session: aiohttp.ClientSession,
        prompt: str,
        model: str,
        max_tokens: Optional[int],
        temperature: Optional[float],
        json_mode: Optional[bool],
        **kwargs,
    ) -> Optional[str]:
        endpoint = f"{self.api_base_url}/v1/completions"

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature

        stop = kwargs.get("stop_sequences") or kwargs.get("stop")
        if stop:
            payload["stop"] = stop

        try:
            async with session.post(
                endpoint, json=payload, headers=self._headers()
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.warning(
                        f"vLLM completions error ({resp.status}): "
                        f"{error_text[:300]}"
                    )
                    return None

                data = await resp.json(loads=json.loads)
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("text", "")
                return None
        except aiohttp.ClientError as e:
            logger.warning(f"vLLM connection error (completions): {e}")
            return None
        except Exception as e:
            logger.error(
                f"vLLM unexpected error (completions): {e}", exc_info=True
            )
            return None

    async def list_models(self) -> Optional[List[Dict[str, Any]]]:
        """List models served by vLLM via /v1/models."""
        if not aiohttp:
            return None
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.api_base_url}/v1/models", headers=self._headers()
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(loads=json.loads)
                    return data.get("data", [])
                return None
        except Exception as e:
            logger.debug(f"vLLM list_models failed: {e}")
            return None

    async def health_check(self) -> bool:
        """Check if vLLM server is reachable."""
        if not aiohttp:
            return False
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.api_base_url}/health",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status == 200
        except Exception:
            # Try /v1/models as fallback health check
            try:
                async with session.get(
                    f"{self.api_base_url}/v1/models",
                    headers=self._headers(),
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as resp:
                    return resp.status == 200
            except Exception:
                return False

    async def generate_embeddings(
        self, text: str, model: Optional[str] = None
    ) -> Optional[List[float]]:
        """Generate embeddings via vLLM /v1/embeddings endpoint."""
        if not aiohttp:
            return None
        session = await self._get_session()
        try:
            payload = {
                "model": model or self.model_name_for_api or "default",
                "input": text[:8000],
            }
            async with session.post(
                f"{self.api_base_url}/v1/embeddings",
                json=payload,
                headers=self._headers(),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(loads=json.loads)
                    emb_data = data.get("data", [])
                    if emb_data and "embedding" in emb_data[0]:
                        return emb_data[0]["embedding"]
                return None
        except Exception as e:
            logger.debug(f"vLLM embeddings failed: {e}")
            return None

    # ── Ollama Cloud Fallback ──────────────────────────────────────────

    async def _try_cloud_fallback(
        self,
        session: aiohttp.ClientSession,
        prompt: str,
        model: str,
        max_tokens: Optional[int],
        temperature: Optional[float],
        json_mode: Optional[bool],
        **kwargs,
    ) -> Optional[str]:
        """Fall back to Ollama cloud when local vLLM is unreachable.

        Same OpenAI-compatible protocol (/v1/chat/completions), Bearer auth.
        Uses OllamaCloudTool's rate limiter for realistic API consumption.
        """
        if not self.cloud_api_key:
            return None  # No API key — can't use cloud

        # Enforce cloud rate limits (borrow from OllamaCloudTool)
        if not self._cloud_rate_limiter:
            try:
                from tools.cloud.ollama_cloud_tool import CloudRateLimiter
                self._cloud_rate_limiter = CloudRateLimiter()
            except ImportError:
                pass

        if self._cloud_rate_limiter:
            allowed = await self._cloud_rate_limiter.acquire()
            if not allowed:
                logger.debug("VLLMHandler: cloud rate limiter blocked request")
                return None

        cloud_endpoint = f"{self.cloud_base_url}/v1/chat/completions"
        cloud_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.cloud_api_key}",
        }

        # Build messages
        messages = kwargs.get("messages")
        if not messages:
            system_prompt = kwargs.get("system_prompt")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with session.post(
                cloud_endpoint, json=payload, headers=cloud_headers,
                timeout=aiohttp.ClientTimeout(total=60),
            ) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    logger.debug(f"VLLMHandler cloud fallback error ({resp.status}): {error_text[:200]}")
                    return None

                data = await resp.json(loads=json.loads)

                # OpenAI-compatible format (Ollama /v1/ returns this)
                choices = data.get("choices", [])
                if choices:
                    message = choices[0].get("message", {})
                    content = message.get("content", "")
                    if content:
                        self._using_cloud = True
                        usage = data.get("usage", {})
                        logger.info(
                            f"VLLMHandler: cloud fallback succeeded — "
                            f"model={model}, tokens={usage.get('total_tokens', '?')}"
                        )
                        return content
                return None
        except aiohttp.ClientError as e:
            logger.debug(f"VLLMHandler cloud fallback connection error: {e}")
            return None
        except Exception as e:
            logger.debug(f"VLLMHandler cloud fallback error: {e}")
            return None

    async def list_cloud_models(self) -> Optional[List[Dict[str, Any]]]:
        """List models available at Ollama cloud via /v1/models."""
        if not self.cloud_api_key or not aiohttp:
            return None
        session = await self._get_session()
        cloud_headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.cloud_api_key}",
        }
        try:
            async with session.get(
                f"{self.cloud_base_url}/v1/models",
                headers=cloud_headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    data = await resp.json(loads=json.loads)
                    models = data.get("data", data.get("models", []))
                    logger.info(f"VLLMHandler: {len(models)} cloud models available")
                    return models
                return None
        except Exception as e:
            logger.debug(f"VLLMHandler cloud model listing failed: {e}")
            return None

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
