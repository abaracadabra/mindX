"""
Comprehensive Error Handling and Monitoring System for mindX
Implements circuit breakers, retry logic, error propagation, and health checks
"""

import asyncio
import time
import random
import traceback
import sys
from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from collections import defaultdict, deque
import json
import inspect

from utils.config import Config, PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    """Context information for error handling"""
    operation: str
    component: str
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class HealthCheckResult:
    """Result of a health check"""
    name: str
    status: HealthStatus
    response_time_ms: float
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

class RetryConfig:
    """Configuration for retry logic"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        backoff_factor: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Tuple = (Exception,)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = self.base_delay * (self.backoff_factor ** (attempt - 1))
        delay = min(delay, self.max_delay)

        if self.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """Determine if exception should trigger a retry"""
        if attempt >= self.max_attempts:
            return False

        return isinstance(exception, self.retryable_exceptions)

class CircuitBreakerConfig:
    """Configuration for circuit breaker"""

    def __init__(
        self,
        failure_threshold: int = 5,
        success_threshold: int = 3,
        timeout_duration: float = 60.0,
        half_open_max_calls: int = 5
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_duration = timeout_duration
        self.half_open_max_calls = half_open_max_calls

class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    """Circuit breaker implementation"""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.half_open_calls = 0

    def __call__(self, func):
        """Decorator implementation"""
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self._execute(func, args, kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(self._execute(func, args, kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    async def _execute(self, func, args, kwargs):
        """Execute function with circuit breaker logic"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._transition_to_half_open()
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Last failure: {datetime.fromtimestamp(self.last_failure_time)}"
                )

        if self.state == CircuitBreakerState.HALF_OPEN:
            if self.half_open_calls >= self.config.half_open_max_calls:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker '{self.name}' is HALF_OPEN but at max calls limit"
                )

        try:
            # Execute the function
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            self._record_success()
            return result

        except Exception as e:
            self._record_failure()
            raise e

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt to reset"""
        return (
            self.state == CircuitBreakerState.OPEN and
            time.time() - self.last_failure_time >= self.config.timeout_duration
        )

    def _transition_to_half_open(self):
        """Transition to half-open state"""
        self.state = CircuitBreakerState.HALF_OPEN
        self.half_open_calls = 0
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")

    def _record_success(self):
        """Record successful call"""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            self.half_open_calls += 1

            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
        else:
            self.failure_count = 0

    def _record_failure(self):
        """Record failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitBreakerState.HALF_OPEN:
            self._transition_to_open()
        elif self.failure_count >= self.config.failure_threshold:
            self._transition_to_open()

    def _transition_to_open(self):
        """Transition to open state"""
        self.state = CircuitBreakerState.OPEN
        self.success_count = 0
        logger.warning(f"Circuit breaker '{self.name}' OPENED after {self.failure_count} failures")

    def _transition_to_closed(self):
        """Transition to closed state"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        logger.info(f"Circuit breaker '{self.name}' CLOSED after successful recovery")

    def get_status(self) -> Dict[str, Any]:
        """Get current circuit breaker status"""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time,
            "half_open_calls": self.half_open_calls,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_duration": self.config.timeout_duration
            }
        }

class CircuitBreakerOpenException(Exception):
    """Exception raised when circuit breaker is open"""
    pass

class RetryExhaustedException(Exception):
    """Exception raised when all retry attempts are exhausted"""
    pass

def retry_with_backoff(config: RetryConfig = None):
    """Decorator for retry with exponential backoff"""
    if config is None:
        config = RetryConfig()

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    if asyncio.iscoroutinefunction(func):
                        return await func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e

                    if not config.should_retry(e, attempt):
                        break

                    if attempt < config.max_attempts:
                        delay = config.calculate_delay(attempt)
                        logger.warning(f"Attempt {attempt} failed for {func.__name__}: {e}. "
                                     f"Retrying in {delay:.2f} seconds...")
                        await asyncio.sleep(delay)

            # All retries exhausted
            logger.error(f"All {config.max_attempts} retry attempts exhausted for {func.__name__}")
            raise RetryExhaustedException(f"Failed after {config.max_attempts} attempts") from last_exception

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator

class ErrorCollector:
    """Collects and analyzes errors across the system"""

    def __init__(self, config: Config):
        self.config = config
        self.errors: deque = deque(maxlen=config.get("error_handling.max_errors", 10000))
        self.error_counts = defaultdict(int)
        self.error_patterns = defaultdict(list)

    def record_error(
        self,
        exception: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        """Record an error with context"""
        error_data = {
            "timestamp": context.timestamp,
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
            "traceback": traceback.format_exc(),
            "operation": context.operation,
            "component": context.component,
            "severity": severity.value,
            "user_id": context.user_id,
            "session_id": context.session_id,
            "request_id": context.request_id,
            "metadata": context.metadata
        }

        self.errors.append(error_data)
        self.error_counts[type(exception).__name__] += 1

        # Detect error patterns
        error_key = f"{context.component}:{type(exception).__name__}"
        self.error_patterns[error_key].append(context.timestamp)

        # Log based on severity
        if severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL ERROR in {context.operation}: {exception}", exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(f"HIGH SEVERITY ERROR in {context.operation}: {exception}", exc_info=True)
        else:
            logger.warning(f"Error in {context.operation}: {exception}")

    def get_error_summary(self, time_window: float = 3600) -> Dict[str, Any]:
        """Get error summary for the specified time window"""
        current_time = time.time()
        recent_errors = [
            error for error in self.errors
            if current_time - error["timestamp"] <= time_window
        ]

        summary = {
            "total_errors": len(recent_errors),
            "error_rate": len(recent_errors) / (time_window / 60),  # errors per minute
            "by_type": defaultdict(int),
            "by_component": defaultdict(int),
            "by_severity": defaultdict(int),
            "patterns": []
        }

        for error in recent_errors:
            summary["by_type"][error["exception_type"]] += 1
            summary["by_component"][error["component"]] += 1
            summary["by_severity"][error["severity"]] += 1

        # Detect error burst patterns
        for pattern_key, timestamps in self.error_patterns.items():
            recent_timestamps = [ts for ts in timestamps if current_time - ts <= time_window]
            if len(recent_timestamps) >= 5:  # 5+ errors in time window
                summary["patterns"].append({
                    "pattern": pattern_key,
                    "count": len(recent_timestamps),
                    "rate": len(recent_timestamps) / (time_window / 60)
                })

        return summary

class HealthChecker:
    """System health checking and monitoring"""

    def __init__(self, config: Config):
        self.config = config
        self.checks: Dict[str, Callable] = {}
        self.results: Dict[str, HealthCheckResult] = {}
        self.check_history: defaultdict[str, deque] = defaultdict(lambda: deque(maxlen=100))

    def register_check(self, name: str, check_func: Callable, timeout: float = 30.0):
        """Register a health check function"""
        self.checks[name] = {
            "func": check_func,
            "timeout": timeout
        }
        logger.info(f"Registered health check: {name}")

    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check"""
        if name not in self.checks:
            return HealthCheckResult(
                name=name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=0,
                message="Check not found"
            )

        check_config = self.checks[name]
        start_time = time.time()

        try:
            async with asyncio.timeout(check_config["timeout"]):
                if asyncio.iscoroutinefunction(check_config["func"]):
                    result = await check_config["func"]()
                else:
                    result = check_config["func"]()

            response_time = (time.time() - start_time) * 1000

            if isinstance(result, HealthCheckResult):
                result.response_time_ms = response_time
                health_result = result
            elif isinstance(result, bool):
                health_result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY,
                    response_time_ms=response_time,
                    message="OK" if result else "Check failed"
                )
            else:
                health_result = HealthCheckResult(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time,
                    message=str(result)
                )

        except asyncio.TimeoutError:
            health_result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                message=f"Check timed out after {check_config['timeout']} seconds"
            )

        except Exception as e:
            health_result = HealthCheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=(time.time() - start_time) * 1000,
                message=f"Check failed: {str(e)}"
            )

        # Store result and history
        self.results[name] = health_result
        self.check_history[name].append(health_result)

        return health_result

    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks"""
        if not self.checks:
            return {}

        # Run checks concurrently
        check_tasks = [
            asyncio.create_task(self.run_check(name), name=f"health_check_{name}")
            for name in self.checks.keys()
        ]

        results = await asyncio.gather(*check_tasks, return_exceptions=True)

        # Process results
        all_results = {}
        for i, result in enumerate(results):
            check_name = list(self.checks.keys())[i]
            if isinstance(result, Exception):
                all_results[check_name] = HealthCheckResult(
                    name=check_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=f"Check execution failed: {str(result)}"
                )
            else:
                all_results[check_name] = result

        return all_results

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health status"""
        if not self.results:
            return {
                "status": HealthStatus.UNKNOWN.value,
                "message": "No health checks configured",
                "checks": {}
            }

        healthy_count = sum(1 for result in self.results.values()
                          if result.status == HealthStatus.HEALTHY)
        degraded_count = sum(1 for result in self.results.values()
                           if result.status == HealthStatus.DEGRADED)
        unhealthy_count = sum(1 for result in self.results.values()
                            if result.status == HealthStatus.UNHEALTHY)

        total_checks = len(self.results)

        # Determine overall status
        if unhealthy_count > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded_count > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "status": overall_status.value,
            "message": f"{healthy_count}/{total_checks} checks healthy",
            "summary": {
                "healthy": healthy_count,
                "degraded": degraded_count,
                "unhealthy": unhealthy_count,
                "total": total_checks
            },
            "checks": {name: result.__dict__ for name, result in self.results.items()}
        }

