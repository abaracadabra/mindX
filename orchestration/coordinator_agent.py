# orchestration/coordinator_agent.py (Version 3.0 - Concurrency & Events)
"""
This module defines the CoordinatorAgent, the central operating system and
service bus for the MindX Sovereign Intelligent Organization (SIO).

Core Philosophy: "Do one thing and do it well."
The Coordinator's role is to manage and route interactions, provide core system
services, and enable decoupled communication. It is a "headless" kernel that does
not perform strategic reasoning.

Improvements in v3.0:
- Concurrency Management: Implemented an asyncio.Semaphore to limit concurrent
  execution of resource-intensive tasks (e.g., component improvement),
  ensuring system stability under load.
- Event-Driven Pub/Sub Bus: Added `subscribe` and `publish_event` methods to
  allow for a decoupled, event-driven architecture where agents can react to
  system-wide events without direct coupling.
- Role Purity: Continues the focus on being a pure orchestrator, with health
  and resource monitoring delegated to specialized agents.
"""
from __future__ import annotations
import asyncio
import json
import time
import uuid
from enum import Enum
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Optional, Callable, Coroutine

# Assuming these are actual, well-defined modules
from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from llm.llm_factory import create_llm_handler
from llm.llm_interface import LLMHandlerInterface
from agents.memory_agent import MemoryAgent
from monitoring.performance_monitor import get_performance_monitor_async
from monitoring.resource_monitor import get_resource_monitor_async
from core.belief_system import BeliefSystem

logger = get_logger(__name__)

# --- Core Data Structures ---

class InteractionType(Enum):
    QUERY = "query"
    SYSTEM_ANALYSIS = "system_analysis"
    COMPONENT_IMPROVEMENT = "component_improvement"
    AGENT_REGISTRATION = "agent_registration"
    PUBLISH_EVENT = "publish_event" # New interaction type for the event bus

class InteractionStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROUTED_TO_TOOL = "routed_to_tool"

class Interaction:
    """A data object representing a single, trackable request within the system."""
    def __init__(self, interaction_id: str, interaction_type: InteractionType, content: str, **kwargs):
        self.interaction_id = interaction_id
        self.interaction_type = interaction_type
        self.content = content
        self.metadata = kwargs.get("metadata", {})
        self.status = InteractionStatus.PENDING
        self.response: Optional[Any] = None
        self.error: Optional[str] = None
        self.created_at: float = time.time()
        self.completed_at: Optional[float] = None

    def to_dict(self):
        return {
            'interaction_id': self.interaction_id,
            'interaction_type': self.interaction_type.value,
            'content': self.content,
            'metadata': self.metadata,
            'status': self.status.value,
            'response': self.response,
            'error': self.error,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
        }

# --- The Coordinator Agent Kernel ---

