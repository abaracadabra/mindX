"""
Production Performance Optimizer for mindX
Implements async/await optimization, connection pooling, and enhanced monitoring
"""

import asyncio
import time
import weakref
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional, List, AsyncGenerator, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
from functools import wraps, partial
import psutil

import asyncpg
from aioredis import Redis, create_redis_pool
from aiohttp import ClientSession, ClientTimeout, TCPConnector

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ConnectionPoolManager:
    """Manages connection pools for various services"""

    def __init__(self, config: Config):
        self.config = config
        self.pools: Dict[str, Any] = {}
        self._cleanup_tasks: List[asyncio.Task] = []

    async def get_postgres_pool(self) -> asyncpg.Pool:
        """Get or create PostgreSQL connection pool"""
        if 'postgres' not in self.pools:
            try:
                db_config = self.config.get("database", {})
                connection_string = (
                    f"postgresql://{db_config.get('user', 'postgres')}:"
                    f"{db_config.get('password', 'password')}@"
                    f"{db_config.get('host', 'localhost')}:"
                    f"{db_config.get('port', 5432)}/"
                    f"{db_config.get('database', 'mindx')}"
                )

                self.pools['postgres'] = await asyncpg.create_pool(
                    connection_string,
                    min_size=self.config.get("database.pool.min_size", 5),
                    max_size=self.config.get("database.pool.max_size", 20),
                    max_queries=self.config.get("database.pool.max_queries", 50000),
                    max_inactive_connection_lifetime=300.0,
                    command_timeout=30.0,
                )
                logger.info("PostgreSQL connection pool created")

            except Exception as e:
                logger.error(f"Failed to create PostgreSQL pool: {e}")
                raise

        return self.pools['postgres']

    async def get_redis_pool(self) -> Redis:
        """Get or create Redis connection pool"""
        if 'redis' not in self.pools:
            try:
                redis_config = self.config.get("redis", {})
                self.pools['redis'] = await create_redis_pool(
                    f"redis://{redis_config.get('host', 'localhost')}:"
                    f"{redis_config.get('port', 6379)}",
                    db=redis_config.get('database', 0),
                    minsize=self.config.get("redis.pool.min_size", 5),
                    maxsize=self.config.get("redis.pool.max_size", 20),
                    timeout=self.config.get("redis.pool.timeout", 5),
                )
                logger.info("Redis connection pool created")

            except Exception as e:
                logger.warning(f"Failed to create Redis pool: {e}")
                # Redis is optional, continue without it
                self.pools['redis'] = None

        return self.pools['redis']

    async def get_http_session(self) -> ClientSession:
        """Get or create HTTP client session with connection pooling"""
        if 'http' not in self.pools:
            connector = TCPConnector(
                limit=self.config.get("http.pool.max_connections", 100),
                limit_per_host=self.config.get("http.pool.max_per_host", 30),
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )

            timeout = ClientTimeout(
                total=self.config.get("http.timeout.total", 30),
                connect=self.config.get("http.timeout.connect", 10)
            )

            self.pools['http'] = ClientSession(
                connector=connector,
                timeout=timeout,
                headers={'User-Agent': 'mindX/2.0.0'}
            )
            logger.info("HTTP client session pool created")

        return self.pools['http']

    async def close_all_pools(self):
        """Close all connection pools"""
        logger.info("Closing all connection pools...")

        # Cancel cleanup tasks
        for task in self._cleanup_tasks:
            if not task.done():
                task.cancel()

        # Close PostgreSQL pool
        if 'postgres' in self.pools and self.pools['postgres']:
            await self.pools['postgres'].close()
            logger.info("PostgreSQL pool closed")

        # Close Redis pool
        if 'redis' in self.pools and self.pools['redis']:
            self.pools['redis'].close()
            await self.pools['redis'].wait_closed()
            logger.info("Redis pool closed")

        # Close HTTP session
        if 'http' in self.pools and self.pools['http']:
            await self.pools['http'].close()
            logger.info("HTTP session closed")

        self.pools.clear()

