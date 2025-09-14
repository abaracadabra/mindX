# monitoring/enhanced_performance_monitor.py
"""
Enhanced Performance Monitor with memory integration and self-awareness.

This enhanced version provides:
- Integration with Enhanced Memory Agent for timestamped performance records
- Self-awareness capabilities through performance pattern analysis
- Human-readable performance summaries
- Proactive performance alerting and recommendations
- Cross-agent performance correlation analysis
"""
import time
import json
import asyncio
from collections import defaultdict, deque
from pathlib import Path
from typing import Dict, Any, Optional, List, Deque
from datetime import datetime, timedelta
from enum import Enum

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.enhanced_memory_agent import EnhancedMemoryAgent, MemoryType, MemoryImportance

try:
    from agents.enhanced_memory_agent import EnhancedMemoryAgent
    from agents.enhanced_memory_agent import MemoryType as EMMemoryType
    from agents.enhanced_memory_agent import MemoryImportance as EMMemoryImportance
    HAS_ENHANCED_MEMORY = True
except ImportError:
    # Fallback if enhanced memory agent not available
    from agents.memory_agent import MemoryAgent as EnhancedMemoryAgent
    HAS_ENHANCED_MEMORY = False
    # Define fallback enums
    class EMMemoryType(Enum):
        PERFORMANCE = "performance"
        ERROR = "error"
        SYSTEM_STATE = "system_state"
    
    class EMMemoryImportance(Enum):
        HIGH = 2
        MEDIUM = 3

logger = get_logger(__name__)

class PerformanceAlert(Enum):
    """Types of performance alerts."""
    HIGH_LATENCY = "high_latency"
    LOW_SUCCESS_RATE = "low_success_rate"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    PATTERN_ANOMALY = "pattern_anomaly"
    DEGRADATION_TREND = "degradation_trend"

