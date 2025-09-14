# learning/goal_management.py
"""
Goal Management System for strategic agents in mindX
Provides GoalManager using a priority queue and various prioritization strategies.
"""
import time
import uuid
import heapq # For priority queue implementation
# import logging # Use get_logger
from typing import Dict, List, Any, Optional, Tuple, Callable, Set # MODIFIED: Added Set
from enum import Enum
from abc import ABC, abstractmethod
from collections import defaultdict # ADDED for get_goal_status_summary

# Assuming this module is part of the learning package, utils is a sibling top-level package
from utils.logging_config import get_logger # Corrected import path

logger = get_logger(__name__)

class GoalSt(Enum):
    """Constants for goal status values within the GoalManager."""
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED_SUCCESS = "COMPLETED_SUCCESS"
    COMPLETED_NO_ACTION = "COMPLETED_NO_ACTION"
    FAILED_PLANNING = "FAILED_PLANNING"
    FAILED_EXECUTION = "FAILED_EXECUTION"
    PAUSED_DEPENDENCY = "PAUSED_DEPENDENCY"
    CANCELLED = "CANCELLED"

class Goal: # pragma: no cover
    """Represents a goal within the GoalManager."""
    def __init__(self,
                 description: str,
                 priority: int,
                 goal_id: Optional[str] = None,
                 metadata: Optional[Dict[str, Any]] = None,
                 parent_goal_id: Optional[str] = None,
                 source: Optional[str] = None):

        if not isinstance(description, str) or not description.strip():
            raise ValueError("Goal description must be a non-empty string")
        if not isinstance(priority, int) or not (1 <= priority <= 10):
            logger.warning(f"Goal '{description}': Invalid priority {priority}, clamping to range 1-10.")
            priority = max(1, min(10, priority))

        self.id: str = goal_id or f"goal_{str(uuid.uuid4())[:8]}"
        self.description: str = description
        self.priority: int = priority
        self.status: GoalSt = GoalSt.PENDING
        self.created_at: float = time.time()
        self.last_updated_at: float = self.created_at
        self.metadata: Dict[str, Any] = metadata or {}
        self.parent_goal_id: Optional[str] = parent_goal_id
        self.subgoal_ids: List[str] = []
        self.dependency_ids: List[str] = []
        self.dependent_ids: List[str] = []
        self.current_plan_id: Optional[str] = None
        self.attempt_count: int = 0
        self.failure_reason: Optional[str] = None
        self.source: Optional[str] = source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "description": self.description, "priority": self.priority,
            "status": self.status.value, "created_at": self.created_at,
            "last_updated_at": self.last_updated_at, "metadata": self.metadata,
            "parent_goal_id": self.parent_goal_id, "subgoal_ids": self.subgoal_ids,
            "dependency_ids": self.dependency_ids, "dependent_ids": self.dependent_ids,
            "current_plan_id": self.current_plan_id, "attempt_count": self.attempt_count,
            "failure_reason": self.failure_reason, "source": self.source
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Goal':
        goal = cls(description=data["description"], priority=data["priority"], goal_id=data.get("id"), # Use get for goal_id
                   metadata=data.get("metadata"), parent_goal_id=data.get("parent_goal_id"),
                   source=data.get("source"))
        goal.status = GoalSt(data.get("status", GoalSt.PENDING.value))
        goal.created_at = data.get("created_at", time.time())
        goal.last_updated_at = data.get("last_updated_at", goal.created_at)
        goal.subgoal_ids = data.get("subgoal_ids", [])
        goal.dependency_ids = data.get("dependency_ids", [])
        goal.dependent_ids = data.get("dependent_ids", [])
        goal.current_plan_id = data.get("current_plan_id")
        goal.attempt_count = data.get("attempt_count", 0)
        goal.failure_reason = data.get("failure_reason")
        return goal

    def __lt__(self, other: 'Goal') -> bool:
        if not isinstance(other, Goal): return NotImplemented
        return (-self.priority, self.created_at) < (-other.priority, other.created_at)