class AsyncWorkloadManager:
    """Manages async workloads and prevents blocking operations"""

    def __init__(self, config: Config):
        self.config = config
        self.executor = None
        self._active_tasks: weakref.WeakSet = weakref.WeakSet()
        self._task_stats = defaultdict(int)

    def get_executor(self):
        """Get thread pool executor for CPU-bound tasks"""
        if self.executor is None:
            import concurrent.futures
            max_workers = self.config.get("performance.executor.max_workers", 4)
            self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
            logger.info(f"Thread pool executor created with {max_workers} workers")
        return self.executor

    async def run_in_executor(self, func: Callable, *args, **kwargs):
        """Run CPU-bound function in thread pool"""
        loop = asyncio.get_event_loop()
        if kwargs:
            func = partial(func, **kwargs)
        return await loop.run_in_executor(self.get_executor(), func, *args)

    def create_task_with_tracking(self, coro, name: str = None) -> asyncio.Task:
        """Create task with automatic tracking and cleanup"""
        task = asyncio.create_task(coro, name=name)
        self._active_tasks.add(task)
        self._task_stats['created'] += 1

        def cleanup_callback(task):
            self._task_stats['completed'] += 1
            if task.exception():
                self._task_stats['failed'] += 1
                logger.error(f"Task {task.get_name()} failed: {task.exception()}")

        task.add_done_callback(cleanup_callback)
        return task

    @asynccontextmanager
    async def timeout_context(self, timeout: float):
        """Context manager for operations with timeout"""
        try:
            async with asyncio.timeout(timeout):
                yield
        except asyncio.TimeoutError:
            logger.warning(f"Operation timed out after {timeout} seconds")
            raise

    async def gather_with_limit(self, *awaitables, limit: int = 10, return_exceptions: bool = True):
        """Gather awaitables with concurrency limit"""
        semaphore = asyncio.Semaphore(limit)

        async def run_with_semaphore(awaitable):
            async with semaphore:
                return await awaitable

        wrapped = [run_with_semaphore(aw) for aw in awaitables]
        return await asyncio.gather(*wrapped, return_exceptions=return_exceptions)

    def get_task_stats(self) -> Dict[str, Any]:
        """Get task execution statistics"""
        return {
            "active_tasks": len(self._active_tasks),
            "total_created": self._task_stats['created'],
            "total_completed": self._task_stats['completed'],
            "total_failed": self._task_stats['failed'],
            "executor_threads": self.executor._max_workers if self.executor else 0
        }

class PerformanceMetrics:
    """Enhanced performance metrics collection"""

    def __init__(self, config: Config):
        self.config = config
        self.metrics = defaultdict(lambda: {
            "count": 0,
            "total_time": 0.0,
            "avg_time": 0.0,
            "min_time": float('inf'),
            "max_time": 0.0,
            "recent_times": deque(maxlen=100),
            "error_count": 0,
            "last_error": None,
            "last_called": None
        })
        self.system_metrics = deque(maxlen=1000)  # Store last 1000 system snapshots

    def record_operation(self, operation: str, duration: float, error: Optional[Exception] = None):
        """Record operation performance metrics"""
        metric = self.metrics[operation]
        metric["count"] += 1
        metric["total_time"] += duration
        metric["avg_time"] = metric["total_time"] / metric["count"]
        metric["min_time"] = min(metric["min_time"], duration)
        metric["max_time"] = max(metric["max_time"], duration)
        metric["recent_times"].append(duration)
        metric["last_called"] = datetime.utcnow().isoformat()

        if error:
            metric["error_count"] += 1
            metric["last_error"] = {
                "type": type(error).__name__,
                "message": str(error),
                "timestamp": datetime.utcnow().isoformat()
            }

    def record_system_metrics(self):
        """Record current system resource usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            metric = {
                "timestamp": datetime.utcnow().isoformat(),
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3)
            }

            self.system_metrics.append(metric)

        except Exception as e:
            logger.error(f"Failed to record system metrics: {e}")

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary report"""
        summary = {
            "operations": {},
            "system": {
                "current": self.system_metrics[-1] if self.system_metrics else None,
                "avg_cpu_5min": 0.0,
                "avg_memory_5min": 0.0
            },
            "recommendations": []
        }

        # Summarize operation metrics
        for op_name, metric in self.metrics.items():
            if metric["count"] > 0:
                recent_avg = sum(metric["recent_times"]) / len(metric["recent_times"]) if metric["recent_times"] else 0
                summary["operations"][op_name] = {
                    "total_calls": metric["count"],
                    "avg_response_ms": metric["avg_time"] * 1000,
                    "recent_avg_ms": recent_avg * 1000,
                    "error_rate": metric["error_count"] / metric["count"] if metric["count"] > 0 else 0,
                    "last_called": metric["last_called"]
                }

        # Calculate system averages
        if self.system_metrics:
            recent_metrics = list(self.system_metrics)[-300:]  # Last 5 minutes at 1 sec interval
            if recent_metrics:
                summary["system"]["avg_cpu_5min"] = sum(m["cpu_percent"] for m in recent_metrics) / len(recent_metrics)
                summary["system"]["avg_memory_5min"] = sum(m["memory_percent"] for m in recent_metrics) / len(recent_metrics)

        # Generate recommendations
        recommendations = []

        # High CPU usage
        if summary["system"]["avg_cpu_5min"] > 80:
            recommendations.append("High CPU usage detected - consider scaling or optimization")

        # High memory usage
        if summary["system"]["avg_memory_5min"] > 85:
            recommendations.append("High memory usage detected - check for memory leaks")

        # Slow operations
        for op_name, op_data in summary["operations"].items():
            if op_data["avg_response_ms"] > 5000:
                recommendations.append(f"Slow operation detected: {op_name} ({op_data['avg_response_ms']:.1f}ms)")

        # High error rates
        for op_name, op_data in summary["operations"].items():
            if op_data["error_rate"] > 0.1:
                recommendations.append(f"High error rate: {op_name} ({op_data['error_rate']*100:.1f}%)")

        summary["recommendations"] = recommendations
        return summary

