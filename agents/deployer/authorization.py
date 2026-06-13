"""
Hierarchical participant authorization for deploys.

The UI wallet authorizes a deploy by signing a challenge; the recovered signer
is mapped to a mindX participant entity, whose dojo verification tier and
per-entity rules in `data/governance/deployment_authorization.json` decide
whether the deploy may proceed and whether it needs operator confirmation.

Fails CLOSED: if the authorization file is missing/empty, a conservative
default (`min_tier: tier2`, low rate limit) applies — never open.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from utils.config import PROJECT_ROOT
from utils.logging_config import get_logger

logger = get_logger(__name__)

AUTHZ_PATH = os.path.join(str(PROJECT_ROOT), "data", "governance", "deployment_authorization.json")
AGENT_MAP_PATH = os.path.join(str(PROJECT_ROOT), "daio", "agents", "agent_map.json")
REGISTRY_PATH = os.path.join(str(PROJECT_ROOT), "data", "identity", "production_registry.json")
INTENTS_DIR = os.path.join(str(PROJECT_ROOT), "data", "governance", "deploy_intents")

# fail-closed default applied when the authz file is absent
DEFAULT_AUTHZ = {"default": {"min_tier": "tier2", "rate_limit_per_hour": 3}, "entities": {},
                 "mainnet_required_approvers": []}


def tier_to_int(tier: str) -> int:
    try:
        return int(str(tier).replace("tier", ""))
    except (ValueError, TypeError):
        return 0


@dataclass
class AuthDecision:
    allowed: bool
    reason: str
    entity_id: Optional[str]
    tier: int
    requires_operator_confirm: bool = False


def _load_json(path: str) -> Optional[dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def map_signer_to_entity(address: str) -> Tuple[Optional[str], int]:
    """Recovered EVM address -> (entity_id, static_verification_tier).

    Primary: daio/agents/agent_map.json (agents + soldiers carry eth_address +
    verification_tier inline). Fallback: data/identity/production_registry.json.
    Returns (None, 0) when no participant matches.
    """
    addr = (address or "").lower()
    if not addr:
        return None, 0
    amap = _load_json(AGENT_MAP_PATH) or {}
    for bucket in ("agents", "soldiers"):
        for entity_id, rec in (amap.get(bucket) or {}).items():
            if str(rec.get("eth_address", "")).lower() == addr:
                return entity_id, int(rec.get("verification_tier", 0))
    reg = _load_json(REGISTRY_PATH) or {}
    for rec in reg.get("agents", []):
        if str(rec.get("address", "")).lower() == addr:
            return rec.get("entity_id"), 0
    return None, 0


async def live_tier(entity_id: str, static_tier: int) -> int:
    """Live dojo verification tier; falls back to the static agent_map tier."""
    try:
        from daio.governance.dojo import Dojo

        dojo = await Dojo.get_instance()
        rep = dojo.get_agent_reputation(entity_id)
        return int(rep.get("verification_tier", static_tier))
    except Exception as e:  # pragma: no cover - dojo optional
        logger.debug(f"dojo tier lookup failed for {entity_id}: {e}")
        return static_tier


class DeploymentAuthorization:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg or DEFAULT_AUTHZ

    @classmethod
    def load(cls) -> "DeploymentAuthorization":
        cfg = _load_json(AUTHZ_PATH)
        if not cfg:
            logger.warning("deployment_authorization.json missing/empty — applying fail-closed default")
            cfg = DEFAULT_AUTHZ
        return cls(cfg)

    def _entity_rules(self, entity_id: Optional[str]) -> Dict[str, Any]:
        ents = self.cfg.get("entities", {})
        return ents.get(entity_id or "", {}) or {}

    def _recent_intent_count(self, entity_id: str, window_s: int = 3600) -> int:
        if not os.path.isdir(INTENTS_DIR):
            return 0
        cutoff = time.time() - window_s
        n = 0
        for fn in os.listdir(INTENTS_DIR):
            if not fn.endswith(".json"):
                continue
            data = _load_json(os.path.join(INTENTS_DIR, fn)) or {}
            if data.get("entity_id") == entity_id and float(data.get("created_at", 0)) >= cutoff:
                n += 1
        return n

    def check(self, *, recovered_signer: str, entity_id: Optional[str], tier: int,
              chain: str, required_min_tier: str, is_mainnet: bool,
              manifest_approvers: Optional[list] = None) -> AuthDecision:
        if not entity_id:
            return AuthDecision(False, f"signer {recovered_signer} maps to no known participant", None, tier)

        rules = self._entity_rules(entity_id)
        # required tier = max(manifest, entity-rule, global default)
        req = max(
            tier_to_int(required_min_tier),
            tier_to_int(rules.get("min_tier", self.cfg.get("default", {}).get("min_tier", "tier2"))),
        )
        if tier < req:
            return AuthDecision(False, f"tier {tier} < required tier{req}", entity_id, tier)

        # chain allow-list (if the entity declares one)
        allowed_chains = rules.get("authorized_chains")
        if allowed_chains is not None and chain not in allowed_chains:
            return AuthDecision(False, f"entity {entity_id} not authorized for chain {chain}", entity_id, tier)

        # rate limit
        limit = int(rules.get("rate_limit_per_hour", self.cfg.get("default", {}).get("rate_limit_per_hour", 3)))
        if self._recent_intent_count(entity_id) >= limit:
            return AuthDecision(False, f"rate limit {limit}/h exceeded for {entity_id}", entity_id, tier)

        # mainnet co-approval requirement (operator confirm still enforced at confirm step)
        requires_confirm = is_mainnet
        if is_mainnet:
            approvers = set(self.cfg.get("mainnet_required_approvers", [])) | set(manifest_approvers or [])
            if approvers:
                requires_confirm = True  # surfaced; operator/admin gate handles enforcement

        return AuthDecision(True, "authorized", entity_id, tier, requires_operator_confirm=requires_confirm)
