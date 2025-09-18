# mindx/core/bdi_agent.py (Final E2E Hardened Version)

from __future__ import annotations
import asyncio
import json
import re
import importlib
import inspect
import uuid
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Callable, Awaitable
from enum import Enum

from utils.config import Config
from utils.logging_config import get_logger
from llm.llm_factory import create_llm_handler
from llm.llm_interface import LLMHandlerInterface

from .belief_system import BeliefSystem, BeliefSource
from learning.goal_management import GoalSt
from agents.memory_agent import MemoryAgent

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from learning.strategic_evolution_agent import StrategicEvolutionAgent
    from orchestration.coordinator_agent import CoordinatorAgent, InteractionType, InteractionStatus
    from orchestration.mastermind_agent import MastermindAgent
    from utils.config import PROJECT_ROOT

logger = get_logger(__name__)

class FailureType(Enum):
    TOOL_UNAVAILABLE = "TOOL_UNAVAILABLE"
    TOOL_EXECUTION_ERROR = "TOOL_EXECUTION_ERROR"
    INVALID_PARAMETERS = "INVALID_PARAMETERS"
    RATE_LIMIT_ERROR = "RATE_LIMIT_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    PLANNING_ERROR = "PLANNING_ERROR"
    GOAL_PARSE_ERROR = "GOAL_PARSE_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

class RecoveryStrategy(Enum):
    RETRY_WITH_DELAY = "RETRY_WITH_DELAY"
    ALTERNATIVE_TOOL = "ALTERNATIVE_TOOL"
    SIMPLIFIED_APPROACH = "SIMPLIFIED_APPROACH"
    ESCALATE_TO_AGINT = "ESCALATE_TO_AGINT"
    FALLBACK_MANUAL = "FALLBACK_MANUAL"
    ABORT_GRACEFULLY = "ABORT_GRACEFULLY"

class FailureAnalyzer:
    """Intelligent failure analysis and adaptive recovery system."""
    
    def __init__(self, config: Config, logger):
        self.config = config
        self.logger = logger
        self.failure_patterns: Dict[str, List[Dict[str, Any]]] = {}
        self.recovery_success_rates: Dict[Tuple[FailureType, RecoveryStrategy], float] = {}
        
    def classify_failure(self, failure_context: Dict[str, Any]) -> FailureType:
        """Classify the type of failure based on context."""
        reason = failure_context.get("reason", "").lower()
        failed_action = failure_context.get("failed_action", {})
        
        if "tool" in reason and "not found" in reason:
            return FailureType.TOOL_UNAVAILABLE
        elif "rate limit" in reason or "ratelimit" in reason:
            return FailureType.RATE_LIMIT_ERROR
        elif "permission" in reason or "access denied" in reason:
            return FailureType.PERMISSION_ERROR
        elif "network" in reason or "connection" in reason:
            return FailureType.NETWORK_ERROR
        elif "parameter" in reason or "invalid" in reason:
            return FailureType.INVALID_PARAMETERS
        elif "planning" in reason or failed_action.get("type") == "plan":
            return FailureType.PLANNING_ERROR
        elif "parse" in reason or "json" in reason:
            return FailureType.GOAL_PARSE_ERROR
        elif failed_action.get("type") in ["tool_execution", "action_execution"]:
            return FailureType.TOOL_EXECUTION_ERROR
        else:
            return FailureType.UNKNOWN_ERROR
    
    def select_recovery_strategy(self, failure_type: FailureType, failure_context: Dict[str, Any]) -> RecoveryStrategy:
        """Select the best recovery strategy based on failure type and historical success rates."""
        
        # Get historical success rates for this failure type
        strategy_scores = {}
        for (f_type, strategy), success_rate in self.recovery_success_rates.items():
            if f_type == failure_type:
                strategy_scores[strategy] = success_rate
        
        # Default strategies based on failure type
        default_strategies = {
            FailureType.TOOL_UNAVAILABLE: RecoveryStrategy.ALTERNATIVE_TOOL,
            FailureType.TOOL_EXECUTION_ERROR: RecoveryStrategy.RETRY_WITH_DELAY,
            FailureType.INVALID_PARAMETERS: RecoveryStrategy.SIMPLIFIED_APPROACH,
            FailureType.RATE_LIMIT_ERROR: RecoveryStrategy.RETRY_WITH_DELAY,
            FailureType.PERMISSION_ERROR: RecoveryStrategy.ESCALATE_TO_AGINT,
            FailureType.NETWORK_ERROR: RecoveryStrategy.RETRY_WITH_DELAY,
            FailureType.PLANNING_ERROR: RecoveryStrategy.SIMPLIFIED_APPROACH,
            FailureType.GOAL_PARSE_ERROR: RecoveryStrategy.SIMPLIFIED_APPROACH,
            FailureType.UNKNOWN_ERROR: RecoveryStrategy.ESCALATE_TO_AGINT
        }
        
        # Use strategy with highest success rate, or default if no history
        if strategy_scores:
            best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
        else:
            best_strategy = default_strategies.get(failure_type, RecoveryStrategy.ESCALATE_TO_AGINT)
        
        return best_strategy
    
    def record_failure(self, failure_context: Dict[str, Any]):
        """Record failure pattern for future analysis."""
        failure_type = self.classify_failure(failure_context)
        action_type = failure_context.get("failed_action", {}).get("type", "unknown")
        
        if action_type not in self.failure_patterns:
            self.failure_patterns[action_type] = []
        
        self.failure_patterns[action_type].append({
            "failure_type": failure_type.value,
            "timestamp": time.time(),
            "context": failure_context
        })
        
        # Limit history size
        if len(self.failure_patterns[action_type]) > 10:
            self.failure_patterns[action_type] = self.failure_patterns[action_type][-10:]
    
    def record_recovery_outcome(self, failure_type: FailureType, strategy: RecoveryStrategy, success: bool):
        """Record the success/failure of a recovery strategy."""
        key = (failure_type, strategy)
        current_rate = self.recovery_success_rates.get(key, 0.5)  # Start with neutral assumption
        
        # Update success rate using exponential moving average
        alpha = 0.3  # Learning rate
        new_outcome = 1.0 if success else 0.0
        self.recovery_success_rates[key] = (1 - alpha) * current_rate + alpha * new_outcome
        
        self.logger.info(f"Updated recovery success rate for {failure_type.value} + {strategy.value}: {self.recovery_success_rates[key]:.3f}")

class BaseTool:
    def __init__(self,
                 config: Optional[Config] = None,
                 llm_handler: Optional[LLMHandlerInterface] = None,
                 bdi_agent_ref: Optional['BDIAgent'] = None,
                 **kwargs: Any):
        self.config = config or Config()
        self.llm_handler = llm_handler
        self.bdi_agent_ref = bdi_agent_ref
        self.logger = get_logger(f"tool.{self.__class__.__name__}")

    async def execute(self, **kwargs) -> Any:
        raise NotImplementedError(f"Tool execute method not implemented for {self.__class__.__name__}.")

