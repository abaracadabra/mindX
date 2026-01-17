# mindx/core/epistemic_agent.py
"""
EpistemicAgent: Specialized knowledge and belief management.

This agent wraps BeliefSystem with an agent interface, providing knowledge base management,
belief certainty tracking, knowledge dynamics, and epistemic state queries.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from utils.config import Config
from utils.logging_config import get_logger
from agents.core.belief_system import BeliefSystem, BeliefSource, Belief
from llm.llm_interface import LLMHandlerInterface
from llm.llm_factory import create_llm_handler
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

logger = get_logger(__name__)


class CertaintyLevel(Enum):
    """Levels of belief certainty."""
    VERY_HIGH = "very_high"  # 0.9-1.0
    HIGH = "high"  # 0.7-0.9
    MEDIUM = "medium"  # 0.5-0.7
    LOW = "low"  # 0.3-0.5
    VERY_LOW = "very_low"  # 0.0-0.3


class EpistemicAgent:
    """
    Agent specialized in knowledge and belief management.
    Provides epistemic state queries and knowledge base management.
    """
    
    def __init__(
        self,
        agent_id: str = "epistemic_agent",
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
        self.log_prefix = f"EpistemicAgent ({self.agent_id}):"
        
        # Knowledge base metadata
        self.knowledge_stats: Dict[str, Any] = {
            "total_beliefs": 0,
            "beliefs_by_source": {},
            "beliefs_by_certainty": {},
            "last_updated": time.time()
        }
    
    async def _async_init(self):
        """Async initialization - create LLM handler if not provided."""
        if not self.llm_handler:
            try:
                self.llm_handler = await create_llm_handler()
                if self.llm_handler:
                    logger.info(f"{self.log_prefix} LLM handler initialized: {self.llm_handler.provider_name}")
            except Exception as e:
                logger.error(f"{self.log_prefix} Failed to create LLM handler: {e}", exc_info=True)
    
    async def query_epistemic_state(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the epistemic state (what is known).
        
        Args:
            query: Query about knowledge state
            filters: Optional filters (source, certainty, etc.)
        
        Returns:
            Dictionary with epistemic state information
        """
        if not self.llm_handler:
            await self._async_init()
        
        # Get knowledge statistics
        stats = await self.get_knowledge_statistics()
        
        prompt = (
            f"Answer this epistemic query: {query}\n\n"
            f"Knowledge Statistics:\n{json.dumps(stats, indent=2)}\n\n"
            f"Filters: {json.dumps(filters, indent=2) if filters else 'None'}\n\n"
            f"Provide answer in JSON format with:\n"
            f"- answer: Direct answer to the query\n"
            f"- relevant_beliefs: List of relevant belief keys\n"
            f"- certainty: Overall certainty of the answer\n"
            f"- sources: List of sources for the information\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            result = json.loads(response_str)
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "epistemic_query",
                    {
                        "timestamp": time.time(),
                        "query": query,
                        "result": result
                    },
                    {"agent_id": self.agent_id}
                )
            
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error querying epistemic state: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def get_knowledge_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge base.
        
        Returns:
            Dictionary with knowledge statistics
        """
        # This would query the belief system for statistics
        # For now, return basic structure
        return {
            "total_beliefs": self.knowledge_stats.get("total_beliefs", 0),
            "beliefs_by_source": self.knowledge_stats.get("beliefs_by_source", {}),
            "beliefs_by_certainty": self.knowledge_stats.get("beliefs_by_certainty", {}),
            "last_updated": self.knowledge_stats.get("last_updated", time.time())
        }
    
    async def track_belief_certainty(
        self,
        belief_key: str,
        certainty_level: CertaintyLevel
    ) -> Dict[str, Any]:
        """
        Track the certainty level of a belief.
        
        Args:
            belief_key: Key of the belief
            certainty_level: Certainty level
        
        Returns:
            Dictionary with tracking results
        """
        belief = await self.belief_system.get_belief(belief_key)
        
        if belief:
            # Update certainty tracking
            certainty_key = certainty_level.value
            if certainty_key not in self.knowledge_stats["beliefs_by_certainty"]:
                self.knowledge_stats["beliefs_by_certainty"][certainty_key] = []
            
            if belief_key not in self.knowledge_stats["beliefs_by_certainty"][certainty_key]:
                self.knowledge_stats["beliefs_by_certainty"][certainty_key].append(belief_key)
            
            self.knowledge_stats["last_updated"] = time.time()
            
            return {
                "belief_key": belief_key,
                "certainty_level": certainty_level.value,
                "confidence": belief.confidence,
                "tracked": True
            }
        else:
            return {
                "belief_key": belief_key,
                "error": "Belief not found"
            }
    
    async def manage_knowledge_base(
        self,
        operation: str,
        belief_key: Optional[str] = None,
        belief_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Manage the knowledge base (add, update, remove beliefs).
        
        Args:
            operation: Operation to perform ("add", "update", "remove", "query")
            belief_key: Key of the belief
            belief_data: Data for the belief
        
        Returns:
            Dictionary with operation results
        """
        if operation == "add" and belief_key and belief_data:
            await self.belief_system.add_belief(
                belief_key,
                belief_data.get("value"),
                confidence=belief_data.get("confidence", 0.7),
                source=BeliefSource(belief_data.get("source", BeliefSource.DEFAULT.value))
            )
            self.knowledge_stats["total_beliefs"] += 1
            return {"operation": "add", "success": True, "belief_key": belief_key}
        
        elif operation == "update" and belief_key and belief_data:
            await self.belief_system.update_belief(
                belief_key,
                belief_data.get("value"),
                confidence=belief_data.get("confidence", 0.7),
                source=BeliefSource(belief_data.get("source", BeliefSource.DEFAULT.value))
            )
            return {"operation": "update", "success": True, "belief_key": belief_key}
        
        elif operation == "remove" and belief_key:
            # BeliefSystem doesn't have remove, but we can mark as invalid
            return {"operation": "remove", "success": False, "message": "Remove not directly supported"}
        
        elif operation == "query" and belief_key:
            belief = await self.belief_system.get_belief(belief_key)
            if belief:
                return {
                    "operation": "query",
                    "success": True,
                    "belief": belief.to_dict()
                }
            else:
                return {
                    "operation": "query",
                    "success": False,
                    "message": "Belief not found"
                }
        
        else:
            return {
                "operation": operation,
                "success": False,
                "message": "Invalid operation or missing parameters"
            }
    
    async def analyze_knowledge_dynamics(
        self,
        time_window: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Analyze knowledge dynamics (how knowledge changes over time).
        
        Args:
            time_window: Time window in seconds (optional)
        
        Returns:
            Dictionary with knowledge dynamics analysis
        """
        # This would analyze how beliefs have changed over time
        # For now, return basic structure
        return {
            "analysis": "Knowledge dynamics analysis",
            "time_window": time_window,
            "changes_detected": 0,
            "trends": []
        }
    
    async def get_beliefs_by_certainty(
        self,
        certainty_level: CertaintyLevel
    ) -> List[str]:
        """
        Get all belief keys with a specific certainty level.
        
        Args:
            certainty_level: Certainty level to filter by
        
        Returns:
            List of belief keys
        """
        return self.knowledge_stats["beliefs_by_certainty"].get(certainty_level.value, [])
    
    async def get_beliefs_by_source(
        self,
        source: BeliefSource
    ) -> List[str]:
        """
        Get all belief keys from a specific source.
        
        Args:
            source: Belief source to filter by
        
        Returns:
            List of belief keys
        """
        return self.knowledge_stats["beliefs_by_source"].get(source.value, [])
    
    async def shutdown(self):
        """Shutdown the epistemic agent."""
        logger.info(f"{self.log_prefix} Shutting down")
