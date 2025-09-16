# mindx/core/agint.py (Build 1.2.2 - Corrected Perception Loop)
from __future__ import annotations
import asyncio
import json
import random
import time
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple

from utils.config import Config
from utils.logging_config import get_logger
from llm.llm_interface import LLMHandlerInterface
from llm.model_registry import ModelRegistry
from llm.model_selector import TaskType
from core.belief_system import BeliefSystem
from core.bdi_agent import BDIAgent
from orchestration.coordinator_agent import CoordinatorAgent, InteractionType, InteractionStatus
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)

class AgentStatus(Enum):
    INACTIVE = "INACTIVE"
    RUNNING = "RUNNING"
    AWAITING_DIRECTIVE = "AWAITING_DIRECTIVE"
    FAILED = "FAILED"

class DecisionType(Enum):
    BDI_DELEGATION = "BDI_DELEGATION"
    RESEARCH = "RESEARCH"
    COOLDOWN = "COOLDOWN"
    SELF_REPAIR = "SELF_REPAIR"
    # Other types preserved for future use
    IDLE = "IDLE"
    PERFORM_TASK = "PERFORM_TASK"
    SELF_IMPROVEMENT = "SELF_IMPROVEMENT"
    STRATEGIC_EVOLUTION = "STRATEGIC_EVOLUTION"