class ErrorHandlingSystem:
    """Main error handling system coordinator"""

    def __init__(self, config: Config):
        self.config = config
        self.error_collector = ErrorCollector(config)
        self.health_checker = HealthChecker(config)
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Register default health checks
        self._register_default_health_checks()

        # Background monitoring task
        self._monitoring_task: Optional[asyncio.Task] = None

    def _register_default_health_checks(self):
        """Register default system health checks"""

        async def check_memory_usage():
            """Check system memory usage"""
            try:
                import psutil
                memory = psutil.virtual_memory()
                if memory.percent > 90:
                    return HealthCheckResult(
                        name="memory",
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=0,
                        message=f"Memory usage critical: {memory.percent:.1f}%"
                    )
                elif memory.percent > 80:
                    return HealthCheckResult(
                        name="memory",
                        status=HealthStatus.DEGRADED,
                        response_time_ms=0,
                        message=f"Memory usage high: {memory.percent:.1f}%"
                    )
                else:
                    return HealthCheckResult(
                        name="memory",
                        status=HealthStatus.HEALTHY,
                        response_time_ms=0,
                        message=f"Memory usage normal: {memory.percent:.1f}%"
                    )
            except ImportError:
                return HealthCheckResult(
                    name="memory",
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    message="psutil not available"
                )

        async def check_disk_space():
            """Check disk space"""
            try:
                import psutil
                disk = psutil.disk_usage('/')
                percent_used = (disk.used / disk.total) * 100

                if percent_used > 95:
                    return HealthCheckResult(
                        name="disk",
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=0,
                        message=f"Disk space critical: {percent_used:.1f}% used"
                    )
                elif percent_used > 85:
                    return HealthCheckResult(
                        name="disk",
                        status=HealthStatus.DEGRADED,
                        response_time_ms=0,
                        message=f"Disk space low: {percent_used:.1f}% used"
                    )
                else:
                    return HealthCheckResult(
                        name="disk",
                        status=HealthStatus.HEALTHY,
                        response_time_ms=0,
                        message=f"Disk space normal: {percent_used:.1f}% used"
                    )
            except Exception as e:
                return HealthCheckResult(
                    name="disk",
                    status=HealthStatus.UNKNOWN,
                    response_time_ms=0,
                    message=f"Disk check failed: {str(e)}"
                )

        def check_event_loop():
            """Check event loop health"""
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    return HealthCheckResult(
                        name="event_loop",
                        status=HealthStatus.HEALTHY,
                        response_time_ms=0,
                        message="Event loop running normally"
                    )
                else:
                    return HealthCheckResult(
                        name="event_loop",
                        status=HealthStatus.UNHEALTHY,
                        response_time_ms=0,
                        message="Event loop not running"
                    )
            except Exception as e:
                return HealthCheckResult(
                    name="event_loop",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    message=f"Event loop check failed: {str(e)}"
                )

        # Register the checks
        self.health_checker.register_check("memory", check_memory_usage, timeout=5.0)
        self.health_checker.register_check("disk", check_disk_space, timeout=5.0)
        self.health_checker.register_check("event_loop", check_event_loop, timeout=2.0)

    def get_circuit_breaker(
        self,
        name: str,
        config: CircuitBreakerConfig = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker"""
        if name not in self.circuit_breakers:
            if config is None:
                config = CircuitBreakerConfig()
            self.circuit_breakers[name] = CircuitBreaker(name, config)

        return self.circuit_breakers[name]

    def record_error(
        self,
        exception: Exception,
        context: ErrorContext,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM
    ):
        """Record an error in the system"""
        self.error_collector.record_error(exception, context, severity)

    async def start_monitoring(self):
        """Start background monitoring"""
        if self._monitoring_task is None or self._monitoring_task.done():
            self._monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Error handling system monitoring started")

    async def stop_monitoring(self):
        """Stop background monitoring"""
        if self._monitoring_task and not self._monitoring_task.done():
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Error handling system monitoring stopped")

    async def _monitoring_loop(self):
        """Background monitoring loop"""
        monitor_interval = self.config.get("error_handling.monitor_interval", 60)

        while True:
            try:
                # Run health checks
                await self.health_checker.run_all_checks()

                # Check for error patterns
                error_summary = self.error_collector.get_error_summary()
                if error_summary["error_rate"] > self.config.get("error_handling.alert_threshold", 10):
                    logger.warning(f"High error rate detected: {error_summary['error_rate']:.1f} errors/min")

                # Log circuit breaker statuses
                for name, breaker in self.circuit_breakers.items():
                    status = breaker.get_status()
                    if status["state"] != "closed":
                        logger.warning(f"Circuit breaker '{name}' is {status['state']}")

                await asyncio.sleep(monitor_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                await asyncio.sleep(monitor_interval)

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        return {
            "health": self.health_checker.get_system_health(),
            "errors": self.error_collector.get_error_summary(),
            "circuit_breakers": {
                name: breaker.get_status()
                for name, breaker in self.circuit_breakers.items()
            },
            "timestamp": time.time()
        }

# Global instance
_error_handling_system = None

def get_error_handling_system(config: Config = None) -> ErrorHandlingSystem:
    """Get singleton error handling system instance"""
    global _error_handling_system
    if _error_handling_system is None:
        if config is None:
            config = Config()
        _error_handling_system = ErrorHandlingSystem(config)
    return _error_handling_system

# Convenience decorators
def with_error_handling(
    operation: str,
    component: str,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
):
    """Decorator to add error handling to a function"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            context = ErrorContext(operation=operation, component=component)
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                error_system = get_error_handling_system()
                error_system.record_error(e, context, severity)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator