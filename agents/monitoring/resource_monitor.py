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

    async def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metrics — async interface used by SystemStateTracker, mindXagent, etc."""
        try:
            metrics = await self.collect_metrics()
            return {
                "cpu_percent": round(metrics.cpu_percent, 1),
                "cpu_count": metrics.cpu_count_logical,
                "load_average": list(metrics.load_average),
                "memory_percent": round(metrics.memory_percent, 1),
                "memory_used_gb": round(metrics.memory_used / (1024**3), 2),
                "memory_total_gb": round(metrics.memory_total / (1024**3), 2),
                "disk_percent": metrics.disk_usage.get("/", 0.0),
                "process_count": metrics.process_count,
                "uptime_seconds": int(metrics.uptime),
                "network_bytes_sent": metrics.network_bytes_sent,
                "network_bytes_recv": metrics.network_bytes_recv,
                "alerts": len(self.active_alerts),
            }
        except Exception as e:
            # Minimal fallback using psutil directly
            try:
                return {
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage("/").percent,
                    "load_average": list(os.getloadavg()),
                    "alerts": 0,
                }
            except Exception:
                return {"error": str(e)}

    async def get_current_resources(self) -> Dict[str, Any]:
        """Alias for get_current_metrics (used by mindXagent._analyze_system_state)."""
        return await self.get_current_metrics()

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


# ─── Full psutil surface (used by /system/resources/full + BDI perceive) ───
def psutil_snapshot() -> Dict[str, Any]:
    """One-shot comprehensive psutil snapshot. Synchronous, ~50ms.

    Returns every dimension psutil exposes that is operationally useful on
    a Linux VPS: cpu_times_percent (user/system/idle/iowait/steal/irq),
    cpu_stats (ctx_switches, interrupts), swap, disk I/O per-disk, net I/O
    per-NIC, socket counts, sensors (temperatures/fans/battery), users,
    and **self-process** stats for the running mindX backend.
    """
    snap: Dict[str, Any] = {"timestamp": time.time()}
    try:
        snap["cpu"] = {
            "percent": psutil.cpu_percent(interval=None),
            "per_core": psutil.cpu_percent(percpu=True, interval=None),
            "count_logical": psutil.cpu_count(logical=True),
            "count_physical": psutil.cpu_count(logical=False),
        }
        try:
            cf = psutil.cpu_freq()
            if cf:
                snap["cpu"]["freq_mhz"] = {"current": cf.current, "min": cf.min, "max": cf.max}
        except Exception:
            pass
        try:
            ct = psutil.cpu_times_percent(interval=None)
            snap["cpu"]["times_percent"] = {f: getattr(ct, f, 0.0) for f in ct._fields}
        except Exception:
            pass
        try:
            cs = psutil.cpu_stats()
            snap["cpu"]["stats"] = {f: getattr(cs, f, 0) for f in cs._fields}
        except Exception:
            pass
    except Exception as e:
        snap["cpu"] = {"error": str(e)}

    try:
        vm = psutil.virtual_memory()
        snap["memory"] = {f: getattr(vm, f, 0) for f in vm._fields}
        snap["memory"]["used_gb"] = round(vm.used / 1024**3, 2)
        snap["memory"]["available_gb"] = round(vm.available / 1024**3, 2)
        snap["memory"]["total_gb"] = round(vm.total / 1024**3, 2)
    except Exception as e:
        snap["memory"] = {"error": str(e)}

    try:
        sm = psutil.swap_memory()
        snap["swap"] = {f: getattr(sm, f, 0) for f in sm._fields}
    except Exception:
        snap["swap"] = {}

    try:
        snap["disk"] = {"per_path": {}, "io": {}, "io_per_disk": {}}
        for part in psutil.disk_partitions(all=False):
            try:
                u = psutil.disk_usage(part.mountpoint)
                snap["disk"]["per_path"][part.mountpoint] = {
                    "device": part.device,
                    "fstype": part.fstype,
                    "total": u.total, "used": u.used, "free": u.free, "percent": u.percent,
                }
            except (OSError, PermissionError):
                continue
        try:
            io = psutil.disk_io_counters()
            if io:
                snap["disk"]["io"] = {f: getattr(io, f, 0) for f in io._fields}
        except Exception:
            pass
        try:
            per = psutil.disk_io_counters(perdisk=True) or {}
            for name, c in per.items():
                snap["disk"]["io_per_disk"][name] = {f: getattr(c, f, 0) for f in c._fields}
        except Exception:
            pass
    except Exception as e:
        snap["disk"] = {"error": str(e)}

    try:
        snap["net"] = {"io": {}, "per_nic": {}, "if_addrs": {}, "if_stats": {}}
        try:
            io = psutil.net_io_counters()
            if io:
                snap["net"]["io"] = {f: getattr(io, f, 0) for f in io._fields}
        except Exception:
            pass
        try:
            per = psutil.net_io_counters(pernic=True) or {}
            for nic, c in per.items():
                snap["net"]["per_nic"][nic] = {f: getattr(c, f, 0) for f in c._fields}
        except Exception:
            pass
        try:
            stats = psutil.net_if_stats() or {}
            for nic, s in stats.items():
                snap["net"]["if_stats"][nic] = {
                    "isup": s.isup, "duplex": int(getattr(s, "duplex", 0)),
                    "speed_mbps": getattr(s, "speed", 0), "mtu": getattr(s, "mtu", 0),
                }
        except Exception:
            pass
        try:
            kinds = {"tcp": 0, "udp": 0, "listen": 0, "established": 0}
            for c in psutil.net_connections(kind="inet"):
                if c.type == 1:    kinds["tcp"] += 1     # SOCK_STREAM
                elif c.type == 2:  kinds["udp"] += 1     # SOCK_DGRAM
                if c.status == "LISTEN":      kinds["listen"] += 1
                elif c.status == "ESTABLISHED": kinds["established"] += 1
            snap["net"]["sockets"] = kinds
        except (psutil.AccessDenied, PermissionError):
            snap["net"]["sockets"] = {"error": "access_denied"}
        except Exception:
            pass
    except Exception as e:
        snap["net"] = {"error": str(e)}

    try:
        snap["sensors"] = {}
        try:
            t = psutil.sensors_temperatures()
            if t:
                snap["sensors"]["temperatures"] = {
                    chip: [{"label": e.label, "current": e.current, "high": e.high, "critical": e.critical} for e in entries]
                    for chip, entries in t.items()
                }
        except Exception:
            pass
        try:
            f = psutil.sensors_fans()
            if f:
                snap["sensors"]["fans"] = {
                    chip: [{"label": e.label, "current": e.current} for e in entries]
                    for chip, entries in f.items()
                }
        except Exception:
            pass
        try:
            b = psutil.sensors_battery()
            if b:
                snap["sensors"]["battery"] = {
                    "percent": b.percent, "secsleft": b.secsleft, "power_plugged": b.power_plugged
                }
        except Exception:
            pass
    except Exception:
        snap["sensors"] = {}

    try:
        snap["host"] = {
            "boot_time": psutil.boot_time(),
            "uptime_seconds": int(time.time() - psutil.boot_time()),
            "process_count": len(psutil.pids()),
            "users": [{"name": u.name, "terminal": u.terminal, "started": u.started} for u in psutil.users()],
        }
        try:
            snap["host"]["load_average"] = list(os.getloadavg())
        except (OSError, AttributeError):
            pass
    except Exception as e:
        snap["host"] = {"error": str(e)}

    # Self-process: how much resource does mindX itself consume?
    try:
        p = psutil.Process(os.getpid())
        with p.oneshot():
            mi = p.memory_info()
            try:
                full = p.memory_full_info()
                uss = getattr(full, "uss", 0)
                pss = getattr(full, "pss", 0)
            except (psutil.AccessDenied, AttributeError):
                uss = pss = 0
            try:
                io = p.io_counters()
                io_dict = {"read_bytes": io.read_bytes, "write_bytes": io.write_bytes,
                           "read_count": io.read_count, "write_count": io.write_count}
            except (psutil.AccessDenied, AttributeError):
                io_dict = {}
            try:
                ct = p.cpu_times()
                ct_dict = {"user": ct.user, "system": ct.system, "iowait": getattr(ct, "iowait", 0.0)}
            except Exception:
                ct_dict = {}
            try:
                num_fds = p.num_fds()
            except (psutil.AccessDenied, AttributeError):
                num_fds = -1
            snap["self_process"] = {
                "pid": p.pid,
                "name": p.name(),
                "status": p.status(),
                "create_time": p.create_time(),
                "uptime_seconds": int(time.time() - p.create_time()),
                "cpu_percent": p.cpu_percent(interval=None),
                "num_threads": p.num_threads(),
                "num_fds": num_fds,
                "rss_bytes": mi.rss,
                "vms_bytes": mi.vms,
                "uss_bytes": uss,
                "pss_bytes": pss,
                "rss_mb": round(mi.rss / 1024**2, 1),
                "io": io_dict,
                "cpu_times": ct_dict,
                "nice": p.nice(),
            }
            try:
                snap["self_process"]["connections"] = len(p.connections(kind="inet"))
            except (psutil.AccessDenied, AttributeError):
                pass
    except Exception as e:
        snap["self_process"] = {"error": str(e)}

    return snap


def psutil_compact_summary(snap: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Compact 14-field summary used by BDI perceive() and the feedback.html
    system-pulse tile. Stable schema, every field always present."""
    s = snap or psutil_snapshot()
    cpu = s.get("cpu", {}) or {}
    mem = s.get("memory", {}) or {}
    swap = s.get("swap", {}) or {}
    host = s.get("host", {}) or {}
    sp = s.get("self_process", {}) or {}
    sock = (s.get("net", {}) or {}).get("sockets", {}) or {}
    times = cpu.get("times_percent", {}) or {}
    root_pct = ((s.get("disk", {}) or {}).get("per_path", {}) or {}).get("/", {}).get("percent", 0.0)
    return {
        "cpu_percent": cpu.get("percent", 0.0),
        "cpu_iowait": times.get("iowait", 0.0),
        "cpu_steal": times.get("steal", 0.0),
        "load_1m": (host.get("load_average") or [0.0, 0.0, 0.0])[0],
        "memory_percent": mem.get("percent", 0.0),
        "memory_available_gb": mem.get("available_gb", 0.0),
        "swap_percent": swap.get("percent", 0.0),
        "disk_root_percent": root_pct,
        "sockets_established": sock.get("established", 0) if isinstance(sock, dict) else 0,
        "self_rss_mb": sp.get("rss_mb", 0.0),
        "self_cpu_percent": sp.get("cpu_percent", 0.0),
        "self_threads": sp.get("num_threads", 0),
        "self_fds": sp.get("num_fds", -1),
        "self_uptime_seconds": sp.get("uptime_seconds", 0),
    }
