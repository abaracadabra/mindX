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

app_state = AppState()

async def get_command_handler() -> CommandHandler:
    """
    FastAPI dependency that provides a validated CommandHandler.
    Raises a 503 Service Unavailable error if the system failed to initialize.
    """
    if app_state.command_handler is None:
        raise HTTPException(
            status_code=503,
            detail="MindX service is not available. Initialization may have failed."
        )
    return app_state.command_handler


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
    Initializes the MindX system. Now decoupled from the API server's direct knowledge.
    It asks the MastermindAgent to build itself and its sub-components.
    """
    logger.info("FastAPI server starting up... Initializing MindX instance.")
    try:
        # The API server no longer needs to know how to build the agent hierarchy.
        # It just requests the top-level agent, which handles its own dependencies.
        mastermind_instance = await MastermindAgent.get_instance(config_override=config)
        app_state.command_handler = CommandHandler(mastermind_instance)
        logger.info("MindX components initialized successfully. API is ready.")
    except Exception as e:
        logger.critical(f"FATAL: Failed to initialize MindX during startup: {e}", exc_info=True)
        # The command handler will remain None, and endpoints will return 503.
        app_state.command_handler = None

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
