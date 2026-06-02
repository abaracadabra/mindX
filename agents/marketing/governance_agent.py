"""
governance_agent — brand-code enforcement + Boardroom routing + Tessera attestation.

Refuse → Route → Attest. The conscience of the cabinet.

Boardroom routing uses the existing daio.governance.boardroom.Boardroom
session if available (production); otherwise a no-op stub. The choice is
runtime — operator decides when Boardroom is wired into marketing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional

from agents.marketing.content_agent import ContentDraft, RefusedDraft
from agents.marketing.tools.brand_code import BrandCode


# Status constants used in marketing.* catalogue events.
STATUS_OK = "OK"
STATUS_REFUSED_VOICE = "REFUSED_VOICE"
STATUS_REFUSED_REGULATORY = "REFUSED_REGULATORY"
STATUS_REFUSED_IDENTITY = "REFUSED_IDENTITY"
STATUS_REGISTRATION_PENDING = "REGISTRATION_PENDING"
STATUS_BOARDROOM_REJECTED = "BOARDROOM_REJECTED"


@dataclass
class GovernanceVerdict:
    status: str
    reason: str = ""
    detail: str = ""
    routed_to_boardroom: bool = False
    boardroom_session_id: Optional[str] = None


@dataclass
class GovernanceConfig:
    spend_threshold_usd: float = 500.0
    hard_stop_spend_usd: float = 5000.0
    convener_required_pillars: List[str] = field(default_factory=lambda: ["code_as_dojo"])
    convener_required_audiences: List[str] = field(default_factory=lambda: ["E"])


class GovernanceAgent:
    AGENT_ID = "marketinga.governance"
    DID = "did:pythai:marketinga.governance"
    ENS = "governance.marketinga.bankon.eth"

    def __init__(
        self,
        config: GovernanceConfig,
        *,
        boardroom_session_runner=None,
        tessera_client=None,
        identity_resolver=None,
    ) -> None:
        """boardroom_session_runner: optional async callable
            (directive: str, importance: str) -> {session_id: str, outcome: str}
        tessera_client: optional sync/async object with `attest(payload) -> credential_id`
        identity_resolver: optional sync callable () -> dict with keys
            {"did_present": bool, "censura_faded": bool}
        """
        self.config = config
        self.boardroom_session_runner = boardroom_session_runner
        self.tessera_client = tessera_client
        self.identity_resolver = identity_resolver

    def review_draft(self, brand: BrandCode, draft) -> GovernanceVerdict:
        if isinstance(draft, RefusedDraft):
            # Map content_a refusals to governance statuses.
            mapping = {
                "founder_only_pillar": STATUS_REFUSED_VOICE,
                "founder_only_audience": STATUS_REFUSED_VOICE,
                "voice_violation": STATUS_REFUSED_VOICE,
                "no_inference_path": STATUS_REFUSED_REGULATORY,  # treated as system unfit
            }
            status = mapping.get(draft.reason, STATUS_REFUSED_VOICE)
            return GovernanceVerdict(status=status, reason=draft.reason, detail=draft.detail)
        if not isinstance(draft, ContentDraft):
            return GovernanceVerdict(
                status=STATUS_REFUSED_VOICE,
                reason="unknown_draft_type",
                detail=type(draft).__name__,
            )
        # Defense-in-depth voice scan
        deny, _ = brand.forbidden.scan(draft.text)
        if deny:
            return GovernanceVerdict(
                status=STATUS_REFUSED_VOICE,
                reason="voice_violation",
                detail="; ".join(deny),
            )
        return GovernanceVerdict(status=STATUS_OK)

    def check_identity(self) -> GovernanceVerdict:
        if self.identity_resolver is None:
            # No resolver → identity unknown; emit pending so the operator binds.
            return GovernanceVerdict(status=STATUS_REGISTRATION_PENDING)
        try:
            state = dict(self.identity_resolver() or {})
        except Exception as exc:
            return GovernanceVerdict(
                status=STATUS_REGISTRATION_PENDING,
                reason="identity_resolver_error",
                detail=repr(exc),
            )
        if state.get("censura_faded"):
            return GovernanceVerdict(status=STATUS_REFUSED_IDENTITY, reason="censura_faded")
        if not state.get("did_present"):
            return GovernanceVerdict(status=STATUS_REGISTRATION_PENDING)
        return GovernanceVerdict(status=STATUS_OK)

    async def route_spend(self, total_spend_usd: float, importance: str = "standard") -> GovernanceVerdict:
        if total_spend_usd >= self.config.hard_stop_spend_usd:
            return GovernanceVerdict(
                status=STATUS_REFUSED_REGULATORY,
                reason="hard_stop_spend",
                detail=f"forecast ${total_spend_usd:.2f} ≥ hard stop ${self.config.hard_stop_spend_usd:.2f}",
            )
        if total_spend_usd <= self.config.spend_threshold_usd:
            return GovernanceVerdict(status=STATUS_OK)
        if self.boardroom_session_runner is None:
            # Above threshold but no runner wired — defer to Convener.
            return GovernanceVerdict(
                status=STATUS_REGISTRATION_PENDING,
                reason="boardroom_not_wired",
                detail=f"forecast ${total_spend_usd:.2f} > threshold ${self.config.spend_threshold_usd:.2f}",
            )
        try:
            outcome = await self.boardroom_session_runner(
                f"approve marketing spend ${total_spend_usd:.2f}",
                importance,
            )
            outcome = dict(outcome or {})
            session_id = outcome.get("session_id")
            decided = (outcome.get("outcome") or "").lower()
            if decided == "approved":
                return GovernanceVerdict(
                    status=STATUS_OK,
                    routed_to_boardroom=True,
                    boardroom_session_id=session_id,
                )
            return GovernanceVerdict(
                status=STATUS_BOARDROOM_REJECTED,
                routed_to_boardroom=True,
                boardroom_session_id=session_id,
                reason=f"boardroom_outcome={decided}",
            )
        except Exception as exc:
            return GovernanceVerdict(
                status=STATUS_REGISTRATION_PENDING,
                reason="boardroom_runner_error",
                detail=repr(exc),
            )

    async def attest(self, payload: Any) -> Optional[str]:
        if self.tessera_client is None:
            return None
        try:
            attest_fn = getattr(self.tessera_client, "attest", None)
            if attest_fn is None:
                return None
            result = attest_fn(payload)
            if hasattr(result, "__await__"):
                result = await result
            return str(result) if result is not None else None
        except Exception:
            return None


__all__ = [
    "GovernanceAgent",
    "GovernanceConfig",
    "GovernanceVerdict",
    "STATUS_OK",
    "STATUS_REFUSED_VOICE",
    "STATUS_REFUSED_REGULATORY",
    "STATUS_REFUSED_IDENTITY",
    "STATUS_REGISTRATION_PENDING",
    "STATUS_BOARDROOM_REJECTED",
]
