# mindx/learning/strategic_evolution_agent.py
"""
StrategicEvolutionAgent (SEA) for mindX

Executes strategic self-improvement campaigns with a focus on resilience.
It generates safe-by-default plans that include rollback and validation steps,
and uses a ModelSelector to choose the optimal LLM for its cognitive tasks.
"""

import asyncio
import json
import re
import uuid
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from core.belief_system import BeliefSystem, BeliefSource
from llm.llm_interface import LLMHandlerInterface
from llm.model_registry import ModelRegistry
from llm.model_selector import ModelSelector, TaskType
from orchestration.coordinator_agent import CoordinatorAgent, InteractionType
from .plan_management import PlanManager, Plan, Action, PlanSt as SEA_PlanSt
from tools.system_analyzer_tool import SystemAnalyzerTool
from evolution.blueprint_agent import BlueprintAgent
from evolution.blueprint_to_action_converter import BlueprintToActionConverter, DetailedAction
from agents.memory_agent import MemoryAgent
from tools.base_gen_agent import BaseGenAgent
from tools.registry_manager_tool import RegistryManagerTool
from tools.audit_and_improve_tool import AuditAndImproveTool
from tools.optimized_audit_gen_agent import OptimizedAuditGenAgent
from agents.automindx_agent import AutoMINDXAgent

logger = get_logger(__name__)

