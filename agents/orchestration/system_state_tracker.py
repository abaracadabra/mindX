# mindx/orchestration/system_state_tracker.py
"""
System State Tracker: Comprehensive system state tracking for self-awareness and self-improvement.

This module tracks system state across startup, replication, and shutdown cycles,
including resource metrics, performance data, improvement history, and rollback capabilities.
"""

import asyncio
import json
import time
import shutil
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger
from agents.memory_agent import MemoryAgent
from agents.monitoring.resource_monitor import ResourceMonitor, get_resource_monitor_async
from agents.monitoring.performance_monitor import PerformanceMonitor

logger = get_logger(__name__)


class SystemEventType(Enum):
    """Types of system events tracked"""
    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    REPLICATION = "replication"
    IMPROVEMENT = "improvement"
    ROLLBACK = "rollback"
    ERROR = "error"


@dataclass
class ResourceSnapshot:
    """Snapshot of resource metrics at a point in time"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_total: int
    disk_usage: Dict[str, float]
    network_bytes_sent: int
    network_bytes_recv: int
    process_count: int
    load_average: Tuple[float, float, float]


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time"""
    timestamp: float
    total_calls: int
    successful_calls: int
    failed_calls: int
    avg_latency_ms: float
    total_cost: float
    total_prompt_tokens: int
    total_completion_tokens: int
    error_rate: float
    top_operations: List[Dict[str, Any]]


@dataclass
class SystemState:
    """Complete system state at a point in time"""
    event_type: str
    timestamp: float
    event_id: str
    resource_snapshot: Optional[ResourceSnapshot] = None
    performance_snapshot: Optional[PerformanceSnapshot] = None
    agents_registered: List[str] = field(default_factory=list)
    agents_active: List[str] = field(default_factory=list)
    tools_registered: List[str] = field(default_factory=list)
    system_version: Optional[str] = None
    improvement_count: int = 0
    rollback_count: int = 0
    last_improvement: Optional[Dict[str, Any]] = None
    last_rollback: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImprovementRecord:
    """Record of a system improvement"""
    improvement_id: str
    timestamp: float
    improvement_type: str
    description: str
    changes_made: List[Dict[str, Any]]
    before_state: Dict[str, Any]
    after_state: Dict[str, Any]
    success: bool
    metrics_improvement: Dict[str, float]
    rollback_available: bool
    rollback_path: Optional[str] = None


@dataclass
class RollbackPoint:
    """Rollback point for system recovery"""
    rollback_id: str
    timestamp: float
    system_state: SystemState
    backup_path: str
    improvement_id: Optional[str] = None
    reason: Optional[str] = None


