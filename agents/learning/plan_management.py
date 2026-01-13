# mindx/learning/plan_management.py
"""
Plan Management System for strategic agents in mindX.
Provides PlanManager for creating, tracking, and executing multi-step plans.
Supports sequential and conceptual parallel execution of actions.
"""
import time
import uuid
import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Callable, Awaitable, Set
from enum import Enum

from utils.logging_config import get_logger
from utils.config import Config

logger = get_logger(__name__)

class PlanSt(Enum):
    PENDING_GENERATION = "PENDING_GENERATION"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED_SUCCESS = "COMPLETED_SUCCESS"
    FAILED_ACTION = "FAILED_ACTION"
    FAILED_VALIDATION = "FAILED_VALIDATION"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"

class ActionSt(Enum):
    PENDING = "PENDING"
    READY_TO_EXECUTE = "READY_TO_EXECUTE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED_SUCCESS = "COMPLETED_SUCCESS"
    FAILED = "FAILED"
    SKIPPED_DEPENDENCY = "SKIPPED_DEPENDENCY"
    CANCELLED = "CANCELLED"

class Action:
    def __init__(self,
                 action_type: str,
                 params: Optional[Dict[str, Any]] = None,
                 action_id: Optional[str] = None,
                 description: Optional[str] = None,
                 dependency_ids: Optional[List[str]] = None,
                 critical: bool = False):
        self.id: str = action_id or f"action_{str(uuid.uuid4())[:8]}"
        self.type: str = action_type.upper()
        self.params: Dict[str, Any] = params or {}
        self.description: Optional[str] = description
        self.status: ActionSt = ActionSt.PENDING
        self.result: Any = None
        self.error_message: Optional[str] = None
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.attempt_count: int = 0
        self.dependency_ids: List[str] = dependency_ids or []
        self.is_critical: bool = critical

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "type": self.type, "params": self.params, "description": self.description,
            "status": self.status.value, "result": str(self.result)[:200] if self.result else None,
            "error_message": self.error_message, "started_at": self.started_at, "completed_at": self.completed_at,
            "attempt_count": self.attempt_count, "dependency_ids": self.dependency_ids, "is_critical": self.is_critical
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Action':
        # This factory method correctly maps the 'id' key from data to the 'action_id' parameter
        action = cls(action_type=data["type"], params=data.get("params"), action_id=data.get("id"),
                     description=data.get("description"), dependency_ids=data.get("dependency_ids"),
                     critical=data.get("is_critical", False))
        action.status = ActionSt(data.get("status", ActionSt.PENDING.value))
        action.result = data.get("result")
        action.error_message = data.get("error_message")
        action.started_at = data.get("started_at"); action.completed_at = data.get("completed_at")
        action.attempt_count = data.get("attempt_count", 0)
        return action

class Plan:
    def __init__(self, goal_id: str, plan_id: Optional[str] = None,
                 description: Optional[str] = None, actions: Optional[List[Action]] = None,
                 created_by: Optional[str] = None):
        self.id: str = plan_id or f"plan_{str(uuid.uuid4())[:8]}"
        self.goal_id: str = goal_id
        self.description: Optional[str] = description
        self.actions: List[Action] = actions or []
        self.status: PlanSt = PlanSt.READY if actions else PlanSt.PENDING_GENERATION
        self.created_at: float = time.time()
        self.last_updated_at: float = self.created_at
        self.started_at: Optional[float] = None
        self.completed_at: Optional[float] = None
        self.created_by: Optional[str] = created_by
        self.current_action_idx: int = 0
        self.action_results: Dict[str, Any] = {}
        self.failure_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "goal_id": self.goal_id, "description": self.description,
            "actions": [a.to_dict() for a in self.actions], "status": self.status.value,
            "created_at": self.created_at, "last_updated_at": self.last_updated_at,
            "started_at": self.started_at, "completed_at": self.completed_at,
            "created_by": self.created_by, "current_action_idx": self.current_action_idx,
            "action_results": {k: str(v)[:200] for k, v in self.action_results.items()},
            "failure_reason": self.failure_reason
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Plan':
        plan = cls(goal_id=data["goal_id"], plan_id=data.get("id"), description=data.get("description"),
                   actions=[Action.from_dict(ad) for ad in data.get("actions", [])],
                   created_by=data.get("created_by"))
        plan.status = PlanSt(data.get("status", PlanSt.READY.value if plan.actions else PlanSt.PENDING_GENERATION.value))
        plan.created_at = data.get("created_at", time.time()); plan.last_updated_at = data.get("last_updated_at", plan.created_at)
        plan.started_at = data.get("started_at"); plan.completed_at = data.get("completed_at")
        plan.current_action_idx = data.get("current_action_idx", 0)
        plan.action_results = data.get("action_results", {})
        plan.failure_reason = data.get("failure_reason")
        return plan

