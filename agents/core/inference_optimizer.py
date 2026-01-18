"""
Inference Optimizer for Ollama

Implements sliding scale optimization to find optimal inference frequency
based on data-driven analysis of input/response patterns.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import deque
from dataclasses import dataclass, asdict

from utils.logging_config import get_logger
from utils.config import Config

logger = get_logger(__name__)


@dataclass
class InferenceMetrics:
    """Metrics for a single inference request"""
    timestamp: float
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    success: bool
    error: Optional[str] = None


@dataclass
class FrequencyWindow:
    """Metrics for a frequency window"""
    frequency: float  # requests per minute
    start_time: float
    end_time: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
    throughput_tokens_per_sec: float
    error_rate: float


class InferenceOptimizer:
    """
    Sliding scale optimizer for Ollama inference frequency.
    
    Uses data-driven approach to find optimal request frequency by:
    1. Testing different frequencies in sliding windows
    2. Collecting metrics (latency, throughput, error rate)
    3. Analyzing patterns to find optimal frequency
    4. Adapting to changing conditions
    """
    
    def __init__(
        self,
        config: Optional[Config] = None,
        metrics_file: Optional[Path] = None,
        min_frequency: float = 1.0,  # 1 request per minute
        max_frequency: float = 120.0,  # 120 requests per minute
        initial_frequency: float = 10.0,  # Start with 10 rpm
        window_duration: int = 300,  # 5 minutes per window
        optimization_interval: int = 600  # Re-optimize every 10 minutes
    ):
        self.config = config or Config()
        self.metrics_file = metrics_file or Path("data/inference_metrics.json")
        self.metrics_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Frequency bounds
        self.min_frequency = min_frequency
        self.max_frequency = max_frequency
        self.current_frequency = initial_frequency
        self.optimal_frequency = initial_frequency
        
        # Window configuration
        self.window_duration = window_duration
        self.optimization_interval = optimization_interval
        
        # Metrics storage
        self.metrics_history: deque = deque(maxlen=10000)  # Last 10k requests
        self.frequency_windows: List[FrequencyWindow] = []
        self.current_window_start: float = time.time()
        self.current_window_metrics: List[InferenceMetrics] = []
        
        # Optimization state
        self.optimization_active = False
        self.optimization_task: Optional[asyncio.Task] = None
        self.last_optimization: float = 0
        
        # Load historical data
        self._load_metrics()
        
        logger.info(f"InferenceOptimizer initialized: {initial_frequency} rpm (range: {min_frequency}-{max_frequency})")
    
    def _load_metrics(self):
        """Load historical metrics from disk"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    # Load recent metrics (last 1000)
                    metrics_data = data.get("metrics", [])[-1000:]
                    for m in metrics_data:
                        self.metrics_history.append(InferenceMetrics(**m))
                    # Load frequency windows
                    windows_data = data.get("frequency_windows", [])[-100:]
                    self.frequency_windows = [FrequencyWindow(**w) for w in windows_data]
                    logger.info(f"Loaded {len(self.metrics_history)} metrics and {len(self.frequency_windows)} windows")
        except Exception as e:
            logger.warning(f"Failed to load metrics: {e}")
    
    def _save_metrics(self):
        """Save metrics to disk"""
        try:
            data = {
                "metrics": [asdict(m) for m in list(self.metrics_history)[-1000:]],
                "frequency_windows": [asdict(w) for w in self.frequency_windows[-100:]],
                "current_frequency": self.current_frequency,
                "optimal_frequency": self.optimal_frequency,
                "last_updated": datetime.now().isoformat()
            }
            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save metrics: {e}")
    
    def record_inference(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None
    ):
        """Record an inference metric"""
        metric = InferenceMetrics(
            timestamp=time.time(),
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            success=success,
            error=error
        )
        
        self.metrics_history.append(metric)
        self.current_window_metrics.append(metric)
        
        # Check if window is complete
        current_time = time.time()
        if current_time - self.current_window_start >= self.window_duration:
            self._finalize_window()
        
        # Periodic save
        if len(self.metrics_history) % 100 == 0:
            self._save_metrics()
    
    def _finalize_window(self):
        """Finalize current window and start new one"""
        if not self.current_window_metrics:
            self.current_window_start = time.time()
            return
        
        current_time = time.time()
        window_duration = current_time - self.current_window_start
        
        # Calculate window metrics
        successful = [m for m in self.current_window_metrics if m.success]
        failed = [m for m in self.current_window_metrics if not m.success]
        
        total_requests = len(self.current_window_metrics)
        successful_count = len(successful)
        failed_count = len(failed)
        
        avg_latency = sum(m.latency_ms for m in successful) / successful_count if successful_count > 0 else 0
        total_input = sum(m.input_tokens for m in self.current_window_metrics)
        total_output = sum(m.output_tokens for m in self.current_window_metrics)
        
        # Calculate actual frequency (requests per minute)
        actual_frequency = (total_requests / window_duration) * 60 if window_duration > 0 else 0
        
        # Calculate throughput (tokens per second)
        total_tokens = total_input + total_output
        throughput = total_tokens / window_duration if window_duration > 0 else 0
        
        # Error rate
        error_rate = failed_count / total_requests if total_requests > 0 else 0
        
        window = FrequencyWindow(
            frequency=self.current_frequency,  # Target frequency
            start_time=self.current_window_start,
            end_time=current_time,
            total_requests=total_requests,
            successful_requests=successful_count,
            failed_requests=failed_count,
            avg_latency_ms=avg_latency,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            throughput_tokens_per_sec=throughput,
            error_rate=error_rate
        )
        
        self.frequency_windows.append(window)
        logger.info(f"Window finalized: {actual_frequency:.1f} rpm, {successful_count}/{total_requests} success, {avg_latency:.0f}ms avg latency")
        
        # Start new window
        self.current_window_metrics = []
        self.current_window_start = current_time
        
        # Save periodically
        if len(self.frequency_windows) % 10 == 0:
            self._save_metrics()
    
    async def optimize_frequency(self) -> float:
        """
        Analyze data and determine optimal frequency.
        
        Returns:
            Optimal frequency in requests per minute
        """
        if len(self.frequency_windows) < 3:
            logger.debug("Not enough data for optimization, keeping current frequency")
            return self.current_frequency
        
        # Analyze recent windows (last 20)
        recent_windows = list(self.frequency_windows[-20:])
        
        # Score each frequency based on:
        # 1. Throughput (higher is better)
        # 2. Error rate (lower is better)
        # 3. Latency (lower is better)
        # 4. Consistency (stable performance)
        
        frequency_scores: Dict[float, List[float]] = {}
        
        for window in recent_windows:
            freq = window.frequency
            if freq not in frequency_scores:
                frequency_scores[freq] = []
            
            # Calculate score (higher is better)
            # Throughput weight: 0.4, Error rate weight: -0.3, Latency weight: -0.2, Success rate: 0.1
            throughput_score = window.throughput_tokens_per_sec * 0.4
            error_penalty = window.error_rate * 100 * -0.3
            latency_penalty = (window.avg_latency_ms / 1000) * -0.2
            success_bonus = (window.successful_requests / window.total_requests) * 10 * 0.1 if window.total_requests > 0 else 0
            
            score = throughput_score + error_penalty + latency_penalty + success_bonus
            frequency_scores[freq].append(score)
        
        # Find frequency with best average score
        best_frequency = self.current_frequency
        best_score = float('-inf')
        
        for freq, scores in frequency_scores.items():
            avg_score = sum(scores) / len(scores)
            if avg_score > best_score:
                best_score = avg_score
                best_frequency = freq
        
        # Apply sliding scale adjustment
        # If current frequency is performing well, try slightly higher
        # If errors are increasing, reduce frequency
        
        current_window = recent_windows[-1] if recent_windows else None
        if current_window:
            if current_window.error_rate < 0.05 and current_window.avg_latency_ms < 5000:
                # Performance is good, try increasing
                adjustment = min(10.0, (self.max_frequency - self.current_frequency) * 0.1)
                best_frequency = min(self.max_frequency, self.current_frequency + adjustment)
            elif current_window.error_rate > 0.1 or current_window.avg_latency_ms > 10000:
                # Performance is poor, reduce frequency
                adjustment = min(10.0, (self.current_frequency - self.min_frequency) * 0.2)
                best_frequency = max(self.min_frequency, self.current_frequency - adjustment)
        
        # Clamp to bounds
        best_frequency = max(self.min_frequency, min(self.max_frequency, best_frequency))
        
        if abs(best_frequency - self.current_frequency) > 1.0:
            logger.info(f"Optimization: {self.current_frequency:.1f} → {best_frequency:.1f} rpm")
            self.current_frequency = best_frequency
            self.optimal_frequency = best_frequency
        
        self.last_optimization = time.time()
        return best_frequency
    
    async def start_optimization_loop(self):
        """Start continuous optimization loop"""
        if self.optimization_active:
            return
        
        self.optimization_active = True
        
        async def _optimization_loop():
            while self.optimization_active:
                try:
                    await asyncio.sleep(self.optimization_interval)
                    
                    # Finalize current window before optimization
                    self._finalize_window()
                    
                    # Run optimization
                    optimal = await self.optimize_frequency()
                    
                    logger.info(f"Inference frequency optimized: {optimal:.1f} rpm")
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Optimization loop error: {e}")
        
        self.optimization_task = asyncio.create_task(_optimization_loop())
        logger.info("Inference optimization loop started")
    
    async def stop_optimization_loop(self):
        """Stop optimization loop"""
        self.optimization_active = False
        if self.optimization_task:
            self.optimization_task.cancel()
            try:
                await self.optimization_task
            except asyncio.CancelledError:
                pass
        # Finalize current window
        self._finalize_window()
        self._save_metrics()
        logger.info("Inference optimization loop stopped")
    
    def get_current_frequency(self) -> float:
        """Get current optimal frequency"""
        return self.current_frequency
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of metrics"""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        recent_metrics = list(self.metrics_history)[-100:]
        successful = [m for m in recent_metrics if m.success]
        
        return {
            "current_frequency": self.current_frequency,
            "optimal_frequency": self.optimal_frequency,
            "total_requests": len(self.metrics_history),
            "recent_requests": len(recent_metrics),
            "recent_success_rate": len(successful) / len(recent_metrics) if recent_metrics else 0,
            "recent_avg_latency_ms": sum(m.latency_ms for m in successful) / len(successful) if successful else 0,
            "windows_analyzed": len(self.frequency_windows),
            "last_optimization": self.last_optimization
        }