class BDIAgent:
    def __init__(self,
                 domain: str,
                 belief_system_instance: BeliefSystem,
                 tools_registry: Dict,
                 initial_goal: Optional[str] = None,
                 config_override: Optional[Config] = None,
                 strategic_evolution_agent: Optional['StrategicEvolutionAgent'] = None,
                 coordinator_agent: Optional['CoordinatorAgent'] = None,
                 memory_agent: Optional[MemoryAgent] = None,
                 automindx_agent: Optional[Any] = None, # Accept AutoMINDX
                 persona_prompt: Optional[str] = None, # New parameter for persona
                 mastermind_ref: Optional['MastermindAgent'] = None, # Add reference to mastermind
                 test_mode: bool = False):

        if hasattr(self, '_initialized_sync_part') and self._initialized_sync_part and not test_mode:
            return

        self.domain = domain
        self.persona_prompt = persona_prompt or "You are a helpful AI assistant." # Default persona
        self.automindx_agent = automindx_agent
        self.config = config_override or Config()
        self.belief_system = belief_system_instance
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.tools_registry = tools_registry
        self.agent_id = f"bdi_agent_{self.domain.replace(' ','_').replace('.','-')}"
        
        self.logger = get_logger(f"bdi_agent.{self.agent_id}")
        self.log_prefix = f"BDI ({self.agent_id}):"
        
        self.strategic_evolution_agent = strategic_evolution_agent
        self.coordinator_agent = coordinator_agent
        self.mastermind_ref = mastermind_ref
        self._internal_state: Dict[str, Any] = {
            "status": "INITIALIZED", "last_action_details": None,
            "current_failure_reason": None, "cycle_count": 0, "current_run_id": None
        }
        self.desires: Dict[str, Any] = {"primary_goal_description": None, "primary_goal_id": None, "priority_queue": []}
        self.intentions: Dict[str, Any] = {"current_plan_id": None, "current_plan_actions": [], "current_goal_id_for_plan": None, "current_action_id_in_plan": None, "plan_status": None}
        self.lessons_learned: List[str] = []

        bdi_llm_provider_cfg_key = f"bdi.{self.domain}.llm.provider"
        bdi_default_llm_provider_cfg_key = "bdi.default_llm.provider"
        global_default_provider_cfg_key = "llm.default_provider"
        self._bdi_llm_provider_cfg = self.config.get(bdi_llm_provider_cfg_key, self.config.get(bdi_default_llm_provider_cfg_key, self.config.get(global_default_provider_cfg_key)))
        
        bdi_llm_model_cfg_key = f"bdi.{self.domain}.llm.model"
        bdi_default_llm_model_cfg_key = "bdi.default_llm.model"
        provider_for_model_default = self._bdi_llm_provider_cfg or "unknown_provider"
        global_default_model_for_provider_cfg_key = f"llm.{provider_for_model_default}.default_model_for_reasoning"
        global_default_model_overall_cfg_key = f"llm.{provider_for_model_default}.default_model"
        self._bdi_llm_model_cfg = self.config.get(bdi_llm_model_cfg_key, self.config.get(bdi_default_llm_model_cfg_key, self.config.get(global_default_model_for_provider_cfg_key, self.config.get(global_default_model_overall_cfg_key))))

        self.llm_handler: Optional[LLMHandlerInterface] = None
        self.available_tools: Dict[str, BaseTool] = {}
        self.failure_analyzer = FailureAnalyzer(self.config, self.logger)
        
        self._internal_action_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Tuple[bool, Any]]]] = {
            "ANALYZE_DATA": self._execute_llm_cognitive_action,
            "SYNTHESIZE_INFO": self._execute_llm_cognitive_action,
            "IDENTIFY_CRITERIA": self._execute_llm_cognitive_action,
            "EVALUATE_OPTIONS": self._execute_llm_cognitive_action,
            "MAKE_DECISION": self._execute_llm_cognitive_action,
            "GENERATE_REPORT": self._execute_llm_cognitive_action,
            "ANALYZE_FAILURE": self._execute_llm_cognitive_action,
            "UPDATE_BELIEF": self._execute_update_belief,
            "EXECUTE_STRATEGIC_EVOLUTION_CAMPAIGN": self._execute_strategic_evolution_campaign,
            "NO_OP": self._execute_no_op,
            "FAIL_ACTION": self._execute_fail_action,
            
            # Enhanced Simple Coder Integration
            "EXECUTE_BASH_COMMAND": self._execute_bash_command,
            "EXECUTE_LLM_BASH_TASK": self._execute_llm_bash_task,
            "READ_FILE": self._execute_read_file,
            "WRITE_FILE": self._execute_write_file,
            "LIST_FILES": self._execute_list_files,
            "CREATE_DIRECTORY": self._execute_create_directory,
            "ANALYZE_CODE": self._execute_analyze_code,
            "GENERATE_CODE": self._execute_generate_code,
            "GET_CODING_SUGGESTIONS": self._execute_get_coding_suggestions,
        }
        if initial_goal: self.set_goal(initial_goal, priority=1, is_primary=True)
        self._initialized_sync_part = True
        self._initialized = False
        self.logger.info("Synchronous __init__ complete. LLM and Tools require async_init_components.")

    async def async_init_components(self):
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        try:
            self.llm_handler = await create_llm_handler(
                provider_name=self._bdi_llm_provider_cfg,
                model_name=self._bdi_llm_model_cfg
            )
            if self.llm_handler:
                self.logger.info(f"Internal LLM initialized: {self.llm_handler.provider_name}/{self.llm_handler.model_name_for_api or 'default'}")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM handler: {e}", exc_info=True)

        # Initialize TokenCalculatorTool for cost tracking
        try:
            from monitoring.token_calculator_tool import TokenCalculatorTool
            self.token_calculator = TokenCalculatorTool(
                memory_agent=self.memory_agent,
                config=self.config
            )
            self.logger.info("TokenCalculatorTool initialized for BDI agent cost tracking")
        except Exception as e:
            self.logger.error(f"Failed to initialize TokenCalculatorTool: {e}")
            self.token_calculator = None

        await self._initialize_tools_async()
        await self._initialize_enhanced_simple_coder()
        
        self._initialized = True
        self.logger.info(f"Fully initialized. LLM Ready: {self.llm_handler is not None}. Tools: {list(self.available_tools.keys())}. Enhanced Simple Coder: {self.enhanced_simple_coder is not None}")

    async def _initialize_tools_async(self):
        self.logger.info("Initializing tools based on the provided tool registry...")
        tools_to_load = self.tools_registry.get("registered_tools", {})
        for tool_id, tool_config in tools_to_load.items():
            if not tool_config.get("enabled", False):
                continue
            try:
                module_path, class_name = tool_config["module_path"], tool_config["class_name"]
                self.logger.info(f"Attempting to load tool '{tool_id}' from {module_path}.{class_name}")
                module = importlib.import_module(module_path)
                ToolClass = getattr(module, class_name)
                
                tool_kwargs = {
                    "config": self.config,
                    "bdi_agent_ref": self,
                    "memory_agent": self.memory_agent
                }
                
                # Only add llm_handler if it's not None
                if self.llm_handler is not None:
                    tool_kwargs["llm_handler"] = self.llm_handler

                if class_name == "AuditAndImproveTool":
                    from tools.base_gen_agent import BaseGenAgent
                    tool_kwargs["base_gen_agent"] = BaseGenAgent(memory_agent=self.memory_agent)
                    tool_kwargs["automindx_agent"] = self.automindx_agent
                elif class_name == "TreeAgent":
                    from utils.config import PROJECT_ROOT
                    tool_kwargs["root_path"] = PROJECT_ROOT
                elif class_name == "CliCommandTool":
                    tool_kwargs["mastermind"] = self.mastermind_ref
                    tool_kwargs["coordinator"] = self.coordinator_agent
                elif class_name == "SystemAnalyzerTool":
                    tool_kwargs["belief_system"] = self.belief_system
                    tool_kwargs["coordinator_ref"] = self.coordinator_agent
                elif class_name == "RegistrySyncTool":
                    tool_kwargs["coordinator_ref"] = self.coordinator_agent
                elif class_name == "AgentFactoryTool":
                    tool_kwargs["coordinator_ref"] = self.coordinator_agent
                    tool_kwargs["guardian_ref"] = getattr(self, 'guardian_ref', None)
                elif class_name == "ToolFactoryTool":
                    # No additional parameters needed
                    pass
                elif class_name == "AugmenticIntelligenceTool":
                    tool_kwargs["coordinator_ref"] = self.coordinator_agent
                    tool_kwargs["mastermind_ref"] = self.mastermind_ref
                    tool_kwargs["guardian_ref"] = getattr(self, 'guardian_ref', None)
                
                sig = inspect.signature(ToolClass.__init__)
                valid_kwargs = {k: v for k, v in tool_kwargs.items() if k in sig.parameters}
                
                self.available_tools[tool_id] = ToolClass(**valid_kwargs)
                self.logger.info(f"Successfully initialized tool: {class_name}")
            except Exception as e:
                self.logger.error(f"Failed to initialize tool '{tool_id}': {e}", exc_info=True)
        self.logger.info(f"Tools initialization phase complete. Loaded tools: {list(self.available_tools.keys())}")

    async def execute_current_intention(self) -> bool:
        action = self.get_next_action_in_plan()
        if not action:
            return True

        action_type, action_id = action.get("type"), action.get("id")
        self.logger.info(f"--- BDI: ACTION ---")
        self.logger.info(f"Executing action '{action_type}' (ID: {action_id}) with params: {str(action.get('params', {}))[:150]}...")

        success, result = False, f"Unknown action type '{action_type}'"
        try:
            if action_type in self._internal_action_handlers:
                handler = self._internal_action_handlers[action_type]
                success, result = await handler(action)
            elif action_type in self.available_tools:
                tool = self.available_tools[action_type]
                params = action.get("params", {})
                if inspect.iscoroutinefunction(tool.execute):
                    success, result = await tool.execute(**params)
                else:
                    success, result = tool.execute(**params)
            else:
                error_msg = f"Action '{action_type}' is not a valid internal action or a registered tool."
                self.logger.error(error_msg)
                result = error_msg
                success = False

        except Exception as e:
            self.logger.error(f"Exception during execution of action '{action_type}': {e}", exc_info=True)
            success, result = False, f"Exception: {e}"

        await self.memory_agent.log_process(
            process_name='bdi_action_execution',
            data={'action': action, 'success': success, 'result': result},
            metadata={'agent_id': self.agent_id, 'run_id': self._internal_state.get("current_run_id")}
        )

        await self.action_completed(action_id, success, result)
        return success

    async def _execute_llm_cognitive_action(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        if not self.llm_handler: return False, "LLM handler not available."
        action_type = action.get('type', 'UNKNOWN_COGNITIVE_ACTION')
        params = action.get('params', {})
        task_description = params.get('task_description', f"Perform: {action_type}.")
        context = params.get('context', 'No specific context provided.')
        belief_summary = await self._get_belief_summary_for_prompt()
        prompt = (f"As an AI agent's cognitive core, perform the action: {action_type}.\n"
                  f"Task: {task_description}\nContext:\n{context}\n\n"
                  f"Current Beliefs:\n{belief_summary}\n\n"
                  f"Provide a comprehensive, reasoned response.")
        try:
            response = await self.llm_handler.generate_text(prompt, model=self.llm_handler.model_name_for_api)
            return True, response
        except Exception as e:
            return False, f"LLM call failed: {e}"

    async def _execute_update_belief(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        params = action.get('params', {})
        key, value = params.get('key'), params.get('value')
        if key is None or value is None: return False, "Missing 'key' or 'value'."
        await self.update_belief(key, value)
        return True, f"Belief '{key}' updated."

    async def _execute_extract_parameters_from_goal(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        if not self.llm_handler: return False, "LLM handler not available."
        params = action.get('params', {})
        goal_desc, target_action, req_params = params.get('goal_description'), params.get('target_action_type'), params.get('required_params')
        if not all([goal_desc, target_action, req_params]): return False, "Missing required params for extraction."
        prompt = (f"Goal: \"{goal_desc}\"\nTarget Action: \"{target_action}\"\n"
                  f"Required Parameters: {req_params}\n\n"
                  f"Extract values for the parameters from the goal. Respond ONLY with a valid JSON object.")
        try:
            response_str = await self.llm_handler.generate_text(prompt, model=self.llm_handler.model_name_for_api, temperature=0.0, json_mode=True)
            return True, json.loads(response_str)
        except Exception as e:
            return False, f"Failed to extract parameters via LLM: {e}"

    async def _execute_strategic_evolution_campaign(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        if not self.strategic_evolution_agent: return False, "StrategicEvolutionAgent not available."
        campaign_goal = action.get("params", {}).get("campaign_goal_description")
        if not campaign_goal: return False, "Missing 'campaign_goal_description'."
        return True, await self.strategic_evolution_agent.run_campaign(campaign_goal)

    async def _execute_no_op(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        return True, "No operation performed."

    async def _execute_fail_action(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        return False, action.get("params", {}).get('reason', 'Intentional failure.')

    # Enhanced Simple Coder Action Handlers
    async def _execute_bash_command(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """Execute a bash command via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        operation = params.get("command", params.get("operation"))
        
        if not operation:
            return False, "No command specified"
        
        # Remove 'command' and 'operation' from params to avoid duplication
        clean_params = {k: v for k, v in params.items() if k not in ["command", "operation"]}
        
        try:
            return await self.enhanced_simple_coder.execute(operation=operation, **clean_params)
        except Exception as e:
            self.logger.error(f"Enhanced Simple Coder execution error: {e}")
            return False, f"Command execution failed: {e}"

    async def _execute_llm_bash_task(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """Execute an LLM-powered bash task via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        task = params.get("task")
        
        if not task:
            return False, "No task specified"
        
        try:
            return await self.enhanced_simple_coder.execute(action="get_coding_suggestions", current_task=task)
        except Exception as e:
            self.logger.error(f"LLM bash task execution error: {e}")
            return False, f"Task execution failed: {e}"

    async def _execute_read_file(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """Read a file via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        file_path = params.get("path", params.get("file_path"))
        
        if not file_path:
            return False, "No file path specified"
        
        try:
            return await self.enhanced_simple_coder.execute(operation="read_file", path=file_path)
        except Exception as e:
            return False, f"File read failed: {e}"

    async def _execute_write_file(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """Write a file via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        file_path = params.get("path", params.get("file_path"))
        content = params.get("content")
        
        if not file_path or content is None:
            return False, "File path and content required"
        
        try:
            return await self.enhanced_simple_coder.execute(operation="write_file", path=file_path, content=content)
        except Exception as e:
            return False, f"File write failed: {e}"

    async def _execute_list_files(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """List files via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        path = params.get("path", ".")
        
        try:
            return await self.enhanced_simple_coder.execute(operation="list_files", path=path)
        except Exception as e:
            return False, f"File listing failed: {e}"

    async def _execute_create_directory(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """Create a directory via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        path = params.get("path")
        
        if not path:
            return False, "Directory path required"
        
        try:
            return await self.enhanced_simple_coder.execute(operation="create_directory", path=path)
        except Exception as e:
            return False, f"Directory creation failed: {e}"

    async def _execute_analyze_code(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """Analyze code via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        
        try:
            return await self.enhanced_simple_coder.execute(operation="analyze_code", **params)
        except Exception as e:
            return False, f"Code analysis failed: {e}"

    async def _execute_generate_code(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """Generate code via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        description = params.get("description")
        
        if not description:
            return False, "Code description required"
        
        try:
            return await self.enhanced_simple_coder.execute(operation="generate_code", **params)
        except Exception as e:
            return False, f"Code generation failed: {e}"

    async def _execute_get_coding_suggestions(self, action: Dict[str, Any]) -> Tuple[bool, Any]:
        """Get coding suggestions via enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        params = action.get("params", {})
        current_task = params.get("task", params.get("current_task"))
        
        if not current_task:
            return False, "Task description required"
        
        try:
            return await self.enhanced_simple_coder.execute(operation="get_coding_suggestions", current_task=current_task)
        except Exception as e:
            return False, f"Coding suggestions failed: {e}"

    async def perceive(self, external_input: Optional[Dict[str, Any]] = None):
        if not self._initialized: await self.async_init_components()
        self.logger.debug("Perceiving environment...")
        if external_input and isinstance(external_input, dict):
            for key, value in external_input.items():
                await self.update_belief(f"environment.{key}", value, 0.9, BeliefSource.PERCEPTION)
        if self.intentions.get("plan_status") == "READY":
            if not await self._is_plan_still_valid_async():
                self.logger.warning(f"Plan ID '{self.intentions.get('current_plan_id')}' no longer valid. Invalidating plan.")
                self.intentions["plan_status"] = "INVALID"

    async def _is_plan_still_valid_async(self) -> bool:
        return True

    def _validate_plan(self, plan: Any) -> Optional[str]:
        if not isinstance(plan, list):
            return f"Plan must be a list, but got {type(plan)}."
        for i, action in enumerate(plan):
            if not isinstance(action, dict):
                return f"Action {i} is not a dictionary."
            action_type = action.get('type')
            if not action_type:
                return f"Action {i} is missing a 'type' key."
            if action_type not in self._internal_action_handlers and action_type not in self.available_tools:
                return f"Action '{action_type}' in step {i} is not a valid action. Valid actions are internal handlers or registered tools."
        return None

    async def plan(self, goal_entry: Dict[str, Any]) -> bool:
        if not self.llm_handler:
            self.logger.error("LLM handler not initialized. Cannot generate plan.")
            return False

        goal_description, goal_id = goal_entry["goal"], goal_entry["id"]
        self.logger.info(f"--- BDI: PLANNING for Goal: {goal_id} ---")
        
        await self.memory_agent.log_process(
            process_name="bdi_planning_start",
            data={"goal_id": goal_id, "goal_description": goal_description},
            metadata={"agent_id": self.agent_id, "run_id": self._internal_state.get("current_run_id")}
        )

        contextual_info = ""
        found_path_map = {}
        
        # Enhanced context awareness for planning
        if "evolve" in goal_description.lower() or "improve" in goal_description.lower() or "review" in goal_description.lower():
            self.logger.info("Context-awareness triggered for planning.")
            
            # Look for tool/agent references in the goal
            tool_patterns = [
                r"\b([\w_]+_tool)\b",  # tool names
                r"\b([\w_]+_agent)\b", # agent names
                r"\bsummarization\s+tool\b",  # specific case
                r"\btool\b.*\bsummarization\b"  # reverse order
            ]
            
            component_found = False
            for pattern in tool_patterns:
                match = re.search(pattern, goal_description, re.IGNORECASE)
                if match:
                    component_name = match.group(1) if match.lastindex else "summarization_tool"
                    component_name = component_name.lower()
                    
                    # Map common references to actual paths
                    path_mappings = {
                        "summarization_tool": "tools",
                        "summarization": "tools", 
                        "base_gen_agent": "tools",
                        "audit_and_improve_tool": "tools",
                        "note_taking_tool": "tools",
                        "system_analyzer_tool": "tools",
                        "shell_command_tool": "tools",
                        "registry_manager_tool": "tools",
                        "agent_factory_tool": "tools",
                        "tool_factory_tool": "tools"
                    }
                    
                    if component_name in path_mappings:
                        actual_path = path_mappings[component_name]
                        found_path_map[component_name] = actual_path
                        found_path_map["summarization_tool"] = "tools"  # Always ensure this mapping
                        found_path_map["summarization"] = "tools"
                        contextual_info = f"\n\nCONTEXT: For any tool analysis or documentation generation, use the 'tools' directory as the root path. Specific tool files are located in the 'tools' directory."
                        self.logger.info(f"Mapped component '{component_name}' to path: {actual_path}")
                        component_found = True
                        break
            
            # If using tree_agent for path discovery, try it as fallback
            if not component_found and "tree_agent" in self.available_tools:
                match = re.search(r"\b([\w_]+\.py)\b", goal_description, re.IGNORECASE)
                if match:
                    file_name = match.group(1)
                    try:
                        tree_agent = self.available_tools["tree_agent"]
                        find_command = f"find . -name {file_name}"
                        file_path_result = await tree_agent.execute(command=find_command)
                        
                        if file_path_result and not file_path_result.startswith("Error"):
                            found_path = file_path_result.strip().replace("./", "")
                            found_path_map[file_name] = found_path
                            contextual_info += f"\n\nFILE LOCATION: {file_name} found at: {found_path}"
                            self.logger.info(f"Tree agent found file at path: {found_path}")
                    except Exception as e:
                        self.logger.error(f"Error while using TreeAgent to find file path: {e}")
            
            # Always add the standard tool path mapping as fallback
            if not found_path_map:
                found_path_map["tools"] = "tools"
                found_path_map["summarization_tool"] = "tools"
                contextual_info = f"\n\nCONTEXT: Use 'tools' as the root path for tool-related operations."

        action_manifest = {}
        internal_actions = {"ANALYZE_FAILURE": "Analyzes a failure. Requires params: 'failure' (string)."}
        action_manifest.update(internal_actions)
        for tool_id, tool_instance in self.available_tools.items():
            description = inspect.getdoc(tool_instance) or f"Executes the {tool_id} tool."
            description = ' '.join(description.split())
            sig = inspect.signature(tool_instance.execute)
            params = [p.name for p in sig.parameters.values() if p.name not in ['self', 'kwargs'] and p.default == inspect.Parameter.empty]
            if params: description += f" Requires params: {', '.join(params)}"
            action_manifest[tool_id] = description
        action_details_str = "\n".join([f"- {name}: {desc}" for name, desc in action_manifest.items()])
        example_action_type = next(iter(self.available_tools.keys()), "NO_OP")
        example_params = {}
        if example_action_type != "NO_OP":
            sig = inspect.signature(self.available_tools[example_action_type].execute)
            for param_name, param in sig.parameters.items():
                if param_name not in ['self', 'kwargs']: example_params[param_name] = f"<{param.annotation.__name__ if hasattr(param.annotation, '__name__') else 'value'}>"
        few_shot_example = json.dumps([{"type": example_action_type, "params": example_params}], indent=2)

        initial_prompt = (
            f"Your current goal is: '{goal_description}'.{contextual_info}\n\n"
            f"Generate a JSON list of actions to achieve the goal. You MUST use ONLY the actions listed below, and you MUST provide all required parameters for each action as specified in the manifest.\n\n"
            f"ACTION MANIFEST:\n{action_details_str}\n\n"
            f"EXAMPLE of a perfect response:\n```json\n{few_shot_example}\n```\n\n"
            f"Now, generate the plan for the goal. Respond ONLY with the JSON list."
        )

        max_repair_attempts = 1
        current_plan_str = ""
        last_error = ""
        for attempt in range(max_repair_attempts + 2):
            try:
                if attempt == 0:
                    prompt = initial_prompt
                else:
                    self.logger.warning(f"Plan validation failed. Attempting repair #{attempt}...")
                    prompt = (f"The following text was supposed to be a valid JSON list but failed validation. "
                              f"Validation Error: '{last_error}'.\n"
                              f"ORIGINAL FAULTY TEXT:\n{current_plan_str}\n\n"
                              f"Correct the faulty text to resolve the error. Respond ONLY with the corrected JSON list.")
                
                current_plan_str = await self._llm_generate_with_cost_tracking(prompt=prompt, model=self.llm_handler.model_name_for_api, operation_type="planning", temperature=0.0, json_mode=True)

                if not current_plan_str: raise ValueError("LLM returned empty response.")
                
                json_match = re.search(r'```json\s*([\s\S]*?)\s*```|(\[[\s\S]*\]|\{[\s\S]*\})', current_plan_str, re.DOTALL)
                if not json_match: raise json.JSONDecodeError("No valid JSON found in LLM response.", current_plan_str, 0)
                
                json_str = json_match.group(1) or json_match.group(2)
                new_plan_actions = json.loads(json_str)

                validation_error = self._validate_plan(new_plan_actions)
                if validation_error: raise ValueError(validation_error)

                # Enhanced path correction for all tools
                for action in new_plan_actions:
                    params = action.get("params", {})
                    action_type = action.get("type", "")
                    
                    # Map of tool types to their path parameter names
                    path_param_mappings = {
                        "audit_and_improve": ["target_path"],
                        "base_gen_agent": ["root_path_str", "root_path"],
                        "summarization": ["file_path", "path"],
                        "system_analyzer": ["target_path", "analysis_path"],
                        "note_taking": ["file_path", "note_path"]
                    }
                    
                    # Check for path parameters that need correction
                    if action_type in path_param_mappings:
                        for path_param in path_param_mappings[action_type]:
                            if path_param in params:
                                current_path = params[path_param]
                                
                                # Check for placeholder paths and correct them
                                if isinstance(current_path, str):
                                    if current_path.startswith("path/to/"):
                                        # Replace placeholder with actual path
                                        params[path_param] = "tools"
                                        self.logger.info(f"Corrected placeholder path '{current_path}' to 'tools' for {action_type}.{path_param}")
                                    elif "/" not in current_path and current_path in found_path_map:
                                        # Use mapped path
                                        params[path_param] = found_path_map[current_path]
                                        self.logger.info(f"Corrected path for '{current_path}' to '{found_path_map[current_path]}' for {action_type}.{path_param}")
                                    elif current_path in ["summarization_tool", "summarization"]:
                                        # Specific fix for summarization tool references
                                        params[path_param] = "tools"
                                        self.logger.info(f"Corrected summarization reference '{current_path}' to 'tools' for {action_type}.{path_param}")
                    
                    # Also check for any parameter that looks like a path placeholder
                    for param_name, param_value in params.items():
                        if isinstance(param_value, str) and param_value.startswith("path/to/"):
                            params[param_name] = "tools"
                            self.logger.info(f"Corrected generic placeholder path '{param_value}' to 'tools' for {action_type}.{param_name}")

                self.logger.info(f"Plan successfully generated and validated after {attempt} attempts.")
                self.set_plan(new_plan_actions, goal_id)
                return True

            except (json.JSONDecodeError, ValueError) as e:
                self.logger.warning(f"Planning attempt {attempt} failed: {e}")
                last_error = str(e)
                if "RateLimit" in current_plan_str:
                    self.logger.error("Rate limit hit during planning. Pausing for 5 seconds before retry...")
                    await asyncio.sleep(5.0)
                    continue

                if attempt >= max_repair_attempts:
                    self.logger.error(f"Plan generation failed permanently for goal '{goal_description}'.")
                    self.set_plan([], goal_id); self.intentions["plan_status"] = "FAILED_PLANNING"
                    return False
            except Exception as e:
                self.logger.critical(f"An unexpected error occurred during planning: {e}", exc_info=True)
                self.set_plan([], goal_id); self.intentions["plan_status"] = "FAILED_PLANNING"
                return False
        return False

    async def run(self, max_cycles: int = 100, external_input: Optional[Dict[str, Any]] = None) -> str:
        if not self._initialized: await self.async_init_components()
        run_id = str(uuid.uuid4())[:8]
        self.logger.info(f"Starting run ID '{run_id}'. Max cycles: {max_cycles}.")
        self._internal_state.update({"current_run_id": run_id, "cycle_count": 0, "status": "RUNNING", "current_failure_reason": None})
        if external_input: await self.perceive(external_input)

        while self._internal_state["cycle_count"] < max_cycles:
            self._internal_state["cycle_count"] += 1
            cycle_num, agent_status = self._internal_state["cycle_count"], self._internal_state["status"]
            self.logger.info(f"--- {self.log_prefix} Cycle {cycle_num}/{max_cycles} | Status: {agent_status} (Run ID: {run_id}) ---")

            if agent_status not in ["RUNNING", "PENDING_GOAL_PROCESSING"]:
                break
            try:
                if cycle_num > 1: await self.perceive()
                current_goal_entry = await self.deliberate()

                if not current_goal_entry:
                    self._internal_state["status"] = "COMPLETED_IDLE"
                    break

                goal_id = current_goal_entry["id"]
                plan_is_ready = self.intentions.get("plan_status") == "READY" and self.intentions.get("current_goal_id_for_plan") == goal_id

                if not plan_is_ready or self.intentions.get("plan_status") == "INVALID":
                    if not await self.plan(current_goal_entry):
                        self._internal_state.update({"status": "FAILED_PLANNING", "current_failure_reason": f"Planning failed for goal."})
                        break
                
                if self.intentions.get("plan_status") == "READY":
                    if not await self.execute_current_intention():
                        self.logger.warning(f"Action execution failed. Initiating intelligent failure recovery.")
                        
                        failure_context = {
                            "failed_action": self._internal_state.get("last_action_details", {}),
                            "reason": self._internal_state.get("current_failure_reason", "Unknown reason"),
                            "original_goal": current_goal_entry
                        }
                        
                        # Record failure for learning
                        self.failure_analyzer.record_failure(failure_context)
                        
                        # Use intelligent failure analysis
                        if not await self._execute_intelligent_failure_recovery(failure_context, current_goal_entry):
                            self.logger.error("Intelligent failure recovery failed. Halting execution.")
                            self._internal_state["status"] = "FAILED_RECOVERY"
                            break
                        
                        continue
                    else:
                        continue

                if self.intentions.get("plan_status") == "COMPLETED":
                    last_action_succeeded = self._internal_state.get("last_action_details", {}).get("success", False)
                    if not last_action_succeeded:
                        self.logger.warning("Plan finished, but last action failed. Goal not achieved.")
                        self._internal_state["status"] = "FAILED_EXECUTION"
                        break
                    
                    goal_entry = next((g for g in self.desires["priority_queue"] if g["id"] == goal_id), None)
                    if goal_entry: goal_entry["status"] = "completed_success"
                    if goal_id == self.desires.get("primary_goal_id"):
                        self._internal_state["status"] = "COMPLETED_GOAL_ACHIEVED"
                        break

                await asyncio.sleep(self.config.get("bdi.agent_cycle_delay_seconds", 0.1))
            except Exception as e:
                self.logger.error(f"Unhandled cycle exception in run ID '{run_id}': {e}", exc_info=True)
                self._internal_state.update({"status": "FAILED", "current_failure_reason": f"Cycle Exception: {e}"})
                break
        
        final_status = self._internal_state.get("status", "UNKNOWN")
        if final_status == "PENDING_GOAL_PROCESSING": final_status = "TIMED_OUT"
        self.logger.info(f"Execution finished for run ID '{run_id}'. Final agent status: {final_status}")
        return f"BDI run {final_status}. Reason: {self._internal_state.get('current_failure_reason', 'N/A')}"

    async def update_belief(self, key: str, value: Any, confidence: float = 0.9, source: BeliefSource = BeliefSource.SELF_ANALYSIS, is_internal_state: bool = False, **kwargs):
        if is_internal_state:
            self._internal_state[key] = value
            return
        namespaced_key = f"bdi.{self.domain}.beliefs.{key}"
        await self.belief_system.add_belief(namespaced_key, value, confidence, source, **kwargs)
        if self.memory_agent:
            await self.memory_agent.log_process(
                'bdi_belief_update',
                {'key': namespaced_key, 'value': value, 'confidence': confidence, 'source': source.name},
                {'agent_id': self.agent_id}
            )

    def set_goal(self, goal_description: str, priority: int = 1, **kwargs):
        goal_id = kwargs.get("goal_id", str(uuid.uuid4())[:8])
        new_goal_entry = {"id": goal_id, "goal": goal_description, "priority": int(priority), "status": "pending", "added_at": time.time(), **kwargs}
        
        if self.memory_agent and asyncio.get_event_loop().is_running():
             asyncio.create_task(self.memory_agent.log_process(
                'bdi_goal_set',
                {'goal': new_goal_entry},
                {'agent_id': self.agent_id}
            ))

        self.desires["priority_queue"].append(new_goal_entry)
        self.logger.info(f"Added goal ID '{goal_id}': '{goal_description}' (Prio: {priority})")
        if kwargs.get("is_primary"): self.desires.update({"primary_goal_description": goal_description, "primary_goal_id": goal_id})
        self.desires["priority_queue"].sort(key=lambda x: (-x["priority"], x["added_at"]))
    
    def get_current_goal_entry(self) -> Optional[Dict[str, Any]]:
        for goal_entry in self.desires["priority_queue"]:
            if goal_entry.get("status") == "pending": return goal_entry
        return None

    def set_plan(self, plan_actions: List[Dict[str, Any]], goal_id_for_plan: str, plan_id: Optional[str] = None):
        plan_id = plan_id or str(uuid.uuid4())[:8]
        processed_actions = []
        for i, action in enumerate(plan_actions):
            action_copy = action.copy()
            action_copy.setdefault("id", f"{plan_id}_act{i}")
            action_copy.setdefault("type", action.get("type"))
            action_copy.setdefault("params", {})
            processed_actions.append(action_copy)
        self.intentions.update({
            "current_plan_id": plan_id,
            "current_plan_actions": processed_actions,
            "plan_status": "READY" if processed_actions else "EMPTY_PLAN",
            "current_goal_id_for_plan": goal_id_for_plan
        })
        self.logger.info(f"Set plan ID '{plan_id}' with {len(processed_actions)} actions for goal '{goal_id_for_plan}'.")

    def get_next_action_in_plan(self) -> Optional[Dict[str, Any]]:
        if self.intentions.get("plan_status") == "READY" and self.intentions.get("current_plan_actions"):
            return self.intentions["current_plan_actions"][0]
        return None

    async def action_completed(self, action_id: str, success: bool, result: Any = None):
        if not self.intentions.get("current_plan_actions") or self.intentions["current_plan_actions"][0].get("id") != action_id:
            return
        
        completed_action = self.intentions["current_plan_actions"].pop(0)
        self._internal_state["last_action_details"] = {**completed_action, "success": success, "result": result}
        
        await self.memory_agent.log_process(
            process_name="bdi_action",
            data=self._internal_state["last_action_details"],
            metadata={"agent_id": self.agent_id, "run_id": self._internal_state.get("current_run_id")}
        )
        
        if success:
            self.logger.info(f"Action '{completed_action.get('type')}' success. Result: {str(result)[:100]}...")
            if not self.intentions["current_plan_actions"]:
                self.intentions["plan_status"] = "COMPLETED"
        else:
            self.intentions["plan_status"] = "FAILED"
            self._internal_state["current_failure_reason"] = f"Action '{completed_action.get('type')}' failed: {str(result)[:200]}"
            self.logger.warning(self._internal_state["current_failure_reason"])

    async def deliberate(self) -> Optional[Dict[str, Any]]:
        current_goal = self.get_current_goal_entry()
        if not current_goal:
            return None
        
        self.logger.info(f"Goal for deliberation: '{current_goal['goal']}'")
        if self.memory_agent:
            await self.memory_agent.log_process(
                'bdi_deliberation',
                {'selected_goal': current_goal, 'full_desire_queue': self.desires["priority_queue"]},
                {'agent_id': self.agent_id, 'run_id': self._internal_state.get("current_run_id")}
            )
        return current_goal
    
    async def shutdown(self):
        self.logger.info("Shutting down.")
    
    async def _get_belief_summary_for_prompt(self, key_prefix: str = "knowledge", max_beliefs: int = 5, max_value_len: int = 80) -> str:
        beliefs = await self.belief_system.query_beliefs(partial_key=f"bdi.{self.domain}.beliefs.{key_prefix}")
        if not beliefs: return "No specific relevant beliefs found."
        summary_parts = []
        sorted_beliefs = sorted(beliefs, key=lambda item: item[0]) # Sort by key
        for i, (key, belief_obj) in enumerate(sorted_beliefs):
            if i >= max_beliefs: break
            value, key_suffix = belief_obj.value, key.split('.')[-1]
            val_str = str(value)
            summary_parts.append(f"- {key_suffix}: {val_str[:max_value_len]}{'...' if len(val_str) > max_value_len else ''}")
        return "\n".join(summary_parts)

    def get_status(self) -> Dict[str, Any]:
        return { "status": self._internal_state.get("status") }

    def register_action(self, action_name: str, handler: Callable[[Dict[str, Any]], Awaitable[Tuple[bool, Any]]]):
        """Allows external agents to register custom action handlers."""
        if action_name in self._internal_action_handlers or action_name in self.available_tools:
            self.logger.warning(f"Action '{action_name}' is already registered. Overwriting.")
        self._internal_action_handlers[action_name] = handler
        self.logger.info(f"Successfully registered custom action: '{action_name}'")

    async def _execute_intelligent_failure_recovery(self, failure_context: Dict[str, Any], original_goal: Dict[str, Any]) -> bool:
        """Execute intelligent failure recovery using adaptive strategies."""
        
        failure_type = self.failure_analyzer.classify_failure(failure_context)
        recovery_strategy = self.failure_analyzer.select_recovery_strategy(failure_type, failure_context)
        
        self.logger.info(f"Failure classified as {failure_type.value}, applying recovery strategy: {recovery_strategy.value}")
        
        recovery_success = False
        
        try:
            if recovery_strategy == RecoveryStrategy.RETRY_WITH_DELAY:
                recovery_success = await self._retry_with_delay(failure_context, original_goal)
                
            elif recovery_strategy == RecoveryStrategy.ALTERNATIVE_TOOL:
                recovery_success = await self._try_alternative_tool(failure_context, original_goal)
                
            elif recovery_strategy == RecoveryStrategy.SIMPLIFIED_APPROACH:
                recovery_success = await self._simplify_approach(failure_context, original_goal)
                
            elif recovery_strategy == RecoveryStrategy.ESCALATE_TO_AGINT:
                recovery_success = await self._escalate_to_agint(failure_context, original_goal)
                
            elif recovery_strategy == RecoveryStrategy.FALLBACK_MANUAL:
                recovery_success = await self._fallback_manual_mode(failure_context, original_goal)
                
            else:  # ABORT_GRACEFULLY
                recovery_success = await self._abort_gracefully(failure_context, original_goal)
        
        except Exception as e:
            self.logger.error(f"Recovery strategy {recovery_strategy.value} failed with exception: {e}", exc_info=True)
            recovery_success = False
        
        # Record the outcome for learning
        self.failure_analyzer.record_recovery_outcome(failure_type, recovery_strategy, recovery_success)
        
        # Log lessons learned
        if self.strategic_evolution_agent and hasattr(self.strategic_evolution_agent, 'lessons_learned'):
            lesson = f"Failure type {failure_type.value} with strategy {recovery_strategy.value}: {'SUCCESS' if recovery_success else 'FAILURE'}"
            self.strategic_evolution_agent.lessons_learned.add_lesson(lesson)
        
        return recovery_success
    
    async def _retry_with_delay(self, failure_context: Dict[str, Any], original_goal: Dict[str, Any]) -> bool:
        """Retry the failed action after a delay."""
        delay = self.config.get("bdi.failure_recovery.retry_delay_seconds", 5.0)
        self.logger.info(f"Retrying after {delay} seconds...")
        
        await asyncio.sleep(delay)
        
        # Reset plan status to retry
        self.intentions["plan_status"] = "READY"
        return True
    
    async def _try_alternative_tool(self, failure_context: Dict[str, Any], original_goal: Dict[str, Any]) -> bool:
        """Try to find an alternative tool for the failed action."""
        failed_action = failure_context.get("failed_action", {})
        failed_tool = failed_action.get("type")
        
        # Look for alternative tools with similar capabilities
        alternatives = []
        for tool_id, tool in self.available_tools.items():
            if tool_id != failed_tool and hasattr(tool, 'execute'):
                alternatives.append(tool_id)
        
        if alternatives:
            # Create a new plan with alternative tool
            alternative_tool = alternatives[0]  # Use first available alternative
            self.logger.info(f"Switching from {failed_tool} to {alternative_tool}")
            
            # Update current plan action to use alternative tool
            if self.intentions.get("current_plan_actions"):
                current_action = self.intentions["current_plan_actions"][0]
                current_action["type"] = alternative_tool
                self.intentions["plan_status"] = "READY"
                return True
        
        return False
    
    async def _simplify_approach(self, failure_context: Dict[str, Any], original_goal: Dict[str, Any]) -> bool:
        """Create a simplified plan to achieve the goal."""
        simplified_goal = {
            "id": f"simplified_{original_goal['id']}",
            "goal": f"Simplified approach: {original_goal['goal']}",
            "priority": original_goal.get("priority", 1),
            "context": {"simplified": True, "original_failure": failure_context}
        }
        
        return await self.plan(simplified_goal)
    
    async def _escalate_to_agint(self, failure_context: Dict[str, Any], original_goal: Dict[str, Any]) -> bool:
        """Escalate the failure to AGInt for strategic assessment."""
        if self.mastermind_ref and hasattr(self.mastermind_ref, 'agint'):
            try:
                # Create escalation context for AGInt
                escalation_context = {
                    "type": "failure_escalation",
                    "bdi_failure": failure_context,
                    "original_goal": original_goal,
                    "timestamp": time.time()
                }
                
                # Set a belief for AGInt to perceive
                await self.belief_system.add_belief(
                    f"escalation.bdi_failure.{self.agent_id}",
                    escalation_context,
                    confidence=1.0,
                    source=BeliefSource.PERCEPTION
                )
                
                self.logger.info("Escalated failure to AGInt for strategic assessment")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to escalate to AGInt: {e}")
                return False
        
        return False
    
    async def _fallback_manual_mode(self, failure_context: Dict[str, Any], original_goal: Dict[str, Any]) -> bool:
        """Fallback to manual intervention mode."""
        self.logger.warning("Falling back to manual intervention mode")
        
        # Create a manual intervention goal
        manual_goal = {
            "id": f"manual_{original_goal['id']}",
            "goal": f"Manual intervention required for: {original_goal['goal']}",
            "priority": 999,  # Highest priority
            "context": {"manual_mode": True, "failure_context": failure_context}
        }
        
        self.set_goal(manual_goal["goal"], priority=manual_goal["priority"], **manual_goal)
        return True
    
    async def _abort_gracefully(self, failure_context: Dict[str, Any], original_goal: Dict[str, Any]) -> bool:
        """Gracefully abort the current goal."""
        self.logger.info(f"Gracefully aborting goal: {original_goal['goal']}")
        
        # Mark the goal as failed
        for goal_entry in self.desires["priority_queue"]:
            if goal_entry["id"] == original_goal["id"]:
                goal_entry["status"] = "failed_gracefully"
                break
        
        # Log the graceful abort
        await self.belief_system.add_belief(
            f"goal.aborted.{original_goal['id']}",
            {"reason": "graceful_abort", "failure_context": failure_context},
            confidence=1.0,
            source=BeliefSource.SELF_ANALYSIS
        )
        
        return True

    async def _initialize_enhanced_simple_coder(self):
        """Initialize the enhanced simple coder as the BDI agent's right-hand assistant."""
        try:
            from agents.enhanced_simple_coder import EnhancedSimpleCoder
            
            self.enhanced_simple_coder = EnhancedSimpleCoder(
                memory_agent=self.memory_agent,
                config=self.config,
                llm_handler=self.llm_handler
            )
            
            self.logger.info("Enhanced Simple Coder initialized as BDI agent's right-hand assistant")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Enhanced Simple Coder: {e}")
            self.enhanced_simple_coder = None

    async def get_coding_assistance(self, action: str, **kwargs) -> Tuple[bool, Any]:
        """Get coding assistance from the enhanced simple coder."""
        if not self.enhanced_simple_coder:
            return False, "Enhanced Simple Coder not available"
        
        try:
            return await self.enhanced_simple_coder.execute(action, **kwargs)
        except Exception as e:
            self.logger.error(f"Error getting coding assistance: {e}")
            return False, f"Coding assistance failed: {e}"

    async def _llm_generate_with_cost_tracking(self, prompt: str, model: str = None, operation_type: str = "reasoning", **kwargs) -> str:
        """LLM generation with automatic cost tracking."""
        if not self.llm_handler:
            raise ValueError("LLM handler not initialized")
        
        # Use default model if not specified
        if not model:
            model = self.llm_handler.model_name_for_api or "unknown"
        
        # Pre-estimate cost if TokenCalculatorTool is available
        estimated_cost = 0.0
        if self.token_calculator:
            try:
                success, cost_estimate = await self.token_calculator.execute(
                    action="estimate_cost",
                    text=prompt,
                    model=model,
                    operation_type=operation_type
                )
                if success:
                    estimated_cost = cost_estimate["total_cost_usd"]
                    self.logger.debug(f"Estimated LLM cost: ${estimated_cost:.6f} for {model}")
            except Exception as e:
                self.logger.warning(f"Cost estimation failed: {e}")
        
        # Execute LLM generation
        start_time = time.time()
        try:
            response = await self.llm_handler.generate_text(prompt=prompt, model=model, **kwargs)
            execution_time = time.time() - start_time
            
            # Track actual usage if TokenCalculatorTool is available
            if self.token_calculator and response:
                try:
                    # Estimate tokens (rough approximation - could be enhanced with tiktoken)
                    input_tokens = len(prompt) // 4  # Rough estimation
                    output_tokens = len(response) // 4
                    
                    await self.token_calculator.execute(
                        action="track_usage",
                        agent_id=self.agent_id,
                        operation=operation_type,
                        model=model,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cost_usd=estimated_cost
                    )
                    
                    self.logger.info(f"LLM operation tracked: ${estimated_cost:.6f} for {operation_type} ({execution_time:.2f}s)")
                except Exception as e:
                    self.logger.warning(f"Usage tracking failed: {e}")
            
            return response
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.logger.error(f"LLM generation failed after {execution_time:.2f}s: {e}")
            raise