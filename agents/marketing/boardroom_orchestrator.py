"""
MarketingBoardroomOrchestrator — drives the boardroom for a marketing campaign,
then dispatches the per-soldier marketing skill on each `approve` vote.

Pipeline:
  1. CEO composes the CampaignBrief from upstream goal text.
  2. CEO formats the boardroom directive.
  3. `Boardroom.convene(directive, members="ceo,cpo,cto,coo,cfo,ciso,clo,cro")`
  4. Hard veto: if CISO or CRO vote `reject`, refuse the campaign immediately.
  5. Dispatch skills in `DISPATCH_ORDER` for each soldier whose vote was
     `approve` (and a skill is registered).
  6. Aggregate per-soldier outputs into `CampaignEnvelope` (now with
     `boardroom_session_id`).
  7. Per-soldier Tessera credential issuance (one per executing soldier).
  8. CEO signs + submits the `MarketingAttributionReceipt`.

Catalogue events fire at every boundary (`marketing.campaign_proposed`,
`marketing.boardroom_routed`, `marketing.soldier_skill_executed`,
`marketing.tessera_attested`, `marketing.campaign_executed`).

Soldier voting semantics in `Boardroom.convene` are unchanged. This
orchestrator is a wrapper *above* the boardroom, not inside it.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from agents.marketing.content_agent import CampaignBrief
from agents.marketing.skills.ceo import CeoSkill
from agents.marketing.skills.protocol import (
    DirectivePromptParts,
    LLMCaller,
    SkillOutput,
    SkillRefusal,
    SoldierSkill,
)
from agents.marketing.skills.registry import (
    DISPATCH_ORDER,
    VETO_SOLDIERS,
    build_registry,
)
from agents.marketing.tools.brand_code import BrandCode, load_brand_code
from agents.marketing.tools.llms_txt_writer import SiteEntry


@dataclass
class CampaignEnvelope:
    """Mirrors the on-chain MarketingCampaign struct (now with boardroomSessionId)."""
    campaign_id: str
    brief_cid: str
    audience_cluster_hash: str
    channel_set_mask: int
    total_spend_usd_micro: int
    outcome_metric_cid: str
    boardroom_session_id: str
    trace_id: str
    signed_at: float = field(default_factory=time.time)


@dataclass
class CampaignResult:
    envelope: CampaignEnvelope
    boardroom_session_id: str
    boardroom_outcome: str                                    # "approved" | "rejected" | "exploration"
    weighted_score: float
    soldier_votes: List[Dict[str, Any]] = field(default_factory=list)   # subset of SoldierVote serialized
    skill_outputs: Dict[str, Any] = field(default_factory=dict)         # soldier_id → SkillOutput | SkillRefusal
    tessera_credentials: List[Dict[str, Any]] = field(default_factory=list)
    refusal: Optional[Dict[str, Any]] = None                  # set if veto'd or all skills refused


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _trace_id(campaign_id: str, soldier_id: str, step: str) -> str:
    return _hash(f"{campaign_id}|{soldier_id}|{step}")


def _audience_cluster_hash(rings: List[str]) -> str:
    return _hash(",".join(sorted(rings)))


def _brief_cid(brief: CampaignBrief) -> str:
    return _hash(f"{brief.campaign_id}|{brief.title}|{brief.pillar}|{brief.summary}")


async def _emit(kind: str, actor: str, payload: Dict[str, Any], **kw) -> None:
    try:
        from agents.catalogue.events import emit_catalogue_event  # type: ignore
        await emit_catalogue_event(
            kind=kind,
            actor=actor,
            payload=payload,
            source_log="marketing.orchestrator",
            **kw,
        )
    except Exception:
        pass


def _serialize_vote(vote) -> Dict[str, Any]:
    """SoldierVote → dict (defensive in case the upstream type evolves)."""
    return {
        "soldier_id": getattr(vote, "soldier_id", None),
        "vote": getattr(vote, "vote", None),
        "reasoning": getattr(vote, "reasoning", "")[:240],
        "confidence": getattr(vote, "confidence", 0.0),
        "weight": getattr(vote, "weight", 1.0),
        "provider": getattr(vote, "provider", None),
    }


def _serialize_skill_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, SkillRefusal):
        return {"kind": "refusal", "reason": result.reason, "detail": result.detail}
    if isinstance(result, SkillOutput):
        artifact = result.artifact
        try:
            from dataclasses import is_dataclass
            if is_dataclass(artifact):
                artifact = asdict(artifact)
        except Exception:
            pass
        if not isinstance(artifact, (dict, list, str, int, float, bool, type(None))):
            artifact = {"_repr": type(artifact).__name__}
        return {"kind": "output", "artifact": artifact, "notes": result.notes}
    return {"kind": "unknown", "_repr": type(result).__name__}


class MarketingBoardroomOrchestrator:
    """Singleton orchestrator. The boardroom is the cabinet."""

    _instance: Optional["MarketingBoardroomOrchestrator"] = None
    _lock = asyncio.Lock()

    AGENT_ID = "marketinga"
    DID = "did:pythai:marketinga"
    ENS = "marketinga.bankon.eth"

    def __init__(
        self,
        brand_code: BrandCode,
        toml_config: Dict[str, Any],
        registry: Dict[str, SoldierSkill],
        *,
        boardroom: Any,
        tessera_client: Any = None,
        attribution_receipt_client: Any = None,
        domain: str = "marketing.umbrella",
        data_root: Optional[Path] = None,
    ) -> None:
        self.brand = brand_code
        self.toml = toml_config
        self.registry = registry
        self.boardroom = boardroom
        self.tessera_client = tessera_client
        self.attribution_receipt_client = attribution_receipt_client
        self.domain = domain
        self.data_root = Path(data_root) if data_root else Path("data")
        self._cycle_count = 0
        self._last_summary: Dict[str, Any] = {}

    @classmethod
    async def get_instance(
        cls,
        brand_code_root: Path,
        toml_config_path: Path,
        registry: Dict[str, SoldierSkill],
        *,
        boardroom: Any,
        tessera_client: Any = None,
        attribution_receipt_client: Any = None,
        domain: str = "marketing.umbrella",
        data_root: Optional[Path] = None,
        test_mode: bool = False,
    ) -> "MarketingBoardroomOrchestrator":
        async with cls._lock:
            if cls._instance is None or test_mode:
                brand = load_brand_code(Path(brand_code_root))
                with open(toml_config_path, "rb") as fh:
                    toml_cfg = tomllib.load(fh)
                cls._instance = cls(
                    brand_code=brand,
                    toml_config=toml_cfg,
                    registry=registry,
                    boardroom=boardroom,
                    tessera_client=tessera_client,
                    attribution_receipt_client=attribution_receipt_client,
                    domain=domain,
                    data_root=data_root,
                )
            return cls._instance

    @classmethod
    def _reset_for_tests(cls) -> None:
        cls._instance = None

    def status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.AGENT_ID,
            "did": self.DID,
            "ens": self.ENS,
            "domain": self.domain,
            "cycle_count": self._cycle_count,
            "last_cycle": self._last_summary,
            "voice_register": self.brand.voice_register(),
            "brand_code_root": str(self.brand.root),
            "soldier_skills": [
                {
                    "soldier_id": sid,
                    "skill_name": getattr(skill, "SKILL_NAME", None),
                    "weight": getattr(skill, "WEIGHT", 1.0),
                    "hbr_layer": getattr(skill, "HBR_LAYER", None),
                }
                for sid, skill in self.registry.items()
            ],
        }

    async def propose_campaign(
        self,
        brief: CampaignBrief,
        *,
        forecast_spend_usd: float = 0.0,
        channel_set_mask: int = 0b00000111,
        importance: str = "standard",
        members: str = "ceo,cpo,cto,coo,cfo,ciso,clo,cro",
        consensus: float = 0.666,
    ) -> CampaignResult:
        self._cycle_count += 1

        # Update CRO with this campaign's forecast (per-call config)
        if "cro_risk" in self.registry:
            cro = self.registry["cro_risk"]
            if hasattr(cro, "forecast_spend_usd"):
                cro.forecast_spend_usd = float(forecast_spend_usd)

        await _emit(
            "marketing.campaign_proposed",
            actor=self.AGENT_ID,
            payload={
                "campaign_id": brief.campaign_id,
                "title": brief.title,
                "pillar": brief.pillar,
                "audience_ring": brief.audience_ring,
                "forecast_spend_usd": forecast_spend_usd,
                "channel_set_mask": channel_set_mask,
            },
        )

        # 1+2+3. CEO formats directive, Boardroom convenes
        directive = CeoSkill.format_boardroom_directive(brief, forecast_spend_usd=forecast_spend_usd)
        try:
            session = await self.boardroom.convene(
                directive=directive,
                importance=importance,
                members=members,
                consensus=consensus,
            )
        except Exception as exc:
            return self._refusal_result(
                brief, channel_set_mask,
                refusal={"reason": "boardroom_convene_failed", "detail": repr(exc)},
                boardroom_session_id="",
                outcome="rejected",
                weighted_score=0.0,
            )

        votes_serialized = [_serialize_vote(v) for v in (session.votes or [])]
        await _emit(
            "marketing.boardroom_routed",
            actor=self.AGENT_ID,
            payload={
                "campaign_id": brief.campaign_id,
                "boardroom_session_id": session.session_id,
                "outcome": session.outcome,
                "weighted_score": session.weighted_score,
                "votes": votes_serialized,
            },
        )

        # 4. Hard veto check — CISO or CRO `reject` short-circuits regardless of score
        veto = self._check_veto(session.votes or [])
        if veto is not None:
            return self._refusal_result(
                brief, channel_set_mask,
                refusal={"reason": "soldier_veto", "soldier": veto},
                boardroom_session_id=session.session_id,
                outcome=session.outcome,
                weighted_score=session.weighted_score,
                votes=votes_serialized,
            )

        # 4b. If overall outcome wasn't approved, refuse
        if session.outcome not in {"approved"}:
            return self._refusal_result(
                brief, channel_set_mask,
                refusal={"reason": "boardroom_outcome", "outcome": session.outcome},
                boardroom_session_id=session.session_id,
                outcome=session.outcome,
                weighted_score=session.weighted_score,
                votes=votes_serialized,
            )

        # 5. Dispatch skills in canonical order for soldiers who voted approve
        approving = {v.soldier_id for v in (session.votes or []) if getattr(v, "vote", None) == "approve"}
        prior_outputs: Dict[str, Any] = {}
        skill_outputs: Dict[str, Any] = {}
        tessera_creds: List[Dict[str, Any]] = []

        for soldier_id in DISPATCH_ORDER:
            if soldier_id not in approving:
                continue
            skill = self.registry.get(soldier_id)
            if skill is None:
                continue
            try:
                result = await skill.execute_if_approved(brief, self.brand, prior_outputs)
            except Exception as exc:
                result = SkillRefusal(soldier_id=soldier_id, reason="skill_exception", detail=repr(exc))

            prior_outputs[soldier_id] = result
            skill_outputs[soldier_id] = _serialize_skill_result(result)

            await _emit(
                "marketing.soldier_skill_executed",
                actor=soldier_id,
                payload={
                    "campaign_id": brief.campaign_id,
                    "boardroom_session_id": session.session_id,
                    "soldier_id": soldier_id,
                    "skill_name": getattr(skill, "SKILL_NAME", None),
                    "result": skill_outputs[soldier_id],
                },
            )

            # Per-soldier Tessera credential
            cred = await self._issue_tessera(
                soldier_id=soldier_id,
                campaign_id=brief.campaign_id,
                step=getattr(skill, "SKILL_NAME", "skill"),
                result=skill_outputs[soldier_id],
            )
            if cred is not None:
                tessera_creds.append(cred)

            # If a CISO or CRO skill refuses post-vote (defense-in-depth), short-circuit
            if isinstance(result, SkillRefusal) and soldier_id in VETO_SOLDIERS:
                return self._refusal_result(
                    brief, channel_set_mask,
                    refusal={"reason": "veto_skill_refusal", "soldier": soldier_id, "detail": result.detail},
                    boardroom_session_id=session.session_id,
                    outcome=session.outcome,
                    weighted_score=session.weighted_score,
                    votes=votes_serialized,
                    skill_outputs=skill_outputs,
                    tessera_creds=tessera_creds,
                )

        # 6. Build envelope
        outcome_metric_cid = self._compute_outcome_cid(skill_outputs)
        envelope = CampaignEnvelope(
            campaign_id=brief.campaign_id,
            brief_cid=_brief_cid(brief),
            audience_cluster_hash=_audience_cluster_hash([brief.audience_ring]),
            channel_set_mask=channel_set_mask,
            total_spend_usd_micro=int(forecast_spend_usd * 1_000_000),
            outcome_metric_cid=outcome_metric_cid,
            boardroom_session_id=session.session_id,
            trace_id=_trace_id(brief.campaign_id, "ceo", "submit"),
        )

        # 7+8. CEO submits MarketingAttributionReceipt
        await self._submit_envelope(envelope)

        result = CampaignResult(
            envelope=envelope,
            boardroom_session_id=session.session_id,
            boardroom_outcome=session.outcome,
            weighted_score=session.weighted_score,
            soldier_votes=votes_serialized,
            skill_outputs=skill_outputs,
            tessera_credentials=tessera_creds,
        )
        self._last_summary = {
            "campaign_id": brief.campaign_id,
            "boardroom_session_id": session.session_id,
            "outcome": session.outcome,
            "weighted_score": session.weighted_score,
            "skill_count": len(skill_outputs),
            "tessera_count": len(tessera_creds),
        }
        return result

    def _check_veto(self, votes) -> Optional[str]:
        for v in votes:
            sid = getattr(v, "soldier_id", "")
            if sid in VETO_SOLDIERS and getattr(v, "vote", "") == "reject":
                return sid
        return None

    def _compute_outcome_cid(self, skill_outputs: Dict[str, Any]) -> str:
        # Deterministic hash over the serialized skill outputs.
        # Stable across runs given the same inputs.
        import json as _json
        payload = _json.dumps(skill_outputs, sort_keys=True, default=str).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    async def _issue_tessera(
        self,
        *,
        soldier_id: str,
        campaign_id: str,
        step: str,
        result: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if self.tessera_client is None:
            await _emit(
                "marketing.tessera_attested",
                actor=soldier_id,
                payload={
                    "campaign_id": campaign_id,
                    "soldier_id": soldier_id,
                    "step": step,
                    "status": "REGISTRATION_PENDING",
                },
            )
            return None
        try:
            attest_fn = getattr(self.tessera_client, "attest", None)
            if attest_fn is None:
                return None
            attest = attest_fn(
                holder=f"0x{'0' * 40}",  # placeholder until per-soldier wallet is bound
                action_id=_trace_id(campaign_id, soldier_id, step),
                payload={"campaign_id": campaign_id, "step": step, "result": result},
            )
            if hasattr(attest, "__await__"):
                attest = await attest
            cred = {
                "soldier_id": soldier_id,
                "credential_id": getattr(attest, "credential_id", None),
                "action_id": getattr(attest, "action_id", None),
                "step": step,
            }
            await _emit(
                "marketing.tessera_attested",
                actor=soldier_id,
                payload={**cred, "campaign_id": campaign_id, "status": "OK"},
            )
            return cred
        except Exception:
            return None

    async def _submit_envelope(self, envelope: CampaignEnvelope) -> None:
        if self.attribution_receipt_client is None:
            await _emit(
                "marketing.campaign_executed",
                actor=self.AGENT_ID,
                payload={**asdict(envelope), "status": "REGISTRATION_PENDING"},
            )
            return
        try:
            submit = getattr(self.attribution_receipt_client, "submit", None)
            if submit is None:
                raise AttributeError("attribution_receipt_client.submit missing")
            tx = submit(envelope)
            if hasattr(tx, "__await__"):
                tx = await tx
            await _emit(
                "marketing.campaign_executed",
                actor=self.AGENT_ID,
                payload={**asdict(envelope), "status": "OK", "tx_or_id": str(tx)},
            )
        except Exception as exc:
            await _emit(
                "marketing.campaign_executed",
                actor=self.AGENT_ID,
                payload={**asdict(envelope), "status": "ATTEST_ERROR", "error": repr(exc)},
            )

    def _refusal_result(
        self,
        brief,
        channel_set_mask: int,
        *,
        refusal: Dict[str, Any],
        boardroom_session_id: str,
        outcome: str,
        weighted_score: float,
        votes: Optional[List[Dict[str, Any]]] = None,
        skill_outputs: Optional[Dict[str, Any]] = None,
        tessera_creds: Optional[List[Dict[str, Any]]] = None,
    ) -> CampaignResult:
        envelope = CampaignEnvelope(
            campaign_id=brief.campaign_id,
            brief_cid=_brief_cid(brief),
            audience_cluster_hash=_audience_cluster_hash([brief.audience_ring]),
            channel_set_mask=channel_set_mask,
            total_spend_usd_micro=0,
            outcome_metric_cid=_hash(f"refused:{brief.campaign_id}"),
            boardroom_session_id=boardroom_session_id,
            trace_id=_trace_id(brief.campaign_id, "ceo", "refused"),
        )
        self._last_summary = {
            "campaign_id": brief.campaign_id,
            "boardroom_session_id": boardroom_session_id,
            "outcome": outcome,
            "refused": refusal,
        }
        return CampaignResult(
            envelope=envelope,
            boardroom_session_id=boardroom_session_id,
            boardroom_outcome=outcome,
            weighted_score=float(weighted_score or 0.0),
            soldier_votes=list(votes or []),
            skill_outputs=skill_outputs or {},
            tessera_credentials=tessera_creds or [],
            refusal=refusal,
        )


__all__ = [
    "MarketingBoardroomOrchestrator",
    "CampaignEnvelope",
    "CampaignResult",
]
