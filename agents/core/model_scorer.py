"""
Hierarchical Model Scoring System for Ollama Model Selection

This system provides adaptive model scoring based on:
- Task type matching
- Performance metrics (latency, throughput, error rate)
- Resource usage (memory, compute)
- Response quality (code quality, reasoning quality)
- Historical feedback from mindXagent
"""

import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
import json

from utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ModelScore:
    """Score for a model based on various factors"""
    model_name: str
    task_type: str
    base_score: float = 0.0
    capability_match: float = 0.0  # How well model matches task requirements
    performance_score: float = 0.0  # Based on latency, throughput
    quality_score: float = 0.0  # Based on response quality, code quality
    resource_efficiency: float = 0.0  # Based on memory/compute usage
    historical_success: float = 0.0  # Based on past performance
    total_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for a model"""
    model_name: str
    task_type: str
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    avg_tokens_per_second: float = 0.0
    avg_response_quality: float = 0.0  # 0-1 scale, from feedback
    avg_code_quality: float = 0.0  # 0-1 scale, from code analysis
    memory_usage_mb: float = 0.0
    last_used: float = 0.0
    success_rate: float = 0.0


class HierarchicalModelScorer:
    """
    Hierarchical model scoring system that adapts based on feedback.
    
    Scoring hierarchy:
    1. Capability Match (task type alignment)
    2. Performance Metrics (latency, throughput, error rate)
    3. Quality Metrics (response quality, code quality)
    4. Resource Efficiency (memory, compute)
    5. Historical Success (past performance on similar tasks)
    """
    
    def __init__(
        self,
        metrics_file: Optional[Path] = None,
        weight_capability: float = 3.0,
        weight_performance: float = 2.0,
        weight_quality: float = 2.5,
        weight_resources: float = 1.0,
        weight_history: float = 1.5
    ):
        self.metrics_file = metrics_file or Path("data/model_performance_metrics.json")
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Scoring weights (hierarchical importance)
        self.weight_capability = weight_capability
        self.weight_performance = weight_performance
        self.weight_quality = weight_quality
        self.weight_resources = weight_resources
        self.weight_history = weight_history
        
        # Model performance data
        self.model_metrics: Dict[str, Dict[str, ModelPerformanceMetrics]] = {}
        self._load_metrics()
        
        # Task type to model capability mapping
        self.task_capabilities = {
            "chat": {
                "keywords": ["mistral", "llama", "chat", "conversational"],
                "preferred_sizes": ["7b", "8b", "13b"],
                "avoid_sizes": ["30b", "70b", "120b"]
            },
            "reasoning": {
                "keywords": ["nemo", "reasoning", "thinking", "deepseek", "qwen"],
                "preferred_sizes": ["7b", "8b", "14b", "27b"],
                "avoid_sizes": ["120b"]
            },
            "coding": {
                "keywords": ["code", "codellama", "deepseek-coder", "qwen2.5-coder"],
                "preferred_sizes": ["7b", "8b", "14b"],
                "avoid_sizes": ["30b", "70b"]
            },
            "multimodal": {
                "keywords": ["llava", "bakllava", "vision"],
                "preferred_sizes": ["7b", "13b"],
                "avoid_sizes": []
            }
        }
        
        logger.info("HierarchicalModelScorer initialized")
    
    def _load_metrics(self):
        """Load model performance metrics from disk"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    for model_name, task_data in data.items():
                        self.model_metrics[model_name] = {}
                        for task_type, metrics_data in task_data.items():
                            self.model_metrics[model_name][task_type] = ModelPerformanceMetrics(
                                **metrics_data
                            )
                logger.info(f"Loaded metrics for {len(self.model_metrics)} models")
        except Exception as e:
            logger.warning(f"Failed to load model metrics: {e}")
            self.model_metrics = {}
    
    def _save_metrics(self):
        """Save model performance metrics to disk"""
        try:
            data = {}
            for model_name, task_data in self.model_metrics.items():
                data[model_name] = {}
                for task_type, metrics in task_data.items():
                    data[model_name][task_type] = {
                        "model_name": metrics.model_name,
                        "task_type": metrics.task_type,
                        "total_requests": metrics.total_requests,
                        "successful_requests": metrics.successful_requests,
                        "failed_requests": metrics.failed_requests,
                        "avg_latency_ms": metrics.avg_latency_ms,
                        "avg_tokens_per_second": metrics.avg_tokens_per_second,
                        "avg_response_quality": metrics.avg_response_quality,
                        "avg_code_quality": metrics.avg_code_quality,
                        "memory_usage_mb": metrics.memory_usage_mb,
                        "last_used": metrics.last_used,
                        "success_rate": metrics.success_rate
                    }
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save model metrics: {e}")
    
    def score_model(
        self,
        model: Dict[str, Any],
        task_type: str,
        preferred_models: Optional[List[str]] = None
    ) -> ModelScore:
        """
        Score a model for a given task type using hierarchical scoring.
        
        Args:
            model: Model dictionary with name, size, etc.
            task_type: Type of task (chat, reasoning, coding, etc.)
            preferred_models: List of preferred model names
            
        Returns:
            ModelScore with all scoring components
        """
        model_name = model.get("name", "unknown")
        model_name_lower = model_name.lower()
        
        # Initialize score
        score = ModelScore(model_name=model_name, task_type=task_type)
        
        # 1. Capability Match Score (highest weight)
        capability_score = self._calculate_capability_match(model_name_lower, task_type)
        score.capability_match = capability_score
        
        # 2. Performance Score
        perf_score = self._calculate_performance_score(model_name, task_type)
        score.performance_score = perf_score
        
        # 3. Quality Score
        quality_score = self._calculate_quality_score(model_name, task_type)
        score.quality_score = quality_score
        
        # 4. Resource Efficiency Score
        resource_score = self._calculate_resource_efficiency(model, model_name, task_type)
        score.resource_efficiency = resource_score
        
        # 5. Historical Success Score
        history_score = self._calculate_historical_success(model_name, task_type)
        score.historical_success = history_score
        
        # Bonus for preferred models
        if preferred_models and model_name in preferred_models:
            preference_bonus = 0.2 * (len(preferred_models) - preferred_models.index(model_name)) / len(preferred_models)
            score.base_score += preference_bonus
        
        # Calculate total weighted score
        score.total_score = (
            score.capability_match * self.weight_capability +
            score.performance_score * self.weight_performance +
            score.quality_score * self.weight_quality +
            score.resource_efficiency * self.weight_resources +
            score.historical_success * self.weight_history +
            score.base_score
        )
        
        score.metadata = {
            "model_size": model.get("size", 0),
            "model_details": model.get("details", {}),
            "scoring_weights": {
                "capability": self.weight_capability,
                "performance": self.weight_performance,
                "quality": self.weight_quality,
                "resources": self.weight_resources,
                "history": self.weight_history
            }
        }
        
        return score
    
    def _calculate_capability_match(self, model_name_lower: str, task_type: str) -> float:
        """Calculate how well model matches task requirements"""
        if task_type not in self.task_capabilities:
            return 0.5  # Neutral score for unknown task types
        
        task_info = self.task_capabilities[task_type]
        score = 0.0
        
        # Check keyword matches
        keyword_matches = sum(1 for keyword in task_info["keywords"] if keyword in model_name_lower)
        if keyword_matches > 0:
            score += 0.6 * (keyword_matches / len(task_info["keywords"]))
        
        # Check size preferences
        size_match = False
        for preferred_size in task_info["preferred_sizes"]:
            if preferred_size in model_name_lower:
                size_match = True
                score += 0.3
                break
        
        # Penalize avoided sizes
        for avoid_size in task_info["avoid_sizes"]:
            if avoid_size in model_name_lower:
                score -= 0.2
                break
        
        # Base score if no specific match
        if score == 0.0:
            score = 0.3
        
        return min(1.0, max(0.0, score))
    
    def _calculate_performance_score(self, model_name: str, task_type: str) -> float:
        """Calculate performance score based on metrics"""
        metrics = self._get_metrics(model_name, task_type)
        if not metrics or metrics.total_requests == 0:
            return 0.5  # Neutral score for unknown models
        
        score = 0.0
        
        # Success rate (0-0.4 weight)
        score += 0.4 * metrics.success_rate
        
        # Latency score (lower is better, 0-0.3 weight)
        # Assume good latency is < 2000ms, poor is > 10000ms
        latency_score = max(0.0, 1.0 - (metrics.avg_latency_ms - 2000) / 8000)
        score += 0.3 * latency_score
        
        # Throughput score (higher is better, 0-0.3 weight)
        # Assume good throughput is > 50 tokens/s
        throughput_score = min(1.0, metrics.avg_tokens_per_second / 50.0)
        score += 0.3 * throughput_score
        
        return min(1.0, max(0.0, score))
    
    def _calculate_quality_score(self, model_name: str, task_type: str) -> float:
        """Calculate quality score based on response and code quality"""
        metrics = self._get_metrics(model_name, task_type)
        if not metrics or metrics.total_requests == 0:
            return 0.5  # Neutral score
        
        # Average of response quality and code quality
        quality = (metrics.avg_response_quality + metrics.avg_code_quality) / 2.0
        return quality
    
    def _calculate_resource_efficiency(self, model: Dict[str, Any], model_name: str, task_type: str) -> float:
        """Calculate resource efficiency score"""
        metrics = self._get_metrics(model_name, task_type)
        model_size = model.get("size", 0)
        
        # Smaller models are more efficient (if performance is acceptable)
        if model_size == 0:
            return 0.5
        
        # Normalize size (assume 1GB = 0.1, 10GB = 0.5, 50GB = 1.0)
        size_score = min(1.0, model_size / (50 * 1024 * 1024 * 1024))
        
        # If model has good performance despite size, boost efficiency
        if metrics and metrics.success_rate > 0.8:
            size_score *= 0.7  # Less penalty for large models if they perform well
        
        return 1.0 - size_score  # Invert: smaller is better
    
    def _calculate_historical_success(self, model_name: str, task_type: str) -> float:
        """Calculate historical success score"""
        metrics = self._get_metrics(model_name, task_type)
        if not metrics or metrics.total_requests == 0:
            return 0.5  # Neutral score
        
        # Combine success rate with recency (recent success is more valuable)
        recency_factor = 1.0
        if metrics.last_used > 0:
            hours_since_use = (time.time() - metrics.last_used) / 3600
            # Decay over 24 hours
            recency_factor = max(0.5, 1.0 - (hours_since_use / 24.0))
        
        return metrics.success_rate * recency_factor
    
    def _get_metrics(self, model_name: str, task_type: str) -> Optional[ModelPerformanceMetrics]:
        """Get performance metrics for a model and task type"""
        if model_name not in self.model_metrics:
            return None
        return self.model_metrics[model_name].get(task_type)
    
    def record_feedback(
        self,
        model_name: str,
        task_type: str,
        success: bool,
        latency_ms: float,
        tokens_per_second: float,
        response_quality: Optional[float] = None,
        code_quality: Optional[float] = None,
        memory_usage_mb: Optional[float] = None
    ):
        """
        Record feedback from model usage to improve future scoring.
        
        Args:
            model_name: Name of the model used
            task_type: Type of task performed
            success: Whether the request was successful
            latency_ms: Request latency in milliseconds
            tokens_per_second: Generation speed
            response_quality: Quality of response (0-1), from mindXagent feedback
            code_quality: Quality of generated code (0-1), from code analysis
            memory_usage_mb: Memory usage in MB
        """
        if model_name not in self.model_metrics:
            self.model_metrics[model_name] = {}
        
        if task_type not in self.model_metrics[model_name]:
            self.model_metrics[model_name][task_type] = ModelPerformanceMetrics(
                model_name=model_name,
                task_type=task_type
            )
        
        metrics = self.model_metrics[model_name][task_type]
        
        # Update metrics
        metrics.total_requests += 1
        if success:
            metrics.successful_requests += 1
        else:
            metrics.failed_requests += 1
        
        # Update averages (exponential moving average)
        alpha = 0.1  # Smoothing factor
        metrics.avg_latency_ms = (alpha * latency_ms) + ((1 - alpha) * metrics.avg_latency_ms)
        metrics.avg_tokens_per_second = (alpha * tokens_per_second) + ((1 - alpha) * metrics.avg_tokens_per_second)
        
        if response_quality is not None:
            metrics.avg_response_quality = (alpha * response_quality) + ((1 - alpha) * metrics.avg_response_quality)
        
        if code_quality is not None:
            metrics.avg_code_quality = (alpha * code_quality) + ((1 - alpha) * metrics.avg_code_quality)
        
        if memory_usage_mb is not None:
            metrics.memory_usage_mb = (alpha * memory_usage_mb) + ((1 - alpha) * metrics.memory_usage_mb)
        
        metrics.last_used = time.time()
        metrics.success_rate = metrics.successful_requests / metrics.total_requests if metrics.total_requests > 0 else 0.0
        
        # Save metrics
        self._save_metrics()
        
        logger.debug(f"Recorded feedback for {model_name} ({task_type}): success={success}, latency={latency_ms}ms")
    
    def select_best_model(
        self,
        available_models: List[Dict[str, Any]],
        task_type: str = "chat",
        preferred_models: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Select the best model from available models using hierarchical scoring.
        
        Returns:
            Name of the best model or None if no models available
        """
        if not available_models:
            return None
        
        # Score all models
        scores = []
        for model in available_models:
            score = self.score_model(model, task_type, preferred_models)
            scores.append(score)
        
        # Sort by total score (descending)
        scores.sort(key=lambda x: x.total_score, reverse=True)
        
        if scores:
            best = scores[0]
            logger.info(f"Selected model {best.model_name} for {task_type} (score: {best.total_score:.2f})")
            logger.debug(f"Score breakdown: capability={best.capability_match:.2f}, performance={best.performance_score:.2f}, "
                        f"quality={best.quality_score:.2f}, resources={best.resource_efficiency:.2f}, "
                        f"history={best.historical_success:.2f}")
            return best.model_name
        
        return None
    
    def get_model_rankings(
        self,
        available_models: List[Dict[str, Any]],
        task_type: str = "chat"
    ) -> List[Dict[str, Any]]:
        """Get ranked list of models with scores"""
        scores = []
        for model in available_models:
            score = self.score_model(model, task_type)
            scores.append({
                "model": model.get("name"),
                "score": score.total_score,
                "breakdown": {
                    "capability": score.capability_match,
                    "performance": score.performance_score,
                    "quality": score.quality_score,
                    "resources": score.resource_efficiency,
                    "history": score.historical_success
                },
                "metadata": score.metadata
            })
        
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores
