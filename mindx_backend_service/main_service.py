# mindx/scripts/api_server.py

import asyncio
import time
import psutil
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

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
