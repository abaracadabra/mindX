# mindx/llm/zerog_handler.py
"""
0G Compute Adapter — agnostic OpenAI-compatible LLM client.

Speaks the OpenAI-shape /v1/proxy/chat/completions endpoint that the 0G
serving broker exposes (default https://api.0g.ai). Captures the
`ZG-Res-Key` response header on every call as an attestation hash — the
cryptographic proof that the output came from the declared model running
in a TEE (TeeML / TeeTLS sealed inference).

This is an **agnostic module**: any agent framework that consumes
OpenAI-shaped chat completions can plug it in. mindX is one consumer; the
factory at `llm/llm_factory.py` is mindX's wiring, but the class works
standalone.

Attestation handling — 3 mandatory steps from the 0G integration guide:

  1. `getRequestHeaders()` per inference call — supplies a fresh
     replay-protected header set the broker validates. Without it, calls
     succeed but lose verifiability properties.
  2. Capture `ZG-Res-Key` on the response — that's the chatID that ties
     the output to a specific TEE attestation.
  3. `processResponse()` — settles the on-chain micropayment ledger and
     verifies the TEE signature. Required before the broker permits the
     next call.

In the broker SDK these are TS-only functions on the broker client. This
Python handler is paired with the openagents/sidecar/ Node bridge for the
storage path. For Compute we currently call the OpenAI-compat endpoint
directly via HTTP and record the attestation, deferring full
processResponse() validation to the operator's broker setup. Production
operators set ZEROG_BROKER_URL pointing at a process running the broker
client; the handler then POSTs the chatID to /process-response on the
broker.

Models served (see models/zerog.yaml):
  - gpt-oss-120b           (cheapest, TeeML)
  - qwen3.6-plus           (1M context, TeeTLS)
  - GLM-5-FP8              (strongest reasoning, TeeML)
  - deepseek-chat-v3-0324  (TeeML)

Min deposit on 0G: 3 0G ledger + 1 0G per provider. The API key issued by
the broker represents a funded account.
"""
import asyncio
import json
import os
from typing import Dict, Any, Optional, List

try:
    import aiohttp
except ImportError:
    aiohttp = None

from utils.logging_config import get_logger
from .llm_interface import LLMHandlerInterface
from .rate_limiter import RateLimiter

logger = get_logger(__name__)


ZEROG_DEFAULT_BASE_URL = "https://api.0g.ai"
ZEROG_ATTESTATION_HEADER = "ZG-Res-Key"
ZEROG_SERVING_BACKEND_HEADER = "ZG-Serving-Backend"
# Optional in-process broker that owns the broker SDK and can settle ledgers.
# When set, the handler POSTs each captured chatID to <broker>/process-response.
ZEROG_BROKER_URL_ENV = "ZEROG_BROKER_URL"


