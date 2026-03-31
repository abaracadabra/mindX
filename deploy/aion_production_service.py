#!/usr/bin/env python3
"""
AION Production Service for aion.pythai.net
© Professor Codephreak - rage.pythai.net
Organizations: github.com/agenticplace, github.com/cryptoagi, github.com/Professor-Codephreak

This service provides the AION autonomous agent interface for production deployment.
Runs on port 8001 and interfaces exclusively with AION agent operations.
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add mindX to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import subprocess

# mindX imports
from agents.aion_agent import AIONAgent
from agents.systemadmin_agent import SystemAdminAgent
from mindx_backend_service.security_middleware import SecurityMiddleware
from mindx_backend_service.encrypted_vault_manager import EncryptedVaultManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/mindx/aion_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('aion_service')

class AIONProductionService:
    """
    Production service for AION autonomous agent operations.

    Features:
    - Exclusive AION agent control
    - Chroot environment management
    - System administration integration
    - Production security and monitoring
    - Professor Codephreak attribution
    """

    def __init__(self):
        self.app = FastAPI(
            title="AION Autonomous Agent Service",
            description="© Professor Codephreak - Autonomous Interoperability and Operations Network",
            version="1.0.0-production",
            docs_url="/docs" if os.getenv("AION_DEBUG") == "true" else None,
            redoc_url="/redoc" if os.getenv("AION_DEBUG") == "true" else None
        )

        self.aion_agent = None
        self.systemadmin_agent = None
        self.vault_manager = None
        self.setup_middleware()
        self.setup_routes()

    def setup_middleware(self):
        """Configure production middleware for AION service."""

        # Trusted hosts (only allow aion.pythai.net)
        self.app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["aion.pythai.net", "localhost", "127.0.0.1"]
        )

        # CORS with restrictive settings
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["https://aion.pythai.net"],
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["X-AION-Request", "Content-Type"],
            max_age=3600
        )

        # Security middleware
        security = SecurityMiddleware()
        self.app.add_middleware(type(security), handler=security)

        # Request logging
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next):
            start_time = datetime.now()

            # Log AION request
            logger.info(f"AION Request: {request.method} {request.url.path} from {request.client.host}")

            response = await call_next(request)

            # Log AION response
            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"AION Response: {response.status_code} in {duration:.3f}s")

            return response

    async def initialize_agents(self):
        """Initialize AION and SystemAdmin agents."""
        try:
            # Initialize encrypted vault
            vault_password = os.getenv("VAULT_PASSWORD")
            if not vault_password:
                raise ValueError("VAULT_PASSWORD not set for AION service")

            vault_path = "/home/aion/vault"
            os.makedirs(vault_path, exist_ok=True)

            self.vault_manager = EncryptedVaultManager(vault_path, vault_password)
            self.vault_manager.initialize_vault()

            # Initialize AION agent with production configuration
            self.aion_agent = AIONAgent(
                agent_id="aion_prime",
                sovereignty_level=5,  # Maximum autonomy
                production_mode=True,
                vault_manager=self.vault_manager
            )

            # Initialize SystemAdmin agent for AION
            self.systemadmin_agent = SystemAdminAgent(
                authorized_agents=["aion_prime"],
                production_mode=True,
                vault_manager=self.vault_manager
            )

            await self.aion_agent.initialize()
            await self.systemadmin_agent.initialize()

            logger.info("AION agents initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AION agents: {e}")
            raise

    def setup_routes(self):
        """Setup AION service routes."""

        @self.app.get("/")
        async def root():
            """AION service root endpoint."""
            return {
                "service": "AION Autonomous Agent",
                "version": "1.0.0-production",
                "author": "Professor Codephreak",
                "organizations": [
                    "github.com/agenticplace",
                    "github.com/cryptoagi",
                    "github.com/Professor-Codephreak"
                ],
                "resources": "rage.pythai.net",
                "status": "operational",
                "architecture": "Augmented Intelligence"
            }

        @self.app.get("/status")
        async def status():
            """AION system status check."""
            if not self.aion_agent:
                return JSONResponse(
                    status_code=503,
                    content={"status": "initializing", "ready": False}
                )

            try:
                aion_status = await self.aion_agent.get_status()
                system_status = await self.systemadmin_agent.get_system_status()

                return {
                    "status": "operational",
                    "ready": True,
                    "timestamp": datetime.now().isoformat(),
                    "aion_agent": aion_status,
                    "system_status": system_status,
                    "chroot_environments": self.get_chroot_status()
                }

            except Exception as e:
                logger.error(f"Status check failed: {e}")
                return JSONResponse(
                    status_code=500,
                    content={"status": "error", "message": str(e)}
                )

        @self.app.post("/execute")
        async def execute_aion_command(request: Request):
            """Execute AION autonomous command."""
            if not self.aion_agent:
                raise HTTPException(status_code=503, detail="AION agent not ready")

            try:
                body = await request.json()
                command = body.get("command")
                parameters = body.get("parameters", {})

                # Verify AION authorization
                if not self.verify_aion_authority(request):
                    raise HTTPException(status_code=403, detail="AION authorization required")

                # Execute AION command
                result = await self.aion_agent.execute_autonomous_action(command, parameters)

                return {
                    "status": "executed",
                    "command": command,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                    "agent": "aion_prime"
                }

            except Exception as e:
                logger.error(f"AION command execution failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/chroot/create")
        async def create_chroot(request: Request):
            """Create new chroot environment via AION."""
            if not self.aion_agent:
                raise HTTPException(status_code=503, detail="AION agent not ready")

            try:
                body = await request.json()
                target_path = body.get("target_path")
                secure_mode = body.get("secure_mode", True)

                if not target_path:
                    raise HTTPException(status_code=400, detail="target_path required")

                # Verify AION authorization
                if not self.verify_aion_authority(request):
                    raise HTTPException(status_code=403, detail="AION authorization required")

                # Execute chroot creation via AION.sh
                result = await self.execute_aion_script("chroot-create", {
                    "target": target_path,
                    "secure": secure_mode
                })

                return {
                    "status": "created",
                    "chroot_path": target_path,
                    "secure_mode": secure_mode,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Chroot creation failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/chroot/optimize")
        async def optimize_chroot(request: Request):
            """Optimize chroot environment via AION."""
            if not self.aion_agent:
                raise HTTPException(status_code=503, detail="AION agent not ready")

            try:
                body = await request.json()
                source_path = body.get("source_path")
                target_path = body.get("target_path")
                secure_mode = body.get("secure_mode", True)

                if not source_path or not target_path:
                    raise HTTPException(status_code=400, detail="source_path and target_path required")

                # Verify AION authorization
                if not self.verify_aion_authority(request):
                    raise HTTPException(status_code=403, detail="AION authorization required")

                # Execute chroot optimization via AION.sh
                result = await self.execute_aion_script("chroot-optimize", {
                    "source": source_path,
                    "target": target_path,
                    "secure": secure_mode
                })

                return {
                    "status": "optimized",
                    "source_path": source_path,
                    "target_path": target_path,
                    "result": result,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Chroot optimization failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/chroot/list")
        async def list_chroots():
            """List available chroot environments."""
            try:
                chroot_status = self.get_chroot_status()

                return {
                    "chroots": chroot_status,
                    "count": len(chroot_status),
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Chroot listing failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/autonomous")
        async def autonomous_action(request: Request):
            """Execute autonomous AION decision."""
            if not self.aion_agent:
                raise HTTPException(status_code=503, detail="AION agent not ready")

            try:
                body = await request.json()
                verify_mode = body.get("verify", False)

                # Verify AION authorization
                if not self.verify_aion_authority(request):
                    raise HTTPException(status_code=403, detail="AION authorization required")

                # Execute autonomous action via AION.sh
                result = await self.execute_aion_script("autonomous-action", {
                    "verify": verify_mode
                })

                return {
                    "status": "autonomous_action_executed",
                    "verify_mode": verify_mode,
                    "result": result,
                    "timestamp": datetime.now().isoformat(),
                    "decision_maker": "aion_prime"
                }

            except Exception as e:
                logger.error(f"Autonomous action failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def verify_aion_authority(self, request: Request) -> bool:
        """Verify request has AION authority."""
        # Check for AION request header
        aion_header = request.headers.get("X-AION-Request")
        if aion_header != "true":
            return False

        # Check if request originates from AION agent or localhost
        client_host = request.client.host
        if client_host not in ["127.0.0.1", "localhost"]:
            # Additional verification for external requests
            return False

        return True

    async def execute_aion_script(self, command: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute AION.sh script with specified command and parameters."""
        try:
            # Build AION.sh command
            script_path = "/home/aion/AION.sh"
            cmd_args = [script_path, "aion_prime", command]

            # Add parameters as arguments
            for key, value in parameters.items():
                cmd_args.extend([f"--{key}", str(value)])

            # Execute command
            process = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/home/aion"
            )

            stdout, stderr = await process.communicate()

            result = {
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8'),
                "stderr": stderr.decode('utf-8'),
                "command": " ".join(cmd_args)
            }

            if process.returncode != 0:
                logger.error(f"AION script failed: {result['stderr']}")
                raise Exception(f"AION script execution failed: {result['stderr']}")

            logger.info(f"AION script executed successfully: {command}")
            return result

        except Exception as e:
            logger.error(f"AION script execution error: {e}")
            raise

    def get_chroot_status(self) -> list:
        """Get status of available chroot environments."""
        try:
            chroot_dir = "/home/aion/chroots"
            if not os.path.exists(chroot_dir):
                return []

            chroots = []
            for item in os.listdir(chroot_dir):
                chroot_path = os.path.join(chroot_dir, item)
                if os.path.isdir(chroot_path):
                    # Check for AION markers
                    aion_marker = os.path.join(chroot_path, ".aion_chroot")
                    optimized_marker = os.path.join(chroot_path, ".aion_optimized")

                    status = {
                        "name": item,
                        "path": chroot_path,
                        "size": self.get_directory_size(chroot_path),
                        "aion_managed": os.path.exists(aion_marker),
                        "optimized": os.path.exists(optimized_marker),
                        "created": os.path.getctime(chroot_path)
                    }
                    chroots.append(status)

            return chroots

        except Exception as e:
            logger.error(f"Failed to get chroot status: {e}")
            return []

    def get_directory_size(self, path: str) -> int:
        """Get directory size in bytes."""
        try:
            result = subprocess.run(
                ["du", "-sb", path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return int(result.stdout.split()[0])
            return 0
        except:
            return 0

# Global service instance
aion_service = AIONProductionService()

@aion_service.app.on_event("startup")
async def startup_event():
    """Initialize AION service on startup."""
    logger.info("Starting AION Production Service...")
    logger.info("© Professor Codephreak - rage.pythai.net")

    try:
        await aion_service.initialize_agents()
        logger.info("AION service ready for autonomous operations")
    except Exception as e:
        logger.error(f"Failed to start AION service: {e}")
        raise

@aion_service.app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on service shutdown."""
    logger.info("Shutting down AION service...")

    try:
        if aion_service.aion_agent:
            await aion_service.aion_agent.shutdown()
        if aion_service.systemadmin_agent:
            await aion_service.systemadmin_agent.shutdown()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# FastAPI app instance for uvicorn
app = aion_service.app

if __name__ == "__main__":
    # Production configuration
    uvicorn.run(
        "aion_production_service:app",
        host="127.0.0.1",
        port=8001,
        reload=False,
        access_log=True,
        log_config={
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "[AION] %(asctime)s - %(levelname)s - %(message)s"
                }
            },
            "handlers": {
                "file": {
                    "class": "logging.FileHandler",
                    "filename": "/var/log/mindx/aion_service.log",
                    "formatter": "default"
                }
            },
            "root": {
                "level": "INFO",
                "handlers": ["file"]
            }
        }
    )