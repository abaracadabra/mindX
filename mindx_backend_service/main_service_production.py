# mindx/mindx_backend_service/main_service_production.py
"""
Production-hardened mindX API Server
Enhanced with security middleware, proper CORS, and comprehensive authentication
"""

import asyncio
import os
import random
import re
import time
import json
import uuid
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, validator
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
from utils.logging_config import setup_logging, get_logger, LOG_DIR, LOG_FILENAME
from mindx_backend_service.vault_manager import get_vault_manager
from agents.monitoring.rate_limit_dashboard import RateLimitDashboard

# Import security middleware
from mindx_backend_service.security_middleware import (
    SecurityMiddleware, require_valid_session, require_admin_access, verify_api_key
)

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Configuration
config = Config()
PRODUCTION_MODE = config.get("security.production_mode", True)
DEVELOPMENT_MODE = config.get("security.development_mode", False)

# Memory availability check
try:
    MemoryAgent()
    MEMORY_AVAILABLE = True
except Exception as e:
    MEMORY_AVAILABLE = False
    logger.warning(f"MemoryAgent not available - memory logging disabled: {e}")

# --- Enhanced Pydantic Models with Validation ---

class DirectivePayload(BaseModel):
    directive: str
    max_cycles: Optional[int] = 8
    autonomous_mode: Optional[bool] = False

    @validator('directive')
    def directive_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Directive cannot be empty')
        if len(v) > 10000:
            raise ValueError('Directive too long (max 10000 characters)')
        return v.strip()

    @validator('max_cycles')
    def max_cycles_must_be_reasonable(cls, v):
        if v is not None and (v < 1 or v > 100):
            raise ValueError('Max cycles must be between 1 and 100')
        return v

class AnalyzeCodebasePayload(BaseModel):
    path: str
    focus: str

    @validator('path')
    def path_validation(cls, v):
        if not v or not v.strip():
            raise ValueError('Path cannot be empty')
        # Basic path traversal protection
        if '..' in v or v.startswith('/'):
            raise ValueError('Invalid path format')
        return v.strip()

class IdCreatePayload(BaseModel):
    entity_id: str

    @validator('entity_id')
    def entity_id_validation(cls, v):
        if not v or not v.strip():
            raise ValueError('Entity ID cannot be empty')
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Entity ID can only contain alphanumeric characters, underscores, and hyphens')
        if len(v) > 100:
            raise ValueError('Entity ID too long (max 100 characters)')
        return v.strip()

class UserRegisterPayload(BaseModel):
    wallet_address: str
    metadata: Optional[Dict[str, Any]] = None

    @validator('wallet_address')
    def wallet_address_validation(cls, v):
        if not v or not v.strip():
            raise ValueError('Wallet address cannot be empty')
        # Basic Ethereum address validation
        if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
            raise ValueError('Invalid Ethereum wallet address format')
        return v.lower()  # Normalize to lowercase

class UserRegisterWithSignaturePayload(BaseModel):
    wallet_address: str
    signature: str
    message: str
    metadata: Optional[Dict[str, Any]] = None

    @validator('wallet_address')
    def wallet_address_validation(cls, v):
        if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
            raise ValueError('Invalid Ethereum wallet address format')
        return v.lower()

    @validator('signature')
    def signature_validation(cls, v):
        if not v or len(v) < 100:
            raise ValueError('Invalid signature format')
        return v

class AgentCreatePayload(BaseModel):
    agent_type: str
    agent_id: str
    config: Dict[str, Any]
    owner_wallet: Optional[str] = None

    @validator('agent_type')
    def agent_type_validation(cls, v):
        allowed_types = ['simple_coder', 'memory_agent', 'guardian_agent', 'persona_agent']
        if v not in allowed_types:
            raise ValueError(f'Agent type must be one of: {", ".join(allowed_types)}')
        return v

    @validator('agent_id')
    def agent_id_validation(cls, v):
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Agent ID can only contain alphanumeric characters, underscores, and hyphens')
        return v

# Additional enhanced models for other payloads...
class CoordQueryPayload(BaseModel):
    query: str

    @validator('query')
    def query_validation(cls, v):
        if not v or not v.strip():
            raise ValueError('Query cannot be empty')
        if len(v) > 5000:
            raise ValueError('Query too long (max 5000 characters)')
        return v.strip()