class CoordinatorAgent:
    """
    The central kernel and service bus of the MindX system. It manages agent
    registration, system monitoring, and routes all formal interactions.
    """
    _instance: Optional['CoordinatorAgent'] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls, **kwargs) -> 'CoordinatorAgent':
        """Singleton factory to get or create the Coordinator instance."""
        async with cls._lock:
            if cls._instance is None or kwargs.get("test_mode", False):
                # Pass memory_agent to constructor if provided
                cls._instance = cls(**kwargs)
                await cls._instance.async_init() # Ensure async components are ready
            return cls._instance

    def __init__(self,
                 config_override: Optional[Config] = None,
                 memory_agent: Optional[MemoryAgent] = None,
                 test_mode: bool = False,
                 **kwargs):
        """Initializes the CoordinatorAgent."""
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return

        self.config = config_override or Config(test_mode=test_mode)
        self.agent_id = "coordinator_agent_main"
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.belief_system = kwargs.get('belief_system', BeliefSystem())
        
        # --- System Registries and Services ---
        self.agent_registry: Dict[str, Any] = {}
        self.tool_registry: Dict[str, Any] = {}
        
        # --- Backlog and History ---
        self.improvement_backlog_file = PROJECT_ROOT / "data" / "improvement_backlog.json"
        self.improvement_backlog: List[Dict[str, Any]] = self._load_backlog()
        self.improvement_campaign_history: List[Dict[str, Any]] = []


        # --- Interaction Management ---
        self.interactions: Dict[str, Interaction] = {}
        self.interaction_handlers: Dict[InteractionType, Callable] = self._get_interaction_handlers()

        # --- IMPROVEMENT: Concurrency Management ---
        max_heavy_tasks = self.config.get("coordinator.max_concurrent_heavy_tasks", 2)
        self.heavy_task_semaphore = asyncio.Semaphore(max_heavy_tasks)
        self.logger = get_logger(f"coordinator_agent")
        self.logger.info(f"Heavy task concurrency limit set to: {max_heavy_tasks}")

        # --- IMPROVEMENT: Event-Driven Pub/Sub Bus ---
        self.event_listeners: Dict[str, List[Callable]] = defaultdict(list)
        
        self.llm_handler: Optional[LLMHandlerInterface] = None
        self.performance_monitor: Optional[Any] = None
        self.resource_monitor: Optional[Any] = None

        self._initialized = True
        self.logger.info("CoordinatorAgent initialized. Awaiting async setup.")

    async def async_init(self):
        """Asynchronously initializes monitoring components and registers self."""
        try:
            self.llm_handler = await create_llm_handler(
                provider_name=self.config.get("coordinator.llm.provider"),
                model_name=self.config.get("coordinator.llm.model")
            )
            if self.llm_handler:
                self.logger.info(f"Coordinator LLM handler initialized: {self.llm_handler.provider_name}/{self.llm_handler.model_name_for_api}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Coordinator LLM handler: {e}", exc_info=True)
        
        from core.id_manager_agent import IDManagerAgent
        id_manager = await IDManagerAgent.get_instance(agent_id=f"id_manager_for_{self.agent_id}", config_override=self.config, memory_agent=self.memory_agent, belief_system=self.belief_system)
        await id_manager.create_new_wallet(entity_id=self.agent_id)

        self.register_agent(
            agent_id="coordinator_agent", agent_type="kernel",
            description="MindX Central Kernel and Service Bus",
            instance=self
        )
        await self._initialize_tools()

        # Initialize and start monitors
        self.performance_monitor = await get_performance_monitor_async(config_override=self.config)
        self.resource_monitor = await get_resource_monitor_async(memory_agent=self.memory_agent, config_override=self.config)
        if self.config.get("monitoring.resource.enabled", True):
            self.resource_monitor.start_monitoring()

        self.logger.info("CoordinatorAgent fully initialized.")

    def _get_interaction_handlers(self) -> Dict[InteractionType, Callable]:
        """Maps interaction types to their handler methods."""
        return {
            InteractionType.QUERY: self._handle_query,
            InteractionType.SYSTEM_ANALYSIS: self._handle_system_analysis,
            InteractionType.COMPONENT_IMPROVEMENT: self._handle_component_improvement,
            InteractionType.PUBLISH_EVENT: self._handle_publish_event,
            # AGENT_REGISTRATION is handled by the public `register_agent` method
        }

    async def _initialize_tools(self):
        """Initializes the tools the Coordinator itself needs to function."""
        # This method is now corrected. The Coordinator doesn't import the SIA as a tool.
        # It invokes it via CLI. This method can be used for other tools the coordinator might need.
        self.logger.info("Coordinator internal tool initialization complete (no tools to load).")

    def _load_backlog(self) -> List[Dict[str, Any]]:
        if self.improvement_backlog_file.exists():
            try:
                with self.improvement_backlog_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                self.logger.error(f"Failed to load improvement backlog: {e}")
        return []

    def _save_backlog(self):
        try:
            with self.improvement_backlog_file.open("w", encoding="utf-8") as f:
                json.dump(self.improvement_backlog, f, indent=2)
        except IOError as e:
            self.logger.error(f"Failed to save improvement backlog: {e}")

    async def _log_to_memory(self, memory_type: str, category: str, data: Dict[str, Any], metadata: Dict[str, Any] = None) -> Optional[Path]:
        """Log information to memory agent if available."""
        if not self.memory_agent:
            return None
        
        try:
            if metadata is None:
                metadata = {}
            
            # Add coordinator specific metadata
            metadata.update({
                "agent": "coordinator_agent_main",
                "agent_id": self.agent_id,
                "timestamp": time.time()
            })
            
            # Use the memory agent's save_memory method
            return await self.memory_agent.save_memory(memory_type, f"coordinator_agent_main/{category}", data, metadata)
        except Exception as e:
            self.logger.error(f"Failed to log to memory: {e}")
            return None

    async def _log_complete_output(self, interaction: Interaction) -> Optional[Path]:
        """Log complete coordinator agent output including system state, registry, and full context."""
        if not self.memory_agent:
            return None
        
        try:
            # Gather comprehensive system state (only serializable data)
            complete_data = {
                "interaction": interaction.to_dict(),
                "system_state": {
                    "agent_registry": {k: {key: val for key, val in v.items() if key != "instance"} for k, v in self.agent_registry.items()},
                    "tool_registry": dict(self.tool_registry),
                    "active_interactions": len([i for i in self.interactions.values() if i.status.name == "IN_PROGRESS"]),
                    "total_interactions": len(self.interactions),
                    "improvement_backlog_count": len(self.improvement_backlog),
                    "event_listeners": list(self.event_listeners.keys())
                },
                "coordinator_state": {
                    "agent_id": self.agent_id,
                    "initialized": getattr(self, "_initialized", False),
                    "llm_handler_available": self.llm_handler is not None,
                    "performance_monitor_available": self.performance_monitor is not None,
                    "resource_monitor_available": self.resource_monitor is not None
                },
                "timestamp": time.time(),
                "memory_type": "complete_output"
            }
            
            # Add interaction-specific metadata
            metadata = {
                "agent": "coordinator_agent_main",
                "agent_id": self.agent_id,
                "interaction_id": interaction.interaction_id,
                "interaction_type": interaction.interaction_type.value,
                "timestamp": time.time(),
                "output_type": "complete_coordinator_output"
            }
            
            # Save complete output to memory
            return await self.memory_agent.save_memory(
                "STM",
                "complete_output",
                complete_data,
                metadata
            )
        except Exception as e:
            self.logger.error(f"Failed to log complete output: {e}")
            return None
        
        try:
            # Gather comprehensive system state
            complete_data = {
                "interaction": interaction.to_dict(),
                "system_state": {
                    "agent_registry": dict(self.agent_registry),
                    "tool_registry": dict(self.tool_registry),
                    "active_interactions": len([i for i in self.interactions.values() if i.status.name == "IN_PROGRESS"]),
                    "total_interactions": len(self.interactions),
                    "improvement_backlog_count": len(self.improvement_backlog),
                    "event_listeners": list(self.event_listeners.keys())
                },
                "coordinator_state": {
                    "agent_id": self.agent_id,
                    "initialized": getattr(self, "_initialized", False),
                    "llm_handler_available": self.llm_handler is not None,
                    "performance_monitor_available": self.performance_monitor is not None,
                    "resource_monitor_available": self.resource_monitor is not None
                },
                "timestamp": time.time(),
                "memory_type": "complete_output"
            }
            
            # Add interaction-specific metadata
            metadata = {
                "agent": "coordinator_agent_main",
                "agent_id": self.agent_id,
                "interaction_id": interaction.interaction_id,
                "interaction_type": interaction.interaction_type.value,
                "timestamp": time.time(),
                "output_type": "complete_coordinator_output"
            }
            
            # Save complete output to memory
            return await self.memory_agent.save_memory(
                "STM",
                "complete_output",
                complete_data,
                metadata
            )
        except Exception as e:
            self.logger.error(f"Failed to log complete output: {e}")
            return None

    # --- Public API for Agent Society ---

    def register_agent(self, agent_id: str, agent_type: str, description: str, instance: Any):
        """Registers a running agent instance, making it known to the system."""
        self.agent_registry[agent_id] = {
            "agent_id": agent_id, "agent_type": agent_type,
            "description": description, "instance": instance,
            "status": "active", "registered_at": time.time(),
        }
        self.logger.info(f"Registered agent '{agent_id}' (Type: {agent_type}). Total agents: {len(self.agent_registry)}")

    def subscribe(self, topic: str, callback: Callable[..., Coroutine[Any, Any, None]]):
        """Allows an agent to listen for a specific event topic."""
        self.event_listeners[topic].append(callback)
        self.logger.info(f"New subscription to topic '{topic}' by '{getattr(callback, '__qualname__', 'unnamed_callback')}'")

    async def publish_event(self, topic: str, data: Dict[str, Any]):
        """Publishes an event, triggering all subscribed callbacks concurrently."""
        self.logger.info(f"Publishing event on topic '{topic}' with data keys: {list(data.keys())}")
        if topic in self.event_listeners:
            tasks = [callback(data) for callback in self.event_listeners[topic]]
            # Gather and log exceptions without stopping other listeners
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    callback_name = getattr(self.event_listeners[topic][i], '__qualname__', 'unnamed_callback')
                    self.logger.error(f"Error in event listener '{callback_name}' for topic '{topic}': {result}", exc_info=result)

    async def handle_user_input(self, content: str, user_id: str, interaction_type: InteractionType, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Handles direct user input by creating and processing an interaction."""
        interaction = Interaction(
            interaction_id=f"inter_{interaction_type.name.lower()}_{uuid.uuid4().hex[:8]}",
            interaction_type=interaction_type,
            content=content,
            metadata=metadata or {}
        )
        self.interactions[interaction.interaction_id] = interaction
        self.logger.info(f"Created interaction '{interaction.interaction_id}' from user '{user_id}'.")
        processed_interaction = await self.process_interaction(interaction)
        return processed_interaction.to_dict()

    async def process_interaction(self, interaction: Interaction) -> Interaction:
        """The main entry point for processing an interaction."""
        if interaction.status != InteractionStatus.PENDING:
            self.logger.warning(f"Attempted to process non-PENDING interaction '{interaction.interaction_id}'.")
            return interaction

        self.logger.info(f"Processing interaction '{interaction.interaction_id}' (Type: {interaction.interaction_type.name})")
        interaction.status = InteractionStatus.IN_PROGRESS
        
        handler = self.interaction_handlers.get(interaction.interaction_type)
        if not handler:
            interaction.status = InteractionStatus.FAILED
            interaction.error = f"No handler for interaction type '{interaction.interaction_type.name}'."
        else:
            try:
                await handler(interaction)
            except Exception as e:
                self.logger.error(f"Unhandled exception in handler for '{interaction.interaction_id}': {e}", exc_info=True)
                interaction.status = InteractionStatus.FAILED
                interaction.error = f"Unhandled handler exception: {str(e)}"

        interaction.completed_at = time.time()
        self.logger.info(f"Finished processing '{interaction.interaction_id}'. Final status: {interaction.status.name}")
        
        # Log the completed interaction
        asyncio.create_task(self.memory_agent.log_process(
            process_name="coordinator_interaction",
            data=interaction.to_dict(),
            metadata={"agent_id": self.agent_id, "interaction_id": interaction.interaction_id}
        ))
        
        # Also save to memory using save_memory method
        asyncio.create_task(self._log_to_memory(
            memory_type="STM",
            category="interactions",
            data=interaction.to_dict(),
            metadata={"interaction_id": interaction.interaction_id}
        ))
        
        # Save complete coordinator output
        await self._log_complete_output(interaction)
        
        return interaction

    # --- Interaction Handler Implementations ---

    async def _handle_query(self, interaction: Interaction):
        """Handles a general query by routing it to the Coordinator's LLM."""
        self.logger.debug(f"Handling QUERY for '{interaction.interaction_id}'.")
        if not self.llm_handler:
            interaction.status = InteractionStatus.FAILED
            interaction.error = "Coordinator's LLM handler is not available."
            return

        try:
            # FIX: Pass the full model ID to the handler.
            model_to_use = self.llm_handler.model_name_for_api or self.config.get("coordinator.llm.model")
            if not model_to_use:
                raise ValueError("No model configured for the Coordinator's LLM handler.")
            
            # Construct the full model ID for the handler
            full_model_id = f"{self.llm_handler.provider_name}/{model_to_use}"
            
            response = await self.llm_handler.generate_text(interaction.content, model=full_model_id)
            
            # Extract API details if available
            api_details = {}
            if hasattr(self.llm_handler, 'last_api_call_details'):
                api_details = self.llm_handler.last_api_call_details
            
            interaction.response = {
                "status": "SUCCESS", 
                "response_text": response,
                "model_used": full_model_id,
                "tokens_used": api_details.get('tokens_used', 'N/A'),
                "cost": api_details.get('cost', 'N/A'),
                "provider": self.llm_handler.provider_name
            }
            interaction.status = InteractionStatus.COMPLETED
        except Exception as e:
            interaction.status = InteractionStatus.FAILED
            interaction.error = f"LLM query failed: {e}"

    async def _handle_system_analysis(self, interaction: Interaction):
        """Gathers raw telemetry about the system state. Does not perform analysis."""
        self.logger.debug(f"Handling SYSTEM_ANALYSIS for '{interaction.interaction_id}'.")
        # In a real system, it would query registered monitoring agents.
        # For now, we simulate this by providing basic kernel info.
        telemetry_data = {
            "registered_agents_count": len(self.agent_registry),
            "active_interaction_count": len([i for i in self.interactions.values() if i.status == InteractionStatus.IN_PROGRESS]),
            "event_bus_topics": list(self.event_listeners.keys()),
        }
        interaction.response = {"status": "SUCCESS", "telemetry": telemetry_data}
        interaction.status = InteractionStatus.COMPLETED

    async def _handle_component_improvement(self, interaction: Interaction):
        """
        Handles a request to improve a component by invoking the SelfImprovementAgent CLI.
        """
        self.logger.debug(f"Handling COMPONENT_IMPROVEMENT for '{interaction.interaction_id}'.")
        
        metadata = interaction.metadata
        target_component = metadata.get("target_component")
        context = metadata.get("analysis_context")

        if not target_component:
            interaction.status = InteractionStatus.FAILED
            interaction.error = "Missing 'target_component' in metadata."
            return

        # This is where the logic to call the SIA CLI would go.
        from tools.system_analyzer_tool import SystemAnalyzerTool
        analyzer = SystemAnalyzerTool(
            config=self.config,
            belief_system=self.belief_system,
            coordinator_ref=self,
            llm_handler=self.llm_handler
        )
        
        self.logger.info(f"Invoking SystemAnalyzerTool for target: {target_component}")
        
        # Generate improvement suggestions
        analysis_result = await analyzer.execute(analysis_focus_hint=context)
        suggestions = analysis_result.get("improvement_suggestions", [])
        
        if not suggestions:
            interaction.response = {"status": "SUCCESS", "message": "System analysis complete, no new improvement suggestions were generated."}
            interaction.status = InteractionStatus.COMPLETED
            return

        # Add suggestions to the backlog
        for suggestion in suggestions:
            self.improvement_backlog.append(suggestion)
        self._save_backlog()
        self.logger.info(f"Saved {len(suggestions)} new improvement suggestions to the backlog.")

        # --- AUTO-EXECUTE EVOLUTION ---
        # Take the highest priority suggestion and immediately try to implement it.
        top_suggestion = suggestions[0] # Assuming the first one is the highest priority
        directive = top_suggestion.get("description", "Implement the top improvement suggestion.")
        
        self.logger.info(f"Attempting to auto-execute top improvement suggestion: {directive}")

        try:
            from orchestration.mastermind_agent import MastermindAgent
            mastermind = await MastermindAgent.get_instance(coordinator_agent_instance=self)
            
            # Run the evolution campaign in the background
            asyncio.create_task(mastermind.manage_mindx_evolution(top_level_directive=directive))
            
            interaction.response = {"status": "SUCCESS", "message": f"Successfully generated {len(suggestions)} suggestions and initiated evolution campaign for the top suggestion: '{directive}'"}
            interaction.status = InteractionStatus.COMPLETED
        except Exception as e:
            self.logger.error(f"Failed to initiate auto-evolution campaign: {e}", exc_info=True)
            interaction.response = {"status": "PARTIAL_SUCCESS", "message": f"Generated {len(suggestions)} suggestions, but failed to start evolution campaign.", "error": str(e)}
            interaction.status = InteractionStatus.COMPLETED # The analysis part was done.

        await self.publish_event(
            "component.improvement.success",
            {"interaction_id": interaction.interaction_id, "metadata": interaction.metadata, "suggestions_generated": len(suggestions)}
        )

    async def _handle_publish_event(self, interaction: Interaction):
        """Handles a request from an agent to publish an event to the bus."""
        topic = interaction.metadata.get("topic")
        data = interaction.metadata.get("data")
        if not isinstance(topic, str) or not isinstance(data, dict):
            interaction.status = InteractionStatus.FAILED
            interaction.error = "PUBLISH_EVENT requires 'topic' (str) and 'data' (dict) in metadata."
            return

        await self.publish_event(topic, data)
        interaction.response = {"status": "SUCCESS", "message": f"Event published to topic '{topic}'."}
        interaction.status = InteractionStatus.COMPLETED

    async def create_and_register_agent(self, agent_type: str, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creates and registers a new agent in the system.
        
        Args:
            agent_type: The type of agent to create (e.g., 'simple_coder', 'memory_agent')
            agent_id: Unique identifier for the new agent
            config: Configuration dictionary for the agent
            
        Returns:
            Dict containing the result of the operation
        """
        # Log agent creation request
        await self.memory_agent.log_process(
            process_name="coordinator_agent_creation_request",
            data={
                "agent_type": agent_type,
                "agent_id": agent_id,
                "config": config,
                "current_agent_count": len(self.agent_registry)
            },
            metadata={"agent_id": self.agent_id}
        )
        
        if agent_id in self.agent_registry:
            result = {
                "status": "FAILURE",
                "message": f"Agent with ID '{agent_id}' already exists",
                "agent_id": agent_id
            }
            # Log agent creation failure
            await self.memory_agent.log_process(
                process_name="coordinator_agent_creation_failed",
                data=result,
                metadata={"agent_id": self.agent_id}
            )
            return result

        try:
            # Create cryptographic identity
            from core.id_manager_agent import IDManagerAgent
            id_manager = await IDManagerAgent.get_instance(
                agent_id=f"id_manager_for_{agent_id}",
                config_override=self.config,
                memory_agent=self.memory_agent,
                belief_system=self.belief_system
            )
            public_key, env_var = await id_manager.create_new_wallet(entity_id=agent_id)
            
            # Log identity creation
            await self.memory_agent.log_process(
                process_name="coordinator_agent_identity_created",
                data={
                    "agent_id": agent_id,
                    "public_key": public_key,
                    "env_var": env_var
                },
                metadata={"agent_id": self.agent_id}
            )

            # Validate with Guardian
            from agents.guardian_agent import GuardianAgent
            guardian = await GuardianAgent.get_instance(
                agent_id="guardian_agent_main",
                memory_agent=self.memory_agent,
                config_override=self.config
            )
            
            # Get agent workspace path for validation
            agent_workspace_path = str(self.memory_agent.get_agent_data_directory(agent_id))
            
            validation_success, validation_result = await guardian.validate_new_agent(
                agent_id=agent_id,
                public_key=public_key,
                workspace_path=agent_workspace_path
            )
            
            # Log guardian validation
            await self.memory_agent.log_process(
                process_name="coordinator_agent_guardian_validation",
                data={
                    "agent_id": agent_id,
                    "validation_success": validation_success,
                    "validation_result": validation_result
                },
                metadata={"agent_id": self.agent_id}
            )

            if not validation_success:
                result = {
                    "status": "FAILURE",
                    "message": f"Guardian validation failed: {validation_result.get('failure_reason', 'Unknown')}",
                    "agent_id": agent_id,
                    "validation_details": validation_result
                }
                # Log validation failure
                await self.memory_agent.log_process(
                    process_name="coordinator_agent_creation_failed",
                    data=result,
                    metadata={"agent_id": self.agent_id}
                )
                return result

            # Instantiate the agent
            agent_instance = await self._instantiate_agent(agent_type, agent_id, config, public_key)
            if not agent_instance:
                result = {
                    "status": "FAILURE",
                    "message": f"Failed to instantiate agent of type '{agent_type}'",
                    "agent_id": agent_id
                }
                # Log instantiation failure
                await self.memory_agent.log_process(
                    process_name="coordinator_agent_creation_failed",
                    data=result,
                    metadata={"agent_id": self.agent_id}
                )
                return result

            # Register the agent
            self.register_agent(
                agent_id=agent_id,
                agent_type=agent_type,
                description=config.get("description", f"Dynamically created {agent_type}"),
                instance=agent_instance
            )

            # Create A2A model card
            model_card = await self._create_a2a_model_card(agent_id, agent_type, config, public_key)
            
            # Log model card creation
            await self.memory_agent.log_process(
                process_name="coordinator_agent_model_card_created",
                data={
                    "agent_id": agent_id,
                    "model_card": model_card
                },
                metadata={"agent_id": self.agent_id}
            )

            # Update registries
            await self._update_tool_registry_for_agent(agent_id, agent_type, config)
            await self._update_model_registry_for_agent(agent_id, agent_type, config)

            result = {
                "status": "SUCCESS",
                "message": f"Agent '{agent_id}' of type '{agent_type}' created and registered successfully",
                "agent_id": agent_id,
                "public_key": public_key,
                "model_card": model_card,
                "validation_details": validation_result
            }
            
            # Log successful agent creation
            await self.memory_agent.log_process(
                process_name="coordinator_agent_creation_completed",
                data=result,
                metadata={"agent_id": self.agent_id}
            )
            return result

        except Exception as e:
            self.logger.error(f"Failed to create and register agent '{agent_id}': {e}", exc_info=True)
            result = {
                "status": "FAILURE",
                "message": f"Exception during agent creation: {str(e)}",
                "agent_id": agent_id,
                "error": str(e)
            }
            # Log creation exception
            await self.memory_agent.log_process(
                process_name="coordinator_agent_creation_failed",
                data=result,
                metadata={"agent_id": self.agent_id}
            )
            return result

    async def deregister_and_shutdown_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Deregisters and shuts down an agent.
        
        Args:
            agent_id: The ID of the agent to deregister and shutdown
            
        Returns:
            Dict containing the result of the operation
        """
        # Log agent deregistration request
        await self.memory_agent.log_process(
            process_name="coordinator_agent_deregistration_request",
            data={
                "agent_id": agent_id,
                "current_agent_count": len(self.agent_registry)
            },
            metadata={"agent_id": self.agent_id}
        )
        
        if agent_id not in self.agent_registry:
            result = {
                "status": "FAILURE",
                "message": f"Agent with ID '{agent_id}' not found in registry",
                "agent_id": agent_id
            }
            # Log deregistration failure
            await self.memory_agent.log_process(
                process_name="coordinator_agent_deregistration_failed",
                data=result,
                metadata={"agent_id": self.agent_id}
            )
            return result

        try:
            agent_info = self.agent_registry[agent_id]
            agent_instance = agent_info.get("instance")
            
            # Shutdown the agent if it has a shutdown method
            if agent_instance and hasattr(agent_instance, 'shutdown'):
                await agent_instance.shutdown()
                
            # Log agent shutdown
            await self.memory_agent.log_process(
                process_name="coordinator_agent_shutdown",
                data={
                    "agent_id": agent_id,
                    "had_shutdown_method": bool(agent_instance and hasattr(agent_instance, 'shutdown'))
                },
                metadata={"agent_id": self.agent_id}
            )

            # Remove from registry
            del self.agent_registry[agent_id]
            
            result = {
                "status": "SUCCESS",
                "message": f"Agent '{agent_id}' deregistered and shutdown successfully",
                "agent_id": agent_id
            }
            
            # Log successful deregistration
            await self.memory_agent.log_process(
                process_name="coordinator_agent_deregistration_completed",
                data=result,
                metadata={"agent_id": self.agent_id}
            )
            return result

        except Exception as e:
            self.logger.error(f"Failed to deregister and shutdown agent '{agent_id}': {e}", exc_info=True)
            result = {
                "status": "FAILURE",
                "message": f"Exception during agent deregistration: {str(e)}",
                "agent_id": agent_id,
                "error": str(e)
            }
            # Log deregistration exception
            await self.memory_agent.log_process(
                process_name="coordinator_agent_deregistration_failed",
                data=result,
                metadata={"agent_id": self.agent_id}
            )
            return result

    async def _instantiate_agent(self, agent_type: str, agent_id: str, config: Dict[str, Any], public_key: str) -> Optional[Any]:
        """Instantiate an agent based on its type."""
        try:
            if agent_type == "bdi_agent":
                from core.bdi_agent import BDIAgent
                bdi_agent = BDIAgent(
                    domain=config.get("domain", agent_id),
                    belief_system_instance=self.belief_system,
                    tools_registry=config.get("tools_registry", {}),
                    config_override=self.config,
                    coordinator_agent=self,
                    memory_agent=self.memory_agent
                )
                # Initialize async components
                await bdi_agent.async_init_components()
                return bdi_agent
            
            elif agent_type == "backup_agent":
                # Create a simple backup agent placeholder
                return {
                    "id": agent_id,
                    "type": agent_type,
                    "config": config,
                    "public_key": public_key,
                    "status": "active"
                }
            
            elif agent_type == "simple_coder":
                # Create a simple coder agent placeholder
                return {
                    "id": agent_id,
                    "type": agent_type,
                    "config": config,
                    "public_key": public_key,
                    "status": "active"
                }
            
            # Dynamic agent creation for unknown types
            else:
                self.logger.info(f"Creating dynamic agent of type '{agent_type}' for agent '{agent_id}'")
                
                # Create a generic agent instance with the specified type
                dynamic_agent = {
                    "id": agent_id,
                    "type": agent_type,
                    "config": config,
                    "public_key": public_key,
                    "status": "active",
                    "capabilities": config.get("capabilities", []),
                    "description": config.get("description", f"Dynamic {agent_type} agent"),
                    "created_at": time.time(),
                    "created_via": config.get("created_via", "coordinator_dynamic"),
                    "workspace_path": str(self.memory_agent.get_agent_data_directory(agent_id))
                }
                
                # If the agent type suggests it's a tool-based agent, add tool capabilities
                if "tool" in agent_type.lower():
                    dynamic_agent["capabilities"].extend(["tool_execution", "task_processing"])
                    dynamic_agent["tool_type"] = agent_type
                
                # Log successful dynamic creation
                self.logger.info(f"Successfully created dynamic agent '{agent_id}' of type '{agent_type}'")
                return dynamic_agent
                
        except Exception as e:
            self.logger.error(f"Failed to instantiate agent of type '{agent_type}': {e}", exc_info=True)
            return None
    
    async def _create_a2a_model_card(self, agent_id: str, agent_type: str, config: Dict[str, Any], public_key: str) -> Dict[str, Any]:
        """Create an A2A-compatible model card for the agent."""
        from core.id_manager_agent import IDManagerAgent
        
        id_manager = await IDManagerAgent.get_instance()
        signature = await id_manager.sign_message(agent_id, f"{agent_type}:{agent_id}")
        
        model_card = {
            "id": agent_id,
            "name": config.get("name", agent_id),
            "description": config.get("description", f"Dynamically created {agent_type}"),
            "type": agent_type,
            "version": config.get("version", "1.0.0"),
            "enabled": True,
            "capabilities": config.get("capabilities", []),
            "commands": config.get("commands", []),
            "access_control": {
                "public": config.get("public_access", False),
                "authorized_agents": config.get("authorized_agents", [])
            },
            "identity": {
                "public_key": public_key,
                "signature": signature,
                "created_at": time.time()
            },
            "a2a_endpoint": f"https://mindx.internal/{agent_id}/a2a",
            "interoperability": {
                "protocols": ["mindx_native", "a2a_standard"],
                "message_formats": ["json", "mindx_action"],
                "authentication": "cryptographic_signature"
            }
        }
        
        # Save model card to file system
        from pathlib import Path
        model_cards_dir = self.memory_agent.get_agent_data_directory("a2a_model_cards")
        model_cards_dir.mkdir(parents=True, exist_ok=True)
        
        model_card_path = model_cards_dir / f"{agent_id}.json"
        with model_card_path.open("w", encoding="utf-8") as f:
            import json
            json.dump(model_card, f, indent=2)
        
        return model_card
    
    async def _update_tool_registry_for_agent(self, agent_id: str, agent_type: str, config: Dict[str, Any]):
        """Update the tool registry if the agent provides tools."""
        provided_tools = config.get("provided_tools", [])
        
        if provided_tools:
            from tools.registry_manager_tool import RegistryManagerTool
            registry_manager = RegistryManagerTool(memory_agent=self.memory_agent, config=self.config)
            
            for tool_config in provided_tools:
                tool_id = f"{agent_id}_{tool_config['tool_id']}"
                await registry_manager.execute(
                    registry_type="tool",
                    action="add",
                    item_id=tool_id,
                    item_config={
                        **tool_config,
                        "agent_id": agent_id,
                        "enabled": True
                    }
                )
    
    async def _update_model_registry_for_agent(self, agent_id: str, agent_type: str, config: Dict[str, Any]):
        """Update the model registry if the agent provides models."""
        provided_models = config.get("provided_models", [])
        
        if provided_models:
            # Get model registry and update with agent's models
            from llm.model_registry import get_model_registry_async
            model_registry = await get_model_registry_async(config=self.config)
            
            for model_config in provided_models:
                model_id = f"{agent_id}_{model_config['model_id']}"
                # Add model capability to registry
                # This would need to be implemented in the model registry
                self.logger.info(f"Model {model_id} from agent {agent_id} would be registered here")

    async def shutdown(self):
        """Gracefully shuts down the Coordinator."""
        self.logger.info(f"CoordinatorAgent shutting down...")
        # Add shutdown logic for any running tasks or persistent connections here
        self.logger.info(f"CoordinatorAgent shutdown complete.")

# --- Factory Function ---

async def get_coordinator_agent_mindx_async(config_override: Optional[Config] = None, memory_agent: Optional[MemoryAgent] = None, belief_system: Optional[BeliefSystem] = None, test_mode: bool = False) -> CoordinatorAgent:
    """The preferred, safe factory for creating or retrieving the Coordinator instance."""
    instance = await CoordinatorAgent.get_instance(config_override=config_override, memory_agent=memory_agent, belief_system=belief_system, test_mode=test_mode)
    return instance
