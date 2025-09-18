# monitoring/enhanced_monitoring_system.py
"""
Enhanced Monitoring System with Memory Agent Integration

This system provides:
- Unified resource and performance monitoring
- Structured logging to /data/monitoring/logs via MemoryAgent
- Real-time metrics collection and analysis
- Alert system with escalation protocols
- Historical trend analysis and insights
- Cross-agent performance correlation
"""
import asyncio
import time
import psutil
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent, MemoryType, MemoryImportance

logger = get_logger(__name__)

class MonitoringCategory(Enum):
    RESOURCE = "resource"
    PERFORMANCE = "performance"
    SYSTEM_HEALTH = "system_health"
    ALERT = "alert"
    TREND_ANALYSIS = "trend_analysis"
    API_USAGE = "api_usage"
    RATE_LIMITER = "rate_limiter"

class AlertSeverity(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    INFO = 5

@dataclass
class DetailedResourceMetrics:
    """Enhanced resource metrics with detailed CPU and RAM information."""
    timestamp: float
    
    # CPU Metrics (detailed)
    cpu_percent: float
    cpu_per_core: List[float]
    cpu_count_logical: int
    cpu_count_physical: int
    cpu_freq_current: float
    cpu_freq_min: float
    cpu_freq_max: float
    load_average: Tuple[float, float, float]
    
    # Memory Metrics (detailed)
    memory_percent: float
    memory_total_gb: float
    memory_available_gb: float
    memory_used_gb: float
    memory_free_gb: float
    memory_cached_gb: float
    memory_buffers_gb: float
    swap_percent: float
    swap_total_gb: float
    swap_used_gb: float
    swap_free_gb: float
    
    # Disk and Network (existing)
    disk_usage: Dict[str, float]
    network_io: Dict[str, int]
    process_count: int

@dataclass
class APITokenMetrics:
    """Comprehensive API token usage metrics."""
    model_name: str
    provider: str
    total_prompt_tokens: int = 0
    total_completion_tokens: int = 0
    total_cost_usd: float = 0.0
    calls_count: int = 0
    average_prompt_tokens: float = 0.0
    average_completion_tokens: float = 0.0
    cost_per_call: float = 0.0
    token_efficiency: float = 0.0  # completion/prompt ratio
    hourly_usage: Optional[Dict[str, Dict[str, int]]] = None  # hour -> {prompt: x, completion: y}
    daily_budget_used: float = 0.0
    rate_limit_hits: int = 0
    
    def __post_init__(self):
        if self.hourly_usage is None:
            self.hourly_usage = defaultdict(lambda: {"prompt": 0, "completion": 0, "calls": 0})

class PerformanceMetrics:
    def __init__(self):
        self.llm_calls = defaultdict(lambda: {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "total_latency_ms": 0,
            "latencies": deque(maxlen=100),
            "error_types": defaultdict(int),
            "tokens": {"prompt": 0, "completion": 0},
            "cost": 0.0,
            "first_call": 0.0,
            "last_call": 0.0
        })
        self.agent_performance = defaultdict(lambda: {
            "actions_executed": 0,
            "successful_actions": 0,
            "failed_actions": 0,
            "avg_execution_time": 0.0,
            "last_activity": 0.0
        })
        # Enhanced API token tracking
        self.api_token_metrics = defaultdict(lambda: APITokenMetrics(model_name="", provider=""))
        # Rate limiter tracking
        self.rate_limiter_metrics = defaultdict(dict)

class EnhancedMonitoringSystem:
    """Unified monitoring system with comprehensive CPU, RAM, API token, and rate limiter monitoring."""
    
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(EnhancedMonitoringSystem, cls).__new__(cls)
        return cls._instance
    
    def __init__(self, 
                 memory_agent: Optional[MemoryAgent] = None,
                 config: Optional[Config] = None,
                 test_mode: bool = False):
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return
            
        self.config = config or Config()
        self.memory_agent = memory_agent or MemoryAgent(config=self.config)
        
        # Initialize monitoring paths
        self.monitoring_base_path = PROJECT_ROOT / "data" / "monitoring"
        self.monitoring_logs_path = self.monitoring_base_path / "logs"
        self.monitoring_logs_path.mkdir(parents=True, exist_ok=True)
        
        # Enhanced monitoring state
        self.resource_metrics = DetailedResourceMetrics(
            timestamp=0, cpu_percent=0, cpu_per_core=[], cpu_count_logical=0,
            cpu_count_physical=0, cpu_freq_current=0, cpu_freq_min=0, cpu_freq_max=0,
            load_average=(0, 0, 0), memory_percent=0, memory_total_gb=0,
            memory_available_gb=0, memory_used_gb=0, memory_free_gb=0,
            memory_cached_gb=0, memory_buffers_gb=0, swap_percent=0,
            swap_total_gb=0, swap_used_gb=0, swap_free_gb=0,
            disk_usage={}, network_io={}, process_count=0
        )
        self.performance_metrics = PerformanceMetrics()
        
        # Configuration
        self.monitoring_interval = self.config.get("monitoring.interval_seconds", 30.0)
        self.resource_thresholds = {
            "cpu_critical": self.config.get("monitoring.thresholds.cpu_critical", 90.0),
            "cpu_warning": self.config.get("monitoring.thresholds.cpu_warning", 70.0),
            "memory_critical": self.config.get("monitoring.thresholds.memory_critical", 85.0),
            "memory_warning": self.config.get("monitoring.thresholds.memory_warning", 70.0),
            "disk_critical": self.config.get("monitoring.thresholds.disk_critical", 90.0),
            "disk_warning": self.config.get("monitoring.thresholds.disk_warning", 80.0),
            "swap_critical": self.config.get("monitoring.thresholds.swap_critical", 80.0),
            "swap_warning": self.config.get("monitoring.thresholds.swap_warning", 60.0)
        }
        
        # Alert management
        self.active_alerts = {}
        self.alert_history = deque(maxlen=1000)
        self.alert_cooldown = self.config.get("monitoring.alert_cooldown_seconds", 300)
        
        # Monitoring control
        self.monitoring_active = False
        self.monitoring_task = None
        
        # Historical data for trend analysis
        self.resource_history = deque(maxlen=2880)  # 24 hours at 30s intervals
        self.performance_history = deque(maxlen=1440)  # 24 hours at 1min intervals
        self.api_usage_history = deque(maxlen=1440)  # 24 hours of API usage
        
        logger.info("Enhanced Monitoring System initialized with comprehensive metrics")
        self._initialized = True
    
    async def start_monitoring(self):
        """Start the monitoring system."""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        await self._log_monitoring_event(
            MonitoringCategory.SYSTEM_HEALTH,
            {"event": "monitoring_started", "interval": self.monitoring_interval},
            AlertSeverity.INFO
        )
        logger.info("Enhanced monitoring system started")
    
    async def stop_monitoring(self):
        """Stop the monitoring system."""
        if not self.monitoring_active:
            return
        
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        await self._log_monitoring_event(
            MonitoringCategory.SYSTEM_HEALTH,
            {"event": "monitoring_stopped"},
            AlertSeverity.INFO
        )
        logger.info("Enhanced monitoring system stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop."""
        try:
            while self.monitoring_active:
                start_time = time.time()
                
                # Collect resource metrics
                await self._collect_resource_metrics()
                
                # Analyze and check alerts
                await self._analyze_resource_alerts()
                
                # Log periodic system state
                if int(start_time) % 300 == 0:  # Every 5 minutes
                    await self._log_system_state()
                
                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0.1, self.monitoring_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info("Monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            await self._log_monitoring_event(
                MonitoringCategory.ALERT,
                {"event": "monitoring_error", "error": str(e)},
                AlertSeverity.CRITICAL
            )
    
    async def _collect_resource_metrics(self):
        """Collect comprehensive resource metrics."""
        try:
            now = time.time()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_per_core = psutil.cpu_percent(percpu=True, interval=0.1)
            cpu_count_logical = psutil.cpu_count(logical=True) or 0
            cpu_count_physical = psutil.cpu_count(logical=False) or 0
            
            # CPU frequency (handle potential None values)
            try:
                cpu_freq = psutil.cpu_freq()
                if cpu_freq:
                    cpu_freq_current = cpu_freq.current or 0.0
                    cpu_freq_min = cpu_freq.min or 0.0
                    cpu_freq_max = cpu_freq.max or 0.0
                else:
                    cpu_freq_current = cpu_freq_min = cpu_freq_max = 0.0
            except (AttributeError, OSError):
                cpu_freq_current = cpu_freq_min = cpu_freq_max = 0.0
            
            # Memory metrics
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk metrics
            disk_usage = {}
            for path in ["/", "/tmp"]:  # Add more paths as needed
                try:
                    usage = psutil.disk_usage(path)
                    disk_usage[path] = (usage.used / usage.total) * 100
                except:
                    disk_usage[path] = -1
            
            # Network I/O
            net_io = psutil.net_io_counters()
            network_io = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
            
            # Process count
            process_count = len(psutil.pids())
            
            # Load average (Unix systems)
            try:
                load_avg = psutil.getloadavg()
            except AttributeError:
                load_avg = (0, 0, 0)  # Windows fallback
            
            # Update current metrics
            self.resource_metrics = DetailedResourceMetrics(
                timestamp=now,
                cpu_percent=cpu_percent,
                cpu_per_core=cpu_per_core,
                cpu_count_logical=cpu_count_logical,
                cpu_count_physical=cpu_count_physical,
                cpu_freq_current=cpu_freq_current,
                cpu_freq_min=cpu_freq_min,
                cpu_freq_max=cpu_freq_max,
                load_average=load_avg,
                memory_percent=memory.percent,
                memory_total_gb=memory.total / 1024**3,
                memory_available_gb=memory.available / 1024**3,
                memory_used_gb=memory.used / 1024**3,
                memory_free_gb=memory.free / 1024**3,
                memory_cached_gb=getattr(memory, 'cached', 0) / 1024**3,
                memory_buffers_gb=getattr(memory, 'buffers', 0) / 1024**3,
                swap_percent=swap.percent,
                swap_total_gb=swap.total / 1024**3,
                swap_used_gb=swap.used / 1024**3,
                swap_free_gb=swap.free / 1024**3,
                disk_usage=disk_usage,
                network_io=network_io,
                process_count=process_count
            )
            
            # Add to historical data
            self.resource_history.append(asdict(self.resource_metrics))
            
            # Log detailed metrics to memory agent
            await self._log_monitoring_event(
                MonitoringCategory.RESOURCE,
                asdict(self.resource_metrics),
                AlertSeverity.INFO
            )
            
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}", exc_info=True)
    
    async def _analyze_resource_alerts(self):
        """Analyze resource metrics and trigger alerts."""
        metrics = self.resource_metrics
        now = time.time()
        
        # CPU alerts
        if metrics.cpu_percent >= self.resource_thresholds["cpu_critical"]:
            await self._trigger_alert("cpu_critical", metrics.cpu_percent, 
                                    f"CPU usage critical: {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent >= self.resource_thresholds["cpu_warning"]:
            await self._trigger_alert("cpu_warning", metrics.cpu_percent,
                                    f"CPU usage high: {metrics.cpu_percent:.1f}%")
        else:
            await self._resolve_alert("cpu_critical")
            await self._resolve_alert("cpu_warning")
        
        # Memory alerts
        if metrics.memory_percent >= self.resource_thresholds["memory_critical"]:
            await self._trigger_alert("memory_critical", metrics.memory_percent,
                                    f"Memory usage critical: {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent >= self.resource_thresholds["memory_warning"]:
            await self._trigger_alert("memory_warning", metrics.memory_percent,
                                    f"Memory usage high: {metrics.memory_percent:.1f}%")
        else:
            await self._resolve_alert("memory_critical")
            await self._resolve_alert("memory_warning")
        
        # Disk alerts
        for path, usage in metrics.disk_usage.items():
            if usage >= self.resource_thresholds["disk_critical"]:
                await self._trigger_alert(f"disk_critical_{path}", usage,
                                        f"Disk usage critical on {path}: {usage:.1f}%")
            elif usage >= self.resource_thresholds["disk_warning"]:
                await self._trigger_alert(f"disk_warning_{path}", usage,
                                        f"Disk usage high on {path}: {usage:.1f}%")
            else:
                await self._resolve_alert(f"disk_critical_{path}")
                await self._resolve_alert(f"disk_warning_{path}")
    
    async def _trigger_alert(self, alert_id: str, value: float, message: str):
        """Trigger an alert if not in cooldown."""
        now = time.time()
        
        if alert_id in self.active_alerts:
            last_alert_time = self.active_alerts[alert_id]["timestamp"]
            if now - last_alert_time < self.alert_cooldown:
                return  # Still in cooldown
        
        # Determine severity
        severity = AlertSeverity.CRITICAL if "critical" in alert_id else AlertSeverity.HIGH
        
        alert_data = {
            "alert_id": alert_id,
            "message": message,
            "value": value,
            "timestamp": now,
            "severity": severity.name
        }
        
        self.active_alerts[alert_id] = alert_data
        self.alert_history.append(alert_data)
        
        await self._log_monitoring_event(
            MonitoringCategory.ALERT,
            alert_data,
            severity
        )
        
        logger.warning(f"Alert triggered: {message}")
    
    async def _resolve_alert(self, alert_id: str):
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            resolved_alert = self.active_alerts.pop(alert_id)
            
            resolve_data = {
                "alert_id": alert_id,
                "message": f"Alert resolved: {resolved_alert['message']}",
                "resolved_at": time.time(),
                "duration_seconds": time.time() - resolved_alert["timestamp"]
            }
            
            await self._log_monitoring_event(
                MonitoringCategory.ALERT,
                resolve_data,
                AlertSeverity.INFO
            )
    
    async def log_llm_performance(self,
                                 model_name: str,
                                 task_type: str,
                                 agent_id: str,
                                 latency_ms: float,
                                 success: bool,
                                 prompt_tokens: Optional[int] = None,
                                 completion_tokens: Optional[int] = None,
                                 cost: Optional[float] = None,
                                 error_type: Optional[str] = None,
                                 metadata: Optional[Dict[str, Any]] = None):
        """Log LLM performance metrics."""
        
        metric_key = f"{model_name}|{task_type}|{agent_id}"
        now = time.time()
        
        # Update performance metrics
        perf_data = self.performance_metrics.llm_calls[metric_key]
        perf_data["total_calls"] += 1
        perf_data["total_latency_ms"] += latency_ms
        perf_data["latencies"].append(latency_ms)
        perf_data["last_call"] = now
        
        if perf_data["first_call"] == 0:
            perf_data["first_call"] = now
        
        if success:
            perf_data["successful_calls"] += 1
        else:
            perf_data["failed_calls"] += 1
            if error_type:
                perf_data["error_types"][error_type] += 1
        
        if prompt_tokens:
            perf_data["tokens"]["prompt"] += prompt_tokens
        if completion_tokens:
            perf_data["tokens"]["completion"] += completion_tokens
        if cost:
            perf_data["cost"] += cost
        
        # Create performance log entry
        performance_data = {
            "metric_key": metric_key,
            "model_name": model_name,
            "task_type": task_type,
            "agent_id": agent_id,
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
        
        await self._log_monitoring_event(
            MonitoringCategory.PERFORMANCE,
            performance_data,
            AlertSeverity.INFO
        )
        
        # Check for performance alerts
        await self._check_performance_alerts(metric_key, perf_data)
    
    async def _check_performance_alerts(self, metric_key: str, perf_data: Dict[str, Any]):
        """Check for performance-related alerts."""
        if perf_data["total_calls"] < 5:  # Need some data for analysis
            return
        
        # Calculate metrics
        success_rate = perf_data["successful_calls"] / perf_data["total_calls"]
        avg_latency = perf_data["total_latency_ms"] / perf_data["total_calls"]
        recent_latencies = list(perf_data["latencies"])[-10:]  # Last 10 calls
        recent_avg_latency = sum(recent_latencies) / len(recent_latencies) if recent_latencies else 0
        
        # Success rate alert
        if success_rate < 0.8:
            await self._trigger_alert(
                f"performance_success_rate_{metric_key}",
                success_rate,
                f"Low success rate for {metric_key}: {success_rate:.2%}"
            )
        
        # Latency alert
        if recent_avg_latency > 5000:  # 5 seconds
            await self._trigger_alert(
                f"performance_latency_{metric_key}",
                recent_avg_latency,
                f"High latency for {metric_key}: {recent_avg_latency:.0f}ms"
            )
    
    async def log_agent_performance(self,
                                  agent_id: str,
                                  action_type: str,
                                  execution_time_ms: float,
                                  success: bool,
                                  metadata: Optional[Dict[str, Any]] = None):
        """Log agent performance metrics."""
        
        # Update agent performance metrics
        agent_perf = self.performance_metrics.agent_performance[agent_id]
        agent_perf["actions_executed"] += 1
        agent_perf["last_activity"] = time.time()
        
        if success:
            agent_perf["successful_actions"] += 1
        else:
            agent_perf["failed_actions"] += 1
        
        # Update average execution time
        total_actions = agent_perf["actions_executed"]
        if total_actions == 1:
            agent_perf["avg_execution_time"] = execution_time_ms
        else:
            current_avg = agent_perf["avg_execution_time"]
            agent_perf["avg_execution_time"] = (current_avg * (total_actions - 1) + execution_time_ms) / total_actions
        
        # Log the performance data
        performance_data = {
            "agent_id": agent_id,
            "action_type": action_type,
            "execution_time_ms": execution_time_ms,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            performance_data.update(metadata)
        
        await self._log_monitoring_event(
            MonitoringCategory.PERFORMANCE,
            performance_data,
            AlertSeverity.INFO
        )

    async def log_api_token_usage(self,
                                 model_name: str,
                                 provider: str,
                                 prompt_tokens: int,
                                 completion_tokens: int,
                                 cost_usd: float = 0.0,
                                 success: bool = True,
                                 rate_limited: bool = False,
                                 metadata: Optional[Dict[str, Any]] = None):
        """Log comprehensive API token usage metrics."""
        
        # Calculate cost using real pricing if not provided
        if cost_usd == 0.0 and prompt_tokens > 0 and completion_tokens > 0:
            cost_usd = self.calculate_llm_cost(model_name, prompt_tokens, completion_tokens, provider)
        
        metric_key = f"{provider}|{model_name}"
        now = time.time()
        hour_key = datetime.fromtimestamp(now).strftime("%Y-%m-%d-%H")
        
        # Get or create token metrics
        if metric_key not in self.performance_metrics.api_token_metrics:
            self.performance_metrics.api_token_metrics[metric_key] = APITokenMetrics(
                model_name=model_name,
                provider=provider
            )
        
        api_metrics = self.performance_metrics.api_token_metrics[metric_key]
        
        # Update token metrics
        api_metrics.total_prompt_tokens += prompt_tokens
        api_metrics.total_completion_tokens += completion_tokens
        api_metrics.total_cost_usd += cost_usd
        api_metrics.calls_count += 1
        
        if rate_limited:
            api_metrics.rate_limit_hits += 1
        
        # Calculate derived metrics
        if api_metrics.calls_count > 0:
            api_metrics.average_prompt_tokens = api_metrics.total_prompt_tokens / api_metrics.calls_count
            api_metrics.average_completion_tokens = api_metrics.total_completion_tokens / api_metrics.calls_count
            api_metrics.cost_per_call = api_metrics.total_cost_usd / api_metrics.calls_count
            
            if api_metrics.total_prompt_tokens > 0:
                api_metrics.token_efficiency = api_metrics.total_completion_tokens / api_metrics.total_prompt_tokens
        
        # Update hourly usage
        if api_metrics.hourly_usage:
            hourly_data = api_metrics.hourly_usage[hour_key]
            hourly_data["prompt"] += prompt_tokens
            hourly_data["completion"] += completion_tokens
            hourly_data["calls"] += 1
        
        # Log the API usage data
        usage_data = {
            "model_name": model_name,
            "provider": provider,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost_usd": cost_usd,
            "success": success,
            "rate_limited": rate_limited,
            "cumulative_cost": api_metrics.total_cost_usd,
            "cumulative_tokens": api_metrics.total_prompt_tokens + api_metrics.total_completion_tokens,
            "efficiency_ratio": api_metrics.token_efficiency,
            "timestamp": datetime.now().isoformat()
        }
        
        if metadata:
            usage_data.update(metadata)
        
        await self._log_monitoring_event(
            MonitoringCategory.API_USAGE,
            usage_data,
            AlertSeverity.INFO
        )
        
        # Check for API usage alerts
        await self._check_api_usage_alerts(metric_key, api_metrics)

    async def log_rate_limiter_metrics(self,
                                      provider: str,
                                      model_name: str,
                                      rate_limiter_metrics: Dict[str, Any],
                                      metadata: Optional[Dict[str, Any]] = None):
        """Log rate limiter performance metrics."""
        
        metric_key = f"{provider}|{model_name}"
        
        # Store rate limiter metrics
        self.performance_metrics.rate_limiter_metrics[metric_key] = {
            "provider": provider,
            "model_name": model_name,
            "last_updated": time.time(),
            **rate_limiter_metrics
        }
        
        # Log the rate limiter data
        limiter_data = {
            "provider": provider,
            "model_name": model_name,
            "metric_key": metric_key,
            "timestamp": datetime.now().isoformat(),
            **rate_limiter_metrics
        }
        
        if metadata:
            limiter_data.update(metadata)
        
        await self._log_monitoring_event(
            MonitoringCategory.RATE_LIMITER,
            limiter_data,
            AlertSeverity.INFO
        )
        
        # Check for rate limiter alerts
        await self._check_rate_limiter_alerts(metric_key, rate_limiter_metrics)

    async def _check_api_usage_alerts(self, metric_key: str, api_metrics: APITokenMetrics):
        """Check for API usage-related alerts."""
        
        # Cost threshold alerts
        daily_cost_threshold = self.config.get("monitoring.api.daily_cost_threshold", 100.0)
        if api_metrics.total_cost_usd > daily_cost_threshold:
            await self._trigger_alert(
                f"api_cost_{metric_key}",
                api_metrics.total_cost_usd,
                f"High API cost for {metric_key}: ${api_metrics.total_cost_usd:.2f}"
            )
        
        # Rate limiting alerts
        if api_metrics.rate_limit_hits > 0:
            rate_limit_threshold = self.config.get("monitoring.api.rate_limit_threshold", 10)
            if api_metrics.rate_limit_hits >= rate_limit_threshold:
                await self._trigger_alert(
                    f"api_rate_limit_{metric_key}",
                    api_metrics.rate_limit_hits,
                    f"Frequent rate limiting for {metric_key}: {api_metrics.rate_limit_hits} hits"
                )
        
        # Token efficiency alerts (very low completion/prompt ratio)
        if api_metrics.token_efficiency < 0.1 and api_metrics.calls_count > 10:
            await self._trigger_alert(
                f"api_efficiency_{metric_key}",
                api_metrics.token_efficiency,
                f"Low token efficiency for {metric_key}: {api_metrics.token_efficiency:.3f}"
            )

    async def _check_rate_limiter_alerts(self, metric_key: str, limiter_metrics: Dict[str, Any]):
        """Check for rate limiter-related alerts."""
        
        success_rate = limiter_metrics.get("success_rate", 1.0)
        block_rate = limiter_metrics.get("block_rate", 0.0)
        avg_wait_time = limiter_metrics.get("avg_wait_time_ms", 0.0)
        
        # Low success rate alert
        if success_rate < 0.7:
            await self._trigger_alert(
                f"rate_limiter_success_{metric_key}",
                success_rate,
                f"Low rate limiter success rate for {metric_key}: {success_rate:.2%}"
            )
        
        # High blocking rate alert  
        if block_rate > 0.5:
            await self._trigger_alert(
                f"rate_limiter_blocking_{metric_key}",
                block_rate,
                f"High rate limiter blocking for {metric_key}: {block_rate:.2%}"
            )
        
        # High wait time alert
        if avg_wait_time > 5000:  # 5 seconds
            await self._trigger_alert(
                f"rate_limiter_wait_{metric_key}",
                avg_wait_time,
                f"High rate limiter wait time for {metric_key}: {avg_wait_time:.0f}ms"
            )

    async def get_api_usage_summary(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get comprehensive API usage summary."""
        
        total_cost = 0.0
        total_tokens = 0
        total_calls = 0
        provider_summary = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "calls": 0})
        model_summary = {}
        
        for metric_key, api_metrics in self.performance_metrics.api_token_metrics.items():
            provider = api_metrics.provider
            model_name = api_metrics.model_name
            
            total_cost += api_metrics.total_cost_usd
            total_tokens += api_metrics.total_prompt_tokens + api_metrics.total_completion_tokens
            total_calls += api_metrics.calls_count
            
            provider_summary[provider]["cost"] += api_metrics.total_cost_usd
            provider_summary[provider]["tokens"] += api_metrics.total_prompt_tokens + api_metrics.total_completion_tokens
            provider_summary[provider]["calls"] += api_metrics.calls_count
            
            model_summary[metric_key] = {
                "model_name": model_name,
                "provider": provider,
                "total_cost": api_metrics.total_cost_usd,
                "total_tokens": api_metrics.total_prompt_tokens + api_metrics.total_completion_tokens,
                "calls": api_metrics.calls_count,
                "efficiency": api_metrics.token_efficiency,
                "avg_cost_per_call": api_metrics.cost_per_call,
                "rate_limit_hits": api_metrics.rate_limit_hits
            }
        
        return {
            "summary": {
                "total_cost_usd": total_cost,
                "total_tokens": total_tokens,
                "total_calls": total_calls,
                "avg_cost_per_call": total_cost / max(total_calls, 1),
                "avg_tokens_per_call": total_tokens / max(total_calls, 1)
            },
            "by_provider": dict(provider_summary),
            "by_model": model_summary,
            "timestamp": datetime.now().isoformat()
        }

    async def get_rate_limiter_summary(self) -> Dict[str, Any]:
        """Get comprehensive rate limiter summary."""
        
        summary = {
            "total_limiters": len(self.performance_metrics.rate_limiter_metrics),
            "limiter_status": {},
            "overall_health": "healthy",
            "timestamp": datetime.now().isoformat()
        }
        
        unhealthy_count = 0
        
        for metric_key, limiter_metrics in self.performance_metrics.rate_limiter_metrics.items():
            success_rate = limiter_metrics.get("success_rate", 1.0)
            status = "healthy" if success_rate > 0.9 else "degraded" if success_rate > 0.5 else "critical"
            
            if status != "healthy":
                unhealthy_count += 1
            
            summary["limiter_status"][metric_key] = {
                "status": status,
                "success_rate": success_rate,
                "current_tokens": limiter_metrics.get("current_tokens", 0),
                "total_requests": limiter_metrics.get("total_requests", 0),
                "avg_wait_time_ms": limiter_metrics.get("avg_wait_time_ms", 0),
                "last_updated": limiter_metrics.get("last_updated", 0)
            }
        
        # Overall health assessment
        if unhealthy_count > len(self.performance_metrics.rate_limiter_metrics) * 0.5:
            summary["overall_health"] = "critical"
        elif unhealthy_count > 0:
            summary["overall_health"] = "degraded"
        
        return summary

    def calculate_llm_cost(self, model: str, prompt_tokens: int, completion_tokens: int, provider: str = "openai") -> float:
        """Calculate cost for LLM API usage with ACTUAL current pricing (January 2025)"""
        # Real pricing from provider websites - updated January 2025
        costs = {
            "openai": {
                "o3": {"input": 1.0, "output": 4.0},
                "o3-mini": {"input": 1.1, "output": 4.4},
                "o1": {"input": 15.0, "output": 60.0},
                "o1-mini": {"input": 1.1, "output": 4.4},
                "gpt-4o": {"input": 2.5, "output": 10.0},
                "gpt-4o-mini": {"input": 0.15, "output": 0.6},
                "gpt-4.1": {"input": 2.0, "output": 8.0},
                "gpt-4.1-mini": {"input": 0.4, "output": 1.6},
                "gpt-4.1-nano": {"input": 0.1, "output": 0.4},
                "gpt-4-turbo": {"input": 10.0, "output": 30.0},
                "gpt-4": {"input": 30.0, "output": 60.0},
                "gpt-3.5-turbo": {"input": 0.5, "output": 1.5}
            },
            "anthropic": {
                "claude-4-opus": {"input": 15.0, "output": 75.0},
                "claude-4-sonnet": {"input": 3.0, "output": 15.0},
                "claude-3.7-sonnet": {"input": 3.0, "output": 15.0},
                "claude-3.5-sonnet": {"input": 3.0, "output": 15.0},
                "claude-3.5-haiku": {"input": 0.8, "output": 4.0},
                "claude-3-opus": {"input": 15.0, "output": 75.0},
                "claude-3-sonnet": {"input": 3.0, "output": 15.0},
                "claude-3-haiku": {"input": 0.25, "output": 1.25}
            },
            "google": {
                "gemini-2.5-pro": {"input": 1.25, "output": 10.0},  # Standard context
                "gemini-2.5-pro-long": {"input": 2.5, "output": 15.0},  # Long context >200k
                "gemini-2.5-flash": {"input": 0.3, "output": 2.5},
                "gemini-2.5-flash-lite": {"input": 0.1, "output": 0.4},
                "gemini-2.0-flash": {"input": 0.1, "output": 0.4},
                "gemini-2.0-flash-lite": {"input": 0.075, "output": 0.3},
                "gemini-1.5-pro": {"input": 1.25, "output": 5.0},  # Standard context
                "gemini-1.5-pro-long": {"input": 2.5, "output": 10.0},  # Long context >128k
                "gemini-1.5-flash": {"input": 0.075, "output": 0.3},  # Standard context
                "gemini-1.5-flash-long": {"input": 0.15, "output": 0.6},  # Long context >128k
                "gemini-1.5-flash-8b": {"input": 0.0375, "output": 0.15}
            },
            "groq": {
                "llama-3.3-70b": {"input": 0.59, "output": 0.79},
                "llama-3.1-405b": {"input": 1.79, "output": 1.79},
                "llama-3.1-70b": {"input": 0.59, "output": 0.79},
                "llama-3.2-90b-vision": {"input": 0.9, "output": 0.9},
                "mixtral-8x7b": {"input": 0.5, "output": 0.5}
            },
            "mistral": {
                "mistral-large-2": {"input": 2.0, "output": 6.0},
                "mistral-small-24.09": {"input": 0.2, "output": 0.6},
                "mistral-nemo": {"input": 0.15, "output": 0.15}
            },
            "cohere": {
                "command-r-plus": {"input": 3.0, "output": 15.0},
                "command-r": {"input": 0.5, "output": 1.5},
                "command": {"input": 10.0, "output": 20.0}
            },
            "deepseek": {
                "deepseek-v3": {"input": 0.14, "output": 0.28},
                "deepseek-r1": {"input": 0.55, "output": 2.19}
            }
        }
        
        if provider not in costs or model not in costs[provider]:
            # Better fallback based on average pricing
            return (prompt_tokens / 1_000_000) * 1.0 + (completion_tokens / 1_000_000) * 3.0
        
        model_costs = costs[provider][model]
        input_cost = (prompt_tokens / 1_000_000) * model_costs["input"]
        output_cost = (completion_tokens / 1_000_000) * model_costs["output"]
        
        return input_cost + output_cost

    async def _log_monitoring_event(self,
                                  category: MonitoringCategory,
                                  data: Dict[str, Any],
                                  severity: AlertSeverity):
        """Log monitoring event to memory agent."""
        try:
            # Determine memory type based on category
            memory_type_mapping = {
                MonitoringCategory.RESOURCE: MemoryType.SYSTEM_STATE,
                MonitoringCategory.PERFORMANCE: MemoryType.PERFORMANCE,
                MonitoringCategory.SYSTEM_HEALTH: MemoryType.SYSTEM_STATE,
                MonitoringCategory.ALERT: MemoryType.ERROR,
                MonitoringCategory.TREND_ANALYSIS: MemoryType.SYSTEM_STATE,
                MonitoringCategory.API_USAGE: MemoryType.SYSTEM_STATE,
                MonitoringCategory.RATE_LIMITER: MemoryType.SYSTEM_STATE
            }
            
            memory_type = memory_type_mapping.get(category, MemoryType.SYSTEM_STATE)
            
            # Determine importance based on severity
            importance_mapping = {
                AlertSeverity.CRITICAL: MemoryImportance.CRITICAL,
                AlertSeverity.HIGH: MemoryImportance.HIGH,
                AlertSeverity.MEDIUM: MemoryImportance.MEDIUM,
                AlertSeverity.LOW: MemoryImportance.LOW,
                AlertSeverity.INFO: MemoryImportance.LOW
            }
            
            importance = importance_mapping.get(severity, MemoryImportance.MEDIUM)
            
            # Save to memory agent
            await self.memory_agent.save_timestamped_memory(
                agent_id="enhanced_monitoring_system",
                memory_type=memory_type,
                content=data,
                importance=importance,
                context={"category": category.value, "severity": severity.name},
                tags=["monitoring", category.value, severity.name.lower()]
            )
            
        except Exception as e:
            logger.error(f"Failed to log monitoring event: {e}", exc_info=True)
    
    async def _log_system_state(self):
        """Log comprehensive system state."""
        system_state = {
            "timestamp": datetime.now().isoformat(),
            "resource_metrics": asdict(self.resource_metrics),
            "active_alerts_count": len(self.active_alerts),
            "active_alerts": list(self.active_alerts.keys()),
            "total_llm_metrics": len(self.performance_metrics.llm_calls),
            "total_agent_metrics": len(self.performance_metrics.agent_performance),
            "monitoring_uptime_seconds": time.time() - (self.resource_history[0]["timestamp"] if self.resource_history else time.time())
        }
        
        await self._log_monitoring_event(
            MonitoringCategory.SYSTEM_HEALTH,
            system_state,
            AlertSeverity.INFO
        )
    
    async def generate_monitoring_report(self, hours_back: int = 24) -> Dict[str, Any]:
        """Generate comprehensive monitoring report."""
        now = time.time()
        cutoff_time = now - (hours_back * 3600)
        
        # Filter historical data
        recent_resource_data = [
            entry for entry in self.resource_history 
            if entry["timestamp"] >= cutoff_time
        ]
        
        # Calculate resource averages
        if recent_resource_data:
            avg_cpu = sum(entry["cpu_percent"] for entry in recent_resource_data) / len(recent_resource_data)
            avg_memory = sum(entry["memory_percent"] for entry in recent_resource_data) / len(recent_resource_data)
            max_cpu = max(entry["cpu_percent"] for entry in recent_resource_data)
            max_memory = max(entry["memory_percent"] for entry in recent_resource_data)
        else:
            avg_cpu = avg_memory = max_cpu = max_memory = 0
        
        # Performance summary
        performance_summary = {}
        for metric_key, perf_data in self.performance_metrics.llm_calls.items():
            if perf_data["last_call"] >= cutoff_time:
                performance_summary[metric_key] = {
                    "total_calls": perf_data["total_calls"],
                    "success_rate": perf_data["successful_calls"] / perf_data["total_calls"] if perf_data["total_calls"] > 0 else 1.0,
                    "avg_latency_ms": perf_data["total_latency_ms"] / perf_data["total_calls"] if perf_data["total_calls"] > 0 else 0,
                    "total_cost": perf_data["cost"]
                }
        
        # Alert summary
        recent_alerts = [
            alert for alert in self.alert_history 
            if alert["timestamp"] >= cutoff_time
        ]
        
        report = {
            "report_timestamp": datetime.now().isoformat(),
            "hours_analyzed": hours_back,
            "resource_summary": {
                "avg_cpu_percent": round(avg_cpu, 2),
                "avg_memory_percent": round(avg_memory, 2),
                "max_cpu_percent": round(max_cpu, 2),
                "max_memory_percent": round(max_memory, 2),
                "data_points": len(recent_resource_data)
            },
            "performance_summary": performance_summary,
            "alert_summary": {
                "total_alerts": len(recent_alerts),
                "critical_alerts": len([a for a in recent_alerts if a["severity"] == "CRITICAL"]),
                "active_alerts": len(self.active_alerts),
                "recent_alerts": recent_alerts[-10:]  # Last 10 alerts
            },
            "system_health": {
                "monitoring_active": self.monitoring_active,
                "last_collection": datetime.fromtimestamp(self.resource_metrics.timestamp).isoformat(),
                "total_data_points": len(self.resource_history)
            }
        }
        
        return report
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current real-time metrics."""
        return {
            "timestamp": datetime.now().isoformat(),
            "resource_metrics": asdict(self.resource_metrics),
            "active_alerts": list(self.active_alerts.keys()),
            "performance_metrics_count": {
                "llm_calls": len(self.performance_metrics.llm_calls),
                "agent_performance": len(self.performance_metrics.agent_performance)
            }
        }
    
    async def export_metrics_to_file(self, output_path: Optional[Path] = None) -> Path:
        """Export all metrics to a JSON file."""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = self.monitoring_logs_path / f"metrics_export_{timestamp}.json"
        
        export_data = {
            "export_timestamp": datetime.now().isoformat(),
            "resource_history": list(self.resource_history),
            "llm_performance": {
                key: {
                    **data,
                    "latencies": list(data["latencies"]),
                    "error_types": dict(data["error_types"])
                }
                for key, data in self.performance_metrics.llm_calls.items()
            },
            "agent_performance": dict(self.performance_metrics.agent_performance),
            "alert_history": list(self.alert_history),
            "active_alerts": self.active_alerts,
            "api_token_metrics": dict(self.performance_metrics.api_token_metrics),
            "rate_limiter_metrics": dict(self.performance_metrics.rate_limiter_metrics)
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Metrics exported to {output_path}")
        return output_path


# Global instance accessor
_monitoring_instance = None

async def get_enhanced_monitoring_system(
    memory_agent: Optional[MemoryAgent] = None,
    config: Optional[Config] = None
) -> EnhancedMonitoringSystem:
    """Get or create the enhanced monitoring system instance."""
    global _monitoring_instance
    if _monitoring_instance is None:
        _monitoring_instance = EnhancedMonitoringSystem(memory_agent, config)
    return _monitoring_instance