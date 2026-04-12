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
"""
import json
import os
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

    def __init__(
        self,
        model_name_for_api: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ):
        super().__init__("vllm", model_name_for_api, api_key, base_url)

        self.api_base_url = (
            self.base_url
            or os.getenv("VLLM_BASE_URL")
            or "http://localhost:8000"
        )
        self.api_base_url = self.api_base_url.rstrip("/")

        # vLLM supports optional API key via --api-key flag
        self.vllm_api_key = (
            self.api_key
            or os.getenv("VLLM_API_KEY")
            or "EMPTY"
        )

        self._session: Optional[aiohttp.ClientSession] = None
        logger.info(
            f"VLLMHandler initialized: base={self.api_base_url}, "
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
        model: str,
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

        # Try chat completions first (preferred for instruction-tuned models)
        result = await self._try_chat_completions(
            session, prompt, model, max_tokens, temperature, json_mode, **kwargs
        )
        if result is not None:
            return result

        # Fallback to raw completions endpoint
        return await self._try_completions(
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

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
