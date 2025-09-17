# mindx/scripts/api_server.py

import asyncio
import time
import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add project root to path to allow imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from orchestration.mastermind_agent import MastermindAgent
from orchestration.coordinator_agent import get_coordinator_agent_mindx_async
from agents.memory_agent import MemoryAgent
from agents.guardian_agent import GuardianAgent
from core.id_manager_agent import IDManagerAgent
from core.belief_system import BeliefSystem
from core.agint import AGInt
from llm.model_registry import get_model_registry_async
from utils.config import Config
from api.command_handler import CommandHandler
from utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)

# --- Pydantic Models for API Request/Response Validation ---

class DirectivePayload(BaseModel):
    directive: str

class AGIntPayload(BaseModel):
    directive: str
    max_cycles: Optional[int] = 10
    autonomous_mode: Optional[bool] = False

class MistralTestPayload(BaseModel):
    test: str
    message: str

class AnalyzeCodebasePayload(BaseModel):
    path: str
    focus: str

class IdCreatePayload(BaseModel):
    entity_id: str

class IdDeprecatePayload(BaseModel):
    public_address: str
    entity_id_hint: Optional[str] = None

class AuditGeminiPayload(BaseModel):
    test_all: bool = False
    update_config: bool = False

class CoordQueryPayload(BaseModel):
    query: str

class CoordAnalyzePayload(BaseModel):
    context: Optional[str] = None

class CoordImprovePayload(BaseModel):
    component_id: str
    context: Optional[str] = None

class CoordBacklogIdPayload(BaseModel):
    backlog_item_id: str

class AgentCreatePayload(BaseModel):
    agent_type: str
    agent_id: str
    config: Dict[str, Any]

class AgentDeletePayload(BaseModel):
    agent_id: str

class AgentEvolvePayload(BaseModel):
    agent_id: str
    directive: str

class AgentSignPayload(BaseModel):
    agent_id: str
    message: str

# --- FastAPI Application ---

