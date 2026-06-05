# SPDX-License-Identifier: Apache-2.0
"""
mindx_backend_service.overlord — the mindX (Python) authority for the
overlord/overseer privilege model. A faithful mirror of the canonical agnostic
module @openagents/overlord (openagents/overlord/) — KEEP IN SYNC.

Additive: the whole subsystem is gated by MINDX_OVERLORD_ENABLED=1. The existing
/admin/shadow/* shadow-overlord gate is untouched, so destructive vault/cabinet/
key-release operations stay overlord-only throughout the cut-over.
"""
from fastapi import Header, HTTPException

from .config import (
    HoldingConfig,
    LevelBand,
    OverlordConfig,
    is_enabled,
    load_config,
)
from .resolver import (
    DESTRUCTIVE,
    can,
    is_privileged,
    member_level,
    resolve_privilege,
)
from .routes import (
    OVERLORD_SESSION_SCOPE,
    issue_overlord_token,
    overlord_router,
    verify_overlord_token,
)

__all__ = [
    "OverlordConfig",
    "HoldingConfig",
    "LevelBand",
    "is_enabled",
    "load_config",
    "resolve_privilege",
    "can",
    "is_privileged",
    "member_level",
    "DESTRUCTIVE",
    "overlord_router",
    "issue_overlord_token",
    "verify_overlord_token",
    "OVERLORD_SESSION_SCOPE",
    "require_overlord",
]


def require_overlord(action: str = "read.member", min_role: str = "member"):
    """FastAPI dependency for NEW overlord-aware endpoints: require a valid
    overlord-session token whose role can perform `action`. Destructive actions
    are overlord-only via `can(...)`. Does NOT touch the legacy shadow gate."""
    from .resolver import ROLE_ORDINAL

    async def _dep(authorization: str = Header(default="")):
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="missing bearer token")
        claims = verify_overlord_token(authorization[7:])
        role = str(claims.get("role", "public"))
        if ROLE_ORDINAL.get(role, 0) < ROLE_ORDINAL.get(min_role, 1):
            raise HTTPException(status_code=403, detail=f"requires role >= {min_role}")
        if not can(role, action):
            raise HTTPException(status_code=403, detail=f"role {role} cannot {action}")
        return claims

    return _dep
