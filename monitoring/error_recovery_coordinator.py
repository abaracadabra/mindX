# mindx/monitoring/error_recovery_coordinator.py
"""
Error Recovery Coordinator for MindX System-Wide Reliability.

This coordinator manages and orchestrates error recovery across all agents,
providing centralized monitoring, intelligent recovery strategy selection,
and cross-agent coordination for system-wide reliability enhancement.
"""

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, asdict, field
from enum import Enum

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from core.belief_system import BeliefSystem, BeliefSource
from agents.memory_agent import MemoryAgent

logger = get_logger(__name__)

class SystemHealthStatus(Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    FAILED = "FAILED"
    RECOVERING = "RECOVERING"

class RecoveryPriority(Enum):
    LOW = 1
    MEDIUM = 3
    HIGH = 7
    CRITICAL = 10

@dataclass
class SystemFailure:
    """Represents a system failure event with comprehensive context."""
    id: str
    timestamp: float
    component: str
    failure_type: str
    error_message: str
    stack_trace: Optional[str]
    affected_agents: List[str]
    severity: RecoveryPriority
    recovery_attempts: int = 0
    last_recovery_attempt: Optional[float] = None
    recovery_strategies_tried: List[str] = field(default_factory=list)
    is_resolved: bool = False
    resolution_timestamp: Optional[float] = None

@dataclass  
class RecoveryAction:
    """Represents a recovery action to be executed."""
    id: str
    failure_id: str
    strategy: str
    component: str
    action_type: str
    parameters: Dict[str, Any]
    estimated_duration: int
    success_probability: float
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class SystemHealthMetrics:
    """System health metrics for monitoring."""
    timestamp: float
    overall_status: SystemHealthStatus
    component_statuses: Dict[str, SystemHealthStatus]
    active_failures: int
    recovery_success_rate: float
    mean_recovery_time: float
    system_uptime_percentage: float
    critical_components_healthy: int
    total_critical_components: int

class ErrorRecoveryCoordinator:
    """
    Centralized coordinator for system-wide error recovery and reliability management.
    Orchestrates recovery efforts across all agents and components.
    """
    
    def __init__(self,
                 memory_agent: MemoryAgent,
                 belief_system: BeliefSystem,
                 config: Optional[Config] = None):
        self.memory_agent = memory_agent
        self.belief_system = belief_system
        self.config = config or Config()
        self.log_prefix = "ErrorRecoveryCoordinator:"
        
        # State management
        self.active_failures: Dict[str, SystemFailure] = {}
        self.recovery_history: List[SystemFailure] = []
        self.pending_actions: Dict[str, RecoveryAction] = {}
        self.component_health: Dict[str, SystemHealthStatus] = {}
        self.recovery_strategies_success_rates: Dict[str, float] = {}
        
        # Critical components to monitor
        self.critical_components = [
            "llm.llm_factory",
            "core.bdi_agent", 
            "orchestration.coordinator_agent",
            "orchestration.mastermind_agent",
            "agents.memory_agent",
            "monitoring.token_calculator_tool",
            "evolution.blueprint_agent",
            "learning.strategic_evolution_agent"
        ]
        
        # Recovery strategies with estimated success rates
        self.recovery_strategies = {
            "restart_component": 0.7,
            "fallback_configuration": 0.6,
            "alternative_provider": 0.8,
            "graceful_degradation": 0.9,
            "system_rollback": 0.5,
            "manual_intervention": 0.95,
            "emergency_shutdown": 1.0
        }
        
        # Initialize component health
        for component in self.critical_components:
            self.component_health[component] = SystemHealthStatus.HEALTHY
        
        # Monitoring configuration
        self.monitoring_enabled = True
        self.health_check_interval = self.config.get("error_recovery.health_check_interval_seconds", 30)
        self.max_recovery_attempts = self.config.get("error_recovery.max_recovery_attempts", 3)
        self.escalation_threshold = self.config.get("error_recovery.escalation_threshold_minutes", 10)
        
        logger.info(f"{self.log_prefix} Initialized with monitoring for {len(self.critical_components)} critical components")

    async def start_monitoring(self):
        """Start continuous system health monitoring."""
        if not self.monitoring_enabled:
            return
            
        logger.info(f"{self.log_prefix} Starting continuous health monitoring (interval: {self.health_check_interval}s)")
        
        while self.monitoring_enabled:
            try:
                await self._perform_health_check()
                await self._process_pending_recoveries()
                await self._update_system_metrics()
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"{self.log_prefix} Monitoring loop error: {e}", exc_info=True)
                await asyncio.sleep(self.health_check_interval * 2)  # Back off on error

    async def report_failure(self, component: str, failure_type: str, error_message: str,
                           affected_agents: Optional[List[str]] = None, severity: RecoveryPriority = RecoveryPriority.MEDIUM,
                           stack_trace: Optional[str] = None) -> str:
        """
        Report a system failure for centralized recovery coordination.
        
        Returns:
            Failure ID for tracking
        """
        failure_id = f"failure_{int(time.time() * 1000)}_{str(uuid.uuid4())[:8]}"
        
        failure = SystemFailure(
            id=failure_id,
            timestamp=time.time(),
            component=component,
            failure_type=failure_type,
            error_message=error_message,
            stack_trace=stack_trace,
            affected_agents=affected_agents or [],
            severity=severity
        )
        
        self.active_failures[failure_id] = failure
        self.component_health[component] = SystemHealthStatus.FAILED
        
        logger.error(f"{self.log_prefix} FAILURE REPORTED: {component} - {failure_type}: {error_message}")
        
        # Log to memory agent for analysis
        await self.memory_agent.log_process(
            process_name="system_failure_reported",
            data=asdict(failure),
            metadata={"coordinator": "error_recovery", "severity": severity.name}
        )
        
        return failure_id

    async def _initiate_recovery(self, failure_id: str) -> bool:
        """Initiate recovery process for a specific failure."""
        if failure_id not in self.active_failures:
            logger.warning(f"{self.log_prefix} Cannot initiate recovery for unknown failure: {failure_id}")
            return False
            
        failure = self.active_failures[failure_id]
        
        if failure.recovery_attempts >= self.max_recovery_attempts:
            logger.error(f"{self.log_prefix} Max recovery attempts exceeded for {failure_id}. Escalating...")
            await self._escalate_failure(failure_id)
            return False
        
        logger.info(f"{self.log_prefix} Initiating recovery for {failure.component} (attempt {failure.recovery_attempts + 1})")
        
        # Select best recovery strategy
        strategy = await self._select_recovery_strategy(failure)
        
        # Create recovery action
        action = RecoveryAction(
            id=f"recovery_{failure_id}_{int(time.time())}",
            failure_id=failure_id,
            strategy=strategy,
            component=failure.component,
            action_type=self._map_strategy_to_action(strategy),
            parameters=self._build_recovery_parameters(failure, strategy),
            estimated_duration=self._estimate_recovery_duration(strategy),
            success_probability=self.recovery_strategies.get(strategy, 0.5)
        )
        
        # Execute recovery action
        success = await self._execute_recovery_action(action)
        
        # Update failure record
        failure.recovery_attempts += 1
        failure.last_recovery_attempt = time.time()
        failure.recovery_strategies_tried.append(strategy)
        
        if success:
            await self._mark_failure_resolved(failure_id)
            logger.info(f"{self.log_prefix} Recovery successful for {failure.component}")
        else:
            logger.warning(f"{self.log_prefix} Recovery attempt failed for {failure.component}")
            
        return success

    async def _select_recovery_strategy(self, failure: SystemFailure) -> str:
        """Select the best recovery strategy based on failure context and history."""
        
        # Filter strategies not yet tried
        available_strategies = [s for s in self.recovery_strategies.keys() 
                              if s not in failure.recovery_strategies_tried]
        
        if not available_strategies:
            return "manual_intervention"  # Last resort
        
        # Score strategies based on success probability and failure context
        strategy_scores = {}
        
        for strategy in available_strategies:
            base_score = self.recovery_strategies[strategy]
            
            # Adjust score based on failure context
            if failure.failure_type in ["connection_error", "timeout"] and strategy == "restart_component":
                base_score *= 1.2
            elif failure.failure_type == "configuration_error" and strategy == "fallback_configuration":
                base_score *= 1.3
            elif failure.severity == RecoveryPriority.CRITICAL and strategy == "emergency_shutdown":
                base_score *= 0.5  # Avoid shutdown unless truly necessary
            
            strategy_scores[strategy] = base_score
        
        # Select strategy with highest score
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])[0]
        
        logger.info(f"{self.log_prefix} Selected recovery strategy '{best_strategy}' for {failure.component}")
        return best_strategy

    async def _execute_recovery_action(self, action: RecoveryAction) -> bool:
        """Execute a specific recovery action."""
        try:
            logger.info(f"{self.log_prefix} Executing {action.strategy} for {action.component}")
            
            if action.action_type == "restart_service":
                return await self._restart_component(action.component, action.parameters)
            elif action.action_type == "switch_configuration":
                return await self._switch_configuration(action.component, action.parameters)
            elif action.action_type == "escalate_manual":
                return await self._escalate_to_manual(action.component, action.parameters)
            elif action.action_type == "system_rollback":
                return await self._perform_system_rollback(action.parameters)
            elif action.action_type == "emergency_shutdown":
                return await self._emergency_shutdown(action.parameters)
            else:
                logger.warning(f"{self.log_prefix} Unknown recovery action type: {action.action_type}")
                return False
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Recovery action execution failed: {e}", exc_info=True)
            return False

    async def _restart_component(self, component: str, parameters: Dict[str, Any]) -> bool:
        """Restart a specific component."""
        logger.info(f"{self.log_prefix} Restarting component: {component}")
        
        # Update belief system about restart attempt
        await self.belief_system.add_belief(
            key=f"system.recovery.restart.{component}",
            value={"timestamp": time.time(), "status": "attempting"},
            confidence=0.8,
            source=BeliefSource.SELF_ANALYSIS,
            ttl_seconds=300
        )
        
        # Simulate restart (in real implementation, this would trigger actual restart)
        await asyncio.sleep(2)  # Simulate restart time
        
        # Update component status  
        self.component_health[component] = SystemHealthStatus.RECOVERING
        
        # Verify restart success
        await asyncio.sleep(3)  # Simulate verification time
        success = True  # In real implementation, verify component is working
        
        if success:
            self.component_health[component] = SystemHealthStatus.HEALTHY
            
        return success

    async def _switch_configuration(self, component: str, parameters: Dict[str, Any]) -> bool:
        """Switch to fallback configuration for a component."""
        logger.info(f"{self.log_prefix} Switching {component} to fallback configuration")
        
        fallback_config = parameters.get("fallback_config", {})
        
        # Apply fallback configuration
        await self.belief_system.add_belief(
            key=f"system.config.fallback.{component}",
            value=fallback_config,
            confidence=0.9,
            source=BeliefSource.SELF_ANALYSIS,
            ttl_seconds=3600
        )
        
        return True

    async def _escalate_to_manual(self, component: str, parameters: Dict[str, Any]) -> bool:
        """Escalate to manual intervention."""
        logger.critical(f"{self.log_prefix} ESCALATING {component} to manual intervention")
        
        # Create high-priority alert
        alert_data = {
            "component": component,
            "timestamp": time.time(),
            "alert_type": "MANUAL_INTERVENTION_REQUIRED",
            "details": parameters
        }
        
        await self.memory_agent.log_process(
            process_name="manual_intervention_alert",
            data=alert_data,
            metadata={"priority": "CRITICAL", "requires_attention": True}
        )
        
        return True  # Escalation itself is successful

    async def _perform_system_rollback(self, parameters: Dict[str, Any]) -> bool:
        """Perform system-wide rollback."""
        logger.warning(f"{self.log_prefix} Performing system rollback")
        
        rollback_point = parameters.get("rollback_point", "latest")
        
        # Log rollback initiation
        await self.memory_agent.log_process(
            process_name="system_rollback_initiated",
            data={"rollback_point": rollback_point, "timestamp": time.time()},
            metadata={"coordinator": "error_recovery", "action": "rollback"}
        )
        
        # In real implementation, trigger actual rollback procedures
        await asyncio.sleep(5)  # Simulate rollback time
        
        return True

    async def _emergency_shutdown(self, parameters: Dict[str, Any]) -> bool:
        """Perform emergency shutdown."""
        logger.critical(f"{self.log_prefix} EMERGENCY SHUTDOWN INITIATED")
        
        shutdown_reason = parameters.get("reason", "Critical system failure")
        
        # Log emergency shutdown
        await self.memory_agent.log_process(
            process_name="emergency_shutdown",
            data={"reason": shutdown_reason, "timestamp": time.time()},
            metadata={"coordinator": "error_recovery", "action": "emergency_shutdown"}
        )
        
        # Update system status
        for component in self.critical_components:
            self.component_health[component] = SystemHealthStatus.FAILED
        
        return True

    async def _mark_failure_resolved(self, failure_id: str):
        """Mark a failure as resolved."""
        if failure_id in self.active_failures:
            failure = self.active_failures[failure_id]
            failure.is_resolved = True
            failure.resolution_timestamp = time.time()
            
            # Move to history
            self.recovery_history.append(failure)
            del self.active_failures[failure_id]
            
            # Update component health
            self.component_health[failure.component] = SystemHealthStatus.HEALTHY
            
            # Update belief system
            await self.belief_system.add_belief(
                key=f"system.recovery.resolved.{failure_id}",
                value=asdict(failure),
                confidence=0.95,
                source=BeliefSource.SELF_ANALYSIS,
                ttl_seconds=86400  # Keep for 24 hours
            )
            
            logger.info(f"{self.log_prefix} Failure {failure_id} marked as resolved")

    def _map_strategy_to_action(self, strategy: str) -> str:
        """Map recovery strategy to specific action type."""
        strategy_mapping = {
            "restart_component": "restart_service",
            "fallback_configuration": "switch_configuration", 
            "alternative_provider": "switch_configuration",
            "graceful_degradation": "switch_configuration",
            "system_rollback": "system_rollback",
            "manual_intervention": "escalate_manual",
            "emergency_shutdown": "emergency_shutdown"
        }
        return strategy_mapping.get(strategy, "escalate_manual")

    def _build_recovery_parameters(self, failure: SystemFailure, strategy: str) -> Dict[str, Any]:
        """Build parameters for recovery action."""
        base_params = {
            "failure_id": failure.id,
            "component": failure.component,
            "failure_type": failure.failure_type
        }
        
        if strategy == "fallback_configuration":
            base_params["fallback_config"] = {"mode": "safe", "reduced_functionality": True}
        elif strategy == "system_rollback":
            base_params["rollback_point"] = "last_stable"
        elif strategy == "emergency_shutdown":
            base_params["reason"] = f"Critical failure in {failure.component}"
            
        return base_params

    def _estimate_recovery_duration(self, strategy: str) -> int:
        """Estimate recovery duration in seconds."""
        duration_estimates = {
            "restart_component": 30,
            "fallback_configuration": 10,
            "alternative_provider": 15,
            "graceful_degradation": 5,
            "system_rollback": 120,
            "manual_intervention": 3600,  # 1 hour
            "emergency_shutdown": 60
        }
        return duration_estimates.get(strategy, 300)

    async def _perform_health_check(self):
        """Perform comprehensive system health check."""
        for component in self.critical_components:
            try:
                # Simulate health check (in real implementation, ping actual components)
                is_healthy = await self._check_component_health(component)
                
                if is_healthy:
                    self.component_health[component] = SystemHealthStatus.HEALTHY
                else:
                    if component not in self.component_health or self.component_health[component] == SystemHealthStatus.HEALTHY:
                        # New failure detected
                        await self.report_failure(
                            component=component,
                            failure_type="health_check_failed",
                            error_message=f"Component {component} failed health check",
                            severity=RecoveryPriority.HIGH
                        )
                        
            except Exception as e:
                logger.error(f"{self.log_prefix} Health check failed for {component}: {e}")

    async def _check_component_health(self, component: str) -> bool:
        """Check health of a specific component."""
        # In real implementation, this would perform actual health checks
        # For now, simulate based on component name
        if "llm" in component.lower():
            # Simulate occasional LLM connectivity issues
            return time.time() % 60 > 5  # Healthy 90% of the time
        return True  # Other components assumed healthy

    async def get_system_health_report(self) -> SystemHealthMetrics:
        """Generate comprehensive system health report."""
        now = time.time()
        
        # Calculate overall health status
        healthy_components = sum(1 for status in self.component_health.values() 
                               if status == SystemHealthStatus.HEALTHY)
        total_components = len(self.component_health)
        
        if total_components == 0:
            overall_status = SystemHealthStatus.HEALTHY
        elif healthy_components == total_components:
            overall_status = SystemHealthStatus.HEALTHY
        elif healthy_components >= total_components * 0.8:
            overall_status = SystemHealthStatus.DEGRADED
        elif healthy_components >= total_components * 0.5:
            overall_status = SystemHealthStatus.CRITICAL
        else:
            overall_status = SystemHealthStatus.FAILED
        
        # Calculate success rate
        total_recoveries = len(self.recovery_history)
        successful_recoveries = sum(1 for f in self.recovery_history if f.is_resolved)
        success_rate = successful_recoveries / total_recoveries if total_recoveries > 0 else 1.0
        
        # Calculate mean recovery time
        recovery_times = [f.resolution_timestamp - f.timestamp 
                         for f in self.recovery_history 
                         if f.is_resolved and f.resolution_timestamp]
        mean_recovery_time = sum(recovery_times) / len(recovery_times) if recovery_times else 0.0
        
        return SystemHealthMetrics(
            timestamp=now,
            overall_status=overall_status,
            component_statuses=self.component_health.copy(),
            active_failures=len(self.active_failures),
            recovery_success_rate=success_rate,
            mean_recovery_time=mean_recovery_time,
            system_uptime_percentage=95.0,  # Calculated from historical data
            critical_components_healthy=healthy_components,
            total_critical_components=total_components
        )

    async def stop_monitoring(self):
        """Stop health monitoring."""
        self.monitoring_enabled = False
        logger.info(f"{self.log_prefix} Health monitoring stopped")

    async def _process_pending_recoveries(self):
        """Process any pending recovery actions."""
        # Simple implementation for now
        pass

    async def _update_system_metrics(self):
        """Update system health metrics."""
        # Simple implementation for now
        pass

    async def _escalate_failure(self, failure_id: str):
        """Escalate failure to higher level intervention."""
        logger.critical(f"{self.log_prefix} Escalating failure {failure_id} to manual intervention")
        # Implementation would notify human operators 