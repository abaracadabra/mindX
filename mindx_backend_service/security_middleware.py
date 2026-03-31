"""
Production Security Middleware for mindX
Implements authentication, rate limiting, and security headers
"""

import time
import asyncio
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, Set, Optional, Tuple
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
import re

from utils.logging_config import get_logger
from utils.config import Config

logger = get_logger(__name__)

class SecurityConfig:
    """Security configuration management"""

    def __init__(self, config: Config):
        self.config = config
        self.allowed_origins = self._get_allowed_origins()
        self.rate_limits = self._get_rate_limits()
        self.protected_endpoints = self._get_protected_endpoints()

    def _get_allowed_origins(self) -> Set[str]:
        """Get allowed CORS origins from configuration"""
        origins_str = self.config.get("security.cors.allowed_origins", "https://agenticplace.pythai.net,https://localhost:3000")
        origins = [origin.strip() for origin in origins_str.split(",")]

        # Add development origins if in dev mode
        if self.config.get("security.development_mode", False):
            origins.extend(["http://localhost:8000", "http://127.0.0.1:8000"])

        return set(origins)

    def _get_rate_limits(self) -> Dict[str, Tuple[int, int]]:
        """Get rate limits: endpoint_pattern -> (requests, window_seconds)"""
        return {
            "/commands/": (10, 60),      # 10 requests per minute for commands
            "/agents/": (20, 60),        # 20 requests per minute for agent operations
            "/users/": (15, 60),         # 15 requests per minute for user operations
            "/vault/": (30, 60),         # 30 requests per minute for vault operations
            "/coordinator/": (5, 60),    # 5 requests per minute for coordinator
            "default": (100, 60)         # Default rate limit
        }

    def _get_protected_endpoints(self) -> Set[str]:
        """Get endpoints that require authentication"""
        return {
            "/commands/",
            "/agents/",
            "/coordinator/",
            "/github/",
            "/users/register",
            "/users/agents",
            "/vault/",
            "/identities"
        }

