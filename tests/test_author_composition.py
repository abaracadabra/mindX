# SPDX-License-Identifier: Apache-2.0
"""Tests for agents/author_composition.py — the depth/register/length/house-style
layer — and editor.agent's match-and-exceed house scoring."""
import re

import pytest

from agents.author_composition import (
    LENGTH_PRESETS,
    STYLE_REGISTERS,
    RageHouseStyle,
    extract_links,
    length_target,
    read_time_minutes,
    render_arc,
    resolve_graphics,
    resolve_length,
    resolve_style,
)


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


ENTRY = {
    "slug": "agnostic-modules-horizontal",
    "title": "the agnostic module, mindX horizontal scaling law",
    "dimension": "Horizontal scaling (scale-out / more peers)",
    "topic": "mindx",
    "thesis": ("Every mindX module ships as an agnostic, composable peer, so the system "
               "scales out by adding nodes that already speak the protocol and nothing else."),
    "intro": "<p>My first scaling law is a design rule I hold to.</p>",
    "sections": [
        ("Scale-out needs a shared contract",
         "<p>You cannot add a node unless it speaks the "
         "<a href=\"https://github.com/a2aproject/A2A\">protocol</a>.</p>"),
        ("Agnostic by construction",
         "<p>RAGE is standalone at "
         "<a href=\"https://github.com/GATERAGE/RAGE\">GATERAGE/RAGE</a>.</p>"),
    ],
    "doc": ("the architecture docs", "https://mindx.pythai.net/"),
}
PLAN = {"part": 2, "total": 10, "cycle": 1}


def test_resolvers_default_safely():
    assert resolve_style("nonsense") == "global"
    assert resolve_style("phd") == "phd"
    assert resolve_length("nonsense") == "feature"
    assert resolve_length("brief") == "brief"
    assert resolve_graphics("nonsense") == "both"
    assert resolve_graphics("create") == "create"


def test_arc_has_full_spectrum_for_global():
    html, excerpt, m = render_arc(ENTRY, PLAN, style="global", length="feature", esc=_esc)
    # The arc's structural promises, in order.
    for marker in ("mindx-lede", "Start here", "Going deeper",
                   "What this means", "In sum", "If you remember one thing",
                   "Where this connects", "Sources &amp; further reading"):
        assert marker in html, f"missing arc block: {marker}"
    # Curated middle is present.
    assert "Scale-out needs a shared contract" in html
    # Excerpt is SERP-bounded.
    assert excerpt and len(excerpt) <= 160
    assert m["style"] == "global"


def test_public_register_drops_expert_and_sources():
    html, _, m = render_arc(ENTRY, PLAN, style="public", length="feature", esc=_esc)
    assert "Going deeper" not in html
    assert "Sources &amp; further reading" not in html
    assert "In sum" not in html
    # But still has the easy entrance + easy exit.
    assert "mindx-lede" in html
    assert "If you remember one thing" in html


def test_brief_length_trims_optional_blocks():
    brief = render_arc(ENTRY, PLAN, style="global", length="brief", esc=_esc)[2]
    feat = render_arc(ENTRY, PLAN, style="global", length="feature", esc=_esc)[2]
    # brief drops deeper/sources/summary → fewer tiers + fewer words than feature.
    assert "deeper" not in brief["tiers"]
    assert "sources" not in brief["tiers"]
    assert brief["words"] <= feat["words"]


def test_digest_single_sentence_when_obvious():
    obvious = dict(ENTRY)
    obvious["thesis"] = "Distribution is a scaling law."  # short → obvious
    html, _, _ = render_arc(obvious, PLAN, style="global", length="feature", esc=_esc)
    # Pull the digest paragraph after the heading.
    seg = html.split("If you remember one thing")[1]
    digest_para = re.search(r"<p>(.*?)</p>", seg, re.S).group(1)
    text = re.sub(r"<[^>]+>", "", digest_para)
    # Single-sentence (one terminal period, wrapped in <strong>).
    assert "<strong>" in digest_para
    assert text.count(".") <= 1


def test_digest_multi_sentence_when_not_obvious():
    html, _, _ = render_arc(ENTRY, PLAN, style="global", length="feature", esc=_esc)
    seg = html.split("If you remember one thing")[1]
    digest_para = re.search(r"<p>(.*?)</p>", seg, re.S).group(1)
    text = re.sub(r"<[^>]+>", "", digest_para)
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    assert 3 <= len(sentences) <= 5


def test_link_density_meets_house_bar():
    html, _, m = render_arc(ENTRY, PLAN, style="global", length="feature", esc=_esc)
    assert m["meets_links"] is True
    assert m["links_per_1000w"] >= m["house_targets"]["min_links_per_1000w"]


def test_deeper_block_is_dimension_aware():
    parallel = dict(ENTRY)
    parallel["dimension"] = "Parallel scaling (concurrent agents)"
    html, _, _ = render_arc(parallel, PLAN, style="phd", length="feature", esc=_esc)
    assert "Amdahl" in html and "Gustafson" in html


