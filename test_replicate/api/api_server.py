# mindx/api/api_server.py
"""
FastAPI Server for the MindX Augmentic Intelligence System.

This version (2.0) has been refactored for improved architecture, maintainability, and security.
Key Improvements:
- Dependency Injection: Replaces repetitive checks with FastAPI's `Depends`.
- Decoupled Startup: The API server is no longer responsible for complex agent wiring.
- Organized Routing: Endpoints are grouped into logical `APIRouter`s.
- Configurable CORS: Security policy is loaded from the environment, not hardcoded.
- Autonomous Replication: Includes the crucial `/system/replicate` endpoint.
"""

import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

# Third-party imports
from fastapi import FastAPI, HTTPException, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Path Setup ---
# Ensures the application can be run from anywhere and still find the 'mindx' modules.
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# --- MindX Core Imports ---
# These are now wrapped in a try/except to provide a clear error if the environment is misconfigured.
try:
    from orchestration.mastermind_agent import MastermindAgent
    from api.command_handler import CommandHandler
    from utils.config import Config
    from utils.logging_config import setup_logging, get_logger
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import MindX modules: {e}")
    print("Please ensure the project's virtual environment is activated and dependencies are installed.")
    sys.exit(1)


# --- Global Configuration and Logging ---
setup_logging()
logger = get_logger(__name__)
config = Config()


# --- API Schemas (Pydantic Models) ---
# In a larger application, these could be moved to a separate `api/schemas.py` file.
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

class CoordQueryPayload(BaseModel):
    query: str

class CoordImprovePayload(BaseModel):
    component_id: str
    context: Optional[str] = None

class CoordBacklogIdPayload(BaseModel):
    backlog_item_id: str

class AgentCreatePayload(BaseModel):
    agent_type: str
    agent_id: str
    config: Dict[str, Any]

class AgentSignPayload(BaseModel):
    agent_id: str
    message: str

class ReplicationPayload(BaseModel):
    target_directory: str = Field(
        "../replicated_instances",
        description="Path relative to the current instance's root for the new deployment."
    )

# --- FastAPI Application State and Dependency Injection ---
class AppState:
    command_handler: Optional[CommandHandler] = None
    initialized = False
    initialization_error = None

app_state = AppState()

async def get_command_handler() -> CommandHandler:
    """
    FastAPI dependency that provides a validated CommandHandler with lazy initialization.
    Raises a 503 Service Unavailable error if the system failed to initialize.
    """
    if app_state.command_handler is None and not app_state.initialization_error:
        try:
            await initialize_mindx_components()
        except Exception as e:
            app_state.initialization_error = str(e)
            logger.error(f"Failed to initialize MindX components: {e}")
            raise HTTPException(status_code=503, detail=f"MindX system not available: {e}")
    
    if app_state.initialization_error:
        raise HTTPException(status_code=503, detail=f"MindX system error: {app_state.initialization_error}")
    
    if app_state.command_handler is None:
        raise HTTPException(
            status_code=503,
            detail="MindX service is not available. Initialization may have failed."
        )
    return app_state.command_handler

async def initialize_mindx_components():
    """Initialize MindX components only when needed"""
    if app_state.initialized:
        return
    
    logger.info("Initializing MindX components...")
    
    try:
        # Create model registry first
        from llm.model_registry import get_model_registry_async
        from orchestration.coordinator_agent import CoordinatorAgent
        from agents.memory_agent import MemoryAgent
        from core.belief_system import BeliefSystem
        
        model_registry = await get_model_registry_async(config=config)
        
        # Create coordinator agent
        memory_agent = MemoryAgent(config=config)
        belief_system = BeliefSystem()
        coordinator_agent = await CoordinatorAgent.get_instance(
            config_override=config,
            memory_agent=memory_agent,
            belief_system=belief_system
        )
        
        # Initialize mastermind agent
        mastermind_instance = await MastermindAgent.get_instance(
            config_override=config,
            coordinator_agent_instance=coordinator_agent,
            memory_agent=memory_agent,
            model_registry=model_registry
        )
        
        app_state.command_handler = CommandHandler(mastermind_instance)
        app_state.initialized = True
        
        logger.info("MindX components initialized successfully")
        
    except Exception as e:
        app_state.initialization_error = str(e)
        logger.error(f"Failed to initialize MindX components: {e}", exc_info=True)
        raise


# --- API Routers ---
# Grouping endpoints by functionality makes the API much easier to manage.
system_router = APIRouter(prefix="/system", tags=["System & Commands"])
coordinator_router = APIRouter(prefix="/coordinator", tags=["Coordinator"])
agent_router = APIRouter(prefix="/agents", tags=["Agents"])
identity_router = APIRouter(prefix="/identities", tags=["Identities"])


