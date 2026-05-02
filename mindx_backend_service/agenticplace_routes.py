"""
AgenticPlace API Routes
Agnostic frontend integration layer for AgenticPlace UI to interact with mindX backend.
"""

from fastapi import APIRouter, HTTPException, Body
from typing import Dict, Any, Optional
import time
from datetime import datetime

from agents.core.mindXagent import MindXAgent
from agents.orchestration.ceo_agent import CEOAgent
from agents.orchestration.mastermind_agent import MastermindAgent
from agents.memory_agent import MemoryAgent
from api.ollama.ollama_url import create_ollama_api
from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/agenticplace", tags=["AgenticPlace"])

_config: Optional[Config] = None
_memory_agent: Optional[MemoryAgent] = None

def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config

def get_memory_agent() -> Optional[MemoryAgent]:
    global _memory_agent
    if _memory_agent is None:
        try:
            _memory_agent = MemoryAgent(config=get_config())
        except Exception as e:
            logger.warning(f"MemoryAgent not available: {e}")
            _memory_agent = None
    return _memory_agent


@router.post("/agent/call", summary="Call mindXagent through specified agent (CEO, mastermind, mindX, SunTsu)")
async def call_mindx_agent(request: Dict[str, Any] = Body(...)):
    """
    Route agent calls from AgenticPlace frontend to mindX backend agents.
    Supports CEO, mastermind, mindX, SunTsu, and PYTHAI agents.
    """
    try:
        agent_type = request.get("agent_type", "ceo")
        directive = request.get("directive", "").strip()
        mode = request.get("mode", "execution")
        persona = request.get("persona")
        prompt = request.get("prompt")
        context = request.get("context", {})
        
        if not directive:
            raise HTTPException(status_code=400, detail="Directive is required")
        
        memory_agent = get_memory_agent()
        
        # Route to appropriate agent
        # CFO routes through CEO agent with priority context for financial tool access
        if agent_type in ["ceo", "pythai"] or (context.get("agent_id") == "cfo" or "CFO Priority Access" in directive):
            # CEO Agent call (also handles CFO with priority access)
            from agents.core.belief_system import BeliefSystem
            belief_system = BeliefSystem()
            
            # Check if this is a CFO request
            is_cfo_request = context.get("agent_id") == "cfo" or "CFO Priority Access" in directive
            agent_id = f"cfo_{agent_type}" if is_cfo_request else f"ceo_{agent_type}"
            
            ceo = CEOAgent(
                agent_id=agent_id,
                memory_agent=memory_agent,
                belief_system=belief_system,
                config=get_config()
            )
            await ceo.initialize()
            
            # If CFO request, enhance directive with financial tool access
            if is_cfo_request:
                # Extract original directive if prefixed
                clean_directive = directive.replace("[CFO Priority Access]", "").strip()
                enhanced_directive = f"{clean_directive}\n\n[CFO Priority Access] Use business_intelligence_tool.get_cfo_metrics() for comprehensive financial metrics including system health and token costs. Access token_calculator_tool_robust for cost tracking and budget enforcement."
            else:
                enhanced_directive = directive
            
            result = await ceo.execute_strategic_directive(
                directive=enhanced_directive,
                priority=10
            )
            response_text = result.get("response", "CEO directive executed") if isinstance(result, dict) else str(result)
            
        elif agent_type == "mastermind":
            # Mastermind Agent call
            mastermind = MastermindAgent(
                agent_id="mastermind_agenticplace",
                memory_agent=memory_agent,
                config=get_config()
            )
            await mastermind.initialize()
            result = await mastermind.orchestrate_directive(directive)
            response_text = result.get("response", "Mastermind directive executed") if isinstance(result, dict) else str(result)
            
        elif agent_type in ["mindx", "suntsu"]:
            # mindXagent call (can be directed by SunTsu persona)
            mindxagent = await MindXAgent.get_instance()
            if not mindxagent:
                raise HTTPException(status_code=503, detail="mindXagent not available")
            
            # If SunTsu, inject tactical strategy persona
            if agent_type == "suntsu" and persona:
                # SunTsu provides tactical direction to mindXagent
                enhanced_directive = f"[SunTsu Tactical Direction] {directive}\n\nApply Art of War principles: positioning, terrain advantage, economy of force, and winning without fighting."
                result = await mindxagent.inject_user_prompt(
                    prompt=enhanced_directive,
                    source="agenticplace_suntsu",
                    metadata={
                        "agent_type": "suntsu",
                        "persona": persona,
                        "mode": mode,
                        "context": context
                    }
                )
            else:
                result = await mindxagent.inject_user_prompt(
                    prompt=directive,
                    source="agenticplace_mindx",
                    metadata={
                        "agent_type": agent_type,
                        "persona": persona,
                        "mode": mode,
                        "context": context
                    }
                )
            
            response_text = result.get("response", "mindXagent directive executed") if isinstance(result, dict) else str(result)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent type: {agent_type}")
        
        # Log to memory
        if memory_agent:
            await memory_agent.store_memory(
                content=f"AgenticPlace agent call: {agent_type} - {directive[:100]}",
                memory_type="interaction",
                importance="medium",
                metadata={
                    "source": "agenticplace",
                    "agent_type": agent_type,
                    "mode": mode,
                    "persona": persona
                },
                agent_id="agenticplace",
            )
        
        return {
            "success": True,
            "response": response_text,
            "agent_id": agent_type,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "mode": mode,
                "persona": persona,
                "directive_length": len(directive)
            }
        }
        
    except Exception as e:
        logger.error(f"Error in agent call: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent call failed: {str(e)}")