# --- FastAPI Application with Enhanced Security ---

app = FastAPI(
    title="mindX API - Production",
    description="Production-hardened API for interacting with the mindX Augmentic Intelligence system.",
    version="2.0.0-production",
    docs_url="/docs" if DEVELOPMENT_MODE else None,  # Hide docs in production
    redoc_url="/redoc" if DEVELOPMENT_MODE else None,
    openapi_url="/openapi.json" if DEVELOPMENT_MODE else None
)

# Production CORS configuration
if PRODUCTION_MODE:
    allowed_origins = [
        "https://agenticplace.pythai.net",
        "https://www.agenticplace.pythai.net",
        "https://mindx.pythai.net"
    ]

    # Add development origins if in development mode
    if DEVELOPMENT_MODE:
        allowed_origins.extend([
            "http://localhost:3000",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000"
        ])
else:
    # Development mode - more permissive but still not wildcard
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
        "https://agenticplace.pythai.net"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Session-Token",
        "X-API-Key",
        "Accept",
        "Origin",
        "User-Agent"
    ],
    expose_headers=["X-Request-ID", "X-Rate-Limit-Remaining"]
)

# Add trusted host middleware
if PRODUCTION_MODE:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "agenticplace.pythai.net",
            "www.agenticplace.pythai.net",
            "mindx.pythai.net",
            "localhost",  # For health checks
            "127.0.0.1"   # For health checks
        ]
    )

# Add security middleware
app.add_middleware(SecurityMiddleware, config=config)

# Add inbound metrics middleware
try:
    from mindx_backend_service.inbound_metrics import InboundMetricsMiddleware, get_inbound_metrics, set_inbound_rate_limit
    app.add_middleware(InboundMetricsMiddleware)
except Exception as e:
    logger.warning(f"InboundMetricsMiddleware not added: {e}")

# Include routers
from mindx_backend_service.mindterm import mindterm_router
from mindx_backend_service.mindterm.routes import set_coordinator_and_monitors
app.include_router(mindterm_router)

# Static files
_mindterm_static = PROJECT_ROOT / "mindx_backend_service" / "mindterm" / "static"
if _mindterm_static.exists():
    app.mount("/mindterm/static", StaticFiles(directory=str(_mindterm_static)), name="mindterm_static")

# Include other routers
from api.llm_routes import router as llm_router
app.include_router(llm_router)

from mindx_backend_service.rage.routes import router as rage_router
app.include_router(rage_router)

from api.ollama.ollama_admin_routes import router as ollama_admin_router
app.include_router(ollama_admin_router)

from mindx_backend_service.agenticplace_routes import router as agenticplace_router
app.include_router(agenticplace_router)

from mindx_backend_service.bankon import bankon_router
app.include_router(bankon_router)

# --- Global Dependencies and State ---
command_handler = None
mastermind_agent = None
rate_limit_dashboard = None

# --- Health Check Endpoints ---

@app.get("/health", summary="Health check endpoint", include_in_schema=False)
async def health_check():
    """Simple health check for load balancers"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health/detailed", summary="Detailed health check")
async def detailed_health_check():
    """Detailed health check including dependencies"""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0-production",
        "services": {}
    }

    # Check command handler
    health_status["services"]["command_handler"] = "available" if command_handler else "unavailable"

    # Check memory agent
    health_status["services"]["memory_agent"] = "available" if MEMORY_AVAILABLE else "unavailable"

    # Check vault manager
    try:
        vault = get_vault_manager()
        health_status["services"]["vault_manager"] = "available"
    except Exception:
        health_status["services"]["vault_manager"] = "unavailable"

    # Overall status
    unhealthy_services = [k for k, v in health_status["services"].items() if v == "unavailable"]
    if unhealthy_services:
        health_status["status"] = "degraded"
        health_status["issues"] = unhealthy_services

    return health_status

# --- Protected Endpoints ---

@app.post("/commands/evolve", summary="Evolve mindX codebase", dependencies=[Depends(require_valid_session)])
async def evolve(payload: DirectivePayload, wallet_address: str = Depends(require_valid_session)):
    """Evolve mindX codebase - requires authentication"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")

    logger.info(f"Evolution request from {wallet_address}: {payload.directive[:100]}...")
    return await command_handler.handle_evolve(payload.directive)

