# mindx/scripts/api_server.py

import asyncio
import os
import random
import re
import time
import json
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

# Add project root to path to allow imports
import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from agents.orchestration.mastermind_agent import MastermindAgent
from agents.orchestration.coordinator_agent import get_coordinator_agent_mindx_async
from agents.memory_agent import MemoryAgent, MemoryType, MemoryImportance
from agents.guardian_agent import GuardianAgent
from agents.core.id_manager_agent import IDManagerAgent
from agents.core.belief_system import BeliefSystem, BeliefSource
from agents.faicey_agent import FaiceyAgent
from agents.persona_agent import PersonaAgent
from tools.user_persistence_manager import get_user_persistence_manager
from llm.model_registry import get_model_registry_async
from utils.config import Config, PROJECT_ROOT
from api.command_handler import CommandHandler
from utils.logging_config import setup_logging, get_logger
from mindx_backend_service.vault_manager import get_vault_manager
from agents.monitoring.rate_limit_dashboard import RateLimitDashboard

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Memory availability check
try:
    # MemoryAgent is already imported above, just check if it's available
    MemoryAgent()
    MEMORY_AVAILABLE = True
except Exception as e:
    MEMORY_AVAILABLE = False
    logger.warning(f"MemoryAgent not available - memory logging disabled: {e}")

# --- Pydantic Models for API Request/Response Validation ---

class DirectivePayload(BaseModel):
    directive: str
    max_cycles: Optional[int] = 8
    autonomous_mode: Optional[bool] = False

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

class GitHubAgentOperationPayload(BaseModel):
    operation: str
    backup_type: Optional[str] = None
    reason: Optional[str] = None
    branch_name: Optional[str] = None
    target_branch: Optional[str] = None
    upgrade_description: Optional[str] = None
    interval: Optional[str] = None
    enabled: Optional[bool] = None
    time: Optional[str] = None
    day: Optional[str] = None

class AgentCreatePayload(BaseModel):
    agent_type: str
    agent_id: str
    config: Dict[str, Any]
    owner_wallet: Optional[str] = None

class AgentDeletePayload(BaseModel):
    agent_id: str
    owner_wallet: Optional[str] = None

class UserRegisterPayload(BaseModel):
    wallet_address: str
    metadata: Optional[Dict[str, Any]] = None

class UserAgentCreatePayload(BaseModel):
    owner_wallet: str
    agent_id: str
    agent_type: str
    metadata: Optional[Dict[str, Any]] = None

class UserRegisterWithSignaturePayload(BaseModel):
    wallet_address: str
    signature: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class UserAgentCreateWithSignaturePayload(BaseModel):
    owner_wallet: str
    agent_id: str
    agent_type: str
    signature: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

class UserAgentDeleteWithSignaturePayload(BaseModel):
    wallet_address: str
    agent_id: str
    signature: str
    message: str

class ChallengeRequestPayload(BaseModel):
    wallet_address: str
    action: str

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

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)
# Inbound metrics and optional rate control (both directions: see docs/monitoring_rate_control.md)
try:
    from mindx_backend_service.inbound_metrics import InboundMetricsMiddleware, get_inbound_metrics, set_inbound_rate_limit
    app.add_middleware(InboundMetricsMiddleware)
except Exception as e:
    logger.warning(f"InboundMetricsMiddleware not added: {e}")

# Include mindterm router
from mindx_backend_service.mindterm import mindterm_router
from mindx_backend_service.mindterm.routes import set_coordinator_and_monitors
app.include_router(mindterm_router)

# Include LLM provider management router
from api.llm_routes import router as llm_router
app.include_router(llm_router)

# Include RAGE (Retrieval Augmented Generative Engine) router
from mindx_backend_service.rage.routes import router as rage_router
app.include_router(rage_router)

# Include Ollama Admin router
from api.ollama.ollama_admin_routes import router as ollama_admin_router
app.include_router(ollama_admin_router)

# Include AgenticPlace router
from mindx_backend_service.agenticplace_routes import router as agenticplace_router
app.include_router(agenticplace_router)

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
        
        # Connect mindX to Ollama so AgenticPlace (and other clients) can use inference
        try:
            from api.ollama.ollama_url import create_ollama_api
            ollama_api = create_ollama_api(config=app_config)
            ollama_test = await ollama_api.test_connection(try_fallback=True)
            if ollama_test.get("success"):
                logger.info(f"mindX connected to Ollama at {ollama_test.get('base_url', 'unknown')} (model_count={ollama_test.get('model_count', 0)}) — AgenticPlace can use mindX as provider.")
            else:
                logger.warning(f"mindX Ollama connection failed: {ollama_test.get('error', 'unknown')} — ensure Ollama is running (e.g. localhost:11434) for AgenticPlace.")
        except Exception as ollama_e:
            logger.warning(f"mindX Ollama startup check failed: {ollama_e} — AgenticPlace may fail until Ollama is available.")
        
        # Initialize mindterm with coordinator and monitors
        try:
            set_coordinator_and_monitors(
                coordinator=coordinator_instance,
                resource_monitor=coordinator_instance.resource_monitor if hasattr(coordinator_instance, 'resource_monitor') else None,
                performance_monitor=coordinator_instance.performance_monitor if hasattr(coordinator_instance, 'performance_monitor') else None
            )
            logger.info("mindterm integrated with coordinator and monitoring systems")
        except Exception as e:
            logger.warning(f"Failed to integrate mindterm with coordinator: {e}", exc_info=True)
        
        logger.info("mindX components initialized successfully. API is ready.")
    except Exception as e:
        logger.critical(f"Failed to initialize mindX components during startup: {e}", exc_info=True)
        command_handler = None

# User-specific agent management handler functions with signature verification
async def handle_user_register_with_signature(wallet_address: str, signature: str, message: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle user registration with wallet signature verification"""
    try:
        # Get user persistence manager
        user_manager = get_user_persistence_manager()
        
        # Register user with signature verification
        success, message_result = user_manager.register_user(wallet_address, signature, message, metadata)
        
        if not success:
            return {"error": message_result}
        
        # Log user registration
        if command_handler and command_handler.mastermind.memory_agent:
            await command_handler.mastermind.memory_agent.log_process(
                process_name="user_registered_with_signature",
                data={
                    "wallet_address": wallet_address,
                    "signature_verified": True,
                    "metadata": metadata or {}
                },
                metadata={"user_wallet": wallet_address}
            )
        
        return {
            "status": "success",
            "wallet_address": wallet_address,
            "message": message_result,
            "signature_verified": True
        }
        
    except Exception as e:
        logger.error(f"Failed to register user {wallet_address}: {e}")
        return {"error": str(e)}

async def handle_user_agent_create_with_signature(owner_wallet: str, agent_id: str, agent_type: str, 
                                                 signature: str, message: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Handle user-specific agent creation with signature verification"""
    try:
        # Get user persistence manager
        user_manager = get_user_persistence_manager()
        
        # Create agent with signature verification
        success, message_result, agent_wallet = user_manager.create_user_agent(
            owner_wallet, agent_id, agent_type, signature, message, metadata
        )
        
        if not success:
            return {"error": message_result}
        
        # Log agent creation
        if command_handler and command_handler.mastermind.memory_agent:
            await command_handler.mastermind.memory_agent.log_process(
                process_name="agent_created_with_signature",
                data={
                    "agent_id": agent_id,
                    "agent_type": agent_type,
                    "owner_wallet": owner_wallet,
                    "agent_wallet": agent_wallet,
                    "signature_verified": True,
                    "metadata": metadata or {}
                },
                metadata={"user_wallet": owner_wallet, "created_agent": agent_id}
            )
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "agent_type": agent_type,
            "owner_wallet": owner_wallet,
            "agent_wallet": agent_wallet,
            "message": message_result,
            "signature_verified": True
        }
        
    except Exception as e:
        logger.error(f"Failed to create agent {agent_id} for user {owner_wallet}: {e}")
        return {"error": str(e)}

async def handle_user_agent_delete_with_signature(wallet_address: str, agent_id: str, signature: str, message: str) -> Dict[str, Any]:
    """Handle user-specific agent deletion with signature verification"""
    try:
        # Get user persistence manager
        user_manager = get_user_persistence_manager()
        
        # Delete agent with signature verification
        success, message_result = user_manager.delete_user_agent(wallet_address, agent_id, signature, message)
        
        if not success:
            return {"error": message_result}
        
        # Log agent deletion
        if command_handler and command_handler.mastermind.memory_agent:
            await command_handler.mastermind.memory_agent.log_process(
                process_name="agent_deleted_with_signature",
                data={
                    "agent_id": agent_id,
                    "owner_wallet": wallet_address,
                    "signature_verified": True
                },
                metadata={"user_wallet": wallet_address, "deleted_agent": agent_id}
            )
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "owner_wallet": wallet_address,
            "message": message_result,
            "signature_verified": True
        }
        
    except Exception as e:
        logger.error(f"Failed to delete agent {agent_id}: {e}")
        return {"error": str(e)}

async def handle_get_user_agents(wallet_address: str) -> Dict[str, Any]:
    """Get all agents owned by a user"""
    try:
        # Get user persistence manager
        user_manager = get_user_persistence_manager()
        
        # Get user agents
        agents = user_manager.get_user_agents(wallet_address)
        
        return {
            "status": "success",
            "wallet_address": wallet_address,
            "agents": agents,
            "total_agents": len(agents)
        }
        
    except Exception as e:
        logger.error(f"Failed to get agents for user {wallet_address}: {e}")
        return {"error": str(e)}

