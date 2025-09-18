# mindx/api/optimized_api_server.py
"""
Optimized FastAPI Server for the MindX Augmentic Intelligence System.

This version focuses on:
- Lazy initialization (only initialize when needed)
- Minimal startup overhead
- Graceful degradation when components fail
- Efficient resource usage
- Fast response times
"""

import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager

# Third-party imports
from fastapi import FastAPI, HTTPException, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Path Setup ---
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# --- MindX Core Imports ---
try:
    from utils.config import Config
    from utils.logging_config import setup_logging, get_logger
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import MindX modules: {e}")
    sys.exit(1)

# --- Global Configuration and Logging ---
setup_logging()
logger = get_logger(__name__)
config = Config()

# --- Global State ---
class AppState:
    def __init__(self):
        self.initialized = False
        self.initialization_error = None
        self.mastermind_agent = None
        self.command_handler = None
        self.model_registry = None
        self.coordinator_agent = None
        self.memory_agent = None
        self.belief_system = None

app_state = AppState()

# --- API Schemas ---
class SystemStatusResponse(BaseModel):
    status: str
    message: str
    initialized: bool
    error: Optional[str] = None

class EvolutionRequest(BaseModel):
    directive: str = Field(..., description="Evolution directive for the system")

class EvolutionResponse(BaseModel):
    message: str
    status: str
    directive: str

class QueryRequest(BaseModel):
    query: str = Field(..., description="Query for the coordinator")

class QueryResponse(BaseModel):
    response: str
    status: str

class AgentInfo(BaseModel):
    id: str
    type: str
    description: str
    status: str

class AgentListResponse(BaseModel):
    agents: List[AgentInfo]
    count: int

class BacklogItem(BaseModel):
    id: str
    task: str
    priority: int
    status: str

class BacklogResponse(BaseModel):
    backlog: List[BacklogItem]
    count: int

# --- Lazy Initialization Functions ---
async def get_mastermind_agent():
    """Lazy initialization of MastermindAgent"""
    if app_state.mastermind_agent is None and not app_state.initialization_error:
        try:
            await initialize_mindx_components()
        except Exception as e:
            app_state.initialization_error = str(e)
            logger.error(f"Failed to initialize MindX components: {e}")
            raise HTTPException(status_code=503, detail=f"MindX system not available: {e}")
    
    if app_state.initialization_error:
        raise HTTPException(status_code=503, detail=f"MindX system error: {app_state.initialization_error}")
    
    return app_state.mastermind_agent

async def initialize_mindx_components():
    """Initialize MindX components only when needed"""
    if app_state.initialized:
        return
    
    logger.info("Initializing MindX components...")
    
    try:
        # Import only when needed
        from orchestration.mastermind_agent import MastermindAgent
        from api.command_handler import CommandHandler
        from llm.model_registry import get_model_registry_async
        from orchestration.coordinator_agent import CoordinatorAgent
        from agents.memory_agent import MemoryAgent
        from core.belief_system import BeliefSystem
        
        # Initialize components with minimal overhead
        app_state.model_registry = await get_model_registry_async(config=config)
        app_state.memory_agent = MemoryAgent(config=config)
        app_state.belief_system = BeliefSystem()
        
        # Initialize coordinator with minimal monitoring
        app_state.coordinator_agent = await CoordinatorAgent.get_instance(
            config_override=config,
            memory_agent=app_state.memory_agent,
            belief_system=app_state.belief_system
        )
        
        # Initialize mastermind agent
        app_state.mastermind_agent = await MastermindAgent.get_instance(
            config_override=config,
            coordinator_agent_instance=app_state.coordinator_agent,
            memory_agent=app_state.memory_agent,
            model_registry=app_state.model_registry
        )
        
        app_state.command_handler = CommandHandler(app_state.mastermind_agent)
        app_state.initialized = True
        
        logger.info("MindX components initialized successfully")
        
    except Exception as e:
        app_state.initialization_error = str(e)
        logger.error(f"Failed to initialize MindX components: {e}", exc_info=True)
        raise

# --- Application Lifecycle ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    logger.info("FastAPI server starting up...")
    yield
    logger.info("FastAPI server shutting down...")

# --- FastAPI App Creation ---
app = FastAPI(
    title="MindX Optimized API",
    description="Optimized MindX Augmentic Intelligence System API",
    version="2.0.0",
    lifespan=lifespan
)

