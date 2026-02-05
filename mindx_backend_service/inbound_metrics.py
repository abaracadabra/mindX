# mindx_backend_service/inbound_metrics.py
"""
Inbound request metrics and optional rate control.

Whether mindX is ingesting or providing inference or services, monitoring and rate
control are essential in both directions. This module records actual network and
data metrics (latency in ms, payload size in bytes, throughput in req/s or req/min)
for incoming API requests and optionally enforces inbound rate limits.
See docs/monitoring_rate_control.md for scientific metric definitions.
"""

import time
from collections import deque
from typing import Dict, Any, Optional
from dataclasses import dataclass, field, asdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from utils.logging_config import get_logger
from utils.config import Config, PROJECT_ROOT

logger = get_logger(__name__)

# Defaults: optional inbound rate limit (req/min); 0 = no limit
DEFAULT_INBOUND_RPM = 0
DEFAULT_INBOUND_WINDOW_S = 60


@dataclass
class InboundMetrics:
    """Actual network and data metrics for inbound requests (scientific units)."""
    total_requests: int = 0
    total_latency_ms: float = 0.0
    total_request_bytes: int = 0
    total_response_bytes: int = 0
    latencies_ms: deque = field(default_factory=lambda: deque(maxlen=200))
    requests_in_window: list = field(default_factory=list)  # timestamps for req/min
    rate_limit_rejects: int = 0

    def record(self, latency_ms: float, request_bytes: int, response_bytes: int) -> None:
        self.total_requests += 1
        self.total_latency_ms += latency_ms
        self.total_request_bytes += request_bytes
        self.total_response_bytes += response_bytes
        self.latencies_ms.append(latency_ms)
        self.requests_in_window.append(time.time())

    def reject_rate_limit(self) -> None:
        self.rate_limit_rejects += 1

    def _trim_window(self, window_s: float) -> None:
        cutoff = time.time() - window_s
        self.requests_in_window[:] = [t for t in self.requests_in_window if t > cutoff]

    def get_metrics(self, window_s: float = 60.0) -> Dict[str, Any]:
        """Return metrics with scientific units: ms, bytes, req/min (actual network and data metrics)."""
        self._trim_window(window_s)
        n = len(self.latencies_ms)
        lat_list = sorted(list(self.latencies_ms))
        return {
            "total_requests": self.total_requests,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "average_latency_ms": round(self.total_latency_ms / self.total_requests, 2) if self.total_requests else 0,
            "total_request_bytes": self.total_request_bytes,
            "total_response_bytes": self.total_response_bytes,
            "requests_per_minute": len(self.requests_in_window),
            "rate_limit_rejects": self.rate_limit_rejects,
            "latency_p50_ms": round(lat_list[int(n * 0.5)], 2) if n else 0,
            "latency_p90_ms": round(lat_list[int(n * 0.9)], 2) if n else 0,
            "latency_p99_ms": round(lat_list[min(int(n * 0.99), n - 1)], 2) if n else 0,
            "window_s": window_s,
        }


_inbound_metrics: Optional[InboundMetrics] = None
_inbound_rpm_limit: int = 0
_inbound_window_s: float = 60.0


def get_inbound_metrics() -> InboundMetrics:
    global _inbound_metrics
    if _inbound_metrics is None:
        _inbound_metrics = InboundMetrics()
    return _inbound_metrics


def set_inbound_rate_limit(requests_per_minute: int = 0, window_s: float = 60.0) -> None:
    """Set optional inbound rate limit. 0 = no limit."""
    global _inbound_rpm_limit, _inbound_window_s
    _inbound_rpm_limit = max(0, requests_per_minute)
    _inbound_window_s = max(1.0, window_s)


def get_inbound_rate_limit() -> tuple:
    return _inbound_rpm_limit, _inbound_window_s


class InboundMetricsMiddleware(BaseHTTPMiddleware):
    """Records per-request latency (ms), request/response body size (bytes), and optional inbound rate limit."""

    async def dispatch(self, request: Request, call_next) -> Response:
        global _inbound_rpm_limit, _inbound_window_s
        metrics = get_inbound_metrics()
        # Optional rate limit (inbound)
        if _inbound_rpm_limit > 0:
            metrics._trim_window(_inbound_window_s)
            if len(metrics.requests_in_window) >= _inbound_rpm_limit:
                metrics.reject_rate_limit()
                return Response(
                    content='{"detail":"Inbound rate limit exceeded"}',
                    status_code=429,
                    media_type="application/json",
                )
        # Body size (approximate: content-length or 0)
        request_bytes = 0
        if request.headers.get("content-length"):
            try:
                request_bytes = int(request.headers["content-length"])
            except ValueError:
                pass
        start = time.perf_counter()
        response = await call_next(request)
        latency_ms = (time.perf_counter() - start) * 1000
        response_bytes = 0
        if hasattr(response, "body"):
            response_bytes = len(response.body) if response.body else 0
        elif response.headers.get("content-length"):
            try:
                response_bytes = int(response.headers["content-length"])
            except ValueError:
                pass
        metrics.record(latency_ms, request_bytes, response_bytes)
        return response