class GoalManager:
    """
    Manages goals for an agent using a priority queue and supports dependencies.
    """
    def __init__(self, agent_id: str):
        self.agent_id: str = agent_id
        self.goals: Dict[str, Goal] = {}
        self.priority_queue: List[Tuple[int, float, str]] = []
        self.log_prefix = f"GoalManager ({self.agent_id}):"
        logger.info(f"{self.log_prefix} Initialized.")

    def add_goal(self, description: str, priority: int = 5,
                 goal_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
                 parent_goal_id: Optional[str] = None, dependency_ids: Optional[List[str]] = None,
                 source: Optional[str] = None) -> Goal:
        for existing_goal in self.goals.values(): # pragma: no cover
            if existing_goal.description == description and existing_goal.status not in [GoalSt.COMPLETED_SUCCESS, GoalSt.FAILED_EXECUTION, GoalSt.FAILED_PLANNING, GoalSt.CANCELLED]: # Added FAILED states
                logger.info(f"{self.log_prefix} Goal with description '{description}' already exists (ID: {existing_goal.id}). Updating priority if higher.")
                if priority > existing_goal.priority:
                    self.update_goal_priority(existing_goal.id, priority)
                return existing_goal

        new_goal = Goal(description, priority, goal_id, metadata, parent_goal_id, source)
        self.goals[new_goal.id] = new_goal

        can_be_active = True
        if dependency_ids:
            new_goal.dependency_ids = list(set(dependency_ids))
            for dep_id in new_goal.dependency_ids:
                if dep_id not in self.goals: # pragma: no cover
                    logger.warning(f"{self.log_prefix} Goal '{new_goal.id}' has non-existent dependency '{dep_id}'. Marking as PAUSED_DEPENDENCY.")
                    new_goal.status = GoalSt.PAUSED_DEPENDENCY; can_be_active = False; break
                dependency_goal = self.goals[dep_id]
                if dep_id not in dependency_goal.dependent_ids: # Ensure not to add duplicates
                    dependency_goal.dependent_ids.append(new_goal.id)
                if dependency_goal.status != GoalSt.COMPLETED_SUCCESS:
                    can_be_active = False

        if can_be_active:
            heapq.heappush(self.priority_queue, (-new_goal.priority, new_goal.created_at, new_goal.id))
        else:
            if new_goal.status == GoalSt.PENDING: # Only set to paused if it wasn't already set by non-existent dep
                new_goal.status = GoalSt.PAUSED_DEPENDENCY
            logger.info(f"{self.log_prefix} Goal '{new_goal.description}' (ID: {new_goal.id}) added but Status is: {new_goal.status.name} (may be PAUSED).")


        logger.info(f"{self.log_prefix} Added goal '{new_goal.description}' (ID: {new_goal.id}), Prio: {new_goal.priority}, Status: {new_goal.status.name}")
        return new_goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self.goals.get(goal_id)

    def get_highest_priority_pending_goal(self) -> Optional[Goal]:
        temp_queue = []
        selected_goal: Optional[Goal] = None
        while self.priority_queue:
            neg_prio, ts, goal_id = heapq.heappop(self.priority_queue)
            goal = self.goals.get(goal_id)
            if not goal or goal.status != GoalSt.PENDING:
                continue

            dependencies_met = True
            for dep_id in goal.dependency_ids:
                dep_goal = self.goals.get(dep_id)
                if not dep_goal or dep_goal.status != GoalSt.COMPLETED_SUCCESS:
                    dependencies_met = False; break

            if dependencies_met:
                selected_goal = goal
                heapq.heappush(temp_queue, (neg_prio, ts, goal_id))
                break
            else:
                heapq.heappush(temp_queue, (neg_prio, ts, goal_id)) # Put back if deps not met

        while temp_queue: # Restore all items (including selected if found, or all if none found)
            heapq.heappush(self.priority_queue, heapq.heappop(temp_queue))

        if selected_goal: logger.debug(f"{self.log_prefix} Highest priority pending goal: {selected_goal.id} ('{selected_goal.description}')")
        else: logger.debug(f"{self.log_prefix} No actionable pending goals found in priority queue.")
        return selected_goal


    def update_goal_status(self, goal_id: str, status: GoalSt, failure_reason: Optional[str] = None) -> bool:
        goal = self.goals.get(goal_id)
        if not goal: # pragma: no cover
            logger.error(f"{self.log_prefix} Cannot update status for non-existent goal ID '{goal_id}'.")
            return False
        if not isinstance(status, GoalSt): # pragma: no cover
            logger.error(f"{self.log_prefix} Invalid status type for goal ID '{goal_id}': {type(status)}. Must be GoalSt enum.")
            return False

        previous_status = goal.status
        goal.status = status
        goal.last_updated_at = time.time()
        if failure_reason: goal.failure_reason = failure_reason
        elif status not in [GoalSt.FAILED_EXECUTION, GoalSt.FAILED_PLANNING] : goal.failure_reason = None

        logger.info(f"{self.log_prefix} Updated goal '{goal.description}' (ID: {goal_id}) from {previous_status.name} to {status.name}.")

        if status == GoalSt.COMPLETED_SUCCESS:
            self._activate_dependent_goals(goal_id)

        if status in [GoalSt.COMPLETED_SUCCESS, GoalSt.FAILED_EXECUTION, GoalSt.FAILED_PLANNING, GoalSt.CANCELLED, GoalSt.COMPLETED_NO_ACTION]:
            self._rebuild_priority_queue_from_active_goals()

        return True

    def _activate_dependent_goals(self, completed_goal_id: str): # pragma: no cover
        goal = self.goals.get(completed_goal_id)
        if not goal or not goal.dependent_ids: return

        for dependent_id in list(goal.dependent_ids): # Iterate over a copy if list might change
            dependent_goal = self.goals.get(dependent_id)
            if dependent_goal and dependent_goal.status == GoalSt.PAUSED_DEPENDENCY:
                all_deps_met = True
                for dep_id_for_dependent in dependent_goal.dependency_ids:
                    dep_g = self.goals.get(dep_id_for_dependent)
                    if not dep_g or dep_g.status != GoalSt.COMPLETED_SUCCESS:
                        all_deps_met = False; break
                if all_deps_met:
                    logger.info(f"{self.log_prefix} All dependencies met for '{dependent_goal.description}' (ID: {dependent_id}). Setting to PENDING.")
                    # Important: Use update_goal_status to correctly handle queue
                    self.update_goal_status(dependent_id, GoalSt.PENDING)


    def update_goal_priority(self, goal_id: str, new_priority: int) -> bool: # pragma: no cover
        goal = self.goals.get(goal_id)
        if not goal: logger.error(f"{self.log_prefix} Goal ID '{goal_id}' not found for priority update."); return False
        if not (1 <= new_priority <= 10): new_priority = max(1, min(10, new_priority)); logger.warning(f"{self.log_prefix} Clamped priority for {goal_id} to {new_priority}.")

        goal.priority = new_priority
        goal.last_updated_at = time.time()
        logger.info(f"{self.log_prefix} Updated priority for goal '{goal.description}' (ID: {goal_id}) to {new_priority}.")

        self._rebuild_priority_queue_from_active_goals()
        return True

    def _rebuild_priority_queue_from_active_goals(self): # pragma: no cover
        new_queue = []
        for goal_id, goal_data in self.goals.items():
            # Only goals that are PENDING or PAUSED_DEPENDENCY are candidates for the active queue
            # (get_highest_priority_pending_goal will filter PAUSED_DEPENDENCY further if deps not met)
            if goal_data.status in [GoalSt.PENDING, GoalSt.PAUSED_DEPENDENCY, GoalSt.ACTIVE]:
                 new_queue.append((-goal_data.priority, goal_data.created_at, goal_id))

        self.priority_queue = new_queue
        heapq.heapify(self.priority_queue)
        logger.debug(f"{self.log_prefix} Rebuilt priority queue. Current size: {len(self.priority_queue)}")

    def add_dependency(self, goal_id: str, depends_on_goal_id: str) -> bool: # pragma: no cover
        if goal_id not in self.goals or depends_on_goal_id not in self.goals:
            logger.error(f"{self.log_prefix} One or both goal IDs not found for adding dependency: {goal_id}, {depends_on_goal_id}"); return False
        if goal_id == depends_on_goal_id: logger.warning(f"{self.log_prefix} Goal cannot depend on itself: {goal_id}"); return False

        # Pass a new set for each top-level call to _would_create_circular_dependency
        if self._would_create_circular_dependency(goal_id, depends_on_goal_id, set()):
            logger.error(f"{self.log_prefix} Adding dependency from '{goal_id}' to '{depends_on_goal_id}' would create a circular dependency. Aborted.")
            return False

        goal = self.goals[goal_id]
        dependency_goal = self.goals[depends_on_goal_id]

        if depends_on_goal_id not in goal.dependency_ids: goal.dependency_ids.append(depends_on_goal_id)
        if goal_id not in dependency_goal.dependent_ids: dependency_goal.dependent_ids.append(goal_id)

        if dependency_goal.status != GoalSt.COMPLETED_SUCCESS and goal.status == GoalSt.PENDING:
            self.update_goal_status(goal_id, GoalSt.PAUSED_DEPENDENCY) # This will trigger queue rebuild

        logger.info(f"{self.log_prefix} Added dependency: Goal '{goal.description}' now depends on '{dependency_goal.description}'.")
        return True

    def _would_create_circular_dependency(self, current_goal_checking_deps: str, potential_dependency: str, visited_path: Set[str]) -> bool: # pragma: no cover
        """
        Checks if making 'current_goal_checking_deps' depend on 'potential_dependency'
        would create a cycle. 'visited_path' tracks the current dependency chain being explored
        from 'potential_dependency' backwards.
        """
        if potential_dependency == current_goal_checking_deps:
            return True # Direct cycle: A depends on B, and B is A.

        if potential_dependency in visited_path: # We've come back to a node already in this specific path check
            return True

        visited_path.add(potential_dependency)

        dep_goal_obj = self.goals.get(potential_dependency)
        if dep_goal_obj:
            for dep_of_potential_dependency in dep_goal_obj.dependency_ids:
                if self._would_create_circular_dependency(current_goal_checking_deps, dep_of_potential_dependency, visited_path.copy()): # Pass copy
                    return True
        return False

    def get_all_goals(self, status_filter: Optional[List[GoalSt]] = None) -> List[Goal]: # pragma: no cover
        all_goals = list(self.goals.values())
        if status_filter:
            return [g for g in all_goals if g.status in status_filter]
        return all_goals

    def get_goal_status_summary(self) -> Dict[str, int]: # pragma: no cover
        summary: Dict[str, int] = defaultdict(int) # Use defaultdict
        for goal in self.goals.values():
            summary[goal.status.name] += 1
        return dict(summary)


class GoalPrioritizationStrategy(ABC): # pragma: no cover
    @abstractmethod
    def sort_goals(self, goals: List[Goal]) -> List[Goal]: pass
    def get_name(self) -> str: return self.__class__.__name__

class SimplePriorityThenTimeStrategy(GoalPrioritizationStrategy): # pragma: no cover
    def sort_goals(self, goals: List[Goal]) -> List[Goal]:
        return sorted(goals, key=lambda g: (-g.priority, g.created_at))

class UrgencyStrategy(GoalPrioritizationStrategy): # pragma: no cover
    def __init__(self, urgency_factor: float = 0.0001):
        self.urgency_factor = urgency_factor
    def sort_goals(self, goals: List[Goal]) -> List[Goal]:
        now = time.time()
        scored_goals = [(goal, goal.priority + ((now - goal.created_at) * self.urgency_factor)) for goal in goals]
        return [g_obj for g_obj, score in sorted(scored_goals, key=lambda x: -x[1])]

# Removed the __main__ block with asyncio.run as it's not needed for library code.
# If testing is desired, it should be in a separate test file.