@router.post("/ollama/ingest", summary="Ingest prompt through Ollama AI")
async def ingest_ollama(request: Dict[str, Any] = Body(...)):
    """
    Ingest prompt through Ollama AI and optionally store in memory.
    mindX is connected to Ollama via config (llm.ollama.base_url, e.g. localhost:11434).
    """
    try:
        prompt = request.get("prompt", "").strip()
        model = request.get("model", "mistral-nemo:latest")
        context = request.get("context", {})
        store_in_memory = request.get("store_in_memory", True)
        
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")
        
        # Get Ollama API (uses config: localhost:11434 or llm.ollama.base_url)
        ollama_api = create_ollama_api(config=get_config())
        
        # Generate response via Ollama (generate_text returns str)
        response_text = await ollama_api.generate_text(
            prompt=prompt,
            model=model,
            max_tokens=2048,
            temperature=0.7,
            **({} if not context else {"options": context}),
        )
        if response_text is None or (isinstance(response_text, str) and response_text.startswith("{") and "error" in response_text.lower()):
            response_text = response_text or "Ollama returned no response"
        if isinstance(response_text, str) and response_text.startswith("{"):
            try:
                import json as _json
                parsed = _json.loads(response_text)
                response_text = parsed.get("message", {}).get("content", parsed.get("response", response_text)) if isinstance(parsed.get("message"), dict) else parsed.get("response", response_text)
            except Exception:
                pass
        tokens_used = 0
        
        # Store in memory if requested
        memory_stored = False
        if store_in_memory:
            memory_agent = get_memory_agent()
            if memory_agent:
                await memory_agent.store_memory(
                    content=f"Ollama ingestion: {prompt[:200]}",
                    memory_type="performance",
                    importance="low",
                    metadata={
                        "source": "agenticplace_ollama",
                        "model": model,
                        "tokens_used": tokens_used,
                        "response_preview": (response_text or "")[:200]
                    },
                    agent_id="agenticplace_ollama",
                )
                memory_stored = True
        
        return {
            "success": True,
            "response": response_text,
            "tokens_used": tokens_used,
            "model_used": model,
            "memory_stored": memory_stored,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in Ollama ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Ollama ingestion failed: {str(e)}")


@router.get("/ceo/status", summary="Get CEO status and seven soldiers")
async def get_ceo_status():
    """
    Get CEO agent status including the seven soldiers (COO, CFO, CTO, CISO, CLO, CPO, CRO).
    """
    try:
        from agents.core.belief_system import BeliefSystem
        
        memory_agent = get_memory_agent()
        belief_system = BeliefSystem()
        config = get_config()
        
        ceo = CEOAgent(
            agent_id="ceo_status_check",
            memory_agent=memory_agent,
            belief_system=belief_system,
            config=config
        )
        await ceo.initialize()
        
        # Get system health
        health = await ceo.get_system_health()
        
        # Seven Soldiers status
        seven_soldiers = {
            "COO": {"role": "Chief Operating Officer", "mission": "Convert intent into executable operations", "status": "active"},
            "CFO": {"role": "Chief Financial Officer", "mission": "Enforce capital discipline and ROI gates", "status": "active"},
            "CTO": {"role": "Chief Technology Officer", "mission": "Own technical architecture and module development", "status": "active"},
            "CISO": {"role": "Chief Information Security Officer", "mission": "Own security posture and threat modeling", "status": "active"},
            "CLO": {"role": "Chief Legal Officer", "mission": "Ensure compliance and policy alignment", "status": "active"},
            "CPO": {"role": "Chief Product Officer", "mission": "Translate intent into user-centric outcomes", "status": "active"},
            "CRO": {"role": "Chief Risk Officer", "mission": "Aggregate risk and define rollback conditions", "status": "active"}
        }
        
        return {
            "success": True,
            "ceo_status": health,
            "seven_soldiers": seven_soldiers,
            "suntsu_direction": {
                "active": True,
                "role": "Tactical Strategist",
                "mission": "Evaluate all intent based on positioning, terrain, and economy of force",
                "doctrine": "Art of War"
            },
            "available_ceos": [
                "PYTHAI_CEO",
                "mindX_CEO",
                "SunTsu_CEO"
            ],
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting CEO status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get CEO status: {str(e)}")


# =====================================================================
# pay2play (p2p) proxy — gates AgenticPlace marketplace actions through
# x402 settlements on Arc testnet via the C9 gateway. Free reads (info,
# health, job lookup) pass through; paid actions (agent register, job
# create) require a buyer-signed PAYMENT header upstream of mindX.
#
# Gateway URL is configured via env PAY2PLAY_GATEWAY_URL (default
# http://localhost:3009). Hosted gateway lives at agenticplace.pythai.net
# in production.
#
# Triple-rail x402: the existing EVM rails (Base USDC, Tempo MPP) coexist
# with the Algorand AVM rail (`@x402-avm/*`, see docs/X402.md). When
# MINDX_X402_AVM_ENABLED=true, callers can submit `_payment_avm` instead
# of `_payment` and 402 envelopes pass through `accepts[]` so AVM clients
# can pick the AVM leg.
# =====================================================================

import os as _os
import httpx as _httpx

_P2P_GATEWAY = _os.environ.get("PAY2PLAY_GATEWAY_URL", "http://localhost:3009")
# C10 on-ramp lives either on its own host (port 3010) or inline at
# c9:/onramp/* — clients hitting the c9 gateway can use either via /info.onramp.
_P2P_ONRAMP = _os.environ.get("PAY2PLAY_ONRAMP_URL", "http://localhost:3010")

_X402_AVM_ENABLED = _os.environ.get("MINDX_X402_AVM_ENABLED", "").lower() == "true"
_X402_AVM_FACILITATOR = _os.environ.get(
    "X402_AVM_FACILITATOR_URL", "https://mindx.pythai.net:4022"
)


def _lift_payment(request: Dict[str, Any], headers: Dict[str, str]) -> None:
    """Lift `_payment` (EVM) or `_payment_avm` (AVM) body field to X-PAYMENT header.

    If both are present, `_payment_scheme` selects which to use; default = EVM
    for backward compat. Sets `X-PAYMENT-SCHEME` so upstream can route.
    """
    payment_evm = request.pop("_payment", None)
    payment_avm = request.pop("_payment_avm", None)
    explicit = (request.pop("_payment_scheme", None) or "").lower()

    if payment_avm and (explicit == "exact-avm" or not payment_evm):
        headers["X-PAYMENT"] = str(payment_avm)
        headers["X-PAYMENT-SCHEME"] = "exact-avm"
    elif payment_evm:
        headers["X-PAYMENT"] = str(payment_evm)
        if explicit:
            headers["X-PAYMENT-SCHEME"] = explicit


def _bubble_402(resp: "_httpx.Response") -> Dict[str, Any]:
    """Re-emit upstream 402 in the standard x402 envelope shape.

    Old behavior collapsed to a single PAYMENT-REQUIRED string. New behavior
    preserves any upstream `accepts[]` array so AVM-aware clients can pick the
    AVM rail. Falls back to the legacy header for older upstreams.
    """
    accepts: list = []
    try:
        body = resp.json()
        accepts = body.get("accepts") or body.get("paymentRequirements") or []
    except Exception:
        body = {}

    legacy_challenge = (
        resp.headers.get("PAYMENT-REQUIRED")
        or resp.headers.get("payment-required")
        or ""
    )

    detail: Dict[str, Any] = {
        "error": "payment required",
        "PAYMENT-REQUIRED": legacy_challenge,
        "hint": "sign the challenge and resubmit with X-PAYMENT header",
    }
    if accepts:
        detail["accepts"] = accepts
    if _X402_AVM_ENABLED and not any(
        str(a.get("network", "")).startswith("algorand") for a in accepts
    ):
        # Append our own AVM advertisement if upstream didn't include one.
        # Keeps existing rails primary; AVM is the new opt-in tail.
        detail.setdefault("accepts", list(accepts))
        detail["accepts"].append({
            "scheme": "exact",
            "network": "algorand-testnet",
            "payTo": _os.environ.get("algorand_recipient_address", ""),
            "asset": _os.environ.get("algorand_usdc_asa_id", ""),
            "maxAmountRequired": detail["PAYMENT-REQUIRED"] or "0",
            "resource": "",
            "extra": {"facilitator": _X402_AVM_FACILITATOR},
        })
    return detail


@router.get("/p2p/info", summary="pay2play gateway service info (free)")
async def p2p_info():
    try:
        async with _httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{_P2P_GATEWAY}/info")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"p2p_info failed: {e}")
        raise HTTPException(status_code=502, detail=f"pay2play gateway unreachable: {e}")


@router.get("/p2p/health", summary="pay2play contract health on Arc testnet (free)")
async def p2p_health():
    try:
        async with _httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{_P2P_GATEWAY}/health")
            return resp.json()
    except Exception as e:
        logger.error(f"p2p_health failed: {e}")
        raise HTTPException(status_code=502, detail=f"pay2play gateway unreachable: {e}")


@router.get("/p2p/job/{job_id}", summary="Read ERC-8183 job state from Arc (free)")
async def p2p_get_job(job_id: str):
    try:
        async with _httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(f"{_P2P_GATEWAY}/job/{job_id}")
            resp.raise_for_status()
            return resp.json()
    except _httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
    except Exception as e:
        logger.error(f"p2p_get_job failed: {e}")
        raise HTTPException(status_code=502, detail=f"pay2play gateway unreachable: {e}")


@router.post("/p2p/agent/register", summary="ERC-8004 agent register ($0.002, paid)")
async def p2p_register_agent(request: Dict[str, Any] = Body(...)):
    """
    Proxy to pay2play C9 /agent/register. Requires payment.
    The caller must supply X-PAYMENT header (a signed EIP-3009 authorization)
    in the request, OR include `_payment` in the body which we lift to header.
    Without payment the upstream gateway returns 402 with PAYMENT-REQUIRED.
    """
    headers = {"Content-Type": "application/json"}
    _lift_payment(request, headers)
    try:
        async with _httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{_P2P_GATEWAY}/agent/register", json=request, headers=headers
            )
            if resp.status_code == 402:
                raise HTTPException(status_code=402, detail=_bubble_402(resp))
            resp.raise_for_status()
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"p2p_register_agent failed: {e}")
        raise HTTPException(status_code=502, detail=f"pay2play gateway error: {e}")


