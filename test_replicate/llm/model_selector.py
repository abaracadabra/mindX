# mindx/llm/model_selector.py
"""
ModelSelector for the MindX Augmentic Intelligence system.

This module provides a sophisticated, weighted scoring system to select the most
appropriate LLM for a given task, balancing capability, performance, cost, and
other strategic requirements. It is a key component for achieving both
Resilience (by selecting fallback models) and Perpetuity (by optimizing for cost).
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set
from enum import Enum

from utils.config import Config
from utils.logging_config import get_logger

logger = get_logger(__name__)

# This enum should ideally be in a central types file, but is placed here for self-containment.
class TaskType(Enum):
    """Defines high-level categories of tasks for model selection."""
    REASONING = "reasoning"
    CODE_GENERATION = "code_generation"
    SIMPLE_CHAT = "simple_chat"
    DATA_ANALYSIS = "data_analysis"
    WRITING = "writing"
    SPEED_SENSITIVE = "speed_sensitive"

class ModelCapability:
    """A data structure representing the known capabilities and metrics of a single LLM."""
    def __init__(self, model_id: str, provider: str, data: Dict[str, Any]):
        self.model_id = model_id
        self.provider = provider
        # Static capabilities from config
        self.task_scores: Dict[str, float] = data.get("task_scores", {})
        self.max_context_length: int = data.get("max_context_length", 8192)
        self.supports_streaming: bool = data.get("supports_streaming", False)
        self.supports_function_calling: bool = data.get("supports_function_calling", False)
        self.cost_per_kilo_input: float = data.get("cost_per_kilo_input_tokens", 0.0)
        self.cost_per_kilo_output: float = data.get("cost_per_kilo_output_tokens", 0.0)
        # Dynamic runtime stats (could be updated from a PerformanceMonitor)
        self.success_rate: float = data.get("success_rate", 1.0)
        self.average_latency_ms: int = data.get("average_latency_ms", 500)
        self.availability: float = data.get("availability", 1.0)

    def get_capability_score(self, task_type: TaskType) -> float:
        """Returns the model's score for a specific task type."""
        return self.task_scores.get(task_type, 0.1) # Default low score if not specified

class ModelSelector:
    """
    Handles the intelligent selection of appropriate LLMs for different task types.
    """
    DEFAULT_SELECTION_WEIGHTS: Dict[str, float] = {
        "capability_match": 3.0,
        "success_rate": 2.0,
        "latency_factor": 0.5,
        "cost_factor": 1.5,
        "provider_preference": 0.2,
    }

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.selection_weights = self.config.get("llm.model_selector.weights", self.DEFAULT_SELECTION_WEIGHTS.copy())
        self.provider_preferences = self.config.get("llm.model_selector.provider_preferences", {"gemini": 1.0, "groq": 0.9, "together_ai": 0.85, "ollama": 0.7})
        logger.info(f"ModelSelector initialized with weights: {self.selection_weights}")

    def select_model(self, model_capabilities: List[ModelCapability], task_type: TaskType, context: Optional[Dict] = None, num_to_return: int = 5) -> List[str]:
        """
        Selects and ranks the most appropriate models for a given task.
        Returns a list of model_ids, sorted from best to worst.
        """
        from utils.config import PROJECT_ROOT
        gemini_data_dir = PROJECT_ROOT / "data" / "gemini"
        audit_files = sorted(gemini_data_dir.glob("*.gemini_audit_report.json"), reverse=True)
        if not audit_files:
            logger.warning(f"No Gemini audit reports found. Using default model scoring.")
            scored_models = self._score_models(model_capabilities, task_type, context or {})
        else:
            latest_audit_file = audit_files[0]
            with open(latest_audit_file, "r") as f:
                audit_data = json.load(f)
            
            scored_models = self._score_models(model_capabilities, task_type, context or {}, audit_data["full_audit_results"])

        if not scored_models:
            logger.warning(f"No suitable model found for task type: {task_type.name}")
            return []
        
        # Return the sorted list of model IDs, limited by num_to_return
        return [model_id for model_id, score in scored_models[:num_to_return]]

    def _score_models(self, capabilities: List[ModelCapability], task_type: TaskType, context: Dict, audit_data: Optional[List[Dict[str, Any]]] = None) -> List[Tuple[str, float]]:
        """Scores all provided models and returns a sorted list."""
        scores = {}
        for cap in capabilities:
            # Exclude models based on context if necessary
            if cap.model_id in context.get("excluded_models", set()):
                continue

            score = 0.0
            #  Capability Match Score
            score += cap.get_capability_score(task_type) * self.selection_weights.get("capability_match", 1.0)
            
            #  Success Rate
            score += cap.success_rate * self.selection_weights.get("success_rate", 1.0)

            #  Latency Factor (lower is better)
            latency_sec = cap.average_latency_ms / 1000.0
            latency_factor = 1.0 / (0.1 + latency_sec) # Add 0.1 to prevent division by zero and extreme scores
            score += latency_factor * self.selection_weights.get("latency_factor", 1.0)
            
            #  Cost Factor (lower is better)
            avg_cost = (cap.cost_per_kilo_input + cap.cost_per_kilo_output) / 2
            cost_factor = 1.0 / (0.01 + avg_cost) if avg_cost > 0.000001 else 2.0 # High score for free/negligible cost models
            score += cost_factor * self.selection_weights.get("cost_factor", 1.0)
            
            #  Provider Preference
            score += self.provider_preferences.get(cap.provider, 0.5) * self.selection_weights.get("provider_preference", 1.0)
            
            # Add audit data to the score
            if audit_data:
                for model_audit in audit_data:
                    if model_audit["api_name"] == cap.model_id.split("/")[-1]:
                        for capability, result in model_audit["assessed_capabilities"].items():
                            if result["status"] == "OPERATIONAL":
                                score += 1.0
                            elif result["status"] == "ERROR":
                                score -= 1.0
            
            scores[cap.model_id] = score
        
        return sorted(scores.items(), key=lambda item: item[1], reverse=True)
