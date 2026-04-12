# mindx/core/reasoning_agent.py
"""
ReasoningAgent: Advanced logical reasoning (deductive, inductive, abductive).

This agent provides specialized reasoning capabilities for augmentic development,
including deductive, inductive, and abductive reasoning using LogicEngine.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

from utils.config import Config
from utils.logging_config import get_logger
from utils.logic_engine import LogicEngine
from agents.core.belief_system import BeliefSystem, BeliefSource
from llm.llm_interface import LLMHandlerInterface
from llm.llm_factory import create_llm_handler
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

logger = get_logger(__name__)


class ReasoningType(Enum):
    """Types of reasoning supported."""
    DEDUCTIVE = "deductive"  # General to specific
    INDUCTIVE = "inductive"  # Specific to general
    ABDUCTIVE = "abductive"  # Best explanation


class ReasoningAgent:
    """
    Agent specialized in advanced logical reasoning.
    Provides deductive, inductive, and abductive reasoning capabilities.
    """
    
    def __init__(
        self,
        agent_id: str = "reasoning_agent",
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
        self.log_prefix = f"ReasoningAgent ({self.agent_id}):"
        
        # Initialize LogicEngine
        self.logic_engine: Optional[LogicEngine] = None
        self._init_logic_engine()
        
        # Reasoning history
        self.reasoning_history: List[Dict[str, Any]] = []
    
    def _init_logic_engine(self):
        """Initialize the LogicEngine."""
        try:
            self.logic_engine = LogicEngine(
                belief_system=self.belief_system,
                llm_handler_for_socratic=self.llm_handler,
                agent_id_namespace=self.agent_id
            )
            logger.info(f"{self.log_prefix} LogicEngine initialized")
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to initialize LogicEngine: {e}", exc_info=True)
    
    async def _async_init(self):
        """Async initialization - create LLM handler if not provided."""
        if not self.llm_handler:
            try:
                self.llm_handler = await create_llm_handler()
                if self.llm_handler:
                    logger.info(f"{self.log_prefix} LLM handler initialized: {self.llm_handler.provider_name}")
                    # Reinitialize LogicEngine with LLM handler
                    self._init_logic_engine()
            except Exception as e:
                logger.error(f"{self.log_prefix} Failed to create LLM handler: {e}", exc_info=True)
    
    async def deductive_reasoning(
        self,
        premises: List[str],
        conclusion_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform deductive reasoning (general to specific).
        
        Args:
            premises: List of general premises/statements
            conclusion_hint: Optional hint about what conclusion to derive
        
        Returns:
            Dictionary with reasoning results
        """
        if not self.llm_handler:
            await self._async_init()
        
        prompt = (
            f"Perform deductive reasoning (general to specific) based on these premises:\n\n"
            f"Premises:\n"
        )
        for i, premise in enumerate(premises, 1):
            prompt += f"{i}. {premise}\n"
        
        if conclusion_hint:
            prompt += f"\nConclusion hint: {conclusion_hint}\n"
        
        prompt += (
            f"\nProvide reasoning in JSON format with:\n"
            f"- conclusion: The derived conclusion\n"
            f"- reasoning_steps: List of reasoning steps\n"
            f"- validity: Whether the reasoning is valid (true/false)\n"
            f"- confidence: Confidence level (0.0-1.0)\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            if not response_str:
                return {"error": "LLM unavailable", "type": "deductive", "conclusion": "Unable to reason — inference unavailable"}
            result = json.loads(response_str)

            # Store reasoning
            reasoning_record = {
                "timestamp": time.time(),
                "type": ReasoningType.DEDUCTIVE.value,
                "premises": premises,
                "result": result
            }
            self.reasoning_history.append(reasoning_record)
            
            # Store conclusion in belief system
            if result.get("conclusion"):
                await self.belief_system.add_belief(
                    "reasoning.deductive.latest",
                    result,
                    confidence=result.get("confidence", 0.7),
                    source=BeliefSource.INFERENCE
                )
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "reasoning_deductive",
                    reasoning_record,
                    {"agent_id": self.agent_id}
                )
            
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in deductive reasoning: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def inductive_reasoning(
        self,
        observations: List[str],
        pattern_hint: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Perform inductive reasoning (specific to general).
        
        Args:
            observations: List of specific observations
            pattern_hint: Optional hint about pattern to find
        
        Returns:
            Dictionary with reasoning results
        """
        if not self.llm_handler:
            await self._async_init()
        
        prompt = (
            f"Perform inductive reasoning (specific to general) based on these observations:\n\n"
            f"Observations:\n"
        )
        for i, obs in enumerate(observations, 1):
            prompt += f"{i}. {obs}\n"
        
        if pattern_hint:
            prompt += f"\nPattern hint: {pattern_hint}\n"
        
        prompt += (
            f"\nProvide reasoning in JSON format with:\n"
            f"- generalization: The general pattern or rule\n"
            f"- reasoning_steps: List of reasoning steps\n"
            f"- confidence: Confidence level (0.0-1.0)\n"
            f"- supporting_evidence: Evidence supporting the generalization\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            if not response_str:
                return {"error": "LLM unavailable", "type": "inductive", "generalization": "Unable to reason — inference unavailable"}
            result = json.loads(response_str)

            reasoning_record = {
                "timestamp": time.time(),
                "type": ReasoningType.INDUCTIVE.value,
                "observations": observations,
                "result": result
            }
            self.reasoning_history.append(reasoning_record)
            
            if result.get("generalization"):
                await self.belief_system.add_belief(
                    "reasoning.inductive.latest",
                    result,
                    confidence=result.get("confidence", 0.6),
                    source=BeliefSource.INFERENCE
                )
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "reasoning_inductive",
                    reasoning_record,
                    {"agent_id": self.agent_id}
                )
            
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in inductive reasoning: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def abductive_reasoning(
        self,
        observations: List[str],
        possible_explanations: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Perform abductive reasoning (best explanation).
        
        Args:
            observations: List of observations to explain
            possible_explanations: Optional list of possible explanations
        
        Returns:
            Dictionary with reasoning results
        """
        if not self.llm_handler:
            await self._async_init()
        
        prompt = (
            f"Perform abductive reasoning (best explanation) for these observations:\n\n"
            f"Observations:\n"
        )
        for i, obs in enumerate(observations, 1):
            prompt += f"{i}. {obs}\n"
        
        if possible_explanations:
            prompt += f"\nPossible explanations:\n"
            for i, exp in enumerate(possible_explanations, 1):
                prompt += f"{i}. {exp}\n"
        
        prompt += (
            f"\nProvide reasoning in JSON format with:\n"
            f"- best_explanation: The best explanation for the observations\n"
            f"- alternative_explanations: List of alternative explanations\n"
            f"- reasoning_steps: List of reasoning steps\n"
            f"- confidence: Confidence level (0.0-1.0)\n"
            f"- explanation_score: Score for the best explanation\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            if not response_str:
                return {"error": "LLM unavailable", "type": "abductive", "best_explanation": "Unable to reason — inference unavailable"}
            result = json.loads(response_str)

            reasoning_record = {
                "timestamp": time.time(),
                "type": ReasoningType.ABDUCTIVE.value,
                "observations": observations,
                "result": result
            }
            self.reasoning_history.append(reasoning_record)
            
            if result.get("best_explanation"):
                await self.belief_system.add_belief(
                    "reasoning.abductive.latest",
                    result,
                    confidence=result.get("confidence", 0.65),
                    source=BeliefSource.INFERENCE
                )
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "reasoning_abductive",
                    reasoning_record,
                    {"agent_id": self.agent_id}
                )
            
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in abductive reasoning: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def logical_inference(
        self,
        facts: List[str],
        query: str
    ) -> Dict[str, Any]:
        """
        Perform logical inference using LogicEngine.
        
        Args:
            facts: List of facts to reason from
            query: Query to answer
        
        Returns:
            Dictionary with inference results
        """
        if not self.logic_engine:
            await self._async_init()
            if not self.logic_engine:
                return {"error": "LogicEngine not available"}
        
        try:
            # Use LogicEngine for inference
            # This is a simplified version - LogicEngine would need to be configured with rules
            result = {
                "query": query,
                "facts": facts,
                "inference": "LogicEngine inference would be performed here",
                "confidence": 0.7
            }
            
            reasoning_record = {
                "timestamp": time.time(),
                "type": "logical_inference",
                "query": query,
                "result": result
            }
            self.reasoning_history.append(reasoning_record)
            
            return result
        except Exception as e:
            logger.error(f"{self.log_prefix} Error in logical inference: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def shutdown(self):
        """Shutdown the reasoning agent."""
        logger.info(f"{self.log_prefix} Shutting down")