# --- CORS Configuration ---
cors_origins = config.get("api.cors.origins", ["*"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- System Router ---
system_router = APIRouter(prefix="/system", tags=["system"])

@system_router.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get system status with minimal overhead"""
    if app_state.initialization_error:
        return SystemStatusResponse(
            status="error",
            message="System initialization failed",
            initialized=False,
            error=app_state.initialization_error
        )
    
    if app_state.initialized:
        return SystemStatusResponse(
            status="running",
            message="MindX system is operational",
            initialized=True
        )
    else:
        return SystemStatusResponse(
            status="initializing",
            message="MindX system is initializing",
            initialized=False
        )

@system_router.post("/evolve", response_model=EvolutionResponse)
async def evolve_system(request: EvolutionRequest):
    """Evolve the system with the given directive"""
    try:
        mastermind = await get_mastermind_agent()
        result = await app_state.command_handler.handle_evolution_directive(request.directive)
        return EvolutionResponse(
            message=result.get("message", "Evolution directive processed"),
            status="processing",
            directive=request.directive
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Evolution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Evolution failed: {str(e)}")

@system_router.get("/logs")
async def get_system_logs():
    """Get system logs"""
    try:
        # Return mock logs for now - can be enhanced later
        return {
            "logs": [
                {"timestamp": "2025-09-15T00:00:00Z", "level": "INFO", "message": "System initialized"},
                {"timestamp": "2025-09-15T00:01:00Z", "level": "INFO", "message": "API server started"},
                {"timestamp": "2025-09-15T00:02:00Z", "level": "INFO", "message": "Monitoring active"}
            ],
            "count": 3
        }
    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")

@system_router.get("/metrics")
async def get_system_metrics():
    """Get system metrics"""
    try:
        import psutil
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent,
            "timestamp": "2025-09-15T00:00:00Z"
        }
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

@system_router.get("/resources")
async def get_system_resources():
    """Get system resource usage"""
    try:
        import psutil
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        return {
            "memory": {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "percent": memory.percent
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2),
                "percent": round((disk.used / disk.total) * 100, 2)
            },
            "cpu_count": psutil.cpu_count()
        }
    except Exception as e:
        logger.error(f"Failed to get resources: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get resources: {str(e)}")

@system_router.get("/config")
async def get_system_config():
    """Get system configuration"""
    try:
        return {
            "config": {
                "api_version": "2.0.0",
                "initialized": app_state.initialized,
                "cors_origins": cors_origins,
                "monitoring_enabled": config.get("monitoring.enabled", True)
            }
        }
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get config: {str(e)}")

@system_router.post("/execute")
async def execute_command(command: dict):
    """Execute a system command (with security restrictions)"""
    try:
        cmd = command.get("command", "")
        if not cmd:
            raise HTTPException(status_code=400, detail="No command provided")
        
        # Security: Only allow safe commands
        safe_commands = ["ls", "pwd", "whoami", "date", "uptime", "free", "df"]
        cmd_parts = cmd.split()
        if cmd_parts[0] not in safe_commands:
            raise HTTPException(status_code=403, detail="Command not allowed")
        
        result = subprocess.run(
            cmd_parts, 
            capture_output=True, 
            text=True, 
            timeout=10
        )
        
        return {
            "command": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail="Command timed out")
    except Exception as e:
        logger.error(f"Command execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")

# --- Coordinator Router ---
coordinator_router = APIRouter(prefix="/coordinator", tags=["coordinator"])

@coordinator_router.post("/query", response_model=QueryResponse)
async def query_coordinator(request: QueryRequest):
    """Query the coordinator"""
    try:
        mastermind = await get_mastermind_agent()
        result = await app_state.command_handler.handle_coordinator_query(request.query)
        return QueryResponse(
            response=result.get("response", "Query processed"),
            status="processed"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Coordinator query failed: {e}")
        raise HTTPException(status_code=500, detail=f"Coordinator query failed: {str(e)}")

@coordinator_router.get("/backlog", response_model=BacklogResponse)
async def get_backlog():
    """Get coordinator backlog"""
    try:
        # Return mock backlog for now
        return BacklogResponse(
            backlog=[
                BacklogItem(id="1", task="System optimization", priority=1, status="pending"),
                BacklogItem(id="2", task="Performance monitoring", priority=2, status="in_progress"),
                BacklogItem(id="3", task="Error handling improvement", priority=3, status="completed")
            ],
            count=3
        )
    except Exception as e:
        logger.error(f"Failed to get backlog: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get backlog: {str(e)}")

# --- Agent Router ---
agent_router = APIRouter(prefix="/agents", tags=["agents"])

@agent_router.get("/", response_model=AgentListResponse)
async def list_agents():
    """List all agents"""
    try:
        if not app_state.initialized:
            return AgentListResponse(agents=[], count=0)
        
        # Return mock agents for now
        agents = [
            AgentInfo(id="mastermind", type="orchestrator", description="Main orchestrator", status="active"),
            AgentInfo(id="coordinator", type="coordinator", description="System coordinator", status="active"),
            AgentInfo(id="memory", type="memory", description="Memory management", status="active")
        ]
        return AgentListResponse(agents=agents, count=len(agents))
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")

# --- Root Endpoint ---
@app.get("/")
async def root():
    """Root endpoint for health checks"""
    return {
        "message": "MindX Optimized API is running",
        "version": "2.0.0",
        "status": "operational",
        "initialized": app_state.initialized
    }

# --- Include Routers ---
app.include_router(system_router)
app.include_router(coordinator_router)
app.include_router(agent_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)



