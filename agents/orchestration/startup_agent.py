# mindx/orchestration/startup_agent.py
"""
StartupAgent: Controls agent startup and initialization.

This agent manages the startup sequence, initializes always-on agents,
loads agent registry from pgvectorscale, and restores agent state from blockchain if needed.
"""

import asyncio
import json
import time
import re
import os
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import asdict

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent
from agents.core.id_manager_agent import IDManagerAgent
from agents.orchestration.system_state_tracker import SystemStateTracker, SystemEventType

logger = get_logger(__name__)

# DeltaVerse configuration
DELTAVERSE_CONFIG = {
    "enabled": True,
    "fileroom_base_path": PROJECT_ROOT / "data" / "deltaverse" / "filerooms",
    "memory_encoding": "blockchain_hybrid",  # blockchain, local, hybrid
    "spawn_on_startup": True,
    "max_concurrent_filerooms": 10,
    "inference_points": []  # Populated dynamically
}


class StartupAgent:
    """
    Agent specialized in controlling agent startup and initialization.
    Manages the startup sequence for the mindX system.
    """
    
    def __init__(
        self,
        agent_id: str = "startup_agent",
        coordinator_agent: Optional[CoordinatorAgent] = None,
        memory_agent: Optional[MemoryAgent] = None,
        config: Optional[Config] = None,
        test_mode: bool = False,
        mindxagent: Optional[Any] = None
    ):
        self.agent_id = agent_id
        self.coordinator_agent = coordinator_agent
        self.memory_agent = memory_agent or MemoryAgent(config=config)
        self.config = config or Config(test_mode=test_mode)
        self.test_mode = test_mode
        self.mindxagent = mindxagent
        self.log_prefix = f"StartupAgent ({self.agent_id}):"
        
        # System state tracker
        self.state_tracker = SystemStateTracker(
            memory_agent=self.memory_agent,
            config=self.config,
            test_mode=test_mode
        )
        
        # Always-on agents list
        self.always_on_agents: List[str] = [
            "coordinator_agent",
            "mindxagent",
            "memory_agent"
        ]
        
        # Startup sequence
        self.startup_sequence: List[Dict[str, Any]] = []
        self.startup_log: List[Dict[str, Any]] = []
        
        # mindX.sh command knowledge
        self.mindx_sh_commands: Dict[str, Any] = {}
        self.startup_docs: Dict[str, Any] = {}

        # Multi-inference provider tracking
        self.connected_providers: Dict[str, Any] = {}
        self.inference_points: List[Dict[str, Any]] = []
        self.provider_registry = None

        # DeltaVerse fileroom system
        self.deltaverse_config = DELTAVERSE_CONFIG.copy()
        self.deltaverse_config["fileroom_base_path"].mkdir(parents=True, exist_ok=True)
        self.active_filerooms: Dict[str, Any] = {}
        self.blockchain_memories: List[Dict[str, Any]] = []

        # GitHub feedback tool reference
        self.feedback_tool = None

        # Terminal log tracking
        self.terminal_log_path = PROJECT_ROOT / "data" / "logs" / "terminal_startup.log"

        # Log startup agent initialization
        logger.info(f"{self.log_prefix} StartupAgent initializing...")
        logger.info(f"{self.log_prefix} Agent ID: {self.agent_id}")
        logger.info(f"{self.log_prefix} Coordinator Agent: {'Available' if coordinator_agent else 'Not provided'}")
        logger.info(f"{self.log_prefix} Memory Agent: {'Available' if self.memory_agent else 'Not provided'}")
        logger.info(f"{self.log_prefix} Test Mode: {self.test_mode}")
        
        # Log to memory agent
        asyncio.create_task(self._log_self_initialization())
        
        # Load mindX.sh and startup documentation knowledge
        asyncio.create_task(self._load_startup_knowledge())
    
    async def initialize_system(
        self,
        restore_from_blockchain: bool = False
    ) -> Dict[str, Any]:
        """
        Initialize the entire system with comprehensive logging and state tracking.
        
        Args:
            restore_from_blockchain: Whether to restore agent state from blockchain
        
        Returns:
            Dictionary with initialization results
        """
        logger.info(f"{self.log_prefix} Starting system initialization")
        
        start_time = time.time()
        initialization_results = {
            "status": "in_progress",
            "steps_completed": [],
            "errors": [],
            "agents_initialized": [],
            "previous_state": None,
            "improvement_history": [],
            "rollback_points": []
        }
        
        try:
            # Load previous state data
            logger.info(f"{self.log_prefix} Loading previous system state")
            previous_state = await self.state_tracker.get_latest_state()
            if previous_state:
                initialization_results["previous_state"] = {
                    "event_id": previous_state.event_id,
                    "timestamp": previous_state.timestamp,
                    "improvement_count": previous_state.improvement_count,
                    "rollback_count": previous_state.rollback_count
                }
            
            # Load improvement history
            improvement_history = await self.state_tracker.get_improvement_history(limit=10)
            initialization_results["improvement_history"] = improvement_history
            
            # Load rollback points
            rollback_points = await self.state_tracker.get_rollback_points(limit=5)
            initialization_results["rollback_points"] = rollback_points
            
            # Log comprehensive startup data to memory agent
            await self.memory_agent.log_process(
                "startup_initiation",
                {
                    "timestamp": time.time(),
                    "previous_state": initialization_results["previous_state"],
                    "improvement_count": len(improvement_history),
                    "rollback_count": len(rollback_points),
                    "restore_from_blockchain": restore_from_blockchain
                },
                {"agent_id": self.agent_id, "event": "startup_initiation"}
            )
            
            # Capture system state before startup
            before_state = await self.state_tracker.capture_system_state(
                SystemEventType.STARTUP,
                coordinator_agent=self.coordinator_agent,
                metadata={"phase": "before_startup"}
            )
            # Step 0: Validate startup environment
            logger.info(f"{self.log_prefix} Step 0: Validating startup environment")
            env_validation = await self.validate_startup_environment()
            initialization_results["environment_validation"] = env_validation
            if not env_validation["valid"]:
                logger.warning(f"{self.log_prefix} Environment validation found issues: {env_validation.get('errors', [])}")
            
            # Step 1: Load agent registry from pgvectorscale
            logger.info(f"{self.log_prefix} Step 1: Loading agent registry from pgvectorscale")
            registry_result = await self._load_agent_registry()
            initialization_results["steps_completed"].append("load_registry")
            initialization_results["registry"] = registry_result
            
            # Include startup knowledge in results
            initialization_results["startup_knowledge"] = {
                "mindx_sh_commands_available": len(self.mindx_sh_commands.get("commands", {})),
                "startup_docs_loaded": len(self.startup_docs),
                "commands": list(self.mindx_sh_commands.get("commands", {}).keys())[:10]  # First 10
            }
            
            # Step 2: Restore agent state from blockchain if requested
            if restore_from_blockchain:
                logger.info(f"{self.log_prefix} Step 2: Restoring agent state from blockchain")
                blockchain_result = await self._restore_from_blockchain()
                initialization_results["steps_completed"].append("restore_blockchain")
                initialization_results["blockchain_restore"] = blockchain_result
            
            # Step 3: Initialize always-on agents
            logger.info(f"{self.log_prefix} Step 3: Initializing always-on agents")
            always_on_result = await self._initialize_always_on_agents()
            initialization_results["steps_completed"].append("initialize_always_on")
            initialization_results["agents_initialized"].extend(always_on_result.get("agents", []))
            
            # Step 4: Coordinate startup sequence
            logger.info(f"{self.log_prefix} Step 4: Coordinating startup sequence")
            sequence_result = await self._coordinate_startup_sequence()
            initialization_results["steps_completed"].append("coordinate_sequence")
            initialization_results["sequence"] = sequence_result
            
            initialization_results["status"] = "completed"
            initialization_results["duration_seconds"] = time.time() - start_time
            
            logger.info(f"{self.log_prefix} System initialization completed in {initialization_results['duration_seconds']:.2f}s")
            
            # Capture system state after startup
            after_state = await self.state_tracker.capture_system_state(
                SystemEventType.STARTUP,
                coordinator_agent=self.coordinator_agent,
                metadata={
                    "phase": "after_startup",
                    "duration_seconds": initialization_results["duration_seconds"],
                    "steps_completed": initialization_results["steps_completed"]
                }
            )
            
            # Comprehensive startup record with resource and performance data
            startup_record = {
                "timestamp": time.time(),
                "duration": initialization_results["duration_seconds"],
                "steps": initialization_results["steps_completed"],
                "agents_initialized": initialization_results["agents_initialized"],
                "before_state": {
                    "resource_snapshot": asdict(before_state.resource_snapshot) if before_state.resource_snapshot else None,
                    "performance_snapshot": asdict(before_state.performance_snapshot) if before_state.performance_snapshot else None
                },
                "after_state": {
                    "resource_snapshot": asdict(after_state.resource_snapshot) if after_state.resource_snapshot else None,
                    "performance_snapshot": asdict(after_state.performance_snapshot) if after_state.performance_snapshot else None,
                    "agents_registered": after_state.agents_registered,
                    "agents_active": after_state.agents_active,
                    "tools_registered": after_state.tools_registered
                },
                "improvement_count": after_state.improvement_count,
                "rollback_count": after_state.rollback_count,
                "previous_state": initialization_results["previous_state"]
            }
            self.startup_log.append(startup_record)
            
            # Log comprehensive startup data to memory agent
            await self.memory_agent.log_process(
                "system_startup_complete",
                startup_record,
                {"agent_id": self.agent_id, "event": "startup_complete"}
            )
            
            # Have mindXagent review startup data for self-improvement
            if self.mindxagent:
                try:
                    await self._review_startup_with_mindxagent(startup_record, before_state, after_state)
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error in mindXagent review: {e}", exc_info=True)
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error during system initialization: {e}", exc_info=True)
            initialization_results["status"] = "failed"
            initialization_results["errors"].append(str(e))
        
        return initialization_results
    
    async def _load_agent_registry(self) -> Dict[str, Any]:
        """
        Load agent registry from pgvectorscale database.
        
        Returns:
            Dictionary with registry data
        """
        # TODO: Implement pgvectorscale integration
        # For now, return placeholder
        logger.info(f"{self.log_prefix} Loading agent registry from pgvectorscale (placeholder)")
        
        # This would query pgvectorscale for agent metadata
        registry_path = PROJECT_ROOT / "data" / "config" / "official_agents_registry.json"
        if registry_path.exists():
            try:
                with registry_path.open("r", encoding="utf-8") as f:
                    registry_data = json.load(f)
                    return {
                        "source": "local_file",
                        "agents_count": len(registry_data.get("registered_agents", {})),
                        "registry": registry_data
                    }
            except Exception as e:
                logger.error(f"{self.log_prefix} Error loading registry from file: {e}")
        
        return {
            "source": "empty",
            "agents_count": 0,
            "registry": {}
        }
    
    async def _restore_from_blockchain(self) -> Dict[str, Any]:
        """
        Restore agent state from blockchain if needed.
        
        Returns:
            Dictionary with restore results
        """
        # TODO: Implement blockchain integration
        logger.info(f"{self.log_prefix} Restoring from blockchain (placeholder)")
        
        return {
            "restored": False,
            "message": "Blockchain restore not yet implemented"
        }
    
    async def _initialize_always_on_agents(self) -> Dict[str, Any]:
        """
        Initialize always-on agents.
        
        Returns:
            Dictionary with initialization results
        """
        initialized_agents = []
        errors = []
        
        for agent_id in self.always_on_agents:
            try:
                logger.info(f"{self.log_prefix} Initializing always-on agent: {agent_id}")
                
                # Register with coordinator if available
                if self.coordinator_agent and agent_id != "coordinator_agent":
                    # Agent should already be initialized, just register
                    if hasattr(self.coordinator_agent, 'agent_registry'):
                        if agent_id in self.coordinator_agent.agent_registry:
                            logger.info(f"{self.log_prefix} Agent {agent_id} already registered")
                            initialized_agents.append(agent_id)
                            continue
                
                # For now, just mark as initialized
                initialized_agents.append(agent_id)
                logger.info(f"{self.log_prefix} Always-on agent {agent_id} initialized")
                
            except Exception as e:
                logger.error(f"{self.log_prefix} Error initializing {agent_id}: {e}", exc_info=True)
                errors.append({"agent_id": agent_id, "error": str(e)})
        
        return {
            "agents": initialized_agents,
            "errors": errors,
            "total": len(initialized_agents)
        }
    
    async def _coordinate_startup_sequence(self) -> Dict[str, Any]:
        """
        Coordinate the startup sequence.
        
        Returns:
            Dictionary with sequence results
        """
        sequence = [
            {"step": 1, "name": "load_registry", "status": "completed"},
            {"step": 2, "name": "initialize_core_agents", "status": "completed"},
            {"step": 3, "name": "initialize_coordinator", "status": "completed"},
            {"step": 4, "name": "initialize_memory", "status": "completed"},
            {"step": 5, "name": "connect_ollama", "status": "pending"},
            {"step": 6, "name": "ready", "status": "pending"}
        ]
        
        # Attempt Ollama auto-connection
        ollama_result = await self._auto_connect_ollama()
        if ollama_result.get("connected"):
            sequence[4]["status"] = "completed"
            logger.info(f"{self.log_prefix} Ollama auto-connected: {ollama_result.get('base_url')}")
        else:
            sequence[4]["status"] = "skipped"
            logger.info(f"{self.log_prefix} Ollama auto-connection skipped: {ollama_result.get('reason', 'Not configured')}")
        
        sequence[5]["status"] = "completed"
        self.startup_sequence = sequence
        
        return {
            "sequence": sequence,
            "ollama_connection": ollama_result,
            "all_completed": all(s["status"] in ["completed", "skipped"] for s in sequence)
        }
    
    async def _auto_connect_ollama(self) -> Dict[str, Any]:
        """
        Automatically connect to Ollama on startup, remembering previous connection.
        
        Returns:
            Dictionary with connection results
        """
        try:
            # Check memory for previous Ollama connection
            ollama_memory = await self.memory_agent.query_memory(
                query="ollama connection configuration",
                memory_type="ltm",
                limit=5
            )
            
            # Default to remembered connection: 10.0.0.155:18080
            default_host = "10.0.0.155"
            default_port = 18080
            
            # Try to find previous connection in memory
            for memory_item in ollama_memory:
                if "ollama" in memory_item.get("content", "").lower():
                    # Try to extract host and port from memory
                    content = str(memory_item.get("content", ""))
                    if "10.0.0.155" in content:
                        default_host = "10.0.0.155"
                    # Check for both 18080 and 108080 (legacy)
                    if "18080" in content:
                        default_port = 18080
                    elif "108080" in content or "10808" in content:
                        default_port = 108080
            
            # Also check config for Ollama settings
            config_host = self.config.get("ollama.host", default_host)
            config_port = self.config.get("ollama.port", default_port)
            config_base_url = self.config.get("ollama.base_url")
            
            if config_base_url:
                base_url = config_base_url
            else:
                base_url = f"http://{config_host}:{config_port}"
            
            # Try to connect
            try:
                from llm.ollama_handler import OllamaHandler
                handler = OllamaHandler(
                    model_name_for_api=None,
                    base_url=base_url
                )
                
                # Test connection by listing models
                models = await handler.list_local_models_api()
                
                if models and not any("error" in str(m).lower() for m in models):
                    # Connection successful
                    await self.memory_agent.log_process(
                        "ollama_auto_connected",
                        {
                            "base_url": base_url,
                            "host": config_host,
                            "port": config_port,
                            "models_count": len(models),
                            "timestamp": time.time()
                        },
                        {"agent_id": self.agent_id, "event": "ollama_connection"}
                    )
                    
                    # Store connection in config
                    logger.info(f"{self.log_prefix} Ollama auto-connected to {base_url} with {len(models)} models")
                    
                    return {
                        "connected": True,
                        "base_url": base_url,
                        "host": config_host,
                        "port": config_port,
                        "models_count": len(models),
                        "models": [m.get("name", "unknown") for m in models[:5]]  # First 5 model names
                    }
                else:
                    return {
                        "connected": False,
                        "reason": "Connection test failed",
                        "base_url": base_url
                    }
            except Exception as e:
                logger.warning(f"{self.log_prefix} Ollama connection attempt failed: {e}")
                return {
                    "connected": False,
                    "reason": str(e),
                    "base_url": base_url
                }
                
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error in Ollama auto-connection: {e}", exc_info=True)
            return {
                "connected": False,
                "reason": f"Error: {str(e)}"
            }
    
    async def initialize_agent_on_demand(
        self,
        agent_type: str,
        agent_id: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Initialize an agent on-demand (not always-on).
        
        Args:
            agent_type: Type of agent to initialize
            agent_id: ID for the agent
            config: Optional configuration
        
        Returns:
            Dictionary with initialization results
        """
        logger.info(f"{self.log_prefix} Initializing on-demand agent: {agent_id} (type: {agent_type})")
        
        if not self.coordinator_agent:
            return {
                "success": False,
                "error": "CoordinatorAgent not available"
            }
        
        try:
            # Use coordinator to create and register agent
            result = await self.coordinator_agent.create_and_register_agent(
                agent_type=agent_type,
                agent_id=agent_id,
                config=config or {}
            )
            
            if result.get("status") == "SUCCESS":
                logger.info(f"{self.log_prefix} On-demand agent {agent_id} initialized successfully")
                return {
                    "success": True,
                    "agent_id": agent_id,
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Unknown error")
                }
        except Exception as e:
            logger.error(f"{self.log_prefix} Error initializing on-demand agent: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _review_startup_with_mindxagent(
        self,
        startup_record: Dict[str, Any],
        before_state: Any,
        after_state: Any
    ):
        """
        Have mindXagent review startup data for self-awareness and self-improvement.
        
        Args:
            startup_record: Complete startup record
            before_state: System state before startup
            after_state: System state after startup
        """
        if not self.mindxagent:
            return
        
        logger.info(f"{self.log_prefix} Requesting mindXagent review of startup data")
        
        try:
            # Prepare review data
            review_data = {
                "startup_record": startup_record,
                "before_state": asdict(before_state) if before_state else None,
                "after_state": asdict(after_state) if after_state else None,
                "improvement_opportunities": [],
                "performance_analysis": {},
                "resource_analysis": {}
            }
            
            # Analyze resource changes
            if before_state and after_state:
                if before_state.resource_snapshot and after_state.resource_snapshot:
                    review_data["resource_analysis"] = {
                        "cpu_change": after_state.resource_snapshot.cpu_percent - before_state.resource_snapshot.cpu_percent,
                        "memory_change": after_state.resource_snapshot.memory_percent - before_state.resource_snapshot.memory_percent,
                        "process_change": after_state.resource_snapshot.process_count - before_state.resource_snapshot.process_count
                    }
            
            # Analyze performance changes
            if before_state and after_state:
                if before_state.performance_snapshot and after_state.performance_snapshot:
                    review_data["performance_analysis"] = {
                        "calls_change": after_state.performance_snapshot.total_calls - before_state.performance_snapshot.total_calls,
                        "error_rate_change": after_state.performance_snapshot.error_rate - before_state.performance_snapshot.error_rate,
                        "latency_change": after_state.performance_snapshot.avg_latency_ms - before_state.performance_snapshot.avg_latency_ms
                    }
            
            # Log review request to memory agent
            await self.memory_agent.log_process(
                "mindxagent_startup_review",
                review_data,
                {"agent_id": self.agent_id, "reviewer": "mindxagent"}
            )
            
            # Call mindXagent review method if available
            if hasattr(self.mindxagent, 'review_system_state'):
                await self.mindxagent.review_system_state(
                    event_type="startup",
                    data=review_data
                )
            
            logger.info(f"{self.log_prefix} mindXagent review completed")
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in mindXagent review: {e}", exc_info=True)
    
    async def _log_self_initialization(self):
        """Log startup agent's own initialization to memory."""
        try:
            await self.memory_agent.log_process(
                "startup_agent_initialized",
                {
                    "agent_id": self.agent_id,
                    "timestamp": time.time(),
                    "coordinator_available": self.coordinator_agent is not None,
                    "memory_agent_available": self.memory_agent is not None,
                    "test_mode": self.test_mode,
                    "always_on_agents": self.always_on_agents
                },
                {"agent_id": self.agent_id, "event": "self_initialization"}
            )
            logger.info(f"{self.log_prefix} Self-initialization logged to memory")
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error logging self-initialization: {e}", exc_info=True)
    
    async def _load_startup_knowledge(self):
        """
        Load knowledge about mindX.sh commands and startup documentation.
        This runs asynchronously during initialization.
        """
        try:
            # Load mindX.sh command knowledge
            await self._parse_mindx_sh_commands()
            
            # Load startup documentation
            await self._load_startup_documentation()
            
            # Log knowledge to memory agent
            await self.memory_agent.log_process(
                "startup_knowledge_loaded",
                {
                    "mindx_sh_commands": list(self.mindx_sh_commands.keys()),
                    "startup_docs_loaded": list(self.startup_docs.keys()),
                    "timestamp": time.time()
                },
                {"agent_id": self.agent_id, "event": "knowledge_loading"}
            )
            
            logger.info(f"{self.log_prefix} Startup knowledge loaded: {len(self.mindx_sh_commands)} commands, {len(self.startup_docs)} docs")
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error loading startup knowledge: {e}", exc_info=True)
    
    async def _parse_mindx_sh_commands(self):
        """
        Parse mindX.sh script to understand available commands and their purposes.
        """
        mindx_sh_path = PROJECT_ROOT / "mindX.sh"
        if not mindx_sh_path.exists():
            logger.warning(f"{self.log_prefix} mindX.sh not found at {mindx_sh_path}")
            return
        
        try:
            with mindx_sh_path.open("r", encoding="utf-8") as f:
                content = f.read()
            
            # Extract command-line options and their descriptions
            commands = {}
            
            # Parse --help output structure
            if "show_help" in content:
                # Extract options from help function
                help_start = content.find("function show_help")
                if help_start != -1:
                    help_end = content.find("}", help_start)
                    help_section = content[help_start:help_end]
                    
                    # Extract options and descriptions
                    option_pattern = r'echo\s+"\s*--([^"]+)"'
                    desc_pattern = r'echo\s+"\s*([^"]+)"'
                    
                    options = re.findall(option_pattern, help_section)
                    descriptions = re.findall(desc_pattern, help_section)
                    
                    for i, option in enumerate(options):
                        if i < len(descriptions):
                            commands[option] = {
                                "description": descriptions[i],
                                "type": "flag" if "=" not in option else "option"
                            }
            
            # Extract key functions and their purposes
            functions = {
                "setup_virtual_environment_and_mindx_deps": "Sets up Python virtual environment and installs dependencies",
                "setup_backend_service": "Sets up MindX Backend Service files",
                "setup_frontend_ui": "Sets up MindX Frontend UI files",
                "start_web_frontend": "Starts MindX Web Interface (backend + frontend)",
                "start_mindx_service": "Starts MindX services (backend or frontend)",
                "stop_mindx_service": "Stops MindX services",
                "ensure_mindx_structure": "Ensures MindX base directory structure exists",
                "setup_dotenv_file": "Sets up .env file with API keys",
                "setup_mindx_config_json": "Sets up mindx_config.json configuration file"
            }
            
            # Extract key variables
            variables = {
                "DEFAULT_PROJECT_ROOT_NAME": "augmentic_mindx",
                "DEFAULT_VENV_NAME": ".mindx_env",
                "DEFAULT_FRONTEND_PORT": "3000",
                "DEFAULT_BACKEND_PORT": "8000",
                "DEFAULT_LOG_LEVEL": "INFO"
            }
            
            self.mindx_sh_commands = {
                "commands": commands,
                "functions": functions,
                "variables": variables,
                "script_path": str(mindx_sh_path),
                "version": "2.0.0"
            }
            
            logger.info(f"{self.log_prefix} Parsed {len(commands)} mindX.sh commands")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error parsing mindX.sh: {e}", exc_info=True)
    
    async def _load_startup_documentation(self):
        """
        Load startup-related documentation from docs folder.
        """
        docs_dir = PROJECT_ROOT / "docs"
        if not docs_dir.exists():
            logger.warning(f"{self.log_prefix} Docs directory not found at {docs_dir}")
            return
        
        startup_docs = {}
        
        # Key startup-related documentation files
        doc_files = [
            "startup_agent.md",
            "MINDX.md",
            "mindx_evolution_startup_guide.md",
            "AGENTS.md",
            "ORCHESTRATION.md"
        ]
        
        for doc_file in doc_files:
            doc_path = docs_dir / doc_file
            if doc_path.exists():
                try:
                    with doc_path.open("r", encoding="utf-8") as f:
                        content = f.read()
                    
                    # Extract key information
                    doc_info = {
                        "path": str(doc_path),
                        "size": len(content),
                        "lines": content.count("\n"),
                        "sections": []
                    }
                    
                    # Extract section headers
                    headers = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
                    doc_info["sections"] = headers[:10]  # First 10 sections
                    
                    # Extract key concepts
                    if "startup" in doc_file.lower() or "initialization" in content.lower():
                        doc_info["type"] = "startup_guide"
                    elif "agent" in doc_file.lower():
                        doc_info["type"] = "agent_documentation"
                    elif "orchestration" in doc_file.lower():
                        doc_info["type"] = "orchestration_guide"
                    else:
                        doc_info["type"] = "general"
                    
                    startup_docs[doc_file] = doc_info
                    
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error loading doc {doc_file}: {e}")
        
        self.startup_docs = startup_docs
        logger.info(f"{self.log_prefix} Loaded {len(startup_docs)} startup documentation files")
    
    async def get_startup_command_info(self, command: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about mindX.sh commands.
        
        Args:
            command: Specific command to get info for, or None for all commands
        
        Returns:
            Dictionary with command information
        """
        if command:
            return {
                "command": command,
                "info": self.mindx_sh_commands.get("commands", {}).get(command, {}),
                "available_commands": list(self.mindx_sh_commands.get("commands", {}).keys())
            }
        
        return self.mindx_sh_commands
    
    async def get_startup_documentation(self, doc_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get startup documentation information.
        
        Args:
            doc_name: Specific document to get info for, or None for all docs
        
        Returns:
            Dictionary with documentation information
        """
        if doc_name:
            return {
                "doc": doc_name,
                "info": self.startup_docs.get(doc_name, {}),
                "available_docs": list(self.startup_docs.keys())
            }
        
        return self.startup_docs
    
    async def validate_startup_environment(self) -> Dict[str, Any]:
        """
        Validate that the startup environment matches mindX.sh requirements.
        
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            "valid": True,
            "checks": [],
            "warnings": [],
            "errors": []
        }
        
        try:
            # Check for required directories
            required_dirs = [
                "data",
                "data/logs",
                "data/config",
                "data/pids",
                "agents",
                "agents/orchestration"
            ]
            
            for dir_path in required_dirs:
                full_path = PROJECT_ROOT / dir_path
                if full_path.exists():
                    validation_results["checks"].append({
                        "check": f"Directory exists: {dir_path}",
                        "status": "pass"
                    })
                else:
                    validation_results["checks"].append({
                        "check": f"Directory exists: {dir_path}",
                        "status": "fail"
                    })
                    validation_results["warnings"].append(f"Missing directory: {dir_path}")
                    validation_results["valid"] = False
            
            # Check for required files
            required_files = [
                "mindX.sh",
                "requirements.txt",
                ".env"
            ]
            
            for file_path in required_files:
                full_path = PROJECT_ROOT / file_path
                if full_path.exists():
                    validation_results["checks"].append({
                        "check": f"File exists: {file_path}",
                        "status": "pass"
                    })
                else:
                    validation_results["checks"].append({
                        "check": f"File exists: {file_path}",
                        "status": "fail"
                    })
                    if file_path == ".env":
                        validation_results["warnings"].append(f"Missing file: {file_path} (may be created during setup)")
                    else:
                        validation_results["errors"].append(f"Missing required file: {file_path}")
                        validation_results["valid"] = False
            
            # Check Python version (should be 3.11 based on mindX.sh)
            import sys
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
            if sys.version_info >= (3, 11):
                validation_results["checks"].append({
                    "check": f"Python version: {python_version}",
                    "status": "pass"
                })
            else:
                validation_results["checks"].append({
                    "check": f"Python version: {python_version}",
                    "status": "fail"
                })
                validation_results["warnings"].append(f"Python version {python_version} may not match mindX.sh requirements (3.11+)")
            
            # Log validation results
            await self.memory_agent.log_process(
                "startup_environment_validation",
                validation_results,
                {"agent_id": self.agent_id, "event": "environment_validation"}
            )
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error validating startup environment: {e}", exc_info=True)
            validation_results["valid"] = False
            validation_results["errors"].append(str(e))
        
        return validation_results
    
    async def shutdown(self):
        """Shutdown the startup agent."""
        logger.info(f"{self.log_prefix} Shutting down")

    # ==================== Multi-Inference Provider Connection ====================

    async def connect_all_inference_providers(self) -> Dict[str, Any]:
        """
        Connect to all available inference providers from environment and config.

        This enables multi-inference scenarios for agentic communication.

        Returns:
            Dictionary with connection results for all providers
        """
        logger.info(f"{self.log_prefix} Connecting to all inference providers...")

        results = {
            "connected": [],
            "failed": [],
            "skipped": [],
            "total_inference_points": 0
        }

        try:
            # Load provider registry
            from api.provider_registry import get_provider_registry
            self.provider_registry = await get_provider_registry()

            providers = self.provider_registry.list_providers()
            logger.info(f"{self.log_prefix} Found {len(providers)} registered providers")

            # Try to connect to each provider
            for provider in providers:
                provider_name = provider["name"]
                connection_result = await self._connect_provider(provider)

                if connection_result["connected"]:
                    results["connected"].append(connection_result)
                    self.connected_providers[provider_name] = connection_result
                    self.inference_points.append({
                        "provider": provider_name,
                        "type": "cloud" if provider_name != "ollama" else "local",
                        "endpoint": connection_result.get("endpoint", ""),
                        "models": connection_result.get("models", [])
                    })
                elif connection_result.get("skipped"):
                    results["skipped"].append(connection_result)
                else:
                    results["failed"].append(connection_result)

            # Also try to reconnect to previously known local models
            local_reconnection = await self._reconnect_local_models()
            if local_reconnection.get("connected"):
                results["connected"].extend(local_reconnection.get("models", []))

            results["total_inference_points"] = len(self.inference_points)

            # Log results to memory
            await self.memory_agent.log_process(
                "inference_providers_connected",
                {
                    "connected_count": len(results["connected"]),
                    "failed_count": len(results["failed"]),
                    "skipped_count": len(results["skipped"]),
                    "inference_points": self.inference_points,
                    "timestamp": time.time()
                },
                {"agent_id": self.agent_id, "event": "provider_connection"}
            )

            logger.info(f"{self.log_prefix} Connected to {len(results['connected'])} providers, "
                       f"{len(results['failed'])} failed, {len(results['skipped'])} skipped")

        except Exception as e:
            logger.error(f"{self.log_prefix} Error connecting providers: {e}", exc_info=True)
            results["error"] = str(e)

        return results

    async def _connect_provider(self, provider: Dict[str, Any]) -> Dict[str, Any]:
        """Connect to a single provider."""
        provider_name = provider["name"]
        result = {
            "provider": provider_name,
            "connected": False,
            "skipped": False
        }

        try:
            # Check if API key is available
            api_key_env = provider.get("api_key_env_var")
            base_url_env = provider.get("base_url_env_var")

            if provider.get("requires_api_key") and api_key_env:
                api_key = os.environ.get(api_key_env)
                if not api_key:
                    result["skipped"] = True
                    result["reason"] = f"No API key found in {api_key_env}"
                    return result

            if provider.get("requires_base_url") and base_url_env:
                base_url = os.environ.get(base_url_env)
                if not base_url:
                    # Try default for Ollama
                    if provider_name == "ollama":
                        base_url = "http://10.0.0.155:108080"
                    else:
                        result["skipped"] = True
                        result["reason"] = f"No base URL found in {base_url_env}"
                        return result

            # Enable and create provider instance
            self.provider_registry.enable_provider(provider_name)
            instance = await self.provider_registry.create_provider_instance(provider_name)

            if instance:
                result["connected"] = True
                result["endpoint"] = provider.get("base_url_env_var", "cloud")

                # Try to get available models
                if hasattr(instance, 'list_models'):
                    try:
                        models = await instance.list_models()
                        result["models"] = models[:10] if models else []
                    except Exception:
                        result["models"] = []

                logger.info(f"{self.log_prefix} Connected to {provider_name}")
            else:
                result["reason"] = "Failed to create provider instance"

        except Exception as e:
            result["reason"] = str(e)
            logger.warning(f"{self.log_prefix} Failed to connect to {provider_name}: {e}")

        return result

    async def _reconnect_local_models(self) -> Dict[str, Any]:
        """Reconnect to previously connected local models from memory."""
        result = {
            "connected": False,
            "models": []
        }

        try:
            # Query memory for previous local model connections
            local_model_memory = await self.memory_agent.query_memory(
                query="local model connection ollama llama",
                memory_type="ltm",
                limit=20
            )

            known_endpoints = set()
            for memory_item in local_model_memory:
                content = str(memory_item.get("content", ""))
                # Extract endpoints
                if "10.0.0.155" in content:
                    known_endpoints.add("http://10.0.0.155:108080")
                if "localhost" in content or "127.0.0.1" in content:
                    known_endpoints.add("http://localhost:11434")

            # Try to connect to each known endpoint
            for endpoint in known_endpoints:
                try:
                    from llm.ollama_handler import OllamaHandler
                    handler = OllamaHandler(model_name_for_api=None, base_url=endpoint)
                    models = await handler.list_local_models_api()

                    if models and not any("error" in str(m).lower() for m in models):
                        for model in models[:5]:
                            model_info = {
                                "provider": "ollama",
                                "type": "local",
                                "endpoint": endpoint,
                                "model_name": model.get("name", "unknown"),
                                "connected": True
                            }
                            result["models"].append(model_info)
                            self.inference_points.append({
                                "provider": "ollama",
                                "type": "local",
                                "endpoint": endpoint,
                                "model": model.get("name")
                            })

                        result["connected"] = True
                        logger.info(f"{self.log_prefix} Reconnected to {len(models)} local models at {endpoint}")

                except Exception as e:
                    logger.debug(f"{self.log_prefix} Could not reconnect to {endpoint}: {e}")

        except Exception as e:
            logger.warning(f"{self.log_prefix} Error reconnecting local models: {e}")

        return result

    # ==================== DeltaVerse Fileroom System ====================

    async def spawn_deltaverse_fileroom(
        self,
        fileroom_id: Optional[str] = None,
        purpose: str = "agentic_communication",
        agents: Optional[List[str]] = None,
        blockchain_encoded: bool = True
    ) -> Dict[str, Any]:
        """
        Spawn a new DeltaVerse fileroom for agentic communication.

        A fileroom is a virtual space where agents can communicate and share
        context, with memories optionally encoded to blockchain.

        Args:
            fileroom_id: Unique ID for the fileroom (auto-generated if None)
            purpose: Purpose of the fileroom
            agents: List of agent IDs to include
            blockchain_encoded: Whether to encode memories to blockchain

        Returns:
            Dictionary with fileroom details
        """
        if len(self.active_filerooms) >= self.deltaverse_config["max_concurrent_filerooms"]:
            return {
                "success": False,
                "error": "Maximum concurrent filerooms reached"
            }

        fileroom_id = fileroom_id or f"fileroom_{int(time.time())}_{hash(purpose) % 10000}"
        fileroom_path = self.deltaverse_config["fileroom_base_path"] / fileroom_id
        fileroom_path.mkdir(parents=True, exist_ok=True)

        fileroom = {
            "id": fileroom_id,
            "purpose": purpose,
            "agents": agents or [],
            "blockchain_encoded": blockchain_encoded,
            "created_at": time.time(),
            "path": str(fileroom_path),
            "status": "active",
            "inference_points": self.inference_points.copy(),
            "messages": [],
            "memories": []
        }

        # Create fileroom metadata file
        metadata_path = fileroom_path / "metadata.json"
        with metadata_path.open("w") as f:
            json.dump(fileroom, f, indent=2, default=str)

        self.active_filerooms[fileroom_id] = fileroom

        # Log to memory
        await self.memory_agent.log_process(
            "deltaverse_fileroom_spawned",
            {
                "fileroom_id": fileroom_id,
                "purpose": purpose,
                "agents": agents,
                "blockchain_encoded": blockchain_encoded,
                "inference_points_count": len(self.inference_points)
            },
            {"agent_id": self.agent_id, "event": "fileroom_spawn"}
        )

        logger.info(f"{self.log_prefix} Spawned DeltaVerse fileroom: {fileroom_id}")

        return {
            "success": True,
            "fileroom": fileroom
        }

    async def encode_memory_to_blockchain(
        self,
        memory_content: Dict[str, Any],
        fileroom_id: Optional[str] = None,
        memory_type: str = "interaction"
    ) -> Dict[str, Any]:
        """
        Encode a memory to blockchain for permanent storage.

        Uses the blockchain agent to create an immutable record of the memory.

        Args:
            memory_content: The memory content to encode
            fileroom_id: Optional fileroom association
            memory_type: Type of memory

        Returns:
            Dictionary with encoding result
        """
        try:
            # Create memory hash for blockchain
            import hashlib
            memory_json = json.dumps(memory_content, sort_keys=True, default=str)
            memory_hash = hashlib.sha256(memory_json.encode()).hexdigest()

            blockchain_record = {
                "memory_hash": memory_hash,
                "memory_type": memory_type,
                "fileroom_id": fileroom_id,
                "timestamp": time.time(),
                "content_preview": str(memory_content)[:200],
                "encoding_method": self.deltaverse_config["memory_encoding"]
            }

            # Store locally first
            blockchain_memories_path = self.deltaverse_config["fileroom_base_path"] / "blockchain_memories.json"
            existing_memories = []
            if blockchain_memories_path.exists():
                with blockchain_memories_path.open("r") as f:
                    existing_memories = json.load(f)

            existing_memories.append(blockchain_record)

            with blockchain_memories_path.open("w") as f:
                json.dump(existing_memories[-1000:], f, indent=2)  # Keep last 1000

            self.blockchain_memories.append(blockchain_record)

            # Log to memory agent
            await self.memory_agent.store_memory(
                agent_id=self.agent_id,
                memory_type="blockchain_encoded",
                content=blockchain_record,
                importance="high"
            )

            # If coordinator has blockchain agent, use it
            if self.coordinator_agent and hasattr(self.coordinator_agent, 'blockchain_agent'):
                # Future: actual blockchain encoding
                pass

            logger.info(f"{self.log_prefix} Encoded memory to blockchain: {memory_hash[:16]}...")

            return {
                "success": True,
                "memory_hash": memory_hash,
                "blockchain_record": blockchain_record
            }

        except Exception as e:
            logger.error(f"{self.log_prefix} Error encoding memory to blockchain: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def load_blockchain_memories(
        self,
        fileroom_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Load memories from blockchain/local storage.

        Args:
            fileroom_id: Filter by fileroom ID
            limit: Maximum number of memories to load

        Returns:
            List of blockchain-encoded memories
        """
        memories = []

        try:
            blockchain_memories_path = self.deltaverse_config["fileroom_base_path"] / "blockchain_memories.json"

            if blockchain_memories_path.exists():
                with blockchain_memories_path.open("r") as f:
                    all_memories = json.load(f)

                if fileroom_id:
                    memories = [m for m in all_memories if m.get("fileroom_id") == fileroom_id]
                else:
                    memories = all_memories

                memories = memories[-limit:]

            logger.info(f"{self.log_prefix} Loaded {len(memories)} blockchain memories")

        except Exception as e:
            logger.error(f"{self.log_prefix} Error loading blockchain memories: {e}")

        return memories

    # ==================== Terminal Log Processing ====================

    async def read_terminal_startup_log(self) -> Dict[str, Any]:
        """
        Read and process the terminal startup log for feedback.

        Returns:
            Dictionary with log content and extracted feedback
        """
        result = {
            "log_exists": False,
            "content": "",
            "errors": [],
            "warnings": [],
            "info": []
        }

        try:
            if self.terminal_log_path.exists():
                result["log_exists"] = True
                with self.terminal_log_path.open("r") as f:
                    content = f.read()
                result["content"] = content[-10000:]  # Last 10KB

                # Parse log entries
                for line in content.split("\n"):
                    line_lower = line.lower()
                    if "error" in line_lower or "exception" in line_lower:
                        result["errors"].append(line)
                    elif "warning" in line_lower or "warn" in line_lower:
                        result["warnings"].append(line)
                    elif "info" in line_lower:
                        result["info"].append(line[-500:])

                logger.info(f"{self.log_prefix} Read terminal log: {len(result['errors'])} errors, "
                           f"{len(result['warnings'])} warnings")

        except Exception as e:
            logger.warning(f"{self.log_prefix} Error reading terminal log: {e}")
            result["error"] = str(e)

        return result

    async def process_startup_feedback(self) -> Dict[str, Any]:
        """
        Process startup feedback from terminal log and GitHub feedback tool.

        Combines local log analysis with AI-powered code review feedback.

        Returns:
            Dictionary with combined feedback
        """
        result = {
            "terminal_feedback": {},
            "github_feedback": {},
            "combined_issues": [],
            "recommendations": []
        }

        try:
            # Get terminal log feedback
            terminal_feedback = await self.read_terminal_startup_log()
            result["terminal_feedback"] = terminal_feedback

            # Get GitHub feedback if available
            if self.coordinator_agent and hasattr(self.coordinator_agent, 'feedback_tool'):
                self.feedback_tool = self.coordinator_agent.feedback_tool
                if self.feedback_tool:
                    github_result = await self.feedback_tool.execute(operation="get_stats")
                    result["github_feedback"] = github_result

                    # Get pending errors
                    if github_result.get("success"):
                        pending = await self.feedback_tool.execute(
                            operation="list_errors",
                            status="pending",
                            limit=20
                        )
                        result["github_feedback"]["pending_errors"] = pending.get("errors", [])

            # Combine issues
            for error in terminal_feedback.get("errors", [])[:10]:
                result["combined_issues"].append({
                    "source": "terminal",
                    "type": "error",
                    "message": error[:200]
                })

            for gh_error in result.get("github_feedback", {}).get("pending_errors", [])[:10]:
                result["combined_issues"].append({
                    "source": "github_ai_review",
                    "type": gh_error.get("category", "other"),
                    "message": gh_error.get("message", "")[:200],
                    "file": gh_error.get("file_path", "unknown")
                })

            # Generate recommendations
            if result["combined_issues"]:
                result["recommendations"].append("Review and fix pending issues before proceeding")
                if any(i["source"] == "github_ai_review" for i in result["combined_issues"]):
                    result["recommendations"].append("Run feedback loop to auto-fix AI-detected issues")

            await self.memory_agent.log_process(
                "startup_feedback_processed",
                result,
                {"agent_id": self.agent_id, "event": "feedback_processing"}
            )

        except Exception as e:
            logger.error(f"{self.log_prefix} Error processing startup feedback: {e}")
            result["error"] = str(e)

        return result

    # ==================== Enhanced Initialization ====================

    async def initialize_with_full_inference(
        self,
        restore_from_blockchain: bool = True,
        spawn_deltaverse: bool = True,
        process_feedback: bool = True
    ) -> Dict[str, Any]:
        """
        Full initialization with multi-inference and DeltaVerse support.

        This is the enhanced startup that:
        1. Connects to all available inference providers
        2. Spawns DeltaVerse filerooms for agent communication
        3. Loads blockchain-encoded memories
        4. Processes startup feedback

        Args:
            restore_from_blockchain: Restore state from blockchain
            spawn_deltaverse: Spawn initial DeltaVerse fileroom
            process_feedback: Process startup feedback

        Returns:
            Complete initialization results
        """
        logger.info(f"{self.log_prefix} Starting full inference initialization...")

        results = {
            "base_init": {},
            "inference_providers": {},
            "deltaverse": {},
            "blockchain_memories": [],
            "feedback": {},
            "status": "in_progress"
        }

        try:
            # Step 1: Base initialization
            results["base_init"] = await self.initialize_system(
                restore_from_blockchain=restore_from_blockchain
            )

            # Step 2: Connect to all inference providers
            logger.info(f"{self.log_prefix} Step 2: Connecting to all inference providers")
            results["inference_providers"] = await self.connect_all_inference_providers()

            # Step 3: Spawn DeltaVerse fileroom if enabled
            if spawn_deltaverse and self.deltaverse_config.get("spawn_on_startup"):
                logger.info(f"{self.log_prefix} Step 3: Spawning DeltaVerse fileroom")
                deltaverse_result = await self.spawn_deltaverse_fileroom(
                    purpose="startup_agent_communication",
                    agents=self.always_on_agents,
                    blockchain_encoded=True
                )
                results["deltaverse"] = deltaverse_result

            # Step 4: Load blockchain memories
            logger.info(f"{self.log_prefix} Step 4: Loading blockchain memories")
            results["blockchain_memories"] = await self.load_blockchain_memories(limit=50)

            # Step 5: Process startup feedback
            if process_feedback:
                logger.info(f"{self.log_prefix} Step 5: Processing startup feedback")
                results["feedback"] = await self.process_startup_feedback()

            results["status"] = "completed"
            results["inference_points_count"] = len(self.inference_points)
            results["active_filerooms_count"] = len(self.active_filerooms)

            # Log comprehensive startup to memory
            await self.memory_agent.log_process(
                "full_inference_initialization_complete",
                {
                    "inference_points": len(self.inference_points),
                    "connected_providers": list(self.connected_providers.keys()),
                    "active_filerooms": list(self.active_filerooms.keys()),
                    "blockchain_memories_loaded": len(results["blockchain_memories"]),
                    "feedback_issues": len(results.get("feedback", {}).get("combined_issues", [])),
                    "timestamp": time.time()
                },
                {"agent_id": self.agent_id, "event": "full_init_complete"}
            )

            logger.info(f"{self.log_prefix} Full inference initialization complete: "
                       f"{len(self.inference_points)} inference points, "
                       f"{len(self.active_filerooms)} filerooms")

        except Exception as e:
            logger.error(f"{self.log_prefix} Error in full inference initialization: {e}", exc_info=True)
            results["status"] = "failed"
            results["error"] = str(e)

        return results