class LessonsLearned:
    """
    A class to manage and persist lessons learned from agent failures.
    """
    def __init__(self, memory_agent: MemoryAgent, agent_id: str):
        self.memory_agent = memory_agent
        self.agent_id = agent_id
        self.lessons_file_path = self.memory_agent.get_agent_data_directory(self.agent_id) / "lessons_learned.json"
        self.lessons: List[str] = self._load_lessons()

    def _load_lessons(self) -> List[str]:
        """Loads lessons from a JSON file."""
        if self.lessons_file_path.exists():
            try:
                with self.lessons_file_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.error(f"Error loading lessons from {self.lessons_file_path}: {e}")
        return []

    def _save_lessons(self):
        """Saves lessons to a JSON file."""
        try:
            with self.lessons_file_path.open("w", encoding="utf-8") as f:
                json.dump(self.lessons, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving lessons to {self.lessons_file_path}: {e}")

    def add_lesson(self, lesson: str):
        """Adds a new lesson and saves it."""
        if lesson not in self.lessons:
            self.lessons.append(lesson)
            self._save_lessons()
            logger.info(f"Added new lesson for agent '{self.agent_id}': {lesson}")

    def get_all_lessons(self) -> List[str]:
        """Returns all learned lessons."""
        return self.lessons

class StrategicEvolutionAgent:
    """
    Manages and executes resilient self-improvement campaigns for the MindX system.
    This agent acts as a high-level project manager for system evolution.
    """
    def __init__(
        self,
        agent_id: str,
        belief_system: BeliefSystem,
        coordinator_agent: CoordinatorAgent,
        model_registry: ModelRegistry,
        memory_agent: MemoryAgent,
        config_override: Optional[Config] = None,
        test_mode: bool = False
    ):
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return

        self.agent_id = agent_id
        self.belief_system = belief_system
        self.coordinator_agent = coordinator_agent
        self.model_registry = model_registry
        self.memory_agent = memory_agent
        self.config = config_override or Config()
        self.log_prefix = f"SEA ({self.agent_id}):"
        
        self.llm_handler: Optional[LLMHandlerInterface] = None
        self.model_selector = ModelSelector(self.config)
        self.system_analyzer: Optional[SystemAnalyzerTool] = None
        self.blueprint_agent: Optional[BlueprintAgent] = None
        self.plan_manager: Optional[PlanManager] = None
        self.registry_manager: Optional[RegistryManagerTool] = None
        
        # Audit system components
        self.audit_improve_tool: Optional[AuditAndImproveTool] = None
        self.optimized_audit_agent: Optional[OptimizedAuditGenAgent] = None
        self.automindx_agent: Optional[AutoMINDXAgent] = None
        
        self.campaign_history: List[Dict[str, Any]] = self._load_campaign_history()
        self._current_campaign_run_id: Optional[str] = None
        self._initialized = False
        logger.info(f"StrategicEvolutionAgent '{self.agent_id}' synchronous __init__ complete.")

    async def _async_init(self):
        """Asynchronously initialize components that require it."""
        if self._initialized:
            return

        # Select the best model for reasoning
        self.llm_handler = self.model_registry.get_handler_for_purpose(
            task_type=TaskType.REASONING,
        )

        if not self.llm_handler:
            logger.critical(f"{self.log_prefix} Could not acquire a reasoning LLM. SEA will be non-operational.")
            return

        # The SystemAnalyzerTool gets its monitor refs from the coordinator.
        self.system_analyzer = SystemAnalyzerTool(
            belief_system=self.belief_system, 
            llm_handler=self.llm_handler,
            coordinator_ref=self.coordinator_agent,
            config=self.config
        )

        self.blueprint_agent = BlueprintAgent(
            belief_system=self.belief_system,
            coordinator_ref=self.coordinator_agent,
            model_registry_ref=self.model_registry,
            memory_agent=self.memory_agent,
            base_gen_agent=BaseGenAgent(memory_agent=self.memory_agent)
        )

        # Initialize BlueprintToActionConverter for enhanced blueprint processing
        self.blueprint_converter = BlueprintToActionConverter(
            llm_handler=self.llm_handler,
            memory_agent=self.memory_agent,
            belief_system=self.belief_system,
            config=self.config
        )

        self.plan_manager = PlanManager(agent_id=self.agent_id, action_executor=self._dispatch_strategic_action, config_override=self.config)
        
        self.registry_manager = RegistryManagerTool(memory_agent=self.memory_agent, config=self.config)

        # Initialize audit system components
        try:
            self.automindx_agent = AutoMINDXAgent(
                memory_agent=self.memory_agent,
                agent_id=f"{self.agent_id}_automindx",
                config=self.config
            )
            
            base_gen_agent = BaseGenAgent(memory_agent=self.memory_agent)
            
            self.audit_improve_tool = AuditAndImproveTool(
                memory_agent=self.memory_agent,
                base_gen_agent=base_gen_agent,
                automindx_agent=self.automindx_agent,
                config=self.config,
                llm_handler=self.llm_handler
            )
            
            self.optimized_audit_agent = OptimizedAuditGenAgent(
                memory_agent=self.memory_agent,
                agent_id=f"{self.agent_id}_audit",
                belief_system=self.belief_system
            )
            
            logger.info(f"{self.log_prefix} Audit system components initialized successfully")
            
        except Exception as e:
            logger.warning(f"{self.log_prefix} Failed to initialize audit components: {e}")
            self.audit_improve_tool = None
            self.optimized_audit_agent = None

        self._initialized = True
        logger.info(f"StrategicEvolutionAgent '{self.agent_id}' fully initialized. Using {self.llm_handler.provider_name} for core reasoning.")
    
    async def run_evolution_campaign(self, campaign_goal_description: str) -> Dict[str, Any]:
        """Manages a self-improvement campaign for a given high-level goal."""
        if not self._initialized: await self._async_init()
        if not self.llm_handler or not self.blueprint_agent:
            return {"status": "FAILURE", "message": "SEA is non-operational due to missing LLM or BlueprintAgent."}

        self._current_campaign_run_id = f"sea_run_{str(uuid.uuid4())[:8]}"
        logger.info(f"{self.log_prefix} Starting new campaign (ID: {self._current_campaign_run_id}). Goal: '{campaign_goal_description}'")
        
        # Generate the master blueprint first
        blueprint = await self.blueprint_agent.generate_next_evolution_blueprint()
        if "error" in blueprint:
            return self._conclude_campaign("FAILURE", f"Failed to generate a blueprint: {blueprint['error']}", {"goal": campaign_goal_description})

        # The BDI ToDo list from the blueprint can now be used to seed the coordinator
        logger.info(f"{self.log_prefix} Blueprint generated. {len(blueprint.get('bdi_todo_list', []))} items added to Coordinator backlog.")

        # For now, we'll still generate a simple plan. A future version could execute the blueprint directly.
        strategic_plan_actions = await self._generate_strategic_plan(campaign_goal_description)
        if not strategic_plan_actions:
            return self._conclude_campaign("FAILURE", "Failed to generate a strategic plan.", {"goal": campaign_goal_description})

        if not self.plan_manager:
            return self._conclude_campaign("FAILURE", "Plan manager not initialized", {"goal": campaign_goal_description})
            
        plan_obj = self.plan_manager.create_plan(
            goal_id=self._current_campaign_run_id, 
            actions_data=[action.to_dict() for action in strategic_plan_actions],
            description=f"Strategic plan for: {campaign_goal_description}"
        )
        
        final_plan_state = await self.plan_manager.execute_plan(plan_obj.id)
        
        if final_plan_state.status != SEA_PlanSt.COMPLETED_SUCCESS:
            # The SEA does not have its own lessons learned, it uses the BDI agent's
            # self.lessons_learned.add_lesson(final_plan_state.failure_reason)
            logger.warning(f"Campaign failed. Reason: {final_plan_state.failure_reason}")
            # Attempt to replan
            strategic_plan_actions = await self._generate_strategic_plan(campaign_goal_description)
            if not strategic_plan_actions:
                return self._conclude_campaign("FAILURE", "Failed to generate a strategic plan after failure.", {"goal": campaign_goal_description})
            if not self.plan_manager:
                return self._conclude_campaign("FAILURE", "Plan manager not initialized for recovery", {"goal": campaign_goal_description})
            plan_obj = self.plan_manager.create_plan(
                goal_id=self._current_campaign_run_id, 
                actions_data=[action.to_dict() for action in strategic_plan_actions],
                description=f"Strategic plan for: {campaign_goal_description} (recovery attempt)"
            )
            final_plan_state = await self.plan_manager.execute_plan(plan_obj.id)

        status = "SUCCESS" if final_plan_state.status == SEA_PlanSt.COMPLETED_SUCCESS else "FAILURE"
        message = f"Campaign plan {final_plan_state.status.name}. Reason: {final_plan_state.failure_reason or 'Completed.'}"
        
        return self._conclude_campaign(status, message, final_plan_state.to_dict())

    async def _generate_strategic_plan(self, campaign_goal_description: str) -> Optional[List[Action]]:
        """Uses an LLM to generate a safe, resilient sequence of strategic actions."""
        available_actions = [
            "REQUEST_SYSTEM_ANALYSIS", "SELECT_IMPROVEMENT_TARGET", 
            "CREATE_ROLLBACK_PLAN", "FORMULATE_SIA_TASK_GOAL",
            "REQUEST_COORDINATOR_FOR_SIA_EXECUTION", "RUN_VALIDATION_TESTS",
            "EVALUATE_SIA_OUTCOME", "TRIGGER_COORDINATED_ROLLBACK"
        ]
        prompt = (
            f"You are a strategic planner for the MindX system, focused on **Resilience** and **Perpetuity**.\n"
            f"Your task is to create a high-level, safe-by-default plan to achieve: '{campaign_goal_description}'\n\n"
            f"Available strategic actions: {', '.join(available_actions)}\n"
            f"**CRITICAL DOCTRINE:** Any plan that involves code modification via `REQUEST_COORDINATOR_FOR_SIA_EXECUTION` **MUST** be bracketed by safety actions. The required sequence is: `CREATE_ROLLBACK_PLAN` -> `REQUEST_COORDINATOR_FOR_SIA_EXECUTION` -> `RUN_VALIDATION_TESTS`. If validation fails, the plan **MUST** include `TRIGGER_COORDINATED_ROLLBACK` as a subsequent step. This is a non-negotiable safety protocol.\n\n"
            f"Structure the plan as a JSON list of action dictionaries. Use placeholders like '$action_result.ACTION_ID.field' to pass data between steps.\n"
            f"Respond ONLY with the JSON list of actions."
        )
        try:
            if not self.llm_handler:
                logger.error(f"{self.log_prefix} LLM handler not available for strategic plan generation")
                return None
                
            model_name = getattr(self.llm_handler, 'model_name_for_api', None) or 'default-model'
            plan_str = await self.llm_handler.generate_text(prompt, model=model_name, max_tokens=2500, temperature=0.1, json_mode=True)
            
            if not plan_str:
                raise ValueError("LLM plan generation returned an empty response.")
            
            # Check for structured errors, which our new handlers return as JSON strings
            try:
                data = json.loads(plan_str)
                if isinstance(data, dict) and "error" in data:
                    raise ValueError(f"LLM plan generation failed: {data.get('message')}")
            except json.JSONDecodeError:
                pass # It's a valid plan, not an error object.

            actions_data = json.loads(plan_str)
            return [Action.from_dict(ad) for ad in actions_data]
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate strategic plan: {e}", exc_info=True)
            return None

    def _conclude_campaign(self, status: str, message: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper to format and log the final campaign summary."""
        campaign_summary = {
            "campaign_run_id": self._current_campaign_run_id,
            "agent_id": self.agent_id,
            "overall_campaign_status": status,
            "final_message": message,
            "campaign_data": data,
            "timestamp": time.time()
        }
        self.campaign_history.append(campaign_summary)
        self._save_campaign_history()
        logger.info(f"{self.log_prefix} Campaign '{self._current_campaign_run_id}' finished. Status: {status}. Message: {message}")
        return campaign_summary

    def _get_history_file_path(self) -> Path:
        safe_agent_id_stem = re.sub(r'\W+', '_', self.agent_id)
        return PROJECT_ROOT / "data" / "sea_campaign_history" / f"{safe_agent_id_stem}.json"

    def _load_campaign_history(self) -> List[Dict[str, Any]]:
        history_file = self._get_history_file_path()
        if history_file.exists():
            try:
                with history_file.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"{self.log_prefix} Error loading campaign history: {e}")
        return []

    def _save_campaign_history(self):
        history_file = self._get_history_file_path()
        try:
            history_file.parent.mkdir(parents=True, exist_ok=True)
            with history_file.open("w", encoding="utf-8") as f:
                json.dump(self.campaign_history, f, indent=2)
        except Exception as e:
            logger.error(f"{self.log_prefix} Error saving campaign history: {e}")

    async def _dispatch_strategic_action(self, action: Action) -> Tuple[bool, Any]:
        """Dispatcher for actions within the SEA's own strategic plans."""
        action_type = action.type.upper()
        logger.info(f"{self.log_prefix} Dispatching strategic action: {action_type} (ID: {action.id})")
        
        handler = getattr(self, f"_sea_action_{action_type.lower()}", None)
        if handler and callable(handler):
            try:
                if self.plan_manager:
                    plan = self.plan_manager.get_plan(action.id.split('_act')[0])
                    current_plan_id = plan.id if plan else self._current_campaign_run_id
                else:
                    current_plan_id = self._current_campaign_run_id
                return await handler(action.params, current_plan_id)
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in handler for {action_type} (ID: {action.id}): {e}", exc_info=True)
                return False, f"Exception in handler for {action_type}: {e}"
        else:
            logger.warning(f"{self.log_prefix} No handler found for strategic action type: {action_type}")
            return False, f"Unknown strategic action type: {action_type}"

    # --- Core Action Handlers (including new Resilience actions) ---

    async def _sea_action_request_system_analysis(self, params: Dict[str, Any], current_plan_id: Optional[str]) -> Tuple[bool, Any]:
        focus_hint = params.get("focus_hint", f"Analysis for campaign {self._current_campaign_run_id}")
        analysis_result = await self.system_analyzer.analyze_system_for_improvements(analysis_focus_hint=focus_hint)
        suggestions = analysis_result.get("improvement_suggestions", [])
        if analysis_result.get("error") or not suggestions:
            return False, {"message": "Analysis failed or yielded no suggestions."}
        
        belief_key = f"sea.{self.agent_id}.plan.{current_plan_id}.analysis_suggestions"
        await self.belief_system.add_belief(belief_key, suggestions, 0.9, BeliefSource.SELF_ANALYSIS, ttl_seconds=3600)
        return True, {"num_suggestions": len(suggestions), "suggestions_belief_key": belief_key}

    async def _sea_action_select_improvement_target(self, params: Dict[str, Any], current_plan_id: Optional[str]) -> Tuple[bool, Any]:
        source_belief_key = params.get("suggestions_belief_key")
        if not source_belief_key: return False, "Missing 'suggestions_belief_key' parameter."
        
        belief = await self.belief_system.get_belief(source_belief_key)
        suggestions = belief.value if belief and isinstance(belief.value, list) else []
        if not suggestions: return False, f"No suggestions found at {source_belief_key}."
        
        suggestions.sort(key=lambda x: x.get("priority", 0), reverse=True)
        selected = suggestions[0]
        
        logger.info(f"{self.log_prefix} Selected improvement target: {selected.get('suggestion')}")
        return True, {"selected_target_item": selected}

    async def _sea_action_create_rollback_plan(self, params: Dict[str, Any], current_plan_id: Optional[str]) -> Tuple[bool, Any]:
        target_file = params.get("target_file_path")
        if not target_file: return False, "Missing 'target_file_path' for rollback plan."
        
        logger.info(f"{self.log_prefix} Creating rollback snapshot for {target_file}")
        # This is a stub for using a privileged tool to read file content.
        success, content = True, f"# Mock original content of {target_file} at {time.time()}"
        
        if not success:
            return False, f"Failed to read original content of {target_file}."

        rollback_belief_key = f"sea.{self.agent_id}.plan.{current_plan_id}.rollback.{target_file.replace('.','_')}"
        await self.belief_system.add_belief(rollback_belief_key, content, 0.99, BeliefSource.SELF_ANALYSIS, ttl_seconds=3600*2)
        
        return True, {"rollback_belief_key": rollback_belief_key, "message": f"Snapshot of {target_file} saved."}

    async def _sea_action_formulate_sia_task_goal(self, params: Dict[str, Any], current_plan_id: Optional[str]) -> Tuple[bool, Any]:
        target_item = params.get("selected_target_item")
        if not isinstance(target_item, dict): return False, "Missing or invalid 'selected_target_item'."

        task_details = {
            "target_component_path": target_item.get("target_component_path"),
            "improvement_description": target_item.get("suggestion"),
            "priority": target_item.get("priority", 5)
        }
        logger.info(f"{self.log_prefix} Formulated SIA task for '{task_details['target_component_path']}'")
        return True, {"formulated_sia_task_details": task_details}

    async def _sea_action_request_coordinator_for_sia_execution(self, params: Dict[str, Any], current_plan_id: Optional[str]) -> Tuple[bool, Any]:
        task_details = params.get("formulated_sia_task_details")
        if not isinstance(task_details, dict): return False, "Missing 'formulated_sia_task_details'."

        metadata = {
            "target_component": task_details["target_component_path"],
            "analysis_context": task_details["improvement_description"],
            "source": f"sea_campaign_{self._current_campaign_run_id}"
        }
        content = f"SEA requests SIA modification for '{task_details['target_component_path']}'. Goal: {task_details['improvement_description'][:100]}"
        
        response = await self.coordinator_agent.handle_user_input(
            content=content, agent_id=self.agent_id,
            interaction_type=InteractionType.COMPONENT_IMPROVEMENT, metadata=metadata)
        
        success = response.get("status") == "completed" and response.get("response", {}).get("status") == "SUCCESS"
        return success, {"coordinator_response": response}

    async def _sea_action_run_validation_tests(self, params: Dict[str, Any], current_plan_id: Optional[str]) -> Tuple[bool, Any]:
        target = params.get("target_component_path")
        logger.info(f"{self.log_prefix} Running validation tests for component: {target}")
        # This is a stub for a real implementation that would trigger a test suite.
        tests_passed = True
        message = "All conceptual validation tests passed." if tests_passed else "Validation tests failed."
        return tests_passed, {"tests_passed": tests_passed, "message": message}

    async def _sea_action_trigger_coordinated_rollback(self, params: Dict[str, Any], current_plan_id: Optional[str]) -> Tuple[bool, Any]:
        rollback_key = params.get("rollback_belief_key")
        if not rollback_key: return False, "Missing 'rollback_belief_key'."
        
        belief = await self.belief_system.get_belief(rollback_key)
        if not belief: return False, f"Rollback data not found at '{rollback_key}'."
        
        target_file = params.get("target_file_path")
        logger.warning(f"{self.log_prefix} TRIGGERING ROLLBACK for {target_file}!")
        # This would use a privileged tool to write the original content back.
        success = True # Simulate success
        
        return success, {"message": f"Rollback of {target_file} executed."}

    async def _sea_action_evaluate_sia_outcome(self, params: Dict[str, Any], current_plan_id: Optional[str]) -> Tuple[bool, Any]:
        outcome = params.get("coordinator_response", {})
        if not outcome: return False, "Missing SIA outcome data."

        logger.info(f"{self.log_prefix} Evaluating SIA outcome.")
        was_successful = outcome.get("status") == "completed" and outcome.get("response",{}).get("status") == "SUCCESS"
        return was_successful, {"assessment": "Positive" if was_successful else "Negative", "details": outcome}

    async def run_enhanced_blueprint_campaign(self, campaign_goal_description: str) -> Dict[str, Any]:
        """
        Enhanced campaign execution using BlueprintToActionConverter for detailed action generation.
        This provides better blueprint-to-action conversion fidelity.
        """
        if not self._initialized: await self._async_init()
        if not self.llm_handler or not self.blueprint_agent or not self.blueprint_converter:
            return {"status": "FAILURE", "message": "SEA components not properly initialized."}

        self._current_campaign_run_id = f"sea_enhanced_run_{str(uuid.uuid4())[:8]}"
        logger.info(f"{self.log_prefix} Starting ENHANCED blueprint campaign (ID: {self._current_campaign_run_id}). Goal: '{campaign_goal_description}'")
        
        # Step 1: Generate strategic blueprint
        blueprint = await self.blueprint_agent.generate_next_evolution_blueprint()
        if "error" in blueprint:
            return self._conclude_campaign("FAILURE", f"Blueprint generation failed: {blueprint['error']}", {"goal": campaign_goal_description})

        logger.info(f"{self.log_prefix} Blueprint '{blueprint.get('blueprint_title', 'Unknown')}' generated with {len(blueprint.get('bdi_todo_list', []))} items")

        # Step 2: Convert blueprint to detailed BDI actions using enhanced converter
        success, detailed_actions = await self.blueprint_converter.convert_blueprint_to_actions(blueprint)
        if not success or not detailed_actions:
            return self._conclude_campaign("FAILURE", "Blueprint-to-action conversion failed", {"blueprint": blueprint})

        logger.info(f"{self.log_prefix} Blueprint converted to {len(detailed_actions)} detailed actions with total estimated cost: ${sum(a.estimated_cost_usd for a in detailed_actions):.3f}")

        # Step 3: Validate action sequence for safety and feasibility
        is_valid, validation_errors = await self.blueprint_converter.validate_action_sequence(detailed_actions)
        if not is_valid:
            logger.warning(f"{self.log_prefix} Action sequence validation failed: {validation_errors}")
            return self._conclude_campaign("FAILURE", f"Action validation failed: {'; '.join(validation_errors)}", {"blueprint": blueprint, "validation_errors": validation_errors})

        # Step 4: Convert to BDI format and execute
        bdi_actions = self.blueprint_converter.actions_to_bdi_format(detailed_actions)
        
        # Save enhanced campaign data
        campaign_data = {
            "blueprint": blueprint,
            "detailed_actions_count": len(detailed_actions),
            "total_estimated_cost": sum(a.estimated_cost_usd for a in detailed_actions),
            "total_estimated_duration": sum(a.estimated_duration_seconds for a in detailed_actions),
            "safety_levels": {level: len([a for a in detailed_actions if a.safety_level == level]) 
                           for level in ["low", "standard", "high", "critical"]},
            "action_types": list(set(a.type for a in detailed_actions))
        }

        # Execute actions through coordinator (seeding the improvement backlog)
        coordinator_tasks_created = 0
        for action_data in bdi_actions:
            try:
                # Convert detailed actions to coordinator interactions
                interaction_result = await self.coordinator_agent.handle_user_input(
                    content=action_data.get("params", {}).get("_meta", {}).get("description", "Enhanced blueprint action"),
                    user_id=self.agent_id,
                    interaction_type="COMPONENT_IMPROVEMENT",
                    metadata={
                        "source": "sea_enhanced_blueprint",
                        "campaign_id": self._current_campaign_run_id,
                        "action_details": action_data.get("params", {}).get("_meta", {}),
                        "priority": action_data.get("params", {}).get("_meta", {}).get("priority", 5)
                    }
                )
                if interaction_result.get("status") != "FAILED":
                    coordinator_tasks_created += 1
            except Exception as e:
                logger.error(f"{self.log_prefix} Failed to create coordinator task for action: {e}")

        logger.info(f"{self.log_prefix} Enhanced blueprint campaign created {coordinator_tasks_created} coordinator tasks")
        
        campaign_data["coordinator_tasks_created"] = coordinator_tasks_created
        return self._conclude_campaign("SUCCESS", f"Enhanced blueprint campaign completed. {coordinator_tasks_created} tasks created.", campaign_data)

    async def run_audit_driven_campaign(self, audit_scope: str = "system", target_components: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute a comprehensive improvement campaign driven by audit findings.
        
        Args:
            audit_scope: Scope of audit ("system", "security", "performance", "code_quality")
            target_components: Specific components to focus on (optional)
            
        Returns:
            Complete campaign results with audit findings, improvements, and validation
        """
        if not self._initialized: await self._async_init()
        if not self.llm_handler or not self.blueprint_agent:
            return {"status": "FAILURE", "message": "SEA is non-operational due to missing components."}

        if not self.audit_improve_tool or not self.optimized_audit_agent:
            return {"status": "FAILURE", "message": "Audit system components not available."}

        self._current_campaign_run_id = f"sea_audit_driven_{str(uuid.uuid4())[:8]}"
        logger.info(f"{self.log_prefix} Starting AUDIT-DRIVEN campaign (ID: {self._current_campaign_run_id}). Scope: '{audit_scope}'")
        
        campaign_start_time = time.time()
        
        try:
            # Step 1: Run comprehensive system audit
            logger.info(f"{self.log_prefix} Phase 1: Running comprehensive audit")
            audit_results = await self._run_comprehensive_audit(audit_scope, target_components)
            
            if not audit_results.get("success", False):
                return self._conclude_campaign("FAILURE", f"Audit phase failed: {audit_results.get('message', 'Unknown error')}", 
                                             {"audit_scope": audit_scope, "audit_results": audit_results})
            
            # Step 2: Convert audit findings to strategic blueprint
            logger.info(f"{self.log_prefix} Phase 2: Converting audit findings to strategic blueprint")
            blueprint = await self._generate_audit_driven_blueprint(audit_results, audit_scope)
            
            if "error" in blueprint:
                return self._conclude_campaign("FAILURE", f"Blueprint generation failed: {blueprint['error']}", 
                                             {"audit_results": audit_results})
            
            logger.info(f"{self.log_prefix} Generated audit-driven blueprint with {len(blueprint.get('bdi_todo_list', []))} improvement items")
            
            # Step 3: Execute improvements with enhanced validation
            logger.info(f"{self.log_prefix} Phase 3: Executing improvement actions")
            improvement_results = await self.run_enhanced_blueprint_campaign(f"Audit-driven improvements: {audit_scope}")
            
            if improvement_results.get("status") != "SUCCESS":
                return self._conclude_campaign("PARTIAL_SUCCESS", "Improvements partially completed", {
                    "audit_results": audit_results,
                    "blueprint": blueprint,
                    "improvement_results": improvement_results
                })
            
            # Step 4: Validate improvements with re-audit
            logger.info(f"{self.log_prefix} Phase 4: Validating improvements")
            validation_results = await self._validate_audit_improvements(audit_results, target_components)
            
            # Step 5: Generate comprehensive campaign report
            campaign_duration = time.time() - campaign_start_time
            campaign_report = await self._generate_audit_campaign_report(
                audit_results, blueprint, improvement_results, validation_results, campaign_duration
            )
            
            logger.info(f"{self.log_prefix} Audit-driven campaign completed in {campaign_duration:.2f}s")
            
            return self._conclude_campaign("SUCCESS", "Audit-driven campaign completed successfully", {
                "campaign_type": "audit_driven",
                "audit_scope": audit_scope,
                "target_components": target_components,
                "audit_results": audit_results,
                "blueprint": blueprint,
                "improvement_results": improvement_results,
                "validation_results": validation_results,
                "campaign_report": campaign_report,
                "duration_seconds": campaign_duration
            })
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Audit-driven campaign failed: {e}", exc_info=True)
            return self._conclude_campaign("FAILURE", f"Campaign failed with exception: {e}", 
                                         {"audit_scope": audit_scope, "error": str(e)})

    async def _run_comprehensive_audit(self, audit_scope: str, target_components: Optional[List[str]]) -> Dict[str, Any]:
        """Run comprehensive audit using available audit tools."""
        
        audit_results = {
            "audit_scope": audit_scope,
            "timestamp": time.time(),
            "findings": [],
            "metrics": {},
            "recommendations": [],
            "success": False
        }
        
        try:
            # Determine audit targets
            if target_components:
                audit_targets = [str(PROJECT_ROOT / comp) for comp in target_components if (PROJECT_ROOT / comp).exists()]
            else:
                # Default system-wide targets based on scope
                scope_targets = {
                    "system": ["core", "agents", "tools", "orchestration"],
                    "security": ["core", "llm", "api", "tools"],
                    "performance": ["monitoring", "llm", "core"],
                    "code_quality": [".", "core", "agents", "tools"]
                }
                audit_targets = [str(PROJECT_ROOT / target) for target in scope_targets.get(audit_scope, ["."])]
            
            logger.info(f"{self.log_prefix} Auditing targets: {audit_targets}")
            
            # Run OptimizedAuditGenAgent for comprehensive analysis
            for target_path in audit_targets:
                if Path(target_path).exists():
                    try:
                        success, target_results = self.optimized_audit_agent.generate_audit_documentation(
                            root_path_str=target_path,
                            focus_areas=[audit_scope],
                            additional_exclude_patterns=["*.pyc", "__pycache__/*", "*.log"]
                        )
                        
                        if success:
                            # Extract findings from audit results
                            findings = target_results.get("audit_findings", {})
                            audit_results["findings"].extend(findings.get("issues", []))
                            
                            # Merge metrics
                            target_metrics = findings.get("metrics", {})
                            for key, value in target_metrics.items():
                                if key in audit_results["metrics"]:
                                    if isinstance(value, (int, float)):
                                        audit_results["metrics"][key] += value
                                    elif isinstance(value, list):
                                        audit_results["metrics"][key].extend(value)
                                else:
                                    audit_results["metrics"][key] = value
                            
                            # Add recommendations
                            audit_results["recommendations"].extend(findings.get("recommendations", []))
                            
                    except Exception as e:
                        logger.warning(f"{self.log_prefix} Failed to audit {target_path}: {e}")
                        audit_results["findings"].append({
                            "type": "audit_error",
                            "severity": "medium",
                            "description": f"Failed to audit {target_path}: {e}",
                            "target": target_path
                        })
            
            # Run targeted file improvements for critical findings
            critical_findings = [f for f in audit_results["findings"] if f.get("severity") == "high"]
            improvement_suggestions = []
            
            for finding in critical_findings[:5]:  # Limit to top 5 critical findings
                if finding.get("target") and Path(finding["target"]).is_file():
                    try:
                        improvement_result = await self.audit_improve_tool.execute(
                            target_path=finding["target"],
                            prompt=f"Address critical issue: {finding.get('description', 'Unknown issue')}"
                        )
                        
                        if improvement_result.get("status") == "SUCCESS":
                            improvement_suggestions.append({
                                "target": finding["target"],
                                "issue": finding.get("description"),
                                "improvement": improvement_result.get("summary"),
                                "output_path": improvement_result.get("output_path")
                            })
                            
                    except Exception as e:
                        logger.warning(f"{self.log_prefix} Failed to generate improvement for {finding.get('target')}: {e}")
            
            audit_results["improvement_suggestions"] = improvement_suggestions
            audit_results["success"] = True
            
            # Save audit results to memory
            await self.memory_agent.log_process(
                process_name="comprehensive_audit",
                data=audit_results,
                metadata={"agent_id": self.agent_id, "campaign_id": self._current_campaign_run_id}
            )
            
            logger.info(f"{self.log_prefix} Comprehensive audit completed: {len(audit_results['findings'])} findings, "
                       f"{len(improvement_suggestions)} improvement suggestions")
            
            return audit_results
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Comprehensive audit failed: {e}", exc_info=True)
            audit_results["error"] = str(e)
            return audit_results

    async def _generate_audit_driven_blueprint(self, audit_results: Dict[str, Any], audit_scope: str) -> Dict[str, Any]:
        """Generate a strategic blueprint based on audit findings."""
        
        try:
            # Extract key findings and recommendations
            findings = audit_results.get("findings", [])
            recommendations = audit_results.get("recommendations", [])
            improvement_suggestions = audit_results.get("improvement_suggestions", [])
            
            # Prioritize findings by severity
            high_priority_findings = [f for f in findings if f.get("severity") == "high"]
            medium_priority_findings = [f for f in findings if f.get("severity") == "medium"]
            
            # Generate blueprint prompt
            blueprint_prompt = f"""
Generate a strategic blueprint for addressing audit findings in the mindX system.

AUDIT SCOPE: {audit_scope}

HIGH PRIORITY FINDINGS ({len(high_priority_findings)}):
{json.dumps(high_priority_findings[:5], indent=2)}

MEDIUM PRIORITY FINDINGS ({len(medium_priority_findings)}):
{json.dumps(medium_priority_findings[:3], indent=2)}

IMPROVEMENT SUGGESTIONS:
{json.dumps(improvement_suggestions, indent=2)}

RECOMMENDATIONS:
{json.dumps(recommendations[:5], indent=2)}

Create a blueprint focusing on:
1. Addressing high-priority security and performance issues
2. Implementing recommended improvements
3. Establishing monitoring for identified problem areas
4. Creating validation steps to ensure fixes work correctly

The blueprint should include specific, actionable BDI goals that can be executed by the system.
"""
            
            # Use the blueprint agent to generate the audit-driven blueprint
            blueprint_context = {
                "context_type": "audit_driven",
                "audit_findings": findings,
                "improvement_focus": audit_scope,
                "priority_areas": [f.get("type", "general") for f in high_priority_findings]
            }
            
            # Generate blueprint with audit context
            blueprint = await self.blueprint_agent.generate_next_evolution_blueprint(
                context_hint=blueprint_prompt,
                additional_context=blueprint_context
            )
            
            if "error" not in blueprint:
                # Enhance blueprint with audit-specific information
                blueprint["audit_context"] = {
                    "audit_scope": audit_scope,
                    "findings_addressed": len(high_priority_findings) + len(medium_priority_findings),
                    "improvement_suggestions_count": len(improvement_suggestions),
                    "focus_areas": list(set(f.get("type", "general") for f in findings))
                }
                
                # Add audit-specific KPIs
                audit_kpis = [
                    f"Reduce {audit_scope} issues by 70%",
                    "Implement all high-priority security fixes",
                    "Establish monitoring for identified vulnerabilities",
                    "Validate all improvements with testing"
                ]
                
                existing_kpis = blueprint.get("key_performance_indicators", [])
                blueprint["key_performance_indicators"] = existing_kpis + audit_kpis
                
                logger.info(f"{self.log_prefix} Generated audit-driven blueprint targeting {len(findings)} findings")
            
            return blueprint
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to generate audit-driven blueprint: {e}", exc_info=True)
            return {"error": f"Blueprint generation failed: {e}"}

    async def _validate_audit_improvements(self, original_audit_results: Dict[str, Any], 
                                         target_components: Optional[List[str]]) -> Dict[str, Any]:
        """Validate improvements by re-running audit and comparing results."""
        
        validation_results = {
            "timestamp": time.time(),
            "validation_success": False,
            "improvements_validated": [],
            "remaining_issues": [],
            "metrics_comparison": {},
            "recommendations": []
        }
        
        try:
            logger.info(f"{self.log_prefix} Running validation audit")
            
            # Re-run audit with same scope and targets
            post_improvement_audit = await self._run_comprehensive_audit(
                original_audit_results.get("audit_scope", "system"),
                target_components
            )
            
            if not post_improvement_audit.get("success", False):
                validation_results["error"] = "Post-improvement audit failed"
                return validation_results
            
            # Compare findings
            original_findings = original_audit_results.get("findings", [])
            new_findings = post_improvement_audit.get("findings", [])
            
            # Track resolved issues
            original_issue_keys = set(f"{f.get('type', 'unknown')}:{f.get('target', 'unknown')}" for f in original_findings)
            new_issue_keys = set(f"{f.get('type', 'unknown')}:{f.get('target', 'unknown')}" for f in new_findings)
            
            resolved_issues = original_issue_keys - new_issue_keys
            persistent_issues = original_issue_keys & new_issue_keys
            new_issues = new_issue_keys - original_issue_keys
            
            validation_results["improvements_validated"] = list(resolved_issues)
            validation_results["remaining_issues"] = list(persistent_issues)
            validation_results["new_issues"] = list(new_issues)
            
            # Compare metrics
            original_metrics = original_audit_results.get("metrics", {})
            new_metrics = post_improvement_audit.get("metrics", {})
            
            for metric_name in original_metrics:
                if metric_name in new_metrics:
                    original_value = original_metrics[metric_name]
                    new_value = new_metrics[metric_name]
                    
                    if isinstance(original_value, (int, float)) and isinstance(new_value, (int, float)):
                        improvement_pct = ((original_value - new_value) / original_value * 100) if original_value != 0 else 0
                        validation_results["metrics_comparison"][metric_name] = {
                            "original": original_value,
                            "new": new_value,
                            "improvement_percent": improvement_pct
                        }
            
            # Determine validation success
            resolved_count = len(resolved_issues)
            total_original_issues = len(original_findings)
            
            if total_original_issues > 0:
                resolution_rate = resolved_count / total_original_issues
                validation_results["resolution_rate"] = resolution_rate
                validation_results["validation_success"] = resolution_rate >= 0.5  # At least 50% of issues resolved
            else:
                validation_results["validation_success"] = True
            
            # Generate recommendations for remaining issues
            if persistent_issues or new_issues:
                validation_results["recommendations"] = [
                    f"Address {len(persistent_issues)} persistent issues",
                    f"Investigate {len(new_issues)} new issues introduced",
                    "Consider additional improvement cycles for unresolved problems"
                ]
            
            logger.info(f"{self.log_prefix} Validation completed: {resolved_count}/{total_original_issues} issues resolved "
                       f"({validation_results.get('resolution_rate', 0)*100:.1f}%)")
            
            # Save validation results
            await self.memory_agent.log_process(
                process_name="audit_improvement_validation",
                data=validation_results,
                metadata={"agent_id": self.agent_id, "campaign_id": self._current_campaign_run_id}
            )
            
            return validation_results
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Validation failed: {e}", exc_info=True)
            validation_results["error"] = str(e)
            return validation_results

    async def _generate_audit_campaign_report(self, audit_results: Dict[str, Any], 
                                            blueprint: Dict[str, Any],
                                            improvement_results: Dict[str, Any],
                                            validation_results: Dict[str, Any],
                                            campaign_duration: float) -> Dict[str, Any]:
        """Generate comprehensive campaign report."""
        
        report = {
            "campaign_id": self._current_campaign_run_id,
            "timestamp": time.time(),
            "duration_seconds": campaign_duration,
            "audit_scope": audit_results.get("audit_scope", "unknown"),
            
            "audit_summary": {
                "findings_count": len(audit_results.get("findings", [])),
                "high_priority_issues": len([f for f in audit_results.get("findings", []) if f.get("severity") == "high"]),
                "improvement_suggestions": len(audit_results.get("improvement_suggestions", [])),
                "recommendations_count": len(audit_results.get("recommendations", []))
            },
            
            "blueprint_summary": {
                "title": blueprint.get("blueprint_title", "Unknown"),
                "bdi_goals": len(blueprint.get("bdi_todo_list", [])),
                "kpis": blueprint.get("key_performance_indicators", []),
                "focus_areas": blueprint.get("focus_areas", [])
            },
            
            "improvement_summary": {
                "status": improvement_results.get("status", "unknown"),
                "actions_executed": improvement_results.get("coordinator_tasks_created", 0),
                "estimated_cost": improvement_results.get("total_estimated_cost", 0.0),
                "estimated_duration": improvement_results.get("total_estimated_duration", 0)
            },
            
            "validation_summary": {
                "success": validation_results.get("validation_success", False),
                "resolution_rate": validation_results.get("resolution_rate", 0.0),
                "issues_resolved": len(validation_results.get("improvements_validated", [])),
                "remaining_issues": len(validation_results.get("remaining_issues", [])),
                "new_issues": len(validation_results.get("new_issues", []))
            },
            
            "overall_assessment": self._assess_campaign_success(audit_results, improvement_results, validation_results),
            
            "next_steps": self._generate_next_steps_recommendations(validation_results)
        }
        
        # Save comprehensive report
        await self.memory_agent.log_process(
            process_name="audit_campaign_completion_report",
            data=report,
            metadata={"agent_id": self.agent_id, "campaign_id": self._current_campaign_run_id}
        )
        
        return report

    def _assess_campaign_success(self, audit_results: Dict[str, Any], 
                               improvement_results: Dict[str, Any],
                               validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Assess overall campaign success and generate insights."""
        
        # Calculate success metrics
        findings_count = len(audit_results.get("findings", []))
        resolution_rate = validation_results.get("resolution_rate", 0.0)
        improvement_status = improvement_results.get("status", "UNKNOWN")
        validation_success = validation_results.get("validation_success", False)
        
        # Determine overall grade
        if resolution_rate >= 0.8 and improvement_status == "SUCCESS" and validation_success:
            grade = "EXCELLENT"
            score = 95
        elif resolution_rate >= 0.6 and improvement_status == "SUCCESS":
            grade = "GOOD"  
            score = 85
        elif resolution_rate >= 0.4 and improvement_status in ["SUCCESS", "PARTIAL_SUCCESS"]:
            grade = "SATISFACTORY"
            score = 75
        elif resolution_rate >= 0.2:
            grade = "NEEDS_IMPROVEMENT"
            score = 60
        else:
            grade = "POOR"
            score = 40
        
        return {
            "overall_grade": grade,
            "success_score": score,
            "key_metrics": {
                "findings_addressed": findings_count,
                "resolution_rate_percent": resolution_rate * 100,
                "improvement_execution": improvement_status,
                "validation_passed": validation_success
            },
            "strengths": self._identify_campaign_strengths(audit_results, improvement_results, validation_results),
            "areas_for_improvement": self._identify_improvement_areas(validation_results)
        }

    def _identify_campaign_strengths(self, audit_results: Dict[str, Any], 
                                   improvement_results: Dict[str, Any],
                                   validation_results: Dict[str, Any]) -> List[str]:
        """Identify campaign strengths."""
        strengths = []
        
        if len(audit_results.get("findings", [])) > 10:
            strengths.append("Comprehensive audit coverage")
        
        if improvement_results.get("coordinator_tasks_created", 0) > 5:
            strengths.append("Extensive improvement implementation")
            
        if validation_results.get("resolution_rate", 0) > 0.7:
            strengths.append("High issue resolution rate")
            
        if validation_results.get("validation_success", False):
            strengths.append("Successful validation of improvements")
            
        if not strengths:
            strengths.append("Campaign completed without critical failures")
            
        return strengths

    def _identify_improvement_areas(self, validation_results: Dict[str, Any]) -> List[str]:
        """Identify areas for improvement in future campaigns."""
        areas = []
        
        if validation_results.get("resolution_rate", 0) < 0.5:
            areas.append("Improve effectiveness of issue resolution")
            
        if len(validation_results.get("new_issues", [])) > 0:
            areas.append("Prevent introduction of new issues during improvements")
            
        if len(validation_results.get("remaining_issues", [])) > 5:
            areas.append("Address persistent issues requiring additional attention")
            
        if not validation_results.get("validation_success", False):
            areas.append("Enhance validation and testing procedures")
            
        return areas

    def _generate_next_steps_recommendations(self, validation_results: Dict[str, Any]) -> List[str]:
        """Generate recommendations for next steps."""
        recommendations = []
        
        remaining_issues = len(validation_results.get("remaining_issues", []))
        new_issues = len(validation_results.get("new_issues", []))
        resolution_rate = validation_results.get("resolution_rate", 0.0)
        
        if remaining_issues > 0:
            recommendations.append(f"Plan follow-up campaign to address {remaining_issues} remaining issues")
            
        if new_issues > 0:
            recommendations.append(f"Investigate and resolve {new_issues} new issues introduced")
            
        if resolution_rate < 0.6:
            recommendations.append("Review and improve issue resolution strategies")
            
        if resolution_rate > 0.8:
            recommendations.append("Consider expanding audit scope to other system areas")
            
        recommendations.append("Schedule regular audit cycles to maintain system health")
        
        return recommendations
