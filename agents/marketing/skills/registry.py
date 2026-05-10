"""
Single source of truth: soldier_id ↔ marketing skill instance.

Tested directly in `tests/test_marketing_skill_registry.py` — verifies:
  - Every boardroom soldier_id has a skill registered (or is intentionally
    omitted, like CEO which is special-cased).
  - WEIGHT on each skill matches `daio.governance.boardroom.SOLDIER_WEIGHTS`.
  - No orphan skills (every registered key is in SOLDIER_WEIGHTS or is "ceo").

The registry is BUILT FROM A FACTORY each time because skills carry
runtime configuration (paths, llm callers, treasury client). Tests
construct their own factory; production wires the real one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

from agents.marketing.skills.cfo import CfoSkill
from agents.marketing.skills.ceo import CeoSkill
from agents.marketing.skills.ciso import CisoSkill
from agents.marketing.skills.clo import CloSkill
from agents.marketing.skills.coo import CooSkill
from agents.marketing.skills.cpo import CpoSkill
from agents.marketing.skills.cro import CroSkill
from agents.marketing.skills.cto import CtoSkill
from agents.marketing.skills.protocol import LLMCaller, SoldierSkill
from agents.marketing.tools.llms_txt_writer import SiteEntry


# Order is the dispatch order — the orchestrator runs skills in this sequence
# so each downstream skill can read the upstream's prior_outputs.
DISPATCH_ORDER: List[str] = [
    "ciso_security",   # Identity + voice gate runs FIRST so a bad brief stops here
    "clo_legal",       # Regulatory + competitor neutrality
    "cpo_product",     # Content drafting (HBR L1)
    "cto_technology",  # Experimentation (HBR L2)
    "coo_operations",  # Distribution (HBR L3)
    "cfo_finance",     # Reporting + treasury (HBR L4)
    "cro_risk",        # Spend risk + hard-stop (uses experimentation output)
]


# Soldier IDs that, on `vote == "reject"`, hard-veto the campaign regardless
# of weighted score. Mirrors `protocol.is_veto_soldier`.
VETO_SOLDIERS: tuple = ("ciso_security", "cro_risk")


def build_registry(
    *,
    llm_caller: LLMCaller,
    cascade_caller: Optional[LLMCaller] = None,
    drafts_dir: Optional[Path] = None,
    outbox_dir: Optional[Path] = None,
    llms_txt_dir: Optional[Path] = None,
    sites: Optional[Iterable[SiteEntry]] = None,
    geo_engines: Optional[List[str]] = None,
    geo_brand_terms: Optional[List[str]] = None,
    geo_prompts: Optional[List[str]] = None,
    geo_cache_dir: Optional[Path] = None,
    geo_cache_seconds: int = 86400,
    geo_weekly_budget_usd: float = 20.0,
    kpi_snapshots_dir: Optional[Path] = None,
    treasury_client: Any = None,
    identity_resolver: Optional[Callable[[], dict]] = None,
    forecast_spend_usd: float = 0.0,
    hard_stop_spend_usd: float = 5000.0,
    spend_threshold_usd: float = 500.0,
    max_variants: int = 4,
    holdout_rate: float = 0.10,
    rings: Optional[List[str]] = None,
) -> Dict[str, SoldierSkill]:
    """Build the canonical soldier_id → skill registry.

    Tests inject mocks; production wires real values from `marketinga.toml`.
    """
    sites_list = list(sites) if sites else [SiteEntry(domain="mindx.pythai.net", product="mindX")]

    return {
        "ceo": CeoSkill(),
        "cpo_product": CpoSkill(llm_caller=llm_caller, drafts_dir=drafts_dir),
        "cto_technology": CtoSkill(
            llm_caller=llm_caller,
            max_variants=max_variants,
            holdout_rate=holdout_rate,
            rings=rings,
        ),
        "coo_operations": CooSkill(
            outbox_dir=outbox_dir or Path("data/marketing/outbox"),
            llms_txt_dir=llms_txt_dir or Path("data/marketing/llms_txt"),
            sites=sites_list,
        ),
        "cfo_finance": CfoSkill(
            engines=list(geo_engines or ["chatgpt", "claude", "perplexity", "gemini", "grok"]),
            brand_terms=list(geo_brand_terms or ["mindX", "PYTHAI"]),
            prompts=list(geo_prompts or []),
            llm_caller=llm_caller,
            cascade_caller=cascade_caller,
            cache_dir=geo_cache_dir,
            cache_seconds=geo_cache_seconds,
            weekly_budget_usd=geo_weekly_budget_usd,
            snapshots_dir=kpi_snapshots_dir,
            treasury_client=treasury_client,
        ),
        "ciso_security": CisoSkill(identity_resolver=identity_resolver),
        "clo_legal": CloSkill(),
        "cro_risk": CroSkill(
            hard_stop_spend_usd=hard_stop_spend_usd,
            spend_threshold_usd=spend_threshold_usd,
            forecast_spend_usd=forecast_spend_usd,
        ),
    }


__all__ = ["build_registry", "DISPATCH_ORDER", "VETO_SOLDIERS"]
