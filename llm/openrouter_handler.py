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

# Public conversation ledger: every exchange with a model is recorded for
# the live substrate at mindx.pythai.net/mindx.html. Import is lazy-safe —
# a missing recorder degrades to a no-op decorator, never a broken handler.
try:
    from agents.interaction_recorder import observe as _observe_interaction
except Exception:  # pragma: no cover
    def _observe_interaction(_provider):
        return lambda fn: fn

logger = get_logger(__name__)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_REFERER = "https://mindx.pythai.net"
OPENROUTER_TITLE = "mindX"


async def refresh_openrouter_roster(seed_slugs: Optional[list] = None) -> Dict[str, Any]:
    """Fetch the live OpenRouter model roster and reconcile model_health.

    The OpenRouter free roster churns constantly — models are decommissioned
    without notice (7 of 8 of mindX's board models were 404 on 2026-06-24). This
    fetches /models, derives the live ``:free`` set, seeds any config slugs so
    they can be judged, and marks configured-but-absent slugs dead (revives ones
    that reappear). Selection then never routes to a model that no longer exists.

    Fail-open: any error returns an empty reconcile result and changes nothing.
    Call periodically (dream cycle / startup) — it is cheap and idempotent.
    """
    result: Dict[str, Any] = {"retired": [], "revived": [], "live_count": 0, "error": None}
    if not aiohttp:
        result["error"] = "aiohttp unavailable"
        return result
    try:
        from llm.model_health import ModelHealth
        mh = ModelHealth.instance()
        for s in (seed_slugs or []):
            mh.seed(s, "openrouter")
        async with aiohttp.ClientSession(json_serialize=json.dumps) as session:
            async with session.get(f"{OPENROUTER_BASE_URL}/models",
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    result["error"] = f"HTTP {resp.status}"
                    return result
                data = json.loads(await resp.text())
        live_free = [m.get("id") for m in (data.get("data") or [])
                     if isinstance(m.get("id"), str) and m["id"].endswith(":free")]
        rec = mh.reconcile_roster("", live_free)
        rec["live_count"] = len(live_free)
        logger.info(f"OpenRouter roster refresh: {len(live_free)} live :free, "
                    f"retired={rec.get('retired')}, revived={rec.get('revived')}")
        return rec
    except Exception as e:  # pragma: no cover
        result["error"] = str(e)
        logger.warning(f"OpenRouter roster refresh failed: {e}")
        return result


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

    @_observe_interaction("openrouter")
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
                    # Inference budget: 429/quota backs off the openrouter tier.
                    try:
                        from llm.inference_budget import record as _budget_record
                        _ra = response.headers.get("Retry-After")
                        _is_rl = response.status == 429 or "rate" in snippet.lower() or "quota" in snippet.lower()
                        _budget_record("openrouter", ok=not _is_rl,
                                       retry_after=float(_ra) if (_ra and _ra.isdigit()) else None)
                    except Exception:
                        pass
                    # Per-model health: a 404 / "decommissioned" retires this slug
                    # so the selector stops routing to it (the dead-roster fix).
                    try:
                        from llm.model_health import record as _health_record
                        _health_record(model, ok=False, http_status=response.status,
                                       error_text=snippet, latency_ms=latency_ms, provider="openrouter")
                    except Exception:
                        pass
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
                    try:
                        from llm.model_health import record as _health_record
                        _emsg = f"{err.get('code')} {err.get('message')}" if err else "no choices"
                        _ecode = err.get("code") if isinstance(err.get("code"), int) else None
                        _health_record(model, ok=False, http_status=_ecode, error_text=_emsg,
                                       latency_ms=latency_ms, provider="openrouter")
                    except Exception:
                        pass
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

                # Inference budget metabolism: healthy use of the openrouter tier.
                _tok_total = int(usage.get("prompt_tokens", 0) or 0) + int(usage.get("completion_tokens", 0) or 0)
                try:
                    from llm.inference_budget import record as _budget_record
                    _budget_record("openrouter", ok=True, tokens=_tok_total)
                except Exception:
                    pass
                # Per-model health: a usable answer keeps (or revives) the slug.
                try:
                    from llm.model_health import record as _health_record
                    _health_record(model, ok=bool(content), http_status=200,
                                   error_text=None if content else "empty content",
                                   tokens=_tok_total, latency_ms=latency_ms,
                                   provider=f"openrouter/{actual_provider}")
                except Exception:
                    pass
                # Precision-metrics ledger — the source of truth behind
                # /insight/inference/ledger and its hash-linked anchor chain.
                # ACTUAL cloud token counts from the API's usage block.
                try:
                    from llm.precision_metrics import OllamaResponseMetrics, PrecisionMetricsTracker
                    PrecisionMetricsTracker.instance().record_with_cost(
                        OllamaResponseMetrics(
                            eval_count=int(usage.get("completion_tokens", 0) or 0),
                            prompt_eval_count=int(usage.get("prompt_tokens", 0) or 0),
                            total_duration_ns=int(latency_ms) * 1_000_000,
                            model=str(actual_model),
                        ),
                        provider=f"openrouter/{actual_provider}",
                    )
                except Exception:
                    pass

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
