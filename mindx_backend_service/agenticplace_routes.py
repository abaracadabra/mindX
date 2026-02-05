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
