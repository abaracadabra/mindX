# mindx/learning/socratic_agent.py
"""
SocraticAgent: Socratic method for learning and problem-solving.

This agent uses the Socratic method to guide learning through questioning,
challenge assumptions, and deepen understanding using LogicEngine's Socratic features.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple

from utils.config import Config
from utils.logging_config import get_logger
from utils.logic_engine import LogicEngine
from agents.core.belief_system import BeliefSystem, BeliefSource
from llm.llm_interface import LLMHandlerInterface
from llm.llm_factory import create_llm_handler
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

logger = get_logger(__name__)


class SocraticAgent:
    """
    Agent specialized in Socratic method for learning and problem-solving.
    Generates Socratic questions to guide learning and challenge assumptions.
    """
    
    def __init__(
        self,
        agent_id: str = "socratic_agent",
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
        self.log_prefix = f"SocraticAgent ({self.agent_id}):"
        
        # Initialize LogicEngine for Socratic questioning
        self.logic_engine: Optional[LogicEngine] = None
        self._init_logic_engine()
        
        # Question history
        self.question_history: List[Dict[str, Any]] = []
    
    def _init_logic_engine(self):
        """Initialize the LogicEngine for Socratic questioning."""
        try:
            self.logic_engine = LogicEngine(
                belief_system=self.belief_system,
                llm_handler_for_socratic=self.llm_handler,
                agent_id_namespace=self.agent_id
            )
            logger.info(f"{self.log_prefix} LogicEngine initialized for Socratic questioning")
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
    
    async def generate_socratic_questions(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
        num_questions: int = 5
    ) -> List[str]:
        """
        Generate Socratic questions about a topic.
        
        Args:
            topic: Topic to generate questions about
            context: Optional context about the topic
            num_questions: Number of questions to generate
        
        Returns:
            List of Socratic questions
        """
        if not self.llm_handler:
            await self._async_init()
        
        if self.logic_engine:
            try:
                # Use LogicEngine's Socratic questioning if available
                # LogicEngine requires agent_belief_prefix_for_context
                belief_prefix = f"{self.agent_id}.{topic.replace(' ', '_').lower()}"
                questions = await self.logic_engine.generate_socratic_questions(
                    topic_or_goal=topic,
                    agent_belief_prefix_for_context=belief_prefix,
                    num_questions=num_questions
                )
                # LogicEngine returns a list of question strings
                if isinstance(questions, list):
                    return questions[:num_questions]
                else:
                    return []
            except Exception as e:
                logger.warning(f"{self.log_prefix} LogicEngine Socratic questioning failed: {e}, using LLM fallback")
        
        # Fallback to LLM-based question generation
        prompt = (
            f"Generate {num_questions} Socratic questions about this topic:\n\n"
            f"Topic: {topic}\n\n"
        )
        
        if context:
            prompt += f"Context:\n{json.dumps(context, indent=2)}\n\n"
        
        prompt += (
            f"Socratic questions should:\n"
            f"- Challenge assumptions\n"
            f"- Encourage deeper thinking\n"
            f"- Guide toward understanding\n"
            f"- Be open-ended\n\n"
            f"Provide questions as a JSON array of strings."
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            result = json.loads(response_str)
            
            questions = result if isinstance(result, list) else result.get("questions", [])
            
            # Store questions
            question_record = {
                "timestamp": time.time(),
                "topic": topic,
                "questions": questions,
                "context": context
            }
            self.question_history.append(question_record)
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "socratic_questions_generated",
                    question_record,
                    {"agent_id": self.agent_id}
                )
            
            return questions
        except Exception as e:
            logger.error(f"{self.log_prefix} Error generating Socratic questions: {e}", exc_info=True)
            return []
    
    async def guide_learning(
        self,
        learning_goal: str,
        current_understanding: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Guide learning through Socratic questioning.
        
        Args:
            learning_goal: Goal of the learning session
            current_understanding: Current understanding of the topic
        
        Returns:
            Dictionary with learning guidance
        """
        if not self.llm_handler:
            await self._async_init()
        
        # Generate questions to guide learning
        questions = await self.generate_socratic_questions(
            topic=learning_goal,
            context={"current_understanding": current_understanding} if current_understanding else None,
            num_questions=5
        )
        
        prompt = (
            f"Create a Socratic learning guide for this goal:\n\n"
            f"Learning Goal: {learning_goal}\n\n"
        )
        
        if current_understanding:
            prompt += f"Current Understanding: {current_understanding}\n\n"
        
        prompt += (
            f"Questions Generated:\n"
        )
        for i, q in enumerate(questions, 1):
            prompt += f"{i}. {q}\n"
        
        prompt += (
            f"\nProvide learning guide in JSON format with:\n"
            f"- learning_path: Sequence of questions to explore\n"
            f"- key_concepts: Concepts to understand\n"
            f"- assumptions_to_challenge: Assumptions to question\n"
            f"- expected_outcomes: What should be learned\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            guide = json.loads(response_str)
            
            guide_record = {
                "timestamp": time.time(),
                "learning_goal": learning_goal,
                "guide": guide,
                "questions": questions
            }
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "socratic_learning_guide",
                    guide_record,
                    {"agent_id": self.agent_id}
                )
            
            return guide
        except Exception as e:
            logger.error(f"{self.log_prefix} Error creating learning guide: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def challenge_assumptions(
        self,
        statement: str,
        assumptions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Challenge assumptions in a statement using Socratic questioning.
        
        Args:
            statement: Statement to challenge
            assumptions: Optional list of known assumptions
        
        Returns:
            Dictionary with assumption challenges
        """
        if not self.llm_handler:
            await self._async_init()
        
        prompt = (
            f"Challenge assumptions in this statement using Socratic questioning:\n\n"
            f"Statement: {statement}\n\n"
        )
        
        if assumptions:
            prompt += f"Known Assumptions:\n"
            for i, assump in enumerate(assumptions, 1):
                prompt += f"{i}. {assump}\n"
            prompt += "\n"
        
        prompt += (
            f"Provide challenges in JSON format with:\n"
            f"- identified_assumptions: List of assumptions found\n"
            f"- challenging_questions: Questions that challenge each assumption\n"
            f"- alternative_perspectives: Alternative ways to view the statement\n"
            f"- reasoning: Explanation of why assumptions should be challenged\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            challenges = json.loads(response_str)
            
            challenge_record = {
                "timestamp": time.time(),
                "statement": statement,
                "challenges": challenges
            }
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "socratic_assumption_challenge",
                    challenge_record,
                    {"agent_id": self.agent_id}
                )
            
            return challenges
        except Exception as e:
            logger.error(f"{self.log_prefix} Error challenging assumptions: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def deepen_understanding(
        self,
        topic: str,
        current_knowledge: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Deepen understanding of a topic through Socratic questioning.
        
        Args:
            topic: Topic to deepen understanding of
            current_knowledge: Current knowledge about the topic
        
        Returns:
            Dictionary with deepened understanding
        """
        if not self.llm_handler:
            await self._async_init()
        
        # Generate questions to deepen understanding
        questions = await self.generate_socratic_questions(
            topic=topic,
            context=current_knowledge,
            num_questions=7
        )
        
        prompt = (
            f"Deepen understanding of this topic through Socratic questioning:\n\n"
            f"Topic: {topic}\n\n"
        )
        
        if current_knowledge:
            prompt += f"Current Knowledge:\n{json.dumps(current_knowledge, indent=2)}\n\n"
        
        prompt += (
            f"Questions to Explore:\n"
        )
        for i, q in enumerate(questions, 1):
            prompt += f"{i}. {q}\n"
        
        prompt += (
            f"\nProvide deepened understanding in JSON format with:\n"
            f"- deeper_insights: New insights gained\n"
            f"- connections: Connections to other knowledge\n"
            f"- implications: Implications of the deeper understanding\n"
            f"- questions_for_further_exploration: Additional questions to explore\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            understanding = json.loads(response_str)
            
            understanding_record = {
                "timestamp": time.time(),
                "topic": topic,
                "understanding": understanding,
                "questions_used": questions
            }
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "socratic_deepened_understanding",
                    understanding_record,
                    {"agent_id": self.agent_id}
                )
            
            return understanding
        except Exception as e:
            logger.error(f"{self.log_prefix} Error deepening understanding: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def shutdown(self):
        """Shutdown the Socratic agent."""
        logger.info(f"{self.log_prefix} Shutting down")
