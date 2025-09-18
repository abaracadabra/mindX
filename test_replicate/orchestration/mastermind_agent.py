# orchestration/mastermind_agent.py

import os
import asyncio
import json
import time
import uuid
import re
import copy
import stat
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable, Awaitable, Union, Set

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
logger = get_logger(__name__)

from core.belief_system import BeliefSystem, BeliefSource
from llm.llm_interface import LLMHandlerInterface
from llm.llm_factory import create_llm_handler
from core.bdi_agent import BDIAgent, BaseTool as BDIBaseTool
from core.id_manager_agent import IDManagerAgent
from .coordinator_agent import CoordinatorAgent, InteractionType, InteractionStatus
from agents.memory_agent import MemoryAgent
from agents.automindx_agent import AutoMINDXAgent # Import the new agent

CodeBaseGenerator = None
try:
    from tools.base_gen_agent import BaseGenAgent as ImportedCodeBaseGenerator
    CodeBaseGenerator = ImportedCodeBaseGenerator
    logger.info("MastermindAgent: CodeBaseGenerator successfully imported.")
except ImportError:
    logger.warning("MastermindAgent: Could not import CodeBaseGenerator. Code analysis will be limited.")

class MastermindAgent:
    _instance = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls,
                           agent_id: str = "mastermind_prime",
                           config_override: Optional[Config] = None,
                           coordinator_agent_instance: Optional[CoordinatorAgent] = None,
                           memory_agent: Optional[MemoryAgent] = None,
                           model_registry: Optional[Any] = None, # Add model_registry
                           test_mode: bool = False,
                           extra_bdi_action_handlers: Optional[Dict[str, Callable]] = None,
                           **kwargs) -> 'MastermindAgent':
        async with cls._lock:
            if cls._instance is None or test_mode:
                if test_mode and cls._instance is not None:
                    await cls._instance.shutdown()
                
                cls._instance = cls(
                    agent_id=agent_id,
                    config_override=config_override,
                    coordinator_agent_instance=coordinator_agent_instance,
                    memory_agent=memory_agent,
                    model_registry=model_registry, # Pass to constructor
                    test_mode=test_mode,
                    **kwargs
                )
                await cls._instance._async_init_components()
                if extra_bdi_action_handlers:
                    for action_name, handler in extra_bdi_action_handlers.items():
                        cls._instance.bdi_agent.register_action(action_name, handler)
            return cls._instance

    def __init__(self,
                 agent_id: str = "mastermind_prime",
                 config_override: Optional[Config] = None,
                 coordinator_agent_instance: Optional[CoordinatorAgent] = None,
                 memory_agent: Optional[MemoryAgent] = None,
                 model_registry: Optional[Any] = None, # Add model_registry
                 test_mode: bool = False,
                 **kwargs):
        if hasattr(self, '_initialized_sync') and self._initialized_sync and not test_mode:
            return
            
        self.agent_id = agent_id
        self.config: Config = config_override or Config(test_mode=test_mode)
        self.belief_system: BeliefSystem = BeliefSystem(test_mode=test_mode)
        self.coordinator_agent: Optional[CoordinatorAgent] = coordinator_agent_instance
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.model_registry = model_registry
        self.test_mode = test_mode
        self.log_prefix = f"Mastermind ({self.agent_id} of mindX):"

        # The agent's data directory is now managed by MemoryAgent
        self.data_dir: Path = self.memory_agent.get_agent_data_directory(self.agent_id)

        self.tools_registry_file_path: Path = PROJECT_ROOT / self.config.get(f"mastermind_agent.{self.agent_id}.tools_registry_path", "data/config/official_tools_registry.json")
        self.tools_registry: Dict[str, Any] = self._load_tools_registry()

        self.llm_handler: Optional[LLMHandlerInterface] = None
        self.automindx_agent: Optional[AutoMINDXAgent] = None # Add instance variable

        # The BDI agent is now initialized in _async_init_components
        # after the AutoMINDX agent is available.
        self.bdi_agent: Optional[BDIAgent] = None

        self.code_base_analyzer: Optional[CodeBaseGenerator] = None # type: ignore
        if CodeBaseGenerator:
            try:
                self.code_base_analyzer = CodeBaseGenerator(
                    memory_agent=self.memory_agent,
                    agent_id=f"base_gen_for_{self.agent_id}"
                )
                logger.info(f"{self.log_prefix} CodeBaseGenerator initialized.")
            except Exception as e:
                logger.error(f"{self.log_prefix} Failed to initialize CodeBaseGenerator: {e}", exc_info=True)
        
        self.id_manager_agent: Optional[IDManagerAgent] = None
        self.strategic_evolution_agent: Optional[Any] = None # Add placeholder
        self.strategic_campaigns_history: List[Dict[str,Any]] = self._load_json_file("mastermind_campaigns_history.json", [])
        self.high_level_objectives: List[Dict[str,Any]] = self._load_json_file("mastermind_objectives.json", [])
        self.autonomous_loop_task: Optional[asyncio.Task] = None
        self._initialized_sync = True
        self._initialized_async = False

    async def _async_init_components(self):
        if self._initialized_async and not self.test_mode: return

        try:
            self.llm_handler = await create_llm_handler()
            if self.llm_handler: logger.info(f"{self.log_prefix} Internal LLM set to: {self.llm_handler.provider_name}/{self.llm_handler.model_name_for_api or 'default'}")
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to create Mastermind LLM handler: {e}", exc_info=True)

        # Initialize AutoMINDX first
        self.automindx_agent = await AutoMINDXAgent.get_instance(memory_agent=self.memory_agent, config_override=self.config)

        # Now initialize the BDI agent with the persona from AutoMINDX
        mastermind_persona = self.automindx_agent.get_persona("MASTERMIND")
        self.bdi_agent = BDIAgent(
            domain=f"mastermind_strategy_{self.agent_id}",
            belief_system_instance=self.belief_system,
            tools_registry=self.tools_registry,
            config_override=self.config,
            test_mode=self.test_mode,
            coordinator_agent=self.coordinator_agent,
            automindx_agent=self.automindx_agent,
            persona_prompt=mastermind_persona,
            mastermind_ref=self # Pass self-reference
        )
        await self.bdi_agent.async_init_components()
        self._register_mastermind_bdi_actions() # Move registration to after BDI agent is created

        try:
            self.id_manager_agent = await IDManagerAgent.get_instance(
                agent_id=f"id_manager_for_{self.agent_id}",
                config_override=self.config,
                memory_agent=self.memory_agent, # Pass the memory agent instance
                test_mode=self.test_mode
            )
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to initialize IDManagerAgent: {e}", exc_info=True)

        self._initialized_async = True
        if self.id_manager_agent:
            await self.id_manager_agent.create_new_wallet(entity_id=self.agent_id)
        
        # Instantiate the StrategicEvolutionAgent
        from learning.strategic_evolution_agent import StrategicEvolutionAgent
        self.strategic_evolution_agent = StrategicEvolutionAgent(
            agent_id="sea_for_mastermind",
            belief_system=self.belief_system,
            coordinator_agent=self.coordinator_agent,
            model_registry=self.model_registry,
            memory_agent=self.memory_agent,
            config_override=self.config
        )
        await self.strategic_evolution_agent._async_init()

        logger.info(f"{self.log_prefix} Asynchronously initialized.")

    def _load_json_file(self, file_name: str, default_value: Union[List, Dict]) -> Union[List, Dict]:
        file_path = self.data_dir / file_name
        if file_path.exists():
            try:
                with file_path.open("r", encoding="utf-8") as f: return json.load(f)
            except Exception as e: logger.error(f"Error loading {file_name}: {e}")
        return copy.deepcopy(default_value)

    def _save_json_file(self, file_name: str, data: Union[List, Dict]):
        file_path = self.data_dir / file_name
        try:
            with file_path.open("w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        except Exception as e: logger.error(f"Error saving {file_name}: {e}")

    def _load_tools_registry(self) -> Dict[str, Any]:
        if self.tools_registry_file_path.exists():
            try:
                with self.tools_registry_file_path.open("r", encoding="utf-8") as f: return json.load(f)
            except Exception as e: logger.error(f"Error loading tools registry: {e}. Starting empty.", exc_info=True)
        return {"registered_tools": {}}

    def _register_mastermind_bdi_actions(self):
        actions_to_register = {
            "ASSESS_TOOL_SUITE_EFFECTIVENESS": self._bdi_action_assess_tool_suite,
            "CONCEPTUALIZE_NEW_TOOL": self._bdi_action_conceptualize_new_tool,
            "PROPOSE_TOOL_STRATEGY": self._bdi_action_propose_tool_strategy,
            "CREATE_AGENT": self._bdi_action_create_agent,
            "DELETE_AGENT": self._bdi_action_delete_agent,
            "EVOLVE_AGENT": self._bdi_action_evolve_agent,
        }
        for action_name, handler in actions_to_register.items():
            self.bdi_agent.register_action(action_name, handler)
        
        logger.info(f"{self.log_prefix} Registered BDI action handlers, including tool and agent lifecycle management.")

    async def _bdi_action_assess_tool_suite(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        logger.info(f"{self.log_prefix} BDI Action: Assessing tool suite effectiveness.")
        
        # Log assessment start
        await self.memory_agent.log_process(
            process_name="mastermind_tool_assessment_start",
            data={"action": action, "tools_count": len(self.tools_registry.get("registered_tools", {}))},
            metadata={"agent_id": self.agent_id}
        )
        
        if not self.llm_handler: 
            await self.memory_agent.log_process(
                process_name="mastermind_tool_assessment_failed",
                data={"reason": "LLM not available"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "Mastermind LLM not available."
        
        tools_for_prompt = [{"id": tool_id, "description": data.get("description", "N/A")} for tool_id, data in self.tools_registry.get("registered_tools", {}).items()]
        prompt = (f"As a strategic AI, assess the current tool suite's effectiveness and identify gaps.\n"
                  f"Registered Tools:\n{json.dumps(tools_for_prompt, indent=2)}\n\n"
                  f"Provide your assessment in JSON format with keys 'overall_assessment' (string) and 'identified_gaps' (list of strings).")
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            assessment_result = json.loads(response_str)
            await self.belief_system.add_belief("assessment.tool_suite.latest", assessment_result)
            
            # Log successful assessment
            await self.memory_agent.log_process(
                process_name="mastermind_tool_assessment_completed",
                data={
                    "assessment_result": assessment_result,
                    "tools_analyzed": len(tools_for_prompt),
                    "gaps_identified": len(assessment_result.get("identified_gaps", []))
                },
                metadata={"agent_id": self.agent_id}
            )
            return True, assessment_result
        except Exception as e:
            # Log assessment failure
            await self.memory_agent.log_process(
                process_name="mastermind_tool_assessment_failed",
                data={"reason": "LLM error", "error": str(e)},
                metadata={"agent_id": self.agent_id}
            )
            return False, f"Tool assessment LLM error: {e}"

    async def _bdi_action_propose_tool_strategy(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        logger.info(f"{self.log_prefix} BDI Action: Proposing tool strategy.")
        
        # Log strategy proposal start
        await self.memory_agent.log_process(
            process_name="mastermind_strategy_proposal_start",
            data={"action": action},
            metadata={"agent_id": self.agent_id}
        )
        
        if not self.llm_handler: 
            await self.memory_agent.log_process(
                process_name="mastermind_strategy_proposal_failed",
                data={"reason": "LLM not available"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "Mastermind LLM not available."

        params = action.get("params", {})
        assessment_key = params.get("assessment_belief_key", "assessment.tool_suite.latest")
        assessment_belief = await self.belief_system.get_belief(assessment_key)
        assessment_text = json.dumps(assessment_belief.value) if assessment_belief else "No assessment provided."

        prompt = (f"Based on the following tool suite assessment, propose a list of concrete strategic actions (e.g., 'CONCEPTUALIZE_NEW_TOOL').\n"
                  f"Assessment: {assessment_text}\n\n"
                  f"Respond ONLY with a JSON object containing a 'recommendations' list.")
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            strategy = json.loads(response_str)
            await self.belief_system.add_belief("strategy.tool_proposal.latest", strategy)
            
            # Log successful strategy proposal
            await self.memory_agent.log_process(
                process_name="mastermind_strategy_proposal_completed",
                data={
                    "strategy": strategy,
                    "recommendations_count": len(strategy.get("recommendations", [])),
                    "assessment_used": bool(assessment_belief)
                },
                metadata={"agent_id": self.agent_id}
            )
            return True, strategy
        except Exception as e:
            # Log strategy proposal failure
            await self.memory_agent.log_process(
                process_name="mastermind_strategy_proposal_failed",
                data={"reason": "LLM error", "error": str(e)},
                metadata={"agent_id": self.agent_id}
            )
            return False, f"Tool strategy LLM error: {e}"

    async def _bdi_action_conceptualize_new_tool(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        logger.info(f"{self.log_prefix} BDI Action: Conceptualizing a new tool.")
        
        # Log conceptualization start
        await self.memory_agent.log_process(
            process_name="mastermind_tool_conceptualization_start",
            data={"action": action},
            metadata={"agent_id": self.agent_id}
        )
        
        if not self.llm_handler: 
            await self.memory_agent.log_process(
                process_name="mastermind_tool_conceptualization_failed",
                data={"reason": "LLM not available"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "Mastermind LLM not available."

        params = action.get("params", {})
        proposal_key = params.get("strategic_proposal_belief_key", "strategy.tool_proposal.latest")
        proposal_belief = await self.belief_system.get_belief(proposal_key)
        if not proposal_belief or not proposal_belief.value.get("recommendations"):
            await self.memory_agent.log_process(
                process_name="mastermind_tool_conceptualization_failed",
                data={"reason": "No strategic proposal found"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "No strategic proposal found in beliefs to act on."
        
        # Find the first recommendation to conceptualize a new tool
        recommendation = next((rec for rec in proposal_belief.value["recommendations"] if rec.get("action") == "CONCEPTUALIZE_NEW_TOOL"), None)
        if not recommendation:
            await self.memory_agent.log_process(
                process_name="mastermind_tool_conceptualization_failed",
                data={"reason": "No CONCEPTUALIZE_NEW_TOOL recommendation found"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "No 'CONCEPTUALIZE_NEW_TOOL' recommendation found in the latest strategy."
        
        identified_need = recommendation.get("target", "an identified strategic gap")

        prompt = (f"Define a concept for a new tool to address this need: '{identified_need}'.\n"
                  f"Provide a complete JSON object with all required keys for tool registration: "
                  f"'tool_id', 'display_name', 'description', 'module_path', 'class_name', 'capabilities' (list), "
                  f"'needs_identity' (bool), 'initial_version', 'initial_status', 'prompt_template_for_llm_interaction', and 'metadata'.")
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            tool_concept = json.loads(response_str)

            required_keys = ["tool_id", "display_name", "description", "module_path", "class_name", "capabilities"]
            if not all(k in tool_concept for k in required_keys):
                missing = [k for k in required_keys if k not in tool_concept]
                await self.memory_agent.log_process(
                    process_name="mastermind_tool_conceptualization_failed",
                    data={"reason": "Missing required keys", "missing_keys": missing},
                    metadata={"agent_id": self.agent_id}
                )
                raise ValueError(f"LLM tool concept missing required keys: {missing}")
            
            await self.belief_system.add_belief(f"mindx.new_tool_concept.{tool_concept['tool_id']}", tool_concept)
            
            # Log successful tool conceptualization
            await self.memory_agent.log_process(
                process_name="mastermind_tool_conceptualization_completed",
                data={
                    "tool_concept": tool_concept,
                    "identified_need": identified_need,
                    "tool_id": tool_concept['tool_id']
                },
                metadata={"agent_id": self.agent_id}
            )
            return True, tool_concept
        except Exception as e:
            # Log conceptualization failure
            await self.memory_agent.log_process(
                process_name="mastermind_tool_conceptualization_failed",
                data={"reason": "LLM error", "error": str(e)},
                metadata={"agent_id": self.agent_id}
            )
            return False, f"New tool conceptualization LLM error: {e}"

    async def _bdi_action_create_agent(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        params = action.get("params", {})
        agent_type = params.get("agent_type")
        agent_id = params.get("agent_id")
        agent_config = params.get("config", {})
        
        # Log agent creation start
        await self.memory_agent.log_process(
            process_name="mastermind_agent_creation_start",
            data={
                "agent_type": agent_type,
                "agent_id": agent_id,
                "config": agent_config
            },
            metadata={"agent_id": self.agent_id}
        )
        
        if not agent_type or not agent_id:
            await self.memory_agent.log_process(
                process_name="mastermind_agent_creation_failed",
                data={"reason": "Missing agent_type or agent_id"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "Missing agent_type or agent_id for CREATE_AGENT action."
        if not self.coordinator_agent:
            await self.memory_agent.log_process(
                process_name="mastermind_agent_creation_failed",
                data={"reason": "CoordinatorAgent not available"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "CoordinatorAgent is not available."
        
        result = await self.coordinator_agent.create_and_register_agent(agent_type, agent_id, agent_config)
        success = result.get("status") == "SUCCESS"
        
        # Log agent creation result
        await self.memory_agent.log_process(
            process_name="mastermind_agent_creation_completed",
            data={
                "success": success,
                "result": result,
                "agent_type": agent_type,
                "agent_id": agent_id
            },
            metadata={"agent_id": self.agent_id}
        )
        return success, result

    async def _bdi_action_delete_agent(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        params = action.get("params", {})
        agent_id = params.get("agent_id")
        
        # Log agent deletion start
        await self.memory_agent.log_process(
            process_name="mastermind_agent_deletion_start",
            data={"target_agent_id": agent_id},
            metadata={"agent_id": self.agent_id}
        )
        
        if not agent_id:
            await self.memory_agent.log_process(
                process_name="mastermind_agent_deletion_failed",
                data={"reason": "Missing agent_id"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "Missing agent_id for DELETE_AGENT action."
        if not self.coordinator_agent:
            await self.memory_agent.log_process(
                process_name="mastermind_agent_deletion_failed",
                data={"reason": "CoordinatorAgent not available"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "CoordinatorAgent is not available."
            
        result = await self.coordinator_agent.deregister_and_shutdown_agent(agent_id)
        success = result.get("status") == "SUCCESS"
        
        # Log agent deletion result
        await self.memory_agent.log_process(
            process_name="mastermind_agent_deletion_completed",
            data={
                "success": success,
                "result": result,
                "target_agent_id": agent_id
            },
            metadata={"agent_id": self.agent_id}
        )
        return success, result

    async def _bdi_action_evolve_agent(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        params = action.get("params", {})
        agent_id = params.get("agent_id")
        directive = params.get("directive")
        
        # Log agent evolution start
        await self.memory_agent.log_process(
            process_name="mastermind_agent_evolution_start",
            data={
                "target_agent_id": agent_id,
                "directive": directive
            },
            metadata={"agent_id": self.agent_id}
        )
        
        if not agent_id or not directive:
            await self.memory_agent.log_process(
                process_name="mastermind_agent_evolution_failed",
                data={"reason": "Missing agent_id or directive"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "Missing agent_id or directive for EVOLVE_AGENT action."
        if not self.coordinator_agent:
            await self.memory_agent.log_process(
                process_name="mastermind_agent_evolution_failed",
                data={"reason": "CoordinatorAgent not available"},
                metadata={"agent_id": self.agent_id}
            )
            return False, "CoordinatorAgent is not available."

        interaction = {
            "interaction_type": InteractionType.COMPONENT_IMPROVEMENT,
            "content": f"Evolve agent '{agent_id}' with directive: {directive}",
            "metadata": {"target_component": agent_id, "analysis_context": directive}
        }
        result = await self.coordinator_agent.handle_user_input(**interaction, user_id=self.agent_id)
        success = result.get("status") == "completed"
        
        # Log agent evolution result
        await self.memory_agent.log_process(
            process_name="mastermind_agent_evolution_completed",
            data={
                "success": success,
                "result": result,
                "target_agent_id": agent_id,
                "directive": directive
            },
            metadata={"agent_id": self.agent_id}
        )
        return success, result

    async def command_augmentic_intelligence(self, directive: str) -> Dict[str, Any]:
        return await self.manage_mindx_evolution(top_level_directive=directive)

    async def manage_mindx_evolution(self, top_level_directive: str, max_mastermind_bdi_cycles: int = 25) -> Dict[str, Any]:
        if not self._initialized_async: await self._async_init_components()
        if not self.bdi_agent or not self.coordinator_agent: return {"status": "FAILURE", "message": "BDI or Coordinator Agent not initialized."}

        run_id = f"mastermind_run_{str(uuid.uuid4())[:8]}"
        logger.info(f"{self.log_prefix} Starting evolution campaign (Run ID: {run_id}). Directive: '{top_level_directive}'")
        
        # --- Step 1: Analyze the system to get concrete suggestions ---
        logger.info(f"{self.log_prefix} Running SystemAnalyzerTool to generate a blueprint for the directive.")
        from tools.system_analyzer_tool import SystemAnalyzerTool
        analyzer = SystemAnalyzerTool(
            config=self.config,
            belief_system=self.belief_system,
            coordinator_ref=self.coordinator_agent,
            llm_handler=self.llm_handler
        )
        analysis_result = await analyzer.execute(analysis_focus_hint=top_level_directive)
        suggestions = analysis_result.get("improvement_suggestions", [])

        if not suggestions:
            logger.warning(f"{self.log_prefix} System analysis yielded no suggestions. Campaign ending.")
            return {"status": "SUCCESS", "message": "Analysis complete, no improvement actions to take."}

        # --- Step 2: Formulate a new goal based on the top suggestion ---
        top_suggestion = suggestions[0]
        concrete_directive = top_suggestion.get("description", top_level_directive)
        logger.info(f"{self.log_prefix} Top suggestion selected. New concrete directive: '{concrete_directive}'")

        self.bdi_agent.set_goal(
            goal_description=f"Implement the following evolution: {concrete_directive}",
            is_primary=True
        )
        
        # --- Step 3: Execute the BDI agent to implement the plan ---
        final_bdi_message = await self.bdi_agent.run(max_cycles=max_mastermind_bdi_cycles)
        
        is_success = "COMPLETED_GOAL_ACHIEVED" in final_bdi_message
        overall_status = "SUCCESS" if is_success else "FAILURE_OR_INCOMPLETE"
        
        logger.info(f"{self.log_prefix} Evolution campaign (Run ID: {run_id}) finished. BDI Message: {final_bdi_message}. Overall: {overall_status}")
        
        campaign_outcome = {"overall_campaign_status": overall_status, "final_bdi_message": final_bdi_message}
        self.strategic_campaigns_history.append({**campaign_outcome, "run_id": run_id, "directive": top_level_directive})
        self._save_json_file("mastermind_campaigns_history.json", self.strategic_campaigns_history)
        
        return campaign_outcome

    async def manage_agent_deployment(self, top_level_directive: str, max_mastermind_bdi_cycles: int = 25) -> Dict[str, Any]:
        """
        Manages a dynamic agent deployment based on a high-level user desire.
        This is the core function for the 'deploy' command.
        """
        if not self._initialized_async: await self._async_init_components()
        if not self.bdi_agent: return {"status": "FAILURE", "message": "BDI Agent not initialized."}

        run_id = f"mastermind_deploy_run_{str(uuid.uuid4())[:8]}"
        logger.info(f"{self.log_prefix} Starting agent deployment campaign (Run ID: {run_id}). Directive: '{top_level_directive}'")

        # The goal for the BDI agent is specifically framed around deployment
        self.bdi_agent.set_goal(
            goal_description=f"Create and orchestrate a set of agents to accomplish the following user desire: '{top_level_directive}'. The plan should include creating necessary agents, having them perform tasks, and then deleting them if they are temporary.",
            is_primary=True
        )

        final_bdi_message = await self.bdi_agent.run(max_cycles=max_mastermind_bdi_cycles)
        
        is_success = "COMPLETED_GOAL_ACHIEVED" in final_bdi_message
        overall_status = "SUCCESS" if is_success else "FAILURE_OR_INCOMPLETE"
        
        logger.info(f"{self.log_prefix} Deployment campaign (Run ID: {run_id}) finished. BDI Message: {final_bdi_message}. Overall: {overall_status}")
        
        campaign_outcome = {"overall_campaign_status": overall_status, "final_bdi_message": final_bdi_message}
        # Maybe save to a different history file? For now, use the same one.
        self.strategic_campaigns_history.append({**campaign_outcome, "run_id": run_id, "directive": top_level_directive, "type": "deployment"})
        self._save_json_file("mastermind_campaigns_history.json", self.strategic_campaigns_history)
        
        return campaign_outcome

    async def shutdown(self):
        logger.info(f"MastermindAgent '{self.agent_id}' shutting down...")
        if self.bdi_agent: await self.bdi_agent.shutdown()
        logger.info(f"MastermindAgent '{self.agent_id}' shutdown complete.")
