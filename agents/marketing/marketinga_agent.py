"""
marketinga_agent — backward-compatible facade for the boardroom orchestrator.

The marketing capabilities are now distributed across the existing CEO + Seven
Soldiers boardroom (`daio.governance.boardroom.Boardroom`). This module
preserves the public `MarketingaAgent.get_instance()` + `propose_campaign()`
API by delegating to `agents.marketing.boardroom_orchestrator.MarketingBoardroomOrchestrator`.

Tests targeting the old API still pass; new tests prefer the
`MarketingBoardroomOrchestrator` directly.
"""

from __future__ import annotations

import asyncio
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional

from agents.marketing.boardroom_orchestrator import (
    CampaignEnvelope,
    CampaignResult,
    MarketingBoardroomOrchestrator,
)
from agents.marketing.content_agent import CampaignBrief
from agents.marketing.skills.protocol import LLMCaller
from agents.marketing.skills.registry import build_registry
from agents.marketing.tools.brand_code import load_brand_code


class _StubBoardroom:
    """Minimal stub that lets propose_campaign() run without a real Boardroom.

    Used when the caller doesn't supply one — it issues an `approved` outcome
    with a synthetic per-soldier vote so the skills exercise their skill paths.
    Production callers always inject the real `Boardroom.get_instance()`.
    """

    class _Vote:
        def __init__(self, soldier_id: str):
            self.soldier_id = soldier_id
            self.vote = "approve"
            self.reasoning = "stub auto-approve (no Boardroom wired)"
            self.confidence = 0.5
            self.weight = 1.0
            self.provider = "stub"

    class _Session:
        def __init__(self, members: List[str]):
            self.session_id = "br_stub_session"
            self.directive = ""
            self.outcome = "approved"
            self.weighted_score = 1.0
            self.votes = [_StubBoardroom._Vote(m) for m in members]
            self.dissent_branches = []
            self.model_report = {}

    async def convene(self, directive, importance="standard", members=None, consensus=0.666, **kw):
        member_list = [m.strip() for m in (members or "").split(",") if m.strip()]
        # Resolve `cpo` shorthand → `cpo_product`, etc.
        canonical = []
        for m in member_list:
            if m == "ceo" or "_" in m:
                canonical.append(m)
            else:
                canonical.append(
                    {
                        "cpo": "cpo_product",
                        "cto": "cto_technology",
                        "coo": "coo_operations",
                        "cfo": "cfo_finance",
                        "ciso": "ciso_security",
                        "clo": "clo_legal",
                        "cro": "cro_risk",
                    }.get(m, m)
                )
        return self._Session(canonical)