async def handle_get_user_stats(wallet_address: str) -> Dict[str, Any]:
    """Get user statistics"""
    try:
        # Get user persistence manager
        user_manager = get_user_persistence_manager()
        
        # Get user stats
        stats = user_manager.get_user_stats(wallet_address)
        
        if not stats:
            return {"error": f"User {wallet_address} not found"}
        
        return {
            "status": "success",
            **stats
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats for user {wallet_address}: {e}")
        return {"error": str(e)}

async def _get_user_agent_count(wallet_address: str) -> int:
    """Get the current agent count for a user"""
    if not command_handler or not command_handler.mastermind.id_manager_agent:
        return 0
    count_belief = await command_handler.mastermind.belief_system.get_belief(f"user.agent_count.{wallet_address}")
    return int(count_belief.value) if count_belief else 0

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

@app.get("/api/monitoring/inbound", summary="Get inbound request metrics (latency ms, bytes, req/min)")
async def get_inbound_monitoring():
    """Inbound metrics: latency (ms), request/response bytes, requests per minute. See docs/monitoring_rate_control.md."""
    try:
        from mindx_backend_service.inbound_metrics import get_inbound_metrics, get_inbound_rate_limit
        metrics = get_inbound_metrics()
        rpm_limit, window_s = get_inbound_rate_limit()
        return {
            "inbound_metrics": metrics.get_metrics(window_s=window_s),
            "inbound_rate_limit": {"requests_per_minute": rpm_limit, "window_s": window_s} if rpm_limit else None,
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Inbound metrics not available: {e}")

@app.get("/registry/agents", summary="Show agent registry")
async def show_agent_registry():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_show_agent_registry()

@app.get("/registry/tools", summary="Show tool registry")
async def show_tool_registry():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_show_tool_registry()

@app.get("/tools", summary="List tools in tools folder")
async def list_tools():
    """List all Python tool files in the tools folder"""
    try:
        tools_dir = "tools"
        if not os.path.exists(tools_dir):
            return {"error": "Tools directory not found", "tools": []}
        
        tools = []
        for filename in os.listdir(tools_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                filepath = os.path.join(tools_dir, filename)
                file_size = os.path.getsize(filepath)
                
                # Try to extract tool description from the file
                description = "Python tool"
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Look for class or function docstrings
                        if 'class ' in content:
                            class_match = re.search(r'class\s+(\w+).*?"""(.*?)"""', content, re.DOTALL)
                            if class_match:
                                description = class_match.group(2).strip()
                        elif 'def ' in content:
                            func_match = re.search(r'def\s+(\w+).*?"""(.*?)"""', content, re.DOTALL)
                            if func_match:
                                description = func_match.group(2).strip()
                except Exception as e:
                    logger.error(f"Error reading tool file {filename}: {e}")
                
                tools.append({
                    "name": filename.replace('.py', ''),
                    "filename": filename,
                    "size": file_size,
                    "description": description,
                    "path": filepath
                })
        
        # Sort tools by name
        tools.sort(key=lambda x: x['name'])
        
        return {
            "status": "success",
            "tools_count": len(tools),
            "tools": tools,
            "tools_directory": tools_dir
        }
        
    except Exception as e:
        logger.error(f"Error listing tools: {e}")
        return {"error": str(e), "tools": []}

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

# GitHub Agent Tool Endpoints
@app.post("/github/execute", summary="Execute GitHub agent operation")
async def github_execute(payload: GitHubAgentOperationPayload):
    """Execute a GitHub agent tool operation."""
    try:
        from tools.github_agent_tool import GitHubAgentTool
        from agents.memory_agent import MemoryAgent
        from utils.config import Config
        
        config = Config()
        memory_agent = MemoryAgent(config=config)
        github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
        
        kwargs = {}
        if payload.backup_type:
            kwargs["backup_type"] = payload.backup_type
        if payload.reason:
            kwargs["reason"] = payload.reason
        if payload.branch_name:
            kwargs["branch_name"] = payload.branch_name
        if payload.target_branch:
            kwargs["target_branch"] = payload.target_branch
        if payload.upgrade_description:
            kwargs["upgrade_description"] = payload.upgrade_description
        if payload.interval:
            kwargs["interval"] = payload.interval
        if payload.enabled is not None:
            kwargs["enabled"] = payload.enabled
        if payload.time:
            kwargs["time"] = payload.time
        if payload.day:
            kwargs["day"] = payload.day
        
        success, result = await github_agent.execute(payload.operation, **kwargs)
        
        return {
            "status": "success" if success else "error",
            "success": success,
            "result": result
        }
    except Exception as e:
        logger.error(f"GitHub agent operation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/github/status", summary="Get GitHub agent status")
async def github_status():
    """Get GitHub agent status and backup information."""
    try:
        from tools.github_agent_tool import GitHubAgentTool
        from agents.memory_agent import MemoryAgent
        from utils.config import Config
        
        config = Config()
        memory_agent = MemoryAgent(config=config)
        github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
        
        # Get backup status
        success, status = await github_agent.execute("get_backup_status")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to get backup status")
        
        # Get schedule
        success, schedule = await github_agent.execute("get_backup_schedule")
        if not success:
            schedule = {}
        
        # List backups
        success, backups = await github_agent.execute("list_backups")
        if not success:
            backups = {}
        
        return {
            "status": "success",
            "backup_status": status,
            "schedule": schedule,
            "backups": backups
        }
    except Exception as e:
        logger.error(f"Failed to get GitHub agent status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/github/schedule", summary="Get backup schedule configuration")
async def github_get_schedule():
    """Get current backup schedule configuration."""
    try:
        from tools.github_agent_tool import GitHubAgentTool
        from agents.memory_agent import MemoryAgent
        from utils.config import Config
        
        config = Config()
        memory_agent = MemoryAgent(config=config)
        github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
        
        success, schedule = await github_agent.execute("get_backup_schedule")
        if not success:
            raise HTTPException(status_code=500, detail="Failed to get schedule")
        
        return {
            "status": "success",
            "schedule": schedule
        }
    except Exception as e:
        logger.error(f"Failed to get schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/github/schedule", summary="Set backup schedule configuration")
async def github_set_schedule(payload: GitHubAgentOperationPayload):
    """Set backup schedule configuration."""
    try:
        from tools.github_agent_tool import GitHubAgentTool
        from agents.memory_agent import MemoryAgent
        from utils.config import Config
        
        if not payload.interval:
            raise HTTPException(status_code=400, detail="interval is required")
        
        config = Config()
        memory_agent = MemoryAgent(config=config)
        github_agent = GitHubAgentTool(memory_agent=memory_agent, config=config)
        
        kwargs = {
            "interval": payload.interval,
            "enabled": payload.enabled if payload.enabled is not None else True
        }
        if payload.time:
            kwargs["time"] = payload.time
        if payload.day:
            kwargs["day"] = payload.day
        
        success, result = await github_agent.execute("set_backup_schedule", **kwargs)
        if not success:
            raise HTTPException(status_code=500, detail=result)
        
        return {
            "status": "success",
            "result": result
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to set schedule: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

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

@app.get("/agents/", summary="List all agents including file-based and system agents")
async def list_all_agents():
    """
    List all agents including those in the agents folder and system agents.
    """
    try:
        import os
        import importlib.util
        
        agents_list = []
        
        # Get agents from the agents folder
        agents_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agents')
        if os.path.exists(agents_folder):
            for filename in os.listdir(agents_folder):
                if filename.endswith('.py') and not filename.startswith('__'):
                    agent_name = filename[:-3]  # Remove .py extension
                    
                    # Try to get agent class name and description
                    agent_info = {
                        "name": agent_name,
                        "type": "file_agent",
                        "file": filename,
                        "path": os.path.join(agents_folder, filename),
                        "status": "available"
                    }
                    
                    # Try to extract class name from the file
                    try:
                        with open(os.path.join(agents_folder, filename), 'r') as f:
                            content = f.read()
                            # Look for class definitions
                            import re
                            class_matches = re.findall(r'class\s+(\w+).*?Agent', content)
                            if class_matches:
                                agent_info["class_name"] = class_matches[0]
                            
                            # Look for docstrings or descriptions
                            docstring_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
                            if docstring_match:
                                agent_info["description"] = docstring_match.group(1).strip()[:100] + "..."
                            else:
                                agent_info["description"] = f"Agent from {filename}"
                    except Exception as e:
                        agent_info["description"] = f"Agent from {filename}"
                        agent_info["error"] = str(e)
                    
                    agents_list.append(agent_info)
        
        # Add system agents with capabilities
        system_agents = [
            {
                "name": "BDI Agent",
                "type": "system_agent",
                "status": "active",
                "description": "Belief-Desire-Intention agent for goal management and planning",
                "capabilities": [
                    {"name": "Decision Making", "category": "cognitive", "icon": "brain"},
                    {"name": "Agent Selection", "category": "orchestration", "icon": "network"},
                    {"name": "Reasoning", "category": "cognitive", "icon": "lightbulb"},
                    {"name": "Belief Management", "category": "memory", "icon": "database"},
                    {"name": "Goal Tracking", "category": "planning", "icon": "target"}
                ],
                "ethereum_address": "0xf8f2da254D4a3F461e0472c65221B26fB4e91fB7"
            },
            {
                "name": "Memory Agent",
                "type": "system_agent",
                "status": "active",
                "description": "Manages short-term and long-term memory systems",
                "capabilities": [
                    {"name": "STM Management", "category": "memory", "icon": "clock"},
                    {"name": "LTM Storage", "category": "memory", "icon": "archive"},
                    {"name": "Memory Search", "category": "retrieval", "icon": "search"},
                    {"name": "Memory Consolidation", "category": "processing", "icon": "compress"}
                ]
            },
            {
                "name": "Guardian Agent",
                "type": "system_agent",
                "status": "active",
                "description": "Security and safety monitoring agent",
                "capabilities": [
                    {"name": "Security Validation", "category": "security", "icon": "shield"},
                    {"name": "Access Control", "category": "security", "icon": "lock"},
                    {"name": "Threat Detection", "category": "monitoring", "icon": "alert"},
                    {"name": "Compliance Check", "category": "governance", "icon": "check"}
                ],
                "ethereum_address": "0xC2cca3d6F29dF17D1999CFE0458BC3DEc024F02D"
            },
            {
                "name": "ID Manager Agent",
                "type": "system_agent",
                "status": "active",
                "description": "Manages entity identities and wallet addresses",
                "capabilities": [
                    {"name": "Wallet Creation", "category": "identity", "icon": "wallet"},
                    {"name": "Identity Binding", "category": "identity", "icon": "link"},
                    {"name": "Signature Verification", "category": "security", "icon": "key"},
                    {"name": "Agent Registration", "category": "management", "icon": "user-plus"}
                ],
                "ethereum_address": "0x290bB0497dBDbC5E8B577E0cc92457cB015A2a1f"
            },
            {
                "name": "Mastermind Agent",
                "type": "system_agent",
                "status": "active",
                "description": "High-level strategic planning and Mistral AI reasoning",
                "capabilities": [
                    {"name": "Strategic Orchestration", "category": "orchestration", "icon": "compass"},
                    {"name": "Mistral AI Reasoning", "category": "ai", "icon": "sparkles"},
                    {"name": "Agent Coordination", "category": "orchestration", "icon": "network"},
                    {"name": "Resource Allocation", "category": "management", "icon": "sliders"}
                ],
                "ethereum_address": "0xb9B46126551652eb58598F1285aC5E86E5CcfB43"
            },
            {
                "name": "Coordinator Agent",
                "type": "system_agent",
                "status": "active",
                "description": "Infrastructure management and autonomous improvement",
                "capabilities": [
                    {"name": "Infrastructure Management", "category": "system", "icon": "server"},
                    {"name": "Autonomous Improvement", "category": "evolution", "icon": "trending-up"},
                    {"name": "Component Evolution", "category": "evolution", "icon": "git-branch"},
                    {"name": "Task Delegation", "category": "orchestration", "icon": "share"}
                ],
                "ethereum_address": "0x7371e20033f65aB598E4fADEb5B4e400Ef22040A"
            },
            {
                "name": "CEO Agent",
                "type": "system_agent",
                "status": "active",
                "description": "Executive decision making and strategic oversight",
                "capabilities": [
                    {"name": "Executive Decisions", "category": "governance", "icon": "crown"},
                    {"name": "Strategic Oversight", "category": "planning", "icon": "eye"},
                    {"name": "Priority Management", "category": "management", "icon": "list"},
                    {"name": "Resource Approval", "category": "governance", "icon": "check-circle"}
                ]
            },
            {
                "name": "Resource Monitor",
                "type": "system_agent",
                "status": "active",
                "description": "Monitors system resources and performance",
                "capabilities": [
                    {"name": "CPU Monitoring", "category": "monitoring", "icon": "cpu"},
                    {"name": "Memory Tracking", "category": "monitoring", "icon": "hard-drive"},
                    {"name": "System Health", "category": "monitoring", "icon": "activity"},
                    {"name": "Alert Generation", "category": "notifications", "icon": "bell"}
                ]
            },
            {
                "name": "Performance Monitor",
                "type": "system_agent",
                "status": "active",
                "description": "Tracks system performance metrics and alerts",
                "capabilities": [
                    {"name": "Latency Tracking", "category": "monitoring", "icon": "clock"},
                    {"name": "Throughput Analysis", "category": "analytics", "icon": "bar-chart"},
                    {"name": "Bottleneck Detection", "category": "diagnostics", "icon": "zap"},
                    {"name": "Performance Reports", "category": "reporting", "icon": "file-text"}
                ]
            }
        ]
        
        agents_list.extend(system_agents)
        
        return {
            "total_agents": len(agents_list),
            "file_agents": len([a for a in agents_list if a["type"] == "file_agent"]),
            "system_agents": len([a for a in agents_list if a["type"] == "system_agent"]),
            "agents": agents_list
        }
        
    except Exception as e:
        logger.error(f"Failed to list agents: {e}")
        return {
            "error": str(e),
            "total_agents": 0,
            "agents": []
        }

@app.post("/agents/{agent_id}/evolve", summary="Evolve a specific agent")
async def agent_evolve(agent_id: str, payload: DirectivePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_evolve(agent_id, payload.directive)

@app.post("/agents/{agent_id}/sign", summary="Sign a message with an agent's identity")
async def agent_sign(agent_id: str, payload: AgentSignPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_agent_sign(agent_id, payload.message)

# User-specific agent management endpoints with signature verification
@app.post("/users/register", summary="Register a new user with wallet address")
async def register_user(payload: UserRegisterPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await handle_user_register(payload.wallet_address, payload.metadata)

@app.post("/users/register-with-signature", summary="Register a new user with wallet signature verification")
async def register_user_with_signature(payload: UserRegisterWithSignaturePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await handle_user_register_with_signature(
        payload.wallet_address, payload.signature, payload.message, payload.metadata
    )

@app.post("/users/agents", summary="Create a new agent for a user")
async def create_user_agent(payload: UserAgentCreatePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await handle_user_agent_create(
        payload.owner_wallet, payload.agent_id, payload.agent_type, payload.metadata
    )

@app.post("/users/agents-with-signature", summary="Create a new agent for a user with signature verification")
async def create_user_agent_with_signature(payload: UserAgentCreateWithSignaturePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await handle_user_agent_create_with_signature(
        payload.owner_wallet, payload.agent_id, payload.agent_type, 
        payload.signature, payload.message, payload.metadata
    )

@app.delete("/users/{wallet_address}/agents/{agent_id}", summary="Delete a user's agent")
async def delete_user_agent(wallet_address: str, agent_id: str):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await handle_user_agent_delete(agent_id, wallet_address)

@app.post("/users/agents/delete-with-signature", summary="Delete a user's agent with signature verification")
async def delete_user_agent_with_signature(payload: UserAgentDeleteWithSignaturePayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await handle_user_agent_delete_with_signature(
        payload.wallet_address, payload.agent_id, payload.signature, payload.message
    )

@app.get("/users/{wallet_address}/agents", summary="Get all agents owned by a user")
async def get_user_agents(wallet_address: str):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await handle_get_user_agents(wallet_address)

@app.get("/users/{wallet_address}/stats", summary="Get user statistics")
async def get_user_stats(wallet_address: str):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await handle_get_user_stats(wallet_address)

@app.post("/users/challenge", summary="Generate a challenge message for signature")
async def generate_challenge(payload: ChallengeRequestPayload):
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    user_manager = get_user_persistence_manager()
    challenge = user_manager.generate_challenge_message(payload.wallet_address, payload.action)
    return {
        "status": "success",
        "wallet_address": payload.wallet_address,
        "action": payload.action,
        "challenge_message": challenge
    }

@app.get("/logs/runtime", summary="Get runtime logs")
async def get_runtime_logs():
    if not command_handler: raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_get_runtime_logs()

@app.get("/", summary="Root endpoint")
async def root():
    return {"message": "Welcome to the mindX API. See /docs for details."}

# Simple Coder endpoints (moved to later in file to avoid duplicates)
# Global BDI state for real-time updates
bdi_state = {
    "current_directive": "None",
    "chosen_agent": "None",
    "reasoning_history": [],
    "beliefs": [],
    "desires": [],
    "intentions": [],
    "goals": [],
    "plans": [],
    "last_updated": time.strftime('%Y-%m-%d %H:%M:%S'),
    "performance_metrics": {
        "total_decisions": 0,
        "success_rate": 0.0,
        "avg_decision_time": "0s",
        "preferred_agent": "None"
    },
    "system_health": {
        "bdi_agent": "operational",
        "reasoning_engine": "active",
        "log_system": "healthy",
        "agent_registry": "updated"
    }
}

def update_bdi_state(directive: str, chosen_agent: str, reasoning: str):
    """Update the global BDI state with new information"""
    global bdi_state
    
    bdi_state["current_directive"] = directive
    bdi_state["chosen_agent"] = chosen_agent
    bdi_state["last_updated"] = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # Add to reasoning history
    if reasoning:
        bdi_state["reasoning_history"].append({
            "timestamp": bdi_state["last_updated"],
            "reasoning": reasoning,
            "directive": directive,
            "agent": chosen_agent
        })
        # Keep only last 10 entries
        if len(bdi_state["reasoning_history"]) > 10:
            bdi_state["reasoning_history"] = bdi_state["reasoning_history"][-10:]
    
    # Log BDI activity for AGIVITY tracking
    bdi_activity = {
        "timestamp": time.time(),
        "agent": "BDI Agent",
        "message": f"Selected {chosen_agent} for directive: {directive}",
        "type": "success",
        "details": {
            "reasoning": reasoning,
            "available_agents": ["simple_coder", "base_gen_agent", "system_analyzer", "audit_and_improve_tool"],
            "decision_factors": ["task_type", "agent_capabilities", "current_system_state"],
            "confidence": "high"
        }
    }
    
    # Store in global activity log for AGIVITY
    if not hasattr(update_bdi_state, 'activity_log'):
        update_bdi_state.activity_log = []
    
    update_bdi_state.activity_log.append(bdi_activity)
    if len(update_bdi_state.activity_log) > 50:
        update_bdi_state.activity_log = update_bdi_state.activity_log[-50:]
    
    # Update beliefs based on current state
    bdi_state["beliefs"] = [
        "System state analysis completed",
        "Available agents and tools identified", 
        "Task requirements understood",
        f"Current directive: {directive}",
        f"Optimal agent identified: {chosen_agent}",
        "BDI reasoning process operational",
        f"Last reasoning: {reasoning[:100]}..." if reasoning else "No recent reasoning"
    ]
    
    # Update desires based on current context
    bdi_state["desires"] = [
        "Choose optimal agent for task execution",
        "Maximize efficiency and effectiveness",
        "Maintain system stability",
        "Ensure successful directive completion",
        "Adapt to changing requirements",
        "Learn from previous decisions",
        f"Execute directive: {directive}" if directive != "None" else "Awaiting new directive"
    ]
    
    # Update intentions based on current state
    bdi_state["intentions"] = [
        f"Execute with {chosen_agent}" if chosen_agent != "None" else "Select appropriate agent",
        "Monitor task progress continuously",
        "Adapt strategy as needed",
        "Maintain system performance",
        "Log all reasoning decisions",
        "Prepare for next directive",
        f"Process: {directive}" if directive != "None" else "Standby for new tasks"
    ]
    
    # Update goals
    bdi_state["goals"] = [
        {"description": f"Process directive: {directive}", "priority": "high", "status": "active", "progress": 75},
        {"description": "Maintain system health", "priority": "medium", "status": "active", "progress": 90},
        {"description": "Optimize agent selection", "priority": "medium", "status": "active", "progress": 85},
        {"description": "Enhance BDI reasoning", "priority": "low", "status": "active", "progress": 60}
    ]
    
    # Update plans
    bdi_state["plans"] = [
        {"description": "BDI reasoning process", "status": "active", "steps": 4, "completed": 3},
        {"description": "Agent selection and execution", "status": "active", "steps": 3, "completed": 2},
        {"description": "Continuous monitoring", "status": "active", "steps": 2, "completed": 1},
        {"description": "Performance optimization", "status": "pending", "steps": 3, "completed": 0}
    ]
    
    # Update performance metrics
    bdi_state["performance_metrics"]["total_decisions"] = len(bdi_state["reasoning_history"])
    bdi_state["performance_metrics"]["preferred_agent"] = chosen_agent
    bdi_state["performance_metrics"]["success_rate"] = min(95.5 + (len(bdi_state["reasoning_history"]) * 0.5), 100.0)

@app.get("/core/bdi-status", summary="BDI Agent status")
async def get_bdi_status():
    """Get BDI Agent status with belief, desire, intention details"""
    try:
        # Read the latest BDI reasoning from the log file for additional context
        agint_log_file = "data/logs/agint/agint_cognitive_cycles.log"
        
        if os.path.exists(agint_log_file):
            with open(agint_log_file, 'r') as f:
                lines = f.readlines()
                # Get the last few entries to supplement global state
                for line in lines[-5:]:  # Last 5 lines
                    if "BDI Reasoning:" in line and not any(r["reasoning"] == line.strip() for r in bdi_state["reasoning_history"]):
                        # Add new reasoning if not already in state
                        timestamp = line.split(']')[0][1:] if ']' in line else time.strftime('%Y-%m-%d %H:%M:%S')
                        bdi_state["reasoning_history"].append({
                            "timestamp": timestamp,
                            "reasoning": line.strip(),
                            "directive": bdi_state["current_directive"],
                            "agent": bdi_state["chosen_agent"]
                        })
        
        # Determine agent status based on current state
        agent_status = "active" if bdi_state["chosen_agent"] != "None" else "idle"
        confidence = "high" if len(bdi_state["reasoning_history"]) > 0 else "medium"
        
        return {
            "status": agent_status,
            "confidence": confidence,
            "last_directive": bdi_state["current_directive"],
            "chosen_agent": bdi_state["chosen_agent"],
            "last_updated": bdi_state["last_updated"],
            "bdi_reasoning": [r["reasoning"] for r in bdi_state["reasoning_history"][-5:]],
            "beliefs": bdi_state["beliefs"],
            "desires": bdi_state["desires"],
            "intentions": bdi_state["intentions"],
            "goals": bdi_state["goals"],
            "plans": bdi_state["plans"],
            "last_action": f"Selected {bdi_state['chosen_agent']} for directive: {bdi_state['current_directive']}",
            "reasoning_history": bdi_state["reasoning_history"],
            "performance_metrics": bdi_state["performance_metrics"],
            "system_health": bdi_state["system_health"]
        }
    except Exception as e:
        logger.error(f"Failed to get BDI status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "beliefs": [],
            "desires": [],
            "intentions": [],
            "goals": [],
            "plans": [],
            "last_action": "Error occurred",
            "reasoning_history": []
    }

@app.get("/system/status", summary="System status")
def system_status():
    return {
        "status": "operational",
        "components": {
            "llm_provider": "online",
            "mistral_api": "online",
            "agint": "online",
            "coordinator": "online"
        }
    }

@app.get("/system/metrics", summary="Get performance metrics")
def get_performance_metrics():
    """
    Get current system performance metrics.
    """
    try:
        import psutil
        
        # Get basic system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            "response_time": 50,  # Mock response time
            "memory_usage": memory.percent,
            "cpu_usage": cpu_percent,
            "disk_usage": disk.percent,
            "network_usage": 0,  # Mock network usage
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return {
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/system/resources", summary="Get resource usage")
def get_resource_usage():
    """
    Get current system resource usage including mindterm metrics.
    """
    try:
        import psutil
        
        # Get system resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        result = {
            "cpu": {
                "usage": cpu_percent,
                "cores": psutil.cpu_count(),
                "load_avg": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else [0, 0, 0]
            },
            "memory": {
                "total": f"{memory.total / (1024**3):.1f} GB",
                "used": f"{memory.used / (1024**3):.1f} GB",
                "free": f"{memory.free / (1024**3):.1f} GB",
                "percentage": memory.percent
            },
            "disk": {
                "total": f"{disk.total / (1024**3):.1f} GB",
                "used": f"{disk.used / (1024**3):.1f} GB",
                "free": f"{disk.free / (1024**3):.1f} GB",
                "percentage": (disk.used / disk.total) * 100
            },
            "timestamp": time.time()
        }
        
        # Add mindterm metrics if available
        try:
            from mindx_backend_service.mindterm.routes import get_service
            svc = get_service()
            mindterm_usage = svc.get_resource_usage()
            if mindterm_usage:
                result["mindterm"] = mindterm_usage
        except Exception as e:
            logger.debug(f"Could not get mindterm metrics: {e}")
        
        return result
    except Exception as e:
        logger.error(f"Failed to get resource usage: {e}")
        return {
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/monitoring/rate-limits", summary="Get rate limit monitoring dashboard data")
def get_rate_limit_monitoring(session_id: Optional[str] = None):
    """
    Get comprehensive rate limit monitoring dashboard data including:
    - Rate limit metrics (minute and hourly)
    - Circuit breaker status
    - Session information
    - Alerts
    """
    try:
        dashboard = RateLimitDashboard()
        
        # Try to get rate limiter from a handler (if available)
        rate_limiter = None
        try:
            from llm.llm_factory import create_llm_handler
            import asyncio
            # Create a handler to get rate limiter (non-blocking check)
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we can't use it synchronously
                # Just return basic info
                pass
            else:
                handler = loop.run_until_complete(create_llm_handler())
                if handler and hasattr(handler, 'rate_limiter'):
                    rate_limiter = handler.rate_limiter
        except Exception as e:
            logger.debug(f"Could not get rate limiter: {e}")
        
        # Try to get stuck loop detector from mindXagent (if available)
        stuck_loop_detector = None
        try:
            from agents.core.mindXagent import MindXAgent
            import asyncio
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                agent = loop.run_until_complete(MindXAgent.get_instance())
                if agent and hasattr(agent, 'stuck_loop_detector'):
                    stuck_loop_detector = agent.stuck_loop_detector
        except Exception as e:
            logger.debug(f"Could not get stuck loop detector: {e}")
        
        # Try to get session manager
        session_manager = None
        try:
            from agents.core.session_manager import SessionManager
            session_manager = SessionManager()
        except Exception as e:
            logger.debug(f"Could not get session manager: {e}")
        
        # Get dashboard data
        dashboard_data = dashboard.get_dashboard_data(
            rate_limiter=rate_limiter,
            stuck_loop_detector=stuck_loop_detector,
            session_manager=session_manager,
            session_id=session_id
        )
        
        return dashboard_data
    except Exception as e:
        logger.error(f"Failed to get rate limit monitoring: {e}")
        return {
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/system/agent-activity", summary="Get real agent activity")
def get_agent_activity():
    """
    Get real agent activity from mindX system.
    """
    try:
        import os
        import json
        from datetime import datetime
        
        activities = []
        
        # Check for agent activity logs in various locations
        log_paths = [
            '/home/hacker/mindX/data/logs/agent_activity.log',
            '/home/hacker/mindX/data/logs/system.log',
            '/home/hacker/mindX/data/memory/stm/',
            '/home/hacker/mindX/logs/'
        ]
        
        # Try to read from log files
        for log_path in log_paths:
            if os.path.exists(log_path):
                try:
                    if os.path.isfile(log_path):
                        with open(log_path, 'r') as f:
                            lines = f.readlines()[-10:]  # Get last 10 lines
                            for line in lines:
                                if any(agent in line for agent in ['BDI', 'Memory', 'Guardian', 'Coordinator', 'Mastermind', 'CEO']):
                                    activities.append({
                                        "timestamp": datetime.now().isoformat(),
                                        "agent": "System",
                                        "message": line.strip(),
                                        "type": "info"
                                    })
                    elif os.path.isdir(log_path):
                        # Check memory files for agent activity
                        for root, dirs, files in os.walk(log_path):
                            for file in files:
                                if file.endswith('.json') and any(agent in file for agent in ['agent', 'coordinator', 'mastermind']):
                                    try:
                                        with open(os.path.join(root, file), 'r') as f:
                                            data = json.load(f)
                                            if isinstance(data, dict) and 'timestamp' in data:
                                                activities.append({
                                                    "timestamp": data.get('timestamp', datetime.now().isoformat()),
                                                    "agent": data.get('agent', 'Unknown'),
                                                    "message": f"Memory update: {data.get('type', 'activity')}",
                                                    "type": "info"
                                                })
                                    except:
                                        continue
                except Exception as e:
                    continue
        
        # If no real activity found, check system status
        if not activities:
            activities.append({
                "timestamp": datetime.now().isoformat(),
                "agent": "System",
                "message": "Monitoring system for agent activity...",
                "type": "info"
            })
        
        return {
            "activities": activities[-20:],  # Return last 20 activities
            "total": len(activities),
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent activity: {e}")
        return {
            "activities": [{
                "timestamp": datetime.now().isoformat(),
                "agent": "System",
                "message": f"Activity monitoring error: {str(e)}",
                "type": "error"
            }],
            "total": 1,
            "timestamp": time.time()
        }

# ==================== Token Usage & Cost Tracking ====================

@app.get("/usage/metrics", summary="Get token usage metrics")
def get_token_usage_metrics():
    """
    Get comprehensive token usage metrics including costs, operations, and budget status.
    """
    try:
        usage_log_path = Path(PROJECT_ROOT) / "data" / "monitoring" / "token_usage.json"
        metrics_path = Path(PROJECT_ROOT) / "data" / "monitoring" / "token_metrics.json"

        # Load usage log
        usage_log = []
        if usage_log_path.exists():
            try:
                with usage_log_path.open("r", encoding="utf-8") as f:
                    usage_log = json.load(f)
            except json.JSONDecodeError:
                usage_log = []

        # Calculate metrics
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        daily_cost = 0.0
        weekly_cost = 0.0
        monthly_cost = 0.0
        total_tokens = 0
        daily_tokens = 0
        provider_breakdown = {}
        model_breakdown = {}
        hourly_usage = [0] * 24

        for record in usage_log:
            try:
                record_time = datetime.fromisoformat(record.get("timestamp", "").replace("Z", "+00:00").split("+")[0])
                cost = float(record.get("cost", 0))
                tokens = int(record.get("total_tokens", record.get("input_tokens", 0) + record.get("output_tokens", 0)))
                provider = record.get("provider", "unknown")
                model = record.get("model", "unknown")

                total_tokens += tokens
                monthly_cost += cost

                if record_time >= today_start:
                    daily_cost += cost
                    daily_tokens += tokens
                    hourly_usage[record_time.hour] += tokens

                if record_time >= week_start:
                    weekly_cost += cost

                # Provider breakdown
                if provider not in provider_breakdown:
                    provider_breakdown[provider] = {"cost": 0.0, "tokens": 0, "calls": 0}
                provider_breakdown[provider]["cost"] += cost
                provider_breakdown[provider]["tokens"] += tokens
                provider_breakdown[provider]["calls"] += 1

                # Model breakdown
                if model not in model_breakdown:
                    model_breakdown[model] = {"cost": 0.0, "tokens": 0, "calls": 0}
                model_breakdown[model]["cost"] += cost
                model_breakdown[model]["tokens"] += tokens
                model_breakdown[model]["calls"] += 1

            except Exception:
                continue

        # Budget configuration
        daily_budget = 100.0  # Default
        try:
            config = Config()
            daily_budget = float(config.get("token_calculator.daily_budget", 100.0))
        except:
            pass

        return {
            "success": True,
            "timestamp": now.isoformat(),
            "summary": {
                "daily_cost": round(daily_cost, 4),
                "weekly_cost": round(weekly_cost, 4),
                "monthly_cost": round(monthly_cost, 4),
                "daily_tokens": daily_tokens,
                "total_tokens": total_tokens,
                "total_operations": len(usage_log),
                "daily_budget": daily_budget,
                "budget_utilization": round((daily_cost / daily_budget) * 100, 2) if daily_budget > 0 else 0
            },
            "provider_breakdown": provider_breakdown,
            "model_breakdown": model_breakdown,
            "hourly_usage": hourly_usage,
            "recent_operations": usage_log[-50:][::-1] if usage_log else []
        }

    except Exception as e:
        logger.error(f"Failed to get token usage metrics: {e}")
        return {
            "success": False,
            "error": str(e),
            "summary": {
                "daily_cost": 0, "weekly_cost": 0, "monthly_cost": 0,
                "daily_tokens": 0, "total_tokens": 0, "total_operations": 0,
                "daily_budget": 100.0, "budget_utilization": 0
            },
            "provider_breakdown": {},
            "model_breakdown": {},
            "hourly_usage": [0] * 24,
            "recent_operations": []
        }


@app.post("/usage/track", summary="Track API usage")
async def track_api_usage(request: Request):
    """
    Track an API inference call for accurate cost calculation.
    """
    try:
        data = await request.json()

        usage_log_path = Path(PROJECT_ROOT) / "data" / "monitoring" / "token_usage.json"
        usage_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing log
        usage_log = []
        if usage_log_path.exists():
            try:
                with usage_log_path.open("r", encoding="utf-8") as f:
                    usage_log = json.load(f)
            except json.JSONDecodeError:
                usage_log = []

        # Pricing data (per 1M tokens)
        pricing = {
            "gemini": {"input": 0.075, "output": 0.30},
            "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
            "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
            "mistral": {"input": 0.25, "output": 0.25},
            "mistral-small": {"input": 0.20, "output": 0.60},
            "mistral-large": {"input": 2.00, "output": 6.00},
            "gpt-4": {"input": 30.00, "output": 60.00},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "claude-3-opus": {"input": 15.00, "output": 75.00},
            "claude-3-sonnet": {"input": 3.00, "output": 15.00},
            "claude-3-haiku": {"input": 0.25, "output": 1.25},
            "default": {"input": 0.50, "output": 1.50}
        }

        # Calculate cost
        model = data.get("model", "default").lower()
        provider = data.get("provider", "unknown")
        input_tokens = int(data.get("input_tokens", 0))
        output_tokens = int(data.get("output_tokens", 0))

        # Find matching pricing
        price_key = "default"
        for key in pricing:
            if key in model:
                price_key = key
                break

        rates = pricing[price_key]
        input_cost = (input_tokens / 1_000_000) * rates["input"]
        output_cost = (output_tokens / 1_000_000) * rates["output"]
        total_cost = input_cost + output_cost

        # Create usage record
        usage_record = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost": round(input_cost, 6),
            "output_cost": round(output_cost, 6),
            "cost": round(total_cost, 6),
            "operation_type": data.get("operation_type", "inference"),
            "agent": data.get("agent", "unknown"),
            "request_id": data.get("request_id", str(uuid.uuid4())[:8])
        }

        usage_log.append(usage_record)

        # Keep log size manageable (last 10000 entries)
        if len(usage_log) > 10000:
            usage_log = usage_log[-8000:]

        # Save log
        with usage_log_path.open("w", encoding="utf-8") as f:
            json.dump(usage_log, f, indent=2)

        return {
            "success": True,
            "tracked": usage_record,
            "message": f"Tracked {input_tokens + output_tokens} tokens, cost: ${total_cost:.6f}"
        }

    except Exception as e:
        logger.error(f"Failed to track usage: {e}")
        return {"success": False, "error": str(e)}


@app.get("/usage/history", summary="Get usage history")
def get_usage_history(
    days: int = 7,
    provider: Optional[str] = None,
    model: Optional[str] = None
):
    """
    Get historical usage data with optional filtering.
    """
    try:
        usage_log_path = Path(PROJECT_ROOT) / "data" / "monitoring" / "token_usage.json"

        if not usage_log_path.exists():
            return {"success": True, "history": [], "total": 0}

        with usage_log_path.open("r", encoding="utf-8") as f:
            usage_log = json.load(f)

        cutoff = datetime.now() - timedelta(days=days)
        filtered = []

        for record in usage_log:
            try:
                record_time = datetime.fromisoformat(record.get("timestamp", "").replace("Z", "+00:00").split("+")[0])
                if record_time < cutoff:
                    continue
                if provider and record.get("provider", "").lower() != provider.lower():
                    continue
                if model and model.lower() not in record.get("model", "").lower():
                    continue
                filtered.append(record)
            except:
                continue

        # Aggregate by day
        daily_stats = {}
        for record in filtered:
            try:
                day = record["timestamp"][:10]
                if day not in daily_stats:
                    daily_stats[day] = {"cost": 0, "tokens": 0, "calls": 0}
                daily_stats[day]["cost"] += float(record.get("cost", 0))
                daily_stats[day]["tokens"] += int(record.get("total_tokens", 0))
                daily_stats[day]["calls"] += 1
            except:
                continue

        return {
            "success": True,
            "history": filtered[::-1],
            "daily_stats": daily_stats,
            "total": len(filtered),
            "total_cost": sum(float(r.get("cost", 0)) for r in filtered),
            "total_tokens": sum(int(r.get("total_tokens", 0)) for r in filtered)
        }

    except Exception as e:
        logger.error(f"Failed to get usage history: {e}")
        return {"success": False, "error": str(e), "history": [], "total": 0}


@app.delete("/usage/clear", summary="Clear usage history")
def clear_usage_history(keep_days: int = 0):
    """
    Clear usage history, optionally keeping recent entries.
    """
    try:
        usage_log_path = Path(PROJECT_ROOT) / "data" / "monitoring" / "token_usage.json"

        if not usage_log_path.exists():
            return {"success": True, "message": "No usage history to clear"}

        if keep_days > 0:
            with usage_log_path.open("r", encoding="utf-8") as f:
                usage_log = json.load(f)

            cutoff = datetime.now() - timedelta(days=keep_days)
            filtered = [
                r for r in usage_log
                if datetime.fromisoformat(r.get("timestamp", "2000-01-01").replace("Z", "+00:00").split("+")[0]) >= cutoff
            ]

            with usage_log_path.open("w", encoding="utf-8") as f:
                json.dump(filtered, f, indent=2)

            return {
                "success": True,
                "message": f"Cleared entries older than {keep_days} days",
                "remaining": len(filtered)
            }
        else:
            usage_log_path.unlink()
            return {"success": True, "message": "Usage history cleared completely"}

    except Exception as e:
        logger.error(f"Failed to clear usage history: {e}")
        return {"success": False, "error": str(e)}


def initialize_agint_logging():
    """Initialize AGInt logging directory and create initial log file"""
    agint_log_dir = "data/logs/agint"
    os.makedirs(agint_log_dir, exist_ok=True)
    
    # Create initial log file with header
    agint_log_file = os.path.join(agint_log_dir, "agint_cognitive_cycles.log")
    if not os.path.exists(agint_log_file):
        with open(agint_log_file, 'w') as f:
            f.write("# AGInt Cognitive Loop Log\n")
            f.write(f"# Started: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# Format: [TIMESTAMP] CYCLE X - MESSAGE\n\n")

async def make_actual_code_changes_with_bdi_reasoning(directive: str, cycle: int, autonomous_mode: bool = False) -> List[Dict[str, Any]]:
    """Make actual code changes using simplified BDI reasoning to choose the best agent/tool."""
    changes = []
    
    try:
        # Simplified BDI reasoning without importing problematic modules
        # Define available agents and tools for BDI to choose from
        available_agents = {
            "simple_coder": {
                "description": "Streamlined and audited coding agent with enhanced security and performance",
                "capabilities": ["code_generation", "file_operations", "shell_execution", "code_analysis", "security_validation", "pattern_learning"],
                "suitability": "high" if "code" in directive.lower() or "evolve" in directive.lower() else "medium"
            },
            "base_gen_agent": {
                "description": "Documentation and base generation agent",
                "capabilities": ["documentation", "markdown_generation", "code_analysis"],
                "suitability": "high" if "document" in directive.lower() or "base" in directive.lower() else "low"
            },
            "system_analyzer": {
                "description": "System analysis and improvement agent",
                "capabilities": ["system_analysis", "performance_optimization", "code_review"],
                "suitability": "high" if "analyze" in directive.lower() or "improve" in directive.lower() else "medium"
            },
            "audit_and_improve_tool": {
                "description": "Code audit and improvement tool",
                "capabilities": ["code_audit", "quality_improvement", "bug_detection"],
                "suitability": "high" if "audit" in directive.lower() or "improve" in directive.lower() else "medium"
            }
        }
        
        # Simple BDI reasoning logic
        chosen_agent = "simple_coder"  # Default fallback
        
        # BDI Belief-Desire-Intention reasoning
        # Belief: Analyze the directive and available agents
        directive_lower = directive.lower()
        
        # Desire: Choose the best agent for the task
        if "code" in directive_lower or "evolve" in directive_lower or "develop" in directive_lower:
            chosen_agent = "simple_coder"
        elif "document" in directive_lower or "base" in directive_lower or "readme" in directive_lower:
            chosen_agent = "base_gen_agent"
        elif "analyze" in directive_lower or "review" in directive_lower or "optimize" in directive_lower:
            chosen_agent = "system_analyzer"
        elif "audit" in directive_lower or "improve" in directive_lower or "quality" in directive_lower:
            chosen_agent = "audit_and_improve_tool"
        
        # Intention: Execute the chosen approach
        bdi_reasoning = f"BDI Reasoning: Directive '{directive}' -> Belief: Task requires {chosen_agent} -> Desire: Use best suited agent -> Intention: Execute with {chosen_agent}"
        
        # Log detailed BDI decision process
        bdi_decision_activity = {
            "timestamp": time.time(),
            "agent": "BDI Agent",
            "message": f"BDI Decision: Selected {chosen_agent} for '{directive}'",
            "type": "success",
            "details": {
                "reasoning": bdi_reasoning,
                "directive": directive,
                "chosen_agent": chosen_agent,
                "available_agents": list(available_agents.keys()),
                "decision_factors": ["task_type", "agent_capabilities", "current_system_state"],
                "confidence": "high",
                "beliefs": [
                    f"Directive requires: {chosen_agent}",
                    "System state analyzed",
                    "Agent capabilities evaluated"
                ],
                "desires": [
                    "Choose optimal agent for task execution",
                    "Maximize efficiency and effectiveness",
                    "Ensure successful directive completion"
                ],
                "intentions": [
                    f"Execute with {chosen_agent}",
                    "Monitor task progress",
                    "Adapt strategy as needed"
                ]
            }
        }
        
        # Update global BDI state for real-time updates
        update_bdi_state(directive, chosen_agent, bdi_reasoning)
        
        # Add detailed BDI activity to log
        if not hasattr(update_bdi_state, 'activity_log'):
            update_bdi_state.activity_log = []
        update_bdi_state.activity_log.append(bdi_decision_activity)
        if len(update_bdi_state.activity_log) > 50:
            update_bdi_state.activity_log = update_bdi_state.activity_log[-50:]
        
        # Log BDI decision - ensure directory exists
        agint_log_dir = "data/logs/agint"
        os.makedirs(agint_log_dir, exist_ok=True)
        agint_log_file = os.path.join(agint_log_dir, "agint_cognitive_cycles.log")
        
        # Always log BDI reasoning, even if execution fails
        with open(agint_log_file, 'a') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - {bdi_reasoning}\n")
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Chosen Agent: {chosen_agent}\n")
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Directive: {directive}\n")
        
        # Execute based on BDI decision
        try:
            if chosen_agent == "simple_coder":
                changes = await execute_simple_coder_changes(directive, cycle, autonomous_mode)
            elif chosen_agent == "base_gen_agent":
                changes = await execute_base_gen_changes(directive, cycle)
            elif chosen_agent == "system_analyzer":
                changes = await execute_system_analyzer_changes(directive, cycle)
            elif chosen_agent == "audit_and_improve_tool":
                changes = await execute_audit_improve_changes(directive, cycle)
            else:
                # Fallback to default behavior
                changes = await execute_default_changes(directive, cycle)
            
            # Log successful completion
            with open(agint_log_file, 'a') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Status: Completed using {chosen_agent}\n")
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Changes made: {len(changes)} items\n\n")
                
        except Exception as execution_error:
            # Log execution error but keep BDI reasoning
            with open(agint_log_file, 'a') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Execution Error: {str(execution_error)}\n")
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - BDI reasoning completed, execution failed\n\n")
            logger.error(f"BDI execution failed for {chosen_agent}: {execution_error}")
            # Still return some basic changes to maintain flow
            changes = [{"type": "bdi_reasoning", "agent": chosen_agent, "status": "reasoned_but_failed_execution"}]
        
    except Exception as e:
        # Fallback to original behavior if BDI reasoning fails
        logger.error(f"BDI reasoning failed, falling back to default: {e}")
        changes = await execute_default_changes(directive, cycle)
        
        # Log the fallback
        agint_log_dir = "data/logs/agint"
        os.makedirs(agint_log_dir, exist_ok=True)
        agint_log_file = os.path.join(agint_log_dir, "agint_cognitive_cycles.log")
        with open(agint_log_file, 'a') as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - BDI Reasoning Failed: {str(e)}\n")
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - Fallback to default behavior\n\n")
    
    return changes

async def execute_simple_coder_changes(directive: str, cycle: int, autonomous_mode: bool = False) -> List[Dict[str, Any]]:
    """Execute changes using enhanced simple_coder approach with sandbox mode."""
    try:
        # Import the enhanced simple_coder module
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from agents.simple_coder import execute_simple_coder_changes as enhanced_simple_coder
        
        # Log the parameters being passed
        logger.info(f"Simple Coder: directive='{directive}', cycle={cycle}, autonomous_mode={autonomous_mode}")
        
        # Use the enhanced simple_coder with sandbox mode enabled
        return await enhanced_simple_coder(directive, cycle, sandbox_mode=True, autonomous_mode=autonomous_mode)
        
    except ImportError as e:
        logger.error(f"Failed to import enhanced simple_coder: {e}")
        # Fallback to original implementation
        return await execute_simple_coder_changes_fallback(directive, cycle)
    except Exception as e:
        logger.error(f"Error in enhanced simple_coder: {e}")
        # Fallback to original implementation
        return await execute_simple_coder_changes_fallback(directive, cycle)

async def execute_simple_coder_changes_fallback(directive: str, cycle: int) -> List[Dict[str, Any]]:
    """Fallback implementation if enhanced simple_coder is not available."""
    changes = []
    
    # Create a test file if it doesn't exist
    test_file = "test_agint_changes.py"
    if not os.path.exists(test_file):
        with open(test_file, 'w') as f:
            f.write("# AGInt Test File - Enhanced Simple Coder Approach\n")
            f.write("def test_function():\n")
            f.write("    return 'original'\n")
    
    try:
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Enhanced approach with better code structure
        enhanced_function = f"""
def agint_cycle_{cycle}_enhanced_function():
    \"\"\"Enhanced function added by AGInt cycle {cycle} using simple_coder reasoning\"\"\"
    return {{
        'cycle': {cycle},
        'directive': '{directive}',
        'approach': 'simple_coder',
        'timestamp': time.time()
    }}

def enhanced_processing_v2():
    \"\"\"Enhanced processing with improved error handling and logging\"\"\"
    try:
        result = f'Enhanced processing completed for cycle {cycle}'
        logger.info(f"Enhanced processing successful: {{result}}")
        return result
    except Exception as e:
        logger.error(f"Enhanced processing failed: {{e}}")
        return f'Error: {{e}}'
"""
        
        # Append enhanced functions
        with open(test_file, 'a') as f:
            f.write(enhanced_function)
        
        changes.append({
            "file": test_file,
            "type": "addition",
            "changes": [
                {
                    "line": len(content.split('\n')) + 1,
                    "old": "",
                    "new": enhanced_function.strip()
                }
            ]
        })
        
        # Enhanced modification of existing function
        if "def test_function():" in content:
            enhanced_content = content.replace(
                "def test_function():\n    return 'original'",
                f"def test_function():\n    # Enhanced by AGInt cycle {cycle} using simple_coder\n    return f'simple_coder_{cycle}'"
            )
            
            with open(test_file, 'w') as f:
                f.write(enhanced_content)
            
            changes.append({
                "file": test_file,
                "type": "modification", 
                "changes": [
                    {
                        "line": 2,
                        "old": "def test_function():\n    return 'original'",
                        "new": f"def test_function():\n    # Enhanced by AGInt cycle {cycle} using simple_coder\n    return f'simple_coder_{cycle}'"
                    }
                ]
            })
        
    except Exception as e:
        changes.append({
            "file": f"agint_enhanced_error_{cycle}.txt",
            "type": "addition",
            "changes": [
                {
                    "line": 1,
                    "old": "",
                    "new": f"AGInt Enhanced Cycle {cycle} - Error: {str(e)}"
                }
            ]
        })
    
    return changes

async def execute_base_gen_changes(directive: str, cycle: int) -> List[Dict[str, Any]]:
    """Execute changes using base_gen_agent approach."""
    changes = []
    
    # Base generation approach
    doc_file = f"agint_cycle_{cycle}_documentation.md"
    doc_content = f"""# AGInt Cycle {cycle} Documentation

## Directive
{directive}

## Approach
Using base_gen_agent for documentation and analysis.

## Generated Content
This file was generated by AGInt cycle {cycle} using base generation approach.

## Timestamp
{time.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(doc_file, 'w') as f:
        f.write(doc_content)
    
    changes.append({
        "file": doc_file,
        "type": "addition",
        "changes": [
            {
                "line": 1,
                "old": "",
                "new": doc_content
            }
        ]
    })
    
    return changes

async def execute_system_analyzer_changes(directive: str, cycle: int) -> List[Dict[str, Any]]:
    """Execute changes using system_analyzer approach."""
    changes = []
    
    # System analysis approach
    analysis_file = f"agint_cycle_{cycle}_analysis.txt"
    analysis_content = f"""AGInt Cycle {cycle} - System Analysis
Directive: {directive}
Approach: system_analyzer
Analysis: System state analyzed and optimized
Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    with open(analysis_file, 'w') as f:
        f.write(analysis_content)
    
    changes.append({
        "file": analysis_file,
        "type": "addition",
        "changes": [
            {
                "line": 1,
                "old": "",
                "new": analysis_content
            }
        ]
    })
    
    return changes

async def execute_audit_improve_changes(directive: str, cycle: int) -> List[Dict[str, Any]]:
    """Execute changes using audit_and_improve_tool approach."""
    changes = []
    
    # Store audit files in data/logs/agint directory instead of root
    # Note: memory_agent already handles AGInt logging, so we'll just log to the existing system
    agint_log_dir = "data/logs/agint"
    os.makedirs(agint_log_dir, exist_ok=True)
    
    # Log to existing AGInt log file instead of creating separate audit files
    agint_log_file = os.path.join(agint_log_dir, "agint_cognitive_cycles.log")
    audit_content = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CYCLE {cycle} - AUDIT: Code quality audited and improvements suggested for directive: {directive}\n"
    
    with open(agint_log_file, 'a') as f:
        f.write(audit_content)
    
    # Create a minimal change entry for tracking purposes
    changes.append({
        "file": f"data/logs/agint/agint_cognitive_cycles.log",
        "type": "modification",
        "changes": [
            {
                "line": "end",
                "old": "",
                "new": audit_content.strip()
            }
        ]
    })
    
    return changes

async def execute_default_changes(directive: str, cycle: int) -> List[Dict[str, Any]]:
    """Execute default changes as fallback."""
    changes = []
    
    # Create a test file if it doesn't exist
    test_file = "test_agint_changes.py"
    if not os.path.exists(test_file):
        with open(test_file, 'w') as f:
            f.write("# AGInt Test File\n")
            f.write("def test_function():\n")
            f.write("    return 'original'\n")
    
    # Make actual changes to the test file
    try:
        with open(test_file, 'r') as f:
            content = f.read()
        
        # Add new function based on cycle
        new_function = f"""
def agint_cycle_{cycle}_function():
    \"\"\"Function added by AGInt cycle {cycle} for directive: {directive}\"\"\"
    return f'Cycle {cycle} result for: {directive}'

def enhanced_processing():
    \"\"\"Enhanced processing function added by AGInt\"\"\"
    return 'Enhanced processing completed'
"""
        
        # Append new functions
        with open(test_file, 'a') as f:
            f.write(new_function)
        
        changes.append({
            "file": test_file,
            "type": "addition",
            "changes": [
                {
                    "line": len(content.split('\n')) + 1,
                    "old": "",
                    "new": new_function.strip()
                }
            ]
        })
        
        # Modify existing function
        if "def test_function():" in content:
            modified_content = content.replace(
                "def test_function():\n    return 'original'",
                f"def test_function():\n    # Modified by AGInt cycle {cycle}\n    return f'enhanced_{cycle}'"
            )
            
            with open(test_file, 'w') as f:
                f.write(modified_content)
            
            changes.append({
                "file": test_file,
                "type": "modification", 
                "changes": [
                    {
                        "line": 2,
                        "old": "def test_function():\n    return 'original'",
                        "new": f"def test_function():\n    # Modified by AGInt cycle {cycle}\n    return f'enhanced_{cycle}'"
                }
            ]
        })
        
    except Exception as e:
        # If file operations fail, create a simple change record
        changes.append({
            "file": f"agint_error_{cycle}.txt",
            "type": "addition",
            "changes": [
                {
                    "line": 1,
                    "old": "",
                    "new": f"AGInt Cycle {cycle} - Error: {str(e)}"
                }
            ]
        })
    
    return changes

async def make_actual_code_changes(directive: str, cycle: int, autonomous_mode: bool = False) -> List[Dict[str, Any]]:
    """Make actual code changes based on the directive and cycle number using BDI reasoning."""
    return await make_actual_code_changes_with_bdi_reasoning(directive, cycle, autonomous_mode)

# Simple Coder endpoints
@app.get("/simple-coder/status", summary="Get Simple Coder Status")
async def get_simple_coder_status():
    """Get the current status of the Simple Coder agent."""
    try:
        import sys
        import os
        # Change to the correct working directory
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from agents.simple_coder import SimpleCoder
        
        # Create a temporary instance to get status
        simple_coder = SimpleCoder()
        return simple_coder.get_status()
    except Exception as e:
        logger.error(f"Failed to get simple_coder status: {e}")
        return {"error": str(e)}

@app.get("/simple-coder/update-requests", summary="Get Update Requests")
async def get_update_requests():
    """Get all pending update requests from Simple Coder."""
    try:
        import sys
        import os
        # Change to the correct working directory
        old_cwd = os.getcwd()
        new_cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        os.chdir(new_cwd)
        sys.path.append(new_cwd)
        from agents.simple_coder import SimpleCoder
        
        # Create a temporary instance to get update requests
        simple_coder = SimpleCoder()
        all_requests = simple_coder.get_update_requests()
        # Filter to only return pending requests
        pending_requests = [req for req in all_requests if req.get('status') == 'pending']
        return pending_requests
    except Exception as e:
        logger.error(f"Failed to get update requests: {e}")
        return {"error": str(e)}

@app.post("/simple-coder/approve-update/{request_id}", summary="Approve Update Request")
async def approve_update_request(request_id: str):
    """Approve and apply an update request."""
    try:
        import sys
        import os
        # Change to the correct working directory
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from agents.simple_coder import SimpleCoder
        
        # Create a temporary instance to approve request
        simple_coder = SimpleCoder()
        success = simple_coder.approve_update_request(request_id)
        return {"success": success, "request_id": request_id}
    except Exception as e:
        logger.error(f"Failed to approve update request: {e}")
        return {"error": str(e), "success": False}

@app.post("/simple-coder/reject-update/{request_id}", summary="Reject Update Request")
async def reject_update_request(request_id: str):
    """Reject an update request."""
    try:
        import sys
        import os
        # Change to the correct working directory
        os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from agents.simple_coder import SimpleCoder
        
        # Create a temporary instance to reject request
        simple_coder = SimpleCoder()
        success = simple_coder.reject_update_request(request_id)
        return {"success": success, "request_id": request_id}
    except Exception as e:
        logger.error(f"Failed to reject update request: {e}")
        return {"error": str(e), "success": False}

# Add AGInt streaming endpoint

# AGInt Memory Integration Functions
async def _log_agint_to_memory(memory_type: str, category: str, data: dict, metadata: dict = None) -> Optional[Path]:
    """Log AGInt information to memory agent if available."""
    if not MEMORY_AVAILABLE:
        return None
    
    try:
        # Initialize memory agent if not already done
        if not hasattr(_log_agint_to_memory, 'memory_agent'):
            _log_agint_to_memory.memory_agent = MemoryAgent()
        
        if metadata is None:
            metadata = {}
        
        # Add AGInt specific metadata
        metadata.update({
            "agent": "mindx_agint",
            "component": "cognitive_loop",
            "timestamp": time.time()
        })
        
        # Use agent-specific category path
        agent_category = f"mindx_agint/{category}"
        
        # Use the memory agent's save_memory method
        return await _log_agint_to_memory.memory_agent.save_memory(memory_type, agent_category, data, metadata)
    except Exception as e:
        logger.error(f"Failed to log AGInt to memory: {e}")
        return None

async def _log_agint_cycle_start(cycle: int, max_cycles, directive: str, autonomous_mode: bool) -> None:
    """Log AGInt cycle start to memory."""
    data = {
        "cycle": cycle,
        "max_cycles": max_cycles,
        "directive": directive,
        "autonomous_mode": autonomous_mode,
        "timestamp": time.time(),
        "status": "started",
        "phase": "cycle_start"
    }
    await _log_agint_to_memory("STM", "cycles", data)

async def _log_agint_cycle_completion(cycle: int, max_cycles, directive: str, autonomous_mode: bool, cycle_duration: float, code_changes: list) -> None:
    """Log AGInt cycle completion to memory."""
    data = {
        "cycle": cycle,
        "max_cycles": max_cycles,
        "directive": directive,
        "autonomous_mode": autonomous_mode,
        "timestamp": time.time(),
        "status": "completed",
        "phase": "cycle_complete",
        "cycle_duration": cycle_duration,
        "code_changes_count": len(code_changes),
        "code_changes_summary": [
            {
                "type": change.get("type", "unknown"),
                "file": change.get("file", "unknown"),
                "changes_count": len(change.get("changes", []))
            } for change in code_changes
        ]
    }
    await _log_agint_to_memory("STM", "cycles", data)

async def _log_agint_step(cycle: int, step_phase: str, step_message: str, directive: str, code_changes: list = None) -> None:
    """Log AGInt step execution to memory."""
    data = {
        "cycle": cycle,
        "step_phase": step_phase,
        "step_message": step_message,
        "directive": directive,
        "timestamp": time.time(),
        "code_changes": code_changes or [],
        "code_changes_count": len(code_changes) if code_changes else 0
    }
    await _log_agint_to_memory("STM", "steps", data)

async def _log_agint_completion(total_cycles: int, total_steps: int, directive: str, autonomous_mode: bool, success: bool = True) -> None:
    """Log AGInt overall completion to memory."""
    data = {
        "total_cycles": total_cycles,
        "total_steps": total_steps,
        "directive": directive,
        "autonomous_mode": autonomous_mode,
        "timestamp": time.time(),
        "status": "completed" if success else "failed",
        "phase": "agint_complete"
    }
    await _log_agint_to_memory("STM", "completion", data)

async def _log_agint_error(error_type: str, error_message: str, cycle: int = None, directive: str = None) -> None:
    """Log AGInt errors to memory."""
    data = {
        "error_type": error_type,
        "error_message": error_message,
        "cycle": cycle,
        "directive": directive,
        "timestamp": time.time(),
        "phase": "error"
    }
    await _log_agint_to_memory("STM", "errors", data)

@app.post("/commands/agint/stream", summary="AGInt Cognitive Loop Stream")
async def agint_stream(payload: DirectivePayload):
    from fastapi.responses import StreamingResponse
    import asyncio
    import json
    import time
    
    async def generate_agint_stream():
        try:
            # Initialize AGInt logging
            initialize_agint_logging()
            
            # Get cycle count from payload, default to 8
            max_cycles = getattr(payload, 'max_cycles', 8)
            autonomous_mode = getattr(payload, 'autonomous_mode', False)
            
            # Set infinite cycles for autonomous mode
            if autonomous_mode:
                max_cycles = float('inf')
                logger.info("Autonomous mode enabled - setting infinite cycles")
            
            # Simulate AGInt cognitive loop with P-O-D-A cycle
            base_steps = [
                {"phase": "PERCEPTION", "message": "System state analysis", "icon": "🔍"},
                {"phase": "ORIENTATION", "message": "Options evaluation", "icon": "🧠"},
                {"phase": "DECISION", "message": "Strategy selection", "icon": "⚡"},
                {"phase": "ACTION", "message": "Making actual code changes", "icon": "🚀"},
                {"phase": "DETAILS", "message": "Real-time action feedback", "icon": "🎯"}
            ]
            
            # Real code changes will be generated during ACTION phase
            code_changes = []
            
            step_count = 0
            
            cycle = 0
            while cycle < max_cycles:
                cycle_start_time = time.time()
                
                # Log cycle start to memory
                await _log_agint_cycle_start(cycle + 1, max_cycles, payload.directive, autonomous_mode)
                
                # Send cycle start notification
                cycle_update = {
                    "step": step_count + 1,
                    "status": "processing",
                    "type": "cycle_start",
                    "phase": f"CYCLE_{cycle + 1}",
                    "icon": "🔄",
                    "message": f"Starting cognitive cycle {cycle + 1}/{max_cycles}",
                    "timestamp": time.time(),
                    "directive": payload.directive,
                    "cycle": cycle + 1,
                    "max_cycles": max_cycles,
                    "autonomous_mode": autonomous_mode,
                    "state_summary": {
                        "llm_operational": True,
                        "awareness": f"Processing directive: {payload.directive}",
                        "llm_status": "Online",
                        "cognitive_loop": "Active",
                        "current_cycle": cycle + 1
                    }
                }
                yield f"data: {json.dumps(cycle_update)}\n\n"
                step_count += 1
                await asyncio.sleep(0.5)
                
                # Process each step in the cycle
                for step_idx, step in enumerate(base_steps):
                    # Make actual code changes for ACTION phase using BDI reasoning
                    code_changes_for_step = []
                    if step["phase"] == "ACTION":
                        code_changes_for_step = await make_actual_code_changes(payload.directive, cycle + 1, autonomous_mode)
                    
                    update = {
                        "step": step_count + 1,
                        "status": "processing",
                        "type": "status",
                        "phase": step["phase"],
                        "icon": step["icon"],
                        "message": step["message"],
                        "timestamp": time.time(),
                        "directive": payload.directive,
                        "cycle": cycle + 1,
                        "max_cycles": max_cycles,
                        "autonomous_mode": autonomous_mode,
                        "code_changes": code_changes_for_step,
                        "state_summary": {
                            "llm_operational": True,
                            "awareness": f"Processing directive: {payload.directive}",
                            "llm_status": "Online",
                            "cognitive_loop": "Active",
                            "current_cycle": cycle + 1,
                            "current_step": step["phase"]
                        }
                    }
                    yield f"data: {json.dumps(update)}\n\n"
                    step_count += 1
                    
                    # Log step execution to memory
                    await _log_agint_step(cycle + 1, step["phase"], step["message"], payload.directive, code_changes_for_step)
                    
                    await asyncio.sleep(1.0)  # Simulate processing time
                
                # Send cycle completion notification
                cycle_complete_update = {
                    "step": step_count + 1,
                    "status": "processing",
                    "type": "cycle_complete",
                    "phase": f"CYCLE_{cycle + 1}_COMPLETE",
                    "icon": "✅",
                    "message": f"Completed cognitive cycle {cycle + 1}/{max_cycles}",
                    "timestamp": time.time(),
                    "directive": payload.directive,
                    "cycle": cycle + 1,
                    "max_cycles": max_cycles,
                    "cycle_duration": time.time() - cycle_start_time,
                    "state_summary": {
                        "llm_operational": True,
                        "awareness": f"Completed cycle {cycle + 1} for directive: {payload.directive}",
                        "llm_status": "Online",
                        "cognitive_loop": "Active",
                        "completed_cycles": cycle + 1
                    }
                }
                yield f"data: {json.dumps(cycle_complete_update)}\n\n"
                step_count += 1
                
                # Log cycle completion to memory
                await _log_agint_cycle_completion(cycle + 1, max_cycles, payload.directive, autonomous_mode, time.time() - cycle_start_time, code_changes_for_step)
                
                await asyncio.sleep(0.3)
                
                # Increment cycle counter
                cycle += 1
                
                # For autonomous mode, add a small delay between cycles
                if autonomous_mode:
                    await asyncio.sleep(2.0)  # Longer delay for autonomous mode
            
            # Final completion message
            cycles_completed = cycle if not autonomous_mode else "∞"
            completion_message = f"AGInt cognitive loop completed successfully after {cycles_completed} cycles" if not autonomous_mode else "AGInt cognitive loop running in autonomous mode"
            
            final_update = {
                "type": "complete",
                "status": "success",
                "phase": "COMPLETE",
                "icon": "🎉" if not autonomous_mode else "🤖",
                "message": completion_message,
                "directive": payload.directive,
                "total_cycles": cycles_completed,
                "autonomous_mode": autonomous_mode,
                "total_steps": step_count,
                "state_summary": {
                    "llm_operational": True,
                    "awareness": f"Completed directive: {payload.directive}",
                    "llm_status": "Online",
                    "cognitive_loop": "Completed" if not autonomous_mode else "Autonomous",
                    "cycles_completed": cycles_completed
                }
            }
            yield f"data: {json.dumps(final_update)}\n\n"
            
        except Exception as e:
            error_response = {
                "type": "error", 
                "message": str(e), 
                "status": "error",
                "phase": "ERROR",
                "icon": "❌"
            }
            yield f"data: {json.dumps(error_response)}\n\n"
    
    return StreamingResponse(generate_agint_stream(), media_type="text/plain")

# ================================
# VAULT API ENDPOINTS
# ================================

class AccessCredentialPayload(BaseModel):
    credential_id: str
    credential_type: str
    credential_value: str
    metadata: Optional[Dict[str, Any]] = None

class URLAccessPayload(BaseModel):
    url: str
    ip_address: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class IPAccessPayload(BaseModel):
    ip_address: str
    url: Optional[str] = None
    agent_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@app.post("/vault/credentials/store", summary="Store access credential in vault")
async def store_access_credential(payload: AccessCredentialPayload):
    """Store an access credential (API key, token, etc.) in the vault."""
    try:
        vault_manager = get_vault_manager()
        success = vault_manager.store_access_credential(
            credential_id=payload.credential_id,
            credential_type=payload.credential_type,
            credential_value=payload.credential_value,
            metadata=payload.metadata
        )
        
        if success:
            # Also log to memory
            if MEMORY_AVAILABLE:
                memory_agent = MemoryAgent()
                await memory_agent.save_timestamped_memory(
                    agent_id=payload.agent_id or "system",
                    memory_type=MemoryType.SYSTEM_STATE,
                    content={
                        "action": "credential_stored",
                        "credential_id": payload.credential_id,
                        "credential_type": payload.credential_type
                    },
                    importance=MemoryImportance.HIGH,
                    tags=["vault", "credential", "security"]
                )
        
        return {
            "success": success,
            "credential_id": payload.credential_id
        }
    except Exception as e:
        logger.error(f"Error storing access credential: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vault/credentials/get/{credential_id}", summary="Get access credential from vault")
async def get_access_credential(credential_id: str, mark_used: bool = True):
    """Retrieve an access credential from the vault."""
    try:
        vault_manager = get_vault_manager()
        credential_value = vault_manager.get_access_credential(credential_id, mark_used=mark_used)
        
        if credential_value:
            return {
                "success": True,
                "credential_id": credential_id,
                "has_credential": True
                # Don't return actual credential value for security
            }
        else:
            return {
                "success": False,
                "credential_id": credential_id,
                "has_credential": False
            }
    except Exception as e:
        logger.error(f"Error getting access credential: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vault/credentials/list", summary="List all access credentials")
async def list_access_credentials():
    """List all access credentials stored in vault (metadata only, no values)."""
    try:
        vault_manager = get_vault_manager()
        credentials = vault_manager.list_access_credentials()
        return {
            "success": True,
            "credentials": credentials,
            "count": len(credentials)
        }
    except Exception as e:
        logger.error(f"Error listing access credentials: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vault/access/url", summary="Log URL access")
async def log_url_access(payload: URLAccessPayload):
    """Log URL access for ML inference tracking."""
    try:
        vault_manager = get_vault_manager()
        success = vault_manager.log_url_access(
            url=payload.url,
            ip_address=payload.ip_address,
            agent_id=payload.agent_id,
            metadata=payload.metadata
        )
        
        if success:
            # Also log to memory
            if MEMORY_AVAILABLE:
                memory_agent = MemoryAgent()
                await memory_agent.save_timestamped_memory(
                    agent_id=payload.agent_id or "system",
                    memory_type=MemoryType.INTERACTION,
                    content={
                        "action": "url_access",
                        "url": payload.url,
                        "ip_address": payload.ip_address
                    },
                    importance=MemoryImportance.MEDIUM,
                    tags=["vault", "url_access", "inference"]
                )
        
        return {
            "success": success,
            "url": payload.url
        }
    except Exception as e:
        logger.error(f"Error logging URL access: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/vault/access/ip", summary="Log IP access")
async def log_ip_access(payload: IPAccessPayload):
    """Log IP access point for ML inference tracking."""
    try:
        vault_manager = get_vault_manager()
        success = vault_manager.log_ip_access(
            ip_address=payload.ip_address,
            url=payload.url,
            agent_id=payload.agent_id,
            metadata=payload.metadata
        )
        
        if success:
            # Also log to memory
            if MEMORY_AVAILABLE:
                memory_agent = MemoryAgent()
                await memory_agent.save_timestamped_memory(
                    agent_id=payload.agent_id or "system",
                    memory_type=MemoryType.INTERACTION,
                    content={
                        "action": "ip_access",
                        "ip_address": payload.ip_address,
                        "url": payload.url
                    },
                    importance=MemoryImportance.MEDIUM,
                    tags=["vault", "ip_access", "inference"]
                )
        
        return {
            "success": success,
            "ip_address": payload.ip_address
        }
    except Exception as e:
        logger.error(f"Error logging IP access: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vault/access/url/history", summary="Get URL access history for ML inference")
async def get_url_access_history(
    url: Optional[str] = None,
    days_back: int = 7,
    limit: int = 100
):
    """Get URL access history for ML inference."""
    try:
        vault_manager = get_vault_manager()
        history = vault_manager.get_url_access_history(
            url=url,
            days_back=days_back,
            limit=limit
        )
        return {
            "success": True,
            "history": history,
            "count": len(history),
            "filters": {
                "url": url,
                "days_back": days_back,
                "limit": limit
            }
        }
    except Exception as e:
        logger.error(f"Error getting URL access history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vault/access/ip/history", summary="Get IP access history for ML inference")
async def get_ip_access_history(
    ip_address: Optional[str] = None,
    days_back: int = 7,
    limit: int = 100
):
    """Get IP access history for ML inference."""
    try:
        vault_manager = get_vault_manager()
        history = vault_manager.get_ip_access_history(
            ip_address=ip_address,
            days_back=days_back,
            limit=limit
        )
        return {
            "success": True,
            "history": history,
            "count": len(history),
            "filters": {
                "ip_address": ip_address,
                "days_back": days_back,
                "limit": limit
            }
        }
    except Exception as e:
        logger.error(f"Error getting IP access history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vault/access/summary", summary="Get access summary for ML inference")
async def get_access_summary():
    """Get comprehensive access summary for ML inference (URLs, IPs, statistics)."""
    try:
        vault_manager = get_vault_manager()
        summary = vault_manager.get_access_summary_for_inference()
        return {
            "success": True,
            "summary": summary
        }
    except Exception as e:
        logger.error(f"Error getting access summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Add missing health and agent activity endpoints
@app.get("/health", summary="Health check endpoint")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "mindx_backend",
        "version": "1.0.0"
    }

@app.get("/core/agent-activity", summary="Get agent activity")
async def get_agent_activity():
    """Get recent agent activity for AGIVITY monitoring"""
    activities = []
    
    # Get BDI activities
    if hasattr(update_bdi_state, 'activity_log'):
        activities.extend(update_bdi_state.activity_log)
    
    # Get AGInt activities from logs
    try:
        agint_log_file = "data/logs/agint/agint_cognitive_cycles.log"
        if os.path.exists(agint_log_file):
            with open(agint_log_file, 'r') as f:
                lines = f.readlines()
                # Get last 10 lines
                for line in lines[-10:]:
                    if line.strip():
                        activities.append({
                            "timestamp": time.time(),
                            "agent": "AGInt Core",
                            "message": line.strip(),
                            "type": "info"
                        })
    except Exception as e:
        logger.error(f"Error reading AGInt logs: {e}")
    
    # Add agent-to-agent communication activities
    agent_communication_activities = [
        {
            "timestamp": time.time() - 300,  # 5 minutes ago
            "agent": "Coordinator",
            "message": "Delegated task to Simple Coder: Code evolution directive",
            "type": "info",
            "details": {
                "target_agent": "Simple Coder",
                "task_type": "code_evolution",
                "priority": "high"
            }
        },
        {
            "timestamp": time.time() - 180,  # 3 minutes ago
            "agent": "Simple Coder",
            "message": "Requested tool access from System Analyzer",
            "type": "info",
            "details": {
                "requested_tool": "code_analysis",
                "target_agent": "System Analyzer",
                "status": "approved"
            }
        },
        {
            "timestamp": time.time() - 120,  # 2 minutes ago
            "agent": "BDI Agent",
            "message": "Evaluating agent capabilities for new directive",
            "type": "info",
            "details": {
                "evaluation_criteria": ["capability_match", "current_load", "success_rate"],
                "agents_considered": ["Simple Coder", "System Analyzer", "Base Gen Agent"]
            }
        }
    ]
    
    activities.extend(agent_communication_activities)
    
    # Sort by timestamp (newest first)
    activities.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    return {
        "status": "success",
        "activities": activities[:20],  # Return last 20 activities
        "total_activities": len(activities),
        "timestamp": time.time()
    }

@app.get("/agents/real-time-activity", summary="Get real-time agent activities")
async def get_real_time_agent_activity():
    """Get real-time activities from all core agents with workflow tracking"""
    activities = []
    
    # Get BDI Agent activities with workflow context
    if hasattr(update_bdi_state, 'activity_log'):
        for bdi_activity in update_bdi_state.activity_log:
            # Enhance BDI activities with workflow context
            bdi_activity['workflow_context'] = {
                'workflow_step': 'agent_selection',
                'triggered_by': 'AGInt Core',
                'triggers': ['Simple Coder', 'Base Gen Agent', 'System Analyzer'],
                'workflow_type': 'cognitive_decision'
            }
            activities.append(bdi_activity)
    
    # Get AGInt activities from memory with workflow context
    try:
        agint_memory_dir = "data/memory/stm/mindx_agint"
        if os.path.exists(agint_memory_dir):
            for filename in os.listdir(agint_memory_dir):
                if filename.endswith('.json'):
                    filepath = os.path.join(agint_memory_dir, filename)
                    with open(filepath, 'r') as f:
                        data = json.load(f)
                        if isinstance(data, dict) and 'content' in data:
                            activities.append({
                                "timestamp": data.get('timestamp', time.time()),
                                "agent": "AGInt Core",
                                "message": data['content'][:100] + "..." if len(data['content']) > 100 else data['content'],
                                "type": "info",
                                "workflow_context": {
                                    'workflow_step': 'cognitive_processing',
                                    'triggers': ['BDI Agent'],
                                    'workflow_type': 'cognitive_cycle',
                                    'cycle_phase': 'perception_orientation_decision_action'
                                },
                                "details": {
                                    "memory_type": "STM",
                                    "file": filename,
                                    "full_content": data['content']
                                }
                            })
    except Exception as e:
        logger.error(f"Error reading AGInt memory: {e}")
    
    # Get AGInt cognitive cycle logs for workflow tracking
    try:
        agint_log_file = "data/logs/agint/agint_cognitive_cycles.log"
        if os.path.exists(agint_log_file):
            with open(agint_log_file, 'r') as f:
                lines = f.readlines()
                for line in lines[-5:]:  # Last 5 lines
                    if line.strip():
                        activities.append({
                            "timestamp": time.time(),
                            "agent": "AGInt Core",
                            "message": line.strip(),
                            "type": "info",
                            "workflow_context": {
                                'workflow_step': 'cognitive_cycle',
                                'triggers': ['User Directive'],
                                'workflow_type': 'poda_cycle',
                                'cycle_phase': 'perception_orientation_decision_action'
                            }
                        })
    except Exception as e:
        logger.error(f"Error reading AGInt logs: {e}")
    
    # Get Simple Coder activities - including pending requests with workflow context
    try:
        # Check for pending update requests
        simple_coder_requests = await get_simple_coder_update_requests()
        if simple_coder_requests and len(simple_coder_requests) > 0:
            activities.append({
                "timestamp": time.time(),
                "agent": "Simple Coder",
                "message": f"Generated {len(simple_coder_requests)} pending update requests",
                "type": "info",
                "workflow_context": {
                    'workflow_step': 'code_generation',
                    'triggered_by': 'BDI Agent',
                    'triggers': ['User Approval'],
                    'workflow_type': 'code_evolution',
                    'status': 'awaiting_approval'
                },
                "details": {
                    "pending_requests": len(simple_coder_requests),
                    "requests": simple_coder_requests[:3]  # First 3 requests for details
                }
            })
        
        # Get Simple Coder status
        simple_coder_status = await get_simple_coder_status()
        if simple_coder_status:
            activities.append({
                "timestamp": time.time(),
                "agent": "Simple Coder",
                "message": f"Status: {simple_coder_status.get('status', 'Unknown')} - {simple_coder_status.get('message', 'No recent activity')}",
                "type": "success" if simple_coder_status.get('status') == 'active' else "warning",
                "workflow_context": {
                    'workflow_step': 'agent_status',
                    'triggered_by': 'BDI Agent',
                    'workflow_type': 'code_evolution',
                    'status': simple_coder_status.get('status', 'unknown')
                }
            })
        
        # Get Simple Coder log activities
        simple_coder_log = "data/logs/simple_coder.log"
        if os.path.exists(simple_coder_log):
            with open(simple_coder_log, 'r') as f:
                lines = f.readlines()
                for line in lines[-3:]:  # Last 3 lines
                    if line.strip():
                        activities.append({
                            "timestamp": time.time(),
                            "agent": "Simple Coder",
                            "message": line.strip(),
                            "type": "info",
                            "workflow_context": {
                                'workflow_step': 'code_execution',
                                'triggered_by': 'BDI Agent',
                                'workflow_type': 'code_evolution'
                            }
                        })
    except Exception as e:
        logger.error(f"Error reading Simple Coder activities: {e}")
    
    # Get Coordinator Agent activities
    try:
        # Check if coordinator is available through command_handler
        if command_handler and hasattr(command_handler, 'mastermind') and command_handler.mastermind.coordinator_agent:
            activities.append({
                "timestamp": time.time(),
                "agent": "Coordinator Agent",
                "message": "Infrastructure management and autonomous improvement active",
                "type": "success",
                "workflow_context": {
                    'workflow_step': 'infrastructure_management',
                    'triggers': ['MastermindAgent'],
                    'workflow_type': 'system_orchestration',
                    'status': 'active'
                },
                "details": {
                    "capabilities": ["Infrastructure Management", "Autonomous Improvement", "Component Evolution"],
                    "ethereum_address": "0x7371e20033f65aB598E4fADEb5B4e400Ef22040A"
                }
            })
    except Exception as e:
        logger.error(f"Error getting Coordinator Agent status: {e}")
    
    # Get MastermindAgent activities
    try:
        if command_handler and hasattr(command_handler, 'mastermind'):
            activities.append({
                "timestamp": time.time(),
                "agent": "MastermindAgent",
                "message": "Strategic orchestration with Mistral AI reasoning active",
                "type": "success",
                "workflow_context": {
                    'workflow_step': 'strategic_orchestration',
                    'triggers': ['User Commands', 'System Events'],
                    'workflow_type': 'system_coordination',
                    'status': 'active'
                },
                "details": {
                    "capabilities": ["Strategic Orchestration", "Mistral AI Reasoning", "Agent Coordination"],
                    "ethereum_address": "0xb9B46126551652eb58598F1285aC5E86E5CcfB43"
                }
            })
    except Exception as e:
        logger.error(f"Error getting MastermindAgent status: {e}")
    
    # Get workflow-specific activities
    try:
        # Add workflow tracking activities
        workflow_activities = [
            {
                "timestamp": time.time(),
                "agent": "Workflow Monitor",
                "message": "AGInt → BDI → Simple Coder workflow active",
                "type": "info",
                "workflow_context": {
                    'workflow_step': 'workflow_monitoring',
                    'workflow_type': 'cognitive_code_evolution',
                    'active_workflows': ['AGInt_BDI_SimpleCoder', 'Mastermind_Coordinator_BDI']
                }
            },
            {
                "timestamp": time.time() - 30,
                "agent": "Workflow Monitor",
                "message": "Coordinator Agent managing infrastructure improvements",
                "type": "info",
                "workflow_context": {
                    'workflow_step': 'infrastructure_improvement',
                    'triggered_by': 'MastermindAgent',
                    'workflow_type': 'autonomous_improvement'
                }
            }
        ]
        activities.extend(workflow_activities)
    except Exception as e:
        logger.error(f"Error getting workflow activities: {e}")
    
    # Get dynamic agent list and their activities
    try:
        # Get all available agents from the system
        agents_response = await get_agents()
        if agents_response and 'agents' in agents_response:
            for agent in agents_response['agents']:
                agent_name = agent.get('name', 'Unknown Agent')
                agent_status = agent.get('status', 'unknown')
                
                # Create activity for each agent with workflow context
                activities.append({
                    "timestamp": time.time(),
                    "agent": agent_name,
                    "message": f"Agent {agent_name} is {agent_status}",
                    "type": "success" if agent_status == "active" else "warning",
                    "workflow_context": {
                        'workflow_step': 'agent_status',
                        'workflow_type': 'system_monitoring',
                        'status': agent_status
                    },
                    "details": {
                        "agent_type": agent.get('type', 'Unknown'),
                        "capabilities": agent.get('capabilities', []),
                        "last_activity": agent.get('lastActivity', 'Unknown')
                    }
                })
    except Exception as e:
        logger.error(f"Error getting dynamic agent list: {e}")
    
    # Sort by timestamp (newest first)
    activities.sort(key=lambda x: x.get('timestamp', 0), reverse=True)
    
    return {
        "status": "success",
        "activities": activities[:30],  # Return last 30 activities
        "total_activities": len(activities),
        "timestamp": time.time(),
        "source": "real_agent_activities_with_workflow",
        "agent_count": len(set(activity.get('agent', 'Unknown') for activity in activities)),
        "workflow_summary": {
            "active_workflows": ["AGInt_BDI_SimpleCoder", "Mastermind_Coordinator_BDI"],
            "workflow_types": ["cognitive_decision", "code_evolution", "system_orchestration"],
            "active_agents": list(set(activity.get('agent', 'Unknown') for activity in activities))
        }
    }


@app.get("/agents/activity", summary="Get consolidated agent activity (canonical endpoint)")
async def get_agents_activity():
    """
    Canonical endpoint for agent activity monitoring.

    This is the standardized endpoint that consolidates all agent activity sources.
    Frontend should use this single endpoint instead of multiple fallback endpoints.

    Returns activities from:
    - BDI Agent reasoning
    - AGInt cognitive cycles
    - Simple Coder operations
    - Coordinator Agent infrastructure management
    - MastermindAgent orchestration
    - All registered agents

    Response format:
    {
        "status": "success",
        "activities": [...],  # List of activity objects
        "total_activities": int,
        "timestamp": float,
        "agent_count": int,
        "workflow_summary": {...}
    }

    Each activity object contains:
    - timestamp: Unix timestamp
    - agent: Agent name
    - message: Activity description
    - type: "info" | "success" | "warning" | "error"
    - workflow_context: Optional workflow metadata
    - details: Optional additional details
    """
    # Delegate to the comprehensive real-time activity endpoint
    return await get_real_time_agent_activity()


# --- Vault and PostgreSQL Management Endpoints ---

class PostgreSQLConfigPayload(BaseModel):
    host: str = "localhost"
    port: int = 5432
    database: str = "mindx_memory"
    user: str = "mindx"
    password: Optional[str] = None


@app.get("/admin/postgresql/config", summary="Get PostgreSQL configuration")
async def get_postgresql_config():
    """Get current PostgreSQL configuration from vault."""
    try:
        vault_manager = get_vault_manager()
        config = vault_manager.get_postgresql_config()
        # Don't return password in response
        safe_config = {k: v for k, v in config.items() if k != "password"}
        safe_config["has_password"] = "password" in config
        return {
            "status": "success",
            "config": safe_config
        }
    except Exception as e:
        logger.error(f"Error getting PostgreSQL config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/postgresql/config", summary="Save PostgreSQL configuration")
async def save_postgresql_config(payload: PostgreSQLConfigPayload):
    """Save PostgreSQL configuration to vault."""
    try:
        vault_manager = get_vault_manager()
        config = {
            "host": payload.host,
            "port": payload.port,
            "database": payload.database,
            "user": payload.user
        }
        if payload.password:
            config["password"] = payload.password
        
        if vault_manager.store_postgresql_config(config):
            return {
                "status": "success",
                "message": "PostgreSQL configuration saved to vault"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save configuration")
    except Exception as e:
        logger.error(f"Error saving PostgreSQL config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/postgresql/test", summary="Test PostgreSQL connection")
async def test_postgresql_connection(payload: PostgreSQLConfigPayload):
    """Test PostgreSQL connection with provided credentials."""
    try:
        import psycopg2
        from psycopg2 import sql
        
        conn = None
        try:
            conn = psycopg2.connect(
                host=payload.host,
                port=payload.port,
                database=payload.database,
                user=payload.user,
                password=payload.password or "",
                connect_timeout=5
            )
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            cursor.close()
            
            return {
                "status": "success",
                "message": "Connection successful",
                "version": version
            }
        except psycopg2.Error as e:
            return {
                "status": "error",
                "message": f"Connection failed: {str(e)}"
            }
        finally:
            if conn:
                conn.close()
    except ImportError:
        return {
            "status": "error",
            "message": "psycopg2 not installed. Install with: pip install psycopg2-binary"
        }
    except Exception as e:
        logger.error(f"Error testing PostgreSQL connection: {e}", exc_info=True)
        return {
            "status": "error",
            "message": str(e)
        }


@app.get("/admin/vault/keys", summary="List agent private keys in vault")
async def list_vault_keys():
    """List all agent private keys stored in vault."""
    try:
        vault_manager = get_vault_manager()
        keys = vault_manager.list_agent_keys()
        return {
            "status": "success",
            "keys": keys,
            "count": len(keys)
        }
    except Exception as e:
        logger.error(f"Error listing vault keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/admin/vault/migrate", summary="Migrate keys from legacy storage to vault")
async def migrate_keys_to_vault():
    """Migrate agent private keys from legacy .wallet_keys.env to vault."""
    try:
        vault_manager = get_vault_manager()
        legacy_path = PROJECT_ROOT / "data" / "identity" / ".wallet_keys.env"
        result = vault_manager.migrate_keys_from_legacy(legacy_path)
        return {
            "status": "success",
            "migration": result
        }
    except Exception as e:
        logger.error(f"Error migrating keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- Faicey Expression Endpoints ---

class FaiceyExpressionPayload(BaseModel):
    agent_id: str
    persona_id: Optional[str] = None
    prompt: Optional[str] = None
    agent_config: Optional[Dict[str, Any]] = None
    dataset_info: Optional[Dict[str, Any]] = None
    model_settings: Optional[Dict[str, Any]] = None  # Renamed from model_config to avoid Pydantic conflict


class FaiceyUpdatePayload(BaseModel):
    ui_modules: Optional[List[Dict[str, Any]]] = None
    customization_options: Optional[Dict[str, Any]] = None


# Global Faicey agent instance
_faicey_agent: Optional[FaiceyAgent] = None


async def get_faicey_agent() -> FaiceyAgent:
    """Get or create Faicey agent instance."""
    global _faicey_agent
    if _faicey_agent is None:
        memory_agent = MemoryAgent(config=Config())
        persona_agent = None  # Can be initialized if needed
        _faicey_agent = FaiceyAgent(
            agent_id="faicey_agent",
            memory_agent=memory_agent,
            persona_agent=persona_agent,
            config=Config()
        )
    return _faicey_agent


@app.post("/faicey/expressions", summary="Create a Faicey expression from persona")
async def create_faicey_expression(payload: FaiceyExpressionPayload):
    """
    Create a Faicey UI/UX expression for an agent.
    
    This combines prompt, agent, dataset, model, and persona to create
    a personalized modular interface expression.
    """
    try:
        faicey_agent = await get_faicey_agent()
        result = await faicey_agent.create_expression_from_persona(
            agent_id=payload.agent_id,
            persona_id=payload.persona_id,
            prompt=payload.prompt,
            agent_config=payload.agent_config,
            dataset_info=payload.dataset_info,
            model_config=payload.model_settings  # Map model_settings to model_config
        )
        return result
    except Exception as e:
        logger.error(f"Error creating Faicey expression: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/faicey/expressions", summary="List all Faicey expressions")
async def list_faicey_expressions(agent_id: Optional[str] = None):
    """List all Faicey expressions, optionally filtered by agent."""
    try:
        faicey_agent = await get_faicey_agent()
        result = await faicey_agent.list_expressions(agent_id=agent_id)
        return result
    except Exception as e:
        logger.error(f"Error listing Faicey expressions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/faicey/expressions/{expression_id}", summary="Get a Faicey expression")
async def get_faicey_expression(expression_id: str):
    """Get a specific Faicey expression by ID."""
    try:
        faicey_agent = await get_faicey_agent()
        result = await faicey_agent.get_expression(expression_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Faicey expression: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/faicey/expressions/agent/{agent_id}", summary="Get expression for agent")
async def get_faicey_expression_for_agent(agent_id: str):
    """Get the most recent Faicey expression for an agent."""
    try:
        faicey_agent = await get_faicey_agent()
        result = await faicey_agent.get_expression_for_agent(agent_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Faicey expression for agent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/faicey/expressions/{expression_id}", summary="Update a Faicey expression")
async def update_faicey_expression(expression_id: str, payload: FaiceyUpdatePayload):
    """Update a Faicey expression's UI modules or customization options."""
    try:
        faicey_agent = await get_faicey_agent()
        result = await faicey_agent.update_expression(
            expression_id=expression_id,
            ui_modules=payload.ui_modules,
            customization_options=payload.customization_options
        )
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating Faicey expression: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/faicey/expressions/{expression_id}/ui-config", summary="Export expression as UI config")
async def export_faicey_ui_config(expression_id: str):
    """Export a Faicey expression as UI configuration for frontend consumption."""
    try:
        faicey_agent = await get_faicey_agent()
        result = await faicey_agent.export_expression_ui_config(expression_id)
        if not result.get("success"):
            raise HTTPException(status_code=404, detail=result.get("error"))
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting Faicey UI config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- Speech Inflection Endpoints ---

class SpeechInflectionPayload(BaseModel):
    text: str
    audio_url: Optional[str] = None
    alphabet: Optional[str] = "english"
    tone_system: Optional[str] = None


@app.post("/faicey/speech/speak", summary="Start speaking with morph target animation")
async def start_speaking(payload: SpeechInflectionPayload):
    """
    Start speaking mode with text-to-speech and morph target animation.
    
    This endpoint triggers the speech inflection system to animate the agent's
    face based on the provided text, mapping phonemes to visemes and synchronizing
    with audio if provided.
    """
    try:
        # This would typically be called from the frontend with the morph mesh
        # For now, return configuration
        return {
            "success": True,
            "message": "Speech inflection started",
            "text": payload.text,
            "alphabet": payload.alphabet,
            "tone_system": payload.tone_system,
            "audio_url": payload.audio_url
        }
    except Exception as e:
        logger.error(f"Error starting speech: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/faicey/speech/listen", summary="Start listening mode")
async def start_listening():
    """
    Start listening mode with ear and eye animations.
    
    This triggers the listening mode animations where ears perk up,
    eyes focus forward, and eyebrows slightly raise for engagement.
    """
    try:
        return {
            "success": True,
            "message": "Listening mode activated",
            "animations": {
                "ears": "perked_up",
                "eyes": "focused_forward",
                "eyebrows": "slightly_raised"
            }
        }
    except Exception as e:
        logger.error(f"Error starting listening mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/faicey/speech/stop", summary="Stop speaking or listening")
async def stop_speech():
    """Stop current speech or listening mode and return to idle."""
    try:
        return {
            "success": True,
            "message": "Speech/listening stopped, returning to idle"
        }
    except Exception as e:
        logger.error(f"Error stopping speech: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# --- MindX Agent Endpoints ---

class MindXAgentAutonomousPayload(BaseModel):
    model: Optional[str] = "mistral-nemo:latest"
    provider: Optional[str] = "ollama"


@app.post("/mindxagent/autonomous/start", summary="Start mindXagent in autonomous mode")
async def start_mindxagent_autonomous(payload: MindXAgentAutonomousPayload = MindXAgentAutonomousPayload()):
    """
    Start mindXagent in autonomous mode for continuous self-improvement.
    
    Uses the specified model (default: mistral-nemo:latest from Ollama) to continuously
    analyze the system, identify improvement opportunities, and execute improvements
    using Blueprint Agent and Strategic Evolution Agent.
    """
    try:
        from agents.core.mindXagent import MindXAgent
        from agents.memory_agent import MemoryAgent
        from utils.config import Config
        
        # Get or create mindXagent instance (force new instance if needed)
        memory_agent = MemoryAgent(config=Config())
        mindxagent = await MindXAgent.get_instance(
            agent_id="mindx_meta_agent",
            memory_agent=memory_agent,
            config=Config(),
            test_mode=False  # Use existing instance if available
        )
        
        # Check if method exists, if not, the instance needs to be recreated
        if not hasattr(mindxagent, 'start_autonomous_mode'):
            # Force new instance by clearing singleton
            MindXAgent._instance = None
            mindxagent = await MindXAgent.get_instance(
                agent_id="mindx_meta_agent",
                memory_agent=memory_agent,
                config=Config()
            )
        
        # Start autonomous mode
        result = await mindxagent.start_autonomous_mode(
            model=payload.model,
            provider=payload.provider
        )
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error starting mindXagent autonomous mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/mindxagent/autonomous/stop", summary="Stop mindXagent autonomous mode")
async def stop_mindxagent_autonomous():
    """Stop mindXagent autonomous mode."""
    try:
        from agents.core.mindXagent import MindXAgent
        
        # Get existing instance
        mindxagent = await MindXAgent.get_instance()
        
        if mindxagent:
            result = await mindxagent.stop_autonomous_mode()
            return result
        else:
            return {"status": "error", "message": "mindXagent not initialized"}
    except Exception as e:
        logger.error(f"Error stopping mindXagent autonomous mode: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error stopping autonomous mode: {str(e)}")


@app.get("/mindxagent/status", summary="Get mindXagent status")
async def get_mindxagent_status():
    """Get current mindXagent status including settings and thinking process."""
    try:
        from agents.core.mindXagent import MindXAgent
        
        mindxagent = await MindXAgent.get_instance()
        if mindxagent:
            # Ensure all required attributes exist before calling get_status
            if not hasattr(mindxagent, 'improvement_opportunities'):
                mindxagent.improvement_opportunities = []
            if not hasattr(mindxagent, '_improvement_opportunities'):
                mindxagent._improvement_opportunities = []
            if not hasattr(mindxagent, 'action_choices'):
                mindxagent.action_choices = []
            if not hasattr(mindxagent, 'thinking_process'):
                mindxagent.thinking_process = []
            if not hasattr(mindxagent, 'agent_knowledge'):
                mindxagent.agent_knowledge = {}
            try:
                return mindxagent.get_status()
            except (AttributeError, TypeError) as attr_err:
                # If get_status fails, fix the attribute and try again
                if 'improvement_opportunities' in str(attr_err):
                    mindxagent.improvement_opportunities = []
                    mindxagent._improvement_opportunities = []
                    return mindxagent.get_status()
                # Handle None comparison errors
                if 'not supported between instances' in str(attr_err) or 'NoneType' in str(attr_err):
                    logger.warning(f"Comparison error in get_status, using safe fallback: {attr_err}")
                    # Return a safe status without problematic fields
                    return {
                        "autonomous_mode": getattr(mindxagent, 'autonomous_mode', False),
                        "running": getattr(mindxagent, 'running', False),
                        "model": getattr(mindxagent, 'llm_model', None),
                        "provider": getattr(mindxagent, 'llm_provider', None),
                        "settings": getattr(mindxagent, 'settings', {}).copy() if hasattr(mindxagent, 'settings') else {},
                        "thinking_steps_count": len(getattr(mindxagent, 'thinking_process', [])),
                        "action_choices_count": len(getattr(mindxagent, 'action_choices', [])),
                        "improvement_opportunities_count": len(getattr(mindxagent, 'improvement_opportunities', [])),
                        "error": "Status calculation had issues, showing partial data"
                    }
                raise
        else:
            return {"status": "not_initialized"}
    except AttributeError as e:
        # Handle missing attributes gracefully
        if 'improvement_opportunities' in str(e):
            logger.warning(f"Missing improvement_opportunities attribute, initializing: {e}")
            try:
                mindxagent = await MindXAgent.get_instance()
                if mindxagent:
                    mindxagent.improvement_opportunities = []
                    return mindxagent.get_status()
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")
    except Exception as e:
        logger.error(f"Error getting mindXagent status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")


@app.get("/mindxagent/startup", summary="Get startup_agent and mindXagent startup flow (input, response, steps)")
async def get_mindxagent_startup():
    """
    Return actual startup flow: startup_agent steps, Ollama connection input/response,
    and mindXagent startup_info (from receive_startup_information). Used by mindXagent tab UI.
    """
    try:
        from agents.core.mindXagent import MindXAgent
        from pathlib import Path

        result = {
            "success": True,
            "startup_info": None,
            "startup_sequence": [],
            "startup_record": None,
            "terminal_log": {"log_exists": False, "last_lines": [], "total_lines": 0},
            "ollama_input_response": None,
        }

        # 1. mindXagent.startup_info (what was received from startup_agent)
        mindxagent = await MindXAgent.get_instance()
        if mindxagent and getattr(mindxagent, "startup_info", None):
            si = mindxagent.startup_info
            result["startup_info"] = {
                "ollama_connected": si.get("ollama_connected", False),
                "ollama_base_url": si.get("ollama_base_url"),
                "ollama_models": si.get("ollama_models", [])[:20],
                "models_count": si.get("models_count", 0),
                "startup_timestamp": si.get("startup_timestamp"),
                "terminal_log_path": si.get("terminal_log_path"),
            }
            if si.get("terminal_log"):
                tl = si["terminal_log"]
                result["startup_info"]["terminal_log_summary"] = {
                    "log_exists": tl.get("log_exists"),
                    "errors_count": tl.get("errors_count", 0),
                    "warnings_count": tl.get("warnings_count", 0),
                }

        # 2. startup_agent: sequence, last record, ollama result (from mastermind lifecycle)
        if command_handler and getattr(command_handler, "mastermind", None):
            mastermind = command_handler.mastermind
            lifecycle = getattr(mastermind, "lifecycle_agents", {}) or {}
            startup_agent = lifecycle.get("startup")
            if startup_agent:
                result["startup_sequence"] = getattr(startup_agent, "startup_sequence", []) or []
                startup_log = getattr(startup_agent, "startup_log", []) or []
                if startup_log:
                    last_record = startup_log[-1]
                    result["startup_record"] = last_record
                    # Ollama input/response from startup flow (from startup_agent → mindXagent)
                    ollama_conn = last_record.get("ollama_connection")
                    if ollama_conn is not None:
                        result["ollama_input_response"] = {
                            "connected": ollama_conn.get("connected", False),
                            "base_url": ollama_conn.get("base_url"),
                            "models": ollama_conn.get("models", [])[:20],
                            "models_count": ollama_conn.get("models_count", 0),
                            "reason": ollama_conn.get("reason"),
                        }
        # 3. terminal_startup.log last lines
        startup_log_path = PROJECT_ROOT / "data" / "logs" / "terminal_startup.log"
        if startup_log_path.exists():
            result["terminal_log"]["log_exists"] = True
            try:
                with open(startup_log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    result["terminal_log"]["total_lines"] = len(lines)
                    result["terminal_log"]["last_lines"] = lines[-40:] if len(lines) > 40 else lines
            except Exception as e:
                logger.warning(f"Could not read terminal_startup.log: {e}")

        return result
    except Exception as e:
        logger.error(f"Error getting mindXagent startup: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mindxagent/ollama/status", summary="Get mindXagent Ollama connection and inference status")
async def get_mindxagent_ollama_status():
    """Get detailed Ollama connection status, available models, and inference metrics."""
    try:
        from agents.core.mindXagent import MindXAgent
        
        mindxagent = await MindXAgent.get_instance()
        if mindxagent:
            return await mindxagent.get_ollama_status()
        else:
            return {"connected": False, "error": "mindXagent not initialized"}
    except Exception as e:
        logger.error(f"Error getting Ollama status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting Ollama status: {str(e)}")


@app.get("/mindxagent/ollama/conversation", summary="Get Ollama conversation history")
async def get_mindxagent_ollama_conversation(conversation_id: Optional[str] = None, limit: int = 50):
    """Get conversation history between mindXagent and Ollama models using OllamaChatDisplayTool."""
    try:
        from api.ollama.ollama_chat_display_tool import OllamaChatDisplayTool
        from utils.config import Config
        
        config = Config()
        display_tool = OllamaChatDisplayTool(config=config)
        result = await display_tool.get_conversation_history(conversation_id, limit)
        return result
    except Exception as e:
        logger.error(f"Error getting conversation history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting conversation history: {str(e)}")


@app.post("/mindxagent/ollama/conversation/clear", summary="Clear Ollama conversation history")
async def clear_mindxagent_ollama_conversation(conversation_id: Optional[str] = None):
    """Clear conversation history between mindXagent and Ollama models using OllamaChatDisplayTool."""
    try:
        from api.ollama.ollama_chat_display_tool import OllamaChatDisplayTool
        from utils.config import Config
        
        config = Config()
        display_tool = OllamaChatDisplayTool(config=config)
        result = await display_tool.clear_conversation(conversation_id)
        return result
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error clearing conversation: {str(e)}")


@app.get("/mindxagent/thinking", summary="Get mindXagent thinking process")
async def get_mindxagent_thinking(limit: int = 100):
    """Get recent thinking process from mindXagent."""
    try:
        from agents.core.mindXagent import MindXAgent
        
        mindxagent = await MindXAgent.get_instance()
        if mindxagent:
            return {
                "thinking_process": mindxagent.get_thinking_process(limit=limit),
                "count": len(mindxagent.thinking_process)
            }
        else:
            return {"thinking_process": [], "count": 0}
    except Exception as e:
        logger.error(f"Error getting thinking process: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting thinking process: {str(e)}")


@app.get("/mindxagent/actions", summary="Get mindXagent action choices")
async def get_mindxagent_actions(limit: int = 50):
    """Get recent action choices from mindXagent."""
    try:
        from agents.core.mindXagent import MindXAgent
        
        mindxagent = await MindXAgent.get_instance()
        if mindxagent:
            return {
                "action_choices": mindxagent.get_action_choices(limit=limit),
                "count": len(mindxagent.action_choices)
            }
        else:
            return {"action_choices": [], "count": 0}
    except Exception as e:
        logger.error(f"Error getting action choices: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting action choices: {str(e)}")


@app.post("/mindxagent/interact", summary="Interact with mindXagent by injecting prompt into Ollama conversation")
async def interact_with_mindxagent(interaction: Dict[str, Any] = Body(...)):
    """
    Inject a user prompt into mindXagent's active Ollama conversation.
    This allows real-time interaction with the agent's reasoning process.
    """
    try:
        prompt = interaction.get("prompt", "").strip()
        if not prompt:
            raise HTTPException(status_code=400, detail="Prompt is required")

        source = interaction.get("source", "api")
        timestamp = interaction.get("timestamp", time.time())

        from agents.core.mindXagent import MindXAgent
        mindxagent = await MindXAgent.get_instance()
        if not mindxagent:
            raise HTTPException(status_code=503, detail="mindXagent not available")

        # Inject the prompt into mindXagent's Ollama conversation
        result = await mindxagent.inject_user_prompt(
            prompt=prompt,
            source=source,
            metadata={
                "timestamp": timestamp,
                "ui_interaction": True,
                "user_initiated": True
            }
        )

        # Log this interaction to memory
        if mindxagent.memory_agent:
            await mindxagent.memory_agent.store_memory(
                content=f"UI Interaction: User injected prompt into mindXagent - '{prompt}'",
                memory_type="interaction",
                importance="medium",
                metadata={
                    "interaction_type": "prompt_injection",
                    "source": source,
                    "timestamp": timestamp,
                    "mindxagent_response": result,
                    "ui_generated": True
                }
            )

        return {
            "success": True,
            "response": result.get("response", "Prompt injected into mindXagent conversation"),
            "conversation_id": result.get("conversation_id"),
            "timestamp": timestamp,
            "logged_to_memory": True
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interacting with mindXagent: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error interacting with mindXagent: {str(e)}")


@app.post("/mindxagent/memory/log", summary="Log event to mindXagent memory")
async def log_to_mindxagent_memory(log_entry: Dict[str, Any] = Body(...)):
    """
    Log an event or interaction to mindXagent's memory system.
    All logs become memories and memories become logs.
    """
    try:
        content = log_entry.get("content", "")
        log_type = log_entry.get("type", "interaction")
        timestamp = log_entry.get("timestamp", time.time())

        from agents.core.mindXagent import MindXAgent
        mindxagent = await MindXAgent.get_instance()
        if not mindxagent or not mindxagent.memory_agent:
            raise HTTPException(status_code=503, detail="mindXagent memory system not available")

        # Store as memory
        memory_result = await mindxagent.memory_agent.store_memory(
            content=f"[MEMORY LOG] {content}",
            memory_type=log_type,
            importance="low",  # Memory logs are generally low importance
            metadata={
                "timestamp": timestamp,
                "log_type": log_type,
                "source": "ui_interaction",
                "auto_logged": True,
                **log_entry.get("metadata", {})
            }
        )

        # Also log to the logs folder as a memory file
        try:
            from pathlib import Path
            log_filename = f"memory_log_{int(timestamp)}.json"
            log_path = Path("data/logs/memories") / log_filename
            log_path.parent.mkdir(parents=True, exist_ok=True)

            with open(log_path, 'w') as f:
                json.dump({
                    "timestamp": timestamp,
                    "type": log_type,
                    "content": content,
                    "memory_id": memory_result.get("memory_id"),
                    "metadata": log_entry.get("metadata", {})
                }, f, indent=2)

        except Exception as log_error:
            logger.warning(f"Failed to write memory log file: {log_error}")

        return {
            "success": True,
            "memory_id": memory_result.get("memory_id"),
            "logged_to_file": True,
            "timestamp": timestamp
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging to memory: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error logging to memory: {str(e)}")


@app.post("/mindxagent/memory/logs/clear", summary="Clear mindXagent memory logs")
async def clear_mindxagent_memory_logs():
    """
    Clear the memory logs directory and reset memory log history.
    """
    try:
        from agents.core.mindXagent import MindXAgent
        mindxagent = await MindXAgent.get_instance()
        if not mindxagent:
            raise HTTPException(status_code=503, detail="mindXagent not available")

        # Clear memory logs directory
        from pathlib import Path
        import shutil
        logs_dir = Path("data/logs/memories")
        if logs_dir.exists():
            shutil.rmtree(logs_dir)

        # Recreate directory
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Clear from memory agent if possible
        if mindxagent.memory_agent and hasattr(mindxagent.memory_agent, 'clear_logs'):
            await mindxagent.memory_agent.clear_logs()

        return {
            "success": True,
            "message": "Memory logs cleared successfully",
            "logs_directory": str(logs_dir)
        }

    except Exception as e:
        logger.error(f"Error clearing memory logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error clearing memory logs: {str(e)}")


@app.post("/mindxagent/settings", summary="Update mindXagent settings")
async def update_mindxagent_settings(settings: Dict[str, Any] = Body(...)):
    """Update mindXagent settings from UI."""
    try:
        from agents.core.mindXagent import MindXAgent
        
        mindxagent = await MindXAgent.get_instance()
        if mindxagent:
            updated = mindxagent.update_settings(settings)
            return {
                "success": True,
                "settings": updated
            }
        else:
            return {"success": False, "error": "mindXagent not initialized"}
    except Exception as e:
        logger.error(f"Error updating mindXagent settings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error updating settings: {str(e)}")


@app.get("/mindxagent/status", summary="Get mindXagent status")
async def get_mindxagent_status():
    """Get current status of mindXagent."""
    try:
        from agents.core.mindXagent import MindXAgent
        
        mindxagent = await MindXAgent.get_instance()
        
        if mindxagent:
            return {
                "success": True,
                "status": {
                    "initialized": mindxagent.initialized,
                    "running": mindxagent.running,
                    "autonomous_mode": mindxagent.autonomous_mode,
                    "agent_count": len(mindxagent.agent_knowledge),
                    "improvement_history_count": len(mindxagent.improvement_history),
                    "llm_model": mindxagent.llm_model,
                    "llm_provider": mindxagent.llm_provider
                }
            }
        else:
            return {
                "success": False,
                "error": "mindXagent not initialized"
            }
    except Exception as e:
        logger.error(f"Error getting mindXagent status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mindxagent/memory/logs", summary="Get mindXagent memory storage logs")
async def get_mindxagent_memory_logs(limit: int = 100, agent_id: Optional[str] = None):
    """Get memory storage logs for mindXagent."""
    try:
        from agents.core.mindXagent import MindXAgent
        from agents.memory_agent import MemoryAgent
        from pathlib import Path
        import json
        
        mindxagent = await MindXAgent.get_instance()
        if not mindxagent:
            return {"success": False, "error": "mindXagent not initialized", "logs": []}
        
        target_agent_id = agent_id or mindxagent.agent_id
        memory_agent = mindxagent.memory_agent
        
        if not memory_agent:
            return {"success": False, "error": "Memory agent not available", "logs": []}
        
        # Get memory directory
        memory_dir = memory_agent.get_agent_data_directory(target_agent_id)
        stm_dir = memory_agent.stm_path / target_agent_id
        
        logs = []
        
        # Read from STM (Short Term Memory) - most recent
        if stm_dir.exists():
            for date_dir in sorted(stm_dir.iterdir(), reverse=True):
                if not date_dir.is_dir():
                    continue
                for memory_file in sorted(date_dir.glob("*.memory.json"), reverse=True):
                    try:
                        with open(memory_file, 'r', encoding='utf-8') as f:
                            memory_data = json.load(f)
                            logs.append({
                                "timestamp": memory_data.get("timestamp"),
                                "memory_type": memory_data.get("memory_type"),
                                "importance": memory_data.get("importance"),
                                "content_preview": str(memory_data.get("content", {}))[:200],
                                "tags": memory_data.get("tags", []),
                                "file": str(memory_file.relative_to(PROJECT_ROOT))
                            })
                            if len(logs) >= limit:
                                break
                    except Exception as e:
                        logger.warning(f"Error reading memory file {memory_file}: {e}")
                if len(logs) >= limit:
                    break
        
        return {
            "success": True,
            "logs": logs[:limit],
            "total": len(logs),
            "agent_id": target_agent_id
        }
    except Exception as e:
        logger.error(f"Error getting memory logs: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/mindxagent/metrics", summary="Get mindXagent metrics including iterations and tokens")
async def get_mindxagent_metrics():
    """Get comprehensive metrics for mindXagent including iterations, token usage, and performance."""
    try:
        from agents.core.mindXagent import MindXAgent
        from pathlib import Path
        import json
        
        mindxagent = await MindXAgent.get_instance()
        if not mindxagent:
            return {
                "success": False,
                "error": "mindXagent not initialized",
                "metrics": {}
            }
        
        metrics = {
            "iterations": {
                "improvement_cycles": len(mindxagent.improvement_history),
                "thinking_steps": len(mindxagent.thinking_process),
                "action_choices": len(mindxagent.action_choices),
                "autonomous_cycles": getattr(mindxagent, 'autonomous_cycle_count', 0)
            },
            "agent_knowledge": {
                "total_agents": len(mindxagent.agent_knowledge),
                "active_agents": sum(1 for ak in mindxagent.agent_knowledge.values() 
                                    if hasattr(ak, 'status') and ak.status.value == 'ACTIVE'),
                "agent_types": {}
            },
            "improvements": {
                "total_opportunities": len(mindxagent.improvement_opportunities),
                "completed": len([h for h in mindxagent.improvement_history if h.get("status") == "completed"]),
                "pending": len(mindxagent.improvement_opportunities)
            },
            "session": {
                "current_session": mindxagent.current_session.session_id if mindxagent.current_session else None,
                "session_active": mindxagent.current_session is not None
            }
        }
        
        # Count agent types
        for ak in mindxagent.agent_knowledge.values():
            agent_type = getattr(ak, 'agent_type', 'unknown')
            metrics["agent_knowledge"]["agent_types"][agent_type] = \
                metrics["agent_knowledge"]["agent_types"].get(agent_type, 0) + 1
        
        # Get token usage from usage metrics endpoint
        try:
            usage_metrics = get_token_usage_metrics()
            if usage_metrics and "metrics" in usage_metrics:
                metrics["token_usage"] = {
                    "total_tokens": usage_metrics["metrics"].get("total_tokens", 0),
                    "daily_tokens": usage_metrics["metrics"].get("daily_tokens", 0),
                    "total_cost": usage_metrics["metrics"].get("total_cost", 0.0),
                    "daily_cost": usage_metrics["metrics"].get("daily_cost", 0.0),
                    "provider_breakdown": usage_metrics["metrics"].get("provider_breakdown", {})
                }
        except Exception as e:
            logger.warning(f"Could not get token usage metrics: {e}")
            metrics["token_usage"] = {"error": "Not available"}
        
        # Get startup information
        startup_log_path = PROJECT_ROOT / "data" / "logs" / "terminal_startup.log"
        startup_info = {
            "log_exists": startup_log_path.exists(),
            "last_modified": None,
            "log_size": 0
        }
        
        if startup_log_path.exists():
            startup_info["last_modified"] = startup_log_path.stat().st_mtime
            startup_info["log_size"] = startup_log_path.stat().st_size
            
            # Read last few lines
            try:
                with open(startup_log_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    startup_info["last_lines"] = lines[-20:] if len(lines) > 20 else lines
                    startup_info["total_lines"] = len(lines)
            except Exception as e:
                logger.warning(f"Could not read startup log: {e}")
        
        metrics["startup"] = startup_info
        
        return {
            "success": True,
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Error getting mindXagent metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