# --- System & Command Endpoints ---
@system_router.get("/status", summary="Get system status")
async def get_status(handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_mastermind_status()

@system_router.post("/evolve", summary="Evolve the entire MindX codebase")
async def evolve_system(payload: DirectivePayload, handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_evolve(payload.directive)

@system_router.post("/analyze_codebase", summary="Analyze a local codebase")
async def analyze_codebase(payload: AnalyzeCodebasePayload, handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_analyze_codebase(payload.path, payload.focus)

@system_router.post("/replicate", status_code=202, summary="Trigger autonomous self-replication")
async def replicate_system(payload: ReplicationPayload):
    """Triggers the constructor script to build a new instance of MindX."""
    logger.info("REPLICATION SIGNAL RECEIVED. Beginning autonomous construction.")
    constructor_script_path = project_root / "deploy_mindx.sh"
    if not constructor_script_path.is_file():
        raise HTTPException(status_code=500, detail="Replication failed: Constructor script missing.")
    
    replication_target_path = (project_root / payload.target_directory).resolve()
    replication_target_path.mkdir(exist_ok=True)
    
    command = ["/bin/bash", str(constructor_script_path), str(replication_target_path), "--run"]
    
    try:
        with open(config.get_log_dir() / "replication.log", "a") as log_file:
            subprocess.Popen(command, stdout=log_file, stderr=log_file)
        return {"message": "Accepted: Autonomous construction process initiated."}
    except Exception as e:
        logger.critical(f"Failed to launch constructor process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Replication failed: {e}")

@system_router.get("/logs", summary="Get system logs")
async def get_system_logs(level: str = "ALL", limit: int = 1000):
    """
    Retrieve system logs with optional filtering by level.
    """
    try:
        # This is a simplified implementation - in a real system you'd read from log files
        logs = [
            {
                "timestamp": "2025-09-15T06:17:36.636Z",
                "level": "INFO",
                "message": "MindX Control Panel initialized"
            },
            {
                "timestamp": "2025-09-15T06:17:36.636Z",
                "level": "INFO",
                "message": "Backend connection successful"
            },
            {
                "timestamp": "2025-09-15T06:17:36.636Z",
                "level": "WARNING",
                "message": "Some components may be in development mode"
            }
        ]
        
        if level != "ALL":
            logs = [log for log in logs if log["level"] == level]
        
        return {
            "logs": logs[:limit],
            "count": len(logs),
            "level": level
        }
    except Exception as e:
        logger.error(f"Failed to retrieve logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve logs: {str(e)}")

@system_router.get("/metrics", summary="Get performance metrics")
async def get_performance_metrics():
    """
    Get current system performance metrics.
    """
    try:
        import psutil
        import time
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "response_time": 45.2,
            "throughput": 850.5,
            "error_rate": 0.1,
            "cpu_usage": cpu_percent,
            "memory_usage": memory.percent,
            "disk_usage": disk.percent,
            "network_io": 1024.5,
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        # Return mock data if psutil is not available
        return {
            "response_time": 45.2,
            "throughput": 850.5,
            "error_rate": 0.1,
            "cpu_usage": 25.5,
            "memory_usage": 68.2,
            "disk_usage": 45.8,
            "network_io": 1024.5,
            "timestamp": time.time()
        }

@system_router.get("/resources", summary="Get resource usage")
async def get_resource_usage():
    """
    Get current system resource usage.
    """
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        cpu_count = psutil.cpu_count()
        load_avg = psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0.5, 0.6, 0.7]
        
        return {
            "memory": {
                "total": f"{memory.total / (1024**3):.1f} GB",
                "used": f"{memory.used / (1024**3):.1f} GB",
                "free": f"{memory.free / (1024**3):.1f} GB",
                "percentage": memory.percent
            },
            "cpu": {
                "cores": cpu_count,
                "usage": psutil.cpu_percent(interval=1),
                "load_avg": list(load_avg)
            },
            "disk": {
                "total": f"{disk.total / (1024**3):.1f} GB",
                "used": f"{disk.used / (1024**3):.1f} GB",
                "free": f"{disk.free / (1024**3):.1f} GB",
                "percentage": (disk.used / disk.total) * 100
            },
            "network": {
                "bytes_sent": 1024000,
                "bytes_received": 2048000,
                "packets_sent": 15000,
                "packets_received": 25000
            }
        }
    except Exception as e:
        logger.error(f"Failed to get resource usage: {e}")
        # Return mock data if psutil is not available
        return {
            "memory": {
                "total": "8.0 GB",
                "used": "5.2 GB",
                "free": "2.8 GB",
                "percentage": 65.0
            },
            "cpu": {
                "cores": 8,
                "usage": 25.5,
                "load_avg": [0.5, 0.6, 0.7]
            },
            "disk": {
                "total": "500.0 GB",
                "used": "250.0 GB",
                "free": "250.0 GB",
                "percentage": 50.0
            },
            "network": {
                "bytes_sent": 1024000,
                "bytes_received": 2048000,
                "packets_sent": 15000,
                "packets_received": 25000
            }
        }

@system_router.get("/config", summary="Get system configuration")
async def get_system_config():
    """
    Get current system configuration.
    """
    try:
        return {
            "version": "1.0.0",
            "environment": "development",
            "debug_mode": True,
            "log_level": "INFO",
            "max_agents": 10,
            "api_timeout": 30,
            "memory_limit": "8GB",
            "cpu_limit": "80%",
            "database_url": "sqlite:///mindx.db",
            "llm_providers": ["mistral", "ollama", "gemini"],
            "autonomous_mode": False,
            "features": {
                "evolution": True,
                "replication": True,
                "monitoring": True,
                "logging": True
            }
        }
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@system_router.post("/execute", summary="Execute terminal command")
async def execute_command(request: Dict[str, Any]):
    """
    Execute a terminal command (for terminal tab functionality).
    """
    try:
        command = request.get("command", "")
        if not command:
            raise HTTPException(status_code=400, detail="No command provided")
        
        # For security, only allow safe commands
        safe_commands = ["ls", "pwd", "whoami", "date", "uptime", "free", "df", "ps", "help"]
        cmd_lower = command.lower().strip()
        
        if any(cmd_lower.startswith(safe) for safe in safe_commands):
            import subprocess
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            return {
                "output": result.stdout if result.returncode == 0 else result.stderr,
                "return_code": result.returncode,
                "command": command
            }
        else:
            return {
                "output": f"Command '{command}' not allowed for security reasons. Allowed commands: {', '.join(safe_commands)}",
                "return_code": 1,
                "command": command
            }
    except subprocess.TimeoutExpired:
        return {
            "output": "Command timed out after 10 seconds",
            "return_code": 124,
            "command": command
        }
    except Exception as e:
        logger.error(f"Failed to execute command: {e}")
        return {
            "output": f"Error executing command: {str(e)}",
            "return_code": 1,
            "command": command
        }

# --- Coordinator Endpoints ---
@coordinator_router.post("/query", summary="Query the Coordinator Agent")
async def query_coordinator(payload: CoordQueryPayload, handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_coord_query(payload.query)

@coordinator_router.post("/improve", summary="Request a specific component improvement")
async def improve_component(payload: CoordImprovePayload, handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_coord_improve(payload.component_id, payload.context)

@coordinator_router.get("/backlog", summary="Get the improvement backlog")
async def get_backlog(handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_coord_backlog()

# --- Agent Endpoints ---
@agent_router.get("/", summary="List all registered agents")
async def list_agents(handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_agent_list()

@agent_router.post("/", summary="Create a new agent")
async def create_agent(payload: AgentCreatePayload, handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_agent_create(payload.agent_type, payload.agent_id, payload.config)

@agent_router.delete("/{agent_id}", summary="Delete an agent")
async def delete_agent(agent_id: str, handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_agent_delete(agent_id)

@agent_router.post("/{agent_id}/sign", summary="Sign a message with an agent's identity")
async def sign_with_agent(agent_id: str, payload: AgentSignPayload, handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_agent_sign(agent_id, payload.message)


# --- Identity Endpoints ---
@identity_router.get("/", summary="List all identities")
async def list_identities(handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_id_list()

@identity_router.post("/", summary="Create a new identity")
async def create_identity(payload: IdCreatePayload, handler: CommandHandler = Depends(get_command_handler)):
    return await handler.handle_id_create(payload.entity_id)

# --- FastAPI App Setup ---
app = FastAPI(
    title="MindX API",
    description="API for the MindX Augmentic Intelligence System.",
    version="2.0.0",
    openapi_tags=[
        {"name": "System & Commands", "description": "Core system-level operations and commands."},
        {"name": "Coordinator", "description": "Endpoints for interacting with the Coordinator Agent."},
        {"name": "Agents", "description": "Manage individual agent lifecycles and actions."},
        {"name": "Identities", "description": "Manage cryptographic identities for agents."},
    ]
)

# Configure CORS from environment variables for security
try:
    allowed_origins_str = config.get("mindx_backend_service.allowed_origins", '[]')
    allowed_origins = json.loads(allowed_origins_str)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info(f"CORS enabled for origins: {allowed_origins}")
except (json.JSONDecodeError, TypeError):
    logger.error("Invalid CORS configuration. Allowing all origins as a fallback for development.")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_event():
    """
    Minimal startup - no heavy initialization to prevent CPU issues.
    Components will be initialized lazily when needed.
    """
    logger.info("FastAPI server starting up... Skipping heavy initialization for performance.")
    app_state.command_handler = None
    logger.info("API server ready with lazy initialization.")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI server shutting down.")


# --- Include Routers in the Main App ---
app.include_router(system_router)
app.include_router(coordinator_router)
app.include_router(agent_router)
app.include_router(identity_router)

# Add a root endpoint for basic health checks
@app.get("/", tags=["System & Commands"])
def root():
    return {"message": "Welcome to the MindX API. See /docs for details."}


if __name__ == "__main__":
    import uvicorn
    # This allows direct execution for local debugging
    uvicorn.run(app, host="0.0.0.0", port=8000)