class MarketingaAgent:
    """Backward-compat facade. New code: use MarketingBoardroomOrchestrator."""

    _instance: Optional["MarketingaAgent"] = None
    _lock = asyncio.Lock()

    AGENT_ID = "marketinga"
    DID = "did:pythai:marketinga"
    ENS = "marketinga.bankon.eth"

    def __init__(self, orchestrator: MarketingBoardroomOrchestrator) -> None:
        self.orchestrator = orchestrator

    @classmethod
    async def get_instance(
        cls,
        brand_code_root: Path,
        toml_config_path: Path,
        *,
        llm_caller: LLMCaller,
        cascade_caller: Optional[LLMCaller] = None,
        boardroom: Any = None,
        boardroom_session_runner: Any = None,  # legacy kwarg — ignored
        tessera_client: Any = None,
        attribution_receipt_client: Any = None,
        identity_resolver: Optional[Callable[[], dict]] = None,
        data_root: Optional[Path] = None,
        domain: str = "marketing.umbrella",
        test_mode: bool = False,
    ) -> "MarketingaAgent":
        async with cls._lock:
            if cls._instance is None or test_mode:
                # Build the registry from the toml + injected callers
                with open(toml_config_path, "rb") as fh:
                    toml_cfg = tomllib.load(fh)
                rep_cfg = toml_cfg.get("reporting", {})
                exp_cfg = toml_cfg.get("experimentation", {})
                gov_cfg = toml_cfg.get("governance", {})
                risk_cfg = toml_cfg.get("risks", {})
                dist_cfg = toml_cfg.get("distribution", {})
                data_root_resolved = Path(data_root) if data_root else Path("data")

                def _resolve(rel_or_abs: Optional[str], default: Path) -> Path:
                    if not rel_or_abs:
                        return default
                    p = Path(rel_or_abs)
                    if p.is_absolute():
                        return p
                    if p.parts and p.parts[0] == "data":
                        return data_root_resolved / Path(*p.parts[1:])
                    return data_root_resolved / p

                from agents.marketing.tools.llms_txt_writer import SiteEntry
                sites_cfg = dist_cfg.get("llms_txt", {}).get("sites", [])
                sites = [SiteEntry(domain=s["domain"], product=s["product"]) for s in sites_cfg] or [
                    SiteEntry(domain="mindx.pythai.net", product="mindX"),
                ]

                registry = build_registry(
                    llm_caller=llm_caller,
                    cascade_caller=cascade_caller,
                    drafts_dir=data_root_resolved / "marketing" / "drafts",
                    outbox_dir=_resolve(dist_cfg.get("outbox_dir"), data_root_resolved / "marketing" / "outbox"),
                    llms_txt_dir=_resolve(
                        dist_cfg.get("llms_txt", {}).get("write_target_dir"),
                        data_root_resolved / "marketing" / "llms_txt",
                    ),
                    sites=sites,
                    geo_engines=list(rep_cfg.get("geo_engines", ["chatgpt", "claude", "perplexity", "gemini", "grok"])),
                    geo_brand_terms=list(rep_cfg.get("geo_brand_terms", ["mindX", "PYTHAI"])),
                    geo_prompts=[],   # reporting agent loads its own default
                    geo_cache_dir=data_root_resolved / "marketing" / "geo_cache",
                    geo_cache_seconds=int(rep_cfg.get("geo_cache_seconds", 86400)),
                    geo_weekly_budget_usd=float(rep_cfg.get("geo_weekly_budget_usd", 20.0)),
                    kpi_snapshots_dir=_resolve(
                        rep_cfg.get("kpi_snapshot_dir"),
                        data_root_resolved / "marketing" / "kpi_snapshots",
                    ),
                    treasury_client=None,
                    identity_resolver=identity_resolver,
                    forecast_spend_usd=0.0,
                    hard_stop_spend_usd=float(risk_cfg.get("hard_stop_spend_usd", 5000.0)),
                    spend_threshold_usd=float(gov_cfg.get("spend_threshold_usd", 500.0)),
                    max_variants=int(exp_cfg.get("max_variants_per_campaign", 4)),
                    holdout_rate=float(exp_cfg.get("holdout_rate", 0.10)),
                )

                # Reset orchestrator singleton in test mode so each test starts clean
                if test_mode:
                    MarketingBoardroomOrchestrator._reset_for_tests()

                orch = await MarketingBoardroomOrchestrator.get_instance(
                    brand_code_root=Path(brand_code_root),
                    toml_config_path=Path(toml_config_path),
                    registry=registry,
                    boardroom=boardroom or _StubBoardroom(),
                    tessera_client=tessera_client,
                    attribution_receipt_client=attribution_receipt_client,
                    domain=domain,
                    data_root=data_root_resolved,
                    test_mode=test_mode,
                )
                cls._instance = cls(orch)
            return cls._instance

    @classmethod
    def _reset_for_tests(cls) -> None:
        cls._instance = None
        MarketingBoardroomOrchestrator._reset_for_tests()

    def status(self) -> Dict[str, Any]:
        s = self.orchestrator.status()
        # Expose the legacy `sub_agents` field for backward-compat with the old
        # status shape; surface the new soldier_skills field too.
        s["sub_agents"] = [skill["soldier_id"] for skill in s.get("soldier_skills", [])]
        return s

    async def propose_campaign(
        self,
        brief: CampaignBrief,
        *,
        forecast_spend_usd: float = 0.0,
        channel_set_mask: int = 0b00000111,
        run_geo: bool = False,           # legacy kwarg — orchestrator runs GEO via CFO skill anyway
        env: Optional[dict] = None,      # legacy kwarg
        importance: str = "standard",
    ) -> CampaignResult:
        # Forward only the kwargs the orchestrator understands.
        return await self.orchestrator.propose_campaign(
            brief,
            forecast_spend_usd=forecast_spend_usd,
            channel_set_mask=channel_set_mask,
            importance=importance,
        )


__all__ = [
    "MarketingaAgent",
    "CampaignEnvelope",
    "CampaignResult",
    "CampaignBrief",
    "LLMCaller",
]