@app.post("/commands/deploy", summary="Deploy a new agent", dependencies=[Depends(require_valid_session)])
async def deploy(payload: DirectivePayload, wallet_address: str = Depends(require_valid_session)):
    """Deploy a new agent - requires authentication"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")

    logger.info(f"Deploy request from {wallet_address}: {payload.directive[:100]}...")
    return await command_handler.handle_deploy(payload.directive)

@app.post("/commands/introspect", summary="Generate a new persona", dependencies=[Depends(require_valid_session)])
async def introspect(payload: DirectivePayload, wallet_address: str = Depends(require_valid_session)):
    """Generate a new persona - requires authentication"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")

    logger.info(f"Introspection request from {wallet_address}: {payload.directive[:100]}...")
    return await command_handler.handle_introspect(payload.directive)

@app.post("/agents", summary="Create a new agent", dependencies=[Depends(require_valid_session)])
async def agent_create(payload: AgentCreatePayload, wallet_address: str = Depends(require_valid_session)):
    """Create a new agent - requires authentication"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")

    # Set owner wallet if not specified
    if not payload.owner_wallet:
        payload.owner_wallet = wallet_address

    logger.info(f"Agent creation request from {wallet_address}: {payload.agent_type} - {payload.agent_id}")
    return await command_handler.handle_agent_create(payload.agent_type, payload.agent_id, payload.config)

@app.delete("/agents/{agent_id}", summary="Delete an agent", dependencies=[Depends(require_valid_session)])
async def agent_delete(agent_id: str, wallet_address: str = Depends(require_valid_session)):
    """Delete an agent - requires authentication and ownership verification"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")

    # TODO: Add ownership verification
    logger.info(f"Agent deletion request from {wallet_address}: {agent_id}")
    return await command_handler.handle_agent_delete(agent_id)

@app.post("/coordinator/query", summary="Query the Coordinator", dependencies=[Depends(require_valid_session)])
async def coord_query(payload: CoordQueryPayload, wallet_address: str = Depends(require_valid_session)):
    """Query the Coordinator - requires authentication"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")

    logger.info(f"Coordinator query from {wallet_address}: {payload.query[:100]}...")
    return await command_handler.handle_coord_query(payload.query)

# --- Admin-Only Endpoints ---

@app.post("/identities", summary="Create a new identity", dependencies=[Depends(require_admin_access)])
async def id_create(payload: IdCreatePayload, admin_wallet: str = Depends(require_admin_access)):
    """Create a new identity - requires admin access"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")

    logger.info(f"Identity creation by admin {admin_wallet}: {payload.entity_id}")
    return await command_handler.handle_id_create(payload.entity_id)

@app.delete("/identities", summary="Deprecate an identity", dependencies=[Depends(require_admin_access)])
async def id_deprecate(payload: IdDeprecatePayload, admin_wallet: str = Depends(require_admin_access)):
    """Deprecate an identity - requires admin access"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")

    logger.info(f"Identity deprecation by admin {admin_wallet}: {payload.public_address}")
    return await command_handler.handle_id_deprecate(payload.public_address, payload.entity_id_hint)

# --- Public Endpoints (Read-Only) ---

@app.get("/status/mastermind", summary="Get Mastermind status")
async def mastermind_status():
    """Get Mastermind status - public endpoint"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_mastermind_status()

