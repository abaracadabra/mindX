# SPDX-License-Identifier: Apache-2.0
"""Tests for agents/wordpress_agent/featured_image.py — FeaturedImagePicker.

Pins the curated topic → file mapping so it can't rotate silently, and
verifies the fallback chain (explicit topic → keyword scan → doorway1)
plus the on-disk file-existence guarantee.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agents.wordpress_agent.featured_image import (
    GFX_ROOT,
    TOPIC_TO_FILE,
    FeaturedImagePicker,
)


# ─── Pin the curated mapping ─────────────────────────────────


def test_topic_map_has_required_keys():
    """The article-substrate keywords must exist in the curated map."""
    required = {
        "competition", "competitive", "agenticplace", "bankon",
        "openclaw", "hermes", "swarmclaw", "machine dreaming",
        "self-healing", "thot", "skill", "default",
    }
    missing = required - set(TOPIC_TO_FILE.keys())
    assert not missing, f"missing curated keywords: {missing}"


def test_topic_map_files_exist_on_disk():
    """Every mapped filename must exist under /gfx/."""
    missing: list[str] = []
    for keyword, filename in TOPIC_TO_FILE.items():
        if not (GFX_ROOT / filename).exists():
            missing.append(f"{keyword} → {filename}")
    assert not missing, f"mapped files missing on disk: {missing}"


# ─── pick() — explicit topic mode ────────────────────────────


# The picker prefers the CDN-safe ``gfx/jpg/<stem>.jpg`` variant when one
# exists (added 2026-05-13 — Hostinger CDN 504s on uploads > ~1.6MB).
# Assertions therefore pin the *stem* of the returned file rather than the
# full filename, so they pass for either the original PNG/WEBP asset or its
# converted JPG variant.


def test_pick_explicit_topic_competition():
    p = FeaturedImagePicker()
    out = p.pick(topic="competition")
    assert out.stem == "war_council_gold"


def test_pick_explicit_topic_agenticplace():
    p = FeaturedImagePicker()
    out = p.pick(topic="agenticplace")
    assert out.stem == "AgenticPlace"


def test_pick_explicit_topic_is_case_insensitive():
    p = FeaturedImagePicker()
    a = p.pick(topic="COMPETITION")
    b = p.pick(topic="  competition  ")
    c = p.pick(topic="competition")
    assert a == b == c


def test_pick_unknown_topic_falls_back_to_keyword_scan():
    """Unknown explicit topic + recognizable title keyword → keyword match."""
    p = FeaturedImagePicker()
    out = p.pick(topic="not-a-real-topic", title="A piece on AgenticPlace listings")
    assert out.stem == "AgenticPlace"


# ─── pick() — keyword scan mode ──────────────────────────────


def test_pick_title_keyword_competition():
    p = FeaturedImagePicker()
    out = p.pick(title="Competition is the substrate")
    assert out.stem == "war_council_gold"


def test_pick_title_keyword_openclaw_routes_to_peers_image():
    p = FeaturedImagePicker()
    out = p.pick(title="What OpenClaw pioneered")
    assert out.stem == "sevensoldiers"


def test_pick_inaugural_article_uses_competition_image():
    """The actual inaugural article title hits the competition keyword first."""
    p = FeaturedImagePicker()
    out = p.pick(
        title="Competition is the substrate: mindX, OpenClaw, Hermes, and the rails ahead",
        tags=["openclaw", "agenticplace", "bankon"],
    )
    # 'competition' appears in the title and comes before 'openclaw' in dict order.
    assert out.stem == "war_council_gold"


def test_pick_tag_keyword_bankon():
    p = FeaturedImagePicker()
    out = p.pick(title="Untitled draft", tags=["bankon"])
    assert out.stem == "bankonvault"


def test_pick_tag_keyword_hermes():
    p = FeaturedImagePicker()
    out = p.pick(title="Curator cadence", tags=["hermes"])
    assert out.stem == "sevensoldiers"


def test_pick_keyword_match_is_case_insensitive():
    p = FeaturedImagePicker()
    a = p.pick(title="BANKON vault sermon")
    b = p.pick(title="bankon vault sermon")
    assert a == b


# ─── pick() — fallback ───────────────────────────────────────


def test_pick_no_match_returns_default_doorway1():
    p = FeaturedImagePicker()
    out = p.pick(title="a completely unmatched article")
    assert out.stem == "doorway1"


def test_pick_with_no_inputs_returns_default():
    p = FeaturedImagePicker()
    out = p.pick()
    assert out.stem == "doorway1"


# ─── pick() — JPG variant preference (2026-05-13) ────────────


def test_pick_prefers_jpg_variant_when_present():
    """If gfx/jpg/<stem>.jpg exists, it must be preferred over the
    original PNG/WEBP for CDN-safety."""
    p = FeaturedImagePicker()
    out = p.pick(topic="bankon")
    # bankonvault.jpg was batch-converted under gfx/jpg/ — picker should pick it.
    if (GFX_ROOT / "jpg" / "bankonvault.jpg").exists():
        assert out.suffix == ".jpg"
        assert out.parent.name == "jpg"
    else:
        # Fallback path: no JPG variant on disk → original PNG returned.
        assert out.name == "bankonvault.png"


def test_pick_cypherpunk2048_topic_routes_to_bankonvault():
    """Phase D mapping: cypherpunk2048 → bankonvault asset."""
    p = FeaturedImagePicker()
    out = p.pick(topic="cypherpunk2048")
    assert out.stem == "bankonvault"


def test_pick_returns_existing_path():
    """Every pick() result must point at a real file on disk."""
    p = FeaturedImagePicker()
    for kwargs in [
        {"topic": "competition"},
        {"title": "OpenClaw"},
        {"tags": ["bankon"]},
        {},   # default
    ]:
        out = p.pick(**kwargs)
        assert out.exists(), f"pick({kwargs}) → {out} does not exist"


# ─── Hard fallback when mapped file is missing ───────────────


def test_first_doorway_fallback_when_mapped_file_gone(tmp_path):
    """If the curated mapping points at a file that doesn't exist, the
    picker walks the doorway* fallback chain rather than raising."""
    # Build a tmp gfx tree that has doorway2 but NOT doorway1 or the
    # curated 'competition' target (war_council_gold.png).
    (tmp_path / "doorway2.webp").write_bytes(b"x")
    p = FeaturedImagePicker(gfx_root=tmp_path)
    out = p.pick(topic="competition")
    assert out.name == "doorway2.webp"


def test_pure_function_never_raises(tmp_path):
    """Empty gfx_root + every input combination → no exception."""
    p = FeaturedImagePicker(gfx_root=tmp_path)
    # No assert on the return — just that it doesn't raise.
    for kwargs in [
        {"topic": "competition"},
        {"title": "anything"},
        {"tags": ["x", "y"]},
        {"topic": "competition", "title": "z", "tags": ["q"]},
    ]:
        p.pick(**kwargs)


# ─── Custom topic-map override ──────────────────────────────


def test_custom_topic_map(tmp_path):
    """Constructor accepts a custom map for tests / dev."""
    (tmp_path / "custom.png").write_bytes(b"x")
    p = FeaturedImagePicker(
        gfx_root=tmp_path,
        topic_map={"mything": "custom.png", "default": "custom.png"},
    )
    out = p.pick(topic="mything")
    assert out.name == "custom.png"