class EnhancedPerformanceMonitor:
    """Enhanced performance monitor with memory integration and self-awareness."""
    
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EnhancedPerformanceMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self, 
                 memory_agent: Optional[EnhancedMemoryAgent] = None,
                 config_override: Optional[Config] = None, 
                 test_mode: bool = False):
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return

        self.config = config_override or Config()
        self.memory_agent = memory_agent or EnhancedMemoryAgent(config=self.config)
        
        # Performance tracking with enhanced metrics
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_latency_ms": 0,
            "latencies_ms": deque(maxlen=self.config.get("monitoring.performance.latency_window_size", 100)),
            "error_types": defaultdict(int),
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost": 0.0,
            "last_called_at": 0.0,
            "first_called_at": 0.0,
            "hourly_stats": defaultdict(lambda: {"calls": 0, "success": 0, "avg_latency": 0.0}),
            "daily_trends": deque(maxlen=30)  # Last 30 days
        })
        
        # Alert thresholds
        self.alert_thresholds = {
            "max_latency_ms": self.config.get("monitoring.performance.max_latency_ms", 5000),
            "min_success_rate": self.config.get("monitoring.performance.min_success_rate", 0.8),
            "max_error_rate": self.config.get("monitoring.performance.max_error_rate", 0.2),
            "latency_trend_threshold": self.config.get("monitoring.performance.latency_trend_threshold", 1.5)
        }
        
        # Performance analysis
        self.performance_history = deque(maxlen=1000)
        self.alert_history = deque(maxlen=100)
        
        # Auto-analysis settings
        self.auto_analysis_enabled = self.config.get("monitoring.performance.auto_analysis_enabled", True)
        self.analysis_interval_seconds = self.config.get("monitoring.performance.analysis_interval_seconds", 300)
        self._analysis_task: Optional[asyncio.Task] = None
        
        self.metrics_file_path = PROJECT_ROOT / self.config.get(
            "monitoring.performance.metrics_file", "data/performance_metrics.json"
        )
        
        if self.auto_analysis_enabled:
            self.start_auto_analysis()
            
        logger.info("Enhanced PerformanceMonitor initialized with memory integration and self-awareness.")
        self._initialized = True

    async def log_llm_call(self,
                          model_name: str,
                          task_type: str,
                          initiating_agent_id: str,
                          latency_ms: float,
                          success: bool,
                          prompt_tokens: Optional[int] = None,
                          completion_tokens: Optional[int] = None,
                          cost: Optional[float] = None,
                          error_type: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None):
        """Log an LLM call with enhanced memory integration."""
        
        metric_key = f"{model_name}|{task_type}|{initiating_agent_id}"
        now = time.time()
        current_hour = datetime.now().hour

        entry = self.metrics[metric_key]
        if entry["total_calls"] == 0:
            entry["first_called_at"] = now

        # Update basic metrics
        entry["total_calls"] += 1
        entry["total_latency_ms"] += latency_ms
        entry["latencies_ms"].append(latency_ms)
        entry["last_called_at"] = now
        
        # Update hourly statistics
        hourly_stat = entry["hourly_stats"][current_hour]
        hourly_stat["calls"] += 1
        
        if success:
            entry["successful_calls"] += 1
            hourly_stat["success"] += 1
        else:
            entry["failed_calls"] += 1
            if error_type:
                entry["error_types"][error_type] += 1
        
        # Update hourly average latency
        if hourly_stat["calls"] > 0:
            hourly_stat["avg_latency"] = (
                (hourly_stat["avg_latency"] * (hourly_stat["calls"] - 1) + latency_ms) / 
                hourly_stat["calls"]
            )
        
        if prompt_tokens is not None:
            entry["total_prompt_tokens"] += prompt_tokens
        if completion_tokens is not None:
            entry["total_completion_tokens"] += completion_tokens
        if cost is not None:
            entry["total_cost"] += cost
        
        # Save to enhanced memory with detailed context
        performance_data = {
            "metric_key": metric_key,
            "model_name": model_name,
            "task_type": task_type,
            "initiating_agent_id": initiating_agent_id,
            "latency_ms": latency_ms,
            "success": success,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
            "error_type": error_type,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            performance_data.update(metadata)
        
        # Store in enhanced memory
        if HAS_ENHANCED_MEMORY and hasattr(self.memory_agent, 'save_timestamped_memory'):
            await self.memory_agent.save_timestamped_memory(
                agent_id="performance_monitor",
                memory_type=EMMemoryType.PERFORMANCE,
                content=performance_data,
                importance=EMMemoryImportance.MEDIUM,
                context={"metric_key": metric_key, "success": success},
                tags=["llm_call", task_type, model_name]
            )
        else:
            # Fallback to original log_process method
            await self.memory_agent.log_process(
                process_name="performance_tracking",
                data=performance_data,
                metadata={"agent_id": "performance_monitor"}
            )
        
        # Add to performance history for trend analysis
        self.performance_history.append({
            "timestamp": now,
            "metric_key": metric_key,
            "latency_ms": latency_ms,
            "success": success,
            "error_type": error_type
        })
        
        # Check for immediate alerts
        await self._check_performance_alerts(metric_key, entry)

    async def _check_performance_alerts(self, metric_key: str, entry: Dict[str, Any]):
        """Check for performance alerts and log them to memory."""
        alerts = []
        
        # Check latency
        if len(entry["latencies_ms"]) > 0:
            recent_avg_latency = sum(list(entry["latencies_ms"])[-10:]) / min(10, len(entry["latencies_ms"]))
            if recent_avg_latency > self.alert_thresholds["max_latency_ms"]:
                alerts.append({
                    "type": PerformanceAlert.HIGH_LATENCY.value,
                    "metric_key": metric_key,
                    "current_value": recent_avg_latency,
                    "threshold": self.alert_thresholds["max_latency_ms"],
                    "message": f"High latency detected: {recent_avg_latency:.1f}ms > {self.alert_thresholds['max_latency_ms']}ms"
                })
        
        # Check success rate
        if entry["total_calls"] >= 10:  # Only check after sufficient data
            success_rate = entry["successful_calls"] / entry["total_calls"]
            if success_rate < self.alert_thresholds["min_success_rate"]:
                alerts.append({
                    "type": PerformanceAlert.LOW_SUCCESS_RATE.value,
                    "metric_key": metric_key,
                    "current_value": success_rate,
                    "threshold": self.alert_thresholds["min_success_rate"],
                    "message": f"Low success rate detected: {success_rate:.1%} < {self.alert_thresholds['min_success_rate']:.1%}"
                })
        
        # Log alerts to memory
        for alert in alerts:
            await self.memory_agent.save_timestamped_memory(
                agent_id="performance_monitor",
                memory_type=MemoryType.ERROR,
                content=alert,
                importance=MemoryImportance.HIGH,
                context={"alert_type": alert["type"]},
                tags=["performance_alert", alert["type"], metric_key]
            )
            
            self.alert_history.append({
                "timestamp": time.time(),
                "alert": alert
            })
            
            logger.warning(f"Performance Alert: {alert['message']}")

    async def analyze_performance_patterns(self, agent_id: Optional[str] = None, hours_back: int = 24) -> Dict[str, Any]:
        """Analyze performance patterns from memory data."""
        try:
            # Get performance memories from enhanced memory agent
            memories = await self.memory_agent.get_recent_memories(
                agent_id="performance_monitor",
                memory_type=MemoryType.PERFORMANCE,
                limit=1000,
                days_back=max(1, hours_back // 24)
            )
            
            if not memories:
                return {"error": "No performance data found for analysis"}
            
            # Filter by specific agent if requested
            if agent_id:
                memories = [m for m in memories if m.content.get("initiating_agent_id") == agent_id]
            
            # Analyze patterns
            analysis = {
                "total_calls": len(memories),
                "time_range_hours": hours_back,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "model_breakdown": defaultdict(lambda: {"calls": 0, "success": 0, "latency_sum": 0}),
                "task_breakdown": defaultdict(lambda: {"calls": 0, "success": 0, "latency_sum": 0}),
                "agent_breakdown": defaultdict(lambda: {"calls": 0, "success": 0, "latency_sum": 0}),
                "hourly_distribution": defaultdict(int),
                "error_patterns": defaultdict(int),
                "trends": {},
                "recommendations": []
            }
            
            successful_calls = 0
            total_latency = 0
            
            for memory in memories:
                content = memory.content
                
                # Basic stats
                if content.get("success", False):
                    successful_calls += 1
                
                latency = content.get("latency_ms", 0)
                total_latency += latency
                
                # Breakdown by model
                model = content.get("model_name", "unknown")
                model_stats = analysis["model_breakdown"][model]
                model_stats["calls"] += 1
                model_stats["latency_sum"] += latency
                if content.get("success", False):
                    model_stats["success"] += 1
                
                # Breakdown by task type
                task = content.get("task_type", "unknown")
                task_stats = analysis["task_breakdown"][task]
                task_stats["calls"] += 1
                task_stats["latency_sum"] += latency
                if content.get("success", False):
                    task_stats["success"] += 1
                
                # Breakdown by agent
                agent = content.get("initiating_agent_id", "unknown")
                agent_stats = analysis["agent_breakdown"][agent]
                agent_stats["calls"] += 1
                agent_stats["latency_sum"] += latency
                if content.get("success", False):
                    agent_stats["success"] += 1
                
                # Hourly distribution
                try:
                    hour = datetime.fromisoformat(memory.timestamp).hour
                    analysis["hourly_distribution"][hour] += 1
                except:
                    pass
                
                # Error patterns
                error_type = content.get("error_type")
                if error_type:
                    analysis["error_patterns"][error_type] += 1
            
            # Calculate overall metrics
            if analysis["total_calls"] > 0:
                analysis["success_rate"] = successful_calls / analysis["total_calls"]
                analysis["avg_latency_ms"] = total_latency / analysis["total_calls"]
            
            # Calculate breakdown averages
            for breakdown in ["model_breakdown", "task_breakdown", "agent_breakdown"]:
                for key, stats in analysis[breakdown].items():
                    if stats["calls"] > 0:
                        stats["success_rate"] = stats["success"] / stats["calls"]
                        stats["avg_latency_ms"] = stats["latency_sum"] / stats["calls"]
            
            # Convert defaultdicts to regular dicts
            analysis["model_breakdown"] = dict(analysis["model_breakdown"])
            analysis["task_breakdown"] = dict(analysis["task_breakdown"])
            analysis["agent_breakdown"] = dict(analysis["agent_breakdown"])
            analysis["hourly_distribution"] = dict(analysis["hourly_distribution"])
            analysis["error_patterns"] = dict(analysis["error_patterns"])
            
            # Generate recommendations
            analysis["recommendations"] = await self._generate_performance_recommendations(analysis)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze performance patterns: {e}", exc_info=True)
            return {"error": str(e)}

    async def _generate_performance_recommendations(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate performance improvement recommendations."""
        recommendations = []
        
        # Success rate recommendations
        if analysis["success_rate"] < 0.9:
            recommendations.append(f"Success rate is {analysis['success_rate']:.1%}. Consider investigating error patterns.")
        
        # Latency recommendations
        if analysis["avg_latency_ms"] > 3000:
            recommendations.append(f"Average latency is {analysis['avg_latency_ms']:.1f}ms. Consider optimizing prompts or using faster models.")
        
        # Model-specific recommendations
        for model, stats in analysis["model_breakdown"].items():
            if stats["success_rate"] < 0.8:
                recommendations.append(f"Model '{model}' has low success rate ({stats['success_rate']:.1%}). Consider prompt optimization.")
            if stats["avg_latency_ms"] > 5000:
                recommendations.append(f"Model '{model}' has high latency ({stats['avg_latency_ms']:.1f}ms). Consider alternative models.")
        
        # Error pattern recommendations
        if analysis["error_patterns"]:
            top_error = max(analysis["error_patterns"].items(), key=lambda x: x[1])
            recommendations.append(f"Most common error: '{top_error[0]}' ({top_error[1]} occurrences). Focus on resolving this error type.")
        
        return recommendations

    async def generate_performance_report(self, agent_id: Optional[str] = None, hours_back: int = 24) -> str:
        """Generate a human-readable performance report."""
        try:
            analysis = await self.analyze_performance_patterns(agent_id, hours_back)
            
            if "error" in analysis:
                return f"Error generating performance report: {analysis['error']}"
            
            agent_filter = f" for {agent_id}" if agent_id else ""
            
            report_lines = [
                f"# Performance Report{agent_filter}",
                f"Time Period: Last {hours_back} hours",
                f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "## Overall Performance",
                f"- Total LLM calls: {analysis['total_calls']}",
                f"- Success rate: {analysis['success_rate']:.1%}",
                f"- Average latency: {analysis['avg_latency_ms']:.1f}ms",
                ""
            ]
            
            # Model breakdown
            if analysis["model_breakdown"]:
                report_lines.extend([
                    "## Performance by Model",
                    *[f"- {model}: {stats['calls']} calls, {stats['success_rate']:.1%} success, {stats['avg_latency_ms']:.1f}ms avg" 
                      for model, stats in analysis["model_breakdown"].items()],
                    ""
                ])
            
            # Task breakdown
            if analysis["task_breakdown"]:
                report_lines.extend([
                    "## Performance by Task Type",
                    *[f"- {task}: {stats['calls']} calls, {stats['success_rate']:.1%} success, {stats['avg_latency_ms']:.1f}ms avg" 
                      for task, stats in analysis["task_breakdown"].items()],
                    ""
                ])
            
            # Error patterns
            if analysis["error_patterns"]:
                report_lines.extend([
                    "## Error Patterns",
                    *[f"- {error}: {count} occurrences" for error, count in analysis["error_patterns"].items()],
                    ""
                ])
            
            # Recommendations
            if analysis["recommendations"]:
                report_lines.extend([
                    "## Recommendations",
                    *[f"- {rec}" for rec in analysis["recommendations"]],
                    ""
                ])
            
            return "\n".join(report_lines)
            
        except Exception as e:
            logger.error(f"Failed to generate performance report: {e}", exc_info=True)
            return f"Error generating performance report: {e}"

    def start_auto_analysis(self):
        """Start automatic performance analysis."""
        if self._analysis_task and not self._analysis_task.done():
            logger.info("Auto-analysis already running.")
            return
        
        if self.analysis_interval_seconds > 0:
            self._analysis_task = asyncio.create_task(self._auto_analysis_worker())
            logger.info(f"Started auto-performance analysis with {self.analysis_interval_seconds}s interval.")

    def stop_auto_analysis(self):
        """Stop automatic performance analysis."""
        if self._analysis_task and not self._analysis_task.done():
            self._analysis_task.cancel()
            logger.info("Auto-performance analysis stopped.")

    async def _auto_analysis_worker(self):
        """Worker for automatic performance analysis."""
        logger.info("Auto-performance analysis started.")
        
        while True:
            try:
                await asyncio.sleep(self.analysis_interval_seconds)
                
                # Generate system-wide performance analysis
                analysis = await self.analyze_performance_patterns(hours_back=1)
                
                if "error" not in analysis:
                    # Store analysis results in memory
                    await self.memory_agent.save_timestamped_memory(
                        agent_id="performance_monitor",
                        memory_type=MemoryType.SYSTEM_STATE,
                        content={
                            "analysis_type": "auto_performance_analysis",
                            "analysis_results": analysis
                        },
                        importance=MemoryImportance.MEDIUM,
                        tags=["auto_analysis", "performance_summary"]
                    )
                    
                    logger.info(f"Auto-analysis complete: {analysis['total_calls']} calls, "
                              f"{analysis['success_rate']:.1%} success rate, "
                              f"{analysis['avg_latency_ms']:.1f}ms avg latency")
                
            except asyncio.CancelledError:
                logger.info("Auto-performance analysis cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in auto-performance analysis: {e}", exc_info=True)
                # Sleep longer on error to avoid rapid error logging
                await asyncio.sleep(self.analysis_interval_seconds * 2)

    async def shutdown(self):
        """Shutdown the enhanced performance monitor."""
        logger.info("Enhanced PerformanceMonitor shutting down...")
        self.stop_auto_analysis()
        
        if self._analysis_task:
            try:
                await asyncio.wait_for(self._analysis_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.warning("Auto-analysis task did not shut down cleanly.")
        
        logger.info("Enhanced PerformanceMonitor shutdown complete.")

    # Compatibility methods with original PerformanceMonitor
    def log_llm_call_sync(self, *args, **kwargs):
        """Synchronous wrapper for compatibility."""
        asyncio.create_task(self.log_llm_call(*args, **kwargs))

    def get_metrics_for_key(self, metric_key: str) -> Optional[Dict[str, Any]]:
        """Get metrics for a specific key (compatibility method)."""
        data = self.metrics.get(metric_key)
        if not data:
            return None
        
        summary = data.copy()
        summary["latencies_ms"] = list(data["latencies_ms"])
        summary["error_types"] = dict(data["error_types"])
        
        if data["total_calls"] > 0:
            summary["avg_latency_ms"] = data["total_latency_ms"] / data["total_calls"]
            summary["success_rate"] = data["successful_calls"] / data["total_calls"]
        else:
            summary["avg_latency_ms"] = 0
            summary["success_rate"] = 1.0
        
        return summary

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all metrics (compatibility method)."""
        all_summaries = {}
        for key in list(self.metrics.keys()):
            summary = self.get_metrics_for_key(key)
            if summary:
                all_summaries[key] = summary
        return all_summaries 