@app.get("/registry/agents", summary="Show agent registry")
async def show_agent_registry():
    """Show agent registry - public endpoint"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_show_agent_registry()

@app.get("/registry/tools", summary="Show tool registry")
async def show_tool_registry():
    """Show tool registry - public endpoint"""
    if not command_handler:
        raise HTTPException(status_code=503, detail="mindX is not available.")
    return await command_handler.handle_show_tool_registry()

@app.get("/", summary="Root endpoint")
async def root():
    """Root endpoint with system information"""
    return {
        "message": "Welcome to mindX API - Production",
        "version": "2.0.0-production",
        "status": "operational",
        "documentation": "/docs" if DEVELOPMENT_MODE else "Contact administrator",
        "security": "enhanced"
    }

# --- Authentication Endpoints ---

@app.post("/users/register-with-signature", summary="Register user with signature verification")
async def register_user_with_signature(payload: UserRegisterWithSignaturePayload):
    """Register a new user with wallet signature verification"""
    try:
        # Verify signature
        from mindx_backend_service.security_middleware import security_manager

        signature_valid = await security_manager.verify_signature(
            payload.wallet_address,
            payload.message,
            payload.signature
        )

        if not signature_valid:
            raise HTTPException(status_code=401, detail="Invalid signature")

        # Handle registration
        if not command_handler:
            raise HTTPException(status_code=503, detail="mindX is not available.")

        logger.info(f"User registration with signature: {payload.wallet_address}")
        return await handle_user_register_with_signature(
            payload.wallet_address,
            payload.signature,
            payload.message,
            payload.metadata or {}
        )

    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.get("/users/session/validate", summary="Validate session token")
async def validate_session(request: Request, session_token: Optional[str] = None):
    """Validate a session token issued after wallet sign-in"""
    token = session_token or request.headers.get("X-Session-Token")
    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")

    vault = get_vault_manager()
    session = vault.get_user_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return {"wallet_address": session["wallet_address"], "expires_at": session.get("expires_at")}

@app.post("/users/logout", summary="Invalidate session")
async def logout_session(request: Request):
    """Invalidate the session token"""
    token = request.headers.get("X-Session-Token")
    if not token:
        return {"logged_out": False, "message": "No session token provided"}

    vault = get_vault_manager()
    invalidated = vault.invalidate_user_session(token)
    return {"logged_out": invalidated}

# --- Vault Endpoints (Protected) ---

@app.get("/vault/user/keys", summary="List user vault keys", dependencies=[Depends(require_valid_session)])
async def vault_user_list_keys(wallet_address: str = Depends(require_valid_session)):
    """List key names in the authenticated user's vault folder"""
    try:
        vault = get_vault_manager()
        keys = vault.list_user_keys(wallet_address)
        return {"keys": keys, "wallet_address": wallet_address}
    except Exception as e:
        logger.error(f"Vault list keys error for {wallet_address}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/vault/user/keys/{key}", summary="Get user vault key value", dependencies=[Depends(require_valid_session)])
async def vault_user_get_key(key: str, wallet_address: str = Depends(require_valid_session)):
    """Get value for key in the authenticated user's vault folder"""
    try:
        vault = get_vault_manager()
        value = vault.get_user_value(wallet_address, key)
        if value is None:
            raise HTTPException(status_code=404, detail="Key not found")
        return {"key": key, "value": value, "wallet_address": wallet_address}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vault get key error for {wallet_address}/{key}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- Error Handlers ---

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler"""
    return {
        "error": exc.detail,
        "status_code": exc.status_code,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler"""
    logger.error(f"Unhandled exception in {request.method} {request.url.path}: {exc}", exc_info=True)
    return {
        "error": "Internal server error",
        "status_code": 500,
        "path": request.url.path,
        "timestamp": datetime.utcnow().isoformat()
    }

# --- Startup and Shutdown Events ---

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global command_handler, mastermind_agent, rate_limit_dashboard

    logger.info("Starting mindX production server...")

    try:
        # Initialize command handler
        command_handler = CommandHandler()
        logger.info("Command handler initialized")

        # Initialize rate limit dashboard
        rate_limit_dashboard = RateLimitDashboard()
        logger.info("Rate limit dashboard initialized")

        logger.info("mindX production server started successfully")

    except Exception as e:
        logger.error(f"Failed to initialize mindX server: {e}", exc_info=True)
        # Don't raise - allow partial functionality

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down mindX production server...")

    try:
        if command_handler:
            # Cleanup command handler resources
            logger.info("Command handler shutdown complete")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)

    logger.info("mindX production server shutdown complete")

if __name__ == "__main__":
    import uvicorn

    # Production server configuration
    uvicorn.run(
        "main_service_production:app",
        host="0.0.0.0",
        port=8000,
        workers=1,  # Single worker for now due to shared state
        access_log=False,  # Use custom logging
        server_header=False,  # Security: hide server header
        date_header=False,  # Security: hide date header
    )