# mindx/core/nonmonotonic_agent.py
"""
NonMonotonicAgent: Non-monotonic reasoning and belief adaptation.

This agent handles belief revision when new information contradicts existing beliefs,
manages default assumptions, handles belief conflicts, and adapts to changing environments.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum

from utils.config import Config
from utils.logging_config import get_logger
from agents.core.belief_system import BeliefSystem, BeliefSource, Belief
from llm.llm_interface import LLMHandlerInterface
from llm.llm_factory import create_llm_handler
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

logger = get_logger(__name__)


class ConflictType(Enum):
    """Types of belief conflicts."""
    DIRECT_CONTRADICTION = "direct_contradiction"
    INCONSISTENCY = "inconsistency"
    DEFAULT_OVERRIDE = "default_override"
    EVIDENCE_CONFLICT = "evidence_conflict"


class NonMonotonicAgent:
    """
    Agent specialized in non-monotonic reasoning and belief adaptation.
    Handles belief revision when new information contradicts existing beliefs.
    """
    
    def __init__(
        self,
        agent_id: str = "nonmonotonic_agent",
        belief_system: Optional[BeliefSystem] = None,
        coordinator_agent: Optional[CoordinatorAgent] = None,
        memory_agent: Optional[MemoryAgent] = None,
        llm_handler: Optional[LLMHandlerInterface] = None,
        config: Optional[Config] = None,
        test_mode: bool = False
    ):
        self.agent_id = agent_id
        self.belief_system = belief_system or BeliefSystem(test_mode=test_mode)
        self.coordinator_agent = coordinator_agent
        self.memory_agent = memory_agent
        self.config = config or Config(test_mode=test_mode)
        self.llm_handler = llm_handler
        self.test_mode = test_mode
        self.log_prefix = f"NonMonotonicAgent ({self.agent_id}):"
        
        # Default assumptions
        self.default_assumptions: Dict[str, Any] = {}
        
        # Conflict history
        self.conflict_history: List[Dict[str, Any]] = []
        
        # Belief revision history
        self.revision_history: List[Dict[str, Any]] = []
        
        # Monitor belief system for conflicts
        self._monitoring = False
        if self.coordinator_agent:
            self._subscribe_to_events()
    
    def _subscribe_to_events(self):
        """Subscribe to coordinator events for conflict detection."""
        if not self.coordinator_agent:
            return
        
        try:
            # Subscribe to events that might indicate conflicts
            self.coordinator_agent.subscribe("belief.updated", self._on_belief_updated)
            logger.info(f"{self.log_prefix} Subscribed to coordinator events")
        except Exception as e:
            logger.error(f"{self.log_prefix} Error subscribing to events: {e}", exc_info=True)
    
    async def _async_init(self):
        """Async initialization - create LLM handler if not provided."""
        if not self.llm_handler:
            try:
                self.llm_handler = await create_llm_handler()
                if self.llm_handler:
                    logger.info(f"{self.log_prefix} LLM handler initialized: {self.llm_handler.provider_name}")
            except Exception as e:
                logger.error(f"{self.log_prefix} Failed to create LLM handler: {e}", exc_info=True)
    
    async def detect_conflicts(
        self,
        new_belief_key: str,
        new_belief_value: Any,
        confidence_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Detect conflicts between a new belief and existing beliefs.
        
        Args:
            new_belief_key: Key of the new belief
            new_belief_value: Value of the new belief
            confidence_threshold: Minimum confidence to consider a conflict
        
        Returns:
            List of detected conflicts
        """
        conflicts = []
        
        # Get all existing beliefs
        all_beliefs = await self._get_all_beliefs()
        
        for belief_key, belief in all_beliefs.items():
            if belief_key == new_belief_key:
                continue
            
            # Check for direct contradiction
            if await self._is_contradiction(new_belief_value, belief.value):
                conflicts.append({
                    "type": ConflictType.DIRECT_CONTRADICTION.value,
                    "new_belief_key": new_belief_key,
                    "conflicting_belief_key": belief_key,
                    "new_value": new_belief_value,
                    "conflicting_value": belief.value,
                    "confidence": belief.confidence
                })
        
        return conflicts
    
    async def revise_belief(
        self,
        belief_key: str,
        new_value: Any,
        new_confidence: float,
        new_source: BeliefSource,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Revise a belief when new information contradicts it.
        
        Args:
            belief_key: Key of the belief to revise
            new_value: New value for the belief
            new_confidence: New confidence level
            new_source: Source of the new information
            reason: Reason for the revision
        
        Returns:
            Dictionary with revision results
        """
        if not self.llm_handler:
            await self._async_init()
        
        # Detect conflicts
        conflicts = await self.detect_conflicts(belief_key, new_value)
        
        # Get existing belief
        existing_belief = await self.belief_system.get_belief(belief_key)
        
        revision_result = {
            "belief_key": belief_key,
            "old_value": existing_belief.value if existing_belief else None,
            "new_value": new_value,
            "conflicts_detected": len(conflicts),
            "revision_applied": False
        }
        
        # Use LLM to determine if revision is appropriate
        if conflicts and self.llm_handler:
            prompt = (
                f"Determine if this belief revision is appropriate:\n\n"
                f"Belief Key: {belief_key}\n"
                f"Old Value: {json.dumps(existing_belief.value) if existing_belief else 'None'}\n"
                f"New Value: {json.dumps(new_value)}\n"
                f"New Confidence: {new_confidence}\n"
                f"Reason: {reason or 'Not provided'}\n\n"
                f"Conflicts Detected: {len(conflicts)}\n"
                f"Conflicts: {json.dumps(conflicts, indent=2)}\n\n"
                f"Provide decision in JSON format with:\n"
                f"- should_revise: Whether to apply the revision (true/false)\n"
                f"- reasoning: Explanation of the decision\n"
                f"- conflict_resolution: How conflicts are resolved\n"
            )
            
            try:
                response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
                decision = json.loads(response_str)
                
                if decision.get("should_revise", False):
                    # Apply revision
                    await self.belief_system.update_belief(
                        belief_key,
                        new_value,
                        confidence=new_confidence,
                        source=new_source
                    )
                    
                    revision_result.update({
                        "revision_applied": True,
                        "reasoning": decision.get("reasoning"),
                        "conflict_resolution": decision.get("conflict_resolution")
                    })
                    
                    # Record revision
                    revision_record = {
                        "timestamp": time.time(),
                        "belief_key": belief_key,
                        "old_value": existing_belief.value if existing_belief else None,
                        "new_value": new_value,
                        "conflicts": conflicts,
                        "reason": reason
                    }
                    self.revision_history.append(revision_record)
                    
                    # Store conflict in history
                    for conflict in conflicts:
                        conflict_record = {
                            "timestamp": time.time(),
                            "conflict": conflict,
                            "resolved": True
                        }
                        self.conflict_history.append(conflict_record)
                    
                    if self.memory_agent:
                        await self.memory_agent.log_process(
                            "belief_revision",
                            revision_record,
                            {"agent_id": self.agent_id}
                        )
                else:
                    revision_result["reasoning"] = decision.get("reasoning", "Revision not applied")
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in belief revision: {e}", exc_info=True)
                revision_result["error"] = str(e)
        else:
            # No conflicts or no LLM - apply revision directly
            await self.belief_system.update_belief(
                belief_key,
                new_value,
                confidence=new_confidence,
                source=new_source
            )
            revision_result["revision_applied"] = True
        
        return revision_result
    
    async def handle_default_assumption(
        self,
        assumption_key: str,
        default_value: Any,
        override_value: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Handle default assumptions that can be overridden.
        
        Args:
            assumption_key: Key of the assumption
            default_value: Default value
            override_value: Optional override value
        
        Returns:
            Dictionary with assumption handling results
        """
        if override_value is not None:
            # Override default
            self.default_assumptions[assumption_key] = override_value
            await self.belief_system.update_belief(
                assumption_key,
                override_value,
                confidence=0.8,
                source=BeliefSource.DEFAULT
            )
            return {
                "assumption_key": assumption_key,
                "value": override_value,
                "is_default": False
            }
        else:
            # Use default
            if assumption_key not in self.default_assumptions:
                self.default_assumptions[assumption_key] = default_value
            
            await self.belief_system.update_belief(
                assumption_key,
                default_value,
                confidence=0.6,
                source=BeliefSource.DEFAULT
            )
            return {
                "assumption_key": assumption_key,
                "value": default_value,
                "is_default": True
            }
    
    async def manage_belief_conflicts(
        self,
        conflict_resolution_strategy: str = "confidence_based"
    ) -> Dict[str, Any]:
        """
        Manage all detected belief conflicts.
        
        Args:
            conflict_resolution_strategy: Strategy for resolving conflicts
        
        Returns:
            Dictionary with conflict management results
        """
        # Get all beliefs
        all_beliefs = await self._get_all_beliefs()
        
        conflicts_resolved = 0
        conflicts_remaining = []
        
        # Check for conflicts between all belief pairs
        belief_keys = list(all_beliefs.keys())
        for i, key1 in enumerate(belief_keys):
            for key2 in belief_keys[i+1:]:
                belief1 = all_beliefs[key1]
                belief2 = all_beliefs[key2]
                
                if await self._is_contradiction(belief1.value, belief2.value):
                    # Resolve conflict based on strategy
                    if conflict_resolution_strategy == "confidence_based":
                        if belief1.confidence > belief2.confidence:
                            # Keep belief1, revise belief2
                            await self.revise_belief(
                                key2,
                                belief1.value,
                                belief1.confidence * 0.9,  # Slightly lower confidence
                                BeliefSource.INFERENCE,
                                f"Resolved conflict with {key1} based on confidence"
                            )
                        else:
                            await self.revise_belief(
                                key1,
                                belief2.value,
                                belief2.confidence * 0.9,
                                BeliefSource.INFERENCE,
                                f"Resolved conflict with {key2} based on confidence"
                            )
                        conflicts_resolved += 1
                    else:
                        conflicts_remaining.append({
                            "belief1_key": key1,
                            "belief2_key": key2,
                            "value1": belief1.value,
                            "value2": belief2.value
                        })
        
        return {
            "conflicts_resolved": conflicts_resolved,
            "conflicts_remaining": len(conflicts_remaining),
            "remaining_conflicts": conflicts_remaining
        }
    
    async def adapt_to_changing_environment(
        self,
        environment_changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Adapt beliefs to a changing environment.
        
        Args:
            environment_changes: Dictionary describing environment changes
        
        Returns:
            Dictionary with adaptation results
        """
        adaptations = []
        
        for change_key, change_value in environment_changes.items():
            # Check if this change affects any beliefs
            affected_beliefs = await self._find_affected_beliefs(change_key, change_value)
            
            for belief_key in affected_beliefs:
                # Revise belief to adapt to change
                result = await self.revise_belief(
                    belief_key,
                    change_value,
                    0.7,
                    BeliefSource.PERCEPTION,
                    f"Adapting to environment change: {change_key}"
                )
                adaptations.append(result)
        
        return {
            "adaptations_applied": len(adaptations),
            "adaptations": adaptations
        }
    
    async def _is_contradiction(self, value1: Any, value2: Any) -> bool:
        """Check if two values contradict each other."""
        # Simple contradiction detection
        if isinstance(value1, bool) and isinstance(value2, bool):
            return value1 != value2
        if isinstance(value1, (int, float)) and isinstance(value2, (int, float)):
            # Consider contradictory if significantly different
            return abs(value1 - value2) > max(abs(value1), abs(value2)) * 0.5
        if isinstance(value1, str) and isinstance(value2, str):
            # Check for explicit contradictions
            contradictions = [
                ("true", "false"),
                ("yes", "no"),
                ("enabled", "disabled"),
                ("active", "inactive")
            ]
            v1_lower = value1.lower()
            v2_lower = value2.lower()
            for c1, c2 in contradictions:
                if (v1_lower == c1 and v2_lower == c2) or (v1_lower == c2 and v2_lower == c1):
                    return True
        return False
    
    async def _get_all_beliefs(self) -> Dict[str, Belief]:
        """Get all beliefs from the belief system."""
        # This would need to be implemented in BeliefSystem or accessed differently
        # For now, return empty dict
        return {}
    
    async def _find_affected_beliefs(self, change_key: str, change_value: Any) -> List[str]:
        """Find beliefs affected by an environment change."""
        # This would analyze which beliefs are related to the change
        return []
    
    async def _on_belief_updated(self, data: Dict[str, Any]):
        """Handle belief update event - check for conflicts."""
        belief_key = data.get("belief_key")
        if belief_key:
            logger.debug(f"{self.log_prefix} Belief updated: {belief_key}, checking for conflicts")
            # Could trigger conflict detection here
    
    async def shutdown(self):
        """Shutdown the non-monotonic agent."""
        logger.info(f"{self.log_prefix} Shutting down")