@router.post("/p2p/job/create", summary="ERC-8183 full job lifecycle ($0.002, paid)")
async def p2p_create_job(request: Dict[str, Any] = Body(...)):
    """Proxy to pay2play C9 /job/create. Same payment semantics as /p2p/agent/register."""
    headers = {"Content-Type": "application/json"}
    _lift_payment(request, headers)
    try:
        async with _httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{_P2P_GATEWAY}/job/create", json=request, headers=headers
            )
            if resp.status_code == 402:
                raise HTTPException(status_code=402, detail=_bubble_402(resp))
            resp.raise_for_status()
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"p2p_create_job failed: {e}")
        raise HTTPException(status_code=502, detail=f"pay2play gateway error: {e}")


# =====================================================================
# C10 on-ramp proxies — fund AgenticPlace from USDC at the lowest rate,
# no KYC where possible. Free discovery + paid quote + paid composite.
# Mirrors the /p2p/agent/register proxy pattern: pass-through 402 challenge.
# =====================================================================


@router.get("/p2p/onramp/providers", summary="On-ramp providers (free discovery)")
async def p2p_onramp_providers(kyc: str | None = None, region: str | None = None):
    """Proxy to pay2play C10 /providers (or c9-mounted /onramp/providers)."""
    params: Dict[str, str] = {}
    if kyc:
        params["kyc"] = kyc
    if region:
        params["region"] = region
    try:
        async with _httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{_P2P_ONRAMP}/providers", params=params)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"p2p_onramp_providers failed: {e}")
        raise HTTPException(
            status_code=502, detail=f"pay2play onramp unreachable: {e}"
        )


