# monitoring/monitoring_integration.py
"""
Monitoring Integration Layer

This module provides integration between the legacy monitoring components
and the new enhanced monitoring system, ensuring backward compatibility
while adding new capabilities.
"""
import asyncio
import time
from typing import Dict, Any, Optional
from pathlib import Path

from utils.config import Config
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent

# Import existing monitoring components
from .resource_monitor import ResourceMonitor
from .performance_monitor import PerformanceMonitor
from .enhanced_performance_monitor import EnhancedPerformanceMonitor
from .enhanced_monitoring_system import EnhancedMonitoringSystem, get_enhanced_monitoring_system

logger = get_logger(__name__)

class IntegratedMonitoringManager:
    """
    Unified monitoring manager that integrates all monitoring components
    with enhanced logging to /data/monitoring/logs via MemoryAgent.
    """
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.memory_agent = MemoryAgent(config=self.config)
        
        # Initialize monitoring components
        self.resource_monitor = None
        self.performance_monitor = None
        self.enhanced_performance_monitor = None
        self.enhanced_monitoring_system = None
        
        # Monitoring state
        self.monitoring_active = False
        self.integration_task = None
        
        logger.info("Integrated Monitoring Manager initialized")
    
    async def initialize_monitoring(self):
        """Initialize all monitoring components."""
        try:
            # Initialize resource monitor
            self.resource_monitor = ResourceMonitor(
                memory_agent=self.memory_agent,
                config_override=self.config
            )
            
            # Initialize performance monitors
            self.performance_monitor = PerformanceMonitor(config_override=self.config)
            self.enhanced_performance_monitor = EnhancedPerformanceMonitor(
                memory_agent=self.memory_agent,
                config_override=self.config
            )
            
            # Initialize enhanced monitoring system
            self.enhanced_monitoring_system = await get_enhanced_monitoring_system(
                memory_agent=self.memory_agent,
                config=self.config
            )
            
            # Setup integration hooks
            await self._setup_integration_hooks()
            
            logger.info("All monitoring components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize monitoring components: {e}", exc_info=True)
            raise
    
    async def _setup_integration_hooks(self):
        """Setup hooks to forward data between monitoring components."""
        
        # Hook resource monitor alerts to enhanced system
        async def resource_alert_handler(monitor, resource_type, value, path=None):
            await self.enhanced_monitoring_system.log_llm_performance(
                model_name="system_resource",
                task_type=f"resource_{resource_type.value}",
                agent_id="resource_monitor",
                latency_ms=0,
                success=value < 80,  # Consider values over 80% as concerning
                metadata={
                    "resource_type": resource_type.value,
                    "value": value,
                    "path": path,
                    "alert_type": "resource_threshold"
                }
            )
        
        # Register alert callbacks
        if hasattr(self.resource_monitor, 'register_alert_callback'):
            self.resource_monitor.register_alert_callback(resource_alert_handler)
    
    async def start_monitoring(self):
        """Start all monitoring components."""
        if self.monitoring_active:
            logger.warning("Monitoring is already active")
            return
        
        if not self.enhanced_monitoring_system:
            await self.initialize_monitoring()
        
        try:
            # Start resource monitoring
            if self.resource_monitor:
                self.resource_monitor.start_monitoring()
            
            # Start performance monitoring
            if self.enhanced_performance_monitor and hasattr(self.enhanced_performance_monitor, 'start_auto_analysis'):
                self.enhanced_performance_monitor.start_auto_analysis()
            
            # Start enhanced monitoring system
            await self.enhanced_monitoring_system.start_monitoring()
            
            # Start integration monitoring loop
            self.monitoring_active = True
            self.integration_task = asyncio.create_task(self._integration_monitoring_loop())
            
            logger.info("Integrated monitoring system started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring: {e}", exc_info=True)
            raise
    
    async def stop_monitoring(self):
        """Stop all monitoring components."""
        if not self.monitoring_active:
            return
        
        try:
            self.monitoring_active = False
            
            # Stop integration task
            if self.integration_task:
                self.integration_task.cancel()
                try:
                    await self.integration_task
                except asyncio.CancelledError:
                    pass
            
            # Stop resource monitor
            if self.resource_monitor:
                self.resource_monitor.stop_monitoring()
            
            # Stop performance monitors
            if self.enhanced_performance_monitor and hasattr(self.enhanced_performance_monitor, 'stop_auto_analysis'):
                self.enhanced_performance_monitor.stop_auto_analysis()
            
            # Stop enhanced monitoring system
            if self.enhanced_monitoring_system:
                await self.enhanced_monitoring_system.stop_monitoring()
            
            logger.info("Integrated monitoring system stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping monitoring: {e}", exc_info=True)
    
    async def _integration_monitoring_loop(self):
        """Integration monitoring loop that syncs data between components."""
        try:
            while self.monitoring_active:
                start_time = time.time()
                
                # Sync resource data to enhanced system
                await self._sync_resource_data()
                
                # Sync performance data
                await self._sync_performance_data()
                
                # Generate periodic reports
                if int(start_time) % 1800 == 0:  # Every 30 minutes
                    await self._generate_integrated_report()
                
                # Sleep for next iteration
                elapsed = time.time() - start_time
                sleep_time = max(1.0, 60.0 - elapsed)  # Run every minute
                await asyncio.sleep(sleep_time)
                
        except asyncio.CancelledError:
            logger.info("Integration monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Error in integration monitoring loop: {e}", exc_info=True)
    
    async def _sync_resource_data(self):
        """Sync resource data from resource monitor to enhanced system."""
        if not self.resource_monitor or not self.enhanced_monitoring_system:
            return
        
        try:
            # Get current resource usage
            resource_usage = self.resource_monitor.get_resource_usage()
            
            # Log to enhanced monitoring system as agent performance
            await self.enhanced_monitoring_system.log_agent_performance(
                agent_id="resource_monitor",
                action_type="resource_collection",
                execution_time_ms=10,  # Approximate collection time
                success=True,
                metadata={
                    "cpu_percent": resource_usage.get("cpu", 0),
                    "memory_percent": resource_usage.get("memory", 0),
                    "disk_usage": resource_usage.get("disk", {}),
                    "sync_type": "resource_data"
                }
            )
            
        except Exception as e:
            logger.error(f"Error syncing resource data: {e}", exc_info=True)
    
    async def _sync_performance_data(self):
        """Sync performance data between monitoring components."""
        if not self.performance_monitor or not self.enhanced_monitoring_system:
            return
        
        try:
            # Get summary metrics from performance monitor
            summary_metrics = self.performance_monitor.get_summary_metrics()
            
            # Log aggregated performance data
            await self.enhanced_monitoring_system.log_agent_performance(
                agent_id="performance_monitor",
                action_type="metrics_aggregation",
                execution_time_ms=5,
                success=True,
                metadata={
                    "total_calls": summary_metrics.get("total_calls", 0),
                    "overall_success_rate": summary_metrics.get("overall_success_rate", 1.0),
                    "avg_latency_ms": summary_metrics.get("avg_latency_overall_ms", 0),
                    "sync_type": "performance_data"
                }
            )
            
        except Exception as e:
            logger.error(f"Error syncing performance data: {e}", exc_info=True)
    
    async def _generate_integrated_report(self):
        """Generate comprehensive integrated monitoring report."""
        try:
            # Generate report from enhanced monitoring system
            report = await self.enhanced_monitoring_system.generate_monitoring_report(hours_back=1)
            
            # Add additional data from other monitors
            if self.resource_monitor:
                report["resource_limits"] = self.resource_monitor.get_resource_limits()
            
            if self.performance_monitor:
                report["legacy_performance_metrics"] = self.performance_monitor.get_summary_metrics()
            
            # Export report to file
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            report_path = Path("data/monitoring/logs") / f"integrated_report_{timestamp}.json"
            
            await self.enhanced_monitoring_system.export_metrics_to_file(report_path)
            
            # Log report generation
            await self.enhanced_monitoring_system.log_agent_performance(
                agent_id="integrated_monitoring_manager",
                action_type="report_generation",
                execution_time_ms=100,
                success=True,
                metadata={
                    "report_path": str(report_path),
                    "report_size_kb": report_path.stat().st_size / 1024 if report_path.exists() else 0,
                    "hours_analyzed": 1
                }
            )
            
            logger.info(f"Integrated monitoring report generated: {report_path}")
            
        except Exception as e:
            logger.error(f"Error generating integrated report: {e}", exc_info=True)
    
    # Convenience methods for external use
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
        """Forward LLM call logging to enhanced monitoring system."""
        if self.enhanced_monitoring_system:
            await self.enhanced_monitoring_system.log_llm_performance(
                model_name=model_name,
                task_type=task_type,
                agent_id=initiating_agent_id,  # Map initiating_agent_id to agent_id
                latency_ms=latency_ms,
                success=success,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                error_type=error_type,
                metadata=metadata
            )
        
        # Also log to legacy performance monitor if available
        if self.performance_monitor:
            self.performance_monitor.log_llm_call(
                model_name=model_name,
                task_type=task_type,
                initiating_agent_id=initiating_agent_id,
                latency_ms=latency_ms,
                success=success,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost=cost,
                error_type=error_type,
                metadata=metadata
            )
    
    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics from all monitoring components."""
        metrics = {}
        
        if self.enhanced_monitoring_system:
            metrics["enhanced_system"] = self.enhanced_monitoring_system.get_current_metrics()
        
        if self.resource_monitor:
            metrics["resource_usage"] = self.resource_monitor.get_resource_usage()
            metrics["resource_limits"] = self.resource_monitor.get_resource_limits()
        
        if self.performance_monitor:
            metrics["performance_summary"] = self.performance_monitor.get_summary_metrics()
        
        return metrics
    
    async def get_monitoring_report(self, hours_back: int = 24) -> Dict[str, Any]:
        """Get comprehensive monitoring report."""
        if self.enhanced_monitoring_system:
            return await self.enhanced_monitoring_system.generate_monitoring_report(hours_back)
        return {}


# Global instance
_integrated_monitoring_manager = None

async def get_integrated_monitoring_manager(config: Optional[Config] = None) -> IntegratedMonitoringManager:
    """Get or create the integrated monitoring manager instance."""
    global _integrated_monitoring_manager
    if _integrated_monitoring_manager is None:
        _integrated_monitoring_manager = IntegratedMonitoringManager(config)
        await _integrated_monitoring_manager.initialize_monitoring()
    return _integrated_monitoring_manager