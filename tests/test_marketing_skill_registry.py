"""Verify SOLDIER_SKILL_REGISTRY covers every boardroom soldier with correct weights."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.marketing.skills.registry import (
    DISPATCH_ORDER,
    VETO_SOLDIERS,
    build_registry,
)


# Mirror SOLDIER_WEIGHTS from daio.governance.boardroom but verified locally
# so this test does NOT need the heavy boardroom import path.
EXPECTED_SOLDIER_WEIGHTS = {
    "coo_operations": 1.0,
    "cfo_finance": 1.0,
    "cto_technology": 1.0,
    "ciso_security": 1.2,
    "clo_legal": 0.8,
    "cpo_product": 1.0,
    "cro_risk": 1.2,
}


async def _noop_llm(s, u):
    return ""


def _build():
    return build_registry(llm_caller=_noop_llm)


def test_registry_covers_all_seven_soldiers_plus_ceo():
    reg = _build()
    expected = set(EXPECTED_SOLDIER_WEIGHTS.keys()) | {"ceo"}
    assert set(reg.keys()) == expected, f"registry mismatch: {set(reg.keys()) ^ expected}"


def test_registry_weights_match_boardroom_weights():
    reg = _build()
    for sid, expected_weight in EXPECTED_SOLDIER_WEIGHTS.items():
        assert sid in reg, f"missing {sid}"
        skill = reg[sid]
        assert skill.WEIGHT == expected_weight, (
            f"{sid} weight {skill.WEIGHT} != boardroom weight {expected_weight}"
        )


def test_registry_skill_names_are_unique():
    reg = _build()
    names = [s.SKILL_NAME for s in reg.values()]
    assert len(names) == len(set(names)), f"duplicate skill names: {names}"


def test_dispatch_order_covers_every_soldier_except_ceo():
    """DISPATCH_ORDER drives the orchestrator's per-soldier skill loop. CEO is
    special-cased before/after the loop, so it does not appear in DISPATCH_ORDER."""
    assert "ceo" not in DISPATCH_ORDER
    assert set(DISPATCH_ORDER) == set(EXPECTED_SOLDIER_WEIGHTS.keys())


def test_veto_soldiers_are_ciso_and_cro():
    """Hard-veto contract: only CISO and CRO short-circuit on `reject`."""
    assert set(VETO_SOLDIERS) == {"ciso_security", "cro_risk"}


def test_dispatch_order_runs_ciso_before_cpo():
    """CISO must run BEFORE CPO so a faded identity blocks the draft."""
    ciso_idx = DISPATCH_ORDER.index("ciso_security")
    cpo_idx = DISPATCH_ORDER.index("cpo_product")
    assert ciso_idx < cpo_idx, "CISO must precede CPO in DISPATCH_ORDER"


def test_dispatch_order_runs_cro_after_cto():
    """CRO needs CTO's ExperimentPlan in prior_outputs to check holdout integrity."""
    cto_idx = DISPATCH_ORDER.index("cto_technology")
    cro_idx = DISPATCH_ORDER.index("cro_risk")
    assert cto_idx < cro_idx, "CRO must run after CTO so holdout integrity check has its input"


def test_dispatch_order_runs_cpo_before_cto_before_coo_before_cfo():
    """The HBR layers must dispatch in 1→2→3→4 order so each downstream skill
    can read its upstream's prior_outputs."""
    indices = [DISPATCH_ORDER.index(sid) for sid in (
        "cpo_product", "cto_technology", "coo_operations", "cfo_finance"
    )]
    assert indices == sorted(indices), f"HBR layer order broken: {indices}"
