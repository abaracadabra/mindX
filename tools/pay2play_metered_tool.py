"""
Pay2PlayMeteredTool — mindX BaseTool that gates any inner action behind a
pay2play x402 metered settlement on Arc testnet.

Two roles in one class:
  1. Direct call mode: `execute(action="job/create", payload={...})` proxies to
     the pay2play C9 gateway (default http://localhost:3009). Each call costs
     $0.002 USDC, batched via Circle Gateway.
  2. Decorator mode: `meter(inner_callable)` wraps any async tool method so
     that invocation triggers a settlement before the inner work runs.

Rate limiter:
  Default 1 settlement / agent / 60 s. mindX's autonomous 5-min loop will
  otherwise burn USDC on every BDI deliberation cycle. Override per-call via
  rate_limit_seconds=0 for tests, or via Config key "pay2play.rate_limit_seconds".

Failure mode:
  If the C9 gateway is unreachable or returns 5xx, execute() raises so the
  caller can fall back to a free path (e.g. local-only inference). We do not
  silently succeed on payment failure — that would let agents bypass billing.

Usage:
  >>> tool = Pay2PlayMeteredTool(buyer_private_key=os.environ["BUYER_PRIVATE_KEY"])
  >>> result = await tool.execute(action="health")
  >>> result = await tool.execute(
  ...     action="job/create",
  ...     payload={
  ...         "clientKey": "0x...", "providerKey": "0x...",
  ...         "descText": "Analyze tweets", "budgetUsdc": 0.05,
  ...     },
  ... )
"""

import asyncio
import os
import time
from typing import Any, Awaitable, Callable, Dict, Optional

import httpx

from agents.core.bdi_agent import BaseTool
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)


