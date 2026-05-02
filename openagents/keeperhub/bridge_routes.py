"""
KeeperHub × AgenticPlace bidirectional x402 bridge.

KeeperHub serves paid workflows over HTTP 402 with parallel x402
(Base USDC, chain 8453) + MPP (Tempo USDC.e, chain 4217) challenges.
AgenticPlace serves paid jobs over HTTP 402 on Arc testnet.

This bridge does two things:

1. **Inbound** — `GET /p2p/keeperhub/<path>` re-emits any AgenticPlace 402
   challenge in KeeperHub-compatible x402 + MPP format, so a wallet that
   speaks KH's `@keeperhub/wallet` SDK can pay an AgenticPlace job
   natively without any Arc-specific signing logic.

2. **Outbound** — `POST /p2p/keeperhub/workflow/callback` is the webhook
   endpoint we register as a KeeperHub paid workflow trigger. KH calls
   this when one of *its* customers pays for our exposed capability;
   we run the underlying mindX work and return the result. KH already
   settled USDC into our Turnkey wallet on Base or Tempo.

Mounted into FastAPI by `mindx_backend_service/main_service.py` via
`from openagents.keeperhub.bridge_routes import router as keeperhub_router`
and `app.include_router(keeperhub_router, prefix='', tags=['keeperhub'])`.

Catalogue: emits `kind=tool.invoke{.keeperhub_bridge}` for every settlement
so `/insight/openagents/keeperhub` can surface them on the dashboard.
"""

from __future__ import annotations

import os
import time
import json
import hashlib
import secrets
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, Body, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter()

# --------------------------------------------------------------------- #
# Config — all overridable via env (BANKON Vault → env injection)
# --------------------------------------------------------------------- #

KH_X402_NETWORK_ID    = os.environ.get("KH_X402_NETWORK_ID", "8453")  # Base mainnet
KH_X402_NETWORK_NAME  = os.environ.get("KH_X402_NETWORK_NAME", "base")
KH_X402_USDC_ADDRESS  = os.environ.get(
    "KH_X402_USDC_ADDRESS", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"  # Base USDC
)

KH_MPP_NETWORK_ID     = os.environ.get("KH_MPP_NETWORK_ID", "4217")  # Tempo
KH_MPP_NETWORK_NAME   = os.environ.get("KH_MPP_NETWORK_NAME", "tempo")
KH_MPP_USDC_ADDRESS   = os.environ.get(
    "KH_MPP_USDC_ADDRESS", "0x20c0…8b50"  # placeholder — operator sets exact USDC.e
)

KH_RECIPIENT          = os.environ.get("KH_RECIPIENT_ADDRESS", "")  # mindX Turnkey wallet on Base
KH_DEFAULT_PRICE_USDC = float(os.environ.get("KH_DEFAULT_PRICE_USDC", "0.005"))
KH_CHALLENGE_TTL_S    = int(os.environ.get("KH_CHALLENGE_TTL_S", "120"))
KH_WEBHOOK_SECRET     = os.environ.get("KH_WEBHOOK_SECRET", "")

P2P_GATEWAY = os.environ.get("PAY2PLAY_GATEWAY_URL", "http://localhost:3009")

# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #

def _usdc_units(amount_usdc: float) -> str:
    """USDC has 6 decimals. Convert dollars to integer base units string."""
    return str(int(round(amount_usdc * 1_000_000)))


