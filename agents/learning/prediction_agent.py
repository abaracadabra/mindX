# mindx/learning/prediction_agent.py
"""
PredictionAgent: Forecasting future states, outcomes, and system behavior.

This agent provides prediction capabilities for augmentic development,
forecasting system performance, agent behavior, task outcomes, and resource needs.
"""

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.core.belief_system import BeliefSystem, BeliefSource
from llm.llm_interface import LLMHandlerInterface
from llm.llm_factory import create_llm_handler
from agents.memory_agent import MemoryAgent
from agents.orchestration.coordinator_agent import CoordinatorAgent

logger = get_logger(__name__)


class PredictionAgent:
    """
    Agent specialized in forecasting future states, outcomes, and system behavior.
    Provides predictions for system performance, agent behavior, task outcomes, and resource needs.
    """
    
    def __init__(
        self,
        agent_id: str = "prediction_agent",
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
        self.log_prefix = f"PredictionAgent ({self.agent_id}):"
        
        # Prediction history for learning
        self.prediction_history: List[Dict[str, Any]] = []
        self.prediction_accuracy: Dict[str, float] = {}
        
        # Subscribe to coordinator events if available
        if self.coordinator_agent:
            self._subscribe_to_events()
    
    def _subscribe_to_events(self):
        """Subscribe to coordinator events for prediction triggers."""
        if not self.coordinator_agent:
            return
        
        try:
            # Subscribe to system events that might need predictions
            self.coordinator_agent.subscribe("agent.created", self._on_agent_created)
            self.coordinator_agent.subscribe("agent.deregistered", self._on_agent_deregistered)
            self.coordinator_agent.subscribe("system.performance.update", self._on_performance_update)
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
    
    async def predict_system_performance(
        self,
        time_horizon: str = "1h",
        metrics: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Predict system performance over a time horizon.
        
        Args:
            time_horizon: Time horizon for prediction (e.g., "1h", "24h", "7d")
            metrics: List of metrics to predict (e.g., ["cpu", "memory", "latency"])
        
        Returns:
            Dictionary with predictions for each metric
        """
        if not self.llm_handler:
            await self._async_init()
        
        metrics = metrics or ["cpu", "memory", "latency", "throughput"]
        
        # Gather current system state
        current_state = await self._gather_system_state()
        
        # Build prediction prompt
        prompt = (
            f"Based on the current system state, predict performance metrics over the next {time_horizon}.\n\n"
            f"Current State:\n{json.dumps(current_state, indent=2)}\n\n"
            f"Metrics to predict: {', '.join(metrics)}\n\n"
            f"Provide predictions in JSON format with keys for each metric, including:\n"
            f"- predicted_value: Expected value\n"
            f"- confidence: Confidence level (0.0-1.0)\n"
            f"- trend: 'increasing', 'decreasing', or 'stable'\n"
            f"- risk_factors: List of potential risk factors\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            predictions = json.loads(response_str)
            
            # Store prediction
            prediction_record = {
                "timestamp": time.time(),
                "time_horizon": time_horizon,
                "metrics": metrics,
                "predictions": predictions,
                "current_state": current_state
            }
            self.prediction_history.append(prediction_record)
            
            # Store in belief system
            await self.belief_system.add_belief(
                f"prediction.system_performance.{time_horizon}",
                predictions,
                confidence=0.8,
                source=BeliefSource.INFERENCE
            )
            
            if self.memory_agent:
                await self.memory_agent.log_process(
                    "prediction_system_performance",
                    prediction_record,
                    {"agent_id": self.agent_id}
                )
            
            return predictions
        except Exception as e:
            logger.error(f"{self.log_prefix} Error predicting system performance: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def predict_agent_behavior(
        self,
        agent_id: str,
        task_description: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict how an agent will behave for a given task.
        
        Args:
            agent_id: ID of the agent to predict behavior for
            task_description: Description of the task
            context: Additional context about the task
        
        Returns:
            Dictionary with behavior predictions
        """
        if not self.llm_handler:
            await self._async_init()
        
        context = context or {}
        
        # Gather agent information
        agent_info = await self._gather_agent_info(agent_id)
        
        prompt = (
            f"Predict how agent '{agent_id}' will behave when performing this task:\n"
            f"Task: {task_description}\n\n"
            f"Agent Information:\n{json.dumps(agent_info, indent=2)}\n\n"
            f"Context:\n{json.dumps(context, indent=2)}\n\n"
            f"Provide predictions in JSON format with:\n"
            f"- expected_actions: List of expected actions\n"
            f"- success_probability: Probability of success (0.0-1.0)\n"
            f"- estimated_duration: Estimated time to complete\n"
            f"- resource_requirements: Expected resource usage\n"
            f"- potential_issues: List of potential problems\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            predictions = json.loads(response_str)
            
            # Store prediction
            prediction_record = {
                "timestamp": time.time(),
                "agent_id": agent_id,
                "task_description": task_description,
                "predictions": predictions
            }
            self.prediction_history.append(prediction_record)
            
            await self.belief_system.add_belief(
                f"prediction.agent_behavior.{agent_id}",
                predictions,
                confidence=0.75,
                source=BeliefSource.INFERENCE
            )
            
            return predictions
        except Exception as e:
            logger.error(f"{self.log_prefix} Error predicting agent behavior: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def predict_task_outcome(
        self,
        task_description: str,
        plan: Optional[List[Dict[str, Any]]] = None,
        resources: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict the outcome of a task.
        
        Args:
            task_description: Description of the task
            plan: Optional plan for the task
            resources: Available resources
        
        Returns:
            Dictionary with outcome predictions
        """
        if not self.llm_handler:
            await self._async_init()
        
        plan = plan or []
        resources = resources or {}
        
        prompt = (
            f"Predict the outcome of this task:\n"
            f"Task: {task_description}\n\n"
            f"Plan: {json.dumps(plan, indent=2) if plan else 'No plan provided'}\n\n"
            f"Resources: {json.dumps(resources, indent=2) if resources else 'No resource info'}\n\n"
            f"Provide predictions in JSON format with:\n"
            f"- success_probability: Probability of success (0.0-1.0)\n"
            f"- expected_outcome: Description of expected outcome\n"
            f"- completion_time: Estimated completion time\n"
            f"- risk_level: Risk level ('low', 'medium', 'high')\n"
            f"- failure_modes: List of potential failure modes\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            predictions = json.loads(response_str)
            
            prediction_record = {
                "timestamp": time.time(),
                "task_description": task_description,
                "predictions": predictions
            }
            self.prediction_history.append(prediction_record)
            
            await self.belief_system.add_belief(
                "prediction.task_outcome.latest",
                predictions,
                confidence=0.7,
                source=BeliefSource.INFERENCE
            )
            
            return predictions
        except Exception as e:
            logger.error(f"{self.log_prefix} Error predicting task outcome: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def predict_resource_needs(
        self,
        task_description: str,
        estimated_duration: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predict resource needs for a task.
        
        Args:
            task_description: Description of the task
            estimated_duration: Estimated duration (optional)
        
        Returns:
            Dictionary with resource predictions
        """
        if not self.llm_handler:
            await self._async_init()
        
        current_resources = await self._gather_resource_state()
        
        prompt = (
            f"Predict resource needs for this task:\n"
            f"Task: {task_description}\n"
            f"Estimated Duration: {estimated_duration or 'Unknown'}\n\n"
            f"Current Resources:\n{json.dumps(current_resources, indent=2)}\n\n"
            f"Provide predictions in JSON format with:\n"
            f"- cpu_requirement: Expected CPU usage\n"
            f"- memory_requirement: Expected memory usage\n"
            f"- network_requirement: Expected network usage\n"
            f"- storage_requirement: Expected storage usage\n"
            f"- llm_tokens: Estimated LLM token usage\n"
        )
        
        try:
            response_str = await self.llm_handler.generate_text(prompt, json_mode=True)
            predictions = json.loads(response_str)
            
            prediction_record = {
                "timestamp": time.time(),
                "task_description": task_description,
                "predictions": predictions
            }
            self.prediction_history.append(prediction_record)
            
            return predictions
        except Exception as e:
            logger.error(f"{self.log_prefix} Error predicting resource needs: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _gather_system_state(self) -> Dict[str, Any]:
        """Gather current system state for predictions."""
        state = {
            "timestamp": time.time(),
            "agents_count": 0,
            "active_tasks": 0
        }
        
        if self.coordinator_agent:
            try:
                registry = getattr(self.coordinator_agent, 'agent_registry', {})
                state["agents_count"] = len(registry)
            except Exception:
                pass
        
        return state
    
    async def _gather_agent_info(self, agent_id: str) -> Dict[str, Any]:
        """Gather information about an agent."""
        info = {
            "agent_id": agent_id,
            "exists": False
        }
        
        if self.coordinator_agent:
            try:
                registry = getattr(self.coordinator_agent, 'agent_registry', {})
                if agent_id in registry:
                    agent_data = registry[agent_id]
                    info.update({
                        "exists": True,
                        "agent_type": agent_data.get("agent_type"),
                        "status": agent_data.get("status"),
                        "registered_at": agent_data.get("registered_at")
                    })
            except Exception:
                pass
        
        return info
    
    async def _gather_resource_state(self) -> Dict[str, Any]:
        """Gather current resource state."""
        # This would integrate with monitoring systems
        return {
            "cpu_usage": "unknown",
            "memory_usage": "unknown",
            "network_usage": "unknown"
        }
    
    async def _on_agent_created(self, data: Dict[str, Any]):
        """Handle agent creation event - predict behavior."""
        agent_id = data.get("agent_id")
        if agent_id:
            logger.info(f"{self.log_prefix} Agent created: {agent_id}, predicting behavior")
            # Could trigger behavior prediction here
    
    async def _on_agent_deregistered(self, data: Dict[str, Any]):
        """Handle agent deregistration event."""
        agent_id = data.get("agent_id")
        if agent_id:
            logger.info(f"{self.log_prefix} Agent deregistered: {agent_id}")
    
    async def _on_performance_update(self, data: Dict[str, Any]):
        """Handle performance update event - update predictions."""
        logger.debug(f"{self.log_prefix} Performance update received")
    
    async def shutdown(self):
        """Shutdown the prediction agent."""
        logger.info(f"{self.log_prefix} Shutting down")
        # Save prediction history if needed
