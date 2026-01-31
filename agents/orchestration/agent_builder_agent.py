# mindx/orchestration/agent_builder_agent.py
"""
Agent Builder Agent: Builds new agents from participant prompts and agent requests.

This agent processes prompts/requests for new agent creation and uses AgentFactoryTool,
IDManagerAgent, and RegistryManagerTool to properly create and register new agents.
It notifies mindXagent when new agents are created so mindXagent can track them.
"""

from __future__ import annotations
import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, asdict

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.core.belief_system import BeliefSystem
from agents.memory_agent import MemoryAgent
from agents.core.id_manager_agent import IDManagerAgent
from agents.guardian_agent import GuardianAgent
from tools.registry.agent_factory_tool import AgentFactoryTool
from tools.registry.registry_manager_tool import RegistryManagerTool

logger = get_logger(__name__)

@dataclass
class AgentBuildRequest:
    """Request to build a new agent"""
    request_id: str
    source: str  # "participant_prompt" or "agent_request"
    prompt: str
    agent_type: Optional[str] = None
    agent_id: Optional[str] = None
    capabilities: List[str] = None
    roles: List[str] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.roles is None:
            self.roles = []
        if self.created_at is None:
            self.created_at = time.time()

@dataclass
class AgentBuildResult:
    """Result of building an agent"""
    request_id: str
    success: bool
    agent_id: Optional[str] = None
    agent_metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

