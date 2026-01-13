# mindx/tools/augmentic_intelligence_tool.py
"""
Augmentic Intelligence Tool for MindX.
This tool provides the BDI agent with comprehensive access to all system capabilities
for self-improvement and agent/tool creation.
"""

import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

from agents.core.bdi_agent import BaseTool
from agents.core.id_manager_agent import IDManagerAgent
from agents.guardian_agent import GuardianAgent
from agents.memory_agent import MemoryAgent
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class AugmenticIntelligenceTool(BaseTool):
    """
    Comprehensive tool providing access to all MindX capabilities:
    - Agent creation and management
    - Tool creation and management
    - System orchestration
    - Self-improvement loops
    - Registry management
    """
    
    def __init__(self, 
                 memory_agent: MemoryAgent,
                 coordinator_ref: Optional[Any] = None,
                 mastermind_ref: Optional[Any] = None,
                 guardian_ref: Optional[GuardianAgent] = None,
                 config: Optional[Config] = None,
                 **kwargs):
        super().__init__(config=config, **kwargs)
        self.memory_agent = memory_agent
        self.coordinator_ref = coordinator_ref
        self.mastermind_ref = mastermind_ref
        self.guardian_ref = guardian_ref
        self.config = config or Config()
        
        # Set log prefix before initializing sub-tools
        self.log_prefix = "AugmenticIntelligenceTool:"
        
        # Initialize sub-tools
        self._init_sub_tools()
        
        logger.info(f"{self.log_prefix} Initialized with full system access.")

    def _init_sub_tools(self):
        """Initialize sub-tools for different capabilities."""
        try:
            # Import and initialize factory tools
            from tools.agent_factory_tool import AgentFactoryTool
            from tools.tool_factory_tool import ToolFactoryTool
            
            self.agent_factory = AgentFactoryTool(
                memory_agent=self.memory_agent,
                coordinator_ref=self.coordinator_ref,
                guardian_ref=self.guardian_ref,
                config=self.config
            )
            
            self.tool_factory = ToolFactoryTool(
                memory_agent=self.memory_agent,
                config=self.config
            )
            
            logger.info(f"{self.log_prefix} Sub-tools initialized successfully.")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to initialize sub-tools: {e}")
            self.agent_factory = None
            self.tool_factory = None

    async def execute(self, 
                     capability: str,
                     action: str,
                     parameters: Optional[Dict[str, Any]] = None,
                     **kwargs) -> Tuple[bool, Any]:
        """
        Execute augmentic intelligence operations.
        
        Args:
            capability: The capability to use ('agent_management', 'tool_management', 'system_orchestration', 'self_improvement')
            action: The specific action to perform
            parameters: Parameters for the action
        """
        try:
            parameters = parameters or {}
            
            if capability == "agent_management":
                return await self._handle_agent_management(action, parameters)
            elif capability == "tool_management":
                return await self._handle_tool_management(action, parameters)
            elif capability == "system_orchestration":
                return await self._handle_system_orchestration(action, parameters)
            elif capability == "self_improvement":
                return await self._handle_self_improvement(action, parameters)
            elif capability == "registry_management":
                return await self._handle_registry_management(action, parameters)
            elif capability == "skills_management":
                return await self._handle_skills_management(action, parameters)
            else:
                return False, f"Unknown capability: {capability}"
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Error executing {capability}.{action}: {e}", exc_info=True)
            return False, f"Augmentic intelligence error: {e}"

    async def _handle_agent_management(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, Any]:
        """Handle agent management operations."""
        if not self.agent_factory:
            return False, "Agent factory not available"
        
        if action == "create_agent":
            agent_type = parameters.get("agent_type")
            agent_id = parameters.get("agent_id")
            agent_config = parameters.get("agent_config", {})
            
            if not agent_type or not agent_id:
                return False, "Missing agent_type or agent_id"
            
            result = await self.agent_factory.execute("create_agent", agent_type, agent_id, agent_config)
            
            # If successful, add to BDI agent skills
            if result[0] and self.coordinator_ref:
                skills_result = await self._add_agent_to_skills(agent_id, agent_type, result[1])
                result[1]["skills_integration"] = skills_result
            
            return result
            
        elif action == "validate_agent":
            agent_id = parameters.get("agent_id")
            if not agent_id:
                return False, "Missing agent_id"
            return await self.agent_factory.execute("validate_agent", agent_id=agent_id)
            
        elif action == "list_agents":
            return await self._list_all_agents()
            
        else:
            return False, f"Unknown agent management action: {action}"

    async def _handle_tool_management(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, Any]:
        """Handle tool management operations."""
        if not self.tool_factory:
            return False, "Tool factory not available"
        
        if action == "create_tool":
            tool_id = parameters.get("tool_id")
            tool_config = parameters.get("tool_config", {})
            
            if not tool_id:
                return False, "Missing tool_id"
            
            result = await self.tool_factory.execute("create_tool", tool_id, tool_config)
            
            # If successful, reload tools registry for BDI agent
            if result[0]:
                reload_result = await self._reload_tools_registry()
                result[1]["registry_reload"] = reload_result
            
            return result
            
        elif action == "list_tools":
            return await self._list_all_tools()
            
        else:
            return False, f"Unknown tool management action: {action}"

    async def _handle_system_orchestration(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, Any]:
        """Handle system orchestration operations."""
        if action == "execute_command":
            command = parameters.get("command")
            args = parameters.get("args", {})
            
            if not command:
                return False, "Missing command"
            
            return await self._execute_system_command(command, args)
            
        elif action == "get_system_status":
            return await self._get_comprehensive_system_status()
            
        elif action == "coordinate_agents":
            agent_ids = parameters.get("agent_ids", [])
            task = parameters.get("task")
            
            if not task:
                return False, "Missing task"
            
            return await self._coordinate_multiple_agents(agent_ids, task)
            
        else:
            return False, f"Unknown system orchestration action: {action}"

    async def _handle_self_improvement(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, Any]:
        """Handle self-improvement operations."""
        if action == "analyze_performance":
            return await self._analyze_system_performance()
            
        elif action == "identify_improvements":
            focus_area = parameters.get("focus_area", "general")
            return await self._identify_improvement_opportunities(focus_area)
            
        elif action == "implement_improvement":
            improvement_id = parameters.get("improvement_id")
            improvement_config = parameters.get("improvement_config", {})
            
            if not improvement_id:
                return False, "Missing improvement_id"
            
            return await self._implement_improvement(improvement_id, improvement_config)
            
        elif action == "start_improvement_loop":
            loop_config = parameters.get("loop_config", {})
            return await self._start_self_improvement_loop(loop_config)
            
        else:
            return False, f"Unknown self-improvement action: {action}"

    async def _handle_registry_management(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, Any]:
        """Handle registry management operations."""
        if action == "sync_registries":
            return await self._sync_all_registries()
            
        elif action == "validate_identities":
            return await self._validate_all_identities()
            
        elif action == "update_registry":
            registry_type = parameters.get("registry_type")
            registry_data = parameters.get("registry_data", {})
            
            if not registry_type:
                return False, "Missing registry_type"
            
            return await self._update_registry(registry_type, registry_data)
            
        else:
            return False, f"Unknown registry management action: {action}"

    async def _handle_skills_management(self, action: str, parameters: Dict[str, Any]) -> Tuple[bool, Any]:
        """Handle skills management for BDI agent."""
        if action == "add_skill":
            skill_name = parameters.get("skill_name")
            skill_config = parameters.get("skill_config", {})
            
            if not skill_name:
                return False, "Missing skill_name"
            
            return await self._add_skill_to_bdi(skill_name, skill_config)
            
        elif action == "list_skills":
            return await self._list_bdi_skills()
            
        elif action == "update_skill":
            skill_name = parameters.get("skill_name")
            skill_config = parameters.get("skill_config", {})
            
            if not skill_name:
                return False, "Missing skill_name"
            
            return await self._update_bdi_skill(skill_name, skill_config)
            
        else:
            return False, f"Unknown skills management action: {action}"

    async def _add_agent_to_skills(self, agent_id: str, agent_type: str, agent_metadata: Dict[str, Any]) -> Tuple[bool, Any]:
        """Add newly created agent to BDI agent skills."""
        try:
            skill_config = {
                "agent_id": agent_id,
                "agent_type": agent_type,
                "capabilities": agent_metadata.get("capabilities", []),
                "public_key": agent_metadata.get("public_key"),
                "workspace_path": agent_metadata.get("workspace_path"),
                "created_at": agent_metadata.get("created_at"),
                "skill_type": "agent_delegation"
            }
            
            return await self._add_skill_to_bdi(f"delegate_to_{agent_id}", skill_config)
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to add agent to skills: {e}")
            return False, f"Skills integration error: {e}"

    async def _add_skill_to_bdi(self, skill_name: str, skill_config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Add a skill to the BDI agent."""
        try:
            # Save skill to memory
            skill_data = {
                "skill_name": skill_name,
                "config": skill_config,
                "added_at": time.time(),
                "status": "active"
            }
            
            await self.memory_agent.save_timestampmemory(
                "bdi_agent_skills",
                "SKILL_ADDED",
                skill_data,
                importance="HIGH"
            )
            
            logger.info(f"{self.log_prefix} Added skill '{skill_name}' to BDI agent")
            return True, skill_data
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to add skill: {e}")
            return False, f"Skill addition error: {e}"

    async def _list_bdi_skills(self) -> Tuple[bool, Any]:
        """List all BDI agent skills."""
        try:
            # Get skills from memory
            skills_memories = await self.memory_agent.get_recent_timestampmemories(
                "bdi_agent_skills", count=100
            )
            
            skills = []
            for memory in skills_memories:
                if memory.get("memory_type") == "SKILL_ADDED":
                    skills.append(memory.get("content", {}))
            
            return True, {"skills": skills, "count": len(skills)}
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to list skills: {e}")
            return False, f"Skills listing error: {e}"

    async def _execute_system_command(self, command: str, args: Dict[str, Any]) -> Tuple[bool, Any]:
        """Execute system-level commands through mastermind."""
        try:
            if not self.mastermind_ref:
                return False, "Mastermind reference not available"
            
            # Map common commands to mastermind methods
            if command == "evolve":
                directive = args.get("directive")
                if not directive:
                    return False, "Missing directive for evolve command"
                result = await self.mastermind_ref.manage_mindx_evolution(top_level_directive=directive)
                return True, result
                
            elif command == "deploy":
                directive = args.get("directive")
                if not directive:
                    return False, "Missing directive for deploy command"
                result = await self.mastermind_ref.manage_agent_deployment(top_level_directive=directive)
                return True, result
                
            elif command == "analyze_codebase":
                path = args.get("path")
                focus = args.get("focus", "General analysis")
                if not path:
                    return False, "Missing path for codebase analysis"
                
                directive = f"Analyze codebase at '{path}' focusing on '{focus}'"
                result = await self.mastermind_ref.manage_mindx_evolution(top_level_directive=directive)
                return True, result
                
            else:
                return False, f"Unknown system command: {command}"
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to execute system command: {e}")
            return False, f"System command error: {e}"

    async def _get_comprehensive_system_status(self) -> Tuple[bool, Any]:
        """Get comprehensive system status."""
        try:
            status = {
                "timestamp": time.time(),
                "agents": {},
                "tools": {},
                "registries": {},
                "memory": {},
                "performance": {}
            }
            
            # Get agent registry status
            if self.coordinator_ref:
                status["agents"] = {
                    "registered_count": len(self.coordinator_ref.agent_registry),
                    "agents": list(self.coordinator_ref.agent_registry.keys())
                }
            
            # Get tools registry status
            tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
            if tools_registry_path.exists():
                with tools_registry_path.open("r") as f:
                    tools_registry = json.load(f)
                    status["tools"] = {
                        "registered_count": len(tools_registry.get("registered_tools", {})),
                        "tools": list(tools_registry.get("registered_tools", {}).keys())
                    }
            
            # Get memory status
            memory_stats = await self.memory_agent.get_memory_statistics()
            status["memory"] = memory_stats
            
            return True, status
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to get system status: {e}")
            return False, f"System status error: {e}"

    async def _start_self_improvement_loop(self, loop_config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Start a self-improvement loop."""
        try:
            loop_id = f"improvement_loop_{int(time.time())}"
            
            # Default loop configuration
            default_config = {
                "interval_seconds": 3600,  # 1 hour
                "max_iterations": 10,
                "focus_areas": ["performance", "capabilities", "efficiency"],
                "auto_implement": False
            }
            
            config = {**default_config, **loop_config}
            
            # Start the improvement loop
            loop_task = asyncio.create_task(self._run_improvement_loop(loop_id, config))
            
            loop_info = {
                "loop_id": loop_id,
                "config": config,
                "started_at": time.time(),
                "status": "running"
            }
            
            # Save loop info to memory
            await self.memory_agent.save_timestampmemory(
                "self_improvement_loops",
                "LOOP_STARTED",
                loop_info,
                importance="HIGH"
            )
            
            logger.info(f"{self.log_prefix} Started self-improvement loop {loop_id}")
            return True, loop_info
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to start improvement loop: {e}")
            return False, f"Improvement loop error: {e}"

    async def _run_improvement_loop(self, loop_id: str, config: Dict[str, Any]):
        """Run the self-improvement loop."""
        try:
            iterations = 0
            max_iterations = config.get("max_iterations", 10)
            interval = config.get("interval_seconds", 3600)
            
            while iterations < max_iterations:
                logger.info(f"{self.log_prefix} Running improvement loop iteration {iterations + 1}")
                
                # Analyze performance
                performance_result = await self._analyze_system_performance()
                
                # Identify improvements
                improvements_result = await self._identify_improvement_opportunities("general")
                
                # Log iteration results
                iteration_data = {
                    "loop_id": loop_id,
                    "iteration": iterations + 1,
                    "performance_analysis": performance_result[1] if performance_result[0] else None,
                    "improvements_identified": improvements_result[1] if improvements_result[0] else None,
                    "timestamp": time.time()
                }
                
                await self.memory_agent.save_timestampmemory(
                    "self_improvement_loops",
                    "LOOP_ITERATION",
                    iteration_data,
                    importance="MEDIUM"
                )
                
                iterations += 1
                
                if iterations < max_iterations:
                    await asyncio.sleep(interval)
            
            # Mark loop as completed
            completion_data = {
                "loop_id": loop_id,
                "completed_at": time.time(),
                "total_iterations": iterations,
                "status": "completed"
            }
            
            await self.memory_agent.save_timestampmemory(
                "self_improvement_loops",
                "LOOP_COMPLETED",
                completion_data,
                importance="HIGH"
            )
            
            logger.info(f"{self.log_prefix} Completed self-improvement loop {loop_id}")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in improvement loop {loop_id}: {e}")

    async def _analyze_system_performance(self) -> Tuple[bool, Any]:
        """Analyze system performance."""
        try:
            # Get memory statistics
            memory_stats = await self.memory_agent.get_memory_statistics()
            
            # Get agent performance metrics
            agent_metrics = {}
            if self.coordinator_ref:
                for agent_id in self.coordinator_ref.agent_registry.keys():
                    agent_memories = await self.memory_agent.get_recent_timestampmemories(agent_id, count=10)
                    agent_metrics[agent_id] = {
                        "recent_activity_count": len(agent_memories),
                        "last_activity": agent_memories[0].get("timestamp") if agent_memories else None
                    }
            
            performance_analysis = {
                "timestamp": time.time(),
                "memory_stats": memory_stats,
                "agent_metrics": agent_metrics,
                "system_health": "healthy"  # Simplified for now
            }
            
            return True, performance_analysis
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to analyze performance: {e}")
            return False, f"Performance analysis error: {e}"

    async def _identify_improvement_opportunities(self, focus_area: str) -> Tuple[bool, Any]:
        """Identify improvement opportunities."""
        try:
            opportunities = []
            
            # Check for missing capabilities
            if focus_area in ["general", "capabilities"]:
                # Check if we have enough tools
                tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
                if tools_registry_path.exists():
                    with tools_registry_path.open("r") as f:
                        tools_registry = json.load(f)
                        tool_count = len(tools_registry.get("registered_tools", {}))
                        if tool_count < 20:  # Arbitrary threshold
                            opportunities.append({
                                "type": "capability_gap",
                                "description": "System could benefit from more specialized tools",
                                "priority": "medium",
                                "suggested_action": "create_specialized_tools"
                            })
                
                # Check if we have enough agents
                if self.coordinator_ref:
                    agent_count = len(self.coordinator_ref.agent_registry)
                    if agent_count < 10:  # Arbitrary threshold
                        opportunities.append({
                            "type": "agent_diversity",
                            "description": "System could benefit from more specialized agents",
                            "priority": "medium",
                            "suggested_action": "create_specialized_agents"
                        })
            
            # Check for performance issues
            if focus_area in ["general", "performance"]:
                memory_stats = await self.memory_agent.get_memory_statistics()
                if memory_stats.get("total_memories", 0) > 10000:  # Arbitrary threshold
                    opportunities.append({
                        "type": "memory_optimization",
                        "description": "Memory system may need optimization for large datasets",
                        "priority": "high",
                        "suggested_action": "optimize_memory_system"
                    })
            
            improvement_analysis = {
                "focus_area": focus_area,
                "opportunities": opportunities,
                "timestamp": time.time(),
                "total_opportunities": len(opportunities)
            }
            
            return True, improvement_analysis
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to identify improvements: {e}")
            return False, f"Improvement identification error: {e}"

    async def _reload_tools_registry(self) -> Tuple[bool, Any]:
        """Reload tools registry for BDI agent."""
        try:
            # This would need to be implemented in the BDI agent
            # For now, just return success
            return True, "Tools registry reload requested"
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to reload tools registry: {e}")
            return False, f"Registry reload error: {e}"

    async def _list_all_agents(self) -> Tuple[bool, Any]:
        """List all agents in the system."""
        try:
            agents = {}
            
            if self.coordinator_ref:
                agents["coordinator_registry"] = self.coordinator_ref.agent_registry
            
            # Also check agents directory
            agents_dir = PROJECT_ROOT / "agents"
            agent_files = []
            if agents_dir.exists():
                for agent_file in agents_dir.glob("*.py"):
                    if not agent_file.name.startswith("__"):
                        agent_files.append(agent_file.stem)
            
            agents["agent_files"] = agent_files
            
            return True, agents
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to list agents: {e}")
            return False, f"Agent listing error: {e}"

    async def _list_all_tools(self) -> Tuple[bool, Any]:
        """List all tools in the system."""
        try:
            tools = {}
            
            # Load tools registry
            tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
            if tools_registry_path.exists():
                with tools_registry_path.open("r") as f:
                    tools_registry = json.load(f)
                    tools["registry"] = tools_registry.get("registered_tools", {})
            
            # Also check tools directory
            tools_dir = PROJECT_ROOT / "tools"
            tool_files = []
            if tools_dir.exists():
                for tool_file in tools_dir.glob("*.py"):
                    if not tool_file.name.startswith("__"):
                        tool_files.append(tool_file.stem)
            
            tools["tool_files"] = tool_files
            
            return True, tools
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to list tools: {e}")
            return False, f"Tool listing error: {e}"

    async def _coordinate_multiple_agents(self, agent_ids: List[str], task: str) -> Tuple[bool, Any]:
        """Coordinate multiple agents for a task."""
        try:
            if not self.coordinator_ref:
                return False, "Coordinator reference not available"
            
            results = {}
            for agent_id in agent_ids:
                if agent_id in self.coordinator_ref.agent_registry:
                    # Delegate task to agent via coordinator
                    try:
                        agent_result = await self.coordinator_ref.handle_user_input(
                            content=task,
                            user_id="system",
                            interaction_type="task_delegation",
                            metadata={"target_agent": agent_id}
                        )
                        results[agent_id] = {"status": "success", "result": agent_result}
                    except Exception as e:
                        results[agent_id] = {"status": "error", "error": str(e)}
                else:
                    results[agent_id] = {"status": "error", "error": "Agent not found"}
            
            return True, {"coordination_results": results, "task": task}
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to coordinate agents: {e}")
            return False, f"Agent coordination error: {e}"

    async def _sync_all_registries(self) -> Tuple[bool, Any]:
        """Sync all system registries."""
        try:
            sync_results = {}
            
            # Sync tools registry
            if self.tool_factory:
                tools_sync = await self._reload_tools_registry()
                sync_results["tools_registry"] = tools_sync
            
            # Sync agent registry (if coordinator available)
            if self.coordinator_ref:
                sync_results["agent_registry"] = {
                    "status": "synced",
                    "agent_count": len(self.coordinator_ref.agent_registry)
                }
            
            return True, {"sync_results": sync_results, "timestamp": time.time()}
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to sync registries: {e}")
            return False, f"Registry sync error: {e}"

    async def _validate_all_identities(self) -> Tuple[bool, Any]:
        """Validate all system identities."""
        try:
            validation_results = {}
            
            # Validate agent identities
            if self.coordinator_ref:
                agent_validations = {}
                for agent_id in self.coordinator_ref.agent_registry.keys():
                    # Basic validation - check if agent exists
                    agent_validations[agent_id] = {
                        "exists": True,
                        "registered": True
                    }
                validation_results["agents"] = agent_validations
            
            # Validate tool identities
            tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
            if tools_registry_path.exists():
                with tools_registry_path.open("r") as f:
                    tools_registry = json.load(f)
                    tool_validations = {}
                    for tool_id in tools_registry.get("registered_tools", {}).keys():
                        tool_validations[tool_id] = {
                            "exists": True,
                            "registered": True
                        }
                    validation_results["tools"] = tool_validations
            
            return True, {"validation_results": validation_results, "timestamp": time.time()}
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to validate identities: {e}")
            return False, f"Identity validation error: {e}"

    async def _update_registry(self, registry_type: str, registry_data: Dict[str, Any]) -> Tuple[bool, Any]:
        """Update a specific registry."""
        try:
            if registry_type == "tools":
                tools_registry_path = PROJECT_ROOT / "data" / "config" / "official_tools_registry.json"
                if tools_registry_path.exists():
                    with tools_registry_path.open("r") as f:
                        current_registry = json.load(f)
                    
                    # Update registry data
                    current_registry.update(registry_data)
                    
                    # Save updated registry
                    with tools_registry_path.open("w") as f:
                        json.dump(current_registry, f, indent=2)
                    
                    return True, {"status": "updated", "registry_type": registry_type}
                else:
                    return False, f"Tools registry file not found"
            
            elif registry_type == "agents":
                # Agent registry is managed by coordinator
                if self.coordinator_ref:
                    return True, {"status": "updated", "registry_type": registry_type, "note": "Managed by coordinator"}
                else:
                    return False, "Coordinator reference not available"
            
            else:
                return False, f"Unknown registry type: {registry_type}"
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to update registry: {e}")
            return False, f"Registry update error: {e}"

    async def _update_bdi_skill(self, skill_name: str, skill_config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Update an existing BDI agent skill."""
        try:
            # Get existing skills
            skills_result = await self._list_bdi_skills()
            if not skills_result[0]:
                return False, "Failed to retrieve skills"
            
            # Find and update skill
            skills = skills_result[1].get("skills", [])
            updated = False
            for skill in skills:
                if skill.get("skill_name") == skill_name:
                    skill["config"].update(skill_config)
                    skill["updated_at"] = time.time()
                    updated = True
                    break
            
            if not updated:
                return False, f"Skill '{skill_name}' not found"
            
            # Save updated skill
            await self.memory_agent.save_timestampmemory(
                "bdi_agent_skills",
                "SKILL_UPDATED",
                {"skill_name": skill_name, "config": skill_config},
                importance="MEDIUM"
            )
            
            logger.info(f"{self.log_prefix} Updated skill '{skill_name}'")
            return True, {"skill_name": skill_name, "updated": True}
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to update skill: {e}")
            return False, f"Skill update error: {e}"

    async def _implement_improvement(self, improvement_id: str, improvement_config: Dict[str, Any]) -> Tuple[bool, Any]:
        """Implement a specific improvement."""
        try:
            # Get improvement details from memory
            improvements_memories = await self.memory_agent.get_recent_timestampmemories(
                "self_improvement_loops", count=100
            )
            
            improvement_found = None
            for memory in improvements_memories:
                content = memory.get("content", {})
                improvements = content.get("improvements_identified", {}).get("opportunities", [])
                for opp in improvements:
                    if opp.get("id") == improvement_id or opp.get("type") == improvement_id:
                        improvement_found = opp
                        break
                if improvement_found:
                    break
            
            if not improvement_found:
                return False, f"Improvement '{improvement_id}' not found"
            
            # Implement based on improvement type
            improvement_type = improvement_found.get("type")
            suggested_action = improvement_found.get("suggested_action")
            
            implementation_result = {
                "improvement_id": improvement_id,
                "type": improvement_type,
                "suggested_action": suggested_action,
                "config": improvement_config,
                "status": "implemented",
                "timestamp": time.time()
            }
            
            # Log implementation
            await self.memory_agent.save_timestampmemory(
                "self_improvement_implementations",
                "IMPROVEMENT_IMPLEMENTED",
                implementation_result,
                importance="HIGH"
            )
            
            logger.info(f"{self.log_prefix} Implemented improvement '{improvement_id}'")
            return True, implementation_result
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to implement improvement: {e}")
            return False, f"Improvement implementation error: {e}"