class CircuitBreaker:
    """Circuit breaker pattern for external service calls"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0, expected_exception=Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open

    def __call__(self, func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == 'open':
                if self._should_attempt_reset():
                    self.state = 'half-open'
                else:
                    raise Exception(f"Circuit breaker is OPEN. Last failure: {self.last_failure_time}")

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result

            except self.expected_exception as e:
                self._on_failure()
                raise e

        return wrapper

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time is not None and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = 'closed'

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = 'open'
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

def performance_monitor(operation_name: str = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            error = None

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                return result

            except Exception as e:
                error = e
                raise

            finally:
                duration = time.time() - start_time
                # Get global performance optimizer instance
                if hasattr(PerformanceOptimizer, '_instance') and PerformanceOptimizer._instance:
                    PerformanceOptimizer._instance.metrics.record_operation(op_name, duration, error)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or f"{func.__module__}.{func.__name__}"
            start_time = time.time()
            error = None

            try:
                result = func(*args, **kwargs)
                return result

            except Exception as e:
                error = e
                raise

            finally:
                duration = time.time() - start_time
                # Get global performance optimizer instance
                if hasattr(PerformanceOptimizer, '_instance') and PerformanceOptimizer._instance:
                    PerformanceOptimizer._instance.metrics.record_operation(op_name, duration, error)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

class PerformanceOptimizer:
    """Main performance optimization coordinator"""

    _instance = None

    def __init__(self, config: Config):
        self.config = config
        self.pool_manager = ConnectionPoolManager(config)
        self.workload_manager = AsyncWorkloadManager(config)
        self.metrics = PerformanceMetrics(config)

        # Set global instance
        PerformanceOptimizer._instance = self

        # Start background tasks
        self._monitoring_task = None
        self._cleanup_task = None

    async def start_background_monitoring(self):
        """Start background monitoring tasks"""
        if self.config.get("performance.monitoring.enabled", True):
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Background performance monitoring started")

        if self.config.get("performance.cleanup.enabled", True):
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("Background cleanup task started")

    async def stop_background_monitoring(self):
        """Stop background monitoring tasks"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        logger.info("Background monitoring stopped")

    async def _monitoring_loop(self):
        """Background monitoring loop"""
        interval = self.config.get("performance.monitoring.interval", 30)

        while True:
            try:
                self.metrics.record_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(interval)

    async def _cleanup_loop(self):
        """Background cleanup loop"""
        interval = self.config.get("performance.cleanup.interval", 300)  # 5 minutes

        while True:
            try:
                # Cleanup old metrics
                cutoff_time = datetime.utcnow() - timedelta(hours=1)
                # Add cleanup logic here

                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")
                await asyncio.sleep(interval)

    async def get_database_connection(self):
        """Get database connection from pool"""
        pool = await self.pool_manager.get_postgres_pool()
        return pool.acquire()

    async def get_redis_connection(self):
        """Get Redis connection from pool"""
        return await self.pool_manager.get_redis_pool()

    async def get_http_session(self):
        """Get HTTP session from pool"""
        return await self.pool_manager.get_http_session()

    async def shutdown(self):
        """Shutdown performance optimizer"""
        logger.info("Shutting down performance optimizer...")

        await self.stop_background_monitoring()
        await self.pool_manager.close_all_pools()

        if self.workload_manager.executor:
            self.workload_manager.executor.shutdown(wait=True)

        logger.info("Performance optimizer shutdown complete")

# Global instance getter
_performance_optimizer_instance = None

def get_performance_optimizer(config: Config = None) -> PerformanceOptimizer:
    """Get singleton performance optimizer instance"""
    global _performance_optimizer_instance
    if _performance_optimizer_instance is None:
        if config is None:
            config = Config()
        _performance_optimizer_instance = PerformanceOptimizer(config)
    return _performance_optimizer_instance