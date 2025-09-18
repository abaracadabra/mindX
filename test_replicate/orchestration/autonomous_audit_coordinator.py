#!/usr/bin/env python3
"""
Autonomous Audit Coordinator for mindX

Integrates audit-driven campaigns with the existing autonomous improvement infrastructure.
This coordinator schedules and manages systematic audit campaigns, feeding results into
the coordinator's improvement backlog for autonomous execution.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from orchestration.coordinator_agent import CoordinatorAgent, InteractionType
from learning.strategic_evolution_agent import StrategicEvolutionAgent
from core.belief_system import BeliefSystem, BeliefSource
from agents.memory_agent import MemoryAgent
from llm.model_registry import ModelRegistry

logger = get_logger(__name__)

class AuditCampaignSchedule:
    """Represents a scheduled audit campaign."""
    
    def __init__(self, campaign_id: str, audit_scope: str, target_components: Optional[List[str]] = None,
                 interval_hours: int = 24, priority: int = 5, enabled: bool = True):
        self.campaign_id = campaign_id
        self.audit_scope = audit_scope
        self.target_components = target_components or []
        self.interval_hours = interval_hours
        self.priority = priority
        self.enabled = enabled
        self.last_execution_time: Optional[float] = None
        self.next_execution_time: Optional[float] = None
        self.execution_count = 0
        self.success_count = 0
        self.failure_count = 0
        
    def is_due(self) -> bool:
        """Check if this campaign is due for execution."""
        if not self.enabled:
            return False
            
        current_time = time.time()
        
        if self.next_execution_time is None:
            # First time - schedule immediately
            return True
            
        return current_time >= self.next_execution_time
    
    def schedule_next_execution(self):
        """Schedule the next execution time."""
        self.next_execution_time = time.time() + (self.interval_hours * 3600)
    
    def record_execution(self, success: bool):
        """Record an execution attempt."""
        self.last_execution_time = time.time()
        self.execution_count += 1
        
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
            
        self.schedule_next_execution()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "campaign_id": self.campaign_id,
            "audit_scope": self.audit_scope,
            "target_components": self.target_components,
            "interval_hours": self.interval_hours,
            "priority": self.priority,
            "enabled": self.enabled,
            "last_execution_time": self.last_execution_time,
            "next_execution_time": self.next_execution_time,
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditCampaignSchedule':
        """Create from dictionary."""
        schedule = cls(
            campaign_id=data["campaign_id"],
            audit_scope=data["audit_scope"],
            target_components=data.get("target_components", []),
            interval_hours=data.get("interval_hours", 24),
            priority=data.get("priority", 5),
            enabled=data.get("enabled", True)
        )
        
        schedule.last_execution_time = data.get("last_execution_time")
        schedule.next_execution_time = data.get("next_execution_time")
        schedule.execution_count = data.get("execution_count", 0)
        schedule.success_count = data.get("success_count", 0)
        schedule.failure_count = data.get("failure_count", 0)
        
        return schedule

class AutonomousAuditCoordinator:
    """
    Manages autonomous audit campaigns integrated with the coordinator's improvement system.
    
    This coordinator:
    1. Schedules periodic audit campaigns based on system needs
    2. Executes audit-driven campaigns using StrategicEvolutionAgent
    3. Feeds audit findings into CoordinatorAgent's improvement backlog
    4. Adapts audit frequency based on system health and performance
    5. Provides comprehensive audit campaign management and reporting
    """
    
    def __init__(self, 
                 coordinator_agent: CoordinatorAgent,
                 memory_agent: MemoryAgent,
                 model_registry: ModelRegistry,
                 belief_system: BeliefSystem,
                 config: Optional[Config] = None):
        self.coordinator_agent = coordinator_agent
        self.memory_agent = memory_agent
        self.model_registry = model_registry
        self.belief_system = belief_system
        self.config = config or Config()
        
        self.agent_id = "autonomous_audit_coordinator"
        self.log_prefix = f"[{self.agent_id}]"
        
        # Initialize audit scheduling
        self.audit_schedules: Dict[str, AuditCampaignSchedule] = {}
        self.active_campaigns: Dict[str, str] = {}  # campaign_id -> sea_campaign_id
        
        # Initialize StrategicEvolutionAgent for audit campaigns
        self.sea_agent: Optional[StrategicEvolutionAgent] = None
        
        # Autonomous loop control
        self.autonomous_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Performance tracking
        self.campaign_metrics = {
            "total_campaigns": 0,
            "successful_campaigns": 0,
            "failed_campaigns": 0,
            "total_findings": 0,
            "total_improvements": 0,
            "last_campaign_time": None
        }
        
        self._load_audit_schedules()
        self._setup_default_schedules()
        
        logger.info(f"{self.log_prefix} Initialized with {len(self.audit_schedules)} audit schedules")
    
    async def async_init(self):
        """Asynchronously initialize components."""
        try:
            # Initialize StrategicEvolutionAgent
            self.sea_agent = StrategicEvolutionAgent(
                agent_id=f"{self.agent_id}_sea",
                belief_system=self.belief_system,
                coordinator_agent=self.coordinator_agent,
                model_registry=self.model_registry,
                memory_agent=self.memory_agent,
                config_override=self.config
            )
            await self.sea_agent._async_init()
            
            logger.info(f"{self.log_prefix} StrategicEvolutionAgent initialized successfully")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to initialize StrategicEvolutionAgent: {e}")
            raise
    
    def _setup_default_schedules(self):
        """Setup default audit campaign schedules."""
        
        default_schedules = [
            # Daily security audit
            AuditCampaignSchedule(
                campaign_id="daily_security_audit",
                audit_scope="security",
                target_components=["core", "llm", "api", "tools"],
                interval_hours=24,
                priority=8,
                enabled=True
            ),
            
            # Weekly comprehensive system audit
            AuditCampaignSchedule(
                campaign_id="weekly_system_audit",
                audit_scope="system",
                target_components=None,  # Full system
                interval_hours=168,  # 7 days
                priority=6,
                enabled=True
            ),
            
            # Bi-daily performance audit
            AuditCampaignSchedule(
                campaign_id="performance_audit",
                audit_scope="performance",
                target_components=["monitoring", "llm", "core"],
                interval_hours=48,  # 2 days
                priority=7,
                enabled=True
            ),
            
            # Daily code quality audit (focused)
            AuditCampaignSchedule(
                campaign_id="code_quality_audit",
                audit_scope="code_quality",
                target_components=["learning", "orchestration", "agents"],
                interval_hours=36,  # 1.5 days
                priority=5,
                enabled=True
            )
        ]
        
        # Add default schedules if they don't exist
        for schedule in default_schedules:
            if schedule.campaign_id not in self.audit_schedules:
                self.audit_schedules[schedule.campaign_id] = schedule
                logger.info(f"{self.log_prefix} Added default schedule: {schedule.campaign_id}")
        
        self._save_audit_schedules()
    
    def _load_audit_schedules(self):
        """Load audit schedules from persistent storage."""
        
        schedules_file = self.memory_agent.get_agent_data_directory(self.agent_id) / "audit_schedules.json"
        
        if schedules_file.exists():
            try:
                with open(schedules_file, 'r') as f:
                    schedules_data = json.load(f)
                
                for schedule_data in schedules_data:
                    schedule = AuditCampaignSchedule.from_dict(schedule_data)
                    self.audit_schedules[schedule.campaign_id] = schedule
                    
                logger.info(f"{self.log_prefix} Loaded {len(self.audit_schedules)} audit schedules")
                
            except Exception as e:
                logger.error(f"{self.log_prefix} Failed to load audit schedules: {e}")
                self.audit_schedules = {}
    
    def _save_audit_schedules(self):
        """Save audit schedules to persistent storage."""
        
        schedules_file = self.memory_agent.get_agent_data_directory(self.agent_id) / "audit_schedules.json"
        schedules_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            schedules_data = [schedule.to_dict() for schedule in self.audit_schedules.values()]
            
            with open(schedules_file, 'w') as f:
                json.dump(schedules_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to save audit schedules: {e}")
    
    def start_autonomous_audit_loop(self, check_interval_seconds: int = 300):
        """Start the autonomous audit campaign loop."""
        
        if self.autonomous_task and not self.autonomous_task.done():
            logger.warning(f"{self.log_prefix} Autonomous audit loop already running")
            return
        
        self.is_running = True
        self.autonomous_task = asyncio.create_task(
            self._autonomous_audit_worker(check_interval_seconds)
        )
        
        logger.info(f"{self.log_prefix} Autonomous audit loop started (check interval: {check_interval_seconds}s)")
    
    def stop_autonomous_audit_loop(self):
        """Stop the autonomous audit campaign loop."""
        
        self.is_running = False
        
        if self.autonomous_task and not self.autonomous_task.done():
            self.autonomous_task.cancel()
            logger.info(f"{self.log_prefix} Autonomous audit loop stopping...")
        else:
            logger.info(f"{self.log_prefix} Autonomous audit loop not running")
    
    async def _autonomous_audit_worker(self, check_interval_seconds: int):
        """Main autonomous audit worker loop."""
        
        logger.info(f"{self.log_prefix} Autonomous audit worker started")
        
        while self.is_running:
            try:
                await asyncio.sleep(check_interval_seconds)
                
                if not self.is_running:
                    break
                
                logger.debug(f"{self.log_prefix} Checking for due audit campaigns...")
                
                # Find due campaigns
                due_campaigns = []
                for schedule in self.audit_schedules.values():
                    if schedule.is_due():
                        due_campaigns.append(schedule)
                
                if not due_campaigns:
                    logger.debug(f"{self.log_prefix} No audit campaigns due")
                    continue
                
                # Sort by priority (higher priority first)
                due_campaigns.sort(key=lambda s: s.priority, reverse=True)
                
                logger.info(f"{self.log_prefix} Found {len(due_campaigns)} due audit campaigns")
                
                # Execute campaigns (one at a time to avoid resource conflicts)
                for schedule in due_campaigns:
                    if not self.is_running:
                        break
                    
                    # Check system resources before starting campaign
                    if await self._should_defer_campaign():
                        logger.info(f"{self.log_prefix} Deferring campaigns due to high system load")
                        break
                    
                    await self._execute_scheduled_campaign(schedule)
                    
                    # Brief pause between campaigns
                    await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info(f"{self.log_prefix} Autonomous audit worker cancelled")
                break
            except Exception as e:
                logger.error(f"{self.log_prefix} Error in autonomous audit worker: {e}", exc_info=True)
                # Continue running despite errors
                await asyncio.sleep(check_interval_seconds)
        
        logger.info(f"{self.log_prefix} Autonomous audit worker stopped")
    
    async def _should_defer_campaign(self) -> bool:
        """Check if campaigns should be deferred due to system load."""
        
        try:
            # Check CPU usage if resource monitor is available
            if hasattr(self.coordinator_agent, 'resource_monitor') and self.coordinator_agent.resource_monitor:
                resource_usage = self.coordinator_agent.resource_monitor.get_resource_usage()
                cpu_usage = resource_usage.get("cpu_percent", 0)
                memory_usage = resource_usage.get("memory_percent", 0)
                
                cpu_threshold = self.config.get("autonomous_audit.max_cpu_before_audit", 80.0)
                memory_threshold = self.config.get("autonomous_audit.max_memory_before_audit", 85.0)
                
                if cpu_usage > cpu_threshold or memory_usage > memory_threshold:
                    logger.info(f"{self.log_prefix} High resource usage: CPU {cpu_usage}%, Memory {memory_usage}%")
                    return True
            
            # Check if coordinator has too many active improvements
            active_improvements = len([
                item for item in self.coordinator_agent.improvement_backlog 
                if item.get("status") == "IN_PROGRESS"
            ])
            
            max_concurrent = self.config.get("autonomous_audit.max_concurrent_improvements", 3)
            if active_improvements >= max_concurrent:
                logger.info(f"{self.log_prefix} Too many active improvements: {active_improvements}/{max_concurrent}")
                return True
            
            return False
            
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error checking system load: {e}")
            return False
    
    async def _execute_scheduled_campaign(self, schedule: AuditCampaignSchedule):
        """Execute a scheduled audit campaign."""
        
        campaign_start_time = time.time()
        logger.info(f"{self.log_prefix} Executing campaign: {schedule.campaign_id} (scope: {schedule.audit_scope})")
        
        try:
            if not self.sea_agent:
                logger.error(f"{self.log_prefix} StrategicEvolutionAgent not available")
                schedule.record_execution(False)
                return
            
            # Execute audit-driven campaign
            campaign_results = await self.sea_agent.run_audit_driven_campaign(
                audit_scope=schedule.audit_scope,
                target_components=schedule.target_components
            )
            
            campaign_duration = time.time() - campaign_start_time
            success = campaign_results.get("status") in ["SUCCESS", "PARTIAL_SUCCESS"]
            
            # Record execution
            schedule.record_execution(success)
            
            # Update metrics
            self.campaign_metrics["total_campaigns"] += 1
            if success:
                self.campaign_metrics["successful_campaigns"] += 1
            else:
                self.campaign_metrics["failed_campaigns"] += 1
            
            self.campaign_metrics["last_campaign_time"] = campaign_start_time
            
            # Process campaign results
            await self._process_campaign_results(schedule, campaign_results, campaign_duration)
            
            # Save updated schedules
            self._save_audit_schedules()
            
            logger.info(f"{self.log_prefix} Campaign {schedule.campaign_id} completed: {campaign_results.get('status', 'UNKNOWN')} in {campaign_duration:.1f}s")
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Campaign {schedule.campaign_id} failed: {e}", exc_info=True)
            schedule.record_execution(False)
            self.campaign_metrics["total_campaigns"] += 1
            self.campaign_metrics["failed_campaigns"] += 1
    
    async def _process_campaign_results(self, schedule: AuditCampaignSchedule, 
                                      campaign_results: Dict[str, Any], 
                                      campaign_duration: float):
        """Process campaign results and integrate with coordinator backlog."""
        
        try:
            campaign_data = campaign_results.get("campaign_data", {})
            
            # Extract audit findings
            audit_results = campaign_data.get("audit_results", {})
            findings = audit_results.get("findings", [])
            improvement_suggestions = audit_results.get("improvement_suggestions", [])
            
            # Update metrics
            self.campaign_metrics["total_findings"] += len(findings)
            
            # Create improvement backlog items for high-priority findings
            high_priority_findings = [f for f in findings if f.get("severity") == "high"]
            
            backlog_items_created = 0
            for finding in high_priority_findings:
                backlog_item = {
                    "id": str(uuid.uuid4()),
                    "target_component_path": finding.get("target", "unknown"),
                    "suggestion": f"Address {schedule.audit_scope} issue: {finding.get('description', 'Unknown issue')}",
                    "priority": 8,  # High priority for security/performance issues
                    "status": "PENDING",
                    "source": f"autonomous_audit_{schedule.campaign_id}",
                    "audit_scope": schedule.audit_scope,
                    "finding_severity": finding.get("severity", "unknown"),
                    "created_at": time.time(),
                    "campaign_id": schedule.campaign_id
                }
                
                # Add to coordinator backlog
                self.coordinator_agent.improvement_backlog.append(backlog_item)
                backlog_items_created += 1
            
            # Save updated backlog
            if backlog_items_created > 0:
                self.coordinator_agent._save_backlog()
                self.campaign_metrics["total_improvements"] += backlog_items_created
                
                logger.info(f"{self.log_prefix} Added {backlog_items_created} items to coordinator backlog from {schedule.campaign_id}")
            
            # Log campaign summary
            await self.memory_agent.log_process(
                process_name="autonomous_audit_campaign_completed",
                data={
                    "campaign_id": schedule.campaign_id,
                    "audit_scope": schedule.audit_scope,
                    "duration_seconds": campaign_duration,
                    "status": campaign_results.get("status"),
                    "findings_count": len(findings),
                    "high_priority_findings": len(high_priority_findings),
                    "backlog_items_created": backlog_items_created,
                    "success_rate": schedule.success_count / schedule.execution_count if schedule.execution_count > 0 else 0
                },
                metadata={"agent_id": self.agent_id}
            )
            
            # Update belief system with audit insights
            await self._update_audit_beliefs(schedule, campaign_results)
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to process campaign results: {e}", exc_info=True)
    
    async def _update_audit_beliefs(self, schedule: AuditCampaignSchedule, campaign_results: Dict[str, Any]):
        """Update belief system with audit insights."""
        
        try:
            campaign_data = campaign_results.get("campaign_data", {})
            
            # Store audit summary beliefs
            audit_summary_key = f"autonomous_audit.{schedule.campaign_id}.latest"
            audit_summary = {
                "timestamp": time.time(),
                "scope": schedule.audit_scope,
                "status": campaign_results.get("status"),
                "findings_count": len(campaign_data.get("audit_results", {}).get("findings", [])),
                "improvements_executed": campaign_data.get("improvement_results", {}).get("coordinator_tasks_created", 0),
                "validation_success": campaign_data.get("validation_results", {}).get("validation_success", False),
                "resolution_rate": campaign_data.get("validation_results", {}).get("resolution_rate", 0.0)
            }
            
            await self.belief_system.add_belief(
                key=audit_summary_key,
                value=audit_summary,
                confidence=0.9,
                source=BeliefSource.SYSTEM_ANALYSIS,
                ttl_seconds=86400 * 7  # Keep for 7 days
            )
            
            # Store system health trend beliefs
            if schedule.execution_count >= 3:
                recent_success_rate = schedule.success_count / schedule.execution_count
                health_trend_key = f"system_health.{schedule.audit_scope}.trend"
                
                health_assessment = "improving" if recent_success_rate > 0.8 else "stable" if recent_success_rate > 0.6 else "declining"
                
                await self.belief_system.add_belief(
                    key=health_trend_key,
                    value={
                        "assessment": health_assessment,
                        "success_rate": recent_success_rate,
                        "execution_count": schedule.execution_count,
                        "last_updated": time.time()
                    },
                    confidence=0.8,
                    source=BeliefSource.SELF_ANALYSIS,
                    ttl_seconds=86400 * 14  # Keep for 14 days
                )
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to update audit beliefs: {e}")
    
    async def get_audit_status(self) -> Dict[str, Any]:
        """Get comprehensive autonomous audit status."""
        
        current_time = time.time()
        
        # Calculate schedule status
        schedule_status = {}
        for campaign_id, schedule in self.audit_schedules.items():
            next_due = schedule.next_execution_time
            time_until_next = (next_due - current_time) if next_due else None
            
            schedule_status[campaign_id] = {
                "enabled": schedule.enabled,
                "scope": schedule.audit_scope,
                "priority": schedule.priority,
                "interval_hours": schedule.interval_hours,
                "execution_count": schedule.execution_count,
                "success_rate": schedule.success_count / schedule.execution_count if schedule.execution_count > 0 else 0,
                "last_execution": schedule.last_execution_time,
                "next_execution": schedule.next_execution_time,
                "time_until_next_hours": time_until_next / 3600 if time_until_next else None,
                "is_due": schedule.is_due()
            }
        
        return {
            "autonomous_loop_running": self.is_running,
            "sea_agent_available": self.sea_agent is not None,
            "total_schedules": len(self.audit_schedules),
            "enabled_schedules": len([s for s in self.audit_schedules.values() if s.enabled]),
            "due_campaigns": len([s for s in self.audit_schedules.values() if s.is_due()]),
            "campaign_metrics": self.campaign_metrics.copy(),
            "schedule_details": schedule_status,
            "active_campaigns": len(self.active_campaigns),
            "coordinator_backlog_size": len(self.coordinator_agent.improvement_backlog)
        }
    
    async def add_audit_schedule(self, campaign_id: str, audit_scope: str, 
                               target_components: Optional[List[str]] = None,
                               interval_hours: int = 24, priority: int = 5) -> bool:
        """Add a new audit campaign schedule."""
        
        try:
            if campaign_id in self.audit_schedules:
                logger.warning(f"{self.log_prefix} Schedule {campaign_id} already exists")
                return False
            
            schedule = AuditCampaignSchedule(
                campaign_id=campaign_id,
                audit_scope=audit_scope,
                target_components=target_components,
                interval_hours=interval_hours,
                priority=priority,
                enabled=True
            )
            
            self.audit_schedules[campaign_id] = schedule
            self._save_audit_schedules()
            
            logger.info(f"{self.log_prefix} Added new audit schedule: {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to add audit schedule: {e}")
            return False
    
    async def remove_audit_schedule(self, campaign_id: str) -> bool:
        """Remove an audit campaign schedule."""
        
        try:
            if campaign_id not in self.audit_schedules:
                logger.warning(f"{self.log_prefix} Schedule {campaign_id} not found")
                return False
            
            del self.audit_schedules[campaign_id]
            self._save_audit_schedules()
            
            logger.info(f"{self.log_prefix} Removed audit schedule: {campaign_id}")
            return True
            
        except Exception as e:
            logger.error(f"{self.log_prefix} Failed to remove audit schedule: {e}")
            return False
    
    async def shutdown(self):
        """Shutdown the autonomous audit coordinator."""
        
        logger.info(f"{self.log_prefix} Shutting down...")
        
        # Stop autonomous loop
        self.stop_autonomous_audit_loop()
        
        # Wait for completion
        if self.autonomous_task:
            try:
                await asyncio.wait_for(self.autonomous_task, timeout=10.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.warning(f"{self.log_prefix} Autonomous task did not shutdown cleanly")
        
        # Save state
        self._save_audit_schedules()
        
        logger.info(f"{self.log_prefix} Shutdown complete") 