"""Tests for the brand_code loader."""

from __future__ import annotations

import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agents.marketing.tools.brand_code import BrandCode, load_brand_code


REPO_BRAND_CODE = Path(__file__).resolve().parents[1] / "data" / "brand_code"


def test_loads_repo_brand_code():
    brand = load_brand_code(REPO_BRAND_CODE)
    assert isinstance(brand, BrandCode)
    assert brand.voice_register() in {"cypherpunk", "cypherpunk\n"}
    assert brand.pillars_md.startswith("---") or "pillars" in brand.pillars_md.lower()


def test_brand_code_is_frozen():
    brand = load_brand_code(REPO_BRAND_CODE)
    with pytest.raises(FrozenInstanceError):
        brand.voice_md = "tampered"  # type: ignore[misc]


def test_pillar_is_reserved_only_for_code_as_dojo():
    brand = load_brand_code(REPO_BRAND_CODE)
    assert brand.pillar_is_reserved("code_as_dojo") is True
    assert brand.pillar_is_reserved("CODE_AS_DOJO") is True
    assert brand.pillar_is_reserved("cognition_you_own") is False


def test_audience_E_is_reserved():
    brand = load_brand_code(REPO_BRAND_CODE)
    assert brand.audience_is_reserved("E") is True
    assert brand.audience_is_reserved("e") is True
    assert brand.audience_is_reserved("A") is False


def test_forbidden_terms_compile_and_match():
    brand = load_brand_code(REPO_BRAND_CODE)
    deny, _ = brand.forbidden.scan("This is going to the moon!")
    assert deny, "deny_pattern must match 'to the moon'"
    deny2, _ = brand.forbidden.scan("Stake your tokens for guaranteed returns.")
    assert deny2, "deny_pattern must match 'guaranteed' clauses"
    deny3, _ = brand.forbidden.scan("Cypherpunk cognition you own.")
    assert not deny3, "neutral copy must not match deny_pattern"


def test_competitor_map_has_required_competitors():
    brand = load_brand_code(REPO_BRAND_CODE)
    for must_have in ("bittensor", "olas", "virtuals"):
        assert brand.has_competitor_constraints(must_have), f"missing competitor: {must_have}"


def test_load_fails_loudly_on_missing_root(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_brand_code(tmp_path / "no-such-dir")


def test_synthetic_brand_code_minimum_shape(tmp_path):
    """Build a minimum brand_code under tmp_path and verify it loads."""
    (tmp_path / "voice.md").write_text("voice_register: test\n", encoding="utf-8")
    (tmp_path / "positioning").mkdir()
    (tmp_path / "positioning" / "pillars.md").write_text("# pillars\n", encoding="utf-8")
    (tmp_path / "positioning" / "icp_segments.md").write_text("# icp\n", encoding="utf-8")
    (tmp_path / "regulatory_constraints.md").write_text("# regs\n", encoding="utf-8")
    (tmp_path / "forbidden_terms.json").write_text(
        json.dumps({"deny_patterns": ["(?i)moon"], "soft_warn_patterns": []}),
        encoding="utf-8",
    )
    (tmp_path / "competitor_map.json").write_text(
        json.dumps({"rule": "neutral", "competitors": {"x": {}}}),
        encoding="utf-8",
    )
    brand = load_brand_code(tmp_path)
    assert brand.voice_register() == "test"
    assert brand.competitors.by_name == {"x": {}}
    deny, _ = brand.forbidden.scan("To the Moon!")
    assert deny == ["Moon"]