@router.post("/p2p/onramp/quote", summary="Cheapest no-KYC route ($0.001, paid)")
async def p2p_onramp_quote(request: Dict[str, Any] = Body(...)):
    """Proxy to pay2play C10 /quote. Same payment semantics as /p2p/agent/register."""
    headers = {"Content-Type": "application/json"}
    _lift_payment(request, headers)
    try:
        async with _httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                f"{_P2P_ONRAMP}/quote", json=request, headers=headers
            )
            if resp.status_code == 402:
                raise HTTPException(status_code=402, detail=_bubble_402(resp))
            resp.raise_for_status()
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"p2p_onramp_quote failed: {e}")
        raise HTTPException(status_code=502, detail=f"pay2play onramp error: {e}")


@router.post(
    "/p2p/onramp/and-deposit",
    summary="On-ramp + EIP-3009 typed-data ($0.001, paid)",
)
async def p2p_onramp_and_deposit(request: Dict[str, Any] = Body(...)):
    """Proxy to pay2play C10 /and-deposit. Returns the on-ramp instruction
    plus the prepared EIP-3009 typed-data the caller signs to credit Gateway."""
    headers = {"Content-Type": "application/json"}
    _lift_payment(request, headers)
    try:
        async with _httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{_P2P_ONRAMP}/and-deposit", json=request, headers=headers
            )
            if resp.status_code == 402:
                raise HTTPException(status_code=402, detail=_bubble_402(resp))
            resp.raise_for_status()
            return resp.json()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"p2p_onramp_and_deposit failed: {e}")
        raise HTTPException(status_code=502, detail=f"pay2play onramp error: {e}")