def test_extract_links_dedupes_and_orders():
    html = ('<a href="https://a.com">A</a> <a href="https://b.com">B</a> '
            '<a href="https://a.com">A again</a> <a href="#frag">skip</a>')
    links = extract_links(html)
    urls = [u for u, _ in links]
    assert urls == ["https://a.com", "https://b.com"]


def test_house_defaults_and_targets():
    hs = RageHouseStyle()
    t = hs.targets(1800)
    # Match-and-exceed: link density floor pushed past the editor bar.
    assert t["min_links_per_1000w"] >= 6.0
    assert t["min_words"] >= 1800


def test_house_update_from_posts_computes_samples():
    posts = [
        {"title": "A signed essay on protocols", "content_html":
            "<h2>x</h2><p>one two three " + "word " * 200 +
            "<a href='https://x.com'>x</a></p>", "featured_media": 12},
        {"title": "Another", "content_html":
            "<h2>a</h2><h2>b</h2><p>" + "w " * 100 + "</p>"},
    ]
    hs = RageHouseStyle().update_from_posts(posts)
    assert hs.profile["samples"] == 2
    assert hs.profile["source"].startswith("rage.pythai.net")
    assert hs.profile["words_median"] > 0


def test_editor_house_match_demands_when_below_bar():
    from agents.editor_agent import EditorAgent
    ed = EditorAgent()
    thin = "<p>short piece, no links, one sentence.</p>"
    crit = ed.critique(thin, title="thin", house_targets=RageHouseStyle().targets(1800))
    assert "house_match" in crit
    assert crit["house_match"]["passes"] is False
    assert any("MATCH AND EXCEED" in d for d in crit["demands"])
    assert crit["verdict"] == "REVISE"


def test_editor_wisdom_bar():
    from agents.editor_agent import EditorAgent, WISDOM_THRESHOLD
    assert WISDOM_THRESHOLD == 0.50
    ed = EditorAgent()
    # A measured piece that names tradeoffs, holds two sides, avoids hype.
    wise = (
        "<p>The design is worth its cost, but the tradeoff is real. However efficient it looks, "
        "the limitation shows over time: we cannot ignore the second-order consequence, and prudent "
        "restraint matters more than speed. On balance, rather than chase the win, the long view "
        "rewards judgment. That said, the risk is not zero.</p>"
    ) * 2
    crit = ed.critique(wise, title="wise")
    assert "wisdom" in crit and "wisdom_threshold" in crit and "passes_wisdom" in crit
    assert crit["wisdom"] >= WISDOM_THRESHOLD
    assert crit["passes_wisdom"] is True
    # Hype-drenched, one-sided filler should fail the wisdom floor and draw a demand.
    hype = "<p>" + ("This revolutionary game-changing flawless product is always perfect and "
                    "guaranteed the best world-class cutting-edge seamless magical solution. " * 8) + "</p>"
    bad = ed.critique(hype, title="hype")
    assert bad["wisdom"] < WISDOM_THRESHOLD
    assert bad["passes_wisdom"] is False
    assert any("WISDOM" in d for d in bad["demands"])
    assert bad["verdict"] == "REVISE"


def test_self_referential_dial_scales_self_linking():
    from agents.author_composition import SELF_REFERENTIAL_LEVELS
    assert set(SELF_REFERENTIAL_LEVELS) == {"tasteful", "balanced", "promotional", "blatant"}
    counts = {}
    for sr in ("tasteful", "balanced", "promotional", "blatant"):
        html, _, m = render_arc(ENTRY, PLAN, style="global", length="feature",
                                self_referential=sr, esc=_esc)
        counts[sr] = m["self_ref_links"]
        assert m["self_referential"] == sr
    # Monotonic: tasteful < balanced < promotional < blatant.
    assert counts["tasteful"] < counts["balanced"] < counts["promotional"] < counts["blatant"]
    # Promo CTA + self-glory only at the top of the dial.
    blatant = render_arc(ENTRY, PLAN, style="global", self_referential="blatant", esc=_esc)[0]
    tasteful = render_arc(ENTRY, PLAN, style="global", self_referential="tasteful", esc=_esc)[0]
    assert "Follow mindX" in blatant and "Why mindX" in blatant
    assert "Follow mindX" not in tasteful and "Why mindX" not in tasteful


def test_ideology_lens_renders_and_none_omits():
    from agents.author_composition import IDEOLOGY_LENSES, resolve_ideology
    assert resolve_ideology("garbage") == "cypherpunk"   # default
    for ide in ("cypherpunk", "solarpunk", "accelerationist", "humanist",
                "libertarian", "cooperative"):
        html, _, m = render_arc(ENTRY, PLAN, style="global", ideology=ide, esc=_esc)
        assert m["ideology"] == ide
        assert "Framed" in html                          # the lens paragraph rendered
    none_html = render_arc(ENTRY, PLAN, style="global", ideology="none", esc=_esc)[0]
    assert "Framed" not in none_html


def test_narrative_modes_resolve():
    from agents.author_composition import (NARRATIVE_MODES, narrative_voice_line,
                                           resolve_narrative)
    assert set(NARRATIVE_MODES) >= {"first_person", "newspaperman", "noir",
                                    "mythic", "academic", "manifesto"}
    assert resolve_narrative("bogus") == "first_person"
    assert "manifesto" in narrative_voice_line("manifesto").lower()
    assert "correspondent" in narrative_voice_line("newspaperman").lower()