class RateLimitTracker:
    """Thread-safe rate limiting tracker"""

    def __init__(self):
        self.requests: Dict[str, Dict[str, int]] = {}
        self.locks: Dict[str, asyncio.Lock] = {}
        self.last_cleanup = time.time()

    async def is_rate_limited(self, client_id: str, endpoint_pattern: str,
                            max_requests: int, window_seconds: int) -> bool:
        """Check if client is rate limited for the endpoint"""
        now = time.time()
        window_start = int(now // window_seconds) * window_seconds

        # Get or create lock for this client
        if client_id not in self.locks:
            self.locks[client_id] = asyncio.Lock()

        async with self.locks[client_id]:
            if client_id not in self.requests:
                self.requests[client_id] = {}

            key = f"{endpoint_pattern}:{window_start}"
            current_requests = self.requests[client_id].get(key, 0)

            if current_requests >= max_requests:
                return True

            # Increment request count
            self.requests[client_id][key] = current_requests + 1

            # Cleanup old entries periodically
            if now - self.last_cleanup > 300:  # Every 5 minutes
                await self._cleanup_old_entries(now, window_seconds * 2)
                self.last_cleanup = now

            return False

    async def _cleanup_old_entries(self, current_time: float, cutoff_seconds: int):
        """Remove old rate limit entries"""
        cutoff_time = current_time - cutoff_seconds

        for client_id in list(self.requests.keys()):
            client_requests = self.requests[client_id]
            keys_to_remove = []

            for key in client_requests:
                try:
                    window_time = float(key.split(':')[-1])
                    if window_time < cutoff_time:
                        keys_to_remove.append(key)
                except (ValueError, IndexError):
                    keys_to_remove.append(key)  # Remove malformed keys

            for key in keys_to_remove:
                del client_requests[key]

            # Remove empty client entries
            if not client_requests:
                del self.requests[client_id]
                if client_id in self.locks:
                    del self.locks[client_id]

class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware"""

    def __init__(self, app, config: Config):
        super().__init__(app)
        self.security_config = SecurityConfig(config)
        self.rate_limiter = RateLimitTracker()

    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier for rate limiting"""
        # Try to get from session token first
        session_token = request.headers.get("X-Session-Token")
        if session_token:
            return f"session:{session_token[:16]}"

        # Fall back to IP address
        client_ip = self._get_client_ip(request)
        return f"ip:{client_ip}"

    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP address"""
        # Check for proxy headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fall back to direct connection IP
        return request.client.host if request.client else "unknown"

    def _match_endpoint_pattern(self, path: str) -> str:
        """Match request path to endpoint pattern for rate limiting"""
        for pattern in self.security_config.rate_limits:
            if pattern != "default" and path.startswith(pattern):
                return pattern
        return "default"

    def _is_protected_endpoint(self, path: str) -> bool:
        """Check if endpoint requires authentication"""
        for pattern in self.security_config.protected_endpoints:
            if path.startswith(pattern):
                return True
        return False

    def _add_security_headers(self, response: Response) -> Response:
        """Add security headers to response"""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"

        # Don't cache sensitive endpoints
        if self._is_protected_endpoint(response.headers.get("request-path", "")):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"

        return response

    async def dispatch(self, request: Request, call_next):
        """Main security middleware logic"""
        start_time = time.time()
        path = request.url.path
        method = request.method

        # Skip security for health checks and public endpoints
        if path in ["/", "/docs", "/redoc", "/openapi.json", "/health"]:
            response = await call_next(request)
            return self._add_security_headers(response)

        try:
            # Rate limiting
            client_id = self._get_client_id(request)
            endpoint_pattern = self._match_endpoint_pattern(path)

            rate_config = self.security_config.rate_limits.get(endpoint_pattern,
                                                             self.security_config.rate_limits["default"])
            max_requests, window_seconds = rate_config

            if await self.rate_limiter.is_rate_limited(client_id, endpoint_pattern,
                                                     max_requests, window_seconds):
                logger.warning(f"Rate limit exceeded for {client_id} on {path}")
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "Rate limit exceeded",
                        "message": f"Maximum {max_requests} requests per {window_seconds} seconds",
                        "retry_after": window_seconds
                    },
                    headers={"Retry-After": str(window_seconds)}
                )

            # CORS validation for non-OPTIONS requests
            origin = request.headers.get("origin")
            if origin and origin not in self.security_config.allowed_origins:
                if method != "OPTIONS":  # Allow preflight requests
                    logger.warning(f"CORS violation: {origin} not in allowed origins")
                    return JSONResponse(
                        status_code=403,
                        content={"error": "Origin not allowed", "origin": origin}
                    )

            # Request validation
            if method in ["POST", "PUT", "PATCH"]:
                content_type = request.headers.get("content-type", "")
                if not content_type.startswith(("application/json", "multipart/form-data")):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "Invalid content type", "expected": "application/json"}
                    )

            # Process request
            response = await call_next(request)

            # Add security headers
            response = self._add_security_headers(response)

            # Log security events
            processing_time = time.time() - start_time
            if processing_time > 5.0:  # Log slow requests
                logger.warning(f"Slow request: {method} {path} took {processing_time:.2f}s")

            return response

        except Exception as e:
            logger.error(f"Security middleware error for {method} {path}: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"error": "Internal security error"}
            )

class AuthenticationManager:
    """Manages authentication for protected endpoints"""

    def __init__(self, config: Config):
        self.config = config

    async def verify_session_token(self, token: str) -> Optional[Dict]:
        """Verify session token and return session data"""
        try:
            from mindx_backend_service.vault_manager import get_vault_manager
            vault = get_vault_manager()
            session = vault.get_user_session(token)
            return session
        except Exception as e:
            logger.error(f"Session verification failed: {e}")
            return None

    async def verify_signature(self, wallet_address: str, message: str, signature: str) -> bool:
        """Verify wallet signature"""
        try:
            from agents.core.id_manager_agent import IDManagerAgent
            from agents.core.belief_system import BeliefSystem

            belief_system = BeliefSystem()
            id_manager = await IDManagerAgent.get_instance("security_verification", belief_system=belief_system)

            # Verify the signature
            return await id_manager.verify_message_signature(wallet_address, message, signature)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False

# Security dependency functions
security_manager = AuthenticationManager(Config())

async def require_valid_session(request: Request) -> str:
    """Dependency to require valid session token"""
    token = request.headers.get("X-Session-Token") or request.query_params.get("session_token")

    if not token:
        raise HTTPException(status_code=401, detail="Missing session token")

    session = await security_manager.verify_session_token(token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired session")

    return session["wallet_address"]

async def require_admin_access(wallet_address: str = Depends(require_valid_session)) -> str:
    """Dependency to require admin access"""
    config = Config()
    admin_addresses = set(config.get("security.admin_addresses", "").split(","))

    if wallet_address not in admin_addresses:
        raise HTTPException(status_code=403, detail="Admin access required")

    return wallet_address

def create_api_key_auth() -> HTTPBearer:
    """Create API key authentication scheme"""
    return HTTPBearer(scheme_name="API Key")

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(create_api_key_auth())) -> bool:
    """Verify API key for service-to-service authentication"""
    config = Config()
    valid_api_keys = set(config.get("security.api_keys", "").split(","))

    if not valid_api_keys or credentials.credentials not in valid_api_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return True