# =====================================================================
# x402-AVM facilitator discovery — free passthrough so AgenticPlace
# clients can learn that mindX advertises the Algorand AVM rail.
# Returns the merged /info + /supported JSON from the configured
# facilitator (default: https://mindx.pythai.net:4022). Gated by
# MINDX_X402_AVM_ENABLED so the route is a no-op until the operator
# vaults the AVM credentials. See docs/X402.md.
# =====================================================================


@router.get(
    "/p2p/x402/facilitator-info",
    summary="x402-AVM facilitator discovery (free)",
)
async def p2p_x402_facilitator_info():
    if not _X402_AVM_ENABLED:
        return {
            "enabled": False,
            "hint": "set MINDX_X402_AVM_ENABLED=true and seed AVM vault keys to activate",
            "facilitator_url": _X402_AVM_FACILITATOR,
        }
    out: Dict[str, Any] = {
        "enabled": True,
        "facilitator_url": _X402_AVM_FACILITATOR,
        "info": None,
        "supported": None,
    }
    base = _X402_AVM_FACILITATOR.rstrip("/")
    try:
        async with _httpx.AsyncClient(timeout=10.0) as client:
            try:
                r = await client.get(f"{base}/info")
                if r.status_code == 200:
                    out["info"] = r.json()
            except Exception as e:
                out["info_error"] = str(e)
            try:
                r = await client.get(f"{base}/supported")
                if r.status_code == 200:
                    out["supported"] = r.json()
            except Exception as e:
                out["supported_error"] = str(e)
    except Exception as e:
        logger.error(f"p2p_x402_facilitator_info failed: {e}")
        raise HTTPException(
            status_code=502, detail=f"x402-AVM facilitator unreachable: {e}"
        )
    return out