class Pay2PlayMeteredTool(BaseTool):
    """Gate mindX agent actions behind pay2play x402 settlements on Arc."""

    DEFAULT_GATEWAY_URL = "http://localhost:3009"
    DEFAULT_ONRAMP_URL = "http://localhost:3010"
    DEFAULT_RATE_LIMIT_SECONDS = 60.0
    DEFAULT_PRICE_USDC = 0.002

    def __init__(
        self,
        config: Optional[Config] = None,
        gateway_url: Optional[str] = None,
        onramp_url: Optional[str] = None,
        buyer_private_key: Optional[str] = None,
        rate_limit_seconds: Optional[float] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(config=config, **kwargs)
        cfg = self.config

        self.gateway_url: str = (
            gateway_url
            or os.environ.get("PAY2PLAY_GATEWAY_URL")
            or cfg.get("pay2play.gateway_url", self.DEFAULT_GATEWAY_URL)
        )
        self.onramp_url: str = (
            onramp_url
            or os.environ.get("PAY2PLAY_ONRAMP_URL")
            or cfg.get("pay2play.onramp_url", self.DEFAULT_ONRAMP_URL)
        )
        self.buyer_private_key: Optional[str] = (
            buyer_private_key
            or os.environ.get("BUYER_PRIVATE_KEY")
            or cfg.get("pay2play.buyer_private_key", None)
        )
        self.rate_limit_seconds: float = float(
            rate_limit_seconds
            if rate_limit_seconds is not None
            else cfg.get("pay2play.rate_limit_seconds", self.DEFAULT_RATE_LIMIT_SECONDS)
        )
        self.price_usdc: float = float(
            cfg.get("pay2play.price_usdc", self.DEFAULT_PRICE_USDC)
        )

        self.tool_name = "pay2play_metered"
        self.version = "0.1"

        # Per-agent last-settlement timestamps, used by the rate limiter.
        self._last_settle_at: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ #
    # Health / status
    # ------------------------------------------------------------------ #

    async def health(self) -> Dict[str, Any]:
        """Hit the C9 gateway /health endpoint (free, no payment)."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.gateway_url}/health")
            resp.raise_for_status()
            return resp.json()

    # ------------------------------------------------------------------ #
    # Rate limiter
    # ------------------------------------------------------------------ #

    async def _check_rate_limit(self, agent_id: str) -> None:
        """Raise RuntimeError if `agent_id` settled within rate_limit_seconds."""
        if self.rate_limit_seconds <= 0:
            return
        async with self._lock:
            now = time.monotonic()
            last = self._last_settle_at.get(agent_id, 0.0)
            wait = self.rate_limit_seconds - (now - last)
            if wait > 0:
                raise RuntimeError(
                    f"pay2play rate limit: agent {agent_id} must wait "
                    f"{wait:.1f}s before next settlement"
                )
            self._last_settle_at[agent_id] = now

    # ------------------------------------------------------------------ #
    # Direct gateway proxy
    # ------------------------------------------------------------------ #

    async def execute(
        self,
        action: str = "health",
        payload: Optional[Dict[str, Any]] = None,
        agent_id: str = "default",
        **_: Any,
    ) -> Dict[str, Any]:
        """
        Proxy a single AgenticPlace gateway action.

        Args:
            action: one of "health", "info", "agent/register", "job/create",
                    "job/<id>" (for GET).
            payload: request body for POST actions (ignored on GET).
            agent_id: rate-limit bucket key.
        """
        if action in ("health", "info"):
            return await self._get(action)

        if action.startswith("job/") and action != "job/create":
            return await self._get(action)

        # Paid actions
        if action not in ("agent/register", "job/create"):
            raise ValueError(f"unknown pay2play action: {action!r}")

        await self._check_rate_limit(agent_id)
        return await self._post_paid(action, payload or {})

    async def _get(self, path: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{self.gateway_url}/{path}")
            resp.raise_for_status()
            return resp.json()

    async def _post_paid(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        POST a paid request. The actual EIP-3009 signing happens upstream — this
        method assumes the C9 gateway is fronted by a buyer-side facilitator
        (or the caller provides X-PAYMENT directly via `payload['_payment']`).

        For mindX's typical use case (server-side agent calling its own
        gateway), the gateway can be configured to accept self-signed requests
        from a trusted caller IP, or the caller pre-signs and passes the
        header verbatim.
        """
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        precomputed = payload.pop("_payment", None) if isinstance(payload, dict) else None
        if precomputed:
            headers["X-PAYMENT"] = str(precomputed)

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.gateway_url}/{path}",
                json=payload,
                headers=headers,
            )
            if resp.status_code == 402:
                # Caller did not include a payment; surface the challenge so
                # the buyer-side facilitator can sign and retry. Also fetch a
                # cheapest no-KYC on-ramp hint from c10 so an upstream BDI
                # agent can decide whether to self-fund. We do NOT auto-fund
                # — that decision stays with the agent.
                challenge = resp.headers.get("PAYMENT-REQUIRED") or resp.headers.get(
                    "payment-required"
                )
                err = PermissionError(
                    "pay2play: payment required and no signature supplied. "
                    f"PAYMENT-REQUIRED={challenge}"
                )
                err.payment_required = challenge  # type: ignore[attr-defined]
                err.onramp_hint = await self._fetch_onramp_hint()  # type: ignore[attr-defined]
                raise err
            resp.raise_for_status()
            return resp.json()

    async def _fetch_onramp_hint(self) -> Optional[Dict[str, Any]]:
        """Pull the cheapest no-KYC provider summary from c10. Free; best-effort.

        Returns ``None`` on any error — the 402 still propagates without the hint.
        Surfacing this lets a BDI agent show "you need ~$0.006 USDC to settle;
        cheapest no-KYC route is CCTP from Base — see {url}/and-deposit" instead
        of just "payment required".
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{self.onramp_url}/providers", params={"kyc": "none"}
                )
                if resp.status_code != 200:
                    return None
                providers = (resp.json() or {}).get("providers") or []
                if not providers:
                    return None
                # Pick the first no-KYC provider as the hint. The on-ramp's
                # default priority puts cctp first; we don't re-rank here
                # because there's no amount/source context at this layer.
                top = providers[0]
                return {
                    "provider_id": top.get("id"),
                    "category": top.get("category"),
                    "kyc_required": top.get("kycRequired"),
                    "and_deposit_url": f"{self.onramp_url}/and-deposit",
                    "providers_url": f"{self.onramp_url}/providers",
                    "note": (
                        "POST /and-deposit with {amountUsdc, userContext, recipient} "
                        "to get the on-ramp instruction + EIP-3009 typed-data."
                    ),
                }
        except Exception as e:
            logger.debug(f"onramp hint fetch failed (non-fatal): {e}")
            return None

    # ------------------------------------------------------------------ #
    # Decorator: meter any async callable
    # ------------------------------------------------------------------ #

    def meter(
        self,
        inner: Callable[..., Awaitable[Any]],
        action: str = "agent/register",
        agent_id: str = "default",
    ) -> Callable[..., Awaitable[Any]]:
        """
        Wrap an async callable so each invocation settles via pay2play first,
        then runs the inner work. If settlement fails, inner is not called.

        Example:
            >>> tool = Pay2PlayMeteredTool()
            >>> paid_search = tool.meter(my_agent.search, action="agent/register")
            >>> await paid_search("query")
        """

        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            settle_payload = kwargs.pop("_p2p_payload", {})
            await self.execute(action=action, payload=settle_payload, agent_id=agent_id)
            return await inner(*args, **kwargs)

        wrapper.__name__ = f"metered_{getattr(inner, '__name__', 'callable')}"
        return wrapper