class ZeroGHandler(LLMHandlerInterface):
    """OpenAI-shape client for 0G Compute. Agnostic — any framework can use it."""

    def __init__(
        self,
        model_name_for_api: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        rate_limiter: Optional[RateLimiter] = None,
        execution_timeout_minutes: Optional[int] = None,
        broker_url: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(
            "zerog",
            model_name_for_api,
            api_key,
            base_url,
            rate_limiter=rate_limiter,
            execution_timeout_minutes=execution_timeout_minutes,
        )

        self.api_base_url = (
            self.base_url
            or os.getenv("ZEROG_BASE_URL")
            or ZEROG_DEFAULT_BASE_URL
        ).rstrip("/")

        self.zerog_api_key = (
            self.api_key
            or os.getenv("ZEROG_API_KEY")
            or ""
        )

        # Optional pointer to a sidecar speaking the broker SDK. None = handler
        # records attestations but does NOT call processResponse(). When set,
        # we POST {chatID, providerAddress} to <broker>/process-response after
        # each successful inference (best-effort).
        self.broker_url = (
            broker_url
            or os.getenv(ZEROG_BROKER_URL_ENV)
            or ""
        ).rstrip("/") or None

        self._session: Optional[aiohttp.ClientSession] = None

        # Stash of the most recent attestation so callers (e.g. boardroom,
        # demo_agent) can grab it without re-sniffing the network.
        self.last_attestation: Optional[str] = None
        self.last_serving_backend: Optional[str] = None
        self.last_model: Optional[str] = None
        # Per-call request fingerprint — see _request_fingerprint(). Replays
        # the role of broker.getRequestHeaders() for replay protection.
        self.last_request_id: Optional[str] = None

        if not self.zerog_api_key:
            logger.warning(
                "ZeroGHandler: no api key found (ZEROG_API_KEY env or vault). "
                "Handler will operate in degraded mode and return mock responses."
            )

        logger.info(
            f"ZeroGHandler initialized: base={self.api_base_url}, "
            f"model={self.model_name_for_api}, "
            f"keyed={'yes' if self.zerog_api_key else 'no'}, "
            f"broker={'yes' if self.broker_url else 'no'}"
        )

    async def _get_session(self) -> "aiohttp.ClientSession":
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                json_serialize=json.dumps,
                timeout=aiohttp.ClientTimeout(total=self.execution_timeout_minutes * 60),
            )
        return self._session

    @staticmethod
    def _request_fingerprint() -> str:
        """Per-call random fingerprint used as the X-Request-Id header.

        The 0G broker SDK's `getRequestHeaders()` mints a fresh header set
        per inference for replay protection. Without the broker SDK we
        emulate this by attaching a random 32-byte hex string the broker
        will echo back in logs; the operator's broker-side process can
        match it against the chatID to detect replays.
        """
        import secrets
        return secrets.token_hex(32)

    def _headers(self, request_id: str) -> Dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "X-Request-Id":  request_id,           # replay-protection
            "X-Zg-Client":   "mindx-zerog-handler/0.2",
        }
        if self.zerog_api_key:
            h["Authorization"] = f"Bearer {self.zerog_api_key}"
        return h

    @staticmethod
    def _strip_provider_prefix(model: str) -> str:
        """Map mindX-style model IDs (zerog/gpt-oss-120b) to API names."""
        if not model:
            return model
        if "/" in model:
            return model.split("/", 1)[1]
        return model

    async def _process_response(self, chat_id: str, model: str) -> bool:
        """Best-effort settle the on-chain ledger via the optional broker.

        If `ZEROG_BROKER_URL` isn't set, we do nothing and return False.
        When set, POST {chatID, model, request_id} to /process-response
        and treat any 2xx as success. Failures are logged, not raised —
        the broker sidecar reconciles asynchronously.
        """
        if not self.broker_url or not chat_id:
            return False
        try:
            session = await self._get_session()
            url = f"{self.broker_url}/process-response"
            payload = {
                "chatID":      chat_id,
                "model":       model,
                "request_id":  self.last_request_id,
            }
            async with session.post(
                url, json=payload,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if 200 <= resp.status < 300:
                    return True
                text = await resp.text()
                logger.debug(
                    f"0G broker process-response {resp.status}: {text[:200]}"
                )
                return False
        except Exception as e:
            logger.debug(f"0G broker process-response failed (non-fatal): {e}")
            return False

    async def generate_text(
        self,
        prompt: str,
        model: str,
        max_tokens: Optional[int] = 2048,
        temperature: Optional[float] = 0.7,
        json_mode: Optional[bool] = False,
        **kwargs: Any,
    ) -> Optional[str]:
        """OpenAI-compatible /v1/proxy/chat/completions on 0G Compute.

        Captures the ZG-Res-Key attestation header into `self.last_attestation`
        so the caller can record it alongside the response (the verifiable-
        inference proof for the boardroom / demo_agent / catalogue layer).
        """
        if not aiohttp:
            return "Error: aiohttp not installed for ZeroGHandler."
        if not self.zerog_api_key:
            return f"[MOCK ZEROG] No API key — would have called {model}: {prompt[:80]}…"

        api_model = self._strip_provider_prefix(model or self.model_name_for_api or "gpt-oss-120b")

        if self.rate_limiter and not await self.rate_limiter.wait():
            logger.warning(f"ZeroGHandler: rate limiter retries exhausted for '{api_model}'")
            return None

        session = await self._get_session()
        endpoint = f"{self.api_base_url}/v1/proxy/chat/completions"

        messages = kwargs.get("messages")
        if not messages:
            system_prompt = kwargs.get("system_prompt")
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": api_model,
            "messages": messages,
            "stream": False,
        }
        if max_tokens and max_tokens > 0:
            payload["max_tokens"] = max_tokens
        if temperature is not None:
            payload["temperature"] = temperature
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        stop = kwargs.get("stop_sequences") or kwargs.get("stop")
        if stop:
            payload["stop"] = stop
        extra_body = kwargs.get("extra_body")
        if extra_body and isinstance(extra_body, dict):
            payload.update(extra_body)

        # Per-call replay-protected fingerprint — emulates broker.getRequestHeaders()
        request_id = self._request_fingerprint()
        self.last_request_id = request_id

        try:
            async with session.post(endpoint, json=payload, headers=self._headers(request_id)) as resp:
                # Capture attestation header regardless of status — even error
                # responses are signed when the model executed but failed
                # post-processing.
                self.last_attestation     = resp.headers.get(ZEROG_ATTESTATION_HEADER)
                self.last_serving_backend = resp.headers.get(ZEROG_SERVING_BACKEND_HEADER)
                self.last_model           = api_model

                if resp.status != 200:
                    error_text = await resp.text()
                    logger.warning(
                        f"0G Compute error ({resp.status}) on {api_model}: "
                        f"{error_text[:300]}"
                    )
                    return None

                data = await resp.json(loads=json.loads)
                choices = data.get("choices", [])
                if not choices:
                    logger.warning(f"0G Compute returned no choices for {api_model}")
                    return None
                content = choices[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})
                logger.debug(
                    f"0G response: {len(content)} chars, "
                    f"tokens={usage.get('total_tokens', '?')}, "
                    f"attest={self.last_attestation[:16] + '…' if self.last_attestation else 'none'}, "
                    f"req={request_id[:8]}"
                )
                # Mandatory step 3 (best-effort): settle the ledger via broker.
                # Fire-and-forget so we don't block the caller; the broker
                # sidecar handles failures + retries.
                if self.last_attestation:
                    asyncio.create_task(
                        self._process_response(self.last_attestation, api_model)
                    )
                return content
        except aiohttp.ClientError as e:
            logger.warning(f"0G Compute connection error: {e}")
            return None
        except Exception as e:
            logger.error(f"0G Compute unexpected error: {e}", exc_info=True)
            return None

    async def list_models(self) -> Optional[List[Dict[str, Any]]]:
        """List models served by 0G Compute via /v1/models."""
        if not aiohttp or not self.zerog_api_key:
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
            logger.debug(f"0G list_models failed: {e}")
            return None

    async def health_check(self) -> bool:
        """Check 0G Compute reachability via /v1/models."""
        if not aiohttp:
            return False
        session = await self._get_session()
        try:
            async with session.get(
                f"{self.api_base_url}/v1/models",
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                return resp.status in (200, 401)  # 401 = reachable but unauthed
        except Exception:
            return False

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
