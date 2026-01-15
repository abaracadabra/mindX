# mindx/orchestration/mindXagent.py
"""
MindX Agent: The Execution Mind of the Gödel Machine

The MindX Agent serves as the meta-agent that understands all agents' roles, capabilities, and powers.
It orchestrates self-improvement of mindX through SEA, BDI, Mastermind, and all other agents.
It is subservient to higher intelligence and acts as the execution mind of the Gödel machine.

Key Responsibilities:
- Understand all agents and their capabilities
- Track registered agents via Registry Manager Tool
- Track agent identities via ID Manager Agent
- Monitor newly created agents from Agent Builder Agent
- Orchestrate self-improvement campaigns
- Use memory feedback and actual results for continuous improvement
"""

from __future__ import annotations
import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.core.belief_system import BeliefSystem, BeliefSource
from agents.memory_agent import MemoryAgent
from agents.core.id_manager_agent import IDManagerAgent

logger = get_logger(__name__)

class AgentStatus(Enum):
    """Status of an agent in the system"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    UNKNOWN = "UNKNOWN"
    CREATING = "CREATING"
    FAILED = "FAILED"

class AgentType(Enum):
    """Types of agents in the system"""
    ORCHESTRATION = "orchestration"
    CORE = "core"
    LEARNING = "learning"
    MONITORING = "monitoring"
    SPECIALIZED = "specialized"
    EVOLUTION = "evolution"

@dataclass
class AgentKnowledge:
    """Comprehensive knowledge about an agent"""
    agent_id: str
    agent_type: str  # orchestration, core, learning, monitoring, specialized
    location: str  # file path
    capabilities: List[str] = field(default_factory=list)
    roles: List[str] = field(default_factory=list)
    powers: Dict[str, Any] = field(default_factory=dict)  # What it can do, limits, dependencies
    integration_points: List[str] = field(default_factory=list)  # Other agents it interacts with
    documentation: Dict[str, Any] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.UNKNOWN
    identity: Optional[Dict[str, Any]] = None  # Cryptographic identity
    registry_info: Optional[Dict[str, Any]] = None  # Registry information
    created_at: Optional[float] = None
    last_updated: Optional[float] = None
    performance_metrics: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AgentCapabilities:
    """Detailed capabilities of an agent"""
    agent_id: str
    primary_capabilities: List[str]
    secondary_capabilities: List[str]
    limitations: List[str]
    dependencies: List[str]
    integration_methods: List[str]
    performance_characteristics: Dict[str, Any]

@dataclass
class MemoryContext:
    """Context from memory agent and data folder"""
    memories: List[Dict[str, Any]]
    system_state: Dict[str, Any]
    improvement_history: List[Dict[str, Any]]
    lessons_learned: List[str]
    data_folder_state: Dict[str, Any]

@dataclass
class ResultAnalysis:
    """Analysis of actual results vs expected outcomes"""
    task_id: str
    expected_outcomes: Dict[str, Any]
    actual_results: Dict[str, Any]
    variance: Dict[str, Any]
    success_metrics: Dict[str, float]
    improvement_opportunities: List[str]

@dataclass
class ImprovementResult:
    """Result of a self-improvement orchestration"""
    goal: str
    success: bool
    agents_used: List[str]
    improvements_made: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    feedback: Dict[str, Any]
    next_steps: List[str]

class MindXAgent:
    """
    The MindX Agent - Meta-agent that understands all agents and orchestrates self-improvement.
    
    This agent serves as the execution mind of the Gödel machine, subservient to higher intelligence.
    It maintains comprehensive knowledge of all agents and uses them to continuously improve mindX.
    """
    
    _instance: Optional['MindXAgent'] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_instance(cls,
                          agent_id: str = "mindx_meta_agent",
                          config: Optional[Config] = None,
                          memory_agent: Optional[MemoryAgent] = None,
                          belief_system: Optional[BeliefSystem] = None,
                          test_mode: bool = False,
                          **kwargs) -> 'MindXAgent':
        """Singleton factory to get or create the MindX Agent instance."""
        async with cls._lock:
            if cls._instance is None or test_mode:
                if test_mode and cls._instance is not None:
                    await cls._instance.shutdown()
                
                cls._instance = cls(
                    agent_id=agent_id,
                    config=config,
                    memory_agent=memory_agent,
                    belief_system=belief_system,
                    test_mode=test_mode,
                    **kwargs
                )
                await cls._instance._async_init()
            return cls._instance
    
    def __init__(self,
                 agent_id: str = "mindx_meta_agent",
                 config: Optional[Config] = None,
                 memory_agent: Optional[MemoryAgent] = None,
                 belief_system: Optional[BeliefSystem] = None,
                 test_mode: bool = False,
                 **kwargs):
        """Initialize MindX Agent"""
        self.agent_id = agent_id
        self.config = config or Config()
        self.test_mode = test_mode
        self.log_prefix = f"MindXAgent ({self.agent_id}):"
        
        # Core components
        self.belief_system = belief_system or BeliefSystem(test_mode=test_mode)
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.id_manager: Optional[IDManagerAgent] = None
        
        # Agent knowledge base
        self.agent_knowledge: Dict[str, AgentKnowledge] = {}
        self.agent_capabilities: Dict[str, AgentCapabilities] = {}
        self.agent_relationship_graph: Dict[str, List[str]] = {}  # agent_id -> [connected_agent_ids]
        
        # Registry and identity tracking
        self.registry_manager_tool: Optional[Any] = None
        self.registered_agents: Dict[str, Dict[str, Any]] = {}
        self.agent_identities: Dict[str, Dict[str, Any]] = {}
        
        # Agent builder integration
        self.agent_builder_agent: Optional[Any] = None
        self.new_agents_queue: List[Dict[str, Any]] = []
        self.agent_creation_subscriptions: List[callable] = []
        
        # Integration with other agents
        self.strategic_evolution_agent: Optional[Any] = None
        self.bdi_agent: Optional[Any] = None
        self.mastermind_agent: Optional[Any] = None
        self.coordinator_agent: Optional[Any] = None
        self.ceo_agent: Optional[Any] = None
        
        # Monitoring agents
        self.performance_monitor: Optional[Any] = None
        self.resource_monitor: Optional[Any] = None
        self.error_recovery_coordinator: Optional[Any] = None
        
        # Improvement tracking
        self.improvement_goals: List[Dict[str, Any]] = []
        self.improvement_history: List[Dict[str, Any]] = []
        self.result_analyses: Dict[str, ResultAnalysis] = {}
        
        # Data directory
        self.data_dir = self.memory_agent.get_agent_data_directory(self.agent_id)
        self.knowledge_base_file = self.data_dir / "agent_knowledge_base.json"
        self.improvement_history_file = self.data_dir / "improvement_history.json"
        
        # Status
        self.initialized = False
        self.running = False
        
    async def _async_init(self):
        """Asynchronous initialization of all components"""
        logger.info(f"{self.log_prefix} Initializing MindX Agent...")
        
        try:
            # Initialize ID Manager Agent
            self.id_manager = await IDManagerAgent.get_instance(
                agent_id=f"id_manager_for_{self.agent_id}",
                belief_system=self.belief_system,
                config_override=self.config,
                memory_agent=self.memory_agent
            )
            
            # Initialize Registry Manager Tool
            await self._init_registry_manager()
            
            # Initialize agent integrations
            await self._init_agent_integrations()
            
            # Initialize agent builder agent
            await self._init_agent_builder()
            
            # Initialize monitoring agents
            await self._init_monitoring_agents()
            
            # Load existing knowledge base if available
            await self._load_knowledge_base()
            
            # Build initial knowledge base
            await self.understand_all_agents()
            
            self.initialized = True
            logger.info(f"{self.log_prefix} Initialization complete")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Initialization failed: {e}", exc_info=True)
            raise
    
    async def _init_registry_manager(self):
        """Initialize Registry Manager Tool"""
        try:
            from tools.registry_manager_tool import RegistryManagerTool
            self.registry_manager_tool = RegistryManagerTool(
                memory_agent=self.memory_agent,
                config=self.config
            )
            logger.info(f"{self.log_prefix} Registry Manager Tool initialized")
        except Exception as e:
            logger.warning(f"{self.log_prefix} Could not initialize Registry Manager Tool: {e}")
    
    async def _init_agent_integrations(self):
        """Initialize integrations with other agents"""
        try:
            # Initialize StrategicEvolutionAgent
            try:
                from agents.learning.strategic_evolution_agent import StrategicEvolutionAgent
                from agents.orchestration.coordinator_agent import CoordinatorAgent
                from agents.orchestration.mastermind_agent import MastermindAgent
                
                # Get coordinator first (needed by others)
                self.coordinator_agent = await CoordinatorAgent.get_instance(
                    memory_agent=self.memory_agent,
                    config=self.config,
                    test_mode=self.test_mode
                )
                
                # Get mastermind
                self.mastermind_agent = await MastermindAgent.get_instance(
                    agent_id="mastermind_prime",
                    config_override=self.config,
                    coordinator_agent_instance=self.coordinator_agent,
                    memory_agent=self.memory_agent,
                    test_mode=self.test_mode
                )
                
                # Get BDI agent from mastermind
                if self.mastermind_agent and hasattr(self.mastermind_agent, 'bdi_agent'):
                    self.bdi_agent = self.mastermind_agent.bdi_agent
                
                # Initialize StrategicEvolutionAgent
                if self.coordinator_agent and self.mastermind_agent:
                    self.strategic_evolution_agent = StrategicEvolutionAgent(
                        coordinator_agent=self.coordinator_agent,
                        mastermind_agent=self.mastermind_agent,
                        config=self.config
                    )
                
                logger.info(f"{self.log_prefix} Agent integrations initialized")
            except Exception as e:
                logger.warning(f"{self.log_prefix} Could not initialize some agent integrations: {e}")
            
            # Initialize CEO Agent (optional)
            try:
                from agents.orchestration.ceo_agent import CEOAgent
                self.ceo_agent = CEOAgent(
                    config=self.config,
                    belief_system=self.belief_system,
                    memory_agent=self.memory_agent
                )
            except Exception as e:
                logger.debug(f"{self.log_prefix} CEO Agent not available: {e}")
            
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error initializing agent integrations: {e}")
    
    async def _init_agent_builder(self):
        """Initialize Agent Builder Agent"""
        try:
            from agents.orchestration.agent_builder_agent import AgentBuilderAgent
            from agents.guardian_agent import GuardianAgent
            
            # Get guardian agent if available
            guardian = None
            try:
                guardian = await GuardianAgent.get_instance(
                    id_manager=self.id_manager,
                    memory_agent=self.memory_agent,
                    config=self.config
                )
            except Exception as e:
                logger.debug(f"{self.log_prefix} Guardian Agent not available: {e}")
            
            # Initialize Agent Builder Agent with reference to self (mindXagent)
            self.agent_builder_agent = await AgentBuilderAgent.get_instance(
                agent_id="agent_builder",
                config=self.config,
                memory_agent=self.memory_agent,
                belief_system=self.belief_system,
                coordinator_agent=self.coordinator_agent,
                guardian_agent=guardian,
                mindx_agent=self,  # Pass self so agent_builder can notify us
                test_mode=self.test_mode
            )
            
            # The agent_builder_agent already has reference to mindXagent (self)
            # It will call _notify_agent_created directly when agents are created
            
            logger.info(f"{self.log_prefix} Agent Builder Agent initialized")
        except Exception as e:
            logger.warning(f"{self.log_prefix} Could not initialize Agent Builder Agent: {e}")
    
    def _on_agent_created(self, agent_info: Dict[str, Any]):
        """Callback when agent_builder_agent creates a new agent"""
        self._notify_agent_created(agent_info)
    
    async def _init_monitoring_agents(self):
        """Initialize monitoring agents"""
        try:
            # Initialize Performance Monitor
            try:
                from agents.monitoring.performance_monitor import get_performance_monitor_async
                self.performance_monitor = await get_performance_monitor_async()
            except Exception as e:
                logger.debug(f"{self.log_prefix} Performance Monitor not available: {e}")
            
            # Initialize Resource Monitor
            try:
                from agents.monitoring.resource_monitor import get_resource_monitor_async
                self.resource_monitor = await get_resource_monitor_async()
            except Exception as e:
                logger.debug(f"{self.log_prefix} Resource Monitor not available: {e}")
            
            # Initialize Error Recovery Coordinator
            try:
                from agents.monitoring.error_recovery_coordinator import ErrorRecoveryCoordinator
                self.error_recovery_coordinator = ErrorRecoveryCoordinator(
                    memory_agent=self.memory_agent,
                    config=self.config
                )
            except Exception as e:
                logger.debug(f"{self.log_prefix} Error Recovery Coordinator not available: {e}")
            
            logger.info(f"{self.log_prefix} Monitoring agents initialized")
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error initializing monitoring agents: {e}")
    
    async def load_registered_agents(self) -> Dict[str, AgentKnowledge]:
        """
        Load all registered agents from registry_manager_tool and official registry.
        
        Returns:
            Dictionary mapping agent_id to AgentKnowledge
        """
        logger.info(f"{self.log_prefix} Loading registered agents from registry...")
        
        registered_agents = {}
        
        try:
            # Load from official agents registry file
            agent_registry_path = Path(self.config.get(
                "mastermind_agent.agents_registry_path",
                "data/config/official_agents_registry.json"
            ))
            
            if agent_registry_path.exists():
                with open(agent_registry_path, 'r') as f:
                    registry_data = json.load(f)
                    agents = registry_data.get("registered_agents", {})
                    
                    for agent_id, agent_config in agents.items():
                        # Create AgentKnowledge from registry entry
                        agent_knowledge = AgentKnowledge(
                            agent_id=agent_id,
                            agent_type=agent_config.get("type", "specialized"),
                            location=agent_config.get("module_path", ""),
                            capabilities=agent_config.get("capabilities", []),
                            roles=agent_config.get("roles", []),
                            powers={
                                "access_control": agent_config.get("access_control", {}),
                                "enabled": agent_config.get("enabled", True),
                                "version": agent_config.get("version", "1.0.0")
                            },
                            documentation=agent_config.get("documentation", {}),
                            status=AgentStatus.ACTIVE if agent_config.get("enabled", True) else AgentStatus.INACTIVE,
                            identity=agent_config.get("identity", {}),
                            registry_info=agent_config,
                            created_at=agent_config.get("created_at"),
                            last_updated=agent_config.get("last_updated_at")
                        )
                        registered_agents[agent_id] = agent_knowledge
                        self.registered_agents[agent_id] = agent_config
            
            # Also use registry_manager_tool if available
            if self.registry_manager_tool:
                # The registry_manager_tool loads from the same file, but we can use it for updates
                pass
            
            logger.info(f"{self.log_prefix} Loaded {len(registered_agents)} registered agents")
            return registered_agents
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error loading registered agents: {e}", exc_info=True)
            return registered_agents
    
    async def _load_knowledge_base(self):
        """Load existing knowledge base from disk"""
        try:
            if self.knowledge_base_file.exists():
                with open(self.knowledge_base_file, 'r') as f:
                    data = json.load(f)
                    # Reconstruct agent knowledge from saved data
                    for agent_id, agent_data in data.get("agents", {}).items():
                        self.agent_knowledge[agent_id] = AgentKnowledge(**agent_data)
                logger.info(f"{self.log_prefix} Loaded knowledge base with {len(self.agent_knowledge)} agents")
        except Exception as e:
            logger.warning(f"{self.log_prefix} Could not load knowledge base: {e}")
    
    async def _save_knowledge_base(self):
        """Save knowledge base to disk"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            data = {
                "agents": {agent_id: asdict(knowledge) for agent_id, knowledge in self.agent_knowledge.items()},
                "last_updated": time.time()
            }
            with open(self.knowledge_base_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"{self.log_prefix} Could not save knowledge base: {e}")
    
    async def track_agent_identities(self) -> Dict[str, Dict[str, Any]]:
        """
        Track agent identities using IDManagerAgent and identity tools.
        
        Returns:
            Dictionary mapping agent_id to identity information
        """
        logger.info(f"{self.log_prefix} Tracking agent identities...")
        
        agent_identities = {}
        
        try:
            if not self.id_manager:
                logger.warning(f"{self.log_prefix} ID Manager not initialized")
                return agent_identities
            
            # Get identities from belief system (fast lookup)
            for agent_id in self.agent_knowledge.keys():
                try:
                    # Check belief system for identity mapping
                    belief_key = f"identity.map.entity_to_address.{agent_id}"
                    # Note: BeliefSystem doesn't have async get_belief, so we'll use a different approach
                    # For now, we'll track identities from registry info
                    if agent_id in self.agent_knowledge:
                        knowledge = self.agent_knowledge[agent_id]
                        if knowledge.identity:
                            agent_identities[agent_id] = knowledge.identity
                except Exception as e:
                    logger.debug(f"{self.log_prefix} Could not get identity for {agent_id}: {e}")
            
            # Also check identity sync tool if available
            try:
                from tools.identity_sync_tool import IdentitySyncTool
                identity_sync = IdentitySyncTool(memory_agent=self.memory_agent, config=self.config)
                # Identity sync tool can provide additional identity information
            except ImportError:
                pass
            
            self.agent_identities = agent_identities
            logger.info(f"{self.log_prefix} Tracked {len(agent_identities)} agent identities")
            return agent_identities
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error tracking agent identities: {e}", exc_info=True)
            return agent_identities
    
    async def discover_agents_from_filesystem(self) -> Dict[str, AgentKnowledge]:
        """
        Discover agents by scanning the filesystem for agent files.
        
        Returns:
            Dictionary mapping agent_id to AgentKnowledge
        """
        logger.info(f"{self.log_prefix} Discovering agents from filesystem...")
        
        discovered_agents = {}
        agents_dir = PROJECT_ROOT / "agents"
        
        try:
            # Scan agents directory
            agent_files = []
            
            # Core agents
            core_dir = agents_dir / "core"
            if core_dir.exists():
                for py_file in core_dir.glob("*.py"):
                    if py_file.name != "__init__.py":
                        agent_files.append(("core", py_file))
            
            # Orchestration agents
            orchestration_dir = agents_dir / "orchestration"
            if orchestration_dir.exists():
                for py_file in orchestration_dir.glob("*.py"):
                    if py_file.name != "__init__.py":
                        agent_files.append(("orchestration", py_file))
            
            # Learning agents
            learning_dir = agents_dir / "learning"
            if learning_dir.exists():
                for py_file in learning_dir.glob("*.py"):
                    if py_file.name != "__init__.py":
                        agent_files.append(("learning", py_file))
            
            # Monitoring agents
            monitoring_dir = agents_dir / "monitoring"
            if monitoring_dir.exists():
                for py_file in monitoring_dir.glob("*.py"):
                    if py_file.name != "__init__.py":
                        agent_files.append(("monitoring", py_file))
            
            # Evolution agents
            evolution_dir = agents_dir / "evolution"
            if evolution_dir.exists():
                for py_file in evolution_dir.glob("*.py"):
                    if py_file.name != "__init__.py":
                        agent_files.append(("evolution", py_file))
            
            # Root level agents
            for py_file in agents_dir.glob("*.py"):
                if py_file.name != "__init__.py":
                    agent_files.append(("specialized", py_file))
            
            # Process each agent file
            for agent_type, agent_file in agent_files:
                agent_id = agent_file.stem
                
                # Skip if already in knowledge base
                if agent_id in self.agent_knowledge:
                    continue
                
                # Create basic knowledge entry
                agent_knowledge = AgentKnowledge(
                    agent_id=agent_id,
                    agent_type=agent_type,
                    location=str(agent_file.relative_to(PROJECT_ROOT)),
                    status=AgentStatus.UNKNOWN,
                    created_at=agent_file.stat().st_mtime if agent_file.exists() else None
                )
                
                discovered_agents[agent_id] = agent_knowledge
            
            logger.info(f"{self.log_prefix} Discovered {len(discovered_agents)} agents from filesystem")
            return discovered_agents
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error discovering agents from filesystem: {e}", exc_info=True)
            return discovered_agents
    
    async def understand_all_agents(self) -> Dict[str, AgentKnowledge]:
        """
        Build comprehensive knowledge base of all agents (registered + discovered + new).
        
        Returns:
            Dictionary mapping agent_id to AgentKnowledge
        """
        logger.info(f"{self.log_prefix} Building comprehensive agent knowledge base...")
        
        # Load registered agents
        registered = await self.load_registered_agents()
        
        # Discover agents from filesystem
        discovered = await self.discover_agents_from_filesystem()
        
        # Track identities
        await self.track_agent_identities()
        
        # Merge all agents into knowledge base
        all_agents = {}
        
        # Start with registered agents (most complete info)
        for agent_id, knowledge in registered.items():
            all_agents[agent_id] = knowledge
            self.agent_knowledge[agent_id] = knowledge
        
        # Add discovered agents (fill in gaps)
        for agent_id, knowledge in discovered.items():
            if agent_id not in all_agents:
                all_agents[agent_id] = knowledge
                self.agent_knowledge[agent_id] = knowledge
            else:
                # Merge information
                existing = all_agents[agent_id]
                if not existing.location and knowledge.location:
                    existing.location = knowledge.location
                if not existing.agent_type and knowledge.agent_type:
                    existing.agent_type = knowledge.agent_type
        
        # Load documentation for each agent
        await self._load_agent_documentation()
        
        # Save knowledge base
        await self._save_knowledge_base()
        
        logger.info(f"{self.log_prefix} Knowledge base built with {len(all_agents)} agents")
        return all_agents
    
    async def _load_agent_documentation(self):
        """Load documentation for agents from docs/ folder"""
        try:
            docs_dir = PROJECT_ROOT / "docs"
            agents_index = PROJECT_ROOT / "agents" / "index.md"
            
            # Load agents/index.md for metadata
            if agents_index.exists():
                # Parse index.md to get agent documentation links
                # This is a simplified version - full parsing would be more complex
                pass
            
            # For each agent, try to load its documentation
            for agent_id, knowledge in self.agent_knowledge.items():
                doc_file = docs_dir / f"{agent_id}.md"
                if not doc_file.exists():
                    # Try alternative naming
                    doc_file = docs_dir / f"{agent_id}_agent.md"
                
                if doc_file.exists():
                    # Store documentation path
                    knowledge.documentation["path"] = str(doc_file.relative_to(PROJECT_ROOT))
                    knowledge.documentation["exists"] = True
                else:
                    knowledge.documentation["exists"] = False
                    
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error loading agent documentation: {e}")
    
    async def monitor_new_agents(self) -> List[AgentKnowledge]:
        """
        Monitor agent_builder_agent for newly created agents and track their capabilities.
        
        Returns:
            List of newly discovered AgentKnowledge objects
        """
        logger.info(f"{self.log_prefix} Monitoring for new agents...")
        
        new_agents = []
        
        try:
            # Check if agent_builder_agent exists and has created new agents
            # This will be implemented when agent_builder_agent is created
            # For now, check the new_agents_queue
            
            while self.new_agents_queue:
                new_agent_info = self.new_agents_queue.pop(0)
                agent_id = new_agent_info.get("agent_id")
                
                if agent_id and agent_id not in self.agent_knowledge:
                    # Create AgentKnowledge for new agent
                    agent_knowledge = AgentKnowledge(
                        agent_id=agent_id,
                        agent_type=new_agent_info.get("agent_type", "specialized"),
                        location=new_agent_info.get("location", ""),
                        capabilities=new_agent_info.get("capabilities", []),
                        roles=new_agent_info.get("roles", []),
                        powers=new_agent_info.get("powers", {}),
                        status=AgentStatus.CREATING,
                        identity=new_agent_info.get("identity"),
                        registry_info=new_agent_info.get("registry_info"),
                        created_at=time.time()
                    )
                    
                    # Analyze capabilities
                    await self.analyze_agent_capabilities(agent_id)
                    
                    # Add to knowledge base
                    self.agent_knowledge[agent_id] = agent_knowledge
                    new_agents.append(agent_knowledge)
                    
                    logger.info(f"{self.log_prefix} Tracked new agent: {agent_id}")
            
            # Subscribe to agent_builder_agent events if available
            # This will be implemented when agent_builder_agent is created
            
            return new_agents
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error monitoring new agents: {e}", exc_info=True)
            return new_agents
    
    def subscribe_to_agent_creation(self, callback: callable):
        """Subscribe to agent creation events"""
        self.agent_creation_subscriptions.append(callback)
    
    def _notify_agent_created(self, agent_info: Dict[str, Any]):
        """Notify subscribers about new agent creation"""
        self.new_agents_queue.append(agent_info)
        for callback in self.agent_creation_subscriptions:
            try:
                callback(agent_info)
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in agent creation callback: {e}")
    
    async def analyze_agent_capabilities(self, agent_id: str) -> AgentCapabilities:
        """
        Deep analysis of a specific agent's capabilities.
        
        Args:
            agent_id: ID of the agent to analyze
            
        Returns:
            AgentCapabilities object with detailed capability information
        """
        logger.info(f"{self.log_prefix} Analyzing capabilities for agent: {agent_id}")
        
        try:
            knowledge = self.agent_knowledge.get(agent_id)
            if not knowledge:
                logger.warning(f"{self.log_prefix} Agent {agent_id} not in knowledge base")
                return AgentCapabilities(
                    agent_id=agent_id,
                    primary_capabilities=[],
                    secondary_capabilities=[],
                    limitations=[],
                    dependencies=[],
                    integration_methods=[],
                    performance_characteristics={}
                )
            
            # Analyze based on agent type and location
            primary_capabilities = knowledge.capabilities.copy()
            secondary_capabilities = []
            limitations = []
            dependencies = []
            integration_methods = []
            
            # Determine capabilities based on agent type
            if knowledge.agent_type == "orchestration":
                primary_capabilities.extend(["orchestration", "coordination", "strategic_planning"])
            elif knowledge.agent_type == "core":
                primary_capabilities.extend(["core_functionality", "system_foundation"])
            elif knowledge.agent_type == "learning":
                primary_capabilities.extend(["learning", "adaptation", "self_improvement"])
            elif knowledge.agent_type == "monitoring":
                primary_capabilities.extend(["monitoring", "health_tracking", "metrics"])
            
            # Extract dependencies from integration points
            dependencies = knowledge.integration_points.copy()
            
            # Determine integration methods
            if knowledge.registry_info:
                integration_methods.append("registry")
            if knowledge.identity:
                integration_methods.append("identity")
            if knowledge.documentation.get("exists"):
                integration_methods.append("documentation")
            
            capabilities = AgentCapabilities(
                agent_id=agent_id,
                primary_capabilities=primary_capabilities,
                secondary_capabilities=secondary_capabilities,
                limitations=limitations,
                dependencies=dependencies,
                integration_methods=integration_methods,
                performance_characteristics=knowledge.performance_metrics
            )
            
            self.agent_capabilities[agent_id] = capabilities
            return capabilities
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error analyzing capabilities for {agent_id}: {e}", exc_info=True)
            return AgentCapabilities(
                agent_id=agent_id,
                primary_capabilities=[],
                secondary_capabilities=[],
                limitations=[],
                dependencies=[],
                integration_methods=[],
                performance_characteristics={}
            )
    
    async def get_memory_feedback(self, context: str) -> MemoryContext:
        """
        Get feedback and context from Memory Agent and data/ folder.
        
        Args:
            context: Context string to search for in memories
            
        Returns:
            MemoryContext with memories, system state, and improvement history
        """
        logger.info(f"{self.log_prefix} Getting memory feedback for context: {context[:50]}...")
        
        try:
            memories = []
            system_state = {}
            improvement_history = []
            lessons_learned = []
            data_folder_state = {}
            
            # Query Memory Agent
            if self.memory_agent:
                # Search memories related to context
                # This is a simplified version - full implementation would use memory search
                try:
                    # Get agent's memory directory
                    agent_memories_dir = self.memory_agent.get_agent_data_directory(self.agent_id)
                    if agent_memories_dir.exists():
                        # Load recent memories
                        # In a full implementation, we'd search memory by context
                        pass
                except Exception as e:
                    logger.debug(f"{self.log_prefix} Error querying memory agent: {e}")
            
            # Load improvement history
            if self.improvement_history_file.exists():
                try:
                    with open(self.improvement_history_file, 'r') as f:
                        improvement_history = json.load(f)
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error loading improvement history: {e}")
            
            # Get data folder state
            data_dir = PROJECT_ROOT / "data"
            if data_dir.exists():
                data_folder_state = {
                    "exists": True,
                    "memory_dir": str(data_dir / "memory"),
                    "config_dir": str(data_dir / "config"),
                    "agent_workspaces": []
                }
                
                # List agent workspaces
                workspaces_dir = data_dir / "agent_workspaces"
                if workspaces_dir.exists():
                    data_folder_state["agent_workspaces"] = [
                        d.name for d in workspaces_dir.iterdir() if d.is_dir()
                    ]
            
            return MemoryContext(
                memories=memories,
                system_state=system_state,
                improvement_history=improvement_history,
                lessons_learned=lessons_learned,
                data_folder_state=data_folder_state
            )
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error getting memory feedback: {e}", exc_info=True)
            return MemoryContext(
                memories=[],
                system_state={},
                improvement_history=[],
                lessons_learned=[],
                data_folder_state={}
            )
    
    async def analyze_actual_results(self, task_id: str) -> ResultAnalysis:
        """
        Analyze actual results vs expected outcomes from monitoring and memory.
        
        Args:
            task_id: ID of the task to analyze
            
        Returns:
            ResultAnalysis with variance and improvement opportunities
        """
        logger.info(f"{self.log_prefix} Analyzing results for task: {task_id}")
        
        try:
            # Get expected outcomes from task history
            expected_outcomes = {}
            actual_results = {}
            
            # Query monitoring agents for actual results
            if self.performance_monitor:
                try:
                    perf_metrics = await self.performance_monitor.get_metrics()
                    actual_results["performance"] = perf_metrics
                except Exception as e:
                    logger.debug(f"{self.log_prefix} Error getting performance metrics: {e}")
            
            if self.resource_monitor:
                try:
                    resource_metrics = await self.resource_monitor.get_current_metrics()
                    actual_results["resources"] = resource_metrics
                except Exception as e:
                    logger.debug(f"{self.log_prefix} Error getting resource metrics: {e}")
            
            # Calculate variance
            variance = {}
            for key in set(list(expected_outcomes.keys()) + list(actual_results.keys())):
                expected = expected_outcomes.get(key, 0)
                actual = actual_results.get(key, 0)
                if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                    variance[key] = actual - expected
            
            # Calculate success metrics
            success_metrics = {
                "overall_success_rate": 0.0,
                "performance_match": 0.0,
                "resource_efficiency": 0.0
            }
            
            # Identify improvement opportunities
            improvement_opportunities = []
            for key, var in variance.items():
                if abs(var) > 0.1:  # Significant variance
                    if var > 0:
                        improvement_opportunities.append(f"{key} exceeded expectations by {var}")
                    else:
                        improvement_opportunities.append(f"{key} fell short by {abs(var)}")
            
            analysis = ResultAnalysis(
                task_id=task_id,
                expected_outcomes=expected_outcomes,
                actual_results=actual_results,
                variance=variance,
                success_metrics=success_metrics,
                improvement_opportunities=improvement_opportunities
            )
            
            self.result_analyses[task_id] = analysis
            return analysis
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error analyzing results: {e}", exc_info=True)
            return ResultAnalysis(
                task_id=task_id,
                expected_outcomes={},
                actual_results={},
                variance={},
                success_metrics={},
                improvement_opportunities=[]
            )
    
    async def orchestrate_self_improvement(self, improvement_goal: str) -> ImprovementResult:
        """
        Orchestrate self-improvement using appropriate agents with feedback loop.
        
        Args:
            improvement_goal: Description of the improvement goal
            
        Returns:
            ImprovementResult with success status and improvements made
        """
        logger.info(f"{self.log_prefix} Orchestrating self-improvement: {improvement_goal[:50]}...")
        
        task_id = str(uuid.uuid4())
        agents_used = []
        improvements_made = []
        
        try:
            # Get memory feedback for context
            memory_context = await self.get_memory_feedback(improvement_goal)
            
            # Select appropriate agents for the improvement task
            selected_agents = await self.select_agents_for_task({
                "type": "self_improvement",
                "goal": improvement_goal,
                "context": memory_context
            })
            agents_used = selected_agents
            
            # Use StrategicEvolutionAgent for campaign creation
            if self.strategic_evolution_agent and "strategic_evolution_agent" in selected_agents:
                try:
                    campaign_result = await self.strategic_evolution_agent.create_improvement_campaign(
                        goal_description=improvement_goal,
                        priority="high"
                    )
                    if campaign_result:
                        improvements_made.append({
                            "type": "campaign",
                            "agent": "strategic_evolution_agent",
                            "result": campaign_result
                        })
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error using StrategicEvolutionAgent: {e}")
            
            # Use BDI Agent for goal planning
            if self.bdi_agent and "bdi_agent" in selected_agents:
                try:
                    bdi_result = await self.bdi_agent.add_goal(
                        goal_description=improvement_goal,
                        priority=1
                    )
                    if bdi_result:
                        improvements_made.append({
                            "type": "goal",
                            "agent": "bdi_agent",
                            "result": bdi_result
                        })
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error using BDI Agent: {e}")
            
            # Use Mastermind for strategic coordination
            if self.mastermind_agent and "mastermind_agent" in selected_agents:
                try:
                    # Mastermind coordination would go here
                    improvements_made.append({
                        "type": "coordination",
                        "agent": "mastermind_agent",
                        "result": "coordinated"
                    })
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error using Mastermind Agent: {e}")
            
            # Analyze results
            result_analysis = await self.analyze_actual_results(task_id)
            
            # Determine success
            success = len(improvements_made) > 0
            
            # Get next steps from analysis
            next_steps = result_analysis.improvement_opportunities.copy()
            
            result = ImprovementResult(
                goal=improvement_goal,
                success=success,
                agents_used=agents_used,
                improvements_made=improvements_made,
                metrics=result_analysis.success_metrics,
                feedback={
                    "memory_context": asdict(memory_context),
                    "result_analysis": asdict(result_analysis)
                },
                next_steps=next_steps
            )
            
            # Save to improvement history
            self.improvement_history.append({
                "task_id": task_id,
                "goal": improvement_goal,
                "result": asdict(result),
                "timestamp": time.time()
            })
            await self._save_improvement_history()
            
            return result
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error orchestrating self-improvement: {e}", exc_info=True)
            return ImprovementResult(
                goal=improvement_goal,
                success=False,
                agents_used=agents_used,
                improvements_made=improvements_made,
                metrics={},
                feedback={"error": str(e)},
                next_steps=[]
            )
    
    async def select_agents_for_task(self, task: Dict[str, Any]) -> List[str]:
        """
        Intelligently select agents based on task requirements (including new agents).
        
        Args:
            task: Task dictionary with type, goal, context, etc.
            
        Returns:
            List of agent IDs selected for the task
        """
        logger.info(f"{self.log_prefix} Selecting agents for task: {task.get('type', 'unknown')}")
        
        selected_agents = []
        task_type = task.get("type", "")
        task_goal = task.get("goal", "")
        
        try:
            # Check for new agents first
            await self.monitor_new_agents()
            
            # Select agents based on task type
            if task_type == "self_improvement":
                # For self-improvement, use SEA, BDI, Mastermind
                if "strategic_evolution_agent" in self.agent_knowledge:
                    selected_agents.append("strategic_evolution_agent")
                if "bdi_agent" in self.agent_knowledge:
                    selected_agents.append("bdi_agent")
                if "mastermind_agent" in self.agent_knowledge:
                    selected_agents.append("mastermind_agent")
            
            elif task_type == "monitoring":
                # For monitoring tasks
                if "performance_monitor" in self.agent_knowledge:
                    selected_agents.append("performance_monitor")
                if "resource_monitor" in self.agent_knowledge:
                    selected_agents.append("resource_monitor")
            
            elif task_type == "coordination":
                # For coordination tasks
                if "coordinator_agent" in self.agent_knowledge:
                    selected_agents.append("coordinator_agent")
                if "mastermind_agent" in self.agent_knowledge:
                    selected_agents.append("mastermind_agent")
            
            # Also consider agents based on capabilities matching task requirements
            for agent_id, capabilities in self.agent_capabilities.items():
                if agent_id not in selected_agents:
                    # Check if agent's capabilities match task requirements
                    task_keywords = task_goal.lower().split()
                    agent_capabilities_str = " ".join(capabilities.primary_capabilities).lower()
                    
                    if any(keyword in agent_capabilities_str for keyword in task_keywords if len(keyword) > 3):
                        selected_agents.append(agent_id)
            
            logger.info(f"{self.log_prefix} Selected {len(selected_agents)} agents: {selected_agents}")
            return selected_agents
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error selecting agents: {e}", exc_info=True)
            return selected_agents
    
    async def execute_improvement_campaign(self, goal: str) -> Dict[str, Any]:
        """
        Execute improvement campaign using SEA, BDI, Mastermind with result tracking.
        
        Args:
            goal: Improvement goal description
            
        Returns:
            Campaign result dictionary
        """
        logger.info(f"{self.log_prefix} Executing improvement campaign: {goal[:50]}...")
        
        try:
            # Use orchestrate_self_improvement which handles the full workflow
            result = await self.orchestrate_self_improvement(goal)
            
            return {
                "success": result.success,
                "agents_used": result.agents_used,
                "improvements": result.improvements_made,
                "metrics": result.metrics,
                "next_steps": result.next_steps
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error executing improvement campaign: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def monitor_system_health(self) -> Dict[str, Any]:
        """
        Monitor overall system health using monitoring agents and actual results.
        
        Returns:
            System health dictionary
        """
        logger.info(f"{self.log_prefix} Monitoring system health...")
        
        try:
            health_status = {
                "overall": "UNKNOWN",
                "components": {},
                "metrics": {},
                "timestamp": time.time()
            }
            
            # Get performance metrics
            if self.performance_monitor:
                try:
                    perf_metrics = await self.performance_monitor.get_metrics()
                    health_status["metrics"]["performance"] = perf_metrics
                except Exception as e:
                    logger.debug(f"{self.log_prefix} Error getting performance metrics: {e}")
            
            # Get resource metrics
            if self.resource_monitor:
                try:
                    resource_metrics = await self.resource_monitor.get_current_metrics()
                    health_status["metrics"]["resources"] = resource_metrics
                except Exception as e:
                    logger.debug(f"{self.log_prefix} Error getting resource metrics: {e}")
            
            # Check agent statuses
            active_count = sum(1 for k in self.agent_knowledge.values() if k.status == AgentStatus.ACTIVE)
            total_count = len(self.agent_knowledge)
            
            health_status["components"]["agents"] = {
                "active": active_count,
                "total": total_count,
                "health_ratio": active_count / total_count if total_count > 0 else 0
            }
            
            # Determine overall health
            if health_status["components"]["agents"]["health_ratio"] > 0.8:
                health_status["overall"] = "HEALTHY"
            elif health_status["components"]["agents"]["health_ratio"] > 0.5:
                health_status["overall"] = "DEGRADED"
            else:
                health_status["overall"] = "CRITICAL"
            
            return health_status
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error monitoring system health: {e}", exc_info=True)
            return {
                "overall": "UNKNOWN",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def evolve_architecture(self, evolution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Guide system architecture evolution based on actual performance data.
        
        Args:
            evolution_plan: Plan for architecture evolution
            
        Returns:
            Evolution result dictionary
        """
        logger.info(f"{self.log_prefix} Evolving architecture...")
        
        try:
            # Analyze current architecture
            architecture_map = await self._map_system_architecture()
            
            # Use StrategicEvolutionAgent for evolution
            if self.strategic_evolution_agent:
                evolution_result = await self.strategic_evolution_agent.create_improvement_campaign(
                    goal_description=f"Architecture evolution: {evolution_plan.get('description', '')}",
                    priority="high"
                )
                return {
                    "success": True,
                    "architecture_map": architecture_map,
                    "evolution_result": evolution_result
                }
            
            return {
                "success": False,
                "error": "StrategicEvolutionAgent not available"
            }
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error evolving architecture: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _map_system_architecture(self) -> Dict[str, Any]:
        """Map the current system architecture"""
        architecture = {
            "agents": {},
            "relationships": {},
            "dependencies": {}
        }
        
        for agent_id, knowledge in self.agent_knowledge.items():
            architecture["agents"][agent_id] = {
                "type": knowledge.agent_type,
                "location": knowledge.location,
                "status": knowledge.status.value
            }
            
            if knowledge.integration_points:
                architecture["relationships"][agent_id] = knowledge.integration_points
        
        return architecture
    
    async def update_agent_knowledge(self, agent_id: str, new_capabilities: Dict[str, Any]):
        """
        Update knowledge base when new agents are created or existing agents evolve.
        
        Args:
            agent_id: ID of the agent to update
            new_capabilities: New capability information
        """
        logger.info(f"{self.log_prefix} Updating knowledge for agent: {agent_id}")
        
        try:
            if agent_id in self.agent_knowledge:
                knowledge = self.agent_knowledge[agent_id]
                
                # Update capabilities
                if "capabilities" in new_capabilities:
                    knowledge.capabilities.extend(new_capabilities["capabilities"])
                
                # Update other fields
                if "roles" in new_capabilities:
                    knowledge.roles.extend(new_capabilities["roles"])
                
                if "powers" in new_capabilities:
                    knowledge.powers.update(new_capabilities["powers"])
                
                knowledge.last_updated = time.time()
                
                # Re-analyze capabilities
                await self.analyze_agent_capabilities(agent_id)
                
                # Save knowledge base
                await self._save_knowledge_base()
                
                logger.info(f"{self.log_prefix} Updated knowledge for {agent_id}")
            else:
                logger.warning(f"{self.log_prefix} Agent {agent_id} not in knowledge base")
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Error updating agent knowledge: {e}", exc_info=True)
    
    async def _save_improvement_history(self):
        """Save improvement history to disk"""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.improvement_history_file, 'w') as f:
                json.dump(self.improvement_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"{self.log_prefix} Could not save improvement history: {e}")
    
    async def shutdown(self):
        """Shutdown MindX Agent"""
        logger.info(f"{self.log_prefix} Shutting down...")
        self.running = False
        await self._save_knowledge_base()
        await self._save_improvement_history()
        logger.info(f"{self.log_prefix} Shutdown complete")