class SystemStateTracker:
    """
    Tracks comprehensive system state for self-awareness and self-improvement.
    """
    
    def __init__(
        self,
        memory_agent: Optional[MemoryAgent] = None,
        config: Optional[Config] = None,
        test_mode: bool = False
    ):
        self.memory_agent = memory_agent
        self.config = config or Config(test_mode=test_mode)
        self.test_mode = test_mode
        self.log_prefix = "SystemStateTracker:"
        
        # Data storage paths
        self.data_dir = PROJECT_ROOT / "data" / "system_state"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.states_dir = self.data_dir / "states"
        self.states_dir.mkdir(parents=True, exist_ok=True)
        
        self.improvements_dir = self.data_dir / "improvements"
        self.improvements_dir.mkdir(parents=True, exist_ok=True)
        
        self.rollbacks_dir = self.data_dir / "rollbacks"
        self.rollbacks_dir.mkdir(parents=True, exist_ok=True)
        
        self.history_file = self.data_dir / "history.json"
        self.improvements_file = self.data_dir / "improvements.json"
        self.rollbacks_file = self.data_dir / "rollbacks.json"
        
        # Load history
        self.history: List[Dict[str, Any]] = self._load_json(self.history_file, [])
        self.improvements: List[Dict[str, Any]] = self._load_json(self.improvements_file, [])
        self.rollbacks: List[Dict[str, Any]] = self._load_json(self.rollbacks_file, [])
        
        # Current state
        self.current_state: Optional[SystemState] = None
        self.improvement_count = len(self.improvements)
        self.rollback_count = len(self.rollbacks)
    
    def _load_json(self, file_path: Path, default: Any) -> Any:
        """Load JSON file, return default if not found or error"""
        if file_path.exists():
            try:
                with file_path.open("r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"{self.log_prefix} Error loading {file_path}: {e}")
        return default
    
    def _save_json(self, file_path: Path, data: Any):
        """Save JSON file"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"{self.log_prefix} Error saving {file_path}: {e}", exc_info=True)
    
    async def capture_system_state(
        self,
        event_type: SystemEventType,
        coordinator_agent: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SystemState:
        """
        Capture complete system state at a point in time.
        
        Args:
            event_type: Type of system event
            coordinator_agent: CoordinatorAgent instance for agent/tool info
            metadata: Additional metadata
        
        Returns:
            SystemState object
        """
        event_id = f"{event_type.value}_{int(time.time())}"
        timestamp = time.time()
        
        logger.info(f"{self.log_prefix} Capturing system state: {event_type.value} (ID: {event_id})")
        
        # Capture resource snapshot
        resource_snapshot = await self._capture_resource_snapshot()
        
        # Capture performance snapshot
        performance_snapshot = await self._capture_performance_snapshot()
        
        # Get agent/tool information
        agents_registered = []
        agents_active = []
        tools_registered = []
        
        if coordinator_agent:
            try:
                registry = getattr(coordinator_agent, 'agent_registry', {})
                agents_registered = list(registry.keys())
                agents_active = [
                    agent_id for agent_id, data in registry.items()
                    if data.get("status") == "active"
                ]
            except Exception as e:
                logger.warning(f"{self.log_prefix} Error getting agent registry: {e}")
            
            try:
                tool_registry = getattr(coordinator_agent, 'tool_registry', {})
                tools_registered = list(tool_registry.keys())
            except Exception as e:
                logger.warning(f"{self.log_prefix} Error getting tool registry: {e}")
        
        # Create system state
        system_state = SystemState(
            event_type=event_type.value,
            timestamp=timestamp,
            event_id=event_id,
            resource_snapshot=resource_snapshot,
            performance_snapshot=performance_snapshot,
            agents_registered=agents_registered,
            agents_active=agents_active,
            tools_registered=tools_registered,
            improvement_count=self.improvement_count,
            rollback_count=self.rollback_count,
            last_improvement=self.improvements[-1] if self.improvements else None,
            last_rollback=self.rollbacks[-1] if self.rollbacks else None,
            metadata=metadata or {}
        )
        
        # Save state
        state_file = self.states_dir / f"{event_id}.json"
        self._save_json(state_file, asdict(system_state))
        
        # Add to history
        self.history.append({
            "event_id": event_id,
            "event_type": event_type.value,
            "timestamp": timestamp,
            "state_file": str(state_file.relative_to(self.data_dir))
        })
        self._save_json(self.history_file, self.history)
        
        self.current_state = system_state
        
        # Log to memory agent
        if self.memory_agent:
            await self.memory_agent.log_process(
                f"system_state_{event_type.value}",
                asdict(system_state),
                {"tracker": "system_state_tracker"}
            )
        
        logger.info(f"{self.log_prefix} System state captured: {event_id}")
        return system_state
    
    async def _capture_resource_snapshot(self) -> Optional[ResourceSnapshot]:
        """Capture resource metrics snapshot"""
        try:
            resource_monitor = await get_resource_monitor_async()
            if resource_monitor:
                metrics = await resource_monitor.get_current_metrics()
                if metrics:
                    return ResourceSnapshot(
                        timestamp=time.time(),
                        cpu_percent=metrics.cpu_percent,
                        memory_percent=metrics.memory_percent,
                        memory_used=metrics.memory_used,
                        memory_total=metrics.memory_total,
                        disk_usage={},
                        network_bytes_sent=metrics.network_bytes_sent,
                        network_bytes_recv=metrics.network_bytes_recv,
                        process_count=metrics.process_count,
                        load_average=metrics.load_average
                    )
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error capturing resource snapshot: {e}")
        return None
    
    async def _capture_performance_snapshot(self) -> Optional[PerformanceSnapshot]:
        """Capture performance metrics snapshot"""
        try:
            performance_monitor = PerformanceMonitor(config_override=self.config)
            metrics = performance_monitor.metrics
            
            if metrics:
                # Calculate aggregate metrics
                total_calls = sum(m.get("total_calls", 0) for m in metrics.values())
                successful_calls = sum(m.get("successful_calls", 0) for m in metrics.values())
                failed_calls = sum(m.get("failed_calls", 0) for m in metrics.values())
                total_latency = sum(m.get("total_latency_ms", 0) for m in metrics.values())
                total_cost = sum(m.get("total_cost", 0.0) for m in metrics.values())
                total_prompt_tokens = sum(m.get("total_prompt_tokens", 0) for m in metrics.values())
                total_completion_tokens = sum(m.get("total_completion_tokens", 0) for m in metrics.values())
                
                avg_latency = total_latency / total_calls if total_calls > 0 else 0.0
                error_rate = failed_calls / total_calls if total_calls > 0 else 0.0
                
                # Get top operations
                top_operations = sorted(
                    [
                        {
                            "operation": op,
                            "calls": data.get("total_calls", 0),
                            "success_rate": data.get("successful_calls", 0) / data.get("total_calls", 1),
                            "avg_latency": data.get("total_latency_ms", 0) / data.get("total_calls", 1) if data.get("total_calls", 0) > 0 else 0
                        }
                        for op, data in metrics.items()
                    ],
                    key=lambda x: x["calls"],
                    reverse=True
                )[:10]
                
                return PerformanceSnapshot(
                    timestamp=time.time(),
                    total_calls=total_calls,
                    successful_calls=successful_calls,
                    failed_calls=failed_calls,
                    avg_latency_ms=avg_latency,
                    total_cost=total_cost,
                    total_prompt_tokens=total_prompt_tokens,
                    total_completion_tokens=total_completion_tokens,
                    error_rate=error_rate,
                    top_operations=top_operations
                )
        except Exception as e:
            logger.warning(f"{self.log_prefix} Error capturing performance snapshot: {e}")
        return None
    
    async def record_improvement(
        self,
        improvement_type: str,
        description: str,
        changes_made: List[Dict[str, Any]],
        before_state: SystemState,
        after_state: SystemState,
        success: bool,
        metrics_improvement: Dict[str, float],
        create_rollback: bool = True
    ) -> ImprovementRecord:
        """
        Record a system improvement.
        
        Args:
            improvement_type: Type of improvement
            description: Description of improvement
            changes_made: List of changes made
            before_state: System state before improvement
            after_state: System state after improvement
            success: Whether improvement was successful
            metrics_improvement: Metrics showing improvement
            create_rollback: Whether to create rollback point
        
        Returns:
            ImprovementRecord
        """
        improvement_id = f"improvement_{int(time.time())}"
        timestamp = time.time()
        
        logger.info(f"{self.log_prefix} Recording improvement: {improvement_id}")
        
        rollback_path = None
        if create_rollback:
            rollback_point = await self.create_rollback_point(
                reason=f"Before improvement: {description}",
                improvement_id=improvement_id
            )
            rollback_path = rollback_point.backup_path
        
        improvement = ImprovementRecord(
            improvement_id=improvement_id,
            timestamp=timestamp,
            improvement_type=improvement_type,
            description=description,
            changes_made=changes_made,
            before_state=asdict(before_state),
            after_state=asdict(after_state),
            success=success,
            metrics_improvement=metrics_improvement,
            rollback_available=create_rollback,
            rollback_path=rollback_path
        )
        
        # Save improvement
        improvement_file = self.improvements_dir / f"{improvement_id}.json"
        self._save_json(improvement_file, asdict(improvement))
        
        # Add to improvements list
        self.improvements.append({
            "improvement_id": improvement_id,
            "timestamp": timestamp,
            "improvement_type": improvement_type,
            "success": success,
            "file": str(improvement_file.relative_to(self.data_dir))
        })
        self._save_json(self.improvements_file, self.improvements)
        
        self.improvement_count += 1
        
        # Log to memory agent
        if self.memory_agent:
            await self.memory_agent.log_process(
                "system_improvement",
                asdict(improvement),
                {"tracker": "system_state_tracker"}
            )
        
        logger.info(f"{self.log_prefix} Improvement recorded: {improvement_id}")
        return improvement
    
    async def create_rollback_point(
        self,
        reason: Optional[str] = None,
        improvement_id: Optional[str] = None
    ) -> RollbackPoint:
        """
        Create a rollback point for system recovery.
        
        Args:
            reason: Reason for rollback point
            improvement_id: Associated improvement ID
        
        Returns:
            RollbackPoint
        """
        rollback_id = f"rollback_{int(time.time())}"
        timestamp = time.time()
        
        logger.info(f"{self.log_prefix} Creating rollback point: {rollback_id}")
        
        # Capture current state
        system_state = self.current_state
        if not system_state:
            # Create a minimal state if none exists
            system_state = SystemState(
                event_type="rollback",
                timestamp=timestamp,
                event_id=rollback_id
            )
        
        # Create backup directory
        backup_dir = self.rollbacks_dir / rollback_id
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy critical system files
        critical_paths = [
            PROJECT_ROOT / "data" / "config",
            PROJECT_ROOT / "data" / "memory",
            PROJECT_ROOT / "data" / "monitoring"
        ]
        
        for path in critical_paths:
            if path.exists():
                dest = backup_dir / path.name
                try:
                    if path.is_dir():
                        shutil.copytree(path, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(path, dest)
                except Exception as e:
                    logger.warning(f"{self.log_prefix} Error backing up {path}: {e}")
        
        # Save system state
        state_file = backup_dir / "system_state.json"
        self._save_json(state_file, asdict(system_state))
        
        rollback_point = RollbackPoint(
            rollback_id=rollback_id,
            timestamp=timestamp,
            system_state=system_state,
            backup_path=str(backup_dir),
            improvement_id=improvement_id,
            reason=reason
        )
        
        # Save rollback record
        rollback_file = self.rollbacks_dir / f"{rollback_id}.json"
        self._save_json(rollback_file, asdict(rollback_point))
        
        # Add to rollbacks list
        self.rollbacks.append({
            "rollback_id": rollback_id,
            "timestamp": timestamp,
            "reason": reason,
            "backup_path": str(backup_dir),
            "file": str(rollback_file.relative_to(self.data_dir))
        })
        self._save_json(self.rollbacks_file, self.rollbacks)
        
        self.rollback_count += 1
        
        # Log to memory agent
        if self.memory_agent:
            await self.memory_agent.log_process(
                "rollback_point_created",
                asdict(rollback_point),
                {"tracker": "system_state_tracker"}
            )
        
        logger.info(f"{self.log_prefix} Rollback point created: {rollback_id}")
        return rollback_point
    
    async def get_latest_state(self) -> Optional[SystemState]:
        """Get the latest system state"""
        if self.current_state:
            return self.current_state
        
        # Load from history
        if self.history:
            latest = self.history[-1]
            state_file = self.data_dir / latest["state_file"]
            if state_file.exists():
                try:
                    with state_file.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Reconstruct SystemState from dict
                        return SystemState(**data)
                except Exception as e:
                    logger.error(f"{self.log_prefix} Error loading latest state: {e}")
        
        return None
    
    async def get_improvement_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get improvement history"""
        return self.improvements[-limit:] if limit else self.improvements
    
    async def get_rollback_points(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get rollback points"""
        return self.rollbacks[-limit:] if limit else self.rollbacks