class PlanManager:
    def __init__(self, agent_id: str,
                 action_executor: Callable[[Action], Awaitable[Tuple[bool, Any]]],
                 config_override: Optional[Config] = None,
                 test_mode: bool = False):

        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return

        self.agent_id = agent_id
        self.config = config_override or Config()
        self.plans: Dict[str, Plan] = {}
        self.log_prefix = f"PlanManager ({self.agent_id}):"

        self.action_executor = action_executor

        self.parallel_execution_enabled: bool = self.config.get(f"plan_manager.{self.agent_id}.parallel_execution.enabled", False)
        self.max_parallel_actions: int = self.config.get(f"plan_manager.{self.agent_id}.parallel_execution.max_concurrent", 3)

        logger.info(f"{self.log_prefix} Initialized. Parallel exec: {self.parallel_execution_enabled}, Max parallel: {self.max_parallel_actions}")
        self._initialized = True

    def create_plan(self, goal_id: str, actions_data: List[Dict[str, Any]],
                    plan_id: Optional[str] = None, description: Optional[str] = None,
                    created_by: Optional[str] = None) -> Plan:
        """Creates a new plan and stores it."""
        if not goal_id: raise ValueError("Goal ID cannot be empty for a plan.")
        if not actions_data or not isinstance(actions_data, list): raise ValueError("Plan must have a list of actions.")

        # <<< FIXED: Use the from_dict classmethod to correctly handle the id->action_id mapping >>>
        actions = [Action.from_dict(ad) for ad in actions_data]

        new_plan = Plan(goal_id, plan_id, description, actions, created_by)
        self.plans[new_plan.id] = new_plan
        logger.info(f"{self.log_prefix} Created plan '{new_plan.id}' for goal '{goal_id}' with {len(actions)} actions.")
        return new_plan

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        return self.plans.get(plan_id)

    def update_plan_status(self, plan_id: str, status: PlanSt, failure_reason: Optional[str] = None) -> bool:
        plan = self.get_plan(plan_id)
        if not plan:
            logger.warning(f"{self.log_prefix} Cannot update status for non-existent plan '{plan_id}'.")
            return False

        plan.status = status
        plan.last_updated_at = time.time()
        if failure_reason:
            plan.failure_reason = failure_reason
        elif status != PlanSt.FAILED_ACTION and status != PlanSt.FAILED_VALIDATION:
            plan.failure_reason = None

        if status == PlanSt.COMPLETED_SUCCESS or status.name.startswith("FAILED"):
            plan.completed_at = time.time()
            if plan.started_at is None:
                plan.started_at = plan.created_at

        logger.info(f"{self.log_prefix} Updated plan '{plan_id}' status to {status.name}.")
        return True

    def _update_action_state(self, plan: Plan, action: Action, status: ActionSt, result: Any = None):
        action.status = status
        action.result = result
        action.completed_at = time.time()
        plan.action_results[action.id] = result

        if status == ActionSt.FAILED:
            action.error_message = str(result)
            logger.warning(f"{self.log_prefix} Action '{action.type}' (ID: {action.id}) in plan '{plan.id}' FAILED. Reason: {action.error_message[:100]}")
            if action.is_critical:
                self.update_plan_status(plan.id, PlanSt.FAILED_ACTION, f"Critical action '{action.type}' (ID: {action.id}) failed.")
        elif status == ActionSt.COMPLETED_SUCCESS:
            logger.info(f"{self.log_prefix} Action '{action.type}' (ID: {action.id}) in plan '{plan.id}' COMPLETED_SUCCESS.")

        all_actions_terminal = all(act.status in [ActionSt.COMPLETED_SUCCESS, ActionSt.FAILED, ActionSt.SKIPPED_DEPENDENCY, ActionSt.CANCELLED] for act in plan.actions)
        if all_actions_terminal and plan.status not in [PlanSt.COMPLETED_SUCCESS, PlanSt.FAILED_ACTION]:
            if any(act.status == ActionSt.FAILED for act in plan.actions):
                self.update_plan_status(plan.id, PlanSt.FAILED_ACTION, "One or more actions in the plan failed.")
            else:
                self.update_plan_status(plan.id, PlanSt.COMPLETED_SUCCESS)

    async def execute_plan(self, plan_id: str) -> Plan:
        plan = self.get_plan(plan_id)
        if not plan:
            logger.error(f"{self.log_prefix} Cannot execute non-existent plan '{plan_id}'.")
            return Plan(goal_id="unknown", plan_id=plan_id, actions=[], description="Plan not found")

        if plan.status not in [PlanSt.READY, PlanSt.PAUSED]:
            logger.warning(f"{self.log_prefix} Plan '{plan_id}' not in READY or PAUSED state (is {plan.status.name}). Cannot execute.")
            return plan

        self.update_plan_status(plan_id, PlanSt.IN_PROGRESS)
        plan.started_at = time.time()
        logger.info(f"{self.log_prefix} Starting execution of plan '{plan_id}' for goal '{plan.goal_id}'. Parallel enabled: {self.parallel_execution_enabled}")

        if self.parallel_execution_enabled:
            await self._execute_plan_parallel_with_dependencies(plan)
        else:
            await self._execute_plan_sequential(plan)

        if plan.status == PlanSt.IN_PROGRESS:
            if all(a.status in [ActionSt.COMPLETED_SUCCESS, ActionSt.SKIPPED_DEPENDENCY] for a in plan.actions):
                self.update_plan_status(plan.id, PlanSt.COMPLETED_SUCCESS)
            else:
                logger.warning(f"{self.log_prefix} Plan '{plan_id}' finished execution loop but status is still IN_PROGRESS and not all actions terminal. This might indicate an issue.")

        logger.info(f"{self.log_prefix} Finished execution of plan '{plan_id}'. Final status: {plan.status.name}")
        return plan

    async def _execute_plan_sequential(self, plan: Plan):
        for idx, action in enumerate(plan.actions):
            plan.current_action_idx = idx
            if action.status == ActionSt.PENDING or action.status == ActionSt.READY_TO_EXECUTE:
                deps_met = all(
                    self.plans[plan.id].action_results.get(dep_id) is not None and
                    next((a for a in self.plans[plan.id].actions if a.id == dep_id), Action("dummy", action_id="dummy")).status == ActionSt.COMPLETED_SUCCESS
                    for dep_id in action.dependency_ids
                )
                if not deps_met:
                    logger.info(f"{self.log_prefix} Action '{action.type}' (ID: {action.id}) skipped due to unmet dependencies in sequential run.")
                    self._update_action_state(plan, action, ActionSt.SKIPPED_DEPENDENCY, "Unmet dependencies")
                    continue

                action.status = ActionSt.IN_PROGRESS
                action.started_at = time.time()
                action.attempt_count += 1
                logger.info(f"{self.log_prefix} Executing action (Seq) {idx+1}/{len(plan.actions)}: '{action.type}' (ID: {action.id})")

                resolved_params = await self._resolve_action_params_from_plan_results(plan, action.params)
                action_with_resolved_params = Action(action.type, resolved_params, action.id, action.description, action.dependency_ids, action.is_critical)

                success, result = await self.action_executor(action_with_resolved_params)
                self._update_action_state(plan, action, ActionSt.COMPLETED_SUCCESS if success else ActionSt.FAILED, result)

                if not success and action.is_critical:
                    logger.error(f"{self.log_prefix} Critical action '{action.type}' (ID: {action.id}) failed. Halting plan '{plan.id}'.")
                    self.update_plan_status(plan.id, PlanSt.FAILED_ACTION, f"Critical action {action.id} failed.")
                    break
            elif action.status in [ActionSt.COMPLETED_SUCCESS, ActionSt.SKIPPED_DEPENDENCY]:
                logger.debug(f"{self.log_prefix} Action '{action.type}' (ID: {action.id}) already {action.status.name}. Skipping.")
            elif action.status == ActionSt.FAILED:
                logger.warning(f"{self.log_prefix} Action '{action.type}' (ID: {action.id}) previously failed. Halting sequential plan '{plan.id}'.")
                if plan.status != PlanSt.FAILED_ACTION:
                    self.update_plan_status(plan.id, PlanSt.FAILED_ACTION, f"Previously failed action {action.id} encountered.")
                break

    async def _execute_plan_parallel_with_dependencies(self, plan: Plan):
        action_tasks: Dict[str, asyncio.Task] = {}

        while plan.status == PlanSt.IN_PROGRESS:
            actions_started_this_iteration = 0

            for action in plan.actions:
                if action.status == ActionSt.PENDING and action.id not in action_tasks:
                    deps_met = True
                    for dep_id in action.dependency_ids:
                        dep_action_obj = next((a for a in plan.actions if a.id == dep_id), None)
                        if not dep_action_obj or dep_action_obj.status != ActionSt.COMPLETED_SUCCESS:
                            deps_met = False
                            break

                    if deps_met:
                        if len(action_tasks) < self.max_parallel_actions:
                            action.status = ActionSt.IN_PROGRESS
                            action.started_at = time.time()
                            action.attempt_count += 1
                            logger.info(f"{self.log_prefix} Starting parallel action '{action.type}' (ID: {action.id}) for plan '{plan.id}'")

                            resolved_params = await self._resolve_action_params_from_plan_results(plan, action.params)
                            action_with_resolved_params = Action(action.type, resolved_params, action.id, action.description, action.dependency_ids, action.is_critical)

                            action_tasks[action.id] = asyncio.create_task(
                                self.action_executor(action_with_resolved_params), name=f"ActionTask_{action.id}"
                            )
                            actions_started_this_iteration += 1
                        else:
                            action.status = ActionSt.READY_TO_EXECUTE

            if not action_tasks and actions_started_this_iteration == 0:
                break

            if not action_tasks:
                await asyncio.sleep(0.01)
                continue

            done, pending = await asyncio.wait(list(action_tasks.values()), return_when=asyncio.FIRST_COMPLETED)

            for task_obj in done:
                completed_action_id: Optional[str] = None
                for aid, lauf_task in list(action_tasks.items()):
                    if lauf_task == task_obj:
                        completed_action_id = aid
                        break

                if completed_action_id:
                    try:
                        success, result = await task_obj
                        self._update_action_state(plan, next(a for a in plan.actions if a.id == completed_action_id), ActionSt.COMPLETED_SUCCESS if success else ActionSt.FAILED, result)
                    except Exception as e_task:
                        logger.error(f"{self.log_prefix} Task for action ID '{completed_action_id}' in plan '{plan.id}' raised exception: {e_task}", exc_info=True)
                        self._update_action_state(plan, next(a for a in plan.actions if a.id == completed_action_id), ActionSt.FAILED, str(e_task))
                    del action_tasks[completed_action_id]

            if plan.status.name.startswith("FAILED"):
                break

        if action_tasks:
            logger.info(f"{self.log_prefix} Plan '{plan.id}' loop ended with {len(action_tasks)} tasks still notionally running. Cancelling them.")
            for task_to_cancel in action_tasks.values():
                task_to_cancel.cancel()
            await asyncio.gather(*action_tasks.values(), return_exceptions=True)

    async def _resolve_action_params_from_plan_results(self, plan: Plan, params: Dict[str, Any]) -> Dict[str, Any]:
        resolved_params = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("$action_result."):
                parts = value[len("$action_result."):].split(".", 1)
                source_action_id = parts[0]
                field_path_str = parts[1] if len(parts) > 1 else None

                source_action_result = plan.action_results.get(source_action_id)
                if source_action_result is not None:
                    if field_path_str:
                        try:
                            current_val = source_action_result
                            for field_part in field_path_str.split('.'):
                                if isinstance(current_val, dict):
                                    current_val = current_val.get(field_part)
                                elif hasattr(current_val, field_part):
                                    current_val = getattr(current_val, field_part)
                                else:
                                    current_val = None
                                    break
                            resolved_params[key] = current_val
                            logger.debug(f"{self.log_prefix} Plan '{plan.id}': Resolved param '{key}' from action '{source_action_id}' field '{field_path_str}' to: {str(current_val)[:50]}")
                        except Exception as e_resolve:
                            logger.warning(f"{self.log_prefix} Plan '{plan.id}': Failed to resolve field path '{field_path_str}' in result of action '{source_action_id}': {e_resolve}. Using None for param '{key}'.")
                            resolved_params[key] = None
                    else:
                        resolved_params[key] = source_action_result
                        logger.debug(f"{self.log_prefix} Plan '{plan.id}': Resolved param '{key}' from whole result of action '{source_action_id}'.")
                else:
                    logger.warning(f"{self.log_prefix} Plan '{plan.id}': Action result for '{source_action_id}' not found for param '{key}'. Using None.")
                    resolved_params[key] = None
            elif isinstance(value, dict):
                resolved_params[key] = await self._resolve_action_params_from_plan_results(plan, value)
            elif isinstance(value, list):
                resolved_params[key] = [await self._resolve_action_params_from_plan_results(plan, item) if isinstance(item, dict) else item for item in value]
            else:
                resolved_params[key] = value
        return resolved_params

    def get_all_plans(self) -> List[Plan]:
        return list(self.plans.values())

    def get_plans_by_status(self, status: PlanSt) -> List[Plan]:
        return [p for p in self.plans.values() if p.status == status]

    def get_plans_for_goal(self, goal_id: str) -> List[Plan]:
        return [p for p in self.plans.values() if p.goal_id == goal_id]

    @classmethod
    def reset_instance(cls):
        cls._instance = None
        logger.debug("PlanManager instance reset.")