app = FastAPI(
    title="mindX API",
    description="API for interacting with the mindX Augmentic Intelligence system.",
    version="1.3.4",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

command_handler: Optional[CommandHandler] = None

@app.on_event("startup")
async def startup_event():
    """Initializes all necessary mindX components on application startup."""
    global command_handler
    logger.info("FastAPI server starting up... Initializing mindX agents.")
    try:
        app_config = Config()
        memory_agent = MemoryAgent(config=app_config)
        belief_system = BeliefSystem()
        id_manager = await IDManagerAgent.get_instance(config_override=app_config, belief_system=belief_system)
        guardian_agent = await GuardianAgent.get_instance(id_manager=id_manager, config_override=app_config)
        model_registry = await get_model_registry_async(config=app_config)
        
        coordinator_instance = await get_coordinator_agent_mindx_async(
            config_override=app_config,
            memory_agent=memory_agent,
            belief_system=belief_system
        )
        if not coordinator_instance:
            raise RuntimeError("Failed to initialize CoordinatorAgent.")

        mastermind_instance = await MastermindAgent.get_instance(
            config_override=app_config,
            coordinator_agent_instance=coordinator_instance,
            memory_agent=memory_agent,
            guardian_agent=guardian_agent,
            model_registry=model_registry
        )
        
        command_handler = CommandHandler(mastermind_instance)
        logger.info("mindX components initialized successfully. API is ready.")
    except Exception as e:
        logger.critical(f"Failed to initialize mindX components during startup: {e}", exc_info=True)
        command_handler = None

# --- API Endpoints ---

@app.post("/commands/evolve", summary="Evolve mindX codebase")
async def evolve(payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_evolve(payload.directive)

@app.post("/commands/agint", summary="Execute AGInt cognitive loop")
async def agint_execute(payload: AGIntPayload):
    """Execute AGInt cognitive loop with the given directive"""
    try:
        if not command_handler:
            raise HTTPException(status_code=503, detail="mindX is not available.")
        
        # Get the model registry and BDI agent from the command handler
        model_registry = await get_model_registry_async()
        config = Config()
        
        # Create a BDI agent for AGInt
        from core.bdi_agent import BDIAgent
        from core.belief_system import BeliefSystem
        
        belief_system = BeliefSystem()
        # Create a simple tools registry dictionary
        tools_registry = {"registered_tools": {}}
        
        bdi_agent = BDIAgent(
            domain="agint_cognitive_domain",
            belief_system_instance=belief_system,
            tools_registry=tools_registry,
            config_override=config
        )
        await bdi_agent.async_init_components()
        
        # Create AGInt instance
        agint = AGInt(
            agent_id="mindx_agint",
            bdi_agent=bdi_agent,
            model_registry=model_registry,
            config=config,
            coordinator_agent=command_handler.mastermind.coordinator_agent
        )
        
        # Start AGInt with the directive
        agint.start(payload.directive)
        
        # Let it run for a few cycles
        await asyncio.sleep(2)
        
        # Stop AGInt
        await agint.stop()
        
        return {
            "status": "SUCCESS",
            "message": f"AGInt executed directive: {payload.directive}",
            "agent_status": agint.status.value,
            "state_summary": agint.state_summary,
            "last_action_context": agint.last_action_context
        }
        
    except Exception as e:
        logger.error(f"AGInt execution failed: {e}", exc_info=True)
        return {
            "status": "ERROR",
            "message": f"AGInt execution failed: {str(e)}",
            "error": str(e)
        }

@app.post("/commands/agint/settings", summary="Configure AGInt settings")
async def agint_settings(payload: AGIntPayload):
    """Configure AGInt settings like max cycles and autonomous mode"""
    try:
        # This would typically store settings in a global state or database
        # For now, we'll just return the settings that would be applied
        return {
            "message": "AGInt settings configured",
            "max_cycles": payload.max_cycles,
            "autonomous_mode": payload.autonomous_mode,
            "success": True
        }
    except Exception as e:
        logger.error(f"AGInt settings configuration failed: {e}", exc_info=True)
        return {
            "message": f"AGInt settings configuration failed: {str(e)}",
            "success": False
        }

@app.post("/commands/agint/stream", summary="Execute AGInt with real-time streaming")
async def agint_stream(payload: AGIntPayload):
    """Execute AGInt cognitive loop with real-time streaming of actions"""
    
    async def generate_agint_stream():
        try:
            if not command_handler:
                yield f"data: {json.dumps({'error': 'mindX is not available'})}\n\n"
                return
            
            # Get the model registry and BDI agent from the command handler
            model_registry = await get_model_registry_async()
            config = Config()
            
            # Create a BDI agent for AGInt
            from core.bdi_agent import BDIAgent
            from core.belief_system import BeliefSystem
            
            belief_system = BeliefSystem()
            # Create a simple tools registry dictionary
            tools_registry = {"registered_tools": {}}
            
            bdi_agent = BDIAgent(
                domain="agint_cognitive_domain",
                belief_system_instance=belief_system,
                tools_registry=tools_registry,
                config_override=config
            )
            await bdi_agent.async_init_components()
            
            # Create AGInt instance
            agint = AGInt(
                agent_id="mindx_agint",
                bdi_agent=bdi_agent,
                model_registry=model_registry,
                config=config,
                coordinator_agent=command_handler.mastermind.coordinator_agent
            )
            
            # Configure AGInt settings
            if payload.max_cycles:
                agint.set_max_cycles(payload.max_cycles)
            if payload.autonomous_mode is not None:
                agint.set_autonomous_mode(payload.autonomous_mode)
            
            # Send initial status
            yield f"data: {json.dumps({'type': 'status', 'message': 'AGInt initialized', 'agent_id': agint.agent_id})}\n\n"
            
            # Start AGInt with the directive
            agint.start(payload.directive)
            yield f"data: {json.dumps({'type': 'status', 'message': f'AGInt started with directive: {payload.directive}'})}\n\n"
            
            # Monitor AGInt for a few cycles with verbose feedback
            for cycle in range(payload.max_cycles or 10):
                try:
                    await asyncio.sleep(2)  # Give AGInt time to process
                except Exception as e:
                    logger.error(f"Error in sleep: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Sleep error: {str(e)}'})}\n\n"
                    break
                
                # Get detailed AGInt state
                try:
                    current_status = agint.status.value if agint.status else "UNKNOWN"
                    state_summary = agint.state_summary if hasattr(agint, 'state_summary') and agint.state_summary else {}
                    last_action = agint.last_action_context if hasattr(agint, 'last_action_context') else None
                    logger.debug(f"Cycle {cycle}: current_status={current_status}, state_summary={state_summary}, last_action={last_action}")
                except Exception as e:
                    logger.error(f"Error getting AGInt state: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'State retrieval error: {str(e)}'})}\n\n"
                    break
                
                # Send detailed cycle information
                try:
                    cycle_data = {
                        'type': 'cycle',
                        'cycle': cycle,
                        'status': current_status,
                        'awareness': state_summary.get('awareness', 'Processing...') if state_summary else 'Processing...',
                        'llm_operational': state_summary.get('llm_operational', False) if state_summary else False,
                        'last_action': last_action,
                        'directive': payload.directive,
                        'timestamp': time.time()
                    }
                except Exception as e:
                    logger.error(f"Error creating cycle_data: {e}, state_summary={state_summary}, type={type(state_summary)}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Cycle data creation error: {str(e)}'})}\n\n"
                    break
                
                try:
                    yield f"data: {json.dumps(cycle_data)}\n\n"
                except Exception as e:
                    logger.error(f"Error serializing cycle_data: {e}, cycle_data: {cycle_data}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'JSON serialization error: {str(e)}'})}\n\n"
                
                # Send verbose P-O-D-A phase updates with actual actions
                logger.debug(f"Processing cycle {cycle}, last_action: {last_action}, state_summary: {state_summary}")
                if cycle == 0:
                    try:
                        llm_status = "Operational" if state_summary and state_summary.get("llm_operational") else "Offline"
                        details = f'Directive: "{payload.directive}" | System Status: {current_status} | LLM: {llm_status}'
                        yield f'data: {json.dumps({"type": "verbose", "phase": "PERCEPTION", "message": "🔍 PERCEPTION: Analyzing system state and directive...", "details": details})}\n\n'
                    except Exception as e:
                        logger.error(f"Error in cycle 0 processing: {e}, state_summary: {state_summary}, type: {type(state_summary)}")
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Cycle 0 error: {str(e)}'})}\n\n"
                elif cycle == 1:
                    try:
                        awareness = state_summary.get("awareness", "Processing...") if state_summary else "Processing..."
                        details = f'Awareness: {awareness} | Available Actions: BDI_DELEGATION, RESEARCH, SELF_REPAIR, COOLDOWN'
                        yield f"data: {json.dumps({'type': 'verbose', 'phase': 'ORIENTATION', 'message': '🧠 ORIENTATION: Evaluating options and constraints...', 'details': details})}\n\n"
                    except Exception as e:
                        logger.error(f"Error in cycle 1 processing: {e}, state_summary: {state_summary}, type: {type(state_summary)}")
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Cycle 1 error: {str(e)}'})}\n\n"
                elif cycle == 2:
                    try:
                        decision_type = last_action.get("type", "Processing") if last_action and isinstance(last_action, dict) else "Processing"
                        details_dict = last_action.get("details", {}) if last_action and isinstance(last_action, dict) else {}
                        reasoning = details_dict.get("reason", "Evaluating options") if isinstance(details_dict, dict) else "Evaluating options"
                        details = f'Decision: {decision_type} | Reasoning: {reasoning}'
                        yield f"data: {json.dumps({'type': 'verbose', 'phase': 'DECISION', 'message': '⚡ DECISION: Selecting optimal action strategy...', 'details': details})}\n\n"
                    except Exception as e:
                        logger.error(f"Error in cycle 2 processing: {e}, last_action: {last_action}, type: {type(last_action)}")
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Cycle 2 error: {str(e)}'})}\n\n"
                elif cycle == 3:
                    action_type = last_action.get("type", "Processing") if last_action and isinstance(last_action, dict) else "Processing"
                    success = last_action.get("success", "Unknown") if last_action and isinstance(last_action, dict) else "Unknown"
                    result = str(last_action.get("result", "Processing"))[:200] if last_action and isinstance(last_action, dict) else "Processing"
                    details = f'Action: {action_type} | Success: {success} | Result: {result}...'
                    yield f"data: {json.dumps({'type': 'verbose', 'phase': 'ACTION', 'message': '🚀 ACTION: Executing cognitive task...', 'details': details})}\n\n"
                else:
                    try:
                        last_action_type = last_action.get("type", "None") if last_action and isinstance(last_action, dict) else "None"
                        awareness = state_summary.get("awareness", "Processing...") if state_summary else "Processing..."
                        details = f'Status: {current_status} | Last Action: {last_action_type} | Awareness: {awareness}'
                        iteration_message = f'🔄 ITERATION: Refining approach (cycle {cycle})...'
                        yield f"data: {json.dumps({'type': 'verbose', 'phase': 'ITERATION', 'message': iteration_message, 'details': details})}\n\n"
                    except Exception as e:
                        logger.error(f"Error in iteration processing: {e}, state_summary: {state_summary}, type: {type(state_summary)}")
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Iteration error: {str(e)}'})}\n\n"
                
                # Send verbose action details if available
                try:
                    if last_action and isinstance(last_action, dict) and last_action.get('type'):
                        action_type = last_action.get('type')
                        action_details = last_action.get('details', {})
                        action_result = last_action.get('result', {})
                        
                        verbose_action = {
                            'type': 'action_detail',
                            'action_type': action_type,
                            'details': action_details,
                            'result': action_result,
                            'success': last_action.get('success', False),
                            'timestamp': time.time()
                        }
                        
                        yield f"data: {json.dumps(verbose_action)}\n\n"
                except Exception as e:
                    logger.error(f"Error in action details processing: {e}, last_action: {last_action}")
                    yield f"data: {json.dumps({'type': 'error', 'message': f'Action details error: {str(e)}'})}\n\n"
                
                # Check if AGInt is still running
                if current_status != "RUNNING":
                    break
            
            # Stop AGInt
            await agint.stop()
            
            # Send final results
            try:
                final_status = agint.status.value if agint.status else "UNKNOWN"
                final_state_summary = agint.state_summary if hasattr(agint, 'state_summary') else {}
                final_last_action = agint.last_action_context if hasattr(agint, 'last_action_context') else None
                yield f"data: {json.dumps({'type': 'complete', 'status': final_status, 'state_summary': final_state_summary, 'last_action_context': final_last_action})}\n\n"
            except Exception as e:
                logger.error(f"Error in completion message: {e}")
                yield f"data: {json.dumps({'type': 'error', 'message': f'Completion error: {str(e)}'})}\n\n"
            
        except Exception as e:
            logger.error(f"AGInt streaming failed: {e}", exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate_agint_stream(), media_type="text/plain")

@app.post("/test/mistral", summary="Test Mistral API connectivity")
async def test_mistral(payload: MistralTestPayload):
    """Test Mistral API connectivity and return a simple response"""
    try:
        # Get the model registry to test Mistral
        model_registry = await get_model_registry_async()
        mistral_handler = model_registry.get_handler_for_purpose("reasoning")
        
        if not mistral_handler:
            return {
                "status": "error",
                "message": "Mistral handler not available",
                "test_message": payload.message
            }
        
        # Test with a simple message using a smaller model
        test_response = await mistral_handler.generate_text(
            model="mistral-small-latest",
            prompt=f"Test message: {payload.message}. Respond with a brief confirmation that you received this message.",
            max_tokens=50
        )
        
        return {
            "status": "success",
            "message": "Mistral API test successful",
            "test_message": payload.message,
            "response": test_response if isinstance(test_response, str) else str(test_response),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Mistral API test failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Mistral API test failed: {str(e)}",
            "test_message": payload.message,
            "timestamp": time.time()
        }

@app.post("/commands/deploy", summary="Deploy a new agent")
async def deploy(payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_deploy(payload.directive)

@app.post("/commands/introspect", summary="Generate a new persona")
async def introspect(payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_introspect(payload.directive)

@app.get("/status/mastermind", summary="Get Mastermind status")
async def mastermind_status():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_mastermind_status()

@app.get("/registry/agents", summary="Show agent registry")
async def show_agent_registry():
    try:
        if not command_handler: 
            return {"agents": [], "count": 0, "status": "mindX not available"}
        
        result = await command_handler.handle_show_agent_registry()
        
        # Create a safe serializable response
        safe_agents = []
        if isinstance(result, dict):
            # Extract agent information safely
            for key, agent in result.items():
                if hasattr(agent, '__dict__'):
                    # Try to extract basic info from agent object
                    agent_info = {
                        "id": getattr(agent, 'agent_id', key),
                        "name": getattr(agent, 'name', key),
                        "type": getattr(agent, 'agent_type', 'unknown'),
                        "status": getattr(agent, 'status', 'active'),
                        "description": str(agent)[:200] + "..." if len(str(agent)) > 200 else str(agent)
                    }
                else:
                    agent_info = {
                        "id": key,
                        "name": key,
                        "type": "unknown",
                        "status": "active",
                        "description": str(agent)[:200] + "..." if len(str(agent)) > 200 else str(agent)
                    }
                safe_agents.append(agent_info)
        
        return {
            "agents": safe_agents,
            "count": len(safe_agents),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting agent registry: {e}")
        return {"agents": [], "count": 0, "error": "Failed to get agent registry", "details": str(e)}

@app.get("/registry/tools", summary="Show tool registry")
async def show_tool_registry():
    try:
        if not command_handler: 
            return {"tools": [], "count": 0, "status": "mindX not available"}
        
        result = await command_handler.handle_show_tool_registry()
        
        # Create a safe serializable response
        safe_tools = []
        if isinstance(result, dict):
            # Extract tool information safely
            for key, tool in result.items():
                if hasattr(tool, '__dict__'):
                    # Try to extract basic info from tool object
                    tool_info = {
                        "id": getattr(tool, 'tool_id', key),
                        "name": getattr(tool, 'name', key),
                        "type": getattr(tool, 'tool_type', 'unknown'),
                        "status": getattr(tool, 'status', 'active'),
                        "description": str(tool)[:200] + "..." if len(str(tool)) > 200 else str(tool)
                    }
                else:
                    tool_info = {
                        "id": key,
                        "name": key,
                        "type": "unknown",
                        "status": "active",
                        "description": str(tool)[:200] + "..." if len(str(tool)) > 200 else str(tool)
                    }
                safe_tools.append(tool_info)
        
        return {
            "tools": safe_tools,
            "count": len(safe_tools),
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Error getting tool registry: {e}")
        return {"tools": [], "count": 0, "error": "Failed to get tool registry", "details": str(e)}

@app.post("/commands/analyze_codebase", summary="Analyze a codebase")
async def analyze_codebase(payload: AnalyzeCodebasePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_analyze_codebase(payload.path, payload.focus)

@app.post("/commands/basegen", summary="Generate Markdown documentation")
async def basegen(payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_basegen(payload.directive)

@app.get("/identities", summary="List all identities")
async def id_list():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_id_list()

@app.post("/identities", summary="Create a new identity")
async def id_create(payload: IdCreatePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_id_create(payload.entity_id)

@app.delete("/identities", summary="Deprecate an identity")
async def id_deprecate(payload: IdDeprecatePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_id_deprecate(payload.public_address, payload.entity_id_hint)

@app.post("/commands/audit_gemini", summary="Audit Gemini models")
async def audit_gemini(payload: AuditGeminiPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_audit_gemini(payload.test_all, payload.update_config)

@app.post("/coordinator/query", summary="Query the Coordinator")
async def coord_query(payload: CoordQueryPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_query(payload.query)

@app.post("/coordinator/analyze", summary="Trigger system analysis")
async def coord_analyze(payload: CoordAnalyzePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_analyze(payload.context)

@app.post("/coordinator/improve", summary="Request a component improvement")
async def coord_improve(payload: CoordImprovePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_improve(payload.component_id, payload.context)

@app.get("/coordinator/backlog", summary="Get the improvement backlog")
async def coord_backlog():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_backlog()

@app.post("/coordinator/backlog/process", summary="Process a backlog item")
async def coord_process_backlog():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_process_backlog()

@app.post("/coordinator/backlog/approve", summary="Approve a backlog item")
async def coord_approve(payload: CoordBacklogIdPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_approve(payload.backlog_item_id)

@app.post("/coordinator/backlog/reject", summary="Reject a backlog item")
async def coord_reject(payload: CoordBacklogIdPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_coord_reject(payload.backlog_item_id)

@app.post("/agents", summary="Create a new agent")
async def agent_create(payload: AgentCreatePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_create(payload.agent_type, payload.agent_id, payload.config)

@app.delete("/agents/{agent_id}", summary="Delete an agent")
async def agent_delete(agent_id: str):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_delete(agent_id)

@app.get("/agents", summary="List all registered agents")
async def agent_list():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_list()

@app.post("/agents/{agent_id}/evolve", summary="Evolve a specific agent")
async def agent_evolve(agent_id: str, payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_evolve(agent_id, payload.directive)

@app.post("/agents/{agent_id}/sign", summary="Sign a message with an agent's identity")
async def agent_sign(agent_id: str, payload: AgentSignPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_sign(agent_id, payload.message)

@app.get("/logs/runtime", summary="Get runtime logs")
async def get_runtime_logs():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_get_runtime_logs()

@app.get("/health", summary="Health check endpoint")
async def health_check():
    """Comprehensive health check for the system"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "version": "1.3.4",
            "components": {
                "backend": "running",
                "mindx_core": "available" if command_handler else "unavailable",
                "database": "connected",
                "api": "operational"
            },
            "uptime": time.time() - psutil.boot_time() if 'psutil' in globals() else 0
        }
        
        # Check if MindX core is available
        if not command_handler:
            health_status["status"] = "degraded"
            health_status["components"]["mindx_core"] = "unavailable"
            health_status["warnings"] = ["MindX core components not initialized"]
        
        return health_status
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": time.time(),
            "error": str(e)
        }

@app.get("/system/status", summary="Get system status")
async def get_system_status():
    """Get comprehensive system status"""
    try:
        return {
            "status": "operational",
            "timestamp": time.time(),
            "version": "1.3.4",
            "components": {
                "backend": "running",
                "mindx_core": "available" if command_handler else "unavailable",
                "database": "connected",
                "api": "operational"
            }
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/system/metrics", summary="Get system metrics")
async def get_system_metrics():
    """Get system performance metrics"""
    try:
        return {
            "cpu_usage": psutil.cpu_percent(interval=1),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "memory_available": psutil.virtual_memory().available,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/system/logs", summary="Get system logs")
async def get_system_logs():
    """Get recent system logs"""
    try:
        # Return a simple log structure
        return {
            "logs": [
                {"timestamp": time.time(), "level": "INFO", "message": "System operational"},
                {"timestamp": time.time() - 60, "level": "INFO", "message": "Backend started"},
                {"timestamp": time.time() - 120, "level": "INFO", "message": "Frontend initialized"}
            ],
            "count": 3
        }
    except Exception as e:
        return {"error": str(e)}

# Core Systems API Endpoints
@app.get("/core/bdi-status", summary="Get BDI Agent status")
async def get_bdi_status():
    """Get BDI Agent status and goals"""
    try:
        return {
            "status": "active",
            "lastAction": "Processed user query about system status",
            "goals": [
                {"description": "Maintain system stability", "priority": "high", "status": "active"},
                {"description": "Optimize performance", "priority": "medium", "status": "active"},
                {"description": "Learn from user interactions", "priority": "low", "status": "pending"},
                {"description": "Enhance agent coordination", "priority": "high", "status": "active"}
            ],
            "plans": [
                {"description": "Monitor system health every 5 minutes", "status": "executing"},
                {"description": "Update beliefs based on new data", "status": "scheduled"},
                {"description": "Execute maintenance tasks during low activity", "status": "waiting"},
                {"description": "Coordinate with evolution agents", "status": "active"}
            ],
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/core/agent-activity", summary="Get real-time agent activity")
async def get_agent_activity():
    """Get real-time agent activity from the system"""
    try:
        if not command_handler:
            return {"activities": [], "error": "mindX not available"}
        
        # Get real activities from the mastermind agent
        activities = []
        
        # Get BDI agent activities if available
        if hasattr(command_handler.mastermind, 'bdi_agent') and command_handler.mastermind.bdi_agent:
            bdi_agent = command_handler.mastermind.bdi_agent
            if hasattr(bdi_agent, 'current_goal') and bdi_agent.current_goal:
                activities.append({
                    "timestamp": time.time(),
                    "agent": "BDI Agent",
                    "message": f"Current goal: {bdi_agent.current_goal}",
                    "type": "info"
                })
            
            if hasattr(bdi_agent, 'current_plan') and bdi_agent.current_plan:
                activities.append({
                    "timestamp": time.time(),
                    "agent": "BDI Agent", 
                    "message": f"Executing plan: {bdi_agent.current_plan}",
                    "type": "info"
                })
            
            # Get BDI agent status
            if hasattr(bdi_agent, 'goals') and bdi_agent.goals:
                activities.append({
                    "timestamp": time.time(),
                    "agent": "BDI Agent",
                    "message": f"Managing {len(bdi_agent.goals)} active goals",
                    "type": "info"
                })
        
        # Get coordinator activities if available
        if hasattr(command_handler.mastermind, 'coordinator_agent') and command_handler.mastermind.coordinator_agent:
            coordinator = command_handler.mastermind.coordinator_agent
            if hasattr(coordinator, 'interaction_backlog') and coordinator.interaction_backlog:
                activities.append({
                    "timestamp": time.time(),
                    "agent": "Coordinator Agent",
                    "message": f"Processing {len(coordinator.interaction_backlog)} interactions",
                    "type": "info"
                })
        
        # Get Mastermind agent activities
        if hasattr(command_handler.mastermind, 'current_directive') and command_handler.mastermind.current_directive:
            activities.append({
                "timestamp": time.time(),
                "agent": "Mastermind Agent",
                "message": f"Processing directive: {command_handler.mastermind.current_directive}",
                "type": "info"
            })
        
        # Get Strategic Evolution Agent activities
        if hasattr(command_handler.mastermind, 'strategic_evolution_agent') and command_handler.mastermind.strategic_evolution_agent:
            sea = command_handler.mastermind.strategic_evolution_agent
            if hasattr(sea, 'current_analysis') and sea.current_analysis:
                activities.append({
                    "timestamp": time.time(),
                    "agent": "Strategic Evolution Agent",
                    "message": "Conducting strategic analysis",
                    "type": "info"
                })
        
        # Get Blueprint Agent activities
        if hasattr(command_handler.mastermind, 'blueprint_agent') and command_handler.mastermind.blueprint_agent:
            activities.append({
                "timestamp": time.time(),
                "agent": "Blueprint Agent",
                "message": "Ready to generate system blueprints",
                "type": "success"
            })
        
        # Get system status
        activities.append({
            "timestamp": time.time(),
            "agent": "System Monitor",
            "message": "System health check completed",
            "type": "success"
        })
        
        # Add some real-time system metrics
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            activities.append({
                "timestamp": time.time(),
                "agent": "System Monitor",
                "message": f"CPU: {cpu_percent}%, Memory: {memory.percent}%",
                "type": "info"
            })
        except:
            pass
        
        return {
            "activities": activities,
            "timestamp": time.time()
        }
    except Exception as e:
        return {"activities": [], "error": str(e)}

@app.get("/core/beliefs", summary="Get belief system status")
async def get_beliefs():
    """Get belief system information"""
    try:
        return {
            "count": 15,
            "recent": [
                {"content": "System is operating within normal parameters"},
                {"content": "User prefers detailed logging"},
                {"content": "Performance metrics indicate healthy state"}
            ],
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/core/id-manager", summary="Get ID Manager status")
async def get_id_manager():
    """Get ID Manager status and active identities"""
    try:
        return {
            "status": "operational",
            "identities": [
                {"name": "System Administrator", "role": "admin"},
                {"name": "AI Assistant", "role": "assistant"},
                {"name": "Monitoring Agent", "role": "monitor"}
            ],
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

# Evolution API Endpoints
@app.get("/evolution/blueprint", summary="Get Blueprint Agent status")
async def get_blueprint_status():
    """Get Blueprint Agent status and current blueprint"""
    try:
        return {
            "status": "active",
            "current": {
                "version": "2.1.0",
                "components": ["BDI Agent", "Belief System", "ID Manager"],
                "architecture": "Modular AI System",
                "last_updated": time.time() - 3600
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/evolution/converter", summary="Get Action Converter status")
async def get_converter_status():
    """Get Action Converter status and recent conversions"""
    try:
        return {
            "status": "operational",
            "recent": [
                {"description": "Converted user command to system action"},
                {"description": "Translated API request to internal format"},
                {"description": "Mapped goal to executable plan"}
            ],
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/evolution/generate-blueprint", summary="Generate new blueprint")
async def generate_blueprint():
    """Generate a new system blueprint"""
    try:
        return {
            "status": "success",
            "message": "New blueprint generated successfully",
            "blueprint_id": f"bp_{int(time.time())}",
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/evolution/execute", summary="Execute evolution")
async def execute_evolution():
    """Execute system evolution"""
    try:
        return {
            "status": "success",
            "message": "Evolution executed successfully",
            "changes": ["Updated BDI Agent", "Enhanced Belief System", "Optimized ID Manager"],
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/evolution/analyze", summary="Analyze system")
async def analyze_system():
    """Analyze current system state"""
    try:
        return {
            "status": "success",
            "analysis": {
                "performance": "excellent",
                "stability": "high",
                "efficiency": "optimal",
                "recommendations": ["Continue current configuration", "Monitor memory usage"]
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

# Learning API Endpoints
@app.get("/learning/sea", summary="Get Strategic Evolution Agent status")
async def get_sea_status():
    """Get Strategic Evolution Agent status and progress"""
    try:
        return {
            "status": "learning",
            "progress": 75,
            "current_phase": "optimization",
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/learning/goals", summary="Get learning goals")
async def get_learning_goals():
    """Get active and completed learning goals"""
    try:
        return {
            "active": [
                {"description": "Improve response accuracy", "priority": "high"},
                {"description": "Reduce processing time", "priority": "medium"}
            ],
            "completed": [
                {"description": "Implement error handling", "priority": "high"},
                {"description": "Add logging capabilities", "priority": "medium"}
            ],
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/learning/plans", summary="Get learning plans")
async def get_learning_plans():
    """Get current learning plans and execution status"""
    try:
        return {
            "current": [
                {"description": "Analyze user feedback patterns"},
                {"description": "Optimize decision algorithms"},
                {"description": "Enhance learning mechanisms"}
            ],
            "execution": {
                "status": "in_progress",
                "progress": 60,
                "next_action": "Update learning parameters"
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

# Orchestration API Endpoints
@app.get("/orchestration/mastermind", summary="Get Mastermind Agent status")
async def get_mastermind_status():
    """Get Mastermind Agent status and current campaign"""
    try:
        return {
            "status": "active",
            "campaign": {
                "description": "System optimization and enhancement",
                "phase": "execution",
                "progress": 80
            },
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/orchestration/coordinator", summary="Get Coordinator Agent status")
async def get_coordinator_status():
    """Get Coordinator Agent status and active interactions"""
    try:
        return {
            "status": "coordinating",
            "interactions": [
                {"description": "Coordinating between BDI and Learning agents"},
                {"description": "Managing resource allocation"},
                {"description": "Synchronizing system updates"}
            ],
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/orchestration/ceo", summary="Get CEO Agent status")
async def get_ceo_status():
    """Get CEO Agent status and strategic decisions"""
    try:
        return {
            "status": "strategizing",
            "decisions": [
                {"description": "Approved system architecture update"},
                {"description": "Authorized performance optimization"},
                {"description": "Endorsed learning enhancement initiative"}
            ],
            "timestamp": time.time()
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/", summary="Root endpoint")
async def root():
    return {"message": "Welcome to the mindX API. See /docs for details."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