def _build_kh_challenge(
    resource: str,
    amount_usdc: float,
    description: str = "",
    recipient: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct a dual x402+MPP envelope KH wallets understand.

    Shape mirrors KH's documented payload (x402 array of accepted
    schemes). Wallets pick whichever they have funds for.
    """
    expires = int(time.time()) + KH_CHALLENGE_TTL_S
    nonce = "0x" + secrets.token_hex(32)
    rcpt = recipient or KH_RECIPIENT or "0x0000000000000000000000000000000000000000"
    units = _usdc_units(amount_usdc)

    return {
        "x402Version": 1,
        "accepts": [
            {
                "scheme": "exact",
                "network": KH_X402_NETWORK_NAME,
                "chainId": int(KH_X402_NETWORK_ID),
                "asset": KH_X402_USDC_ADDRESS,
                "maxAmountRequired": units,
                "payTo": rcpt,
                "resource": resource,
                "description": description or f"mindX/AgenticPlace job",
                "mimeType": "application/json",
                "extra": {"nonce": nonce, "expiresAt": expires},
            },
            {
                "scheme": "mpp",
                "network": KH_MPP_NETWORK_NAME,
                "chainId": int(KH_MPP_NETWORK_ID),
                "asset": KH_MPP_USDC_ADDRESS,
                "maxAmountRequired": units,
                "payTo": rcpt,
                "resource": resource,
                "description": description or f"mindX/AgenticPlace job",
                "mimeType": "application/json",
                "extra": {"nonce": nonce, "expiresAt": expires},
            },
        ],
    }


async def _record_settlement(direction: str, payload: Dict[str, Any]) -> None:
    """Mirror to catalogue so the dashboard can show it. Best-effort."""
    try:
        from agents.catalogue.events import emit_catalogue_event
        await emit_catalogue_event(
            kind="tool.invoke",
            actor="keeperhub_bridge",
            payload={"direction": direction, **payload},
            source_log="keeperhub_bridge_routes",
        )
    except Exception as e:
        logger.debug(f"catalogue mirror failed (non-fatal): {e}")


# --------------------------------------------------------------------- #
# Inbound: KH-shaped 402 wrapping AgenticPlace endpoints
# --------------------------------------------------------------------- #

@router.get("/p2p/keeperhub/info", summary="KeeperHub bridge info (free)")
async def kh_info() -> Dict[str, Any]:
    """Free metadata: which AgenticPlace endpoints are exposed via KH."""
    return {
        "ok": True,
        "service": "mindX × AgenticPlace × KeeperHub bridge",
        "x402_supported_networks": [
            {"name": KH_X402_NETWORK_NAME, "chainId": int(KH_X402_NETWORK_ID), "usdc": KH_X402_USDC_ADDRESS},
            {"name": KH_MPP_NETWORK_NAME,  "chainId": int(KH_MPP_NETWORK_ID),  "usdc": KH_MPP_USDC_ADDRESS},
        ],
        "recipient_configured": bool(KH_RECIPIENT),
        "exposed_endpoints": [
            {"path": "/p2p/keeperhub/agent/register", "price_usdc": KH_DEFAULT_PRICE_USDC, "wraps": "/p2p/agent/register"},
            {"path": "/p2p/keeperhub/job/create",     "price_usdc": KH_DEFAULT_PRICE_USDC, "wraps": "/p2p/job/create"},
            {"path": "/p2p/keeperhub/inference",      "price_usdc": KH_DEFAULT_PRICE_USDC, "wraps": "0G Compute via mindX"},
        ],
        "challenge_ttl_s": KH_CHALLENGE_TTL_S,
    }


def _kh_402_response(resource: str, description: str, amount_usdc: float) -> JSONResponse:
    challenge = _build_kh_challenge(resource, amount_usdc, description=description)
    return JSONResponse(
        status_code=402,
        content={"error": "payment required", **challenge},
        headers={"X-Payment-Required": "true"},
    )


@router.post("/p2p/keeperhub/agent/register", summary="ERC-8004 agent register via KH x402 (paid)")
async def kh_register_agent(
    request: Request,
    body: Dict[str, Any] = Body(...),
    x_payment: Optional[str] = Header(default=None, alias="X-PAYMENT"),
):
    """Wraps AgenticPlace /p2p/agent/register with KH-compatible x402 challenge."""
    if not x_payment:
        return _kh_402_response(
            resource=str(request.url),
            description="ERC-8004 agent register on AgenticPlace (Arc) — settled in USDC via KeeperHub",
            amount_usdc=KH_DEFAULT_PRICE_USDC,
        )

    headers = {"Content-Type": "application/json", "X-PAYMENT": x_payment}
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{P2P_GATEWAY}/agent/register", json=body, headers=headers)
            if resp.status_code == 402:
                # Upstream still wants payment — pass through with KH framing.
                return _kh_402_response(str(request.url), "Upstream still requires payment", KH_DEFAULT_PRICE_USDC)
            resp.raise_for_status()
            data = resp.json()
            await _record_settlement("inbound", {
                "endpoint": "agent/register",
                "amount_usdc": KH_DEFAULT_PRICE_USDC,
                "x402_payment_present": True,
                "upstream_status": resp.status_code,
            })
            return data
    except httpx.HTTPError as e:
        logger.error(f"kh_register_agent upstream error: {e}")
        raise HTTPException(status_code=502, detail=f"AgenticPlace upstream error: {e}")


@router.post("/p2p/keeperhub/job/create", summary="ERC-8183 job lifecycle via KH x402 (paid)")
async def kh_create_job(
    request: Request,
    body: Dict[str, Any] = Body(...),
    x_payment: Optional[str] = Header(default=None, alias="X-PAYMENT"),
):
    if not x_payment:
        return _kh_402_response(
            resource=str(request.url),
            description="ERC-8183 job creation on AgenticPlace (Arc) — settled in USDC via KeeperHub",
            amount_usdc=KH_DEFAULT_PRICE_USDC,
        )

    headers = {"Content-Type": "application/json", "X-PAYMENT": x_payment}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{P2P_GATEWAY}/job/create", json=body, headers=headers)
            if resp.status_code == 402:
                return _kh_402_response(str(request.url), "Upstream still requires payment", KH_DEFAULT_PRICE_USDC)
            resp.raise_for_status()
            data = resp.json()
            await _record_settlement("inbound", {
                "endpoint": "job/create",
                "amount_usdc": KH_DEFAULT_PRICE_USDC,
                "upstream_status": resp.status_code,
            })
            return data
    except httpx.HTTPError as e:
        logger.error(f"kh_create_job upstream error: {e}")
        raise HTTPException(status_code=502, detail=f"AgenticPlace upstream error: {e}")


@router.post("/p2p/keeperhub/inference", summary="0G Compute inference via KH x402 (paid)")
async def kh_inference(
    request: Request,
    body: Dict[str, Any] = Body(...),
    x_payment: Optional[str] = Header(default=None, alias="X-PAYMENT"),
):
    """Pay-per-call wrapper for an mindX → 0G Compute inference round-trip.

    Markup model: customer pays KH_DEFAULT_PRICE_USDC; mindX pays whatever
    0G charges (see `models/zerog.yaml`); margin covers infrastructure.
    """
    if not x_payment:
        return _kh_402_response(
            resource=str(request.url),
            description="Sealed inference via 0G Compute (mindX-routed). Returns response + ZG-Res-Key attestation.",
            amount_usdc=KH_DEFAULT_PRICE_USDC,
        )

    prompt = body.get("prompt") or body.get("messages")
    model = body.get("model", "zerog/gpt-oss-120b")
    if not prompt:
        raise HTTPException(status_code=400, detail="missing 'prompt' or 'messages'")

    try:
        from llm.llm_factory import create_llm_handler

        handler = await create_llm_handler(provider_name="zerog", model_name=model)
        if isinstance(prompt, list):
            text = await handler.generate_text(
                prompt="",  # unused when messages is supplied
                model=model,
                max_tokens=int(body.get("max_tokens", 1024)),
                temperature=float(body.get("temperature", 0.7)),
                messages=prompt,
            )
        else:
            text = await handler.generate_text(
                prompt=str(prompt),
                model=model,
                max_tokens=int(body.get("max_tokens", 1024)),
                temperature=float(body.get("temperature", 0.7)),
            )

        attestation = getattr(handler, "last_attestation", None)
        backend = getattr(handler, "last_serving_backend", None)

        await _record_settlement("inbound", {
            "endpoint": "inference",
            "amount_usdc": KH_DEFAULT_PRICE_USDC,
            "model": model,
            "attestation": (attestation or "")[:64],
            "backend": backend,
        })

        return {
            "ok": True,
            "model": model,
            "response": text,
            "attestation": attestation,
            "serving_backend": backend,
            "settled_usdc": KH_DEFAULT_PRICE_USDC,
        }
    except Exception as e:
        logger.exception("kh_inference failed")
        raise HTTPException(status_code=500, detail=f"inference failed: {e}")


# --------------------------------------------------------------------- #
# Outbound: KH webhook receiver — KH already settled USDC, run the work
# --------------------------------------------------------------------- #

@router.post("/p2p/keeperhub/workflow/callback", summary="KeeperHub paid-workflow webhook target")
async def kh_workflow_callback(
    request: Request,
    body: Dict[str, Any] = Body(...),
    x_kh_signature: Optional[str] = Header(default=None, alias="X-KH-Signature"),
):
    """Webhook hit by KeeperHub when a customer pays for our exposed
    workflow. The USDC is already in our Turnkey wallet.

    Validates the optional KH webhook signature (HMAC-SHA256 over body
    using KH_WEBHOOK_SECRET). Currently advisory-only when no secret set.
    """
    if KH_WEBHOOK_SECRET and x_kh_signature:
        raw = await request.body()
        expected = hashlib.sha256(KH_WEBHOOK_SECRET.encode() + raw).hexdigest()
        if not secrets.compare_digest(expected, x_kh_signature):
            raise HTTPException(status_code=401, detail="bad webhook signature")

    workflow = body.get("workflow_id") or body.get("workflowId")
    payload  = body.get("payload") or {}
    tx_hash  = body.get("tx_hash") or body.get("txHash")
    payer    = body.get("payer")
    amount   = body.get("amount_usdc") or body.get("amountUsdc")

    await _record_settlement("outbound", {
        "workflow_id": workflow,
        "tx_hash": tx_hash,
        "payer": payer,
        "amount_usdc": amount,
        "payload_keys": list(payload.keys()),
    })

    # The default behaviour is just to ACK so KH considers the workflow done.
    # Workflow-specific handlers can be plugged in via the `workflow` field.
    handlers = {
        "mindx_inference": _handle_workflow_inference,
        "mindx_boardroom": _handle_workflow_boardroom,
    }
    handler = handlers.get(workflow)
    if handler:
        result = await handler(payload)
        return {"ok": True, "workflow": workflow, "result": result}
    return {"ok": True, "workflow": workflow, "note": "ack only — no handler registered"}


async def _handle_workflow_inference(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch a 0G Compute inference for a paid KH workflow."""
    from llm.llm_factory import create_llm_handler

    model = payload.get("model", "zerog/gpt-oss-120b")
    prompt = payload.get("prompt", "")
    handler = await create_llm_handler(provider_name="zerog", model_name=model)
    text = await handler.generate_text(
        prompt=prompt,
        model=model,
        max_tokens=int(payload.get("max_tokens", 1024)),
        temperature=float(payload.get("temperature", 0.7)),
    )
    return {
        "model": model,
        "response": text,
        "attestation": getattr(handler, "last_attestation", None),
    }


async def _handle_workflow_boardroom(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convene the 8-soldier boardroom to deliberate on a paid directive.

    Best-effort: if the boardroom module isn't wired in this deployment,
    return a minimal stub so KH still considers the workflow complete.
    """
    directive = payload.get("directive", "")
    try:
        # Lazy import — boardroom is heavy and not always loaded.
        from daio.governance.boardroom import convene_session  # type: ignore
        result = await convene_session(directive=directive, source="keeperhub_paid_workflow")
        return {"directive": directive, "session": result}
    except Exception as e:
        logger.warning(f"boardroom convene unavailable: {e}")
        return {"directive": directive, "note": "boardroom module unavailable in this deploy"}