class AGInt:
    def __init__(self,
                 agent_id: str,
                 bdi_agent: BDIAgent,
                 model_registry: ModelRegistry,
                 config: Optional[Config] = None,
                 web_search_tool: Optional[Any] = None,
                 coordinator_agent: Optional[CoordinatorAgent] = None,
                 memory_agent: Optional[MemoryAgent] = None,
                 **kwargs): # Accept other agents
        self.agent_id = agent_id
        self.log_prefix = f"AGInt ({self.agent_id}):"
        logger.info(f"{self.log_prefix} Initializing...")

        from core.id_manager_agent import IDManagerAgent
        from core.belief_system import BeliefSystem
        belief_system = BeliefSystem()
        id_manager = IDManagerAgent(agent_id=f"id_manager_for_{self.agent_id}", belief_system=belief_system, config_override=config)
        id_manager.create_new_wallet(entity_id=self.agent_id)

        self.bdi_agent = bdi_agent
        self.model_registry = model_registry
        self.config = config or Config()
        self.coordinator_agent = coordinator_agent
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        self.tools: Dict[str, Any] = kwargs.get('tools', {})
        
        self.status = AgentStatus.INACTIVE
        self.primary_directive: Optional[str] = None
        self.main_loop_task: Optional[asyncio.Task] = None
        self.state_summary: Dict[str, Any] = { "llm_operational": True, "awareness": "System starting up." }
        self.last_action_context: Optional[Dict[str, Any]] = None

    def start(self, directive: str):
        if self.status == AgentStatus.RUNNING: return
        self.status = AgentStatus.RUNNING
        self.primary_directive = directive
        self.main_loop_task = asyncio.create_task(self._cognitive_loop())

    async def stop(self):
        if self.status != AgentStatus.RUNNING: return
        self.status = AgentStatus.INACTIVE
        if self.main_loop_task:
            self.main_loop_task.cancel()
            try: await self.main_loop_task
            except asyncio.CancelledError: pass
        logger.info(f"{self.log_prefix} Cognitive loop stopped.")

    async def _cognitive_loop(self):
        """The main P-O-D-A cycle with a corrected perception-action sequence."""
        while self.status == AgentStatus.RUNNING:
            try:
                # PERCEPTION: Occurs first, aware of the *previous* cycle's outcome.
                perception = await self._perceive()
                if self.memory_agent: await self.memory_agent.log_process('agint_perception', perception, {'agent_id': self.agent_id})

                # DECISION: Based on the fresh perception.
                decision = await self._orient_and_decide(perception)
                if self.memory_agent: await self.memory_agent.log_process('agint_decision', decision, {'agent_id': self.agent_id})
                
                # ACTION: The outcome of this action will be perceived in the *next* cycle.
                success, result_data = await self._act(decision)
                self.last_action_context = {'success': success, 'result': result_data} # Update internal state for next perception
                if self.memory_agent: await self.memory_agent.log_process('agint_action', self.last_action_context, {'agent_id': self.agent_id})

                await asyncio.sleep(self.config.get("agint.cycle_delay_seconds", 5.0))
            except asyncio.CancelledError:
                logger.info(f"{self.log_prefix} Cognitive loop cancelled.")
                break
            except Exception as e:
                logger.critical(f"{self.log_prefix} UNHANDLED CRITICAL ERROR in cognitive loop: {e}. Agent FAILED.", exc_info=True)
                self.status = AgentStatus.FAILED
                break

    async def _perceive(self) -> Dict[str, Any]:
        """Gathers information, now correctly using its internal state for failure context."""
        perception_data = {"timestamp": time.time()}
        if self.last_action_context and not self.last_action_context.get('success'):
            perception_data['last_action_failure_context'] = self.last_action_context.get('result')
            logger.warning(f"{self.log_prefix} Perceiving with failure context: {perception_data['last_action_failure_context']}")
        return perception_data

    async def _execute_cognitive_task(self, prompt: str, task_type: TaskType, **kwargs) -> Optional[str]:
        # Corrected logic from previous audit to align with ModelRegistry's actual API
        all_capabilities = list(self.model_registry.capabilities.values())
        ranked_models = self.model_registry.model_selector.select_model(all_capabilities, task_type)
        sanitized_ranked_models = [f"gemini/{m}" if not m.startswith("gemini/") else m for m in ranked_models]
        valid_models = [m for m in list(dict.fromkeys(sanitized_ranked_models)) if m in self.model_registry.capabilities]

        if not valid_models:
            self.state_summary["llm_operational"] = False
            return None
        for model_id in valid_models:
            try:
                handler = self.model_registry.get_handler(self.model_registry.capabilities[model_id].provider)
                if not handler: continue
                response_str = await handler.generate_text(prompt, model=model_id, **kwargs)
                if response_str is None: raise ValueError("Handler returned None response.")
                if kwargs.get("json_mode"): json.loads(response_str)
                return response_str
            except Exception as e:
                logger.error(f"Cognitive attempt with model '{model_id}' failed: {e}. Trying next.", exc_info=False)
                continue
        self.state_summary["llm_operational"] = False
        return None

    async def _decide_rule_based(self, perception: Dict[str, Any]) -> DecisionType:
        """Implements a deterministic, rule-based decision tree for Build 1."""
        decision = DecisionType.BDI_DELEGATION
        reason = "System healthy. Choosing BDI_DELEGATION to pursue directive."

        if not self.state_summary.get("llm_operational", True):
            decision = DecisionType.SELF_REPAIR
            reason = "System health check failed. Choosing SELF_REPAIR."
        elif perception.get('last_action_failure_context'):
            decision = DecisionType.RESEARCH
            reason = "Last action failed. Choosing RESEARCH to re-evaluate."

        logger.warning(f"Rule-Based Decision: {reason}")
        if self.memory_agent:
            await self.memory_agent.log_process(
                'agint_rule_decision',
                {'decision': decision.name, 'reason': reason, 'perception_summary': perception},
                {'agent_id': self.agent_id}
            )
        return decision

    async def _orient_and_decide(self, perception: Dict[str, Any]) -> Dict[str, Any]:
        decision_type = await self._decide_rule_based(perception)
        
        prompt = (f"As an AI core, your directive is '{self.primary_directive}'. Your chosen action is '{decision_type.name}'. "
                  f"Synthesize 'situational_awareness' from perception, especially 'last_action_failure_context'. Then formulate 'decision_details' for your action. "
                  f"Perception: {json.dumps(perception, default=str)[:2000]}. Respond ONLY with JSON: {{\"situational_awareness\": \"...\", \"decision_details\": {{...}}}}")

        if self.memory_agent:
            await self.memory_agent.log_process('agint_orient_prompt', {'prompt': prompt}, {'agent_id': self.agent_id})

        response_str = await self._execute_cognitive_task(prompt, TaskType.REASONING, json_mode=True)
        
        if self.memory_agent:
            await self.memory_agent.log_process('agint_orient_response', {'response': response_str}, {'agent_id': self.agent_id})

        if response_str is None: return {"type": DecisionType.COOLDOWN, "details": {"reason": "Orient/Decide LLM call failed."}}
        try:
            data = json.loads(response_str)
            if "situational_awareness" not in data or "decision_details" not in data: raise KeyError("Required keys missing.")
            self.state_summary["awareness"] = data["situational_awareness"]
            return {"type": decision_type, "details": data["decision_details"]}
        except (json.JSONDecodeError, KeyError) as e:
            return {"type": DecisionType.COOLDOWN, "details": {"reason": f"LLM response validation failed: {e}"}}

    async def _act(self, decision: Dict[str, Any]) -> Tuple[bool, Any]:
        """Routes the decision to the appropriate execution function."""
        decision_type = decision.get("type")
        details = decision.get("details", {})
        logger.info(f"--- AGInt: ACTION (Decision: {decision_type.name if decision_type else 'NONE'}) ---")
        
        action_map = {
            DecisionType.BDI_DELEGATION: lambda: self._delegate_task_to_bdi(details.get("task_description")),
            DecisionType.RESEARCH: lambda: self._execute_research(details.get("search_query")),
            DecisionType.SELF_REPAIR: self._execute_self_repair,
            DecisionType.COOLDOWN: self._execute_cooldown,
        }
        action_func = action_map.get(decision_type)
        if action_func: return await action_func()
        return True, {"message": f"Action {decision_type.name} completed as no-op."}

    async def _delegate_task_to_bdi(self, task_description: Optional[str]) -> Tuple[bool, Any]:
        """Delegates a task to the subordinate BDI agent and awaits its result."""
        if not task_description: return False, {"error": "No task description provided for BDI agent."}
        
        log_data = {'task_description': task_description}
        logger.info(f"Delegating to BDI Agent: '{str(task_description)[:200]}...'")
        if self.memory_agent:
            await self.memory_agent.log_process('agint_bdi_delegation_start', log_data, {'agent_id': self.agent_id})

        try:
            self.bdi_agent.set_goal(task_description, priority=1, is_primary=True)
            result_message = await self.bdi_agent.run(max_cycles=100)
            final_bdi_status = self.bdi_agent.get_status().get("status", "UNKNOWN")
            success = final_bdi_status == "COMPLETED_GOAL_ACHIEVED"
            if success: return True, {"task_outcome_message": result_message}
            else: return False, {"error": "BDI_TASK_FAILED", "details": result_message, "final_status": final_bdi_status}
        except Exception as e:
            return False, {"error": "BDI_DELEGATION_EXCEPTION", "details": str(e)}

    async def _execute_research(self, query: Optional[str]) -> Tuple[bool, Any]:
        """Executes a web search query."""
        if "web_search" not in self.tools: return False, {"error": "WebSearchTool not available."}
        if not query: return False, {"error": "No query provided for research."}
        try:
            results = await self.tools["web_search"].execute(query=query)
            return True, {"search_results_summary": f"Found {len(results)} results."}
        except Exception as e:
            return False, {"error": f"Research failed: {e}"}

    async def _execute_cooldown(self) -> Tuple[bool, Any]:
        """Pauses the agent for a configured duration."""
        cooldown_period = self.config.get("agint.llm_failure_cooldown_seconds", 30)
        logger.info(f"Executing COOLDOWN. Waiting for {cooldown_period} seconds.")
        await asyncio.sleep(cooldown_period)
        return True, {"message": f"Successfully waited for {cooldown_period}s."}

    async def _execute_self_repair(self) -> Tuple[bool, Any]:
        """Executes the self-repair sequence with mandatory verification."""
        logger.info(f"{self.log_prefix} Initiating self-repair sequence...")
        if not self.coordinator_agent: return False, {"error": "CoordinatorAgent not available."}
        try:
            interaction = await self.coordinator_agent.create_interaction(InteractionType.SYSTEM_ANALYSIS, "Automated self-repair triggered.")
            result = await self.coordinator_agent.process_interaction(interaction)
            if result.status != InteractionStatus.COMPLETED: raise RuntimeError(f"Coordinator failed repair task with status {result.status.name}")
            
            logger.info(f"Repair task completed. Verifying LLM connectivity...")
            await self.model_registry.force_reload()
            verification_result = await self._execute_cognitive_task("Status check. Respond ONLY with 'OK'.", TaskType.HEALTH_CHECK)
            
            if verification_result and "OK" in verification_result:
                self.state_summary["llm_operational"] = True
                return True, {"message": "Self-repair verification successful."}
            else:
                self.state_summary["llm_operational"] = False
                return False, {"error": "Self-repair verification failed."}
        except Exception as e:
            return False, {"error": str(e)}

    def _create_state_representation(self, perception: Dict[str, Any]) -> str:
        """Enhanced RL state representation for future use."""
        llm_ok = self.state_summary.get("llm_operational", True)
        last_action_failed = 'last_action_failure_context' in perception
        return f"llm_ok:{llm_ok}|last_action_failed:{last_action_failed}"

    async def _update_learning(self, state: str, decision: Dict[str, Any], success: bool, next_state: str):
        """Updates the Q-table for the RL system (inactive in RULE_BASED mode)."""
        decision_type = decision.get("type")
        if not decision_type: return

        if decision_type == DecisionType.IDLE:
            reward = -0.1  # Small penalty for inaction
        else:
            reward = 0.0 if decision_type == DecisionType.COOLDOWN else 1.0 if success else -1.0
        
        old_value = self.q_values.get((state, decision_type), 0.0)
        next_max_q = max(self.q_values.get((next_state, dt), 0.0) for dt in DecisionType)
        new_value = old_value + self.config.get("agint.learning.alpha", 0.1) * (reward + self.config.get("agint.learning.gamma", 0.9) * next_max_q - old_value)
        
        self.q_values[(state, decision_type)] = new_value
        logger.info(f"RL: Updated Q-value for ({state}, {decision_type.name}) to {new_value:.3f}")
