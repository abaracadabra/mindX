"""LLM Handler for OpenRouter — universal OpenAI-compatible LLM backplane.

Posts to https://openrouter.ai/api/v1/chat/completions via aiohttp. Auth is a
single Bearer key from OPENROUTER_API_KEY (loaded from BANKON Vault by
mindx_backend_service.bankon_vault.credential_provider on startup).

This handler is what makes the mindx.self.improve selector's openrouter slugs
(e.g. 'inclusionai/ling-2.6-1t:free', 'openai/gpt-oss-120b:free') actually
routable. Before this handler existed, the selector picked openrouter slugs but
the request fell through to ollama_handler, which hung indefinitely on the
foreign model name. See docs/OPENROUTER_mindX.md for the full integration spec.

Free-first policy: callers should prefer ':free' slugs. Paid escalation is the
caller's decision (value > cost predicate from mindx.self.aware).

Key semantics for mindX:
- Reads OPENROUTER_API_KEY from process environment (vault-injected).
- Identifies mindX to OpenRouter via HTTP-Referer + X-Title headers (drives the
  rankings leaderboard and ties usage to mindx.pythai.net).
- 60s default request timeout; OpenRouter free models can stall under load.
- Logs the actually-used model + provider on every successful response (the
  selector picks a slug; OpenRouter may route to any of several upstream
  providers — both must be visible for regression triage).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from typing import Any, Dict, Optional

try:
    import aiohttp
except ImportError:  # pragma: no cover
    aiohttp = None  # type: ignore

from utils.logging_config import get_logger
from .llm_interface import LLMHandlerInterface

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER = "https://mindx.pythai.net"
OPENROUTER_TITLE = "mindX"


class OpenRouterHandler(LLMHandlerInterface):
    """OpenAI-compatible chat completions against OpenRouter."""

    def __init__(
        self,
        model_name_for_api: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        rate_limiter: Optional[Any] = None,
        config: Optional[Any] = None,
        execution_timeout_minutes: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            provider_name="openrouter",
            model_name_for_api=model_name_for_api,
            api_key=api_key or os.getenv("OPENROUTER_API_KEY"),
            base_url=base_url or OPENROUTER_BASE_URL,
            rate_limiter=rate_limiter,
            execution_timeout_minutes=execution_timeout_minutes,
            **kwargs,
        )
        self._session: Optional[aiohttp.ClientSession] = None
        if not self.api_key:
            logger.warning(
                "OpenRouterHandler initialized without OPENROUTER_API_KEY — "
                "calls will return None (graceful fallback)."
            )
        logger.info(
            f"OpenRouterHandler initialized for {self.base_url}. "
            f"Default model: {self.model_name_for_api or '(per-call)'}"
        )

    async def _get_session(self) -> "aiohttp.ClientSession":
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(json_serialize=json.dumps)
        return self._session

    async def generate_text(
        self,
        prompt: str,
        model: str,
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        json_mode: Optional[bool] = False,
        **kwargs: Any,
    ) -> Optional[str]:
        if not aiohttp:  # pragma: no cover
            logger.error("OpenRouterHandler: aiohttp not installed.")
            return None
        if not self.api_key:
            logger.warning("OpenRouterHandler: no API key — returning None for fallback.")
            return None
        if not model:
            logger.error("OpenRouterHandler: no model specified.")
            return None

        if self.rate_limiter and not await self.rate_limiter.wait():
            logger.warning(f"OpenRouterHandler: rate limiter exhausted for '{model}'")
            return None

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": OPENROUTER_REFERER,
            "X-Title": OPENROUTER_TITLE,
        }

        # Build OpenAI-compatible body. OpenRouter accepts both 'max_tokens' and
        # 'max_completion_tokens'; the latter is the post-2025 standard.
        body: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature if temperature is not None else 0.7,
        }
        if max_tokens and max_tokens > 0:
            body["max_completion_tokens"] = int(max_tokens)
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        # OpenRouter-only fields ride in the body alongside the OpenAI-standard
        # ones (we are not using the OpenAI SDK that strips unknowns).
        if "provider" in kwargs:
            body["provider"] = kwargs["provider"]
        if "models" in kwargs:
            body["models"] = kwargs["models"]
        if "stop_sequences" in kwargs and isinstance(kwargs["stop_sequences"], list):
            body["stop"] = kwargs["stop_sequences"]

        timeout_s = (self.execution_timeout_minutes or 1) * 60
        request_timeout = aiohttp.ClientTimeout(total=timeout_s, connect=10)

        t0 = time.monotonic()
        try:
            session = await self._get_session()
            async with session.post(url, json=body, headers=headers, timeout=request_timeout) as response:
                latency_ms = int((time.monotonic() - t0) * 1000)
                text = await response.text()

                if response.status != 200:
                    snippet = text[:300]
                    logger.warning(
                        f"OpenRouterHandler: {response.status} for model '{model}' "
                        f"({latency_ms}ms): {snippet}"
                    )
                    # 429 / 5xx → return None so caller can cascade to next provider
                    return None

                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    logger.warning(f"OpenRouterHandler: non-JSON response for '{model}': {text[:200]}")
                    return None

                # Standard OpenAI envelope.
                choices = data.get("choices") or []
                if not choices:
                    err = data.get("error") or {}
                    if err:
                        logger.warning(
                            f"OpenRouterHandler: API error for '{model}': "
                            f"{err.get('code')} {err.get('message')}"
                        )
                    return None

                msg = (choices[0] or {}).get("message") or {}
                content = msg.get("content")
                actual_model = data.get("model") or model
                actual_provider = data.get("provider") or "unknown"
                usage = data.get("usage") or {}

                logger.info(
                    f"OpenRouterHandler: ok model_requested={model} "
                    f"model_actual={actual_model} provider={actual_provider} "
                    f"in={usage.get('prompt_tokens', 0)} out={usage.get('completion_tokens', 0)} "
                    f"latency_ms={latency_ms}"
                )

                # Best-effort cost ledger — never blocks inference.
                try:
                    from agents import memory_pgvector as _mpg
                    cost_usd = float((usage.get("cost") or 0.0))
                    asyncio.create_task(_mpg.record_cost(
                        provider=f"openrouter/{actual_provider}",
                        model=str(actual_model),
                        tokens_in=int(usage.get("prompt_tokens", 0) or 0),
                        tokens_out=int(usage.get("completion_tokens", 0) or 0),
                        latency_ms=latency_ms,
                        cost_usd_est=cost_usd,
                        free_tier=str(model).endswith(":free"),
                        success=True,
                        agent_id=None,
                        task_kind=None,
                    ))
                except Exception:
                    pass

                if isinstance(content, list):
                    # Multimodal content parts — concatenate text parts.
                    parts = [p.get("text", "") for p in content if isinstance(p, dict) and p.get("type") == "text"]
                    return "".join(parts).strip()
                if isinstance(content, str):
                    return content.strip()
                return None

        except asyncio.TimeoutError:
            logger.warning(f"OpenRouterHandler: timeout after {timeout_s}s for '{model}'")
            return None
        except aiohttp.ClientError as e:
            logger.warning(f"OpenRouterHandler: client error for '{model}': {e}")
            return None

    async def shutdown(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
