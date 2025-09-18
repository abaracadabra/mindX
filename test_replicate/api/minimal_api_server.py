# mindx/api/minimal_api_server.py
"""
Ultra-minimal FastAPI Server for MindX - No heavy initialization
"""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess

# Third-party imports
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# --- Path Setup ---
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

# --- FastAPI App Creation ---
app = FastAPI(
    title="MindX Minimal API",
    description="Minimal MindX API with no heavy initialization",
    version="1.0.0"
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API Schemas ---
class SystemStatusResponse(BaseModel):
    status: str
    message: str
    initialized: bool = True

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

# --- System Endpoints ---
@app.get("/")
async def root():
    """Root endpoint for health checks"""
    return {
        "message": "MindX Minimal API is running",
        "version": "1.0.0",
        "status": "operational"
    }

@app.get("/system/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get system status"""
    return SystemStatusResponse(
        status="running",
        message="MindX system is operational",
        initialized=True
    )

@app.post("/system/evolve", response_model=EvolutionResponse)
async def evolve_system(request: EvolutionRequest):
    """Evolve the system with the given directive"""
    return EvolutionResponse(
        message=f"Evolution directive processed: {request.directive}",
        status="processing",
        directive=request.directive
    )

@app.post("/coordinator/query", response_model=QueryResponse)
async def query_coordinator(request: QueryRequest):
    """Query the coordinator"""
    return QueryResponse(
        response=f"Query processed: {request.query}",
        status="processed"
    )

@app.get("/agents/", response_model=AgentListResponse)
async def list_agents():
    """List all agents"""
    agents = [
        AgentInfo(id="mastermind", type="orchestrator", description="Main orchestrator", status="active"),
        AgentInfo(id="coordinator", type="coordinator", description="System coordinator", status="active"),
        AgentInfo(id="memory", type="memory", description="Memory management", status="active")
    ]
    return AgentListResponse(agents=agents, count=len(agents))

@app.get("/coordinator/backlog", response_model=BacklogResponse)
async def get_backlog():
    """Get coordinator backlog"""
    return BacklogResponse(
        backlog=[
            BacklogItem(id="1", task="System optimization", priority=1, status="pending"),
            BacklogItem(id="2", task="Performance monitoring", priority=2, status="in_progress"),
            BacklogItem(id="3", task="Error handling improvement", priority=3, status="completed")
        ],
        count=3
    )

@app.get("/system/logs")
async def get_system_logs():
    """Get system logs"""
    return {
        "logs": [
            {"timestamp": "2025-09-15T00:00:00Z", "level": "INFO", "message": "System initialized"},
            {"timestamp": "2025-09-15T00:01:00Z", "level": "INFO", "message": "API server started"},
            {"timestamp": "2025-09-15T00:02:00Z", "level": "INFO", "message": "Monitoring active"}
        ],
        "count": 3
    }

@app.get("/system/metrics")
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
        return {
            "cpu_percent": 0,
            "memory_percent": 0,
            "disk_usage": 0,
            "timestamp": "2025-09-15T00:00:00Z",
            "error": str(e)
        }

@app.get("/system/resources")
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
        return {
            "memory": {"total_gb": 0, "available_gb": 0, "used_gb": 0, "percent": 0},
            "disk": {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0},
            "cpu_count": 0,
            "error": str(e)
        }

@app.get("/system/config")
async def get_system_config():
    """Get system configuration"""
    return {
        "config": {
            "api_version": "1.0.0",
            "initialized": True,
            "cors_origins": ["*"],
            "monitoring_enabled": False
        }
    }

@app.post("/system/execute")
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
        raise HTTPException(status_code=500, detail=f"Command execution failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)