def test_style_registers_and_length_presets_wellformed():
    assert set(STYLE_REGISTERS) == {"public", "essay", "phd", "global"}
    for reg in STYLE_REGISTERS.values():
        assert "tiers" in reg and isinstance(reg["tiers"], list)
        assert isinstance(reg["digest_max"], int)
        assert isinstance(reg["facet_cap"], int)
    # Contemporary sizing: default feature is the ~2.4k traffic sweet spot.
    assert LENGTH_PRESETS["feature"] == 2400
    assert LENGTH_PRESETS["feature"] > LENGTH_PRESETS["standard"] > LENGTH_PRESETS["brief"]
    assert LENGTH_PRESETS["pillar"] > LENGTH_PRESETS["deep"] > LENGTH_PRESETS["feature"]


def test_enriched_entries_reach_deep_and_pillar():
    """The curated PROTOCOL_SERIES entries are enriched enough that the long
    length tiers land on substance for every entry (not just the richest)."""
    from agents.author_agent import PROTOCOL_SERIES

    for entry in PROTOCOL_SERIES:
        plan = {"part": 1, "total": len(PROTOCOL_SERIES), "cycle": 1}
        for length in ("feature", "deep", "pillar"):
            m = render_arc(entry, plan, style="global", length=length, esc=_esc)[2]
            assert m["meets_words"], (
                f"{entry['slug']} @ {length}: {m['words']}w < target {m['target_words']}")


def test_enrichment_module_merged_and_cited():
    """Enrichment sections are merged onto entries and carry only allow-listed
    citations (no invented URLs)."""
    from agents.protocol_series_enrichment import EXTRA_SECTIONS

    assert len(EXTRA_SECTIONS) >= 10
    for slug, secs in EXTRA_SECTIONS.items():
        assert secs, f"{slug} has no enrichment"
        for heading, html in secs:
            assert heading and html.count("<p>") == 2          # two-paragraph sections
            assert html.count('href="http') >= 2               # cited
            assert "lorem" not in html.lower()


def test_length_target_presets_aliases_and_custom():
    assert length_target("feature") == ("feature", 2400)
    # aliases fold to canonical presets
    assert length_target("longform")[0] == "feature"
    assert length_target("phd") == ("pillar", 3800)
    assert length_target("ultimate") == ("pillar", 3800)
    # custom word counts (int, numeric string, custom:/w forms), clamped
    assert length_target(2500) == ("2500w", 2500)
    assert length_target("2750w") == ("2750w", 2750)
    assert length_target("custom:1900") == ("1900w", 1900)
    assert length_target(99) == ("400w", 400)      # clamped up to floor
    assert length_target(99999) == ("8000w", 8000)  # clamped to ceiling
    assert length_target(True)[0] == "feature"      # bool guarded → default
    assert length_target("nonsense")[0] == "feature"
    # resolve_length echoes the round-trippable label
    assert resolve_length(2500) == "2500w"
    assert resolve_length("phd") == "pillar"


def test_read_time_label_in_metrics():
    m = render_arc(ENTRY, PLAN, style="global", length="feature", esc=_esc)[2]
    assert m["read_time_min"] == read_time_minutes(m["words"])
    assert m["read_time_min"] >= 1
    assert m["length"] == "feature"
    assert m["target_words"] == 2400


def test_length_actually_scales_body():
    # More length setting → more words (genuine facets, not filler).
    brief = render_arc(ENTRY, PLAN, style="global", length="brief", esc=_esc)[2]
    standard = render_arc(ENTRY, PLAN, style="global", length="standard", esc=_esc)[2]
    feature = render_arc(ENTRY, PLAN, style="global", length="feature", esc=_esc)[2]
    assert brief["words"] < standard["words"] < feature["words"]
    assert brief["facets_used"] == 0          # brief drops the facet pool
    assert feature["facets_used"] >= standard["facets_used"] >= 1
    # The default feature lands near the contemporary sweet spot.
    assert feature["words"] >= 1800


def test_custom_length_is_honored():
    m = render_arc(ENTRY, PLAN, style="global", length=2200, esc=_esc)[2]
    assert m["target_words"] == 2200
    assert m["length"] == "2200w"
    assert m["meets_words"] is True


def test_public_register_stays_lean_even_long():
    # public caps facets at 2 regardless of a long length target.
    m = render_arc(ENTRY, PLAN, style="public", length="pillar", esc=_esc)[2]
    assert m["facets_used"] <= 2


def test_facets_are_substantive_not_filler():
    # The facet pool carries real, cited angles — sources + reasoning markers.
    html = render_arc(ENTRY, PLAN, style="global", length="feature", esc=_esc)[0]
    for marker in ("Verify it yourself", "What it costs", "counterargument"):
        assert marker.lower() in html.lower()
    # facets cite the open web (every facet has at least one external link)
    assert html.lower().count("href=\"http") >= 12