class AgentBuilderAgent:
    """
    Agent Builder Agent - Builds new agents from prompts and requests.
    
    This agent processes participant prompts or agent requests, analyzes requirements,
    and creates new agents using AgentFactoryTool with proper identity and registry.
    """
    
    _instance: Optional['AgentBuilderAgent'] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls,
                          agent_id: str = "agent_builder",
                          config: Optional[Config] = None,
                          memory_agent: Optional[MemoryAgent] = None,
                          belief_system: Optional[BeliefSystem] = None,
                          coordinator_agent: Optional[Any] = None,
                          guardian_agent: Optional[GuardianAgent] = None,
                          mindx_agent: Optional[Any] = None,
                          test_mode: bool = False,
                          **kwargs) -> 'AgentBuilderAgent':
        """Singleton factory to get or create the Agent Builder Agent instance."""
        async with cls._lock:
            if cls._instance is None or test_mode:
                if test_mode and cls._instance is not None:
                    await cls._instance.shutdown()
                
                cls._instance = cls(
                    agent_id=agent_id,
                    config=config,
                    memory_agent=memory_agent,
                    belief_system=belief_system,
                    coordinator_agent=coordinator_agent,
                    guardian_agent=guardian_agent,
                    mindx_agent=mindx_agent,
                    test_mode=test_mode,
                    **kwargs
                )
                await cls._instance._async_init()
            return cls._instance
    
    def __init__(self,
                 agent_id: str = "agent_builder",
                 config: Optional[Config] = None,
                 memory_agent: Optional[MemoryAgent] = None,
                 belief_system: Optional[BeliefSystem] = None,
                 coordinator_agent: Optional[Any] = None,
                 guardian_agent: Optional[GuardianAgent] = None,
                 mindx_agent: Optional[Any] = None,
                 test_mode: bool = False,
                 **kwargs):
        """Initialize Agent Builder Agent"""
        self.agent_id = agent_id
        self.config = config or Config()
        self.test_mode = test_mode
        self.log_prefix = f"AgentBuilderAgent ({self.agent_id}):"
        
        # Core components
        self.belief_system = belief_system or BeliefSystem(test_mode=test_mode)
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.coordinator_agent = coordinator_agent
        self.guardian_agent = guardian_agent
        self.mindx_agent = mindx_agent  # Reference to mindXagent for notifications
        
        # Tools
        self.agent_factory_tool: Optional[AgentFactoryTool] = None
        self.registry_manager_tool: Optional[RegistryManagerTool] = None
        self.id_manager: Optional[IDManagerAgent] = None
        
        # Request tracking
        self.build_requests: Dict[str, AgentBuildRequest] = {}
        self.build_results: Dict[str, AgentBuildResult] = {}
        
        # Data directory
        self.data_dir = self.memory_agent.get_agent_data_directory(self.agent_id)
        self.requests_file = self.data_dir / "build_requests.json"
        self.results_file = self.data_dir / "build_results.json"
        
        # Status
        self.initialized = False
        
    async def _async_init(self):
        """Asynchronous initialization"""
        logger.info(f"{self.log_prefix} Initializing Agent Builder Agent...")
        
        try:
            # Initialize ID Manager
            self.id_manager = await IDManagerAgent.get_instance(
                agent_id=f"id_manager_for_{self.agent_id}",
                belief_system=self.belief_system,
                config_override=self.config,
                memory_agent=self.memory_agent
            )
            
            # Initialize Agent Factory Tool
            self.agent_factory_tool = AgentFactoryTool(
                memory_agent=self.memory_agent,
                coordinator_ref=self.coordinator_agent,
                guardian_ref=self.guardian_agent,
                config=self.config
            )
            
            # Initialize Registry Manager Tool
            self.registry_manager_tool = RegistryManagerTool(
                memory_agent=self.memory_agent,
                config=self.config
            )
            
            # Load previous requests and results
            await self._load_history()
            
            self.initialized = True
            logger.info(f"{self.log_prefix} Initialization complete")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Initialization failed: {e}", exc_info=True)
            raise
    
    async def _load_history(self):
        """Load previous build requests and results"""
        try:
            if self.requests_file.exists():
                with open(self.requests_file, 'r') as f:
                    data = json.load(f)
                    for req_id, req_data in data.items():
                        self.build_requests[req_id] = AgentBuildRequest(**req_data)
            
            if self.results_file.exists():
                with open(self.results_file, 'r') as f:
                    data = json.load(f)
                    for req_id, result_data in data.items():
                        self.build_results[req_id] = AgentBuildResult(**result_data)
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error loading history: {e}")
    
    async def _save_history(self):
        """Save build requests and results"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            requests_data = {req_id: asdict(req) for req_id, req in self.build_requests.items()}
            with open(self.requests_file, 'w') as f:
                json.dump(requests_data, f, indent=2, default=str)
            
            results_data = {req_id: asdict(result) for req_id, result in self.build_results.items()}
            with open(self.results_file, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"{self.log_prefix} Error saving history: {e}")
    
    async def build_agent_from_prompt(self,
                                      prompt: str,
                                      source: str = "participant_prompt",
                                      agent_type: Optional[str] = None) -> AgentBuildResult:
        """
        Build a new agent from a participant prompt or agent request.
        
        Args:
            prompt: Prompt describing the agent to create
            source: Source of the request ("participant_prompt" or "agent_request")
            agent_type: Optional agent type hint
            
        Returns:
            AgentBuildResult with creation status and metadata
        """
        logger.info(f"{self.log_prefix} Building agent from prompt: {prompt[:50]}...")
        
        request_id = str(uuid.uuid4())
        
        try:
            # Create build request
            build_request = AgentBuildRequest(
                request_id=request_id,
                source=source,
                prompt=prompt,
                agent_type=agent_type
            )
            
            # Analyze prompt to extract agent requirements
            agent_spec = await self._analyze_prompt(prompt, agent_type)
            
            # Generate agent ID if not provided
            agent_id = agent_spec.get("agent_id") or self._generate_agent_id(agent_spec)
            build_request.agent_id = agent_id
            build_request.agent_type = agent_spec.get("agent_type", "specialized")
            build_request.capabilities = agent_spec.get("capabilities", [])
            build_request.roles = agent_spec.get("roles", [])
            
            self.build_requests[request_id] = build_request
            
            # Create agent using AgentFactoryTool
            success, agent_metadata = await self.agent_factory_tool.execute(
                action="create_agent",
                agent_type=build_request.agent_type,
                agent_id=agent_id,
                agent_config={
                    "description": prompt,
                    "capabilities": build_request.capabilities,
                    "roles": build_request.roles,
                    "source": source,
                    "created_by": self.agent_id
                }
            )
            
            # Register agent in registry
            if success and agent_metadata:
                await self._register_agent_in_registry(agent_id, agent_metadata, agent_spec)
            
            # Create build result
            build_result = AgentBuildResult(
                request_id=request_id,
                success=success,
                agent_id=agent_id if success else None,
                agent_metadata=agent_metadata if success else None,
                error=None if success else str(agent_metadata) if isinstance(agent_metadata, str) else "Unknown error"
            )
            
            self.build_results[request_id] = build_result
            
            # Notify mindXagent about new agent
            if success and self.mindx_agent:
                await self._notify_mindx_agent(agent_id, agent_metadata, agent_spec)
            
            # Save history
            await self._save_history()
            
            logger.info(f"{self.log_prefix} Agent build {'succeeded' if success else 'failed'}: {agent_id}")
            return build_result
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error building agent: {e}", exc_info=True)
            build_result = AgentBuildResult(
                request_id=request_id,
                success=False,
                error=str(e)
            )
            self.build_results[request_id] = build_result
            return build_result
    
    async def _analyze_prompt(self, prompt: str, agent_type_hint: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze prompt to extract agent specifications.
        
        Args:
            prompt: Prompt text
            agent_type_hint: Optional hint about agent type
            
        Returns:
            Dictionary with agent specifications
        """
        # Simple analysis - in a full implementation, this would use LLM
        # For now, extract basic information
        
        prompt_lower = prompt.lower()
        
        # Determine agent type
        agent_type = agent_type_hint
        if not agent_type:
            if "orchestration" in prompt_lower or "coordinate" in prompt_lower:
                agent_type = "orchestration"
            elif "monitor" in prompt_lower or "track" in prompt_lower:
                agent_type = "monitoring"
            elif "learn" in prompt_lower or "improve" in prompt_lower:
                agent_type = "learning"
            elif "core" in prompt_lower or "foundation" in prompt_lower:
                agent_type = "core"
            else:
                agent_type = "specialized"
        
        # Extract capabilities keywords
        capabilities = []
        capability_keywords = {
            "analysis": "data_analysis",
            "code": "code_generation",
            "monitor": "monitoring",
            "coordinate": "coordination",
            "learn": "learning",
            "improve": "self_improvement",
            "security": "security_validation",
            "memory": "memory_management"
        }
        
        for keyword, capability in capability_keywords.items():
            if keyword in prompt_lower:
                capabilities.append(capability)
        
        # Extract roles
        roles = []
        if "agent" in prompt_lower:
            roles.append("agent")
        if "tool" in prompt_lower:
            roles.append("tool")
        
        return {
            "agent_type": agent_type,
            "capabilities": capabilities,
            "roles": roles,
            "description": prompt
        }
    
    def _generate_agent_id(self, agent_spec: Dict[str, Any]) -> str:
        """Generate a unique agent ID from specifications"""
        agent_type = agent_spec.get("agent_type", "agent")
        timestamp = int(time.time())
        random_suffix = uuid.uuid4().hex[:6]
        return f"{agent_type}_{timestamp}_{random_suffix}"
    
    async def _register_agent_in_registry(self,
                                         agent_id: str,
                                         agent_metadata: Dict[str, Any],
                                         agent_spec: Dict[str, Any]):
        """Register new agent in the official registry"""
        try:
            if not self.registry_manager_tool:
                return
            
            agent_config = {
                "id": agent_id,
                "name": agent_metadata.get("agent_id", agent_id),
                "type": agent_spec.get("agent_type", "specialized"),
                "description": agent_spec.get("description", ""),
                "capabilities": agent_spec.get("capabilities", []),
                "roles": agent_spec.get("roles", []),
                "module_path": agent_metadata.get("code_path", f"agents.{agent_id}"),
                "version": "1.0.0",
                "enabled": True,
                "identity": {
                    "public_key": agent_metadata.get("public_key"),
                    "signature": None
                },
                "created_at": time.time(),
                "created_by": self.agent_id
            }
            
            success, result = await self.registry_manager_tool.execute(
                registry_type="agent",
                action="add",
                item_id=agent_id,
                item_config=agent_config
            )
            
            if success:
                logger.info(f"{self.log_prefix} Registered agent {agent_id} in registry")
            else:
                logger.warning(f"{self.log_prefix} Failed to register agent {agent_id}: {result}")
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Error registering agent in registry: {e}")
    
    async def _notify_mindx_agent(self,
                                  agent_id: str,
                                  agent_metadata: Dict[str, Any],
                                  agent_spec: Dict[str, Any]):
        """Notify mindXagent about newly created agent"""
        try:
            if self.mindx_agent and hasattr(self.mindx_agent, '_notify_agent_created'):
                agent_info = {
                    "agent_id": agent_id,
                    "agent_type": agent_spec.get("agent_type", "specialized"),
                    "location": agent_metadata.get("code_path", ""),
                    "capabilities": agent_spec.get("capabilities", []),
                    "roles": agent_spec.get("roles", []),
                    "powers": {},
                    "identity": {
                        "public_key": agent_metadata.get("public_key")
                    },
                    "registry_info": {
                        "registered": True,
                        "registry_path": "data/config/official_agents_registry.json"
                    }
                }
                self.mindx_agent._notify_agent_created(agent_info)
                logger.info(f"{self.log_prefix} Notified mindXagent about new agent: {agent_id}")
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error notifying mindXagent: {e}")
    
    async def shutdown(self):
        """Shutdown Agent Builder Agent"""
        logger.info(f"{self.log_prefix} Shutting down...")
        await self._save_history()
        logger.info(f"{self.log_prefix} Shutdown complete")
