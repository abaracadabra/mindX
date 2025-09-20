# monitoring/resource_monitor.py
"""
Enhanced Resource Monitor with Real System Data

This module provides comprehensive resource monitoring with actual system metrics:
- Real-time CPU, memory, and disk usage
- Process monitoring and system load
- Network I/O monitoring
- Alert system for resource thresholds
- Historical data tracking
- Integration with the frontend monitoring dashboard
"""
import os
import time
import psutil
import asyncio
import json
from typing import Dict, Any, Optional, List, Union, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
from collections import deque

# Import from sibling top-level package
try:
    from utils.config import Config, PROJECT_ROOT
    from utils.logging_config import get_logger
    from agents.memory_agent import MemoryAgent
except ImportError:
    # Fallback for when imports fail
    class Config:
        def get(self, key, default=None):
            return default
    
    PROJECT_ROOT = Path(__file__).parent.parent
    
    def get_logger(name):
        import logging
        return logging.getLogger(name)
    
    class MemoryAgent:
        pass

logger = get_logger(__name__)

class ResourceType(Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    PROCESS = "process"

@dataclass
class ResourceMetrics:
    """Comprehensive resource metrics data structure."""
    timestamp: float
    cpu_percent: float
    cpu_per_core: List[float]
    cpu_count_logical: int
    cpu_count_physical: int
    cpu_freq_current: float
    memory_percent: float
    memory_used: int
    memory_available: int
    memory_total: int
    memory_cached: int
    memory_buffers: int
    disk_usage: Dict[str, float]
    disk_io_read: int
    disk_io_write: int
    network_bytes_sent: int
    network_bytes_recv: int
    network_packets_sent: int
    network_packets_recv: int
    process_count: int
    load_average: Tuple[float, float, float]
    boot_time: float
    uptime: float

class ResourceMonitor:
    """Enhanced resource monitor with real system data collection."""
    
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ResourceMonitor, cls).__new__(cls)
        return cls._instance

    def __init__(self, memory_agent: Optional[MemoryAgent] = None, 
                 config_override: Optional[Config] = None, 
                 test_mode: bool = False):
        if hasattr(self, '_initialized') and self._initialized and not test_mode:
            return

        self.config = config_override or Config()
        self.memory_agent = memory_agent
        self.test_mode = test_mode
        
        # Resource thresholds
        self.max_cpu_percent = float(self.config.get("monitoring.resource.max_cpu_percent", 85.0))
        self.max_memory_percent = float(self.config.get("monitoring.resource.max_memory_percent", 85.0))
        self.max_disk_percent = float(self.config.get("monitoring.resource.max_disk_percent", 90.0))
        
        # Disk monitoring paths
        self.disk_paths = [
            "/",  # Root filesystem
            "/home",  # Home directory
            "/tmp",   # Temporary directory
            str(PROJECT_ROOT)  # Project directory
        ]
        
        # Historical data storage
        self.metrics_history = deque(maxlen=1000)  # Keep last 1000 measurements
        self.alerts_history = deque(maxlen=500)    # Keep last 500 alerts
        
        # Current metrics
        self.current_metrics: Optional[ResourceMetrics] = None
        self.active_alerts: Dict[str, Dict[str, Any]] = {}
        
        # Network baseline for I/O calculations
        self._network_baseline = None
        self._last_network_time = None
        
        self._initialized = True
        logger.info("Enhanced ResourceMonitor initialized")

    async def collect_metrics(self) -> ResourceMetrics:
        """Collect comprehensive real-time resource metrics."""
        try:
            now = time.time()
            
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_per_core = psutil.cpu_percent(percpu=True, interval=0.1)
            cpu_count_logical = psutil.cpu_count(logical=True) or 0
            cpu_count_physical = psutil.cpu_count(logical=False) or 0
            
            # CPU frequency
            try:
                cpu_freq = psutil.cpu_freq()
                cpu_freq_current = cpu_freq.current if cpu_freq else 0.0
            except (AttributeError, OSError):
                cpu_freq_current = 0.0
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_used = memory.used
            memory_available = memory.available
            memory_total = memory.total
            memory_cached = getattr(memory, 'cached', 0)
            memory_buffers = getattr(memory, 'buffers', 0)
            
            # Disk metrics
            disk_usage = {}
            for path in self.disk_paths:
                try:
                    if os.path.exists(path):
                        usage = psutil.disk_usage(path)
                        disk_usage[path] = (usage.used / usage.total) * 100
                except (OSError, PermissionError):
                    disk_usage[path] = 0.0
            
            # Disk I/O
            try:
                disk_io = psutil.disk_io_counters()
                disk_io_read = disk_io.read_bytes if disk_io else 0
                disk_io_write = disk_io.write_bytes if disk_io else 0
            except (AttributeError, OSError):
                disk_io_read = disk_io_write = 0
            
            # Network metrics
            try:
                network_io = psutil.net_io_counters()
                network_bytes_sent = network_io.bytes_sent if network_io else 0
                network_bytes_recv = network_io.bytes_recv if network_io else 0
                network_packets_sent = network_io.packets_sent if network_io else 0
                network_packets_recv = network_io.packets_recv if network_io else 0
            except (AttributeError, OSError):
                network_bytes_sent = network_bytes_recv = 0
                network_packets_sent = network_packets_recv = 0
            
            # Process count
            try:
                process_count = len(psutil.pids())
            except (OSError, psutil.NoSuchProcess):
                process_count = 0
            
            # Load average (Unix-like systems)
            try:
                load_average = os.getloadavg()
            except (OSError, AttributeError):
                load_average = (0.0, 0.0, 0.0)
            
            # Boot time and uptime
            try:
                boot_time = psutil.boot_time()
                uptime = now - boot_time
            except (OSError, AttributeError):
                boot_time = now
                uptime = 0.0
            
            # Create metrics object
            metrics = ResourceMetrics(
                timestamp=now,
                cpu_percent=cpu_percent,
                cpu_per_core=cpu_per_core,
                cpu_count_logical=cpu_count_logical,
                cpu_count_physical=cpu_count_physical,
                cpu_freq_current=cpu_freq_current,
                memory_percent=memory_percent,
                memory_used=memory_used,
                memory_available=memory_available,
                memory_total=memory_total,
                memory_cached=memory_cached,
                memory_buffers=memory_buffers,
                disk_usage=disk_usage,
                disk_io_read=disk_io_read,
                disk_io_write=disk_io_write,
                network_bytes_sent=network_bytes_sent,
                network_bytes_recv=network_bytes_recv,
                network_packets_sent=network_packets_sent,
                network_packets_recv=network_packets_recv,
                process_count=process_count,
                load_average=load_average,
                boot_time=boot_time,
                uptime=uptime
            )
            
            # Store current metrics
            self.current_metrics = metrics
            self.metrics_history.append(metrics)
            
            # Check for alerts
            await self._check_alerts(metrics)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting resource metrics: {e}")
            # Return empty metrics on error
            return ResourceMetrics(
                timestamp=time.time(),
                cpu_percent=0.0, cpu_per_core=[], cpu_count_logical=0, cpu_count_physical=0,
                cpu_freq_current=0.0, memory_percent=0.0, memory_used=0, memory_available=0,
                memory_total=0, memory_cached=0, memory_buffers=0, disk_usage={},
                disk_io_read=0, disk_io_write=0, network_bytes_sent=0, network_bytes_recv=0,
                network_packets_sent=0, network_packets_recv=0, process_count=0,
                load_average=(0.0, 0.0, 0.0), boot_time=0.0, uptime=0.0
            )

    async def _check_alerts(self, metrics: ResourceMetrics):
        """Check for resource threshold alerts."""
        alerts = []
        
        # CPU alert
        if metrics.cpu_percent > self.max_cpu_percent:
            alerts.append({
                "type": "cpu_high",
                "severity": "warning" if metrics.cpu_percent < 95 else "critical",
                "message": f"CPU usage is {metrics.cpu_percent:.1f}% (threshold: {self.max_cpu_percent}%)",
                "value": metrics.cpu_percent,
                "threshold": self.max_cpu_percent
            })
        
        # Memory alert
        if metrics.memory_percent > self.max_memory_percent:
            alerts.append({
                "type": "memory_high",
                "severity": "warning" if metrics.memory_percent < 95 else "critical",
                "message": f"Memory usage is {metrics.memory_percent:.1f}% (threshold: {self.max_memory_percent}%)",
                "value": metrics.memory_percent,
                "threshold": self.max_memory_percent
            })
        
        # Disk alerts
        for path, usage in metrics.disk_usage.items():
            if usage > self.max_disk_percent:
                alerts.append({
                    "type": "disk_high",
                    "severity": "warning" if usage < 95 else "critical",
                    "message": f"Disk usage on {path} is {usage:.1f}% (threshold: {self.max_disk_percent}%)",
                    "value": usage,
                    "threshold": self.max_disk_percent,
                    "path": path
                })
        
        # Store alerts
        for alert in alerts:
            alert_id = f"{alert['type']}_{int(metrics.timestamp)}"
            alert["timestamp"] = metrics.timestamp
            self.active_alerts[alert_id] = alert
            self.alerts_history.append(alert)
        
        # Clean up old alerts (older than 1 hour)
        cutoff_time = time.time() - 3600
        self.active_alerts = {
            k: v for k, v in self.active_alerts.items() 
            if v.get("timestamp", 0) > cutoff_time
        }

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage in a format compatible with the API."""
        if not self.current_metrics:
            return {
                "cpu": 0.0,
                "memory": 0.0,
                "disk": 0.0,
                "alerts": 0,
                "cpu_cores": 0,
                "cpu_load": "0.0, 0.0, 0.0",
                "memory_used": "0 B",
                "memory_free": "0 B",
                "memory_total": "0 B",
                "disk_used": "0 B",
                "disk_free": "0 B",
                "process_count": 0,
                "uptime": "0:00:00"
            }
        
        metrics = self.current_metrics
        
        # Format memory values
        def format_bytes(bytes_val):
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_val < 1024.0:
                    return f"{bytes_val:.1f} {unit}"
                bytes_val /= 1024.0
            return f"{bytes_val:.1f} PB"
        
        # Get root disk usage (primary disk)
        root_disk_usage = metrics.disk_usage.get("/", 0.0)
        
        # Calculate disk space info
        try:
            disk_usage = psutil.disk_usage("/")
            disk_used = format_bytes(disk_usage.used)
            disk_free = format_bytes(disk_usage.free)
            disk_total = format_bytes(disk_usage.total)
        except (OSError, AttributeError):
            disk_used = disk_free = disk_total = "Unknown"
        
        return {
            "cpu": round(metrics.cpu_percent, 1),
            "memory": round(metrics.memory_percent, 1),
            "disk": round(root_disk_usage, 1),
            "alerts": len(self.active_alerts),
            "cpu_cores": metrics.cpu_count_logical,
            "cpu_load": f"{metrics.load_average[0]:.2f}, {metrics.load_average[1]:.2f}, {metrics.load_average[2]:.2f}",
            "memory_used": format_bytes(metrics.memory_used),
            "memory_free": format_bytes(metrics.memory_available),
            "memory_total": format_bytes(metrics.memory_total),
            "disk_used": disk_used,
            "disk_free": disk_free,
            "process_count": metrics.process_count,
            "uptime": str(timedelta(seconds=int(metrics.uptime)))
        }

    def get_resource_limits(self) -> Dict[str, Any]:
        """Get current resource limits and thresholds."""
        return {
            "max_cpu_percent": self.max_cpu_percent,
            "max_memory_percent": self.max_memory_percent,
            "max_disk_percent": self.max_disk_percent,
            "disk_paths": self.disk_paths
        }

    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed metrics for advanced monitoring."""
        if not self.current_metrics:
            return {}
        
        metrics = self.current_metrics
        return {
            "timestamp": metrics.timestamp,
            "cpu": {
                "percent": metrics.cpu_percent,
                "per_core": metrics.cpu_per_core,
                "count_logical": metrics.cpu_count_logical,
                "count_physical": metrics.cpu_count_physical,
                "frequency": metrics.cpu_freq_current
            },
            "memory": {
                "percent": metrics.memory_percent,
                "used": metrics.memory_used,
                "available": metrics.memory_available,
                "total": metrics.memory_total,
                "cached": metrics.memory_cached,
                "buffers": metrics.memory_buffers
            },
            "disk": {
                "usage": metrics.disk_usage,
                "io_read": metrics.disk_io_read,
                "io_write": metrics.disk_io_write
            },
            "network": {
                "bytes_sent": metrics.network_bytes_sent,
                "bytes_recv": metrics.network_bytes_recv,
                "packets_sent": metrics.network_packets_sent,
                "packets_recv": metrics.network_packets_recv
            },
            "system": {
                "process_count": metrics.process_count,
                "load_average": list(metrics.load_average),
                "uptime": metrics.uptime,
                "boot_time": metrics.boot_time
            },
            "alerts": list(self.active_alerts.values())
        }

    def get_historical_data(self, hours: int = 1) -> List[Dict[str, Any]]:
        """Get historical resource data for the specified time period."""
        cutoff_time = time.time() - (hours * 3600)
        return [
            asdict(metrics) for metrics in self.metrics_history
            if metrics.timestamp > cutoff_time
        ]

    def get_alerts_summary(self) -> Dict[str, Any]:
        """Get summary of current alerts."""
        alert_counts = {}
        for alert in self.active_alerts.values():
            alert_type = alert.get("type", "unknown")
            severity = alert.get("severity", "info")
            key = f"{alert_type}_{severity}"
            alert_counts[key] = alert_counts.get(key, 0) + 1
        
        return {
            "total_alerts": len(self.active_alerts),
            "alert_counts": alert_counts,
            "recent_alerts": list(self.active_alerts.values())[-10:]  # Last 10 alerts
        }

    async def start_monitoring(self, interval: float = 5.0):
        """Start continuous resource monitoring."""
        logger.info(f"Starting resource monitoring with {interval}s interval")
        
        while True:
            try:
                await self.collect_metrics()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(interval)

# Global instance management
_resource_monitor_instance = None

def get_resource_monitor() -> ResourceMonitor:
    """Get the global resource monitor instance."""
    global _resource_monitor_instance
    if _resource_monitor_instance is None:
        _resource_monitor_instance = ResourceMonitor()
    return _resource_monitor_instance

async def start_resource_monitoring(interval: float = 5.0):
    """Start the global resource monitoring."""
    monitor = get_resource_monitor()
    await monitor.start_monitoring(interval)

# For backward compatibility
def get_resource_usage() -> Dict[str, Any]:
    """Get current resource usage (backward compatibility)."""
    monitor = get_resource_monitor()
    return monitor.get_resource_usage()

def get_resource_limits() -> Dict[str, Any]:
    """Get resource limits (backward compatibility)."""
    monitor = get_resource_monitor()
    return monitor.get_resource_limits()
async def get_resource_monitor_async(memory_agent=None, config_override=None, test_mode=False):
    """Async wrapper for get_resource_monitor."""
    return get_resource_monitor()
